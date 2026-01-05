import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURAÇÕES ---
# URL da sua planilha do Google (Copie do navegador e cole aqui entre aspas)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1wybd-IHYe05S002sZP3GQRUsqz06GGNaZoWBro8mzd8/edit?gid=0#gid=0"

ABAS_MAQUINAS = ["Fagor", "Esquadros", "Marafon", "Divimec (Slitter)", "Divimec (Rebaixamento)"]

# Usuários (Idealmente isso ficaria nos 'secrets' também, mas para facilitar manteremos aqui)
USUARIOS = {
    "rodrigo": "1234",
    "bassan": "1234",
    "bispo": "1234",
    "hugo": "admin"
}

st.set_page_config(page_title="Portal Vendedor Dox", page_icon="🏭", layout="wide")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados_google():
    dados_consolidados = []
    
    for aba in ABAS_MAQUINAS:
        try:
            # Lê a aba específica do Google Sheets
            df = conn.read(spreadsheet=URL_PLANILHA, worksheet=aba)
            
            # Adiciona identificador da máquina
            df['Máquina/Processo'] = aba
            
            # Filtra colunas essenciais
            cols_necessarias = ["Número do Pedido", "Cliente Correto", "Produto", "Quantidade", "Prazo", "Vendedor Correto"]
            cols_existentes = [c for c in cols_necessarias if c in df.columns]
            
            if "Vendedor Correto" in cols_existentes:
                df_limpo = df[cols_existentes + ['Máquina/Processo']].copy()
                dados_consolidados.append(df_limpo)
        except Exception as e:
            continue # Pula se a aba der erro
            
    if dados_consolidados:
        return pd.concat(dados_consolidados, ignore_index=True)
    return pd.DataFrame()

# --- INTERFACE ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_atual'] = ""

if not st.session_state['logado']:
    st.title("🔒 Login - PCP Dox Brasil")
    col1, col2 = st.columns([1, 2])
    with col1:
        usuario = st.text_input("Usuário").lower().strip()
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if usuario in USUARIOS and USUARIOS[usuario] == senha:
                st.session_state['logado'] = True
                st.session_state['usuario_atual'] = usuario
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
else:
    usuario_logado = st.session_state['usuario_atual']
    with st.sidebar:
        st.write(f"Bem-vindo, **{usuario_logado.upper()}**")
        if st.button("Sair"):
            st.session_state['logado'] = False
            st.rerun()
        if st.button("Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.info("Dados lidos diretamente do Google Sheets (PCP).")

    st.title(f"🏭 Carteira de Pedidos: {usuario_logado.capitalize()}")

    # Carrega dados
    try:
        df_total = carregar_dados_google()
    except Exception as e:
        st.error(f"Erro de conexão com Google Sheets. Verifique os Secrets.")
        st.stop()

    if df_total is not None and not df_total.empty:
        if usuario_logado == "hugo":
            df_filtrado = df_total
        else:
            df_filtrado = df_total[df_total["Vendedor Correto"].astype(str).str.lower() == usuario_logado]

        if df_filtrado.empty:
            st.warning("Nenhum pedido pendente encontrado para sua carteira.")
        else:
            # Tratamento de dados para exibição
            df_filtrado['Quantidade'] = pd.to_numeric(df_filtrado['Quantidade'], errors='coerce').fillna(0)
            
            total_pedidos = len(df_filtrado)
            total_peso = df_filtrado['Quantidade'].sum()

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Pedidos em Carteira", total_pedidos)
            kpi2.metric("Volume Total (Tons)", f"{total_peso:,.3f}")
            
            st.divider()
            
            st.dataframe(
                df_filtrado, 
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Quantidade": st.column_config.NumberColumn("Peso (ton)", format="%.3f"),
                }
            )
    else:
        st.error("Não foi possível carregar os dados das abas.")