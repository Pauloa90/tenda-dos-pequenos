import streamlit as st
import pandas as pd
from datetime import datetime
import openai
import json
import time
import gspread
from google.oauth2.service_account import Credentials

# Configuração da página
st.set_page_config(
    page_title="Tenda dos Pequenos",
    page_icon="📖",
    layout="wide"
)

# ID da planilha
SPREADSHEET_ID = "1USj7J6jVR387eVjxVDzy69404qaRcgjEfxclBv0U5M4"
ASSISTANT_ID = "asst_QeV7hQfMyuvrXS4zk41pbkTF"
PERSONAGENS_ASSISTANT_ID = "asst_C3jWk8RdgvwoVFFR8CK5jq6a"  # Diretor de Personagens

# Configurar Google Sheets
@st.cache_resource
def init_gsheet():
    try:
        # Usar credenciais do secrets
        creds_dict = dict(st.secrets["google_credentials"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID)
        return sheet
    except Exception as e:
        st.error(f"Erro ao conectar Google Sheets: {e}")
        return None

# Configurar OpenAI
try:
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        st.success(f"✅ API Key encontrada: {api_key[:10]}...")
        st.success("✅ OpenAI configurado com sucesso!")
        
    else:
        st.error("❌ OPENAI_API_KEY não encontrada nas secrets")
        st.stop()
        
except Exception as e:
    st.error(f"Erro ao configurar OpenAI: {e}")
    st.stop()

# Função para chamar o Assistant via requests direto
def generate_episodes(num_episodes):
    try:
        import requests
        
        api_key = st.secrets["OPENAI_API_KEY"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"
        }
        
        # Criar thread
        thread_response = requests.post(
            "https://api.openai.com/v1/threads",
            headers=headers,
            json={}
        )
        
        if thread_response.status_code != 200:
            st.error(f"Erro ao criar thread: {thread_response.text}")
            return []
            
        thread_id = thread_response.json()["id"]
        
        # Enviar mensagem
        message_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=headers,
            json={
                "role": "user",
                "content": f"Gere {num_episodes} ideias de episódios bíblicos infantis"
            }
        )
        
        if message_response.status_code != 200:
            st.error(f"Erro ao enviar mensagem: {message_response.text}")
            return []
        
        # Executar Assistant
        run_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/runs",
            headers=headers,
            json={
                "assistant_id": ASSISTANT_ID
            }
        )
        
        if run_response.status_code != 200:
            st.error(f"Erro ao executar assistant: {run_response.text}")
            return []
            
        run_id = run_response.json()["id"]
        
        # Aguardar conclusão
        max_attempts = 30
        for attempt in range(max_attempts):
            status_response = requests.get(
                f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}",
                headers=headers
            )
            
            if status_response.status_code != 200:
                st.error(f"Erro ao verificar status: {status_response.text}")
                return []
                
            status = status_response.json()["status"]
            
            if status == "completed":
                break
            elif status in ["failed", "cancelled", "expired"]:
                st.error(f"Assistant falhou: {status}")
                return []
            
            time.sleep(2)
        else:
            st.error("Timeout - Assistant demorou muito para responder")
            return []
        
        # Buscar resposta
        messages_response = requests.get(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=headers
        )
        
        if messages_response.status_code != 200:
            st.error(f"Erro ao buscar mensagens: {messages_response.text}")
            return []
            
        messages = messages_response.json()["data"]
        
        if not messages:
            st.error("Nenhuma resposta encontrada")
            return []
            
        response_text = messages[0]["content"][0]["text"]["value"]
        
        # Tentar parsear JSON
        try:
            # Limpar markdown se existir
            response_clean = response_text.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]  # Remove ```json
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]   # Remove ```
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]  # Remove ```
            response_clean = response_clean.strip()
            
            episodes = json.loads(response_clean)
            if isinstance(episodes, dict):
                episodes = [episodes]
            return episodes
        except json.JSONDecodeError as e:
            st.error(f"Erro ao processar JSON: {e}")
            st.text(f"Resposta limpa: {response_clean}")
            return []
            
    except Exception as e:
        st.error(f"Erro geral: {e}")
        return []

