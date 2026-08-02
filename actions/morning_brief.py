"""morning_brief.py — Resumen matutino: clima, noticias y tareas pendientes."""
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_BRIEF_FILE = BASE_DIR / "data" / "last_brief.json"


def morning_brief(parameters: dict, player=None) -> str:
    """Resumen de la mañana. Acciones: brief, weather, news, tasks."""
    params = parameters or {}
    action = (params.get("action") or "brief").lower()

    if action == "weather":
        return str(_get_weather())
    if action == "news":
        return str(_get_news(5))
    if action == "tasks":
        return _get_tasks()

    parts = [f"Buenos días. Hoy es {datetime.now().strftime('%A %d de %B de %Y')}."]
    try:
        clima = _get_weather()
        parts.append(f"Clima: {clima}")
    except Exception as e:
        parts.append(f"(Clima no disponible: {e})")
    try:
        news = _get_news(3)
        if news:
            parts.append("Noticias destacadas:")
            parts.append(news)
    except Exception as e:
        parts.append(f"(Noticias no disponibles: {e})")
    try:
        tasks = _get_tasks()
        parts.append(tasks)
    except Exception:
        pass
    return "\n".join(str(p) for p in parts)


def _get_weather() -> str:
    from core.tool_registry import get_tool
    try:
        return get_tool("weather_report")({"city": ""})
    except Exception as e:
        return f"no disponible ({e})"


def _get_news(limit: int = 3) -> str:
    from core.tool_registry import get_tool
    try:
        raw = get_tool("web_search")({"action": "news", "query": "noticias de hoy", "num_results": limit})
    except Exception as e:
        return f"No se pudieron obtener noticias: {e}"
    lines = [ln.strip() for ln in str(raw).splitlines() if ln.strip()]
    out = []
    for ln in lines[1:limit + 1]:
        if not ln.startswith(("-", "*", "•")):
            out.append(f"  • {ln[:110]}")
        else:
            out.append(f"  {ln[:110]}")
    return "\n".join(out) or str(raw)[:400]


def _get_tasks() -> str:
    p = BASE_DIR / "data" / "eris_tasks.json"
    if not p.exists():
        return "No hay archivo de tareas."
    try:
        tasks = json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return "No se pudieron leer las tareas."
    if isinstance(tasks, dict):
        tasks = tasks.get("tasks", []) or []
    pend = [t for t in tasks if isinstance(t, dict) and not (t.get("done") or t.get("completed"))]
    if not pend:
        return "No tienes tareas pendientes. Descanso merecido."
    lines = [f"Tienes {len(pend)} tareas pendientes:"]
    for t in pend[:6]:
        lines.append(f"  • {t.get('title') or t.get('task') or t.get('description', '?')[:80]}")
    return "\n".join(lines)


def already_briefed_today() -> bool:
    try:
        data = json.loads(_BRIEF_FILE.read_text(encoding="utf-8"))
        return data.get("date") == datetime.now().strftime("%Y-%m-%d")
    except Exception:
        return False


def mark_briefed() -> None:
    try:
        _BRIEF_FILE.parent.mkdir(parents=True, exist_ok=True)
        _BRIEF_FILE.write_text(json.dumps({"date": datetime.now().strftime("%Y-%m-%d")}), encoding="utf-8")
    except Exception:
        pass
