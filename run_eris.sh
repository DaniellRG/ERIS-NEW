#!/usr/bin/env bash
# Arranca / relanza ERIS (Linux) con log persistente y detención segura.
#
# Patrón de kill seguro: `main[.]py` NUNCA matchea el propio cmdline (el texto
# literal "main[.]py" no contiene "main.py"), así que esta línea no se auto-mata.
# Se excluye además QtWebEngineProcess (su args trae `--application-name=main.py`).
set -u
PROJ="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJ"
PY="$PROJ/.venv-linux/bin/python"
LOG="$PROJ/eris_run.log"

pids=$(ps -eo pid,args | grep -E "bin/python +main[.]py" | grep -vE "WebEngine|grep" | awk '{print $1}')
if [ -n "$pids" ]; then
    echo "Deteniendo instancias previas: $pids"
    kill $pids 2>/dev/null
    sleep 2
fi

setsid nohup "$PY" main.py >> "$LOG" 2>&1 &
newpid=$!
disown
echo "ERIS arrancado: pid=$newpid  (log: $LOG)"

for i in $(seq 1 25); do
    sleep 1
    if ! kill -0 "$newpid" 2>/dev/null; then
        echo "ERIS murió al arrancar. Últimas líneas del log:"
        tail -25 "$LOG"
        exit 1
    fi
done
echo "ERIS viva tras arranque. Tracebacks en log: $(grep -c Traceback "$LOG" 2>/dev/null || echo 0)"