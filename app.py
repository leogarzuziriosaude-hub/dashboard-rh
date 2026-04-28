import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Configuração da página (Apenas uma vez)
st.set_page_config(layout="wide", page_title="Dashboard HMRG")

# NOVO CSS PARA O MODO ESCURO "ESTILO NASA"
st.markdown("""
<style>
.stApp {
    background: #0e1117 !important;
}

.stPlotlyChart {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 15px !important;
    padding: 10px !important;
    box-shadow: 5px 5px 15px rgba(0,0,0,0.5) !important;
}

[data-testid="stMetricValue"] {
    color: #00d4ff !important;
    font-family: 'Courier New', Courier, monospace !important;
    font-weight: bold !important; 
}

h1 {
    color: #ffffff !important;
    text-align: center !important; 
    width: 100% !important;        
    text-transform: uppercase !important;
    letter-spacing: 3px !important;
    display: block !important;
}

hr {
    margin-top: 0px !important;
    margin-bottom: 20px !important;
}
</style>
""", unsafe_allow_html=True)

# 2. Conexão com Google Sheets
@st.cache_data(ttl=600)
def carregar_dados():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open("BASE DE DADOS - HMRG")

    abas = [
        "BASE DE DADOS",
        "ADMISSÃO",
        "DESLIGAMENTO",
        "TRANSFERÊNCIA",
        "PERMUTA",
        "ALTERAÇÃO CH",
        "BENEFÍCIO"
    ]

    dados = {}

    for aba_nome in abas:
        try:
            aba = sheet.worksheet(aba_nome)
            dados[aba_nome] = pd.DataFrame(aba.get_all_records())
        except Exception as e:
            st.warning(f"Erro ao carregar aba {aba_nome}: {e}")
            dados[aba_nome] = pd.DataFrame()
    sheet_atestados = client.open_by_url("https://docs.google.com/spreadsheets/d/1did243q7zncd33rsUi8frHLneR5ymFEkEYsejRaZp2Y/edit#gid=1311645159")

    abas_meses = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
                  "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

    abas_meses_validos = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
                          "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

    lista_atestados = []
    todas_abas = sheet_atestados.worksheets()

    for i, aba in enumerate(todas_abas):
        if i == 0:
            continue  # ignora sempre a primeira aba (DEZ/2025)

        if aba.title.upper() not in abas_meses_validos:
            continue

        try:
            df_mes = pd.DataFrame(aba.get_all_records())
            df_mes["MES"] = aba.title.upper()
            lista_atestados.append(df_mes)
        except Exception as e:
            st.warning(f"Erro ao carregar aba {aba.title}: {e}")

    if lista_atestados:
        dados["ATESTADOS"] = pd.concat(lista_atestados, ignore_index=True)
    else:
        dados["ATESTADOS"] = pd.DataFrame()

    return dados

# 3. Lógica de Divisões
def classificar_divisao(nome_funcao):
    texto = str(nome_funcao).upper()
    if "MEDICO" in texto or "MÉDICO" in texto:
        return "DIV. MÉDICA"
    elif any(palavra in texto for palavra in ["ENFERMEIRO", "TECNICO DE ENFERMAGEM", "INSTRUMENTADOR"]):
        return "DIV. DE ENFERMAGEM"
    elif any(palavra in texto for palavra in [
        "PSICOLOGO", "FARMACEUTICO", "FISIOTERAPEUTA",
        "NUTRICIONISTA", "DENTISTA", "ASSISTENTE SOCIAL",
        "FONOAUDIOLOGO"
    ]):
        return "DIV. MULTIDISCIPLINAR"
    elif "LIMPEZA" in texto:
        return "HIGIENE"
    else:
        return "OUTROS"

# Carrega dados
dados = carregar_dados()

df_base = dados["BASE DE DADOS"]
df_desligamento = dados["DESLIGAMENTO"]
df_desligamento['DIVISAO'] = df_desligamento['CARGO'].apply(classificar_divisao)
df_admissao = dados["ADMISSÃO"]

df_desligamento['DIVISAO'] = df_desligamento['CARGO'].apply(classificar_divisao)
df_admissao['DIVISAO'] = df_admissao['CARGO'].apply(classificar_divisao)

