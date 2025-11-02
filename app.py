from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from datetime import datetime
from database import init_db, get_connection
from recognizer import ProductRecognizer
import numpy as np
import cv2

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Inicializar DB
init_db()

# Inicializar reconocedor (carga imágenes de referencia desde BD)
recognizer = ProductRecognizer()
recognizer.reload()

# Lista de marcas (por si la usas en tu formulario)
marcas = ["Ésika", "Natura", "L'Bel", "Yanbal", "Cyzone",
          "Avon", "Vogue", "Maybelline", "Premier", "Mary Kay", "Otros"]

# Página principal (dashboard inventario)
@app.route("/")
def index():
    conn = get_connection()
    productos = conn.execute("""
        SELECT id, nombre, categoria, marca, stock, precio, imagen,
               strftime('%d-%m-%Y', fecha_ingreso) AS fecha_ingreso
        FROM productos
        ORDER BY id DESC
    """).fetchall()
    conn.close()
    return render_template("index.html", productos=productos, marcas=marcas)

# Ruta para agregar producto
@app.route("/agregar", methods=["POST"])
def agregar():
    nombre = request.form["nombre"]
    categoria = request.form.get("categoria", "")
    marca = request.form.get("marca", "")  # ✅ nuevo campo
    stock = request.form.get("stock", 0)
    precio = request.form.get("precio", 0)

    imagen = None
    if "imagen" in request.files:
        file = request.files["imagen"]
        if file and file.filename != "":
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(save_path)
            imagen = save_path

    conn = get_connection()
    conn.execute("""
        INSERT INTO productos (nombre, categoria, marca, stock, precio, imagen)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nombre, categoria, marca, stock, precio, imagen))
    conn.commit()
    conn.close()

    recognizer.reload()

    return redirect(url_for("index"))

# Ruta para eliminar producto
@app.route("/eliminar/<int:id>", methods=["POST"])
def eliminar(id):
    conn = get_connection()
    conn.execute("DELETE FROM productos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    recognizer.reload()  # recarga referencias si eliminas uno existente
    return redirect(url_for("index"))

# Ruta para editar producto (solo ejemplo)
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = get_connection()
    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria = request.form.get("categoria", "")
        marca = request.form.get("marca", "")
        stock = request.form.get("stock", 0)
        precio = request.form.get("precio", 0)
        conn.execute("""
            UPDATE productos
            SET nombre=?, categoria=?, marca=?, stock=?, precio=?
            WHERE id=?
        """, (nombre, categoria, marca, stock, precio, id))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    # GET → mostrar formulario con datos
    producto = conn.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("editar.html", producto=producto, marcas=marcas)



# Recargar referencias manualmente (por si agregas muchas imágenes)
@app.route("/recargar_referencias", methods=["POST"])
def recargar_referencias():
    recognizer.reload()
    return jsonify({"ok": True, "msg": "Referencias recargadas"})

# Reconocer producto a partir de una imagen enviada (multipart/form-data)
@app.route("/reconocer", methods=["POST"])
def reconocer():
    file = request.files.get("imagen")
    if not file:
        return jsonify({"ok": False, "msg": "No se envió imagen"})

    path = "static/temp.jpg"
    file.save(path)

    nombre, score = recognizer.recognize(path)
    # Si recognizer devuelve un dict con info del producto
    if isinstance(nombre, dict):
        producto_nombre = nombre.get("nombre")
    else:
        producto_nombre = nombre
    if not producto_nombre:
        return jsonify({"ok": False, "msg": "No se encontró coincidencia", "debug_score": score})
    
    conn = get_connection()
    row = conn.execute("SELECT * FROM productos WHERE nombre = ?", (producto_nombre,)).fetchone()
    conn.close()

    if not row:
        return jsonify({"ok": False, "msg": "No se encontró en base de datos"})

    return jsonify({
    "ok": True,
    "nombre": row["nombre"],
    "categoria": row["categoria"],
    "marca": row["marca"] if "marca" in row.keys() else "Sin marca",
    "precio": row["precio"] if "precio" in row.keys() else "No registrado",
    "imagen": row["imagen"],
    "match_score": score,
    "fecha_ingreso": row["fecha_ingreso"] if "fecha_ingreso" in row.keys() else None
    })


    # 📸 Reconocer producto desde imagen base64 (por cámara de celular)
@app.route("/reconocer_base64", methods=["POST"])
def reconocer_base64():
    data = request.json
    if not data or "image" not in data:
        return jsonify({"ok": False, "msg": "Falta campo 'image'"}), 400

    import base64
    img_b64 = data["image"].split(",")[-1]
    img_bytes = base64.b64decode(img_b64)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return jsonify({"ok": False, "msg": "No se pudo decodificar la imagen"}), 400

    ref, score = recognizer.recognize_from_bgr(bgr)
    if not ref:
        return jsonify({"ok": False, "msg": "No se reconoció el producto", "debug_score": score})

    conn = get_connection()
    prod = conn.execute("""
        SELECT id, nombre, categoria, stock, precio, imagen,
               strftime('%d-%m-%Y', fecha_ingreso) AS fecha_ingreso
        FROM productos
        WHERE id = ?
    """, (ref["id"],)).fetchone()
    conn.close()

    if not prod:
        return jsonify({"ok": False, "msg": "Referencia encontrada pero no existe en BD"})

    descripcion = f"{prod['nombre']} ({prod['categoria']}) - Precio S/. {prod['precio']}"

    return jsonify({
        "ok": True,
        "id": prod["id"],
        "nombre": prod["nombre"],
        "categoria": prod["categoria"],
        "precio": prod["precio"],
        "stock": prod["stock"],
        "fecha_ingreso": prod["fecha_ingreso"],
        "imagen": prod["imagen"],
        "descripcion": descripcion,
        "match_score": score
    })

if __name__ == "__main__":
    app.run(debug=True)
