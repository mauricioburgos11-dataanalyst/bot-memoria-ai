import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
import database # Tu módulo de MySQL
import rag_manager # Módulo RAG

# Cargar variables de entorno y cliente Gemini
load_dotenv()
client = genai.Client()
database.inicializar_db()

# Herramienta para guardar en MySQL
def guardar_informacion_en_base_de_datos(clave: str, valor: str) -> str:
    database.guardar_dato(clave, valor)
    return f"Éxito: Guardado '{clave}' -> '{valor}'"

# Configuración de página de Streamlit
st.set_page_config(page_title="AI Engineer Bot - RAG + MySQL", page_icon="🚀", layout="wide")
st.title("🧠 Bot con Memoria Híbrida: MySQL + RAG (Vectorial)")

# BARRA LATERAL
with st.sidebar:
    st.header("🗄️ 1. Memoria MySQL (Clave-Valor)")
    contexto_mysql = database.obtener_memoria()
    st.text_area("Datos personales en MySQL:", contexto_mysql, height=150)
    
    st.markdown("---")
    st.header("📄 2. Memoria RAG (Cargar PDF)")
    archivo_pdf = st.file_uploader("Sube un apunte o documento PDF:", type=["pdf"])
    
    if archivo_pdf is not None:
        if st.button("Procesar PDF en Base Vectorial"):
            with st.spinner("Creando Embeddings y guardando en ChromaDB..."):
                num_chunks = rag_manager.procesar_pdf(archivo_pdf)
                st.success(f"¡PDF procesado con éxito! Se guardaron {num_chunks} fragmentos vectoriales.")

# HISTORIAL DE CHAT
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# CHAT INTERACTIVO
if prompt := st.chat_input("Hazme una pregunta sobre tus datos o sobre el PDF cargado..."):
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Recuperar contexto desde la Base Vectorial (RAG) según la pregunta
    contexto_rag = rag_manager.buscar_contexto_relevante(prompt)

    # 2. Configurar Gemini combinando MySQL + RAG
    config = types.GenerateContentConfig(
        system_instruction=f"""
        Eres un asistente de IA avanzado capaz de razonar usando datos relacionales y búsquedas semánticas.
        
        === MEMORIA PERSONAL (MySQL) ===
        {contexto_mysql}
        
        === DOCUMENTOS Y CONTEXTO RECUPERADO (RAG / Vectorial) ===
        {contexto_rag}
        
        INSTRUCCIONES:
        - Responde la consulta combinando ambas fuentes de información de forma precisa.
        - Si la respuesta está en el contexto RAG, cítala o explícala claramente.
        """
    )

    with st.chat_message("assistant"):
        with st.spinner("Consultando MySQL + ChromaDB..."):
            try:
                # 1. Intenta con el modelo principal más reciente
                respuesta = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=prompt,
                    config=config
                )
                texto_bot = respuesta.text
            except Exception as e:
                # 2. Si hay saturación o fallo, conmuta al modelo lite vigente
                try:
                    respuesta = client.models.generate_content(
                        model='gemini-3.1-flash-lite',
                        contents=prompt,
                        config=config
                    )
                    texto_bot = respuesta.text
                except Exception as e2:
                    texto_bot = f"⚠️ Ocurrió un error al consultar la API: {e2}"

            st.markdown(texto_bot)
            st.session_state.mensajes.append({"role": "assistant", "content": texto_bot})