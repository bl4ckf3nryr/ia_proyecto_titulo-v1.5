@echo off
REM ============================================================
REM  iniciar.bat (RAIZ)  -  Login Simple + Emulador Bodega 3D
REM
REM  Hace TODO en un solo doble clic:
REM    1) Detecta cualquier Python compatible (3.9 a 3.13, 64 bits)
REM       o instala Python 3.12 si no hay ninguno.
REM    2) Crea/valida el entorno virtual "venv".
REM    3) Instala dependencias (ruedas binarias; se adapta a la
REM       version de Python, incl. 3.13 donde numpy 1.x no existe).
REM    4) Verifica la estructura del proyecto.
REM    5) Lanza el EMULADOR en otra ventana:
REM          emulador\INSTALAR_Y_EJECUTAR.bat   (puerto 8080)
REM    6) Levanta el servidor central (Uvicorn, puerto 8000).
REM
REM  Opciones:
REM    iniciar.bat --sin-emulador     no lanza el emulador
REM
REM  La ventana NUNCA se cierra sola: si algo falla, queda abierta.
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

title Login Simple + Emulador - Iniciando...

set "ARG_SIN_EMULADOR=0"
if /i "%~1"=="--sin-emulador" set "ARG_SIN_EMULADOR=1"

echo.
echo ============================================================
echo   LOGIN SIMPLE + EMULADOR - INICIANDO
echo ============================================================
echo       Carpeta de trabajo: %CD%
echo.

REM ------------------------------------------------------------
REM Variables de configuracion
REM ------------------------------------------------------------
set "PYTHON_VERSION=3.12.8"
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
set "PYTHON_INSTALADOR=%TEMP%\python-3.12.8-amd64.exe"
set "PYTHON_TAMANO_MIN=20000000"

set "PAQUETES_PIP=fastapi uvicorn[standard] jinja2 pydantic[email] bcrypt PyJWT sqlalchemy python-multipart numpy opencv-python-headless ultralytics transformers"
set "PAQUETES_PY=base_de_datos"

set "CHECK_PY=import importlib.util as u,sys; m=['fastapi','uvicorn','sqlalchemy','bcrypt','jwt','multipart','jinja2','pydantic','numpy','cv2','ultralytics','transformers']; sys.exit(1 if any(u.find_spec(x) is None for x in m) else 0)"

set "EMU_DIR=%~dp0emulador"
set "EMU_BAT=%~dp0emulador\INSTALAR_Y_EJECUTAR.bat"
set "EMU_PORT=8080"
set "MAIN_PORT=8000"

REM ------------------------------------------------------------
REM 0) Detectar Python compatible
REM ------------------------------------------------------------
call :detectar_python
if defined PYTHON_CMD goto :python_listo

REM ------------------------------------------------------------
REM 0.1) No hay Python compatible: descargar e instalar 3.12
REM ------------------------------------------------------------
echo.
echo ============================================================
echo   No se encontro un Python compatible ^(3.9 a 3.13, 64 bits^).
echo   Se instalara automaticamente Python %PYTHON_VERSION%
echo ============================================================
echo.

if exist "%PYTHON_INSTALADOR%" (
    for %%A in ("%PYTHON_INSTALADOR%") do set TAMANO_CACHE=%%~zA
    if !TAMANO_CACHE! GEQ %PYTHON_TAMANO_MIN% (
        echo       Reutilizando instalador cacheado ^(!TAMANO_CACHE! bytes^).
        goto :instalar_python
    ) else (
        echo       Instalador cacheado corrupto. Eliminando...
        del /q "%PYTHON_INSTALADOR%"
    )
)

echo       Descargando Python %PYTHON_VERSION%...
echo       URL: %PYTHON_URL%
echo       Destino: %PYTHON_INSTALADOR%
echo.

where curl >nul 2>nul
if not errorlevel 1 (
    curl -L -f -o "%PYTHON_INSTALADOR%" "%PYTHON_URL%"
    if errorlevel 1 (
        echo       [AVISO] curl fallo. Probando con PowerShell...
        goto :descargar_powershell
    )
    goto :verificar_descarga
)

:descargar_powershell
powershell -NoProfile -Command ^
    "$ProgressPreference='SilentlyContinue';" ^
    "try {" ^
    "  Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALADOR%' -UseBasicParsing;" ^
    "  exit 0" ^
    "} catch { exit 1 }"
