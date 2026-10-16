"""Normalização de texto em português para a busca na base."""

import re
import unicodedata

STOPWORDS = set("""
a o as os um uma uns umas de do da dos das em no na nos nas por pelo pela pelos pelas
para pra pro com sem e ou que se me te nos lhe eu tu ele ela voce voces meu minha
meus minhas seu sua seus suas isso isto esse essa este esta aquele aquela ao aos
como qual quais quando onde ja ate mais muito muita muitos muitas tem ter
sao ser foi era e esta estou estar ha hoje la aqui entao mas tambem so nao sim
the
""".split())

# Sinônimos levados a uma forma comum antes da busca.
SINONIMOS = {
    "cotacao": "odd",
    "cotacoes": "odd",
    "odds": "odd",
    "bets": "bet",
    "apostar": "aposta",
    "apostas": "aposta",
    "apostando": "aposta",
    "aposto": "aposta",
    "apostei": "aposta",
    "chance": "probabilidade",
    "chances": "probabilidade",
    "viciado": "vicio",
    "viciada": "vicio",
    "vicio": "vicio",
    "compulsao": "vicio",
    "ludopatia": "vicio",
    "palpites": "palpite",
    "dica": "palpite",
    "dicas": "palpite",
    "tip": "palpite",
    "tips": "palpite",
    "investir": "investimento",
    "investindo": "investimento",
    "aplicacao": "investimento",
    "poupanca": "investimento",
    "calculo": "calcul",
    "calcula": "calcul",
    "calcular": "calcul",
    "calculando": "calcul",
    "calculado": "calcul",
}


def sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def radical(palavra: str) -> str:
    """Radicalizador simples: corta sufixos comuns para juntar variações."""
    for sufixo in ("mente", "coes", "cao", "oes", "ades", "ade", "ismo", "istas", "ista",
                   "ando", "endo", "indo", "ados", "idas", "idos", "adas", "ado", "ida", "ido", "ada",
                   "ar", "er", "ir", "es", "s"):
        if len(palavra) > len(sufixo) + 3 and palavra.endswith(sufixo):
            return palavra[: -len(sufixo)]
    return palavra


def normalizar(texto: str) -> str:
    texto = sem_acento(texto.lower())
    texto = re.sub(r"(\d),(\d)", r"\1.\2", texto)
    return re.sub(r"[^a-z0-9.$ ]+", " ", texto)


def tokens(texto: str) -> list[str]:
    saida = []
    for palavra in normalizar(texto).split():
        palavra = palavra.strip(".")
        if not palavra or palavra in STOPWORDS:
            continue
        palavra = SINONIMOS.get(palavra, palavra)
        saida.append(radical(palavra))
    return saida
