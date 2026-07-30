import mysql.connector
import database  # Reutilizamos la conexión con SSL a Aiven

# 1. ESQUEMA DE LA BASE DE DATOS (Se lo enviamos a Gemini para que sepa qué consultar)
ESQUEMA_FARMACIA = """
Tablas disponibles en la base de datos 'defaultdb':

1. Tabla 'productos':
   - id (INT, PRIMARY KEY)
"""

def ejecutar_consulta_sql(query_sql: str):
    """Ejecuta una consulta SELECT generada por la IA de forma segura en Aiven."""
    conn = database.obtener_conexion()
    if not conn:
        return "⚠️ Error: No se pudo conectar a Aiven MySQL."
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query_sql)
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not resultados:
            return "La consulta no devolvió ningún registro."
        return resultados
    except Exception as e:
        return f"Error ejecutando SQL: {e}"
