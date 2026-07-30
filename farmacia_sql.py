import mysql.connector
import database  # Reutilizamos la conexión con SSL a Aiven

# 1. ESQUEMA DE LA BASE DE DATOS (Se lo enviamos a Gemini para que sepa qué consultar)
ESQUEMA_FARMACIA = """

Tablas disponibles en la base de datos 'sistemafarmacia':

Table: accion_terapeutica
  - accion_id (Primary Key)
  - nombre (Unique)
  - descripcion

Table: auditoria_stock
  - numero_auditoria (Primary Key)
  - numero_lote (Foreign Key -> lotes_en_stock.numero_lote)
  - cantidad_ajustada
  - tipo_motivo
  - fecha_ajuste
  - observaciones

Table: categoria_productos
  - categoria_id (Primary Key)
  - nombre (Unique)
  - requiere_receta

Table: concentraciones
  - concentracion_id (Primary Key)
  - valor (Unique)

Table: devoluciones_droguerias
  - numero_devolucion (Primary Key)
  - cuit_drogueria (Foreign Key -> droguerias.cuit)
  - numero_lote (Foreign Key -> lotes_en_stock.numero_lote)
  - cantidad_devuelta
  - fecha_devolucion
  - motivo_devolucion

Table: droguerias
  - cuit (Primary Key)
  - nombre

Table: forma_farmaceutica
  - forma_id (Primary Key)
  - nombre (Unique)

Table: historial_precios
  - numero_historial (Primary Key)
  - codigo_barras (Foreign Key -> productos.codigo_barras)
  - precio_pvp_anterior
  - precio_pvp_actual
  - fecha_modificacion

Table: laboratorios
  - laboratorio_id (Primary Key)
  - nombre
  - cuit (Unique)
  - email

Table: lotes_en_stock
  - numero_lote (Primary Key)
  - codigo_barras (Foreign Key -> productos.codigo_barras)
  - posicion_id (Foreign Key -> posiciones_deposito.posicion_id)
  - numero_pedido (Foreign Key -> pedidos.numero_pedido)
  - fecha_vencimiento
  - cantidad_stock

Table: monodrogas
  - monodroga_id (Primary Key)
  - nombre (Unique)

Table: monodrogas_acciones (Junction Table)
  - monodroga_id (Primary Key, Foreign Key -> monodrogas.monodroga_id)
  - accion_id (Primary Key, Foreign Key -> accion_terapeutica.accion_id)

Table: pedidos
  - numero_pedido (Primary Key)
  - cuit_drogueria (Foreign Key -> droguerias.cuit)
  - codigo_barras (Foreign Key -> productos.codigo_barras)
  - cantidad_solicitada
  - precio_costo_unitario
  - fecha_pedido
  - estado_pedido

Table: posiciones_deposito
  - posicion_id (Primary Key)
  - nombre_posicion
  - sector_id (Foreign Key -> sectores_deposito.sector_id)

Table: presentaciones
  - presentacion_id (Primary Key)
  - descripcion (Unique)

Table: productos
  - codigo_barras (Primary Key)
  - nombre_comercial
  - precio_pvp_actual
  - laboratorio_id (Foreign Key -> laboratorios.laboratorio_id)
  - forma_id (Foreign Key -> forma_farmaceutica.forma_id)
  - concentracion_id (Foreign Key -> concentraciones.concentracion_id)
  - presentacion_id (Foreign Key -> presentaciones.presentacion_id)
  - categoria_id (Foreign Key -> categoria_productos.categoria_id)

Table: productos_monodrogas (Junction Table)
  - codigo_barras (Primary Key, Foreign Key -> productos.codigo_barras)
  - monodroga_id (Primary Key, Foreign Key -> monodrogas.monodroga_id)

Table: sectores_deposito
  - sector_id (Primary Key)
  - nombre_sector (Unique)
  - requiere_refrigeracion

Table: telefonos_droguerias
  - telefono_id (Primary Key)
  - cuit_drogueria (Foreign Key -> droguerias.cuit)
  - numero
  - tipo_contacto

Table: telefonos_laboratorios
  - telefono_id (Primary Key)
  - laboratorio_id (Foreign Key -> laboratorios.laboratorio_id)
  - numero
  - tipo_contacto

 REGLAS PARA CONSULTAS SQL:
- Siempre ten presente el historial de la conversación. Si el usuario hace una pregunta de seguimiento (como "¿y cuál es el lote?" o "¿y cuánto sale?"), infiere el producto del cual se habló en los mensajes previos.
- No uses comillas dobles ("") para los nombres de tablas ni columnas en las consultas MySQL.
- Al filtrar por texto en nombres de laboratorios, productos o drogas, USA SIEMPRE 'LIKE %texto%' (por ejemplo: WHERE l.nombre LIKE '%Roemmers%').
- Para saber el stock de un producto, debes unir 'productos' con 'lotes_en_stock' usando productos.codigo_barras = lotes_en_stock.codigo_barras.
- Para saber la droga, forma o laboratorio de un producto, haz los JOINs correspondientes con 'laboratorios', 'forma_farmaceutica', 'concentraciones' y 'presentaciones'.
- Genera ÚNICAMENTE consultas de lectura que comiencen con 'SELECT'.
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

def ejecutar_modificacion_sql(query_sql: str):
    """Ejecuta consultas de modificación DDL/DML (CREATE, ALTER, INSERT, UPDATE) en Aiven."""
    conn = database.obtener_conexion()
    if not conn:
        return "⚠️ Error: No se pudo conectar a la base de datos de Aiven."
    
    try:
        cursor = conn.cursor()
        cursor.execute(query_sql)
        conn.commit()
        cursor.close()
        conn.close()
        return "✅ Operación SQL ejecutada con éxito en la base de datos."
    except Exception as e:
        return f"Error al ejecutar modificación SQL: {e}"
