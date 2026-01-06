import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURAÇÕES ---
ABAS_MAQUINAS = ["Fagor", "Esquadros", "Marafon", "Divimec (Slitter)", "Divimec (Rebaixamento)"]

st.set_page_config(page_title="Portal Vendedor Dox", page_icon="🏭", layout="wide")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_usuarios():
    """Lê a aba 'Usuarios' para validar login"""
    try:
        df_users = conn.read(worksheet="Usuarios", ttl=0)
        df_users = df_users.astype(str)
        return df_users
    except Exception as e:
        st.error(f"Erro ao carregar base de usuários: {e}")
        return pd.DataFrame()

def carregar_dados_pedidos():
    """Lê todas as abas de máquinas"""
    dados_consolidados = []
    
    for aba in ABAS_MAQUINAS:
        try:
            df = conn.read(worksheet=aba, ttl=0)
            df['Máquina/Processo'] = aba
            
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

# --- FUNÇÃO DE FORMATAÇÃO PERSONALIZADA (NOVA) ---
def formatar_peso_brasileiro(valor):
    """
    Recebe um número (ex: 1.0 ou 9.65) e retorna texto (ex: '1' ou '9,65')
    """
    try:
        if pd.isna(valor) or valor == "":
            return "0"
        
        # 1. Formata para ter 3 casas decimais fixas (ex: 9.6 -> "9.600")
        texto = f"{float(valor):.3f}"
        
        # 2. Troca ponto por vírgula (ex: "9.600" -> "9,600")
        texto = texto.replace('.', ',')
        
        # 3. Remove zeros à direita (ex: "9,600" -> "9,6")
        texto = texto.rstrip('0')
        
        # 4. Se sobrou uma vírgula no final (caso de inteiros), remove ela (ex: "1," -> "1")
        texto = texto.rstrip(',')
        
        return texto
    except:
        return str(valor)

# --- ESTADO DA SESSÃO (LOGIN) ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_nome'] = ""
    st.session_state['usuario_filtro'] = ""
    st.session_state['usuario_tipo'] = ""

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
                usuario_encontrado = df_users[
                    (df_users['Login'].str.lower() == usuario_input.lower()) & 
                    (df_users['Senha'] == senha_input)
                ]
                
                if not usuario_encontrado.empty:
                    dados_user = usuario_encontrado.iloc[0]
                    st.session_state['logado'] = True
                    # Pega apenas o primeiro nome para a saudação
                    st.session_state['usuario_nome'] = dados_user['Nome Vendedor'].split()[0]
                    st.session_state['usuario_filtro'] = dados_user['Nome Vendedor']
                    st.session_state['usuario_tipo'] = dados_user['Tipo']
                    st.rerun()
                else:
                    st.error("Login ou Senha incorretos.")
            else:
                st.error("Erro ao conectar com base de usuários.")

# --- TELA PRINCIPAL (LOGADO) ---
else:
    with st.sidebar:
        st.write(f"Bem-vindo, **{st.session_state['usuario_nome'].upper()}**")
        
        if st.button("Sair"):
            st.session_state['logado'] = False
            st.session_state['usuario_nome'] = ""
            st.session_state['usuario_filtro'] = ""
            st.rerun()
        
        st.divider()
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()
        
        st.caption("Dados atualizados conforme planilha do PCP.")

    # Título da Página
    st.title(f"🏭 Carteira de Pedidos: {st.session_state['usuario_nome']}")

    # Carrega Dados
    df_total = carregar_dados_pedidos()

    if df_total is not None and not df_total.empty:
        
        # Filtros de Segurança
        usuario_eh_admin = st.session_state['usuario_tipo'].lower() == "admin"
        
        if usuario_eh_admin:
            vendedores_unicos = sorted(df_total["Vendedor Correto"].dropna().astype(str).unique())
            filtro_vendedor = st.selectbox("Filtrar Vendedor (Visão Admin)", ["Todos"] + vendedores_unicos)
            
            if filtro_vendedor != "Todos":
                df_filtrado = df_total[df_total["Vendedor Correto"].astype(str) == filtro_vendedor].copy()
            else:
                df_filtrado = df_total.copy()
        else:
            # Vendedor Comum: Filtra pelo nome dele
            nome_para_filtrar = st.session_state['usuario_filtro']
            df_filtrado = df_total[df_total["Vendedor Correto"].astype(str).str.lower() == nome_para_filtrar.lower()].copy()

        # Exibe se estiver vazio
        if df_filtrado.empty:
            st.info(f"Nenhum pedido pendente encontrado na sua carteira.")
        else:
            # --- APLICAÇÃO DAS SUAS SOLICITAÇÕES ---
            
            # 1. Converte a coluna Quantidade para número para somar no KPI
            df_filtrado['Quantidade_Num'] = pd.to_numeric(df_filtrado['Quantidade'], errors='coerce').fillna(0)
            
            # 2. Cria uma coluna NOVA formatada como TEXTO (para ficar exatamente como você quer: 9,6)
            df_filtrado['Peso (ton)'] = df_filtrado['Quantidade_Num'].apply(formatar_peso_brasileiro)
            
            # 3. Remove a coluna do Vendedor se NÃO for Admin
            if not usuario_eh_admin:
                if "Vendedor Correto" in df_filtrado.columns:
                    df_filtrado = df_filtrado.drop(columns=["Vendedor Correto"])
            
            # 4. Remove colunas auxiliares que usamos só para conta
            if "Quantidade" in df_filtrado.columns:
                df_filtrado = df_filtrado.drop(columns=["Quantidade"])
            
            # --- CARDS DE KPI ---
            total_pedidos = len(df_filtrado)
            total_peso = df_filtrado['Quantidade_Num'].sum()
            # Formata o total do KPI também (ex: 1.234,56)
            total_peso_str = f"{total_peso:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            kpi1, kpi2 = st.columns(2)
            kpi1.metric("📦 Pedidos Pendentes", total_pedidos)
            kpi2.metric("⚖️ Peso Total (Tons)", total_peso_str)
            
            st.divider()
            
            # Filtro de Máquina
            maquinas_disponiveis = df_filtrado['Máquina/Processo'].unique()
            maquina_sel = st.multiselect("Filtrar por Processo:", maquinas_disponiveis, default=maquinas_disponiveis)
            
            df_final = df_filtrado[df_filtrado['Máquina/Processo'].isin(maquina_sel)]
            
            # Remove a coluna auxiliar numérica antes de mostrar a tabela
            df_final = df_final.drop(columns=['Quantidade_Num'])

            # --- TABELA FINAL ---
            st.dataframe(
                df_final, 
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Prazo": st.column_config.DateColumn("Previsão", format="DD/MM/YYYY"),
                    # Não configuramos "Peso (ton)" aqui porque ele já foi formatado como texto na mão
                }
            )
    else:
        st.error("Não foi possível carregar a planilha de pedidos. Verifique se o arquivo existe ou a conexão.")