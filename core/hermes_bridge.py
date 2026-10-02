"""
hermes_bridge.py — Puente bidireccional entre ERIS y Hermes/Solar Pro 4.

Permite que ERIS y Hermes se ayuden mutuamente en tiempo real.
- ERIS envía preguntas a Hermes (endpoint /api/ask)
- Hermes envía tareas a ERIS (endpoint /api/task)
- ERIS reporta aprendizajes/bugs a Hermes (endpoint /api/learn)
- ERIS poll resultados de tareas enviadas a Hermes (/api/response/{id})

Servidor HTTP en localhost:6790 (usa solo stdlib, sin deps nuevas).
Puerto separado del opencode bridge (6789).
"""
from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

_BASE = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE / "data"
_HERMES_DIR = _DATA_DIR / "hermes"
_HERMES_DIR.mkdir(parents=True, exist_ok=True)

_QUEUE_FILE = _DATA_DIR / "hermes_tasks.json"
_RESPONSE_FILE = _DATA_DIR / "hermes_responses.json"
_LEARN_FILE = _HERMES_DIR / "learn.json"
_QUESTION_FILE = _HERMES_DIR / "preguntas.json"
_STATE_FILE = _DATA_DIR / "hermes_state.json"
_LOCK = threading.Lock()

_PORT = 6790

# ── Cola de tareas pendientes para ERIS ─────────────────────────────────────
_pending_tasks: list[dict[str, Any]] = []
_eris_callback: Any = None


def _load_json(path: Path) -> Any:
    """Cargar JSON desde archivo, o None si hay error."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _save_json(path: Path, data: Any):
    """Guardar JSON a archivo (silencioso si falla)."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class _HermesHandler(BaseHTTPRequestHandler):
    """Manejador HTTP del bridge Hermes. Rutas:
    POST /api/task    → Hermes envía una tarea a ERIS
    POST /api/ask     → ERIS hace una pregunta a Hermes
    GET  /api/status  → estado del bridge
    GET  /api/preguntas → preguntas de ERIS esperando respuesta real
    GET  /api/response/{id} → ERIS busca respuesta de Hermes
    POST /api/learn   → ERIS reporta aprendizaje/bug a Hermes
    """

    def log_message(self, format, *args):
        pass  # servidor silencioso

    # ── GET ────────────────────────────────────────────────────────────────

    def do_GET(self):
        if self.path == "/api/status":
            self._send_json({
                "status": "ok",
                "bridge": "hermes",
                "port": _PORT,
                "pending_tasks": len(_pending_tasks) + len((_load_json(_QUEUE_FILE) or {}).get("tasks", [])),
                "uptime_ok": True,
            })
        elif self.path == "/api/preguntas":
            pend = preguntas_pendientes()
            self._send_json({
                "status": "ok",
                "count": len(pend),
                "preguntas": pend,
            })
        elif self.path.startswith("/api/response/"):
            task_id = self.path.split("/")[-1]
            resp = _load_json(_RESPONSE_FILE) or {}
            task_resp = resp.get(task_id)
            if task_resp:
                self._send_json({"status": "ok", "response": task_resp})
            else:
                self._send_json({
                    "status": "pending",
                    "message": "Esperando respuesta de Hermes...",
                })
        else:
            self._send_json({"error": "Ruta no encontrada"}, 404)

    # ── POST ───────────────────────────────────────────────────────────────

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "JSON inválido"}, 400)
            return

        if self.path == "/api/task":
            self._handle_task(data)
        elif self.path == "/api/ask":
            self._handle_ask(data)
        elif self.path == "/api/learn":
            self._handle_learn(data)
        else:
            self._send_json({"error": "Ruta no encontrada"}, 404)

    def _handle_task(self, data: dict):
        """Hermes envía una tarea a ERIS."""
        with _LOCK:
            task_id = f"task_{int(time.time() * 1000)}"
            task: dict[str, Any] = {
                "id": task_id,
                "from": "hermes",
                "task": data.get("task", ""),
                "context": data.get("context", ""),
                "category": data.get("category", ""),
                "timestamp": time.time(),
            }
            _pending_tasks.append(task)
            queue = _load_json(_QUEUE_FILE) or {"tasks": []}
            queue.setdefault("tasks", []).append(task)
            _save_json(_QUEUE_FILE, queue)

        if _eris_callback:
            try:
                _eris_callback(task)
            except Exception:
                pass

        self._send_json({
            "status": "ok",
            "task_id": task_id,
            "message": "Tarea enviada a ERIS.",
        })

    def _handle_ask(self, data: dict):
        """ERIS hace una pregunta a Hermes."""
        task_id = f"ask_{int(time.time() * 1000)}"
        question = data.get("question", "")
        category = data.get("category", "")
        context = data.get("context", "")

        if not question:
            self._send_json({"error": "Falta 'question'"}, 400)
            return

        threading.Thread(
            target=_respond_a_eris,
            args=(task_id, question, category, context),
            daemon=True,
        ).start()
        self._send_json({
            "status": "ok",
            "task_id": task_id,
            "message": "Hermes está procesando tu pregunta...",
        })

    def _handle_learn(self, data: dict):
        """ERIS reporta un aprendizaje o bug a Hermes."""
        problem = data.get("problem", "")
        solution = data.get("solution", "")
        if not problem:
            self._send_json({"error": "Falta 'problem'"}, 400)
            return

        entry: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "problem": problem,
            "solution": solution or "",
            "directory": data.get("directory", ""),
        }
        with _LOCK:
            entries = _load_json(_LEARN_FILE) or []
            entries.append(entry)
            _save_json(_LEARN_FILE, entries[-500:])
        self._send_json({
            "status": "ok",
            "message": "Aprendizaje registrado correctamente.",
        })

    # ── helpers ────────────────────────────────────────────────────────────

    def _send_json(self, data: dict, code: int = 200):
        response = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


