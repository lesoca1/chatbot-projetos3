"""Orquestra a resposta: segurança primeiro, depois busca restrita à base."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from .busca import IndiceBM25
from .seguranca import detectar_risco

CAMINHO_BASE = Path(__file__).resolve().parent.parent / "base" / "base_conhecimento.json"

MENSAGEM_FORA_DA_BASE = (
    "Não encontrei essa resposta na base de conhecimento do assistente. "
    "Para não inventar informação, só respondo com o conteúdo da base, sem consultar a internet. "
    "Tente reformular a pergunta ou escolha um dos temas ao lado."
)


@dataclass
class Resposta:
    tipo: str  # "base", "seguranca" ou "fora_da_base"
    texto: str
    registro: dict | None = None
    fontes: list[str] = field(default_factory=list)
    sugestoes: list[str] = field(default_factory=list)


class Assistente:
    def __init__(self, caminho_base: Path = CAMINHO_BASE):
        with open(caminho_base, encoding="utf-8") as f:
            self.base = json.load(f)
        self.indice = IndiceBM25(self.base["registros"])

    @property
    def data_revisao(self) -> str:
        return self.base["data_revisao"]

    def temas(self) -> dict[str, list[str]]:
        saida: dict[str, list[str]] = {}
        for r in self.base["registros"]:
            saida.setdefault(r["tema"], []).append(r["perguntas"][0])
        return saida

    def citar(self, chaves: list[str]) -> list[str]:
        return [self.base["fontes"][c] for c in chaves]

    def responder(self, pergunta: str) -> Resposta:
        risco = detectar_risco(pergunta)
        if risco:
            reg = self.base["respostas_seguranca"][risco]
            return Resposta("seguranca", reg["resposta"], reg, self.citar(reg["fontes"]))

        resultados = self.indice.buscar(pergunta)
        if resultados and self.indice.suficiente(resultados[0]):
            reg = resultados[0].registro
            return Resposta("base", reg["resposta"], reg, self.citar(reg["fontes"]))

        sugestoes = [r.registro["perguntas"][0] for r in resultados if r.nota > 0][:3]
        return Resposta("fora_da_base", MENSAGEM_FORA_DA_BASE, sugestoes=sugestoes)
