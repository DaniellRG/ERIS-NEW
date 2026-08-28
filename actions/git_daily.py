# -*- coding: utf-8 -*-
"""
git_daily.py — Flujo git diario con convención de commits y verificación.

Complementa git_control con el flujo que ERIS usa en su propio desarrollo:
  * commit CONVENCIONAL (feat:/fix:/refactor:/docs:/chore:/style:/test:)
    inferido automáticamente del diff si no se da 'message'.
  * pre-check opcional (py_compile de los .py modificados) antes de commitear.
  * sync: commit + pull --rebase + push en un solo paso.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def _git(repo: str, *args: str, timeout: int = 60) -> tuple[bool, str]:
    try:
        r = subprocess.run(["git", *args], cwd=repo, capture_output=True,
                           text=True, timeout=timeout)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        return r.returncode == 0, (out or err)[:3000]
    except Exception as e:
        return False, f"[git error] {e}"


def _changed_py(repo: str) -> list[str]:
    ok, out = _git(repo, "diff", "--name-only", "--cached")
    if not ok:
        return []
    return [l.strip() for l in out.splitlines() if l.strip().endswith(".py")]


def _infer_type(diff_text: str) -> str:
    low = diff_text.lower()
    if any(w in low for w in ("def ", "class ", "import ", "new file")):
        return "feat"
    if any(w in low for w in ("fix", "bug", "error", "crash", "correg", "arregl")):
        return "fix"
    if any(w in low for w in ("refactor", "rename", "move", "clean")):
        return "refactor"
    if any(w in low for w in ("readme", "docstring", "doc", "coment")):
        return "docs"
    if any(w in low for w in ("test", "assert", "pytest")):
        return "test"
    if any(w in low for w in ("style", "format", "whitespace")):
        return "style"
    return "chore"


def _short_summary(diff_text: str) -> str:
    names = []
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            names.append(line[6:].split("/")[-1])
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return ", ".join(out[:4]) or "cambios"


def _py_compile(path: Path) -> tuple[bool, str]:
    try:
        import py_compile
        py_compile.compile(str(path), doraise=True)
        return True, "OK"
    except py_compile.PyCompileError as e:
        return False, str(e)[:300]


def git_daily(parameters: dict = None, player=None) -> str:
    """Flujo git diario con convención de commits. Acciones: status (corto), diff (--stat o 'full'=true),
    commit (stage todo + mensaje 'message' o convencional auto; 'verify'=true hace py_compile previo),
    sync (commit + pull --rebase + push), log (últimos 15), branch (ramas). 'path' es el repo (default: ERIS)."""
    action = str(parameters.get("action") or "status").lower()
    repo = parameters.get("path") or str(PROJECT_DIR)
    msg = parameters.get("message") or ""
    verify = bool(parameters.get("verify", True))
    full = bool(parameters.get("full", False))

    if player:
        try:
            player.write_log(f"[git_daily] {action}")
        except Exception:
            pass

    if action == "status":
        ok, out = _git(repo, "status", "--short")
        return out if ok else f"Error: {out}"

    if action == "diff":
        args = ["diff"] if full else ["diff", "--stat"]
        ok, out = _git(repo, *args)
        return out if ok else f"Error: {out}"

    if action == "log":
        ok, out = _git(repo, "log", "--oneline", "-15")
        return out if ok else f"Error: {out}"

    if action == "branch":
        ok, out = _git(repo, "branch", "-a")
        return out if ok else f"Error: {out}"

    if action == "commit":
        _git(repo, "add", "-A")
        ok, diff = _git(repo, "diff", "--cached")
        if not ok or not diff.strip():
            return "Nada para commitear (working tree limpio)."
        if verify:
            broken = []
            for py in _changed_py(repo):
                okp, outp = _py_compile(Path(repo) / py)
                if not okp:
                    broken.append(f"{py}: {outp[:200]}")
            if broken:
                return ("PRE-CHECK FALLÓ (py_compile): no se commiteará.\n"
                        + "\n".join(broken)
                        + "\nCorregí los errores o usá verify=false.")
        if not msg:
            msg = f"{_infer_type(diff)}: {_short_summary(diff)}"
        ok2, out2 = _git(repo, "commit", "-m", msg)
        if not ok2:
            return f"Error commit: {out2}"
        result = f"COMMIT OK: '{msg}'\n{out2}"
        if verify:
            for py in _changed_py(repo):
                _, outp = _py_compile(Path(repo) / py)
                if "ERROR" in outp:
                    result += f"\n⚠️ {py}: {outp[:200]}"
        return result

    if action == "sync":
        _git(repo, "add", "-A")
        ok, diff = _git(repo, "diff", "--cached")
        if not ok or not diff.strip():
            return "Nada para commitear."
        if not msg:
            msg = f"{_infer_type(diff)}: {_short_summary(diff)}"
        okc, outc = _git(repo, "commit", "-m", msg)
        okp, outp = _git(repo, "pull", "--rebase")
        okph, outph = _git(repo, "push")
        return f"COMMIT: {outc}\nPULL: {outp}\nPUSH: {outph}"

    return (f"Accion no valida: {action}. Disponibles: status, diff, commit, sync, log, branch.")
