"""Cálculos do simulador financeiro (especificação do Conteúdo IV, Parte II).

As contas ficam em funções; a interface só mostra e explica o resultado.
Primeira versão: cálculos determinísticos. A faixa de resultados por simulação
de trajetórias e o gráfico entram na Implementação II.
"""

from dataclasses import dataclass

APOSTAS_POR_ANO = {"dia": 365, "semana": 52, "mes": 12}
MESES_POR_ANO = 12


@dataclass
class Cenario:
    valor_por_aposta: float
    apostas_por_periodo: float
    periodicidade: str  # "dia", "semana" ou "mes"
    anos: float
    odd: float | None = None
    probabilidade: float | None = None  # hipótese do usuário, entre 0 e 1
    taxa_anual: float | None = None  # ex.: 0.08 para 8% ao ano


def validar(c: Cenario) -> list[str]:
    erros = []
    if c.valor_por_aposta <= 0:
        erros.append("O valor por aposta precisa ser maior que zero.")
    if c.apostas_por_periodo <= 0:
        erros.append("A frequência precisa ser maior que zero.")
    if c.periodicidade not in APOSTAS_POR_ANO:
        erros.append("A periodicidade precisa ser dia, semana ou mês.")
    if c.anos <= 0:
        erros.append("O período precisa ser maior que zero.")
    if c.odd is not None and c.odd <= 1:
        erros.append("A odd decimal precisa ser maior que 1.")
    if c.probabilidade is not None and not 0 < c.probabilidade < 1:
        erros.append("A probabilidade precisa estar entre 0% e 100%.")
    if c.taxa_anual is not None and c.taxa_anual <= -1:
        erros.append("A taxa anual precisa ser maior que -100%.")
    return erros


def numero_de_apostas(c: Cenario) -> int:
    return round(c.apostas_por_periodo * APOSTAS_POR_ANO[c.periodicidade] * c.anos)


def total_em_risco(c: Cenario) -> float:
    return c.valor_por_aposta * numero_de_apostas(c)


def probabilidade_implicita(odd: float) -> float:
    return 1 / odd


def valor_esperado_por_aposta(valor: float, odd: float, probabilidade: float) -> float:
    return valor * (probabilidade * odd - 1)


def valor_final_investimento(c: Cenario) -> float:
    """Aportes iguais ao valor apostado em cada período, com juros compostos.

    A taxa anual vira taxa por período: (1 + taxa) ^ (1 / períodos por ano) - 1.
    Aportes no fim de cada período (anuidade postecipada).
    """
    periodos_ano = APOSTAS_POR_ANO[c.periodicidade]
    n = round(periodos_ano * c.anos)
    aporte = c.valor_por_aposta * c.apostas_por_periodo
    i = (1 + c.taxa_anual) ** (1 / periodos_ano) - 1
    if i == 0:
        return aporte * n
    return aporte * ((1 + i) ** n - 1) / i


def simular(c: Cenario) -> dict:
    erros = validar(c)
    if erros:
        return {"erros": erros}
    n = numero_de_apostas(c)
    saida = {"erros": [], "numero_de_apostas": n, "total_em_risco": total_em_risco(c)}
    if c.odd is not None:
        saida["probabilidade_implicita"] = probabilidade_implicita(c.odd)
    if c.odd is not None and c.probabilidade is not None:
        ve = valor_esperado_por_aposta(c.valor_por_aposta, c.odd, c.probabilidade)
        saida["ve_por_aposta"] = ve
        saida["ve_total"] = ve * n
    if c.taxa_anual is not None:
        saida["valor_final_investimento"] = valor_final_investimento(c)
    return saida
