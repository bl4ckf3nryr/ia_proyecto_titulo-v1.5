import io
import os
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import bcrypt
import cv2
import jwt
import numpy as np
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool  # NUEVO: segmentación piso/pared
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ultralytics import YOLO

from base_de_datos.conexion import SesionLocal, crear_tablas, obtener_sesion
from base_de_datos.auditoria import listar_todas, registrar_accion
from base_de_datos.empresas import (
    actualizar_empresa,
    crear_empresa,
    eliminar_empresa,
    listar_empresas,
    obtener_por_id as obtener_empresa_por_id,
    obtener_por_nombre as obtener_empresa_por_nombre,
)
from base_de_datos.usuarios import (
    actualizar_password,
    actualizar_usuario,
    crear_usuario,
    eliminar_usuario,
    guardar_codigo_reset,
    listar_usuarios,
    listar_usuarios_por_empresa,
    obtener_por_email,
    obtener_por_id,
)
from base_de_datos.camaras import (
    crear_camara,
    listar_por_empresa as listar_camaras_por_empresa,
    listar_por_departamento as listar_camaras_por_departamento,
    listar_por_usuario as listar_camaras_por_usuario,
    obtener_por_id as obtener_camara_por_id,
)
from base_de_datos.departamentos import (
    crear_departamento,
    listar_por_empresa as listar_departamentos_por_empresa,
    obtener_por_id as obtener_departamento_por_id,
)
from deepseek.servicio import modelo_disponible, segmentar_bytes  # NUEVO: segmentación piso/pared
from base_de_datos.modelos import CamaraORM, UsuarioORM  # NUEVO: learning lista todas las cámaras
from deepseek.camara import frame_de_camara  # NUEVO: frame leído por el servidor
from deepseek.volumen import (  # NUEVO: habitación vacía vs con cosas
    analizar_bytes,
    guardar_config,
    guardar_referencia,
    hay_referencia,
    obtener_config,
    ruta_referencia,
)
from deepseek.learning_api import crear_router  # NUEVO: herramientas de entrenamiento

# ============================================================
# Modelo YOLO — carga única al importar el módulo
# ============================================================
modelo_yolo = YOLO("yolov8n.pt")

# ============================================================
# Configuración
# ============================================================
SECRETO_JWT = "cambia-esto-en-produccion"
ALGORITMO = "HS256"
MINUTOS_EXPIRACION = 60
MINUTOS_RESET = 15

ROLES_VALIDOS = {"admin", "supervisor", "usuario", "learning"}  # NUEVO: learning

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Login Simple + Admin")
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)


# ============================================================
# Utilidades de seguridad
# ============================================================
def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verificar_password(password: str, hasheada: str) -> bool:
    return bcrypt.checkpw(password.encode(), hasheada.encode())


def crear_token(usuario_id: int, email: str, rol: str, empresa_id: Optional[int]) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "email": email,
        "rol": rol,
        "empresa_id": empresa_id,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=MINUTOS_EXPIRACION),
    }
    return jwt.encode(payload, SECRETO_JWT, algorithm=ALGORITMO)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRETO_JWT, algorithms=[ALGORITMO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )


def extraer_token(request: Request) -> Optional[str]:
    """Lee el token desde cookie (preferido) o desde header Authorization."""
    token = request.cookies.get("access_token")
    if token:
        return token

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()

    return None


