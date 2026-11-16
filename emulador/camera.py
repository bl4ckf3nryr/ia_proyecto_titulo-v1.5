"""
camera.py
Sirve los frames 3D reales generados por la interfaz Three.js
como flujo MJPEG multipart. Fallback a placeholder con HUD de seguridad.
"""

import io
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

CAMERA_ID = "CAM-BODEGA-01"
FRAME_W = 1280
FRAME_H = 720
FPS = 10
JPEG_QUALITY = 82

COL_BG = (14, 16, 20)
COL_TEXT = (235, 238, 240)
COL_ACCENT = (0, 230, 118)
COL_WARN = (255, 176, 32)
COL_REC = (255, 42, 42)


def _load_font(size):
    for name in ("DejaVuSans-Bold.ttf", "arial.ttf", "Arial.ttf", "consola.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_hud(draw, w, h):
    """Dibuja el HUD estilo cámara de seguridad: REC, ID, timestamp y esquinas."""
    font_hud = _load_font(22)
    font_hud_sm = _load_font(18)
    font_sm = _load_font(15)

    # REC parpadeante
    ts_ms = int(time.time() * 1000)
    if (ts_ms // 500) % 2 == 0:
        draw.ellipse([22, 22, 42, 42], fill=COL_REC)
    draw.text((52, 22), "REC", fill=(255, 255, 255), font=font_hud)

    # ID
    draw.text((20, 58), CAMERA_ID, fill=COL_ACCENT, font=font_hud_sm)

    # Timestamp
    ts = datetime.now()
    draw.text((w - 20, 22), ts.strftime("%Y-%m-%d"),
              fill=(255, 255, 255), font=font_hud, anchor="ra")
    draw.text((w - 20, 50), ts.strftime("%H:%M:%S"),
              fill=(255, 255, 255), font=font_hud, anchor="ra")

    # Esquinas HUD
    m, l = 26, 42
    col = (200, 200, 200)
    for (x0, y0, x1, y1, x2, y2) in [
        (m, m + l, m, m, m + l, m),                 # sup-izq
        (w - m - l, m, w - m, m, w - m, m + l),     # sup-der
        (m, h - m - l, m, h - m, m + l, h - m),     # inf-izq
        (w - m - l, h - m, w - m, h - m, w - m, h - m - l),  # inf-der
    ]:
        draw.line([(x0, y0), (x1, y1), (x2, y2)], fill=col, width=2)

    # Cruz central
    draw.line([(w//2 - 20, h//2), (w//2 + 20, h//2)], fill=(120, 120, 120), width=1)
    draw.line([(w//2, h//2 - 20), (w//2, h//2 + 20)], fill=(120, 120, 120), width=1)

    # Pie
    draw.text((20, h - 34), "1920x1080", fill=(255, 255, 255), font=font_sm)
    draw.text((w - 20, h - 34), "10 FPS", fill=(255, 255, 255),
              font=font_sm, anchor="ra")
    draw.rectangle([0, h - 4, w, h], fill=(0, 0, 0))


def build_placeholder_frame(reason="Sin señal 3D"):
    """Frame de respaldo con HUD de seguridad cuando no hay interfaz 3D."""
    img = Image.new("RGB", (FRAME_W, FRAME_H), COL_BG)
    draw = ImageDraw.Draw(img)

    # Cuadrícula sutil
    for x in range(0, FRAME_W, 80):
        draw.line([(x, 0), (x, FRAME_H)], fill=(24, 28, 34), width=1)
    for y in range(0, FRAME_H, 80):
        draw.line([(0, y), (FRAME_W, y)], fill=(24, 28, 34), width=1)

    # Texto central
    font_lg = _load_font(44)
    font_md = _load_font(20)
    cx, cy = FRAME_W // 2, FRAME_H // 2
    draw.text((cx, cy - 50), "CÁMARA 3D SIN SEÑAL", fill=COL_WARN,
              font=font_lg, anchor="mm")
    draw.text((cx, cy), reason, fill=COL_TEXT, font=font_md, anchor="mm")
    draw.text((cx, cy + 40),
              "Abra la interfaz en: http://127.0.0.1:8080/",
              fill=(170, 175, 180), font=font_md, anchor="mm")

    _draw_hud(draw, FRAME_W, FRAME_H)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()


def mjpeg_stream_from_buffer(get_frame, frame_age):
    """
    Generador MJPEG multipart que sirve los frames reales
    desde el buffer compartido con la interfaz 3D.
    """
    boundary = b"--frame\r\n"
    interval = 1.0 / FPS
    placeholder = None
    placeholder_ts = 0.0

    while True:
        jpg = get_frame()
        age = frame_age()

        if jpg is None or age > 5.0:
            now = time.time()
            if placeholder is None or (now - placeholder_ts) > 0.5:
                if jpg is None:
                    placeholder = build_placeholder_frame(
                        "Abra la interfaz 3D para iniciar la camara"
                    )
                else:
                    placeholder = build_placeholder_frame(
                        f"Senal 3D perdida (ultima hace {age:.0f}s)"
                    )
                placeholder_ts = now
            jpg = placeholder

        yield (
            boundary
            + b"Content-Type: image/jpeg\r\n"
            + b"Content-Length: " + str(len(jpg)).encode() + b"\r\n\r\n"
            + jpg
            + b"\r\n"
        )
        time.sleep(interval)