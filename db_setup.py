import sqlite3

# Crear base de datos
conn = sqlite3.connect("inventario.db")
cursor = conn.cursor()

# Tabla productos con campo 'marca'
cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    marca TEXT NOT NULL,
    stock INTEGER NOT NULL
)
""")

# Tabla historial ventas / salidas
cursor.execute("""
CREATE TABLE IF NOT EXISTS historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER,
    fecha TEXT,
    tipo TEXT,  -- 'venta' o 'salida_no_autorizada'
    FOREIGN KEY(producto_id) REFERENCES productos(id)
)
""")

# Insertar productos de prueba con marca
cursor.execute("INSERT INTO productos (nombre, marca, stock) VALUES (?, ?, ?)", ("Perfume", "Natura", 10))
cursor.execute("INSERT INTO productos (nombre, marca, stock) VALUES (?, ?, ?)", ("Crema", "Yanbal", 15))

conn.commit()
conn.close()

print("✅ Base de datos creada con productos de prueba y marcas")
