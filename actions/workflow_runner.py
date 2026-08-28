"""
workflow_runner.py — Automatizacion de flujos de trabajo complejos.

Define workflows reutilizables (JSON en data/workflows/) con pasos encadenados.
Cada paso llama a una tool existente via core.agent_architecture._run_tool.
Soporta: variables {{var}}, salidas de pasos previos {{step.N.salida}},
retry, on_error (stop/continue/skip), y pasos paralelos (parallel: true).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_WF_DIR = _BASE / "data" / "workflows"


def _load_workflows() -> dict:
    if not _WF_DIR.exists():
        return {}
    out = {}
    for f in sorted(_WF_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            out[data.get("name") or f.stem] = {"file": f, "data": data}
        except Exception:
            continue
    return out


def _save_workflow(data: dict) -> Path:
    _WF_DIR.mkdir(parents=True, exist_ok=True)
    name = data.get("name", "workflow").strip().lower().replace(" ", "_")
    safe = re.sub(r"[^a-z0-9_\-]", "", name)
    path = _WF_DIR / f"{safe}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _resolve(value, ctx):
    """Resuelve {{var}} y {{step.N}} en strings/listas/dicts."""
    if isinstance(value, str):
        def repl(m):
            key = m.group(1).strip()
            parts = key.split(".")
            if parts and parts[0] in ctx.get("vars", {}):
                return str(ctx["vars"].get(parts[0], ""))
            if parts and parts[0] == "step" and len(parts) >= 3 and parts[1].isdigit():
                step = ctx.get("steps", {}).get(int(parts[1]) - 1, {})
                return str(step.get(parts[2], ""))
            if parts and parts[0] == "env":
                return os.environ.get(parts[1], "")
            return m.group(0)
        return re.sub(r"\{\{\s*([^}]+)\s*\}\}", repl, value)
    if isinstance(value, list):
        return [_resolve(v, ctx) for v in value]
    if isinstance(value, dict):
        return {k: _resolve(v, ctx) for k, v in value.items()}
    return value


def _run_step(step, ctx) -> dict:
    tool = str(step.get("tool") or step.get("name") or "").strip()
    params = dict(step.get("params") or {})
    params = _resolve(params, ctx)
    retries = int(step.get("retries") or 0)
    label = step.get("label") or tool

    from core.agent_architecture import _run_tool

    last_error = ""
    for attempt in range(retries + 1):
        try:
            result = _run_tool(tool, params)
        except Exception as e:
            last_error = str(e)
            result = None
        if result is not None and not (isinstance(result, str) and result.strip().lower().startswith(("error", "[error", "no disponible"))):
            return {"tool": tool, "label": label, "ok": True, "salida": str(result)[:4000], "error": ""}
        last_error = str(result) if result else last_error
        if attempt < retries:
            continue
        break
    return {"tool": tool, "label": label, "ok": False, "salida": "", "error": last_error}


def _execute(data: dict, inputs: dict, player=None) -> str:
    name = data.get("name", "workflow")
    steps = data.get("steps") or []
    if not steps:
        return f"Workflow '{name}': sin pasos definidos."

    vars_map = dict(data.get("vars") or {})
    vars_map.update({k: v for k, v in (inputs or {}).items()})
    ctx = {"vars": vars_map, "steps": []}
    on_error = data.get("on_error", "stop")
    global_retries = int(data.get("retries") or 0)

    lines = [f"WORKFLOW: {name}", f"  {data.get('description', '')}", f"  Pasos: {len(steps)}"]
    if player:
        try:
            player.write_log(f"[workflow_runner] {name}: {len(steps)} pasos")
        except Exception:
            pass

    for i, step in enumerate(steps, 1):
        if step.get("if"):
            cond = _resolve(step["if"], ctx)
            truthy = str(cond).strip().lower() in ("1", "true", "yes", "si", "sí")
            if not truthy:
                lines.append(f"  [{i}] {step.get('label') or step.get('tool')}: saltado (if=False)")
                ctx["steps"].append({"ok": True, "salida": "(saltado)"})
                continue

        # Pasos paralelos: una lista de subpasos con su propio tool
        if step.get("parallel") and isinstance(step.get("tasks"), list):
            from concurrent.futures import ThreadPoolExecutor, as_completed
            tasks = step["tasks"]
            sub_steps = []
            for t in tasks:
                t2 = dict(t)
                t2.setdefault("retries", global_retries)
                sub_steps.append(t2)
            results = {}
            with ThreadPoolExecutor(max_workers=min(len(tasks), 4)) as pool:
                futures = {pool.submit(_run_step, t, ctx): idx for idx, t in enumerate(sub_steps)}
                for fut in as_completed(futures):
                    idx = futures[fut]
                    try:
                        results[idx] = fut.result(timeout=180)
                    except Exception as e:
                        results[idx] = {"ok": False, "salida": "", "error": str(e)}
            for idx, t in enumerate(tasks):
                r = results.get(idx, {"ok": False, "salida": "", "error": "sin resultado"})
                ctx["steps"].append(r)
                lines.append(f"  [{i}.{idx+1}] {r['label']}: {'OK' if r['ok'] else 'FALLO'}")
                if not r["ok"]:
                    lines.append(f"       error: {r['error']}")
            continue

        step = dict(step)
        step.setdefault("retries", global_retries)
        result = _run_step(step, ctx)
        ctx["steps"].append(result)
        status = "OK" if result["ok"] else "FALLO"
        lines.append(f"  [{i}] {result['label']}: {status}")
        if result["ok"]:
            lines.append(f"       -> {result['salida'][:400]}")
        else:
            lines.append(f"       error: {result['error'][:400]}")
            if on_error == "stop":
                lines.append("  (workflow detenido por error)")
                break
            if on_error == "skip":
                continue
            if on_error == "continue":
                continue

    ok_count = sum(1 for s in ctx["steps"] if s.get("ok"))
    total = len(ctx["steps"])
    lines.append(f"\n  Resultado: {ok_count}/{total} pasos OK")
    return "\n".join(lines)


# ── Workflows de ejemplo ────────────────────────────────────────────────
def _builtin_examples() -> dict:
    return {
        "briefing_matutino": {
            "name": "briefing_matutino",
            "description": "Resumen del dia: clima + noticias + recordatorios.",
            "on_error": "continue",
            "vars": {"ciudad": "Buenos Aires"},
            "steps": [
                {"label": "Clima", "tool": "weather", "params": {"city": "{{ciudad}}"}, "retries": 1},
                {"label": "Noticias", "tool": "web_search", "params": {"query": "ultimas noticias Argentina", "count": 5}},
            ],
        },
        "estado_sistema": {
            "name": "estado_sistema",
            "description": "Diagnostico rapido del sistema.",
            "on_error": "continue",
            "steps": [
                {"label": "Sistema", "tool": "system_reader", "params": {"action": "status"}},
                {"label": "Salud", "tool": "system_reader", "params": {"action": "advisory"}},
                {"label": "Procesos", "tool": "system_reader", "params": {"action": "top_processes"}},
            ],
        },
        "mantenimiento": {
            "name": "mantenimiento",
            "description": "Limpieza de temporales + backup de configuracion.",
            "on_error": "continue",
            "steps": [
                {"label": "Config", "tool": "config_export", "params": {"action": "backup"}, "retries": 1},
                {"label": "Temporales", "tool": "system_cleaner", "params": {"action": "clean_temps", "confirm": True}},
            ],
        },
    }


def workflow_runner(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action") or "run").lower().strip()
    name = str(params.get("name") or "").strip()
    inputs = params.get("inputs") or params.get("vars") or {}

    if action in ("status", "list"):
        wfs = _load_workflows()
        if not wfs:
            return "No hay workflows guardados. Usa action=example para crear los de ejemplo."
        lines = [f"Workflows disponibles ({len(wfs)}):"]
        for n, w in wfs.items():
            desc = w["data"].get("description", "")
            nsteps = len(w["data"].get("steps") or [])
            lines.append(f"  - {n} ({nsteps} pasos): {desc}")
        return "\n".join(lines)

    if action == "example":
        created = []
        for n, data in _builtin_examples().items():
            path = _save_workflow(data)
            created.append(str(path))
        return "Workflows de ejemplo creados:\n  " + "\n  ".join(created)

    if action in ("save", "add"):
        data = params.get("data") or params.get("workflow")
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception as e:
                return f"Error: 'data' JSON invalido: {e}"
        if not isinstance(data, dict) or "steps" not in data:
            return "Error: se requiere 'data' con {name, description, steps:[{tool, params}]}"
        if not data.get("name"):
            data["name"] = name or "workflow"
        path = _save_workflow(data)
        return f"Workflow guardado: {path}"

    if action == "delete":
        if not name:
            return "Error: se requiere 'name' del workflow."
        path = _WF_DIR / f"{name}.json"
        if not path.exists():
            return f"Workflow no encontrado: {name}"
        path.unlink()
        return f"Workflow eliminado: {name}"

    if action == "show":
        if not name:
            return "Error: se requiere 'name'."
        wfs = _load_workflows()
        if name not in wfs:
            return f"Workflow no encontrado: {name}"
        return json.dumps(wfs[name]["data"], ensure_ascii=False, indent=2)

    # default: run
    if not name:
        wfs = _load_workflows()
        if len(wfs) == 1:
            name = list(wfs.keys())[0]
        else:
            return ("Error: se requiere 'name' del workflow a ejecutar.\nDisponibles: "
                    + ", ".join(sorted(wfs.keys()) or ["(ninguno; usa action=example)"]))
    wfs = _load_workflows()
    if name not in wfs:
        # permitir ejecutar un workflow pasado como data inline
        data = params.get("data")
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = None
        if isinstance(data, dict) and "steps" in data:
            return _execute(data, inputs, player)
        return f"Workflow no encontrado: {name}"
    return _execute(wfs[name]["data"], inputs, player)
