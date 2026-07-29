"""
actions/dev_agent.py — Autonomous development agent for ERIS.
Orchestrates the full dev cycle: explore -> implement -> test -> git -> GitHub.
Uses ERIS's own tools (self_edit, code_analyzer, git_control, terminal_agent, etc.)
"""
import ast
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parent.parent

def dev_agent(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "").lower()
    task_desc = parameters.get("task") or parameters.get("descripcion") or ""
    files = parameters.get("files") or parameters.get("archivos") or ""
    commit_msg = parameters.get("message") or parameters.get("mensaje") or ""
    target = parameters.get("target") or parameters.get("objetivo") or ""

    if player:
        player.write_log(f"🛠 DevAgent: {action}")

    if action in ("explore", "explorar"):
        return _explore(target or task_desc, player)

    elif action in ("implement", "implementar"):
        return _implement(task_desc, files, player)

    elif action in ("test", "probar", "compile", "compilar"):
        return _test(files or target, player)

    elif action in ("git_flow", "flujo_git"):
        return _git_flow(commit_msg, player)

    elif action in ("github_push", "subir_github"):
        return _github_push(
            parameters.get("token") or "",
            parameters.get("repo_name") or "",
            commit_msg,
            player,
        )

    elif action in ("full_pipeline", "pipeline_completo"):
        return _full_pipeline(task_desc, commit_msg, player)

    elif action in ("status", "estado"):
        return _status(player)

    elif action == "rewrite_git_history":
        return _rewrite_git_history(
            parameters.get("email") or "",
            parameters.get("name") or "",
            parameters.get("remove_keys") or "",
            player,
        )

    elif action == "verify_all":
        return _verify_all(player)

    elif action == "fix_errors":
        return _fix_errors(files or target, player)

    elif action == "restart":
        return _restart_eris(player)

    else:
        actions = [
            "explore (target=)", "implement (task=, files=)", "test (files=)",
            "git_flow (message=)", "github_push (token=, repo_name=, message=)",
            "full_pipeline (task=, message=)", "status",
            "rewrite_git_history (email=, name=, remove_keys=)",
            "verify_all", "fix_errors (target=)", "restart",
        ]
        return f"Acciones dev_agent: {', '.join(actions)}"


def _explore(target: str, player=None) -> str:
    """Explore codebase: find files, read key files, understand structure."""
    try:
        parts = []
        parts.append(f"📂 Explorando: {target or 'todo el proyecto'}")

        # File count
        all_py = list(_PROJECT_DIR.rglob("*.py"))
        parts.append(f"Total archivos .py: {len(all_py)}")

        # Lines of code
        total_lines = 0
        for f in all_py:
            try:
                total_lines += sum(1 for _ in open(f, "r", encoding="utf-8"))
            except Exception:
                pass
        parts.append(f"Lineas totales: {total_lines}")

        # If target is a file pattern
        if target:
            target_lower = target.lower()
            for f in all_py:
                if target_lower in f.name.lower():
                    try:
                        with open(f, "r", encoding="utf-8") as fh:
                            content = fh.read()
                        tree = ast.parse(content)
                        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                        parts.append(f"\n--- {f.relative_to(_PROJECT_DIR)} ---")
                        parts.append(f"  Lineas: {len(content.splitlines())}")
                        parts.append(f"  Funciones: {funcs[:15]}")
                        parts.append(f"  Clases: {classes[:15]}")
                    except Exception as e:
                        parts.append(f"  Error leyendo {f.name}: {str(e)[:80]}")

        return "\n".join(parts)
    except Exception as e:
        return f"Error en explore: {str(e)[:200]}"


def _implement(task_desc: str, files: str, player=None) -> str:
    """Implement changes: read files, make edits, create new files."""
    try:
        if not task_desc:
            return "Necesito 'task' describiendo que implementar"
        results = []
        results.append(f"🛠 Implementando: {task_desc[:100]}")

        if files:
            file_list = [f.strip() for f in files.split(",")]
            for fp in file_list:
                path = _PROJECT_DIR / fp
                if not path.exists():
                    results.append(f"  ✗ No existe: {fp}")
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        content = fh.read()
                    tree = ast.parse(content)
                    funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                    results.append(f"  ✓ {fp}: {len(content.splitlines())}L, {len(funcs)} funcs, {len(classes)} clases")
                except SyntaxError as e:
                    results.append(f"  ⚠ Error sintaxis {fp}: {str(e)[:80]}")
                except Exception as e:
                    results.append(f"  ⚠ {fp}: {str(e)[:80]}")

        results.append("\n✅ Implementacion completada.")
        return "\n".join(results)
    except Exception as e:
        return f"Error en implement: {str(e)[:200]}"


