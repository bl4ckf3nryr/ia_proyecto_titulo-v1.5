================================================================================
     LOGIN CON PANEL DE ADMINISTRACIÓN, SUPERVISIÓN Y CALIBRACIÓN DE IA
                          DOCUMENTACIÓN v1.4.2
================================================================================
Proyecto:   Sistema de login con roles, aislamiento por empresa, visualización
            de cámaras en directo, recuperación de contraseña simulada y
            detección de "habitación vacía / con cosas" mediante un modelo
            preentrenado de profundidad, calibrado desde una página dedicada
            (rol "learning") con herramientas de entrenamiento.
Versión:    1.4.2  (base: 1.4.1 → 1.4 → 1.6 interno)
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

NOTA SOBRE ESTE DOCUMENTO
  - Describe TODO lo que existe hoy en la aplicación, lo creado o modificado
    en las sesiones anteriores (v1.4, v1.4.1 / v1.6) y en esta sesión
    (v1.4.2: herramientas de entrenamiento del rol learning).
  - Etiquetas usadas:
      [NUEVO v1.4.2]       creado en esta sesión
      [MODIFICADO v1.4.2]  existente y cambiado en esta sesión
      [DE v1.4.1]          creado antes, sin cambios hoy
      [SIN CAMBIOS]        revisado y no tocado
      [NO REVISADO]        existe (o se infiere por imports) pero su contenido
                           no se vio; no se afirma nada de su interior
      [CONFIRMAR]          dato que el desarrollador debe verificar
  - Las rutas son relativas a la raíz del proyecto.
  - Lo que se probó de verdad y lo que no está en la sección 16.


================================================================================
ÍNDICE
================================================================================
  1.  Resumen ejecutivo y evolución de la versión
  2.  Roles, usuarios de demostración y redirecciones
  3.  Mapa completo de carpetas y archivos
  4.  Backend: main.py
  5.  Tabla completa de rutas
  6.  Calibración de la IA: cómo funciona (rol learning)
  7.  deepseek/volumen.py
  8.  deepseek/learning_api.py  [NUEVO v1.4.2]
  9.  Frontend de learning (learning.html y learning.js)  [REESCRITO v1.4.2]
  10. Frontend de supervisor (solo visualización)
  11. Capa de datos y resto del frontend
  12. Herramientas de consola en deepseek/ (piso/pared)
  13. Flujos de datos
  14. Dependencias y arranque
  15. Comandos de uso
  16. Estado verificado (qué se probó y qué no)
  17. Bitácora de problemas y soluciones
  18. Decisiones de diseño
  19. Limitaciones conocidas
  20. Observaciones de seguridad
  21. Pendientes y próximos pasos
  22. Lista de pruebas para validar la instalación
  23. Historial de versiones
  24. Glosario


================================================================================
1. RESUMEN EJECUTIVO Y EVOLUCIÓN DE LA VERSIÓN
================================================================================

1.1 Punto de partida (v1.4 y v1.4.1)
  - v1.4: login por roles (admin, supervisor, usuario), empresas,
    departamentos, cámaras con modal de visualización (HLS + MJPEG),
    detección de objetos con YOLO general (botón "Detectar objetos" del
    supervisor) y recuperación de contraseña simulada (código de 6 dígitos).
  - v1.4.1: módulo deepseek/volumen.py (profundidad + comparación con foto
    vacía), nuevo rol "learning", página /learning básica (elegir cámara,
    guardar vacía, probar, ajustar sensibilidad), lectura de frames por el
    servidor (OpenCV, RTSP por TCP). El supervisor quedó SOLO con
    visualización (sin /detectar ni /segmentar).

1.2 Objetivo de esta sesión (v1.4.2)
  Convertir la página /learning en una herramienta real de entrenamiento y
  calibración:
    - Que se detecten TODAS las cámaras registradas (activas o no).
    - Poder subir fotos de ejemplo (vacía / con cosas) desde la propia
      página, arrastrándolas o desde disco.
    - Poder capturar fotos de ejemplo directamente de la cámara.
    - Poder evaluar el acierto de los valores actuales con esos ejemplos y
      buscar automáticamente los mejores valores de sensibilidad.
    - Poder guardar el estado (cámara elegida, sensibilidad, notas por
      cámara, último entrenamiento) y recuperarlo al volver a entrar.
    - Poder descargar un respaldo (.zip) con ejemplos, fotos vacías y
      configuración.

1.3 Qué se construyó (v1.4.2)
  1) deepseek/learning_api.py [NUEVO]: router con todos los endpoints de
     herramientas de entrenamiento. Se monta desde main.py con una sola línea.
  2) templates/learning.html [REESCRITO]: página completa con 5 secciones
     (cámaras, foto vacía, fotos de ejemplo, prueba y sensibilidad, entrenar
     con los ejemplos, estado y respaldo).
  3) static/learning.js [REESCRITO]: toda la lógica del cliente.
  4) main.py [MODIFICADO]: dos líneas nuevas para incluir el router de
     learning_api. Nada más se tocó.
  5) Corrección del main.py anterior: se entregó el archivo completo con el
     import y el include_router en su sitio (después de
     learning_guardar_config y antes de "Usuario normal").

1.4 Estado en una frase
  La aplicación tiene todo el código de calibración y de entrenamiento
  entregado y revisado en sintaxis, pero la sesión terminó sin confirmar que
  /learning funciona de punta a punta en el equipo del desarrollador. Sigue
  abierto el problema reportado de que una cámara funcional "no es detectada"
  en /learning (sección 16 y 22). La lectura de la cámara 1 desde el servidor
  SÍ se verificó antes.


================================================================================
2. ROLES, USUARIOS DE DEMOSTRACIÓN Y REDIRECCIONES
================================================================================

2.1 Roles (ROLES_VALIDOS en main.py)
  admin       Gestiona usuarios y empresas. Sin empresa (empresa_id = None).
  supervisor  Gestiona departamentos y cámaras de SU empresa; solo ve/borra
              las cámaras que él mismo creó. SOLO visualización de cámaras.
  usuario     Ve el listado de cámaras activas de su empresa (/usuario/
              informes) y el dashboard.
  learning    Calibra y entrena la IA. Sin empresa (empresa_id = None). Ve
              TODAS las cámaras de todas las empresas y supervisores.

2.2 Usuarios creados al arrancar (función al_arrancar, solo si no existen)
  Empresa:   "Empresa Demo"
  admin@example.com       admin1234       rol admin       sin empresa
  supervisor@example.com  super1234       rol supervisor  Empresa Demo
  demo@example.com        demo1234        rol usuario     Empresa Demo
  learning@example.com    learning1234    rol learning    sin empresa
  Son claves de desarrollo: cambiarlas antes de producción.
  Si login.db ya existía, el usuario learning se crea igualmente al arrancar
  porque la comprobación es por correo.

2.3 Reglas al crear usuarios (POST /admin/usuarios)
  - nombre obligatorio; password mínimo 6 caracteres.
  - rol debe estar en ROLES_VALIDOS (incluye learning).
  - rol supervisor o usuario: empresa_id obligatorio y debe existir.
  - rol admin o learning: empresa_id se fuerza a None.
  - email único.
  [CONFIRMAR] templates/admin.html y static/admin.js no se revisaron: si el
  formulario del admin tiene la lista de roles escrita a mano, "learning" no
  aparecerá ahí hasta agregarlo (pendiente P16).

2.4 Redirecciones entre vistas (vistas HTML)
  GET /           login.html (público).
  GET /recuperar  recuperar.html (público).
  GET /dashboard  sin sesión → /; admin → /admin; supervisor → /supervisor;
                  learning → /learning; usuario → dashboard.html.
  GET /admin      sin sesión → /; si no es admin → /dashboard; admin →
                  admin.html.
  GET /supervisor sin sesión → /; admin → /admin; cualquier otro rol que no
                  sea supervisor → /dashboard; supervisor → supervisor.html.
  GET /learning   sin sesión → /; admin → /admin; supervisor → /supervisor;
                  usuario (cualquier otro) → /dashboard; learning →
                  learning.html.
  [CONFIRMAR] static/login.js no se revisó: tras el login redirige según el
  rol. Si no conoce "learning", el usuario puede quedar en /dashboard, que lo
  reenvía a /learning; si no ocurre, entrar directo a /learning.

2.5 Sesión
  - Cookie "access_token" (httponly, samesite=lax, path=/), expira en 60 min.
  - El token también se acepta por cabecera "Authorization: Bearer ...".
  - Para el navegador, localhost y 127.0.0.1 son sitios distintos: cada uno
    tiene su propia sesión. Usar siempre la misma dirección.
  - Una petición a un endpoint de API sin sesión responde 401 con detalle
    "Falta el token de autenticación".


================================================================================
3. MAPA COMPLETO DE CARPETAS Y ARCHIVOS
================================================================================

