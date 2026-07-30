import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
import database      # Módulo MySQL (Aiven)
import rag_manager   # Módulo ChromaDB (RAG)
import farmacia_sql # Importamos el nuevo módulo

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

# DEFINIMOS LA HERRAMIENTA DE CONSULTA A FARMACIA
def consultar_base_de_datos_farmacia(consulta_sql: str) -> str:
    """
    Ejecuta una consulta SQL SELECT en la base de datos de la farmacia.
    Úsala SIEMPRE que el usuario pregunte por stock, precios, productos, laboratorios.
    IMPORTANTE: Genera únicamente consultas SELECT.
    """
    # Seguridad básica: Solo permitimos consultas de lectura (SELECT)
    if not consulta_sql.strip().lower().startswith("select"):
        return "Error de seguridad: Solo se permiten consultas de lectura (SELECT)."
    
    res = farmacia_sql.ejecutar_consulta_sql(consulta_sql)
    return str(res)

def modificar_base_de_datos_farmacia(consulta_sql: str) -> str:
    """
    Ejecuta comandos DDL o DML (CREATE TABLE, ALTER TABLE, INSERT, UPDATE, DELETE) 
    para modificar o ampliar la estructura de la base de datos de la farmacia.
    Úsala cuando el usuario te pida crear tablas nuevas, agregar campos o insertar registros.
    """
    return farmacia_sql.ejecutar_modificacion_sql(consulta_sql)

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

# Si la IA sugiere una modificación SQL, la mostramos en un bloque especial
if "sql_pendiente" in st.session_state and st.session_state.sql_pendiente:
    st.warning("⚠️ La IA propone ejecutar la siguiente modificación en la base de datos:")
    st.code(st.session_state.sql_pendiente, language="sql")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirmar y Aplicar Cambio en Aiven"):
            resultado = farmacia_sql.ejecutar_modificacion_sql(st.session_state.sql_pendiente)
            st.success(resultado)
            st.session_state.sql_pendiente = None
            st.rerun()
            
    with col2:
        if st.button("❌ Cancelar Operación"):
            st.session_state.sql_pendiente = None
            st.info("Operación cancelada. No se modificó la base de datos.")
            st.rerun()

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
        Eres un asistente de IA experto para una farmacia y asistente personal del usuario.
        
        === DATOS CONOCIDOS DEL USUARIO (MySQL) ===
        {contexto_mysql}
        
        === CONTEXTO DE DOCUMENTOS (RAG / ChromaDB) ===
        {contexto_rag}

        === ESTRUCTURA DE LA BASE DE DATOS DE FARMACIA (Text-to-SQL) ===
        {farmacia_sql.ESQUEMA_FARMACIA}
        
        INSTRUCCIONES:
        1. Si el usuario pregunta por precios, stock o productos de la farmacia, 
           genera la consulta SQL correcta y usa la herramienta 'consultar_base_de_datos_farmacia'.
        2. Si el usuario comparte un dato personal nuevo sobre sí mismo, usa 'guardar_informacion_en_base_de_datos'.
        3. Si la pregunta es sobre prospectos o PDFs cargados, usa la información de RAG.
        """,
        tools=[guardar_informacion_en_base_de_datos, consultar_base_de_datos_farmacia, modificar_base_de_datos_farmacia]
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
                    se_guardo = False
                    for llamada in resp.function_calls:
                        if llamada.name == "guardar_informacion_en_base_de_datos":
                            args = llamada.args
                            guardar_informacion_en_base_de_datos(args.get("clave"), args.get("valor"))
                            se_guardo = True
                        elif llamada.name == "consultar_base_de_datos_farmacia":
                            args = llamada.args
                            query = args.get("consulta_sql")
                            st.info(f"⚙️ [SQL Generado por la IA]: `{query}`") # Muestra el SQL en pantalla
                            resultado_db = consultar_base_de_datos_farmacia(query)
                            
                            # Le devolvemos el resultado de la base de datos a Gemini para que redacte la respuesta final
                            resp_final = client.models.generate_content(
                                model=modelo_nombre,
                                contents=f"El resultado de la base de datos fue: {resultado_db}. Responde amigablemente a: {prompt}",
                                config=config
                            )
                            return resp_final.text, False
                            
                    if se_guardo_dato:
                        resp_final = client.models.generate_content(
                            model=modelo_nombre,
                            contents=f"El dato fue guardado con éxito. Responde amigablemente a Mauricio sobre: {prompt}",
                            config=config
                        )
                        return resp_final.text, True
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
