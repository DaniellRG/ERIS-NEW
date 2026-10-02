#!/usr/bin/env python3
"""hermes_poll.py — Lado HERMES del puente con ERIS (puerto 6790).

ERIS pregunta (hermes_consult action=ask) y la pregunta queda encolada en
data/hermes/preguntas.json. Este script es la otra punta del canal: la lee y
postea la respuesta REAL, que ERIS recibe por HTTP y por inyección en vivo.

    python tools/hermes_poll.py status
    python tools/hermes_poll.py list                    # preguntas pendientes
    python tools/hermes_poll.py show <task_id>
    python tools/hermes_poll.py answer <task_id> "texto de la respuesta"
    python tools/hermes_poll.py answer-file <task_id> respuesta.md
    python tools/hermes_poll.py tasks                   # tareas que ERIS te dejó
    python tools/hermes_poll.py reply <task_id> "texto"  # responder una TAREA
    python tools/hermes_poll.py learn "problema" "solución" [directorio]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

PORT = 6790
QFILE = BASE / "data" / "hermes" / "preguntas.json"
LEARN = BASE / "data" / "hermes" / "learn.json"
OUTBOX = BASE / "data" / "hermes" / "outbox.json"


def _read(path: Path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return default


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_status():
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status", timeout=4) as r:
            print(f"bridge: ACTIVO  puerto={PORT}  {json.loads(r.read().decode('utf-8'))}")
    except Exception as exc:
        print(f"bridge: CAIDO ({exc}). ERIS no esta corriendo, o el puerto {PORT} no escucha.")
    pend = [q for q in _read(QFILE, []) if q.get("status") == "pending"]
    print(f"preguntas pendientes de ERIS: {len(pend)}")
    for q in pend:
        cat = q.get("category", "?")
        preg = q.get("question", "")[:90]
        print(f"  [{q['task_id']}] {cat}: {preg}")
    return 0


def cmd_list():
    pend = [q for q in _read(QFILE, []) if q.get("status") == "pending"]
    if not pend:
        print("Sin preguntas pendientes.")
        return 0
    for q in pend:
        print("─" * 70)
        print(f"task_id  : {q['task_id']}")
        print(f"categoria: {q.get('category') or '-'}")
        print(f"preguntada: {q.get('asked_at')}")
        if q.get("context"):
            print(f"contexto:\n{q['context']}")
        print(f"pregunta:\n{q.get('question','')}")
    return 0


def cmd_show(task_id: str):
    for q in _read(QFILE, []):
        if q["task_id"] == task_id:
            print(json.dumps(q, ensure_ascii=False, indent=2))
            return 0
    print(f"No encuentro la pregunta {task_id}.")
    return 1


def _queue_answer(task_id: str, answer: str) -> int:
    """Escribe la respuesta y la manda al bridge si esta vivo (best effort)."""
    box = _read(OUTBOX, [])
    box.append({
        "task_id": task_id,
        "answer": answer,
        "status": "ok",
        "from": "hermes",
        "answered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    _write(OUTBOX, box[-200:])
    try:
        from core.hermes_bridge import send_response_to_eris
        send_response_to_eris(task_id, answer)
        print(f"Respuesta entregada a ERIS para {task_id} (bridge vivo).")
    except Exception as exc:
        print(f"Respuesta guardada en {OUTBOX} (bridge caido: {exc}).")
        print("Cuando ERIS levante, se reinyecta sola.")
    return 0


def cmd_answer(task_id: str, text: str) -> int:
    return _queue_answer(task_id, text)


def cmd_answer_file(task_id: str, path: str) -> int:
    try:
        return _queue_answer(task_id, Path(path).read_text("utf-8").strip())
    except Exception as exc:
        print(f"No pude leer {path}: {exc}")
        return 1


def cmd_reply(task_id: str, text: str) -> int:
    """Alias explicito para responder una TAREA (no una pregunta)."""
    return _queue_answer(task_id, text)


def cmd_tasks() -> int:
    tareas = _read(BASE / "data" / "hermes_tasks.json", {}).get("tasks", [])
    limpio = [t for t in tareas if t.get("task")]
    if not limpio:
        print("ERIS no te dejo tareas.")
        return 0
    for t in limpio:
        print(f"  [{t['id']}] {t['task'][:100]}")
    return 0


def cmd_learn(problem: str, solution: str, directory: str = "") -> int:
    entries = _read(LEARN, [])
    entries.append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "problem": problem,
        "solution": solution,
        "directory": directory,
    })
    _write(LEARN, entries[-500:])
    print(f"Aprendizaje registrado en {LEARN}.")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    table = {"status": cmd_status, "list": cmd_list, "tasks": cmd_tasks}
    if cmd in table:
        return table[cmd]()
    if cmd == "show" and rest:
        return cmd_show(rest[0])
    if cmd in ("answer", "reply") and len(rest) >= 2:
        fn = cmd_answer if cmd == "answer" else cmd_reply
        return fn(rest[0], " ".join(rest[1:]))
    if cmd == "answer-file" and len(rest) >= 2:
        return cmd_answer_file(rest[0], rest[1])
    if cmd == "learn" and len(rest) >= 2:
        return cmd_learn(rest[0], rest[1], rest[2] if len(rest) > 2 else "")
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))