================================================================================
     LOGIN CON PANEL DE ADMINISTRACIÓN Y SUPERVISIÓN — DOCUMENTACIÓN v1.4
================================================================================
Proyecto:   Sistema de login con roles, aislamiento por empresa, visualización
            de cámaras en directo y recuperación de contraseña simulada.
Versión:    1.4
Fecha:      Octubre 2026
Stack:      Python 3.12 · FastAPI · SQLAlchemy · bcrypt · PyJWT · Jinja2
Frontend:   HTML + CSS + JS puro (sin frameworks) + hls.js (solo HLS)
Base datos: SQLite (login.db)
Seguridad:  JWT en cookie httpOnly + validación en servidor por rol
Generado:   Claude (Anthropic)
================================================================================


================================================================================
1. RESUMEN EJECUTIVO (Novedades v1.4)
================================================================================

La versión 1.4 incorpora un flujo completo de recuperación de contraseña sin 
dependencias externas de correo electrónico (sin Gmail, SendGrid ni ningún 
proveedor SMTP). El código de verificación se genera en el servidor y se 
devuelve directamente en la respuesta JSON para mostrarse en la interfaz, lo 
que permite simular el flujo completo en un entorno de desarrollo o demo. Se 
incluyeron las medidas de seguridad pertinentes para que el mecanismo sea apto 
para producción con mínimos ajustes futuros.

Cambios principales:

  1. Recuperación de contraseña simulada
     El usuario solicita un código de 6 dígitos, el cual se muestra en pantalla.
     El código expira a los 15 minutos y se borra de la base de datos al usarse.

  2. Prevención de enumeración de usuarios
     Si se ingresa un correo no registrado, el sistema responde de forma genérica
     (HTTP 200 con "codigo_simulado": null) para no revelar si el email existe.

  3. Nuevas funciones en la Base de Datos
     Se añadieron las columnas reset_code y reset_code_expira a la tabla usuarios,
     junto con las funciones guardar_codigo_reset() y actualizar_password().

Alcance v1.4:

  - Login de usuarios existentes.
  - Panel admin: gestión de usuarios y empresas.
  - Panel supervisor: gestión de departamentos y cámaras.
  - Visualización de cámaras en modal (HLS + MJPEG).
  - Recuperación de contraseña mediante código simulado.

Fuera de alcance (para futuras versiones):

  - Envío real de correos electrónicos (SMTP).
  - Edición/desactivación de usuarios.
  - Conversión RTSP → HLS dentro del backend.
  - Paginación en listados.
  - Tests automatizados.




1.4.1

================================================================================
     LOGIN CON PANEL DE ADMINISTRACION, SUPERVISION Y CALIBRACION DE IA
     DOCUMENTACION v1.6  (estado actual completo de la aplicacion)
================================================================================
Proyecto:   Sistema de login con roles, aislamiento por empresa, visualizacion
            de camaras en directo, recuperacion de contrasena simulada y
            deteccion de "habitacion vacia / con cosas" mediante un modelo
            preentrenado de profundidad, calibrado desde una pagina dedicada
            (rol "learning").
Version:    1.6 (base: v1.5; la v1.4 y v1.5 se integran en este documento)
Fecha:      7 de noviembre de 2026
Stack:      Python 3.12 · FastAPI · SQLAlchemy · bcrypt · PyJWT · Jinja2
            Ultralytics (YOLO) · OpenCV · NumPy · Pillow · transformers
Frontend:   HTML + CSS + JS puro (sin frameworks) + hls.js (solo HLS)
Base datos: SQLite (login.db)
Seguridad:  JWT en cookie httpOnly + validacion en servidor por rol
Modelos IA: Depth Anything V2 Small (profundidad, preentrenado, en uso)
            YOLOv8n yolov8n.pt (se carga al arrancar, YA NO se usa en la web)
            YOLOv8n-seg piso/pared (herramienta de consola, sin modelo
            entrenado todavia)
Carpeta:    C:\Users\yochu\Desktop\ia_proyecto_titulo v1.4   (raiz; el nombre
            de la carpeta sigue diciendo v1.4)
Generado:   Claude (Anthropic)

NOTA SOBRE ESTE DOCUMENTO
  - Describe TODO lo que existe hoy en la aplicacion, lo creado o modificado
    en la sesion de la v1.5 y de esta sesion (v1.6), y lo que NO se pudo ver.
  - Etiquetas usadas:
      [NUEVO v1.6]       creado en esta sesion
      [MODIFICADO v1.6]  existente y cambiado en esta sesion
      [DE v1.5]          creado en la sesion anterior, sin cambios hoy
      [SIN CAMBIOS]      revisado y no tocado
      [NO REVISADO]      existe (o se infiere por imports) pero su contenido
                         no se vio; no se afirma nada de su interior
      [CONFIRMAR]        dato que el desarrollador debe verificar
  - Las rutas son relativas a la raiz del proyecto.
  - Lo que se probo de verdad y lo que no esta en la seccion 15.


================================================================================
INDICE
================================================================================
  1.  Resumen ejecutivo y evolucion de la sesion
  2.  Roles, usuarios de demostracion y redirecciones
  3.  Mapa completo de carpetas y archivos
  4.  Backend: main.py
  5.  Tabla completa de rutas
  6.  Calibracion de la IA: como funciona (rol learning)
  7.  deepseek/volumen.py (archivo por archivo)
  8.  Frontend de learning (learning.html y learning.js)
  9.  Frontend de supervisor (solo visualizacion)
 10.  Capa de datos y resto del frontend (lo que no se reviso)
 11.  Herramientas de consola en deepseek/ (piso/pared)
 12.  Flujos de datos
 13.  Dependencias y arranque (requirements.txt, iniciar.bat)
 14.  Comandos de uso
 15.  Estado verificado (que se probo y que no)
 16.  Bitacora de problemas y soluciones
 17.  Decisiones de diseno
 18.  Limitaciones conocidas
 19.  Observaciones de seguridad
 20.  Pendientes y proximos pasos
 21.  Lista de pruebas para validar la instalacion
 22.  Historial de versiones
 23.  Glosario


================================================================================
1. RESUMEN EJECUTIVO Y EVOLUCION DE LA SESION
================================================================================

1.1 Punto de partida (v1.4 y v1.5)
  - v1.4: login por roles (admin, supervisor, usuario), empresas,
    departamentos, camaras con modal de visualizacion (HLS + MJPEG),
    deteccion de objetos con YOLO general (boton "Detectar objetos" del
    supervisor) y recuperacion de contrasena simulada (codigo de 6 digitos).
  - v1.5: modulo deepseek/ para segmentacion piso/pared con YOLO-seg
    (capturar, etiquetar, entrenar, predecir) y endpoint /segmentar. Quedo
    sin modelo entrenado.

1.2 Objetivo de esta sesion
  Detectar si una habitacion "tiene cosas" (algo tridimensional, cualquier
  objeto) SIN entrenar una lista de clases, y que quien calibra la IA NO sea
  el supervisor.

