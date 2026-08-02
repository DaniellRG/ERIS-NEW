"""goals.py — Trackeador de metas: add, update, delete, progress, list."""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
GOALS_PATH = BASE_DIR / "config" / "goals.json"


def _load() -> list:
    if not GOALS_PATH.exists():
        return []
    try:
        items = json.loads(GOALS_PATH.read_text(encoding="utf-8"))
        return items if isinstance(items, list) else []
    except Exception:
        return []


def _save(items: list) -> None:
    GOALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOALS_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


def goals(parameters: dict, player=None) -> str:
    """Lee, crea, actualiza o elimina metas."""
    action = parameters.get("action", "list").lower()

    if action == "list":
        items = _load()
        if not items:
            return "No tienes metas activas."
        return "Metas activas:\n" + "\n".join(f"  {i + 1}. {g}" for i, g in enumerate(items))

    if action == "add":
        goal_text = (parameters.get("goal") or "").strip()
        if not goal_text:
            return "Necesito el texto de la meta (parámetro 'goal')."
        items = _load()
        items.append(goal_text)
        _save(items)
        return f"Meta agregada: '{goal_text}'"

    if action == "update":
        goal_text = (parameters.get("goal") or parameters.get("goal_id") or "").strip()
        new_text = (parameters.get("new_goal") or parameters.get("text") or "").strip()
        if not new_text:
            return "Falta el nuevo texto de la meta (parámetro 'new_goal')."
        items = _load()
        if not items:
            return "No hay metas para actualizar."
        idx = None
        if goal_text.isdigit():
            idx = int(goal_text) - 1
        else:
            for i, g in enumerate(items):
                if goal_text in str(g):
                    idx = i
                    break
        if idx is None or not (0 <= idx < len(items)):
            return "No encontré la meta indicada."
        old = items[idx]
        items[idx] = new_text
        _save(items)
        return f"Meta actualizada: '{old}' → '{new_text}'"

    if action == "delete":
        goal_text = (parameters.get("goal") or parameters.get("goal_id") or "").strip()
        items = _load()
        if not items:
            return "No hay metas para eliminar."
        if goal_text.isdigit():
            idx = int(goal_text) - 1
            if 0 <= idx < len(items):
                removed = items.pop(idx)
                _save(items)
                return f"Meta eliminada: '{removed}'"
            return "Índice de meta no válido."
        before = len(items)
        items = [g for g in items if goal_text not in str(g)]
        if len(items) == before:
            return f"No encontré la meta '{goal_text}'."
        _save(items)
        return f"Meta eliminada: '{goal_text}'"

    if action == "progress":
        items = _load()
        if not items:
            return "No tienes metas registradas. Agregá una con action 'add'."
        done = sum(1 for g in items if str(g).strip().startswith("[x]") or "✔" in str(g))
        lines = [f"Progreso: {done}/{len(items)} metas completadas."]
        for i, g in enumerate(items, 1):
            mark = "✅" if (str(g).strip().startswith("[x]") or "✔" in str(g)) else "⬜"
            lines.append(f"  {mark} {i}. {g}")
        return "\n".join(lines)

    return "Acciones: add, update, delete, progress, list"
