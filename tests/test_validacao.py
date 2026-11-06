"""Testes e Validação II: as perguntas dos testes viram teste de regressão.

Se uma mudança na base fizer o assistente errar uma pergunta que já acertava, o teste falha.
"""

import json
from pathlib import Path

import pytest

from assistente.assistente import Assistente

A = Assistente()
PASTA = Path(__file__).resolve().parent.parent / "docs" / "avaliacao"


def carregar(nome: str) -> list:
    return json.loads((PASTA / nome).read_text(encoding="utf-8"))["perguntas"]


def achado(pergunta: str) -> str:
    r = A.responder(pergunta)
    return r.registro["id"] if r.registro and r.tipo not in ("seguranca", "glossario") else r.tipo


@pytest.mark.parametrize("perfil,tarefa,pergunta,aceitos", carregar("perguntas_testes_i.json"))
def test_perguntas_das_sessoes_da_testes_i(perfil, tarefa, pergunta, aceitos):
    assert achado(pergunta) in aceitos


@pytest.mark.parametrize("pergunta,esperado", carregar("perguntas_novas.json") + carregar("perguntas_validacao_final.json"))
def test_conjuntos_de_controle_e_validacao(pergunta, esperado):
    assert achado(pergunta) == esperado


def test_conjunto_de_desenvolvimento():
    dados = carregar("perguntas_apostador.json")
    certas = sum(achado(p) == e for p, e in dados)
    assert certas / len(dados) >= 0.95
