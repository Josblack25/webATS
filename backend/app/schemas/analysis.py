from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

# Definimos la estructura de respuesta de la IA (JSON) 
class AnalysisRequest(BaseModel):
    # validacion que el camppo coincida con las restriciones del frontend
    job_description: str = Field(
        ...,
        description = 'Texto completo de la cavante o perfil solicitado',
        min_length= 10,
        max_length=4000
    )

    @field_validator('job_description')
    @classmethod
    def not_empty_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('La descripción no puede estar vacía o contener solo espacios')
            return vars

class AnalysisResponse(BaseModel):
    match_percentage: float = Field(..., ge=0, le=100, description='porcentaje de compatibilidad entre el CV y la vacante') 
    missing_keywords: list[str] = Field(..., description='Palabras claves faltantes en el CV')
    strengths: list[str] = Field(..., description='Puntos fuertes detectados')
    recomendations: str = Field(..., description='Sugerencias de optimización y mejora para el candidato')