1.3 Que se construyo (v1.6)
  1) deepseek/volumen.py: compara la profundidad de la foto actual contra la
     foto de la habitacion VACIA (camara fija) con Depth Anything V2 Small
     (preentrenado, sin entrenamiento propio).
  2) Nuevo rol "learning" (usuario learning@example.com) y pagina /learning
     para calibrar: elegir camara, guardar la foto vacia, probar y ajustar la
     sensibilidad. Puede ver TODAS las camaras registradas.
  3) El servidor lee el frame directo de la camara (OpenCV), sin depender del
     navegador; por eso funciona tambien con RTSP.
  4) El supervisor se dejo SOLO con visualizacion: se le quitaron el boton
     "Detectar objetos" y los endpoints /detectar y /segmentar.

1.4 Recorrido (para entender por que quedo asi)
  - Se propuso primero que el supervisor guardara la foto vacia y revisara
    con botones en su modal (endpoints /supervisor/camaras/{id}/referencia y
    /revisar). Esos endpoints y botones FUERON CREADOS Y LUEGO ELIMINADOS en
    esta misma sesion; ya no existen.
  - Se pidio que el supervisor solo vea camaras y que el resultado se refleje
    en un grafico del dashboard "demo". Se propuso un monitor automatico (ver
    seccion 20, NO implementado).
  - Se pidio una pagina dedicada a "entrenar" la IA y un usuario "learning".
    Con el modelo elegido "entrenar" significa CALIBRAR cada camara (foto
    vacia + sensibilidad); la red neuronal ya viene entrenada.

1.5 Estado en una frase
  La aplicacion tiene todo el codigo de calibracion entregado y revisado en
  sintaxis, pero la sesion termino sin confirmar que /learning funciona de
  punta a punta: el desarrollador reporto que una camara funcional "no es
  detectada" y ese punto sigue abierto (seccion 15 y 16). La lectura de la
  camara 1 desde el servidor SI se verifico.


================================================================================
2. ROLES, USUARIOS DE DEMOSTRACION Y REDIRECCIONES
================================================================================

2.1 Roles (ROLES_VALIDOS en main.py)  [MODIFICADO v1.6: se agrego "learning"]
  admin       Gestiona usuarios y empresas. Sin empresa (empresa_id = None).
  supervisor  Gestiona departamentos y camaras de SU empresa; solo ve/borra
              las camaras que el mismo creo. SOLO visualizacion de camaras.
  usuario     Ve el listado de camaras activas de su empresa (/usuario/
              informes) y el dashboard. (Es el "demo" del que se habla en la
              conversacion: demo@example.com.)
  learning    NUEVO. Calibra la IA. Sin empresa (empresa_id = None). Ve todas
              las camaras de todas las empresas y supervisores.

2.2 Usuarios creados al arrancar (funcion al_arrancar, solo si no existen)
  Empresa:   "Empresa Demo"
  admin@example.com       admin1234       rol admin       sin empresa
  supervisor@example.com  super1234       rol supervisor  Empresa Demo
  demo@example.com        demo1234        rol usuario     Empresa Demo
  learning@example.com    learning1234    rol learning    sin empresa  [NUEVO]
  Son claves de desarrollo: cambiarlas antes de produccion.
  Si login.db ya existia, el usuario learning se crea igualmente al arrancar
  porque la comprobacion es por correo.

2.3 Reglas al crear usuarios (POST /admin/usuarios)  [MODIFICADO v1.6]
  - nombre obligatorio; password minimo 6 caracteres.
  - rol debe estar en ROLES_VALIDOS (ahora incluye learning).
  - rol supervisor o usuario: empresa_id obligatorio y debe existir.
  - rol admin o learning: empresa_id se fuerza a None.
  - email unico.
  [CONFIRMAR] templates/admin.html y static/admin.js no se revisaron: si el
  formulario del admin tiene la lista de roles escrita a mano, "learning" no
  aparecera ahi hasta agregarlo.

2.4 Redirecciones entre vistas (vistas HTML)
  GET /           login.html (publico).
  GET /recuperar  recuperar.html (publico).
  GET /dashboard  sin sesion -> /; admin -> /admin; supervisor -> /supervisor;
                  learning -> /learning [NUEVO]; usuario -> dashboard.html.
  GET /admin      sin sesion -> /; si no es admin -> /dashboard; admin ->
                  admin.html.
  GET /supervisor sin sesion -> /; admin -> /admin; cualquier otro rol que no
                  sea supervisor -> /dashboard [MODIFICADO v1.6; antes solo
                  mandaba al rol usuario]; supervisor -> supervisor.html.
  GET /learning   [NUEVO] sin sesion -> /; admin -> /admin; supervisor ->
                  /supervisor; usuario (cualquier otro) -> /dashboard;
                  learning -> learning.html.
  [CONFIRMAR] static/login.js no se reviso: tras el login redirige segun el
  rol. Si no conoce "learning", el usuario puede quedar en /dashboard, que lo
  reenvia a /learning; si no ocurre, entrar directo a /learning.

2.5 Sesion
  - Cookie "access_token" (httponly, samesite=lax, path=/), expira en 60 min.
  - El token tambien se acepta por cabecera "Authorization: Bearer ...".
  - Para el navegador, localhost y 127.0.0.1 son sitios distintos: cada uno
    tiene su propia sesion. Usar siempre la misma direccion.
  - Una peticion a un endpoint de API sin sesion responde 401 con detalle
    "Falta el token de autenticacion".


================================================================================
3. MAPA COMPLETO DE CARPETAS Y ARCHIVOS
================================================================================

