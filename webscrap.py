import os
import requests
from bs4 import BeautifulSoup
from openai import AzureOpenAI
import json
import re  # Para eliminar posibles etiquetas de Markdown en la respuesta

# 🔹 Configuración de Azure OpenAI
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://tu-recurso.openai.azure.com")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "tu-clave-secreta")
API_VERSION = "2024-07-01-preview"  # Verifica la versión en Azure
DEPLOYMENT_NAME = "gpt-4o-mini"  # ⚠️ CAMBIA ESTO SEGÚN TU NOMBRE DE DEPLOYMENT

# 🔹 Crear cliente Azure OpenAI
print("📌 Configurando Azure OpenAI...")
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY,
    api_version=API_VERSION
)

# 🔹 Definir la ruta del archivo TXT
txt_path = "./qa_dataset.txt"

# 🔹 Almacenar todo el contenido scrapeado
total_contenido = ""

while True:
    url = input("🔹 Ingresa la URL de la guía que deseas scrapear (o escribe 'salir' para finalizar): ").strip()

    if url.lower() == "salir":
        break  # Salimos del bucle si el usuario escribe "salir"

    print(f"📌 Haciendo request a {url}...")
    response = requests.get(url)

    # Verificar que la respuesta es correcta (200)
    if response.status_code == 200:
        print("✅ Página descargada correctamente.")
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extraer la sección principal de contenido
        content_div = soup.find("div", class_="grid-col col-9 knowledge-base-content")

        if content_div:
            print("✅ Se encontró la sección de contenido.")

            # Extraer párrafos y listas
            contenido = []
            for elem in content_div.find_all(["p", "ul"]):  # Párrafos y listas
                if elem.name == "p":
                    contenido.append(elem.text.strip())  # Añadir texto de párrafo
                elif elem.name == "ul":  # Si es una lista
                    items = [li.text.strip() for li in elem.find_all("li")]
                    contenido.append(" - " + "\n - ".join(items))  # Convertir lista a texto

            # Verificar que el contenido no está vacío
            if contenido:
                total_contenido += "\n\n".join(contenido) + "\n\n"  # Agregar al contenido total
                print(f"🔹 Añadido {len(contenido)} párrafos al total.")
            else:
                print("❌ No se encontró contenido válido en la página.")

        else:
            print("❌ No se encontró la sección de contenido.")
    else:
        print(f"❌ Error al acceder a la página. Código HTTP: {response.status_code}")

# 🔹 Verificar si hay contenido antes de proceder a la generación de preguntas
if not total_contenido.strip():
    print("❌ No se ha recopilado contenido. Saliendo...")
    exit()

print("📌 Se ha recopilado todo el contenido. Enviando a OpenAI para generar 100 preguntas...")

def generar_preguntas(texto):
    """Genera 100 preguntas y respuestas en inglés basadas en un texto usando OpenAI."""
    
    prompt = f"""
    You will receive a large text. Your task is to generate **100 relevant questions and answers** based on the text.

    - The questions **must be in English**.
    - The answers **must be in English**.
    - Format the response strictly as JSON, like this:
    
    [
        {{"question": "What is ResourceSpace?", "answer": "ResourceSpace is a digital asset management system."}},
        {{"question": "How do users access ResourceSpace?", "answer": "Users need an account to access the system."}}
    ]

    Now generate 100 question-answer pairs for the following text:

    {texto}
    """

    try:
        print("📌 Enviando contenido a OpenAI...")
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        # Extraer la respuesta del modelo
        qa_texto = response.choices[0].message.content.strip()

        # 🔹 Eliminar etiquetas Markdown ```json ... ```
        qa_texto = re.sub(r"```json|```", "", qa_texto).strip()

        # Intentar convertir la respuesta en JSON
        try:
            qa_pairs = json.loads(qa_texto)
            if isinstance(qa_pairs, list):
                print(f"✅ {len(qa_pairs)} questions generated.")
                return qa_pairs
            else:
                print(f"❌ Unexpected format, response: {qa_texto}")
                return []
        except json.JSONDecodeError:
            print(f"❌ Failed to parse response as JSON, response:\n{qa_texto}")
            return []
    except Exception as e:
        print(f"❌ Error generating questions: {e}")
        return []

# 🔹 Generar preguntas con todo el contenido junto
qa_pairs = generar_preguntas(total_contenido)

# 🔹 Guardar en archivo TXT
if not qa_pairs:
    print("❌ No se generaron preguntas. Saliendo...")
    exit()

try:
    with open(txt_path, mode="a", encoding="utf-8") as file:
        for idx, qa in enumerate(qa_pairs, start=1):
            pregunta = qa.get("question", "").strip().replace("\n", " ")
            respuesta = qa.get("answer", "").strip().replace("\n", " ")
            if pregunta and respuesta:
                file.write(f"{idx}. \"{pregunta}\"\nRespuesta: \"{respuesta}\"\n\n")
    print(f"✅ Archivo actualizado correctamente: {txt_path}")
except Exception as e:
    print(f"❌ Error al guardar el archivo TXT: {e}")
