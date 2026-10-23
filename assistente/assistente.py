"""Orquestra a resposta: segurança primeiro, depois busca restrita à base e simulador."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import cenario as leitor
from .busca import IndiceBM25
from .explicacao import explicar, explicar_aposta_unica, resumir
from .seguranca import detectar_risco
from .simulador import Cenario, simular
from .texto import sem_acento

CAMINHO_BASE = Path(__file__).resolve().parent.parent / "base" / "base_conhecimento.json"

MENSAGEM_FORA_DA_BASE = (
    "Essa pergunta não está na minha base. Para não inventar, só respondo com o que o grupo escreveu e "
    "revisou, sem consultar a internet. Tente com outras palavras ou escolha um tema ao lado."
)
MENSAGEM_SIMULACAO = "Fiz as contas com os seus números."
MAX_TERMOS = 4
RE_PEDIDO_DEFINICAO = re.compile(r"\b(o que|oque|oq|que)\s+(e|eh|sao|significa|quer dizer)\b|\bsignifica")

# Temas em que o simulador não é anexado: pedidos de palpite e estratégia recebem só a resposta neutra.
TEMAS_SEM_SIMULADOR = {"Limites do assistente"}


@dataclass
class Resposta:
    tipo: str  # "base", "simulacao", "seguranca", "glossario" ou "fora_da_base"
    texto: str
    registro: dict | None = None
    fontes: list[str] = field(default_factory=list)
    sugestoes: list[str] = field(default_factory=list)
    cenario: Cenario | None = None
    simulacao: dict | None = None
    calculo: list[str] = field(default_factory=list)  # frases com os números calculados
    resumo: str = ""  # a resposta em uma frase, mostrada primeiro
    termos: list[tuple[str, str]] = field(default_factory=list)  # palavras difíceis da resposta e o que querem dizer


class Assistente:
    def __init__(self, caminho_base: Path = CAMINHO_BASE):
        with open(caminho_base, encoding="utf-8") as f:
            self.base = json.load(f)
        self.indice = IndiceBM25(self.base["registros"])
        # Formas mais longas primeiro, para "probabilidade implícita" ganhar de "probabilidade".
        self._formas = sorted(((sem_acento(f.lower()), g) for g in self.base["glossario"] for f in g["formas"]),
                              key=lambda x: -len(x[0]))

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

    def termos_em(self, texto: str, ignorar: str = "") -> list[dict]:
        """Verbetes do glossário que aparecem no texto, na ordem em que aparecem.

        Termos que já estão em `ignorar` (a pergunta do registro) ficam de fora:
        a resposta inteira já explica esse termo.
        """
        alvo, ignorar = sem_acento(texto.lower()), sem_acento(ignorar.lower())
        achados: dict[str, tuple[int, dict]] = {}
        for forma, g in self._formas:
            m = re.search(r"\b" + re.escape(forma) + r"\b", alvo)
            if not m or g["termo"] in achados:
                continue
            if any(re.search(r"\b" + re.escape(sem_acento(f.lower())) + r"\b", ignorar) for f in g["formas"]):
                continue
            achados[g["termo"]] = (m.start(), g)
            alvo = alvo[:m.start()] + " " * len(forma) + alvo[m.end():]  # não conta "probabilidade" de novo
        return [g for _, g in sorted(achados.values(), key=lambda x: x[0])]

    def _montar(self, tipo: str, reg: dict, pergunta: str = "", **extra) -> Resposta:
        texto = reg["resumo"] + " " + reg["resposta"]
        ignorar = pergunta + " " + reg.get("perguntas", [""])[0]
        termos = [(g["termo"], g["definicao"]) for g in self.termos_em(texto, ignorar)]
        resumo = reg["resumo"]
        # "O que é mediana?" caiu num registro mais amplo: a definição do termo vem primeiro.
        if RE_PEDIDO_DEFINICAO.search(sem_acento(pergunta.lower())):
            pedidos = self.termos_em(pergunta, reg.get("perguntas", [""])[0])
            if pedidos:
                g = pedidos[0]
                resumo = f"{g['termo'][0].upper()}{g['termo'][1:]}: {g['definicao']}"
                termos = [x for x in termos if x[0] != g["termo"]]
        return Resposta(tipo, reg["resposta"], reg, self.citar(reg["fontes"]), resumo=resumo,
                        termos=termos[:MAX_TERMOS], **extra)

    def definir(self, pergunta: str) -> Resposta | None:
        """Pergunta do tipo "o que é X", com X no glossário mas sem registro próprio."""
        if not RE_PEDIDO_DEFINICAO.search(sem_acento(pergunta.lower())):
            return None
        achados = self.termos_em(pergunta)
        if not achados:
            return None
        g = achados[0]
        return Resposta("glossario", f"{g['termo'][0].upper()}{g['termo'][1:]}: {g['definicao']}",
                        fontes=self.citar(["GLOSSARIO_GRUPO"]))

    def responder(self, pergunta: str, cenario_anterior: Cenario | None = None) -> Resposta:
        # 1. Segurança tem prioridade e desliga o simulador.
        risco = detectar_risco(pergunta)
        if risco:
            return self._montar("seguranca", self.base["respostas_seguranca"][risco], pergunta)

        # 2. Busca só na base. Se a frase traz um cenário, os números saem da busca.
        dados = leitor.extrair(pergunta)
        resultados = self.indice.buscar(leitor.sem_numeros(pergunta) if dados else pergunta)
        reg = resultados[0].registro if resultados and self.indice.suficiente(resultados[0]) else None
        if reg is not None and reg["tema"] in TEMAS_SEM_SIMULADOR:
            return self._montar("base", reg, pergunta)

        # 3. Números da conversa vão para o simulador.
        c, avisos = leitor.montar(pergunta, cenario_anterior)
        if c is not None:
            s = simular(c)
            calculo = avisos + explicar(c, s)
            seguimento = cenario_anterior is not None and leitor.eh_seguimento(pergunta)
            if reg is not None and not seguimento:
                return self._montar("base", reg, pergunta, cenario=c, simulacao=s, calculo=calculo)
            return Resposta("simulacao", MENSAGEM_SIMULACAO, cenario=c, simulacao=s, calculo=calculo,
                            resumo=resumir(c, s))

        if reg is not None:
            calculo = []
            if "valor_por_aposta" in dados and "odd" in dados and dados["odd"] > 1:
                calculo = explicar_aposta_unica(dados["valor_por_aposta"], dados["odd"], dados.get("probabilidade"))
            return self._montar("base", reg, pergunta, calculo=calculo)

        definicao = self.definir(pergunta)
        if definicao is not None:
            return definicao

        sugestoes = [r.registro["perguntas"][0] for r in resultados if r.nota > 0][:3]
        return Resposta("fora_da_base", MENSAGEM_FORA_DA_BASE, sugestoes=sugestoes)