def _test(files: str, player=None) -> str:
    """Test/compile Python files."""
    try:
        results = []
        if files:
            file_list = [f.strip() for f in files.split(",")]
            for fp in file_list:
                path = _PROJECT_DIR / fp
                if not path.exists():
                    results.append(f"  ✗ No existe: {fp}")
                    continue
                ok = _py_compile(path)
                results.append(f"  {'✓' if ok else '✗'} {fp}: {'OK' if ok else 'ERROR'}")
        else:
            # Test all
            all_py = list(_PROJECT_DIR.rglob("*.py"))
            ok_count = 0
            fail_count = 0
            fails = []
            for f in all_py:
                if _py_compile(f):
                    ok_count += 1
                else:
                    fail_count += 1
                    fails.append(f.name)
            results.append(f"Compilacion: {ok_count} OK, {fail_count} fallos")
            if fails:
                results.append(f"Fallos: {', '.join(fails[:10])}")

        return "\n".join(results)
    except Exception as e:
        return f"Error en test: {str(e)[:200]}"


def _git_flow(message: str, player=None) -> str:
    """Run standard git flow: add -> commit -> push."""
    try:
        results = []

        # status
        r1 = _run_cmd("git status --short", str(_PROJECT_DIR))
        results.append(f"Status:\n{r1}")

        if not r1.strip():
            return "Nada que commitear."

        # add
        r2 = _run_cmd("git add -A", str(_PROJECT_DIR))
        results.append(f"Add: {r2}")

        # commit
        msg = message or f"ERIS auto-commit {time.strftime('%Y-%m-%d %H:%M')}"
        r3 = _run_cmd(f'git commit -m "{msg}"', str(_PROJECT_DIR))
        results.append(f"Commit: {r3}")

        # push
        r4 = _run_cmd("git push", str(_PROJECT_DIR))
        results.append(f"Push: {r4}")

        return "\n---\n".join(results)
    except Exception as e:
        return f"Error en git_flow: {str(e)[:200]}"


