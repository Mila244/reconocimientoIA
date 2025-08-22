import os
import cv2
import numpy as np
from database import get_connection

class ProductRecognizer:
    def __init__(self, image_base_dir="."):
        self.image_base_dir = image_base_dir
        # ORB y matcher (rápidos y sin GPU)
        self.orb = cv2.ORB_create(nfeatures=2000)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.refs = []  # [{id, nombre, path, des}, ...]

    def _abs_path(self, path):
        if not path:
            return None
        return path if os.path.isabs(path) else os.path.join(self.image_base_dir, path)

    def _load_gray(self, path):
        if not path or not os.path.exists(path):
            return None
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        return img

    def reload(self):
        """Carga/recarga referencias desde la BD."""
        self.refs.clear()
        conn = get_connection()
        rows = conn.execute("SELECT id, nombre, imagen FROM productos WHERE imagen IS NOT NULL").fetchall()
        conn.close()

        for r in rows:
            p = self._abs_path(r["imagen"])
            gray = self._load_gray(p)
            if gray is None:
                continue
            kp, des = self.orb.detectAndCompute(gray, None)
            if des is None:
                continue
            self.refs.append({
                "id": r["id"],
                "nombre": r["nombre"],
                "path": r["imagen"],
                "des": des
            })

    def recognize_from_bgr(self, bgr_img, min_good_matches=20):
        """Devuelve (ref, score) si encuentra producto; ref=None si no."""
        if bgr_img is None:
            return None, 0
        gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        kp2, des2 = self.orb.detectAndCompute(gray, None)
        if des2 is None or len(des2) < 10 or not self.refs:
            return None, 0

        best_ref = None
        best_score = 0

        for ref in self.refs:
            matches = self.bf.match(ref["des"], des2)
            # Menor distancia = mejor. Puntuar por cantidad de "buenos" (dist < 60)
            good = [m for m in matches if m.distance < 60]
            score = len(good)
            if score > best_score:
                best_score = score
                best_ref = ref

        if best_ref is not None and best_score >= min_good_matches:
            return best_ref, best_score
        return None, best_score
