@echo off
cd /d "%~dp0"
title Instalador de ERIS AI
echo ====================================
echo   INSTALADOR DE ERIS AI
echo ====================================
echo.

:: ── Buscar Python ──
set PYTHON=python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.12+ desde python.org
    pause
    exit /b 1
)

:: ── Crear .venv si no existe ──
if not exist ".venv\" (
    echo Creando entorno virtual...
    "%PYTHON%" -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear .venv
        pause
        exit /b 1
    )
)

:: ── Activar e instalar dependencias ──
echo Instalando dependencias...
.venv\Scripts\python.exe -m pip install --upgrade pip -q
.venv\Scripts\python.exe -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Fallo al instalar dependencias
    pause
    exit /b 1
)

:: ── Ejecutar setup (API keys, nombre, acceso directo) ──
echo.
echo Configuracion inicial...
.venv\Scripts\python.exe install.py
if errorlevel 1 (
    echo [ERROR] Configuracion cancelada
    pause
    exit /b 1
)

echo.
echo ====================================
echo   INSTALACION COMPLETADA
echo ====================================
echo.
echo Hace doble clic en ERIS.lnk del escritorio
echo para iniciar ERIS.
echo.
pause