# Converter datas de admissão e desligamento
df_admissao['EXERCÍCIO'] = pd.to_datetime(
    df_admissao['EXERCÍCIO'],
    dayfirst=True,
    errors='coerce'
)

df_desligamento['DATA DO DESLIGAMENTO'] = pd.to_datetime(
    df_desligamento['DATA DO DESLIGAMENTO'],
    dayfirst=True,
    errors='coerce'
)
NOME_DA_COLUNA = "CARGO"



# Aplica classificação
df_base['DIVISAO'] = df_base[NOME_DA_COLUNA].apply(classificar_divisao)

# 4. Preparação dos dados
contagem = df_base['DIVISAO'].value_counts().reset_index()
contagem.columns = ['Divisão', 'Quantidade']

# Layout
st.title("DASHBOARD - RH")
st.markdown("---")



tabs = st.tabs([
    "Ativos",
    "Desligamento",
    "Admissão", 
    "Atestados"
])

    # ---------------- BASE DE DADOS ----------------
with tabs[0]:
    st.subheader("ATIVOS")

    col1, col2 = st.columns([3, 1])

    with col2:
        st.metric("Total de Colaboradores", len(df_base))

    # ORDEM PERSONALIZADA
    ordem = [
        'DIV. DE ENFERMAGEM',
        'DIV. MÉDICA',
        'DIV. MULTIDISCIPLINAR',
        'HIGIENE',
        'OUTROS'
    ]

    contagem['Divisão'] = pd.Categorical(
        contagem['Divisão'],
        categories=ordem,
        ordered=True
    )

    contagem_ordenada = contagem.sort_values('Divisão')

    # -------- GRÁFICO DE DIVISÃO --------
    with col1:
        fig = px.bar(
            contagem_ordenada,
            x='Divisão',
            y='Quantidade',
            text='Quantidade'
        )

        fig.update_traces(
            textposition='inside',
            insidetextanchor='middle',
            textfont_size=18,
            textfont_color='black'
        )

        with st.container():
            st.plotly_chart(fig, use_container_width=True)

    # ESPAÇO
    st.markdown("###")

    # -------- FILTRO + MÉTRICA --------
    col_filtro, col_mes = st.columns([0.1, 1])

    with col_filtro:
        mes_selecionado = st.selectbox(
            "Mês",
            [
                "Janeiro", "Fevereiro", "Março", "Abril",
                "Maio", "Junho", "Julho", "Agosto",
                "Setembro", "Outubro", "Novembro", "Dezembro"
            ]
        )

    mapa_meses = {
        "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
        "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
        "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
    }

    mes_num = mapa_meses[mes_selecionado]

    admissoes_mes = df_admissao[
        df_admissao['EXERCÍCIO'].dt.month == mes_num
    ]

    desligamentos_mes = df_desligamento[
        df_desligamento['DATA DO DESLIGAMENTO'].dt.month == mes_num
    ]

    total_funcionarios = len(df_base)

    turnover_mes = (
        (len(admissoes_mes) + len(desligamentos_mes)) / 2
    ) / total_funcionarios * 100

    with col_mes:
        st.metric("Turnover do Mês", f"{turnover_mes:.2f}%")

    # -------- DADOS DO GRÁFICO --------
    meses = list(range(1, 13))
    turnover_lista = []

    for mes in meses:
        adm_mes = df_admissao[df_admissao['EXERCÍCIO'].dt.month == mes]
        des_mes = df_desligamento[df_desligamento['DATA DO DESLIGAMENTO'].dt.month == mes]

        turnover = ((len(adm_mes) + len(des_mes)) / 2) / total_funcionarios * 100
        turnover_lista.append(turnover)

    df_turnover = pd.DataFrame({
        "Mês": [
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"
        ],
        "Turnover": turnover_lista
    })

    # -------- GRÁFICO TURNOVER --------
    fig_turnover = px.line(
        df_turnover,
        x="Mês",
        y="Turnover",
        markers=True
    )

    fig_turnover.update_traces(
        line=dict(width=2, color="rgba(255,255,255,0.2)"),
        marker=dict(size=6)
    )

    # 🔴 rastro até o mês selecionado
    df_ate_mes = df_turnover.iloc[:mes_num]

    fig_turnover.add_scatter(
        x=df_ate_mes["Mês"],
        y=df_ate_mes["Turnover"],
        mode="lines",
        line=dict(color="#ff4d4d", width=4)
    )

    # 🔴 ponto do mês atual
    mes_nome = df_turnover.iloc[mes_num - 1]["Mês"]

    valor_mes = df_turnover.iloc[mes_num - 1]["Turnover"]

    fig_turnover.add_scatter(
        x=[mes_nome],
        y=[valor_mes],
        mode="markers+text",
        text=[f"{valor_mes:.2f}%"],
        textposition="top center",
        marker=dict(size=14, color="#ff0000")
    )

    fig_turnover.update_layout(
        title="📈 Evolução do Turnover",
        yaxis_title="%",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="white",
        title_x=0.45,
        showlegend=False,
        margin=dict(l=30, r=20, t=50, b=20)
    )

    fig_turnover.update_xaxes(showgrid=False)

    fig_turnover.update_yaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.1)"
    )

    with st.container():
        st.plotly_chart(fig_turnover, use_container_width=True)





