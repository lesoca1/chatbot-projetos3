"""Leitura de um cenário de apostas escrito na conversa.

Exemplo: "aposto R$ 50 por semana há 5 anos, odd 1,80, 50% de chance, 8% ao ano".
Só extrai números que o usuário escreveu. Nada é estimado ou buscado fora da
conversa: se um dado falta, o assistente diz o que falta.
"""

import re
from dataclasses import replace

from .simulador import Cenario
from .texto import sem_acento

PALAVRAS_NUMERO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
    "sete": 7, "oito": 8, "nove": 9, "dez": 10, "doze": 12, "vinte": 20, "trinta": 30,
}
NUM = r"(\d+(?:[.,]\d+)*|" + "|".join(PALAVRAS_NUMERO) + r")"
PERIODO = {"dia": "dia", "dias": "dia", "semana": "semana", "semanas": "semana", "mes": "mes", "meses": "mes"}

RE_VALOR = [
    re.compile(r"r\$\s*" + NUM + r"(\s*mil\b)?"),
    re.compile(NUM + r"(\s*mil)?\s*(?:reais|real|conto|contos|pila)\b"),
]
RE_FREQ = re.compile(NUM + r"\s*(?:vez|vezes|apostas?|jogos?|bilhetes?)\s*(?:por|ao|a|na|no|em cada|cada)\s*(dia|semana|mes)\b")
RE_PERIODICIDADE = [
    (re.compile(r"\b(?:por|ao|cada|todo|toda|todos os|todas as)\s+(dia|dias|semana|semanas|mes|meses)\b"), None),
    (re.compile(r"\b(?:fim|final|fins|finais) de semana\b"), "semana"),
    (re.compile(r"\bdiari[oa]s?\b|\bdiariamente\b"), "dia"),
    (re.compile(r"\bsemana(?:l|is|lmente)\b"), "semana"),
    (re.compile(r"\bmens(?:al|ais|almente)\b"), "mes"),
]
RE_DURACAO = [
    (re.compile(NUM + r"\s*anos?\b"), 1),
    (re.compile(NUM + r"\s*mes(?:es)?\b"), 1 / 12),
    (re.compile(NUM + r"\s*semanas\b"), 1 / 52),
    (re.compile(r"\bmeio ano\b"), None),
]
RE_ODD = re.compile(r"\b(?:odds?|cotac(?:ao|oes))\s*(?:media|medio|de|da|em|igual a|=|:)?\s*(?:de\s*)?(\d+(?:[.,]\d+)?)")
RE_PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:%|por cento)")
RE_CORTE = re.compile(r"[,;\d]| e ")
CONTEXTO_TAXA = re.compile(r"\bano\b|taxa|\ba\.?a\b|anual|rend|juros|poupanca|investi|aplica|selic|cdi|guard")
CONTEXTO_CHANCE = re.compile(r"chance|acert|probab|ganh|vitori|venc")
RE_SEGUIMENTO = re.compile(r"^\s*(?:e se|e com|e no caso|e quando|e|agora|mas e|e para|e pra)\b|\be se\b")


def _numero(txt: str) -> float:
    if txt in PALAVRAS_NUMERO:
        return float(PALAVRAS_NUMERO[txt])
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", txt):  # 1.000 ou 1.000,50
        txt = txt.replace(".", "")
    return float(txt.replace(",", "."))


def extrair(texto: str) -> dict:
    """Devolve só os campos que aparecem no texto."""
    t = sem_acento(texto.lower())
    dados: dict = {}

    for rx in RE_VALOR:
        m = rx.search(t)
        if m:
            dados["valor_por_aposta"] = _numero(m.group(1)) * (1000 if m.group(2) else 1)
            break

    m = RE_FREQ.search(t)
    if m:
        dados["apostas_por_periodo"] = _numero(m.group(1))
        dados["periodicidade"] = m.group(2)
    else:
        for rx, fixo in RE_PERIODICIDADE:
            m = rx.search(t)
            if m:
                dados["periodicidade"] = fixo or PERIODO[m.group(1)]
                break

    for rx, fator in RE_DURACAO:
        m = rx.search(t)
        if m:
            dados["anos"] = 0.5 if fator is None else _numero(m.group(1)) * fator
            break

    m = RE_ODD.search(t)
    if m:
        dados["odd"] = _numero(m.group(1))

    # Cada porcentagem é lida pelas palavras vizinhas, até a vírgula ou o número mais próximo.
    for m in RE_PCT.finditer(t):
        depois = RE_CORTE.split(t[m.end():], maxsplit=1)[0]
        antes = RE_CORTE.split(t[:m.start()])[-1]
        valor = _numero(m.group(1)) / 100
        for trecho in (depois, antes):
            if CONTEXTO_CHANCE.search(trecho):
                dados.setdefault("probabilidade", valor)
                break
            if CONTEXTO_TAXA.search(trecho):
                dados.setdefault("taxa_anual", valor)
                break
    return dados


RE_NUMEROS = re.compile(r"r\$\s*[\d.,]+(\s*mil\b)?|\b\d+(?:[.,]\d+)*\s*(?:%|por cento|mil|reais|real)?")


def sem_numeros(texto: str) -> str:
    """Texto sem os valores do cenário, para a busca na base não ser diluída por eles."""
    return RE_NUMEROS.sub(" ", sem_acento(texto.lower()))


def eh_seguimento(texto: str) -> bool:
    return bool(RE_SEGUIMENTO.search(sem_acento(texto.lower())))


def montar(texto: str, anterior: Cenario | None = None) -> tuple[Cenario | None, list[str]]:
    """Monta o cenário da pergunta. Devolve (cenário, avisos sobre dados assumidos).

    - Valor e periodicidade na mesma frase: cenário novo.
    - Frase de seguimento ("e se eu apostar 3 vezes por semana?") com algum número:
      altera o cenário anterior da conversa.
    """
    dados = extrair(texto)
    avisos = []
    if anterior is not None and dados and eh_seguimento(texto):
        if "periodicidade" in dados and "apostas_por_periodo" not in dados:
            dados["apostas_por_periodo"] = 1
        return replace(anterior, **dados), avisos
    if "valor_por_aposta" in dados and "periodicidade" in dados:
        if "anos" not in dados:
            dados["anos"] = 1.0
            avisos.append("Você não disse por quanto tempo; as contas mostram 1 ano.")
        dados.setdefault("apostas_por_periodo", 1)
        return Cenario(**dados), avisos
    return None, avisos
