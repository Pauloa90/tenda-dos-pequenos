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
        
        # Usar método antigo para compatibilidade
        import openai
        openai.api_key = api_key
        client = None  # Usar método antigo
        st.success("✅ OpenAI configurado com sucesso!")
        
    else:
        st.error("❌ OPENAI_API_KEY não encontrada nas secrets")
        st.stop()
        
except Exception as e:
    st.error(f"Erro ao configurar OpenAI: {e}")
    st.stop()

# Função para chamar o Assistant
def generate_episodes(num_episodes):
    try:
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
            
    except Exception as e:
        st.error(f"Erro ao conectar com OpenAI: {e}")
        return []

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

def update_episode_status(row_index, new_status):
    try:
        sheet = init_gsheet()
        if sheet is None:
            return False
            
        episodios_sheet = sheet.worksheet("Episodios")
        # row_index + 2 porque: +1 para index real, +1 para pular header
        episodios_sheet.update_cell(row_index + 2, 4, new_status)
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
                            if update_episode_status(i, new_status):
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
