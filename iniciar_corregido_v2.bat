@echo off
REM ============================================================
REM  iniciar.bat - Automatiza TODO: Python + entorno + servidor
REM  Login Simple - FastAPI + SQLite
REM
REM  Esta version garantiza que la ventana NUNCA se cierre
REM  automaticamente. Si algo falla, se queda abierta para
REM  que puedas leer el error.
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

title Login Simple - Iniciando...

echo.
echo ============================================================
echo   LOGIN SIMPLE - INICIANDO
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

set "PAQUETES_PIP=fastapi uvicorn[standard] jinja2 pydantic[email] bcrypt PyJWT sqlalchemy python-multipart"
set "PAQUETES_PY=base_de_datos"

REM ------------------------------------------------------------
REM 0) Detectar Python compatible
REM ------------------------------------------------------------
call :detectar_python
if defined PYTHON_CMD goto :python_listo

REM ------------------------------------------------------------
REM 0.1) No hay Python: descargar e instalar
REM ------------------------------------------------------------
echo.
echo ============================================================
echo   No se encontro Python 3.12 compatible.
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
echo [1/6] Python compatible: !PY_VERSION!
echo.

REM ------------------------------------------------------------
REM 2) Validar/Crear entorno virtual
REM ------------------------------------------------------------
echo [2/6] Validando entorno virtual...

set "VENV_OK=1"

if not exist "venv\" (
    set "VENV_OK=0"
) else (
    if not exist "venv\Scripts\python.exe"    set "VENV_OK=0"
    if not exist "venv\Scripts\activate.bat"  set "VENV_OK=0"
    if not exist "venv\Scripts\pip.exe"       set "VENV_OK=0"
)

if "!VENV_OK!"=="1" (
    for /f "tokens=2" %%v in ('"venv\Scripts\python.exe" --version 2^>^&1') do set VENV_VER=%%v
    for /f "tokens=1,2 delims=." %%a in ("!VENV_VER!") do (
        set "VMAJOR=%%a"
        set "VMINOR=%%b"
    )
    if not "!VMAJOR!.!VMINOR!"=="3.12" set "VENV_OK=0"
    REM Este proyecto fija Python 3.12 para evitar que pip intente
    REM compilar NumPy 1.26.4 en versiones no compatibles.
)

if "!VENV_OK!"=="0" (
    if exist "venv\" (
        echo       Eliminando "venv" anterior ^(incompatible o roto^)...
        rmdir /s /q venv
        if exist "venv\" (
            echo   [ERROR] No se pudo borrar "venv".
            goto :error_final
        )
    )

    echo       Creando entorno virtual con !PYTHON_CMD! ...
    %PYTHON_CMD% -m venv venv
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

for /f "tokens=2" %%v in ('"!VENV_PY!" --version 2^>^&1') do set VENV_VERSION=%%v
REM Comprobar arquitectura sin FOR /F: evita errores con rutas que contienen espacios.
"!VENV_PY!" -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8 == 64 else 1)" >nul 2>nul
if errorlevel 1 (
    echo   [ERROR] Se necesita Python de 64 bits para NumPy, OpenCV y YOLO.
    echo   No se pudo validar la arquitectura del Python del entorno virtual.
    goto :error_final
)
echo [3/6] Python del venv: !VENV_VERSION!
echo.

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

