import re
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser


@dataclass
class DadosFarmacia:
    nome: str
    # 4 badges principais
    aguardando_atendimento: int
    em_andamento: int
    atendimentos_finalizados: int
    total_atendimentos: int
    # métricas extras
    vendas_realizadas: int
    vendas_nao_realizadas: int
    receita_total: float
    periodo_inicio: str
    periodo_fim: str
    erro: Optional[str] = None


def _parse_moeda(texto: str) -> float:
    """Converte 'R$48.146,84' → 48146.84"""
    limpo = re.sub(r"[R$\s]", "", texto).replace(".", "").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return 0.0


def _parse_inteiro(texto: str) -> int:
    limpo = re.sub(r"\D", "", texto)
    return int(limpo) if limpo else 0


async def _fazer_login(page: Page, email: str, senha: str) -> bool:
    await page.fill('input[type="email"]', email)
    await page.fill('input[type="password"]', senha)
    # Tenta "Entrar" (pt-BR) e "Sign In" (en) como fallback
    botao = page.locator('button:has-text("Entrar"), button:has-text("Sign In"), button[type="submit"]')
    await botao.first.click(timeout=10000)
    try:
        # Aguarda sair da página de login (pode ir para novidades ou dashboard)
        await page.wait_for_function("!window.location.pathname.includes('login')", timeout=15000)
        # Navega explicitamente para o dashboard
        base = page.url.split("/")[0] + "//" + page.url.split("/")[2]
        await page.goto(f"{base}/dashboard", timeout=15000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        return True
    except Exception:
        return False


async def _aplicar_filtro_datas(page: Page, inicio: str, fim: str):
    """
    Abre o painel de filtros e define o período.
    inicio / fim no formato YYYY-MM-DD.
    """
    # Abre o painel — botão aparece em pt-BR ou en dependendo do browser
    filtros_btn = page.locator(
        'button:has-text("Filtros"), span:has-text("Filtros"), '
        'button:has-text("Filters"), span:has-text("Filters")'
    )
    if await filtros_btn.count() > 0:
        await filtros_btn.first.click()
        await page.wait_for_timeout(800)

    # Tenta input[type="date"] primeiro, depois input genérico dentro do painel de filtros
    date_inputs = page.locator('input[type="date"]')
    if await date_inputs.count() < 2:
        # Alguns dashboards usam input[type="text"] com máscara de data
        date_inputs = page.locator('input[placeholder*="/"], input[placeholder*="-"], input[class*="date"]')

    # Converte YYYY-MM-DD para DD/MM/YYYY (formato BR usado em alguns inputs de texto)
    d_inicio = datetime.strptime(inicio, "%Y-%m-%d")
    d_fim    = datetime.strptime(fim,    "%Y-%m-%d")
    br_inicio = d_inicio.strftime("%d/%m/%Y")
    br_fim    = d_fim.strftime("%d/%m/%Y")

    count = await date_inputs.count()
    if count >= 2:
        # Tenta fill direto (type=date) senão usa triple_click + type para inputs mascarados
        try:
            await date_inputs.nth(0).fill(inicio, timeout=5000)
            await date_inputs.nth(1).fill(fim,    timeout=5000)
        except Exception:
            await date_inputs.nth(0).triple_click()
            await date_inputs.nth(0).type(br_inicio)
            await date_inputs.nth(1).triple_click()
            await date_inputs.nth(1).type(br_fim)

    # Salvar — tenta pt-BR e en
    salvar_btn = page.locator('button:has-text("Salvar"), button:has-text("Save")')
    if await salvar_btn.count() > 0:
        await salvar_btn.first.click()

    await page.wait_for_load_state("networkidle", timeout=20000)
    await page.wait_for_timeout(1500)

    # Fecha o painel de filtros com Escape (funciona em overlays React/Vue)
    try:
        date_still_visible = await page.locator('input[type="date"]').is_visible()
        if date_still_visible:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(600)
    except Exception:
        pass


async def _extrair_metricas(page: Page) -> dict:
    """Extrai os números do dashboard após o filtro ter sido aplicado."""
    dados = {
        "aguardando_atendimento": 0,
        "em_andamento": 0,
        "atendimentos_finalizados": 0,
        "total_atendimentos": 0,
        "vendas_realizadas": 0,
        "vendas_nao_realizadas": 0,
        "receita_total": 0.0,
    }

    # Garante que o painel de filtros está fechado (clica fora se ainda aberto)
    try:
        date_visible = await page.locator('input[type="date"]').is_visible()
        if date_visible:
            await page.mouse.click(500, 300)
            await page.wait_for_timeout(600)
    except Exception:
        pass

    # Rola o container da sidebar (painel direito fixo)
    await page.evaluate("""
        const selectors = [
            '[class*="sidebar-right"]', '[class*="right-sidebar"]',
            '[class*="metrics"]', '[class*="stats"]', 'aside'
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) { el.scrollTop = el.scrollHeight; break; }
        }
        window.scrollTo(0, document.body.scrollHeight);
    """)
    await page.wait_for_timeout(800)

    # Receita — "Você possui R$X em vendas!"
    try:
        corpo = await page.locator("body").text_content(timeout=5000)
        match = re.search(r"R\$\s*[\d.,]+", corpo or "")
        if match:
            dados["receita_total"] = _parse_moeda(match.group())
    except Exception:
        pass

    # Usa evaluate para mapear todos os badges numericos e seus labels do DOM
    badges_dom = await page.evaluate("""
        () => {
            const resultado = [];
            // Pega todo texto visível e busca padrões número + label
            document.querySelectorAll('*').forEach(el => {
                const txt = el.innerText || '';
                const filhos = el.children.length;
                // Elemento folha com número grande
                if (filhos === 0 && /^\\d+$/.test(txt.trim()) && parseInt(txt) > 10) {
                    const pai = el.parentElement;
                    const labelEl = pai ? pai.querySelector('*:not(:first-child)') : null;
                    const label = labelEl ? (labelEl.innerText || '').trim() : '';
                    const avo = pai ? pai.parentElement : null;
                    const labelAvo = avo ? (avo.innerText || '').trim() : '';
                    resultado.push({
                        numero: parseInt(txt.trim()),
                        label: label || labelAvo.replace(txt.trim(), '').trim()
                    });
                }
            });
            return resultado;
        }
    """)

    # Mapeia badges para campos pelo conteúdo do label
    for b in badges_dom:
        num = b.get("numero", 0)
        label = (b.get("label") or "").lower()
        if num < 0:
            continue
        if ("aguard" in label or "waiting" in label) and dados["aguardando_atendimento"] == 0:
            dados["aguardando_atendimento"] = num
        elif ("andamento" in label or "progress" in label or "ongoing" in label) and dados["em_andamento"] == 0:
            dados["em_andamento"] = num
        elif "finaliz" in label and dados["atendimentos_finalizados"] == 0:
            dados["atendimentos_finalizados"] = num
        elif "total" in label and "atendimento" in label and dados["total_atendimentos"] == 0:
            dados["total_atendimentos"] = num
        elif ("venda" in label or "sale" in label) and "não" not in label and "nao" not in label and dados["vendas_realizadas"] == 0:
            dados["vendas_realizadas"] = num
        elif ("não realiz" in label or "nao realiz" in label or "unrealiz" in label) and dados["vendas_nao_realizadas"] == 0:
            dados["vendas_nao_realizadas"] = num

    return dados


async def coletar_farmacia(
    nome: str,
    url_base: str,
    email: str,
    senha: str,
    browser: Browser,
    dias: int = 7,
    headless: bool = True,
) -> DadosFarmacia:
    hoje = datetime.now()
    inicio = (hoje - timedelta(days=dias)).strftime("%Y-%m-%d")
    fim = hoje.strftime("%Y-%m-%d")

    context = await browser.new_context(locale="pt-BR")
    page = await context.new_page()

    try:
        await page.goto(f"{url_base}/", timeout=20000)

        logado = await _fazer_login(page, email, senha)
        if not logado:
            return DadosFarmacia(
                nome=nome,
                aguardando_atendimento=0, em_andamento=0,
                atendimentos_finalizados=0, total_atendimentos=0,
                vendas_realizadas=0, vendas_nao_realizadas=0,
                receita_total=0, periodo_inicio=inicio, periodo_fim=fim,
                erro="Falha no login — verifique e-mail e senha",
            )

        await _aplicar_filtro_datas(page, inicio, fim)
        m = await _extrair_metricas(page)

        return DadosFarmacia(
            nome=nome,
            aguardando_atendimento=m["aguardando_atendimento"],
            em_andamento=m["em_andamento"],
            atendimentos_finalizados=m["atendimentos_finalizados"],
            total_atendimentos=m["total_atendimentos"],
            vendas_realizadas=m["vendas_realizadas"],
            vendas_nao_realizadas=m["vendas_nao_realizadas"],
            receita_total=m["receita_total"],
            periodo_inicio=inicio,
            periodo_fim=fim,
        )

    except Exception as e:
        return DadosFarmacia(
            nome=nome,
            aguardando_atendimento=0, em_andamento=0,
            atendimentos_finalizados=0, total_atendimentos=0,
            vendas_realizadas=0, vendas_nao_realizadas=0,
            receita_total=0, periodo_inicio=inicio, periodo_fim=fim,
            erro=str(e),
        )
    finally:
        await context.close()


async def coletar_todas(farmacias: list[dict], paralelo: int = 5) -> list[DadosFarmacia]:
    resultados = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)

        # Processa em lotes para não sobrecarregar
        for i in range(0, len(farmacias), paralelo):
            lote = farmacias[i: i + paralelo]
            tarefas = [
                coletar_farmacia(
                    nome=f["nome"],
                    url_base=f["url_base"],
                    email=f["email"],
                    senha=f["senha"],
                    browser=browser,
                )
                for f in lote
            ]
            resultados_lote = await asyncio.gather(*tarefas)
            resultados.extend(resultados_lote)
            print(f"  Lote {i // paralelo + 1} concluído ({len(resultados)}/{len(farmacias)})")

        await browser.close()

    return resultados
