"""
camera_headless.py
Cámara virtual 3D permanente (headless) en UN solo módulo.

Reemplaza camera.py + camera_worker.py. Provee:
  - Worker (hilo) con Chromium headless (Playwright) que captura /viewer3d
  - Buffer de frames compartido
  - Rutas: /video.mjpg, /snapshot.jpg, /viewer3d, /vendor/three.module.js,
           /api/camera/status  (diagnóstico: aquí se ve la causa real si falla)
  - Placeholder "SIN SEÑAL" que muestra el error real (no el mensaje viejo)

Uso en app.py (ver instrucciones):
    import camera_headless
    camera_headless.init_camera(app, port=8080)
"""
import base64
import io
import logging
import os
import threading
import time
import urllib.request

from flask import Response, jsonify, redirect, render_template, send_file

log = logging.getLogger("camera")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

CAMERA_ID = "CAM-BODEGA-01"
FPS = 10
JPEG_QUALITY = 0.82
STALE_SECONDS = 5          # sin frames nuevos por este tiempo => "reconectando"
W, H = 1280, 720

THREE_URL = "https://unpkg.com/three@0.160.0/build/three.module.js"
VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "vendor")
THREE_PATH = os.path.join(VENDOR_DIR, "three.module.js")

CHROMIUM_ARGS = [
    "--use-gl=angle",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
]


# ----------------------------------------------------------------------
#  Estado compartido
# ----------------------------------------------------------------------
class _State:
    def __init__(self):
        self.lock = threading.Lock()
        self.jpeg = None          # último frame real (bytes)
        self.ts = 0.0             # time.time() del último frame real
        self.frames = 0
        self.ready = False
        self.error = None         # último error del worker (texto)
        self.page_errors = []     # errores de consola/JS de la página headless
        self.restarts = 0

    def put(self, jpeg):
        with self.lock:
            self.jpeg = jpeg
            self.ts = time.time()
            self.frames += 1

    def get(self):
        with self.lock:
            return self.jpeg, self.ts

    def add_page_error(self, msg):
        with self.lock:
            self.page_errors.append(msg[:300])
            self.page_errors = self.page_errors[-8:]


STATE = _State()


def camera_status():
    jpeg, ts = STATE.get()
    age = (time.time() - ts) if ts else None
    return {
        "worker_ready": bool(STATE.ready and age is not None and age < STALE_SECONDS),
        "worker_error": STATE.error,
        "last_frame_age_s": None if age is None else round(age, 1),
        "frames": STATE.frames,
        "restarts": STATE.restarts,
        "page_errors": list(STATE.page_errors),
    }