if errorlevel 1 (
    echo   [ERROR] No se pudo descargar el instalador.
    echo   Descarga manualmente desde: %PYTHON_URL%
    echo   Guardalo como: %PYTHON_INSTALADOR%
    goto :error_final
)

:verificar_descarga
if not exist "%PYTHON_INSTALADOR%" (
    echo   [ERROR] El archivo no se descargo.
    goto :error_final
)

for %%A in ("%PYTHON_INSTALADOR%") do set TAMANO=%%~zA
echo       Tamano descargado: !TAMANO! bytes.

if !TAMANO! LSS %PYTHON_TAMANO_MIN% (
    echo   [ERROR] La descarga fallo ^(archivo demasiado pequeno^).
    del /q "%PYTHON_INSTALADOR%"
    goto :error_final
)

echo       Descarga completa y valida.
echo.

:instalar_python
echo       Instalando Python %PYTHON_VERSION% silenciosamente...
echo       ^(esto puede tardar 1-2 minutos^)
echo.

"%PYTHON_INSTALADOR%" /quiet ^
    InstallAllUsers=0 ^
    PrependPath=1 ^
    Include_launcher=1 ^
    Include_pip=1 ^
    Include_test=0 ^
    Include_doc=0 ^
    Include_tcltk=1 ^
    SimpleInstall=1 ^
    /L*V "%TEMP%\python_install.log"

if errorlevel 1 (
    echo       [AVISO] El instalador devolvio un codigo distinto de 0.
    echo       Log: %TEMP%\python_install.log
)

echo       Esperando a que el instalador termine...
timeout /t 5 /nobreak >nul

echo       Verificando instalacion...
call :detectar_python
if not defined PYTHON_CMD (
    echo   [ERROR] La instalacion no se completo.
    echo   Reinicia Windows y ejecuta iniciar.bat de nuevo.
    goto :error_final
)

echo       Python instalado correctamente: !PY_VERSION!
echo.

:python_listo
echo.
echo [1/6] Python compatible: !PY_VERSION!   ^(!PYTHON_CMD!^)
echo.

REM ------------------------------------------------------------
REM 2) Validar/Crear entorno virtual
REM ------------------------------------------------------------
echo [2/6] Validando entorno virtual...

set "VENV_OK=1"
if not exist "venv\Scripts\python.exe"    set "VENV_OK=0"
if not exist "venv\Scripts\activate.bat"  set "VENV_OK=0"

if "!VENV_OK!"=="1" (
    call :version_ok "%~dp0venv\Scripts\python.exe"
    if errorlevel 1 set "VENV_OK=0"
)

if "!VENV_OK!"=="0" (
    if exist "venv\" (
        echo       Eliminando "venv" anterior ^(roto o con Python incompatible^)...
        rmdir /s /q venv
        if exist "venv\" (
            echo   [ERROR] No se pudo borrar "venv". Cierra programas que lo usen.
            goto :error_final
        )
    )

    echo       Creando entorno virtual con !PYTHON_CMD! ...
    !PYTHON_CMD! -m venv venv
    if errorlevel 1 (
        echo   [ERROR] No se pudo crear el entorno virtual.
        goto :error_final
    )

    if not exist "venv\Scripts\python.exe" (
        echo   [ERROR] El entorno no quedo bien.
        goto :error_final
    )
    echo       Entorno virtual creado.
) else (
    echo       Entorno virtual OK.
)
echo.

REM ------------------------------------------------------------
REM 3) Rutas absolutas del venv
REM ------------------------------------------------------------
set "VENV_PY=%~dp0venv\Scripts\python.exe"

if not exist "!VENV_PY!" (
    echo   [ERROR] No se encuentra: !VENV_PY!
    goto :error_final
)

for /f "tokens=2" %%v in ('"!VENV_PY!" --version 2^>^&1') do set "VENV_VERSION=%%v"
echo [3/6] Python del venv: !VENV_VERSION! ^(64 bits^)

"!VENV_PY!" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo       pip no disponible en el venv. Reparando con ensurepip...
    "!VENV_PY!" -m ensurepip --upgrade
    if errorlevel 1 (
        echo   [ERROR] No se pudo reparar pip.
        goto :error_final
    )
)
echo.

