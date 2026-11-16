"""Herramientas de entrenamiento/calibracion para el rol learning.

Se monta desde main.py (ver instrucciones). No toca los endpoints existentes.
Datos: deepseek/entrenamiento/cam<ID>/{vacia,con_cosas}/*.jpg
Estado: deepseek/estado_learning.json
"""
import asyncio
import io
import json
import re
import time
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from base_de_datos.conexion import obtener_sesion
from base_de_datos.modelos import CamaraORM
from deepseek.camara import frame_de_camara
from deepseek.volumen import analizar_bytes, hay_referencia, guardar_referencia, obtener_config, ruta_referencia

BASE = Path(__file__).resolve().parent
DATOS = BASE / "entrenamiento"
ESTADO = BASE / "estado_learning.json"
ETIQUETAS = ("vacia", "con_cosas")


def _carpeta(cid: int, et: str) -> Path:
    if et not in ETIQUETAS:
        raise HTTPException(400, "Etiqueta invalida (vacia o con_cosas)")
    return DATOS / f"cam{int(cid)}" / et


def _nombre_ok(n: str) -> str:
    if not re.fullmatch(r"[\w\-.]+\.jpg", n) or ".." in n:
        raise HTTPException(400, "Nombre invalido")
    return n


def _a_jpg(contenido: bytes) -> bytes:
    img = cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Imagen invalida")
    h, w = img.shape[:2]
    if w > 1280:
        img = cv2.resize(img, (1280, int(h * 1280 / w)))
    return cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tobytes()


