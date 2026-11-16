================================================================================
                 LOGIN CON PANEL DE ADMINISTRACIÓN — DOCUMENTACIÓN
================================================================================
Proyecto:   Login + Panel admin con FastAPI + SQLite + JWT + HTML/CSS/JS
Stack:      Python 3.12 · FastAPI · SQLAlchemy · bcrypt · PyJWT · Jinja2
Frontend:   HTML + CSS + JS puro (sin frameworks)
CSS:        Un único archivo global para todas las páginas
Seguridad:  JWT en cookie httpOnly + validación en servidor por rol
================================================================================


================================================================================
1. DESCRIPCIÓN GENERAL
================================================================================

Aplicación web con dos tipos de usuario:

  - Usuario común → accede a /dashboard
  - Administrador → accede a /admin (panel de gestión de usuarios)

Características:

  - Backend en FastAPI (Python 3.12)
  - Base de datos SQLite mediante SQLAlchemy 2.x
  - Contraseñas hasheadas con bcrypt
  - Autenticación basada en tokens JWT guardados en cookie httpOnly
  - Redirección automática según el rol tras el login
  - Control de acceso validado en el SERVIDOR (no solo en JS)
  - Un único archivo CSS global (static/style.css)

Alcance actual:
  - Login de usuarios existentes
  - Panel de administración para crear usuarios (nombre, email, password, rol)
  - Listado de usuarios registrados
  - Logout con borrado de cookie en servidor

Fuera de alcance (por ahora):
  - Registro público desde el frontend
  - Edición / eliminación de usuarios desde el panel
  - Recuperación de contraseña
  - Integración con IA


================================================================================
2. ESTRUCTURA DEL PROYECTO
================================================================================

login-simple/
│
├── base_de_datos/              ← Capa de datos (TODO lo de SQL aquí)
│   ├── __init__.py             → Marca la carpeta como paquete Python
│   ├── conexion.py             → Motor SQLAlchemy, sesión, creación de tablas
│   ├── modelos.py              → Definición de la tabla "usuarios"
│   └── usuarios.py             → Funciones CRUD sobre usuarios
│
├── templates/                  ← HTML (Jinja2)
│   ├── login.html              → Formulario de login
│   ├── dashboard.html          → Página de usuario común
│   └── admin.html              → Panel de administración
│
├── static/                     ← Archivos estáticos
│   ├── style.css               → ÚNICO CSS GLOBAL (todas las páginas)
│   ├── login.js                → Lógica del formulario de login
│   ├── dashboard.js            → Lógica del dashboard de usuario
│   └── admin.js                → Lógica del panel de administración
│
├── main.py                     → App FastAPI, rutas y utilidades
├── requirements.txt            → Dependencias Python
└── DOCUMENTACION.txt           → Este archivo


Notas importantes sobre nombres:

  - "base_de_datos" SIEMPRE en minúsculas (Python es case-sensitive).
  - Los archivos .py dentro de base_de_datos/ deben existir en minúsculas.
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
  - Conexión a internet solo la primera vez

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

    uvicorn main:app --reload

PASO 4 — Abrir en el navegador:

    http://localhost:8000

Credenciales demo (se crean automáticamente al arrancar):

    ┌────────────────────┬─────────────────┬───────────┐
    │ Rol                │ Email           │ Password  │
    ├────────────────────┼─────────────────┼───────────┤
    │ Administrador      │ admin@example.com │ admin1234 │
    │ Usuario común      │ demo@example.com  │ demo1234  │
    └────────────────────┴─────────────────┴───────────┘


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


⚠️  NO quitar python-multipart. Si falta, los formularios devuelven error 500.


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
  - Configurar la sesión (SessionLocal)
  - Definir la clase Base para los modelos
  - Proveer la dependency "obtener_sesion" para FastAPI
  - Proveer "crear_tablas" para inicializar la BD

Detalles clave:

  URL_BASE_DATOS = "sqlite:///./login.db"
      → Crea un archivo login.db en la raíz del proyecto.

  connect_args={"check_same_thread": False}
      → Necesario SOLO para SQLite, permite usar la conexión desde
        distintos threads (uvicorn usa un thread por request).

  obtener_sesion():
      → Dependency de FastAPI que abre una sesión y la cierra al terminar.
        Se usa con Depends(obtener_sesion) en las rutas.

  crear_tablas():
      → Crea las tablas definidas en modelos.py si no existen.
        Se llama una sola vez, al arrancar la app (evento "startup").


