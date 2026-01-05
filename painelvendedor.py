import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURAÇÕES ---
# O link da planilha já está nos Secrets, então não precisamos por aqui se usarmos a conexão padrão.
# Mas para garantir, o código abaixo usa a conexão configurada nos secrets.

ABAS_MAQUINAS = ["Fagor", "Esquadros", "Marafon", "Divimec (Slitter)", "Divimec (Rebaixamento)"]

st.set_page_config(page_title="Portal Vendedor Dox", page_icon="🏭", layout="wide")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_usuarios():
    """Lê a aba 'Usuarios' para validar login"""
    try:
        # ttl=0 garante que ele não use cache antigo (importante se você mudar a senha de alguém)
        df_users = conn.read(worksheet="Usuarios", ttl=0)
        # Garante que as colunas sejam tratadas como texto (evita erro se a senha for só numeros)
        df_users = df_users.astype(str)
        return df_users
    except Exception as e:
        st.error(f"Erro ao carregar base de usuários: {e}")
        return pd.DataFrame()

def carregar_dados_pedidos():
    """Lê todas as abas de máquinas"""
    dados_consolidados = []
    
    # ttl=600 faz o cache durar 10 min para ficar rápido. 
    # Se quiser dados em tempo real sempre, mude para ttl=0 (mas fica mais lento)
    for aba in ABAS_MAQUINAS:
        try:
            df = conn.read(worksheet=aba, ttl=0)
            
            # Adiciona identificador da máquina
            df['Máquina/Processo'] = aba
            
            # Filtra colunas essenciais
            cols_necessarias = ["Número do Pedido", "Cliente Correto", "Produto", "Quantidade", "Prazo", "Vendedor Correto"]
            cols_existentes = [c for c in cols_necessarias if c in df.columns]
            
            if "Vendedor Correto" in cols_existentes:
                df_limpo = df[cols_existentes + ['Máquina/Processo']].copy()
                dados_consolidados.append(df_limpo)
        except Exception:
            continue
            
    if dados_consolidados:
        return pd.concat(dados_consolidados, ignore_index=True)
    return pd.DataFrame()

# --- ESTADO DA SESSÃO (LOGIN) ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_nome'] = ""   # Nome de exibição
    st.session_state['usuario_filtro'] = "" # Nome para filtrar na planilha
    st.session_state['usuario_tipo'] = ""   # Admin ou Vendedor

# --- TELA DE LOGIN ---
if not st.session_state['logado']:
    st.title("🔒 Login - PCP Dox Brasil")
    st.markdown("Entre com suas credenciais para visualizar sua carteira.")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        usuario_input = st.text_input("Login").strip()
        senha_input = st.text_input("Senha", type="password").strip()
        
        if st.button("Acessar Sistema"):
            df_users = carregar_usuarios()
            
            if not df_users.empty:
                # Procura o usuário e senha exatos
                usuario_encontrado = df_users[
                    (df_users['Login'].str.lower() == usuario_input.lower()) & 
                    (df_users['Senha'] == senha_input)
                ]
                
                if not usuario_encontrado.empty:
                    # Login Sucesso! Pega os dados da linha encontrada
                    dados_user = usuario_encontrado.iloc[0]
                    
                    st.session_state['logado'] = True
                    st.session_state['usuario_nome'] = dados_user['Nome Vendedor'].split()[0]
                    st.session_state['usuario_filtro'] = dados_user['Nome Vendedor'] # O nome que está na planilha de pedidos
                    st.session_state['usuario_tipo'] = dados_user['Tipo'] # Admin ou Vendedor
                    st.rerun()
                else:
                    st.error("Login ou Senha incorretos.")
            else:
                st.error("Erro ao conectar com base de usuários.")

# --- TELA PRINCIPAL (LOGADO) ---
else:
    # Barra Lateral
    with st.sidebar:
        st.write(f"Olá, **{st.session_state['usuario_nome'].upper()}**")
        st.caption(f"Perfil: {st.session_state['usuario_tipo']}")
        
        if st.button("Sair / Logout"):
            st.session_state['logado'] = False
            st.session_state['usuario_nome'] = ""
            st.session_state['usuario_filtro'] = ""
            st.rerun()
        
        st.divider()
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

    # Título
    st.title(f"🏭 Carteira de Pedidos: {st.session_state['usuario_filtro']}")

    # Carrega Dados
    df_total = carregar_dados_pedidos()

    if df_total is not None and not df_total.empty:
        
        # --- LÓGICA DE FILTRO (SEGURANÇA) ---
        if st.session_state['usuario_tipo'].lower() == "admin":
            # Se for Admin, mostra tudo, mas permite filtrar por vendedor se quiser
            vendedores_unicos = sorted(df_total["Vendedor Correto"].dropna().astype(str).unique())
            filtro_vendedor = st.selectbox("Filtrar Vendedor (Admin)", ["Todos"] + vendedores_unicos)
            
            if filtro_vendedor != "Todos":
                df_filtrado = df_total[df_total["Vendedor Correto"].astype(str) == filtro_vendedor]
            else:
                df_filtrado = df_total
        else:
            # Se for Vendedor, OBRIGA o filtro pelo nome cadastrado na aba Usuarios
            nome_para_filtrar = st.session_state['usuario_filtro']
            # Filtro insensível a maiúsculas/minúsculas para evitar erro de digitação
            df_filtrado = df_total[df_total["Vendedor Correto"].astype(str).str.lower() == nome_para_filtrar.lower()]

        # --- EXIBIÇÃO ---
        if df_filtrado.empty:
            st.info(f"Nenhum pedido pendente encontrado para: {st.session_state['usuario_filtro']}")
        else:
            # Tratamento numérico
            df_filtrado['Quantidade'] = pd.to_numeric(df_filtrado['Quantidade'], errors='coerce').fillna(0)
            
            # Cards de Resumo
            total_pedidos = len(df_filtrado)
            total_peso = df_filtrado['Quantidade'].sum()

            kpi1, kpi2 = st.columns(2)
            kpi1.metric("📦 Pedidos em Carteira", total_pedidos)
            kpi2.metric("⚖️ Volume Total (Tons)", f"{total_peso:,.3f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            st.divider()
            
            # Filtro de Máquina na tela
            maquinas_disponiveis = df_filtrado['Máquina/Processo'].unique()
            maquina_sel = st.multiselect("Filtrar por Processo:", maquinas_disponiveis, default=maquinas_disponiveis)
            
            df_final = df_filtrado[df_filtrado['Máquina/Processo'].isin(maquina_sel)]
            
            # Tabela
            st.dataframe(
                df_final, 
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Quantidade": st.column_config.NumberColumn("Peso (ton)", format="%.3f"),
                    "Prazo": st.column_config.DateColumn("Previsão", format="DD/MM/YYYY"),
                }
            )
    else:
        st.error("Não foi possível carregar os pedidos. Verifique a planilha.")