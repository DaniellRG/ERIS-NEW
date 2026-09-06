"""
actions/git_autonomo.py — Git autónomo para ERIS.

Eris versiona su propio código y tus proyectos: status, commit con mensaje
generado por ella (según qué archivos cambió), log, y un diario de cambios
persistente en memory/git_diario.md.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DIARIO = BASE / "memory" / "git_diario.md"


def _find_repo(start=None) -> Path | None:
    p = Path(start or BASE).resolve()
    for cand in [p, *p.parents]:
        if (cand / ".git").exists():
            return cand
    return None


def _git(repo: Path, args, timeout=60):
    bin_ = shutil.which("git")
    if not bin_:
        return "Error: git no está instalado."
    try:
        r = subprocess.run([bin_, "-C", str(repo), *args],
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return f"Error git ({r.returncode}): {(r.stderr or r.stdout).strip()[:300]}"
        return (r.stdout or "(ok)").strip()
    except subprocess.TimeoutExpired:
        return "Error: git tardó demasiado."
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def _auto_message(repo: Path) -> str:
    files = [l for l in _git(repo, ["diff", "--cached", "--name-only"]).splitlines()
             if l and not l.startswith("Error")]
    if not files:
        return "chore: snapshot de trabajo"
    sco = "eris"
    for f in files:
        for prefix, scope in (("core/", "core"), ("actions/", "actions"),
                              ("config/", "config"), ("tests/", "tests"),
                              ("memory/", "mem"), ("data/", "data"),
                              ("tools/", "tools")):
            if f.startswith(prefix):
                sco = scope
                break
        if sco != "eris":
            break
    txt = " ".join(files[:8])
    kinds = {"fix": r"\bfix|fix \[|correg|bug|error", "feat": r"\bfeat|add |nuev|creat|new ",
             "docs": r"\.md\b|docs|readme|doc", "refactor": r"\brefactor|refac|reorgan", "test": r"test"}
    t = "chore"
    for kind, pat in (("fix", kinds["fix"]), ("feat", kinds["feat"]),
                      ("refactor", kinds["refactor"]), ("test", kinds["test"]),
                      ("docs", kinds["docs"])):
        if re.search(pat, txt, re.I):
            t = kind
            break
    base = Path(repo).name
    short = (files[0].replace("\\", "/").split("/")[-2] if "/" in files[0] else files[0])
    return f"{t}({sco}): {short} (+{len(files)-1})"


def _diary(repo: Path, texto: str):
    DIARIO.parent.mkdir(parents=True, exist_ok=True)
    fecha = time.strftime("%Y-%m-%d %H:%M")
    with open(DIARIO, "a", encoding="utf-8") as f:
        f.write(f"\n## {fecha} — {Path(repo).name}\n{texto}\n")


def git_autonomo(parameters: dict | None = None, player=None) -> str:
    """Git autónomo. Acciones: status, commit (message?), auto (message
    autogenerada + diario), log (n, since), diary, init (repo?)."""
    parameters = parameters or {}
    action = (parameters.get("action") or "status").lower()
    repo = parameters.get("repo") or parameters.get("path") or ""
    rp = Path(repo).resolve() if repo and os.path.isdir(repo) else _find_repo()
    if not rp:
        return "No hay repo git. Usá action=init (o pass repo=<ruta del proyecto>)."

    if action in ("status", "estado"):
        return _git(rp, ["status", "--short", "--branch"]) or f"[{rp.name}] limpio"

    if action in ("init", "inicializar"):
        if (rp / ".git").exists():
            return f"Ya es repo: {rp}"
        r = _git(rp, ["init", "-b", "main"]) or "(inicializado)"
        _git(rp, ["config", "user.email", "eris@localhost"])
        _git(rp, ["config", "user.name", "Eris"])
        return f"{r}\nRepo listo: {rp} (git config local: Eris <eris@localhost>)"

    if action in ("add", "stage"):
        paths = parameters.get("paths") or "."
        return _git(rp, ["add", str(paths)]) or "(staged)"

    if action in ("commit", "confirmar"):
        msg = (parameters.get("message") or "").strip()
        staged = _git(rp, ["diff", "--cached", "--name-only"])
        if not msg and (not staged or staged.startswith("Error")):
            _git(rp, ["add", "-A"])
        if not msg:
            msg = _auto_message(rp)
        r = _git(rp, ["commit", "-m", msg])
        if "Error" not in r and "nothing to commit" not in r:
            _diary(rp, f"- `{r}`")
        return (r or "(sin cambios)") + f"\n→ {msg}"

    if action in ("auto",):
        _git(rp, ["add", "-A"])
        msg = _auto_message(rp)
        r = _git(rp, ["commit", "-m", msg])
        if "Error" not in r and "nothing to commit" not in r:
            r += f"\n→ {msg}"
            _diary(rp, f"- `{r}`")
        return r or f"Sin cambios para commitear en {rp.name}."

    if action in ("log", "historial"):
        n = int(parameters.get("n", 15) or 15)
        since = parameters.get("since")
        args = ["log", "--oneline", f"-{n}"]
        if since:
            args = ["log", "--oneline", "--since", since]
        return _git(rp, args) or "(sin commits)"

    if action in ("diary", "diario"):
        repo_ = rp
        r = _git(repo_, ["log", "--oneline", "--since=1 day ago"])
        if not r or "Error" in r or "does not have" in r:
            return "(sin commits hoy)"
        _diary(repo_, "\n".join("- " + l for l in r.splitlines()))
        if DIARIO.exists():
            return f"Diario actualizado → memory/git_diario.md:\n{r[:400]}"
        return r or "(diario vacío)"

    if action in ("commit_diario",):
        if DIARIO.exists():
            return DIARIO.read_text(encoding="utf-8")[-1500:]
        return "(aún no hay diario)"

    return ("Acciones: status, init, add (paths), commit (message), "
            "auto (mensaje autogenerado + diario), log (n|since), "
            "diary (loguea commits de hoy), commit_diario (ver diario). "
            "Repo por defecto: el de ERIS o 'repo'.")