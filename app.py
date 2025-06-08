import streamlit as st
import pandas as pd
from datetime import datetime
import openai
import os
import json
import time

# Configuração da página
st.set_page_config(
    page_title="Tenda dos Pequenos",
    page_icon="📖",
    layout="wide"
)

# Configurar OpenAI (usando secrets do Streamlit)
try:
    from openai import OpenAI
    
    # Debug: verificar se a secret existe
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        st.success(f"✅ API Key encontrada: {api_key[:10]}...")
        
        # Usar versão mais simples do client
        client = OpenAI(
            api_key=api_key
        )
        ASSISTANT_ID = "asst_QeV7hQfMyuvrXS4zk41pbkTF"
        st.success("✅ Cliente OpenAI configurado com sucesso!")
        
    else:
        st.error("❌ OPENAI_API_KEY não encontrada nas secrets")
        st.write("Secrets disponíveis:", list(st.secrets.keys()))
        st.stop()
        
except Exception as e:
    st.error(f"Erro ao configurar OpenAI: {e}")
    
    # Fallback: tentar importação alternativa
    try:
        import openai
        openai.api_key = st.secrets["OPENAI_API_KEY"]
        st.warning("⚠️ Usando método alternativo do OpenAI")
        client = None  # Vamos usar o método antigo
        ASSISTANT_ID = "asst_QeV7hQfMyuvrXS4zk41pbkTF"
    except:
        st.error("Não foi possível configurar OpenAI de forma alguma")
        st.stop()

# Função para chamar o Assistant
def generate_episodes(num_episodes):
    try:
        if client is None:
            # Usar método antigo
            import openai
            
            # Criar thread
            thread = openai.beta.threads.create()
            
            # Enviar mensagem
            message = openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"Gere {num_episodes} ideias de episódios bíblicos infantis"
            )
            
            # Executar Assistant
            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )
            
            # Aguardar resposta
            while run.status in ['queued', 'in_progress']:
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                # Buscar mensagens
                messages = openai.beta.threads.messages.list(
                    thread_id=thread.id
                )
                
                response = messages.data[0].content[0].text.value
                
                # Tentar parsear JSON
                try:
                    episodes = json.loads(response)
                    if isinstance(episodes, dict):
                        episodes = [episodes]
                    return episodes
                except:
                    st.error("Erro ao processar resposta do Assistant")
                    return []
            else:
                st.error(f"Erro no Assistant: {run.status}")
                return []
        else:
            # Usar método novo (se client funcionar)
            thread = client.beta.threads.create()
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"Gere {num_episodes} ideias de episódios bíblicos infantis"
            )
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )
            
            while run.status in ['queued', 'in_progress']:
                time.sleep(1)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                response = messages.data[0].content[0].text.value
                try:
                    episodes = json.loads(response)
                    if isinstance(episodes, dict):
                        episodes = [episodes]
                    return episodes
                except:
                    return []
            return []
            
    except Exception as e:
        st.error(f"Erro ao conectar com OpenAI: {e}")
        return []

# Título principal
st.title("📖 Tenda dos Pequenos - Sistema de Vídeos Bíblicos")
st.markdown("---")

# Sidebar para navegação
st.sidebar.title("Navegação")
tab_selected = st.sidebar.selectbox(
    "Escolha uma aba:",
    ["Episódios", "Personagens Visuais", "Cenas"]
)

# Aba 1: Episódios
if tab_selected == "Episódios":
    st.header("📚 Ideias de Episódios")
    
    # Input para gerar novas ideias
    col1, col2 = st.columns([3, 1])
    with col1:
        num_ideias = st.number_input("Quantas novas ideias gerar?", min_value=0, max_value=10, value=0)
    with col2:
        if st.button("Gerar Episódios", type="primary"):
            if num_ideias > 0:
                with st.spinner(f"Gerando {num_ideias} novas ideias com OpenAI Assistant..."):
                    new_episodes = generate_episodes(num_ideias)
                    if new_episodes:
                        st.success(f"✅ {len(new_episodes)} episódios gerados!")
                        
                        # Exibir episódios gerados
                        for ep in new_episodes:
                            with st.expander(f"🆕 {ep.get('episodio', 'Novo Episódio')}"):
                                st.write(f"**Descrição:** {ep.get('descricao', '')}")
                                st.write(f"**Moral:** {ep.get('moral', '')}")
                                st.write("**Status:** Aguardando Aprovação")
                    else:
                        st.error("Erro ao gerar episódios")
            else:
                st.warning("Digite um número maior que 0")
    
    st.markdown("---")
    
    # Exemplo de episódios
    episodios_exemplo = [
        {
            "Episódio": "A Fé de Daniel",
            "Descrição": "Daniel enfrenta os leões com coragem e fé",
            "Moral": "A fé em Deus nos dá coragem",
            "Status": "Aguardando Aprovação"
        },
        {
            "Episódio": "Noé e a Arca",
            "Descrição": "Noé obedece a Deus e salva os animais",
            "Moral": "Obediência traz bênçãos",
            "Status": "Approved"
        }
    ]
    
    # Exibir episódios
    for i, ep in enumerate(episodios_exemplo):
        with st.expander(f"📖 {ep['Episódio']}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Descrição:** {ep['Descrição']}")
                st.write(f"**Moral:** {ep['Moral']}")
            
            with col2:
                status = st.selectbox(
                    "Status:",
                    ["Aguardando Aprovação", "Approved", "Pendente"],
                    index=["Aguardando Aprovação", "Approved", "Pendente"].index(ep['Status']),
                    key=f"status_{i}"
                )
                
                if status == "Approved":
                    st.success("✅ Aprovado")
                elif status == "Pendente":
                    st.warning("⏳ Pendente")
                else:
                    st.info("⏰ Aguardando")

