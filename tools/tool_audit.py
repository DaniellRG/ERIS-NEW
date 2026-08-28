# -*- coding: utf-8 -*-
"""tool_audit.py — Auditoría profunda de alineación TOOL_DECLARATIONS <-> funciones reales.

El dispatcher llama a TODA herramienta como func(parameters=args, player=...).
Por eso la comparación por firma no alcanza: los bugs reales están en las CLAVES que
la función lee del dict (params.get("name")) vs las que la declaración envía (property "skill").

Detección por clases:
  A) Claves declaradas que la función NUNCA lee  → la llamada "funciona" pero el parámetro
     se ignora en silencio (caso skill_manage: declarado 'skill', leído 'name').
  B) Claves que la función LEE pero no están declaradas → el modelo nunca las manda → None.
  C) Funciones no-dict (firma con kwargs reales) → se invocan mal por el dispatcher.

Uso: python tools/tool_audit.py
"""
import sys
import inspect
import os
import re
import json
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_declarations import TOOL_DECLARATIONS
from core.tool_registry import get_tool

RESERVED = {"parameters", "player", "self", "args", "kwargs"}
PARAM_WORD_RE = re.compile(r"\b(parameters|params|args|payload)\b")
GET_RECV_RE = re.compile(r"(?<![.\w])([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*get\(\s*[\"']([a-zA-Z0-9_]+)[\"']")
BRACKET_RECV_RE = re.compile(r"(?<![.\w])([a-zA-Z_][a-zA-Z0-9_]*)\s*\[\s*[\"']([a-zA-Z0-9_]+)[\"']\s*\]")


def _body_of(module_src: str, start: int) -> str:
    """Cuerpo de una función del módulo: desde el offset (en caracteres) de su 'def'
    hasta la siguiente def/class a nivel 0."""
    lines = module_src.splitlines()
    line_no = module_src.count("\n", 0, start)
    end = len(lines)
    for i in range(line_no + 1, len(lines)):
        if re.match(r"^(def|class)\s+", lines[i]):
            end = i
            break
    return "\n".join(lines[line_no:end])


def _param_vars(text: str) -> set:
    """Variables que representan el dict de parámetros en un cuerpo de código:
    los nombres de la firma (PRIMERA línea del cuerpo, que es la def real) + alias
    asignados desde ellos (ej. params = parameters or {}).

    NOTA: 'data' NO cuenta como dict de parámetros — es el dict interno de datos
    (respuestas del LLM, historial, etc.) y leerlo no significa que el modelo deba
    mandar esas claves."""
    vars_ = set()
    lines = text.splitlines()
    if lines:
        # La firma puede estar en varias líneas: juntar desde 'def' hasta el cierre ')'.
        header = lines[0]
        if "(" in header and ")" not in header:
            for line in lines[1:]:
                header += " " + line.strip()
                if ")" in line:
                    break
        m = re.search(r"def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(([^)]*)\)", header)
        if m:
            for p in m.group(1).split(","):
                name = re.split(r"[:=]", p.strip())[0].strip()
                if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", name):
                    vars_.add(name)
    for line in lines:
        am = re.match(r"\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(parameters|params|args|payload)(?!\s*[.\[])\b(?:\s+or\b)?", line)
        if am:
            vars_.add(am.group(1))
        # Alias derivado: X = dict(parameters ...) o X = funcion(parameters ...)
        am2 = re.match(r"\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:dict\s*\(|[a-zA-Z_][a-zA-Z0-9_.]*\s*\()([^)]*\b(parameters|params|args|payload)\b)", line)
        if am2:
            vars_.add(am2.group(1))
    return vars_


def _keys_from_text(text: str, param_vars: set) -> set:
    """Claves leídas vía .get() o [] SOLO sobre variables que son el dict de parámetros."""
    keys = set()
    for line in text.splitlines():
        if not PARAM_WORD_RE.search(line):
            continue
        for recv, key in GET_RECV_RE.findall(line):
            if recv in param_vars:
                keys.add(key)
        for recv, key in BRACKET_RECV_RE.findall(line):
            if recv in param_vars:
                keys.add(key)
    return keys


