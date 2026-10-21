from contextlib import closing

from html import escape

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st

st.set_page_config(page_title="Radar de Dados · Mercado de trabalho", page_icon="◈", layout="wide")

st.markdown("""
<style>
.stApp { background: #f5f5f0; color: #172d32; }
.block-container { max-width: 1440px; padding-top: 2.5rem; padding-bottom: 3rem; }
[data-testid="stHeader"] { background: #f5f5f0; }
h1, h2, h3 { color: #172d32; letter-spacing: -.04em; }
h1 { font-size: clamp(2.4rem, 5vw, 4.3rem) !important; font-weight: 650 !important; line-height: 1.06 !important; }
h3 { font-size: 1.2rem !important; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
[data-testid="stMetric"] { background: white; border: 1px solid #dfe5de; border-radius: 14px; padding: 22px 24px; }
[data-testid="stMetricLabel"] { color: #61716d; font-size: .86rem; }
[data-testid="stMetricValue"] { color: #172d32; font-size: 2.5rem; font-weight: 600; letter-spacing: -.05em; }
[data-testid="stTabs"] [role="tablist"] { gap: 28px; border-bottom: 1px solid #dce2db; }
[data-testid="stTabs"] [role="tab"] { font-size: .95rem; padding-bottom: 14px; }
.brand { display: flex; align-items: center; gap: 10px; font-size: 13px; font-weight: 700; letter-spacing: .14em; }
.brand-icon { background: #172d32; color: #b8eccb; padding: 5px 9px; border-radius: 8px; font-size: 20px; }
.eyebrow { color: #15776b; font-size: 12px; font-weight: 700; letter-spacing: .14em; margin: 35px 0 10px; }
.hero-copy { color: #61716d; font-size: 17px; max-width: 620px; line-height: 1.65; margin: 12px 0 24px; }
.note { background: #e7eee4; border-left: 3px solid #15776b; padding: 18px 22px; border-radius: 0 12px 12px 0; margin: 8px 0 28px; color: #425c50; font-size: 14px; }
.footer { border-top: 1px solid #dce2db; margin-top: 32px; padding-top: 18px; color: #61716d; font-size: 12px; }
@media (max-width: 640px) { .block-container { padding: 1.5rem 1rem; } }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def load_data(query: str) -> pd.DataFrame:
    with closing(psycopg2.connect(st.secrets["DATABASE_URL"])) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return pd.DataFrame(cur.fetchall(), columns=[column.name for column in cur.description])


GREEN = "#15776B"
NAVY = "#172D32"
PALETTE = [GREEN, "#89B69A", NAVY, "#C2CDA5", "#D3A76A", "#A5B9BE"]


def number(value):
    return f"{value:,}".replace(",", ".")


def chart_style(fig, height=360):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color=NAVY, size=12),
        margin=dict(l=0, r=35, t=12, b=0), showlegend=False,
        hoverlabel=dict(bgcolor=NAVY, font_color="white"),
    )
    fig.update_xaxes(title=None, showgrid=True, gridcolor="#E9EDE6", zeroline=False, fixedrange=True)
    fig.update_yaxes(title=None, showgrid=False, categoryorder="total ascending", fixedrange=True)
    fig.update_traces(hovertemplate="%{y}<br><b>%{x} vagas</b><extra></extra>", cliponaxis=False)
    return fig


df_estado = load_data("select * from vagas_por_estado")
df_senioridade = load_data("select * from vagas_por_senioridade")
df_empresa = load_data("select * from vagas_por_empresa")
df_vagas = load_data("select cargo, empresa, cidade, estado, senioridade, regime_trabalho, data_coleta from stg_vagas")
total = len(df_vagas)
last_date = pd.to_datetime(df_vagas["data_coleta"]).max() if total else pd.NaT
updated = last_date.strftime("%d.%m.%Y") if pd.notna(last_date) else "Sem dados"

brand, freshness = st.columns([3, 2])
with brand:
    st.markdown('<div class="brand"><span class="brand-icon">◈</span> RADAR DE DADOS</div>', unsafe_allow_html=True)
with freshness:
    st.caption(f"Gupy · Coleta diária · Última inclusão: {updated}")
st.markdown('<div class="eyebrow">OBSERVATÓRIO DO MERCADO DE TRABALHO</div>', unsafe_allow_html=True)
st.markdown("<h1>Seu próximo passo<br>começa nos dados.</h1>", unsafe_allow_html=True)
st.markdown('<p class="hero-copy">Um retrato das oportunidades em dados no Brasil. Explore onde estão as vagas, quem contrata e quais perfis o mercado procura.</p>', unsafe_allow_html=True)

metrics = st.columns(4)
metrics[0].metric("Vagas na base", number(total))
metrics[1].metric("Empresas", number(df_vagas["empresa"].nunique()))
metrics[2].metric("Vagas remotas", number((df_vagas["regime_trabalho"] == "Remoto").sum()))
metrics[3].metric("Vagas júnior", number((df_vagas["senioridade"] == "Júnior").sum()))
st.write("")

if total:
    leader = df_vagas["estado"].dropna().value_counts()
    if not leader.empty:
        st.markdown(f'<div class="note"><b>O mercado em perspectiva</b> · {escape(str(leader.index[0]))} concentra {leader.iloc[0] / total:.0%} das vagas da base. Use os recortes abaixo para explorar outras oportunidades.</div>', unsafe_allow_html=True)
else:
    st.info("A base ainda não tem vagas. Os dados aparecerão após a primeira coleta.")

overview, explore = st.tabs(["Panorama do mercado", "Explorar oportunidades"])
with overview:
    left, right = st.columns([1.2, 1], gap="large")
    with left, st.container(border=True):
        st.subheader("Onde estão as oportunidades")
        st.caption("Os 10 estados com mais vagas na base")
        states = df_estado.nlargest(10, "total_vagas")
        fig = px.bar(states, x="total_vagas", y="estado", orientation="h", text="total_vagas", color_discrete_sequence=[GREEN])
        fig.update_traces(textposition="outside", marker_cornerradius=4)
        st.plotly_chart(chart_style(fig), width="stretch", config={"displayModeBar": False})
    with right, st.container(border=True):
        st.subheader("Experiência em demanda")
        st.caption("Distribuição das vagas por senioridade")
        fig = px.bar(df_senioridade, x="total_vagas", y="senioridade", orientation="h", text="total_vagas", color="senioridade", color_discrete_sequence=PALETTE)
        fig.update_traces(textposition="outside", marker_cornerradius=4)
        st.plotly_chart(chart_style(fig), width="stretch", config={"displayModeBar": False})
    with st.container(border=True):
        st.subheader("Quem está contratando")
        st.caption("As 12 empresas com mais oportunidades na base")
        fig = px.bar(df_empresa.nlargest(12, "total_vagas"), x="total_vagas", y="empresa", orientation="h", text="total_vagas", color_discrete_sequence=[NAVY])
        fig.update_traces(textposition="outside", marker_cornerradius=4)
        st.plotly_chart(chart_style(fig, 440), width="stretch", config={"displayModeBar": False})

with explore:
    st.subheader("Encontre o seu recorte")
    st.caption("Busque por cargo ou empresa e combine os filtros para explorar a base.")
    search = st.text_input("Cargo ou empresa", placeholder="Ex.: engenheiro de dados, analytics, nome da empresa…")
    f1, f2, f3 = st.columns(3)
    seniority = f1.multiselect("Senioridade", sorted(df_vagas["senioridade"].dropna().unique()))
    workplace = f2.multiselect("Regime", sorted(df_vagas["regime_trabalho"].dropna().unique()))
    states = f3.multiselect("Estado", sorted(df_vagas["estado"].dropna().unique()))
    filtered = df_vagas.copy()
    if search.strip():
        query = search.strip()
        filtered = filtered[filtered["cargo"].str.contains(query, case=False, regex=False, na=False) | filtered["empresa"].str.contains(query, case=False, regex=False, na=False)]
    for column, selection in [("senioridade", seniority), ("regime_trabalho", workplace), ("estado", states)]:
        if selection:
            filtered = filtered[filtered[column].isin(selection)]
    st.caption(f"{number(len(filtered))} oportunidades · {number(total)} vagas na base")
    if filtered.empty:
        st.info("Nenhuma vaga encontrada. Tente outro termo ou remova um dos filtros.")
    else:
        st.dataframe(
            filtered.sort_values("data_coleta", ascending=False), hide_index=True, width="stretch", height=430,
            column_config={
                "cargo": st.column_config.TextColumn("Cargo", width="large"),
                "empresa": "Empresa", "cidade": "Cidade", "estado": "Estado",
                "senioridade": "Senioridade", "regime_trabalho": "Regime",
                "data_coleta": st.column_config.DateColumn("Incluída em", format="DD/MM/YYYY"),
            },
        )
    st.download_button("Baixar este recorte · CSV", filtered.to_csv(index=False).encode("utf-8-sig"), "radar-de-dados.csv", "text/csv")

st.markdown('<div class="footer">RADAR DE DADOS &nbsp; / &nbsp; Fonte: Gupy · Atualização diária · Dados em cache por até 1 hora.<br>Os números refletem vagas coletadas. A disponibilidade atual deve ser confirmada na Gupy.</div>', unsafe_allow_html=True)