ia_proyecto_titulo v1.4/                      (raiz del proyecto)
|
+-- base_de_datos/                            Capa de datos (SQLAlchemy)
|   +-- __init__.py                           [NO REVISADO]
|   +-- conexion.py                           [NO REVISADO] exporta SesionLocal
|   |                                         (OJO: SesionLocal, no
|   |                                         SessionLocal), crear_tablas,
|   |                                         obtener_sesion
|   +-- modelos.py                            [NO REVISADO] ORM: usuarios,
|   |                                         empresas, departamentos y
|   |                                         camaras (CamaraORM). main.py
|   |                                         importa CamaraORM de aqui.
|   +-- usuarios.py                           [NO REVISADO] usadas en main:
|   |                                         actualizar_password,
|   |                                         crear_usuario,
|   |                                         guardar_codigo_reset,
|   |                                         listar_usuarios,
|   |                                         listar_usuarios_por_empresa,
|   |                                         obtener_por_email, obtener_por_id
|   +-- empresas.py                           [NO REVISADO] crear_empresa,
|   |                                         listar_empresas, obtener_por_id,
|   |                                         obtener_por_nombre
|   +-- departamentos.py                      [NO REVISADO] crear_departamento,
|   |                                         listar_por_empresa,
|   |                                         obtener_por_id
|   +-- camaras.py                            [SIN CAMBIOS] ver 10.1
|
+-- deepseek/                                 Modulo de IA
|   +-- __init__.py                           [DE v1.5] vacio, marca paquete
|   +-- volumen.py                            [NUEVO v1.6] habitacion vacia vs
|   |                                         con cosas (profundidad)
|   +-- camara.py                             [DE v1.5] URL desde la BD +
|   |                                         lectura de frames (la usa main.py
|   |                                         desde v1.6)
|   +-- capturar.py                           [DE v1.5] guarda frames en el
|   |                                         dataset (consola)
|   +-- train.py                              [DE v1.5] entrena YOLO-seg
|   +-- predict.py                            [DE v1.5] inferencia piso/pared
|   +-- servicio.py                           [DE v1.5] puente piso/pared; main
|   |                                         lo importa pero ya no lo usa
|   +-- data.yaml                             [DE v1.5] dataset (piso, pared)
|   +-- config_volumen.json                   [GENERADO] se crea al pulsar
|   |                                         "Guardar sensibilidad" por
|   |                                         primera vez
|   +-- referencias/                          [GENERADA] fotos de habitacion
|   |   +-- cam<ID>.jpg                       vacia, una por camara
|   +-- dataset/                              [DE v1.5]
|   |   +-- images/train/                     fotos de prueba capturadas:
|   |   |                                     cam1_20261106_232145.jpg y
|   |   |                                     cam1_20261107_184708.jpg
|   |   +-- images/val/                       vacia
|   |   +-- labels/train/  labels/val/        vacias
|   +-- runs/piso_pared/weights/best.pt       NO existe (no se ha entrenado)
|
+-- templates/                                HTML (Jinja2)
|   +-- login.html                            [NO REVISADO]
|   +-- recuperar.html                        [NO REVISADO]
|   +-- dashboard.html                        [NO REVISADO] (rol usuario)
|   +-- admin.html                            [NO REVISADO]
|   +-- supervisor.html                       [MODIFICADO v1.6] sin boton de IA
|   +-- learning.html                         [NUEVO v1.6]
|
+-- static/
|   +-- style.css                             [NO REVISADO] CSS global
|   +-- login.js                              [NO REVISADO]
|   +-- dashboard.js                          [NO REVISADO]
|   +-- admin.js                              [NO REVISADO]
|   +-- supervisor.js                         [MODIFICADO v1.6] sin codigo de IA
|   +-- learning.js                           [NUEVO v1.6]
|   (puede haber otros .js, p. ej. para /recuperar: no se vieron)
|
+-- main.py                                   [MODIFICADO v1.6] ver seccion 4
+-- requirements.txt                          ver seccion 13 [CONFIRMAR]
+-- iniciar.bat                               ver seccion 13
+-- DOCUMENTACION.txt                         [NO REVISADO] documentacion
|                                             antigua: su arbol esta
|                                             desactualizado
+-- DOCUMENTACION_v1.5.txt                    documento de la sesion anterior
+-- DOCUMENTACION_v1.6.txt                    ESTE DOCUMENTO
|
+-- login.db                                  GENERADO por la app (SQLite);
|                                             contiene usuarios y hashes
+-- venv/                                     GENERADO por iniciar.bat
+-- __pycache__/                              GENERADO por Python

Archivos entregados en esta sesion y donde van:
  main.py          -> raiz (reemplaza)
  volumen.py       -> deepseek\volumen.py (reemplaza el existente)
  learning.html    -> templates\learning.html
  learning.js      -> static\learning.js
  supervisor.html  -> templates\supervisor.html (reemplaza)
  supervisor.js    -> static\supervisor.js (reemplaza)
Despues de copiar: Ctrl+F5 en el navegador para no usar JS en cache.


================================================================================
4. BACKEND: main.py                                        [MODIFICADO v1.6]
================================================================================

4.1 Arranque del archivo
  - Antes de cualquier import de cv2 se fija
    OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" (setdefault) para que
    RTSP vaya por TCP. (deepseek/camara.py tambien lo fija, pero main.py
    importa cv2 primero, por eso se agrego aqui.)
  - Modelo YOLO general: modelo_yolo = YOLO("yolov8n.pt") se carga al importar
    main.py. YA NO SE USA (se quito /detectar); sigue cargandose y alarga el
    arranque. Se puede borrar cuando se quiera.
  - Imports sin uso actual: deepseek.servicio (modelo_disponible,
    segmentar_bytes), numpy, JSONResponse, listar_camaras_por_departamento.
    No molestan.
  - Imports nuevos de v1.6:
      from fastapi.responses import FileResponse (y el resto)
      from base_de_datos.modelos import CamaraORM
      from deepseek.camara import frame_de_camara
      from deepseek.volumen import analizar_bytes, guardar_config,
           guardar_referencia, hay_referencia, obtener_config,
           ruta_referencia
  - Si deepseek/volumen.py no existe o no define esas funciones, el servidor
    NO arranca (ImportError).

4.2 Configuracion
  SECRETO_JWT = "cambia-esto-en-produccion" (cambiar), ALGORITMO HS256,
  MINUTOS_EXPIRACION = 60, MINUTOS_RESET = 15.
  ROLES_VALIDOS = {"admin", "supervisor", "usuario", "learning"}.

4.3 Dependencias de autenticacion
  usuario_actual     lee el token (cookie o Bearer), valida, devuelve usuario
                     activo o 401.
  requiere_admin     403 si rol != admin.
  requiere_supervisor 403 si rol != supervisor.
  requiere_usuario   403 si rol != usuario.
  requiere_learning  [NUEVO] 403 si rol != learning.
  verificar_empresa_del_objeto  403 si objeto.empresa_id != usuario.empresa_id.

4.4 Endpoints del supervisor (version actual)
  Solo: listar/crear departamentos, listar/crear/borrar camaras.
  ELIMINADOS en v1.6: /supervisor/camaras/{id}/detectar (YOLO general) y
  /supervisor/camaras/{id}/segmentar (piso/pared). Ya no se pueden llamar
  ni desde /docs.

4.5 Bloque learning  [NUEVO v1.6]
  Funciones auxiliares:
    _frame_jpg(camara_id)   frame_de_camara -> JPEG calidad 90 (bytes).
    _frame_servidor(id)     lo ejecuta en un hilo (run_in_threadpool). Si la
                            camara no responde: imprime en la consola
                            "[learning] Fallo la lectura de la camara N: ..."
                            y responde 502 con un mensaje generico (NO incluye
                            la URL, que puede llevar usuario y clave).
    _camara_o_404(sesion,id) 404 "Camara no encontrada".
  Los endpoints estan en la seccion 5 y la logica en la seccion 6.


================================================================================
5. TABLA COMPLETA DE RUTAS
================================================================================
METODO  RUTA                                        QUIEN / RESPUESTA
GET     /                                           publico (login.html)
GET     /recuperar                                  publico (recuperar.html)
GET     /dashboard                                  sesion; redirige segun rol
GET     /admin                                      admin
GET     /supervisor                                 supervisor
GET     /learning                                   learning                [NUEVO]
POST    /auth/login                                 publico
POST    /auth/logout                                cualquiera
GET     /auth/yo                                    sesion (401 si no hay)
POST    /auth/recuperar                             publico (codigo simulado)
POST    /auth/restablecer                           publico (codigo + clave)
GET     /admin/usuarios                             admin (filtro ?empresa_id=)
POST    /admin/usuarios                             admin
GET     /admin/empresas                             admin
POST    /admin/empresas                             admin
GET     /supervisor/departamentos                   supervisor
POST    /supervisor/departamentos                   supervisor
GET     /supervisor/camaras                         supervisor (solo las suyas)
POST    /supervisor/camaras                         supervisor
DELETE  /supervisor/camaras/{camara_id}             supervisor (solo las suyas)
GET     /learning/camaras                           learning                [NUEVO]
GET     /learning/camaras/{id}/frame                learning                [NUEVO]
GET     /learning/camaras/{id}/referencia           learning                [NUEVO]
POST    /learning/camaras/{id}/referencia           learning                [NUEVO]
POST    /learning/camaras/{id}/probar               learning                [NUEVO]
GET     /learning/config                            learning                [NUEVO]
PUT     /learning/config                            learning                [NUEVO]
GET     /usuario/informes                           rol "usuario"
GET     /health                                     publico
Documentacion automatica de FastAPI: http://localhost:8000/docs