def _read_keys(func):
    """Claves que la función lee del dict de parámetros.

    Sigue handlers: si la función pasa el dict completo a otras funciones del módulo
    (patrón dispatcher, ej. _merge_pdf(params)), también cuenta las claves que esas
    funciones leen. Sin esto, todo dispatcher genera falsos positivos.
    """
    module = sys.modules.get(func.__module__)
    try:
        src = inspect.getsource(func)
    except (TypeError, OSError):
        try:
            src = inspect.getsource(module)
        except (TypeError, OSError):
            return set()
    param_vars = _param_vars(src)
    keys = _keys_from_text(src, param_vars)
    if module:
        try:
            module_src = inspect.getsource(module)
        except (TypeError, OSError):
            module_src = ""
        defs = {m.group(1): m.start() for m in re.finditer(r"^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", module_src, re.M)}

        def _called_in(text: str, extra_handlers=None) -> set:
            found = set()
            for line in text.splitlines():
                for fn in defs:
                    if re.search(rf"\b{re.escape(fn)}\s*\([^)]*\b(parameters|params|args|payload)\b(?!\s*[.\[])",
                                 line):
                        found.add(fn)
                # Patrón dict-de-handlers: X = { "accion": fn1, ... }; h = X.get(...); h(parameters)
                for vm in re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*(parameters|params|args|payload)\s*\)", line):
                    if extra_handlers and vm.group(1) in extra_handlers:
                        dict_name = extra_handlers[vm.group(1)]
                        found.update(dict_vals.get(dict_name, []))
            return found

        # Patrón dict-de-handlers: X = { "accion": fn1, ... }; h = X.get(...); h(parameters)
        dict_vals = {}
        for dm in re.finditer(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\{([^}]*)\}", module_src, re.M):
            values = re.findall(r":\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:,|\})", dm.group(2))
            if values:
                dict_vals[dm.group(1)] = values
        handler_aliases = {}
        for am in re.finditer(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*(?:get|pop)\(",
                              module_src, re.M):
            if am.group(2) in dict_vals:
                handler_aliases[am.group(1)] = am.group(2)

        # Seguimiento transitivo: dispatcher -> handler -> sub-handler, etc.
        seen, queue = set(), [src]
        while queue:
            text = queue.pop()
            called = _called_in(text, handler_aliases)
            for fn in called:
                if fn in defs and fn not in seen:
                    seen.add(fn)
                    body = _body_of(module_src, defs[fn])
                    keys.update(_keys_from_text(body, _param_vars(body)))
                    queue.append(body)
    return keys - {"unknown"}


def main():
    class_a, class_b, class_c, dict_style = [], [], [], 0
    for decl in TOOL_DECLARATIONS:
        name = decl.get("name", "")
        declared = set((decl.get("parameters") or {}).get("properties", {}).keys())
        func = get_tool(name)
        if func is None:
            continue
        try:
            sig = inspect.signature(func)
        except (TypeError, ValueError):
            continue
        named = [p for p in sig.parameters if p not in RESERVED and not p.startswith("*")]
        is_dict_style = set(named) <= {"parameters", "player"}
        has_var_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        accepts_parameters_kw = "parameters" in sig.parameters
        accepts_player_kw = "player" in sig.parameters
        # El dispatcher llama func(parameters=args, player=...): solo es segura si
        # absorbe ambos (por kwargs) o acepta los dos kwargs explícitos.
        callable_safe = has_var_kwargs or (accepts_parameters_kw and accepts_player_kw)
        if not callable_safe:
            class_c.append((name, ", ".join(sig.parameters)))
            continue
        if not is_dict_style:
            continue
        dict_style += 1
        read_keys = _read_keys(func)
        if declared and not read_keys:
            # Declara keys pero la función no lee NADA del dict → todas las keys
            # declaradas se ignoran en silencio (clase A). Ya no se esconden.
            for key in declared:
                class_a.append((name, key, "no leída (la función no lee parámetros)"))
            continue
        for key in declared:
            if key not in read_keys:
                class_a.append((name, key, "no leída (lee: " + ", ".join(sorted(read_keys)[:10]) + ")"))
        for key in sorted(read_keys):
            if key not in declared:
                class_b.append((name, key, "no declarada"))

    print("=" * 70)
    print(f"Dict-style auditadas: {dict_style}")
    print("=" * 70)
    print("\n[CLASE A] Declaradas pero NUNCA leídas por la función (se ignoran en silencio):")
    if class_a:
        for name, key, det in sorted(class_a):
            print(f"  {name}: '{key}' {det}")
    else:
        print("  (ninguna)")
    print("\n[CLASE B] Leídas por la función pero NO declaradas (el modelo nunca las manda):")
    if class_b:
        for name, key, det in sorted(class_b):
            print(f"  {name}: '{key}' {det}")
    else:
        print("  (ninguna)")
    print("\n[CLASE C] Funciones no-dict (firma con kwargs reales; el dispatcher las invoca mal):")
    if class_c:
        for name, sigs in sorted(class_c):
            print(f"  {name}: firma ({sigs})")
    else:
        print("  (ninguna)")

    # ── BITÁCORA: ediciones recientes + .py modificados sin registro ──
    try:
        journal = Path(__file__).resolve().parent.parent / "data" / "edit_journal.jsonl"
        logged = set()
        if journal.exists():
            for ln in journal.read_text(encoding="utf-8").splitlines()[-200:]:
                try:
                    r = json.loads(ln)
                    logged.add(str(r.get("path", "")).lower())
                except Exception:
                    continue
        root = Path(__file__).resolve().parent.parent
        now = time.time()
        unlogged = []
        for p in root.rglob("*.py"):
            if ".git" in p.parts or "backups" in p.parts:
                continue
            try:
                if now - p.stat().st_mtime < 86400 and str(p).lower() not in logged:
                    unlogged.append(p)
            except Exception:
                continue
        print("\n[BITÁCORA] .py modificados en las últimas 24h SIN entrada en edit_journal.jsonl"
              " (ediciones hechas fuera de self_edit/file_controller):")
        if unlogged:
            for p in sorted(unlogged)[:10]:
                print(f"  {p}")
        else:
            print("  (ninguno — todas las ediciones recientes quedaron registradas)")
    except Exception as e:
        print(f"\n[BITÁCORA] Error: {e}")
    print("=" * 70)


if __name__ == "__main__":
    main()
