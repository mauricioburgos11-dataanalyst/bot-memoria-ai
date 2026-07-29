import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import database

# Cargar variables de entorno (.env)
load_dotenv()
client = genai.Client()

# Inicializar la base de datos MySQL
database.inicializar_db()

# DEFINIMOS LA HERRAMIENTA QUE GEMINI PUEDE USAR
def guardar_informacion_en_base_de_datos(clave: str, valor: str) -> str:
    """
    Guarda o actualiza una información clave sobre el usuario en la base de datos MySQL.
    Úsala cuando el usuario comparta datos personales importantes sobre su vida, 
    preferencias, compras, trabajo o estudios.
    """
    database.guardar_dato(clave, valor)
    return f"Éxito: Se ha guardado que tu '{clave}' es '{valor}'."

def chatear():
    print("🤖 Bot con Memoria Dinámica Activo. Escribe 'salir' para terminar.\n")
    
    # Sembramos tu información real inicial directamente en tu MySQL
    database.guardar_dato("nombre", "Mauricio") 
    database.guardar_dato("carrera", "Analista de Sistemas")
    database.guardar_dato("objetivo", "Ser AI Engineer")

    while True:
        mensaje_usuario = input("Tú: ")
        if mensaje_usuario.lower() == 'salir':
            break

        # 1. Recuperar el estado actual de la memoria desde tu IP/Puerto de MySQL
        contexto_memoria = database.obtain_memoria() if hasattr(database, 'obtain_memoria') else database.obtener_memoria()

        # 2. Configurar instrucciones y registrar la función como herramienta
        config = types.GenerateContentConfig(
            system_instruction=f"""
            Eres un asistente de IA muy útil y preciso con acceso a una base de datos de memoria.
            
            {contexto_memoria}
            
            INSTRUCCIONES:
            - Responde de forma personalizada usando la información conocida provista arriba.
            - Si el usuario te cuenta un dato nuevo, importante o de interés sobre sí mismo 
              (por ejemplo: una compra, hobbies, rutinas, familia, cambios de estudio), utiliza 
              inmediatamente la herramienta 'guardar_informacion_en_base_de_datos' para almacenarlo.
            """,
            tools=[guardar_informacion_en_base_de_datos] # Le entregamos la herramienta
        )

        # 3. Primera llamada a Gemini
        respuesta = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=mensaje_usuario,
            config=config
        )

        # 4. Verificar si Gemini decidió ejecutar la herramienta
        if respuesta.function_calls:
            for llamada in respuesta.function_calls:
                if llamada.name == "guardar_informacion_en_base_de_datos":
                    # Extraer los argumentos detectados por el LLM
                    args = llamada.args
                    clave_detectada = args.get("clave")
                    valor_detectado = args.get("valor")
                    
                    # Ejecutar la función real de Python conectada a tu MySQL
                    resultado_funcion = guardar_informacion_en_base_de_datos(clave_detectada, valor_detectado)
                    print(f"⚙️ [Sistema MLOps]: {resultado_funcion}")
            
            # 5. Volver a llamar a Gemini para que dé la respuesta final al usuario confirmando la acción
            # Le pasamos el historial de que la función se ejecutó con éxito
            respuesta_final = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"El sistema ejecutó la acción con éxito. Ahora responde al usuario amigablemente sobre: {mensaje_usuario}",
                config=config
            )
            print(f"\nBot: {respuesta_final.text}\n")
        else:
            # Si no requería guardar nada, mostramos la respuesta directa
            print(f"\nBot: {respuesta.text}\n")

if __name__ == "__main__":
    chatear()