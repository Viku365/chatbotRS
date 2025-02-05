from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.questionanswering import QuestionAnsweringClient
from dotenv import load_dotenv
import os

# Cargar las variables de entorno
load_dotenv()
AI_ENDPOINT = os.getenv('AI_SERVICE_ENDPOINT')
AI_KEY = os.getenv('AI_SERVICE_KEY')
AI_PROJECT_NAME = os.getenv('QA_PROJECT_NAME')
AI_DEPLOYMENT_NAME = os.getenv('QA_DEPLOYMENT_NAME')

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

