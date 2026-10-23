"""Interface do assistente sobre apostas esportivas (Streamlit).

Executar: streamlit run app.py
"""

import csv
import io

import altair as alt
import pandas as pd
import streamlit as st

from assistente.assistente import Assistente
from assistente.explicacao import acertos_para_empatar, descrever_cenario, dinheiro, em_100, explicar, resumir
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

def grafico_dinheiro(s: dict, altura: int = 220):
    """Três barras: o que passou pelas apostas, o que volta em média e o que teria guardado."""
    barras = [("Você apostou", s["total_em_risco"], CINZA)]
    if "ve_total" in s:
        barras.append(("Volta para você, em média", s["total_em_risco"] + s["ve_total"], LARANJA))
    if "valor_final_investimento" in s:
        barras.append(("Se tivesse guardado", s["valor_final_investimento"], AZUL))
    if len(barras) == 1:
        return
    df = pd.DataFrame({"Item": [b[0] for b in barras], "v": [b[1] for b in barras],
                       "rotulo": [dinheiro(b[1]) for b in barras]})
    cores = alt.Scale(domain=[b[0] for b in barras], range=[b[2] for b in barras])
    base = alt.Chart(df).encode(
        y=alt.Y("Item:N", sort=None, title=None, axis=alt.Axis(labelLimit=220, labelFontSize=13)),
        x=alt.X("v:Q", title=None, axis=None))
    graf = base.mark_bar(height=28).encode(color=alt.Color("Item:N", scale=cores, legend=None)) + \
        base.mark_text(align="left", dx=6, fontSize=14, color=TINTA).encode(text="rotulo:N")
    st.altair_chart(graf.properties(height=altura - 40 * (3 - len(barras))), use_container_width=True)


def grafico_resultado(s: dict, altura: int = 360):
    t = s["trajetorias"]
    df = pd.DataFrame({
        "ano": t["anos"], "p5": t["p5"], "p95": t["p95"], "Resultado do meio": t["mediana"],
        "Média": [s["ve_por_aposta"] * a for a in t["apostas"]],
    })
    base = alt.Chart(df).encode(x=alt.X("ano:Q", title="Anos", axis=EIXO_ANOS))
    faixa = base.mark_area(opacity=0.18, color=AZUL).encode(
        y=alt.Y("p5:Q", title=None, axis=alt.Axis(labelExpr=EIXO_REAIS)), y2="p95:Q")
    longo = df.melt("ano", ["Resultado do meio", "Média"], var_name="Série", value_name="v")
    cores = alt.Scale(domain=["Resultado do meio", "Média"], range=[AZUL, TINTA])
    linhas = alt.Chart(longo).mark_line(strokeWidth=2).encode(
        x="ano:Q", y="v:Q", color=alt.Color("Série:N", scale=cores, legend=alt.Legend(orient="bottom", title=None)),
        strokeDash=alt.StrokeDash("Série:N", scale=alt.Scale(domain=list(cores.domain), range=[[1, 0], [5, 4]]),
                                  legend=None))
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=CINZA, strokeWidth=1).encode(y="y:Q")
    perto = alt.selection_point(nearest=True, on="pointerover", fields=["ano"], empty=False)
    alvo = base.mark_rule(color=CINZA).encode(
        opacity=alt.condition(perto, alt.value(0.6), alt.value(0)),
        tooltip=[alt.Tooltip("ano:Q", title="Ano", format=".1f"),
                 alt.Tooltip("Média:Q", format=",.0f"),
                 alt.Tooltip("Resultado do meio:Q", format=",.0f"),
                 alt.Tooltip("p5:Q", title="9 de cada 10 ficaram entre", format=",.0f"),
                 alt.Tooltip("p95:Q", title="e", format=",.0f")]).add_params(perto)
    st.altair_chart((faixa + zero + linhas + alvo).properties(height=altura), use_container_width=True)
    st.caption("Como ler: a linha cinza do zero é \"não ganhar nem perder\". A área azul mostra onde "
               "ficaram 9 de cada 10 simulações. Quanto mais o tempo passa, mais tudo fica abaixo do zero.")