# ----------------------------------------------------------------------
#  Placeholder (muestra la causa real)
# ----------------------------------------------------------------------
def _font(size):
    from PIL import ImageFont
    for name in ("arial.ttf", "DejaVuSans.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


_ph_cache = {"key": None, "jpeg": None}


def placeholder_jpeg(line1, line2=""):
    from PIL import Image, ImageDraw
    key = (line1, line2, int(time.time()))      # 1 regeneración por segundo (reloj)
    if _ph_cache["key"] == key:
        return _ph_cache["jpeg"]
    img = Image.new("RGB", (W, H), (14, 16, 20))
    d = ImageDraw.Draw(img)
    f_big, f_mid, f_sm = _font(54), _font(26), _font(22)

    def center(text, y, font, fill):
        if not text:
            return
        w = d.textlength(text, font=font)
        d.text(((W - w) / 2, y), text, font=font, fill=fill)

    center(line1, H / 2 - 70, f_big, (242, 194, 24))
    # línea 2 puede ser larga: partirla
    y = H / 2 + 10
    words, cur = (line2 or "").split(), ""
    for wd in words:
        if d.textlength(cur + " " + wd, font=f_mid) > W - 160:
            center(cur.strip(), y, f_mid, (200, 205, 212))
            y += 34
            cur = wd
        else:
            cur += " " + wd
    center(cur.strip(), y, f_mid, (200, 205, 212))

    ts = time.strftime("%Y-%m-%d"), time.strftime("%H:%M:%S")
    d.ellipse((22, 22, 42, 42), fill=(255, 42, 42))
    d.text((52, 18), "REC", font=f_sm, fill=(255, 255, 255))
    d.text((20, 56), CAMERA_ID, font=f_sm, fill=(0, 230, 118))
    for i, t in enumerate(ts):
        w = d.textlength(t, font=f_sm)
        d.text((W - 20 - w, 18 + 30 * i), t, font=f_sm, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    _ph_cache.update(key=key, jpeg=buf.getvalue())
    return _ph_cache["jpeg"]


def current_jpeg():
    """Frame real si está fresco; si no, placeholder con la causa."""
    jpeg, ts = STATE.get()
    if jpeg and (time.time() - ts) < STALE_SECONDS:
        return jpeg
    if STATE.error:
        return placeholder_jpeg("CÁMARA 3D SIN SEÑAL", "Error: " + STATE.error)
    if jpeg:
        return placeholder_jpeg("RECONECTANDO CÁMARA 3D", "Último frame hace %ds" % int(time.time() - ts))
    return placeholder_jpeg("INICIANDO CÁMARA 3D", "Arrancando Chromium headless (la primera vez puede tardar)...")


# ----------------------------------------------------------------------
#  Worker headless
# ----------------------------------------------------------------------
class CameraWorker(threading.Thread):
    def __init__(self, port):
        super().__init__(daemon=True, name="CameraWorker")
        self.port = port
        self.base = "http://127.0.0.1:%d" % port

    def _wait_server(self, timeout=90):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                urllib.request.urlopen(self.base + "/api/state", timeout=2).read(1)
                return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError("El servidor no responde en %s/api/state" % self.base)

    def _session(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("Falta Playwright: ejecute  python -m pip install playwright  y  python -m playwright install chromium")

        self._wait_server()
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True, args=CHROMIUM_ARGS)
            except Exception as e:
                raise RuntimeError("No se pudo iniciar Chromium (%s). Ejecute: python -m playwright install chromium" % str(e).splitlines()[0])
            try:
                ctx = browser.new_context(viewport={"width": W, "height": H})
                page = ctx.new_page()
                page.on("console", lambda m: STATE.add_page_error("[%s] %s" % (m.type, m.text)) if m.type in ("error", "warning") else None)
                page.on("pageerror", lambda e: STATE.add_page_error("JS: %s" % e))
                page.on("requestfailed", lambda r: STATE.add_page_error("req fallida: %s" % r.url))

                page.goto(self.base + "/viewer3d", wait_until="domcontentloaded", timeout=60000)
                try:
                    page.wait_for_function("window.__viewerReady && window.__viewerReady()", timeout=90000)
                except Exception:
                    detail = "; ".join(STATE.page_errors[-3:]) or "sin errores de consola"
                    raise RuntimeError("viewer3d no inició (%s)" % detail)

                STATE.ready = True
                STATE.error = None
                log.info("Worker listo: capturando %s/viewer3d a %d FPS", self.base, FPS)

                period = 1.0 / FPS
                fails = 0
                n = 0
                while True:
                    t0 = time.time()
                    try:
                        data = page.evaluate("window.getFrame(%s)" % JPEG_QUALITY)
                        STATE.put(base64.b64decode(data.split(",", 1)[1]))
                        fails = 0
                    except Exception as e:
                        fails += 1
                        if fails >= 5:
                            raise RuntimeError("fallo capturando frames: %s" % str(e).splitlines()[0])
                    n += 1
                    if n % 50 == 0:   # watchdog: el viewer debe seguir renderizando
                        age = page.evaluate("Date.now() - (window.__lastFrameTs || 0)")
                        if age > 5000:
                            raise RuntimeError("el viewer dejó de renderizar")
                    dt = time.time() - t0
                    if dt < period:
                        time.sleep(period - dt)
            finally:
                try:
                    browser.close()
                except Exception:
                    pass

    def run(self):
        backoff = 2
        while True:
            try:
                self._session()
            except Exception as e:
                STATE.ready = False
                STATE.error = str(e)
                STATE.restarts += 1
                log.error("Worker caído: %s (reintento en %ds)", e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 15)
            else:
                backoff = 2


# ----------------------------------------------------------------------
#  Three.js local (evita depender de unpkg en cada arranque)
# ----------------------------------------------------------------------
def _ensure_three():
    if os.path.exists(THREE_PATH):
        return True
    try:
        os.makedirs(VENDOR_DIR, exist_ok=True)
        data = urllib.request.urlopen(THREE_URL, timeout=30).read()
        with open(THREE_PATH, "wb") as f:
            f.write(data)
        log.info("three.module.js guardado en %s", THREE_PATH)
        return True
    except Exception as e:
        log.warning("No se pudo descargar three.js (%s); se usará unpkg directo", e)
        return False


# ----------------------------------------------------------------------
#  Integración con Flask
# ----------------------------------------------------------------------
def init_camera(app, port=8080):
    threading.Thread(target=_ensure_three, daemon=True).start()

    @app.route("/video.mjpg")
    def cam_video_mjpg():
        def gen():
            while True:
                jpeg = current_jpeg()
                yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                       + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
                time.sleep(1.0 / FPS)
        return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame",
                        headers={"Cache-Control": "no-store"})

    @app.route("/snapshot.jpg")
    def cam_snapshot():
        return Response(current_jpeg(), mimetype="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.route("/viewer3d")
    def cam_viewer3d():
        return render_template("viewer3d.html")

    @app.route("/vendor/three.module.js")
    def cam_vendor_three():
        if _ensure_three():
            return send_file(THREE_PATH, mimetype="text/javascript")
        return redirect(THREE_URL)

    @app.route("/api/camera/status")
    def cam_status():
        return jsonify(camera_status())

    CameraWorker(port).start()
    log.info("Cámara headless iniciada (esperando al servidor en el puerto %d)", port)