5.1 Detalle de los endpoints /learning (todos: 401 sin sesion, 403 si el rol
    no es learning)
  GET /learning/camaras
    200: lista de TODAS las camaras (orden por id). Cada una:
         {id, nombre, empresa_id, esta_activa, tiene_referencia}
    No devuelve url_stream (puede contener credenciales).
  GET /learning/camaras/{id}/frame
    Lee un frame de la camara en el servidor. 200 image/jpeg con
    Cache-Control: no-store. 404 camara inexistente. 502 si no se puede leer.
  GET /learning/camaras/{id}/referencia
    Devuelve la foto vacia guardada (image/jpeg, no-store). 404 si la camara
    no existe o aun no hay foto vacia.
  POST /learning/camaras/{id}/referencia
    Sin cuerpo. Toma un frame AHORA y lo guarda como habitacion vacia
    (reemplaza la anterior). 200 {"mensaje":"Referencia guardada",
    "camara_id":N}. 404, 502, 400 (imagen invalida).
  POST /learning/camaras/{id}/probar
    Form opcional: umbral_diff (float), area_min_pct (float). Si se envian se
    usan SOLO para esta prueba (no se guardan). Toma un frame ahora y lo
    compara con la foto vacia. 200: {camara_id, camara_nombre, hay_cosas,
    porcentaje, umbral_diff, area_min_pct, imagen (data URI JPEG base64)}.
    Errores: 404 camara; 409 "Primero guarda una foto de la habitacion
    vacia"; 502 camara no legible; 400 valores fuera de rango; 503 si el
    modelo de profundidad no se pudo cargar/descargar (OSError).
  GET /learning/config
    200 {"umbral_diff": x, "area_min_pct": y}.
  PUT /learning/config
    Form obligatorio: umbral_diff, area_min_pct. Guarda en
    deepseek/config_volumen.json. 200 con los valores guardados; 400 si estan
    fuera de rango. Estos valores los usa toda la aplicacion.

5.2 Endpoints existentes sin cambios (resumen)
  POST /auth/login           form email, password; fija cookie; devuelve
                             token y datos del usuario. 401 credenciales
                             invalidas; 403 usuario inactivo.
  POST /auth/logout          borra la cookie.
  GET  /auth/yo              {usuario_id, email, nombre, rol, empresa_id}.
  POST /auth/recuperar       genera codigo de 6 digitos (expira en 15 min) y
                             lo DEVUELVE en la respuesta (flujo simulado). Si
                             el correo no existe responde 200 con
                             codigo_simulado null (no revela si existe).
  POST /auth/restablecer     valida email + codigo + nueva clave (>= 6).
  GET  /usuario/informes     camaras ACTIVAS de la empresa del usuario con
                             {id, nombre, url_stream, departamento_id,
                             esta_activa}.
  GET  /health               {"status":"ok"}.


================================================================================
6. CALIBRACION DE LA IA: COMO FUNCIONA (ROL LEARNING)
================================================================================

6.1 Idea
  El modelo Depth Anything V2 Small ya viene entrenado y calcula, a partir de
  UNA foto, que tan lejos esta cada punto de la imagen (profundidad
  RELATIVA, no en metros). Para saber si la habitacion "tiene cosas" se
  compara el mapa de profundidad de la foto actual contra el de una foto de la
  habitacion VACIA. Donde la profundidad cambia, hay algo.
  No hace falta etiquetar ni entrenar. "Calibrar" = (a) guardar la foto vacia
  de cada camara y (b) ajustar la sensibilidad.

6.2 Requisito: camara fija
  La foto vacia solo sirve si la camara esta siempre en el mismo lugar y
  angulo. Si se mueve, hay que guardar otra foto vacia. La luz tambien debe
  ser parecida.

6.3 Pasos del rol learning
  1) Entrar a /learning con learning@example.com.
  2) Elegir la camara del selector (muestra todas).
  3) Con la habitacion SIN nada, revisar la "Imagen actual" y pulsar
     "Guardar como vacia". La foto queda en deepseek\referencias\cam<ID>.jpg.
  4) Poner algo en la habitacion y pulsar "Probar ahora": el resultado dice
     si hay cosas, el porcentaje de imagen que cambio y una imagen con las
     zonas distintas en rojo.
  5) Mover los dos deslizadores hasta que acierte y pulsar "Guardar
     sensibilidad".

6.4 Que significan los ajustes
  Umbral de profundidad (umbral_diff, por defecto 0.15): cuanto debe cambiar
    la profundidad normalizada (0 a 1) para marcar un pixel como distinto.
    Mas alto = ignora cambios pequenos (sombras, luz). Mas bajo = detecta
    objetos mas planos.
  Area minima (area_min_pct, por defecto 1.5 %): porcentaje minimo de la
    imagen cambiada para decir "hay cosas". Mas alto = solo objetos grandes.
    Mas bajo = detecta objetos chicos.
  Rangos que acepta el servidor: umbral 0.02 a 0.60; area 0.1 a 50. Los
  deslizadores de la pagina cubren un rango mas corto (ver 8.2).

6.5 Para que sirve despues
  Hoy la calibracion deja listo el analisis, pero NADA lo ejecuta de forma
  automatica ni lo muestra en el dashboard del usuario "demo" todavia
  (pendiente, seccion 20). El unico punto de uso actual es el boton "Probar
  ahora" de /learning.


================================================================================
7. deepseek/volumen.py                                         [NUEVO v1.6]
================================================================================
Constantes
  CARPETA_REF      deepseek/referencias/
  ARCHIVO_CONFIG   deepseek/config_volumen.json
  MODELO_ID        "depth-anything/Depth-Anything-V2-Small-hf"
  ANCHO            640 (las imagenes se reducen a 640 px de ancho)
  CONFIG_POR_DEFECTO  umbral_diff 0.15, area_min_pct 1.5

Funciones publicas
  obtener_config() -> dict
    Lee config_volumen.json en cada llamada (no hay cache, los cambios se
    aplican al instante). Si el archivo no existe o esta danado, usa los
    valores por defecto.
  guardar_config(umbral_diff, area_min_pct) -> dict
    Valida rangos (ValueError si no) y escribe el JSON.
  ruta_referencia(camara_id) -> Path       deepseek/referencias/cam<ID>.jpg
  hay_referencia(camara_id) -> bool
  guardar_referencia(camara_id, contenido: bytes)
    Decodifica (ValueError si la imagen no es valida), reduce a 640 de ancho y
    guarda el JPEG; crea la carpeta si falta.
  analizar_bytes(camara_id, contenido, umbral_diff=None, area_min_pct=None)
    Si faltan umbrales usa los guardados. Algoritmo:
      1. Carga la foto vacia y reduce la actual a su mismo tamano.
      2. Calcula la profundidad de ambas con el modelo (normalizada 0-1).
      3. _alinear(): la profundidad es relativa, asi que ajusta la escala de la
         actual a la de referencia por minimos cuadrados, 3 iteraciones,
         ignorando el 20 % de pixeles que mas difieren (donde estarian los
         objetos).
      4. Diferencia absoluta + desenfoque gaussiano (9x9), umbral, y apertura
         morfologica (7x7) para quitar ruido.
      5. porcentaje = pixeles distintos / total * 100.
      6. Imagen: zonas distintas pintadas de rojo con 50 % de transparencia,
         JPEG calidad 85 en base64 (data URI).
    Devuelve {hay_cosas, porcentaje (1 decimal), umbral_diff, area_min_pct,
    imagen}. hay_cosas = porcentaje >= area_min_pct.
    FileNotFoundError si no hay foto vacia (main.py ya lo comprueba antes).