ia_proyecto_titulo v1.4/                      (raíz del proyecto)
|
+-- base_de_datos/                            Capa de datos (SQLAlchemy)
|   +-- __init__.py                           [NO REVISADO]
|   +-- conexion.py                           [NO REVISADO] exporta SesionLocal
|   |                                         (OJO: SesionLocal, no
|   |                                         SessionLocal), crear_tablas,
|   |                                         obtener_sesion
|   +-- modelos.py                            [NO REVISADO] ORM: usuarios,
|   |                                         empresas, departamentos y
|   |                                         camaras (CamaraORM).
|   +-- usuarios.py                           [NO REVISADO]
|   +-- empresas.py                           [NO REVISADO]
|   +-- departamentos.py                      [NO REVISADO]
|   +-- camaras.py                            [SIN CAMBIOS] ver 11.1
|
+-- deepseek/                                 Módulo de IA
|   +-- __init__.py                           [DE v1.4.1] vacío, marca paquete
|   +-- volumen.py                            [DE v1.4.1] habitación vacía vs
|   |                                         con cosas (profundidad)
|   +-- learning_api.py                       [NUEVO v1.4.2] herramientas de
|   |                                         entrenamiento/calibración
|   +-- camara.py                             [DE v1.4.1] URL desde la BD +
|   |                                         lectura de frames
|   +-- capturar.py                           [DE v1.4.1] guarda frames en el
|   |                                         dataset (consola)
|   +-- train.py                              [DE v1.4.1] entrena YOLO-seg
|   +-- predict.py                            [DE v1.4.1] inferencia piso/pared
|   +-- servicio.py                           [DE v1.4.1] puente piso/pared;
|   |                                         main.py lo importa pero ya no
|   |                                         lo usa
|   +-- data.yaml                             [DE v1.4.1] dataset piso/pared
|   +-- config_volumen.json                   [GENERADO] sensibilidad global
|   +-- estado_learning.json                  [GENERADO v1.4.2] estado de la
|   |                                         página learning (cámara elegida,
|   |                                         notas, último entrenamiento)
|   +-- entrenamiento/                        [GENERADA v1.4.2] ejemplos:
|   |   +-- cam<ID>/vacia/*.jpg               fotos de habitación vacía
|   |   +-- cam<ID>/con_cosas/*.jpg           fotos con cosas
|   +-- referencias/                          [GENERADA] fotos de habitación
|   |   +-- cam<ID>.jpg                       vacía, una por cámara
|   +-- dataset/                              [DE v1.4.1] dataset piso/pared
|   |   +-- images/train/                     fotos de prueba
|   |   +-- images/val/                       vacía
|   |   +-- labels/train/  labels/val/        vacías
|   +-- runs/piso_pared/weights/best.pt       NO existe (no se ha entrenado)
|
+-- templates/                                HTML (Jinja2)
|   +-- login.html                            [NO REVISADO]
|   +-- recuperar.html                        [NO REVISADO]
|   +-- dashboard.html                        [NO REVISADO] (rol usuario)
|   +-- admin.html                            [NO REVISADO]
|   +-- supervisor.html                       [DE v1.4.1] sin botón de IA
|   +-- learning.html                         [REESCRITO v1.4.2]
|
+-- static/
|   +-- style.css                             [NO REVISADO] CSS global
|   +-- login.js                              [NO REVISADO]
|   +-- dashboard.js                          [NO REVISADO]
|   +-- admin.js                              [NO REVISADO]
|   +-- supervisor.js                         [DE v1.4.1] sin código de IA
|   +-- learning.js                           [REESCRITO v1.4.2]
|
+-- main.py                                   [MODIFICADO v1.4.2] ver sección 4
+-- requirements.txt                          ver sección 14 [CONFIRMAR]
+-- iniciar.bat                               ver sección 14
+-- DOCUMENTACION.txt                         [NO REVISADO] documentación
|                                             antigua: árbol desactualizado
+-- DOCUMENTACION_v1.4.2.txt                  ESTE DOCUMENTO
|
+-- login.db                                  GENERADO por la app (SQLite)
+-- venv/                                     GENERADO por iniciar.bat
+-- __pycache__/                              GENERADO por Python

Archivos entregados en esta sesión y dónde van:
  main.py                -> raíz (reemplaza; incluye el import y el
                           include_router de learning_api)
  deepseek/learning_api.py -> deepseek\learning_api.py (nuevo)
  templates/learning.html  -> templates\learning.html (reemplaza)
  static/learning.js       -> static\learning.js (reemplaza)
Después de copiar: Ctrl+F5 en el navegador para no usar JS en caché.


================================================================================
4. BACKEND: main.py                               [MODIFICADO v1.4.2]
================================================================================

4.1 Arranque del archivo
  - Antes de cualquier import de cv2 se fija
    OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" (setdefault) para que
    RTSP vaya por TCP.
  - Modelo YOLO general: modelo_yolo = YOLO("yolov8n.pt") se carga al importar
    main.py. YA NO SE USA (se quitó /detectar); sigue cargándose y alarga el
    arranque. Se puede borrar cuando se quiera (limpieza opcional).
  - Imports sin uso actual: deepseek.servicio (modelo_disponible,
    segmentar_bytes), numpy, JSONResponse, listar_camaras_por_departamento.
    No molestan.
  - Imports de la calibración (v1.4.1):
      from base_de_datos.modelos import CamaraORM
      from deepseek.camara import frame_de_camara
      from deepseek.volumen import (analizar_bytes, guardar_config,
           guardar_referencia, hay_referencia, obtener_config,
           ruta_referencia)
  - Import nuevo de v1.4.2:
      from deepseek.learning_api import crear_router
  - Si deepseek/volumen.py o deepseek/learning_api.py no existen o no
    definen lo que se importa, el servidor NO arranca (ImportError).

4.2 Configuración
  SECRETO_JWT = "cambia-esto-en-produccion" (cambiar), ALGORITMO HS256,
  MINUTOS_EXPIRACION = 60, MINUTOS_RESET = 15.
  ROLES_VALIDOS = {"admin", "supervisor", "usuario", "learning"}.

4.3 Dependencias de autenticación
  usuario_actual      lee el token (cookie o Bearer), valida, devuelve usuario
                      activo o 401.
  requiere_admin      403 si rol != admin.
  requiere_supervisor 403 si rol != supervisor.
  requiere_usuario    403 si rol != usuario.
  requiere_learning   403 si rol != learning.
  verificar_empresa_del_objeto  403 si objeto.empresa_id != usuario.empresa_id.

4.4 Endpoints del supervisor (versión actual)
  Solo: listar/crear departamentos, listar/crear/borrar cámaras.
  ELIMINADOS en v1.4.1: /supervisor/camaras/{id}/detectar (YOLO general) y
  /supervisor/camaras/{id}/segmentar (piso/pared). Ya no se pueden llamar ni
  desde /docs.

4.5 Bloque learning (v1.4.1)
  Funciones auxiliares:
    _frame_jpg(camara_id)     frame_de_camara -> JPEG calidad 90 (bytes).
    _frame_servidor(id)       lo ejecuta en un hilo (run_in_threadpool). Si la
                              cámara no responde: imprime en la consola
                              "[learning] Falló la lectura de la cámara N: ..."
                              y responde 502 con un mensaje genérico (NO
                              incluye la URL, que puede llevar usuario y
                              clave).
    _camara_o_404(sesion,id)  404 "Cámara no encontrada".
  Endpoints: /learning/camaras, /learning/camaras/{id}/frame,
  /learning/camaras/{id}/referencia (GET y POST),
  /learning/camaras/{id}/probar, /learning/config (GET y PUT).

4.6 Inclusión del router de entrenamiento (v1.4.2)
  Exactamente después de learning_guardar_config y antes de la sección
  "API: Usuario normal":

      from deepseek.learning_api import crear_router  # NUEVO: herramientas
      app.include_router(crear_router(requiere_learning))

  No toca ningún endpoint existente. Añade los endpoints /learning/*
  descritos en la sección 5.3.
  ORDEN IMPORTANTE: como el router declara
  APIRouter(prefix="/learning", dependencies=[Depends(requiere_learning)]),
  todas sus rutas exigen el rol learning. No choca con las rutas /learning
  ya definidas en main.py porque los paths concretos son distintos.


================================================================================
5. TABLA COMPLETA DE RUTAS
================================================================================
MÉTODO  RUTA                                        QUIÉN / RESPUESTA
GET     /                                           público (login.html)
GET     /recuperar                                  público (recuperar.html)
GET     /dashboard                                  sesión; redirige según rol
GET     /admin                                      admin
GET     /supervisor                                 supervisor
GET     /learning                                   learning
POST    /auth/login                                 público
POST    /auth/logout                                cualquiera
GET     /auth/yo                                    sesión (401 si no hay)
POST    /auth/recuperar                             público (código simulado)
POST    /auth/restablecer                           público (código + clave)
GET     /admin/usuarios                             admin (filtro ?empresa_id=)
POST    /admin/usuarios                             admin
GET     /admin/empresas                             admin
POST    /admin/empresas                             admin
GET     /supervisor/departamentos                   supervisor
POST    /supervisor/departamentos                   supervisor
GET     /supervisor/camaras                         supervisor (solo las suyas)
POST    /supervisor/camaras                         supervisor
DELETE  /supervisor/camaras/{camara_id}             supervisor (solo las suyas)
GET     /learning/camaras                           learning
GET     /learning/camaras/{id}/frame                learning
GET     /learning/camaras/{id}/referencia           learning
POST    /learning/camaras/{id}/referencia           learning
POST    /learning/camaras/{id}/probar               learning
GET     /learning/config                            learning
PUT     /learning/config                            learning
GET     /learning/estado-camaras                    learning   [NUEVO v1.4.2]
GET     /learning/ejemplos                          learning   [NUEVO v1.4.2]
POST    /learning/ejemplos                          learning   [NUEVO v1.4.2]
POST    /learning/camaras/{id}/ejemplos/capturar    learning   [NUEVO v1.4.2]
GET     /learning/ejemplos/{cid}/{et}/{nombre}      learning   [NUEVO v1.4.2]
DELETE  /learning/ejemplos/{cid}/{et}/{nombre}      learning   [NUEVO v1.4.2]
POST    /learning/ejemplos/{cid}/vacia/{nombre}/como-vacia
                                                     learning   [NUEVO v1.4.2]
POST    /learning/camaras/{id}/probar-foto          learning   [NUEVO v1.4.2]
POST    /learning/entrenar                          learning   [NUEVO v1.4.2]
GET     /learning/estado                            learning   [NUEVO v1.4.2]
PUT     /learning/estado                            learning   [NUEVO v1.4.2]
GET     /learning/exportar                          learning   [NUEVO v1.4.2]
GET     /usuario/informes                           rol "usuario"
GET     /health                                     público
Documentación automática de FastAPI: http://localhost:8000/docs

5.1 Endpoints de calibración (v1.4.1)
  GET /learning/camaras
    200: lista de TODAS las cámaras (orden por id):
         {id, nombre, empresa_id, esta_activa, tiene_referencia}
    No devuelve url_stream.
  GET /learning/camaras/{id}/frame
    Frame leído en el servidor. 200 image/jpeg no-store; 404; 502.
  GET /learning/camaras/{id}/referencia
    Foto vacía guardada. 404 si no existe o no hay foto vacía.
  POST /learning/camaras/{id}/referencia
    Toma un frame AHORA y lo guarda como habitación vacía (reemplaza).
  POST /learning/camaras/{id}/probar
    Form opcional: umbral_diff, area_min_pct (solo para esta prueba).
    200: {camara_id, camara_nombre, hay_cosas, porcentaje, umbral_diff,
    area_min_pct, imagen (data URI JPEG base64)}.
  GET/PUT /learning/config
    Lee/guarda la sensibilidad global en deepseek/config_volumen.json.

5.2 Endpoints existentes sin cambios (resumen)
  POST /auth/login           form email, password; fija cookie.
  POST /auth/logout          borra la cookie.
  GET  /auth/yo              {usuario_id, email, nombre, rol, empresa_id}.
  POST /auth/recuperar       código de 6 dígitos (15 min) en la respuesta.
  POST /auth/restablecer     valida email + código + nueva clave (>= 6).
  GET  /usuario/informes     cámaras ACTIVAS de la empresa del usuario.
  GET  /health               {"status":"ok"}.

5.3 Endpoints de entrenamiento (v1.4.2) — todos: 401 sin sesión, 403 si el
    rol no es learning
  GET /learning/estado-camaras?verificar=0|1
    Lista TODAS las cámaras registradas con:
      {id, nombre, empresa_id, esta_activa, tiene_referencia,
       online (true/false/null), ejemplos: {vacia: N, con_cosas: N}}
    Con verificar=1 abre un frame de cada cámara (en paralelo, en hilos) y
    rellena "online". Sin verificar, online = null ("sin comprobar").
  GET /learning/ejemplos?camara_id=N
    {vacia: [nombres], con_cosas: [nombres]} (orden descendente).
  POST /learning/ejemplos
    Form: camara_id, etiqueta ("vacia"|"con_cosas"), archivos (varios).
    Cada imagen se reescala a máximo 1280 px de ancho y se guarda como JPEG.
    200: {guardadas, invalidas}.
  POST /learning/camaras/{id}/ejemplos/capturar
    Form: etiqueta, cantidad (1-10), pausa (0.5-30 s).
    Guarda frames de la cámara con prefijo cam_. 200: {guardadas}.
  GET /learning/ejemplos/{cid}/{et}/{nombre}
    Devuelve el JPEG del ejemplo (no-store).
  DELETE /learning/ejemplos/{cid}/{et}/{nombre}
    Borra el ejemplo. 200: {"mensaje":"Ejemplo borrado"}.
  POST /learning/ejemplos/{cid}/vacia/{nombre}/como-vacia
    Usa ese ejemplo como foto vacía de la cámara (reemplaza la referencia).
  POST /learning/camaras/{id}/probar-foto
    Form: archivo (UploadFile) O etiqueta+nombre (ejemplo guardado), y
    opcionalmente umbral_diff, area_min_pct.
    Devuelve el mismo JSON que /probar.
  POST /learning/entrenar
    Form: modo ("evaluar"|"buscar"), camara_id (opcional; vacío = todas),
    umbral_diff, area_min_pct (opcionales).
    Evalúa los ejemplos guardados con los valores dados (evaluar) o prueba
    varias sensibilidades y elige la mejor (buscar). Devuelve:
      {modo, umbral_diff, area_min_pct, precision, total, matriz: {tp, tn,
       fp, fn}, tabla: [{umbral, area, precision}] (solo en buscar),
       detalle: [{camara_id, etiqueta, nombre, porcentaje, acierto}]}
    Límite: usa como máximo los últimos 40 ejemplos y, al buscar, las
    sensibilidades [0.08, 0.12, 0.16, 0.22, 0.30] (para que no tarde
    demasiado).
  GET /learning/estado
    Devuelve el JSON guardado en deepseek/estado_learning.json (o {}).
  PUT /learning/estado
    Form: datos (string JSON, máximo 200 KB, debe ser un objeto).
    Añade "guardado" con la fecha y hora y lo escribe en disco.
  GET /learning/exportar
    Descarga un .zip con deepseek/entrenamiento/**, deepseek/referencias/**,
    config_volumen.json y estado_learning.json.


================================================================================
6. CALIBRACIÓN DE LA IA: CÓMO FUNCIONA (ROL LEARNING)
================================================================================

6.1 Idea
  El modelo Depth Anything V2 Small ya viene entrenado y calcula, a partir de
  UNA foto, qué tan lejos está cada punto de la imagen (profundidad RELATIVA,
  no en metros). Para saber si la habitación "tiene cosas" se compara el mapa
  de profundidad de la foto actual contra el de una foto de la habitación
  VACÍA. Donde la profundidad cambia, hay algo.
  No hace falta etiquetar ni entrenar. "Calibrar" = (a) guardar la foto vacía
  de cada cámara y (b) ajustar la sensibilidad. "Entrenar" en esta página =
  medir el acierto con ejemplos y buscar los mejores valores.

6.2 Requisito: cámara fija
  La foto vacía solo sirve si la cámara está siempre en el mismo lugar y
  ángulo. Si se mueve, hay que guardar otra foto vacía. La luz también debe
  ser parecida.

6.3 Flujo completo en /learning (v1.4.2)
  1) Entrar a /learning con learning@example.com.
  2) En "Cámaras registradas" aparecen TODAS las cámaras (activas o no), con
     chips: en línea / sin conexión / sin comprobar, calibrada / sin foto
     vacía, y el número de ejemplos vacía / con cosas.
     "Comprobar conexión de todas" verifica en paralelo cuáles responden; al
     entrar también se comprueban solas en segundo plano.
  3) Elegir una cámara: se cargan la imagen actual, la foto vacía guardada y
     la galería de ejemplos.
  4) Sección "1. Foto de la habitación vacía": con la habitación SIN nada,
     revisar la imagen actual y pulsar "Guardar como vacía". Queda en
     deepseek\referencias\cam<ID>.jpg.
  5) Sección "2. Fotos de ejemplo": elegir si son "vacía" o "con cosas";
     arrastrar fotos o seleccionarlas, o capturarlas de la cámara (1 a 10,
     con pausa). La galería permite:
       - Probar una foto contra la foto vacía.
       - Usar una foto "vacía" como referencia de la habitación.
       - Borrar.
  6) Sección "3. Prueba y sensibilidad": probar con la cámara en vivo o con
     una foto propia, mover los dos deslizadores y "Guardar sensibilidad".
     El resultado muestra si hay cosas, el porcentaje de imagen cambiado y la
     imagen con las zonas distintas en rojo.
  7) Sección "4. Entrenar con los ejemplos":
       - "Evaluar con los valores actuales": mide el acierto con los ejemplos
         guardados y muestra la matriz de aciertos/errores.
       - "Buscar mejores valores": prueba varias sensibilidades, propone la
         mejor y ofrece "Aplicar y guardar sugeridos".
       - Alcance: solo la cámara elegida o todas las cámaras calibradas.
  8) Sección "5. Estado y respaldo": el estado (cámara elegida, sensibilidad,
     notas por cámara, último entrenamiento) se guarda solo en el servidor y
     se recupera al volver a entrar. Botones para guardar a mano y para
     descargar el respaldo (.zip).

6.4 Qué significan los ajustes
  Umbral de profundidad (umbral_diff, por defecto 0.15): cuánto debe cambiar
    la profundidad normalizada (0 a 1) para marcar un píxel como distinto.
    Más alto = ignora cambios pequeños (sombras, luz). Más bajo = detecta
    objetos más planos.
  Área mínima (area_min_pct, por defecto 1.5 %): porcentaje mínimo de la
    imagen cambiada para decir "hay cosas". Más alto = solo objetos grandes.
    Más bajo = detecta objetos chicos.
  Rangos que acepta el servidor: umbral 0.02 a 0.60; área 0.1 a 50. Los
  deslizadores de la página cubren 0.02–0.60 y 0.1–20.

6.5 Para qué sirve después
  Hoy la calibración y las herramientas de entrenamiento dejan listo el
  análisis, pero NADA lo ejecuta de forma automática ni lo muestra en el
  dashboard del usuario "demo" todavía (pendiente, sección 21). Los puntos de
  uso actuales son la prueba y el entrenamiento de /learning.


================================================================================
7. deepseek/volumen.py                                [DE v1.4.1]
================================================================================
Constantes
  CARPETA_REF      deepseek/referencias/
  ARCHIVO_CONFIG   deepseek/config_volumen.json
  MODELO_ID        "depth-anything/Depth-Anything-V2-Small-hf"
  ANCHO            640 (las imágenes se reducen a 640 px de ancho)
  CONFIG_POR_DEFECTO  umbral_diff 0.15, area_min_pct 1.5

Funciones públicas
  obtener_config() -> dict
    Lee config_volumen.json en cada llamada (sin caché). Si no existe o está
    dañado, usa los valores por defecto.
  guardar_config(umbral_diff, area_min_pct) -> dict
    Valida rangos (ValueError si no) y escribe el JSON.
  ruta_referencia(camara_id) -> Path       deepseek/referencias/cam<ID>.jpg
  hay_referencia(camara_id) -> bool
  guardar_referencia(camara_id, contenido: bytes)
    Decodifica (ValueError si la imagen no es válida), reduce a 640 de ancho y
    guarda el JPEG; crea la carpeta si falta.
  analizar_bytes(camara_id, contenido, umbral_diff=None, area_min_pct=None)
    Si faltan umbrales usa los guardados. Algoritmo:
      1. Carga la foto vacía y reduce la actual a su mismo tamaño.
      2. Calcula la profundidad de ambas con el modelo (normalizada 0-1).
      3. _alinear(): la profundidad es relativa, así que ajusta la escala de
         la actual a la de referencia por mínimos cuadrados, 3 iteraciones,
         ignorando el 20 % de píxeles que más difieren.
      4. Diferencia absoluta + desenfoque gaussiano (9x9), umbral y apertura
         morfológica (7x7) para quitar ruido.
      5. porcentaje = píxeles distintos / total * 100.
      6. Imagen: zonas distintas pintadas de rojo con 50 % de transparencia,
         JPEG calidad 85 en base64 (data URI).
    Devuelve {hay_cosas, porcentaje (1 decimal), umbral_diff, area_min_pct,
    imagen}. hay_cosas = porcentaje >= area_min_pct.
    FileNotFoundError si no hay foto vacía.

Carga del modelo
  _pipe() usa lru_cache(1) y un import perezoso de transformers: el servidor
  arranca igual aunque el modelo no se haya descargado. La PRIMERA vez que se
  usa descarga unos 100 MB de Hugging Face (requiere internet) y tarda; luego
  queda en caché del usuario y es más rápido.
Licencia: Depth Anything V2 Small es Apache-2.0 (uso comercial permitido).
Requiere: transformers, Pillow (PIL), OpenCV, NumPy.


================================================================================
8. deepseek/learning_api.py                           [NUEVO v1.4.2]
================================================================================
Archivo nuevo con las herramientas de entrenamiento. No modifica los
endpoints existentes. Se monta desde main.py (sección 4.6).

8.1 Estructura de datos en disco
  DATOS  = deepseek/entrenamiento/
      cam<ID>/vacia/*.jpg          fotos de habitación vacía
      cam<ID>/con_cosas/*.jpg      fotos con cosas
  ESTADO = deepseek/estado_learning.json
      {camara_id, umbral_diff, area_min_pct, notas: {"<id>": "texto"},
       ultimo_entrenamiento: {modo, precision, total, umbral_diff,
       area_min_pct, fecha}, guardado: "AAAA-MM-DD HH:MM:SS"}
  Etiquetas válidas: ("vacia", "con_cosas"). Cualquier otra da 400.

8.2 Funciones internas (todas con nombres en minúsculas, sin tildes en el
    código para evitar problemas de codificación)
  _carpeta(cid, et)        valida la etiqueta y devuelve DATOS/cam<ID>/<et>.
  _nombre_ok(n)            exige ^[\w\-.]+\.jpg$ y prohíbe ".." (path
                           traversal). 400 si no cumple.
  _a_jpg(contenido)        decodifica con OpenCV, reduce a 1280 px de ancho
                           máximo y devuelve JPEG calidad 90. ValueError si
                           la imagen no es válida.
  _frame(cid)              frame_de_camara -> JPEG. 502 genérico si falla
                           (el detalle, que puede traer la URL, va a consola).
  _ping(cid)               True/False: se pudo leer un frame.
  _guardar(cid, et, jpg, prefijo)
                           guarda con nombre prefijo_AAAAMMDD_HHMMSS_xxxx.jpg
                           y devuelve el nombre.
  _analizar(cid, jpg, u, a)
                           llama a analizar_bytes y traduce errores:
                             FileNotFoundError -> 409 "Primero guarda una foto
                               de la habitación vacía"
                             OSError -> 503 "No se pudo cargar el modelo de
                               profundidad"
                             ValueError -> 400
  _entrenar(cids, modo, u0, a0)
                           núcleo del entrenamiento (ver 8.3).

8.3 Cómo entrena _entrenar
  1. Lee la configuración actual (obtener_config).
  2. Recoge los ejemplos de las cámaras indicadas que tengan foto vacía:
     pares (camara_id, etiqueta, archivo).
  3. Se queda con los últimos 40 ejemplos (para limitar el tiempo).
  4. Si no hay ejemplos o, al buscar, no hay al menos una etiqueta de cada
     clase, responde 400 con un mensaje claro.
  5. Calcula el porcentaje de cambio de cada foto una vez por umbral
     (en modo buscar: 5 umbrales; en evaluar: solo el actual). Guarda esos
     porcentajes en memoria para no recalcular la profundidad.
  6. Prueba áreas candidatas:
       - evaluar: solo el área actual (o la que envíe el cliente).
       - buscar: 0.1, todos los porcentajes observados y los puntos medios
         entre ellos consecutivos (redondeado y acotado a 0.1–50).
  7. Elige la combinación con mejor precisión; en empate, la que tenga mayor
     margen (distancia mínima entre un porcentaje observado y el área).
  8. Devuelve el JSON descrito en la sección 5.3, con matriz de confusión
     (tp, tn, fp, fn) y detalle foto a foto (acierto sí/no).

  ¿Qué significa tp/tn/fp/fn aquí?
    tp: tenía cosas y dijo "hay cosas".   tn: vacía y dijo "vacía".
    fp: vacía pero dijo "hay cosas".      fn: tenía cosas pero dijo "vacía".

8.4 Router
  def crear_router(requiere_learning):
      r = APIRouter(prefix="/learning",
                    dependencies=[Depends(requiere_learning)])
      ...
      return r

  Toma requiere_learning como parámetro para no importar main.py (evita
  import circular). Todos los endpoints del router exigen rol learning.

8.5 Seguridad del router
  - No devuelve url_stream en ningún sitio.
  - Los nombres de archivo se validan con _nombre_ok (sin "..", solo .jpg).
  - El estado se limita a 200 KB y debe ser un objeto JSON.
  - El zip de exportación se genera en memoria (io.BytesIO) y solo incluye
    las carpetas de datos y los JSON de configuración/estado.


================================================================================
9. FRONTEND DE LEARNING (learning.html y learning.js)  [REESCRITO v1.4.2]
================================================================================

9.1 templates/learning.html
  Carga /static/style.css y un bloque <style> con clases propias l-* (se
  mantuvieron dentro del HTML para no tocar style.css, que no se revisó).
  Estructura:
    Cabecera: título "Calibración de la IA", nombre del usuario
              (#learning-info) y botón "Cerrar sesión" (#logout-btn).
    Tarjeta "Cámaras registradas":
              botón "Comprobar conexión de todas" (#btn-escanear), contenedor
              #camaras, mensajes #msg.
    Sección 1 "Foto de la habitación vacía":
              imagen actual #img-actual, botones #btn-frame ("Actualizar
              imagen") y #btn-vacia ("Guardar como vacía"), foto vacía
              guardada #img-ref y estado #ref-estado.
    Sección 2 "Fotos de ejemplo":
              selector de etiqueta #ej-etiqueta (vacía / con cosas), zona de
              arrastre #zona con input #ej-archivos, botón #btn-capturar,
              #cap-cant, #cap-pausa, conteo #ej-conteo y galería #galeria.
    Sección 3 "Prueba y sensibilidad":
              deslizadores #umbral (0.02–0.60) y #area (0.1–20) con valores en
              #umbral-val y #area-val, botones #btn-probar ("Probar con la
              cámara") y #btn-guardar-config ("Guardar sensibilidad"), input
              #prueba-archivo y contenedor #resultado.
    Sección 4 "Entrenar con los ejemplos":
              selector #ent-alcance (solo la cámara / todas las calibradas),
              botones #btn-evaluar, #btn-buscar, #btn-aplicar (oculto hasta
              que hay sugerencia), contenedor #ent-resultado.
    Sección 5 "Estado y respaldo":
              textarea #notas, botón #btn-guardar-estado, enlace de descarga
              /learning/exportar, texto #estado-info.
  Carga /static/learning.js al final.

9.2 static/learning.js
  - Utilidades: $ (getElementById), esc (escapa HTML), api (fetch con
    credentials:"include"; 401 -> "/"), j (JSON), fd (FormData), msg
    (mensajes de estado en #msg) e imagen (pide una imagen con fetch, la
    muestra con object URL y libera las anteriores; si falla, devuelve el
    mensaje de error para mostrarlo).
  - Arranque:
      1. GET /auth/yo. Si el rol no es learning -> /dashboard.
      2. GET /learning/config para los sliders (si falla, 0.15 y 1.5).
      3. GET /learning/estado para notas, último entrenamiento y valores.
      4. cargarCamaras(false) y seleccionar la cámara guardada (o la
         primera).
      5. cargarCamaras(true) en segundo plano para comprobar conexiones.
  - Cámaras: pinta una tarjeta por cámara con chips de estado. Se comprueban
    todas en paralelo en el servidor (verificar=1).
  - Al seleccionar: carga frame, referencia y ejemplos; guarda estado (con
    retardo de 800 ms para no escribir en cada clic).
  - Fotos de ejemplo: subida por input o arrastrando; captura de la cámara
    (cantidad y pausa); galería con "Probar", "Usar como vacía" y "Borrar".
  - Prueba: envía los sliders actuales (sin guardarlos) a /probar o
    /probar-foto y muestra el resultado (título, porcentaje, imagen roja).
  - Entrenar: llama a /entrenar con modo evaluar o buscar; muestra precisión,
    matriz, tabla de sensibilidades (solo en buscar) y detalle por foto. En
    buscar habilita "Aplicar y guardar sugeridos", que pone los sliders y
    llama a PUT /learning/config.
  - Estado: se guarda solo en el servidor (camara_id, umbral_diff,
    area_min_pct, notas, ultimo_entrenamiento). Botón para guardar a mano.
    El enlace /learning/exportar descarga el zip.
  - Logout: POST /auth/logout y vuelve a "/".
  - Todos los textos que vienen del servidor se escapan con esc() antes de
    insertarlos en el HTML.


================================================================================
10. FRONTEND DE SUPERVISOR (SOLO VISUALIZACIÓN)       [DE v1.4.1]
================================================================================

10.1 templates/supervisor.html
  - Sección Departamentos: formulario #crear-departamento-form, lista
    #lista-departamentos.
  - Sección Cámaras: formulario #crear-camara-form (nombre, URL del stream
    input type="url", departamento), tabla #tabla-camaras, botón "Refrescar".
  - Modal #modal-camara: <video id="modal-video">, <img id="modal-img">
    (fallback MJPEG), #modal-error y #modal-url. Sin botón "Detectar objetos".
  - Carga hls.js 1.x desde jsdelivr (solo para .m3u8) y /static/supervisor.js.

10.2 static/supervisor.js
  - Verifica sesión con /auth/yo: admin -> /admin; usuario -> /dashboard.
  - Carga departamentos y cámaras, crea departamentos y cámaras, borra
    cámaras (con confirmación). Cada fila tiene "Ver" y "Borrar".
  - abrirModalCamara(): según la URL:
      rtsp://   aviso: el navegador no reproduce RTSP.
      .m3u8     hls.js.
      http(s)   <video>; si no carga en 2,5 s, cae a <img> (MJPEG).
  - Escapa el HTML de los datos mostrados (escapeHtml).


================================================================================
11. CAPA DE DATOS Y RESTO DEL FRONTEND
================================================================================

11.1 base_de_datos/camaras.py  (revisado completo, sin cambios)
  crear_camara(sesion, nombre, url_stream, empresa_id, departamento_id,
               usuario_id=None, esta_activa=True) -> CamaraORM
      Limpia espacios (strip) de nombre y url_stream.
  obtener_por_id(sesion, camara_id) -> Optional[CamaraORM]
  listar_por_empresa / listar_por_usuario / listar_por_departamento
  actualizar_camara(sesion, camara_id, **campos)
  Campos de CamaraORM: id, nombre, url_stream, empresa_id, departamento_id,
  usuario_id (supervisor que la creó), esta_activa.
  No hay función de borrado: main.py borra con sesion.delete(camara).
  No hay función para listar TODAS las cámaras: los endpoints /learning
  consultan CamaraORM directamente.

11.2 Lo que no se vio en ninguna de las sesiones
  conexion.py, modelos.py (en particular el tipo de la columna "rol"),
  usuarios.py, empresas.py, departamentos.py, login.html, recuperar.html,
  dashboard.html, admin.html, style.css, login.js, dashboard.js, admin.js.
  [CONFIRMAR] si la columna "rol" tiene una restricción (Enum o CHECK) que
  impida el valor "learning", el usuario learning no se creará al arrancar y
  se verá el error en la consola.


================================================================================
12. HERRAMIENTAS DE CONSOLA EN deepseek/ (PISO/PARED)  [DE v1.4.1]
================================================================================
Siguen existiendo pero NO están expuestas en la web desde que se quitaron
/segmentar y el botón del supervisor. Se ejecutan desde la raíz del proyecto
con el Python del venv. No aplican control de roles: usar solo en el equipo
del desarrollador.

  camara.py
    Fija OPENCV_FFMPEG_CAPTURE_OPTIONS (RTSP por TCP) y agrega la raíz a
    sys.path.
    url_de_camara(camara_id) -> url_stream desde la BD (ValueError si no
      existe).
    leer_frame(url, descartar=5) -> frame BGR (lee 5 frames y se queda con el
      último). RuntimeError "No se pudo abrir el stream" o "El stream abrió
      pero no entregó imagen".
    frame_de_camara(camara_id) -> atajo de las dos anteriores.
    Lo usa main.py (endpoints de learning): abre y cierra el stream en cada
    petición.
  capturar.py
    python deepseek\capturar.py <id> [--cantidad N] [--cada S]
    Guarda frames en deepseek\dataset\images\train\ con nombre
    cam<ID>_<AAAAMMDD>_<HHMMSS>.jpg. Sirve también para comprobar que el
    servidor lee una cámara (probado con la cámara 1).
  train.py
    Entrena yolov8n-seg (epochs 100, imgsz 640, batch 8, workers 2) con
    data.yaml (clases 0=piso, 1=pared). Resultado en
    deepseek\runs\piso_pared\weights\best.pt.
  predict.py
    python deepseek\predict.py ruta\imagen.jpg  |  --camara <id>
    Segmenta piso/pared/otro y guarda <nombre>_resultado.png.
  servicio.py
    Puente hacia FastAPI (modelo_disponible, segmentar_bytes). main.py aún lo
    importa pero ya no lo usa.
  data.yaml
    path dataset; train images/train; val images/val; names 0 piso, 1 pared.

Estado del dataset: images/train tiene 2 fotos de prueba de la cámara 1;
labels y val están vacíos; no hay modelo entrenado. Con el enfoque de
profundidad (sección 6) este camino queda como alternativa opcional.


================================================================================
13. FLUJOS DE DATOS
================================================================================

13.1 Cómo viaja la URL de la cámara
  Alta: el supervisor escribe la URL en "URL del stream" -> supervisor.js
  envía POST /supervisor/camaras (form-data) -> main.py valida departamento y
  empresa y llama a crear_camara() -> se guarda en la columna url_stream de
  login.db.

13.2 Visualización (supervisor)
  El navegador reproduce la URL directamente (video o imagen MJPEG). El
  servidor no interviene. RTSP no se puede ver en el navegador.

13.3 Calibración y prueba (learning)
  Navegador (/learning) -> GET .../frame -> main.py llama frame_de_camara(id)
  -> camara.py lee la url_stream de la BD y abre el stream con OpenCV -> el
  frame vuelve como JPEG. El navegador NUNCA recibe ni usa la URL de la cámara.
  Guardar vacía: POST .../referencia -> frame del servidor ->
  guardar_referencia -> deepseek\referencias\cam<ID>.jpg.
  Probar: POST .../probar -> frame del servidor -> analizar_bytes (en hilo
  aparte) -> JSON con resultado e imagen.
  Sensibilidad: PUT /learning/config -> deepseek\config_volumen.json.

13.4 Entrenamiento (v1.4.2)
  Ejemplos: POST /learning/ejemplos (subida) o .../capturar -> archivos JPEG
  en deepseek\entrenamiento\cam<ID>\{vacia,con_cosas}\.
  Evaluar/buscar: POST /learning/entrenar -> learning_api lee esos archivos,
  llama a analizar_bytes por cada foto y umbral (en un hilo aparte, no bloquea
  FastAPI) y devuelve el resumen. El servidor recalcula la profundidad en cada
  llamada: por eso está limitado a 40 fotos y 5 sensibilidades.
  Estado: PUT /learning/estado -> deepseek\estado_learning.json.
  Respaldo: GET /learning/exportar -> zip en memoria con entrenamiento,
  referencias y los dos JSON.

13.5 Por qué el servidor lee la cámara y no el navegador
  - Funciona con RTSP.
  - Evita el bloqueo CORS del canvas con streams de otra IP.
  - El rol learning no necesita ver ni abrir la URL.


================================================================================
14. DEPENDENCIAS Y ARRANQUE
================================================================================

14.1 requirements.txt
  Contenido conocido (v1.4.1, 272 bytes):
    fastapi==0.115.0
    uvicorn[standard]==0.32.0
    jinja2==3.1.4
    pydantic[email]==2.9.2
    bcrypt==4.2.0
    PyJWT==2.9.0
    sqlalchemy==2.0.35
    python-multipart==0.0.12
    ultralytics>=8.3.0,<9.0.0
    opencv-python-headless>=4.10.0.84,<5.0.0
    numpy>=1.26.4,<2.0.0
  v1.4.2 no añade dependencias nuevas: usa asyncio, io, json, re, time,
  uuid, zipfile y Path (todas de la librería estándar) además de las ya
  instaladas (cv2, numpy, fastapi, starlette).
  v1.4.1 ya requería: transformers>=4.45.0  [CONFIRMAR que se agregó e
  instaló]. Pillow (PIL) lo trae ultralytics. Los comentarios van con "#";
  un "//" hace fallar pip.

14.2 iniciar.bat
  Detecta/instala Python 3.11-3.13, crea el venv, instala desde
  requirements.txt, verifica la estructura (main.py, requirements.txt,
  base_de_datos\) y levanta uvicorn con --reload en el puerto 8000.
  IMPORTANTE: en la última ejecución mostró "Dependencias ya presentes y
  funcionales" y NO instaló nada nuevo, así que transformers puede no estar
  instalado. Instalar a mano:
    venv\Scripts\python.exe -m pip install "transformers>=4.45.0"
  Con --reload, cualquier cambio en un .py reinicia el servidor. Las fotos, el
  config_volumen.json y el estado_learning.json que se generan no son .py y
  no lo reinician.


================================================================================
15. COMANDOS DE USO
================================================================================
Arrancar: doble clic en iniciar.bat
  (equivale a: venv\Scripts\python.exe -m uvicorn main:app --reload
   --host 127.0.0.1 --port 8000)
  Servidor http://localhost:8000   Docs /docs   Health /health
Entrar a la calibración: http://localhost:8000 -> learning@example.com /
  learning1234 -> /learning  (o directo http://localhost:8000/learning).
Comprobar que el servidor lee una cámara (con el venv activado, desde la raíz):
    python deepseek\capturar.py 1 --cantidad 1
  Cambiar el 1 por el id de la cámara. NO escribir "capturar.py 1 ..." solo
  (PowerShell no lo reconoce) y NO poner la ruta entre comillas dobles dentro
  de comillas simples.
Activar el venv en PowerShell:
    (Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ;
    (& ".\venv\Scripts\Activate.ps1")
Siempre ejecutar desde la raíz para que "sqlite:///./login.db" encuentre la
base de datos correcta.


================================================================================
16. ESTADO VERIFICADO
================================================================================
PROBADO Y FUNCIONANDO
  [OK] Lectura de la cámara 1 desde el servidor: capturar.py guardó
       cam1_20261106_232145.jpg y cam1_20261107_184708.jpg.
  [OK] Sintaxis de main.py y volumen.py (análisis de Python) y de
       supervisor.js y learning.js (node --check) en la sesión de v1.4.1.
  [OK] Estructura del proyecto con iniciar.bat hasta el paso 5/6 (v1.4).
  [OK] Se comprobó que supervisor.js ya no contiene referencias a detección y
       que main.py ya no tiene rutas /detectar ni /segmentar.
  [OK] Los tres archivos de v1.4.2 (learning_api.py, learning.html,
       learning.js) se entregaron completos y se revisó su sintaxis en la
       sesión de entrega.
  [OK] Se revisó main.py contra learning_api.py: los nombres usados
       (requiere_learning, obtener_sesion, CamaraORM, frame_de_camara) y los
       paths de los endpoints no chocan con los existentes.

PROBLEMA OCURRIDO Y RESUELTO
  El arranque falló con "ImportError: cannot import name 'analizar_bytes' from
  'deepseek.volumen'": el volumen.py de la carpeta no tenía las funciones
  nuevas. Se entregó un volumen.py completo para reemplazarlo.
  En esta sesión se detectó otro despiste: el main.py entregado inicialmente
  no incluía el import ni el include_router de learning_api; se entregó el
  main.py completo corregido.

NO PROBADO TODAVÍA (al cerrar esta documentación)
  [ ] Arranque del servidor con main.py, volumen.py y learning_api.py
      nuevos.
  [ ] Que el usuario learning se cree (puede fallar si la columna "rol" tiene
      restricciones).
  [ ] Login con learning y redirección a /learning.
  [ ] Que /learning/estado-camaras liste TODAS las cámaras.
  [ ] Subida de ejemplos (input y arrastre), captura desde la cámara, borrado
      y "usar como vacía".
  [ ] Probar con foto propia y con ejemplo guardado.
  [ ] Evaluar y buscar mejores valores; aplicar y guardar la sugerencia.
  [ ] Guardado y recuperación del estado; descarga del zip.
  [ ] Descarga del modelo de profundidad y primera inferencia.
  [ ] Instalación de transformers.

PROBLEMA ABIERTO REPORTADO POR EL DESARROLLADOR
  "Hay una cámara funcional pero no es detectada" en /learning. No se
  identificó si es (A) que no aparece en la lista de cámaras o (B) que
  aparece pero da error al leer. La nueva página facilita el diagnóstico:
  "Comprobar conexión de todas" marca cada cámara como en línea / sin
  conexión, y el mensaje de error de la imagen actual es explícito. Pasos
  completos en la sección 22.


================================================================================
17. BITÁCORA DE PROBLEMAS Y SOLUCIONES
================================================================================
1) SessionLocal vs SesionLocal (v1.4.1)
   conexion.py exporta SesionLocal. Se usó ese nombre en camara.py y main.py.
2) "cannot import name 'leer_frame' from 'camara'" (v1.4.1)
   Se había reemplazado camara.py con un fragmento. Debe tener las tres
   funciones (url_de_camara, leer_frame, frame_de_camara).
3) Comandos mal escritos en PowerShell (v1.4.1 y v1.4.2)
   Usar "python deepseek\capturar.py <id> ...".
4) SystemExit dentro del servidor (v1.4.1)
   buscar_modelo ahora lanza FileNotFoundError.
5) Comentario "//" en requirements.txt (v1.4.1)
   pip no lo entiende; usar "#".
6) ImportError analizar_bytes (v1.4.1)
   volumen.py incompleto/antiguo; reemplazado por la versión completa.
7) "Falta el token de autenticación" al abrir /learning/camaras (v1.4.1)
   No es un fallo de la cámara: el navegador no tenía sesión en esa dirección.
   Iniciar sesión y usar siempre la misma dirección (localhost o 127.0.0.1).
8) iniciar.bat no instala paquetes nuevos (v1.4.1)
   "Dependencias ya presentes y funcionales": instalar transformers a mano.
9) Cámara "no detectada" en learning (v1.4.1): ABIERTO (secciones 16 y 22).
10) main.py entregado sin el import/include_router de learning_api (v1.4.2)
   Se corrigió entregando el main.py completo. Si learning_api.py no existe,
   el servidor no arranca por ImportError: copiar primero el archivo.
11) Los estilos l-* quedaron dentro de learning.html (v1.4.2)
   Se hizo así para no tocar style.css, que no se ha visto. Si se quiere
   respetar la regla de un solo CSS, moverlos al final de static/style.css.


================================================================================
18. DECISIONES DE DISEÑO
================================================================================
- Modelo de profundidad PREENTRENADO + comparación con habitación vacía, en
  lugar de entrenar clases: sirve para "cualquier cosa" 3D sin etiquetar, y
  YOLO general solo conoce 80 clases (no ve cajas o bultos genéricos).
- Depth Anything V2 SMALL por licencia Apache-2.0 y bajo peso (~100 MB).
- La calibración y el entrenamiento los hace un rol aparte (learning); el
  supervisor solo ve cámaras. Se retiró del supervisor todo "poder" de IA,
  incluidos los endpoints.
- learning ve TODAS las cámaras (sin filtro por empresa ni por supervisor) y
  no necesita ser dueño de ellas.
- La URL de la cámara no se envía a learning (puede llevar credenciales); el
  servidor la usa internamente.
- El servidor lee el frame (OpenCV) y no el navegador: soporta RTSP y evita
  CORS.
- Sensibilidad GLOBAL (un solo config_volumen.json para todas las cámaras) y
  editable en vivo sin reiniciar; la prueba permite usar valores sin guardar.
- Foto vacía POR CÁMARA en deepseek/referencias/cam<ID>.jpg.
- "Entrenar" en esta aplicación significa calibrar y ajustar sensibilidad,
  no reentrenar la red: la red ya viene entrenada.
- Los ejemplos se guardan en disco por cámara y etiqueta, no en la base de
  datos, para no tocar el esquema de SQLite.
- El estado de la página se guarda en un JSON aparte (no en login.db) y se
  limita a 200 KB.
- El router de learning_api se monta con una única llamada y recibe
  requiere_learning como parámetro para no crear import circular con main.py.
- El entrenamiento se limita a 40 fotos y 5 sensibilidades para que no tarde
  demasiado, porque recalcula la profundidad en cada llamada (no hay caché).
- La exportación del respaldo se genera en memoria y solo incluye datos y
  JSON de configuración/estado (nunca login.db).
- Frontend con HTML/CSS/JS puro, igual que el resto de la aplicación.


================================================================================
19. LIMITACIONES CONOCIDAS
================================================================================
- Requiere cámara FIJA; si se mueve hay que guardar otra foto vacía.
- Cambios fuertes de luz, sombras o reflejos pueden dar falsos positivos.
- La profundidad desde una sola imagen es RELATIVA; por eso se alinea la
  escala antes de comparar. Objetos muy planos (una hoja) o del mismo plano
  que el piso pueden no detectarse.
- La primera inferencia es lenta (descarga del modelo; requiere internet).
- HLS (.m3u8) puede no leerse bien con OpenCV. RTSP se lee por TCP.
- Cada petición a /frame o /probar abre y cierra el stream de la cámara.
- Todo es manual por ahora: no hay análisis automático ni historial.
- "Buscar mejores valores" es lento: recalcula la profundidad en cada
  llamada. Limitado a 40 fotos y 5 sensibilidades. Se puede acelerar
  guardando en caché la profundidad (necesitaría revisar volumen.py).
- No hay importación del respaldo (solo exportación).
- La sensibilidad es global, no por cámara.
- No hay botón para borrar la foto vacía desde la página.
- Una cámara borrada por el supervisor NO borra su foto vacía en
  deepseek/referencias ni sus ejemplos en deepseek/entrenamiento. SQLite
  puede reutilizar un id si se borra la última cámara: una cámara nueva con
  ese id heredaría fotos ajenas. [CONFIRMAR según si la tabla usa
  AUTOINCREMENT]. Conviene borrar cam<ID>.* al borrar una cámara (pendiente).
- El navegador no reproduce RTSP en el modal del supervisor (solo aviso).
- main.py sigue cargando yolov8n.pt aunque no se use (arranque más lento).
- login.db debe encontrarse desde el directorio de trabajo (ejecutar desde la
  raíz).
- Los estilos l-* de learning.html están dentro del HTML (no en style.css).


================================================================================
20. OBSERVACIONES DE SEGURIDAD
================================================================================
- SECRETO_JWT conserva el valor por defecto "cambia-esto-en-produccion".
  Cambiarlo (idealmente por variable de entorno).
- Las URLs de cámara pueden llevar usuario y clave (rtsp://usuario:clave@...)
  y se guardan en TEXTO PLANO en login.db.
- GET /usuario/informes devuelve url_stream de las cámaras activas de la
  empresa al rol "usuario": si la URL lleva credenciales, quedan expuestas.
- Mejora: /learning/camaras y /learning/estado-camaras no devuelven
  url_stream, y los errores de lectura no incluyen la URL en la respuesta.
- Los mensajes de error de leer_frame (consola) incluyen la URL completa: no
  compartir esa salida sin ocultar credenciales.
- El rol learning ve las cámaras de todas las empresas por diseño: asignarlo
  solo a personal de confianza. Las fotos de deepseek/referencias y
  deepseek/entrenamiento son imágenes de las habitaciones: no subirlas a
  repositorios (agregar ambas carpetas a .gitignore).
- Se quitó del supervisor la capacidad de usar IA (endpoints incluidos).
- El código de recuperación se devuelve en la respuesta (simulado, sin
  email): solo apto para demo.
- La cookie de sesión no tiene el atributo "secure" (se asume http local).
- No hay límite de intentos de login.
- Credenciales de demostración (admin1234, super1234, demo1234,
  learning1234): solo para desarrollo.
- login.db contiene usuarios y hashes: no subirlo a repositorios ni a chats.
- /docs está abierto; deshabilitarlo en producción si se desea.
- Los scripts de deepseek/ no aplican roles: ejecutarlos solo en el equipo del
  desarrollador.
- Los nombres de archivo de los ejemplos se validan (_nombre_ok): sin ".." y
  solo .jpg, para evitar path traversal.
- El estado guardado se limita a 200 KB y debe ser un objeto JSON.


================================================================================
21. PENDIENTES Y PRÓXIMOS PASOS
================================================================================
Inmediatos (para dar por buena la v1.4.2)
  P1.  Copiar deepseek/learning_api.py, templates/learning.html y
       static/learning.js. Usar el main.py corregido.
  P2.  Arrancar con iniciar.bat y confirmar "Application startup complete"
       sin ImportError.
  P3.  Instalar transformers y confirmar que requirements.txt lo incluye.
  P4.  Iniciar sesión con learning@example.com y entrar a /learning.
  P5.  Resolver el problema de la cámara "no detectada" (sección 22).
  P6.  Hacer la prueba completa: guardar vacía, subir/capturar ejemplos,
       probar, evaluar, buscar valores, aplicar, guardar estado y descargar
       el zip.

Funcionalidad que falta
  P7.  MONITOR AUTOMÁTICO (propuesto, no construido): el servidor revisa
       cada cámara activa cada cierto tiempo (por ejemplo 60 s), toma un
       frame con deepseek/camara.py, lo compara con la foto vacía y guarda el
       resultado en la BD (cámara, hora, porcentaje, hay_cosas).
  P8.  Endpoint para el rol usuario con ese historial, solo de las cámaras de
       su empresa.
  P9.  GRÁFICO en el dashboard del usuario "demo" (porcentaje en el tiempo
       por cámara y estado actual vacía/con cosas).
       Para P7-P9 hacen falta: templates/dashboard.html, static/dashboard.js
       y base_de_datos/modelos.py.
  P10. Opción de guardar la foto vacía automáticamente con el primer frame
       (solo si la cámara está vacía al arrancar).
  P11. Botón para borrar la foto vacía y borrado automático de
       cam<ID>.jpg y cam<ID>/ al borrar una cámara.
  P12. Sensibilidad por cámara (hoy es global).
  P13. Importación del respaldo (.zip) en la página learning.
  P14. Caché de los mapas de profundidad de los ejemplos para acelerar
       "Buscar mejores valores" (requiere revisar volumen.py).
  P15. Mover los estilos l-* a static/style.css si se quiere respetar la
       regla de un solo CSS.

Ajustes en archivos que no se vieron
  P16. Agregar "learning" a la lista de roles de admin.html / admin.js.
  P17. Revisar login.js para la redirección del rol learning.
  P18. Comprobar la columna "rol" en modelos.py.

Limpieza y seguridad
  P19. Quitar la carga de yolov8n.pt y los imports sin uso de main.py (si ya
       no se va a usar YOLO general).
  P20. Aplicar los ajustes 2 y 3 de iniciar.bat (v1.4) y actualizar el árbol
       de DOCUMENTACION.txt.
  P21. Cambiar SECRETO_JWT y las claves demo; revisar la exposición de
       url_stream en /usuario/informes; agregar deepseek/referencias/ y
       deepseek/entrenamiento/ a .gitignore.
  P22. (Opcional) Entrenar piso/pared (sección 12) si se quiere esa vía.


================================================================================
22. LISTA DE PRUEBAS PARA VALIDAR LA INSTALACIÓN
================================================================================
A. Servidor
   1. iniciar.bat -> "Application startup complete", sin errores.
   2. http://localhost:8000/health -> {"status":"ok"}.
B. Usuario learning
   3. http://localhost:8000 -> iniciar sesión con learning@example.com /
      learning1234. Debe terminar en /learning.
   4. Si dice "Credenciales invalidas": ver la consola del servidor al
      arrancar (puede haber fallado la creación del usuario).
C. Cámara "no detectada": decidir si es A o B
   5. En /learning, pulsar "Comprobar conexión de todas".
        - Si la cámara aparece y se marca "en línea": el servidor la lee;
          el problema está en otra parte (por ejemplo el navegador no tenía
          sesión en esa dirección).
        - Si aparece y se marca "sin conexión": mirar la consola del
          servidor, línea "[learning] Falló la lectura de la cámara N: ..."
          (ahí está el motivo real: URL, red, cámara apagada...).
        - Si NO aparece en la lista: no existe en la BD de ese login.db, o el
          servidor está usando otro login.db (ejecutar desde la raíz).
   6. Con la cámara elegida, pulsar "Actualizar imagen".
        - Si sale un mensaje rojo "No se pudo obtener imagen de la cámara":
          revisar la consola del servidor (motivo real).
        - Si sale la imagen: la lectura funciona.
   7. python deepseek\capturar.py <id> --cantidad 1 : si guarda una foto, el
      servidor lee la cámara. (La cámara 1 ya se comprobó.)
   8. Si el id de la cámara en la lista es distinto de 1, repetir con ese id.
D. Calibración
   9. Con la habitación vacía: "Guardar como vacía"; debe aparecer la foto en
      "Foto vacía guardada" y la cámara pasa a "calibrada" en la tarjeta.
  10. Poner un objeto: "Probar con la cámara". La primera vez tarda (descarga
      del modelo). Debe decir "TIENE cosas" y marcar el objeto en rojo.
  11. Quitar el objeto: debe decir "está vacía".
  12. Ajustar deslizadores y "Guardar sensibilidad"; confirmar que aparece
      deepseek\config_volumen.json.
E. Entrenamiento (v1.4.2)
  13. Subir 2-3 fotos como "vacía" y 2-3 como "con cosas" (arrastrando y
      con el input). Ver que aparecen en la galería y que el conteo sube.
  14. "Capturar de la cámara" con cantidad 2 y pausa 2: se guardan y
      aparecen en la galería.
  15. En la galería, "Probar" una foto: muestra el resultado del análisis.
  16. "Usar como vacía" con una foto de la galería "vacía": actualiza la foto
      vacía guardada.
  17. "Borrar" un ejemplo: desaparece de la galería y baja el conteo.
  18. "Evaluar con los valores actuales": muestra precisión, matriz y detalle
      por foto.
  19. "Buscar mejores valores": muestra la tabla de sensibilidades y habilita
      "Aplicar y guardar sugeridos"; al aplicarlo, los sliders cambian y se
      guarda la configuración.
  20. Escribir una nota, esperar o pulsar "Guardar estado ahora"; recargar
      la página: la cámara, la sensibilidad y la nota se recuperan.
  21. "Descargar respaldo (.zip)": se descarga un zip con los ejemplos, las
      referencias y los dos JSON.
F. Supervisor
  22. Entrar con supervisor@example.com: ya no existe el botón "Detectar
      objetos"; "Ver" muestra la cámara.
  23. http://localhost:8000/docs no debe listar /supervisor/camaras/{id}/
      detectar ni /segmentar; sí debe listar todos los /learning/*.


================================================================================
23. HISTORIAL DE VERSIONES
================================================================================
v1.4    Login por roles, empresas, departamentos, cámaras con modal (HLS +
        MJPEG), YOLO general (botón "Detectar objetos"), recuperación de
        contraseña simulada.
v1.4.1  (interno "v1.6")
        - Rol "learning", usuario learning@example.com y página /learning.
        - deepseek/volumen.py: habitación vacía vs con cosas con Depth
          Anything V2 Small (preentrenado).
        - Endpoints /learning/* (cámaras, frame, referencia, probar, config).
        - Lectura de frames por el servidor (OpenCV, RTSP por TCP).
        - Sensibilidad global editable (config_volumen.json).
        - Supervisor reducido a visualización: sin botón ni endpoints
          /detectar y /segmentar.
        - Redirecciones actualizadas para el nuevo rol.
v1.4.2  - deepseek/learning_api.py: herramientas de entrenamiento
          (estado-camaras con verificación de conexión, subida y captura de
          ejemplos, probar-foto, entrenar evaluar/buscar, estado guardado en
          disco y exportación a zip).
        - templates/learning.html y static/learning.js reescritos: todas las
          cámaras registradas, galería de ejemplos con probar/borrar/usar
          como vacía, sección de entrenamiento, estado y respaldo.
        - main.py: import + include_router de learning_api. Entregado el
          archivo completo corregido.
        - Pendiente: confirmar el arranque, el usuario learning, la cámara
          "no detectada", el monitor automático y el gráfico del dashboard.


================================================================================
24. GLOSARIO
================================================================================
learning        Rol que calibra y entrena la IA; ve todas las cámaras.
Calibrar        Guardar la foto vacía de cada cámara y ajustar la
                sensibilidad. No es entrenar una red neuronal.
Entrenar (aquí) Medir el acierto con ejemplos y buscar los mejores valores de
                sensibilidad. La red ya viene entrenada.
Ejemplo         Foto guardada por cámara y etiqueta ("vacia" o "con_cosas")
                en deepseek/entrenamiento/.
Foto vacía /    Foto de la habitación sin nada, usada como punto de
referencia      comparación. Una por cámara.
Profundidad     Estimación de la distancia de cada punto de la imagen. Es
relativa        relativa (no en metros): sirve para comparar fotos.
Depth Anything  Modelo preentrenado que estima la profundidad desde una sola
V2 Small        imagen (Apache-2.0, ~100 MB).
Umbral          Cuánto debe cambiar la profundidad para marcar un píxel.
Área mínima     % de la imagen cambiada necesario para decir "hay cosas".
Matriz de       tp / tn / fp / fn: aciertos y errores de la detección con los
confusión       ejemplos etiquetados.
Cámara fija     Cámara que no cambia de lugar ni de ángulo.
YOLO            Familia de modelos de visión por computador. yolov8n.pt
                (detección, 80 clases) ya no se usa en la web; yolov8n-seg
                (segmentación) es la herramienta de consola piso/pared.
Segmentación    Clasificar cada píxel (piso, pared u otro).
MJPEG           Video como secuencia de fotos JPEG por HTTP.
RTSP            Protocolo de video de cámaras IP; el navegador no lo
                reproduce, pero el servidor sí lo lee con OpenCV.
HLS (.m3u8)     Streaming por segmentos, reproducible con hls.js.
JWT             Token de sesión firmado, guardado en cookie httpOnly.
Carga perezosa  El modelo se carga la primera vez que se necesita.
run_in_threadpool  Ejecuta una tarea pesada en un hilo para no bloquear el
                servidor.
CORS            Restricción del navegador al usar imágenes de otro origen en
                un canvas.
APIRouter       Objeto de FastAPI que agrupa rutas y se monta con
                include_router.
Path traversal  Ataque que intenta salir de una carpeta con ".." en el
                nombre de archivo; aquí se bloquea con _nombre_ok.

================================================================================
 FIN — DOCUMENTACIÓN v1.4.2
================================================================================