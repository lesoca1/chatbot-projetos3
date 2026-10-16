"""Simulador completo: Monte Carlo conferido com a conta exata, sensibilidade, margem e investimento."""

import pytest

from assistente.simulador import (Cenario, aposta_unica, margem_da_casa, prob_prejuizo_exata, quantil_exato,
                                  simular, simular_trajetorias, valor_final_investimento)

CASO_IV = Cenario(50, 1, "semana", 5, odd=1.80, probabilidade=0.5, taxa_anual=0.08)


def test_monte_carlo_bate_com_a_distribuicao_exata():
    t = simular_trajetorias(CASO_IV)["final"]
    # Resultado = 50 × (1,80 × vitórias − 260); desvio-padrão ≈ R$ 726, erro da média em 10.000 sorteios ≈ R$ 7.
    assert t["media"] == pytest.approx(-1300, abs=40)
    assert t["p5"] == pytest.approx(quantil_exato(CASO_IV, 0.05), abs=100)
    assert t["mediana"] == pytest.approx(quantil_exato(CASO_IV, 0.50), abs=100)
    assert t["p95"] == pytest.approx(quantil_exato(CASO_IV, 0.95), abs=100)
    assert t["prob_prejuizo"] == pytest.approx(prob_prejuizo_exata(260, 1.80, 0.5), abs=0.01)


def test_monte_carlo_e_reproduzivel_e_ordenado():
    a, b = simular_trajetorias(CASO_IV), simular_trajetorias(CASO_IV)
    assert a == b
    for i in range(len(a["anos"])):
        assert a["p5"][i] <= a["p25"][i] <= a["mediana"][i] <= a["p75"][i] <= a["p95"][i]
    assert a["apostas"][0] == 0 and a["apostas"][-1] == 260
    assert a["p5"][0] == a["p95"][0] == 0


def test_faixa_estreita_em_relacao_ao_total_com_mais_apostas():
    # Lei dos grandes números: a faixa cresce mais devagar do que o total apostado.
    curto = simular(Cenario(10, 1, "semana", 1, 1.9, 0.5))
    longo = simular(Cenario(10, 1, "semana", 20, 1.9, 0.5))
    largura = lambda s: (s["trajetorias"]["final"]["p95"] - s["trajetorias"]["final"]["p5"]) / s["total_em_risco"]
    assert largura(longo) < largura(curto) / 3
    assert longo["trajetorias"]["final"]["prob_prejuizo"] > curto["trajetorias"]["final"]["prob_prejuizo"]


def test_sensibilidade_inclui_hipotese_e_ponto_de_empate():
    linhas = simular(CASO_IV)["sensibilidade"]
    informada = [l for l in linhas if l["informada"]]
    empate = [l for l in linhas if l["empate"]]
    assert len(informada) == 1 and informada[0]["ve_total"] == pytest.approx(-1300)
    assert len(empate) == 1 and empate[0]["probabilidade"] == pytest.approx(1 / 1.8)
    assert empate[0]["ve_total"] == 0
    ves = [l["ve_total"] for l in linhas]
    assert ves == sorted(ves)  # mais chance suposta, resultado médio maior


def test_custo_de_oportunidade_do_conteudo_iv():
    s = simular(CASO_IV)
    assert s["valor_final_investimento"] == pytest.approx(15_843.73, abs=0.01)
    assert s["sobra_media_apostando"] == pytest.approx(11_700)
    assert s["custo_oportunidade"] == pytest.approx(4_143.73, abs=0.01)
    assert s["investimento"]["guardado"][-1] == pytest.approx(s["valor_final_investimento"])
    assert s["tabela_anual"][-1]["guardado"] == pytest.approx(s["valor_final_investimento"])


def test_investimento_sem_juros_e_a_soma_dos_aportes():
    assert valor_final_investimento(Cenario(20, 2, "dia", 1, taxa_anual=0.0)) == pytest.approx(20 * 2 * 365)


def test_sem_odd_nao_ha_faixa_nem_valor_esperado():
    s = simular(Cenario(20, 1, "dia", 1))
    assert s["total_em_risco"] == pytest.approx(7300)
    assert "trajetorias" not in s and "ve_total" not in s


def test_margem_da_casa():
    m = margem_da_casa([2.10, 3.40, 3.60])
    assert m["margem"] == pytest.approx(0.0481, abs=1e-4)
    assert sum(m["sem_margem"]) == pytest.approx(1)
    assert margem_da_casa([2.0])["erros"]
    assert margem_da_casa([2.0, 0.9])["erros"]


def test_aposta_unica():
    a = aposta_unica(10, 2.5, 0.4)
    assert a["retorno"] == 25 and a["lucro"] == 15
    assert a["ve"] == pytest.approx(0)


def test_cenario_grande_e_rapido():
    s = simular(Cenario(20, 5, "dia", 10, 1.9, 0.5, 0.1))
    assert s["numero_de_apostas"] == 18_250
    assert s["trajetorias"]["final"]["media"] == pytest.approx(s["ve_total"], rel=0.02)