# Aba 2: Personagens Visuais
elif tab_selected == "Personagens Visuais":
    st.header("👥 Personagens Visuais")
    
    # Exemplo de personagens
    personagens_exemplo = [
        {
            "Nome": "Daniel",
            "Papel": "Protagonista corajoso",
            "Descrição": "Jovem hebreu de túnica azul, cabelos castanhos",
            "Status": "Approved",
            "Imagem": "https://via.placeholder.com/300x300/4CAF50/white?text=Daniel"
        },
        {
            "Nome": "Leão",
            "Papel": "Desafio de Daniel",
            "Descrição": "Leão majestoso mas dócil, juba dourada",
            "Status": "Pendente",
            "Imagem": "https://via.placeholder.com/300x300/FF9800/white?text=Leao"
        }
    ]
    
    for i, personagem in enumerate(personagens_exemplo):
        with st.expander(f"👤 {personagem['Nome']} - {personagem['Papel']}"):
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                st.image(personagem['Imagem'], caption=personagem['Nome'], width=200)
            
            with col2:
                st.write(f"**Papel:** {personagem['Papel']}")
                st.write(f"**Descrição:** {personagem['Descrição']}")
                
                # Campo para updates
                update_text = st.text_area(
                    "Atualizações/Correções:",
                    placeholder="Digite aqui se precisar de ajustes...",
                    key=f"update_{i}"
                )
            
            with col3:
                status = st.selectbox(
                    "Status:",
                    ["Gerando imagem", "Approved", "Pendente", "Rejected"],
                    index=["Gerando imagem", "Approved", "Pendente", "Rejected"].index(personagem['Status']),
                    key=f"char_status_{i}"
                )
                
                if status == "Approved":
                    st.success("✅ Aprovado")
                elif status == "Rejected":
                    st.error("❌ Rejeitado")
                    if st.button(f"Regenerar {personagem['Nome']}", key=f"regen_{i}"):
                        st.info("Regenerando personagem...")
                elif status == "Gerando imagem":
                    st.info("🎨 Gerando...")
                else:
                    st.warning("⏳ Pendente")

# Aba 3: Cenas
elif tab_selected == "Cenas":
    st.header("🎬 Cenas do Episódio")
    
    # Seletor de episódio
    episodio_selecionado = st.selectbox(
        "Escolha um episódio:",
        ["01 - A Fé de Daniel", "02 - Noé e a Arca"]
    )
    
    st.subheader(f"Cenas de: {episodio_selecionado}")
    
    # Exemplo de cenas
    cenas_exemplo = [
        {
            "Nº": 1,
            "Descrição": "Daniel orando em seu quarto",
            "Personagens": "Daniel",
            "Narração": "Daniel sempre orava três vezes ao dia...",
            "Imagem1": "https://via.placeholder.com/400x300/2196F3/white?text=Daniel+Orando",
            "Imagem2": "https://via.placeholder.com/400x300/3F51B5/white?text=Quarto+Daniel"
        },
        {
            "Nº": 2,
            "Descrição": "Daniel sendo jogado na cova dos leões",
            "Personagens": "Daniel, Leões, Guardas",
            "Narração": "Os soldados jogaram Daniel na cova...",
            "Imagem1": "https://via.placeholder.com/400x300/FF5722/white?text=Cova+Leoes",
            "Imagem2": "https://via.placeholder.com/400x300/795548/white?text=Daniel+Corajoso"
        }
    ]
    
    for cena in cenas_exemplo:
        with st.expander(f"🎬 Cena {cena['Nº']}: {cena['Descrição']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.image(cena['Imagem1'], caption="Imagem 1", width=300)
            
            with col2:
                st.image(cena['Imagem2'], caption="Imagem 2", width=300)
            
            st.write(f"**Personagens:** {cena['Personagens']}")
            st.write(f"**Narração:** {cena['Narração']}")
    
    # Botão para gerar mais cenas
    if st.button("➕ Gerar Próximas 5 Cenas", type="primary"):
        st.success("Gerando novas cenas...")

# Footer
st.markdown("---")
st.markdown("🙏 **Tenda dos Pequenos** - Criando histórias bíblicas com amor e tecnologia")
