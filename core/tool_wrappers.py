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

CONTRATO: las acciones que expone cada wrapper están alineadas con el bloque
correspondiente de core/tool_declarations.py (el vocabulario que ve el LLM).
Si cambiás una action acá, sincronizala también en la declaration.
"""
import json
from pathlib import Path


# ── 1. agent_bus ──
def agent_bus_tool(parameters: dict = None, player=None) -> str:
    """Bus de agentes: lista agentes/colas, publica eventos y lee bandejas.
    actions: list (default), publish, inbox.
    """
    parameters = parameters or {}
    action = str(parameters.get("action", "list")).strip().lower()
    try:
        from core.agent_bus import get_agent_bus
        bus = get_agent_bus()

        if action in ("list", "status"):
            st = bus.status() if hasattr(bus, "status") else {}
            lines = []
            handlers = st.get("handlers", [])
            lines.append("Agentes con handler: " + (", ".join(handlers) if handlers else "(ninguno)"))
            queues = st.get("queues", {})
            if queues:
                lines.append("Colas pendientes: " + ", ".join(f"{k}={v}" for k, v in queues.items()))
            shared = st.get("shared_keys", [])
            if shared:
                lines.append("Estado compartido: " + ", ".join(shared))
            subs = st.get("subscribers", [])
            if subs:
                lines.append("Suscripciones de eventos: " + ", ".join(subs))
            return "\n".join(lines)

        if action in ("publish", "emit", "event"):
            event = parameters.get("event", "") or parameters.get("name", "")
            if not event:
                return "Especificá event para publicar (action=publish, event=NOMBRE)."
            payload = parameters.get("data", parameters.get("payload"))
            if isinstance(payload, str) and payload.strip():
                try:
                    payload = json.loads(payload)
                except Exception:
                    pass
            bus.publish(event, payload if isinstance(payload, dict) else {"data": payload})
            return f"Evento '{event}' publicado en el bus."

        if action in ("inbox", "peek", "messages"):
            agent = parameters.get("agent", "") or parameters.get("receiver", "")
            if not agent:
                return "Especificá agent para ver su bandeja (action=inbox, agent=NOMBRE)."
            msgs = bus.peek(agent) if hasattr(bus, "peek") else []
            if not msgs:
                return f"Bandeja de '{agent}' vacía."
            return f"Bandeja de '{agent}' ({len(msgs)}):\n" + "\n".join(
                f"  * de {m.get('sender', '?')}: {m.get('action', '?')}" for m in msgs
            )

        return f"Accion desconocida '{action}'. Usá 'list' (default), 'publish' o 'inbox'."
    except Exception as e:
        return f"Error agent_bus: {e}"


# ── 2. memory_unified ──
def memory_unified_tool(parameters: dict = None, player=None) -> str:
    """Memoria unificada (semántica, episódica, facts, working).
    actions: status (default), search, store, retrieve, recent.
    """
    parameters = parameters or {}
    action = str(parameters.get("action", "status")).strip().lower()
    try:
        from core.memory_unified import get_memory
        mem = get_memory()

        if action == "status":
            return f"Memoria unificada OK ({type(mem).__name__})."

        if action in ("search", "query", "buscar"):
            query = parameters.get("query", "") or parameters.get("q", "")
            if not query:
                return "Especificá query para buscar (action=search, query=TEXTO)."
            res = mem.search_all(query) if hasattr(mem, "search_all") else {}
            hits = []
            if isinstance(res, dict):
                for layer, items in res.items():
                    for it in (items or []):
                        hits.append(f"[{layer}] {str(it)[:200]}")
            if not hits:
                return f"No se encontraron resultados para: {query}"
            return "Resultados:\n" + "\n".join(f"  * {h}" for h in hits[:10])

        if action in ("store", "save", "remember", "guardar"):
            text = (parameters.get("text") or parameters.get("query")
                    or parameters.get("content") or parameters.get("statement") or "")
            if not str(text).strip():
                return "Especificá text/query con lo que querés guardar (action=store)."
            category = parameters.get("category", "")
            key = parameters.get("key", "")
            if category and key:
                mem.remember(category, key, str(text))
                return f"Guardado en memoria [{category}].{key}."
            mem.add_fact(str(text), source="eris")
            return "Hecho guardado en memoria."

        if action in ("retrieve", "recall", "get", "recuperar"):
            category = parameters.get("category", "")
            key = parameters.get("key", "")
            if not category:
                return "Especificá category (y opcional key) para recuperar (action=retrieve)."
            return str(mem.recall(category, key))

        if action in ("recent", "episodic", "reciente"):
            events = mem.recent_events(10) if hasattr(mem, "recent_events") else []
            if not events:
                return "Sin eventos recientes."
            return "Eventos recientes:\n" + "\n".join(
                f"  * {e.get('event', '?')}" for e in events
            )

        return f"Accion desconocida '{action}'. Usá 'status', 'search', 'store', 'retrieve' o 'recent'."
    except Exception as e:
        return f"Error memory_unified: {e}"


# ── 3. permission_gate ──
def permission_gate_tool(parameters: dict = None, player=None) -> str:
    """Estado, chequeo y reglas del gate de permisos.
    actions: status (default), check, approve, deny, list_rules.
    """
    parameters = parameters or {}
    action = str(parameters.get("action", "status")).strip().lower()
    try:
        from core.permission_gate import get_permission_gate, _reload_rules
        g = get_permission_gate()

        if action in ("status", "list_rules", "rules"):
            try:
                rules = _reload_rules() or {}
            except Exception:
                rules = {}
            auto_appr = sorted(getattr(g, "_auto_approve", set()) or [])
            auto_deny = sorted(getattr(g, "_auto_deny", set()) or [])
            parts = [f"Permission gate activo. Reglas explícitas: {len(rules)}."]
            if auto_appr:
                parts.append("Auto-aprobadas: " + ", ".join(auto_appr))
            if auto_deny:
                parts.append("Auto-denegadas: " + ", ".join(auto_deny))
            if rules:
                parts.append("Reglas: " + ", ".join(f"{k}={v}" for k, v in rules.items()))
            if action == "list_rules" and not rules:
                parts.append("(Sin reglas en data/permission_rules.json — gate en modo heurístico.)")
            return "\n".join(parts)

        if action == "check":
            tool_name = parameters.get("tool_name", "") or parameters.get("tool", "")
            if not tool_name:
                return "Especificá tool_name para simular el check (action=check)."
            args = parameters.get("args") or {}
            if isinstance(args, str) and args.strip():
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            r = g.check(tool_name, args if isinstance(args, dict) else {})
            return f"Tool '{tool_name}': allowed={r.allowed}, reason={r.reason}"

        if action in ("approve", "allow"):
            tool_name = parameters.get("tool_name", "") or parameters.get("tool", "")
            if not tool_name:
                return "Especificá tool_name para auto-aprobar (action=approve)."
            g.set_auto_approve(set(getattr(g, "_auto_approve", set())) | {tool_name})
            return f"'{tool_name}' agregada a auto-aprobadas."

        if action in ("deny", "block"):
            tool_name = parameters.get("tool_name", "") or parameters.get("tool", "")
            if not tool_name:
                return "Especificá tool_name para auto-denegar (action=deny)."
            g.set_auto_deny(set(getattr(g, "_auto_deny", set())) | {tool_name})
            return f"'{tool_name}' agregada a auto-denegadas."

        return f"Accion desconocida '{action}'. Usá 'status', 'check', 'approve', 'deny' o 'list_rules'."
    except Exception as e:
        return f"Error permission_gate: {e}"


# ── 4. ast_edit ──
def ast_edit(parameters: dict = None, player=None) -> str:
    """Analiza o edita código Python.
    actions: analyze, edit (default), add_import, remove_import.
    Acepta el param `file` (canónico, usado por file_undo) o `filepath`.
    """
    parameters = parameters or {}
    action = str(parameters.get("action", "edit")).strip().lower()
    filepath = parameters.get("file") or parameters.get("filepath") or parameters.get("file_path") or ""
    old_text = parameters.get("old_text", parameters.get("target_old", ""))
    new_text = parameters.get("new_text", parameters.get("target_new", ""))
    code = parameters.get("code", parameters.get("import_line", ""))
    target = parameters.get("target", parameters.get("module", ""))
    try:
        from core.ast_editor import safe_edit, analyze_file, insert_import, remove_import

        if action in ("analyze", "analizar"):
            if not filepath:
                return "Especificá file para analizar (action=analyze)."
            return str(analyze_file(filepath))

        if action in ("add_import", "insert_import"):
            if not filepath or not code:
                return "Especificá file + code (línea de import) para add_import."
            return str(insert_import(filepath, code))

        if action in ("remove_import",):
            if not filepath or not target:
                return "Especificá file + target (módulo) para remove_import."
            return str(remove_import(filepath, target))

        # action == edit (default)
        if not filepath:
            return "Especificá file para editar (action=edit)."
        if not old_text or not new_text:
            return ("edit requiere old_text + new_text. "
                    f"file='{filepath}', old='{old_text}', new='{new_text}'")
        result = safe_edit(filepath, old_text, new_text)
        return str(result) if result is not None else f"safe_edit aplicado a {filepath}"
    except TypeError as te:
        return f"ast_edit: error de parametros — {te}. Usá: file, old_text, new_text."
    except Exception as e:
        return f"Error ast_edit: {e}"


# ── 5. eris_update ──
def eris_update(parameters: dict = None, player=None) -> str:
    """Chequea actualizaciones de ERIS (delega en eris_updater, que nunca
    devuelve None). Sin parámetros = check. actions: check, status.
    """
    parameters = parameters or {}
    action = str(parameters.get("action", "check")).strip().lower()
    try:
        from core.updater import eris_updater
        # eris_updater ya hace action-dispatch y devuelve siempre un string útil.
        return eris_updater({**parameters, "action": action})
    except Exception as e:
        return f"Error eris_update: {e}"
