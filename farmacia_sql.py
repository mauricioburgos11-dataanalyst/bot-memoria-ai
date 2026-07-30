import mysql.connector
import database  # Reutilizamos la conexión con SSL a Aiven

# 1. ESQUEMA DE LA BASE DE DATOS (Se lo enviamos a Gemini para que sepa qué consultar)
ESQUEMA_FARMACIA = """
Tablas disponibles en la base de datos 'defaultdb':

1. Tabla 'accion_terapeutica' (
   'accion_id' int NOT NULL AUTO_INCREMENT,
   'nombre' varchar(100) NOT NULL,
   'descripcion' text,
   PRIMARY KEY ('accion_id'),
   UNIQUE KEY 'nombre' ('nombre')
 )

 2. Tabla "auditoria_stock" (
   "numero_auditoria" int NOT NULL AUTO_INCREMENT,
   "numero_lote" varchar(50) NOT NULL,
   "cantidad_ajustada" int NOT NULL,
   "tipo_motivo" varchar(50) NOT NULL,
   "fecha_ajuste" datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
   "observaciones" text,
   PRIMARY KEY ("numero_auditoria"),
   KEY "numero_lote" ("numero_lote"),
   CONSTRAINT "auditoria_stock_ibfk_1" FOREIGN KEY ("numero_lote") REFERENCES "lotes_en_stock" ("numero_lote")
 )

 3. Tabla "categoria_productos" (
   "categoria_id" int NOT NULL AUTO_INCREMENT,
   "nombre" varchar(50) NOT NULL,
   "requiere_receta" tinyint(1) NOT NULL DEFAULT '0',
   PRIMARY KEY ("categoria_id"),
   UNIQUE KEY "nombre" ("nombre")
 )

 4. Tabla "concentraciones" (
   "concentracion_id" int NOT NULL AUTO_INCREMENT,
   "valor" varchar(30) NOT NULL,
   PRIMARY KEY ("concentracion_id"),
   UNIQUE KEY "valor" ("valor")
 )

 5. Tabla "devoluciones_droguerias" (
   "numero_devolucion" int NOT NULL AUTO_INCREMENT,
   "cuit_drogueria" varchar(20) NOT NULL,
   "numero_lote" varchar(50) NOT NULL,
   "cantidad_devuelta" int NOT NULL,
   "fecha_devolucion" datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
   "motivo_devolucion" varchar(100) NOT NULL,
   PRIMARY KEY ("numero_devolucion"),
   KEY "cuit_drogueria" ("cuit_drogueria"),
   KEY "numero_lote" ("numero_lote"),
   CONSTRAINT "devoluciones_droguerias_ibfk_1" FOREIGN KEY ("cuit_drogueria") REFERENCES "droguerias" ("cuit"),
   CONSTRAINT "devoluciones_droguerias_ibfk_2" FOREIGN KEY ("numero_lote") REFERENCES "lotes_en_stock" ("numero_lote")
 )

 6. Tabla "droguerias" (
   "cuit" varchar(20) NOT NULL,
   "nombre" varchar(100) NOT NULL,
   PRIMARY KEY ("cuit")
 )

 7. Tabla "forma_farmaceutica" (
   "forma_id" int NOT NULL AUTO_INCREMENT,
   "nombre" varchar(50) NOT NULL,
   PRIMARY KEY ("forma_id"),
   UNIQUE KEY "nombre" ("nombre")
 )

 8. Tabla "historial_precios" (
   "numero_historial" int NOT NULL AUTO_INCREMENT,
   "codigo_barras" varchar(50) NOT NULL,
   "precio_pvp_anterior" decimal(10,2) NOT NULL,
   "precio_pvp_actual" decimal(10,2) NOT NULL,
   "fecha_modificacion" datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
   PRIMARY KEY ("numero_historial"),
   KEY "codigo_barras" ("codigo_barras"),
   CONSTRAINT "historial_precios_ibfk_1" FOREIGN KEY ("codigo_barras") REFERENCES "productos" ("codigo_barras")
 )

 9. Tabla "laboratorios" (
   "laboratorio_id" int NOT NULL AUTO_INCREMENT,
   "nombre" varchar(100) NOT NULL,
   "cuit" varchar(20) NOT NULL,
   "email" varchar(100) DEFAULT NULL,
   PRIMARY KEY ("laboratorio_id"),
   UNIQUE KEY "cuit" ("cuit")
 )

 10. Tabla "lotes_en_stock" (
   "numero_lote" varchar(50) NOT NULL,
   "codigo_barras" varchar(50) NOT NULL,
   "posicion_id" int NOT NULL,
   "numero_pedido" int DEFAULT NULL,
   "fecha_vencimiento" date NOT NULL,
   "cantidad_stock" int NOT NULL DEFAULT '0',
   PRIMARY KEY ("numero_lote"),
   KEY "codigo_barras" ("codigo_barras"),
   KEY "posicion_id" ("posicion_id"),
   KEY "numero_pedido" ("numero_pedido"),
   CONSTRAINT "lotes_en_stock_ibfk_1" FOREIGN KEY ("codigo_barras") REFERENCES "productos" ("codigo_barras"),
   CONSTRAINT "lotes_en_stock_ibfk_2" FOREIGN KEY ("posicion_id") REFERENCES "posiciones_deposito" ("posicion_id"),
   CONSTRAINT "lotes_en_stock_ibfk_3" FOREIGN KEY ("numero_pedido") REFERENCES "pedidos" ("numero_pedido")
 )

 11. Tabla "monodrogas" (
   "monodroga_id" int NOT NULL AUTO_INCREMENT,
   "nombre" varchar(100) NOT NULL,
   PRIMARY KEY ("monodroga_id"),
   UNIQUE KEY "nombre" ("nombre")
 )

 12. Tabla "monodrogas_acciones" (
   "monodroga_id" int NOT NULL,
   "accion_id" int NOT NULL,
   PRIMARY KEY ("monodroga_id","accion_id"),
   KEY "accion_id" ("accion_id"),
   CONSTRAINT "monodrogas_acciones_ibfk_1" FOREIGN KEY ("monodroga_id") REFERENCES "monodrogas" ("monodroga_id") ON DELETE CASCADE,
   CONSTRAINT "monodrogas_acciones_ibfk_2" FOREIGN KEY ("accion_id") REFERENCES "accion_terapeutica" ("accion_id") ON DELETE CASCADE
 )

 13. Tabla "pedidos" (
   "numero_pedido" int NOT NULL AUTO_INCREMENT,
   "cuit_drogueria" varchar(20) NOT NULL,
   "codigo_barras" varchar(50) NOT NULL,
   "cantidad_solicitada" int NOT NULL,
   "precio_costo_unitario" decimal(10,2) NOT NULL,
   "fecha_pedido" datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
   "estado_pedido" varchar(30) NOT NULL DEFAULT 'Pendiente',
   PRIMARY KEY ("numero_pedido"),
   KEY "cuit_drogueria" ("cuit_drogueria"),
   KEY "codigo_barras" ("codigo_barras"),
   CONSTRAINT "pedidos_ibfk_1" FOREIGN KEY ("cuit_drogueria") REFERENCES "droguerias" ("cuit"),
   CONSTRAINT "pedidos_ibfk_2" FOREIGN KEY ("codigo_barras") REFERENCES "productos" ("codigo_barras")
 )

14. Tabla "posiciones_deposito" (
   "posicion_id" int NOT NULL AUTO_INCREMENT,
   "nombre_posicion" varchar(50) NOT NULL,
   "sector_id" int NOT NULL,
   PRIMARY KEY ("posicion_id"),
   KEY "sector_id" ("sector_id"),
   CONSTRAINT "posiciones_deposito_ibfk_1" FOREIGN KEY ("sector_id") REFERENCES "sectores_deposito" ("sector_id")
 )

15. Tabla "presentaciones" (
   "presentacion_id" int NOT NULL AUTO_INCREMENT,
   "descripcion" varchar(50) NOT NULL,
   PRIMARY KEY ("presentacion_id"),
   UNIQUE KEY "descripcion" ("descripcion")
 )

16. Tabla "productos" (
   "codigo_barras" varchar(50) NOT NULL,
   "nombre_comercial" varchar(100) NOT NULL,
   "precio_pvp_actual" decimal(10,2) NOT NULL,
   "laboratorio_id" int NOT NULL,
   "forma_id" int NOT NULL,
   "concentracion_id" int NOT NULL,
   "presentacion_id" int NOT NULL,
   "categoria_id" int NOT NULL,
   PRIMARY KEY ("codigo_barras"),
   KEY "laboratorio_id" ("laboratorio_id"),
   KEY "forma_id" ("forma_id"),
   KEY "concentracion_id" ("concentracion_id"),
   KEY "presentacion_id" ("presentacion_id"),
   KEY "categoria_id" ("categoria_id"),
   CONSTRAINT "productos_ibfk_1" FOREIGN KEY ("laboratorio_id") REFERENCES "laboratorios" ("laboratorio_id"),
   CONSTRAINT "productos_ibfk_2" FOREIGN KEY ("forma_id") REFERENCES "forma_farmaceutica" ("forma_id"),
   CONSTRAINT "productos_ibfk_3" FOREIGN KEY ("concentracion_id") REFERENCES "concentraciones" ("concentracion_id"),
   CONSTRAINT "productos_ibfk_4" FOREIGN KEY ("presentacion_id") REFERENCES "presentaciones" ("presentacion_id"),
   CONSTRAINT "productos_ibfk_5" FOREIGN KEY ("categoria_id") REFERENCES "categoria_productos" ("categoria_id")
 )

 17. Tabla "productos_monodrogas" (
   "codigo_barras" varchar(50) NOT NULL,
   "monodroga_id" int NOT NULL,
   PRIMARY KEY ("codigo_barras","monodroga_id"),
   KEY "monodroga_id" ("monodroga_id"),
   CONSTRAINT "productos_monodrogas_ibfk_1" FOREIGN KEY ("codigo_barras") REFERENCES "productos" ("codigo_barras") ON DELETE CASCADE,
   CONSTRAINT "productos_monodrogas_ibfk_2" FOREIGN KEY ("monodroga_id") REFERENCES "monodrogas" ("monodroga_id") ON DELETE CASCADE
 )

18. Tabla "sectores_deposito" (
   "sector_id" int NOT NULL AUTO_INCREMENT,
   "nombre_sector" varchar(50) NOT NULL,
   "requiere_refrigeracion" tinyint(1) NOT NULL DEFAULT '0',
   PRIMARY KEY ("sector_id"),
   UNIQUE KEY "nombre_sector" ("nombre_sector")
 )

 19. Tabla "telefonos_droguerias" (
   "telefono_id" int NOT NULL AUTO_INCREMENT,
   "cuit_drogueria" varchar(20) NOT NULL,
   "numero" varchar(50) NOT NULL,
   "tipo_contacto" varchar(50) DEFAULT NULL,
   PRIMARY KEY ("telefono_id"),
   KEY "cuit_drogueria" ("cuit_drogueria"),
   CONSTRAINT "telefonos_droguerias_ibfk_1" FOREIGN KEY ("cuit_drogueria") REFERENCES "droguerias" ("cuit") ON DELETE CASCADE
 )

20. Tabla "telefonos_laboratorios" (
   "telefono_id" int NOT NULL AUTO_INCREMENT,
   "laboratorio_id" int NOT NULL,
   "numero" varchar(50) NOT NULL,
   "tipo_contacto" varchar(50) DEFAULT NULL,
   PRIMARY KEY ("telefono_id"),
   KEY "laboratorio_id" ("laboratorio_id"),
   CONSTRAINT "telefonos_laboratorios_ibfk_1" FOREIGN KEY ("laboratorio_id") REFERENCES "laboratorios" ("laboratorio_id") ON DELETE CASCADE
 )

 REGLAS PARA CONSULTAS SQL:
- Genera ÚNICAMENTE consultas de lectura SQL que empiecen con 'SELECT'.
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
