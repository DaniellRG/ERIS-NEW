"""
actions/git_control.py — Full Git operations for ERIS.
Allows ERIS to manage git repositories: status, add, commit, push, pull, branch, log, diff,
filter-branch, remote, init, tag, and GitHub API integration.
"""
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parent.parent
_GIT_DIR = _PROJECT_DIR / ".git"

def git_control(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "").lower()
    repo_path = parameters.get("path") or str(_PROJECT_DIR)
    msg = parameters.get("message") or ""
    branch = parameters.get("branch") or ""
    url = parameters.get("url") or ""
    file_path = parameters.get("file") or ""
    n = parameters.get("n") or 10
    token = parameters.get("token") or ""
    repo_name = parameters.get("repo_name") or ""

    if player:
        player.write_log(f"🔧 Git: {action}")

    if action in ("status", "estado"):
        return _git_cmd(repo_path, "status")

    elif action in ("log", "historial"):
        return _git_cmd(repo_path, "log", f"--oneline -{n}")

    elif action in ("diff"):
        return _git_cmd(repo_path, "diff", "--stat")

    elif action in ("add", "agregar"):
        return _git_cmd(repo_path, "add", file_path or "-A")

    elif action in ("commit", "confirmar"):
        if not msg:
            return "Necesito un mensaje para el commit"
        return _git_cmd(repo_path, "commit", f'-m "{msg}"')

    elif action in ("push", "subir"):
        if branch:
            return _git_cmd(repo_path, "push", "origin", branch)
        return _git_cmd(repo_path, "push")

    elif action in ("pull", "bajar"):
        return _git_cmd(repo_path, "pull")

    elif action in ("branch", "rama"):
        if branch:
            result = _git_cmd(repo_path, "branch", branch)
            return result
        return _git_cmd(repo_path, "branch", "-a")

    elif action in ("checkout", "cambiar"):
        if not branch:
            return "Especifico 'branch' para hacer checkout"
        return _git_cmd(repo_path, "checkout", branch)

    # ── Worktrees: experimentos en ramas aisladas sin tocar el working dir ──
    elif action == "worktree_add":
        wt_path = parameters.get("worktree_path") or ""
        if not wt_path:
            return "Especifico 'worktree_path' (carpeta destino del worktree)."
        if branch:
            return _git_cmd(repo_path, "worktree", "add", "-b", branch, wt_path)
        return _git_cmd(repo_path, "worktree", "add", wt_path)

    elif action == "worktree_list":
        return _git_cmd(repo_path, "worktree", "list")

    elif action == "worktree_remove":
        wt_path = parameters.get("worktree_path") or ""
        if not wt_path:
            return "Especifico 'worktree_path' (el worktree a remover)."
        return _git_cmd(repo_path, "worktree", "remove", wt_path)

    elif action in ("merge", "fusionar"):
        if not branch:
            return "Especifico 'branch' para mergear"
        return _git_cmd(repo_path, "merge", branch)

    elif action == "init":
        return _git_cmd(repo_path, "init")

    elif action == "remote":
        if url:
            existing = _git_cmd(repo_path, "remote", "get-url", "origin", check=False)
            if existing and "fatal" not in existing.lower():
                _git_cmd(repo_path, "remote", "set-url", "origin", url)
                return f"Remote URL actualizado a: {url}"
            return _git_cmd(repo_path, "remote", "add", "origin", url)
        return _git_cmd(repo_path, "remote", "-v")

    elif action in ("tag", "etiqueta"):
        if branch:
            return _git_cmd(repo_path, "tag", branch)
        return _git_cmd(repo_path, "tag")

    elif action == "force_push":
        if branch:
            return _git_cmd(repo_path, "push", "origin", branch, "--force")
        return _git_cmd(repo_path, "push", "--force")

    elif action == "push_tags":
        return _git_cmd(repo_path, "push", "--tags", "--force")

    elif action == "filter_branch":
        expr = parameters.get("expression") or ""
        if not expr:
            return "Necesito 'expression' para filter-branch (ej: cambiar autor)"
        return _git_cmd(repo_path, "filter-branch", "-f", "--env-filter", f'"{expr}"', "--", "--all", timeout=120)

    elif action == "gc":
        return _git_cmd(repo_path, "gc", "--aggressive", "--prune=now", timeout=60)

    elif action == "log_all":
        return _git_cmd(repo_path, "log", "--all", f"--oneline -{n}")

    elif action == "show":
        if not branch:
            return "Necesito un ref/commit hash para mostrar"
        return _git_cmd(repo_path, "show", f"--stat", branch)

    elif action in ("rm", "eliminar"):
        if not file_path:
            return "Especifico 'file' a eliminar del repo"
        return _git_cmd(repo_path, "rm", "-r", file_path)

    elif action == "stash":
        return _git_cmd(repo_path, "stash")

    elif action == "stash_pop":
        return _git_cmd(repo_path, "stash", "pop")

    elif action == "reset":
        if branch:
            return _git_cmd(repo_path, "reset", "--hard", branch)
        return "Especifico un ref para resetear"

    elif action == "reflog":
        return _git_cmd(repo_path, "reflog", f"--oneline -{n}")

    elif action == "clean":
        return _git_cmd(repo_path, "clean", "-fd")

    elif action == "credential":
        return _get_github_token(repo_path)

    elif action == "github_create_repo":
        if not repo_name:
            return "Necesito 'repo_name' para crear el repo"
        return _github_create_repo(repo_name, token or _get_github_token(repo_path))

    elif action == "github_set_remote":
        if not repo_name:
            return "Necesito 'repo_name'"
        remote_url = f"https://github.com/{_get_github_user(token or _get_github_token(repo_path))}/{repo_name}.git"
        _git_cmd(repo_path, "remote", "remove", "origin", check=False)
        return _git_cmd(repo_path, "remote", "add", "origin", remote_url)

    else:
        actions = [
            "status", "add", "commit (msg=)", "push", "pull", "branch (branch=)",
            "checkout (branch=)", "merge (branch=)", "log (n=)", "diff", "remote (url=)",
            "init", "tag (branch=)", "force_push (branch=)", "push_tags",
            "filter_branch (expression=)", "gc", "show (branch=)", "rm (file=)",
            "stash", "stash_pop", "reset (branch=)", "reflog (n=)", "clean",
            "credential", "github_create_repo (repo_name=, token=)", "github_set_remote (repo_name=)"
        ]
        return f"Acciones git: {', '.join(actions)}"


