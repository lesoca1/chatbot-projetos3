"""Interface do assistente sobre apostas esportivas (Streamlit).

Executar: streamlit run app.py
"""

import altair as alt
import pandas as pd
import streamlit as st

from assistente.assistente import Assistente
from assistente.explicacao import descrever_cenario, explicar
from assistente.formato import numero, pct, reais
from assistente.simulador import Cenario, margem_da_casa, simular

st.set_page_config(page_title="Assistente sobre apostas", layout="centered")

AZUL, LARANJA, CINZA, TINTA = "#2a78d6", "#eb6834", "#8a8984", "#52514e"
EIXO_ANOS = alt.Axis(tickCount=6, format="~g", labelExpr="replace(datum.label, '.', ',')")
EIXO_REAIS = "'R$ ' + replace(format(datum.value, ',.0f'), regexp(',', 'g'), '.')"
PADRAO_SIM = {"sim_valor": 50.0, "sim_freq": 1, "sim_periodo": "semana", "sim_anos": 5.0,
              "sim_usar_ve": True, "sim_odd": 1.80, "sim_prob": 50, "sim_usar_inv": True, "sim_taxa": 8.0}


@st.cache_resource
def carregar() -> Assistente:
    return Assistente()


def md(texto: str) -> str:
    """Escapa o cifrão para o Streamlit não tratar "R$ ... R$" como fórmula."""
    return texto.replace("$", "\\$")


assistente = carregar()
for chave, valor in PADRAO_SIM.items():
    st.session_state.setdefault(chave, valor)
st.session_state.setdefault("pagina", "Assistente")
st.session_state.setdefault("historico", [])
st.session_state.setdefault("ultimo_cenario", None)


def preencher_simulador(c: Cenario):
    """Leva o cenário da conversa para o simulador e troca de página."""
    st.session_state.update({
        "sim_valor": float(c.valor_por_aposta), "sim_freq": max(1, int(round(c.apostas_por_periodo))),
        "sim_periodo": c.periodicidade, "sim_anos": float(max(0.25, c.anos)),
        "sim_usar_ve": c.odd is not None and c.probabilidade is not None,
        "sim_usar_inv": c.taxa_anual is not None, "pagina": "Simulador",
    })
    if c.odd is not None:
        st.session_state.sim_odd = float(max(1.01, c.odd))
    if c.probabilidade is not None:
        st.session_state.sim_prob = int(min(99, max(1, round(c.probabilidade * 100))))
    if c.taxa_anual is not None:
        st.session_state.sim_taxa = float(c.taxa_anual * 100)


def perguntar(texto: str):
    st.session_state.pendente = texto
    st.session_state.pagina = "Assistente"


# ---------- Gráficos e tabelas do simulador ----------

def grafico_resultado(s: dict, altura: int = 380):
    t = s["trajetorias"]
    df = pd.DataFrame({
        "ano": t["anos"], "p5": t["p5"], "p95": t["p95"], "Mediana das simulações": t["mediana"],
        "Resultado médio esperado": [s["ve_por_aposta"] * a for a in t["apostas"]],
    })
    base = alt.Chart(df).encode(x=alt.X("ano:Q", title="Anos", axis=EIXO_ANOS))
    faixa = base.mark_area(opacity=0.18, color=AZUL).encode(
        y=alt.Y("p5:Q", title=None, axis=alt.Axis(labelExpr=EIXO_REAIS)), y2="p95:Q")
    longo = df.melt("ano", ["Mediana das simulações", "Resultado médio esperado"], var_name="Série", value_name="v")
    cores = alt.Scale(domain=["Mediana das simulações", "Resultado médio esperado"], range=[AZUL, TINTA])
    linhas = alt.Chart(longo).mark_line(strokeWidth=2).encode(
        x="ano:Q", y="v:Q", color=alt.Color("Série:N", scale=cores, legend=alt.Legend(orient="bottom", title=None)),
        strokeDash=alt.StrokeDash("Série:N", scale=alt.Scale(domain=list(cores.domain), range=[[1, 0], [5, 4]]),
                                  legend=None))
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=CINZA, strokeWidth=1).encode(y="y:Q")
    perto = alt.selection_point(nearest=True, on="pointerover", fields=["ano"], empty=False)
    alvo = base.mark_rule(color=CINZA).encode(
        opacity=alt.condition(perto, alt.value(0.6), alt.value(0)),
        tooltip=[alt.Tooltip("ano:Q", title="Ano", format=".1f"),
                 alt.Tooltip("Resultado médio esperado:Q", format=",.0f"),
                 alt.Tooltip("Mediana das simulações:Q", format=",.0f"),
                 alt.Tooltip("p5:Q", title="Faixa de 90%: de", format=",.0f"),
                 alt.Tooltip("p95:Q", title="até", format=",.0f")]).add_params(perto)
    st.altair_chart((faixa + zero + linhas + alvo).properties(height=altura), use_container_width=True)
    st.caption("Área azul: faixa em que ficaram 90% das 10.000 simulações. Uma simulação isolada não é "
               "previsão do que vai acontecer com você.")