# ============================================================
# Dependencias de autenticación
# ============================================================
def usuario_actual(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Dependency: devuelve el usuario logueado o lanza 401."""
    token = extraer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decodificar_token(token)
    usuario_id = int(payload.get("sub", 0))
    usuario = obtener_por_id(sesion, usuario_id)

    if not usuario or not usuario.esta_activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no válido o inactivo",
        )
    return usuario


def requiere_admin(usuario=Depends(usuario_actual)):
    """Dependency: exige que el usuario sea administrador."""
    if usuario.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return usuario


def requiere_supervisor(usuario=Depends(usuario_actual)):
    """Dependency: exige que el usuario sea supervisor."""
    if usuario.rol != "supervisor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de supervisor",
        )
    return usuario


def requiere_usuario(usuario=Depends(usuario_actual)):
    """Dependency: exige que el usuario tenga rol 'usuario'."""
    if usuario.rol != "usuario":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a usuarios con rol 'usuario'",
        )
    return usuario


def requiere_learning(usuario=Depends(usuario_actual)):
    """Dependency: exige que el usuario sea del rol 'learning' (calibración IA)."""
    if usuario.rol != "learning":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de learning",
        )
    return usuario


def verificar_empresa_del_objeto(objeto, usuario) -> None:
    """
    Auxiliar: verifica que objeto.empresa_id coincida con usuario.empresa_id.
    Lanza 403 si no coincide. Usar antes de cualquier modificación.
    """
    if objeto.empresa_id != usuario.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a recursos de otra empresa",
        )


# ============================================================
# Arranque
# ============================================================
@app.on_event("startup")
def al_arrancar() -> None:
    crear_tablas()
    with SesionLocal() as sesion:
        # Empresa demo (necesaria para usuarios no-admin)
        empresa_demo = obtener_empresa_por_nombre(sesion, "Empresa Demo")
        if not empresa_demo:
            empresa_demo = crear_empresa(sesion, nombre="Empresa Demo")

        # Admin por defecto (sin empresa)
        if not obtener_por_email(sesion, "admin@example.com"):
            crear_usuario(
                sesion,
                nombre="Administrador",
                email="admin@example.com",
                password_hasheada=hashear_password("admin1234"),
                rol="admin",
                empresa_id=None,
            )

        # Supervisor demo
        if not obtener_por_email(sesion, "supervisor@example.com"):
            crear_usuario(
                sesion,
                nombre="Supervisor Demo",
                email="supervisor@example.com",
                password_hasheada=hashear_password("super1234"),
                rol="supervisor",
                empresa_id=empresa_demo.id,
            )

        # Learning (calibra la IA; sin empresa, ve todas las cámaras)
        if not obtener_por_email(sesion, "learning@example.com"):
            crear_usuario(
                sesion,
                nombre="Learning",
                email="learning@example.com",
                password_hasheada=hashear_password("learning1234"),
                rol="learning",
                empresa_id=None,
            )

        # Usuario demo
        if not obtener_por_email(sesion, "demo@example.com"):
            crear_usuario(
                sesion,
                nombre="Usuario Demo",
                email="demo@example.com",
                password_hasheada=hashear_password("demo1234"),
                rol="usuario",
                empresa_id=empresa_demo.id,
            )


# ============================================================
# Vistas HTML
# ============================================================
@app.get("/", response_class=HTMLResponse)
def vista_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/recuperar", response_class=HTMLResponse)
def vista_recuperar(request: Request):
    return templates.TemplateResponse("recuperar.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def vista_dashboard(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """
    - Sin sesión → al login.
    - admin → /admin
    - supervisor → /supervisor
    - usuario → dashboard.html
    """
    token = extraer_token(request)
    if not token:
        return RedirectResponse(url="/", status_code=302)

    try:
        payload = decodificar_token(token)
    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

    usuario_id = int(payload.get("sub", 0))
    usuario = obtener_por_id(sesion, usuario_id)

    if not usuario or not usuario.esta_activo:
        return RedirectResponse(url="/", status_code=302)

    if usuario.rol == "admin":
        return RedirectResponse(url="/admin", status_code=302)

    if usuario.rol == "supervisor":
        return RedirectResponse(url="/supervisor", status_code=302)

    if usuario.rol == "learning":
        return RedirectResponse(url="/learning", status_code=302)

    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
def vista_admin(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """
    - Sin sesión → al login.
    - No admin → al dashboard.
    - Admin → admin.html.
    """
    token = extraer_token(request)
    if not token:
        return RedirectResponse(url="/", status_code=302)

    try:
        payload = decodificar_token(token)
    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

    usuario_id = int(payload.get("sub", 0))
    usuario = obtener_por_id(sesion, usuario_id)

    if not usuario or not usuario.esta_activo:
        return RedirectResponse(url="/", status_code=302)

    if usuario.rol != "admin":
        return RedirectResponse(url="/dashboard", status_code=302)

    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/supervisor", response_class=HTMLResponse)
def vista_supervisor(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """
    - Sin sesión → al login.
    - admin → /admin
    - usuario → /dashboard
    - supervisor → supervisor.html
    """
    token = extraer_token(request)
    if not token:
        return RedirectResponse(url="/", status_code=302)

    try:
        payload = decodificar_token(token)
    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

    usuario_id = int(payload.get("sub", 0))
    usuario = obtener_por_id(sesion, usuario_id)

    if not usuario or not usuario.esta_activo:
        return RedirectResponse(url="/", status_code=302)

    if usuario.rol == "admin":
        return RedirectResponse(url="/admin", status_code=302)

    if usuario.rol != "supervisor":
        return RedirectResponse(url="/dashboard", status_code=302)

    return templates.TemplateResponse("supervisor.html", {"request": request})


@app.get("/learning", response_class=HTMLResponse)
def vista_learning(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """
    - Sin sesión → al login.
    - admin → /admin, supervisor → /supervisor, usuario → /dashboard
    - learning → learning.html
    """
    token = extraer_token(request)
    if not token:
        return RedirectResponse(url="/", status_code=302)

    try:
        payload = decodificar_token(token)
    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

    usuario = obtener_por_id(sesion, int(payload.get("sub", 0)))

    if not usuario or not usuario.esta_activo:
        return RedirectResponse(url="/", status_code=302)

    if usuario.rol == "admin":
        return RedirectResponse(url="/admin", status_code=302)

    if usuario.rol == "supervisor":
        return RedirectResponse(url="/supervisor", status_code=302)

    if usuario.rol != "learning":
        return RedirectResponse(url="/dashboard", status_code=302)

    return templates.TemplateResponse("learning.html", {"request": request})


# ============================================================
# API: Autenticación
# ============================================================
@app.post("/auth/login")
def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    sesion: Session = Depends(obtener_sesion),
):
    usuario = obtener_por_email(sesion, email)

    if not usuario or not verificar_password(password, usuario.password_hasheada):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    if not usuario.esta_activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    token = crear_token(usuario.id, usuario.email, usuario.rol, usuario.empresa_id)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=MINUTOS_EXPIRACION * 60,
        path="/",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario_id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "empresa_id": usuario.empresa_id,
    }


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    return {"mensaje": "Sesión cerrada"}


@app.get("/auth/yo")
def quien_soy(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Devuelve los datos del usuario logueado o 401."""
    token = extraer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Sin sesión")

    payload = decodificar_token(token)
    usuario = obtener_por_id(sesion, int(payload.get("sub", 0)))

    if not usuario or not usuario.esta_activo:
        raise HTTPException(status_code=401, detail="Sesión inválida")

    return {
        "usuario_id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "empresa_id": usuario.empresa_id,
    }


@app.post("/auth/recuperar")
def solicitar_recuperacion(
    email: str = Form(...),
    sesion: Session = Depends(obtener_sesion),
):
    """
    Genera un código de 6 dígitos y lo guarda en el usuario.
    Devuelve el código en la respuesta (flujo simulado, sin email real).
    Si el email no existe responde igualmente con 200 para no revelar
    qué direcciones están registradas.
    """
    usuario = obtener_por_email(sesion, email)

    # Respuesta genérica aunque el usuario no exista (seguridad)
    if not usuario:
        return {"mensaje": "Si el correo existe, recibirás un código", "codigo_simulado": None}

    codigo = str(random.randint(100000, 999999))
    expiracion = datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_RESET)

    # Guardar sin tzinfo para SQLite (naive UTC)
    guardar_codigo_reset(sesion, usuario.id, codigo, expiracion.replace(tzinfo=None))

    return {"mensaje": "Código generado", "codigo_simulado": codigo}