def grafico_comparacao(s: dict, altura: int = 320):
    inv = s["investimento"]
    dados = {"ano": s["marcos_anos"], "Guardado, com rendimento": inv["guardado"],
             "Guardado, sem rendimento": inv["separado"]}
    if "trajetorias" in s:
        dados["Apostando (média)"] = [sep + s["ve_por_aposta"] * a
                                      for sep, a in zip(inv["separado"], s["trajetorias"]["apostas"])]
    df = pd.DataFrame(dados).melt("ano", var_name="Cenário", value_name="v")
    dominio = [k for k in ["Guardado, com rendimento", "Apostando (média)", "Guardado, sem rendimento"] if k in dados]
    cores = {"Guardado, com rendimento": AZUL, "Apostando (média)": LARANJA, "Guardado, sem rendimento": CINZA}
    graf = alt.Chart(df).mark_line(strokeWidth=2).encode(
        x=alt.X("ano:Q", title="Anos", axis=EIXO_ANOS),
        y=alt.Y("v:Q", title=None, axis=alt.Axis(labelExpr=EIXO_REAIS)),
        color=alt.Color("Cenário:N", scale=alt.Scale(domain=dominio, range=[cores[k] for k in dominio]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=[alt.Tooltip("ano:Q", title="Ano", format=".1f"), "Cenário:N",
                 alt.Tooltip("v:Q", title="Valor (R$)", format=",.0f")])
    st.altair_chart(graf.properties(height=altura), use_container_width=True)
    st.caption("Como ler: a distância entre a linha azul e a laranja é o que você deixa de ter por apostar.")


def tabela_anual(s: dict):
    linhas = []
    for l in s["tabela_anual"]:
        linha = {"Ano": numero(l["ano"], 0 if float(l["ano"]).is_integer() else 1),
                 "Apostas": numero(l["apostas"]), "Total apostado": reais(l["em_risco"], 0)}
        if "ve" in l:
            linha["Perda média"] = reais(-l["ve"], 0) if l["ve"] < 0 else "nenhuma"
        if "guardado" in l:
            linha["Se tivesse guardado"] = reais(l["guardado"], 0)
        linhas.append(linha)
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)


def tabela_sensibilidade(s: dict, odd: float):
    linhas = []
    for l in s["sensibilidade"]:
        rotulo = em_100(l["probabilidade"], exato=l["informada"] or l["empate"])
        if l["informada"]:
            rotulo += " (o que você disse)"
        elif l["empate"]:
            rotulo += " (empate)"
        ve = l["ve_total"]
        linhas.append({"Se você acerta": rotulo,
                       "Resultado médio": "zero" if abs(ve) < 0.5 else (
                           f"perde {dinheiro(-ve)}" if ve < 0 else f"ganha {dinheiro(ve)}"),
                       "Terminam no prejuízo": em_100(l["prob_prejuizo"]) if l["prob_prejuizo"] is not None else "-"})
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
    st.caption(md(f"Com odd {numero(odd, 2)}, só deixa de perder quem acerta {acertos_para_empatar(odd)}. "
                  "Errar a sua estimativa por poucos pontos muda bastante o resultado."))


def como_as_contas_sao_feitas():
    st.markdown(md(
        "**Contas**\n"
        "- Número de apostas = apostas por período × períodos no prazo.\n"
        "- Total apostado = valor por aposta × número de apostas.\n"
        "- Chance que a odd sugere (probabilidade implícita) = 1 ÷ odd.\n"
        "- Resultado médio por aposta (valor esperado) = valor × (chance suposta × odd − 1).\n"
        "- Faixa de resultados: 10.000 sequências sorteadas de vitórias e derrotas (método de Monte Carlo), "
        "com semente fixa. A faixa vai do percentil 5 ao 95, ou seja, deixa de fora as 5% piores e as 5% "
        "melhores.\n"
        "- Chance de terminar no prejuízo na tabela \"E se...\": conta exata pela distribuição binomial.\n"
        "- Guardar o dinheiro: o valor apostado em cada período vira um depósito; a taxa anual vira taxa do "
        "período por (1 + taxa)^(1 / períodos por ano) − 1.\n\n"
        "**Suposições**\n"
        "- Valor, frequência, odd e chance não mudam. Uma aposta não afeta a outra.\n"
        "- Valor fixo: nada de dobrar a aposta depois de perder.\n"
        "- A chance de acerto é uma suposição sua, não uma previsão. A taxa é só um exemplo.\n"
        "- Impostos, bônus, cash out e odds ao vivo ficam de fora."))
    st.caption("Fontes: " + " ".join(assistente.citar(["BUSSAB", "MONTECARLO1949", "ASSAF"])))


def mostrar_simulacao(c: Cenario, s: dict, chave: str, na_conversa: bool):
    if s["erros"]:
        for e in s["erros"]:
            st.error(e)
        return
    if na_conversa:
        grafico_dinheiro(s)
        st.caption(md("Seus números: " + descrever_cenario(c)))
        st.button("Ver gráficos e detalhes no simulador", key=f"abrir_{chave}",
                  on_click=preencher_simulador, args=(c,), type="primary")
        return

    grafico_dinheiro(s)
    if s.get("ve_total", 0) > 0:
        st.warning("Com a chance que você informou, a conta dá positiva. Isso só vale se você acertar mesmo "
                   "tanto assim. Veja abaixo o que acontece se acertar um pouco menos.")
    st.write("Quer ir além? Abra os itens abaixo.")
    if "trajetorias" in s:
        with st.expander("Como o resultado muda com a sorte"):
            grafico_resultado(s)
    if "sensibilidade" in s:
        with st.expander("E se você acertar menos (ou mais) do que imagina?"):
            tabela_sensibilidade(s, c.odd)
    if "valor_final_investimento" in s:
        with st.expander("Apostar ou guardar, ao longo do tempo"):
            grafico_comparacao(s)
    with st.expander("Ano a ano"):
        tabela_anual(s)
    with st.expander("Como as contas são feitas"):
        como_as_contas_sao_feitas()


# ---------- Conversa ----------

def registrar_avaliacao(i: int):
    st.session_state.setdefault("avaliacoes", {})[i] = st.session_state.get(f"fb_{i}")


def mostrar_resposta(r, i: int):
    if r.resumo:
        st.markdown(f"**{md(r.resumo)}**")
    if r.tipo == "seguranca":
        st.warning(md(r.texto))
    else:
        st.write(md(r.texto))
    if r.termos:
        st.caption(md("Palavras desta resposta:  \n" + "  \n".join(f"**{t}:** {d}" for t, d in r.termos)))
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
            st.info("Quer ver isso com os seus números? Escreva como você aposta, por exemplo "
                    "\"aposto R$ 20 por dia, odd 1,90, acerto 50%\", ou abra o simulador.")
            st.button("Abrir o simulador", key=f"sim_{i}", on_click=lambda: st.session_state.update(pagina="Simulador"))
        elif r.registro.get("acao") == "redirecionar_fonte_oficial":
            st.info("Regras mudam com o tempo. Confira a versão atual no site da Secretaria de Prêmios e "
                    "Apostas (gov.br/fazenda).")
    if r.sugestoes:
        st.write("Talvez você queira saber:")
        for j, s in enumerate(r.sugestoes):
            st.button(s, key=f"sug_{i}_{j}", on_click=perguntar, args=(s,))
    st.feedback("thumbs", key=f"fb_{i}", on_change=registrar_avaliacao, args=(i,))


def registro_csv() -> bytes:
    """Conversa com a avaliação de cada resposta, para os testes com usuários."""
    saida = io.StringIO()
    w = csv.writer(saida)
    w.writerow(["pergunta", "tipo_de_resposta", "registro", "avaliacao"])
    avaliacoes = st.session_state.get("avaliacoes", {})
    hist = st.session_state.historico
    for k in range(0, len(hist) - 1, 2):
        r = hist[k + 1][1]
        nota = avaliacoes.get(k + 1)
        w.writerow([hist[k][1], r.tipo, r.registro["id"] if r.registro else "",
                    {1: "ajudou", 0: "não ajudou"}.get(nota, "")])
    return saida.getvalue().encode("utf-8")


with st.sidebar:
    st.header("Sobre")
    st.write(
        "Assistente educativo sobre apostas esportivas. Responde só com a base do grupo, sem consultar a "
        "internet. Não dá palpites nem recomenda apostas."
    )
    st.caption(f"Base revisada em {assistente.data_revisao}. {len(assistente.base['registros'])} temas de "
               f"pergunta.")
    st.subheader("Temas")
    for tema, perguntas in assistente.temas().items():
        with st.expander(tema):
            for j, p in enumerate(perguntas):
                st.button(p, key=f"tema_{tema}_{j}", on_click=perguntar, args=(p,), type="tertiary")
    with st.expander("Glossário: palavras das apostas"):
        for g in sorted(assistente.base["glossario"], key=lambda g: g["termo"].lower()):
            st.markdown(md(f"**{g['termo']}:** {g['definicao']}"))
    sem_resposta = [p for p, r in zip(st.session_state.historico[::2], st.session_state.historico[1::2])
                    if r[1].tipo == "fora_da_base"]
    if sem_resposta:
        with st.expander(f"Perguntas sem resposta nesta conversa ({len(sem_resposta)})"):
            for _, p in sem_resposta:
                st.write(md(f"• {p}"))
            st.caption("O grupo usa esta lista para ampliar a base.")
    if st.session_state.historico:
        st.download_button("Baixar registro da conversa", registro_csv(), "registro_conversa.csv",
                           help="Perguntas, respostas e avaliações. Usado nos testes com usuários.")
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
        st.write("Pergunte o que quiser sobre apostas, com as suas palavras. Ou conte como você aposta, e eu "
                 "mostro o que acontece com o seu dinheiro. Alguns exemplos:")
        cols = st.columns(2)
        exemplos = ["O que é odd?", "Dá para ganhar dinheiro com bet?", "O que é green e red?",
                    "Como sei se estou viciado?",
                    "Aposto R$ 50 por semana há 5 anos, odd 1,80, acerto 50%, 8% ao ano",
                    "Acerto mais da metade e mesmo assim perco, por quê?"]
        for i, ex in enumerate(exemplos):
            cols[i % 2].button(md(ex), key=f"ex_{i}", on_click=perguntar, args=(ex,), use_container_width=True)

    for i, (papel, conteudo) in enumerate(st.session_state.historico):
        with st.chat_message(papel):
            if papel == "user":
                st.write(md(conteudo))
            else:
                mostrar_resposta(conteudo, i)

    pergunta = st.chat_input("Escreva sua pergunta ou como você aposta")
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
    st.write("Conte como você aposta. O simulador mostra quanto dinheiro passa pelas apostas, quanto você "
             "perderia em média e quanto teria se guardasse o mesmo valor. Ele não prevê jogos.")
    c1, c2 = st.columns(2)
    valor = c1.number_input("Quanto você aposta por vez (R$)", min_value=1.0, step=5.0, key="sim_valor")
    freq = c2.number_input("Quantas vezes", min_value=1, step=1, key="sim_freq")
    periodo = c1.selectbox("Por", ["semana", "dia", "mes"], key="sim_periodo",
                           format_func=lambda p: {"dia": "dia", "semana": "semana", "mes": "mês"}[p])
    anos = c2.number_input("Durante quantos anos", min_value=0.25, max_value=50.0, step=0.5, key="sim_anos")
    usar_ve = st.checkbox("Calcular quanto eu perderia em média (precisa da odd e de quanto você acerta)",
                          key="sim_usar_ve")
    odd = prob = None
    if usar_ve:
        c3, c4 = st.columns(2)
        odd = c3.number_input("Odd média das suas apostas", min_value=1.01, step=0.05, key="sim_odd",
                              help="O número que a bet mostra ao lado de cada resultado, como 1,80.")
        prob = c4.slider("Em quantas de cada 100 apostas você acha que acerta?", 1, 99, key="sim_prob") / 100
        st.caption(md(f"Com odd {numero(odd, 2)}, só deixa de perder quem acerta {acertos_para_empatar(odd)}."))
    usar_inv = st.checkbox("Comparar com guardar o dinheiro", key="sim_usar_inv")
    taxa = None
    if usar_inv:
        taxa = st.number_input("Quanto o dinheiro guardado renderia por ano (%)", min_value=0.0, max_value=100.0,
                               step=0.5, key="sim_taxa",
                               help="Só um exemplo para comparar. Não é recomendação de investimento.") / 100

    c = Cenario(valor, freq, periodo, anos, odd, prob, taxa)
    s = simular(c)
    if not s["erros"]:
        st.markdown(f"**{md(resumir(c, s))}**")
        st.info(md("\n\n".join(explicar(c, s))))
    mostrar_simulacao(c, s, "pagina", na_conversa=False)

    with st.expander("Calcular a margem da casa em um jogo"):
        st.write("Digite as odds de todos os resultados do mesmo jogo, separadas por espaço. "
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
            st.markdown(md(f"**A casa fica com cerca de {dinheiro(m['margem'] * 100)} de cada R$ 100 apostados "
                           "neste jogo.**"))
            st.dataframe(pd.DataFrame({
                "Odd": [numero(o, 2) for o in odds],
                "Chance que a odd sugere": [pct(p) for p in m["implicitas"]],
                "Sem a parte da casa": [pct(p) for p in m["sem_margem"]]}), hide_index=True,
                use_container_width=True)
            st.caption(f"As chances que as odds sugerem somam {pct(m['soma'])}. Num jogo justo, somariam 100%. "
                       f"O que passa ({pct(m['margem'])}) é a margem da casa.")

    st.caption("A chance de acerto é uma suposição sua, não uma previsão. O rendimento é só um exemplo e não é "
               "recomendação de investimento.")
