#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/tool_wrappers.py — Wrappers que transforman los GETTERS (que devuelven
objetos) en tools callables que respetan el `action` declarado y devuelven
SIEMPRE str|dict legible.

Las siguientes tools declaradas en core/tool_declarations.py apuntan a getters
que devuelven singletons:
  - agent_bus          → core.agent_bus.get_agent_bus()   [object at 0x...]
  - memory_unified     → core.memory_unified.get_memory() [object at 0x...]
  - permission_gate    → core.permission_gate.get_permission_gate() [object]
  - ast_edit           → core.ast_editor.safe_edit(...)     [missing required args]
  - eris_update        → core.updater.check_for_update()  [no devolvió resultado]

ESTOS WRAPPERS se registran en core/tool_registry.py reemplazando los pares
(módulo, función) originales, manteniendo el sync registry ↔ declarations.
"""
import json, os, sys, importlib, subprocess, time
from pathlib import Path

# Evitar hardcodeos de rutas: usar Path(__file__).resolve().parent.parent
_BASE = Path(__file__).resolve().parent.parent


# ── 1. agent_bus: wrapper con action dispatch ──
def agent_bus_tool(action: str = "status", event: str = "", data: str = "") -> str:
    """Interfaz de agentes especializados (deploy, dev, file, etc.).

    Acciones:
      - status: lista los agentes cargados
      - event: publica un evento en el bus
      - data: info extra (JSON)
    """
    try:
        from core.agent_bus import get_agent_bus
        bus = get_agent_bus()
        _agents = getattr(bus, "agents", {})
        if action == "status":
            if not _agents:
                return "No hay agentes registrados en el bus."
            return "Agentes en el bus:\n" + "\n".join(
                f"  • {name}" for name in sorted(_agents.keys())
            )
        elif action == "event":
            if event:
                bus.publish(event, json.loads(data) if data else None)
                return f"Evento '{event}' publicado en el bus."
            return "Especificá un evento para publicar (action=event, event=NOMBRE)."
        return "Acción desconocida. Usá 'status' (default) o 'event'."
    except Exception as e:
        return f"Error agent_bus: {e}"


# ── 2. memory_unified: wrapper con action dispatch ──
def memory_unified_tool(action: str = "status", query: str = "", category: str = "notes") -> str:
    """Interfaz unificada de memoria (persistente + episódica + conocimiento).

    Acciones:
      - status:  estado del sistema de memoria
      - query:   buscar en todas las memorias
      - category: listar/borrar por categoría (notes, conocimiento, episodios)
    """
    try:
        from core.memory_unified import get_memory
        mem = get_memory()
        if action == "status":
            info = mem.info() if hasattr(mem, "info") else str(type(mem))
            return f"Sistema de memoria OK.\n{info}" if isinstance(info, str) else f"Estado: {info}"
        elif action == "query":
            if query:
                results = mem.search(query, limit=5) if hasattr(mem, "search") else []
                if results:
                    return "Resultados:\n" + "\n".join(f"  • {r}" for r in results[:5])
                return f"No se encontraron resultados para: {query}"
            return "Especificá un query para buscar (action=query, query=TEXT)."
        elif action == "category":
            items = mem.list(category) if hasattr(mem, "list") else []
            return f"[{category}]\n" + "\n".join(f"  • {i}" for i in items[:10]) if items else f"[{category}] vacío."
        return "Acción desconocida. Usá 'status' (default), 'query' o 'category'."
    except Exception as e:
        return f"Error memory_unified: {e}"


# ── 3. permission_gate: wrapper con action dispatch ──
def permission_gate_tool(action: str = "status", tool_name: str = "", args: str = "") -> str:
    """Interfaz de permisos de seguridad.

    Acciones:
      - status:  estado del gate (cuántas reglas activas)
      - check:   simular un chequeo (tool_name=NAME)
      - rules:   listar reglas conocidas
    """
    try:
        from core.permission_gate import get_permission_gate
        g = get_permission_gate()
        if action == "status":
            rules = getattr(g, "rules", {})
            return f"Gate activo. Reglas cargadas: {len(rules) if rules else 'dinámicas'}"
        elif action == "check":
            if tool_name:
                r = g.check(tool_name, json.loads(args) if args else {})
                return f"Tool '{tool_name}': allowed={r.allowed}, reason={r.reason}"
            return "Especificá tool_name para simular check."
        elif action == "rules":
            rules = getattr(g, "rules", {})
            if rules:
                return "Reglas:\n" + "\n".join(f"  • {k}" for k in rules)
            return "Gate en modo dinámico (no hay reglas predefinidas)."
        return f"Permission gate OK. (action={action}). Usá 'status' (default), 'check' o 'rules'."
    except Exception as e:
        return f"Error permission_gate: {e}"


# ── 4. ast_edit: wrapper que resuelve params con _build_kwargs ──
def ast_edit(filepath: str = "", action: str = "edit", old_text: str = "",
             new_text: str = "", code: str = "", target: str = "") -> str:
    """Edita código con análisis AST. Action dispatch:
      - edit:   safe_edit(filepath, old_text, new_text)
      - analyze: analizar archivo (filepath=PATH)
      - create: crear archivo (filepath=PATH, code=CONTENT)
    """
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
        old = old_text or target or ""
        new = new_text or code or ""
        if not old or not new:
            return (f"safe_edit requiere old_text + new_text. "
                    f"Recibido: filepath='{filepath}', old='{old}', new='{new}'")
        result = safe_edit(filepath, old, new)
        return str(result) if result is not None else f"safe_edit aplicado a {filepath}"
    except TypeError as te:
        return f"ast_edit: error de parámetros — {te}. Usá args: filepath, old_text, new_text."
    except Exception as e:
        return f"Error ast_edit: {e}"


# ── 5. eris_update: wrapper que llama check_for_update ──
def eris_update(action: str = "check", player=None) -> str:
    """Chequea actualizaciones de ERIS.

    Acciones:
      - check:  check_for_update() → str de resultado
      - status: estado del sistema de actualización
    """
    try:
        from core.updater import check_for_update, eris_updater
        if action == "check":
            r = check_for_update()
            if r is None:
                return "check_for_update() no devolvió datos (puede que esté deshabilitado)."
            return str(r)
        elif action == "status":
            return eris_updater() if callable(eris_updater) else "eris_updater no disponible"
        return str(check_for_update())
    except Exception as e:
        return f"Error eris_update: {e}"
