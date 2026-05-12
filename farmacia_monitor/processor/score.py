from dataclasses import dataclass
from typing import Optional


@dataclass
class MetricasSemana:
    clientes_google: int
    clientes_facebook: int
    clientes_grupos_oferta: int
    vendas_realizadas: int
    receita_total: float


def _variacao(atual: float, anterior: float) -> float:
    if anterior == 0:
        return 0.0
    return ((atual - anterior) / anterior) * 100


def calcular_score(atual: MetricasSemana, anterior: Optional[MetricasSemana]) -> dict:
    """
    Score 0–100: quanto maior, mais crítica a farmácia.

    Pesos:
      - Queda de clientes Google    : 25 pts
      - Queda de clientes Facebook  : 20 pts
      - Queda de clientes Grupos    : 15 pts
      - Queda de vendas realizadas  : 25 pts
      - Queda de receita            : 15 pts
    """
    score = 0.0
    alertas = []

    var_google   = var_facebook = var_grupos = 0.0
    var_vendas   = var_receita  = 0.0

    if anterior:
        var_google   = _variacao(atual.clientes_google,        anterior.clientes_google)
        var_facebook = _variacao(atual.clientes_facebook,      anterior.clientes_facebook)
        var_grupos   = _variacao(atual.clientes_grupos_oferta, anterior.clientes_grupos_oferta)
        var_vendas   = _variacao(atual.vendas_realizadas,      anterior.vendas_realizadas)
        var_receita  = _variacao(atual.receita_total,          anterior.receita_total)

        if var_google < -25:
            score += 25
            alertas.append(f"Google caiu {abs(var_google):.1f}%")
        elif var_google < -10:
            score += 12

        if var_facebook < -25:
            score += 20
            alertas.append(f"Facebook caiu {abs(var_facebook):.1f}%")
        elif var_facebook < -10:
            score += 10

        if var_grupos < -25:
            score += 15
            alertas.append(f"Grupos caiu {abs(var_grupos):.1f}%")
        elif var_grupos < -10:
            score += 7

        if var_vendas < -20:
            score += 25
            alertas.append(f"Vendas cairam {abs(var_vendas):.1f}%")
        elif var_vendas < -10:
            score += 12

        if var_receita < -20:
            score += 15
            alertas.append(f"Receita caiu {abs(var_receita):.1f}%")
        elif var_receita < -10:
            score += 7

    nivel = "verde"
    if score >= 50:
        nivel = "vermelho"
    elif score >= 20:
        nivel = "amarelo"

    return {
        "score_criticidade": round(score, 2),
        "nivel_alerta":      nivel,
        "variacao_google":   round(var_google, 2),
        "variacao_facebook": round(var_facebook, 2),
        "variacao_grupos":   round(var_grupos, 2),
        "variacao_vendas":   round(var_vendas, 2),
        "variacao_receita":  round(var_receita, 2),
        "alertas":           alertas,
    }
