"""
Teste do scraper para UMA farmácia.
Abre o Chrome visível para você acompanhar o que está sendo coletado.
Execute: python testar_scraper.py
"""

import asyncio
from playwright.async_api import async_playwright
from farmacia_monitor.scraper.pharmachatbot import (
    _fazer_login,
    _aplicar_filtro_datas,
    _extrair_metricas,
)
from datetime import datetime, timedelta

# ─── CONFIGURE AQUI ──────────────────────────────────────────────────────────
URL_BASE = "https://app13.pharmachatbot.com.br"
EMAIL    = "suporte@drogariasaorafael.com"
SENHA    = "v!g?u7DYNI1Wnvr/T3"
# ─────────────────────────────────────────────────────────────────────────────

async def testar():
    hoje   = datetime.now()
    inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
    fim    = hoje.strftime("%Y-%m-%d")

    print(f"\n{'='*55}")
    print(f"  Teste do Scraper — PharmaChatBot")
    print(f"  URL    : {URL_BASE}")
    print(f"  Periodo: {inicio} ate {fim}")
    print(f"{'='*55}\n")

    async with async_playwright() as pw:
        # headless=False → Chrome visível para você acompanhar
        browser = await pw.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="pt-BR",
        )
        page    = await context.new_page()

        print(">> Abrindo login...")
        await page.goto(f"{URL_BASE}/", timeout=20000)
        await page.screenshot(path="debug_01_login.png")

        print(">> Fazendo login...")
        logado = await _fazer_login(page, EMAIL, SENHA)

        if not logado:
            await page.screenshot(path="debug_02_erro_login.png")
            print("\n[ERRO] Login falhou!")
            print("  Verifique e-mail e senha no topo deste arquivo.")
            print("  Screenshot salvo: debug_02_erro_login.png")
            await browser.close()
            return

        print(">> Login OK — aguardando dashboard carregar...")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="debug_02_dashboard.png")

        print(f">> Aplicando filtro de datas ({inicio} ate {fim})...")
        await _aplicar_filtro_datas(page, inicio, fim)
        await page.wait_for_timeout(2000)
        await page.screenshot(path="debug_03_filtro.png")

        # Rola a pagina para revelar todos os elementos da sidebar
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="debug_03b_sidebar_baixo.png")
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        # Dump do texto da sidebar direita para descobrir labels exatos
        sidebar_texto = await page.locator("body").text_content()
        print("\n--- TEXTO DA SIDEBAR (para debug) ---")
        linhas = [l.strip() for l in (sidebar_texto or "").split("\n") if l.strip()]
        # Mostra apenas numeros grandes e seus labels proximos
        for i, linha in enumerate(linhas):
            if linha.isdigit() and int(linha) > 50:
                contexto = linhas[max(0,i-1):i+3]
                print("  " + " | ".join(contexto))
        print("-------------------------------------\n")

        print(">> Extraindo metricas...")
        metricas = await _extrair_metricas(page)
        await page.screenshot(path="debug_04_metricas.png")

        await browser.close()

    print(f"\n{'='*55}")
    print(f"  Resultado da coleta")
    print(f"{'='*55}")
    print(f"  Aguardando atendimento   : {metricas['aguardando_atendimento']}")
    print(f"  Em andamento             : {metricas['em_andamento']}")
    print(f"  Atendimentos finalizados : {metricas['atendimentos_finalizados']}")
    print(f"  Total de atendimentos    : {metricas['total_atendimentos']}")
    print(f"  ---")
    print(f"  Vendas realizadas        : {metricas['vendas_realizadas']}")
    print(f"  Vendas nao realizadas    : {metricas['vendas_nao_realizadas']}")
    print(f"  Receita total            : R$ {metricas['receita_total']:,.2f}")

    badges_principais = [
        metricas['atendimentos_finalizados'],
        metricas['total_atendimentos'],
    ]
    zeros = sum(1 for v in badges_principais if v == 0)
    print(f"\n{'='*55}")
    if zeros == 2:
        print("  [ATENCAO] Badges principais zerados — verifique os seletores")
    elif zeros > 0:
        print(f"  [PARCIAL] Alguns badges nao coletados")
    else:
        print("  [SUCESSO] Todas as metricas coletadas corretamente!")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    asyncio.run(testar())
