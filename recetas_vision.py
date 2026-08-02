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

def analizar_imagen_receta(bytes_imagen: bytes, mime_type: str, catalogo_productos: list) -> dict:
    """
    Analiza receta comparándola con un catálogo de productos real.
    catalogo_productos: una lista de strings con los nombres exactos de tu base (ej: ['Hexaler Cort', 'Ibupirac 600', ...])
    """
    
    prompt_instrucciones = f"""
    Eres un asistente farmacéutico experto. Tu tarea es extraer medicamentos de recetas.
    
    CATÁLOGO DE PRODUCTOS VÁLIDOS (IMPORTANTE):
    {catalogo_productos}
    
    REGLAS:
    1. Si el nombre detectado en la receta es similar a alguno en el catálogo, DEBES corregirlo al nombre exacto del catálogo.
    2. Ejemplo: Si lees 'Hexaler cat', corrígelo a 'Hexaler Cort'.
    3. Si la fecha es ambigua (ej: 6/6 vs 9/6), indica el valor más probable y añade una advertencia en 'observaciones'.
    4. Devuelve los datos en formato JSON estricto según el esquema.
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
