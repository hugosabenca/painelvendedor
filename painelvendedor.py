import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(
    page_title="Painel do Vendedor Dox",
    page_icon="logodox.png",
    layout="wide"
)

# --- LOGO NO MENU ---
try:
    st.logo("logodox.png")
except Exception:
    pass 

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE CARREGAMENTO E SALVAMENTO ---

def carregar_usuarios():
    try:
        df_users = conn.read(worksheet="Usuarios", ttl=0)
        df_users = df_users.astype(str)
        return df_users
    except Exception as e:
        st.error(f"Erro ao carregar base de usuários. Verifique se a aba 'Usuarios' existe.")
        return pd.DataFrame()

def carregar_solicitacoes():
    try:
        df = conn.read(worksheet="Solicitacoes", ttl=0)
        return df
    except Exception:
        return pd.DataFrame(columns=["Nome", "Email", "Login", "Senha", "Data", "Status"])

def salvar_nova_solicitacao(nome, email, login, senha):
    try:
        df_existente = carregar_solicitacoes()
        nova_linha = pd.DataFrame([{
            "Nome": nome,
            "Email": email,
            "Login": login,
            "Senha": senha,
            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Status": "Pendente"
        }])
        df_final = pd.concat([df_existente, nova_linha], ignore_index=True)
        conn.update(worksheet="Solicitacoes", data=df_final)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar solicitação: {e}")
        return False

def carregar_dados_pedidos():
    ABAS_MAQUINAS = ["Fagor", "Esquadros", "Marafon", "Divimec (Slitter)", "Divimec (Rebaixamento)"]
    dados_consolidados = []
    
    for aba in ABAS_MAQUINAS:
        try:
            df = conn.read(worksheet=aba, ttl=0)
            df['Máquina/Processo'] = aba
            
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

# --- FUNÇÃO PRINCIPAL DE EXIBIÇÃO DA CARTEIRA ---
# Esta função isola toda a lógica de mostrar os pedidos.
# Assim podemos chamá-la dentro da aba do Admin ou na tela principal do Vendedor.
def exibir_carteira_pedidos():
    titulo_prefixo = "Carteira de Pedidos"
    if st.session_state['usuario_tipo'].lower() == "gerente":
        titulo_prefixo = "Gerência de Carteira"
    
    st.title(f"{titulo_prefixo}: {st.session_state['usuario_nome']}")

    df_total = carregar_dados_pedidos()

    if df_total is not None and not df_total.empty:
        
        # Limpeza
        df_total = df_total.dropna(subset=["Número do Pedido"])
        df_total = df_total[df_total["Número do Pedido"].astype(str).str.strip() != ""]
        df_total = df_total[~df_total["Número do Pedido"].astype(str).str.lower().isin(["none", "nan"])]

        # Filtros de Permissão
        tipo_usuario = st.session_state['usuario_tipo'].lower()
        nome_filtro = st.session_state['usuario_filtro']
        
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
            # Tratamento
            df_filtrado['Quantidade_Num'] = pd.to_numeric(df_filtrado['Quantidade'], errors='coerce').fillna(0)
            df_filtrado['Peso (ton)'] = df_filtrado['Quantidade_Num'].apply(formatar_peso_brasileiro)
            
            df_filtrado['Prazo'] = pd.to_datetime(df_filtrado['Prazo'], dayfirst=True, errors='coerce')
            df_filtrado['Prazo'] = df_filtrado['Prazo'].dt.strftime('%d/%m/%Y').fillna("-")

            colunas_visiveis = ["Número do Pedido", "Cliente Correto", "Produto", "Peso (ton)", "Prazo", "Máquina/Processo"]
            
            if tipo_usuario in ["admin", "gerente"]:
                colunas_visiveis.insert(5, "Vendedor Correto")
            
            colunas_finais = [c for c in colunas_visiveis if c in df_filtrado.columns]
            df_final = df_filtrado[colunas_finais]

            # KPIs
            total_pedidos = len(df_filtrado)
            total_peso = df_filtrado['Quantidade_Num'].sum()
            total_peso_str = f"{total_peso:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            kpi1, kpi2 = st.columns(2)
            kpi1.metric("Itens Programados:", total_pedidos)
            kpi2.metric("Volume Total (Tons):", total_peso_str)
            
            st.divider()
            
            # Filtro de Busca
            texto_busca = st.text_input("🔍 Filtro:", placeholder="Digite cliente, pedido, produto ou máquina...")

            if texto_busca:
                mask = df_final.astype(str).apply(
                    lambda x: x.str.contains(texto_busca, case=False, na=False)
                ).any(axis=1)
                df_exibicao = df_final[mask]
            else:
                df_exibicao = df_final

            # Tabela
            st.dataframe(
                df_exibicao, 
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Prazo": st.column_config.TextColumn("Previsão"),
                }
            )
            
            if texto_busca and df_exibicao.empty:
                st.warning(f"Nenhum resultado encontrado para '{texto_busca}'")
    else:
        st.error("Não foi possível carregar a planilha de pedidos.")