REM ------------------------------------------------------------
REM Lanzar el EMULADOR (en paralelo, en su propia ventana)
REM ------------------------------------------------------------
if "!ARG_SIN_EMULADOR!"=="1" (
    echo       Emulador omitido ^(--sin-emulador^).
    echo.
) else (
    call :lanzar_emulador
)

REM ------------------------------------------------------------
REM 4) Instalar dependencias
REM ------------------------------------------------------------
echo [4/6] Instalando dependencias...

if not exist "requirements.txt" (
    echo   [ERROR] No se encuentra requirements.txt en:
    echo           %CD%
    goto :error_final
)

for %%A in ("requirements.txt") do set TAMANO_REQ=%%~zA
if !TAMANO_REQ! LSS 10 (
    echo   [ERROR] requirements.txt esta vacio.
    goto :error_final
)
echo       requirements.txt detectado ^(!TAMANO_REQ! bytes^).

REM Se comprueba la PRESENCIA de cada paquete ^(incluye transformers^)
"!VENV_PY!" -c "!CHECK_PY!" >nul 2>nul
if not errorlevel 1 goto :deps_ok

echo       Faltan paquetes. Instalando ^(puede tardar varios minutos
echo       la primera vez: ultralytics y torch pesan bastante^)...
echo.

"!VENV_PY!" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 echo       [AVISO] No se pudo actualizar pip/setuptools/wheel. Se continua.

set "REQ_FILE=requirements.txt"

echo       Instalando NumPy mediante paquete binario...
"!VENV_PY!" -m pip install --only-binary=:all: "numpy>=1.26.4,<2.0.0"
if not errorlevel 1 goto :instalar_requirements

echo       [AVISO] No hay NumPy 1.x binario para esta version de Python.
echo       Se usara el NumPy compatible mas reciente ^(sin el pin del proyecto^).
"!VENV_PY!" -m pip install --only-binary=:all: numpy
if errorlevel 1 (
    echo   [ERROR] No existe ninguna rueda binaria de NumPy para este Python.
    echo   Comprueba Internet y que Python sea de 64 bits entre 3.9 y 3.13.
    goto :error_final
)
call :requirements_flexible

:instalar_requirements
echo       Instalando !REQ_FILE! ...
"!VENV_PY!" -m pip install --prefer-binary -r "!REQ_FILE!"
if not errorlevel 1 goto :verificar_deps

if /i "!REQ_FILE!"=="requirements.txt" (
    echo       [AVISO] Fallo con el pin de NumPy. Reintentando sin el...
    call :requirements_flexible
    "!VENV_PY!" -m pip install --prefer-binary -r "!REQ_FILE!"
    if not errorlevel 1 goto :verificar_deps
)
goto :deps_individual

:verificar_deps
echo       Verificando instalacion...
"!VENV_PY!" -c "!CHECK_PY!" >nul 2>nul
if not errorlevel 1 goto :deps_instaladas

:deps_individual
echo.
echo   [AVISO] pip -r no dejo todo disponible. Instalando paquete por paquete...
echo.
for %%P in (%PAQUETES_PIP%) do (
    echo       Instalando %%P ...
    "!VENV_PY!" -m pip install --prefer-binary "%%P"
    if errorlevel 1 echo       [AVISO] Fallo la instalacion de %%P
)
echo.
echo       Verificando instalacion final...
"!VENV_PY!" -c "!CHECK_PY!" >nul 2>nul
if errorlevel 1 (
    echo   [ERROR] No se pudieron instalar todos los paquetes.
    echo   Revisa los [AVISO] de arriba para ver cual fallo.
    goto :error_final
)

:deps_instaladas
echo       Dependencias instaladas y verificadas.
goto :deps_fin

:deps_ok
echo       Dependencias ya presentes y funcionales.

:deps_fin
"!VENV_PY!" -m uvicorn --version >nul 2>nul
if errorlevel 1 (
    echo   [ERROR] uvicorn no responde ^(instalacion corrupta^).
    goto :error_final
)
echo.

REM ------------------------------------------------------------
REM 5) Verificar estructura del proyecto
REM ------------------------------------------------------------
echo [5/6] Verificando estructura del proyecto...

if not exist "main.py" (
    echo   [ERROR] No se encuentra main.py en:
    echo           %CD%
    goto :error_final
)
echo       main.py OK.

if not exist "requirements.txt" (
    echo   [ERROR] No se encuentra requirements.txt.
    goto :error_final
)
echo       requirements.txt OK.

