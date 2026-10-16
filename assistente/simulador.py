"""Cálculos do simulador financeiro (especificação do Conteúdo IV, Parte II).

As contas ficam em funções; a interface só mostra e explica o resultado.

- Cálculos determinísticos: número de apostas, total em risco, probabilidade
  implícita, valor esperado e investimento com aportes periódicos.
- Faixa de resultados: método de Monte Carlo com 10.000 trajetórias de vitórias
  e derrotas, com semente fixa para que o mesmo cenário dê sempre o mesmo número.
- Tabela de sensibilidade: conta exata pela distribuição binomial, que também
  serve para conferir o Monte Carlo nos testes.
- Margem da casa: só quando há odds de todos os resultados do mercado.
"""

import math
from dataclasses import dataclass

import numpy as np

APOSTAS_POR_ANO = {"dia": 365, "semana": 52, "mes": 12}
NOME_PERIODO = {"dia": "dia", "semana": "semana", "mes": "mês"}
TRAJETORIAS = 10_000
SEMENTE = 2026
PONTOS_GRAFICO = 60
MAX_ANOS = 50
MAX_APOSTAS = 1_000_000


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
    if c.anos > MAX_ANOS:
        erros.append(f"O período máximo é de {MAX_ANOS} anos.")
    if c.odd is not None and c.odd <= 1:
        erros.append("A odd decimal precisa ser maior que 1.")
    if c.probabilidade is not None and not 0 < c.probabilidade < 1:
        erros.append("A probabilidade precisa estar entre 0% e 100%.")
    if c.taxa_anual is not None and c.taxa_anual <= -1:
        erros.append("A taxa anual precisa ser maior que -100%.")
    if not erros and numero_de_apostas(c) > MAX_APOSTAS:
        erros.append("O cenário passa de 1 milhão de apostas. Reduza a frequência ou o período.")
    if not erros and numero_de_apostas(c) < 1:
        erros.append("Com esses dados não há nenhuma aposta no período.")
    return erros


def periodos(c: Cenario) -> int:
    return max(1, round(APOSTAS_POR_ANO[c.periodicidade] * c.anos))


def numero_de_apostas(c: Cenario) -> int:
    return round(c.apostas_por_periodo * APOSTAS_POR_ANO[c.periodicidade] * c.anos)


def total_em_risco(c: Cenario) -> float:
    return c.valor_por_aposta * numero_de_apostas(c)


def probabilidade_implicita(odd: float) -> float:
    return 1 / odd


def valor_esperado_por_aposta(valor: float, odd: float, probabilidade: float) -> float:
    return valor * (probabilidade * odd - 1)


def taxa_por_periodo(taxa_anual: float, periodicidade: str) -> float:
    return (1 + taxa_anual) ** (1 / APOSTAS_POR_ANO[periodicidade]) - 1


def valor_investido(aporte: float, i: float, n: int) -> float:
    """Valor final de n aportes iguais no fim de cada período (anuidade postecipada)."""
    if i == 0:
        return aporte * n
    return aporte * ((1 + i) ** n - 1) / i


def valor_final_investimento(c: Cenario) -> float:
    """Aportes iguais ao valor apostado em cada período, com juros compostos.

    A taxa anual vira taxa por período: (1 + taxa) ^ (1 / períodos por ano) - 1.
    """
    aporte = c.valor_por_aposta * c.apostas_por_periodo
    return valor_investido(aporte, taxa_por_periodo(c.taxa_anual, c.periodicidade), periodos(c))


def aposta_unica(valor: float, odd: float, probabilidade: float | None = None) -> dict:
    """Contas de uma aposta isolada: retorno, lucro e, com hipótese de chance, valor esperado."""
    saida = {"retorno": valor * odd, "lucro": valor * (odd - 1), "perda": valor,
             "probabilidade_implicita": probabilidade_implicita(odd)}
    if probabilidade is not None:
        saida["ve"] = valor_esperado_por_aposta(valor, odd, probabilidade)
    return saida


