"""
Pipeline principal — coleta, processa e salva no banco.
Executado automaticamente todo domingo às 22h via cron/Task Scheduler.
"""

import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from farmacia_monitor.scraper.pharmachatbot import coletar_todas
from farmacia_monitor.processor.score import calcular_score, MetricasSemana
from farmacia_monitor.database.db import init_db, SessionLocal, Farmacia, Coleta


def carregar_farmacias() -> list[dict]:
    caminho = os.path.join(os.path.dirname(__file__), "config", "farmacias.json")
    with open(caminho, encoding="utf-8") as f:
        todas = json.load(f)
    return [fa for fa in todas if fa.get("ativa", True)]


def _coleta_anterior(db, farmacia_id: int) -> Coleta | None:
    return (
        db.query(Coleta)
        .filter(Coleta.farmacia_id == farmacia_id)
        .order_by(Coleta.data_coleta.desc())
        .first()
    )


def salvar_resultados(dados_coletados):
    init_db()
    db = SessionLocal()
    try:
        for dado in dados_coletados:
            if dado.erro:
                print(f"  [ERRO]    {dado.nome}: {dado.erro}")
                continue

            farmacia = db.query(Farmacia).filter(Farmacia.nome == dado.nome).first()
            if not farmacia:
                print(f"  [AVISO]   {dado.nome} nao encontrada no banco.")
                continue

            anterior = _coleta_anterior(db, farmacia.id)
            metricas_anterior = None
            if anterior:
                metricas_anterior = MetricasSemana(
                    total_atendimentos=int(anterior.total_atendimentos or 0),
                    atendimentos_finalizados=int(anterior.atendimentos_finalizados or 0),
                    vendas_realizadas=int(anterior.vendas_realizadas or 0),
                    receita_total=float(anterior.receita_total or 0),
                )

            score_info = calcular_score(
                MetricasSemana(
                    total_atendimentos=dado.total_atendimentos,
                    atendimentos_finalizados=dado.atendimentos_finalizados,
                    vendas_realizadas=dado.vendas_realizadas,
                    receita_total=dado.receita_total,
                ),
                metricas_anterior,
            )

            coleta = Coleta(
                farmacia_id=farmacia.id,
                periodo_inicio=dado.periodo_inicio,
                periodo_fim=dado.periodo_fim,
                aguardando_atendimento=dado.aguardando_atendimento,
                em_andamento=dado.em_andamento,
                atendimentos_finalizados=dado.atendimentos_finalizados,
                total_atendimentos=dado.total_atendimentos,
                vendas_realizadas=dado.vendas_realizadas,
                vendas_nao_realizadas=dado.vendas_nao_realizadas,
                receita_total=dado.receita_total,
                score_criticidade=score_info["score_criticidade"],
                nivel_alerta=score_info["nivel_alerta"],
                taxa_conversao=score_info["taxa_conversao"],
                variacao_receita=score_info["variacao_receita"],
                variacao_atendimentos=score_info["variacao_atendimentos"],
                variacao_vendas=score_info["variacao_vendas"],
            )
            db.add(coleta)

            alertas = score_info.get("alertas", [])
            alerta_str = " | ".join(alertas) if alertas else "OK"
            print(
                f"  [{score_info['nivel_alerta'].upper():8}] {dado.nome:40} "
                f"Score: {score_info['score_criticidade']:5.1f} | {alerta_str}"
            )

        db.commit()
    finally:
        db.close()


async def pipeline():
    print(f"\n{'='*60}")
    print(f"  Pipeline iniciado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}\n")

    farmacias = carregar_farmacias()
    print(f"  Farmacias ativas: {len(farmacias)}\n")

    print("  Coletando dados...\n")
    resultados = await coletar_todas(farmacias, paralelo=5)

    print("\n  Processando e salvando...\n")
    salvar_resultados(resultados)

    erros = [r for r in resultados if r.erro]
    sucesso = len(resultados) - len(erros)

    print(f"\n{'='*60}")
    print(f"  Concluido: {sucesso}/{len(resultados)} farmacias coletadas")
    if erros:
        print(f"  Erros: {len(erros)} ({', '.join(e.nome for e in erros)})")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(pipeline())
