from dataclasses import dataclass
from typing import Optional


@dataclass
class MetricasSemana:
    total_atendimentos: int
    atendimentos_finalizados: int
    vendas_realizadas: int
    receita_total: float


def _variacao(atual: float, anterior: float) -> float:
    if anterior == 0:
        return 0.0
    return ((atual - anterior) / anterior) * 100


def _taxa_finalizacao(finalizados: int, total: int) -> float:
    if total == 0:
        return 0.0
    return (finalizados / total) * 100


def calcular_score(atual: MetricasSemana, anterior: Optional[MetricasSemana]) -> dict:
    """
    Score 0–100: quanto maior, mais crítica a farmácia.

    Pesos:
      - Queda de atendimentos  : 40 pts
      - Queda de vendas        : 30 pts
      - Queda de receita       : 20 pts
      - Taxa de finalização    : 10 pts
    """
    score = 0.0
    alertas = []

    taxa_finalizacao = _taxa_finalizacao(
        atual.atendimentos_finalizados, atual.total_atendimentos
    )

    var_atendimentos = var_vendas = var_receita = 0.0

    if anterior:
        var_atendimentos = _variacao(atual.total_atendimentos, anterior.total_atendimentos)
        var_vendas       = _variacao(atual.vendas_realizadas,  anterior.vendas_realizadas)
        var_receita      = _variacao(atual.receita_total,      anterior.receita_total)

        # Queda de atendimentos (peso 40)
        if var_atendimentos < -20:
            score += 40
            alertas.append(f"Atendimentos caíram {abs(var_atendimentos):.1f}%")
        elif var_atendimentos < -10:
            score += 20

        # Queda de vendas (peso 30)
        if var_vendas < -20:
            score += 30
            alertas.append(f"Vendas caíram {abs(var_vendas):.1f}%")
        elif var_vendas < -10:
            score += 15

        # Queda de receita (peso 20)
        if var_receita < -25:
            score += 20
            alertas.append(f"Receita caiu {abs(var_receita):.1f}%")
        elif var_receita < -15:
            score += 10

    # Taxa de finalização baixa — independe do histórico (peso 10)
    if taxa_finalizacao < 80:
        score += 10
        alertas.append(f"Finalizacao baixa: {taxa_finalizacao:.1f}%")

    nivel = "verde"
    if score >= 50:
        nivel = "vermelho"
    elif score >= 20:
        nivel = "amarelo"

    return {
        "score_criticidade":    round(score, 2),
        "nivel_alerta":         nivel,
        "taxa_conversao":       round(taxa_finalizacao, 2),
        "variacao_receita":     round(var_receita, 2),
        "variacao_atendimentos":round(var_atendimentos, 2),
        "variacao_vendas":      round(var_vendas, 2),
        "alertas":              alertas,
    }
