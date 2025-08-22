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
recognizer = ProductRecognizer(image_base_dir=".")
recognizer.reload()

# Lista de marcas (por si la usas en tu formulario)
marcas = ["Ésika", "Natura", "L'Bel", "Yanbal", "Cyzone",
          "Avon", "Vogue", "Maybelline", "Premier", "Mary Kay", "Otros"]

# Página principal (dashboard inventario)
@app.route("/")
def index():
    conn = get_connection()
    # Formateamos fecha como dd-mm-YYYY al traerla
    productos = conn.execute("""
        SELECT id, nombre, categoria, stock, precio, imagen,
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
    stock = request.form.get("stock", 0)
    precio = request.form.get("precio", 0)

    # Guardar solo la fecha (dd-mm-YYYY)
    fecha_ingreso = datetime.now().strftime("%d-%m-%Y")

    imagen = None
    if "imagen" in request.files:
        file = request.files["imagen"]
        if file and file.filename != "":
            # Guardar imagen subida como referencia
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(save_path)
            imagen = save_path

    conn = get_connection()
    conn.execute("""
        INSERT INTO productos (nombre, categoria, stock, precio, imagen, fecha_ingreso)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nombre, categoria, stock, precio, imagen, fecha_ingreso))
    conn.commit()
    conn.close()

    # Recargar referencias para incluir este nuevo producto como referencia
    recognizer.reload()

    return redirect(url_for("index"))

# Recargar referencias manualmente (por si agregas muchas imágenes)
@app.route("/recargar_referencias", methods=["POST"])
def recargar_referencias():
    recognizer.reload()
    return jsonify({"ok": True, "msg": "Referencias recargadas"})

# Reconocer producto a partir de una imagen enviada (multipart/form-data)
@app.route("/reconocer", methods=["POST"])
def reconocer():
    if "imagen" not in request.files:
        return jsonify({"ok": False, "msg": "Falta el archivo 'imagen'"}), 400

    file = request.files["imagen"]
    if not file or file.filename == "":
        return jsonify({"ok": False, "msg": "Archivo vacío"}), 400

    # Leer bytes -> BGR (OpenCV)
    file_bytes = np.frombuffer(file.read(), np.uint8)
    bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if bgr is None:
        return jsonify({"ok": False, "msg": "No se pudo decodificar la imagen"}), 400

    ref, score = recognizer.recognize_from_bgr(bgr)
    if not ref:
        return jsonify({"ok": False, "msg": "No se reconoció el producto", "debug_score": score})

    # Traer datos completos desde BD
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

    # Puedes construir una "descripción" simple combinando campos
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
        "match_score": score  # útil para ajustar umbral
    })

if __name__ == "__main__":
    app.run(debug=True)
