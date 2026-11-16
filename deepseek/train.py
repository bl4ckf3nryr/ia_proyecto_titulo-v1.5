"""Entrena un YOLO de segmentación para distinguir piso y pared.

Uso (desde cualquier carpeta):
    python deepseek/train.py
"""
import os
from pathlib import Path

from ultralytics import YOLO

AQUI = Path(__file__).resolve().parent


def main():
    # Trabajamos desde deepseek/ para que "path: dataset" del data.yaml funcione
    os.chdir(AQUI)

    modelo = YOLO("yolov8n-seg.pt")  # modelo base de segmentación (se descarga solo)
    modelo.train(
        data="data.yaml",
        epochs=100,
        imgsz=640,
        batch=8,
        project="runs",
        name="piso_pared",
        exist_ok=True,   # reutiliza runs/piso_pared en vez de crear piso_pared2, 3...
        workers=2,
    )


# El if es obligatorio en Windows
if __name__ == "__main__":
    main()
