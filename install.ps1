# ============================================================
#  ERIS - Instalador one-liner para WINDOWS
#  Uso (PowerShell):
#     powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/DaniellRG/ERIS-NEW/main/install.ps1 | iex"
#
#  Instala a %USERPROFILE%\.eris\ERIS-NEW (no toca tu workspace de
#  desarrollo), crea .venv, instala deps, deja el comando `eris`
#  y abre la ventana de configuracion (wizard) si es el primer uso.
# ============================================================
$ErrorActionPreference = "Stop"

$REPO_URL = "https://github.com/DaniellRG/ERIS-NEW.git"
$ERIS_HOME = Join-Path $HOME ".eris"
$REPO      = Join-Path $ERIS_HOME "ERIS-NEW"
$WINDOWS_APPS = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"

Write-Host "============================================="
Write-Host "  ERIS  -  instalacion para Windows"
Write-Host "============================================="

# 0) Pre-requisitos
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "!! Falta git. Instalalo con:"
    Write-Host "   winget install Git.Git"
    exit 1
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "!! Falta Python. Instalalo con:"
    Write-Host "   winget install Python.Python.3.12"
    exit 1
}

# 1) Clonar (o actualizar)
New-Item -ItemType Directory -Force -Path $ERIS_HOME | Out-Null
if (Test-Path (Join-Path $REPO ".git")) {
    Write-Host "==> ERIS ya estaba instalado. Actualizando..."
    Push-Location $REPO
    git pull --ff-only | Out-Null
    Pop-Location
} else {
    Write-Host "==> Descargando ERIS a $REPO ..."
    git clone --depth 1 $REPO_URL $REPO
}
Set-Location $REPO

# 2) venv
$PY = Join-Path $REPO ".venv\Scripts\python.exe"
if (-not (Test-Path $PY)) {
    Write-Host "==> Creando el entorno virtual..."
    python -m venv .venv
}

# 3) Dependencias pip
Write-Host "==> Instalando dependencias (requirements.txt)..."
& python -m pip install --upgrade pip | Out-Null
& $PY -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit 1 }

# 4) Comando `eris`
New-Item -ItemType Directory -Force -Path $WINDOWS_APPS | Out-Null
$ERIS_CMD = Join-Path $WINDOWS_APPS "eris.cmd"
@"
@echo off
@rem ERIS launcher (generado por install.ps1)
set "ERIS_REPO=$REPO"
set "ERIS_PY=$PY"
set PYTHONIOENCODING=utf-8
if "%1"=="--update" (
    git -C "%ERIS_REPO%" pull --ff-only
    "%ERIS_PY%" -m pip install --upgrade -r "%ERIS_REPO%\requirements.txt"
    echo ERIS actualizado.
    exit /b 0
)
if "%1"=="--wizard" (
    "%ERIS_PY%" "%ERIS_REPO%\setup_wizard.py"
    exit /b 0
)
if "%1"=="--check" (
    "%ERIS_PY%" "%ERIS_REPO%\setup_wizard.py" --check
    exit /b 0
)
if "%1"=="--cli" (
    "%ERIS_PY%" "%ERIS_REPO%\eris_cli.py" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b 0
)
if not exist "%ERIS_REPO%\config\api_keys.json" (
    echo Primera vez: abriendo la configuracion de ERIS...
    "%ERIS_PY%" "%ERIS_REPO%\setup_wizard.py"
    exit /b 0
)
"%ERIS_PY%" "%ERIS_REPO%\main.py"
"@ | Set-Content -Encoding ASCII -Path $ERIS_CMD

# 5) Ollama (OPCIONAL, chat 100% local - el modelo va aparte)
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "==> Ollama OPCIONAL (chat sin internet). Eris funciona igual con internet."
    Write-Host "    Si lo queres:  winget install Ollama.Ollama"
    Write-Host "    El modelo se descarga aparte:  ollama pull qwen3:8b"
}

# 6) Primer arranque con wizard
@"

ERIS quedo instalado.

Para arrancar, abri cualquier terminal y escribi:
    eris                 (GUI, abre el configurador en el primer uso)
    eris --cli           (chat por terminal)
    eris --update        (traer la ultima version desde GitHub)

"@

if ($args -contains "--no-run") { exit 0 }

if (Test-Path (Join-Path $REPO "config\api_keys.json")) {
    Write-Host "==> Configuracion existente. Iniciando ERIS..."
    & $ERIS_CMD
} else {
    Write-Host "==> Abriendo la configuracion de ERIS (primer arranque)..."
    & $PY (Join-Path $REPO "setup_wizard.py")
}