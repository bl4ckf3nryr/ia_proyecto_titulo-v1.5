"""Guarda frames de una cámara en dataset/images/train para etiquetarlos.

Uso (desde la raíz de login-simple/):
    python deepseek/capturar.py 3 --cantidad 20 --cada 10

Sirve para armar el dataset con imágenes reales de tu bodega.
Captura en distintos momentos del día para tener variedad de luz.
"""
import argparse
import time
from datetime import datetime
from pathlib import Path

import cv2

from camara import leer_frame, url_de_camara

DESTINO = Path(__file__).resolve().parent / "dataset" / "images" / "train"


def main():
    parser = argparse.ArgumentParser(description="Captura frames de una cámara")
    parser.add_argument("camara", type=int, help="id de la cámara en la base de datos")
    parser.add_argument("--cantidad", type=int, default=10, help="cuántos frames guardar")
    parser.add_argument("--cada", type=float, default=10, help="segundos entre frames")
    args = parser.parse_args()

    DESTINO.mkdir(parents=True, exist_ok=True)
    url = url_de_camara(args.camara)

    for i in range(args.cantidad):
        frame = leer_frame(url)
        nombre = f"cam{args.camara}_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        cv2.imwrite(str(DESTINO / nombre), frame)
        print(f"[{i + 1}/{args.cantidad}] {nombre}")
        if i < args.cantidad - 1:
            time.sleep(args.cada)


if __name__ == "__main__":
    main()