"""Índice de legibilidade de Flesch adaptado ao português (Martins et al., 1996).

    índice = 248,835 − 1,015 × (palavras por frase) − 84,6 × (sílabas por palavra)

Faixas usuais: 75 a 100 muito fácil, 50 a 75 fácil, 25 a 50 difícil, 0 a 25 muito difícil.
As sílabas são contadas pelos grupos de vogais, uma aproximação suficiente para comparar versões
do mesmo texto. Usado nos testes e no documento de entrega.
"""

import re

RE_FRASE = re.compile(r"(?<=[.!?])\s+")
RE_PALAVRA = re.compile(r"[A-Za-zÀ-ÿ0-9]+(?:[-'][A-Za-zÀ-ÿ]+)*")
RE_VOGAIS = re.compile(r"[aeiouáéíóúâêôãõàüy]+")


def silabas(palavra: str) -> int:
    if palavra.isdigit():
        return max(1, len(palavra))
    return max(1, len(RE_VOGAIS.findall(palavra.lower())))


def flesch(texto: str) -> float:
    frases = [f for f in RE_FRASE.split(texto.strip()) if f]
    palavras = RE_PALAVRA.findall(texto)
    if not frases or not palavras:
        return 0.0
    return (248.835 - 1.015 * len(palavras) / len(frases)
            - 84.6 * sum(silabas(p) for p in palavras) / len(palavras))


def palavras_por_frase(texto: str) -> float:
    frases = [f for f in RE_FRASE.split(texto.strip()) if f]
    return len(RE_PALAVRA.findall(texto)) / max(1, len(frases))
