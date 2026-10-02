#!/bin/bash
# ============================================================
# ERIS - Script de lanzamiento (Linux)
# Arranca ERIS desde el menú de aplicaciones o terminal
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Verificar venv
if [ ! -d ".venv-linux" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv .venv-linux
fi

source .venv-linux/bin/activate

# Verificar dependencias críticas
for pkg in sounddevice pyqt6 PyQt6.QtCore; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        echo "Error: Falta el paquete $pkg. Instalando..."
        pip install -q "$pkg" || echo "ERROR: No se pudo instalar $pkg"
    fi
done

# Setencias de entorno
export PYTHONIOENCODING="utf-8"
export QT_QPA_PLATFORM=wayland
export QT_LOGGING_RULES="*.debug=false;qt.qpa.*=false"

# Iniciar ERIS
echo "Iniciando ERIS AI..."
exec python3 main.py "$@"