--------------------------------------------------------------------------------
5.2 base_de_datos/modelos.py
--------------------------------------------------------------------------------

Define la tabla "usuarios":

  Columnas:
    id                 → Integer, primary key, indexado
    nombre             → String, no nulo (nombre completo del usuario)
    email              → String, único, indexado, no nulo
    password_hasheada  → String, no nulo (el hash bcrypt)
    esta_activo        → Boolean, por defecto True
    es_admin           → Boolean, por defecto False

⚠️  Si modificas esta tabla:
      1. Borra login.db
      2. Reinicia el servidor
    SQLite NO migra cambios de esquema automáticamente.


--------------------------------------------------------------------------------
5.3 base_de_datos/usuarios.py
--------------------------------------------------------------------------------

Funciones disponibles:

  obtener_por_email(sesion, email) -> Optional[UsuarioORM]
      Busca un usuario por email (case-insensitive).

  obtener_por_id(sesion, usuario_id) -> Optional[UsuarioORM]
      Busca un usuario por su id.

  listar_usuarios(sesion) -> List[UsuarioORM]
      Devuelve todos los usuarios ordenados por id.

  crear_usuario(sesion, email, password_hasheada, nombre="", esta_activo=True,
                es_admin=False) -> UsuarioORM
      Crea un usuario nuevo, lo persiste y devuelve la instancia.

Todas las funciones reciben la sesión como parámetro (inyección explícita).
NO abren sesiones por sí mismas — eso lo hace FastAPI con la dependency.


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

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), ...)
    → Sirve los archivos estáticos bajo /static/.


--------------------------------------------------------------------------------
6.2 Utilidades de seguridad
--------------------------------------------------------------------------------

hashear_password(password) -> str
    Genera el hash bcrypt de una contraseña.

verificar_password(password, hasheada) -> bool
    Comprueba si una contraseña coincide con su hash.

crear_token(usuario_id, email, es_admin) -> str
    Genera un JWT con sub, email, es_admin, iat y exp.

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
    → Exige que el usuario sea admin (verificado en la BD). Lanza 403 si no.
    → Se usa con Depends(requiere_admin) en los endpoints de /admin.


--------------------------------------------------------------------------------
6.4 Evento de arranque
--------------------------------------------------------------------------------

@app.on_event("startup")
def al_arrancar():
    1. Llama a crear_tablas() para asegurar que existan las tablas.
    2. Si no existe admin@example.com, lo crea con es_admin=True.
    3. Si no existe demo@example.com, lo crea como usuario común.

Esto permite que el proyecto funcione desde el primer arranque sin pasos
manuales de seed.


--------------------------------------------------------------------------------
6.5 Rutas HTML
--------------------------------------------------------------------------------

GET /              → login.html
GET /dashboard     → dashboard.html (redirige a /admin si es admin)
GET /admin         → admin.html (redirige a /dashboard si es usuario común)


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
        5. Devuelve los datos del usuario (incluyendo es_admin).

    Respuestas:
        200 OK
            {
                "access_token": "...",
                "token_type": "bearer",
                "usuario_id": 1,
                "email": "admin@example.com",
                "nombre": "Administrador",
                "es_admin": true
            }
        401 Unauthorized → "Credenciales inválidas"
        403 Forbidden    → "Usuario inactivo"


POST /auth/logout
    Borra la cookie "access_token". Devuelve {"mensaje": "Sesión cerrada"}.

GET /auth/yo
    Devuelve los datos del usuario logueado o 401.
    Se usa para verificar sesión desde el JS.


--------------------------------------------------------------------------------
6.7 API de administración
--------------------------------------------------------------------------------

GET /admin/usuarios
    Requiere ser admin. Devuelve la lista de usuarios:
        [{"id": 1, "nombre": "...", "email": "...",
          "esta_activo": true, "es_admin": false}, ...]


POST /admin/usuarios
    Requiere ser admin. Recibe (FormData):
        nombre, email, password, es_admin (opcional)
    Validaciones:
        - nombre no vacío
        - password >= 6 caracteres
        - email no registrado
    Respuestas:
        200 OK → {"mensaje": "Usuario creado", "usuario": {...}}
        400 Bad Request → mensajes específicos
        403 Forbidden → si no es admin


