import mysql.connector
import database  # Reutilizamos la conexión con SSL a Aiven

# 1. ESQUEMA DE LA BASE DE DATOS (Se lo enviamos a Gemini para que sepa qué consultar)
ESQUEMA_FARMACIA = """
Tablas disponibles en la base de datos 'defaultdb':