def _git_cmd(repo_path: str, *args: str, check: bool = True, timeout: int = 30) -> str:
    """Execute a git command and return the output."""
    try:
        cmd = ["git"]
        cmd.extend(args)
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0 and check:
            stderr = result.stderr.strip()
            if not stderr:
                stderr = result.stdout.strip()[:200]
            return f"Error git: {stderr[:500]}"
        output = result.stdout.strip() or result.stderr.strip()
        return output[:2000] if output else "OK (sin output)"
    except subprocess.TimeoutExpired:
        return f"Error: git command timed out after {timeout}s"
    except FileNotFoundError:
        return "Error: git no esta instalado o no en PATH"
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _get_github_token(repo_path: str = None) -> str:
    """Get GitHub token from git credential helper."""
    try:
        if repo_path is None:
            repo_path = str(_PROJECT_DIR)
        input_data = "protocol=https\nhost=github.com\n"
        proc = subprocess.run(
            ["git", "credential", "fill"],
            cwd=repo_path,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except Exception:
        pass
    return ""


def _get_github_user(token: str = "") -> str:
    """Get GitHub username from API."""
    try:
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ERIS",
        }
        req = urllib.request.Request("https://api.github.com/user", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("login", "DaniellRG")
    except Exception:
        return "DaniellRG"
    return ""


def _github_create_repo(repo_name: str, token: str) -> str:
    """Create a new repository on GitHub."""
    if not token:
        return "No GitHub token disponible. Usa 'credential' primero."
    try:
        body = json.dumps({
            "name": repo_name,
            "description": "ERIS AI - Desktop AI Agent",
            "private": False,
            "auto_init": False,
        }).encode()
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "ERIS",
        }
        req = urllib.request.Request(
            "https://api.github.com/user/repos",
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            url = data.get("html_url", "desconocido")
            return f"Repo creado: {url}"
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return f"Error GitHub API ({e.code}): {error_body[:300]}"
    except Exception as e:
        return f"Error creando repo: {str(e)[:200]}"
