"""
Detecta si una habitación "tiene cosas" comparando su mapa de profundidad
contra el de una foto de la habitación vacía (cámara fija).
Modelo preentrenado: Depth Anything V2 Small (Apache-2.0). Sin entrenamiento.
La calibración (foto vacía + sensibilidad) la hace el rol "learning".
"""
import base64
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

CARPETA_REF = Path(__file__).resolve().parent / "referencias"
ARCHIVO_CONFIG = Path(__file__).resolve().parent / "config_volumen.json"
MODELO_ID = "depth-anything/Depth-Anything-V2-Small-hf"
ANCHO = 640

CONFIG_POR_DEFECTO = {
    "umbral_diff": 0.15,   # cuánto debe cambiar la profundidad (0-1)
    "area_min_pct": 1.5,   # % mínimo de imagen cambiada para decir "hay cosas"
}


# ------------------------------------------------------------
# Configuración de sensibilidad (la edita el rol learning)
# ------------------------------------------------------------
def obtener_config() -> dict:
    config = dict(CONFIG_POR_DEFECTO)
    try:
        guardado = json.loads(ARCHIVO_CONFIG.read_text(encoding="utf-8"))
        for clave in config:
            if clave in guardado:
                config[clave] = float(guardado[clave])
    except (OSError, ValueError):
        pass
    return config


def _validar_config(umbral_diff: float, area_min_pct: float) -> None:
    if not 0.02 <= umbral_diff <= 0.6:
        raise ValueError("El umbral de profundidad debe estar entre 0.02 y 0.60")
    if not 0.1 <= area_min_pct <= 50:
        raise ValueError("El área mínima debe estar entre 0.1 y 50 %")


def guardar_config(umbral_diff: float, area_min_pct: float) -> dict:
    _validar_config(umbral_diff, area_min_pct)
    config = {"umbral_diff": umbral_diff, "area_min_pct": area_min_pct}
    ARCHIVO_CONFIG.write_text(json.dumps(config), encoding="utf-8")
    return config


# ------------------------------------------------------------
# Referencia (foto de la habitación vacía)
# ------------------------------------------------------------
def ruta_referencia(camara_id: int) -> Path:
    return CARPETA_REF / f"cam{camara_id}.jpg"


def hay_referencia(camara_id: int) -> bool:
    return ruta_referencia(camara_id).exists()


def guardar_referencia(camara_id: int, contenido: bytes) -> None:
    img = _decodificar(contenido)
    CARPETA_REF.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(ruta_referencia(camara_id)), img)


# ------------------------------------------------------------
# Modelo de profundidad
# ------------------------------------------------------------
@lru_cache(maxsize=1)
def _pipe():
    # Import perezoso: el servidor arranca aunque transformers tarde en cargar
    from transformers import pipeline
    return pipeline("depth-estimation", model=MODELO_ID)


def _decodificar(contenido: bytes):
    img = cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("La imagen no es válida")
    h, w = img.shape[:2]
    return cv2.resize(img, (ANCHO, int(h * ANCHO / w)))


def _profundidad(img_bgr) -> np.ndarray:
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    salida = _pipe()(Image.fromarray(rgb))
    d = np.array(salida["depth"], dtype=np.float32)
    rango = float(d.max() - d.min())
    d = (d - d.min()) / (rango if rango > 0 else 1.0)
    return cv2.resize(d, (img_bgr.shape[1], img_bgr.shape[0]))


def _alinear(actual: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """La profundidad es relativa: ajusta la escala de 'actual' a 'ref'
    ignorando los píxeles que más difieren (donde estarían los objetos)."""
    a, r = actual.ravel(), ref.ravel()
    mask = np.ones_like(a, dtype=bool)
    k, b = 1.0, 0.0
    for _ in range(3):
        A = np.vstack([a[mask], np.ones(int(mask.sum()))]).T
        k, b = np.linalg.lstsq(A, r[mask], rcond=None)[0]
        res = np.abs(k * a + b - r)
        mask = res <= np.percentile(res, 80)
    return k * actual + b


def analizar_bytes(
    camara_id: int,
    contenido: bytes,
    umbral_diff: Optional[float] = None,
    area_min_pct: Optional[float] = None,
) -> dict:
    """Si no se pasan umbrales, usa los guardados en config_volumen.json."""
    ruta = ruta_referencia(camara_id)
    if not ruta.exists():
        raise FileNotFoundError("No hay foto de la habitación vacía")

    config = obtener_config()
    if umbral_diff is None:
        umbral_diff = config["umbral_diff"]
    if area_min_pct is None:
        area_min_pct = config["area_min_pct"]
    _validar_config(umbral_diff, area_min_pct)

    ref_img = cv2.imread(str(ruta))
    act_img = _decodificar(contenido)
    act_img = cv2.resize(act_img, (ref_img.shape[1], ref_img.shape[0]))

    ref_d = _profundidad(ref_img)
    act_d = _alinear(_profundidad(act_img), ref_d)

    diff = cv2.GaussianBlur(np.abs(act_d - ref_d), (9, 9), 0)
    mascara = (diff > umbral_diff).astype(np.uint8)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))

    porcentaje = float(mascara.mean() * 100)

    overlay = act_img.copy()
    overlay[mascara == 1] = (0, 0, 255)
    resultado = cv2.addWeighted(overlay, 0.5, act_img, 0.5, 0)
    _, buf = cv2.imencode(".jpg", resultado, [cv2.IMWRITE_JPEG_QUALITY, 85])
    imagen = "data:image/jpeg;base64," + base64.b64encode(buf).decode()

    return {
        "hay_cosas": porcentaje >= area_min_pct,
        "porcentaje": round(porcentaje, 1),
        "umbral_diff": umbral_diff,
        "area_min_pct": area_min_pct,
        "imagen": imagen,
    }