@app.post("/auth/restablecer")
def restablecer_password(
    email: str = Form(...),
    codigo: str = Form(...),
    nueva_password: str = Form(...),
    sesion: Session = Depends(obtener_sesion),
):
    """
    Valida el código y, si es correcto y no expiró, actualiza la contraseña.
    """
    if len(nueva_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres",
        )

    usuario = obtener_por_email(sesion, email)

    if not usuario or not usuario.reset_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado",
        )

    # Comparar código
    if usuario.reset_code != codigo.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado",
        )

    # Verificar expiración (la BD guarda naive UTC)
    ahora = datetime.utcnow()
    if usuario.reset_code_expira is None or ahora > usuario.reset_code_expira:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado",
        )

    actualizar_password(sesion, usuario.id, hashear_password(nueva_password))
    registrar_accion(
        sesion,
        usuario_email=usuario.email,
        accion="RESTABLECER_PASSWORD",
        detalle=f"Contraseña restablecida para '{usuario.email}'",
    )
    return {"mensaje": "Contraseña actualizada correctamente"}


# ============================================================
# API: Administración — Usuarios
# ============================================================
@app.get("/admin/usuarios")
def admin_listar_usuarios(
    empresa_id: Optional[int] = None,
    admin=Depends(requiere_admin),
    sesion: Session = Depends(obtener_sesion),
):
    if empresa_id is not None:
        usuarios = listar_usuarios_por_empresa(sesion, empresa_id)
    else:
        usuarios = listar_usuarios(sesion)

    return [
        {
            "id": u.id,
            "nombre": u.nombre,
            "email": u.email,
            "esta_activo": u.esta_activo,
            "rol": u.rol,
            "empresa_id": u.empresa_id,
        }
        for u in usuarios
    ]