# ---------------- DESLIGAMENTO ----------------
with tabs[1]:
    st.title("DESLIGAMENTOS")

    # ---------------- FILTROS ----------------
    col_filtro1, col_filtro2, col_vazio = st.columns([0.5, 0.5, 3])

    with col_filtro1:
        st.markdown(
            "<p style='margin-bottom: -10px;'>Divisão</p>",
            unsafe_allow_html=True
)
        divisao_selecionada = st.selectbox(
            "",
            ["Todas"] + sorted(df_desligamento['DIVISAO'].dropna().unique())
        )

    with col_filtro2:
        st.markdown(
            "<p style='margin-bottom: -10px;'>Tipo de Desligamento</p>",
            unsafe_allow_html=True
        )

        tipos = df_desligamento['TIPO DE DESLIGAMENTO'] \
            .dropna() \
            .astype(str) \
            .str.strip()

        tipos = tipos[tipos != ""]

        lista_tipos = ["Todos"] + sorted(tipos.unique())

        tipo_selecionado = st.selectbox(
            "",
            lista_tipos
        )

    # ---------------- FILTRAGEM ----------------
    df_filtrado = df_desligamento.copy()

    if divisao_selecionada != "Todas":
        df_filtrado = df_filtrado[
            df_filtrado['DIVISAO'] == divisao_selecionada
        ]

    if tipo_selecionado != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado['TIPO DE DESLIGAMENTO'] == tipo_selecionado
        ]

    df_filtrado = df_filtrado.copy()

    # ---------------- LIMPEZA DE DATAS ----------------
    df_filtrado['DATA DO DESLIGAMENTO'] = pd.to_datetime(
        df_filtrado['DATA DO DESLIGAMENTO'],
        dayfirst=True,
        errors='coerce'
    )

    df_filtrado = df_filtrado.dropna(subset=['DATA DO DESLIGAMENTO'])

    # ---------------- MÉTRICA ----------------
    st.metric("Total de Desligamentos", len(df_filtrado))

    st.markdown("---")

    # ---------------- GRÁFICOS ----------------
    col_graf1, col_graf2 = st.columns([3, 2])

    # 📊 DESLIGAMENTOS POR MÊS
    df_filtrado['MES_NUM'] = df_filtrado['DATA DO DESLIGAMENTO'].dt.month

    df_filtrado['MES_NOME'] = df_filtrado['MES_NUM'].map({
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    })

    deslig_por_mes = df_filtrado.groupby(
        ['MES_NUM', 'MES_NOME']
    ).size().reset_index(name='Quantidade')

    deslig_por_mes = deslig_por_mes.sort_values('MES_NUM')

    with col_graf1:
        fig_mes = px.bar(
            deslig_por_mes,
            x='MES_NOME',
            y='Quantidade',
            text='Quantidade'
        )

        fig_mes.update_traces(
            textposition='inside',
            insidetextanchor='middle',
            textfont_size=18,
            textfont_color='black'
        )

        fig_mes.update_layout(
            title="Desligamentos por Mês",
            xaxis_title="Mês",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color="white",
            height=450,
            margin=dict(l=20, r=20, t=50, b=20)
        )

        fig_mes.update_xaxes(showgrid=False)

        fig_mes.update_yaxes(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)"
        )

        st.plotly_chart(fig_mes, use_container_width=True)

    # 🥧 TIPO DE DESLIGAMENTO
    tipo_deslig = df_filtrado['TIPO DE DESLIGAMENTO'].value_counts().reset_index()
    tipo_deslig.columns = ['Tipo', 'Quantidade']

    with col_graf2:
        fig_tipo = px.pie(
            tipo_deslig,
            names='Tipo',
            values='Quantidade'
        )

        fig_tipo.update_traces(
            textinfo='percent'
        )

        fig_tipo.update_layout(
            title="Tipo de Desligamento",
            paper_bgcolor='rgba(0,0,0,0)',
            font_color="white",
            height=350
        )

        st.plotly_chart(fig_tipo, use_container_width=True)






