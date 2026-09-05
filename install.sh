#!/usr/bin/env bash
# ============================================================
#  ERIS - instalador one-liner para Linux
#
#  Uso:
#     curl -fsSL https://raw.githubusercontent.com/DaniellRG/ERIS-NEW/main/install.sh | bash
#
#  Instala a ~/.eris/ERIS-NEW (no toca tu workspace de desarrollo),
#  crea el venv, instala dependencias, deja el comando `eris`
#  y abre la ventana de configuracion (wizard) si es la primera vez.
# ============================================================
set -e

ERIS_HOME="${ERIS_HOME:-$HOME/.eris}"
REPO_URL="https://github.com/DaniellRG/ERIS-NEW.git"
REPO="$ERIS_HOME/ERIS-NEW"
BIN_DIR="$HOME/.local/bin"

usage() {
    sed -n '3,12p' "$0"
    exit 0
}
[ "${1:-}" = "--help" ] && usage
[ "${1:-}" = "--dry-run" ] && { echo "  (dry-run) ERIS_HOME=$ERIS_HOME"; echo "  (dry-run) REPO=$REPO"; echo "  (dry-run) BIN_DIR=$BIN_DIR"; exit 0; }

echo "============================================="
echo "  ERIS  -  instalacion para Linux"
echo "============================================="

# 0) Pre-requisitos
for cmd in git python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "!! Falta el comando: $cmd"
        echo "   Instalalo primero, por ejemplo:  sudo pacman -S $cmd   (o tu gestor de paquetes)"
        exit 1
    fi
done

# 1) Clonar (o actualizar) el codigo
mkdir -p "$ERIS_HOME"
if [ -d "$REPO/.git" ]; then
    echo "==> ERIS ya estaba instalado. Actualizando..."
    git -C "$REPO" pull --ff-only || true
else
    echo "==> Descargando ERIS a $REPO ..."
    git clone --depth 1 "$REPO_URL" "$REPO"
fi

cd "$REPO"

# 2) venv
if [ ! -x ".venv-linux/bin/python" ]; then
    echo "==> Creando el entorno virtual..."
    python3 -m venv .venv-linux
fi
PY=".venv-linux/bin/python"

# 3) Dependencias pip
echo "==> Instalando dependencias (requirements-linux.txt)..."
".venv-linux/bin/pip" install --upgrade pip >/dev/null
".venv-linux/bin/pip" install -q -r requirements-linux.txt

# 4) Comando `eris`
mkdir -p "$BIN_DIR"
if [ -e "$BIN_DIR/eris" ]; then
    echo "==> Configurando el launcher en $BIN_DIR/eris (sobreescribe la version vieja)"
    rm -f "$BIN_DIR/eris"
fi
chmod +x "$REPO/eris"
ln -s "$REPO/eris" "$BIN_DIR/eris"

# 5) Dependencias de sistema (aviso, no bloquea)
MISSING_SYS=""
for pkg in brightnessctl xclip; do
    command -v "$pkg" >/dev/null 2>&1 || MISSING_SYS="$MISSING_SYS $pkg"
done
if [ -n "$MISSING_SYS" ]; then
    echo "==> Paquetes de sistema opcionales no detectados:$MISSING_SYS"
    echo "    (brightnessctl: control de brillo | xclip: portapapeles)"
fi

# 6) Ollama (OPCIONAL, para chat 100% local — el modelo se descarga aparte)
if ! command -v ollama >/dev/null 2>&1; then
    echo "==> Ollama no esta instalado. Es OPCIONAL: Eris funciona igual con"
    echo "    internet (key de Gemini). Si queres chat local despues:"
    echo "      curl -fsSL https://ollama.com/install.sh | sh"
    echo "      ollama pull qwen3:8b    <- el modelo, cuando lo quieras bajar"
fi

# 7) Primer arranque con wizard
cat <<'EOF'

ERIS quedo instalado.

Para arrancar:
    eris                 (GUI, abre el configurador en el primer uso)
    eris --cli           (chat por terminal)
    eris --update        (traer la ultima version desde GitHub)
EOF

if [ "${1:-}" = "--no-run" ]; then
    exit 0
fi

if [ -f "$REPO/config/api_keys.json" ]; then
    echo "==> Configuracion existente. Iniciando ERIS..."
    exec "$REPO/eris"
else
    echo "==> Abriendo la configuracion de ERIS (primer arranque)..."
    exec "$REPO/eris" --wizard
fi