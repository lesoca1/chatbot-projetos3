"""Frases que explicam o resultado do simulador em linguagem simples.

Os textos são modelos fixos preenchidos com os números calculados. Nada é
gerado por modelo de linguagem.
"""

from .formato import anos_texto, numero, pct, reais
from .simulador import NOME_PERIODO, Cenario, aposta_unica


def descrever_cenario(c: Cenario) -> str:
    vezes = numero(c.apostas_por_periodo, 0 if float(c.apostas_por_periodo).is_integer() else 1)
    freq = f"{vezes} {'aposta' if c.apostas_por_periodo == 1 else 'apostas'} por {NOME_PERIODO[c.periodicidade]}"
    partes = [f"{reais(c.valor_por_aposta)} por aposta", freq, f"durante {anos_texto(c.anos)}"]
    if c.odd is not None:
        partes.append(f"odd {numero(c.odd, 2)}")
    if c.probabilidade is not None:
        partes.append(f"chance de acerto suposta de {pct(c.probabilidade, 0)}")
    if c.taxa_anual is not None:
        partes.append(f"taxa hipotética de {pct(c.taxa_anual)} ao ano")
    return ", ".join(partes) + "."


def explicar(c: Cenario, s: dict) -> list[str]:
    """Leitura principal do cenário, em ordem: volume, média, faixa, comparação, o que falta."""
    if s["erros"]:
        return s["erros"]
    frases = [f"São {numero(s['numero_de_apostas'])} apostas e {reais(s['total_em_risco'])} colocados em risco."]
    if "ve_total" in s:
        ve = s["ve_total"]
        if ve < 0:
            frases.append(f"Com essas hipóteses, o resultado médio esperado é uma perda de {reais(-ve)} "
                          f"({reais(-s['ve_por_aposta'])} por aposta), porque a odd {numero(c.odd, 2)} "
                          f"paga como se a chance fosse {pct(s['probabilidade_implicita'])}, e você supôs "
                          f"{pct(c.probabilidade)}.")
        elif ve > 0:
            frases.append(f"Com a chance que você supôs, a conta dá um ganho médio de {reais(ve)}. Isso é só "
                          "um cenário: se a sua hipótese estiver errada por poucos pontos, o resultado muda de "
                          "sinal. Veja a tabela de sensibilidade.")
        else:
            frases.append("Com essas hipóteses, o resultado médio esperado é zero.")
        f = s["trajetorias"]["final"] if "trajetorias" in s else None
        if f:
            frases.append(f"Em 90% das {numero(s['trajetorias']['n_trajetorias'])} simulações, o resultado final "
                          f"ficou entre {reais(f['p5'])} e {reais(f['p95'])}. "
                          f"{pct(f['prob_prejuizo'])} delas terminaram no prejuízo.")
    else:
        frases.append("Para calcular o resultado médio e a faixa de resultados, informe a odd média e a sua "
                      "hipótese de chance de acerto (por exemplo: odd 1,80 e 50% de chance).")
    if "valor_final_investimento" in s:
        fv = s["valor_final_investimento"]
        if "custo_oportunidade" in s:
            frases.append(f"Se o mesmo dinheiro fosse guardado, viraria {reais(fv)}. Apostando, sobram em média "
                          f"{reais(s['sobra_media_apostando'])}: a diferença, de {reais(s['custo_oportunidade'])}, "
                          "é o custo de oportunidade esperado.")
        else:
            frases.append(f"Se o mesmo dinheiro fosse guardado, viraria {reais(fv)}, "
                          f"{reais(s['rendimento'])} a mais do que foi separado.")
    else:
        frases.append("Para comparar com guardar o dinheiro, informe uma taxa anual (por exemplo: 8% ao ano).")
    return frases


def explicar_aposta_unica(valor: float, odd: float, probabilidade: float | None) -> list[str]:
    a = aposta_unica(valor, odd, probabilidade)
    frases = [f"Apostando {reais(valor)} com odd {numero(odd, 2)}, se acertar você recebe {reais(a['retorno'])}: "
              f"{reais(a['lucro'])} de lucro mais os {reais(valor)} apostados. Se errar, perde {reais(valor)}.",
              f"A odd {numero(odd, 2)} corresponde a uma probabilidade implícita de "
              f"{pct(a['probabilidade_implicita'])}."]
    if "ve" in a:
        frases.append(f"Com a sua hipótese de {pct(probabilidade, 0)} de acerto, o valor esperado da aposta é "
                      f"{reais(a['ve'])}.")
    return frases
