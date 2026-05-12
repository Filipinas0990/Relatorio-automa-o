"""
Teste do scraper para UMA farmácia com Chrome visível.
Execute: python testar_scraper.py
"""
import asyncio
from playwright.async_api import async_playwright
from farmacia_monitor.scraper.pharmachatbot import (
    _fazer_login, _aplicar_filtro_datas,
    _extrair_canais_pizza, _extrair_receita,
    _extrair_vendas_badge, _extrair_total_atendimentos,
    _mapear_canais,
)
from datetime import datetime, timedelta

URL_BASE = "https://app13.pharmachatbot.com.br"
EMAIL    = "suporte@drogariasaorafael.com"
SENHA    = "v!g?u7DYNI1Wnvr/T3"


async def testar():
    hoje   = datetime.now()
    inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
    fim    = hoje.strftime("%Y-%m-%d")

    print(f"\n{'='*55}")
    print(f"  Teste do Scraper")
    print(f"  Periodo: {inicio} ate {fim}")
    print(f"{'='*55}\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="pt-BR",
        )
        page = await context.new_page()

        print(">> Login...")
        await page.goto(f"{URL_BASE}/", timeout=20000)
        if not await _fazer_login(page, EMAIL, SENHA):
            print("[ERRO] Login falhou")
            await browser.close()
            return

        print(">> Aplicando filtro de datas...")
        await _aplicar_filtro_datas(page, inicio, fim)

        print(">> Extraindo dados...\n")

        receita, vendas, total_atend = await asyncio.gather(
            _extrair_receita(page),
            _extrair_vendas_badge(page),
            _extrair_total_atendimentos(page),
        )

        print(">> Lendo grafico de canais (hover nas fatias)...")
        canais_raw = await _extrair_canais_pizza(
            page, "Quantidade de atendimentos por canal de divulga"
        )
        mapeado = _mapear_canais(canais_raw)

        await browser.close()

    print(f"\n{'='*55}")
    print(f"  Resultado")
    print(f"{'='*55}")
    print(f"\n  ORIGEM DOS CLIENTES:")
    print(f"  Google           : {mapeado['google']}")
    print(f"  Facebook/Insta   : {mapeado['facebook']}")
    print(f"  Grupos de Oferta : {mapeado['grupos_oferta']}")
    print(f"  Total atendimentos: {total_atend}")
    print(f"\n  VENDAS:")
    print(f"  Vendas realizadas: {vendas}")
    print(f"  Faturamento total: R$ {receita:,.2f}")

    print(f"\n  TODOS OS CANAIS COLETADOS:")
    for canal, total in sorted(canais_raw.items(), key=lambda x: -x[1]):
        print(f"    {canal:35} {total}")

    ok = mapeado["google"] > 0 or mapeado["facebook"] > 0 or mapeado["grupos_oferta"] > 0
    print(f"\n{'='*55}")
    print(f"  {'[SUCESSO]' if ok else '[ATENCAO] Canais zerados — hover nao funcionou'}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    asyncio.run(testar())
