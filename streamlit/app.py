import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2

# -------------------------------------------------------------------
# Configuração da página
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Vagas de Dados no Brasil",
    page_icon="📊",
    layout="wide",
)

# -------------------------------------------------------------------
# Conexão com o banco
# -------------------------------------------------------------------
@st.cache_resource
def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

@st.cache_data(ttl=3600)
def load_data(query: str) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql(query, conn)

# -------------------------------------------------------------------
# Carrega os dados
# -------------------------------------------------------------------
df_estado      = load_data("select * from vagas_por_estado")
df_senioridade = load_data("select * from vagas_por_senioridade")
df_empresa     = load_data("select * from vagas_por_empresa")
df_vagas       = load_data("select cargo, empresa, cidade, estado, senioridade, regime_trabalho, fonte, data_coleta from stg_vagas")

# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------
st.title("📊 Mercado de Dados no Brasil")
st.markdown("Pipeline de coleta diária de vagas via **Gupy** e **LinkedIn**")
st.divider()

# -------------------------------------------------------------------
# Métricas principais
# -------------------------------------------------------------------
total       = len(df_vagas)
total_sp    = len(df_vagas[df_vagas["estado"] == "São Paulo"])
total_remoto = len(df_vagas[df_vagas["regime_trabalho"] == "Remoto"])
total_junior = len(df_vagas[df_vagas["senioridade"] == "Júnior"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de vagas",     total)
col2.metric("Vagas em São Paulo", total_sp)
col3.metric("Vagas remotas",      total_remoto)
col4.metric("Vagas Júnior",       total_junior)

st.divider()

# -------------------------------------------------------------------
# Gráficos — linha 1
# -------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📍 Vagas por Estado")
    fig_estado = px.bar(
        df_estado,
        x="total_vagas",
        y="estado",
        orientation="h",
        color="total_vagas",
        color_continuous_scale="Blues",
        labels={"total_vagas": "Total de Vagas", "estado": "Estado"},
    )
    fig_estado.update_layout(
        coloraxis_showscale=False,
        yaxis={"categoryorder": "total ascending"},
        height=400,
    )
    st.plotly_chart(fig_estado, use_container_width=True)

with col_right:
    st.subheader("🎯 Vagas por Senioridade")
    fig_senior = px.pie(
        df_senioridade,
        names="senioridade",
        values="total_vagas",
        color_discrete_sequence=px.colors.sequential.Blues_r,
        hole=0.4,
    )
    fig_senior.update_traces(textposition="inside", textinfo="percent+label")
    fig_senior.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig_senior, use_container_width=True)

st.divider()

# -------------------------------------------------------------------
# Gráficos — linha 2
# -------------------------------------------------------------------
st.subheader("🏢 Empresas que mais contratam")
fig_empresa = px.bar(
    df_empresa.head(15),
    x="empresa",
    y="total_vagas",
    color="fonte",
    color_discrete_map={"linkedin": "#0077B5", "gupy": "#00C853"},
    labels={"total_vagas": "Total de Vagas", "empresa": "Empresa", "fonte": "Fonte"},
)
fig_empresa.update_layout(height=400, xaxis_tickangle=-30)
st.plotly_chart(fig_empresa, use_container_width=True)

st.divider()

# -------------------------------------------------------------------
# Tabela completa com filtros
# -------------------------------------------------------------------
st.subheader("🔍 Explorar vagas")

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    filtro_senioridade = st.multiselect(
        "Senioridade",
        options=df_vagas["senioridade"].unique(),
        default=[],
    )

with col_f2:
    filtro_regime = st.multiselect(
        "Regime",
        options=df_vagas["regime_trabalho"].unique(),
        default=[],
    )

with col_f3:
    filtro_fonte = st.multiselect(
        "Fonte",
        options=df_vagas["fonte"].unique(),
        default=[],
    )

df_filtrado = df_vagas.copy()
if filtro_senioridade:
    df_filtrado = df_filtrado[df_filtrado["senioridade"].isin(filtro_senioridade)]
if filtro_regime:
    df_filtrado = df_filtrado[df_filtrado["regime_trabalho"].isin(filtro_regime)]
if filtro_fonte:
    df_filtrado = df_filtrado[df_filtrado["fonte"].isin(filtro_fonte)]

st.dataframe(df_filtrado, use_container_width=True, height=400)
st.caption(f"Mostrando {len(df_filtrado)} de {total} vagas")