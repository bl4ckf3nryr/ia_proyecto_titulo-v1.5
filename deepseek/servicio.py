"""Segmentación piso/pared lista para usar desde main.py.

    from deepseek.servicio import modelo_disponible, segmentar_bytes

El modelo se carga una sola vez, la primera vez que se necesita, buscando
el best.pt más reciente en deepseek/runs/. Si reentrenas, reinicia el servidor.
"""
import base64
from functools import lru_cache

import cv2
import numpy as np
from ultralytics import YOLO

from deepseek.predict import COLOR_PARED, COLOR_PISO, buscar_modelo, segmentar


def modelo_disponible() -> bool:
    """True si ya existe un modelo entrenado."""
    try:
        buscar_modelo()
        return True
    except FileNotFoundError:
        return False


@lru_cache(maxsize=1)
def _modelo() -> YOLO:
    return YOLO(str(buscar_modelo()))


def segmentar_bytes(contenido: bytes) -> dict:
    """Recibe los bytes de una imagen (jpg/png) y devuelve porcentajes + imagen coloreada."""
    imagen = cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_COLOR)
    if imagen is None:
        raise ValueError("La imagen recibida no es válida")

    piso, pared, otro = segmentar(imagen, _modelo())

    capa = imagen.copy()
    capa[piso] = COLOR_PISO
    capa[pared] = COLOR_PARED
    resultado = cv2.addWeighted(capa, 0.5, imagen, 0.5, 0)

    ok, jpg = cv2.imencode(".jpg", resultado, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError("No se pudo codificar la imagen de salida")

    total = piso.size
    return {
        "piso": round(float(piso.sum()) / total * 100, 1),
        "pared": round(float(pared.sum()) / total * 100, 1),
        "otro": round(float(otro.sum()) / total * 100, 1),
        "imagen": "data:image/jpeg;base64," + base64.b64encode(jpg.tobytes()).decode(),
    }