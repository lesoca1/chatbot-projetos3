"""Interface do assistente sobre apostas esportivas (Streamlit).

Executar: streamlit run app.py
"""

import streamlit as st

from assistente.assistente import Assistente
from assistente.simulador import Cenario, simular

st.set_page_config(page_title="Assistente sobre apostas", layout="centered")


@st.cache_resource
def carregar() -> Assistente:
    return Assistente()


def reais(v: float) -> str:
    texto = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("− " if v < 0 else "") + "R$ " + texto


assistente = carregar()

with st.sidebar:
    st.header("Sobre")
    st.write(
        "Assistente educativo sobre apostas esportivas. Responde apenas com a base de "
        "conhecimento do grupo, sem consultar a internet. Não dá palpites nem recomenda apostas."
    )
    st.caption(f"Base revisada em {assistente.data_revisao}.")
    st.subheader("Temas")
    for tema, perguntas in assistente.temas().items():
        with st.expander(tema):
            for p in perguntas:
                st.write(f"• {p}")
    st.divider()
    st.caption(
        "Precisa de ajuda? CVV: 188 (gratuito, 24 horas). CAPS do SUS na sua cidade. "
        "Em emergência, ligue 192."
    )

st.title("Assistente sobre apostas esportivas")
aba_chat, aba_sim = st.tabs(["Assistente", "Simulador (prévia)"])


def md(texto: str) -> str:
    """Escapa o cifrão para o Streamlit não tratar "R$ ... R$" como fórmula."""
    return texto.replace("$", "\\$")


def mostrar_resposta(r):
    if r.tipo == "seguranca":
        st.warning(md(r.texto))
    else:
        st.write(md(r.texto))
    if r.registro:
        with st.expander("Quer entender melhor?"):
            st.write(md(r.registro["aprofundamento"]))
            st.markdown("**Limite desta resposta:** " + md(r.registro["limite"]))
            st.markdown("**Fontes:**")
            for f in r.fontes:
                st.caption(f)
            st.caption(f"Base revisada em {assistente.data_revisao}.")
        if r.registro.get("acao") == "oferecer_simulador":
            st.info("Você pode testar esse efeito com os seus números na aba Simulador.")
        elif r.registro.get("acao") == "redirecionar_fonte_oficial":
            st.info("Regras mudam com o tempo. Confira a versão atual no site da Secretaria de Prêmios e Apostas (gov.br/fazenda).")
    if r.sugestoes:
        st.write("Talvez você queira saber:")
        for s in r.sugestoes:
            st.write(md(f"• {s}"))


with aba_chat:
    if "historico" not in st.session_state:
        st.session_state.historico = []

    if not st.session_state.historico:
        st.write("Faça uma pergunta sobre apostas esportivas. Alguns exemplos:")
        cols = st.columns(2)
        exemplos = ["O que é odd?", "Vale a pena apostar?", "O que é margem da casa?",
                    "Como saber se estou viciado em bets?"]
        for i, ex in enumerate(exemplos):
            if cols[i % 2].button(ex, use_container_width=True):
                st.session_state.pendente = ex

    for papel, conteudo in st.session_state.historico:
        with st.chat_message(papel):
            if papel == "user":
                st.write(md(conteudo))
            else:
                mostrar_resposta(conteudo)

    pergunta = st.chat_input("Escreva sua pergunta")
    pergunta = pergunta or st.session_state.pop("pendente", None)
    if pergunta:
        resposta = assistente.responder(pergunta)
        st.session_state.historico.append(("user", pergunta))
        st.session_state.historico.append(("assistant", resposta))
        st.rerun()

with aba_sim:
    st.write(
        "Prévia do simulador. Mostra quanto dinheiro passa pelas apostas, o resultado médio "
        "esperado nas hipóteses que você informar e a comparação com guardar o mesmo valor. "
        "Não prevê jogos e não recomenda apostas nem investimentos."
    )
    c1, c2 = st.columns(2)
    valor = c1.number_input("Valor médio por aposta (R$)", min_value=1.0, value=50.0, step=5.0)
    freq = c2.number_input("Apostas por período", min_value=1, value=1, step=1)
    periodo = c1.selectbox("Período", ["semana", "dia", "mes"],
                           format_func=lambda p: {"dia": "por dia", "semana": "por semana", "mes": "por mês"}[p])
    anos = c2.number_input("Duração (anos)", min_value=0.25, value=5.0, step=0.5)
    usar_ve = st.checkbox("Calcular valor esperado (informar odd e probabilidade)", value=True)
    odd = prob = None
    if usar_ve:
        c3, c4 = st.columns(2)
        odd = c3.number_input("Odd decimal média", min_value=1.01, value=1.80, step=0.05)
        prob = c4.slider("Sua hipótese de chance de acerto (%)", 1, 99, 50) / 100
    usar_inv = st.checkbox("Comparar com guardar o dinheiro", value=True)
    taxa = None
    if usar_inv:
        taxa = st.number_input("Taxa anual hipotética (%)", min_value=0.0, value=8.0, step=0.5) / 100

    s = simular(Cenario(valor, freq, periodo, anos, odd, prob, taxa))
    if s["erros"]:
        for e in s["erros"]:
            st.error(e)
    else:
        m1, m2 = st.columns(2)
        m1.metric("Número de apostas", f"{s['numero_de_apostas']:,}".replace(",", "."))
        m2.metric("Total colocado em risco", reais(s["total_em_risco"]))
        if "ve_total" in s:
            m3, m4 = st.columns(2)
            m3.metric("Resultado médio esperado", reais(s["ve_total"]))
            m4.metric("Chance sugerida pela odd", f"{s['probabilidade_implicita']:.1%}".replace(".", ","))
            if s["ve_total"] > 0:
                st.warning("Com a chance que você informou, a conta dá positiva. Isso é só um cenário: "
                           "a sua hipótese pode estar errada e não é uma previsão.")
        if "valor_final_investimento" in s:
            st.metric("Valor final se o dinheiro fosse guardado", reais(s["valor_final_investimento"]))
        st.caption("A chance de acerto é uma hipótese sua, não uma previsão. A taxa é ilustrativa. "
                   "Faixa de resultados e gráfico entram na próxima versão.")
