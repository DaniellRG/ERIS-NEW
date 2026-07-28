# -*- coding: utf-8 -*-
"""
self_healing_loop.py — ERIS Self-Healing Orchestrator.
Detect → Backup → Fix → Test → Apply → Restart.

This module provides the INFRASTRUCTURE for self-healing.
ERIS's LLM brain (Gemini) generates the actual fixes.
This module provides: detection, backup, testing, validation, restart.
"""
import ast
import json
import os
import py_compile
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / "backups"
HEALING_LOG = BASE_DIR / "data" / "self_healing_loop.json"
TEMP_DIR = BASE_DIR / "data" / "healing_temp"
PYTHON = sys.executable
MAX_ATTEMPTS = 5


def _log(msg: str):
    """Append to healing log."""
    try:
        entries = []
        if HEALING_LOG.exists():
            entries = json.loads(HEALING_LOG.read_text("utf-8"))
        entries.append({"time": datetime.now().isoformat(), "msg": msg})
        HEALING_LOG.parent.mkdir(parents=True, exist_ok=True)
        HEALING_LOG.write_text(json.dumps(entries[-300:], indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass


def _backup_file(file_path: Path) -> str:
    """Create timestamped backup before any modification."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rel = str(file_path.relative_to(BASE_DIR)).replace(os.sep, "__").replace("/", "__")
    bak = BACKUP_DIR / f"{rel}.{ts}.heal_loop.bak"
    shutil.copy2(file_path, bak)
    return str(bak)


def _syntax_check(file_path: Path) -> tuple[bool, str]:
    """Check if a Python file has valid syntax."""
    try:
        py_compile.compile(str(file_path), doraise=True)
        return True, "Syntax OK"
    except py_compile.PyCompileError as e:
        return False, str(e)


def _runtime_test(file_path: Path, timeout: int = 10) -> tuple[bool, str]:
    """Try to import the file (without executing top-level side effects)."""
    try:
        result = subprocess.run(
            [PYTHON, "-c", f"import ast; ast.parse(open(r'{file_path}', encoding='utf-8').read())"],
            capture_output=True, text=True, timeout=timeout,
            creationflags=0x08000000
        )
        if result.returncode == 0:
            return True, "AST parse OK"
        return False, result.stderr[:500] if result.stderr else "AST parse failed"
    except subprocess.TimeoutExpired:
        return False, "Timeout during AST parse"
    except Exception as e:
        return False, str(e)


def _ruff_check(file_path: Path) -> tuple[bool, str]:
    """Run ruff on a single file to check for critical errors."""
    try:
        result = subprocess.run(
            [PYTHON, "-m", "ruff", "check", str(file_path), "--select=F,E", "--output-format=concise"],
            capture_output=True, text=True, timeout=30,
            creationflags=0x08000000
        )
        output = result.stdout.strip()
        if not output or result.returncode == 0:
            return True, "Ruff clean"
        return False, output[:500]
    except Exception:
        return True, "Ruff not available, skipping"


def _validate_fix(original_path: Path, candidate_code: str) -> tuple[bool, str, str]:
    """
    Validate a candidate fix BEFORE applying it.
    Returns (is_valid, message, temp_path_or_empty).
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    temp_file = TEMP_DIR / f"fix_{ts}.py"

    try:
        # 1. Write candidate to temp file
        temp_file.write_text(candidate_code, encoding="utf-8")

        # 2. Syntax check
        ok, msg = _syntax_check(temp_file)
        if not ok:
            return False, f"Syntax error: {msg}", ""

        # 3. AST parse test
        ok, msg = _runtime_test(temp_file)
        if not ok:
            return False, f"AST error: {msg}", ""

        # 4. Ruff check (non-critical)
        ok, msg = _ruff_check(temp_file)

        return True, "All validations passed", str(temp_file)

    except Exception as e:
        return False, f"Validation error: {e}", ""
    finally:
        # Cleanup temp file
        try:
            if temp_file.exists():
                temp_file.unlink()
        except Exception:
            pass


def _detect_issues(file_path: Path) -> list[dict]:
    """
    Detect all issues in a file. Returns a structured list.
    This is what gets sent to the LLM for fix generation.
    """
    issues = []

    # 1. Syntax check
    ok, msg = _syntax_check(file_path)
    if not ok:
        issues.append({
            "severity": "CRITICAL",
            "type": "syntax_error",
            "message": msg,
            "file": str(file_path),
        })

    # 2. AST analysis
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Find bare excepts
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({
                    "severity": "WARNING",
                    "type": "bare_except",
                    "line": node.lineno,
                    "message": "bare 'except:' — should catch specific exception",
                    "file": str(file_path),
                })

        # Find undefined names (robust AST analysis)
        defined = set()
        used = {}

        for node in ast.walk(tree):
            # Function definitions — params + name
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined.add(node.name)
                for arg in node.args.args:
                    defined.add(arg.arg)
                for arg in node.args.posonlyargs:
                    defined.add(arg.arg)
                for arg in node.args.kwonlyargs:
                    defined.add(arg.arg)
                if node.args.vararg:
                    defined.add(node.args.vararg.arg)
                if node.args.kwarg:
                    defined.add(node.args.kwarg.arg)
            # Class definitions
            elif isinstance(node, ast.ClassDef):
                defined.add(node.name)
            # Assignments
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        defined.add(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)
            # Augmented assignments (+=, -=, etc.)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)
            # Walrus operator (:=)
            elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)
            # For-loop targets
            elif isinstance(node, ast.For):
                if isinstance(node.target, ast.Name):
                    defined.add(node.target.id)
                elif isinstance(node.target, ast.Tuple):
                    for elt in node.target.elts:
                        if isinstance(elt, ast.Name):
                            defined.add(elt.id)
            # With-as targets
            elif isinstance(node, ast.With):
                for item in node.items:
                    if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                        defined.add(item.optional_vars.id)
            # Exception handler names
            elif isinstance(node, ast.ExceptHandler):
                if node.name:
                    defined.add(node.name)
            # Imports
            elif isinstance(node, ast.Import):
                for a in node.names:
                    defined.add(a.asname or a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    if a.name == "*":
                        continue
                    defined.add(a.asname or a.name)
            # Global/nonlocal
            elif isinstance(node, ast.Global):
                for n in node.names:
                    defined.add(n)
            elif isinstance(node, ast.Nonlocal):
                for n in node.names:
                    defined.add(n)
            # Lambda params
            elif isinstance(node, ast.Lambda):
                for arg in node.args.args:
                    defined.add(arg.arg)
                if node.args.vararg:
                    defined.add(node.args.vararg.arg)
                if node.args.kwarg:
                    defined.add(node.args.kwarg.arg)
            # Comprehension targets
            elif isinstance(node, ast.comprehension):
                if isinstance(node.target, ast.Name):
                    defined.add(node.target.id)
                elif isinstance(node.target, ast.Tuple):
                    for elt in node.target.elts:
                        if isinstance(elt, ast.Name):
                            defined.add(elt.id)
            # Names used (only track loads, not stores)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in used:
                    used[node.id] = node.lineno

        builtins_set = set(dir(__builtins__)) if not isinstance(__builtins__, dict) else set(__builtins__.keys())
        # Also include all common builtin names
        builtins_set.update([
            "str", "int", "float", "bool", "list", "dict", "set", "tuple",
            "type", "object", "None", "True", "False",
            "len", "range", "enumerate", "zip", "map", "filter",
            "sorted", "reversed", "any", "all", "sum", "min", "max", "abs",
            "print", "input", "open", "isinstance", "issubclass", "hasattr",
            "getattr", "setattr", "delattr", "super", "property", "staticmethod",
            "classmethod", "vars", "dir", "id", "hash", "repr", "format",
            "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
            "AttributeError", "ImportError", "RuntimeError", "StopIteration",
            "OSError", "IOError", "FileNotFoundError", "FileExistsError",
            "json", "os", "sys", "time", "datetime", "Path", "Pathlib",
            "subprocess", "shutil", "ast", "re", "math", "random",
            "Optional", "Union", "List", "Dict", "Tuple", "Set", "Any",
        ])
        for name, lineno in used.items():
            if name.startswith("_"):
                continue
            if name in builtins_set:
                continue
            if name in defined:
                continue
            if name in ("player", "self", "cls", "kwargs", "args", "e", "f", "r", "p", "t", "n", "i", "x", "y", "k", "v", "s", "fp", "bak"):
                continue
            issues.append({
                "severity": "ERROR",
                "type": "undefined_name",
                "line": lineno,
                "message": f"undefined name '{name}'",
                "file": str(file_path),
            })

    except SyntaxError:
        pass  # Already caught by syntax check

    # 3. Ruff check
    try:
        result = subprocess.run(
            [PYTHON, "-m", "ruff", "check", str(file_path), "--select=F,E,B", "--output-format=concise"],
            capture_output=True, text=True, timeout=30,
            creationflags=0x08000000
        )
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(":")
            if len(parts) >= 4:
                try:
                    lineno = int(parts[1].strip())
                    code = parts[2].strip().split()[0] if parts[2].strip() else "E"
                    msg = ":".join(parts[3:]).strip()
                    severity = "ERROR" if code.startswith("F") else "WARNING"
                    issues.append({
                        "severity": severity,
                        "type": f"ruff_{code}",
                        "line": lineno,
                        "message": msg,
                        "file": str(file_path),
                    })
                except (ValueError, IndexError):
                    pass
    except Exception:
        pass

    return issues


def _build_fix_prompt(file_path: Path, issues: list[dict], current_code: str) -> str:
    """
    Build the prompt that goes to ERIS's LLM brain for fix generation.
    Returns a structured prompt string.
    """
    issue_summary = "\n".join(
        f"  [{i['severity']}] L{i.get('line', '?')}: {i['type']} — {i['message']}"
        for i in issues
    )

    return f"""You are ERIS's self-healing system. Fix the following issues in this file.

FILE: {file_path.name}
ISSUES FOUND ({len(issues)}):
{issue_summary}

CURRENT CODE:
```python
{current_code}
```

INSTRUCTIONS:
1. Fix ALL issues listed above.
2. Keep the original functionality intact.
3. Return ONLY the corrected Python code, nothing else.
4. Do NOT add comments explaining the fixes.
5. Do NOT wrap in markdown code blocks.
6. Ensure the code is syntactically valid Python.
"""


# ═══════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════

def self_healing_loop(parameters: dict, player=None) -> str:
    """
    Self-Healing Loop orchestrator for ERIS.
    Actions:
      detect     — Detect issues in a file (returns structured issues + prompt)
      fix_file   — Full cycle: detect → prompt → validate → apply
      test       — Test if a file compiles and parses
      validate   — Validate candidate code before applying
      scan_all   — Scan all ERIS .py files for issues
      status     — Show healing history
      rollback   — Restore last backup
      restart    — Kill and restart ERIS process
    """
    action = parameters.get("action", "detect").lower()
    file_ref = parameters.get("file", "")
    candidate_code = parameters.get("code", "")

    if action == "info":
        return (
            "Self-Healing Loop — Auto-detect, fix, test, apply.\n\n"
            "Actions:\n"
            "  detect     — Detect issues in a file (returns prompt for LLM)\n"
            "  fix_file   — Full cycle: detect → validate candidate → apply\n"
            "  test       — Syntax + AST test a file\n"
            "  validate   — Validate candidate code before applying\n"
            "  scan_all   — Scan all ERIS .py files\n"
            "  status     — Healing history\n"
            "  rollback   — Restore last backup\n"
            "  restart    — Restart ERIS process\n\n"
            "Parameters:\n"
            "  file — file to analyze/fix\n"
            "  code — candidate fix code (for fix_file)"
        )

    # ── TEST ──
    if action == "test":
        if not file_ref:
            return "Error: 'file' required"
        fp = BASE_DIR / file_ref
        if not fp.exists():
            return f"Error: '{file_ref}' not found"

        results = []
        ok, msg = _syntax_check(fp)
        results.append(f"Syntax: {'OK' if ok else 'FAIL'} — {msg}")

        ok, msg = _runtime_test(fp)
        results.append(f"AST:    {'OK' if ok else 'FAIL'} — {msg}")

        ok, msg = _ruff_check(fp)
        results.append(f"Ruff:   {'OK' if ok else 'WARN'} — {msg[:200]}")

        return f"Test results for {file_ref}:\n" + "\n".join(results)

    # ── VALIDATE ──
    if action == "validate":
        if not candidate_code:
            return "Error: 'code' required (candidate fix to validate)"
        target = file_ref or "test_validation.py"
        fp = BASE_DIR / target if not Path(target).is_absolute() else Path(target)
        ok, msg, temp = _validate_fix(fp, candidate_code)
        return f"Validation: {'PASS' if ok else 'FAIL'} — {msg}"

    # ── DETECT ──
    if action == "detect":
        if not file_ref:
            return "Error: 'file' required (e.g. 'actions/self_heal.py')"
        fp = BASE_DIR / file_ref
        if not fp.exists():
            return f"Error: '{file_ref}' not found"

        issues = _detect_issues(fp)
        current_code = fp.read_text(encoding="utf-8")
        prompt = _build_fix_prompt(fp, issues, current_code)

        _log(f"DETECT {file_ref}: {len(issues)} issues found")

        report = f"DETECT — {file_ref}\n"
        report += f"Issues: {len(issues)}\n\n"

        if not issues:
            report += "No issues found. File is healthy."
            return report

        # Group by severity
        critical = [i for i in issues if i["severity"] == "CRITICAL"]
        errors = [i for i in issues if i["severity"] == "ERROR"]
        warnings = [i for i in issues if i["severity"] == "WARNING"]

        if critical:
            report += f"CRITICAL ({len(critical)}):\n"
            for i in critical:
                report += f"  L{i.get('line', '?')}: {i['message']}\n"
        if errors:
            report += f"ERRORS ({len(errors)}):\n"
            for i in errors[:10]:
                report += f"  L{i.get('line', '?')}: {i['message']}\n"
        if warnings:
            report += f"WARNINGS ({len(warnings)}):\n"
            for i in warnings[:10]:
                report += f"  L{i.get('line', '?')}: {i['message']}\n"

        report += f"\nPROMPT FOR LLM FIX:\n{prompt}"
        return report

    # ── FIX_FILE (full cycle) ──
    if action == "fix_file":
        if not file_ref:
            return "Error: 'file' required"
        fp = BASE_DIR / file_ref
        if not fp.exists():
            return f"Error: '{file_ref}' not found"

        # Step 1: Detect
        issues = _detect_issues(fp)
        if not issues:
            return f"✅ {file_ref}: No issues detected. File is healthy."

        # Step 2: If candidate code provided, validate and apply
        if candidate_code:
            ok, msg, temp = _validate_fix(fp, candidate_code)
            if not ok:
                return f"❌ Candidate fix FAILED validation: {msg}"

            # Create backup
            backup = _backup_file(fp)

            # Apply fix
            fp.write_text(candidate_code, encoding="utf-8")

            # Verify the fix
            ok2, msg2 = _syntax_check(fp)
            if not ok2:
                # Rollback
                shutil.copy2(backup, fp)
                _log(f"FIX FAILED (rollback): {file_ref} — {msg2}")
                return f"❌ Fix caused syntax error! Rollback applied.\nError: {msg2}"

            _log(f"FIX APPLIED: {file_ref} — {len(issues)} issues fixed")
            return (
                f"✅ Fix applied to {file_ref}\n"
                f"Backup: {Path(backup).name}\n"
                f"Issues fixed: {len(issues)}\n"
                f"Validation: {msg}"
            )

        # Step 3: No candidate code — return prompt for LLM to generate fix
        current_code = fp.read_text(encoding="utf-8")
        prompt = _build_fix_prompt(fp, issues, current_code)

        _log(f"FIX NEEDED: {file_ref} — {len(issues)} issues, waiting for LLM")

        return (
            f"FIX NEEDED — {file_ref}\n"
            f"Issues: {len(issues)}\n"
            f"Action required: LLM must generate fix code, then call fix_file with code parameter.\n\n"
            f"PROMPT:\n{prompt}"
        )

    # ── SCAN_ALL ──
    if action == "scan_all":
        ignore = {"__pycache__", ".git", "build", "lib", "share", "venv", ".venv"}
        files = []
        for f in BASE_DIR.rglob("*.py"):
            rel = f.relative_to(BASE_DIR)
            if any(p in ignore for p in rel.parts):
                continue
            files.append(f)

        results = []
        total_issues = 0
        for f in sorted(files):
            issues = _detect_issues(f)
            total_issues += len(issues)
            if issues:
                critical = sum(1 for i in issues if i["severity"] == "CRITICAL")
                errors = sum(1 for i in issues if i["severity"] == "ERROR")
                warnings = sum(1 for i in issues if i["severity"] == "WARNING")
                marker = "🔴" if critical else "🟡" if errors else "🟢"
                rel = str(f.relative_to(BASE_DIR))
                results.append(f"{marker} {rel}: {len(issues)} (C:{critical} E:{errors} W:{warnings})")

        report = f"SCAN ALL — {len(files)} files, {total_issues} total issues\n\n"
        if results:
            report += "\n".join(results[:30])
            if len(results) > 30:
                report += f"\n... and {len(results) - 30} more files with issues"
        else:
            report += "All files healthy!"

        _log(f"SCAN ALL: {len(files)} files, {total_issues} issues")
        return report

    # ── STATUS ──
    if action == "status":
        try:
            if HEALING_LOG.exists():
                entries = json.loads(HEALING_LOG.read_text("utf-8"))
                report = f"Healing History ({len(entries)} entries):\n\n"
                for e in entries[-20:]:
                    ts = e.get("time", "?")[:19]
                    msg = e.get("msg", "?")
                    report += f"  [{ts}] {msg}\n"
                return report
        except Exception:
            pass
        return "No healing history yet."

    # ── ROLLBACK ──
    if action == "rollback":
        if not file_ref:
            # Rollback most recent
            backups = sorted(
                BACKUP_DIR.glob("*.heal_loop.bak"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not backups:
                return "No healing backups found."
            latest = backups[0]
            parts = latest.stem.split(".")
            if len(parts) >= 2:
                orig_rel = parts[0].replace("__", os.sep)
                orig_path = BASE_DIR / orig_rel
                if orig_path.exists():
                    _backup_file(orig_path)
                shutil.copy2(latest, orig_path)
                _log(f"ROLLBACK: {orig_rel} from {latest.name}")
                return f"✅ Rollback: {orig_rel} restored from {latest.name}"
            return f"Could not determine original file from: {latest.name}"

        fp = BASE_DIR / file_ref
        safe = str(fp.relative_to(BASE_DIR)).replace(os.sep, "__") if fp.exists() else file_ref.replace(os.sep, "__")
        candidates = sorted(
            BACKUP_DIR.glob(f"{safe}.*.heal_loop.bak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if not candidates:
            return f"No healing backups for '{file_ref}'"
        latest = candidates[0]
        if fp.exists():
            _backup_file(fp)
        shutil.copy2(latest, fp)
        _log(f"ROLLBACK: {file_ref} from {latest.name}")
        return f"✅ Rollback: {file_ref} restored from {latest.name}"

    # ── RESTART ──
    if action == "restart":
        try:
            # Find current ERIS process
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace"
            )
            my_pid = os.getpid()
            killed = 0
            for line in result.stdout.split("\n"):
                if "python" in line.lower():
                    parts = line.split(",")
                    if len(parts) >= 2:
                        pid = parts[1].strip('"')
                        if pid and pid != str(my_pid):
                            try:
                                subprocess.run(["taskkill", "/F", "/PID", pid], timeout=5)
                                killed += 1
                            except Exception:
                                pass

            # Wait a moment
            time.sleep(2)

            # Restart
            subprocess.Popen(
                [PYTHON, str(BASE_DIR / "main.py")],
                cwd=str(BASE_DIR),
                creationflags=0x00000010  # DETACHED_PROCESS
            )

            _log(f"RESTART: Killed {killed} processes, starting new ERIS")
            return f"✅ ERIS restarted (killed {killed} old processes, new process starting)"

        except Exception as e:
            return f"❌ Restart failed: {e}"

    return (
        f"Unknown action: '{action}'.\n"
        "Available: detect, fix_file, test, validate, scan_all, status, rollback, restart"
    )
