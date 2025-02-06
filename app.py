import os
import streamlit as st
import requests
import webbrowser
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.questionanswering import QuestionAnsweringClient
from dotenv import load_dotenv
import threading
import uvicorn

# Cargar las variables de entorno
load_dotenv()
AI_ENDPOINT = st.secrets['AI_SERVICE_ENDPOINT']
AI_KEY = st.secrets['AI_SERVICE_KEY']
AI_PROJECT_NAME = st.secrets['QA_PROJECT_NAME']
AI_DEPLOYMENT_NAME = st.secrets['QA_DEPLOYMENT_NAME']

# Verificación de configuración
if not all([AI_ENDPOINT, AI_KEY, AI_PROJECT_NAME, AI_DEPLOYMENT_NAME]):
    raise ValueError("Faltan variables de entorno en .env")

# Inicializar FastAPI
app = FastAPI()

# Configurar el cliente de Azure QnA
credential = AzureKeyCredential(AI_KEY)
ai_client = QuestionAnsweringClient(endpoint=AI_ENDPOINT, credential=credential)

# Modelo de datos para la solicitud
class QuestionRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask_question(data: QuestionRequest):
    """Recibe una pregunta y devuelve la respuesta de Azure QnA"""
    try:
        response = ai_client.get_answers(
            question=data.question,
            project_name=AI_PROJECT_NAME,
            deployment_name=AI_DEPLOYMENT_NAME
        )

        if not response.answers:
            raise HTTPException(status_code=404, detail="No se encontraron respuestas")

        # Formatear la respuesta
        answers = [
            {
                "answer": ans.answer,
                "confidence": ans.confidence,
                "source": ans.source
            }
            for ans in response.answers
        ]
        return {"answers": answers}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- Streamlit UI ---------------- #

# URL de la Knowledge Base de ResourceSpace
KB_URL = "https://www.resourcespace.com/knowledge-base"

# Preguntas Frecuentes
FAQS = [
    "What is required to access a ResourceSpace system?",
    "How can users change their password in ResourceSpace?",
    "How can users refine their searches in ResourceSpace?",
    "What options do users have for displaying search results?",
    "How can users apply metadata before uploading files?",
    "What types of notifications can users receive via email?",
    "What should users do after finishing their session in ResourceSpace?",
]

# Sonido de respuesta
sound_html = """
    <audio autoplay>
        <source src="data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA=" type="audio/wav">
    </audio>
"""

def play_sound():
    st.markdown(sound_html, unsafe_allow_html=True)

# Inicializar estados si no existen
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¿En qué puedo ayudarte hoy?"}]
if "show_sidebar" not in st.session_state:
    st.session_state.show_sidebar = False
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# 🌟 HEADER (Título y botones fuera del contenedor del chatbot)
st.markdown("<h1 style='display: inline-block;'>💬 ResourceSpace AI Assistant</h1>", unsafe_allow_html=True)
st.caption("Chatea con el asistente de ResourceSpace")

# 🔄 Botones en la parte superior
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    faq_btn = st.button("📌 FAQ", use_container_width=True)

with col2:
    if st.button("📖 Knowledge Base", use_container_width=True):
        webbrowser.open(KB_URL)

with col3:
    restart_btn = st.button("🔄 Reiniciar Chat", use_container_width=True)

# 📌 Manejo de botones
if restart_btn:
    st.session_state.messages = [{"role": "assistant", "content": "¿En qué puedo ayudarte hoy?"}]
    st.rerun()

if faq_btn:
    st.session_state.show_sidebar = not st.session_state.show_sidebar

# 📌 SIDEBAR (Preguntas Frecuentes)
if st.session_state.show_sidebar:
    st.sidebar.subheader("📌 Preguntas Frecuentes")
    for question in FAQS:
        if st.sidebar.button(question):
            st.session_state.user_input = question

# 📝 MAIN (Chat)
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"""
            <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
                <div style="background-color: #4CAF50; color: white; padding: 10px; border-radius: 10px; max-width: 70%;">
                    {msg["content"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.chat_message("assistant").write(msg["content"])

# 🔽 Input de chat
user_input = st.chat_input("Escribe tu pregunta...")

# 📌 Procesar entrada del usuario
if user_input or st.session_state.user_input:
    input_text = user_input if user_input else st.session_state.user_input
    st.session_state.messages.append({"role": "user", "content": input_text})

    # Mostrar mensaje del usuario alineado a la derecha
    st.markdown(
        f"""
        <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
            <div style="background-color: #4CAF50; color: white; padding: 10px; border-radius: 10px; max-width: 70%;">
                {input_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Enviar pregunta directamente al backend de FastAPI interno
    response = requests.post("http://127.0.0.1:8000/ask", json={"question": input_text})
    if response.status_code == 200:
        response_json = response.json()
        answer = response_json.get("answers", [{"answer": "No se encontró una respuesta."}])[0]["answer"]
    else:
        answer = "⚠️ Error al obtener respuesta."

    # Mostrar respuesta del bot
    st.session_state.messages.append({"role": "assistant", "content": answer})
    play_sound()
    st.chat_message("assistant").write(answer)

    # Limpiar variable después de usarla
    st.session_state.user_input = ""

# ------------------ Iniciar FastAPI en segundo plano ------------------ #
def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Ejecutar FastAPI en un hilo separado
if __name__ == "__main__":
    threading.Thread(target=run_api, daemon=True).start()