Carga del modelo
  _pipe() usa lru_cache(1) y un import perezoso de transformers: el servidor
  arranca igual aunque el modelo no se haya descargado. La PRIMERA vez que se
  usa descarga unos 100 MB de Hugging Face (requiere internet) y tarda; luego
  queda en cache del usuario y es mas rapido.
Licencia: Depth Anything V2 Small es Apache-2.0 (uso comercial permitido). Las
  versiones Base/Large/Giant son CC-BY-NC-4.0 (no comercial).
Requiere: transformers, Pillow (PIL), OpenCV, NumPy.


================================================================================
8. FRONTEND DE LEARNING                                        [NUEVO v1.6]
================================================================================

8.1 templates/learning.html
  Pagina con estilos propios minimos (clases l-*) mas /static/style.css para
  los botones y mensajes (boton, boton--primario, boton--peligro, mensaje).
  Estructura:
    Cabecera: titulo "Calibracion de la IA", nombre del usuario
              (#learning-info) y boton "Cerrar sesion" (#logout-btn).
    Tarjeta 1 "Elige la camara": selector #camara-select, boton
              "Actualizar imagen" #btn-frame, linea de mensajes #msg.
    Tarjeta 2 "Foto de la habitacion vacia": imagen actual #img-actual, boton
              "Guardar como vacia" #btn-vacia, foto vacia guardada #img-ref
              y estado #ref-estado.
    Tarjeta 3 "Prueba y sensibilidad": deslizadores #umbral y #area (con
              valores en #umbral-val y #area-val), botones "Probar ahora"
              #btn-probar y "Guardar sensibilidad" #btn-guardar-config, y
              contenedor de resultado #resultado.
  Carga /static/learning.js.

8.2 static/learning.js
  - Al cargar verifica /auth/yo: sin sesion -> "/"; rol distinto de learning
    -> "/dashboard". Luego carga la sensibilidad y las camaras.
  - Selector: cada opcion muestra "#id · nombre (empresa X) · calibrada /
    sin foto vacia". Si no hay camaras: "No hay camaras registradas".
  - Al elegir camara: carga la imagen actual (GET .../frame) y la foto vacia
    (GET .../referencia; 404 se muestra como "(todavia no hay)").
  - Las imagenes se piden con fetch y se muestran con object URLs; asi, si el
    servidor responde un error, se ve el mensaje real (por ejemplo 502) en vez
    de una imagen rota. Las URLs viejas se liberan.
  - "Guardar como vacia": pide confirmacion, hace POST .../referencia,
    recarga la foto guardada y la lista de camaras (para actualizar la marca
    calibrada) manteniendo la camara elegida.
  - "Probar ahora": envia los valores actuales de los deslizadores (sin
    guardarlos) a POST .../probar y muestra titulo "La habitacion TIENE cosas"
    o "La habitacion esta vacia", el porcentaje, el minimo y la imagen roja.
    Despues refresca la imagen actual.
  - "Guardar sensibilidad": PUT /learning/config.
  - Deslizadores: umbral 0.05 a 0.50 (paso 0.01); area 0.5 a 10 (paso 0.5).
  - Cualquier respuesta 401 devuelve al login.
  - Escapa el HTML de los textos que muestra (escapeHtml).


================================================================================
9. FRONTEND DE SUPERVISOR (SOLO VISUALIZACION)         [MODIFICADO v1.6]
================================================================================

9.1 templates/supervisor.html
  - Seccion Departamentos: formulario #crear-departamento-form, lista
    #lista-departamentos.
  - Seccion Camaras: formulario #crear-camara-form (nombre, URL del stream
    input type="url" con placeholder "rtsp://... o http://...", departamento),
    tabla #tabla-camaras, boton "Refrescar".
  - Modal #modal-camara: <video id="modal-video">, <img id="modal-img">
    (fallback MJPEG), #modal-error y #modal-url. Ya NO tiene el boton
    "Detectar objetos" ni #modal-detecciones.
  - Carga hls.js 1.x desde jsdelivr (solo para .m3u8) y /static/supervisor.js.

9.2 static/supervisor.js
  - Verifica sesion con /auth/yo: admin -> /admin; usuario -> /dashboard.
    [CONFIRMAR] un usuario con rol learning que entre a /supervisor es
    reenviado por el servidor (la vista ya lo redirige), asi que no llega
    a cargar este JS.
  - Carga departamentos y camaras, crea departamentos y camaras, borra
    camaras (con confirmacion). Cada fila tiene "Ver" y "Borrar".
  - abrirModalCamara(): segun la URL:
      rtsp://   muestra aviso: el navegador no reproduce RTSP.
      .m3u8     hls.js.
      http(s)   <video>; si no carga en 2,5 s, cae a <img> (MJPEG).
  - Se elimino todo el codigo de captura de frames y deteccion YOLO.
  - Escapa el HTML de los datos mostrados (escapeHtml).
  - Tabla de camaras: muestra la URL completa (url_stream) al supervisor, que
    es quien la creo.


================================================================================
10. CAPA DE DATOS Y RESTO DEL FRONTEND (LO QUE NO SE REVISO)
================================================================================

10.1 base_de_datos/camaras.py  (revisado completo, sin cambios)
  crear_camara(sesion, nombre, url_stream, empresa_id, departamento_id,
               usuario_id=None, esta_activa=True) -> CamaraORM
      Limpia espacios (strip) de nombre y url_stream.
  obtener_por_id(sesion, camara_id) -> Optional[CamaraORM]
  listar_por_empresa / listar_por_usuario / listar_por_departamento (orden
      por id)
  actualizar_camara(sesion, camara_id, **campos)  campos permitidos: nombre,
      url_stream, empresa_id, departamento_id, usuario_id, esta_activa.
  Campos de CamaraORM: id, nombre, url_stream, empresa_id, departamento_id,
  usuario_id (supervisor que la creo), esta_activa.
  No hay funcion de borrado: main.py borra con sesion.delete(camara).
  No hay funcion para listar TODAS las camaras: el endpoint /learning/camaras
  consulta CamaraORM directamente.

10.2 Lo que no se vio en ninguna de las sesiones
  conexion.py, modelos.py (en particular el tipo de la columna "rol"),
  usuarios.py, empresas.py, departamentos.py, login.html, recuperar.html,
  dashboard.html, admin.html, style.css, login.js, dashboard.js, admin.js.
  [CONFIRMAR] si la columna "rol" tiene una restriccion (Enum o CHECK) que
  impida el valor "learning", el usuario learning no se creara al arrancar y
  se vera el error en la consola.


