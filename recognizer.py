import os
import cv2
import numpy as np
import sqlite3

DB_NAME = "inventario.db"
UPLOAD_FOLDER = "static/uploads"

class ProductRecognizer:
    def __init__(self):
        self.refs = []  # referencias cargadas desde la BD
        self.reload()

    def reload(self):
        """Carga las imágenes de referencia desde la base de datos."""
        self.refs.clear()
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, nombre, marca, imagen FROM productos WHERE imagen IS NOT NULL"
        ).fetchall()
        conn.close()

        for r in rows:
            path = r["imagen"]
            if not os.path.exists(path):
                continue
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            self.refs.append({
                "id": r["id"],
                "nombre": r["nombre"],
                "marca": r["marca"],
                "img": img
            })

        print(f"🔄 {len(self.refs)} imágenes de referencia cargadas")

    def recognize(self, image_path):
        """Compara la imagen recibida con las referencias guardadas."""
        if not self.refs:
            print("⚠ No hay referencias cargadas")
            return None, 0

        img_query = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img_query is None:
            print("⚠ No se pudo leer la imagen recibida")
            return None, 0

        orb = cv2.ORB_create()
        kp_query, des_query = orb.detectAndCompute(img_query, None)
        if des_query is None:
            return None, 0

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        best_match = None
        best_score = 0

        for ref in self.refs:
            kp_ref, des_ref = orb.detectAndCompute(ref["img"], None)
            if des_ref is None:
                continue
            matches = bf.match(des_query, des_ref)
            score = len(matches)
            if score > best_score:
                best_score = score
                best_match = ref

        if best_match and best_score > 25:  # Umbral ajustable
            return best_match, best_score
        else:
            return None, best_score