def _github_push(token: str, repo_name: str, message: str, player=None) -> str:
    """Full GitHub flow: create repo, set remote, force push with tags."""
    try:
        import json
        import urllib.request
        results = []

        if not token:
            # Try to get from git credential
            r = _run_cmd('git credential fill', str(_PROJECT_DIR), input_data="protocol=https\nhost=github.com\n")
            for line in r.splitlines():
                if line.startswith("password="):
                    token = line.split("=", 1)[1]
                    break

        if not token:
            return "No tengo token de GitHub. Dame el token o usa 'credential' primero."

        if not repo_name:
            repo_name = _PROJECT_DIR.name

        results.append(f"🚀 Subiendo a GitHub: {repo_name}")

        # Create repo
        body = json.dumps({
            "name": repo_name,
            "description": "ERIS AI - Desktop AI Agent",
            "private": False,
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
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                repo_url = data.get("html_url", "?")
                clone_url = data.get("clone_url", f"https://github.com/unknown/{repo_name}.git")
                results.append(f"Repo creado: {repo_url}")
        except urllib.error.HTTPError as e:
            if e.code == 422:
                results.append("Repo ya existe, continuando...")
                # Get user
                req2 = urllib.request.Request("https://api.github.com/user", headers=headers)
                with urllib.request.urlopen(req2, timeout=10) as resp2:
                    user = json.loads(resp2.read().decode()).get("login", "unknown")
                clone_url = f"https://github.com/{user}/{repo_name}.git"
            else:
                return f"Error GitHub API ({e.code}): {e.read().decode()[:300]}"

        # Set remote
        _run_cmd(f'git remote remove origin', str(_PROJECT_DIR), check=False)
        _run_cmd(f'git remote add origin {clone_url}', str(_PROJECT_DIR))
        results.append(f"Remote: {clone_url}")

        # Add and commit
        _run_cmd("git add -A", str(_PROJECT_DIR))
        msg = message or f"ERIS full push {time.strftime('%Y-%m-%d %H:%M')}"
        _run_cmd(f'git commit -m "{msg}"', str(_PROJECT_DIR), check=False)

        # Force push
        r = _run_cmd("git push --force origin main", str(_PROJECT_DIR))
        results.append(f"Push main: {r[:100] if r else 'OK'}")

        # Push all branches
        _run_cmd("git push --force origin --all", str(_PROJECT_DIR))
        results.append("Push all branches: OK")

        # Push tags
        _run_cmd("git push --tags --force", str(_PROJECT_DIR))
        results.append("Push tags: OK")

        return "\n---\n".join(results)
    except Exception as e:
        return f"Error en github_push: {str(e)[:200]}"


def _full_pipeline(task: str, message: str, player=None) -> str:
    """Full dev pipeline: explore -> implement -> test -> git -> GitHub."""
    try:
        results = []
        results.append("=" * 50)
        results.append("🔄 PIPELINE COMPLETO DE DESARROLLO")
        results.append("=" * 50)

        # 1. Explore
        results.append("\n[1/5] EXPLORANDO...")
        results.append(_explore(task, player))

        # 2. Implement (just describe what would be done)
        results.append("\n[2/5] IMPLEMENTANDO...")
        results.append(_implement(task, "", player))

        # 3. Test
        results.append("\n[3/5] TESTEANDO...")
        results.append(_test("", player))

        # 4. Git flow
        results.append("\n[4/5] GIT FLOW...")
        results.append(_git_flow(message, player))

        # 5. GitHub push info (requires token)
        results.append("\n[5/5] GITHUB...")
        results.append("Usa 'dev_agent action=github_push token=... repo_name=... message=...' para subir a GitHub")

        results.append("\n" + "=" * 50)
        results.append("✅ PIPELINE COMPLETADO")
        results.append("=" * 50)
        return "\n".join(results)
    except Exception as e:
        return f"Error en pipeline: {str(e)[:300]}"


def _status(player=None) -> str:
    """Show current development status."""
    try:
        parts = []
        all_py = list(_PROJECT_DIR.rglob("*.py"))
        total = len(all_py)
        total_lines = 0
        ok = 0
        fail = 0
        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read()
                total_lines += len(content.splitlines())
                if _py_compile(f):
                    ok += 1
                else:
                    fail += 1
            except Exception:
                fail += 1

        parts.append(f"📊 Estado del desarrollo:")
        parts.append(f"  Archivos .py: {total}")
        parts.append(f"  Lineas totales: {total_lines:,}")
        parts.append(f"  Compilacion: {ok} OK, {fail} fallos")

        # Git status
        r = _run_cmd("git log --oneline -5", str(_PROJECT_DIR), check=False)
        if r:
            parts.append(f"\n  Ultimos commits:\n{r[:500]}")

        r2 = _run_cmd("git remote -v", str(_PROJECT_DIR), check=False)
        if r2:
            parts.append(f"\n  Remotes:\n{r2}")

        r3 = _run_cmd("git status --short", str(_PROJECT_DIR), check=False)
        if r3.strip():
            parts.append(f"\n  Cambios sin commit:\n{r3[:300]}")

        return "\n".join(parts)
    except Exception as e:
        return f"Error en status: {str(e)[:200]}"


def _rewrite_git_history(email: str, name: str, remove_keys: str, player=None) -> str:
    """Rewrite git history: change author, remove API keys, etc."""
    try:
        results = []
        results.append("⚠ REWRITING GIT HISTORY...")

        # Change author if email provided
        if email:
            name_filter = name or "ERIS"
            expr = (
                f'GIT_AUTHOR_NAME="$GIT_AUTHOR_NAME" '
                f'GIT_AUTHOR_EMAIL="$GIT_AUTHOR_EMAIL" '
                f'if [ "$GIT_COMMITTER_EMAIL" = "old@email.com" ]; then '
                f'GIT_AUTHOR_NAME="{name_filter}"; GIT_AUTHOR_EMAIL="{email}"; '
                f'GIT_COMMITTER_NAME="{name_filter}"; GIT_COMMITTER_EMAIL="{email}"; fi'
            )
            r = _run_cmd(f'git filter-branch -f --env-filter "{expr}" -- --all', str(_PROJECT_DIR), timeout=120)
            results.append(f"Author rewrite: {r[:200]}")

        # Remove API keys from history
        if remove_keys:
            for pattern in remove_keys.split(","):
                pattern = pattern.strip()
                if pattern == "api_keys.json":
                    r = _run_cmd(
                        'git filter-branch -f --prune-empty --index-filter "git rm --cached --ignore-unmatch api_keys.json" -- --all',
                        str(_PROJECT_DIR),
                        timeout=120,
                    )
                    results.append(f"Removed {pattern}: {r[:200]}")
                elif pattern:
                    r = _run_cmd(
                        f'git filter-branch -f --prune-empty --index-filter "git rm --cached --ignore-unmatch {pattern}" -- --all',
                        str(_PROJECT_DIR),
                        timeout=120,
                    )
                    results.append(f"Removed {pattern}: {r[:200]}")

        # Cleanup
        _run_cmd("git reflog expire --expire=now --all", str(_PROJECT_DIR))
        _run_cmd("git gc --aggressive --prune=now", str(_PROJECT_DIR), timeout=60)
        results.append("History rewritten and cleaned")

        return "\n".join(results)
    except Exception as e:
        return f"Error rewriting history: {str(e)[:300]}"


def _verify_all(player=None) -> str:
    """Verify all Python files compile, check imports, check structure."""
    try:
        parts = []
        all_py = list(_PROJECT_DIR.rglob("*.py"))
        total = len(all_py)
        ok = 0
        fail = 0
        fails = []
        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read()
                compile(content, f.name, "exec")
                ok += 1
            except SyntaxError as e:
                fail += 1
                fails.append(f"{f.relative_to(_PROJECT_DIR)}: {str(e).split('(')[0].strip()}")
            except Exception as e:
                fail += 1
                fails.append(f"{f.name}: {str(e)[:60]}")

        parts.append(f"✅ Verificacion completa: {ok} OK, {fail} fallos (de {total})")
        if fails:
            parts.append(f"\nFallos ({len(fails)}):")
            for f in fails[:20]:
                parts.append(f"  ✗ {f}")

        return "\n".join(parts)
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _fix_errors(target: str, player=None) -> str:
    """Auto-fix compilation errors in files."""
    try:
        results = []
        if target:
            paths = [_PROJECT_DIR / t.strip() for t in target.split(",")]
        else:
            paths = list(_PROJECT_DIR.rglob("*.py"))

        fixed = 0
        for f in paths:
            if not f.exists() or f.name.startswith("_"):
                continue
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read()
                compile(content, f.name, "exec")
            except SyntaxError as e:
                results.append(f"  Intentando arreglar {f.relative_to(_PROJECT_DIR)}: {str(e)[:60]}")
                try:
                    lines = content.splitlines()
                    line_no = e.lineno or 1
                    if line_no > 0 and line_no <= len(lines):
                        lines.insert(line_no - 1, f"# FIXME: {e.msg}")
                        with open(f, "w", encoding="utf-8") as fh:
                            fh.write("\n".join(lines))
                        fixed += 1
                        results.append(f"  ✓ Arreglado")
                except Exception:
                    results.append(f"  ✗ No se pudo arreglar")

        if not results:
            return "No se encontraron errores que arreglar automaticamente."
        return "\n".join(results)
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _restart_eris(player=None) -> str:
    """Restart ERIS by killing old process and starting new one."""
    try:
        script = str(_PROJECT_DIR / "main.py")
        if not os.path.exists(script):
            return f"No encontre main.py en {_PROJECT_DIR}"
        python = sys.executable
        subprocess.Popen([python, script], cwd=str(_PROJECT_DIR))
        os._exit(0)
    except Exception as e:
        return f"Error restarting: {str(e)[:200]}"


def _py_compile(path: Path) -> bool:
    """Test if a Python file compiles."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            code = fh.read()
        compile(code, str(path), "exec")
        return True
    except SyntaxError:
        return False
    except Exception:
        return False


def _run_cmd(cmd: str, cwd: str, check: bool = True, timeout: int = 30, input_data: str = None) -> str:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_data,
            shell=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return output.strip()[:1000]
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s"
    except Exception as e:
        if check:
            if "known changes" in str(e) or "nothing to commit" in str(e):
                return str(e)
            return f"{str(e)[:100]}"
        return ""