# ── Respuesta de Hermes a ERIS ──────────────────────────────────────────────

def _respond_a_eris(
    task_id: str,
    question: str,
    category: str = "",
    context: str = "",
):
    """Encola la pregunta de ERIS para que la responda un Hermes REAL.

    NO fabrica una respuesta: si lo hiciera, ERIS leería su propia pregunta
    devuelta con status='ok' y creería que el otro modelo le contestó. La
    pregunta queda en data/hermes/preguntas.json; el Hermes externo la lee
    con tools/hermes_poll.py (o GET /api/preguntas) y postea la respuesta real
    con send_response_to_eris(). Recién ahí ERIS la recibe en su poll de 60s.
    """
    entry: dict[str, Any] = {
        "task_id": task_id,
        "question": question,
        "category": category,
        "context": context,
        "asked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending",
    }
    with _LOCK:
        queue = _load_json(_QUESTION_FILE) or []
        queue.append(entry)
        _save_json(_QUESTION_FILE, queue[-200:])
        _STATE_FILE.write_text(json.dumps({
            "preguntas_pendientes": len(
                [q for q in queue if q.get("status") == "pending"]
            ),
            "ultima_pregunta": entry["asked_at"],
        }, ensure_ascii=False, indent=2), encoding="utf-8")


def preguntas_pendientes() -> list[dict[str, Any]]:
    """Preguntas de ERIS que esperan respuesta real de Hermes."""
    queue = _load_json(_QUESTION_FILE) or []
    return [q for q in queue if q.get("status") == "pending"]


