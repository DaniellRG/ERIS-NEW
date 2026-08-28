"""
ERIS DevOps Pipeline — Git workflow completo (diff, commit, branch, merge, log)
+ test execution loop (run → fail → fix → re-run).

Capacidades:
- Git: status, diff, commit, branch, log, blame, merge, stash
- Test: run tests, iterative fix loop, coverage
"""
import os
import re
import subprocess
import time
from pathlib import Path

_WORKSPACE = Path(os.environ.get("ERIS_WORKSPACE", r"D:\Eris_Source"))


def _run_git(args: list, timeout: int = 30) -> dict:
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, timeout=timeout,
            cwd=str(_WORKSPACE),
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip()[:5000],
            "stderr": result.stderr.strip()[:1000],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Git timeout after {timeout}s"}
    except FileNotFoundError:
        return {"ok": False, "error": "Git not found in PATH"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _run_command(cmd: str, timeout: int = 120, cwd: str = None) -> dict:
    """Run an arbitrary shell command."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
            cwd=cwd or str(_WORKSPACE),
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip()[:8000],
            "stderr": result.stderr.strip()[:2000],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Command timeout after {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def devops_pipeline(parameters: dict = None, player=None) -> str:
    """Tool entry point."""
    params = parameters or {}
    action = params.get("action", "status").lower()

    # ── Git Operations ──
    if action == "git_status":
        result = _run_git(["status", "--short"])
        if not result["ok"]:
            return f"Error: {result.get('error', result.get('stderr', ''))}"
        files = result["stdout"].split("\n") if result["stdout"] else []
        return f"Git status ({len(files)} archivos):\n{result['stdout'][:3000]}" if result["stdout"] else "Working tree limpio."

    elif action == "git_diff":
        target = params.get("target", "HEAD")
        result = _run_git(["diff", target])
        if not result["ok"]:
            return f"Error: {result.get('error', result.get('stderr', ''))}"
        if not result["stdout"]:
            return "Sin cambios."
        return f"Diff vs {target}:\n{result['stdout'][:5000]}"

    elif action == "git_diff_staged":
        result = _run_git(["diff", "--cached"])
        if not result["ok"]:
            return f"Error: {result.get('error', result.get('stderr', ''))}"
        return f"Staged diff:\n{result['stdout'][:5000]}" if result["stdout"] else "Sin staged changes."

    elif action == "git_commit":
        message = params.get("message", "")
        if not message:
            return "Necesito 'message' para el commit."
        files = params.get("files", "")
        if files:
            file_list = [f.strip() for f in files.split(",") if f.strip()]
            _run_git(["add"] + file_list)
        else:
            _run_git(["add", "-A"])
        result = _run_git(["commit", "-m", message])
        if not result["ok"]:
            return f"Error commit: {result.get('stderr', result.get('error', ''))}"
        return f"Commit: {message}\n{result['stdout'][:500]}"

    elif action == "git_log":
        count = int(params.get("limit", 10))
        result = _run_git(["log", f"--oneline", f"-{count}"])
        if not result["ok"]:
            return f"Error: {result.get('error', '')}"
        return f"Últimos {count} commits:\n{result['stdout'][:3000]}"

    elif action == "git_branch":
        result = _run_git(["branch", "-a"])
        if not result["ok"]:
            return f"Error: {result.get('error', '')}"
        return f"Branches:\n{result['stdout'][:3000]}"

    elif action == "git_branch_create":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name' para el branch."
        result = _run_git(["checkout", "-b", name])
        if not result["ok"]:
            return f"Error: {result.get('stderr', result.get('error', ''))}"
        return f"Branch '{name}' creado y activo."

    elif action == "git_branch_switch":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name'."
        result = _run_git(["checkout", name])
        if not result["ok"]:
            return f"Error: {result.get('stderr', result.get('error', ''))}"
        return f"Cambiado a branch '{name}'."

    elif action == "git_merge":
        branch = params.get("branch", "")
        if not branch:
            return "Necesito 'branch' a mergear."
        result = _run_git(["merge", branch])
        if not result["ok"]:
            return f"Error merge: {result.get('stderr', result.get('error', ''))}"
        return f"Merge '{branch}': {result['stdout'][:500]}"

    elif action == "git_stash":
        result = _run_git(["stash", "push", "-m", params.get("message", "auto-stash")])
        return f"Stash: {result['stdout'][:200]}" if result["ok"] else f"Error: {result.get('error', '')}"

    elif action == "git_stash_pop":
        result = _run_git(["stash", "pop"])
        return f"Stash pop: {result['stdout'][:200]}" if result["ok"] else f"Error: {result.get('error', '')}"

    elif action == "git_blame":
        filepath = params.get("file", "")
        if not filepath:
            return "Necesito 'file'."
        result = _run_git(["blame", "--line-porcelain", filepath])
        if not result["ok"]:
            return f"Error: {result.get('error', '')}"
        return f"Blame {filepath}:\n{result['stdout'][:4000]}"

    elif action == "git_add":
        files = params.get("files", ".")
        file_list = [f.strip() for f in files.split(",") if f.strip()]
        result = _run_git(["add"] + file_list)
        return f"Staged: {files}" if result["ok"] else f"Error: {result.get('error', '')}"

    elif action == "git_reset":
        result = _run_git(["reset", "HEAD"])
        return "Unstaged all." if result["ok"] else f"Error: {result.get('error', '')}"

    # ── Test Execution ──
    elif action == "run_tests":
        cmd = params.get("command", "")
        if not cmd:
            # Auto-detect test runner
            if (_WORKSPACE / "pytest.ini").exists() or (_WORKSPACE / "pyproject.toml").exists():
                cmd = "python -m pytest -x --tb=short -q"
            elif (_WORKSPACE / "tests").exists():
                cmd = "python -m pytest tests/ -x --tb=short -q"
            else:
                return "No encontré pytest.ini, pyproject.toml, o tests/. Especificá 'command'."
        result = _run_command(cmd, timeout=int(params.get("timeout", 120)))
        output = result["stdout"] + "\n" + result["stderr"]
        return f"Tests {'PASARON' if result['ok'] else 'FALLARON'}:\n{output[:5000]}"

    elif action == "run_command":
        cmd = params.get("command", "")
        if not cmd:
            return "Necesito 'command'."
        result = _run_command(cmd, timeout=int(params.get("timeout", 120)))
        output = result["stdout"]
        if result["stderr"]:
            output += "\n--- STDERR ---\n" + result["stderr"]
        status = "OK" if result["ok"] else f"FALLÓ (exit code: {result['returncode']})"
        return f"{status}:\n{output[:6000]}"

    elif action == "test_loop":
        cmd = params.get("command", "python -m pytest -x --tb=short -q")
        max_iterations = int(params.get("max_iterations", 5))
        log = []

        for i in range(max_iterations):
            result = _run_command(cmd, timeout=int(params.get("timeout", 120)))
            iteration = {"attempt": i + 1, "passed": result["ok"],
                        "output": (result["stdout"] + "\n" + result["stderr"])[:2000]}
            log.append(iteration)
            if result["ok"]:
                return f"Tests PASARON en intento {i + 1}/{max_iterations}\n\n" + "\n".join(
                    f"  Intento {l['attempt']}: {'PASS' if l['passed'] else 'FAIL'}" for l in log
                )
        return f"Tests FALLARON después de {max_iterations} intentos:\n\n" + "\n".join(
            f"  Intento {l['attempt']}: {l['output'][:300]}" for l in log
        )

    # ── Project Info ──
    elif action == "project_info":
        info = []
        # Check common project files
        for name in ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "package.json", "Cargo.toml"]:
            p = _WORKSPACE / name
            if p.exists():
                info.append(f"  {name}: EXISTS ({p.stat().st_size} bytes)")
        # Python version
        py_result = _run_command("python --version")
        if py_result["ok"]:
            info.append(f"  Python: {py_result['stdout']}")
        # Git info
        git_result = _run_git(["remote", "-v"])
        if git_result["ok"] and git_result["stdout"]:
            info.append(f"  Git remote: {git_result['stdout'].split(chr(10))[0]}")
        return "Project info:\n" + "\n".join(info) if info else "No project info found."

    return f"Acción '{action}' no reconocida. Usa: git_status, git_diff, git_commit, git_log, git_branch, git_merge, run_tests, run_command, test_loop, project_info"