# --- GESTÃO DE ESTADO (SESSÃO) ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_nome'] = ""
    st.session_state['usuario_filtro'] = ""
    st.session_state['usuario_tipo'] = ""
if 'fazendo_cadastro' not in st.session_state:
    st.session_state['fazendo_cadastro'] = False

# ==============================================================================
# LÓGICA DE LOGIN E CADASTRO
# ==============================================================================
if not st.session_state['logado']:
    
    # --- TELA DE CADASTRO ---
    if st.session_state['fazendo_cadastro']:
        st.title("📝 Solicitação de Acesso")
        st.markdown("Preencha os dados abaixo. Seu cadastro passará por aprovação.")
        
        with st.form("form_cadastro"):
            nome_completo = st.text_input("Nome Completo")
            email_user = st.text_input("E-mail")
            novo_login = st.text_input("Crie um Login (Usuário)")
            nova_senha = st.text_input("Crie uma Senha", type="password")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                btn_enviar = st.form_submit_button("Enviar Solicitação", type="primary", use_container_width=True)
            with col_b2:
                btn_voltar = st.form_submit_button("Voltar para Login", use_container_width=True)

        if btn_voltar:
            st.session_state['fazendo_cadastro'] = False
            st.rerun()
            
        if btn_enviar:
            if not nome_completo or not email_user or not novo_login or not nova_senha:
                st.warning("Por favor, preencha todos os campos.")
            else:
                df_users = carregar_usuarios()
                login_existe = False
                if not df_users.empty and 'Login' in df_users.columns:
                     if novo_login.lower() in df_users['Login'].str.lower().values:
                         login_existe = True
                
                if login_existe:
                    st.error("Este login já está em uso por outro usuário. Escolha outro.")
                else:
                    df_solic = carregar_solicitacoes()
                    solic_existe = False
                    if not df_solic.empty and 'Login' in df_solic.columns:
                        if novo_login.lower() in df_solic['Login'].str.lower().values:
                            solic_existe = True
                    
                    if solic_existe:
                        st.warning("Já existe uma solicitação pendente para este login. Aguarde a aprovação.")
                    else:
                        sucesso = salvar_nova_solicitacao(nome_completo, email_user, novo_login, nova_senha)
                        if sucesso:
                            st.success("✅ Solicitação enviada com sucesso! Aguarde um e-mail informando quando seu cadastro estiver concluído.")
    
    # --- TELA DE LOGIN (PADRÃO) ---
    else:
        st.title("🔒 Login - Painel do Vendedor - Dox Brasil")
        st.markdown("Entre com suas credenciais para visualizar a carteira.")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            usuario_input = st.text_input("Login").strip()
            senha_input = st.text_input("Senha", type="password").strip()
            
            if st.button("Acessar Sistema", type="primary"):
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
            
            st.markdown("---")
            if st.button("Não tem acesso? Solicite aqui"):
                st.session_state['fazendo_cadastro'] = True
                st.rerun()

# ==============================================================================
# ÁREA LOGADA (DASHBOARD)
# ==============================================================================
else:
    # --- BARRA LATERAL ---
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

    # --- DEFINIÇÃO DO CONTEÚDO PRINCIPAL ---
    
    # SE FOR ADMIN: MOSTRA ABAS
    if st.session_state['usuario_tipo'].lower() == "admin":
        aba1, aba2 = st.tabs(["📂 Carteira de Pedidos", "📝 Solicitações de Acesso"])
        
        # ABA 1: Chama a função que desenha a carteira
        with aba1:
            exibir_carteira_pedidos()
        
        # ABA 2: Gestão de Cadastros
        with aba2:
            st.subheader("Gerenciamento de Solicitações de Cadastro")
            st.info("Aqui estão os usuários que pediram acesso pelo site. Copie os dados para a aba 'Usuarios' do Excel para aprovar.")
            
            df_solicitacoes = carregar_solicitacoes()
            if not df_solicitacoes.empty:
                st.dataframe(df_solicitacoes, use_container_width=True)
                
                if st.button("Atualizar Lista de Solicitações"):
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.info("Nenhuma solicitação pendente no momento.")

    # SE NÃO FOR ADMIN: MOSTRA DIRETO A CARTEIRA
    else:
        exibir_carteira_pedidos()