if not exist "base_de_datos\" (
    echo   [ERROR] No existe la carpeta "base_de_datos\".
    echo   Estructura minima:
    echo     base_de_datos\  templates\  static\  main.py  requirements.txt
    goto :error_final
)
echo       base_de_datos\ OK.

if not exist "templates\"  echo       [AVISO] No existe "templates\".
if not exist "static\"     echo       [AVISO] No existe "static\".

echo       Verificando archivos __init__.py ...
for %%D in (%PAQUETES_PY%) do (
    if exist "%%D\" (
        if not exist "%%D\__init__.py" (
            echo       Creando %%D\__init__.py faltante...
            type nul > "%%D\__init__.py"
            if errorlevel 1 (
                echo       [AVISO] No se pudo crear %%D\__init__.py
            ) else (
                echo       %%D\__init__.py creado.
            )
        ) else (
            echo       %%D\__init__.py OK.
        )
    )
)

for %%F in (conexion.py modelos.py usuarios.py) do (
    if not exist "base_de_datos\%%F" (
        echo       [AVISO] Falta base_de_datos\%%F
    )
)

echo       Verificando import de base_de_datos ...
"!VENV_PY!" -c "import base_de_datos" >nul 2>nul
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   [ERROR] No se puede importar "base_de_datos".
    echo ============================================================
    echo   Carpeta actual: %CD%
    echo   Python: !VENV_PY!
    echo.
    echo   Contenido de la carpeta actual:
    dir /b
    echo.
    if exist "base_de_datos\" (
        echo   Contenido de base_de_datos\:
        dir /b "base_de_datos\"
    )
    echo.
    goto :error_final
)
echo       base_de_datos importable. OK.
echo.

REM ------------------------------------------------------------
REM 6) Levantar servidor central
REM ------------------------------------------------------------
echo [6/6] Iniciando servidor Uvicorn...
echo.
echo ============================================================
echo   SERVIDOR CENTRAL
echo     App:       http://localhost:%MAIN_PORT%
echo     Docs:      http://localhost:%MAIN_PORT%/docs
echo     Health:    http://localhost:%MAIN_PORT%/health
echo     Demo:      demo@example.com / demo1234
echo.
if "!ARG_SIN_EMULADOR!"=="0" (
echo   EMULADOR BODEGA 3D  ^(ventana aparte^)
echo     Interfaz:  http://127.0.0.1:%EMU_PORT%/
echo     Camara:    http://127.0.0.1:%EMU_PORT%/camera
echo     MJPEG:     http://127.0.0.1:%EMU_PORT%/video.mjpg
echo.
)
echo   Para detener el servidor central:  Ctrl + C
echo ============================================================
echo.

title Login Simple - Servidor central ^(puerto %MAIN_PORT%^)

start "" cmd /c "timeout /t 2 >nul && start http://localhost:%MAIN_PORT%"

REM --- Uvicorn en primer plano. El .bat se queda esperando.
REM --- Se excluye "emulador" del autoreload para que sus archivos
REM --- no reinicien el servidor central.
"!VENV_PY!" -m uvicorn main:app --reload --reload-exclude "emulador/*" --host 127.0.0.1 --port %MAIN_PORT%

REM --- Si llegamos aqui, uvicorn termino (Ctrl+C o crash) ---
echo.
echo ============================================================
echo   Uvicorn termino.
echo ============================================================
echo.
echo   Si el servidor se cerro solo, revisa los mensajes
echo   anteriores en esta ventana.
echo.

call :puerto_escuchando %EMU_PORT%
if errorlevel 1 goto :fin_ok

echo   El emulador sigue activo en el puerto %EMU_PORT%.
choice /c SN /t 10 /d N /m "  Cerrar tambien el emulador (S/N)"
if errorlevel 2 goto :fin_ok
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%EMU_PORT% .*LISTENING"') do taskkill /F /T /PID %%P >nul 2>nul
echo       Emulador detenido.
goto :fin_ok


REM ============================================================
REM ETIQUETAS DE CIERRE
REM ============================================================

:error_final
echo.
echo ============================================================
echo   PROCESO DETENIDO POR UN ERROR.
echo ============================================================
echo.
echo   Lee los mensajes anteriores para ver la causa.
echo   Esta ventana NO se cerrara automaticamente.
echo   ^(Si lanzaste el emulador, sigue en su propia ventana.^)
echo.
goto :fin_ok