================================================================================
11. HERRAMIENTAS DE CONSOLA EN deepseek/ (PISO/PARED)         [DE v1.5]
================================================================================
Siguen existiendo pero NO estan expuestas en la web desde que se quitaron
/segmentar y el boton del supervisor. Se ejecutan desde la raiz del proyecto
con el Python del venv. No aplican control de roles: usar solo en el equipo
del desarrollador.

  camara.py
    Fija OPENCV_FFMPEG_CAPTURE_OPTIONS (RTSP por TCP) y agrega la raiz a
    sys.path.
    url_de_camara(camara_id) -> url_stream desde la BD (ValueError si no
      existe).
    leer_frame(url, descartar=5) -> frame BGR (lee 5 frames y se queda con el
      ultimo para evitar imagenes viejas del buffer). RuntimeError "No se
      pudo abrir el stream" o "El stream abrio pero no entrego imagen". Los
      mensajes incluyen la URL completa.
    frame_de_camara(camara_id) -> atajo de las dos anteriores.
    DESDE v1.6 lo usa main.py (endpoints de learning): abre y cierra el stream
    en cada peticion.
  capturar.py
    python deepseek\capturar.py <id> [--cantidad N] [--cada S]
    Guarda frames en deepseek\dataset\images\train\ con nombre
    cam<ID>_<AAAAMMDD>_<HHMMSS>.jpg. Sirve tambien para comprobar que el
    servidor lee una camara (probado con la camara 1).
  train.py
    Entrena yolov8n-seg (epochs 100, imgsz 640, batch 8, workers 2) con
    data.yaml (clases 0=piso, 1=pared). Resultado en
    deepseek\runs\piso_pared\weights\best.pt. Necesita imagenes y etiquetas
    en train y val.
  predict.py
    python deepseek\predict.py ruta\imagen.jpg  |  --camara <id>
    Segmenta piso/pared/otro y guarda <nombre>_resultado.png.
  servicio.py
    Puente hacia FastAPI (modelo_disponible, segmentar_bytes). main.py aun lo
    importa pero ya no lo usa.
  data.yaml
    path dataset; train images/train; val images/val; names 0 piso, 1 pared.

Estado del dataset: images/train tiene 2 fotos de prueba de la camara 1;
labels y val estan vacios; no hay modelo entrenado. Con el enfoque de
profundidad (seccion 6) este camino queda como alternativa opcional.


================================================================================
12. FLUJOS DE DATOS
================================================================================

12.1 Como viaja la URL de la camara
  Alta: el supervisor escribe la URL en "URL del stream" -> supervisor.js envia
  POST /supervisor/camaras (form-data) -> main.py valida departamento y
  empresa y llama a crear_camara() -> se guarda en la columna url_stream de
  login.db.

12.2 Visualizacion (supervisor)
  El navegador reproduce la URL directamente (video o imagen MJPEG). El
  servidor no interviene. RTSP no se puede ver en el navegador.

12.3 Calibracion y prueba (learning)
  Navegador (/learning) -> GET .../frame -> main.py llama frame_de_camara(id)
  -> camara.py lee la url_stream de la BD y abre el stream con OpenCV -> el
  frame vuelve como JPEG. El navegador NUNCA recibe ni usa la URL de la camara.
  Guardar vacia: POST .../referencia -> frame del servidor -> guardar_referencia
  -> deepseek\referencias\cam<ID>.jpg.
  Probar: POST .../probar -> frame del servidor -> analizar_bytes (en hilo
  aparte) -> JSON con resultado e imagen.
  Sensibilidad: PUT /learning/config -> deepseek\config_volumen.json.

12.4 Por que el servidor lee la camara y no el navegador
  - Funciona con RTSP.
  - Evita el bloqueo CORS del canvas con streams de otra IP.
  - El rol learning no necesita ver ni abrir la URL.


================================================================================
13. DEPENDENCIAS Y ARRANQUE
================================================================================

13.1 requirements.txt
  Contenido conocido (v1.5, 272 bytes):
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
  v1.6 agrega:  transformers>=4.45.0     [CONFIRMAR que se agrego e instalo]
  Pillow (PIL) lo trae ultralytics. Los comentarios van con "#"; un "//" hace
  fallar pip.

13.2 iniciar.bat
  Detecta/instala Python 3.11-3.13, crea el venv, instala desde
  requirements.txt, verifica la estructura (main.py, requirements.txt,
  base_de_datos\) y levanta uvicorn con --reload en el puerto 8000.
  IMPORTANTE: en la ultima ejecucion mostro "Dependencias ya presentes y
  funcionales" y NO instalo nada nuevo, asi que transformers puede no estar
  instalado. Instalar a mano:
    venv\Scripts\python.exe -m pip install "transformers>=4.45.0"
  Ajustes 2 y 3 recomendados en v1.5 (verificar paquete deepseek y crear las
  carpetas del dataset): [CONFIRMAR] si se aplicaron; no afectan al
  funcionamiento de la calibracion.
  Con --reload, cualquier cambio en un .py reinicia el servidor. Las fotos y
  el config_volumen.json que se generan no son .py y no lo reinician.


================================================================================
14. COMANDOS DE USO
================================================================================
Arrancar: doble clic en iniciar.bat
  (equivale a: venv\Scripts\python.exe -m uvicorn main:app --reload
   --host 127.0.0.1 --port 8000)
  Servidor http://localhost:8000   Docs /docs   Health /health
Entrar a la calibracion: http://localhost:8000 -> learning@example.com /
  learning1234 -> /learning  (o directo http://localhost:8000/learning).
Comprobar que el servidor lee una camara (con el venv activado, desde la raiz):
    python deepseek\capturar.py 1 --cantidad 1
  Cambiar el 1 por el id de la camara. NO escribir "capturar.py 1 ..." solo
  (PowerShell no lo reconoce) y NO poner la ruta entre comillas dobles dentro
  de comillas simples (da "argumento requerido: camara").
Activar el venv en PowerShell:
    (Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ;
    (& ".\venv\Scripts\Activate.ps1")
Siempre ejecutar desde la raiz para que "sqlite:///./login.db" encuentre la
base de datos correcta.


================================================================================
15. ESTADO VERIFICADO
================================================================================
PROBADO Y FUNCIONANDO
  [OK] Lectura de la camara 1 desde el servidor: capturar.py guardo
       cam1_20261106_232145.jpg y cam1_20261107_184708.jpg (la segunda, hoy).
  [OK] Sintaxis de main.py y volumen.py (analisis de Python) y de
       supervisor.js y learning.js (node --check), en la sesion de entrega.
  [OK] Estructura del proyecto con iniciar.bat hasta el paso 5/6 (v1.5).
  [OK] Se comprobo que supervisor.js ya no contiene referencias a deteccion
       y que main.py ya no tiene rutas /detectar ni /segmentar.

PROBLEMA OCURRIDO Y RESUELTO
  El arranque fallo con "ImportError: cannot import name 'analizar_bytes' from
  'deepseek.volumen'": el volumen.py que habia en la carpeta no tenia las
  funciones nuevas. Se entrego un volumen.py completo para reemplazarlo.
  No se pego despues un nuevo arranque para confirmar que quedo resuelto.

NO PROBADO TODAVIA (al cerrar esta documentacion)
  [ ] Arranque del servidor con el main.py y volumen.py nuevos.
  [ ] Que el usuario learning se cree (puede fallar si la columna "rol" tiene
      restricciones).
  [ ] Login con learning y redireccion a /learning.
  [ ] Que /learning/camaras liste las camaras. El desarrollador abrio
      http://localhost:8000/learning/camaras y recibio "Falta el token de
      autenticacion": estaba sin sesion en esa direccion (ver 2.5), asi que
      sigue sin verificarse.
  [ ] Frame, guardar vacia, probar y guardar sensibilidad desde la pagina.
  [ ] Descarga del modelo de profundidad y primera inferencia.
  [ ] Que la imagen capturada sea una vista real (abrirla y confirmar que no
      esta negra ni congelada).
  [ ] Instalacion de transformers.

PROBLEMA ABIERTO REPORTADO POR EL DESARROLLADOR
  "Hay una camara funcional pero no es detectada." No se identifico si es
  (A) que no aparece en el selector de /learning o (B) que aparece pero da
  error al leer. Pasos de diagnostico en la seccion 21.


================================================================================
16. BITACORA DE PROBLEMAS Y SOLUCIONES
================================================================================
1) SessionLocal vs SesionLocal (v1.5)
   conexion.py exporta SesionLocal. Se uso ese nombre en camara.py y main.py.
2) "cannot import name 'leer_frame' from 'camara'" (v1.5)
   Se habia reemplazado camara.py con un fragmento. Debe tener las tres
   funciones (url_de_camara, leer_frame, frame_de_camara).
