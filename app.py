import re
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================

st.set_page_config(
    page_title="CRM Analytics | Charry",
    page_icon="📊",
    layout="wide",
)

SHEETS = {
    "diario": "Preenchimento Diário",
    "campanhas": "Campanhas",
    "fluxos": "Fluxos",
    "insights": "Insights",
    "kpis_mensais": "KPIs Mensais",
}

CANAL_ORDEM = [
    "E-mail Marketing",
    "WhatsApp HSM",
    "Personal Shopper",
    "Comunidade",
    "Grupo Exclusivo",
    "Canal",
]


# =========================
# FUNÇÕES AUXILIARES
# =========================

def parse_sheet_id(url_or_id: str) -> str:
    """Aceita o ID puro ou o link completo do Google Sheets."""
    if not url_or_id:
        return ""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url_or_id)
    return match.group(1) if match else url_or_id.strip()


def money(value: float) -> str:
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def number(value: float) -> str:
    try:
        return f"{value:,.0f}".replace(",", ".")
    except Exception:
        return "0"


def percent(value: float) -> str:
    try:
        return f"{value:.1f}%".replace(".", ",")
    except Exception:
        return "0,0%"


def clean_numeric(series: pd.Series) -> pd.Series:
    """Converte valores como R$ 1.234,56, 12,5% ou 1234.56 para número."""
    if series is None:
        return pd.Series(dtype=float)

    s = series.astype(str).str.strip()
    s = s.str.replace("R$", "", regex=False)
    s = s.str.replace("%", "", regex=False)
    s = s.str.replace(" ", "", regex=False)

    # Se tiver vírgula, assume padrão brasileiro: 1.234,56
    has_comma = s.str.contains(",", regex=False, na=False)
    s_br = s[has_comma].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    s_us = s[~has_comma].str.replace(",", "", regex=False)

    out = pd.Series(index=series.index, dtype="float64")
    out.loc[has_comma] = pd.to_numeric(s_br, errors="coerce")
    out.loc[~has_comma] = pd.to_numeric(s_us, errors="coerce")
    return out.fillna(0)


def clean_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


@st.cache_data(ttl=300)
def read_google_sheet(sheet_id: str, tab_name: str) -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={quote(tab_name)}"
    return pd.read_csv(url)


@st.cache_data(ttl=300)
def read_excel_file(uploaded_file, tab_name: str) -> pd.DataFrame:
    return pd.read_excel(uploaded_file, sheet_name=tab_name)


def load_data(sheet_id: str, uploaded_file):
    data = {}

    if uploaded_file is not None:
        for key, tab in SHEETS.items():
            try:
                data[key] = read_excel_file(uploaded_file, tab)
            except Exception:
                data[key] = pd.DataFrame()
        return data

    if sheet_id:
        for key, tab in SHEETS.items():
            try:
                data[key] = read_google_sheet(sheet_id, tab)
            except Exception:
                data[key] = pd.DataFrame()
        return data

    return {key: pd.DataFrame() for key in SHEETS}


