import streamlit as st

# Configuração da página centralizada
st.set_page_config(page_title="Painel Dox - Mudamos de Endereço", layout="centered")

# CSS para esconder menus e remover o espaço em branco excessivo do topo
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Força o conteúdo a subir, reduzindo a margem padrão do Streamlit */
        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 2rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Colunas para manter o conteúdo central e organizado
col1, col2, col3 = st.columns([1, 8, 1])

with col2:
    st.image("https://emojicdn.elk.sh/⚠️", width=80) 
    st.title("Mudamos de Endereço!")
    
    st.warning("Este link antigo será desativado em breve.")
    
    st.markdown("""
    ### O Painel do Vendedor agora é **Painel Dox**.
    
    Por favor, atualize seus favoritos e acesse o novo link clicando no botão abaixo:
    """)
    
    st.write("") # Pequeno espaço estético
    
    # Botão Grande de Acesso
    st.link_button("👉 ACESSAR O NOVO PAINEL DOX", "https://paineldox.streamlit.app/", type="primary", use_container_width=True)