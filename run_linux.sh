#!/usr/bin/env bash
# ============================================================
#  ERIS - Launch script para LINUX (CachyOS / Arch)
#  Crea el venv, instala dependencias y arranca Eris.
# ------------------------------------------------------------
#  Uso:   ./run_linux.sh            (instala y arranca)
#         ./run_linux.sh --update   (solo actualiza deps)
#  Nota:  chmod +x run_linux.sh
# ============================================================
set -e
cd "$(dirname "$0")"

PYTHON_BIN="python3"
# Preferir python del sistema si existe
command -v python3.12 >/dev/null 2>&1 && PYTHON_BIN="python3.12"

echo "==> Preparando entorno Linux para ERIS..."

# 1) Paquetes de sistema (deja pasar si ya estan instalados)
echo "==> Asegurando paquetes de sistema (portaudio)..."
for pkg in portaudio pipewire-pulse; do
    if ! pacman -Qs "$pkg" >/dev/null 2>&1; then
        echo "   Falta: $pkg -> intentando instalar con sudo pacman -S $pkg"
        sudo pacman -S --noconfirm "$pkg" || echo "   (instala $pkg manualmente si hace falta)"
    fi
done

# 2) venv
if [ ! -d ".venv-linux" ]; then
    echo "==> Creando .venv-linux ..."
    "$PYTHON_BIN" -m venv .venv-linux
fi
source .venv-linux/bin/activate

# 3) Dependencias pip
echo "==> Instalando dependencias pip (requirements-linux.txt)..."
pip install --upgrade pip >/dev/null
pip install -r requirements-linux.txt

# 4) Playwright browser (mejor no forzar aqui, se instala bajo demanda)
# echo "==> Instalando navegador Playwright..."
# python -m playwright install chromium

if [ "$1" = "--update" ]; then
    echo "==> Dependencias actualizadas. Eris no se lanzo (modo --update)."
    exit 0
fi

# 5) Config OS
export ERIS_OBSIDIAN_VAULT="${ERIS_OBSIDIAN_VAULT:-$HOME/Eris_NEW/BaseDatosObsidian/BaseObsiEris}"
export PYTHONIOENCODING="utf-8"

echo "==> Lanzando ERIS en Linux..."
python main.py