def grafico_comparacao(s: dict, altura: int = 340):
    inv = s["investimento"]
    dados = {"ano": s["marcos_anos"], "Guardado com rendimento": inv["guardado"],
             "Separado, sem rendimento": inv["separado"]}
    if "trajetorias" in s:
        dados["Apostando (média)"] = [sep + s["ve_por_aposta"] * a
                                      for sep, a in zip(inv["separado"], s["trajetorias"]["apostas"])]
    df = pd.DataFrame(dados).melt("ano", var_name="Cenário", value_name="v")
    dominio = [k for k in ["Guardado com rendimento", "Apostando (média)", "Separado, sem rendimento"] if k in dados]
    cores = {"Guardado com rendimento": AZUL, "Apostando (média)": LARANJA, "Separado, sem rendimento": CINZA}
    graf = alt.Chart(df).mark_line(strokeWidth=2).encode(
        x=alt.X("ano:Q", title="Anos", axis=EIXO_ANOS),
        y=alt.Y("v:Q", title=None, axis=alt.Axis(labelExpr=EIXO_REAIS)),
        color=alt.Color("Cenário:N", scale=alt.Scale(domain=dominio, range=[cores[k] for k in dominio]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=[alt.Tooltip("ano:Q", title="Ano", format=".1f"), "Cenário:N",
                 alt.Tooltip("v:Q", title="Valor (R$)", format=",.0f")])
    st.altair_chart(graf.properties(height=altura), use_container_width=True)


def tabela_anual(s: dict):
    linhas = []
    for l in s["tabela_anual"]:
        linha = {"Ano": numero(l["ano"], 0 if float(l["ano"]).is_integer() else 1),
                 "Apostas": numero(l["apostas"]), "Total em risco": reais(l["em_risco"], 0)}
        if "ve" in l:
            linha["Resultado médio"] = reais(l["ve"], 0)
        if "guardado" in l:
            linha["Se guardado"] = reais(l["guardado"], 0)
        linhas.append(linha)
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)


def tabela_sensibilidade(s: dict):
    linhas = []
    for l in s["sensibilidade"]:
        rotulo = pct(l["probabilidade"])
        if l["informada"]:
            rotulo += " (sua hipótese)"
        elif l["empate"]:
            rotulo += " (ponto de empate)"
        linhas.append({"Chance de acerto": rotulo, "Resultado médio": reais(l["ve_total"], 0),
                       "Chance de terminar no prejuízo": pct(l["prob_prejuizo"]) if l["prob_prejuizo"] is not None else "-"})
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
    st.caption("Ponto de empate: a chance em que o resultado médio seria zero (1 dividido pela odd). "
               "Abaixo dele, cada aposta perde em média.")


def entender_melhor_simulador(c: Cenario, s: dict):
    with st.expander("Quer entender melhor? Contas, hipóteses e fontes"):
        st.markdown(md(
            "**Contas**\n"
            "- Número de apostas = apostas por período × períodos no prazo.\n"
            "- Total colocado em risco = valor por aposta × número de apostas.\n"
            "- Probabilidade implícita = 1 ÷ odd.\n"
            "- Valor esperado por aposta = valor × (chance suposta × odd − 1). O total é esse valor × número de apostas.\n"
            "- Faixa de resultados: 10.000 sequências sorteadas de vitórias e derrotas (método de Monte Carlo), "
            "com semente fixa. A faixa vai do percentil 5 ao 95.\n"
            "- Chance de terminar no prejuízo (tabela de sensibilidade): conta exata pela distribuição binomial.\n"
            "- Investimento: o valor apostado em cada período vira um depósito; a taxa anual vira taxa do "
            "período por (1 + taxa)^(1 / períodos por ano) − 1.\n\n"
            "**Hipóteses**\n"
            "- Valor, frequência, odd e chance constantes. Apostas independentes entre si.\n"
            "- Valor fixo: nada de dobrar a aposta depois de perder.\n"
            "- A chance de acerto é uma hipótese sua, não uma previsão. A taxa é ilustrativa.\n"
            "- Impostos, bônus, cash out e mudança de odds ao vivo ficam fora."))
        st.caption("Fontes: " + " ".join(assistente.citar(["BUSSAB", "MONTECARLO1949", "ASSAF"])))


def mostrar_simulacao(c: Cenario, s: dict, chave: str, na_conversa: bool):
    if s["erros"]:
        for e in s["erros"]:
            st.error(e)
        return
    st.caption(md("Cenário: " + descrever_cenario(c)))
    m1, m2, m3 = st.columns(3)
    m1.metric("Apostas", numero(s["numero_de_apostas"]))
    m2.metric("Total em risco", reais(s["total_em_risco"], 0))
    if "ve_total" in s:
        m3.metric("Resultado médio esperado", reais(s["ve_total"], 0))
    elif "valor_final_investimento" in s:
        m3.metric("Se guardado", reais(s["valor_final_investimento"], 0))
    if "trajetorias" in s:
        f = s["trajetorias"]["final"]
        m4, m5, m6 = st.columns(3)
        m4.metric("Faixa de 90%: de", reais(f["p5"], 0))
        m5.metric("até", reais(f["p95"], 0))
        m6.metric("Terminam no prejuízo", pct(f["prob_prejuizo"]))
        if s["ve_total"] > 0:
            st.warning("Com a chance que você informou, a conta dá positiva. Isso é só um cenário: a sua "
                       "hipótese pode estar errada e não é uma previsão.")
    if "custo_oportunidade" in s:
        m7, m8, m9 = st.columns(3)
        m7.metric("Se guardado", reais(s["valor_final_investimento"], 0))
        m8.metric("Apostando, sobra em média", reais(s["sobra_media_apostando"], 0))
        m9.metric("Custo de oportunidade", reais(s["custo_oportunidade"], 0))

    if na_conversa:
        if "trajetorias" in s:
            grafico_resultado(s, altura=300)
        st.button("Abrir no simulador com esses números", key=f"abrir_{chave}",
                  on_click=preencher_simulador, args=(c,), type="primary")
        return

    if "trajetorias" in s:
        st.subheader("Resultado acumulado das apostas")
        grafico_resultado(s)
    if "valor_final_investimento" in s:
        st.subheader("Apostar ou guardar o mesmo dinheiro")
        grafico_comparacao(s)
    st.subheader("Ano a ano")
    tabela_anual(s)
    if "sensibilidade" in s:
        st.subheader("E se a sua hipótese de chance estiver errada?")
        tabela_sensibilidade(s)
    entender_melhor_simulador(c, s)


# ---------- Conversa ----------

def mostrar_resposta(r, i: int):
    if r.tipo == "seguranca":
        st.warning(md(r.texto))
    else:
        st.write(md(r.texto))
    if r.calculo:
        st.info(md("\n\n".join(r.calculo)))
    if r.simulacao is not None:
        mostrar_simulacao(r.cenario, r.simulacao, f"msg{i}", na_conversa=True)
    if r.registro:
        with st.expander("Quer entender melhor?"):
            st.write(md(r.registro["aprofundamento"]))
            st.markdown("**Limite desta resposta:** " + md(r.registro["limite"]))
            st.markdown("**Fontes:**")
            for f in r.fontes:
                st.caption(f)
            st.caption(f"Base revisada em {assistente.data_revisao}.")
        if r.registro.get("acao") == "oferecer_simulador" and r.simulacao is None:
            st.info("Você pode testar esse efeito com os seus números. Escreva o cenário aqui, por exemplo "
                    "\"aposto R$ 20 por dia há 1 ano, odd 1,90, 50% de chance\", ou abra o simulador.")
            st.button("Abrir o simulador", key=f"sim_{i}", on_click=lambda: st.session_state.update(pagina="Simulador"))
        elif r.registro.get("acao") == "redirecionar_fonte_oficial":
            st.info("Regras mudam com o tempo. Confira a versão atual no site da Secretaria de Prêmios e "
                    "Apostas (gov.br/fazenda).")
    if r.sugestoes:
        st.write("Talvez você queira saber:")
        for j, s in enumerate(r.sugestoes):
            st.button(s, key=f"sug_{i}_{j}", on_click=perguntar, args=(s,))


with st.sidebar:
    st.header("Sobre")
    st.write(
        "Assistente educativo sobre apostas esportivas. Responde apenas com a base de "
        "conhecimento do grupo, sem consultar a internet. Não dá palpites nem recomenda apostas."
    )
    st.caption(f"Base revisada em {assistente.data_revisao}. {len(assistente.base['registros'])} temas de "
               f"pergunta.")
    st.subheader("Temas")
    for tema, perguntas in assistente.temas().items():
        with st.expander(tema):
            for j, p in enumerate(perguntas):
                st.button(p, key=f"tema_{tema}_{j}", on_click=perguntar, args=(p,), type="tertiary")
    sem_resposta = [p for p, r in zip(st.session_state.historico[::2], st.session_state.historico[1::2])
                    if r[1].tipo == "fora_da_base"]
    if sem_resposta:
        with st.expander(f"Perguntas sem resposta nesta conversa ({len(sem_resposta)})"):
            for _, p in sem_resposta:
                st.write(md(f"• {p}"))
            st.download_button("Baixar lista", "\n".join(p for _, p in sem_resposta).encode("utf-8"),
                               "perguntas_sem_resposta.txt")
            st.caption("O grupo usa esta lista para ampliar a base.")
    st.divider()
    st.caption(
        "Precisa de ajuda? CVV: 188 (gratuito, 24 horas). CAPS do SUS na sua cidade. "
        "Em emergência, ligue 192."
    )

st.title("Assistente sobre apostas esportivas")
pagina = st.segmented_control("Página", ["Assistente", "Simulador"], key="pagina",
                              label_visibility="collapsed") or "Assistente"

if pagina == "Assistente":
    if not st.session_state.historico:
        st.write("Faça uma pergunta sobre apostas esportivas ou descreva como você aposta. Alguns exemplos:")
        cols = st.columns(2)
        exemplos = ["O que é odd?", "Vale a pena apostar?", "O que é handicap?",
                    "Como saber se estou viciado em bets?",
                    "Aposto R$ 50 por semana há 5 anos, odd 1,80, 50% de chance, 8% ao ano"]
        for i, ex in enumerate(exemplos):
            cols[i % 2].button(md(ex), key=f"ex_{i}", on_click=perguntar, args=(ex,), use_container_width=True)

    for i, (papel, conteudo) in enumerate(st.session_state.historico):
        with st.chat_message(papel):
            if papel == "user":
                st.write(md(conteudo))
            else:
                mostrar_resposta(conteudo, i)

    pergunta = st.chat_input("Escreva sua pergunta ou o seu cenário de apostas")
    pergunta = pergunta or st.session_state.pop("pendente", None)
    if pergunta:
        resposta = assistente.responder(pergunta, st.session_state.ultimo_cenario)
        if resposta.tipo == "seguranca":
            st.session_state.ultimo_cenario = None  # sinal de risco encerra o cenário em curso
        elif resposta.cenario is not None:
            st.session_state.ultimo_cenario = resposta.cenario
        st.session_state.historico.append(("user", pergunta))
        st.session_state.historico.append(("assistant", resposta))
        st.rerun()

else:
    st.write(
        "Mostra quanto dinheiro passa pelas apostas, o resultado médio esperado nas hipóteses que você "
        "informar, a faixa de resultados possíveis e a comparação com guardar o mesmo valor. "
        "Não prevê jogos e não recomenda apostas nem investimentos."
    )
    c1, c2 = st.columns(2)
    valor = c1.number_input("Valor médio por aposta (R$)", min_value=1.0, step=5.0, key="sim_valor")
    freq = c2.number_input("Apostas por período", min_value=1, step=1, key="sim_freq")
    periodo = c1.selectbox("Período", ["semana", "dia", "mes"], key="sim_periodo",
                           format_func=lambda p: {"dia": "por dia", "semana": "por semana", "mes": "por mês"}[p])
    anos = c2.number_input("Duração (anos)", min_value=0.25, max_value=50.0, step=0.5, key="sim_anos")
    usar_ve = st.checkbox("Calcular resultado esperado e faixa de resultados (informar odd e chance)", key="sim_usar_ve")
    odd = prob = None
    if usar_ve:
        c3, c4 = st.columns(2)
        odd = c3.number_input("Odd decimal média", min_value=1.01, step=0.05, key="sim_odd")
        prob = c4.slider("Sua hipótese de chance de acerto (%)", 1, 99, key="sim_prob") / 100
        st.caption(md(f"A odd {numero(odd, 2)} sugere {pct(1 / odd)} de chance. Abaixo disso, cada aposta perde "
                      "em média."))
    usar_inv = st.checkbox("Comparar com guardar o dinheiro", key="sim_usar_inv")
    taxa = None
    if usar_inv:
        taxa = st.number_input("Taxa anual hipotética (%)", min_value=0.0, max_value=100.0, step=0.5,
                               key="sim_taxa") / 100

    c = Cenario(valor, freq, periodo, anos, odd, prob, taxa)
    s = simular(c)
    if not s["erros"]:
        st.info(md("\n\n".join(explicar(c, s))))
    mostrar_simulacao(c, s, "pagina", na_conversa=False)

    with st.expander("Calcular a margem da casa em um jogo"):
        st.write("Informe as odds de todos os resultados possíveis do mesmo mercado, separadas por espaço. "
                 "Exemplo para vitória, empate e derrota: 2,10 3,40 3,60.")
        texto_odds = st.text_input("Odds", "2,10 3,40 3,60", key="sim_margem")
        try:
            odds = [float(x.replace(",", ".")) for x in texto_odds.replace(";", " ").split()]
            m = margem_da_casa(odds)
        except ValueError:
            m = {"erros": ["Use apenas números, como 2,10 3,40 3,60."]}
        if m["erros"]:
            for e in m["erros"]:
                st.error(e)
        else:
            st.metric("Margem da casa", pct(m["margem"]))
            st.dataframe(pd.DataFrame({
                "Odd": [numero(o, 2) for o in odds],
                "Probabilidade implícita": [pct(p) for p in m["implicitas"]],
                "Sem a margem": [pct(p) for p in m["sem_margem"]]}), hide_index=True, use_container_width=True)
            st.caption(f"As probabilidades implícitas somam {pct(m['soma'])}. O que passa de 100% é a margem.")

    st.caption("A chance de acerto é uma hipótese sua, não uma previsão. A taxa é ilustrativa e não é "
               "recomendação de investimento.")
