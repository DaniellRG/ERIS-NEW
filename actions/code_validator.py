# -*- coding: utf-8 -*-
"""
code_validator.py — Auto-validación post-cambio con corrección iterativa.

Tras una edición, ERIS compila, corre los tests/lint y, si algo falla, usa el
LLM para proponer una corrección y la aplica con file_editor, repitiendo hasta
que pase o se agoten los intentos. Es el equivalente al ciclo
py_compile/pytest/lint → fix que hace opencode.
"""
from __future__ import annotations

import subprocess
import sys

BASE_DIR = sys.path and None


def _run(cmd: list, cwd: str, timeout: int = 120) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        text = f"{out}\n{err}".strip()
        return r.returncode == 0, text[-4000:]
    except Exception as e:
        return False, f"[ejecucion error] {e}"


def _py_compile(path: str) -> tuple[bool, str]:
    return _run([sys.executable, "-m", "py_compile", path], os_path(path))


def os_path(path: str) -> str:
    import os
    return os.path.dirname(os.path.abspath(path))


def _pytest(repo: str) -> tuple[bool, str]:
    return _run([sys.executable, "-m", "pytest", "-q", os.path.join(repo, "tests")], repo)


def _fix_with_llm(error_text: str, goal: str) -> str:
    """Pide al LLM una corrección concreta (acción file_editor) para el error."""
    try:
        from core.agent_architecture import _chat
    except Exception:
        return ""
    system = (
        "Eres el corrector de código de ERIS. Dado un error de compilación/test, "
        "propón una corrección. Responde SOLO con JSON: "
        '{"path": "...", "old_text": "...", "new_text": "..."} con el fragmento '
        "exacto a reemplazar (old_text debe ser único en el archivo). Si el error "
        "no es de código o no puedes corregirlo, responde {\"error\": \"motivo\"}."
    )
    user = f"Objetivo: {goal}\n\nError:\n{error_text[:4000]}"
    resp = _chat([{"role": "system", "content": system},
                  {"role": "user", "content": user}], max_tokens=800)
    if resp.get("error"):
        return ""
    text = resp.get("content") or ""
    import re as _re
    m = _re.search(r"\{[\s\S]*\}", text)
    if not m:
        return ""
    try:
        import json
        return json.loads(m.group(0))
    except Exception:
        return ""


def _apply_fix(fix: dict) -> str:
    if not isinstance(fix, dict) or "error" in fix:
        return f"[skip] {fix.get('error', 'sin corrección')}"
    path = fix.get("path") or ""
    old_text = fix.get("old_text") or ""
    new_text = fix.get("new_text") or ""
    if not path or not old_text:
        return "[skip] corrección incompleta"
    try:
        from core.tool_registry import get_tool
        fe = get_tool("file_editor")
        return str(fe({"action": "edit", "path": path,
                       "old_text": old_text, "new_text": new_text}))
    except Exception as e:
        return f"[aplicar error] {e}"


def code_validator(parameters: dict = None, player=None) -> str:
    """Auto-validación de código. Acciones: validate (py_compile de 'path' o pytest de 'repo'),
    fix (corrige en bucle el 'path' o 'repo' hasta que pase, 'max_fixes' intentos, default 3),
    status (ver estado). Devuelve OK o el error con las correcciones aplicadas."""
    action = str(parameters.get("action") or "validate").lower()
    path = str(parameters.get("path") or "").strip()
    repo = str(parameters.get("repo") or "").strip()
    max_fixes = int(parameters.get("max_fixes") or 3)
    goal = str(parameters.get("goal") or path or repo)

    if action == "status":
        return "code_validator: listo. validate -> compile/pytest; fix -> bucle de corrección con LLM."

    if not path and not repo:
        return "Error: se requiere 'path' (archivo) o 'repo' (directorio con tests/)."

    if action == "validate":
        if path:
            ok, out = _py_compile(path)
            return f"{'OK' if ok else 'FALLO'} (py_compile {path}):\n{out}"
        ok, out = _pytest(repo)
        return f"{'OK' if ok else 'FALLO'} (pytest {repo}):\n{out}"

    if action == "fix":
        if player:
            try:
                player.write_log(f"[code_validator] corrigiendo {path or repo}...")
            except Exception:
                pass
        applied = []
        for attempt in range(1, max_fixes + 1):
            if path:
                ok, out = _py_compile(path)
            else:
                ok, out = _pytest(repo)
            if ok:
                res = "OK" if path else "OK (tests pasan)"
                return (f"VALIDACION OK tras {len(applied)} correcciones ({attempt} intentos).\n"
                        + "\n".join(applied) + (f"\n{res}" if path else ""))
            if attempt < max_fixes:
                fix = _fix_with_llm(out, goal)
                if not fix:
                    return f"FALLO persistente ({attempt}/{max_fixes}):\n{out}"
                applied.append(f"  [{attempt}] {_apply_fix(fix)[:200]}")
            else:
                return f"FALLO persistente tras {max_fixes} intentos:\n{out}"
        return f"FALLO persistente:\n{out}"

    return f"Accion no valida: {action}. Disponibles: validate, fix, status."
