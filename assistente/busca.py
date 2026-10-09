"""Busca na base de conhecimento (BM25), sem modelo de linguagem e sem internet.

Cada forma alternativa de pergunta de um registro vira um documento. A nota do
registro é a maior nota entre os seus documentos. Abaixo do limiar, o assistente
diz que a base não cobre a pergunta em vez de improvisar.
"""

import math
from collections import Counter
from dataclasses import dataclass

from .texto import tokens

K1 = 1.5
B = 0.75
LIMIAR_NOTA = 5.0
LIMIAR_COBERTURA = 0.34
# Pergunta curta em que todas as palavras aparecem no registro, como "o que é probabilidade".
LIMIAR_NOTA_COBERTURA_TOTAL = 3.0


@dataclass
class Resultado:
    registro: dict
    nota: float
    cobertura: float


class IndiceBM25:
    def __init__(self, registros: list[dict]):
        self.registros = {r["id"]: r for r in registros}
        self.docs: list[tuple[str, list[str]]] = []
        for r in registros:
            for pergunta in r["perguntas"]:
                self.docs.append((r["id"], tokens(pergunta)))
            chave = " ".join(r.get("palavras_chave", [])) + " " + r["tema"]
            self.docs.append((r["id"], tokens(chave)))
        self.n = len(self.docs)
        self.media_len = sum(len(d) for _, d in self.docs) / self.n
        df = Counter()
        for _, d in self.docs:
            df.update(set(d))
        self.idf = {t: math.log(1 + (self.n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def _nota(self, consulta: list[str], doc: list[str]) -> float:
        tf = Counter(doc)
        nota = 0.0
        for t in consulta:
            if t not in tf:
                continue
            f = tf[t]
            nota += self.idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * len(doc) / self.media_len))
        return nota

    def buscar(self, pergunta: str, k: int = 3) -> list[Resultado]:
        consulta = tokens(pergunta)
        if not consulta:
            return []
        melhores: dict[str, Resultado] = {}
        for rid, doc in self.docs:
            nota = self._nota(consulta, doc)
            if nota <= 0:
                continue
            cobertura = sum(1 for t in set(consulta) if t in doc) / len(set(consulta))
            atual = melhores.get(rid)
            if atual is None or nota > atual.nota:
                melhores[rid] = Resultado(self.registros[rid], nota, cobertura)
        return sorted(melhores.values(), key=lambda r: r.nota, reverse=True)[:k]

    @staticmethod
    def suficiente(r: Resultado) -> bool:
        if r.cobertura == 1.0 and r.nota >= LIMIAR_NOTA_COBERTURA_TOTAL:
            return True
        return r.nota >= LIMIAR_NOTA and r.cobertura >= LIMIAR_COBERTURA
