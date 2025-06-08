import requests
import streamlit as st
import time
import json

class PiapiService:
    def __init__(self):
        self.api_key = st.secrets["PIAPI_API_KEY"]
        self.base_url = "https://api.piapi.ai/mj/v2"
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
    
    def generate_character_images(self, character_name, character_description, episode_context=""):
        """Gera 4 opções de imagem para um personagem"""
        
        # Criar prompt otimizado para Pixar 3D
        prompt = self._create_character_prompt(character_name, character_description, episode_context)
        
        try:
            # Chamar API imagine
            response = requests.post(
                f"{self.base_url}/imagine",
                headers=self.headers,
                json={
                    "prompt": prompt,
                    "aspect_ratio": "1:1",
                    "model": "mj-6"
                }
            )
            
            if response.status_code == 200:
                task_id = response.json().get("task_id")
                return self._wait_for_completion(task_id)
            else:
                st.error(f"Erro na API PIAPI: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            st.error(f"Erro ao gerar imagens: {e}")
            return None
    
    def upscale_image(self, image_url, index=1):
        """Faz upscale da imagem escolhida"""
        try:
            response = requests.post(
                f"{self.base_url}/upscale",
                headers=self.headers,
                json={
                    "origin_task_id": image_url,  # Na verdade é o task_id da imagem original
                    "index": index  # 1, 2, 3 ou 4
                }
            )
            
            if response.status_code == 200:
                task_id = response.json().get("task_id")
                return self._wait_for_completion(task_id)
            else:
                st.error(f"Erro no upscale: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            st.error(f"Erro ao fazer upscale: {e}")
            return None
    
    def _create_character_prompt(self, name, description, context):
        """Cria prompt otimizado para personagens bíblicos infantis"""
        
        base_prompt = f"""3D Pixar animation style, {description}, full body character, white background, child-friendly, vibrant colors, high quality, detailed, cute, biblical character"""
        
        # Adicionar contexto se fornecido
        if context:
            base_prompt += f", {context}"
        
        # Adicionar elementos técnicos
        technical_params = "--ar 1:1 --style raw --v 6.0"
        
        return f"{base_prompt} {technical_params}"
    
    def _wait_for_completion(self, task_id, max_wait=300):
        """Aguarda a conclusão da tarefa"""
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.base_url}/fetch",
                    headers=self.headers,
                    params={"task_id": task_id}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    status = result.get("status")
                    
                    if status == "finished":
                        return result
                    elif status == "failed":
                        st.error(f"Tarefa falhou: {result.get('error', 'Erro desconhecido')}")
                        return None
                    elif status in ["processing", "waiting"]:
                        # Continuar aguardando
                        time.sleep(10)
                    else:
                        st.warning(f"Status desconhecido: {status}")
                        time.sleep(5)
                else:
                    st.error(f"Erro ao verificar status: {response.status_code}")
                    return None
                    
            except Exception as e:
                st.error(f"Erro ao verificar status: {e}")
                return None
        
        st.error("Timeout: Geração de imagem demorou muito")
        return None
    
    def test_connection(self):
        """Testa a conexão com a API"""
        try:
            response = requests.get(
                f"{self.base_url}/account",
                headers=self.headers
            )
            
            if response.status_code == 200:
                account_info = response.json()
                return True, account_info
            else:
                return False, f"Erro: {response.status_code} - {response.text}"
                
        except Exception as e:
            return False, f"Erro de conexão: {e}"

# Função para testar o serviço
def test_piapi_service():
    """Função para testar o serviço PIAPI"""
    st.subheader("🧪 Teste PIAPI Service")
    
    piapi = PiapiService()
    
    if st.button("Testar Conexão"):
        with st.spinner("Testando conexão..."):
            success, result = piapi.test_connection()
            
            if success:
                st.success("✅ Conexão com PIAPI funcionando!")
                st.json(result)
            else:
                st.error(f"❌ Erro na conexão: {result}")
    
    st.markdown("---")
    
    # Teste de geração de imagem
    with st.form("test_image_generation"):
        st.subheader("Teste Geração de Imagem")
        
        test_name = st.text_input("Nome do Personagem", value="Davi")
        test_desc = st.text_area("Descrição", value="jovem pastor hebreu, túnica simples, cabelos castanhos, sorriso gentil")
        test_context = st.text_input("Contexto", value="pastoreando ovelhas no campo")
        
        submitted = st.form_submit_button("🎨 Gerar Teste")
        
        if submitted:
            with st.spinner("Gerando imagens... (pode demorar 1-2 minutos)"):
                result = piapi.generate_character_images(test_name, test_desc, test_context)
                
                if result:
                    st.success("✅ Imagens geradas com sucesso!")
                    st.json(result)
                    
                    # Tentar exibir as imagens se disponíveis
                    if "image_url" in result:
                        st.image(result["image_url"], caption="Resultado Midjourney")
                else:
                    st.error("❌ Falha na geração de imagens")
