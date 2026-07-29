import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
import database      # Módulo MySQL (Aiven)
import rag_manager   # Módulo ChromaDB (RAG)

# Cargar variables de entorno
load_dotenv()
client = genai.Client()

# Inicializar MySQL en Aiven (Crea la tabla automáticamente si no existe)
database.inicializar_db()

# DEFINICIÓN DE LA HERRAMIENTA DE GUARDADO
def guardar_informacion_en_base_de_datos(clave: str, valor: str) -> str:
    """
    Guarda o actualiza una información clave sobre el usuario en la base de datos MySQL.
    Úsala cuando el usuario comparta su nombre, datos personales, compras, gustos o estudios.
    """
    database.guardar_dato(clave, valor)
    return f"Éxito: Se guardó en MySQL '{clave}' = '{valor}'"

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="AI Engineer App - Mauricio", page_icon="🧠", layout="wide")
st.title("🧠 Asistente con Memoria MySQL + RAG")

# BARRA LATERAL (SIDEBAR)
with st.sidebar:
    st.header("🗄️ 1. Memoria en MySQL (Aiven)")
    contexto_mysql = database.obtener_memoria()
    st.text_area("Datos guardados del usuario:", contexto_mysql, height=200)
    
    if st.button("🔄 Recargar Memoria"):
        st.rerun()

    st.markdown("---")
    st.header("📄 2. Memoria RAG (PDFs)")
    archivo_pdf = st.file_uploader("Sube un PDF:", type=["pdf"])
    if archivo_pdf is not None:
        if st.button("Procesar PDF en Base Vectorial"):
            with st.spinner("Creando Embeddings en ChromaDB..."):
                num_chunks = rag_manager.procesar_pdf(archivo_pdf)
                st.success(f"¡PDF procesado! {num_chunks} fragmentos guardados.")

# HISTORIAL DE CHAT
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# INPUT DEL USUARIO
if prompt := st.chat_input("Escribe tu mensaje..."):
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Búsqueda semántica en RAG
    contexto_rag = rag_manager.buscar_contexto_relevante(prompt)

    # 2. Configurar Gemini con System Instruction + Herramientas
    config = types.GenerateContentConfig(
        system_instruction=f"""
        Eres un asistente de IA personal muy atento y profesional.
        
        === DATOS CONOCIDOS DEL USUARIO (MySQL) ===
        {contexto_mysql}
        
        === CONTEXTO DE DOCUMENTOS (RAG / ChromaDB) ===
        {contexto_rag}
        
        INSTRUCCIONES:
        - Utiliza los datos conocidos del usuario para responder de forma personalizada.
        - Si el usuario te cuenta un dato personal nuevo (ej: su nombre, trabajo, hobbies, compras),
          DEBES usar obligatoriamente la herramienta 'guardar_informacion_en_base_de_datos'.
        """,
        tools=[guardar_informacion_en_base_de_datos]
    )

    with st.chat_message("assistant"):
        with st.spinner("Procesando con Gemini + MySQL..."):
            # Función auxiliar para llamar a Gemini con soporte de herramientas
            def ejecutar_llamada(modelo_nombre):
                resp = client.models.generate_content(
                    model=modelo_nombre,
                    contents=prompt,
                    config=config
                )
                
                # VERIFICAR SI GEMINI PIDIÓ EJECUTAR LA HERRAMIENTA
                if resp.function_calls:
                    se_guardos_datos = False
                    for llamada in resp.function_calls:
                        if llamada.name == "guardar_informacion_en_base_de_datos":
                            args = llamada.args
                            c = args.get("clave")
                            v = args.get("valor")
                            # EJECUCIÓN REAL EN PYTHON CONECTADO A AIVEN
                            guardar_informacion_en_base_de_datos(c, v)
                            se_guardos_datos = True
                    
                    # Si guardó datos, pedimos la respuesta final conversacional
                    resp_final = client.models.generate_content(
                        model=modelo_nombre,
                        contents=f"Se guardó el dato en la base de datos correctamente. Responde de forma natural a: {prompt}",
                        config=config
                    )
                    return resp_final.text, se_guardos_datos
                else:
                    return resp.text, False

            # Intentos con fallback de modelos
            try:
                texto_bot, guardo_algo = ejecutar_llamada('gemini-3.5-flash')
            except Exception as e:
                try:
                    texto_bot, guardo_algo = ejecutar_llamada('gemini-3.1-flash-lite')
                except Exception as e2:
                    texto_bot, guardo_algo = f"⚠️ Error al conectar con la API: {e2}", False

            st.markdown(texto_bot)
            st.session_state.mensajes.append({"role": "assistant", "content": texto_bot})
            
            # Si se guardó un dato nuevo en Aiven, recargamos la interfaz para actualizar el sidebar
            if guardo_algo:
                st.rerun()