def generate_characters_for_episode(episode_title, episode_description, episode_moral):
    """Chama o Agent Diretor de Personagens para criar personagens"""
    try:
        import requests
        
        api_key = st.secrets["OPENAI_API_KEY"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"
        }
        
        # Criar thread
        thread_response = requests.post(
            "https://api.openai.com/v1/threads",
            headers=headers,
            json={}
        )
        
        if thread_response.status_code != 200:
            st.error(f"Erro ao criar thread para personagens: {thread_response.text}")
            return []
            
        thread_id = thread_response.json()["id"]
        
        # Prompt para o Diretor de Personagens
        prompt = f"""
        EPISÓDIO: {episode_title}
        DESCRIÇÃO: {episode_description}
        MORAL: {episode_moral}
        
        Analise este episódio e crie os personagens necessários (máximo 4).
        Para cada personagem, forneça:
        - Nome
        - Papel na história
        - Descrição física detalhada
        - Prompt para imagem (estilo 3D Pixar, fundo branco, corpo inteiro)
        
        Responda em JSON formato:
        [
          {
            "nome": "Nome do Personagem",
            "papel": "Protagonista/Coadjuvante/etc",
            "descricao": "Descrição física detalhada",
            "prompt_imagem": "Prompt específico para Midjourney",
            "status": "Pendente"
          }
        ]
        """
        
        # Enviar mensagem
        message_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=headers,
            json={
                "role": "user",
                "content": prompt
            }
        )
        
        if message_response.status_code != 200:
            st.error(f"Erro ao enviar mensagem para personagens: {message_response.text}")
            return []
        
        # Executar Assistant
        run_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/runs",
            headers=headers,
            json={
                "assistant_id": PERSONAGENS_ASSISTANT_ID
            }
        )
        
        if run_response.status_code != 200:
            st.error(f"Erro ao executar assistant de personagens: {run_response.text}")
            return []
            
        run_id = run_response.json()["id"]
        
        # Aguardar conclusão
        max_attempts = 30
        for attempt in range(max_attempts):
            status_response = requests.get(
                f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}",
                headers=headers
            )
            
            if status_response.status_code != 200:
                st.error(f"Erro ao verificar status de personagens: {status_response.text}")
                return []
                
            status = status_response.json()["status"]
            
            if status == "completed":
                break
            elif status in ["failed", "cancelled", "expired"]:
                st.error(f"Assistant de personagens falhou: {status}")
                return []
            
            time.sleep(2)
        else:
            st.error("Timeout - Diretor de Personagens demorou muito")
            return []
        
        # Buscar resposta
        messages_response = requests.get(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=headers
        )
        
        if messages_response.status_code != 200:
            st.error(f"Erro ao buscar mensagens de personagens: {messages_response.text}")
            return []
            
        messages = messages_response.json()["data"]
        
        if not messages:
            st.error("Nenhuma resposta do Diretor de Personagens")
            return []
            
        response_text = messages[0]["content"][0]["text"]["value"]
        
        # Limpar markdown e parsear JSON
        try:
            response_clean = response_text.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            response_clean = response_clean.strip()
            
            characters = json.loads(response_clean)
            return characters
        except json.JSONDecodeError as e:
            st.error(f"Erro ao processar JSON de personagens: {e}")
            st.text(f"Resposta recebida: {response_text}")
            return []
            
    except Exception as e:
        st.error(f"Erro geral no Diretor de Personagens: {e}")
        return []

def add_characters_to_sheet(characters, episode_title):
    """Adiciona personagens à aba Personagens do Google Sheets"""
    try:
        sheet = init_gsheet()
        if sheet is None:
            return False
            
        # Tentar acessar aba Personagens
        try:
            personagens_sheet = sheet.worksheet("Personagens")
        except:
            # Criar aba se não existir
            personagens_sheet = sheet.add_worksheet(title="Personagens", rows="100", cols="6")
            # Adicionar cabeçalho
            personagens_sheet.append_row(["Nome", "Papel", "Descrição", "Prompt Imagem", "Status", "Link"])
        
        # Adicionar cada personagem
        for char in characters:
            personagens_sheet.append_row([
                char.get('nome', ''),
                char.get('papel', ''),
                char.get('descricao', ''),
                char.get('prompt_imagem', ''),
                char.get('status', 'Pendente'),
                ''  # Link vazio inicialmente
            ])
        
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar personagens à planilha: {e}")
        return False

# Funcões Google Sheets
def get_episodes_from_sheet():
    try:
        sheet = init_gsheet()
        if sheet is None:
            return []
            
        # Aba Episodios
        episodios_sheet = sheet.worksheet("Episodios")
        data = episodios_sheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"Erro ao ler episódios: {e}")
        return []

def add_episodes_to_sheet(episodes):
    try:
        sheet = init_gsheet()
        if sheet is None:
            return False
            
        episodios_sheet = sheet.worksheet("Episodios")
        
        # Adicionar cada episódio
        for ep in episodes:
            episodios_sheet.append_row([
                ep.get('episodio', ''),
                ep.get('descricao', ''),
                ep.get('moral', ''),
                'Aguardando Aprovação'
            ])
        
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar episódios: {e}")
        return False