@app.post("/admin/usuarios")
def admin_crear_usuario(
    nombre: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    rol: str = Form("usuario"),
    empresa_id: Optional[int] = Form(None),
    admin=Depends(requiere_admin),
    sesion: Session = Depends(obtener_sesion),
):
    if not nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")

    if len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="La contraseña debe tener al menos 6 caracteres",
        )

    if rol not in ROLES_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Debe ser uno de: {', '.join(ROLES_VALIDOS)}",
        )

    if rol in ("supervisor", "usuario") and empresa_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"El campo empresa_id es obligatorio para el rol '{rol}'",
        )

    if rol in ("admin", "learning"):
        empresa_id = None

    if empresa_id is not None and not obtener_empresa_por_id(sesion, empresa_id):
        raise HTTPException(status_code=400, detail="La empresa especificada no existe")

    if obtener_por_email(sesion, email):
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    usuario = crear_usuario(
        sesion,
        nombre=nombre,
        email=email,
        password_hasheada=hashear_password(password),
        rol=rol,
        empresa_id=empresa_id,
    )
    registrar_accion(
        sesion,
        usuario_email=admin.email,
        accion="CREAR_USUARIO",
        detalle=f"Usuario '{usuario.email}' creado con rol '{usuario.rol}'",
    )
    return {
        "mensaje": "Usuario creado",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "empresa_id": usuario.empresa_id,
        },
    }


@app.put("/admin/usuarios/{usuario_id}")
def admin_actualizar_usuario(
    usuario_id: int,
    nombre: str = Form(...),
    rol: str = Form(...),
    empresa_id: Optional[int] = Form(None),
    esta_activo: bool = Form(True),
    admin=Depends(requiere_admin),
    sesion: Session = Depends(obtener_sesion),
):
    """Actualiza nombre, rol, empresa y estado activo de un usuario."""
    objetivo = obtener_por_id(sesion, usuario_id)
    if not objetivo:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # El admin no puede cambiar su propio rol
    if usuario_id == admin.id and rol != admin.rol:
        raise HTTPException(
            status_code=400,
            detail="No puedes cambiar tu propio rol",
        )

    if rol not in ROLES_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Debe ser uno de: {', '.join(ROLES_VALIDOS)}",
        )

    if rol in ("supervisor", "usuario") and empresa_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"El campo empresa_id es obligatorio para el rol '{rol}'",
        )

    if rol in ("admin", "learning"):
        empresa_id = None

    if empresa_id is not None and not obtener_empresa_por_id(sesion, empresa_id):
        raise HTTPException(status_code=400, detail="La empresa especificada no existe")

    datos = {
        "nombre": nombre,
        "rol": rol,
        "empresa_id": empresa_id,
        "esta_activo": esta_activo,
    }
    usuario_actualizado = actualizar_usuario(sesion, usuario_id, datos)

    registrar_accion(
        sesion,
        usuario_email=admin.email,
        accion="ACTUALIZAR_USUARIO",
        detalle=(
            f"Usuario '{objetivo.email}' (id={usuario_id}) actualizado: "
            f"rol='{rol}', empresa_id={empresa_id}, esta_activo={esta_activo}"
        ),
    )
    return {
        "mensaje": "Usuario actualizado",
        "usuario": {
            "id": usuario_actualizado.id,
            "nombre": usuario_actualizado.nombre,
            "email": usuario_actualizado.email,
            "rol": usuario_actualizado.rol,
            "empresa_id": usuario_actualizado.empresa_id,
            "esta_activo": usuario_actualizado.esta_activo,
        },
    }


