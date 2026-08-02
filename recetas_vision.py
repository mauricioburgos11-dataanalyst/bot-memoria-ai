import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# 1. Definimos la estructura de datos que queremos extraer de la receta
class MedicamentoDetectado(BaseModel):
    nombre_comercial_o_droga: str = Field(description="Nombre comercial o principio activo detectado en la receta")
    concentracion: str = Field(description="Concentración (ej. 600mg, 500mg, 1g, etc.)")
    forma_farmaceutica: str = Field(description="Forma farmacéutica (ej. Comprimidos, Jarabe, Crema, etc.)")
    cantidad_solicitada: int = Field(description="Cantidad de cajas o unidades solicitadas (por defecto 1)")

class EstructuraReceta(BaseModel):
    es_receta_valida: bool = Field(description="True si la imagen parece ser una receta médica o pedido de medicamento")
    obra_social_o_prepaga: str = Field(description="Nombre de la obra social o prepaga si figura, de lo contrario 'Particular'")
    medicamentos: list[MedicamentoDetectado]
    observaciones: str = Field(description="Aclaraciones extra (ej. 'Requiere receta archivada', 'Letra poco legible', etc.)")

def analizar_imagen_receta(bytes_imagen: bytes, mime_type: str) -> dict:
    """
    Recibe los bytes de una imagen de receta y utiliza Gemini Vision
    para extraer medicamentos y obra social en formato JSON estructurado.
    """
    client = genai.Client()

    prompt_instrucciones = """
    Eres un asistente farmacéutico experto en lectura de recetas médicas argentinas (manuscritas o digitales).
    Analiza la imagen adjunta y extrae la información requerida de manera precisa.
    Si la caligrafía es difícil, deduce con la mejor aproximación médica posible.
    """

    config = types.GenerateContentConfig(
        system_instruction=prompt_instrucciones,
        temperature=0.1,  # Baja temperatura para evitar inventiva
        response_mime_type="application/json",
        response_schema=EstructuraReceta,
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Recomendado para tareas de visión estándar
            contents=[
                types.Part.from_bytes(data=bytes_imagen, mime_type=mime_type),
                "Extrae los datos de esta receta médica."
            ],
            config=config
        )
        # Convertimos la respuesta JSON a un diccionario de Python
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"Error al procesar la imagen: {str(e)}"}
