"""Frases que explicam o resultado do simulador em linguagem simples.

Os textos são modelos fixos preenchidos com os números calculados. Nada é
gerado por modelo de linguagem.

Regras de escrita (Implementação III, a partir do retorno da professora):
- uma ideia por frase, com palavras do dia a dia;
- valores em reais redondos, sem centavos;
- chances ditas como "X de cada 100", que é mais fácil de imaginar que uma porcentagem;
- termos técnicos (valor esperado, Monte Carlo, percentil) ficam só na parte "Como as contas são feitas".
"""

import math

from .formato import anos_texto, numero, reais
from .simulador import NOME_PERIODO, Cenario, aposta_unica


def dinheiro(v: float) -> str:
    """Reais sem centavos. Abaixo de R$ 1, diz "menos de R$ 1" (Testes e Validação II)."""
    if 0 < abs(v) < 0.995:
        return "menos de R$ 1"
    return reais(v, 0)


def exato(v: float) -> str:
    """Valor de uma aposta só: centavos apenas quando existem (R$ 18,50, mas R$ 50)."""
    return reais(v, 0 if abs(v - round(v)) < 0.005 else 2)


def em_100(p: float, exato: bool = False) -> str:
    """0,969 -> "97 de cada 100". Com exato=True, mantém uma casa decimal (55,6 de cada 100).

    Nos extremos, evita prometer "100 de cada 100" ou "0 de cada 100".
    """
    x = p * 100
    if x > 99.5:
        return "mais de 99 de cada 100"
    if 0 < x < 0.5:
        return "menos de 1 de cada 100"
    return f"{numero(x, 1 if exato and abs(x - round(x)) >= 0.05 else 0)} de cada 100"


def acertos_para_empatar(odd: float) -> str:
    """Quantos acertos em 100 apostas são preciso para não perder na média (1 / odd)."""
    x = 100 / odd
    if abs(x - round(x)) < 1e-9:
        return f"mais de {round(x)} de cada 100"
    return f"pelo menos {math.ceil(x)} de cada 100"


def maximo_que_perde(odd: float) -> int:
    """Maior número de acertos em 100 que ainda dá perda na média. Odd 1,90: 52; odd 2,00: 49."""
    x = 100 / odd
    return round(x) - 1 if abs(x - round(x)) < 1e-9 else math.floor(x)


def aviso_equilibrio(odd: float) -> str:
    """Frase para quando a chance suposta passa do ponto de equilíbrio (corrige a frase quebrada da Testes I)."""
    n = maximo_que_perde(odd)
    return (f"Com odd {numero(odd, 2)}, quem acerta {n} de cada 100 ou menos já perde. "
            "Quase todo apostador acha que acerta mais do que acerta de verdade.")


def sujeito(c: Cenario) -> dict:
    """Palavras que mudam quando o cenário é de outra pessoa ("meu filho aposta...")."""
    if c.terceiro:
        return {"perderia": "quem aposta assim perderia", "pelas": "pelas", "disse": "A chance suposta é de",
                "acerta": "acerta", "voce_acertar": "ele ou ela acertar"}
    return {"perderia": "você perderia", "pelas": "pelas suas", "disse": "Você disse que acerta",
            "acerta": "você acerta", "voce_acertar": "você acertar"}


def resultado(v: float) -> str:
    if v < -0.5:
        return f"perder {dinheiro(-v)}"
    if v > 0.5:
        return f"ganhar {dinheiro(v)}"
    return "não ganhar nem perder"


def descrever_cenario(c: Cenario) -> str:
    vezes = numero(c.apostas_por_periodo, 0 if float(c.apostas_por_periodo).is_integer() else 1)
    freq = f"{vezes} {'vez' if c.apostas_por_periodo == 1 else 'vezes'} por {NOME_PERIODO[c.periodicidade]}"
    partes = [f"{dinheiro(c.valor_por_aposta)} por aposta", freq, f"durante {anos_texto(c.anos)}"]
    if c.odd is not None:
        partes.append(f"odd {numero(c.odd, 2)}")
    if c.probabilidade is not None:
        partes.append(f"{sujeito(c)['acerta']} {em_100(c.probabilidade, exato=True)}")
    if c.taxa_anual is not None:
        partes.append(f"rendimento de {numero(c.taxa_anual * 100, 1).replace(',0', '')}% ao ano")
    return ", ".join(partes) + "."