def prepare_diario(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    if "Data" in df.columns:
        df["Data"] = clean_date(df["Data"])

    numeric_cols = [
        "Receita (R$)",
        "Pedidos",
        "Ticket Médio",
        "Conversão",
        "Cliques",
        "Abertura/Leitura",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = clean_numeric(df[col])

    df = df.dropna(subset=["Data"], how="any")
    df = df[df.get("Canal", "").astype(str).str.strip() != ""]
    return df


def prepare_campanhas(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    if "Data" in df.columns:
        df["Data"] = clean_date(df["Data"])

    numeric_cols = [
        "Receita",
        "Pedidos",
        "Ticket Médio",
        "Abertura %",
        "CTOR %",
        "Conversão %",
        "ROI",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = clean_numeric(df[col])

    df = df.dropna(subset=["Data"], how="any")
    return df


def prepare_fluxos(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    if "Última Verificação" in df.columns:
        df["Última Verificação"] = clean_date(df["Última Verificação"])

    for col in ["Receita", "Pedidos", "Conversão"]:
        if col in df.columns:
            df[col] = clean_numeric(df[col])

    return df


def prepare_insights(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    if "Data" in df.columns:
        df["Data"] = clean_date(df["Data"])

    return df.dropna(subset=["Data"], how="any")


def filter_period(df: pd.DataFrame, start, end, date_col="Data") -> pd.DataFrame:
    if df.empty or date_col not in df.columns:
        return df.iloc[0:0]

    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    return df[(df[date_col] >= start) & (df[date_col] <= end)]


def calc_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "receita": 0,
            "pedidos": 0,
            "ticket": 0,
            "cliques": 0,
            "abertura": 0,
            "conversao": 0,
            "melhor_canal": "-",
        }

    receita = df["Receita (R$)"].sum() if "Receita (R$)" in df.columns else 0
    pedidos = df["Pedidos"].sum() if "Pedidos" in df.columns else 0
    ticket = receita / pedidos if pedidos else 0
    cliques = df["Cliques"].sum() if "Cliques" in df.columns else 0
    abertura = df["Abertura/Leitura"].mean() if "Abertura/Leitura" in df.columns else 0
    conversao = df["Conversão"].mean() if "Conversão" in df.columns else 0

    if "Canal" in df.columns and "Receita (R$)" in df.columns:
        receita_canal = df.groupby("Canal", as_index=False)["Receita (R$)"].sum()
        receita_canal = receita_canal.sort_values("Receita (R$)", ascending=False)
        melhor_canal = receita_canal.iloc[0]["Canal"] if not receita_canal.empty else "-"
    else:
        melhor_canal = "-"

    return {
        "receita": receita,
        "pedidos": pedidos,
        "ticket": ticket,
        "cliques": cliques,
        "abertura": abertura,
        "conversao": conversao,
        "melhor_canal": melhor_canal,
    }


def delta(current, previous):
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100


def metric_card(label, value, delta_value=None, formatter=None):
    if formatter is None:
        formatter = lambda x: x

    delta_text = None
    if delta_value is not None:
        delta_text = percent(delta_value)

    st.metric(label, formatter(value), delta=delta_text)


# =========================
# SIDEBAR
# =========================

st.sidebar.title("⚙️ Configuração")

st.sidebar.markdown(
    """
Use uma das opções:

1. Cole o link/ID do Google Sheets público; ou  
2. Faça upload do Excel para testar localmente.
"""
)

sheet_input = st.sidebar.text_input("Link ou ID do Google Sheets")
sheet_id = parse_sheet_id(sheet_input)

uploaded_file = st.sidebar.file_uploader("Ou envie o Excel", type=["xlsx"])

data = load_data(sheet_id, uploaded_file)

diario = prepare_diario(data["diario"])
campanhas = prepare_campanhas(data["campanhas"])
fluxos = prepare_fluxos(data["fluxos"])
insights = prepare_insights(data["insights"])


# =========================
# VALIDAÇÃO
# =========================

st.title("📊 CRM Analytics | Charry")
st.caption("Dashboard de resumo com comparação de períodos via Google Sheets.")

if diario.empty:
    st.warning(
        "Conecte sua planilha do Google Sheets ou envie o Excel na barra lateral. "
        "A aba principal precisa se chamar **Preenchimento Diário**."
    )
    st.stop()


# =========================
# FILTROS DE PERÍODO
# =========================

min_date = diario["Data"].min().date()
max_date = diario["Data"].max().date()

st.sidebar.divider()
st.sidebar.subheader("📅 Períodos")

periodo_a = st.sidebar.date_input(
    "Período A",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

periodo_b = st.sidebar.date_input(
    "Comparar com Período B",
    value=(min_date, min_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(periodo_a, tuple) and len(periodo_a) == 2:
    a_start, a_end = periodo_a
else:
    a_start = a_end = periodo_a

if isinstance(periodo_b, tuple) and len(periodo_b) == 2:
    b_start, b_end = periodo_b
else:
    b_start = b_end = periodo_b

df_a = filter_period(diario, a_start, a_end)
df_b = filter_period(diario, b_start, b_end)

camp_a = filter_period(campanhas, a_start, a_end)
camp_b = filter_period(campanhas, b_start, b_end)

summary_a = calc_summary(df_a)
summary_b = calc_summary(df_b)


# =========================
# RESUMO EXECUTIVO
# =========================

st.subheader("Resumo Geral")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    metric_card(
        "Receita CRM",
        summary_a["receita"],
        delta(summary_a["receita"], summary_b["receita"]),
        money,
    )

with col2:
    metric_card(
        "Pedidos",
        summary_a["pedidos"],
        delta(summary_a["pedidos"], summary_b["pedidos"]),
        number,
    )

with col3:
    metric_card(
        "Ticket Médio",
        summary_a["ticket"],
        delta(summary_a["ticket"], summary_b["ticket"]),
        money,
    )

with col4:
    metric_card(
        "Cliques",
        summary_a["cliques"],
        delta(summary_a["cliques"], summary_b["cliques"]),
        number,
    )

with col5:
    st.metric("Melhor Canal", summary_a["melhor_canal"])


# =========================
# GRÁFICOS PRINCIPAIS
# =========================

st.divider()

col_left, col_right = st.columns([1.1, 1])

with col_left:
    st.subheader("Receita por Canal")

    if not df_a.empty:
        receita_canal = (
            df_a.groupby("Canal", as_index=False)["Receita (R$)"]
            .sum()
            .sort_values("Receita (R$)", ascending=False)
        )

        fig = px.bar(
            receita_canal,
            x="Canal",
            y="Receita (R$)",
            text_auto=".2s",
            title=None,
        )
        fig.update_layout(xaxis_title="", yaxis_title="Receita")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados no Período A.")

with col_right:
    st.subheader("Participação por Canal")

    if not df_a.empty and df_a["Receita (R$)"].sum() > 0:
        receita_canal = (
            df_a.groupby("Canal", as_index=False)["Receita (R$)"]
            .sum()
            .sort_values("Receita (R$)", ascending=False)
        )

        fig = px.pie(
            receita_canal,
            names="Canal",
            values="Receita (R$)",
            hole=0.45,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem receita no Período A.")


st.subheader("Evolução Diária")

if not df_a.empty:
    evolucao = (
        df_a.groupby("Data", as_index=False)
        .agg({"Receita (R$)": "sum", "Pedidos": "sum"})
        .sort_values("Data")
    )

    fig = px.line(
        evolucao,
        x="Data",
        y="Receita (R$)",
        markers=True,
    )
    fig.update_layout(xaxis_title="", yaxis_title="Receita")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados para evolução diária.")


# =========================
# COMPARATIVO POR CANAL
# =========================

st.divider()
st.subheader("Comparativo por Canal")

canal_a = (
    df_a.groupby("Canal", as_index=False)
    .agg({"Receita (R$)": "sum", "Pedidos": "sum", "Cliques": "sum"})
    if not df_a.empty
    else pd.DataFrame(columns=["Canal", "Receita (R$)", "Pedidos", "Cliques"])
)

canal_b = (
    df_b.groupby("Canal", as_index=False)
    .agg({"Receita (R$)": "sum", "Pedidos": "sum", "Cliques": "sum"})
    if not df_b.empty
    else pd.DataFrame(columns=["Canal", "Receita (R$)", "Pedidos", "Cliques"])
)

comparativo = canal_a.merge(canal_b, on="Canal", how="outer", suffixes=(" A", " B")).fillna(0)

if not comparativo.empty:
    comparativo["Variação Receita %"] = comparativo.apply(
        lambda row: delta(row["Receita (R$) A"], row["Receita (R$) B"]), axis=1
    )
    comparativo["Ticket A"] = comparativo.apply(
        lambda row: row["Receita (R$) A"] / row["Pedidos A"] if row["Pedidos A"] else 0,
        axis=1,
    )

    display_comp = comparativo.copy()
    display_comp["Receita A"] = display_comp["Receita (R$) A"].apply(money)
    display_comp["Receita B"] = display_comp["Receita (R$) B"].apply(money)
    display_comp["Ticket A"] = display_comp["Ticket A"].apply(money)
    display_comp["Variação Receita %"] = display_comp["Variação Receita %"].apply(
        lambda x: "-" if pd.isna(x) else percent(x)
    )

    st.dataframe(
        display_comp[
            [
                "Canal",
                "Receita A",
                "Receita B",
                "Variação Receita %",
                "Pedidos A",
                "Pedidos B",
                "Ticket A",
                "Cliques A",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Sem dados para comparar.")


# =========================
# CAMPANHAS
# =========================

st.divider()
st.subheader("Ranking de Campanhas")

if not camp_a.empty and "Campanha" in camp_a.columns:
    ranking = (
        camp_a.groupby(["Campanha", "Canal"], as_index=False)
        .agg({"Receita": "sum", "Pedidos": "sum"})
        .sort_values("Receita", ascending=False)
        .head(15)
    )

    col1, col2 = st.columns([1.2, 1])

    with col1:
        fig = px.bar(
            ranking,
            x="Receita",
            y="Campanha",
            color="Canal",
            orientation="h",
        )
        fig.update_layout(yaxis_title="", xaxis_title="Receita")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        ranking_display = ranking.copy()
        ranking_display["Receita"] = ranking_display["Receita"].apply(money)
        st.dataframe(ranking_display, use_container_width=True, hide_index=True)
else:
    st.info("Sem dados de campanhas no período selecionado.")


# =========================
# FLUXOS
# =========================

st.divider()
st.subheader("Status dos Fluxos")

if not fluxos.empty:
    flux_display = fluxos.copy()

    if "Receita" in flux_display.columns:
        flux_display["Receita"] = flux_display["Receita"].apply(money)

    st.dataframe(flux_display, use_container_width=True, hide_index=True)
else:
    st.info("Sem dados na aba Fluxos.")


# =========================
# INSIGHTS
# =========================

st.divider()
st.subheader("Últimos Insights")

if not insights.empty:
    insights_periodo = filter_period(insights, a_start, a_end)

    if not insights_periodo.empty:
        insights_periodo = insights_periodo.sort_values("Data", ascending=False).head(10)
        st.dataframe(insights_periodo, use_container_width=True, hide_index=True)
    else:
        st.info("Sem insights registrados no Período A.")
else:
    st.info("Sem dados na aba Insights.")


# =========================
# BASE DE DADOS
# =========================

with st.expander("Ver base do período"):
    st.dataframe(df_a, use_container_width=True, hide_index=True)
