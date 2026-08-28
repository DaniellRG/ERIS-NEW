# -*- coding: utf-8 -*-
"""github_pr.py — Pull Requests en GitHub vía API REST (patrón de git_control).

Acciones:
  pr_create  — crear PR (owner, repo, title, head, base, body)
  pr_list    — listar PRs (owner, repo, state=open, limit)
  pr_view    — ver estado de un PR (owner, repo, number)
  pr_checks  — ver checks/CI de un PR (owner, repo, number)
  pr_merge   — mergear un PR (owner, repo, number, method)

Usa el mismo token de git_control (git credential fill). Sin token devuelve
error claro en vez de crashear.
"""
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parent.parent
_API = "https://api.github.com"


def _get_github_token(repo_path: str = None) -> str:
    """Token de GitHub desde el credential helper de git."""
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


def _owner_repo(parameters: dict, repo_path: str = None) -> tuple:
    """(owner, repo) desde parámetros o desde el remote origin."""
    owner = parameters.get("owner", "")
    repo = parameters.get("repo", "")
    if owner and repo:
        return owner, repo
    try:
        if repo_path is None:
            repo_path = str(_PROJECT_DIR)
        url = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        url = url.replace(".git", "").rstrip("/")
        if url.endswith("/"):
            return "", ""
        if url.startswith("https://github.com/"):
            parts = url[len("https://github.com/"):].split("/")
            return parts[0], parts[1] if len(parts) > 1 else ""
        if ":" in url and "github.com" in url:
            parts = url.split("github.com:")[1].split("/")
            return parts[0], parts[1] if len(parts) > 1 else ""
    except Exception:
        pass
    return "", ""


def _api(path: str, method: str = "GET", body: dict = None) -> tuple:
    """Llama a la API. Devuelve (ok: bool, payload_dict_o_error_str)."""
    token = _get_github_token()
    if not token:
        return False, "No GitHub token disponible. Configuralo con 'credential' (git_control) o git credential fill."
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "ERIS",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{_API}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            return True, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return False, f"Error GitHub API ({e.code}): {error_body[:300]}"
    except Exception as e:
        return False, f"Error: {str(e)[:200]}"


def _pr_summary(pr: dict) -> str:
    return (
        f"#{pr.get('number')} [{pr.get('state')}] {pr.get('title')} "
        f"(user: {pr.get('user', {}).get('login')} | "
        f"{pr.get('head', {}).get('ref')} -> {pr.get('base', {}).get('ref')})"
    )


def github_pr(parameters: dict, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "pr_list").lower()
    owner, repo = _owner_repo(params)
    if not owner or not repo:
        return "Error: no se pudo determinar owner/repo. Pasá 'owner' y 'repo', o configurá remote.origin.url."

    if action == "pr_create":
        title = params.get("title", "").strip()
        head = params.get("head", "").strip()
        base = params.get("base", "main")
        if not title or not head:
            return "Error: se requieren 'title' y 'head' para crear un PR."
        body = {"title": title, "head": head, "base": base}
        if params.get("body"):
            body["body"] = params["body"]
        ok, res = _api(f"/repos/{owner}/{repo}/pulls", method="POST", body=body)
        if not ok:
            return res
        return f"PR creado: {res.get('html_url')} | {_pr_summary(res)}"

    elif action == "pr_list":
        state = params.get("state", "open")
        limit = int(params.get("limit", 10))
        ok, res = _api(f"/repos/{owner}/{repo}/pulls?state={state}&per_page={limit}")
        if not ok:
            return res
        if not res:
            return f"No hay PRs ({state}) en {owner}/{repo}."
        lines = [_pr_summary(pr) for pr in res[:limit]]
        return f"PRs ({state}) en {owner}/{repo} ({len(lines)}):\n" + "\n".join(lines)

    elif action == "pr_view":
        number = params.get("number", "")
        ok, res = _api(f"/repos/{owner}/{repo}/pulls/{number}")
        if not ok:
            return res
        return (
            f"#{res.get('number')} [{res.get('state')}] {res.get('title')}\n"
            f"Rama: {res.get('head', {}).get('ref')} -> {res.get('base', {}).get('ref')}\n"
            f"Mergeable: {res.get('mergeable')} | Estado: {res.get('mergeable_state')}\n"
            f"Creado por: {res.get('user', {}).get('login')}\n"
            f"URL: {res.get('html_url')}\n"
            f"Body: {(res.get('body') or '')[:200]}"
        )

    elif action == "pr_checks":
        number = params.get("number", "")
        ok, res = _api(f"/repos/{owner}/{repo}/pulls/{number}/checks")
        if not ok:
            return res
        checks = res.get("check_runs", []) + res.get("statuses", [])
        if not checks:
            return f"PR #{number}: sin checks de CI todavía."
        lines = [f"  [{c.get('status')}/{c.get('conclusion')}] {c.get('name') or c.get('context')}" for c in checks]
        return f"Checks del PR #{number} ({len(checks)}):\n" + "\n".join(lines)

    elif action == "pr_merge":
        number = params.get("number", "")
        method = params.get("method", "merge")
        ok, res = _api(f"/repos/{owner}/{repo}/pulls/{number}/merge", method="PUT",
                       body={"merge_method": method})
        if not ok:
            return res
        return f"PR #{number} mergeado ({method}): {res.get('message', 'OK')}"

    return "Acciones: pr_create (title=, head=, base=, body=), pr_list (state=, limit=), pr_view (number=), pr_checks (number=), pr_merge (number=, method=)"