def update_episode_status(row_index, new_status, episode_data=None):
    try:
        sheet = init_gsheet()
        if sheet is None:
            return False
            
        episodios_sheet = sheet.worksheet("Episodios")
        episodios_sheet.update_cell(row_index + 2, 4, new_status)
        
        # Se episódio foi aprovado, gerar personagens
        if new_status == "Approved" and episode_data:
            st.info("🎭 Episódio aprovado! Gerando personagens...")
            
            with st.spinner("Criando personagens com Diretor de Personagens..."):
                characters = generate_characters_for_episode(
                    episode_data.get('Episódio', ''),
                    episode_data.get('Descrição Curta', ''),
                    episode_data.get('Moral', '')
                )
                
                if characters:
                    if add_characters_to_sheet(characters, episode_data.get('Episódio', '')):
                        st.success(f"✅ {len(characters)} personagens criados!")
                        # Mostrar personagens criados
                        for char in characters:
                            st.write(f"👤 **{char.get('nome')}** - {char.get('papel')}")
                    else:
                        st.error("Erro ao salvar personagens na planilha")
                else:
                    st.error("Erro ao gerar personagens")
        
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False

def get_personagens_from_sheet():
    try:
        sheet = init_gsheet()
        if sheet is None:
            return []
            
        personagens_sheet = sheet.worksheet("Personagens")
        data = personagens_sheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"Erro ao ler personagens: {e}")
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
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        num_ideias = st.number_input("Quantas novas ideias gerar?", min_value=0, max_value=10, value=0)
    with col2:
        if st.button("🎲 Gerar Episódios", type="primary"):
            if num_ideias > 0:
                with st.spinner(f"Gerando {num_ideias} novas ideias com OpenAI Assistant..."):
                    new_episodes = generate_episodes(num_ideias)
                    if new_episodes:
                        # Adicionar à planilha
                        if add_episodes_to_sheet(new_episodes):
                            st.success(f"✅ {len(new_episodes)} episódios gerados e salvos na planilha!")
                            st.rerun()  # Recarregar para mostrar novos dados
                        else:
                            st.error("Erro ao salvar na planilha")
                    else:
                        st.error("Erro ao gerar episódios")
            else:
                st.warning("Digite um número maior que 0")
    
    with col3:
        if st.button("🔄 Atualizar Lista"):
            st.rerun()
    
    st.markdown("---")
    
    # Carregar episódios da planilha
    episodes_data = get_episodes_from_sheet()
    
    if episodes_data:
        st.subheader(f"📋 Episódios na Planilha ({len(episodes_data)} total)")
        
        for i, ep in enumerate(episodes_data):
            with st.expander(f"📖 {ep.get('Episódio', 'Sem título')} - {ep.get('Status', 'Sem status')}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Descrição:** {ep.get('Descrição Curta', '')}")
                    st.write(f"**Moral:** {ep.get('Moral', '')}")
                
                with col2:
                    current_status = ep.get('Status', 'Aguardando Aprovação')
                    new_status = st.selectbox(
                        "Status:",
                        ["Aguardando Aprovação", "Approved", "Pendente", "Rejected"],
                        index=["Aguardando Aprovação", "Approved", "Pendente", "Rejected"].index(current_status) if current_status in ["Aguardando Aprovação", "Approved", "Pendente", "Rejected"] else 0,
                        key=f"status_{i}"
                    )
                    
                    if new_status != current_status:
                        if st.button(f"💾 Salvar Status", key=f"save_{i}"):
                            if update_episode_status(i, new_status, ep):  # Passa os dados do episódio
                                st.success("Status atualizado!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Erro ao atualizar")
                    
                    # Indicador visual do status
                    if new_status == "Approved":
                        st.success("✅ Aprovado")
                    elif new_status == "Rejected":
                        st.error("❌ Rejeitado")
                    elif new_status == "Pendente":
                        st.warning("⏳ Pendente")
                    else:
                        st.info("⏰ Aguardando")
    else:
        st.info("📝 Nenhum episódio encontrado. Gere algumas ideias para começar!")

