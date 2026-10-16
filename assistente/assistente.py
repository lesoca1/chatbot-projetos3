"""Orquestra a resposta: segurança primeiro, depois busca restrita à base e simulador."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import cenario as leitor
from .busca import IndiceBM25
from .explicacao import explicar, explicar_aposta_unica
from .seguranca import detectar_risco
from .simulador import Cenario, simular

CAMINHO_BASE = Path(__file__).resolve().parent.parent / "base" / "base_conhecimento.json"

MENSAGEM_FORA_DA_BASE = (
    "Não encontrei essa resposta na base de conhecimento do assistente. "
    "Para não inventar informação, só respondo com o conteúdo da base, sem consultar a internet. "
    "Tente reformular a pergunta ou escolha um dos temas ao lado."
)
MENSAGEM_SIMULACAO = "Fiz as contas com os números que você informou."

# Temas em que o simulador não é anexado: pedidos de palpite e estratégia recebem só a resposta neutra.
TEMAS_SEM_SIMULADOR = {"Limites do assistente"}


@dataclass
class Resposta:
    tipo: str  # "base", "simulacao", "seguranca" ou "fora_da_base"
    texto: str
    registro: dict | None = None
    fontes: list[str] = field(default_factory=list)
    sugestoes: list[str] = field(default_factory=list)
    cenario: Cenario | None = None
    simulacao: dict | None = None
    calculo: list[str] = field(default_factory=list)  # frases com os números calculados


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

    def responder(self, pergunta: str, cenario_anterior: Cenario | None = None) -> Resposta:
        # 1. Segurança tem prioridade e desliga o simulador.
        risco = detectar_risco(pergunta)
        if risco:
            reg = self.base["respostas_seguranca"][risco]
            return Resposta("seguranca", reg["resposta"], reg, self.citar(reg["fontes"]))

        # 2. Busca só na base. Se a frase traz um cenário, os números saem da busca.
        dados = leitor.extrair(pergunta)
        resultados = self.indice.buscar(leitor.sem_numeros(pergunta) if dados else pergunta)
        reg = resultados[0].registro if resultados and self.indice.suficiente(resultados[0]) else None
        if reg is not None and reg["tema"] in TEMAS_SEM_SIMULADOR:
            return Resposta("base", reg["resposta"], reg, self.citar(reg["fontes"]))

        # 3. Números da conversa vão para o simulador.
        c, avisos = leitor.montar(pergunta, cenario_anterior)
        if c is not None:
            s = simular(c)
            calculo = avisos + explicar(c, s)
            seguimento = cenario_anterior is not None and leitor.eh_seguimento(pergunta)
            if reg is not None and not seguimento:
                return Resposta("base", reg["resposta"], reg, self.citar(reg["fontes"]),
                                cenario=c, simulacao=s, calculo=calculo)
            return Resposta("simulacao", MENSAGEM_SIMULACAO, cenario=c, simulacao=s, calculo=calculo)

        if reg is not None:
            calculo = []
            if "valor_por_aposta" in dados and "odd" in dados and dados["odd"] > 1:
                calculo = explicar_aposta_unica(dados["valor_por_aposta"], dados["odd"], dados.get("probabilidade"))
            return Resposta("base", reg["resposta"], reg, self.citar(reg["fontes"]), calculo=calculo)

        sugestoes = [r.registro["perguntas"][0] for r in resultados if r.nota > 0][:3]
        return Resposta("fora_da_base", MENSAGEM_FORA_DA_BASE, sugestoes=sugestoes)
