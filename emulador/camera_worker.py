"""
camera_worker.py
Worker que abre un Chromium headless con la escena 3D, la mantiene viva
y captura frames a 10 FPS sin depender de que el usuario tenga la interfaz
abierta. Publica los frames en un buffer compartido.
"""

import io
import time
import threading
import traceback

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except Exception:
    PLAYWRIGHT_OK = False


class CameraWorker:
    def __init__(self, target_url="http://127.0.0.1:8080/viewer3d", fps=10):
        self.target_url = target_url
        self.fps = fps
        self.interval = 1.0 / fps
        self._latest = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._ready = threading.Event()
        self._error = None

    def _set_frame(self, jpeg_bytes):
        with self._lock:
            self._latest = jpeg_bytes

    def get_frame(self):
        with self._lock:
            return self._latest

    def is_ready(self):
        return self._ready.is_set()

    def error(self):
        return self._error

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="CameraWorker")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self):
        if not PLAYWRIGHT_OK:
            self._error = "playwright no está instalado"
            return
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--use-gl=swiftshader",
                        "--enable-webgl",
                        "--ignore-gpu-blocklist",
                    ],
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    device_scale_factor=1,
                )
                page = context.new_page()

                # Esperar a que la escena 3D esté lista
                page.goto(self.target_url, wait_until="networkidle", timeout=30000)
                # Esperar que el canvas tenga contenido
                page.wait_for_timeout(2000)
                self._ready.set()

                print(f"[camera_worker] Navegador headless listo → {self.target_url}")

                while not self._stop.is_set():
                    try:
                        # Capturar el canvas de la cámara 3D directamente
                        jpeg = page.evaluate("""() => {
                            const c = document.getElementById('camera-canvas');
                            if (!c) return null;
                            return c.toDataURL('image/jpeg', 0.82).split(',')[1];
                        }""")
                        if jpeg:
                            import base64
                            self._set_frame(base64.b64decode(jpeg))
                    except Exception as e:
                        print(f"[camera_worker] Error capturando frame: {e}")

                    time.sleep(self.interval)

        except Exception as e:
            self._error = f"{type(e).__name__}: {e}"
            print(f"[camera_worker] ERROR FATAL: {self._error}")
            traceback.print_exc()
        finally:
            try:
                browser.close()
            except Exception:
                pass