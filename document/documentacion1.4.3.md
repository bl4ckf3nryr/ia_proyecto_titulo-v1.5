================================================================================
     LOGIN CON PANEL DE ADMINISTRACIÓN, SUPERVISIÓN Y CALIBRACIÓN DE IA
                          DOCUMENTACIÓN v1.4.3
================================================================================
Proyecto:   Sistema de login con roles, aislamiento por empresa, visualización
            de cámaras en directo, recuperación de contraseña simulada,
            detección de "habitación vacía / con cosas" mediante un modelo
            preentrenado de profundidad, herramientas de entrenamiento del rol
            learning, y sistema de auditoría y reportes de actividad.
Versión:    1.4.3  (base: 1.4.2)
Fecha:      Noviembre 2026
Stack:      Python 3.12 · FastAPI · SQLAlchemy · bcrypt · PyJWT · Jinja2
            Ultralytics (YOLO) · OpenCV · NumPy · Pillow · transformers
Frontend:   HTML + CSS + JS puro (sin frameworks) + hls.js (solo HLS)
Base datos: SQLite (login.db)
Seguridad:  JWT en cookie httpOnly + validación en servidor por rol
Modelos IA: Depth Anything V2 Small (profundidad, preentrenado, en uso)
            YOLOv8n yolov8n.pt (se carga al arrancar, YA NO se usa en la web)
            YOLOv8n-seg piso/pared (herramienta de consola, sin modelo
            entrenado todavía)
Generado:   Claude (Anthropic)
================================================================================


================================================================================
ÍNDICE
================================================================================
  1.  Descripción general y resumen ejecutivo
  2.  Estructura del proyecto
  3.  Instalación
  4.  Dependencias (requirements.txt)
  5.  Capa de base de datos (base_de_datos/)
  6.  Aplicación principal (main.py)
  7.  Flujo de autenticación
  8.  Templates (templates/)
  9.  Estilos (static/style.css)
  10. JavaScript (static/)
  11. Tabla completa de rutas
  12. Seguridad por capas
  13. Reglas para no romper el código
  14. Cómo agregar cosas nuevas sin romper nada
  15. Errores comunes y soluciones
  16. Pruebas de funcionamiento
  17. Checklist antes de subir a producción
  18. Historial de versiones
  19. Glosario


================================================================================
1. DESCRIPCIÓN GENERAL Y RESUMEN EJECUTIVO
================================================================================

Aplicación web con múltiples tipos de usuario y roles diferenciados:

  - admin      → panel de gestión de usuarios, empresas y auditoría (/admin)
  - supervisor → gestión de departamentos y cámaras de su empresa (/supervisor)
  - usuario    → dashboard con cámaras activas de su empresa (/dashboard)
  - learning   → calibración y entrenamiento de la IA (/learning)

Características del sistema base:

  - Backend en FastAPI (Python 3.12)
  - Base de datos SQLite mediante SQLAlchemy 2.x
  - Contraseñas hasheadas con bcrypt
  - Autenticación basada en tokens JWT guardados en cookie httpOnly
  - Redirección automática según el rol tras el login
  - Control de acceso validado en el SERVIDOR (no solo en JS)
  - Un único archivo CSS global (static/style.css)

--------------------------------------------------------------------------------
1.1 Novedades v1.4.3 — Sistema de Auditoría y Reportes
--------------------------------------------------------------------------------

Esta versión incorpora un sistema de auditoría que registra automáticamente
las acciones críticas realizadas por el administrador y permite descargar un
reporte completo de actividad en formato .txt.

Acciones que quedan registradas en la BD:
  - Creación de un usuario          (POST /admin/usuarios)
  - Creación de una empresa         (POST /admin/empresas)
  - Creación de una cámara          (POST /supervisor/camaras)
  - Restablecimiento de contraseña  (POST /auth/restablecer)

Cada registro almacena: email del actor, descripción de la acción, detalle
adicional (p. ej. nombre del recurso creado) y fecha/hora exacta.

El administrador puede descargar el reporte completo en cualquier momento
desde el botón "📄 Descargar Reporte de Actividad" en el footer del panel
/admin, que llama al endpoint GET /admin/auditoria/descargar.

No fue necesario borrar ni recrear login.db: la tabla auditoria se crea de
forma aditiva al arrancar sin afectar los datos existentes.

--------------------------------------------------------------------------------
1.2 Novedades v1.4.2 — Herramientas de entrenamiento del rol learning
--------------------------------------------------------------------------------

  - deepseek/learning_api.py: router con herramientas de entrenamiento
    (gestión de ejemplos, evaluación de aciertos, búsqueda de mejores valores
    de sensibilidad, estado guardado en disco y exportación a .zip).
  - templates/learning.html y static/learning.js reescritos: galería de
    ejemplos con subida y captura desde cámara, secciones de prueba,
    entrenamiento y respaldo.
  - main.py: import + include_router de learning_api.

