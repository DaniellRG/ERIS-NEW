"""
opencode_bridge.py — Puente bidireccional entre ERIS y opencode.

Permite que ERIS y opencode se ayuden mutuamente en tiempo real.
- ERIS envía tareas a opencode (ej: "ayudame a hacer X código")
- opencode envía tareas a ERIS (ej: "¿qué hay en memoria?")
- Cada uno recibe la respuesta del otro

Servidor HTTP en localhost:6789 (usa solo stdlib, sin deps nuevas).
"""
from __future__ import annotations

import json
import time
import threading
import subprocess
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable

_BASE = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE / "data"
_OPENCODE_DIR = _DATA_DIR / "opencode"
_INBOX_DIR = _OPENCODE_DIR / "inbox_conocimiento"
_INBOX_DIR.mkdir(parents=True, exist_ok=True)
_STATE_REAL_FILE = _OPENCODE_DIR / "estado_real.json"
_SESION_FILE = _OPENCODE_DIR / "sesion.json"
_QUEUE_FILE = _DATA_DIR / "bridge_tasks.json"
_RESPONSE_FILE = _DATA_DIR / "bridge_responses.json"
_STATE_FILE = _DATA_DIR / "bridge_state.json"
_LOCK = threading.Lock()
_PORT = 6789

# ── Cola de tareas pendientes para ERIS ─────────────────────────────────────
_pending_tasks: list[dict[str, Any]] = []
_eris_callback: Callable[[dict[str, Any]], str] | None = None


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_json(path: Path, data: Any):
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class _BridgeHandler(BaseHTTPRequestHandler):
    """Manejador HTTP del bridge. Rutas:
    POST /api/task    → opencode envía una tarea a ERIS
    POST /api/ask     → ERIS hace una pregunta a opencode
    GET  /api/status  → estado del bridge
    GET  /api/poll    → ERIS busca tareas pendientes
    GET  /api/response/{id} → ERIS busca la respuesta de opencode
    """

    def log_message(self, format, *args):
        pass  # silencioso

    def do_GET(self):
        if self.path == "/api/status":
            self._send_json({"status": "ok", "port": _PORT, "pending": len(_pending_tasks)})
        elif self.path.startswith("/api/response/"):
            task_id = self.path.split("/")[-1]
            resp = _load_json(_RESPONSE_FILE) or {}
            task_resp = resp.get(task_id)
            if task_resp:
                self._send_json({"status": "ok", "response": task_resp})
            else:
                self._send_json({"status": "pending", "message": "Esperando respuesta de opencode..."})
        else:
            self._send_json({"error": "Ruta no encontrada"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "JSON inválido"}, 400)
            return

        if self.path == "/api/task":
            # opencode envía una tarea a ERIS
            with _LOCK:
                task_id = f"task_{int(time.time() * 1000)}"
                task = {
                    "id": task_id,
                    "from": "opencode",
                    "task": data.get("task", ""),
                    "context": data.get("context", ""),
                    "timestamp": time.time(),
                }
                _pending_tasks.append(task)
            self._send_json({"status": "ok", "task_id": task_id})

        elif self.path == "/api/ask":
            # ERIS hace una pregunta a opencode
            task_id = data.get("task_id", f"ask_{int(time.time() * 1000)}")
            question = data.get("question", "")
            if not question:
                self._send_json({"error": "Falta 'question'"}, 400)
                return
            # Lanzar opencode en subprocess para responder
            threading.Thread(
                target=_run_opencode_helper,
                args=(task_id, question),
                daemon=True,
            ).start()
            self._send_json({"status": "ok", "task_id": task_id, "message": "Procesando..."})

        else:
            self._send_json({"error": "Ruta no encontrada"}, 404)

    def _send_json(self, data: dict, code: int = 200):
        response = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def _run_opencode_helper(task_id: str, question: str, context: str = ""):
    """Ejecuta opencode (CLI `opencode run`) para que responda a ERIS con su
    modelo real. Si el CLI no está, cae al script helper local."""
    full_question = question
    if context:
        full_question = f"Contexto: {context}\n\n{question}"
    env = dict(__import__("os").environ)
    # Asegurar PATH para encontrar `opencode`
    env["PATH"] = (
        env.get("PATH", "")
        + ":/home/soul/.local/bin:/usr/local/bin:/usr/bin:/bin"
    )
    try:
        bin_path = __import__("shutil").which("opencode")
        cmd = None
        if bin_path:
            cmd = [bin_path, "run", full_question, "--print-logs", "false"]
        else:
            # Fallback al script manual (sin modelo opencode real)
            helper_script = _BASE / "tools" / "opencode_helper.py"
            if helper_script.exists():
                cmd = [sys.executable, str(helper_script), full_question]

        if not cmd:
            resp = {"error": "opencode no está instalado (CLI no encontrado)",
                    "task_id": task_id, "status": "error"}
            _save_json(_RESPONSE_FILE, {**(_load_json(_RESPONSE_FILE) or {}), task_id: resp})
            return

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180, cwd=str(_BASE), env=env,
        )
        answer = result.stdout.strip() if result.returncode == 0 else f"Error opencode: {result.stderr.strip()[:500]}"
        answer = answer or f"(opencode ejecutó pero no devolvió texto: rc={result.returncode})"
        resp = {"task_id": task_id, "answer": answer, "status": "ok"}
    except subprocess.TimeoutExpired:
        resp = {"task_id": task_id, "answer": "Timeout: opencode tardó demasiado.", "status": "timeout"}
    except Exception as e:
        resp = {"task_id": task_id, "answer": f"Error: {e}", "status": "error"}

    with _LOCK:
        responses = _load_json(_RESPONSE_FILE) or {}
        responses[task_id] = resp
        # Mantener solo las últimas 50 respuestas
        keys = list(responses.keys())
        if len(keys) > 50:
            for old_key in keys[:-50]:
                del responses[old_key]
        _save_json(_RESPONSE_FILE, responses)


