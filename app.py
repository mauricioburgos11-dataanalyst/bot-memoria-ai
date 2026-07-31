import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
import database      # Tu módulo MySQL para memoria personal
import rag_manager   # Tu módulo para ChromaDB/RAG
import farmacia_sql  # Tu módulo para consultas SQL de la farmacia

# Cargar variables de entorno
load_dotenv()
client = genai.Client()

# Inicializar bases de datos al arrancar
database.inicializar_db()

# Inicializar estados de la sesión
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
if "sql_pendiente" not in st.session_state:
    st.session_state.sql_pendiente = None

# ==============================================================================
# 1. HERRAMIENTAS (Tools) PARA GEMINI
# ==============================================================================

def guardar_informacion_en_base_de_datos(clave: str, valor: str) -> str:
    """Guarda o actualiza datos personales del usuario en MySQL."""
    database.guardar_dato(clave, valor)
    return f"Éxito: Se guardó '{clave}' = '{valor}'"

def consultar_base_de_datos_farmacia(consulta_sql: str) -> str:
    """Ejecuta una consulta SQL SELECT en la base de datos de la farmacia."""
    if not consulta_sql.strip().lower().startswith("select"):
        return "Error: Solo se permiten consultas de lectura (SELECT)."
    return str(farmacia_sql.ejecutar_consulta_sql(consulta_sql))

def proponer_modificacion_farmacia(consulta_sql: str) -> str:
    """Propone una modificación DDL/DML para revisión humana."""
    st.session_state.sql_pendiente = consulta_sql
    return "Propuesta SQL creada. Esperando confirmación manual."

# ==============================================================================
# 2. INTERFAZ STREAMLIT
# ==============================================================================

st.set_page_config(page_title="AI Engineer App", page_icon="🧠", layout="wide")
st.title("🧠 Asistente de IA: Farmacia + RAG + Memoria")

# BARRA LATERAL
with st.sidebar:
    st.header("🗄️ Memoria Personal (MySQL)")
    st.text_area("Datos guardados:", database.obtener_memoria(), height=150)
    if st.button("🔄 Recargar Memoria"):
        st.rerun()

    st.markdown("---")
    st.header("📄 Memoria RAG (PDFs)")
    archivo = st.file_uploader("Subir PDF:", type=["pdf"])
    if archivo and st.button("Indexar PDF"):
        with st.spinner("Procesando embeddings..."):
            n = rag_manager.procesar_pdf(archivo)
            st.success(f"¡Hecho! {n} fragmentos guardados.")

# SECCIÓN HUMAN-IN-THE-LOOP
if st.session_state.sql_pendiente:
    st.warning("⚠️ Acción pendiente: Revisa y confirma el código SQL:")
    st.code(st.session_state.sql_pendiente, language="sql")
    if st.button("✅ Confirmar y ejecutar"):
        res = farmacia_sql.ejecutar_modificacion_sql(st.session_state.sql_pendiente)
        st.success(res)
        st.session_state.sql_pendiente = None
        st.rerun()
    if st.button("❌ Cancelar"):
        st.session_state.sql_pendiente = None
        st.rerun()

# MOSTRAR HISTORIAL DE MENSAJES
for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# CHAT INTERACTIVO
if prompt := st.chat_input("Consulta tu farmacia o gestiona datos..."):
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Preparar historial en el formato correcto (Content/Part)
    historial_gemini = []
    for msg in st.session_state.mensajes[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        historial_gemini.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=msg["content"])]
        ))
    
    # 2. Agregar mensaje actual
    prompt_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)]
    )
    final_contents = historial_gemini + [prompt_content]

    # Contextos adicionales
    contexto_rag = rag_manager.buscar_contexto_relevante(prompt)
    contexto_mysql = database.obtener_memoria()

    config = types.GenerateContentConfig(
        system_instruction=f"""
        Eres un asistente inteligente para una farmacia.
        Memoria del usuario: {contexto_mysql}
        Contexto RAG: {contexto_rag}
        Base de datos: {farmacia_sql.ESQUEMA_FARMACIA}
        """,
        tools=[guardar_informacion_en_base_de_datos, consultar_base_de_datos_farmacia, proponer_modificacion_farmacia]
    )

    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            resp = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=final_contents,
                config=config
            )

            # Lógica de herramientas
            debe_recargar = False
            if resp.function_calls:
                for llamada in resp.function_calls:
                    if llamada.name == "guardar_informacion_en_base_de_datos":
                        guardar_informacion_en_base_de_datos(llamada.args.get("clave"), llamada.args.get("valor"))
                        debe_recargar = True
                    elif llamada.name == "consultar_base_de_datos_farmacia":
                        sql = llamada.args.get("consulta_sql")
                        st.info(f"⚙️ SQL: `{sql}`")
                        res = consultar_base_de_datos_farmacia(sql)
                        # Llamada final con resultado
                        resp = client.models.generate_content(
                            model='gemini-3.1-flash-lite',
                            contents=final_contents + [resp.candidates[0].content] + [types.Content(role="model", parts=[types.Part.from_text(text=f"Resultado: {res}")])],
                            config=config
                        )
            
            st.markdown(resp.text)
            st.session_state.mensajes.append({"role": "assistant", "content": resp.text})
            if debe_recargar or st.session_state.sql_pendiente:
                st.rerun()
