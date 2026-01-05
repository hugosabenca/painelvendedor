import streamlit as st
import pandas as pd
import os
import shutil
import time

# --- CONFIGURAÇÕES ---
ARQUIVO_PEDIDOS = "pedidos.xlsx"  # Nome exato do seu arquivo
ABAS_MAQUINAS = ["Fagor", "Esquadros", "Marafon", "Divimec (Slitter)", "Divimec (Rebaixamento)"]

# Simulando um banco de usuários e senhas (no futuro pode vir do SQL ou arquivo seguro)
USUARIOS = {
    "rodrigo": "1234",
    "bassan": "1234",
    "bispo": "1234",
    "hugo": "admin"  # Você veria tudo
}

# --- FUNÇÕES ---
def carregar_dados_seguro():
    """Lê a planilha fazendo cópia temporária para evitar erro de permissão"""
    if not os.path.exists(ARQUIVO_PEDIDOS):
        return None
    
    # Cria cópia temporária
    temp_file = f"temp_stream_{int(time.time())}.xlsx"
    shutil.copy2(ARQUIVO_PEDIDOS, temp_file)
    
    dados_consolidados = []
    
    try:
        # Lê todas as abas definidas
        for aba in ABAS_MAQUINAS:
            try:
                df = pd.read_excel(temp_file, sheet_name=aba)
                # Adiciona coluna da máquina para saber de onde veio
                df['Máquina/Processo'] = aba
                
                # Garante que as colunas essenciais existam
                cols_necessarias = ["Número do Pedido", "Cliente Correto", "Produto", "Quantidade", "Prazo", "Vendedor Correto"]
                # Filtra só colunas que existem para evitar erro
                cols_existentes = [c for c in cols_necessarias if c in df.columns]
                
                if "Vendedor Correto" in cols_existentes: # Só processa se tiver vendedor
                    df_limpo = df[cols_existentes + ['Máquina/Processo']].copy()
                    dados_consolidados.append(df_limpo)
            except Exception as e:
                continue # Pula aba se der erro ou não existir
                
        if dados_consolidados:
            return pd.concat(dados_consolidados, ignore_index=True)
        return pd.DataFrame()
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# --- INTERFACE ---
st.set_page_config(page_title="Portal Vendedor Dox", page_icon="🏭", layout="wide")

# Lógica de Login Simples
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
    # --- ÁREA LOGADA ---
    usuario_logado = st.session_state['usuario_atual']
    
    # Barra lateral
    with st.sidebar:
        st.write(f"Bem-vindo, **{usuario_logado.upper()}**")
        if st.button("Sair"):
            st.session_state['logado'] = False
            st.rerun()
        st.divider()
        st.info("Dados atualizados conforme planilha do PCP.")

    st.title(f"🏭 Carteira de Pedidos: {usuario_logado.capitalize()}")

    # Carrega dados
    df_total = carregar_dados_seguro()

    if df_total is not None and not df_total.empty:
        # Filtra pelo vendedor logado
        if usuario_logado == "hugo": # Admin vê tudo
            df_filtrado = df_total
        else:
            # Filtro insensível a maiúsculas/minúsculas
            df_filtrado = df_total[df_total["Vendedor Correto"].astype(str).str.lower() == usuario_logado]

        if df_filtrado.empty:
            st.warning("Nenhum pedido pendente encontrado para sua carteira.")
        else:
            # Formatação de Datas
            df_filtrado['Prazo'] = pd.to_datetime(df_filtrado['Prazo'], errors='coerce').dt.strftime('%d/%m/%Y')
            
            # KPI's (Indicadores)
            total_pedidos = len(df_filtrado)
            total_peso = pd.to_numeric(df_filtrado['Quantidade'], errors='coerce').sum()

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Pedidos em Carteira", total_pedidos)
            kpi2.metric("Volume Total (Tons)", f"{total_peso:,.3f}")
            
            st.divider()
            
            # Filtros na tela
            maquina_filtro = st.multiselect("Filtrar por Máquina", options=df_filtrado['Máquina/Processo'].unique())
            if maquina_filtro:
                df_filtrado = df_filtrado[df_filtrado['Máquina/Processo'].isin(maquina_filtro)]

            # Exibe a Tabela
            st.dataframe(
                df_filtrado, 
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Quantidade": st.column_config.NumberColumn("Peso (ton)", format="%.3f"),
                }
            )
    else:
        st.error("Erro ao carregar a planilha de pedidos. Verifique se o arquivo existe.")