def margem_da_casa(odds: list[float]) -> dict:
    """Margem a partir das odds de TODOS os resultados de um mercado (Conteúdo IV, hipótese 5)."""
    if len(odds) < 2:
        return {"erros": ["Informe as odds de todos os resultados possíveis (pelo menos duas)."]}
    if any(o <= 1 for o in odds):
        return {"erros": ["Toda odd decimal precisa ser maior que 1."]}
    implicitas = [1 / o for o in odds]
    soma = sum(implicitas)
    return {"erros": [], "soma": soma, "margem": soma - 1, "implicitas": implicitas,
            "sem_margem": [p / soma for p in implicitas]}


# ---------- Distribuição exata (binomial) ----------

def _pmf_binomial(n: int, p: float) -> np.ndarray:
    k = np.arange(n + 1)
    log = (math.lgamma(n + 1) - np.array([math.lgamma(x + 1) + math.lgamma(n - x + 1) for x in k])
           + k * math.log(p) + (n - k) * math.log1p(-p))
    return np.exp(log)


def prob_prejuizo_exata(n: int, odd: float, p: float) -> float:
    """P(resultado < 0). Com W vitórias: resultado = valor × (W × odd − n) < 0  ⇔  W < n / odd."""
    pmf = _pmf_binomial(n, p)
    limite = n / odd
    k = np.arange(n + 1)
    return float(pmf[k < limite - 1e-9].sum())


def quantil_exato(c: Cenario, q: float) -> float:
    n = numero_de_apostas(c)
    cdf = np.cumsum(_pmf_binomial(n, c.probabilidade))
    w = int(np.searchsorted(cdf, q - 1e-12))
    return c.valor_por_aposta * (w * c.odd - n)


def sensibilidade(c: Cenario, passos=(-0.10, -0.05, 0.0, 0.05, 0.10)) -> list[dict]:
    """Como o resultado muda quando a hipótese de chance muda (Conteúdo IV, item 10)."""
    n = numero_de_apostas(c)
    empate = 1 / c.odd  # chance em que o valor esperado é zero
    chances = {round(c.probabilidade + d, 4) for d in passos}
    chances = {p for p in chances if abs(p - empate) > 0.005} | {empate}
    linhas = []
    for p in sorted(x for x in chances if 0 < x < 1):
        linhas.append({
            "probabilidade": p,
            "ve_total": 0.0 if p == empate else valor_esperado_por_aposta(c.valor_por_aposta, c.odd, p) * n,
            "prob_prejuizo": prob_prejuizo_exata(n, c.odd, p) if n <= 200_000 else None,
            "informada": abs(p - c.probabilidade) < 1e-9,
            "empate": p == empate,
        })
    return linhas


# ---------- Monte Carlo ----------

