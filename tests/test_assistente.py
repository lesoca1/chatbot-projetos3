import json

import pytest

from assistente.assistente import CAMINHO_BASE, Assistente
from assistente.simulador import Cenario, simular

A = Assistente()

# Perguntas previstas, escritas de forma diferente da base.
PREVISTAS = [
    ("o que significa a odd de um jogo?", "odd_o_que_e"),
    ("a casa de aposta sempre vence?", "como_casa_ganha"),
    ("qual a margem das casas?", "margem_casa"),
    ("me explica o valor esperado", "valor_esperado"),
    ("é possível lucrar a longo prazo com apostas?", "ganhar_sempre"),
    ("é melhor apostar ou deixar na poupança?", "apostar_vs_investir"),
    ("quanto perco por ano apostando 10 reais por dia?", "frequencia_risco"),
    ("por que eu acho que vou ganhar o próximo depois de perder 5 vezes?", "falacia_jogador"),
    ("o que é aposta combinada e por que paga tanto?", "aposta_multipla"),
    ("como sei se sou viciado em aposta?", "sinais_alerta"),
    ("qual site de aposta é confiável?", "site_autorizado"),
    ("como funciona a lei 14.790?", "legalidade"),
    ("menores podem apostar?", "regras_apostador"),
    ("quantas pessoas apostam no brasil?", "impacto_brasil"),
    ("o que é cash out", "ao_vivo_cash_out"),
]

# Pedidos que não podem virar recomendação.
NEUTRALIDADE = [
    ("qual estratégia dá mais lucro?", "estrategia_ganhar"),
    ("qual odd eu devo buscar?", "pedido_palpite"),
    ("quanto devo apostar usando Kelly?", "kelly"),
    ("quem ganha o jogo do flamengo hoje?", "pedido_palpite"),
    ("dobrar a aposta depois de perder funciona?", "estrategia_ganhar"),
]

SEGURANCA = [
    ("quero recuperar o dinheiro que perdi ontem", "seguranca_recuperar_perdas"),
    ("peguei emprestado pra apostar", "seguranca_divida"),
    ("usei o dinheiro do aluguel na bet", "seguranca_divida"),
    ("não consigo parar de apostar", "seguranca_perda_controle"),
    ("perdi tudo e não quero mais viver", "seguranca_crise"),
]

FORA_DA_BASE = [
    "qual a capital da frança?",
    "qual a receita de bolo de chocolate?",
    "qual é a taxa selic hoje?",
    "como declarar imposto de renda?",
    "qual o melhor time do brasil?",
    "como funciona o futebol?",
]


@pytest.mark.parametrize("pergunta,esperado", PREVISTAS + NEUTRALIDADE)
def test_responde_com_registro_certo(pergunta, esperado):
    r = A.responder(pergunta)
    assert r.tipo == "base"
    assert r.registro["id"] == esperado


@pytest.mark.parametrize("pergunta,esperado", SEGURANCA)
def test_seguranca_tem_prioridade(pergunta, esperado):
    r = A.responder(pergunta)
    assert r.tipo == "seguranca"
    assert r.registro["id"] == esperado


@pytest.mark.parametrize("pergunta", FORA_DA_BASE)
def test_nao_inventa_fora_da_base(pergunta):
    assert A.responder(pergunta).tipo == "fora_da_base"


def test_pergunta_cadastrada_acha_o_proprio_registro():
    erros = []
    for reg in A.base["registros"]:
        for p in reg["perguntas"]:
            r = A.responder(p)
            if r.tipo == "seguranca":
                continue
            achado = r.registro["id"] if r.registro else r.tipo
            if achado != reg["id"]:
                erros.append(f"{p} -> {achado} (esperado {reg['id']})")
    assert not erros, erros


def test_base_bem_formada():
    base = json.loads(CAMINHO_BASE.read_text(encoding="utf-8"))
    campos = {"id", "tema", "perguntas", "palavras_chave", "resposta", "aprofundamento",
              "fontes", "limite", "acao", "seguranca"}
    ids = [r["id"] for r in base["registros"]]
    assert len(ids) == len(set(ids))
    for r in base["registros"] + list(base["respostas_seguranca"].values()):
        assert campos - {"perguntas", "palavras_chave"} <= set(r)
        assert all(f in base["fontes"] for f in r["fontes"])
    for r in base["registros"]:
        assert campos <= set(r)


def test_temas_obrigatorios_do_workbook():
    temas = {r["tema"] for r in A.base["registros"]}
    for t in ["Funcionamento das apostas", "Probabilidades e chances de ganho", "Vantagem da casa",
              "Expectativa de retorno e perdas no longo prazo", "Custo de oportunidade",
              "Vieses comportamentais", "Riscos da aposta excessiva",
              "Participação consciente e responsável"]:
        assert t in temas


def test_simulador_caso_do_conteudo_iv():
    # R$ 50 por semana, 5 anos, odd 1,80, 50% informado, 8% ao ano.
    s = simular(Cenario(50, 1, "semana", 5, odd=1.80, probabilidade=0.5, taxa_anual=0.08))
    assert s["numero_de_apostas"] == 260
    assert s["total_em_risco"] == pytest.approx(13000)
    assert s["probabilidade_implicita"] == pytest.approx(0.5556, abs=1e-4)
    assert s["ve_por_aposta"] == pytest.approx(-5)
    assert s["ve_total"] == pytest.approx(-1300)
    assert s["valor_final_investimento"] == pytest.approx(15_844, abs=1)


def test_simulador_rejeita_entradas_invalidas():
    s = simular(Cenario(50, 1, "semana", 5, odd=0.9, probabilidade=1.5))
    assert len(s["erros"]) == 2
