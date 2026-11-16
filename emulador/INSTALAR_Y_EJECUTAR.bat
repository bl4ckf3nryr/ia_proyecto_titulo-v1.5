@echo off
if /i "%~1"=="__RUN__" goto :main
start "" cmd /k ""%~f0" __RUN__"
exit /b 0

:main
setlocal EnableExtensions
title Simulador de Bodega 3D
color 0A
cd /d "%~dp0"

echo ============================================================
echo   SIMULADOR DE BODEGA 3D
echo ============================================================
echo Carpeta: %CD%
echo.

set "FALTA="
if not exist "app.py" set "FALTA=%FALTA% app.py"
if not exist "state.py" set "FALTA=%FALTA% state.py"
if not exist "camera.py" set "FALTA=%FALTA% camera.py"
if not exist "camera_worker.py" set "FALTA=%FALTA% camera_worker.py"
if not exist "templates\index.html" set "FALTA=%FALTA% templates\index.html"
if not exist "templates\camera.html" set "FALTA=%FALTA% templates\camera.html"
if not exist "templates\viewer3d.html" set "FALTA=%FALTA% templates\viewer3d.html"
if defined FALTA (
    echo [ERROR] Faltan archivos:%FALTA%
    pause
    exit /b 1
)
echo [OK] Archivos presentes.

:: Verificar si existe el .venv
if exist ".venv\Scripts\python.exe" (
    set "PY=%CD%\.venv\Scripts\python.exe"
    echo [OK] Usando .venv existente.
) else (
    echo [ERROR] No se encontro la carpeta .venv en esta ruta.
    echo Por favor, abre una terminal aqui y ejecuta: python -m venv .venv
    pause
    exit /b 1
)

echo Python: "%PY%"

:: Intentar actualizar pip y dependencias con el entorno virtual
"%PY%" -m pip install --upgrade pip >nul 2>nul

echo Instalando dependencias ...
"%PY%" -m pip install Flask Pillow playwright

echo Instalando Chromium para Playwright ...
"%PY%" -m playwright install chromium
if errorlevel 1 (
    echo [AVISO] No se pudo instalar Chromium para Playwright.
    echo         La camara mostrara 'SIN SEÑAL' hasta resolverlo.
)

:: Matar el proceso si el puerto 8080 esta ocupado
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%P >nul 2>nul
)

:: Abrir el navegador despues de 5 segundos
start "" /B cmd /c "timeout /t 5 >nul & start http://127.0.0.1:8080/"

echo.
echo Iniciando servidor (CTRL+C para detener) ...
echo.

"%PY%" -u app.py

echo.
echo Servidor detenido.
pause
endlocal
exit /b 0