def simular_trajetorias(c: Cenario, n_trajetorias: int = TRAJETORIAS, semente: int = SEMENTE) -> dict:
    """Sorteia sequências de vitórias e derrotas e resume a faixa de resultados.

    Para não guardar cada aposta, o período é dividido em até 60 marcos. Entre dois
    marcos, o número de vitórias segue uma binomial com as apostas daquele trecho,
    o que dá a mesma distribuição de sortear aposta por aposta.
    """
    n = numero_de_apostas(c)
    per = periodos(c)
    marcos = np.unique(np.linspace(0, per, min(per, PONTOS_GRAFICO) + 1).round().astype(int))
    apostas = np.minimum(np.round(marcos * c.apostas_por_periodo).astype(int), n)
    apostas[-1] = n
    rng = np.random.default_rng(semente)
    vitorias = rng.binomial(np.diff(apostas), c.probabilidade, size=(n_trajetorias, len(marcos) - 1))
    acumuladas = np.concatenate([np.zeros((n_trajetorias, 1), dtype=int), vitorias.cumsum(axis=1)], axis=1)
    resultado = c.valor_por_aposta * (acumuladas * c.odd - apostas)  # lucro ou prejuízo acumulado
    final = resultado[:, -1]
    q = lambda arr, x: np.percentile(arr, x, axis=0)
    return {
        "n_trajetorias": n_trajetorias,
        "anos": (marcos / APOSTAS_POR_ANO[c.periodicidade]).tolist(),
        "periodos": marcos.tolist(),
        "apostas": apostas.tolist(),
        "p5": q(resultado, 5).tolist(),
        "p25": q(resultado, 25).tolist(),
        "mediana": q(resultado, 50).tolist(),
        "p75": q(resultado, 75).tolist(),
        "p95": q(resultado, 95).tolist(),
        "media": resultado.mean(axis=0).tolist(),
        "final": {
            "p5": float(q(final, 5)), "p25": float(q(final, 25)), "mediana": float(q(final, 50)),
            "p75": float(q(final, 75)), "p95": float(q(final, 95)), "media": float(final.mean()),
            "pior": float(final.min()), "melhor": float(final.max()),
            "prob_prejuizo": float((final < 0).mean()), "prob_lucro": float((final > 0).mean()),
        },
    }


def serie_investimento(c: Cenario, marcos_periodo: list[int]) -> dict:
    aporte = c.valor_por_aposta * c.apostas_por_periodo
    i = taxa_por_periodo(c.taxa_anual, c.periodicidade) if c.taxa_anual is not None else 0.0
    return {"guardado": [valor_investido(aporte, i, t) for t in marcos_periodo],
            "separado": [aporte * t for t in marcos_periodo]}


def tabela_anual(c: Cenario, s: dict) -> list[dict]:
    """Uma linha por ano (ou só a final, se o período for menor que um ano)."""
    linhas = []
    anos_int = list(range(1, int(c.anos) + 1))
    if not anos_int or anos_int[-1] < c.anos:
        anos_int.append(c.anos)
    por_ano = APOSTAS_POR_ANO[c.periodicidade]
    aporte = c.valor_por_aposta * c.apostas_por_periodo
    for a in anos_int:
        n_a = round(c.apostas_por_periodo * por_ano * a)
        linha = {"ano": a, "apostas": n_a, "em_risco": n_a * c.valor_por_aposta}
        if "ve_por_aposta" in s:
            linha["ve"] = s["ve_por_aposta"] * n_a
        if c.taxa_anual is not None:
            linha["guardado"] = valor_investido(aporte, taxa_por_periodo(c.taxa_anual, c.periodicidade),
                                                round(por_ano * a))
        linhas.append(linha)
    return linhas


def simular(c: Cenario, trajetorias: bool = True) -> dict:
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
        saida["sensibilidade"] = sensibilidade(c)
        if trajetorias:
            saida["trajetorias"] = simular_trajetorias(c)
    if c.taxa_anual is not None:
        saida["valor_final_investimento"] = valor_final_investimento(c)
        if "ve_total" in saida:
            # Quem apostou termina, em média, com o dinheiro separado mais o resultado das apostas.
            saida["sobra_media_apostando"] = saida["total_em_risco"] + saida["ve_total"]
            saida["custo_oportunidade"] = saida["valor_final_investimento"] - saida["sobra_media_apostando"]
        else:
            saida["rendimento"] = saida["valor_final_investimento"] - saida["total_em_risco"]
    marcos = saida.get("trajetorias", {}).get("periodos") or np.unique(
        np.linspace(0, periodos(c), min(periodos(c), PONTOS_GRAFICO) + 1).round().astype(int)).tolist()
    saida["marcos_anos"] = [m / APOSTAS_POR_ANO[c.periodicidade] for m in marcos]
    saida["investimento"] = serie_investimento(c, marcos)
    saida["tabela_anual"] = tabela_anual(c, saida)
    return saida