# ---------------- ADMISSÃO ----------------
# ---------------- ADMISSÃO ----------------
with tabs[2]:
    st.title("ADMISSÕES")

    # 🔧 PADRONIZAÇÃO
    df_admissao['DIVISAO'] = df_admissao['CARGO'].apply(classificar_divisao)

    # ---------------- FILTRO ----------------
    col_filtro1, col_vazio = st.columns([0.5, 3])

    with col_filtro1:
        st.markdown(
            "<p style='margin-bottom: -10px;'>Divisão</p>",
            unsafe_allow_html=True
        )

        divisao_selecionada = st.selectbox(
            "",
            ["Todas"] + sorted(df_admissao['DIVISAO'].dropna().unique())
        )

    # ---------------- FILTRAGEM ----------------
    df_filtrado = df_admissao.copy()

    if divisao_selecionada != "Todas":
        df_filtrado = df_filtrado[
            df_filtrado['DIVISAO'] == divisao_selecionada
        ]

    # ---------------- DATAS ----------------
    df_filtrado['EXERCÍCIO'] = pd.to_datetime(
        df_filtrado['EXERCÍCIO'],
        dayfirst=True,
        errors='coerce'
    )

    df_filtrado = df_filtrado.dropna(subset=['EXERCÍCIO'])

    df_filtrado['MES_NUM'] = df_filtrado['EXERCÍCIO'].dt.month

    df_filtrado['MES_NOME'] = df_filtrado['MES_NUM'].map({
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    })

    # ---------------- MÉTRICA ----------------
    st.metric("Total de Admissões", len(df_filtrado))

    st.markdown("---")

    # ---------------- DADOS DO GRÁFICO ----------------
    adm_por_mes = df_filtrado.groupby(
        ['MES_NUM', 'MES_NOME']
    ).size().reset_index(name='Quantidade')

    adm_por_mes = adm_por_mes.sort_values('MES_NUM')

    # ---------------- CRIAR GRÁFICO ----------------
    fig_adm = px.bar(
        adm_por_mes,
        x='MES_NOME',
        y='Quantidade',
        text='Quantidade'
    )

    fig_adm.update_traces(
        textposition='outside',
        marker_color='#00d4ff'
    )

    fig_adm.update_layout(
        title="Admissões por Mês",
        xaxis_title="Mês",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="white",
        height=450,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    fig_adm.update_xaxes(showgrid=False)

    fig_adm.update_yaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.1)"
    )

    # ---------------- CENTRALIZAR GRÁFICO ----------------
    st.plotly_chart(fig_adm, use_container_width=True)

# ---------------- PERMUTA ----------------
#with tabs[5]:
    st.title("PERMUTAS")

    df_permuta = dados["PERMUTA"]

    st.metric("Total de Permutas", len(df_permuta))

    st.write(df_permuta.head())


# ---------------- BENEFÍCIO ----------------
#with tabs[6]:
    st.title("BENEFÍCIO")

    df_beneficio = dados["BENEFÍCIO"]

    st.metric("Total de Registros", len(df_beneficio))

    st.write(df_beneficio.head())


