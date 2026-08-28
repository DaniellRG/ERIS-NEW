# -*- coding: utf-8 -*-
"""
self_extend.py — Loop seguro de auto-extension para ERIS.

Ciclo: propuesta -> implementacion (auto_programmer: py_compile + sandbox)
    -> registro (tool_registry + action_imports + tool_declarations)
    -> verificacion (self_regression: compile total + pytest + auditoria A/B)
    -> revert si la verificacion falla (restaura backups).

El ciclo garantiza que ERIS solo active tools auto-generadas que pasan
todas las validaciones, y que nunca deja el proyecto en estado roto.
"""
from __future__ import annotations

import io
import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
ACTIONS_DIR = PROJECT_DIR / "actions"
CORE_DIR = PROJECT_DIR / "core"
BACKUP_DIR = PROJECT_DIR / "data" / "self_extend_backups"

_REGISTRY = CORE_DIR / "tool_registry.py"
_IMPORTS = CORE_DIR / "action_imports.py"
_DECLARATIONS = CORE_DIR / "tool_declarations.py"

_STATE_FILE = PROJECT_DIR / "memory" / "self_extend.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tools": {}}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _backup(targets: dict) -> dict:
    """Copia de seguridad de los archivos a editar. Devuelve mapa relativo -> backup path."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backups = {}
    for name, path in targets.items():
        if not path.exists():
            continue
        bpath = BACKUP_DIR / f"{stamp}_{name}"
        shutil.copy2(str(path), str(bpath))
        backups[name] = str(bpath)
    return backups


def _restore(backups: dict):
    for name, bpath in backups.items():
        target = {"registry": _REGISTRY, "imports": _IMPORTS, "declarations": _DECLARATIONS}.get(name)
        if target and Path(bpath).exists():
            shutil.copy2(str(bpath), str(target))


def _implement(tool_name: str, python_code: str, description: str,
               params_schema: dict, test_params: dict) -> tuple[bool, str]:
    """Paso 1: escribe el archivo, py_compile y sandbox via auto_programmer."""
    from actions.auto_programmer import auto_programmer
    result = auto_programmer({
        "action": "create_tool",
        "tool_name": tool_name,
        "description": description,
        "parameters_schema": json.dumps(params_schema or {}),
        "python_code": python_code,
        "test_parameters": test_params or {},
    })
    ok = ("desarrollada e integrada con éxito" in result
          or "Compilación: Exitosa" in result and "Sandbox: Exitosa" in result)
    return ok, result


def _register(tool_name: str, module: str, func: str, decl: dict) -> tuple[bool, str]:
    """Paso 2: registra la tool en tool_registry, action_imports y tool_declarations."""
    errors = []

    # 1) tool_registry.py
    try:
        src = _REGISTRY.read_text(encoding="utf-8")
        entry = f'    "{tool_name}":            ("{module}", "{func}"),\n'
        if f'"{tool_name}"' not in src:
            marker = '    # ── Batch 4B: Stub Tools (declared but not yet implemented) ──\n'
            if marker in src:
                src = src.replace(marker, entry + marker)
            else:
                src = src.rstrip("\n") + "\n" + entry
            _REGISTRY.write_text(src, encoding="utf-8")
    except Exception as e:
        errors.append(f"tool_registry: {e}")

    # 2) action_imports.py — insertar try/except block tras el bloque de data_visualize
    try:
        src = _IMPORTS.read_text(encoding="utf-8")
        block = (f"try:\n"
                 f"    from actions.{tool_name} import {tool_name}\n"
                 f"except ImportError:\n"
                 f"    {tool_name} = None\n")
        if f"from actions.{tool_name}" not in src:
            anchor = "except ImportError:\n    data_visualize = None\n"
            if anchor in src:
                src = src.replace(anchor, anchor + block, 1)
            else:
                src = src.rstrip("\n") + "\n" + block
            _IMPORTS.write_text(src, encoding="utf-8")
    except Exception as e:
        errors.append(f"action_imports: {e}")

    # 3) tool_declarations.py — insertar la declaracion antes del cierre del array
    try:
        src = _DECLARATIONS.read_text(encoding="utf-8")
        if f'"name": "{tool_name}"' not in src:
            block = _build_declaration_block(decl)
            marker = '\n    {\n        "name": "disk_wiper",'
            if marker in src:
                src = src.replace(marker, block + marker, 1)
            else:
                # ultimo "}]" del array (buscar "}\n    }\n]" real, no el primer cierre)
                idx = src.rfind("\n    }\n]")
                if idx >= 0:
                    src = src[:idx] + "\n    }" + block + "\n]"
                else:
                    raise RuntimeError("No se encontro el cierre del array TOOL_DECLARATIONS")
            _DECLARATIONS.write_text(src, encoding="utf-8")
    except Exception as e:
        errors.append(f"tool_declarations: {e}")

    if errors:
        return False, "Errores de registro:\n  " + "\n  ".join(errors)
    return True, "Tool registrada en tool_registry, action_imports y tool_declarations."


def _build_declaration_block(decl: dict) -> str:
    """Construye el bloque de declaracion con el formato del archivo:
    llaves de objeto a 4 espacios, campos a 8, alineado al estilo existente."""
    lines = ["\n    {"]
    for k, v in decl.items():
        lines.append(f"        {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)},")
    lines.append("    },")
    return "\n".join(lines)


def _verify() -> tuple[bool, dict]:
    """Paso 3: self_regression completa (compile + pytest + auditoria)."""
    from actions.self_regression import self_regression
    out = self_regression({"action": "run"})
    ok = ("RESULTADO: ✓ TODO OK" in out or "RESULTADO: ✔ TODO OK" in out)
    return ok, {"output": out[:2000]}


def self_extend(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action") or "status").lower().strip()
    tool_name = str(params.get("tool_name") or "").strip()
    module = str(params.get("module") or f"actions.{tool_name}").strip()
    func = str(params.get("func") or tool_name).strip()
    description = str(params.get("description") or f"Herramienta autónoma {tool_name}").strip()
    python_code = str(params.get("python_code") or "").strip()
    params_schema = params.get("parameters_schema") or {}
    test_params = params.get("test_parameters") or {}
    decl = params.get("declaration") or {}

    state = _load_state()

    if action in ("status", "list"):
        tools = state.get("tools", {})
        if not tools:
            return ("self_extend: sin tools auto-generadas registradas.\n"
                    "Acciones: implement, register, verify, extend, revert, status.")
        lines = [f"Tools auto-generadas ({len(tools)}):"]
        for name, info in tools.items():
            lines.append(f"  - {name}: {info.get('status', '?')} "
                         f"({info.get('updated_at', '')[:16]}) {info.get('description', '')[:50]}")
        return "\n".join(lines)

    if action == "implement":
        if not tool_name or not python_code:
            return "Error: se requiere 'tool_name' y 'python_code'."
        ok, msg = _implement(tool_name, python_code, description, params_schema, test_params)
        if ok:
            state.setdefault("tools", {})[tool_name] = {
                "status": "implementado", "description": description,
                "updated_at": datetime.now().isoformat(),
            }
            _save_state(state)
        return f"{'✓ Implementada' if ok else '✗ Fallo en implementacion'}:\n{msg}"

    if action == "register":
        if not tool_name:
            return "Error: se requiere 'tool_name'."
        if not decl:
            decl = {
                "name": tool_name,
                "description": description,
                "parameters": {
                    "type": "OBJECT",
                    "properties": params_schema,
                    "required": list(params_schema.keys()),
                },
            }
        backups = _backup({"registry": _REGISTRY, "imports": _IMPORTS, "declarations": _DECLARATIONS})
        ok, msg = _register(tool_name, module, func, decl)
        if not ok:
            _restore(backups)
            return f"✗ Fallo en registro (revertido):\n{msg}"
        state.setdefault("tools", {}).setdefault(tool_name, {})
        state["tools"][tool_name]["status"] = "registrado"
        state["tools"][tool_name]["updated_at"] = datetime.now().isoformat()
        state["tools"][tool_name]["backups"] = backups
        _save_state(state)
        return f"✓ {msg}"

    if action == "verify":
        ok, info = _verify()
        return f"{'✓ REGRESIÓN OK' if ok else '✗ REGRESIÓN CON FALLOS'}:\n{info['output']}"

    if action == "revert":
        if not tool_name:
            return "Error: se requiere 'tool_name'."
        info = state.get("tools", {}).get(tool_name)
        if not info or not info.get("backups"):
            return f"Sin backups de registro para '{tool_name}'."
        _restore(info["backups"])
        state["tools"][tool_name]["status"] = "revertido"
        _save_state(state)
        return f"Revertido: '{tool_name}' desregistrada (backups restaurados)."

    if action == "extend":
        # Ciclo completo seguro
        if not tool_name or not python_code:
            return "Error: se requiere 'tool_name' y 'python_code' para el ciclo completo."
        if player:
            try:
                player.write_log(f"[self_extend] Ciclo completo para '{tool_name}'...")
            except Exception:
                pass

        # 1) implementar
        ok, msg = _implement(tool_name, python_code, description, params_schema, test_params)
        if not ok:
            return f"✗ [1/4] Implementación falló:\n{msg}"
        # 2) registrar
        backups = _backup({"registry": _REGISTRY, "imports": _IMPORTS, "declarations": _DECLARATIONS})
        decl = decl or {
            "name": tool_name,
            "description": description,
            "parameters": {
                "type": "OBJECT",
                "properties": params_schema,
                "required": list(params_schema.keys()),
            },
        }
        ok, msg = _register(tool_name, module, func, decl)
        if not ok:
            _restore(backups)
            return f"✗ [2/4] Registro falló (revertido):\n{msg}"
        # 3) verificar
        ok, info = _verify()
        if not ok:
            _restore(backups)
            state.setdefault("tools", {})[tool_name] = {
                "status": "fallo_verificacion", "updated_at": datetime.now().isoformat(),
            }
            _save_state(state)
            return (f"✗ [3/4] Verificación falló — tool revertida:\n"
                    f"{info['output']}")
        # 4) confirmar
        state.setdefault("tools", {})[tool_name] = {
            "status": "activa", "description": description,
            "updated_at": datetime.now().isoformat(), "backups": backups,
        }
        _save_state(state)
        return (f"✓ [4/4] Ciclo self_extend completo.\n"
                f"  Implementación: OK | Registro: OK | "
                f"Verificación (compile+pytest+auditoría): OK\n"
                f"  La tool '{tool_name}' está ACTIVA y validada.")

    return ("Acciones: status, implement, register, verify, revert, extend. "
            "Params: tool_name, python_code, description, parameters_schema, test_parameters, declaration.")