3) Comandos mal escritos en PowerShell (v1.5 y v1.6)
   Usar "python deepseek\capturar.py <id> ...".
4) SystemExit dentro del servidor (v1.5)
   buscar_modelo ahora lanza FileNotFoundError.
5) Comentario "//" en requirements.txt (v1.5)
   pip no lo entiende; usar "#".
6) ImportError analizar_bytes (v1.6)
   volumen.py incompleto/antiguo; reemplazado por la version completa.
7) "Falta el token de autenticacion" al abrir /learning/camaras (v1.6)
   No es un fallo de la camara: el navegador no tenia sesion en esa
   direccion. Iniciar sesion y usar siempre la misma direccion
   (localhost o 127.0.0.1).
8) iniciar.bat no instala paquetes nuevos (v1.6)
   "Dependencias ya presentes y funcionales": instalar transformers a mano.
9) Camara "no detectada" en learning (v1.6): ABIERTO (seccion 15 y 21).


================================================================================
17. DECISIONES DE DISENO
================================================================================
- Modelo de profundidad PREENTRENADO + comparacion con habitacion vacia, en
  lugar de entrenar clases: sirve para "cualquier cosa" 3D sin etiquetar, y
  YOLO general solo conoce 80 clases (no ve cajas o bultos genericos).
- Depth Anything V2 SMALL por licencia Apache-2.0 y bajo peso (~100 MB).
- La calibracion la hace un rol aparte (learning); el supervisor solo ve
  camaras. Se retiro del supervisor todo "poder" de IA, incluidos los
  endpoints, para que no pueda usarlo ni llamando a la API a mano.
- learning ve TODAS las camaras (sin filtro por empresa ni por supervisor) y
  no necesita ser dueno de ellas.
- La URL de la camara no se envia a learning (puede llevar credenciales); el
  servidor la usa internamente.
- El servidor lee el frame (OpenCV) y no el navegador: soporta RTSP y evita
  CORS.
- Sensibilidad GLOBAL (un solo config_volumen.json para todas las camaras) y
  editable en vivo sin reiniciar; la prueba permite usar valores sin guardar.
- Foto vacia POR CAMARA en deepseek/referencias/cam<ID>.jpg.
- Modelo cargado de forma perezosa y una sola vez (lru_cache); la inferencia
  corre en un hilo aparte (run_in_threadpool) para no bloquear FastAPI.
- Errores de lectura de camara: detalle en la consola del servidor, mensaje
  generico en la respuesta (para no filtrar la URL).
- Se mantienen YOLOv8n y las herramientas piso/pared como opcionales; no se
  borraron.
- Frontend con HTML/CSS/JS puro, igual que el resto de la aplicacion.


================================================================================
18. LIMITACIONES CONOCIDAS
================================================================================
- Requiere camara FIJA; si se mueve hay que guardar otra foto vacia.
- Cambios fuertes de luz, sombras o reflejos pueden dar falsos positivos.
- La profundidad desde una sola imagen es RELATIVA; por eso se alinea la
  escala antes de comparar. Objetos muy planos (una hoja) o del mismo plano
  que el piso pueden no detectarse.
- La primera inferencia es lenta (descarga del modelo; requiere internet).
- HLS (.m3u8) puede no leerse bien con OpenCV. RTSP se lee por TCP.
- Cada peticion a /frame o /probar abre y cierra el stream de la camara.
- Todo es manual por ahora: no hay analisis automatico ni historial.
- Una camara borrada por el supervisor NO borra su foto vacia en
  deepseek/referencias. SQLite puede reutilizar un id si se borra la ultima
  camara: una camara nueva con ese id heredaria una foto vacia ajena.
  [CONFIRMAR segun si la tabla usa AUTOINCREMENT]. Conviene borrar
  cam<ID>.jpg al borrar una camara (pendiente).
- No hay boton para borrar la foto vacia desde la pagina.
- El navegador no reproduce RTSP en el modal del supervisor (solo aviso).
- main.py sigue cargando yolov8n.pt aunque no se use (arranque mas lento).
- login.db debe encontrarse desde el directorio de trabajo (ejecutar desde la
  raiz).


================================================================================
19. OBSERVACIONES DE SEGURIDAD
================================================================================
(Observaciones sobre lo que hay; solo se cambiaron los puntos marcados.)
- SECRETO_JWT conserva el valor por defecto "cambia-esto-en-produccion".
  Cambiarlo (idealmente por variable de entorno).
