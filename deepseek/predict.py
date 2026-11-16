"""Segmenta una imagen en piso, pared y "otro" usando el modelo entrenado.

Uso (desde la raíz de login-simple/):
    python deepseek/predict.py ruta/a/imagen.jpg
    python deepseek/predict.py --camara 3     # usa el url_stream de la BD

Guarda <imagen>_resultado.png con piso en verde y pared en azul.
"""
import argparse
import os
from pathlib import Path

# Debe ir antes de importar cv2 (RTSP por TCP)
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

import cv2
import numpy as np
from ultralytics import YOLO

AQUI = Path(__file__).resolve().parent
COLOR_PISO = (0, 200, 0)     # BGR: verde
COLOR_PARED = (200, 100, 0)  # BGR: azul


def buscar_modelo() -> Path:
    """Devuelve el best.pt más reciente dentro de deepseek/runs/."""
    pesos = sorted(AQUI.glob("runs/**/weights/best.pt"), key=os.path.getmtime)
    if not pesos:
        raise FileNotFoundError("No hay modelo entrenado. Ejecuta train.py primero.")
    return pesos[-1]


def segmentar(imagen_bgr: np.ndarray, modelo: YOLO):
    """Devuelve tres máscaras booleanas (alto x ancho): piso, pared y otro.

    'otro' = todo lo que no es ni piso ni pared (base para el paso siguiente).
    """
    alto, ancho = imagen_bgr.shape[:2]
    resultado = modelo(imagen_bgr, verbose=False)[0]

    piso = np.zeros((alto, ancho), np.uint8)
    pared = np.zeros((alto, ancho), np.uint8)

    if resultado.masks is not None:
        clases = resultado.boxes.cls.int().tolist()
        for poligono, clase in zip(resultado.masks.xy, clases):
            destino = piso if clase == 0 else pared
            cv2.fillPoly(destino, [poligono.astype(np.int32)], 1)

    piso, pared = piso.astype(bool), pared.astype(bool)
    otro = ~(piso | pared)
    return piso, pared, otro


def main():
    parser = argparse.ArgumentParser(description="Segmenta piso y pared")
    parser.add_argument("imagen", nargs="?", help="ruta a una imagen")
    parser.add_argument("--camara", type=int, help="id de la cámara en la base de datos")
    args = parser.parse_args()

    if args.camara is not None:
        from camara import frame_de_camara

        imagen = frame_de_camara(args.camara)
        ruta = AQUI / f"camara_{args.camara}.jpg"
        cv2.imwrite(str(ruta), imagen)  # guarda el frame original
    elif args.imagen:
        ruta = Path(args.imagen)
        imagen = cv2.imread(str(ruta))
        if imagen is None:
            raise SystemExit(f"No se pudo leer la imagen: {ruta}")
    else:
        parser.error("indica una imagen o --camara ID")

    try:
        modelo = YOLO(str(buscar_modelo()))
    except FileNotFoundError as error:
        raise SystemExit(str(error))
    piso, pared, otro = segmentar(imagen, modelo)

    capa = imagen.copy()
    capa[piso] = COLOR_PISO
    capa[pared] = COLOR_PARED
    salida = cv2.addWeighted(capa, 0.5, imagen, 0.5, 0)

    destino = ruta.with_name(f"{ruta.stem}_resultado.png")
    cv2.imwrite(str(destino), salida)

    total = piso.size
    print(f"Piso:  {piso.sum() / total:.1%}")
    print(f"Pared: {pared.sum() / total:.1%}")
    print(f"Otro:  {otro.sum() / total:.1%}")
    print(f"Guardado en {destino}")


if __name__ == "__main__":
    main()