@app.delete("/admin/usuarios/{usuario_id}")
def admin_eliminar_usuario(
    usuario_id: int,
    admin=Depends(requiere_admin),
    sesion: Session = Depends(obtener_sesion),
):
    """Elimina un usuario. El admin no puede eliminarse a sí mismo."""
    if usuario_id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="No puedes eliminarte a ti mismo",
        )

    objetivo = obtener_por_id(sesion, usuario_id)
    if not objetivo:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    email_objetivo = objetivo.email
    eliminado = eliminar_usuario(sesion, usuario_id)

    if not eliminado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    registrar_accion(
        sesion,
        usuario_email=admin.email,
        accion="ELIMINAR_USUARIO",
        detalle=f"Usuario '{email_objetivo}' (id={usuario_id}) eliminado",
    )
    return {"mensaje": "Usuario eliminado", "id": usuario_id}


# ============================================================
# API: Administración — Empresas
# ============================================================
@app.get("/admin/empresas")
def admin_listar_empresas(
    admin=Depends(requiere_admin),
    sesion: Session = Depends(obtener_sesion),
):
    empresas = listar_empresas(sesion)
    return [
        {
            "id": e.id,
            "nombre": e.nombre,
            "esta_activa": e.esta_activa,
        }
        for e in empresas
    ]


@app.post("/admin/empresas")
def admin_crear_empresa(
    nombre: str = Form(...),
    admin=Depends(requiere_admin),
    sesion: Session = Depends(obtener_sesion),
):
    if not nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")

    if obtener_empresa_por_nombre(sesion, nombre):
        raise HTTPException(status_code=400, detail="Ya existe una empresa con ese nombre")

    empresa = crear_empresa(sesion, nombre=nombre)
    registrar_accion(
        sesion,
        usuario_email=admin.email,
        accion="CREAR_EMPRESA",
        detalle=f"Empresa '{empresa.nombre}' creada (id={empresa.id})",
    )
    return {
        "mensaje": "Empresa creada",
        "empresa": {
            "id": empresa.id,
            "nombre": empresa.nombre,
            "esta_activa": empresa.esta_activa,
        },
    }