"!VENV_PY!" -c "import fastapi, uvicorn, sqlalchemy, bcrypt, jwt, multipart, jinja2, pydantic, numpy, cv2, ultralytics" >nul 2>nul
if errorlevel 1 (
    echo       Faltan paquetes. Instalando desde requirements.txt...

    "!VENV_PY!" -m pip install --upgrade pip setuptools wheel
    if errorlevel 1 (
        echo   [ERROR] No se pudieron actualizar pip, setuptools y wheel.
        goto :error_final
    )

    REM Instalar NumPy desde una rueda binaria: evita compilar C/C++ en Windows.
    echo       Instalando NumPy mediante paquete binario...
    "!VENV_PY!" -m pip install --only-binary=:all: "numpy>=1.26.4,<2.0.0"
    if errorlevel 1 (
        echo   [ERROR] No existe una rueda binaria de NumPy compatible.
        echo   Comprueba que Python sea 3.12 de 64 bits y que haya Internet.
        goto :error_final
    )

    REM --prefer-binary prioriza ruedas precompiladas para las demas dependencias.
    echo       Instalando requirements.txt...
    "!VENV_PY!" -m pip install --prefer-binary -r requirements.txt
    if errorlevel 1 (
        echo   [ERROR] Fallo pip install -r requirements.txt
        echo   Se detiene aqui para mostrar el error real; no se fuerza una compilacion.
        goto :error_final
    )

    echo       Verificando instalacion...
    "!VENV_PY!" -c "import fastapi, uvicorn, sqlalchemy, bcrypt, jwt, multipart, jinja2, pydantic, numpy, cv2, ultralytics" >nul 2>nul
    if errorlevel 1 (
        echo.
        echo   [AVISO] pip install no dejo los paquetes disponibles.
        echo   Forzando instalacion individual...
        echo.

        for %%P in (%PAQUETES_PIP%) do (
            echo       Instalando %%P ...
            "!VENV_PY!" -m pip install "%%P"
            if errorlevel 1 echo       [AVISO] Fallo la instalacion de %%P
        )

        echo.
        echo       Verificando instalacion final...
        "!VENV_PY!" -c "import fastapi, uvicorn, sqlalchemy, bcrypt, jwt, multipart, jinja2, pydantic, numpy, cv2, ultralytics" >nul 2>nul
        if errorlevel 1 (
            echo   [ERROR] No se pudieron instalar los paquetes.
            goto :error_final
        )
    )

    echo       Dependencias instaladas y verificadas.
) else (
    echo       Dependencias ya presentes y funcionales.
)

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
REM 6) Levantar servidor
REM ------------------------------------------------------------
echo [6/6] Iniciando servidor Uvicorn...
echo.
echo ============================================================
echo   Servidor:  http://localhost:8000
echo   Docs:      http://localhost:8000/docs
echo   Health:    http://localhost:8000/health
echo.
echo   Usuario demo:  demo@example.com / demo1234
echo.
echo   Para detener el servidor:  Ctrl + C
echo ============================================================
echo.

start "" cmd /c "timeout /t 2 >nul && start http://localhost:8000"

REM --- Uvicorn en primer plano. El .bat se queda esperando ---
"!VENV_PY!" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

REM --- Si llegamos aqui, uvicorn termino (Ctrl+C o crash) ---
echo.
echo ============================================================
echo   Uvicorn termino.
echo ============================================================
echo.
echo   Si el servidor se cerro solo, revisa los mensajes
echo   anteriores en esta ventana.
echo.
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
echo.
goto :fin_ok

:fin_ok
echo.
echo   Presiona cualquier tecla para cerrar esta ventana...
pause >nul
endlocal
exit /b 0


REM ============================================================
REM SUBRUTINA: detectar_python
REM ============================================================
:detectar_python
set "PYTHON_CMD="
set "PY_VERSION="

for %%V in (3.12) do (
    if not defined PYTHON_CMD (
        py -%%V --version >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_CMD=py -%%V"
            for /f "tokens=2" %%v in ('py -%%V --version 2^>^&1') do set PY_VERSION=%%v
        )
    )
)
if defined PYTHON_CMD exit /b 0

for %%P in (
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "C:\Python312\python.exe"
    "C:\Program Files\Python312\python.exe"
) do (
    if not defined PYTHON_CMD (
        if exist %%P (
            %%P -c "import sys; sys.exit(0)" >nul 2>nul
            if not errorlevel 1 (
                set "PYTHON_CMD=%%~P"
                for /f "tokens=2" %%v in ('%%~P --version 2^>^&1') do set PY_VERSION=%%v
            )
        )
    )
)
exit /b 0