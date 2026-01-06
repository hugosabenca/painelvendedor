import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURAÇÕES ---
ABAS_MAQUINAS = ["Fagor", "Esquadros", "Marafon", "Divimec (Slitter)", "Divimec (Rebaixamento)"]

# 1. Configuração da Página com o Ícone da Dox na aba do navegador
st.set_page_config(
    page_title="Portal Vendedor Dox", 
    page_icon="logodox.png",  # Usa o logo na aba do navegador
    layout="wide"
)

# 2. Configuração do Logo no Menu Lateral (canto superior esquerdo)
try:
    st.logo("logodox.png")
except Exception:
    pass # Se não achar a imagem, ignora e segue sem logo

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
            
            # Colunas necessárias (incluindo Gerente)
            cols_necessarias = ["Número do Pedido", "Cliente Correto", "Produto", "Quantidade", "Prazo", "Vendedor Correto", "Gerente Correto"]
            cols_existentes = [c for c in cols_necessarias if c in df.columns]
            
            if "Vendedor Correto" in cols_existentes:
                df_limpo = df[cols_existentes + ['Máquina/Processo']].copy()
                dados_consolidados.append(df_limpo)
        except Exception:
            continue
            
    if dados_consolidados:
        return pd.concat(dados_consolidados, ignore_index=True)
    return pd.DataFrame()

# --- FUNÇÃO DE FORMATAÇÃO ---
def formatar_peso_brasileiro(valor):
    try:
        if pd.isna(valor) or valor == "": return "0"
        texto = f"{float(valor):.3f}"
        texto = texto.replace('.', ',')
        texto = texto.rstrip('0')
        texto = texto.rstrip(',')
        return texto
    except:
        return str(valor)

# --- ESTADO DA SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_nome'] = ""
    st.session_state['usuario_filtro'] = ""
    st.session_state['usuario_tipo'] = ""

# --- TELA DE LOGIN ---
if not st.session_state['logado']:
    st.title("🔒 Login - PCP Dox Brasil")
    st.markdown("Entre com suas credenciais para visualizar a carteira.")
    
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
                    st.session_state['usuario_nome'] = dados_user['Nome Vendedor'].split()[0]
                    st.session_state['usuario_filtro'] = dados_user['Nome Vendedor']
                    st.session_state['usuario_tipo'] = dados_user['Tipo']
                    st.rerun()
                else:
                    st.error("Login ou Senha incorretos.")
            else:
                st.error("Erro ao conectar com base de usuários.")

# --- TELA PRINCIPAL ---
else:
    with st.sidebar:
        st.write(f"Bem-vindo, **{st.session_state['usuario_nome'].upper()}**")
        st.caption(f"Perfil: {st.session_state['usuario_tipo']}")
        
        if st.button("Sair"):
            st.session_state['logado'] = False
            st.session_state['usuario_nome'] = ""
            st.rerun()
        
        st.divider()
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

    titulo_prefixo = "Carteira de Pedidos"
    if st.session_state['usuario_tipo'].lower() == "gerente":
        titulo_prefixo = "Gerência de Carteira"
    
    st.title(f"🏭 {titulo_prefixo}: {st.session_state['usuario_nome']}")

    df_total = carregar_dados_pedidos()

    if df_total is not None and not df_total.empty:
        
        tipo_usuario = st.session_state['usuario_tipo'].lower()
        nome_filtro = st.session_state['usuario_filtro']
        
        # 1. Filtro de Permissão (Quem vê o quê)
        if tipo_usuario == "admin":
            vendedores_unicos = sorted(df_total["Vendedor Correto"].dropna().astype(str).unique())
            filtro_vendedor = st.selectbox("Filtrar Vendedor (Admin)", ["Todos"] + vendedores_unicos)
            
            if filtro_vendedor != "Todos":
                df_filtrado = df_total[df_total["Vendedor Correto"].astype(str) == filtro_vendedor].copy()
            else:
                df_filtrado = df_total.copy()
                
        elif tipo_usuario == "gerente":
            if "Gerente Correto" in df_total.columns:
                df_filtrado = df_total[df_total["Gerente Correto"].astype(str).str.lower() == nome_filtro.lower()].copy()
            else:
                df_filtrado = pd.DataFrame()
                
        else:
            df_filtrado = df_total[df_total["Vendedor Correto"].astype(str).str.lower() == nome_filtro.lower()].copy()

        if df_filtrado.empty:
            st.info(f"Nenhum pedido pendente encontrado.")
        else:
            # 2. Formatação e Seleção de Colunas
            df_filtrado['Quantidade_Num'] = pd.to_numeric(df_filtrado['Quantidade'], errors='coerce').fillna(0)
            df_filtrado['Peso (ton)'] = df_filtrado['Quantidade_Num'].apply(formatar_peso_brasileiro)
            
            # Ordem das colunas
            colunas_visiveis = ["Número do Pedido", "Cliente Correto", "Produto", "Peso (ton)", "Prazo", "Máquina/Processo"]
            
            if tipo_usuario in ["admin", "gerente"]:
                colunas_visiveis.insert(5, "Vendedor Correto")
            
            colunas_finais = [c for c in colunas_visiveis if c in df_filtrado.columns]
            df_final = df_filtrado[colunas_finais]

            # KPI Cards
            total_pedidos = len(df_filtrado)
            total_peso = df_filtrado['Quantidade_Num'].sum()
            total_peso_str = f"{total_peso:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            kpi1, kpi2 = st.columns(2)
            kpi1.metric("📦 Pedidos na Visão", total_pedidos)
            kpi2.metric("⚖️ Volume Total (Tons)", total_peso_str)
            
            st.divider()
            
            # --- 3. NOVO FILTRO DE BUSCA GERAL ---
            texto_busca = st.text_input("🔍 Filtro:", placeholder="Digite cliente, pedido, produto ou máquina...")

            if texto_busca:
                # Converte tudo para texto e busca em qualquer coluna
                # case=False faz ignorar maiuscula/minuscula
                mask = df_final.astype(str).apply(
                    lambda x: x.str.contains(texto_busca, case=False, na=False)
                ).any(axis=1)
                
                df_exibicao = df_final[mask]
            else:
                df_exibicao = df_final

            # 4. Tabela Final
            st.dataframe(
                df_exibicao, 
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Prazo": st.column_config.DateColumn("Previsão", format="DD/MM/YYYY"),
                }
            )
            
            if texto_busca and df_exibicao.empty:
                st.warning(f"Nenhum resultado encontrado para '{texto_busca}'")

    else:
        st.error("Não foi possível carregar a planilha de pedidos. Verifique se o arquivo existe.")