--------------------------------------------------------------------------------
1.3 Novedades v1.4.1 — Rol learning y detección de habitación vacía
--------------------------------------------------------------------------------

  - Rol "learning", usuario learning@example.com y página /learning.
  - deepseek/volumen.py: detección de habitación vacía / con cosas con
    Depth Anything V2 Small (preentrenado). No requiere entrenar clases.
  - Endpoints /learning/* (cámaras, frame, referencia, probar, config).
  - Lectura de frames por el servidor (OpenCV, RTSP por TCP).
  - Sensibilidad global editable (config_volumen.json).
  - Supervisor reducido a solo visualización (sin /detectar ni /segmentar).

--------------------------------------------------------------------------------
1.4 Novedades v1.4 — Recuperación de contraseña
--------------------------------------------------------------------------------

  - Flujo completo de recuperación de contraseña simulada sin SMTP.
  - POST /auth/recuperar genera un código de 6 dígitos (expira 15 min)
    que se devuelve en la respuesta JSON para mostrarse en pantalla.
  - POST /auth/restablecer valida email + código + nueva clave.
  - Prevención de enumeración de usuarios (respuesta genérica si el email
    no existe).
  - Columnas reset_code y reset_code_expira en la tabla usuarios.

Alcance actual del sistema:
  - Login de usuarios existentes con recuperación de contraseña simulada.
  - Panel admin: gestión de usuarios, empresas y descarga de auditoría.
  - Panel supervisor: gestión de departamentos y cámaras.
  - Visualización de cámaras en modal (HLS + MJPEG).
  - Rol learning: calibración de la IA con Depth Anything V2 Small.
  - Herramientas de entrenamiento: subida de ejemplos, evaluación, búsqueda
    de mejores valores de sensibilidad y exportación de respaldo.

Fuera de alcance (para futuras versiones):
  - Envío real de correos electrónicos (SMTP).
  - Edición/desactivación de usuarios desde el panel.
  - Monitor automático con análisis periódico de cámaras.
  - Gráfico en el dashboard del usuario con historial de detecciones.
  - Paginación en listados.
  - Tests automatizados.


================================================================================
2. ESTRUCTURA DEL PROYECTO
================================================================================

ia_proyecto_titulo v1.4/                      (raíz del proyecto)
|
+-- base_de_datos/                            Capa de datos (SQLAlchemy)
|   +-- __init__.py
|   +-- conexion.py                           Motor, sesión, crear_tablas
|   +-- modelos.py                            ORM: usuarios, empresas,
|   |                                         departamentos, camaras,
|   |                                         auditoria  [NUEVO v1.4.3]
|   +-- usuarios.py                           CRUD de usuarios
|   +-- empresas.py                           CRUD de empresas
|   +-- departamentos.py                      CRUD de departamentos
|   +-- camaras.py                            CRUD de cámaras
|   +-- auditoria.py                          Registro y listado de auditoría
|                                             [NUEVO v1.4.3]
|
+-- deepseek/                                 Módulo de IA
|   +-- __init__.py
|   +-- volumen.py                            Detección vacía/con cosas
|   +-- learning_api.py                       Router de herramientas de
|   |                                         entrenamiento
|   +-- camara.py                             Lectura de frames por servidor
|   +-- capturar.py                           Captura de frames (consola)
|   +-- train.py                              Entrenamiento YOLO-seg (consola)
|   +-- predict.py                            Inferencia piso/pared (consola)
|   +-- servicio.py                           Puente piso/pared (sin uso activo)
|   +-- data.yaml                             Dataset piso/pared
|   +-- config_volumen.json                   [GENERADO] sensibilidad global
|   +-- estado_learning.json                  [GENERADO] estado de /learning
|   +-- entrenamiento/                        [GENERADA] ejemplos de calibración
|   |   +-- cam<ID>/vacia/*.jpg
|   |   +-- cam<ID>/con_cosas/*.jpg
|   +-- referencias/                          [GENERADA] fotos habitación vacía
|   |   +-- cam<ID>.jpg
|   +-- dataset/                              Dataset piso/pared
|
+-- templates/                                HTML (Jinja2)
|   +-- login.html
|   +-- recuperar.html
|   +-- dashboard.html                        (rol usuario)
|   +-- admin.html
|   +-- supervisor.html
|   +-- learning.html
|
+-- static/
|   +-- style.css                             ÚNICO CSS GLOBAL
|   +-- login.js
|   +-- dashboard.js
|   +-- admin.js
|   +-- supervisor.js
|   +-- learning.js
|
+-- main.py                                   App FastAPI, rutas y utilidades
+-- requirements.txt
+-- iniciar.bat
+-- login.db                                  [GENERADO] SQLite


Notas importantes sobre nombres:

  - "base_de_datos" SIEMPRE en minúsculas (Python es case-sensitive).
  - En Windows, renombrar una carpeta solo cambiando mayúsculas requiere
    hacerlo en dos pasos:
        ren Base_de_datos base_de_datos_temp
        ren base_de_datos_temp base_de_datos


================================================================================
3. INSTALACIÓN
================================================================================

Requisitos previos:
  - Python 3.11, 3.12 o 3.13 (NO 3.14+, por compatibilidad con bcrypt y
    pydantic-core que aún no tienen wheels compiladas para esa versión)
  - pip actualizado
  - Conexión a internet (para descargar dependencias y, la primera vez que
    se usa el modelo de profundidad, ~100 MB desde Hugging Face)

OPCIÓN A — Inicio automático (Windows):

    Doble clic en iniciar.bat
    Detecta Python, crea el venv, instala dependencias y levanta uvicorn
    con --reload en el puerto 8000.

    IMPORTANTE: si ya existía el venv y aparece "Dependencias ya presentes
    y funcionales", puede que transformers no esté instalado. Instalar a mano:
        venv\Scripts\python.exe -m pip install "transformers>=4.45.0"

OPCIÓN B — Manual:

PASO 1 — Crear entorno virtual:

    Windows:
        python -m venv venv
        venv\Scripts\activate

    Linux / macOS:
        python3 -m venv venv
        source venv/bin/activate

PASO 2 — Instalar dependencias:

    pip install -r requirements.txt

PASO 3 — Ejecutar el servidor:

    uvicorn main:app --reload --host 127.0.0.1 --port 8000

PASO 4 — Abrir en el navegador:

    http://localhost:8000

Siempre ejecutar desde la raíz del proyecto para que "sqlite:///./login.db"
encuentre la base de datos correcta.

Credenciales demo (se crean automáticamente al arrancar):

    ┌───────────────┬──────────────────────────┬─────────────────┐
    │ Rol           │ Email                    │ Password        │
    ├───────────────┼──────────────────────────┼─────────────────┤
    │ admin         │ admin@example.com        │ admin1234       │
    │ supervisor    │ supervisor@example.com   │ super1234       │
    │ usuario       │ demo@example.com         │ demo1234        │
    │ learning      │ learning@example.com     │ learning1234    │
    └───────────────┴──────────────────────────┴─────────────────┘

    ⚠️  Cambiar estas claves antes de cualquier despliegue en producción.


================================================================================
4. DEPENDENCIAS (requirements.txt)
================================================================================

fastapi==0.115.0            Framework web asíncrono
uvicorn[standard]==0.32.0   Servidor ASGI con extras
jinja2==3.1.4               Motor de plantillas HTML
pydantic[email]==2.9.2      Validación de datos + validación de emails
bcrypt==4.2.0               Hash de contraseñas
PyJWT==2.9.0                Generación y validación de tokens JWT
sqlalchemy==2.0.35          ORM para la base de datos
python-multipart==0.0.12    OBLIGATORIO para que funcionen los Form(...)
ultralytics>=8.3.0,<9.0.0   YOLO (incluye Pillow y OpenCV como dependencias)
opencv-python-headless>=4.10.0.84,<5.0.0  Lectura de cámaras
numpy>=1.26.4,<2.0.0        Álgebra lineal para el análisis de profundidad
transformers>=4.45.0        Depth Anything V2 Small

⚠️  NO quitar python-multipart. Si falta, los formularios devuelven error 500.
⚠️  Los comentarios en requirements.txt van con "#". Un "//" hace fallar pip.


================================================================================
5. CAPA DE BASE DE DATOS (base_de_datos/)
================================================================================

Esta carpeta contiene TODO lo relacionado con SQL. Ningún otro módulo
del proyecto debería importar SQLAlchemy directamente.


--------------------------------------------------------------------------------
5.1 base_de_datos/conexion.py
--------------------------------------------------------------------------------

Responsabilidad:
  - Crear el motor (engine) de SQLAlchemy
  - Configurar la sesión (SesionLocal)
  - Definir la clase Base para los modelos
  - Proveer la dependency "obtener_sesion" para FastAPI
  - Proveer "crear_tablas" para inicializar la BD

Detalles clave:

  URL_BASE_DATOS = "sqlite:///./login.db"
      → Crea un archivo login.db en la raíz del proyecto.

  connect_args={"check_same_thread": False}
      → Necesario SOLO para SQLite, permite usar la conexión desde
        distintos threads (uvicorn usa un thread por request).

  NOTA: el nombre de la sesión es SesionLocal (no SessionLocal).
        Usar exactamente ese nombre en los imports.

  obtener_sesion():
      → Dependency de FastAPI que abre una sesión y la cierra al terminar.
        Se usa con Depends(obtener_sesion) en las rutas.

  crear_tablas():
      → Crea las tablas definidas en modelos.py si no existen.
        Se llama una sola vez, al arrancar la app.


--------------------------------------------------------------------------------
5.2 base_de_datos/modelos.py
--------------------------------------------------------------------------------

Tabla "usuarios":
  id                 → Integer, primary key, indexado
  nombre             → String, no nulo
  email              → String, único, indexado, no nulo
  password_hasheada  → String, no nulo (hash bcrypt)
  esta_activo        → Boolean, por defecto True
  es_admin           → Boolean, por defecto False
  rol                → String (admin, supervisor, usuario, learning)
  empresa_id         → Integer, FK a empresas (nullable)
  reset_code         → String, nullable (código de recuperación)
  reset_code_expira  → DateTime, nullable (expiración del código)

Tabla "empresas":
  id                 → Integer, primary key
  nombre             → String, único, no nulo

Tabla "departamentos":
  id                 → Integer, primary key
  nombre             → String, no nulo
  empresa_id         → Integer, FK a empresas

Tabla "camaras":
  id                 → Integer, primary key
  nombre             → String, no nulo
  url_stream         → String, no nulo (rtsp://, http://, .m3u8)
  empresa_id         → Integer, FK a empresas
  departamento_id    → Integer, FK a departamentos
  usuario_id         → Integer, FK a usuarios (supervisor que la creó)
  esta_activa        → Boolean, por defecto True

Tabla "auditoria":                                      [NUEVA v1.4.3]
  id                 → Integer, primary key, autoincremental
  usuario_email      → String, no nulo (email del actor de la acción)
  accion             → String, no nulo (descripción corta de la acción,
                        ej. "Crear usuario", "Crear empresa")
  detalle            → String, nullable (información adicional,
                        ej. nombre del recurso creado)
  fecha_hora         → DateTime, no nulo (timestamp del momento exacto)

⚠️  Si modificas las tablas existentes:
      1. Borra login.db
      2. Reinicia el servidor
    La tabla "auditoria" se agrega de forma aditiva al arrancar (v1.4.3):
    no es necesario borrar login.db para que aparezca.


--------------------------------------------------------------------------------
5.3 base_de_datos/usuarios.py
--------------------------------------------------------------------------------

Funciones disponibles:
  obtener_por_email(sesion, email) -> Optional[UsuarioORM]
  obtener_por_id(sesion, usuario_id) -> Optional[UsuarioORM]
  listar_usuarios(sesion) -> List[UsuarioORM]
  listar_usuarios_por_empresa(sesion, empresa_id) -> List[UsuarioORM]
  crear_usuario(sesion, email, password_hasheada, nombre, rol, empresa_id,
                esta_activo=True) -> UsuarioORM
  guardar_codigo_reset(sesion, usuario, codigo, expira) -> None
  actualizar_password(sesion, usuario, nueva_hash) -> None

Todas las funciones reciben la sesión como parámetro (inyección explícita).
NO abren sesiones por sí mismas — eso lo hace FastAPI con la dependency.


--------------------------------------------------------------------------------
5.4 base_de_datos/auditoria.py                                 [NUEVO v1.4.3]
--------------------------------------------------------------------------------

Funciones disponibles:
  registrar_accion(sesion, usuario_email, accion, detalle=None) -> None
      Inserta un nuevo registro de auditoría con la fecha/hora actual.
      Se llama desde main.py tras cada acción crítica exitosa.

  listar_todas(sesion) -> List[AuditoriaORM]
      Retorna todos los registros ordenados cronológicamente.
      Se usa en el endpoint GET /admin/auditoria/descargar para generar
      el reporte.


================================================================================
6. APLICACIÓN PRINCIPAL (main.py)
================================================================================

--------------------------------------------------------------------------------
6.1 Configuración
--------------------------------------------------------------------------------

SECRETO_JWT = "cambia-esto-en-produccion"
    ⚠️  En producción, muévelo a variable de entorno.
    ⚠️  Si lo cambias, TODOS los tokens emitidos dejan de ser válidos.

ALGORITMO = "HS256"
MINUTOS_EXPIRACION = 60
MINUTOS_RESET = 15
ROLES_VALIDOS = {"admin", "supervisor", "usuario", "learning"}

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), ...)
    → Sirve los archivos estáticos bajo /static/.

Imports relevantes v1.4.3:
    from base_de_datos.auditoria import registrar_accion, listar_todas
    from deepseek.learning_api import crear_router
    app.include_router(crear_router(requiere_learning))


--------------------------------------------------------------------------------
6.2 Utilidades de seguridad
--------------------------------------------------------------------------------

hashear_password(password) -> str
    Genera el hash bcrypt de una contraseña.

verificar_password(password, hasheada) -> bool
    Comprueba si una contraseña coincide con su hash.

crear_token(usuario_id, email, rol) -> str
    Genera un JWT con sub, email, rol, iat y exp.

decodificar_token(token) -> dict
    Valida y decodifica el JWT. Lanza 401 si expiró o es inválido.

extraer_token(request) -> Optional[str]
    Lee el token desde la cookie "access_token" (preferido) o desde el
    header Authorization: Bearer <token> (fallback).


--------------------------------------------------------------------------------
6.3 Dependencias de autenticación
--------------------------------------------------------------------------------

usuario_actual(request, sesion)
    → Devuelve el usuario logueado o lanza 401.

requiere_admin(usuario)
    → Exige rol admin. Lanza 403 si no.

requiere_supervisor(usuario)
    → Exige rol supervisor. Lanza 403 si no.

requiere_usuario(usuario)
    → Exige rol usuario. Lanza 403 si no.

requiere_learning(usuario)
    → Exige rol learning. Lanza 403 si no.

verificar_empresa_del_objeto(objeto, usuario)
    → 403 si objeto.empresa_id != usuario.empresa_id.


--------------------------------------------------------------------------------
6.4 Evento de arranque
--------------------------------------------------------------------------------

@app.on_event("startup")
def al_arrancar():
    1. Llama a crear_tablas() para asegurar que existan todas las tablas,
       incluida "auditoria" (v1.4.3). No borra datos existentes.
    2. Crea los usuarios demo si no existen (admin, supervisor, demo, learning).

Esto permite que el proyecto funcione desde el primer arranque sin pasos
manuales de seed, y que la tabla de auditoría aparezca sin borrar login.db.


--------------------------------------------------------------------------------
6.5 Rutas HTML
--------------------------------------------------------------------------------

GET /              → login.html (público)
GET /recuperar     → recuperar.html (público)
GET /dashboard     → dashboard.html; redirige según rol
GET /admin         → admin.html (solo admin)
GET /supervisor    → supervisor.html (solo supervisor)
GET /learning      → learning.html (solo learning)


--------------------------------------------------------------------------------
6.6 API de autenticación
--------------------------------------------------------------------------------

POST /auth/login
    Recibe (FormData): email, password
    Proceso:
        1. Busca el usuario por email.
        2. Verifica contraseña con bcrypt.
        3. Comprueba que esta_activo sea True.
        4. Genera un JWT y lo guarda en cookie httpOnly.
        5. Devuelve los datos del usuario (incluyendo rol).

    Respuestas:
        200 OK  → {access_token, token_type, usuario_id, email, nombre, rol}
        401     → "Credenciales inválidas"
        403     → "Usuario inactivo"

POST /auth/logout
    Borra la cookie "access_token". Devuelve {"mensaje": "Sesión cerrada"}.

GET /auth/yo
    Devuelve los datos del usuario logueado o 401.

POST /auth/recuperar
    Genera un código de 6 dígitos (expira en 15 min) y lo devuelve en la
    respuesta JSON (flujo simulado, sin email). Si el correo no existe,
    responde 200 con codigo_simulado: null (no revela si existe).

POST /auth/restablecer
    Valida email + código + nueva clave (mínimo 6 caracteres).
    Registra la acción en la tabla de auditoría.          [v1.4.3]


--------------------------------------------------------------------------------
6.7 API de administración
--------------------------------------------------------------------------------

GET /admin/usuarios?empresa_id=N
    Requiere ser admin. Devuelve la lista de usuarios (filtrable por empresa).

POST /admin/usuarios
    Requiere ser admin. Recibe (FormData): nombre, email, password, rol,
    empresa_id (opcional).
    Registra la acción en la tabla de auditoría.          [v1.4.3]
    Respuestas:
        200 OK  → {"mensaje": "Usuario creado", "usuario": {...}}
        400     → mensajes específicos de validación
        403     → si no es admin

GET /admin/empresas
    Requiere ser admin. Devuelve la lista de empresas.

POST /admin/empresas
    Requiere ser admin. Recibe (FormData): nombre.
    Registra la acción en la tabla de auditoría.          [v1.4.3]

GET /admin/auditoria/descargar                             [NUEVO v1.4.3]
    Requiere ser admin.
    Genera y devuelve un archivo .txt con todos los registros de auditoría
    ordenados cronológicamente. El nombre del archivo incluye la fecha actual
    (ej. reporte_auditoria_2026-11-14.txt).
    Se activa desde el botón "📄 Descargar Reporte de Actividad" en /admin.


--------------------------------------------------------------------------------
6.8 API del supervisor
--------------------------------------------------------------------------------

GET /supervisor/departamentos
POST /supervisor/departamentos
GET /supervisor/camaras            (solo las cámaras del supervisor)
POST /supervisor/camaras
    Registra la acción en la tabla de auditoría.          [v1.4.3]
DELETE /supervisor/camaras/{camara_id}


--------------------------------------------------------------------------------
6.9 API de learning
--------------------------------------------------------------------------------

GET /learning/camaras
GET /learning/camaras/{id}/frame
GET /learning/camaras/{id}/referencia
POST /learning/camaras/{id}/referencia
POST /learning/camaras/{id}/probar
GET /learning/config
PUT /learning/config

--- Endpoints de entrenamiento (deepseek/learning_api.py) ---
GET  /learning/estado-camaras?verificar=0|1
GET  /learning/ejemplos?camara_id=N
POST /learning/ejemplos
POST /learning/camaras/{id}/ejemplos/capturar
GET  /learning/ejemplos/{cid}/{et}/{nombre}
DELETE /learning/ejemplos/{cid}/{et}/{nombre}
POST /learning/ejemplos/{cid}/vacia/{nombre}/como-vacia
POST /learning/camaras/{id}/probar-foto
POST /learning/entrenar
GET  /learning/estado
PUT  /learning/estado
GET  /learning/exportar


--------------------------------------------------------------------------------
6.10 Healthcheck
--------------------------------------------------------------------------------

GET /health → {"status": "ok"}


================================================================================
7. FLUJO DE AUTENTICACIÓN
================================================================================

1. Usuario abre http://localhost:8000 → login.html

2. Usuario ingresa email/contraseña → login.js envía POST /auth/login

3. Backend valida y responde:
     - admin    → redirige a /admin
     - supervisor → redirige a /supervisor
     - learning → redirige a /learning
     - usuario  → redirige a /dashboard

4. El JWT se guarda en cookie httpOnly (el JS no puede leerlo).

5. En cada petición posterior, la cookie viaja automáticamente
   (gracias a credentials: "include" en los fetch).

6. Backend valida el token y el rol en CADA endpoint protegido.


Flujo visual:

    ┌──────────────┐         POST /auth/login        ┌──────────────┐
    │  login.html  │ ───────────────────────────────► │   FastAPI    │
    │  login.js    │                                  │   main.py    │
    └──────┬───────┘                                  └──────┬───────┘
           │                                                 │
           │  ◄──── 200 + cookie httpOnly + rol ─────────────┘
           │
           ▼
    ┌──────────────────────────────┐
    │ Según rol:                   │
    │   admin      → /admin        │
    │   supervisor → /supervisor   │
    │   learning   → /learning     │
    │   usuario    → /dashboard    │
    └──────────────────────────────┘


================================================================================
8. TEMPLATES (templates/)
================================================================================

--------------------------------------------------------------------------------
8.1 templates/login.html
--------------------------------------------------------------------------------

Elementos críticos:
  - <form id="login-form" method="post" action="/auth/login">
  - <input id="email" name="email">
  - <input id="password" name="password">
  - <button id="submit-btn">
  - <p id="message">
  - <script src="/static/login.js"></script>

⚠️  Si cambias algún id, DEBES actualizar login.js.
⚠️  El <form> DEBE tener id="login-form" para que el JS lo intercepte.


--------------------------------------------------------------------------------
8.2 templates/recuperar.html
--------------------------------------------------------------------------------

Página de recuperación de contraseña (pública).
Muestra el código generado en pantalla (flujo simulado sin email).


--------------------------------------------------------------------------------
8.3 templates/dashboard.html
--------------------------------------------------------------------------------

Elementos críticos:
  - <p id="user-email">
  - <button id="logout-btn">
  - <script src="/static/dashboard.js"></script>

⚠️  Si el usuario es admin, el servidor NUNCA sirve este HTML.
    Redirige a /admin automáticamente.


--------------------------------------------------------------------------------
8.4 templates/admin.html
--------------------------------------------------------------------------------

Elementos críticos:
  - <form id="crear-usuario-form">
  - <input id="nombre" name="nombre">
  - <input id="email" name="email">
  - <input id="password" name="password">
  - <select id="rol" name="rol"> (admin, supervisor, usuario, learning)
  - <select id="empresa_id" name="empresa_id"> (para roles no-admin)
  - <button id="submit-btn">
  - <p id="message">
  - <div id="tabla-usuarios">
  - <button id="refrescar-btn">
  - <button id="logout-btn">
  - Footer: <button id="btn-descargar-auditoria">               [v1.4.3]
            "📄 Descargar Reporte de Actividad"
            Activa la descarga del reporte vía fetch en admin.js.
  - <script src="/static/admin.js"></script>

⚠️  NUNCA cargar login.js o dashboard.js aquí.
    Si lo haces, se produce un bucle de redirecciones.


--------------------------------------------------------------------------------
8.5 templates/supervisor.html
--------------------------------------------------------------------------------

Sección Departamentos: formulario #crear-departamento-form, lista
#lista-departamentos.
Sección Cámaras: formulario #crear-camara-form (nombre, URL del stream,
departamento), tabla #tabla-camaras.
Modal #modal-camara: reproductor HLS o MJPEG. SIN botón "Detectar objetos".


--------------------------------------------------------------------------------
8.6 templates/learning.html
--------------------------------------------------------------------------------

Cabecera: título "Calibración de la IA", nombre del usuario, logout.
Tarjeta "Cámaras registradas": chips de estado (en línea/sin conexión),
botón "Comprobar conexión de todas".
Sección 1 "Foto de la habitación vacía": imagen actual, botón "Guardar como
vacía", foto vacía guardada.
Sección 2 "Fotos de ejemplo": subida por arrastre o input, captura desde
cámara, galería con probar/borrar/usar como vacía.
Sección 3 "Prueba y sensibilidad": deslizadores umbral_diff y area_min_pct,
botones "Probar con la cámara" y "Guardar sensibilidad".
Sección 4 "Entrenar con los ejemplos": evaluar con valores actuales, buscar
mejores valores, aplicar sugeridos.
Sección 5 "Estado y respaldo": notas por cámara, guardar estado, descargar
.zip de respaldo.


================================================================================
9. ESTILOS (static/style.css)
================================================================================

REGLA FUNDAMENTAL:
    SOLO EXISTE UN ARCHIVO CSS EN TODO EL PROYECTO: static/style.css
    Todas las páginas lo cargan con:
        <link rel="stylesheet" href="/static/style.css" />

NO crear archivos CSS por página. NO usar <style> inline.
(Excepción: las clases l-* de learning.html se definieron dentro del propio
HTML para no tocar style.css; si se desea unificar, moverlas al final de
static/style.css.)

Estructura del archivo:
  1. Reset (box-sizing, margin, padding)
  2. Variables CSS en :root (colores, radios, sombras)
  3. Base (body, tipografía, fondo)
  4. Layout (.pagina)
  5. Componentes reutilizables:
       .tarjeta, .encabezado, .campo, .boton, .boton--primario,
       .boton--peligro, .boton--secundario, .boton--sm, .mensaje,
       .spinner, .pie
  6. Sección admin: .admin-seccion, .admin-form, .tabla, .badge, etc.
  7. Animaciones (@keyframes fadeInUp, spin)
  8. Responsive (@media max-width)
  9. Modo oscuro automático (@media prefers-color-scheme)


================================================================================
10. JAVASCRIPT (static/)
================================================================================

--------------------------------------------------------------------------------
10.1 static/login.js
--------------------------------------------------------------------------------

Responsabilidades:
  - Si ya hay sesión activa, redirigir según rol.
  - Interceptar el submit del formulario con e.preventDefault().
  - Validar campos no vacíos.
  - Enviar FormData a POST /auth/login.
  - Redirigir a /admin, /supervisor, /learning o /dashboard según rol.
  - Limpiar los estados de error cuando el usuario escribe.

⚠️  El fetch DEBE incluir credentials: "include" para enviar la cookie.


--------------------------------------------------------------------------------
10.2 static/dashboard.js
--------------------------------------------------------------------------------

Responsabilidades:
  - Verificar sesión con GET /auth/yo.
  - Si es admin, redirigir a /admin.
  - Mostrar nombre y email del usuario.
  - Logout: POST /auth/logout y redirigir a /.


--------------------------------------------------------------------------------
10.3 static/admin.js
--------------------------------------------------------------------------------

Responsabilidades:
  - Verificar al arrancar que el usuario sea admin (GET /auth/yo).
  - Cargar la lista de usuarios (GET /admin/usuarios).
  - Crear usuarios (POST /admin/usuarios).
  - Refrescar la tabla bajo demanda.
  - Logout: POST /auth/logout y redirigir a /.
  - Descargar reporte de auditoría:                              [v1.4.3]
      Escucha el clic en #btn-descargar-auditoria.
      Realiza un GET /admin/auditoria/descargar con credentials: "include".
      Convierte la respuesta en un Blob y crea un enlace temporal <a>
      con URL de objeto para disparar la descarga del archivo .txt.
      Libera la URL de objeto tras la descarga.

⚠️  Todos los fetch DEBEN incluir credentials: "include" para enviar la cookie.


--------------------------------------------------------------------------------
10.4 static/supervisor.js
--------------------------------------------------------------------------------

Responsabilidades:
  - Verificar sesión con /auth/yo: admin → /admin; otro rol → /dashboard.
  - Cargar departamentos y cámaras propias.
  - Crear departamentos y cámaras.
  - Borrar cámaras (con confirmación).
  - Abrir modal de cámara (HLS, MJPEG o aviso RTSP).
  - SIN código de detección YOLO ni segmentación.


--------------------------------------------------------------------------------
10.5 static/learning.js
--------------------------------------------------------------------------------

Responsabilidades:
  - Verificar sesión (/auth/yo): rol distinto de learning → /dashboard.
  - Cargar sensibilidad, estado guardado y lista de cámaras al arrancar.
  - Pintar tarjetas de cámara con chips de estado.
  - Comprobar conexión de todas las cámaras en paralelo (verificar=1).
  - Gestión de foto vacía (guardar, ver).
  - Gestión de ejemplos (subida, captura, galería, probar, borrar,
    usar como vacía).
  - Prueba con cámara en vivo o foto propia.
  - Evaluación y búsqueda de mejores valores de sensibilidad.
  - Guardado y recuperación del estado en el servidor.
  - Descarga del respaldo .zip.
  - Escape de HTML en todos los textos del servidor (escapeHtml).


================================================================================
11. TABLA COMPLETA DE RUTAS
================================================================================

MÉTODO  RUTA                                        QUIÉN
GET     /                                           público (login.html)
GET     /recuperar                                  público (recuperar.html)
GET     /dashboard                                  autenticado; redirige
GET     /admin                                      admin
GET     /supervisor                                 supervisor
GET     /learning                                   learning
POST    /auth/login                                 público
POST    /auth/logout                                autenticado
GET     /auth/yo                                    autenticado
POST    /auth/recuperar                             público
POST    /auth/restablecer                           público
GET     /admin/usuarios                             admin
POST    /admin/usuarios                             admin
GET     /admin/empresas                             admin
POST    /admin/empresas                             admin
GET     /admin/auditoria/descargar                  admin     [NUEVO v1.4.3]
GET     /supervisor/departamentos                   supervisor
POST    /supervisor/departamentos                   supervisor
GET     /supervisor/camaras                         supervisor
POST    /supervisor/camaras                         supervisor
DELETE  /supervisor/camaras/{camara_id}             supervisor
GET     /learning/camaras                           learning
GET     /learning/camaras/{id}/frame                learning
GET     /learning/camaras/{id}/referencia           learning
POST    /learning/camaras/{id}/referencia           learning
POST    /learning/camaras/{id}/probar               learning
GET     /learning/config                            learning
PUT     /learning/config                            learning
GET     /learning/estado-camaras                    learning
GET     /learning/ejemplos                          learning
POST    /learning/ejemplos                          learning
POST    /learning/camaras/{id}/ejemplos/capturar    learning
GET     /learning/ejemplos/{cid}/{et}/{nombre}      learning
DELETE  /learning/ejemplos/{cid}/{et}/{nombre}      learning
POST    /learning/ejemplos/{cid}/vacia/{nombre}/como-vacia  learning
POST    /learning/camaras/{id}/probar-foto          learning
POST    /learning/entrenar                          learning
GET     /learning/estado                            learning
PUT     /learning/estado                            learning
GET     /learning/exportar                          learning
GET     /usuario/informes                           usuario
GET     /health                                     público
GET     /docs                                       desarrollo (Swagger UI)
GET     /static/*                                   público


================================================================================
12. SEGURIDAD POR CAPAS
================================================================================

El control de acceso se aplica en 3 niveles:

  Capa 1 — Frontend (JS)
      login.js redirige según rol tras el login.
      admin.js / supervisor.js / learning.js verifican el rol al arrancar.
      → Es UX, no seguridad real. Puede saltarse editando JS.

  Capa 2 — Vistas HTML (servidor)
      Cada vista verifica el rol antes de servir el HTML. Si no corresponde,
      redirige al destino correcto o a /.
      → El HTML no se entrega a quien no tiene permiso.

  Capa 3 — Endpoints (servidor)
      requiere_admin / requiere_supervisor / requiere_learning validan
      el token y el rol consultando la BD.
      → Aunque alguien falsifique el frontend, el servidor rechaza (403).

Tabla de escenarios:

  ┌─────────────────────────────────────────────┬──────────────────────────┐
  │ Escenario                                   │ Resultado                │
  ├─────────────────────────────────────────────┼──────────────────────────┤
  │ Admin hace login                            │ → /admin (directo)       │
  │ Supervisor hace login                       │ → /supervisor            │
  │ Usuario common hace login                   │ → /dashboard             │
  │ Learning hace login                         │ → /learning              │
  │ Admin escribe /dashboard en la URL          │ 302 → /admin             │
  │ Usuario común escribe /admin en URL         │ 302 → /dashboard         │
  │ Sin sesión escribe /admin                   │ 302 → /                  │
  │ Usuario común hace GET /admin/usuarios      │ 403 Forbidden            │
  │ Sin sesión hace GET /admin/usuarios         │ 401 Unauthorized         │
  │ Edita localStorage para decir admin         │ No sirve, server valida  │
  │ Roba la cookie desde otro navegador         │ No puede (httpOnly)      │
  │ Llama a /admin/auditoria/descargar sin ser  │ 403 Forbidden            │
  │ admin                                       │                          │
  └─────────────────────────────────────────────┴──────────────────────────┘

Observaciones adicionales de seguridad:
  - Las URLs de cámara pueden llevar usuario:clave (rtsp://user:pass@...) y
    se guardan en texto plano en login.db.
  - /learning/camaras no devuelve url_stream para proteger credenciales.
  - Los mensajes de error de lectura de cámara son genéricos en la respuesta
    HTTP; el detalle (con la URL) va solo a la consola del servidor.
  - El código de recuperación de contraseña se devuelve en la respuesta JSON
    (flujo simulado, sin email): solo apto para demo/desarrollo.
  - SECRETO_JWT conserva el valor por defecto "cambia-esto-en-produccion".
  - Las credenciales demo (admin1234, super1234, demo1234, learning1234)
    son solo para desarrollo.
  - login.db contiene usuarios y hashes: no subirlo a repositorios.
  - /docs está abierto; deshabilitarlo en producción si se desea.
  - Agregar deepseek/referencias/ y deepseek/entrenamiento/ a .gitignore.


================================================================================
13. REGLAS PARA NO ROMPER EL CÓDIGO
================================================================================

REGLA 1 — UN SOLO CSS GLOBAL
    Todo el estilo vive en static/style.css.
    No crear CSS por página. No usar <style> inline.
    (Excepción controlada: clases l-* en learning.html.)

REGLA 2 — SEPARACIÓN POR CAPAS
    base_de_datos/  → SOLO SQL
    templates/      → SOLO HTML
    static/         → SOLO CSS y JS
    deepseek/       → SOLO módulos de IA
    main.py         → Rutas FastAPI y utilidades

REGLA 3 — NOMBRES EN MINÚSCULAS
    base_de_datos (SIEMPRE en minúsculas).
    En Windows, renombrar en dos pasos si solo cambias mayúsculas.

REGLA 4 — IDs EN HTML Y getElementById EN JS
    Si cambias un id en un template, actualiza el .js que lo usa.
    IDs críticos:
        login.html:      login-form, email, password, submit-btn, message
        dashboard.html:  user-email, logout-btn
        admin.html:      crear-usuario-form, nombre, email, password,
                         rol, empresa_id, submit-btn, message,
                         tabla-usuarios, refrescar-btn, logout-btn,
                         btn-descargar-auditoria            [v1.4.3]

REGLA 5 — SCRIPT CORRECTO POR PÁGINA
    login.html      → login.js
    dashboard.html  → dashboard.js
    admin.html      → admin.js
    supervisor.html → supervisor.js
    learning.html   → learning.js
    ⚠️  NO cargar login.js en admin.html (provoca bucle de redirecciones).

REGLA 6 — FORMULARIOS SIEMPRE CON id
    El <form> DEBE tener id para que el JS lo intercepte.
    Los <input> DEBEN tener name="" para que el FormData los lea.

REGLA 7 — e.preventDefault() PRIMERO
    La PRIMERA línea de cada handler de submit.

REGLA 8 — credentials: "include" EN FETCH
    Todo fetch a endpoints que dependan de la cookie DEBE tener:
        credentials: "include"

REGLA 9 — __init__.py EN CARPETAS DE PAQUETES
    base_de_datos/ y deepseek/ DEBEN tener __init__.py.

REGLA 10 — BASE DE DATOS
    login.db se crea solo al arrancar. Si modificas la estructura de
    tablas existentes: borra login.db y reinicia el servidor.
    La tabla "auditoria" se agrega sin borrar login.db (v1.4.3).

REGLA 11 — SECRETO_JWT
    Si lo cambias, TODOS los tokens quedan inválidos.
    En producción debe venir de variable de entorno.

REGLA 12 — SesionLocal (no SessionLocal)
    conexion.py exporta SesionLocal. Usar exactamente ese nombre.

REGLA 13 — IMPORT CIRCULAR EN learning_api
    learning_api.py recibe requiere_learning como parámetro de
    crear_router() en vez de importar main.py directamente.


================================================================================
14. CÓMO AGREGAR COSAS NUEVAS SIN ROMPER NADA
================================================================================

--------------------------------------------------------------------------------
14.1 Agregar una página nueva
--------------------------------------------------------------------------------

  1. Crear templates/nueva.html con <link rel="stylesheet" href="/static/style.css">
  2. Crear static/nueva.js si necesita lógica.
  3. Agregar la ruta en main.py.
  4. Solo si hace falta, agregar clases nuevas AL FINAL de static/style.css.

--------------------------------------------------------------------------------
14.2 Agregar un campo al usuario (ej: "telefono")
--------------------------------------------------------------------------------

  1. Editar base_de_datos/modelos.py → agregar la columna.
  2. Borrar login.db.
  3. Editar base_de_datos/usuarios.py → incluir el campo en crear_usuario.
  4. Devolverlo en /auth/login y /auth/yo si aplica.
  5. Actualizar templates y JS para mostrarlo.

--------------------------------------------------------------------------------
14.3 Agregar un endpoint de auditoría adicional
--------------------------------------------------------------------------------

  1. Importar registrar_accion desde base_de_datos.auditoria en main.py.
  2. Llamar a registrar_accion(sesion, usuario.email, "Mi acción", detalle)
     dentro del endpoint, después de que la operación sea exitosa.

--------------------------------------------------------------------------------
14.4 Cambiar SQLite por Postgres
--------------------------------------------------------------------------------

  1. Editar base_de_datos/conexion.py → cambiar URL_BASE_DATOS.
  2. Instalar driver: pip install psycopg2-binary
  3. El resto del código NO cambia.

--------------------------------------------------------------------------------
14.5 Agregar el monitor automático de cámaras (pendiente)
--------------------------------------------------------------------------------

  1. Crear una tarea periódica (APScheduler o asyncio.create_task) que
     llame a deepseek/camara.py + volumen.py para cada cámara activa.
  2. Guardar el resultado en una tabla nueva (ej. HistorialDeteccionORM).
  3. Exponer un endpoint en /usuario/historial para el rol usuario.
  4. Agregar el gráfico en templates/dashboard.html y dashboard.js.


================================================================================
15. ERRORES COMUNES Y SOLUCIONES
================================================================================

ERROR: El formulario se envía por GET en vez de POST
FIX:   Verificar id en el <form>, e.preventDefault() y ausencia de errores
       JS en la consola.

ERROR: "ModuleNotFoundError: No module named 'base_de_datos'"
CAUSA: Carpeta con mayúsculas o sin __init__.py.
FIX:   Renombrar a minúsculas (dos pasos en Windows) y crear __init__.py.

ERROR: "ModuleNotFoundError: No module named 'deepseek'"
CAUSA: deepseek/ sin __init__.py o servidor no arrancado desde la raíz.
FIX:   Crear deepseek/__init__.py y ejecutar desde la raíz.

ERROR: "ImportError: cannot import name 'analizar_bytes' from 'deepseek.volumen'"
CAUSA: volumen.py incompleto o de versión anterior.
FIX:   Reemplazar con la versión completa del archivo.

ERROR: "ImportError: cannot import name 'crear_router' from 'deepseek.learning_api'"
CAUSA: learning_api.py no existe o está incompleto.
FIX:   Copiar deepseek/learning_api.py y reiniciar el servidor.

ERROR: Bucle infinito /auth/yo → /admin → /
CAUSA: admin.html carga login.js en vez de admin.js.
FIX:   Verificar <script src="/static/admin.js"></script> al final de admin.html.

ERROR: "Form data requires python-multipart to be installed"
FIX:   pip install python-multipart==0.0.12

ERROR: "no such table: usuarios" o "no such table: auditoria"
FIX:   Verificar crear_tablas() en al_arrancar(). Reiniciar el servidor.
       No es necesario borrar login.db para que aparezca "auditoria" (v1.4.3).

ERROR: La descarga del reporte no funciona (botón de auditoría)
CAUSA: El fetch en admin.js no incluye credentials: "include", o el
       endpoint no está registrado en main.py.
FIX:   Verificar el import de registrar_accion y listar_todas en main.py,
       y que el endpoint GET /admin/auditoria/descargar esté definido.

ERROR: "Falta el token de autenticación" al abrir /learning/camaras
CAUSA: El navegador no tiene sesión activa en esa dirección.
FIX:   Iniciar sesión desde la misma dirección (localhost o 127.0.0.1,
       nunca mezclar ambos).

ERROR: iniciar.bat no instala paquetes nuevos
CAUSA: "Dependencias ya presentes y funcionales" → no reinstala.
FIX:   Instalar transformers a mano:
       venv\Scripts\python.exe -m pip install "transformers>=4.45.0"

ERROR: "Credenciales inválidas" para learning@example.com
CAUSA: La columna "rol" tiene restricción Enum que no incluye "learning".
FIX:   Verificar modelos.py y, si aplica, borrar login.db y reiniciar.


================================================================================
16. PRUEBAS DE FUNCIONAMIENTO
================================================================================

PRUEBA 1 — Servidor arriba
    iniciar.bat (o uvicorn main:app --reload --host 127.0.0.1 --port 8000)
    → Debe mostrar "Application startup complete" sin ImportError.

PRUEBA 2 — Healthcheck
    http://localhost:8000/health
    → {"status": "ok"}

PRUEBA 3 — Login por rol
    admin@example.com / admin1234           → /admin
    supervisor@example.com / super1234     → /supervisor
    demo@example.com / demo1234            → /dashboard
    learning@example.com / learning1234   → /learning

PRUEBA 4 — Crear usuario desde /admin
    Crear un usuario nuevo con rol supervisor y empresa asociada.
    Verificar que aparece en la tabla.

PRUEBA 5 — Auditoría                                           [v1.4.3]
    Crear un usuario y una empresa desde /admin.
    Pulsar "📄 Descargar Reporte de Actividad".
    → Se descarga un archivo .txt con los registros de ambas acciones.

PRUEBA 6 — Recuperación de contraseña
    Ir a /recuperar → ingresar email de un usuario existente.
    El código de 6 dígitos aparece en pantalla.
    Usar ese código para restablecer la contraseña.
    Verificar que el nuevo login funciona.

PRUEBA 7 — Calibración de la IA
    Entrar con learning@example.com.
    Elegir una cámara, guardar la foto vacía, poner un objeto y probar.
    La primera vez descarga el modelo (~100 MB, requiere internet).

PRUEBA 8 — Logout
    Pulsar "Cerrar sesión" desde cualquier panel.
    Intentar acceder a /admin → debe redirigir a /.


================================================================================
17. CHECKLIST ANTES DE SUBIR A PRODUCCIÓN
================================================================================

[ ] Cambiar SECRETO_JWT por uno aleatorio largo.
[ ] Mover SECRETO_JWT a variable de entorno.
[ ] Cambiar URL_BASE_DATOS a Postgres/MySQL.
[ ] Activar HTTPS.
[ ] Cambiar la cookie a secure=True y samesite="strict".
[ ] Proteger o deshabilitar /docs en producción.
[ ] Añadir rate limiting en /auth/login y /auth/recuperar.
[ ] Borrar los usuarios demo de la base de datos.
[ ] Configurar CORS si el frontend se sirve desde otro dominio.
[ ] Verificar que __init__.py exista en base_de_datos/ y deepseek/.
[ ] Agregar deepseek/referencias/ y deepseek/entrenamiento/ a .gitignore.
[ ] No subir login.db a repositorios.
[ ] No subir credenciales de cámaras (rtsp://user:pass@...) a repositorios.
[ ] Revisar la exposición de url_stream en GET /usuario/informes.
[ ] Eliminar la carga de yolov8n.pt si YOLO general ya no se usa.


================================================================================
18. HISTORIAL DE VERSIONES
================================================================================

v1.4    Login por roles, empresas, departamentos, cámaras con modal (HLS +
        MJPEG), YOLO general (botón "Detectar objetos"), recuperación de
        contraseña simulada (código de 6 dígitos), prevención de enumeración
        de usuarios.

v1.4.1  - Rol "learning", usuario learning@example.com y página /learning.
        - deepseek/volumen.py: habitación vacía vs con cosas con Depth
          Anything V2 Small (preentrenado, Apache-2.0).
        - Endpoints /learning/* (cámaras, frame, referencia, probar, config).
        - Lectura de frames por el servidor (OpenCV, RTSP por TCP).
        - Sensibilidad global editable (config_volumen.json).
        - Supervisor reducido a solo visualización: sin botón ni endpoints
          /detectar y /segmentar.
        - Redirecciones actualizadas para el nuevo rol.

v1.4.2  - deepseek/learning_api.py: herramientas de entrenamiento (estado
          de cámaras con verificación de conexión, subida y captura de
          ejemplos, probar-foto, entrenar evaluar/buscar, estado guardado en
          disco y exportación a .zip).
        - templates/learning.html y static/learning.js reescritos: todas las
          cámaras registradas, galería de ejemplos, sección de entrenamiento,
          estado y respaldo.
        - main.py: import + include_router de learning_api.

v1.4.3  - base_de_datos/auditoria.py: funciones registrar_accion y
          listar_todas.
        - base_de_datos/modelos.py: tabla AuditoriaORM (id, usuario_email,
          accion, detalle, fecha_hora).
        - main.py: llamadas a registrar_accion en POST /admin/usuarios,
          POST /admin/empresas, POST /supervisor/camaras y
          POST /auth/restablecer. Nuevo endpoint GET
          /admin/auditoria/descargar.
        - templates/admin.html: botón "📄 Descargar Reporte de Actividad"
          en el footer.
        - static/admin.js: lógica de descarga del reporte con fetch + Blob.
        - No fue necesario borrar login.db.


================================================================================
19. GLOSARIO
================================================================================

JWT             Token firmado que representa la sesión del usuario.
httpOnly        Atributo de cookie que impide que JS la lea.
bcrypt          Algoritmo de hash de contraseñas (no reversible).
SQLAlchemy      ORM de Python para hablar con la base de datos.
FastAPI         Framework web moderno para Python.
Jinja2          Motor de plantillas HTML.
Uvicorn         Servidor ASGI que ejecuta FastAPI.
SQLite          Base de datos en un archivo (login.db).
FormData        Formato de envío de formularios.
Dependency      Función que FastAPI ejecuta antes de una ruta (Depends).
ORM             Object-Relational Mapping.
Módulo          Archivo .py que puede importarse.
Paquete         Carpeta con __init__.py que agrupa módulos.
Rol             Distinción entre admin, supervisor, usuario y learning.
learning        Rol que calibra y entrena la IA; ve todas las cámaras.
Calibrar        Guardar la foto vacía de cada cámara y ajustar la
                sensibilidad. No es entrenar una red neuronal.
Entrenar (aquí) Medir el acierto con ejemplos y buscar los mejores valores
                de sensibilidad. La red ya viene preentrenada.
Auditoría       Registro automático de acciones críticas (crear usuario,
                empresa, cámara, resetear contraseña) con email del actor,
                descripción y fecha/hora.
Depth Anything  Modelo preentrenado que estima la profundidad desde una sola
V2 Small        imagen (Apache-2.0, ~100 MB).
Umbral          Cuánto debe cambiar la profundidad para marcar un píxel.
Área mínima     % de la imagen cambiada necesario para decir "hay cosas".
MJPEG           Video como secuencia de fotos JPEG por HTTP.
RTSP            Protocolo de video de cámaras IP; el servidor lo lee con
                OpenCV (el navegador no puede reproducirlo directamente).
HLS (.m3u8)     Streaming por segmentos, reproducible con hls.js.
APIRouter       Objeto de FastAPI que agrupa rutas y se monta con
                include_router.
Blob            Objeto JavaScript que representa datos binarios; se usa para
                disparar descargas de archivos desde el navegador.
Path traversal  Ataque que intenta salir de una carpeta con ".." en el
                nombre de archivo; bloqueado con validación _nombre_ok.

================================================================================
                               FIN DEL DOCUMENTO
================================================================================