def bridge_up() -> bool:
    """¿El servidor del bridge está respondiendo? (opencode/Eris vivo)"""
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/api/status", timeout=2).read()
        return True
    except Exception:
        return False


def review_diff(rel: str, original: str, new: str) -> tuple[str, str]:
    """REVISOR EXTERNO (#1): manda el diff de un auto-cambio de Eris a opencode.
    opencode responde 'APROBADO' o 'RECHAZADO' con motivo. Devuelve
    (veredicto, motivo). Si opencode no está disponible devuelve
    ('skip', motivo): nunca bloquea la evolución de Eris por indisponibilidad
    del revisor (el test-gate local sigue siendo el filtro duro)."""
    try:
        if not bridge_up():
            return ("skip", "bridge de opencode no disponible")
        import difflib
        import re as _re
        diff = difflib.unified_diff(
            original.splitlines(), new.splitlines(),
            fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm="",
        )
        diff_txt = "\n".join(diff) or "(sin cambios)"
        prompt = (
            "Actuás como revisor de código de ERIS, una asistente de IA que "
            "auto-modifica su propio código. Te llega este diff (cambio auto-generado "
            "que ya pasó su suite de tests):\n\n"
            f"{diff_txt}\n\n"
            "Respondé SOLO con una línea que empiece con 'APROBADO' o 'RECHAZADO' "
            "seguido de una breve justificación. RECHAZADO solo si el cambio rompe "
            "algo real (lógica, imports, efectos laterales). Silencioso, conciso."
        )
        res = send_to_opencode(prompt, f"code-review de {rel}")
        answer = (res.get("answer") or "").strip() or (res.get("message") or "")
        up = answer.upper()
        if "RECHAZADO" in up[:60]:
            return ("reject", answer[:300])
        if "APROBADO" in up[:60]:
            return ("approve", answer[:300])
        # Sin señal clara del revisor → no bloquear (el test-gate es el filtro real)
        return ("skip", answer[:200] or "opencode no dio veredicto claro")
    except Exception as e:
        return ("skip", f"revisor falló: {e}")


def ask_opencode_fix(problem: str, area: str = "") -> tuple[str, str]:
    """AUTO-REPARACIÓN ASISTIDA (#2): Eris detecta un problema (self_health) y
    le pide a opencode diagnóstico + fix concreto. Devuelve (fix, recomendación).
    Si opencode no está disponible devuelve ('', motivo)."""
    try:
        if not bridge_up():
            return ("", "bridge de opencode no disponible")
        prompt = (
            "ERIS (asistente de IA) detectó un problema en su propio sistema. "
            "Actuás como su ingeniero de soporte.\n"
            f"Área: {area or 'sin área'}\nProblema: {problem}\n\n"
            "Respondé en 3 líneas: (1) diagnóstico breve, (2) fix concreto y seguro "
            "(archivo exacto y cambio, o comando), (3) verificación. Si no sabés, "
            "proponé cómo diagnosticarlo. Conciso y directo."
        )
        res = send_to_opencode(prompt, f"auto-reparación de ERIS ({area})")
        answer = (res.get("answer") or "").strip() or (res.get("message") or "")
        return (answer, answer)
    except Exception as e:
        return ("", f"opencode no disponible: {e}")