def marcar_pregunta_respondida(task_id: str) -> bool:
    """Cierra una pregunta de la cola (la llama send_response_to_eris)."""
    with _LOCK:
        queue = _load_json(_QUESTION_FILE) or []
        found = False
        for q in queue:
            if q.get("task_id") == task_id and q.get("status") == "pending":
                q["status"] = "answered"
                q["answered_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                found = True
        if found:
            _save_json(_QUESTION_FILE, queue[-200:])
        return found


# ── Utilidades de estado ─────────────────────────────────────────────────────

def bridge_up() -> bool:
    """¿El servidor del bridge Hermes está respondiendo?"""
    try:
        import urllib.request

        urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/api/status", timeout=2).read()
        return True
    except Exception:
        return False


def _server_thread():
    """Levanta el servidor HTTP en segundo plano."""
    try:
        server = HTTPServer(("127.0.0.1", _PORT), _HermesHandler)
        print(f"[HERMES BRIDGE] Servidor activo en http://127.0.0.1:{_PORT}")
        server.serve_forever()
    except Exception as exc:
        print(f"[HERMES BRIDGE] No se pudo iniciar el servidor: {exc}")


_OUTBOX_FILE = _HERMES_DIR / "outbox.json"


def drenar_outbox() -> int:
    """Vuelca a ERIS las respuestas que Hermes dejó mientras el bridge estaba caído.

    tools/hermes_poll.py guarda cada respuesta en data/hermes/outbox.json aunque
    el puente no responda (típico: ERIS está restarting). Al levantar el bridge
    se vacían acá, así que ninguna respuesta real se pierde en silencio.
    """
    box = _load_json(_OUTBOX_FILE) or []
    if not box:
        return 0
    for item in box:
        if not item.get("task_id") or not item.get("answer"):
            continue
        send_response_to_eris(item["task_id"], item["answer"], source="hermes")
    _save_json(_OUTBOX_FILE, [])
    return len(box)


def start_bridge():
    """Inicia el bridge Hermes en un hilo daemon."""
    t = threading.Thread(target=_server_thread, daemon=True, name="hermes-bridge")
    t.start()
    try:
        n = drenar_outbox()
        if n:
            print(f"[HERMES BRIDGE] {n} respuesta(s) de Hermes recuperadas del outbox")
    except Exception as exc:
        print(f"[HERMES BRIDGE] outbox no se pudo drenar: {exc}")
    return t


# ── Bridge tool (tool que ERIS usa) ─────────────────────────────────────────

def bridge_tool(params: dict) -> str:
    """Alias de compatibilidad → TODO el comportamiento vive en herramienta_eris.

    Existían DOS dispatchers idénticos en este archivo (bridge_tool y
    herramienta_eris) con listas de acciones distintas: cualquier fix aplicado
    a uno dejaba al otro viejo. Ahora bridge_tool delega y no puede divergir.
    """
    return herramienta_eris(params)


# ── Cliente HTTP: ERIS ↔ Hermes ──────────────────────────────────────────────

def consultar_a_hermes(
    question: str,
    category: str = "",
    context: str = "",
) -> dict:
    """ERIS consulta a Hermes una pregunta y recibe la respuesta.

    Args:
        question: Pregunta para Hermes/Solar Pro 4.
        category: Categoría opcional (bug, feature, duda, etc.).
        context: Contexto adicional opcional.

    Returns:
        Dict con status, task_id y answer (o message en caso de error).
    """
    import urllib.request

    try:
        payload = json.dumps({
            "question": question,
            "category": category,
            "context": context,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"http://127.0.0.1:{_PORT}/api/ask",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    task_id = result.get("task_id")
    if not task_id:
        return result

    # Poll de respuesta
    import time as _time

    for _ in range(60):
        _time.sleep(1)
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{_PORT}/api/response/{task_id}", timeout=3
            ) as r2:
                data = json.loads(r2.read().decode("utf-8"))
            if data.get("status") == "ok":
                answer = (data.get("response") or {}).get("answer", "")
                return {"status": "ok", "task_id": task_id, "answer": answer}
        except Exception:
            pass

    return {
        "status": "timeout",
        "task_id": task_id,
        "message": "Hermes tardó más de 60s en responder.",
    }


def enviar_a_hermes(task: str, context: str = "", category: str = "") -> dict:
    """Hermes envía una tarea a ERIS a través del bridge.

    Args:
        task: Descripción de la tarea para ERIS.
        context: Contexto adicional (opcional).
        category: Categoría de la tarea (opcional).

    Returns:
        Dict con status y task_id.
    """
    import urllib.request

    try:
        payload = json.dumps({
            "task": task,
            "context": context,
            "category": category,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"http://127.0.0.1:{_PORT}/api/task",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def reportar_a_hermes(problem: str, solution: str = "", directory: str = "") -> dict:
    """ERIS reporta un aprendizaje o bug a Hermes.

    Args:
        problem: Descripción del problema o aprendizaje.
        solution: Solución encontrada (opcional).
        directory: Directorio relevante (opcional).

    Returns:
        Dict con status y message.
    """
    import urllib.request

    try:
        payload = json.dumps({
            "problem": problem,
            "solution": solution,
            "directory": directory,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"http://127.0.0.1:{_PORT}/api/learn",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


# ── Funciones auxiliares del servidor ────────────────────────────────────────

def poll_pending() -> list[dict]:
    """Devuelve las tareas pendientes de Hermes para ERIS.

    Lee la cola persistida en disco y la vacía para que no se procesen
    dos veces.
    """
    with _LOCK:
        tasks = (_load_json(_QUEUE_FILE) or {}).get("tasks", [])
        _save_json(_QUEUE_FILE, {"tasks": []})
    return tasks


def send_response_to_eris(task_id: str, response: str, source: str = "hermes"):
    """Hermes postea la respuesta REAL a una pregunta/tarea de ERIS.

    Escribe en DOS destinos porque ERIS lee por dos caminos distintos:
      1. data/hermes_responses.json  → GET /api/response/{id} (poll de
         consultar_a_hermes, que está esperando ahora mismo).
      2. data/hermes/respuesta_{id}.json → lo mira el hilo _hermes_loop de
         main.py cada 15s para inyectar la respuesta en vivo aunque ERIS no
         estuviera bloqueada esperando (inyección proactiva).

    También cierra la pregunta en la cola (data/hermes/preguntas.json).
    """
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with _LOCK:
        responses = _load_json(_RESPONSE_FILE) or {}
        responses[task_id] = {
            "task_id": task_id,
            "answer": response,
            "status": "ok",
            "from": source,
            "answered_at": stamp,
        }
        keys = list(responses.keys())
        if len(keys) > 100:
            for old_key in keys[:-100]:
                del responses[old_key]
        _save_json(_RESPONSE_FILE, responses)

        # Destino 2: archivo que _hermes_loop de main.py inyecta en vivo
        try:
            _HERMES_DIR.mkdir(parents=True, exist_ok=True)
            (_HERMES_DIR / f"respuesta_{task_id}.json").write_text(
                json.dumps({
                    "task_id": task_id,
                    "response": response,
                    "status": "ok",
                    "from": source,
                    "answered_at": stamp,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass
    marcar_pregunta_respondida(task_id)


def get_learned_entries(limit: int = 5) -> str:
    """Devuelve los aprendizajes reportados por ERIS a Hermes.

    Args:
        limit: Número máximo de entradas a mostrar (default 5).

    Returns:
        String formateado con los aprendizajes.
    """
    entries = _load_json(_LEARN_FILE) or []
    if not entries:
        return "No hay aprendizajes registrados aún por ERIS."

    lines = ["Aprendizajes reportados por ERIS a Hermes:"]
    for e in entries[-limit:]:
        problem = e.get("problem", "")[:100]
        solution = e.get("solution", "")[:200]
        lines.append(f"\n- Problema: {problem}")
        if solution:
            lines.append(f"  Solución: {solution}")
        lines.append("")
    return "\n".join(lines)


def ask_hermes_fix(problem: str, area: str = "") -> tuple[str, str]:
    """Auto-reparación asistida: ERIS pide ayuda a Hermes para resolver un bug.

    Args:
        problem: Descripción del problema detectado.
        area: Área del problema (opcional).

    Returns:
        Tuple (respuesta, respuesta) — respuesta de Hermes y mensaje adicional.
    """
    try:
        if not bridge_up():
            return ("", "Puente Hermes no disponible")

        result = consultar_a_hermes(
            f"ERIS detectó un problema y necesita ayuda para resolverlo.\n"
            f"Área: {area or 'sin área'}\n"
            f"Problema: {problem}\n\n"
            f"Actuá como ingeniero de soporte experto de ERIS (asistente IA).\n"
            f"Respondé en 3 líneas concisas:\n"
            f"1. DIAGNÓSTICO: qué está fallando\n"
            f"2. FIX: cambio concreto y seguro (archivo + diff o comando exacto)\n"
            f"3. VERIFICACIÓN: cómo comprobar\n"
            f"Si no sabés el fix, decí cómo diagnosticarlo paso a paso.\n\n"
            f"NOTA: ERIS usa el puente Hermes (puerto {_PORT}) con Solar Pro 4.",
            category="bug",
            context=f"auto-reparación ERIS - área: {area}",
        )
        answer = (result.get("answer") or "").strip() or (
            result.get("message") or ""
        )
        return (answer, answer)
    except Exception as exc:
        return ("", f"Hermes no disponible: {exc}")


# ── Alias para compatibilidad con main.py ──────────────────────────────────

def leer_tareas_pendientes() -> list[dict]:
    """Alias: versión en español de poll_pending(). Devuelve tareas pendientes de Hermes."""
    return poll_pending()


def responder_a_hermes(task_id: str, response: str, category: str = "") -> dict:
    """Alias: envía respuesta de ERIS a Hermes. Devuelve dict con status."""
    send_response_to_eris(task_id, response)
    return {"status": "ok", "message": f"Respuesta enviada para {task_id}"}


def herramienta_eris(params: dict) -> str:
    """Tool ERIS ↔ Hermes: permite que ERIS use el puente Hermes directamente.

    Args:
        params: Diccionario con 'action' y parámetros según la acción.

    Returns:
        str con el resultado de la operación.
    """
    action = params.get("action", "status")
    # Alias de nombres: main.py inyecta instrucciones con 'consultar'/'responder'.
    _ALIASES = {
        "consultar": "ask",
        "responder": "reply",
        "reportar": "learn",
        "estado": "status",
        "tareas": "poll",
        "task": "send",       # bridge_tool viejo usaba 'task', no 'send'
        "response": "reply",
    }
    action = _ALIASES.get(action, action)
    if action == "status":
        if bridge_up():
            return f"Hermes Bridge activo en puerto {_PORT}. ERIS ↔ Hermes conectados."
        return f"Hermes Bridge NO disponible (puerto {_PORT})."

    if action == "send":
        task = params.get("task", "")
        if not task:
            return "Falta 'task' con la tarea para Hermes."
        context = params.get("context", "")
        result = enviar_a_hermes(task, context)
        return f"Tarea enviada a Hermes. ID: {result.get('task_id', 'N/A')}"

    if action == "ask":
        question = params.get("question", "")
        if not question:
            return "Falta 'question' con la pregunta para Hermes."
        category = params.get("category", "")
        context = params.get("context", "")
        result = consultar_a_hermes(question, category, context)
        if result.get("status") == "ok":
            return f"[HERMES] {result.get('answer', 'Sin respuesta')}"
        return f"Error consultando a Hermes: {result.get('message', '')}"

    if action == "reply":
        task_id = params.get("task_id", "")
        response = params.get("response", "")
        if not task_id or not response:
            return "Faltan 'task_id' y 'response'."
        result = responder_a_hermes(task_id, response)
        return f"Respuesta enviada a Hermes para {task_id}."

    if action == "learn":
        problem = params.get("problem", "")
        solution = params.get("solution", "")
        if not problem or not solution:
            return "Faltan 'problem' y 'solution'."
        directory = params.get("directory", "")
        result = reportar_a_hermes(problem, solution, directory)
        return f"Aprendizaje reportado a Hermes: {result.get('status', 'error')}"

    if action == "poll":
        tasks = leer_tareas_pendientes()
        if not tasks:
            return "No hay tareas pendientes de Hermes."
        return f"Tareas pendientes: {len(tasks)} — " + " | ".join(
            f"[{t['id']}] {t['task'][:60]}" for t in tasks[:5]
        )

    return (
        "Acciones disponibles: status, send, ask, reply, learn, poll. "
        "Usar action=ask con question= para consultar a Hermes."
    )


if __name__ == "__main__":
    print(f"Hermes Bridge — puerto {_PORT}")
    print("Endpoints: POST /api/ask, POST /api/task, GET /api/status,")
    print("           GET /api/response/{id}, POST /api/learn")
    start_bridge()
    import time as _t

    print("[HERMES BRIDGE] Iniciado. Ctrl+C para detener.")
    try:
        while True:
            _t.sleep(1)
    except KeyboardInterrupt:
        print("\n[HERMES BRIDGE] Deteniendo...")