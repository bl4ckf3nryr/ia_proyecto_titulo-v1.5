"""Conecta la base de datos de cámaras con YOLO.

- url_de_camara(id): lee url_stream de la tabla de cámaras.
- leer_frame(url):   abre el stream (RTSP o http MJPEG) y devuelve un frame.
- frame_de_camara(id): las dos anteriores juntas.

Ejecuta los scripts desde la raíz del proyecto para que
"sqlite:///./login.db" apunte al login.db correcto.
"""
import os
import sys
from pathlib import Path

# Debe ir antes de importar cv2: RTSP por TCP es más estable que por UDP
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

import cv2  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent  # raíz del proyecto
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def url_de_camara(camara_id: int) -> str:
    """Devuelve el url_stream guardado en la base de datos."""
    from base_de_datos.camaras import obtener_por_id
    from base_de_datos.conexion import SesionLocal

    sesion = SesionLocal()
    try:
        camara = obtener_por_id(sesion, camara_id)
        if camara is None:
            raise ValueError(f"No existe la cámara con id {camara_id}")
        return camara.url_stream
    finally:
        sesion.close()


def leer_frame(url: str, descartar: int = 5):
    """Abre el stream y devuelve el frame más reciente (BGR, numpy)."""
    captura = cv2.VideoCapture(url)
    if not captura.isOpened():
        raise RuntimeError(f"No se pudo abrir el stream: {url}")
    try:
        frame = None
        # Se leen varios frames para saltarse los que quedaron en el buffer
        for _ in range(descartar):
            ok, actual = captura.read()
            if ok:
                frame = actual
        if frame is None:
            raise RuntimeError("El stream abrió pero no entregó imagen")
        return frame
    finally:
        captura.release()


def frame_de_camara(camara_id: int):
    return leer_frame(url_de_camara(camara_id))