# ---------------- ABSENTEÍSMO ----------------
with tabs[3]:
    st.title("ATESTADOS")

    # ---------------- CARREGAR DADOS ----------------
    df_abs = dados["ATESTADOS"].copy()


    # ---------------- TRATAR DATAS ----------------
    df_abs['DATA INICIAL'] = pd.to_datetime(
        df_abs['DATA INICIAL'],
        dayfirst=True,
        errors='coerce'
    )

    df_abs = df_abs.dropna(subset=['DATA INICIAL'])

    # ---------------- FILTRO DE ANO (2026) ----------------
    df_abs = df_abs[df_abs['DATA INICIAL'].dt.year == 2026]

    # ---------------- MÊS A PARTIR DA DATA ----------------
    ordem_meses = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
                   "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

    mapa_mes = {
        1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR",
        5: "MAI", 6: "JUN", 7: "JUL", 8: "AGO",
        9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
    }

    df_abs['MES'] = df_abs['DATA INICIAL'].dt.month.map(mapa_mes)

    # ---------------- DIVISÃO ----------------
    df_abs['DIVISAO'] = df_abs['FUNÇÃO'].astype(str).str.strip().apply(classificar_divisao)

    # ---------------- FILTROS ----------------
    if st.button("🔄"):
        st.session_state['mes_abs'] = "Todos"
        st.session_state['divisao_abs'] = "Todas"
        st.session_state['funcao_abs'] = "Todas"
        st.session_state['pref_abs'] = "Todos"

    col1, col2, col3, col4, _ = st.columns([0.1, 0.1, 0.1, 0.1, 0.1])

    with col1:
        mes = st.selectbox("Mês", ["Todos"] + ordem_meses,
            key='mes_abs',
            index=(["Todos"] + ordem_meses).index(st.session_state.get('mes_abs', 'Todos')))

    with col2:
        divisoes = sorted(df_abs['DIVISAO'].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique())
        divisao = st.selectbox("Divisão", ["Todas"] + divisoes,
            key='divisao_abs',
            index=(["Todas"] + divisoes).index(st.session_state.get('divisao_abs', 'Todas')) if st.session_state.get('divisao_abs', 'Todas') in ["Todas"] + divisoes else 0)

    with col3:
        funcoes = sorted(df_abs['FUNÇÃO'].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique())
        funcao = st.selectbox("Função", ["Todas"] + funcoes,
            key='funcao_abs',
            index=(["Todas"] + funcoes).index(st.session_state.get('funcao_abs', 'Todas')) if st.session_state.get('funcao_abs', 'Todas') in ["Todas"] + funcoes else 0)

    with col4:
        prefs = sorted(df_abs['PREF'].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique())
        pref = st.selectbox("Pref", ["Todos"] + prefs,
            key='pref_abs',
            index=(["Todos"] + prefs).index(st.session_state.get('pref_abs', 'Todos')) if st.session_state.get('pref_abs', 'Todos') in ["Todos"] + prefs else 0)
        
    # ---------------- FILTRAGEM ----------------
    df_filtrado = df_abs.copy()

    if pref != "Todos":
        df_filtrado = df_filtrado[df_filtrado['PREF'].astype(str).str.strip() == pref]

    if divisao != "Todas":
        df_filtrado = df_filtrado[df_filtrado['DIVISAO'].astype(str).str.strip() == divisao]

    if funcao != "Todas":
        df_filtrado = df_filtrado[df_filtrado['FUNÇÃO'].astype(str).str.strip() == funcao]

    if mes != "Todos":
        df_filtrado = df_filtrado[df_filtrado['MES'] == mes]

    # ---------------- MÉTRICAS ----------------
    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.metric("Total de Atestados", len(df_filtrado))

    with col_m2:
        st.metric("Colaboradores Afastados", df_filtrado['MATRÍCULA'].nunique())

    st.markdown("---")

    # ---------------- GRÁFICO 1: ATESTADOS POR MÊS ----------------
    base_meses = pd.DataFrame({'Mês': ordem_meses})

    atestados_mes = df_filtrado['MES'].value_counts().reset_index()
    atestados_mes.columns = ['Mês', 'Quantidade']

    atestados_mes = base_meses.merge(atestados_mes, on='Mês', how='left').fillna(0)
    atestados_mes['Quantidade'] = atestados_mes['Quantidade'].astype(int)
    atestados_mes['Mês'] = pd.Categorical(atestados_mes['Mês'], categories=ordem_meses, ordered=True)
    atestados_mes = atestados_mes.sort_values('Mês')

    fig1 = px.bar(atestados_mes, x='Mês', y='Quantidade', text='Quantidade')

    fig1.update_traces(textposition='outside', marker_color='#4dabf7')

    fig1.update_layout(
        title="Atestados por Mês",
        xaxis_title="Mês",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="white"
    )

    fig1.update_xaxes(showgrid=False)
    fig1.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")

    st.plotly_chart(fig1, use_container_width=True)

    # ---------------- GRÁFICO 2: COLABORADORES POR MÊS ----------------
    base_meses = pd.DataFrame({'Mês': ordem_meses})

    pessoas_mes = df_filtrado.groupby('MES')['MATRÍCULA'].nunique().reset_index()
    pessoas_mes.columns = ['Mês', 'Quantidade']

    pessoas_mes = base_meses.merge(pessoas_mes, on='Mês', how='left').fillna(0)
    pessoas_mes['Quantidade'] = pessoas_mes['Quantidade'].astype(int)
    pessoas_mes['Mês'] = pd.Categorical(pessoas_mes['Mês'], categories=ordem_meses, ordered=True)
    pessoas_mes = pessoas_mes.sort_values('Mês')

    fig2 = px.bar(pessoas_mes, x='Mês', y='Quantidade', text='Quantidade')

    fig2.update_traces(textposition='outside', marker_color='#ff6b6b')

    fig2.update_layout(
        title="Colaboradores Afastados por Mês",
        xaxis_title="Mês",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="white"
    )

    fig2.update_xaxes(showgrid=False)
    fig2.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")

    st.plotly_chart(fig2, use_container_width=True)

    # ---------------- TOP 10 CID + FUNÇÕES + DIVISÃO ----------------
    st.markdown("---")

    col_vazio1, col_cid, col_func, col_div, col_vazio2 = st.columns([0.5, 1, 2, 4, 0.5])

    with col_cid:
        st.subheader("Top 10 CID")

        cid_series = df_filtrado['CID'].astype(str).str.strip()
        cid_series = cid_series[cid_series.str.upper() != "NAN"]
        cid_series = cid_series[cid_series != ""]

        top_cid = cid_series.value_counts().head(10).reset_index()
        top_cid.columns = ['CID', 'Quantidade']
        top_cid.index = range(1, len(top_cid) + 1)


        st.dataframe(
            top_cid,
            use_container_width=False,
            width=200
        )

    with col_func:
        st.subheader("Top 10 Funções")

        func_series = df_filtrado['FUNÇÃO'].astype(str).str.strip()
        func_series = func_series[func_series.str.upper() != "NAN"]
        func_series = func_series[func_series != ""]

        top_func = func_series.value_counts().head(10).reset_index()
        top_func.columns = ['Função', 'Quantidade']
        top_func.index = range(1, len(top_func) + 1)

        st.dataframe(
            top_func,
            use_container_width=False,
            width=500
        )

    with col_div:
        st.subheader("Atestados por Divisão")

        div_series = df_filtrado['DIVISAO'].astype(str).str.strip()
        div_series = div_series[div_series.str.upper() != "NAN"]
        div_series = div_series[div_series != ""]

        ranking_div = div_series.value_counts().reset_index()
        ranking_div.columns = ['Divisão', 'Quantidade']

        ordem_div = ['DIV. DE ENFERMAGEM', 'DIV. MÉDICA', 'DIV. MULTIDISCIPLINAR', 'HIGIENE', 'OUTROS']

        ranking_div['Divisão'] = pd.Categorical(
            ranking_div['Divisão'],
            categories=ordem_div,
            ordered=True
        )

        ranking_div = ranking_div.sort_values('Divisão')

        fig_div = px.bar(
            ranking_div,
            x='Quantidade',
            y='Divisão',
            orientation='h',
            text='Quantidade'
        )

        fig_div.update_traces(
            textposition='outside',
            marker_color='#a78bfa'
        )

        fig_div.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color="white",
            yaxis=dict(autorange="reversed"),
            xaxis_title="",
            yaxis_title="",
            margin=dict(l=10, r=10, t=10, b=10),
            height=350
        )

        fig_div.update_xaxes(showgrid=False)
        fig_div.update_yaxes(showgrid=False)

        st.plotly_chart(fig_div, use_container_width=True)