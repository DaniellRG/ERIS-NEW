"""
actions/ci_cd.py — CI/CD automation for ERIS.
Run tests, lint, generate reports, and manage commit hooks.
"""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "data" / "ci_cd_state.json"

def _load_state():
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"runs": [], "last_run": None}

def _save_state(state):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def _run_cmd(cmd, timeout=120):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=True, cwd=str(_BASE))
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1


def ci_cd(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "status":
        state = _load_state()
        return (
            f"CI/CD Status:\n"
            f"  Total runs: {len(state.get('runs', []))}\n"
            f"  Last run: {state.get('last_run', 'never')}\n"
            f"  Python: {_get_python_version()}\n"
            f"  Git: {'available' if _has_git() else 'not initialized'}"
        )

    elif action == "test":
        return _run_tests(params)

    elif action == "lint":
        return _run_lint(params)

    elif action == "typecheck":
        return _run_typecheck(params)

    elif action == "all":
        results = []
        results.append("=== CI/CD Full Pipeline ===\n")

        results.append("[1/3] Tests:")
        results.append(_run_tests(params))
        results.append("")

        results.append("[2/3] Lint:")
        results.append(_run_lint(params))
        results.append("")

        results.append("[3/3] Type Check:")
        results.append(_run_typecheck(params))

        _record_run("all", results)
        return "\n".join(results)

    elif action == "history":
        state = _load_state()
        runs = state.get("runs", [])
        if not runs:
            return "No CI/CD runs yet."
        lines = [f"CI/CD History ({len(runs)}):"]
        for r in runs[-10:]:
            lines.append(f"  [{r['timestamp'][:16]}] {r['action']} — {'PASS' if r.get('success') else 'FAIL'}")
        return "\n".join(lines)

    elif action == "install_hooks":
        return _install_hooks()

    elif action == "git_status":
        stdout, stderr, code = _run_cmd("git status --short")
        if code != 0:
            return "Not a git repository or git not available."
        lines = ["Git Status:"]
        if stdout:
            for line in stdout.split("\n")[:20]:
                lines.append(f"  {line}")
        else:
            lines.append("  Working tree clean")
        return "\n".join(lines)

    elif action == "git_log":
        stdout, stderr, code = _run_cmd("git log --oneline -10")
        if code != 0:
            return "Not a git repository."
        return f"Recent Commits:\n{stdout}" if stdout else "No commits yet."

    elif action == "git_diff":
        stdout, stderr, code = _run_cmd("git diff --stat")
        if code != 0:
            return "Not a git repository."
        return f"Diff:\n{stdout}" if stdout else "No changes."

    elif action == "clean":
        patterns = ["__pycache__", "*.pyc", ".pytest_cache", "*.egg-info"]
        cleaned = 0
        for pattern in patterns:
            for p in _BASE.rglob(pattern):
                try:
                    if p.is_dir():
                        import shutil
                        shutil.rmtree(str(p))
                    else:
                        p.unlink()
                    cleaned += 1
                except Exception:
                    pass
        return f"Cleaned {cleaned} files/directories."

    elif action == "security":
        return _security_check()

    return "Actions: status, test, lint, typecheck, all, history, install_hooks, git_status, git_log, git_diff, clean, security"


def _run_tests(params):
    test_file = params.get("file", "test_all.py")
    test_path = _BASE / test_file
    if not test_path.exists():
        return f"Test file not found: {test_file}"
    stdout, stderr, code = _run_cmd(f"python {test_file}", timeout=300)
    success = code == 0
    output = stdout if stdout else stderr
    return f"Tests {'PASSED' if success else 'FAILED'} (exit {code}):\n{output[-500:]}"


def _run_lint(params):
    target = params.get("target", ".")
    stdout, stderr, code = _run_cmd(f"python -m py_compile main.py 2>&1 || true")
    errors = [l for l in (stdout + stderr).split("\n") if "Error" in l or "error" in l]
    if not errors:
        return "Lint: No syntax errors found in main.py"
    return f"Lint issues ({len(errors)}):\n" + "\n".join(errors[:10])


def _run_typecheck(params):
    try:
        import mypy
        stdout, stderr, code = _run_cmd("python -m mypy --ignore-missing-imports main.py", timeout=120)
        return f"Typecheck:\n{stdout[:500]}"
    except ImportError:
        return "mypy not installed. Install with: pip install mypy"


def _install_hooks():
    hooks_dir = _BASE / ".git" / "hooks"
    if not hooks_dir.exists():
        return "No .git directory. Initialize git first."

    hook_content = """#!/bin/bash
echo "Running ERIS pre-commit checks..."
python test_all.py
if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi
echo "All tests passed. Proceeding with commit."
"""
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(hook_content)
    try:
        os.chmod(str(hook_path), 0o755)
    except Exception:
        pass
    return "Pre-commit hook installed. Tests will run before each commit."


def _security_check():
    issues = []
    security_patterns = [
        ("eval(", "Potential code injection"),
        ("exec(", "Potential code injection"),
        ("os.system(", "Shell injection risk"),
        ("shell=True", "Shell injection risk"),
    ]
    for py_file in _BASE.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for pattern, msg in security_patterns:
                if pattern in content:
                    issues.append(f"  {py_file.name}: {msg} ({pattern})")
        except Exception:
            pass

    if not issues:
        return "Security check: No issues found."
    return f"Security issues ({len(issues)}):\n" + "\n".join(issues[:20])


def _record_run(action, results):
    state = _load_state()
    success = any("PASS" in r for r in results if isinstance(r, str))
    state["runs"].append({
        "action": action,
        "timestamp": datetime.now().isoformat(),
        "success": success,
    })
    state["runs"] = state["runs"][-50:]
    state["last_run"] = datetime.now().isoformat()
    _save_state(state)


def _get_python_version():
    try:
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    except Exception:
        return "unknown"


def _has_git():
    return (_BASE / ".git").exists()