@app.put("/admin/empresas/{empresa_id}")
def admin_actualizar_empresa(
    empresa_id: int,
    nombre: str = Form(...),
    esta_activa: bool = Form(True),
    admin=Depends(requiere_admin),
    sesion: Session = Depends(obtener_sesion),
):
    """Actualiza el nombre y estado activo de una empresa."""
    empresa = obtener_empresa_por_id(sesion, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if not nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")

    # Verificar nombre duplicado (excluyendo la empresa actual)
    existente = obtener_empresa_por_nombre(sesion, nombre)
    if existente and existente.id != empresa_id:
        raise HTTPException(status_code=400, detail="Ya existe una empresa con ese nombre")

    empresa_actualizada = actualizar_empresa(
        sesion,
        empresa_id=empresa_id,
        nombre=nombre,
        esta_activa=esta_activa,
    )
    registrar_accion(
        sesion,
        usuario_email=admin.email,
        accion="ACTUALIZAR_EMPRESA",
        detalle=(
            f"Empresa id={empresa_id} actualizada: "
            f"nombre='{nombre}', esta_activa={esta_activa}"
        ),
    )
    return {
        "mensaje": "Empresa actualizada",
        "empresa": {
            "id": empresa_actualizada.id,
            "nombre": empresa_actualizada.nombre,
            "esta_activa": empresa_actualizada.esta_activa,
        },
    }


@app.delete("/admin/empresas/{empresa_id}")
def admin_eliminar_empresa(
    empresa_id: int,
    admin=Depends(requiere_admin),
    sesion: Session = Depends(obtener_sesion),
):
    """
    Elimina una empresa. Falla con HTTP 400 si tiene usuarios o cámaras asociadas.
    """
    empresa = obtener_empresa_por_id(sesion, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Verificar usuarios asociados
    usuarios_asociados = (
        sesion.query(UsuarioORM)
        .filter(UsuarioORM.empresa_id == empresa_id)
        .count()
    )
    if usuarios_asociados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: la empresa tiene {usuarios_asociados} usuario(s) asociado(s)",
        )

    # Verificar cámaras asociadas
    camaras_asociadas = (
        sesion.query(CamaraORM)
        .filter(CamaraORM.empresa_id == empresa_id)
        .count()
    )
    if camaras_asociadas > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: la empresa tiene {camaras_asociadas} cámara(s) asociada(s)",
        )

    nombre_empresa = empresa.nombre
    eliminada = eliminar_empresa(sesion, empresa_id)

    if not eliminada:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    registrar_accion(
        sesion,
        usuario_email=admin.email,
        accion="ELIMINAR_EMPRESA",
        detalle=f"Empresa '{nombre_empresa}' (id={empresa_id}) eliminada",
    )
    return {"mensaje": "Empresa eliminada", "id": empresa_id}


# ============================================================
# API: Administración — Auditoría
# ============================================================
@app.get("/admin/auditoria/descargar")
def admin_descargar_auditoria(
    admin=Depends(requiere_admin),
    sesion: Session = Depends(obtener_sesion),
):
    """Genera y descarga un reporte de auditoría en texto plano."""
    registros = listar_todas(sesion)

    lineas = [
        "REPORTE DE AUDITORÍA — GESTOR DE BULTOS",
        f"Generado: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"Solicitado por: {admin.email}",
        "=" * 60,
        "",
    ]

    if not registros:
        lineas.append("Sin registros de auditoría.")
    else:
        for r in registros:
            fecha = r.fecha_hora.strftime("%Y-%m-%d %H:%M:%S") if r.fecha_hora else "—"
            lineas.append(f"[{fecha} UTC]")
            lineas.append(f"  Usuario : {r.usuario_email}")
            lineas.append(f"  Acción  : {r.accion}")
            lineas.append(f"  Detalle : {r.detalle}")
            lineas.append("")

    contenido = "\n".join(lineas).encode("utf-8")
    return Response(
        content=contenido,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="reporte_auditoria.txt"',
            "Content-Length": str(len(contenido)),
        },
    )


# ============================================================
# API: Supervisor — Departamentos
# ============================================================
@app.get("/supervisor/departamentos")
def supervisor_listar_departamentos(
    supervisor=Depends(requiere_supervisor),
    sesion: Session = Depends(obtener_sesion),
):
    departamentos = listar_departamentos_por_empresa(sesion, supervisor.empresa_id)
    return [
        {
            "id": d.id,
            "nombre": d.nombre,
            "empresa_id": d.empresa_id,
        }
        for d in departamentos
    ]


@app.post("/supervisor/departamentos")
def supervisor_crear_departamento(
    nombre: str = Form(...),
    supervisor=Depends(requiere_supervisor),
    sesion: Session = Depends(obtener_sesion),
):
    if not nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")

    departamento = crear_departamento(sesion, nombre=nombre, empresa_id=supervisor.empresa_id)
    return {
        "mensaje": "Departamento creado",
        "departamento": {
            "id": departamento.id,
            "nombre": departamento.nombre,
            "empresa_id": departamento.empresa_id,
        },
    }


