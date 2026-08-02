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
    Eres un asistente farmacéutico experto. 
    Tu tarea es extraer datos de recetas argentinas.
    
    REGLAS DE ORO:
    1. Si el nombre del producto es ambiguo, compáralo con los nombres comerciales reales (Ej: "Hexaler Cort" vs "Hexaler Cat").
    2. Si la fecha es difícil de leer, indica el valor más probable pero añade una advertencia en 'observaciones'.
    3. Siempre devuelve los datos en el formato JSON especificado.
    """

    config = types.GenerateContentConfig(
        system_instruction=prompt_instrucciones,
        temperature=0.1,  # Baja temperatura para evitar inventiva
        response_mime_type="application/json",
        response_schema=EstructuraReceta,
    )

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
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
