import sqlite3

# Crear base de datos
conn = sqlite3.connect("inventario.db")
cursor = conn.cursor()

# Tabla productos
cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    categoria TEXT,
    marca TEXT,
    stock INTEGER,
    precio REAL,
    imagen TEXT,
    fecha_ingreso TEXT DEFAULT (strftime('%d-%m-%Y', 'now'))
)
""")

# Tabla historial
cursor.execute("""
CREATE TABLE IF NOT EXISTS historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER,
    fecha TEXT,
    tipo TEXT,  -- 'venta' o 'salida_no_autorizada'
    FOREIGN KEY(producto_id) REFERENCES productos(id)
)
""")

# Insertar productos de prueba
cursor.execute("INSERT INTO productos (nombre, categoria, marca, stock, precio) VALUES (?, ?, ?, ?, ?)",
               ("Perfume", "Fragancia", "Natura", 10, 45.0))
cursor.execute("INSERT INTO productos (nombre, categoria, marca, stock, precio) VALUES (?, ?, ?, ?, ?)",
               ("Crema hidratante", "Cuidado de piel", "Yanbal", 15, 30.0))

conn.commit()
conn.close()

print("✅ Base de datos creada correctamente con productos de prueba y fecha automática.")