def resumir(c: Cenario, s: dict) -> str:
    """O resultado principal em uma frase, mostrado antes das explicações."""
    if s["erros"]:
        return "Não consegui fazer as contas com esses números."
    v = sujeito(c)
    ve = s.get("ve_total")
    if ve is not None and ve < -0.005:
        return (f"Em {anos_texto(c.anos)}, {v['perderia']} em média {dinheiro(-ve)} dos "
                f"{dinheiro(s['total_em_risco'])} apostados.")
    return f"Em {anos_texto(c.anos)}, {dinheiro(s['total_em_risco'])} passariam {v['pelas']} apostas."


def explicar(c: Cenario, s: dict) -> list[str]:
    """Leitura do cenário em ordem: quanto passa pelas apostas, perda média, por quê, sorte, guardar."""
    if s["erros"]:
        return s["erros"]
    v = sujeito(c)
    vezes = "aposta" if s["numero_de_apostas"] == 1 else "apostas"
    frases = [f"Em {anos_texto(c.anos)}, são {numero(s['numero_de_apostas'])} {vezes} de "
              f"{dinheiro(c.valor_por_aposta)}. Ao todo, {dinheiro(s['total_em_risco'])} passam pelas apostas."]
    if "ve_total" in s:
        ve = s["ve_total"]
        if ve < -0.005:
            por_100 = -ve / s["total_em_risco"] * 100
            frases.append(f"Na média, {v['perderia']} {dinheiro(-ve)}. É como perder {dinheiro(por_100)} "
                          "de cada R$ 100 apostados.")
            frases.append(f"Por quê? Com odd {numero(c.odd, 2)}, só deixa de perder quem acerta "
                          f"{acertos_para_empatar(c.odd)} apostas. {v['disse']} {em_100(c.probabilidade, exato=True)}.")
        elif ve > 0.005:
            frases.append(f"Com a chance suposta, a conta daria um ganho médio de {dinheiro(ve)}. "
                          f"Cuidado: isso só vale se {v['voce_acertar']} mesmo {em_100(c.probabilidade, exato=True)}. "
                          + aviso_equilibrio(c.odd))
        else:
            frases.append("Com esses números, na média não se ganha nem se perde.")
        f = s["trajetorias"]["final"] if "trajetorias" in s else None
        if f:
            p = f["prob_prejuizo"]
            quantas = "praticamente todas" if p > 0.995 else (
                "quase nenhuma" if p < 0.005 else f"cerca de {numero(p * 100, 0)}")
            frases.append(f"O resultado muda com a sorte. Em 9 de cada 10 simulações, ficou entre "
                          f"{resultado(f['p5'])} e {resultado(f['p95'])}. Se 100 pessoas apostassem assim, "
                          f"{quantas} terminariam no prejuízo.")
    else:
        frases.append(f"Para saber quanto {v['perderia']} em média, diga também a odd e quantas de cada 100 "
                      "apostas acerta. Exemplo: odd 1,80 e 50% de chance.")
    if "valor_final_investimento" in s:
        fv = s["valor_final_investimento"]
        taxa = numero(c.taxa_anual * 100, 1).replace(",0", "")
        if "custo_oportunidade" in s:
            frases.append(f"Se guardasse esse dinheiro, rendendo {taxa}% ao ano, teria {dinheiro(fv)} no fim. "
                          f"Apostando, ficaria em média com {dinheiro(s['sobra_media_apostando'])}. "
                          f"A diferença é de {dinheiro(s['custo_oportunidade'])}.")
        else:
            frases.append(f"Se guardasse esse dinheiro, rendendo {taxa}% ao ano, teria {dinheiro(fv)} no fim, "
                          f"{dinheiro(s['rendimento'])} a mais do que separou.")
    else:
        frases.append("Para comparar com guardar o dinheiro, diga quanto ele renderia por ano. Exemplo: 8% ao ano.")
    return frases


def explicar_aposta_unica(valor: float, odd: float, probabilidade: float | None) -> list[str]:
    a = aposta_unica(valor, odd, probabilidade)
    frases = [f"Se acertar, você recebe {exato(a['retorno'])}: os {exato(valor)} de volta mais "
              f"{exato(a['lucro'])} de lucro. Se errar, perde os {exato(valor)}.",
              f"Com odd {numero(odd, 2)}, só deixa de perder no longo prazo quem acerta "
              f"{acertos_para_empatar(odd)} apostas assim."]
    if "ve" in a:
        ve = a["ve"]
        media = "não ganha nem perde" if abs(ve) < 0.005 else (
            f"perde {exato(-ve)}" if ve < 0 else f"ganha {exato(ve)}")
        frases.append(f"Se você acerta {em_100(probabilidade, exato=True)}, na média {media} por aposta.")
    return frases
