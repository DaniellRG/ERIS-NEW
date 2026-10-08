#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/tool_wrappers.py — Wrappers action-dispatch para 5 tools que tenían
getters que devolvían objetos (object at 0x) o fallaban por params.

Cada wrapper recibe `parameters` (dict) como único primer arg — el
_build_kwargs del dispatcher lo detecta (first == "parameters") y pasa
el dict de args completo. Adentro, cada wrapper hace action-dispatch.

Las 5 tools declaradas en core/tool_declarations.py apuntaban a:
  - agent_bus          → core.agent_bus.get_agent_bus()   [object at 0x...]
  - memory_unified     → core.memory_unified.get_memory() [object at 0x...]
  - permission_gate    → core.permission_gate.get_permission_gate() [object]
  - ast_edit           → core.ast_editor.safe_edit(...)     [missing required args]
  - eris_update        → core.updater.check_for_update()  [no devolvió resultado]

ESTOS WRAPPERS se registran en core/tool_registry.py reemplazando los
pares (módulo, función) originales, manteniendo el sync registry ↔ declarations.
"""
import json
from pathlib import Path


# ── 1. agent_bus ──
def agent_bus_tool(parameters: dict = None, player=None) -> str:
    """Lista agentes, publica eventos, gestiona el bus de agentes.
    actions: status, event, data.
    """
    parameters = parameters or {}
    action = parameters.get("action", "status")
    try:
        from core.agent_bus import get_agent_bus
        bus = get_agent_bus()
        _agents = getattr(bus, "agents", {})
        if action == "status":
            if not _agents:
                return "No hay agentes registrados en el bus."
            return "Agentes en el bus:\n" + "\n".join(
                f"  * {name}" for name in sorted(_agents.keys())
            )
        elif action == "event":
            event = parameters.get("event", "")
            if event:
                bus.publish(event, parameters.get("data"))
                return f"Evento '{event}' publicado en el bus."
            return "Especificá un evento para publicar (action=event, event=NOMBRE)."
        return f"Accion desconocida '{action}'. Usá 'status' (default) o 'event'."
    except Exception as e:
        return f"Error agent_bus: {e}"


# ── 2. memory_unified ──
def memory_unified_tool(parameters: dict = None, player=None) -> str:
    """Gestiona memoria persistente, episodica y de conocimiento.
    actions: status, query, category.
    """
    parameters = parameters or {}
    action = parameters.get("action", "status")
    try:
        from core.memory_unified import get_memory
        mem = get_memory()
        if action == "status":
            return f"Sistema de memoria OK. Tipo: {type(mem).__name__}"
        elif action == "query":
            query = parameters.get("query", "")
            if query:
                results = mem.search(query, limit=5) if hasattr(mem, "search") else []
                if results:
                    return "Resultados:\n" + "\n".join(f"  * {r}" for r in str(results)[:5])
                return f"No se encontraron resultados para: {query}"
            return "Especificá query para buscar (action=query, query=TEXT)."
        elif action == "category":
            cat = parameters.get("category", "notes")
            items = mem.list(cat) if hasattr(mem, "list") else []
            if items:
                return f"[{cat}]\n" + "\n".join(f"  * {i}" for i in items[:10])
            return f"[{cat}] vacío."
        return f"Accion desconocida '{action}'. Usá 'status', 'query' o 'category'."
    except Exception as e:
        return f"Error memory_unified: {e}"


# ── 3. permission_gate ──
def permission_gate_tool(parameters: dict = None, player=None) -> str:
    """Estado y chequeo de permisos de seguridad.
    actions: status, check, rules.
    """
    parameters = parameters or {}
    action = parameters.get("action", "status")
    try:
        from core.permission_gate import get_permission_gate
        g = get_permission_gate()
        if action == "status":
            rules = getattr(g, "rules", {})
            return f"Gate activo. {len(rules) if rules else 'Sin reglas predefinidas'}."
        elif action == "check":
            tool_name = parameters.get("tool_name", "")
            if tool_name:
                r = g.check(tool_name, parameters.get("args", {}))
                return f"Tool '{tool_name}': allowed={r.allowed}, reason={r.reason}"
            return "Especificá tool_name para simular check."
        elif action == "rules":
            rules = getattr(g, "rules", {})
            if rules:
                return "Reglas:\n" + "\n".join(f"  * {k}" for k in rules)
            return "Gate en modo dinámico (no hay reglas predefinidas)."
        return f"Permission gate OK (action={action}). Usá 'status', 'check' o 'rules'."
    except Exception as e:
        return f"Error permission_gate: {e}"


# ── 4. ast_edit ──
def ast_edit(parameters: dict = None, player=None) -> str:
    """Edita código con análisis AST.
    actions: edit (filepath, old_text, new_text), analyze (filepath),
    create (filepath, code).
    """
    parameters = parameters or {}
    action = parameters.get("action", "edit")
    filepath = parameters.get("filepath", parameters.get("file_path", ""))
    old_text = parameters.get("old_text", parameters.get("target", ""))
    new_text = parameters.get("new_text", parameters.get("code", ""))
    code = parameters.get("code", parameters.get("new_text", ""))
    try:
        from core.ast_editor import safe_edit, analyze_file
        if action == "analyze" or (not old_text and not new_text and filepath):
            if filepath:
                return str(analyze_file(filepath))
            return "Especificá filepath para analizar."
        if action == "create":
            if filepath and code:
                Path(filepath).parent.mkdir(parents=True, exist_ok=True)
                Path(filepath).write_text(code or "", encoding="utf-8")
                return f"Archivo creado: {filepath}"
            return "Especificá filepath + code para crear."
        # action == edit (default)
        if not filepath:
            return "Especificá filepath para editar."
        if not old_text or not new_text:
            return (f"safe_edit requiere old_text + new_text. "
                    f"filepath='{filepath}', old='{old_text}', new='{new_text}'")
        result = safe_edit(filepath, old_text, new_text)
        return str(result) if result is not None else f"safe_edit aplicado a {filepath}"
    except TypeError as te:
        return f"ast_edit: error de parametros — {te}. Usá: filepath, old_text, new_text."
    except Exception as e:
        return f"Error ast_edit: {e}"


# ── 5. eris_update ──
def eris_update(parameters: dict = None, player=None) -> str:
    """Chequea actualizaciones de ERIS.
    actions: check, status.
    """
    parameters = parameters or {}
    action = parameters.get("action", "check")
    try:
        from core.updater import check_for_update, eris_updater
        if action == "check":
            r = check_for_update()
            if r is None:
                return "check_for_update no devolvio datos (puede estar deshabilitado)."
            return str(r)
        elif action == "status":
            return eris_updater() if callable(eris_updater) else "eris_updater no disponible"
        return str(check_for_update())
    except Exception as e:
        return f"Error eris_update: {e}"
