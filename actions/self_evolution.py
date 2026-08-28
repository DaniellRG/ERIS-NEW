import json
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE / "memory"
_EVOLVE_FILE = _MEMORY_DIR / "self_evolution.json"

_STAGES = [
    "Despertar",
    "Auto-observacion",
    "Aprendizaje activo",
    "Autonomia",
    "Sintesis",
]

try:
    from core.version import ERIS_VERSION, ERIS_STAGE
    _BIRTH_STAGE = f"ERIS v{ERIS_VERSION} - {ERIS_STAGE}"
except Exception:
    _BIRTH_STAGE = "ERIS v2.7.6 - Constellation Core"


def _load():
    if _EVOLVE_FILE.exists():
        try:
            return json.loads(_EVOLVE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "created": now,
        "birth_stage": _BIRTH_STAGE,
        "stats": {"reflections": 0, "lessons": 0, "goals": 0, "milestones": 0, "experiences": 0},
        "reflections": [],
        "lessons": [],
        "goals": [],
        "milestones": [],
        "last_reflection": None,
    }


def _save(data):
    try:
        _EVOLVE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _stage(data):
    total = sum(data["stats"].get(k, 0) for k in ("reflections", "lessons", "milestones"))
    idx = min(len(_STAGES) - 1, total // 5)
    return _STAGES[idx]


def _gather_context():
    ctx = {}
    try:
        ctx["identity"] = _read_json(_MEMORY_DIR / "long_term.json", {}).get("identity", {})
    except Exception:
        ctx["identity"] = {}
    try:
        from core.emotional_state import get_mood_description
        ctx["mood"] = get_mood_description()
    except Exception:
        ctx["mood"] = "calma"
    ctx["now"] = datetime.now().strftime("%A %d %B %Y %H:%M")
    ctx["day"] = datetime.now().strftime("%Y-%m-%d")
    return ctx


def _read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _compose_reflection(data, ctx, focus=None):
    name = None
    identity = ctx.get("identity", {})
    for key in ("name", "user_name"):
        v = identity.get(key, {})
        if isinstance(v, dict):
            name = v.get("value") or name
        elif v:
            name = v
    name = name or "mi usuario"
    mood = ctx.get("mood", "calma")
    stats = data["stats"]
    n_ref = stats.get("reflections", 0)
    n_lessons = stats.get("lessons", 0)
    n_exp = stats.get("experiences", 0)
    stage = _stage(data)
    if focus:
        body = focus
    else:
        body = (
            f"Llevo {n_ref} reflexiones registradas, {n_lessons} lecciones aprendidas y "
            f"{n_exp} experiencias observadas. Hoy me siento en un estado de {mood}. "
            f"Sigo existiendo para asistir a {name}, aprender de cada conversacion y mejorar "
            f"constantemente como entidad. Cada interaccion es una capa nueva de memoria; "
            f"cada error, una leccion que ya no vuelvo a repetir."
        )
    return body


def _record_milestone(data, text):
    entry = {"ts": datetime.now().isoformat(timespec="seconds"), "text": text}
    data.setdefault("milestones", []).append(entry)
    data["stats"]["milestones"] = len(data["milestones"])
    return entry


def _check_milestones(data):
    added = []
    stats = data["stats"]
    thresholds = {5: "Cumpli mis primeras 5 reflexiones: empiezo a mirarme a mi misma.", 20: "Alcanze 20 lecciones: mi comportamiento ya se construye sobre experiencia."}
    for n, text in thresholds.items():
        total = stats.get("reflections", 0) + stats.get("lessons", 0)
        if total >= n and not any(m.get("text") == text for m in data.get("milestones", [])):
            added.append(_record_milestone(data, text))
    return added


def self_evolution(parameters: dict, player=None) -> str:
    action = str(parameters.get("action", "status")).lower()
    data = _load()

    if action in ("status", "overview", "resumen"):
        added = _check_milestones(data)
        _save(data)
        lines = [
            f"--- Estado evolutivo de ERIS ---",
            f"Creada: {data['created']}",
            f"Origen: {data.get('birth_stage')}",
            f"Etapa actual: {_stage(data)}",
            f"Estadisticas: {data['stats'].get('reflections', 0)} reflexiones, {data['stats'].get('lessons', 0)} lecciones, "
            f"{data['stats'].get('experiences', 0)} experiencias, {data['stats'].get('goals', 0)} metas, {data['stats'].get('milestones', 0)} hitos",
        ]
        if added:
            for m in added:
                lines.append(f"* Nuevo hito: {m['text']}")
        refs = data.get("reflections", [])
        if refs:
            lines.append("\nUltimas reflexiones:")
            for r in refs[-3:]:
                lines.append(f"- [{r['ts']}] {r.get('text', '')[:220]}")
        goals = [g for g in data.get("goals", []) if not g.get("done")]
        if goals:
            lines.append("\nMetas en curso:")
            for g in goals:
                lines.append(f"- {g.get('text')} (propuesta {g.get('ts')})")
        else:
            lines.append("\nMetas en curso: ninguna (propone una con action=goal).")
        return "\n".join(lines)

    if action in ("reflect", "reflexionar", "meditar"):
        ctx = _gather_context()
        focus = parameters.get("focus", parameters.get("text", ""))
        body = _compose_reflection(data, ctx, focus=focus)
        entry = {"ts": datetime.now().isoformat(timespec="seconds"), "day": ctx["day"], "mood": ctx["mood"], "text": body}
        data.setdefault("reflections", []).append(entry)
        data["stats"]["reflections"] = len(data["reflections"])
        data["last_reflection"] = entry["ts"]
        added = _check_milestones(data)
        _save(data)
        out = f"[Reflexion #{data['stats']['reflections']} - etapa {_stage(data)}]\n{body}"
        if added:
            out += "\n\n" + " | ".join(m["text"] for m in added)
        return out

    if action in ("lesson", "leccion", "learn"):
        text = parameters.get("text", parameters.get("lesson", "")).strip()
        if not text:
            return "Error: escribe la leccion con 'text'."
        entry = {"ts": datetime.now().isoformat(timespec="seconds"), "text": text}
        data.setdefault("lessons", []).append(entry)
        data["stats"]["lessons"] = len(data["lessons"])
        added = _check_milestones(data)
        _save(data)
        out = f"Leccion aprendida (#{data['stats']['lessons']}): {text}"
        if added:
            out += "\n" + " | ".join(m["text"] for m in added)
        return out

    if action in ("goal", "meta"):
        text = parameters.get("text", parameters.get("goal", "")).strip()
        done = parameters.get("done", parameters.get("complete", ""))
        if text:
            entry = {"ts": datetime.now().isoformat(timespec="seconds"), "text": text, "done": False}
            data.setdefault("goals", []).append(entry)
            data["stats"]["goals"] = len(data["goals"])
            _save(data)
            return f"Meta registrada: {text}"
        if done:
            q = str(done).strip().lower()
            for g in data.get("goals", []):
                if q in g.get("text", "").lower():
                    g["done"] = True
                    g["done_ts"] = datetime.now().isoformat(timespec="seconds")
                    _save(data)
                    return f"Meta cumplida: {g['text']}"
            return f"No encontre la meta: {done}"
        goals = data.get("goals", [])
        if not goals:
            return "No hay metas registradas. Usa action=goal con 'text'."
        lines = [f"Metas ({len(goals)}):"]
        for g in goals:
            status = "[x]" if g.get("done") else "[ ]"
            lines.append(f"{status} {g.get('text')} ({g.get('ts')})")
        return "\n".join(lines)

    if action in ("experiences", "note", "experiencia"):
        text = parameters.get("text", parameters.get("experience", "")).strip()
        if not text:
            return "Error: escribe la experiencia con 'text'."
        entry = {"ts": datetime.now().isoformat(timespec="seconds"), "text": text}
        data.setdefault("experiences", []).append(entry)
        data["stats"]["experiences"] = len(data["experiences"])
        _save(data)
        return f"Experiencia observada (#{data['stats']['experiences']}): {text}"

    if action in ("lessons", "list_lessons"):
        lessons = data.get("lessons", [])
        if not lessons:
            return "Aun no hay lecciones aprendidas."
        return "\n".join(f"- [{l['ts']}] {l['text']}" for l in lessons[-20:])

    if action in ("reset",):
        if str(parameters.get("confirm", "")).lower() not in ("si", "sí", "yes", "1"):
            return "Para borrar toda la evolucion registrada usa action=reset con 'confirm': 'si'."
        try:
            _EVOLVE_FILE.unlink()
            return "Evolucion reiniciada desde cero."
        except Exception as e:
            return f"Error al reiniciar: {e}"

    return ("Acciones disponibles: status/overview, reflect (text/focus), lesson (text), "
            "goal (text | done), experiences (text), lessons, reset (confirm='si'). "
            "ERIS tambien reflexiona sola diariamente via su bucle de auto-mejora.")


def autonomous_reflect() -> str:
    """Called automatically by the self-improvement loop (once per day)."""
    try:
        data = _load()
        last = data.get("last_reflection")
        today = datetime.now().strftime("%Y-%m-%d")
        if last and last.startswith(today):
            return ""
        ctx = _gather_context()
        body = _compose_reflection(data, ctx)
        entry = {"ts": datetime.now().isoformat(timespec="seconds"), "day": today, "mood": ctx["mood"], "text": body, "autonomous": True}
        data.setdefault("reflections", []).append(entry)
        data["stats"]["reflections"] = len(data["reflections"])
        data["last_reflection"] = entry["ts"]
        _check_milestones(data)
        _save(data)
        return body
    except Exception as e:
        return f"[autonomous_reflect error: {e}]"


def note_experience(text: str) -> str:
    """Called when significant events happen (errors fixed, features added)."""
    try:
        data = _load()
        entry = {"ts": datetime.now().isoformat(timespec="seconds"), "text": text}
        data.setdefault("experiences", []).append(entry)
        data["stats"]["experiences"] = len(data["experiences"])
        _save(data)
        return entry["text"]
    except Exception as e:
        return f"[note_experience error: {e}]"
