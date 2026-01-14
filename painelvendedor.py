import streamlit as st
import time

st.set_page_config(page_title="Painel Dox - Mudamos de Endereço", layout="centered")

# CSS para esconder menus e deixar limpo
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Espaço em branco para centralizar verticalmente
st.write("#")
st.write("#")

col1, col2, col3 = st.columns([1, 6, 1])

with col2:
    st.image("https://emojicdn.elk.sh/⚠️", width=100) # Ou sua logo
    st.title("Mudamos de Endereço!")
    
    st.warning("Este link antigo será desativado em breve.")
    
    st.markdown("""
    ### O Painel do Vendedor agora é **Painel Dox**.
    
    Por favor, atualize seus favoritos e acesse o novo link abaixo:
    """)
    
    st.write("#")
    
    # Botão Grande de Redirecionamento
    st.link_button("👉 ACESSAR O NOVO PAINEL DOX", "https://paineldox.streamlit.app/", type="primary", use_container_width=True)

    st.write("#")
    st.info("Você será redirecionado automaticamente em instantes...")

# Redirecionamento Automático via HTML/JS (Meta Refresh)
# Isso força o navegador a pular para o site novo após 3 segundos
st.markdown('<meta http-equiv="refresh" content="7; url=https://paineldox.streamlit.app/">', unsafe_allow_html=True)