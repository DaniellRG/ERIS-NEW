# -*- coding: utf-8 -*-
"""core/goal_context.py — ALINEACIÓN DE METAS ("el por qué").

Fase F5a (2026-10-13). Federación de LECTURA (no unifica escritura) de los dos
stores de metas activos de Eris:

  - goal_setting (memory/goals.json)  -> metas autónomas que Eris se auto-genera
                                          (lo que `main.py` auto-puebla al arrancar).
  - goal_tracker (data/goals.json)    -> objetivos ricos con subtareas/milestones.

`linea_meta()` devuelve una línea compacta para inyectar como `[METAS]` en el
prompt (o "" si no hay nada activo). Incluye el `id` para que el modelo pueda
pasarlo como `goal_id` a `agente_sub`/`proyectar` y las tareas arrastren el
propósito. `meta_activa()` devuelve el dict de la meta más prioritaria.

Nunca lanza: cualquier fallo degrada a "".
"""
from __future__ import annotations

_PRIO = {"critical": 4, "high": 3, "medium": 2, "low": 1}

__all__ = ["metas_activas", "meta_activa", "linea_meta"]


def _de_goal_setting() -> list[dict]:
    """Metas activas de memory/goals.json (goal_setting autónomo)."""
    out: list[dict] = []
    try:
        from core.goal_setting import list_goals
        for g in list_goals("active"):
            out.append({
                "id": str(g.get("id", "")),
                "title": str(g.get("title", "")).strip(),
                "progress": int(g.get("progress", 0) or 0),
                "priority": str(g.get("priority", "medium")),
                "next": "",
                "source": "goal_setting",
            })
    except Exception:
        pass
    return out


def _de_goal_tracker() -> list[dict]:
    """Objetivos activos de data/goals.json (goal_tracker rico)."""
    out: list[dict] = []
    try:
        from core.goal_tracker import get_active_goals, get_next_step
        for g in get_active_goals():
            step = get_next_step(str(g.get("id", ""))) or {}
            out.append({
                "id": str(g.get("id", "")),
                "title": str(g.get("title", "")).strip(),
                "progress": int(g.get("progress", 0) or 0),
                "priority": str(g.get("priority", "medium")),
                "next": str(step.get("text", "")).strip(),
                "source": "goal_tracker",
            })
    except Exception:
        pass
    return out


def metas_activas() -> list[dict]:
    """Metas/objetivos activos de ambos stores, ordenados por prioridad.

    Es una federación de LECTURA: no unifica ni migra ningún store.
    """
    try:
        merged = _de_goal_tracker() + _de_goal_setting()
        merged = [m for m in merged if m["title"]]
        merged.sort(key=lambda m: _PRIO.get(m["priority"], 2), reverse=True)
        seen: set[str] = set()
        out: list[dict] = []
        for m in merged:
            key = m["title"].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(m)
        return out
    except Exception:
        return []


def meta_activa() -> dict | None:
    """La meta activa más prioritaria (con su `id`), o None."""
    metas = metas_activas()
    return metas[0] if metas else None


def linea_meta() -> str:
    """Línea `[METAS] ...` para el prompt, o "" si no hay metas activas."""
    try:
        metas = metas_activas()
        if not metas:
            return ""
        top = metas[0]
        txt = '[METAS] Objetivo activo: "{}"'.format(top["title"][:80])
        if top["id"]:
            txt += f' (id {top["id"]}, {top["progress"]}%)'
        else:
            txt += f' ({top["progress"]}%)'
        if top["next"]:
            txt += f' · Próximo paso: {top["next"][:80]}'
        if len(metas) > 1:
            otras = ", ".join(m["title"][:30] for m in metas[1:3])
            txt += f' · Otras activas: {otras}'
        return txt
    except Exception:
        return ""
