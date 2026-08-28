"""
actions/habit_tracker.py — Track user habits and routines for ERIS.
Actions:
  add        — Add a new habit
  log        — Log habit completion
  list       — List all habits with streak info
  stats      — Statistics for a habit
  streak     — Current streak for a habit
  delete     — Delete a habit
  reminders  — Show habits not done today
  export     — Export habit data to CSV
  leaderboard — Show habits ranked by consistency

Storage: D:/Eris_Source/data/habits.json
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_DATA_FILE = _BASE_DIR / "data" / "habits.json"


def _load() -> dict:
    try:
        if _DATA_FILE.exists():
            return json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"habits": {}, "completions": {}}


def _save(data: dict) -> None:
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    _DATA_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _date_range(start: str, end: str) -> list[str]:
    """Return list of date strings between start and end (inclusive)."""
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    dates = []
    while s <= e:
        dates.append(s.strftime("%Y-%m-%d"))
        s += timedelta(days=1)
    return dates


def _compute_streak(habit_name: str, completions: dict) -> tuple[int, int]:
    """Compute (current_streak, best_streak) for a habit."""
    habit_dates = sorted(completions.get(habit_name, []), reverse=True)
    if not habit_dates:
        return 0, 0

    today = datetime.now().date()
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()

    current = 0
    best = 0
    streak = 0
    check_date = today

    all_dates = sorted(set(habit_dates))

    # Build a set for O(1) lookup
    date_set = set(all_dates)

    # Current streak: count backwards from today or yesterday
    if today_str in date_set:
        check_date = today
    elif yesterday_str in date_set:
        check_date = today - timedelta(days=1)
    else:
        current = 0

    d = check_date
    while d.isoformat() in date_set:
        current += 1
        d -= timedelta(days=1)

    # Best streak: scan all dates
    sorted_dates = sorted(date_set)
    streak = 1
    best = 1
    for i in range(1, len(sorted_dates)):
        prev = datetime.strptime(sorted_dates[i - 1], "%Y-%m-%d")
        curr = datetime.strptime(sorted_dates[i], "%Y-%m-%d")
        if (curr - prev).days == 1:
            streak += 1
            best = max(best, streak)
        else:
            streak = 1
    best = max(best, streak)

    return current, best


def _completion_rate(habit_name: str, habit: dict, completions: dict, days: int = 30) -> float:
    """Calculate completion rate over last N days."""
    freq = habit.get("frequency", "daily")
    dates = completions.get(habit_name, [])
    today = datetime.now().date()

    if freq == "daily":
        expected = days
    elif freq == "weekly":
        expected = days // 7
    elif freq == "monthly":
        expected = days // 30
    else:
        expected = days

    count = 0
    for i in range(days):
        d = (today - timedelta(days=i)).isoformat()
        if d in dates:
            count += 1

    return round(count / max(expected, 1) * 100, 1)


def habit_tracker(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "list")).strip().lower()

    if player:
        try:
            player.write_log(f"[HabitTracker] action={action}")
        except Exception:
            pass

    data = _load()
    habits = data.get("habits", {})
    completions = data.get("completions", {})

    if action == "add":
        return _add(habits, completions, params, data)
    elif action == "log":
        return _log(habits, completions, params, data)
    elif action == "list":
        return _list_habits(habits, completions)
    elif action == "stats":
        return _stats(habits, completions, params)
    elif action == "streak":
        return _streak(habits, completions, params)
    elif action == "delete":
        return _delete(habits, completions, params, data)
    elif action == "reminders":
        return _reminders(habits, completions)
    elif action == "export":
        return _export_csv(habits, completions)
    elif action == "leaderboard":
        return _leaderboard(habits, completions)
    return "Actions: add, log, list, stats, streak, delete, reminders, export, leaderboard"


def _add(habits: dict, completions: dict, params: dict, data: dict) -> str:
    name = str(params.get("name", "")).strip()
    if not name:
        return "Falta el nombre del hábito."

    name_lower = name.lower()
    if name_lower in habits:
        return f"Ya existe un hábito '{habits[name_lower].get('name', name_lower)}'. Elegí otro nombre."

    frequency = str(params.get("frequency", "daily")).strip().lower()
    if frequency not in ("daily", "weekly", "monthly"):
        return f"Frecuencia no válida: {frequency}. Opciones: daily, weekly, monthly"

    try:
        target = int(params.get("target", 1))
    except (TypeError, ValueError):
        target = 1

    category = str(params.get("category", "general")).strip()

    habits[name_lower] = {
        "name": name,
        "frequency": frequency,
        "target": target,
        "category": category,
        "created": datetime.now().isoformat(),
    }
    completions[name_lower] = []
    data["habits"] = habits
    data["completions"] = completions
    _save(data)
    return f"Hábito '{name}' creado ({frequency}, meta: {target}x, categoría: {category})."


def _log(habits: dict, completions: dict, params: dict, data: dict) -> str:
    name = str(params.get("habit_name", params.get("name", ""))).strip()
    if not name:
        return "Falta el nombre del hábito para registrar."

    name_lower = name.lower()
    if name_lower not in habits:
        return f"No existe el hábito '{name}'. Crealo con 'add' primero."

    notes = str(params.get("notes", "")).strip()
    today = _today()

    dates = completions.get(name_lower, [])
    if today in dates:
        return f"Ya registraste '{habits[name_lower].get('name', name_lower)}' hoy."

    entry = today
    if notes:
        entry = f"{today}|{notes}"
    dates.append(entry)
    completions[name_lower] = dates
    data["completions"] = completions
    _save(data)

    current, best = _compute_streak(name_lower, completions)
    return f"¡Registrado! '{habits[name_lower].get('name', name_lower)}' completado. Racha actual: {current} días."


def _list_habits(habits: dict, completions: dict) -> str:
    if not habits:
        return "No tenés hábitos registrados. Creá uno con 'add'."

    lines = [f"Tus hábitos ({len(habits)}):\n"]
    for key, h in habits.items():
        current, best = _compute_streak(key, completions)
        freq = {"daily": "diario", "weekly": "semanal", "monthly": "mensual"}.get(h.get("frequency", "daily"), "?")
        done_today = _today() in completions.get(key, [])
        status = "HECHO" if done_today else "pendiente"
        lines.append(f"  {h.get('name', key)} [{status}]")
        lines.append(f"    Frecuencia: {freq} | Categoría: {h.get('category', '?')}")
        lines.append(f"    Racha actual: {current} | Mejor: {best}")
        lines.append("")

    return "\n".join(lines)


def _stats(habits: dict, completions: dict, params: dict) -> str:
    name = str(params.get("habit_name", params.get("name", ""))).strip()
    period = str(params.get("period", "month")).strip().lower()

    if not name:
        return "Falta 'habit_name' para ver estadísticas."

    name_lower = name.lower()
    if name_lower not in habits:
        return f"No existe el hábito '{name}'."

    h = habits[name_lower]
    dates = completions.get(name_lower, [])

    period_days = {"week": 7, "month": 30, "year": 365}.get(period, 30)
    today = datetime.now().date()
    start = (today - timedelta(days=period_days)).isoformat()

    count = sum(1 for d in dates if d >= start)
    rate = _completion_rate(name_lower, h, completions, period_days)
    current, best = _compute_streak(name_lower, completions)

    lines = [
        f"Estadísticas de '{h.get('name', name)}' (últimos {period_days} días):",
        f"  Completado: {count} veces",
        f"  Tasa de cumplimiento: {rate}%",
        f"  Racha actual: {current}",
        f"  Mejor racha: {best}",
        f"  Frecuencia: {h.get('frequency', '?')}",
        f"  Meta por período: {h.get('target', '?')}",
    ]

    if dates:
        lines.append(f"\n  Últimas fechas: {', '.join(sorted(dates)[-5:])}")
    return "\n".join(lines)


def _streak(habits: dict, completions: dict, params: dict) -> str:
    name = str(params.get("habit_name", params.get("name", ""))).strip()
    if not name:
        return "Falta 'habit_name'."

    name_lower = name.lower()
    if name_lower not in habits:
        return f"No existe el hábito '{name}'."

    current, best = _compute_streak(name_lower, completions)
    hname = habits[name_lower].get("name", name)
    return f"'{hname}': racha actual = {current} días, mejor racha = {best} días."


def _delete(habits: dict, completions: dict, params: dict, data: dict) -> str:
    name = str(params.get("habit_name", params.get("name", ""))).strip()
    if not name:
        return "Falta 'habit_name' para eliminar."

    name_lower = name.lower()
    if name_lower not in habits:
        return f"No existe el hábito '{name}'."

    hname = habits[name_lower].get("name", name)
    del habits[name_lower]
    completions.pop(name_lower, None)
    data["habits"] = habits
    data["completions"] = completions
    _save(data)
    return f"Hábito '{hname}' eliminado."


def _reminders(habits: dict, completions: dict) -> str:
    today = _today()
    pending = []

    for key, h in habits.items():
        dates = completions.get(key, [])
        if today not in dates:
            pending.append(h.get("name", key))

    if not pending:
        return "Todos los hábitos de hoy están completados. ¡Bien!"

    lines = [f"Hábitos pendientes para hoy ({len(pending)}):"]
    for name in pending:
        lines.append(f"  - {name}")
    return "\n".join(lines)


def _export_csv(habits: dict, completions: dict) -> str:
    if not habits:
        return "No hay hábitos para exportar."

    out_dir = _BASE_DIR / "data" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"habits_{timestamp}.csv"

    try:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Hábito", "Frecuencia", "Categoría", "Meta",
                             "Fecha_Registro", "Notas"])

            for key, h in habits.items():
                dates = sorted(completions.get(key, []))
                for d in dates:
                    note = ""
                    if "|" in d:
                        parts = d.split("|", 1)
                        d = parts[0]
                        note = parts[1]
                    writer.writerow([
                        h.get("name", key),
                        h.get("frequency", ""),
                        h.get("category", ""),
                        h.get("target", 1),
                        d,
                        note,
                    ])

        return f"Exportado a: {out_path}"
    except Exception as e:
        return f"Error exportando: {e}"


def _leaderboard(habits: dict, completions: dict) -> str:
    if not habits:
        return "No hay hábitos para rankear."

    rankings = []
    for key, h in habits.items():
        current, best = _compute_streak(key, completions)
        rate = _completion_rate(key, h, completions, 30)
        total = len(completions.get(key, []))
        rankings.append({
            "name": h.get("name", key),
            "current_streak": current,
            "best_streak": best,
            "rate_30d": rate,
            "total": total,
        })

    rankings.sort(key=lambda x: (-x["current_streak"], -x["rate_30d"], -x["best_streak"]))

    lines = ["Leaderboard de hábitos:\n"]
    for i, r in enumerate(rankings, 1):
        medal = {1: "[1°]", 2: "[2°]", 3: "[3°]"}.get(i, f"[{i}°]")
        lines.append(
            f"  {medal} {r['name']} — "
            f"racha: {r['current_streak']} | mejor: {r['best_streak']} | "
            f"cumplimiento: {r['rate_30d']}% | total: {r['total']}"
        )
    return "\n".join(lines)