# ============================================================
# API: Supervisor — Cámaras
# ============================================================
@app.get("/supervisor/camaras")
def supervisor_listar_camaras(
    supervisor=Depends(requiere_supervisor),
    sesion: Session = Depends(obtener_sesion),
):
    """Devuelve SOLO las cámaras creadas por este supervisor."""
    camaras = listar_camaras_por_usuario(sesion, supervisor.id)
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "url_stream": c.url_stream,
            "empresa_id": c.empresa_id,
            "departamento_id": c.departamento_id,
            "usuario_id": c.usuario_id,
            "esta_activa": c.esta_activa,
        }
        for c in camaras
    ]


@app.post("/supervisor/camaras")
def supervisor_crear_camara(
    nombre: str = Form(...),
    url_stream: str = Form(...),
    departamento_id: int = Form(...),
    supervisor=Depends(requiere_supervisor),
    sesion: Session = Depends(obtener_sesion),
):
    if not nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")

    if not url_stream.strip():
        raise HTTPException(status_code=400, detail="La URL del stream es obligatoria")

    departamento = obtener_departamento_por_id(sesion, departamento_id)
    if not departamento:
        raise HTTPException(status_code=400, detail="El departamento no existe")

    verificar_empresa_del_objeto(departamento, supervisor)

    camara = crear_camara(
        sesion,
        nombre=nombre,
        url_stream=url_stream,
        empresa_id=supervisor.empresa_id,
        departamento_id=departamento_id,
        usuario_id=supervisor.id,
    )
    registrar_accion(
        sesion,
        usuario_email=supervisor.email,
        accion="CREAR_CAMARA",
        detalle=f"Cámara '{camara.nombre}' creada (id={camara.id}, depto={departamento_id})",
    )
    return {
        "mensaje": "Cámara creada",
        "camara": {
            "id": camara.id,
            "nombre": camara.nombre,
            "url_stream": camara.url_stream,
            "empresa_id": camara.empresa_id,
            "departamento_id": camara.departamento_id,
            "usuario_id": camara.usuario_id,
            "esta_activa": camara.esta_activa,
        },
    }


@app.delete("/supervisor/camaras/{camara_id}")
def supervisor_eliminar_camara(
    camara_id: int,
    supervisor=Depends(requiere_supervisor),
    sesion: Session = Depends(obtener_sesion),
):
    """Borra una cámara SOLO si pertenece a este supervisor."""
    camara = obtener_camara_por_id(sesion, camara_id)
    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    if camara.usuario_id != supervisor.id:
        raise HTTPException(
            status_code=403,
            detail="No puedes borrar cámaras de otro supervisor",
        )

    sesion.delete(camara)
    sesion.commit()
    return {"mensaje": "Cámara eliminada", "id": camara_id}


# NUEVO ─ Módulo learning: calibración de la IA ─────────────
def _frame_jpg(camara_id: int) -> bytes:
    """Lee un frame directo de la cámara (desde el servidor) y lo da en JPEG."""
    frame = frame_de_camara(camara_id)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("No se pudo codificar el frame")
    return buf.tobytes()


async def _frame_servidor(camara_id: int) -> bytes:
    try:
        return await run_in_threadpool(_frame_jpg, camara_id)
    except (RuntimeError, ValueError) as error:
        # No se devuelve el error original: puede incluir la URL con credenciales
        print(f"[learning] Falló la lectura de la cámara {camara_id}: {error}")
        raise HTTPException(
            status_code=502,
            detail="No se pudo obtener imagen de la cámara. "
                   "Revisa que esté encendida y accesible desde el servidor.",
        )


def _camara_o_404(sesion: Session, camara_id: int):
    camara = obtener_camara_por_id(sesion, camara_id)
    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    return camara


@app.get("/learning/camaras")
def learning_listar_camaras(
    learning=Depends(requiere_learning),
    sesion: Session = Depends(obtener_sesion),
):
    """Todas las cámaras (sin la URL, que puede llevar credenciales)."""
    camaras = sesion.query(CamaraORM).order_by(CamaraORM.id).all()
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "empresa_id": c.empresa_id,
            "esta_activa": c.esta_activa,
            "tiene_referencia": hay_referencia(c.id),
        }
        for c in camaras
    ]


