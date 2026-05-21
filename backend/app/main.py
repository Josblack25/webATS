import os
import io
import shutil
from fastapi import FastAPI, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

app = FastAPI(
    title="ATS Personal API", 
    description="ATS Personal API con soporte para archivos locales",
    version="1.0.0"
)

# Directorio local para guardar los archivos
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configuración de Orígenes Permitidos (CORS)
origins = [
    "http://localhost:4200",    
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# Inicializar cliente Groq
groq_api_key = os.getenv('GROQ_API_KEY')
if not groq_api_key:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error interno del servidor: Falta la variable de entorno GROQ_API_KEY"
    )

client = Groq(api_key=groq_api_key)

# Modelos de validación de datos
class AnalysisRequest(BaseModel):
    job_description: str = Field(..., min_length=10, max_length=4000)
    cv_text: str = Field(default="CV Adonis Dller. Desarrollador Full-Stack enfocado en Next.js...")

class AnalysisResponse(BaseModel):
    match_percentage: int
    missing_skills: list[str]  # Unificado
    strengths: list[str]
    recommendations: str



# Endpoint 1: Análisis por Archivo Físico (Guardando copia local)
@app.post('/api/v1/analyze-file', response_model=AnalysisResponse)
async def analyze_cv_file(
    job_description: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # 1. Validar extensión del archivo
        if not file.filename.lower().endswith(('.pdf', '.doc', '.docx')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de archivo no soportado. Sube un PDF o DOCX."
            )

        # 2. Leer los bytes del archivo
        file_content = await file.read()

        # 📌 3. GUARDAR EN LOCAL (Tu requerimiento actual)
        # Creamos una ruta segura dentro de la carpeta 'uploads' con el nombre original del archivo
        local_file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(local_file_path, "wb") as buffer:
            buffer.write(file_content)

        # 4. Extraer texto del PDF desde la memoria (para mantener velocidad de análisis)
        cv_text = ""
        if file.filename.lower().endswith('.pdf'):
            pdf_reader = PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    cv_text += page_text + "\n"
        else:
            # Fallback temporal para archivos de Word
            cv_text = "Texto extraído de archivo DOCX en fase de desarrollo."

        # Validar que la extracción no quedó vacía (ej. PDFs escaneados como imagen)
        if not cv_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo extraer texto del archivo. Asegúrate de que no sea una imagen escaneada."
            )

        # 5. Configurar Prompts para Groq
        system_prompt = (
            'Eres un Analista Senior de Recursos Humanos y un experto en ATS (Applicant Tracking System).\n'
            'Tu objetivo es analizar el CV de un candidato junto con la descripción de una vacante y proporcionar un informe detallado.\n'
            'DEBES responder EXCLUSIVAMENTE en formato JSON válido que coincida exactamente con la siguiente estructura:\n'
            '{\n'
            '  "match_percentage": un entero de 0 a 100,\n'
            '  "missing_skills": [lista de tecnologías o habilidades que faltan en el CV],\n'
            '  "strengths": [lista de puntos fuertes donde el candidato encaja perfectamente],\n'
            '  "recommendations": "consejo con 4 puntos que mejorar en formato de lista   y directo para optimizar el perfil"\n'
            '  "recommendations": "describe como mejorar sus experiencias para ajustar las necesidades de la empresa"\n'
            '}\n'
            'No saludes, no des explicaciones fuera del JSON, sé extremadamente objetivo.'
        )
        
        user_content = f"OFERTA DE TRABAJO:\n{job_description}\n\nCURRÍCULUM DEL CANDIDATO:\n{cv_text}"

       # 6. Llamada a Groq corregida con el nuevo modelo
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content}
            ],
            temperature=0.2,
            response_format={'type': 'json_object'}
        )

        raw_json_response = completion.choices[0].message.content
        return AnalysisResponse.model_validate_json(raw_json_response)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el archivo: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)