"""
app.py
Servidor Flask del Simulador de Bodega 3D.
Incluye:
  - Interfaz 3D (templates/index.html)
  - Pagina de camara (templates/camera.html)
  - API JSON completa (config, pallets, metricas)
  - Camara virtual 3D PERMANENTE (headless) via camera_headless.py:
      /video.mjpg, /snapshot.jpg, /viewer3d, /api/camera/status
"""

import os
import sys
import socket
import threading
import traceback

# ============================================================
#  Forzar que ESTA carpeta esté en sys.path (rutas con espacios)
# ============================================================
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:
    os.chdir(_HERE)
except Exception:
    pass

# ============================================================
#  Log duplicado (consola + archivo)
# ============================================================
LOG_PATH = os.path.join(_HERE, "_servidor.log")


class Tee:
    def __init__(self, original, logfile):
        self.original = original
        self.logfile = logfile

    def write(self, msg):
        try:
            self.original.write(msg)
        except Exception:
            pass
        try:
            self.logfile.write(msg)
            self.logfile.flush()
        except Exception:
            pass

    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass
        try:
            self.logfile.flush()
        except Exception:
            pass


try:
    _log_fp = open(LOG_PATH, "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, _log_fp)
    sys.stderr = Tee(sys.__stderr__, _log_fp)
except Exception:
    _log_fp = None


def _p(*a, **k):
    try:
        print(*a, **k)
    except Exception:
        pass


# ============================================================
#  Diagnóstico
# ============================================================
_p("=" * 68)
_p(" SIMULADOR DE BODEGA 3D - ARRANCANDO")
_p("=" * 68)
_p(f" Python:     {sys.version.split()[0]}")
_p(f" Ejecutable: {sys.executable}")
_p(f" Carpeta:    {_HERE}")
_p(f" CWD:        {os.getcwd()}")
_p("")

_p("[1/6] Importando Flask ...")
try:
    from flask import Flask, render_template, request, jsonify, abort
    _p("      OK")
except Exception:
    _p("      [ERROR] Flask no disponible:")
    traceback.print_exc()
    input("ENTER para salir...")
    sys.exit(1)

_p("[2/6] Importando state ...")
try:
    from state import STATE, PRODUCT_TYPES
    _p("      OK")
except Exception:
    _p("      [ERROR] state.py no importable:")
    traceback.print_exc()
    input("ENTER para salir...")
    sys.exit(1)

_p("[3/6] Importando camera_headless ...")
try:
    import camera_headless
    _p("      OK")
except Exception:
    _p("      [ERROR] camera_headless.py no importable:")
    traceback.print_exc()
    _p(' Reinstale Pillow: ".venv\\Scripts\\python.exe" -m pip install --force-reinstall Pillow')
    input("ENTER para salir...")
    sys.exit(1)

_p("[4/6] Verificando Playwright ...")
try:
    import playwright  # noqa: F401
    _p("      OK")
except Exception:
    _p("      [AVISO] Playwright no esta instalado: la camara mostrara SIN SEÑAL.")
    _p('      Ejecute: ".venv\\Scripts\\python.exe" -m pip install playwright')
    _p('               ".venv\\Scripts\\python.exe" -m playwright install chromium')

_p("[5/6] Creando aplicación Flask ...")
try:
    app = Flask(__name__, template_folder=os.path.join(_HERE, "templates"))
    _p("      OK")
except Exception:
    _p("      [ERROR] No se pudo crear Flask app:")
    traceback.print_exc()
    input("ENTER para salir...")
    sys.exit(1)

PORT = 8080


# ============================================================
#  Utilidades
# ============================================================
def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


SERVER_IP = _local_ip()


def _json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Se esperaba un cuerpo JSON.")
    return data


# ============================================================
#  Cámara virtual 3D permanente (headless)
#  Registra: /video.mjpg  /snapshot.jpg  /viewer3d
#            /vendor/three.module.js  /api/camera/status
#  y arranca el worker (Chromium invisible) en un hilo daemon.
# ============================================================
camera_headless.init_camera(app, port=PORT)


# ============================================================
#  Rutas de interfaz
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/camera")
def camera_page():
    return render_template("camera.html", camera_id="CAM-TECHO-01-3D")


# ============================================================
#  API — Estado y control de capacidad
# ============================================================
@app.get("/api/state")
def api_state():
    snap = STATE.snapshot()
    cam = camera_headless.camera_status()
    snap["server_ip"] = SERVER_IP
    snap["worker_ready"] = cam["worker_ready"]
    snap["worker_error"] = cam["worker_error"]
    snap["camera_frame_age"] = cam["last_frame_age_s"] if cam["last_frame_age_s"] is not None else -1.0
    snap["camera_active"] = cam["worker_ready"]
    return jsonify(snap)


@app.post("/api/config")
def api_config():
    """
    Actualiza dimensiones (ancho, fondo, niveles) y umbral mínimo.
    Al cambiar dimensiones se reinicia la distribución.
    """
    body = _json_body()
    try:
        width = int(body.get("width", STATE.width))
        depth = int(body.get("depth", STATE.depth))
        levels = int(body.get("levels", STATE.levels))
    except (TypeError, ValueError):
        return jsonify(ok=False, message="Dimensiones invalidas."), 400

    threshold = body.get("min_threshold_pct", None)
    if threshold is not None:
        try:
            threshold = float(threshold)
        except (TypeError, ValueError):
            return jsonify(ok=False, message="Umbral invalido."), 400

    ok, msg = STATE.configure(width, depth, levels, threshold)
    return jsonify(ok=ok, message=msg, state=STATE.snapshot()), (200 if ok else 400)


@app.post("/api/slot")
def api_slot():
    body = _json_body()
    action = body.get("action")

    if action == "add":
        try:
            x = int(body["x"]); y = int(body["y"]); level = int(body["level"])
        except (KeyError, TypeError, ValueError):
            return jsonify(ok=False, message="Coordenadas invalidas."), 400
        product = body.get("product", "leche")
        ok, msg = STATE.add_pallet(x, y, level, product)

    elif action == "remove":
        try:
            x = int(body["x"]); y = int(body["y"]); level = int(body["level"])
        except (KeyError, TypeError, ValueError):
            return jsonify(ok=False, message="Coordenadas invalidas."), 400
        ok, msg = STATE.remove_pallet(x, y, level)

    elif action == "move":
        try:
            src = (int(body["src"]["x"]), int(body["src"]["y"]), int(body["src"]["level"]))
            dst = (int(body["dst"]["x"]), int(body["dst"]["y"]), int(body["dst"]["level"]))
        except (KeyError, TypeError, ValueError):
            return jsonify(ok=False, message="Coordenadas invalidas."), 400
        ok, msg = STATE.move_pallet(src, dst)

    else:
        return jsonify(ok=False, message=f"Accion desconocida: {action}"), 400

    return jsonify(ok=ok, message=msg, state=STATE.snapshot()), (200 if ok else 400)


@app.post("/api/clear")
def api_clear():
    ok, msg = STATE.clear()
    return jsonify(ok=ok, message=msg, state=STATE.snapshot()), (200 if ok else 400)


# ============================================================
#  Puerto libre
# ============================================================
def _port_is_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", port))
        s.close()
        return True
    except OSError:
        s.close()
        return False


# ============================================================
#  Main
# ============================================================
if __name__ == "__main__":
    port = PORT
    ip = SERVER_IP

    _p(f"[6/6] Verificando puerto {port} ...")
    if not _port_is_free(port):
        _p(f"      [ERROR] El puerto {port} esta OCUPADO.")
        _p(f'      for /f "tokens=5" %P in (\'netstat -ano ^| findstr ":{port}" ^| findstr "LISTENING"\') do taskkill /F /PID %P')
        input("ENTER para salir...")
        sys.exit(1)
    _p("      OK: puerto libre")
    _p("")

    _p("=" * 68)
    _p(" SERVIDOR ACTIVO")
    _p("=" * 68)
    _p(f" Interfaz   : http://127.0.0.1:{port}/")
    _p(f" Camara     : http://127.0.0.1:{port}/camera")
    _p(f" Flujo MJPEG: http://127.0.0.1:{port}/video.mjpg")
    _p(f" Snapshot   : http://127.0.0.1:{port}/snapshot.jpg")
    _p(f" Diagnostico: http://127.0.0.1:{port}/api/camera/status")
    _p("-" * 68)
    _p(f" Desde otra PC: http://{ip}:{port}/video.mjpg")
    _p("-" * 68)
    _p(" La camara 3D corre en el servidor (Chromium headless).")
    _p(" Detener: CTRL+C")
    _p("=" * 68)
    _p("")

    try:
        app.run(host="0.0.0.0", port=port, threaded=True,
                debug=False, use_reloader=False)
    except KeyboardInterrupt:
        _p("\nDetenido por CTRL+C.")
    except Exception:
        _p("\n[ERROR FATAL]")
        traceback.print_exc()
        input("ENTER para salir...")
        sys.exit(1)
    finally:
        try:
            if _log_fp:
                _log_fp.close()
        except Exception:
            pass