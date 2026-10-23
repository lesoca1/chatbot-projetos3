"""Integração entre conversa e simulador: números ditos no chat viram cenário."""

import pytest

from assistente.assistente import Assistente
from assistente.cenario import extrair, montar
from assistente.simulador import Cenario

A = Assistente()


@pytest.mark.parametrize("texto,esperado", [
    ("Aposto R$ 50 por semana há 5 anos, odd 1,80, 50% de chance, 8% ao ano",
     dict(valor_por_aposta=50, periodicidade="semana", anos=5, odd=1.8, probabilidade=0.5, taxa_anual=0.08)),
    ("aposto 30 reais 3 vezes por semana durante 2 anos com odd média 2,1 e acerto 45%",
     dict(valor_por_aposta=30, apostas_por_periodo=3, periodicidade="semana", anos=2, odd=2.1, probabilidade=0.45)),
    ("gasto R$ 1.000 por mês em bets faz 6 meses, a poupança rende 6% ao ano",
     dict(valor_por_aposta=1000, periodicidade="mes", anos=0.5, taxa_anual=0.06)),
    ("todo fim de semana aposto 2 mil reais", dict(valor_por_aposta=2000, periodicidade="semana")),
    ("aposto cinco reais diariamente há dois anos", dict(valor_por_aposta=5, periodicidade="dia", anos=2)),
    ("R$ 50 por semana, 5 anos, chance de 50%, taxa de 10%",
     dict(valor_por_aposta=50, periodicidade="semana", anos=5, probabilidade=0.5, taxa_anual=0.10)),
])
def test_extrai_numeros_da_frase(texto, esperado):
    assert extrair(texto) == pytest.approx(esperado)


def test_sem_periodo_assume_um_ano_e_avisa():
    c, avisos = montar("quanto eu coloco em risco apostando R$ 20 por dia?")
    assert c == Cenario(20, 1, "dia", 1.0)
    assert avisos


@pytest.mark.parametrize("texto", ["menor de 18 anos pode apostar?", "qual odd eu devo buscar?",
                                   "o que é over 2,5?", "o que significa 50% de chance?"])
def test_perguntas_sem_cenario_nao_viram_simulacao(texto):
    assert montar(texto)[0] is None
    assert A.responder(texto).simulacao is None


def test_caso_do_conteudo_iv_na_conversa():
    r = A.responder("Aposto R$ 50 por semana há 5 anos, odd 1,80, 50% de chance, 8% ao ano")
    assert r.tipo == "simulacao"
    assert r.simulacao["ve_total"] == pytest.approx(-1300)
    texto = " ".join(r.calculo)
    assert "260 apostas" in texto and "R$ 13.000" in texto and "R$ 15.844" in texto
    assert "perderia R$ 1.300" in texto and "R$ 10 de cada R$ 100" in texto
    assert "pelo menos 56 de cada 100" in texto and "acerta 50 de cada 100" in texto


def test_pergunta_da_base_com_numeros_traz_texto_e_contas():
    r = A.responder("Quanto eu coloco em risco apostando R$ 20 por dia?")
    assert r.tipo == "base" and r.registro["id"] == "frequencia_risco"
    assert r.simulacao["total_em_risco"] == pytest.approx(7300)


def test_seguimento_altera_o_cenario_anterior():
    r1 = A.responder("Aposto R$ 50 por semana há 5 anos, odd 1,80, 50% de chance")
    r2 = A.responder("e se eu apostar 3 vezes por semana?", r1.cenario)
    assert r2.tipo == "simulacao"
    assert r2.cenario.apostas_por_periodo == 3 and r2.cenario.odd == 1.8
    assert r2.simulacao["numero_de_apostas"] == 780
    r3 = A.responder("e com 40% de chance?", r2.cenario)
    assert r3.cenario.probabilidade == 0.4 and r3.cenario.apostas_por_periodo == 3


def test_seguimento_sem_cenario_anterior_nao_inventa():
    assert A.responder("e com 40% de chance?").simulacao is None


def test_aposta_unica_na_conversa():
    r = A.responder("Quanto recebo se apostar R$ 10 com odd 2,5?")
    assert r.registro["id"] == "calcular_retorno"
    assert any("R$ 25,00" in f for f in r.calculo)


@pytest.mark.parametrize("texto", [
    "quero recuperar o que perdi apostando R$ 100 por dia",
    "peguei emprestado R$ 500 para apostar toda semana",
])
def test_sinal_de_risco_desliga_o_simulador(texto):
    r = A.responder(texto)
    assert r.tipo == "seguranca" and r.simulacao is None


def test_pedido_de_estrategia_nao_vira_otimizacao():
    r = A.responder("qual estratégia dá mais lucro apostando R$ 50 por semana?")
    assert r.registro["id"] == "estrategia_ganhar"
    assert r.registro["seguranca"] == "nao_recomendar"


def test_entrada_invalida_explica_o_erro():
    r = A.responder("aposto R$ 50 por semana há 5 anos com odd 0,9 e 50% de chance")
    assert r.simulacao["erros"]
    assert any("odd" in f for f in r.calculo)