--------------------------------------------------------------------------------
6.8 Healthcheck
--------------------------------------------------------------------------------

GET /health → {"status": "ok"}


================================================================================
7. FLUJO DE AUTENTICACIÓN
================================================================================

1. Usuario abre http://localhost:8000 → login.html

2. Usuario ingresa email/contraseña → login.js envía POST /auth/login

3. Backend valida y responde:
     - Si es admin → redirige a /admin
     - Si es usuario común → redirige a /dashboard

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
           │  ◄──── 200 + cookie httpOnly + es_admin ────────┘
           │
           ▼
    ┌──────────────────────────────┐
    │ ¿es_admin?                   │
    │   sí → /admin                │
    │   no → /dashboard            │
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
8.2 templates/dashboard.html
--------------------------------------------------------------------------------

Elementos críticos:
  - <p id="user-email">
  - <code id="token-display">
  - <button id="logout-btn">
  - <script src="/static/dashboard.js"></script>

⚠️  Si el usuario es admin, el servidor NUNCA sirve este HTML.
    Redirige a /admin automáticamente.


--------------------------------------------------------------------------------
8.3 templates/admin.html
--------------------------------------------------------------------------------

Elementos críticos:
  - <form id="crear-usuario-form">
  - <input id="nombre" name="nombre">
  - <input id="email" name="email">
  - <input id="password" name="password">
  - <input id="es_admin" type="checkbox">
  - <button id="submit-btn">
  - <p id="message">
  - <div id="tabla-usuarios">
  - <button id="refrescar-btn">
  - <button id="logout-btn">
  - <script src="/static/admin.js"></script>

⚠️  NUNCA cargar login.js o dashboard.js aquí.
    Si lo haces, se produce un bucle de redirecciones.


================================================================================
9. ESTILOS (static/style.css)
================================================================================

REGLA FUNDAMENTAL:
    SOLO EXISTE UN ARCHIVO CSS EN TODO EL PROYECTO: static/style.css
    Todas las páginas lo cargan con:
        <link rel="stylesheet" href="/static/style.css" />

NO crear archivos CSS por página. NO usar <style> inline.

Estructura del archivo:

  1. Reset (box-sizing, margin, padding)
  2. Variables CSS en :root (colores, radios, sombras)
  3. Base (body, tipografía, fondo)
  4. Layout (.pagina)
  5. Componentes reutilizables:
       .tarjeta          contenedor blanco con sombra
       .tarjeta--login   variante login
       .tarjeta--dashboard  variante dashboard
       .tarjeta--admin   variante admin
       .encabezado       título + subtítulo centrados
       .campo            label + input
       .boton            botón base
       .boton--primario  variante azul
       .boton--peligro   variante roja
       .boton--secundario variante gris
       .boton--sm        tamaño pequeño
       .mensaje          texto de error/éxito
       .spinner          indicador de carga
       .pie              pie de la tarjeta
       .caja-token       contenedor del token en dashboard
       .dashboard-acciones  botones del dashboard
  6. Sección admin:
       .admin-seccion        cada bloque del panel
       .admin-subtitulo      subtítulo de sección
       .admin-seccion-header cabecera con botón Refrescar
       .admin-form           formulario del panel
       .checkbox-label       checkbox estilizado
       .tabla-usuarios       contenedor de la tabla
       .tabla                tabla de usuarios
       .badge                etiquetas de rol/estado
       .badge--admin         badge amarillo para admins
       .badge--activo        badge verde
       .badge--inactivo      badge rojo
       .enlace-volver        link "← Volver"
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
  - Guardar datos no sensibles en localStorage (email, nombre, es_admin).
  - Redirigir a /admin si es admin, /dashboard si no.
  - Limpiar los estados de error cuando el usuario escribe.

⚠️  El fetch DEBE incluir credentials: "include" para enviar la cookie.

--------------------------------------------------------------------------------
10.2 static/dashboard.js
--------------------------------------------------------------------------------

Responsabilidades:
  - Verificar sesión con GET /auth/yo.
  - Si es admin, redirigir a /admin (aunque el server ya lo hizo, por si acaso).
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

