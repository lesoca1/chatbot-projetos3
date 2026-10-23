"""Implementação III: linguagem simples, glossário e perguntas escritas como o apostador escreve."""

import statistics
import sys
from pathlib import Path

import pytest

from assistente.assistente import Assistente
from assistente.explicacao import em_100, explicar, resumir
from assistente.legibilidade import flesch, palavras_por_frase
from assistente.simulador import Cenario, simular

A = Assistente()
REGISTROS = A.base["registros"]
CASO_IV = Cenario(50, 1, "semana", 5, odd=1.80, probabilidade=0.5, taxa_anual=0.08)


def test_todo_registro_tem_resumo_curto():
    for r in REGISTROS + list(A.base["respostas_seguranca"].values()):
        assert r["resumo"], r["id"]
        assert len(r["resumo"].split()) <= 22, r["id"]


def test_respostas_sao_faceis_de_ler():
    # Flesch adaptado ao português: 75 ou mais é "muito fácil"; 50 a 75 é "fácil".
    notas = [flesch(r["resposta"]) for r in REGISTROS]
    assert statistics.mean(notas) >= 75
    assert min(notas) >= 50
    assert statistics.mean(palavras_por_frase(r["resposta"]) for r in REGISTROS) <= 13


def test_explicacao_do_simulador_sem_jargao():
    texto = " ".join(explicar(CASO_IV, simular(CASO_IV))).lower()
    for termo in ["valor esperado", "monte carlo", "percentil", "probabilidade implícita", "hipótese",
                  "custo de oportunidade", "trajetória"]:
        assert termo not in texto
    assert ",00" not in texto  # sem centavos em valores grandes
    assert flesch(texto) >= 75


def test_resumo_do_simulador():
    assert resumir(CASO_IV, simular(CASO_IV)) == "Em 5 anos, você perderia em média R$ 1.300 dos R$ 13.000 apostados."


@pytest.mark.parametrize("p,esperado", [(0.969, "97 de cada 100"), (0.9995, "mais de 99 de cada 100"),
                                        (0.001, "menos de 1 de cada 100"), (0.5, "50 de cada 100")])
def test_chance_em_100(p, esperado):
    assert em_100(p) == esperado


@pytest.mark.parametrize("pergunta,esperado", [
    ("o que é green e red?", "green_red"),
    ("gestão de banca dá lucro?", "banca"),
    ("o que é stake?", "stake"),
    ("o que é zebra?", "zebra_favorito"),
    ("por que as odds mudam?", "odds_mudam"),
    ("o que é ambas marcam?", "ambas_marcam"),
    ("placar exato vale a pena?", "placar_exato"),
    ("acerto mais da metade e perco dinheiro, por quê?", "acerto_vs_lucro"),
    ("surebet é garantido?", "surebet"),
    ("o que é odd turbinada?", "odd_turbinada"),
    ("como colocar limite de depósito?", "limite_deposito"),
    ("como ver quanto já perdi?", "quanto_ja_perdi"),
    ("a bet não paga meu saque", "saque_problema"),
    ("bet autorizada é segura?", "autorizada_nao_garante"),
    ("quais termos das apostas preciso conhecer?", "glossario"),
    # Erros de digitação e escrita informal
    ("oq é handcap", "handicap"),
    ("o que é probabilidade inplicita", "probabilidade_implicita"),
    ("vc sabe o resultado do jogo?", "dados_externos"),
    ("quanto do salário posso gastar com bet?", "orcamento_lazer"),
])
def test_perguntas_novas_e_informais(pergunta, esperado):
    r = A.responder(pergunta)
    assert r.tipo == "base" and r.registro["id"] == esperado


def test_salario_ja_usado_continua_sinal_de_risco():
    assert A.responder("gastei o salário todo na bet").tipo == "seguranca"


def test_glossario_explica_palavras_da_resposta():
    r = A.responder("o que é margem da casa?")
    termos = [t for t, _ in r.termos]
    assert "odd" in termos
    assert "margem da casa" not in termos  # a resposta inteira já explica esse termo


def test_glossario_responde_termo_sem_registro():
    r = A.responder("o que significa tipster?")
    assert r.tipo in ("base", "glossario")
    r = A.responder("o que é mandante?")
    assert "joga em casa" in r.resumo  # cai no registro do 1X2, mas a definição vem primeiro
    r = A.responder("o que quer dizer quota fixa?")
    assert "prêmio fica definido" in r.resumo


def test_glossario_bem_formado():
    termos = [g["termo"] for g in A.base["glossario"]]
    assert len(termos) == len(set(termos)) >= 30
    assert all(g["formas"] and g["definicao"] for g in A.base["glossario"])


def test_conjunto_de_perguntas_do_apostador():
    # Conjunto usado para guiar a ampliação da base: serve de teste de regressão.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs" / "avaliacao"))
    from avaliar import avaliar
    certas, total, erros = avaliar(A)
    assert certas / total >= 0.9, erros