- Las URLs de camara pueden llevar usuario y clave (rtsp://usuario:clave@...)
  y se guardan en TEXTO PLANO en login.db.
- GET /usuario/informes devuelve url_stream de las camaras activas de la
  empresa al rol "usuario": si la URL lleva credenciales, quedan expuestas.
- Mejora v1.6: /learning/camaras no devuelve url_stream y los errores de
  lectura no incluyen la URL en la respuesta HTTP.
- Los mensajes de error de leer_frame (consola) incluyen la URL completa: no
  compartir esa salida sin ocultar credenciales.
- El rol learning ve las camaras de todas las empresas por diseno: asignarlo
  solo a personal de confianza. Las fotos de deepseek/referencias son
  imagenes de las habitaciones: no subirlas a repositorios (agregar
  deepseek/referencias/ a .gitignore).
- Se quito del supervisor la capacidad de usar IA (endpoints incluidos).
- El codigo de recuperacion se devuelve en la respuesta (simulado, sin email):
  solo apto para demo.
- La cookie de sesion no tiene el atributo "secure" (se asume http local).
- No hay limite de intentos de login.
- Credenciales de demostracion (admin1234, super1234, demo1234,
  learning1234): solo para desarrollo.
- login.db contiene usuarios y hashes: no subirlo a repositorios ni a chats.
- /docs esta abierto; deshabilitarlo en produccion si se desea.
- Los scripts de deepseek/ no aplican roles: ejecutarlos solo en el equipo del
  desarrollador.


================================================================================
20. PENDIENTES Y PROXIMOS PASOS
================================================================================
Inmediatos (para dar por buena la v1.6)
  P1. Arrancar con iniciar.bat y confirmar "Application startup complete" sin
      ImportError.
  P2. Instalar transformers y confirmar que requirements.txt lo incluye.
  P3. Iniciar sesion con learning@example.com y entrar a /learning.
  P4. Resolver el problema de la camara "no detectada" (seccion 21).
  P5. Abrir deepseek\dataset\images\train\cam1_20261107_184708.jpg y confirmar
      que es una imagen real.
  P6. Hacer la prueba completa: guardar vacia, poner un objeto, probar, ajustar
      y guardar sensibilidad.

Funcionalidad que falta
  P7. MONITOR AUTOMATICO (propuesto, no construido): el servidor revisa cada
      camara activa cada cierto tiempo (por ejemplo 60 s), toma un frame con
      deepseek/camara.py, lo compara con la foto vacia y guarda el resultado
      en la BD (camara, hora, porcentaje, hay_cosas).
  P8. Endpoint para el rol usuario con ese historial, solo de las camaras de
      su empresa.
  P9. GRAFICO en el dashboard del usuario "demo" (porcentaje en el tiempo por
      camara y estado actual vacia/con cosas).
      Para P7-P9 hacen falta: templates/dashboard.html, static/dashboard.js y
      base_de_datos/modelos.py.
  P10. Opcion de guardar la foto vacia automaticamente con el primer frame
       (solo si la camara esta vacia al arrancar).
  P11. Boton para borrar la foto vacia y borrado automatico de
       cam<ID>.jpg al borrar una camara.
  P12. Sensibilidad por camara (hoy es global).

Ajustes en archivos que no se vieron
  P13. Agregar "learning" a la lista de roles de admin.html / admin.js.
  P14. Revisar login.js para la redireccion del rol learning.
  P15. Comprobar la columna "rol" en modelos.py.

Limpieza y seguridad
  P16. Quitar la carga de yolov8n.pt y los imports sin uso de main.py (si ya no
       se va a usar YOLO general).
  P17. Aplicar los ajustes 2 y 3 de iniciar.bat (v1.5) y actualizar el arbol de
       DOCUMENTACION.txt.
  P18. Cambiar SECRETO_JWT y las claves demo; revisar la exposicion de
       url_stream en /usuario/informes; agregar deepseek/referencias/ a
       .gitignore.
  P19. (Opcional) Entrenar piso/pared (seccion 11) si se quiere esa via.


================================================================================
21. LISTA DE PRUEBAS PARA VALIDAR LA INSTALACION
================================================================================
A. Servidor
   1. iniciar.bat -> "Application startup complete", sin errores.
   2. http://localhost:8000/health -> {"status":"ok"}.
B. Usuario learning
   3. http://localhost:8000 -> iniciar sesion con learning@example.com /
      learning1234. Debe terminar en /learning.
   4. Si dice "Credenciales invalidas": ver la consola del servidor al arrancar
      (puede haber fallado la creacion del usuario).
C. Camara "no detectada": decidir si es A o B
   5. Con sesion de learning abierta (misma direccion, localhost o
      127.0.0.1), abrir http://localhost:8000/learning/camaras.
        - Si la camara NO esta en el JSON: no existe/no se guardo en la BD, o
          el servidor esta usando otro login.db (ejecutar desde la raiz).
        - Si esta: seguir.
   6. En /learning elegir la camara y pulsar "Actualizar imagen".
        - Si sale un mensaje rojo "No se pudo obtener imagen de la camara":
          mirar la consola del servidor, linea "[learning] Fallo la lectura de
          la camara N: ..." (ahi esta el motivo real).
   7. python deepseek\capturar.py <id> --cantidad 1 : si guarda una foto, el
      servidor lee la camara. (La camara 1 ya se comprobo.)
   8. Si el id de la camara en la lista es distinto de 1, repetir con ese id.
D. Calibracion
   9. Con la habitacion vacia: "Guardar como vacia"; debe aparecer la foto en
      "Foto vacia guardada" y la camara pasa a "calibrada" en el selector.
  10. Poner un objeto: "Probar ahora". La primera vez tarda (descarga del
      modelo). Debe decir "TIENE cosas" y marcar el objeto en rojo.
  11. Quitar el objeto: "Probar ahora" debe decir "esta vacia".
  12. Ajustar deslizadores y "Guardar sensibilidad"; confirmar que aparece
      deepseek\config_volumen.json.
E. Supervisor
  13. Entrar con supervisor@example.com: ya no existe el boton "Detectar
      objetos"; "Ver" muestra la camara.
  14. http://localhost:8000/docs no debe listar /supervisor/camaras/{id}/
      detectar ni /segmentar.


================================================================================
22. HISTORIAL DE VERSIONES
================================================================================
v1.4  Login por roles, empresas, departamentos, camaras con modal (HLS +
      MJPEG), YOLO general (boton "Detectar objetos"), recuperacion de
      contrasena simulada.
v1.5  Modulo deepseek/ (segmentacion piso/pared): capturar, train, predict,
      camara, servicio, data.yaml; endpoint /segmentar. Sin modelo entrenado.
v1.6  - Rol "learning", usuario learning@example.com y pagina /learning.
      - deepseek/volumen.py: habitacion vacia vs con cosas con Depth Anything
        V2 Small (preentrenado).
      - Endpoints /learning/* (camaras, frame, referencia, probar, config).
      - Lectura de frames por el servidor (OpenCV, RTSP por TCP).
      - Sensibilidad global editable (config_volumen.json).
      - Supervisor reducido a visualizacion: sin boton ni endpoints /detectar
        y /segmentar.
      - Redirecciones actualizadas para el nuevo rol.
      - Pendiente: monitor automatico y grafico en el dashboard del usuario.


================================================================================
23. GLOSARIO
================================================================================
learning        Rol que calibra la IA; ve todas las camaras.
Calibrar        Guardar la foto vacia de cada camara y ajustar la
                sensibilidad. No es entrenar una red neuronal.
Foto vacia /    Foto de la habitacion sin nada, usada como punto de
referencia      comparacion. Una por camara.
Profundidad     Estimacion de la distancia de cada punto de la imagen. Es
relativa        relativa (no en metros): sirve para comparar fotos.
Depth Anything  Modelo preentrenado que estima la profundidad desde una sola
V2 Small        imagen (Apache-2.0, ~100 MB).
Umbral          Cuanto debe cambiar la profundidad para marcar un pixel.
Area minima     % de la imagen cambiada necesario para decir "hay cosas".
Camara fija     Camara que no cambia de lugar ni de angulo.
YOLO            Familia de modelos de vision por computador. yolov8n.pt
                (deteccion, 80 clases) ya no se usa en la web; yolov8n-seg
                (segmentacion) es la herramienta de consola piso/pared.
Segmentacion    Clasificar cada pixel (piso, pared u otro).
MJPEG           Video como secuencia de fotos JPEG por HTTP.
RTSP            Protocolo de video de camaras IP; el navegador no lo
                reproduce, pero el servidor si lo lee con OpenCV.
HLS (.m3u8)     Streaming por segmentos, reproducible con hls.js.
JWT             Token de sesion firmado, guardado en cookie httpOnly.
Carga perezosa  El modelo se carga la primera vez que se necesita.
run_in_threadpool  Ejecuta una tarea pesada en un hilo para no bloquear el
                servidor.
CORS            Restriccion del navegador al usar imagenes de otro origen en
                un canvas.
================================================================================
 FIN — DOCUMENTACION v1.6
================================================================================