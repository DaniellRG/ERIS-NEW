"""
actions/rutinas_diarias.py — Rutinas diarias de ERIS estilo Jarvis OS.

Inbox matutino, plan del día, métricas del sistema, vault Obsidian y cierre
del día. Orquesta tools existentes (db_tasks, goals, res_monitor, obsidian_note)
sin depender de la nube: funciona aunque Gemini/Ollama estén caídos.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
from core.logging_setup import get_obsidian_vault
VAULT_DIR = get_obsidian_vault()


def _run_tool(name: str, params: dict, player=None) -> str:
    try:
        from core.tool_registry import get_tool
        tool = get_tool(name)
        if tool is None:
            return f"(tool '{name}' no disponible)"
        return str(tool(params, player))
    except Exception as e:
        return f"(error en {name}: {e})"


def _now() -> str:
    return datetime.now().strftime("%H:%M")


def _date_slug() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _task_list(limit: int = 6) -> list[str]:
    lines = []
    try:
        res = _run_tool("db_tasks", {"action": "list"})
        for ln in res.splitlines():
            ln = ln.strip()
            if ln.startswith("#") and "[pending]" in ln:
                lines.append(ln)
    except Exception:
        pass
    return lines[:limit]


def _vault_exists() -> bool:
    return VAULT_DIR.exists()


def _vault_notes_today() -> list[str]:
    if not _vault_exists():
        return []
    try:
        return [p.name for p in VAULT_DIR.rglob("*.md") if _date_slug() in p.name][:5]
    except Exception:
        return []


def _write_vault_note(filename: str, content: str) -> str:
    try:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        target = VAULT_DIR / filename
        target.write_text(content, encoding="utf-8")
        return str(target)
    except Exception as e:
        return f"(no se pudo escribir en el vault: {e})"


def rutinas_diarias(parameters: dict = None, player=None) -> str:
    """Tool: rutinas diarias de ERIS (inbox, plan, métricas, vault, cierre)."""
    params = parameters or {}
    action = str(params.get("action") or "inbox").lower().strip()

    if action in ("inbox", "matutino", "buenos_dias", "morning"):
        return _inbox(player)

    if action in ("plan", "plan_del_dia", "plan_dia", "hoy"):
        return _plan(player)

    if action in ("metricas", "metricas_sistema", "sistema", "status"):
        return _metricas(player)

    if action in ("vault", "obsidian", "guardar", "anotar"):
        text = str(params.get("text") or params.get("nota") or params.get("note") or "").strip()
        if text:
            return _vault_save(text)
        return _vault_status()

    if action in ("cierre", "cierre_dia", "cierre_del_dia", "buenas_noches", "night"):
        return _cierre(player)

    if action in ("todas", "todo", "rutinas"):
        parts = [_inbox(player), _plan(player), _metricas(player), _vault_status()]
        return "\n\n".join(parts)

    return ("Acciones: inbox (matutino), plan, metricas, vault (guardar/anotar), "
            "cierre, todas. Ej: rutinas_diarias action=inbox")


def _inbox(player=None) -> str:
    vault_ok = _vault_exists()
    notes = _vault_notes_today()
    tasks = _task_list()
    out = [
        f"☀️ Buenos días, Daniel. Son las {_now()}.",
        f"Vault Obsidian: {'✓ disponible' if vault_ok else '✗ no encontrado'}.",
    ]
    if notes:
        out.append(f"Notas de hoy en el vault ({len(notes)}): {', '.join(notes)}")
    else:
        out.append("No hay notas nuevas de hoy en el vault.")
    if tasks:
        out.append(f"Tienes {len(tasks)} tareas pendientes:")
        for t in tasks:
            out.append(f"  • {t}")
    else:
        out.append("No tienes tareas pendientes registradas.")
    return "\n".join(out)


def _plan(player=None) -> str:
    tasks = _task_list(7)
    out = [f"📋 Plan del día ({_now()})"]
    if tasks:
        out.append("Prioridades de hoy:")
        for i, t in enumerate(tasks, 1):
            out.append(f"  {i}. {t}")
    else:
        out.append("No hay tareas programadas. ¿Quieres que agregue alguna?")
    goals = _run_tool("goals", {"action": "list"})
    if goals and "error" not in goals.lower() and "no disponible" not in goals.lower():
        out.append(f"Objetivos activos:\n{goals}")
    return "\n".join(out)


def _metricas(player=None) -> str:
    out = [f"📊 Métricas del sistema ({_now()})"]
    res = _run_tool("res_monitor", {"action": "status"})
    out.append(res if res else "(sin datos de recursos)")
    return "\n".join(out)


def _vault_save(text: str) -> str:
    if not _vault_exists():
        return ("El vault Obsidian no está disponible en "
                f"'{VAULT_DIR}'. Verifica la ruta.")
    slug = _date_slug()
    title = text[:60].strip().replace(" ", "-").replace("/", "-")
    path = _write_vault_note(f"{title}-{slug}.md", f"# {text[:120]}\n\n{text}\n\n_Fecha: {datetime.now().isoformat()}_\n")
    return f"Guardado en el vault: {path}"


def _vault_status() -> str:
    if not _vault_exists():
        return f"Vault Obsidian no encontrado en {VAULT_DIR}."
    count = 0
    try:
        count = sum(1 for _ in VAULT_DIR.rglob("*.md"))
    except Exception:
        pass
    return (f"Vault Obsidian activo: {VAULT_DIR}\nNotas totales: {count}\n"
            f"Acciones: rutinas_diarias action=vault text='<lo que quieras guardar>'.")


def _cierre(player=None) -> str:
    out = [f"🌙 Cierre del día — {_date_slug()} ({_now()})"]
    done = _run_tool("db_tasks", {"action": "list"})
    out.append("Estado de tareas:\n" + (done if done else "(sin tareas registradas)"))
    resume = (
        f"# Resumen del día {_date_slug()}\n\n"
        f"Generado por ERIS a las {_now()}.\n\n"
        f"Tareas/estado:\n{done}\n"
    )
    path = _write_vault_note(f"Resumen-{_date_slug()}.md", resume)
    out.append(f"Resumen guardado en el vault: {path}")
    out.append("Buenas noches, Daniel. Descansa.")
    return "\n".join(out)