:fin_ok
echo.
echo   Presiona cualquier tecla para cerrar esta ventana...
pause >nul
endlocal
exit /b 0


REM ============================================================
REM SUBRUTINA: version_ok  ^(comando python como argumentos^)
REM   Exito si es Python 3.9 - 3.13 de 64 bits.
REM ============================================================
:version_ok
%* -c "import sys,struct; sys.exit(0 if ((3,9)<=sys.version_info[:2]<=(3,13) and struct.calcsize('P')*8==64) else 1)" >nul 2>nul
exit /b %errorlevel%


REM ============================================================
REM SUBRUTINA: probar_python  ^(comando python como argumentos^)
REM   Si es compatible fija PYTHON_CMD y PY_VERSION.
REM ============================================================
:probar_python
call :version_ok %*
if errorlevel 1 exit /b 1
set "PYTHON_CMD=%*"
for /f "tokens=2" %%v in ('%* --version 2^>^&1') do set "PY_VERSION=%%v"
exit /b 0


REM ============================================================
REM SUBRUTINA: detectar_python
REM   Orden: launcher "py" ^(3.12, 3.11, 3.13, 3.10, 3.9^),
REM   luego "python" del PATH y por ultimo rutas tipicas.
REM ============================================================
:detectar_python
set "PYTHON_CMD="
set "PY_VERSION="

for %%V in (3.12 3.11 3.13 3.10 3.9) do (
    if not defined PYTHON_CMD call :probar_python py -%%V
)
if defined PYTHON_CMD exit /b 0

call :probar_python python
if defined PYTHON_CMD exit /b 0

for %%P in (
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python311\python.exe"
    "%LocalAppData%\Programs\Python\Python313\python.exe"
    "%LocalAppData%\Programs\Python\Python310\python.exe"
    "%LocalAppData%\Programs\Python\Python39\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python313\python.exe"
    "C:\Python310\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python310\python.exe"
) do (
    if not defined PYTHON_CMD (
        if exist %%P call :probar_python %%P
    )
)
exit /b 0


REM ============================================================
REM SUBRUTINA: requirements_flexible
REM   Crea una copia de requirements.txt sin la linea de numpy
REM   para que pip no choque con el NumPy ya instalado.
REM ============================================================
:requirements_flexible
findstr /v /b /i "numpy" "requirements.txt" > "%TEMP%\req_sin_numpy.txt"
set "REQ_FILE=%TEMP%\req_sin_numpy.txt"
exit /b 0


REM ============================================================
REM SUBRUTINA: puerto_escuchando  ^(puerto^)
REM   Exito si hay algo escuchando en ese puerto.
REM ============================================================
:puerto_escuchando
netstat -ano | findstr /R /C:":%~1 .*LISTENING" >nul 2>nul
exit /b %errorlevel%


REM ============================================================
REM SUBRUTINA: lanzar_emulador
REM   Abre emulador\INSTALAR_Y_EJECUTAR.bat en una ventana nueva
REM   ^(con su propio entorno^), sin heredar las variables de este
REM   script para que no interfieran con las suyas.
REM ============================================================
:lanzar_emulador
echo       Emulador Bodega 3D...

if not exist "%EMU_BAT%" (
    echo       [AVISO] No se encuentra:
    echo               %EMU_BAT%
    echo       Se continua solo con el servidor central.
    echo.
    exit /b 0
)

call :puerto_escuchando %EMU_PORT%
if not errorlevel 1 (
    echo       El puerto %EMU_PORT% ya esta en uso: se asume que el emulador
    echo       ya esta corriendo. No se lanza otra copia.
    echo.
    exit /b 0
)

setlocal
set "PYTHON_CMD="
set "PY_VERSION="
set "PYTHON_VERSION="
set "PYTHON_URL="
set "PYTHON_INSTALADOR="
set "PYTHON_TAMANO_MIN="
set "PAQUETES_PIP="
set "PAQUETES_PY="
set "CHECK_PY="
set "VENV_PY="
set "VENV_OK="
set "VENV_VERSION="
set "REQ_FILE="
start "Emulador Bodega 3D" /D "%EMU_DIR%" cmd /k "INSTALAR_Y_EJECUTAR.bat"
endlocal

echo       Lanzado en una ventana aparte ^(puerto %EMU_PORT%^).
echo       La primera vez instala Playwright y Chromium: puede tardar.
echo.
exit /b 0
