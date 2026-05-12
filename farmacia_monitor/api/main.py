"""
API FastAPI — serve os dados do PostgreSQL para o frontend (PharmaFlow).
Endpoints consumidos pelas telas: Painel Geral, Farmácias, Relatórios.
"""

import io
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from farmacia_monitor.database.db import get_db, Farmacia, Coleta

app = FastAPI(title="PharmaFlow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Painel Geral ─────────────────────────────────────────────────────────────

@app.get("/api/painel")
def get_painel(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT * FROM vw_ranking_atual")).mappings().all()

    if not rows:
        return {
            "receita_total": 0,
            "total_atendimentos": 0,
            "vendas_realizadas": 0,
            "farmacias_ativas": 0,
            "farmacias_alerta": 0,
            "farmacias_atencao": 0,
            "taxa_conversao_media": 0,
            "ultima_atualizacao": None,
        }

    receita_total       = sum(float(r["receita_total"] or 0) for r in rows)
    total_atendimentos  = sum(int(r["total_atendimentos"] or 0) for r in rows)
    vendas_realizadas   = sum(int(r["vendas_realizadas"] or 0) for r in rows)
    conversoes          = [float(r["taxa_conversao"] or 0) for r in rows]
    taxa_media          = round(sum(conversoes) / len(conversoes), 2) if conversoes else 0
    ultima_atualizacao  = max((r["data_coleta"] for r in rows), default=None)

    return {
        "receita_total":        round(receita_total, 2),
        "total_atendimentos":   total_atendimentos,
        "vendas_realizadas":    vendas_realizadas,
        "farmacias_ativas":     len(rows),
        "farmacias_alerta":     sum(1 for r in rows if r["nivel_alerta"] == "vermelho"),
        "farmacias_atencao":    sum(1 for r in rows if r["nivel_alerta"] == "amarelo"),
        "taxa_conversao_media": taxa_media,
        "ultima_atualizacao":   ultima_atualizacao,
    }


# ── Farmácias ─────────────────────────────────────────────────────────────────

@app.get("/api/farmacias")
def get_farmacias(
    status: Optional[str] = None,
    busca:  Optional[str] = None,
    db: Session = Depends(get_db),
):
    rows = db.execute(text("SELECT * FROM vw_ranking_atual ORDER BY posicao_ranking")).mappings().all()

    resultado = []
    for r in rows:
        # Mapeia nivel_alerta → label de status do frontend
        label_status = {"verde": "Ativa", "amarelo": "Atenção", "vermelho": "Alerta"}.get(
            r["nivel_alerta"], "Ativa"
        )

        if status and label_status.lower() != status.lower():
            continue
        if busca and busca.lower() not in r["farmacia"].lower():
            continue

        resultado.append({
            "id":                      r["farmacia_id"],
            "nome":                    r["farmacia"],
            "status":                  label_status,
            "nivel_alerta":            r["nivel_alerta"],
            "receita_total":           float(r["receita_total"] or 0),
            "total_atendimentos":      int(r["total_atendimentos"] or 0),
            "atendimentos_finalizados":int(r["atendimentos_finalizados"] or 0),
            "vendas_realizadas":       int(r["vendas_realizadas"] or 0),
            "taxa_conversao":          float(r["taxa_conversao"] or 0),
            "variacao_receita":        float(r["variacao_receita"] or 0),
            "variacao_atendimentos":   float(r["variacao_atendimentos"] or 0),
            "variacao_vendas":         float(r["variacao_vendas"] or 0),
            "score_criticidade":       float(r["score_criticidade"] or 0),
            "posicao_ranking":         int(r["posicao_ranking"]),
            "periodo_inicio":          str(r["periodo_inicio"]),
            "periodo_fim":             str(r["periodo_fim"]),
            "data_coleta":             r["data_coleta"],
        })

    return resultado


@app.get("/api/farmacias/{farmacia_id}/evolucao")
def get_evolucao(farmacia_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT * FROM vw_evolucao_semanal
            WHERE farmacia_id = :fid
            ORDER BY semana_numero ASC
        """),
        {"fid": farmacia_id},
    ).mappings().all()

    return [dict(r) for r in rows]


# ── Relatórios / Histórico de Execuções ───────────────────────────────────────

@app.get("/api/relatorios")
def get_relatorios(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT
            DATE_TRUNC('week', data_coleta)::DATE  AS periodo_inicio,
            MAX(periodo_fim)                        AS periodo_fim,
            MAX(data_coleta)                        AS data_geracao,
            COUNT(DISTINCT farmacia_id)             AS farmacias,
            SUM(CASE WHEN nivel_alerta != 'sem_dados' THEN 1 ELSE 0 END) AS concluidas
        FROM coletas
        GROUP BY DATE_TRUNC('week', data_coleta)::DATE
        ORDER BY periodo_inicio DESC
        LIMIT 20
    """)).mappings().all()

    resultado = []
    for i, r in enumerate(rows):
        total     = int(r["farmacias"] or 0)
        concluidas = int(r["concluidas"] or total)
        status    = "Concluído" if concluidas == total else "Parcial" if concluidas > 0 else "Erro"

        inicio = r["periodo_inicio"]
        fim    = r["periodo_fim"]
        label  = f"Semana {len(rows) - i} — {_fmt_data(inicio)} a {_fmt_data(fim)}"

        resultado.append({
            "id":            i + 1,
            "label":         label,
            "periodo_inicio": str(inicio),
            "periodo_fim":    str(fim),
            "data_geracao":   r["data_geracao"],
            "farmacias":      f"{total}/70",
            "status":         status,
        })

    return resultado


@app.get("/api/relatorios/{periodo_inicio}/xlsx")
def download_xlsx(periodo_inicio: str, db: Session = Depends(get_db)):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    rows = db.execute(text("""
        SELECT
            f.nome,
            c.periodo_inicio, c.periodo_fim,
            c.receita_total, c.total_atendimentos,
            c.atendimentos_finalizados, c.vendas_realizadas,
            c.taxa_conversao, c.variacao_receita,
            c.variacao_atendimentos, c.variacao_vendas,
            c.score_criticidade, c.nivel_alerta
        FROM coletas c
        JOIN farmacias f ON f.id = c.farmacia_id
        WHERE c.periodo_inicio::TEXT = :periodo
        ORDER BY c.score_criticidade DESC
    """), {"periodo": periodo_inicio}).mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail="Período não encontrado")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Relatório Semanal"

    cabecalho = [
        "Farmácia", "Período Início", "Período Fim",
        "Receita Total (R$)", "Total Atendimentos", "Atend. Finalizados",
        "Vendas Realizadas", "Taxa Conversão (%)", "Variação Receita (%)",
        "Variação Atendimentos (%)", "Variação Vendas (%)",
        "Score Criticidade", "Nível Alerta",
    ]

    header_fill = PatternFill("solid", fgColor="1A7A4A")
    header_font = Font(bold=True, color="FFFFFF")

    for col, titulo in enumerate(cabecalho, 1):
        cell = ws.cell(row=1, column=col, value=titulo)
        cell.fill   = header_fill
        cell.font   = header_font
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = max(len(titulo) + 4, 18)

    cores_alerta = {"verde": "C6EFCE", "amarelo": "FFEB9C", "vermelho": "FFC7CE"}

    for linha, r in enumerate(rows, 2):
        valores = [
            r["nome"], str(r["periodo_inicio"]), str(r["periodo_fim"]),
            float(r["receita_total"] or 0),
            int(r["total_atendimentos"] or 0),
            int(r["atendimentos_finalizados"] or 0),
            int(r["vendas_realizadas"] or 0),
            float(r["taxa_conversao"] or 0),
            float(r["variacao_receita"] or 0),
            float(r["variacao_atendimentos"] or 0),
            float(r["variacao_vendas"] or 0),
            float(r["score_criticidade"] or 0),
            r["nivel_alerta"],
        ]
        cor = cores_alerta.get(r["nivel_alerta"], "FFFFFF")
        fill = PatternFill("solid", fgColor=cor)
        for col, val in enumerate(valores, 1):
            cell = ws.cell(row=linha, column=col, value=val)
            cell.fill = fill

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    nome_arquivo = f"relatorio_{periodo_inicio}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"},
    )


# ── Execução manual ("Rodar Agora") ───────────────────────────────────────────

_pipeline_rodando = False

@app.post("/api/rodar-agora")
async def rodar_agora(background_tasks: BackgroundTasks):
    global _pipeline_rodando
    if _pipeline_rodando:
        return {"status": "ja_rodando", "mensagem": "Pipeline já está em execução"}

    async def _executar():
        global _pipeline_rodando
        _pipeline_rodando = True
        try:
            from main import pipeline
            await pipeline()
        finally:
            _pipeline_rodando = False

    background_tasks.add_task(_executar)
    return {"status": "iniciado", "mensagem": "Pipeline iniciado em background"}


@app.get("/api/status")
def get_status():
    return {
        "pipeline_rodando": _pipeline_rodando,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_data(d) -> str:
    if not d:
        return ""
    if hasattr(d, "strftime"):
        return d.strftime("%d %b")
    return str(d)