# Aba 2: Personagens Visuais
elif tab_selected == "Personagens Visuais":
    st.header("👥 Personagens Visuais")
    
    # Carregar personagens da planilha
    personagens_data = get_personagens_from_sheet()
    
    if personagens_data:
        st.subheader(f"👤 Personagens na Planilha ({len(personagens_data)} total)")
        
        for i, personagem in enumerate(personagens_data):
            with st.expander(f"👤 {personagem.get('Nome', 'Sem nome')} - {personagem.get('Status', 'Sem status')}"):
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    # Tentar exibir imagem se houver link
                    img_link = personagem.get('Link Imagem', '')
                    if img_link and img_link.startswith('http'):
                        try:
                            st.image(img_link, caption=personagem.get('Nome', ''), width=200)
                        except:
                            st.write("🖼️ Imagem não disponível")
                    else:
                        st.write("🖼️ Aguardando imagem")
                
                with col2:
                    st.write(f"**Papel:** {personagem.get('Papel', '')}")
                    st.write(f"**Descrição:** {personagem.get('Descrição', '')}")
                    
                    # Campo para updates
                    update_text = st.text_area(
                        "Atualizações/Correções:",
                        placeholder="Digite aqui se precisar de ajustes...",
                        key=f"update_char_{i}"
                    )
                
                with col3:
                    current_status = personagem.get('Status', 'Pendente')
                    new_status = st.selectbox(
                        "Status:",
                        ["Gerando imagem", "Approved", "Pendente", "Rejected"],
                        index=["Gerando imagem", "Approved", "Pendente", "Rejected"].index(current_status) if current_status in ["Gerando imagem", "Approved", "Pendente", "Rejected"] else 2,
                        key=f"char_status_{i}"
                    )
                    
                    if new_status == "Approved":
                        st.success("✅ Aprovado")
                    elif new_status == "Rejected":
                        st.error("❌ Rejeitado")
                        if st.button(f"🔄 Regenerar", key=f"regen_{i}"):
                            st.info("🎨 Regenerando personagem...")
                    elif new_status == "Gerando imagem":
                        st.info("🎨 Gerando...")
                    else:
                        st.warning("⏳ Pendente")
    else:
        st.info("👥 Nenhum personagem encontrado. Os personagens são criados automaticamente quando um episódio é aprovado.")

# Aba 3: Cenas
elif tab_selected == "Cenas":
    st.header("🎬 Cenas do Episódio")
    
    # Buscar episódios aprovados
    episodes_data = get_episodes_from_sheet()
    approved_episodes = [ep for ep in episodes_data if ep.get('Status') == 'Approved']
    
    if approved_episodes:
        # Seletor de episódio
        episode_options = [f"{i+1:02d} - {ep.get('Episódio', 'Sem título')}" for i, ep in enumerate(approved_episodes)]
        episodio_selecionado = st.selectbox(
            "Escolha um episódio aprovado:",
            episode_options
        )
        
        if episodio_selecionado:
            st.subheader(f"🎬 Cenas de: {episodio_selecionado}")
            st.info("🚧 Sistema de cenas em desenvolvimento. Em breve você poderá visualizar e gerenciar as cenas aqui!")
            
            # Placeholder para cenas futuras
            st.markdown("### 📝 Próximas funcionalidades:")
            st.markdown("- ✅ Geração automática de 5 cenas por episódio")
            st.markdown("- ✅ Duas imagens por cena")
            st.markdown("- ✅ Narração personalizada")
            st.markdown("- ✅ Botão 'Próximas 5 cenas'")
    else:
        st.warning("⚠️ Nenhum episódio aprovado encontrado. Aprove pelo menos um episódio na aba 'Episódios' para gerar cenas.")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📚 Episódios", len(get_episodes_from_sheet()))
with col2:
    st.metric("👥 Personagens", len(get_personagens_from_sheet()))
with col3:
    approved_count = len([ep for ep in get_episodes_from_sheet() if ep.get('Status') == 'Approved'])
    st.metric("✅ Aprovados", approved_count)

st.markdown("🙏 **Tenda dos Pequenos** - Criando histórias bíblicas com amor e tecnologia")

# Debug info (remover em produção)
if st.sidebar.checkbox("🔧 Debug Info"):
    st.sidebar.write("**Planilha ID:**", SPREADSHEET_ID)
    st.sidebar.write("**Assistant ID:**", ASSISTANT_ID)
    if st.sidebar.button("Test Sheets Connection"):
        sheet = init_gsheet()
        if sheet:
            st.sidebar.success("✅ Google Sheets OK")
        else:
            st.sidebar.error("❌ Google Sheets Error")
# TESTE MANUAL - Adicione temporariamente
if st.sidebar.button("🧪 Teste Manual Personagens"):
    st.write("Testando geração manual de personagens...")
    
    # Dados de teste
    test_episode = {
        'Episódio': 'O Bom Samaritano',
        'Descrição Curta': 'Um viajante é ajudado por um gentil samaritano',
        'Moral': 'Amar e ajudar a todos'
    }
    
    with st.spinner("Testando Diretor de Personagens..."):
        characters = generate_characters_for_episode(
            test_episode['Episódio'],
            test_episode['Descrição Curta'],
            test_episode['Moral']
        )
        
        if characters:
            st.success(f"✅ {len(characters)} personagens criados!")
            st.json(characters)
            
            # Testar salvar na planilha
            if add_characters_to_sheet(characters, test_episode['Episódio']):
                st.success("✅ Personagens salvos na planilha!")
            else:
                st.error("❌ Erro ao salvar na planilha")
        else:
            st.error("❌ Erro ao gerar personagens")
