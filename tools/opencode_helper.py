#!/usr/bin/env python3
"""
opencode_helper.py — Herramienta para que opencode se comunique con ERIS.

Uso desde opencode (o cualquier script):
    python tools/opencode_helper.py "pregunta para ERIS"      # pregunta y espera respuesta
    python tools/opencode_helper.py --task "tarea para ERIS"  # deja una tarea pendiente
    python tools/opencode_helper.py --status                  # estado del bridge
    python tools/opencode_helper.py --compartir "aprendizaje" # simbiosis: le comparte un aprendizaje
    python tools/opencode_helper.py --estado-real             # fuente de verdad: reporta git+procesos
    python tools/opencode_helper.py --sesion "qué hace el usuario"     # contexto de sesión
    python tools/opencode_helper.py --setup "tarea de config" # pide a ERIS un setup

Puerto: 6789 (localhost)
"""
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

BRIDGE_URL = "http://127.0.0.1:6789"


def _post(endpoint: str, data: dict) -> dict:
    try:
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            f"{BRIDGE_URL}{endpoint}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError:
        return {"status": "error", "message": "Bridge no disponible. ¿Está Eris corriendo?"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _get(endpoint: str) -> dict:
    try:
        with urllib.request.urlopen(f"{BRIDGE_URL}{endpoint}", timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"status": "error", "message": str(e)}


def ask_eris(question: str) -> str:
    """Pregunta algo a ERIS y espera su respuesta (deja la tarea y hace polling)."""
    result = _post("/api/task", {"task": question, "context": "Consulta desde opencode"})
    if result.get("status") == "ok":
        task_id = result.get("task_id")
        if task_id:
            import time
            for _ in range(90):  # esperar hasta 90 segundos
                time.sleep(1)
                resp = _get(f"/api/response/{task_id}")
                if resp.get("status") == "ok":
                    return resp.get("response", {}).get("answer", "Sin respuesta")
                if resp.get("status") == "error":
                    return f"Error: {resp.get('message')}"
            return ("Eris recibió la tarea pero aún no respondió (puede estar "
                    "ocupada; reintentá o mirá su UI).")
    return f"Error: {result.get('message', 'Respuesta inválida')}"


def send_task(task: str, context: str = "") -> str:
    """Envía una tarea a ERIS para que la procese."""
    result = _post("/api/task", {"task": task, "context": context})
    return f"Tarea enviada: {result.get('task_id', 'sin id')}"


def poll_pending() -> str:
    """Ver tareas pendientes que ERIS dejó a opencode (best-effort)."""
    result = _get("/api/status")
    if result.get("status") == "ok":
        return f"Bridge activo. Tareas pendientes para ERIS: {result.get('pending', 0)}"
    return f"Bridge no disponible: {result.get('message', '')}"


def status() -> str:
    """Estado del bridge."""
    return json.dumps(_get("/api/status"), ensure_ascii=False, indent=2)


def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "opencode"


def compartir(texto: str) -> str:
    """Simbiosis de memoria: opencode le comparte un aprendizaje a Eris."""
    import time
    d = _data_dir()
    d.mkdir(parents=True, exist_ok=True)
    name = time.strftime("aprendizaje_%Y%m%d_%H%M%S.md")
    (d / "inbox_conocimiento" / name).write_text(texto, encoding="utf-8")
    return f"Aprendizaje compartido a Eris: {name}"


def estado_real() -> str:
    """Fuente de verdad externa: opencode reporta el estado real del sistema."""
    import subprocess
    import time
    snapshot = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, timeout=8)
        snapshot["git_status"] = r.stdout.strip()[:800] or "(repo limpio)"
    except Exception:
        snapshot["git_status"] = "(no repo en cwd)"
    try:
        r = subprocess.run(["git", "log", "-1", "--oneline"], capture_output=True, text=True, timeout=8)
        snapshot["git_ultimo"] = r.stdout.strip()[:200]
    except Exception:
        pass
    try:
        r = subprocess.run(["ps", "-eo", "pid,comm"], capture_output=True, text=True, timeout=8)
        top = [l.strip() for l in r.stdout.splitlines()[1:] if "main.py" in l or "opencode" in l][:5]
        snapshot["procesos"] = " | ".join(top) or "(sin procesos de Eris/opencode activos)"
    except Exception:
        snapshot["procesos"] = "(error listando procesos)"
    try:
        import os
        snapshot["workspace"] = os.getcwd()
    except Exception:
        pass
    d = _data_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "estado_real.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.dumps(snapshot, ensure_ascii=False, indent=2)


def sesion(resumen: str) -> str:
    """Contexto de sesión: en qué está trabajando el usuario."""
    import time
    d = _data_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "sesion.json").write_text(
        json.dumps({"fecha": time.strftime("%Y-%m-%d %H:%M"), "resumen": resumen},
                   ensure_ascii=False), encoding="utf-8")
    return "Contexto de sesión compartido a Eris."


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    arg = sys.argv[1]

    if arg == "--status":
        print(status())
    elif arg in ("--poll", "--tasks"):
        print(poll_pending())
    elif arg in ("--task", "--send-task") and len(sys.argv) >= 3:
        task = " ".join(sys.argv[2:])
        print(send_task(task))
    elif arg == "--compartir" and len(sys.argv) >= 3:
        print(compartir(" ".join(sys.argv[2:])))
    elif arg == "--estado-real":
        print(estado_real())
    elif arg == "--sesion" and len(sys.argv) >= 3:
        print(sesion(" ".join(sys.argv[2:])))
    elif arg == "--setup" and len(sys.argv) >= 3:
        print(ask_eris(f"[SETUP] Ayudame a configurar: {' '.join(sys.argv[2:])}"))
    else:
        # Por defecto: preguntar a ERIS y esperar su respuesta
        question = " ".join(sys.argv[1:])
        print(ask_eris(question))


if __name__ == "__main__":
    main()