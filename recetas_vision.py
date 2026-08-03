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

def analizar_imagen_receta(client, bytes_imagen: bytes, mime_type: str, catalogo_productos: list) -> dict:
    """
    Recibe los bytes de la imagen y una lista de productos válidos para corregir errores de lectura.
    """
    # Convertimos la lista de Python en un texto legible para el prompt
    lista_catalogo_str = "\n".join([f"- {prod}" for prod in catalogo_productos])

    prompt_instrucciones = f"""
    Eres un asistente farmacéutico experto en lectura de recetas médicas argentinas.
    
    CATÁLOGO DE PRODUCTOS VÁLIDOS EN LA FARMACIA:
    {lista_catalogo_str}
    
    REGLAS DE EXTRACCIÓN Y CORRECCIÓN:
    1. Compara el medicamento que leas en la imagen con el CATÁLOGO DE PRODUCTOS VÁLIDOS.
    2. Si hay errores por la caligrafía (Ej: lees 'Hexaler cat'), DEBES mapearlo al nombre exacto del catálogo (Ej: 'Hexaler Cort').
    3. REGLA ESTRICTA: NO expliques ni menciones que hiciste una corrección. No lo pongas en las observaciones ni al lado del nombre. Simplemente devuelve el nombre correcto del catálogo en silencio.
    4. Si el medicamento claramente NO está en el catálogo, extrae lo que leas literalmente.
    5. Fechas: Prioriza la interpretación de fecha más coherente con la actualidad.
    """

    config = types.GenerateContentConfig(
        system_instruction=prompt_instrucciones,
        temperature=0.1,  # Temperatura baja para evitar alucinaciones
        response_mime_type="application/json",
        response_schema=EstructuraReceta,
    )

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=[
                types.Part.from_bytes(data=bytes_imagen, mime_type=mime_type),
                "Extrae los datos de esta receta médica respetando las reglas de corrección."
            ],
            config=config
        )
        # Convertimos la respuesta JSON a un diccionario de Python
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"Error al procesar la imagen: {str(e)}"}