⚠️  Todos los fetch DEBEN incluir credentials: "include" para enviar la cookie.


================================================================================
11. RUTAS DE LA APLICACIÓN
================================================================================

MÉTODO   RUTA                DESCRIPCIÓN                      QUIÉN
------   -----------------   ------------------------------   ---------------
GET      /                   Login (HTML)                     público
GET      /dashboard          Dashboard (HTML)                 autenticado
GET      /admin              Panel admin (HTML)               solo admin
POST     /auth/login         Autenticación                    público
POST     /auth/logout        Cerrar sesión                    autenticado
GET      /auth/yo            Datos del usuario logueado       autenticado
GET      /admin/usuarios     Listar usuarios                  solo admin
POST     /admin/usuarios     Crear usuario                    solo admin
GET      /health             Healthcheck                      público
GET      /docs               Swagger UI                       desarrollo
GET      /static/*           Archivos estáticos               público


================================================================================
12. SEGURIDAD POR CAPAS
================================================================================

El control de acceso se aplica en 3 niveles:

  Capa 1 — Frontend (JS)
      login.js redirige según es_admin tras el login.
      admin.js verifica el rol al arrancar y redirige si no es admin.
      → Es UX, no seguridad real. Puede saltarse editando JS.

  Capa 2 — Vistas HTML (servidor)
      vista_dashboard() redirige a /admin si el usuario es admin.
      vista_admin() redirige a /dashboard si NO es admin.
      → El HTML no se entrega a quien no tiene permiso.

  Capa 3 — Endpoints (servidor)
      requiere_admin() valida el token y el rol consultando la BD.
      → Aunque alguien falsifique el frontend, el servidor rechaza (403).

Tabla de escenarios:

  ┌────────────────────────────────────────┬──────────────────────────────┐
  │ Escenario                              │ Resultado                    │
  ├────────────────────────────────────────┼──────────────────────────────┤
  │ Admin hace login                       │ → /admin (directo)           │
  │ Usuario común hace login               │ → /dashboard                 │
  │ Admin escribe /dashboard en la URL     │ 302 → /admin                 │
  │ Usuario común escribe /admin en URL    │ 302 → /dashboard             │
  │ Sin sesión escribe /admin              │ 302 → /                     │
  │ Usuario común hace GET /admin/usuarios │ 403 Forbidden                │
  │ Sin sesión hace GET /admin/usuarios    │ 401 Unauthorized             │
  │ Edita localStorage para decir admin    │ No sirve, el server valida BD│
  │ Roba la cookie desde otro navegador    │ No puede leerla (httpOnly)   │
  └────────────────────────────────────────┴──────────────────────────────┘


================================================================================
13. REGLAS PARA NO ROMPER EL CÓDIGO
================================================================================

REGLA 1 — UN SOLO CSS GLOBAL
    Todo el estilo vive en static/style.css.
    No crear CSS por página. No usar <style> inline.

REGLA 2 — SEPARACIÓN POR CAPAS
    base_de_datos/  → SOLO SQL
    templates/      → SOLO HTML
    static/         → SOLO CSS y JS
    main.py         → Rutas FastAPI y utilidades

REGLA 3 — NOMBRES EN MINÚSCULAS
    base_de_datos (SIEMPRE en minúsculas).
    En Windows, renombrar en dos pasos si solo cambias mayúsculas.

REGLA 4 — IDs EN HTML Y getElementById EN JS
    Si cambias un id en un template, actualiza el .js que lo usa.
    IDs críticos:
        login.html:     login-form, email, password, submit-btn, message
        dashboard.html: user-email, token-display, logout-btn
        admin.html:     crear-usuario-form, nombre, email, password,
                        es_admin, submit-btn, message, tabla-usuarios,
                        refrescar-btn, logout-btn

REGLA 5 — SCRIPT CORRECTO POR PÁGINA
    login.html     → login.js
    dashboard.html → dashboard.js
    admin.html     → admin.js
    ⚠️  NO cargar login.js en admin.html (provoca bucle de redirecciones).

REGLA 6 — FORMULARIOS SIEMPRE CON id
    El <form> DEBE tener id (ej: login-form) para que el JS lo intercepte.
    Si no tiene id, el navegador envía por GET y se rompe todo.
    Los <input> DEBEN tener name="" para que el FormData los lea.

REGLA 7 — e.preventDefault() PRIMERO
    En cada addEventListener("submit", async (e) => {...}),
    la PRIMERA línea debe ser e.preventDefault().

REGLA 8 — credentials: "include" EN FETCH
    Todo fetch a endpoints que dependan de la cookie DEBE tener:
        credentials: "include"
    Si falta, el servidor no recibe la cookie y responde 401.

REGLA 9 — __init__.py EN CARPETAS DE PAQUETES
    base_de_datos/ DEBE tener __init__.py.

REGLA 10 — BASE DE DATOS
    El archivo login.db se crea solo al arrancar.
    Si modificas la estructura de la tabla "usuarios":
        1. Borra login.db
        2. Reinicia el servidor

REGLA 11 — SECRETO_JWT
    Si lo cambias, TODOS los tokens quedan inválidos.
    En producción debe venir de variable de entorno.

REGLA 12 — NO DUPLICAR CÓDIGO
    Antes de crear una función, revisa:
        base_de_datos/usuarios.py:
            obtener_por_email, obtener_por_id, listar_usuarios, crear_usuario
        main.py:
            hashear_password, verificar_password, crear_token,
            decodificar_token, extraer_token


================================================================================
14. CÓMO AGREGAR COSAS NUEVAS SIN ROMPER NADA
================================================================================

--------------------------------------------------------------------------------
14.1 Agregar una página nueva
--------------------------------------------------------------------------------

  1. Crear templates/nueva.html con <link rel="stylesheet" href="/static/style.css">
  2. Crear static/nueva.js si necesita lógica.
  3. Agregar la ruta en main.py:

        @app.get("/nueva", response_class=HTMLResponse)
        def vista_nueva(request: Request):
            return templates.TemplateResponse("nueva.html", {"request": request})

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
14.3 Agregar edición de usuarios desde el panel
--------------------------------------------------------------------------------

  1. Añadir en main.py:
        @app.patch("/admin/usuarios/{usuario_id}")
        def admin_editar_usuario(usuario_id: int, ..., admin=Depends(requiere_admin)):
            ...
  2. Añadir botón "Editar" en cada fila de la tabla (admin.js).
  3. Añadir modal o formulario inline en admin.html.

--------------------------------------------------------------------------------
14.4 Cambiar SQLite por Postgres
--------------------------------------------------------------------------------

  1. Editar base_de_datos/conexion.py → cambiar URL_BASE_DATOS.
  2. Instalar driver: pip install psycopg2-binary
  3. El resto del código NO cambia.

--------------------------------------------------------------------------------
14.5 Agregar integración con IA
--------------------------------------------------------------------------------

  1. Crear carpeta nueva con su propio __init__.py (ej: ia/ o deepseek/).
  2. Dentro: cliente.py, esquemas.py, rutas.py.
  3. En main.py:
        from ia.rutas import router as ia_router
        app.include_router(ia_router)
  4. Crear template y JS nuevos reutilizando style.css.
  5. NO tocar base_de_datos/ ni templates/ existentes.


================================================================================
15. ERRORES COMUNES Y SOLUCIONES
================================================================================

ERROR: El formulario se envía por GET en vez de POST
CAUSA 1: El <form> no tiene id="login-form".
FIX 1:   Agregar id al form.
CAUSA 2: login.js falla antes de registrar el listener.
FIX 2:   Revisar F12 → Console, corregir el error.
CAUSA 3: El navegador tiene login.js cacheado.
FIX 3:   Ctrl + Shift + R (recarga forzada).
CAUSA 4: Falta e.preventDefault() en el submit.
FIX 4:   Añadirlo como primera línea del handler.

ERROR: "ModuleNotFoundError: No module named 'base_de_datos'"
CAUSA 1: La carpeta se llama "Base_de_datos" (mayúscula).
FIX 1:   Renombrar a minúsculas (dos pasos en Windows).
CAUSA 2: Falta base_de_datos/__init__.py.
FIX 2:   type nul > base_de_datos\__init__.py
CAUSA 3: main.py no está en la raíz.
FIX 3:   Mover main.py a la raíz del proyecto.

ERROR: Bucle infinito /auth/yo → /admin → /
CAUSA: admin.html carga login.js en vez de admin.js.
FIX:   Verificar <script src="/static/admin.js"></script> al final de admin.html.

ERROR: "Form data requires python-multipart to be installed"
FIX:   pip install python-multipart==0.0.12

ERROR: "TemplateNotFound: login.html"
CAUSA: Ruta de templates mal o archivo faltante.
FIX:   Verificar que templates/login.html exista.

ERROR: "no such table: usuarios"
FIX:   Verificar crear_tablas() en al_arrancar(). Borrar login.db y reiniciar.

ERROR: Login devuelve 500
CAUSA: bcrypt o BD mal configurados.
FIX:   Mirar la consola de uvicorn → traceback completo.

ERROR: Tras login, redirige pero vuelve a "/"
CAUSA 1: No se guardó la cookie httpOnly.
FIX 1:   DevTools → Application → Cookies → verificar access_token.
CAUSA 2: Fetch sin credentials: "include".
FIX 2:   Añadirlo a todos los fetch que dependan de la sesión.

ERROR: El CSS no se aplica
FIX:   Verificar <link rel="stylesheet" href="/static/style.css"> en el HTML.
       Y que main.py monte:
           app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


================================================================================
16. PRUEBAS DE FUNCIONAMIENTO
================================================================================

PRUEBA 1 — Servidor arriba
    uvicorn main:app --reload
    → Debe mostrar "Uvicorn running on http://127.0.0.1:8000"

PRUEBA 2 — Healthcheck
    curl http://localhost:8000/health
    → {"status":"ok"}

PRUEBA 3 — Login correcto (admin)
    curl -X POST http://localhost:8000/auth/login ^
      -d "email=admin@example.com" ^
      -d "password=admin1234" -i
    → 200 OK, con Set-Cookie: access_token=...
    → JSON con es_admin: true

PRUEBA 4 — Login incorrecto
    curl -X POST http://localhost:8000/auth/login ^
      -d "email=admin@example.com" ^
      -d "password=mal"
    → 401 {"detail":"Credenciales inválidas"}

PRUEBA 5 — Flujo completo admin
    1. http://localhost:8000
    2. Login: admin@example.com / admin1234
    3. Debe redirigir a /admin
    4. Crear un usuario de prueba
    5. Ver la tabla actualizada

PRUEBA 6 — Flujo completo usuario común
    1. Login: demo@example.com / demo1234
    2. Debe redirigir a /dashboard
    3. Escribir /admin a mano → debe redirigir a /dashboard

PRUEBA 7 — Logout
    1. Estar logueado
    2. Pulsar "Cerrar sesión"
    3. Debe volver a / y no poder acceder a /admin ni /dashboard


================================================================================
17. CHECKLIST ANTES DE SUBIR A PRODUCCIÓN
================================================================================

[ ] Cambiar SECRETO_JWT por uno aleatorio largo.
[ ] Mover SECRETO_JWT a variable de entorno.
[ ] Cambiar URL_BASE_DATOS a Postgres/MySQL.
[ ] Activar HTTPS.
[ ] Cambiar la cookie a secure=True y samesite="strict".
[ ] Proteger o deshabilitar /docs en producción.
[ ] Añadir rate limiting en /auth/login.
[ ] Borrar el usuario demo de la base de datos.
[ ] Configurar CORS si el frontend se sirve desde otro dominio.
[ ] Verificar que __init__.py exista en todos los paquetes.


================================================================================
18. GLOSARIO
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
Dependency      Función que FastAPI ejecuta antes de una ruta
                (Depends) para inyectar recursos como la sesión de BD.
ORM             Object-Relational Mapping.
Módulo          Archivo .py que puede importarse.
Paquete         Carpeta con __init__.py que agrupa módulos.
Rol             Distinción entre admin y usuario común.
Middleware      Capa que procesa la petición antes/después de la ruta.


================================================================================
19. CONTACTO Y SOPORTE
================================================================================

Si algo se rompe:

    1. Mira la consola donde corre uvicorn → 90% de los errores aparecen ahí.
    2. Abre DevTools (F12) → Console y Network.
    3. Revisa la sección 15 (Errores comunes).
    4. Último recurso:
         - Borrar login.db
         - Borrar venv/ y recrearlo
         - Reiniciar el servidor


================================================================================
                                FIN DEL DOCUMENTO
================================================================================