import mysql.connector
import os
from mysql.connector import Error
import streamlit as st

def obtener_config_db():
    """Obtiene la configuración leyendo desde st.secrets (Nube) o de os.getenv (.env local)."""
    # Intentamos leer desde Secrets de Streamlit (Entorno Cloud)
    try:
        return {
            'host': st.secrets["DB_HOST"],
            'port': int(st.secrets["DB_PORT"]),
            'user': st.secrets["DB_USER"],
            'password': st.secrets["DB_PASSWORD"],
            'database': st.secrets["DB_NAME"],
            'ssl_disabled': False # Mantiene SSL activo para Aiven
        }
    except Exception:
        # Si no existen st.secrets (Entorno Local .env)
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME', 'bot_memoria')
        }

def obtener_conexion():
    """Crea y retorna la conexión a MySQL usando IP y Puerto específicos."""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"❌ Error al conectar a MySQL ({DB_CONFIG['host']}:{DB_CONFIG['port']}): {e}")
        return None

def inicializar_db():
    """Crea la tabla de memoria si no existe."""
    conn = obtener_conexion()
    if conn:
        cursor = conn.cursor()
        query = '''
            CREATE TABLE IF NOT EXISTS datos_usuario (
                id INT AUTO_INCREMENT PRIMARY KEY,
                clave VARCHAR(100) UNIQUE,
                valor TEXT
            )
        '''
        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()

def guardar_dato(clave, valor):
    """Guarda o actualiza un dato en MySQL."""
    conn = obtener_conexion()
    if conn:
        cursor = conn.cursor()
        # Sintaxis UPSERT propia de MySQL
        query = '''
            INSERT INTO datos_usuario (clave, valor)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE valor = VALUES(valor)
        '''
        cursor.execute(query, (clave, valor))
        conn.commit()
        cursor.close()
        conn.close()

def obtener_memoria():
    """Recupera todos los datos guardados sobre el usuario."""
    conn = obtener_conexion()
    if not conn:
        return "Error de conexión a la base de datos."
    
    cursor = conn.cursor()
    cursor.execute("SELECT clave, valor FROM datos_usuario")
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not filas:
        return "No hay información previa guardada."
    
    memoria_texto = "Información conocida sobre el usuario:\n"
    for clave, valor in filas:
        memoria_texto += f"- {clave}: {valor}\n"
    return memoria_texto