def _frame(cid: int) -> bytes:
    try:
        ok, buf = cv2.imencode(".jpg", frame_de_camara(cid), [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            raise RuntimeError("No se pudo codificar el frame")
        return buf.tobytes()
    except Exception as e:  # el detalle (puede traer la URL) solo va a la consola
        print(f"[learning] Fallo la lectura de la camara {cid}: {e}")
        raise HTTPException(502, "No se pudo obtener imagen de la camara")


def _ping(cid: int) -> bool:
    try:
        _frame(cid)
        return True
    except HTTPException:
        return False


def _guardar(cid: int, et: str, jpg: bytes, prefijo: str = "up") -> str:
    c = _carpeta(cid, et)
    c.mkdir(parents=True, exist_ok=True)
    nombre = f"{prefijo}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}.jpg"
    (c / nombre).write_bytes(jpg)
    return nombre


def _analizar(cid: int, jpg: bytes, u=None, a=None) -> dict:
    try:
        return analizar_bytes(cid, jpg, umbral_diff=u, area_min_pct=a)
    except FileNotFoundError:
        raise HTTPException(409, "Primero guarda una foto de la habitacion vacia")
    except OSError:
        raise HTTPException(503, "No se pudo cargar el modelo de profundidad (revisa internet y transformers)")
    except ValueError as e:
        raise HTTPException(400, str(e))


def _entrenar(cids: List[int], modo: str, u0, a0) -> dict:
    cfg = obtener_config()
    buscar = modo == "buscar"
    umbrales = [0.08, 0.12, 0.16, 0.22, 0.30] if buscar else [u0 or cfg["umbral_diff"]]
    ej = [(cid, et, f) for cid in cids if hay_referencia(cid) for et in ETIQUETAS
          for f in sorted(_carpeta(cid, et).glob("*.jpg"))]
    ej = ej[-40:]  # tope para que no tarde demasiado
    if not ej or (buscar and len({e[1] for e in ej}) < 2):
        raise HTTPException(400, "Faltan ejemplos: sube fotos 'vacia' y 'con cosas' y guarda la foto vacia de la camara")
    pcts = [{u: _analizar(c, f.read_bytes(), u, 1.0)["porcentaje"] for u in umbrales} for c, _, f in ej]

    def evaluar(u, a):
        v = [(p[u] >= a, e[1] == "con_cosas") for p, e in zip(pcts, ej)]
        return v, sum(x == y for x, y in v) / len(v)

    mejor, por_u = None, {}
    for u in umbrales:
        vals = sorted({p[u] for p in pcts})
        cands = {a0 or cfg["area_min_pct"]} if not buscar else {0.1, *vals, *[(x + y) / 2 for x, y in zip(vals, vals[1:])]}
        for a in cands:
            a = round(min(max(a, 0.1), 50), 1)
            acc = evaluar(u, a)[1]
            clave = (acc, min(abs(p[u] - a) for p in pcts))  # precision y luego margen
            if u not in por_u or clave > por_u[u][0]:
                por_u[u] = (clave, a)
            if mejor is None or clave > mejor[0]:
                mejor = (clave, u, a)
    _, u, a = mejor
    v, acc = evaluar(u, a)
    return {
        "modo": modo, "umbral_diff": u, "area_min_pct": a, "precision": round(acc * 100, 1), "total": len(v),
        "matriz": {"tp": sum(x and y for x, y in v), "tn": sum(not x and not y for x, y in v),
                   "fp": sum(x and not y for x, y in v), "fn": sum(not x and y for x, y in v)},
        "tabla": [{"umbral": k, "area": z[1], "precision": round(z[0][0] * 100, 1)} for k, z in por_u.items()] if buscar else [],
        "detalle": [{"camara_id": e[0], "etiqueta": e[1], "nombre": e[2].name, "porcentaje": p[u], "acierto": ok == real}
                    for e, p, (ok, real) in zip(ej, pcts, v)],
    }


def crear_router(requiere_learning):
    r = APIRouter(prefix="/learning", dependencies=[Depends(requiere_learning)])

    def cam_o_404(sesion, cid):
        if not sesion.get(CamaraORM, cid):
            raise HTTPException(404, "Camara no encontrada")

    # ---- Camaras: TODAS las registradas, con estado de conexion y conteo de ejemplos
    @r.get("/estado-camaras")
    async def estado_camaras(verificar: bool = False, sesion=Depends(obtener_sesion)):
        cams = sesion.query(CamaraORM).order_by(CamaraORM.id).all()
        vivas = await asyncio.gather(*[run_in_threadpool(_ping, c.id) for c in cams]) if verificar else [None] * len(cams)
        return [{"id": c.id, "nombre": c.nombre, "empresa_id": c.empresa_id, "esta_activa": c.esta_activa,
                 "tiene_referencia": hay_referencia(c.id), "online": v,
                 "ejemplos": {e: len(list(_carpeta(c.id, e).glob("*.jpg"))) for e in ETIQUETAS}}
                for c, v in zip(cams, vivas)]

    # ---- Ejemplos
    @r.get("/ejemplos")
    def listar(camara_id: int):
        return {e: sorted((p.name for p in _carpeta(camara_id, e).glob("*.jpg")), reverse=True) for e in ETIQUETAS}

    @r.post("/ejemplos")
    async def subir(camara_id: int = Form(...), etiqueta: str = Form(...),
                    archivos: List[UploadFile] = File(...), sesion=Depends(obtener_sesion)):
        cam_o_404(sesion, camara_id)
        n = malas = 0
        for f in archivos:
            try:
                _guardar(camara_id, etiqueta, _a_jpg(await f.read()))
                n += 1
            except ValueError:
                malas += 1
        return {"guardadas": n, "invalidas": malas}

    @r.post("/camaras/{cid}/ejemplos/capturar")
    async def capturar(cid: int, etiqueta: str = Form(...), cantidad: int = Form(1),
                       pausa: float = Form(2.0), sesion=Depends(obtener_sesion)):
        cam_o_404(sesion, cid)
        cantidad = max(1, min(cantidad, 10))
        for i in range(cantidad):
            _guardar(cid, etiqueta, await run_in_threadpool(_frame, cid), "cam")
            if i < cantidad - 1:
                await asyncio.sleep(max(0.5, min(pausa, 30)))
        return {"guardadas": cantidad}

    @r.get("/ejemplos/{cid}/{et}/{nombre}")
    def ver(cid: int, et: str, nombre: str):
        p = _carpeta(cid, et) / _nombre_ok(nombre)
        if not p.exists():
            raise HTTPException(404, "No existe")
        return Response(p.read_bytes(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @r.delete("/ejemplos/{cid}/{et}/{nombre}")
    def borrar(cid: int, et: str, nombre: str):
        p = _carpeta(cid, et) / _nombre_ok(nombre)
        p.unlink(missing_ok=True)
        return {"mensaje": "Ejemplo borrado"}

    @r.post("/ejemplos/{cid}/vacia/{nombre}/como-vacia")
    def como_vacia(cid: int, nombre: str):
        p = _carpeta(cid, "vacia") / _nombre_ok(nombre)
        if not p.exists():
            raise HTTPException(404, "No existe")
        try:
            guardar_referencia(cid, p.read_bytes())
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"mensaje": "Referencia guardada", "camara_id": cid}

    # ---- Probar una foto (subida o un ejemplo guardado) contra la foto vacia
    @r.post("/camaras/{cid}/probar-foto")
    async def probar_foto(cid: int, archivo: Optional[UploadFile] = File(None), etiqueta: Optional[str] = Form(None),
                          nombre: Optional[str] = Form(None), umbral_diff: Optional[float] = Form(None),
                          area_min_pct: Optional[float] = Form(None), sesion=Depends(obtener_sesion)):
        cam_o_404(sesion, cid)
        if archivo is not None:
            try:
                jpg = _a_jpg(await archivo.read())
            except ValueError as e:
                raise HTTPException(400, str(e))
        elif etiqueta and nombre:
            jpg = (_carpeta(cid, etiqueta) / _nombre_ok(nombre)).read_bytes()
        else:
            raise HTTPException(400, "Envia una foto o un ejemplo")
        return {"camara_id": cid, **await run_in_threadpool(_analizar, cid, jpg, umbral_diff, area_min_pct)}

    # ---- Entrenar: evaluar con los valores actuales o buscar los mejores con los ejemplos
    @r.post("/entrenar")
    async def entrenar(modo: str = Form("evaluar"), camara_id: Optional[int] = Form(None),
                       umbral_diff: Optional[float] = Form(None), area_min_pct: Optional[float] = Form(None),
                       sesion=Depends(obtener_sesion)):
        cids = [camara_id] if camara_id else [c.id for c in sesion.query(CamaraORM).all()]
        return await run_in_threadpool(_entrenar, cids, modo, umbral_diff, area_min_pct)

    # ---- Estado guardado en disco y respaldo
    @r.get("/estado")
    def leer_estado():
        try:
            return json.loads(ESTADO.read_text("utf-8"))
        except Exception:
            return {}

    @r.put("/estado")
    def guardar_estado(datos: str = Form(...)):
        try:
            d = json.loads(datos)
        except ValueError:
            raise HTTPException(400, "JSON invalido")
        if not isinstance(d, dict) or len(datos) > 200_000:
            raise HTTPException(400, "Estado invalido")
        d["guardado"] = time.strftime("%Y-%m-%d %H:%M:%S")
        ESTADO.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
        return d

    @r.get("/exportar")
    def exportar():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for base in (DATOS, ruta_referencia(0).parent):
                for p in base.rglob("*"):
                    if p.is_file():
                        z.write(p, p.relative_to(BASE).as_posix())
            for p in (BASE / "config_volumen.json", ESTADO):
                if p.exists():
                    z.write(p, p.name)
        return Response(buf.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": 'attachment; filename="learning_respaldo.zip"'})

    return r