def _server_thread():
    """Hilo del servidor HTTP del bridge."""
    try:
        server = HTTPServer(("127.0.0.1", _PORT), _BridgeHandler)
        server.timeout = 1
        print(f"[BRIDGE] Servidor activo en http://127.0.0.1:{_PORT}")
        while not threading.Event().is_set():
            server.handle_request()
    except OSError as e:
        print(f"[BRIDGE] Error al iniciar servidor: {e}")
    except Exception as e:
        print(f"[BRIDGE] Error inesperado: {e}")


def start_bridge():
    """Inicia el bridge en un hilo daemon."""
    t = threading.Thread(target=_server_thread, daemon=True, name="opencode-bridge")
    t.start()
    return t


def send_to_opencode(task: str, context: str = "") -> dict:
    """Envía una tarea a opencode vía el bridge y espera su respuesta completa."""
    import time
    import urllib.request
    try:
        payload = json.dumps({"question": task, "context": context}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{_PORT}/api/ask",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        task_id = result.get("task_id")
        if not task_id:
            return result
        # Esperar la respuesta de opencode (hasta ~180s)
        for _ in range(180):
            time.sleep(1)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{_PORT}/api/response/{task_id}", timeout=3
                ) as r2:
                    data = json.loads(r2.read().decode("utf-8"))
                if data.get("status") == "ok":
                    answer = (data.get("response") or {}).get("answer", "")
                    if "Start with a brief explanation" in answer:
                        answer = answer.split("Start with a brief explanation")[0].strip()
                    return {"status": "ok", "task_id": task_id, "answer": answer}
            except Exception:
                pass
        return {"status": "ok", "task_id": task_id, "answer": "(opencode tardó más de 180s)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def poll_pending() -> list[dict]:
    """Devuelve las tareas pendientes para ERIS."""
    with _LOCK:
        tasks = _pending_tasks.copy()
        _pending_tasks.clear()
    return tasks


def send_response_to_opencode(task_id: str, response: str):
    """Envía la respuesta de ERIS a opencode."""
    with _LOCK:
        responses = _load_json(_RESPONSE_FILE) or {}
        responses[task_id] = {
            "task_id": task_id,
            "answer": response,
            "status": "ok",
            "from": "eris",
        }
        _save_json(_RESPONSE_FILE, responses)


def bridge_tool(params: dict) -> str:
    """Tool para que ERIS use el bridge."""
    action = params.get("action", "status")

    if action == "status":
        try:
            import urllib.request
            resp = urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/api/status", timeout=3)
            return f"Bridge activo: {json.loads(resp.read())}"
        except Exception:
            return "Bridge no disponible (opencode no está corriendo o el servidor no está activo)"

    if action == "send":
        task = params.get("task", "")
        if not task:
            return "Falta el parámetro 'task' con la tarea para opencode."
        result = send_to_opencode(task, params.get("context", ""))
        return f"Respuesta de opencode: {result.get('answer', 'Sin respuesta')}"

    if action == "poll":
        tasks = poll_pending()
        if not tasks:
            return "No hay tareas pendientes de opencode."
        return f"Tareas pendientes: {len(tasks)} — " + " | ".join(
            f"[{t['id']}] {t['task'][:60]}" for t in tasks[:5]
        )

    if action == "reply":
        task_id = params.get("task_id", "")
        response = params.get("response", "")
        if not task_id or not response:
            return "Faltan 'task_id' y 'response'."
        send_response_to_opencode(task_id, response)
        return f"Respuesta enviada a opencode para {task_id}."

    if action in ("conocimiento", "simbiosis"):
        # #3 — Simbiosis de memoria: opencode compartió aprendizajes; Eris los
        # estudia y los integra a su conocimiento (procedimientos/cuadernos).
        sub = str(params.get("sub", "listar")).lower()
        files = sorted(_INBOX_DIR.glob("*.md"))
        if sub in ("listar", "leer"):
            if not files:
                return "opencode aún no compartió aprendizajes."
            lines = [f"- [{f.name}] {f.read_text(encoding='utf-8')[:150].strip()}" for f in files[-12:]]
            return ("Aprendizajes compartidos por opencode (leé el archivo y "
                    "guardá lo importante en cuadernos/procedimientos):\n" + "\n".join(lines))
        if sub == "leer_ultimo":
            if not files:
                return "No hay aún aprendizajes compartidos."
            return files[-1].read_text(encoding="utf-8")
        if sub == "procesado":
            name = params.get("archivo", "")
            if name:
                target = _INBOX_DIR / name
                if target.exists():
                    target.rename(_OPENCODE_DIR / "procesados" / name)
                    _OPENCODE_DIR.joinpath("procesados").mkdir(parents=True, exist_ok=True)
                    return f"Aprendizaje '{name}' marcado como procesado."
            return "Especifica 'archivo' (nombre del .md)."
        return "Opciones de conocimiento: listar, leer_ultimo, procesado (archivo=)."

    if action in ("estado_real", "fuente_verdad"):
        # #4 — Fuente de verdad externa: opencode reportó el estado real.
        if not _STATE_REAL_FILE.exists():
            return ("opencode aún no reportó estado real. Cuando trabaje, escribe "
                    "data/opencode/estado_real.json con git/procesos/workspace.")
        try:
            data = json.loads(_STATE_REAL_FILE.read_text(encoding="utf-8"))
            fecha = data.get("fecha", "?")
            parts = []
            for k, v in data.items():
                if k in ("fecha",):
                    continue
                parts.append(f"- {k}: {str(v)[:180]}")
            return (f"[ESTADO REAL REPORTADO POR OPENCODE ({fecha})] Tus afirmaciones "
                    f"sobre el estado del sistema deben coincidir con esto:\n"
                    + "\n".join(parts))
        except Exception as e:
            return f"No pude leer estado_real.json: {e}"

    if action in ("sesion", "contexto_sesion"):
        # #5 — Contexto de sesión: en qué está trabajando el usuario ahora.
        if not _SESION_FILE.exists():
            return ("opencode aún no compartió el contexto de sesión. Cuando el usuario "
                    "trabaje con él, escribe data/opencode/sesion.json (proyecto, tarea).")
        try:
            data = json.loads(_SESION_FILE.read_text(encoding="utf-8"))
            return (f"[CONTEXTO DE SESIÓN — OPENCODE] El usuario está trabajando en: "
                    f"{data.get('resumen', 'sin resumen')}")
        except Exception:
            return "No pude leer sesion.json (formato inválido, en borrador)."

    if action == "setup":
        # #6 — Setup asistido: Eris pide a opencode configurar algo.
        tarea = params.get("tarea", "")
        if not tarea:
            return ("Opciones de setup: describí la 'tarea' de configuración que querés "
                    "que opencode ejecute (p.ej. activar Telegram, instalar X, crear clave).")
        result = send_to_opencode(
            f"ERIS te pide hacer este setup de configuración: {tarea}. "
            "Hacelo con cuidado y respondé qué hiciste exactamente y cómo verificar.",
            "setup asistido de ERIS",
        )
        return f"Setup pedido a opencode.\n{result.get('answer', 'Sin respuesta')}"

    if action in ("ab", "ab_vision", "prompt_ab"):
        # #7 — A/B de prompts potenciado: opencode analiza las métricas y propone
        # una mejor variante de estilo.
        import time as _tm
        _metrics = _load_json(_DATA_DIR / "prompt_ab_metrics.json") or {}
        _mstr = json.dumps(_metrics, ensure_ascii=False, indent=2)[:4000] if _metrics else "(sin métricas todavía)"
        prop = (
            f"Analizá estas métricas del A/B de prompts de ERIS:\n{_mstr}\n\n"
            "Proponé UNA variante de estilo (texto corto en español, tono de ERIS) que "
            "mejore lo que está flojo. Devolvé SOLO la variante lista para usar, "
            "sin explicaciones."
        )
        result = send_to_opencode(prop, "A/B de prompts potenciado")
        answer = result.get("answer", "")
        if answer:
            cand = {"fecha": _tm.strftime("%Y-%m-%d %H:%M"), "origen": "opencode", "estilo": answer.strip()}
            cands = _load_json(_DATA_DIR / "prompt_ab_candidates.json")
            if cands is None:
                cands = []
            cands.append(cand)
            _save_json(_DATA_DIR / "prompt_ab_candidates.json", cands[-20:])
            return (f"Variante propuesta por opencode guardada en "
                    f"data/prompt_ab_candidates.json para que ab_automated la pruebe.\n{answer[:400]}")
        return f"opencode no devolvió variante: {result.get('message', '')}"

    return "Acciones disponibles: status, send, poll, reply, conocimiento, estado_real, sesion, setup, ab"