@app.get("/learning/camaras/{camara_id}/frame")
async def learning_frame(
    camara_id: int,
    learning=Depends(requiere_learning),
    sesion: Session = Depends(obtener_sesion),
):
    """Imagen actual de la cámara, leída por el servidor (sirve para RTSP)."""
    _camara_o_404(sesion, camara_id)
    contenido = await _frame_servidor(camara_id)
    return Response(
        content=contenido,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/learning/camaras/{camara_id}/referencia")
def learning_ver_referencia(
    camara_id: int,
    learning=Depends(requiere_learning),
    sesion: Session = Depends(obtener_sesion),
):
    _camara_o_404(sesion, camara_id)
    if not hay_referencia(camara_id):
        raise HTTPException(status_code=404, detail="Aún no hay foto de la habitación vacía")
    return FileResponse(
        str(ruta_referencia(camara_id)),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


@app.post("/learning/camaras/{camara_id}/referencia")
async def learning_guardar_referencia(
    camara_id: int,
    learning=Depends(requiere_learning),
    sesion: Session = Depends(obtener_sesion),
):
    """Toma un frame de la cámara AHORA y lo guarda como habitación vacía."""
    _camara_o_404(sesion, camara_id)
    contenido = await _frame_servidor(camara_id)
    try:
        await run_in_threadpool(guardar_referencia, camara_id, contenido)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return {"mensaje": "Referencia guardada", "camara_id": camara_id}


@app.post("/learning/camaras/{camara_id}/probar")
async def learning_probar(
    camara_id: int,
    umbral_diff: Optional[float] = Form(None),
    area_min_pct: Optional[float] = Form(None),
    learning=Depends(requiere_learning),
    sesion: Session = Depends(obtener_sesion),
):
    """
    Toma un frame ahora y lo compara con la foto vacía. Si se envían umbrales
    se usan solo para esta prueba (no se guardan).
    """
    camara = _camara_o_404(sesion, camara_id)
    if not hay_referencia(camara_id):
        raise HTTPException(
            status_code=409,
            detail="Primero guarda una foto de la habitación vacía",
        )
    contenido = await _frame_servidor(camara_id)
    try:
        resultado = await run_in_threadpool(
            analizar_bytes, camara_id, contenido, umbral_diff, area_min_pct
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except OSError:
        raise HTTPException(
            status_code=503,
            detail="No se pudo cargar el modelo de profundidad (¿hay internet?)",
        )
    return {"camara_id": camara_id, "camara_nombre": camara.nombre, **resultado}


@app.get("/learning/config")
def learning_ver_config(learning=Depends(requiere_learning)):
    return obtener_config()


@app.put("/learning/config")
def learning_guardar_config(
    umbral_diff: float = Form(...),
    area_min_pct: float = Form(...),
    learning=Depends(requiere_learning),
):
    """Guarda la sensibilidad que usará toda la aplicación."""
    try:
        return guardar_config(umbral_diff, area_min_pct)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


# NUEVO ─ Herramientas de entrenamiento (deepseek/learning_api.py):
# estado de cámaras, fotos de ejemplo, entrenar, estado guardado y respaldo.
app.include_router(crear_router(requiere_learning))
# ───────────────────────────────────────────────────────────


# ============================================================
# API: Usuario normal
# ============================================================
@app.get("/usuario/informes")
def usuario_informes(
    usuario=Depends(requiere_usuario),
    sesion: Session = Depends(obtener_sesion),
):
    """Devuelve las cámaras activas de la empresa del usuario."""
    camaras = listar_camaras_por_empresa(sesion, usuario.empresa_id)
    return {
        "empresa_id": usuario.empresa_id,
        "camaras": [
            {
                "id": c.id,
                "nombre": c.nombre,
                "url_stream": c.url_stream,
                "departamento_id": c.departamento_id,
                "esta_activa": c.esta_activa,
            }
            for c in camaras
            if c.esta_activa
        ],
    }


# ============================================================
# Healthcheck
# ============================================================
@app.get("/health")
def health():
    return {"status": "ok"}
