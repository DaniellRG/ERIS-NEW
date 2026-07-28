"""
actions/code_review.py — Automated code review for ERIS.
Detects issues, suggests improvements, checks style and security.
"""
import ast
import json
import os
import re
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_HISTORY_FILE = _BASE / "data" / "code_review_history.json"

SECURITY_PATTERNS = [
    (r"eval\s*\(", "HIGH", "Use of eval() — potential code injection"),
    (r"exec\s*\(", "HIGH", "Use of exec() — potential code injection"),
    (r"os\.system\s*\(", "MEDIUM", "os.system() — prefer subprocess"),
    (r"subprocess\.call.*shell=True", "HIGH", "Shell injection risk with shell=True"),
    (r"pickle\.loads?\s*\(", "MEDIUM", "Pickle deserialization — security risk"),
    (r"yaml\.load\s*\((?!.*Loader)", "MEDIUM", "yaml.load without Loader — use safe_load"),
    (r"password\s*=\s*['\"]", "HIGH", "Hardcoded password detected"),
    (r"api_key\s*=\s*['\"]", "HIGH", "Hardcoded API key detected"),
    (r"secret\s*=\s*['\"]", "HIGH", "Hardcoded secret detected"),
    (r"SELECT.*FROM.*WHERE.*=.*\+", "MEDIUM", "Possible SQL injection"),
    (r"requests\.get\s*\(.*verify\s*=\s*False", "MEDIUM", "SSL verification disabled"),
]

STYLE_ISSUES = [
    (r"def\s+\w+\s*\(.*\)\s*->.*:\s*$", "INFO", "Function has type hints (good)"),
    (r"print\s*\(", "INFO", "Debug print() — consider using logging"),
    (r"except\s*:", "WARNING", "Bare except — use specific exception types"),
    (r"except\s+Exception\s*:", "WARNING", "Catching generic Exception"),
    (r"TODO|FIXME|HACK|XXX", "INFO", "TODO/FIXME comment found"),
    (r"import\s+\*", "WARNING", "Wildcard import — prefer explicit imports"),
    (r"len\(\w+\)\s*==\s*0", "INFO", "Use 'not x' instead of 'len(x) == 0'"),
    (r"len\(\w+\)\s*!=\s*0", "INFO", "Use 'x' instead of 'len(x) != 0'"),
    (r"len\(\w+\)\s*>\s*0", "INFO", "Use 'x' instead of 'len(x) > 0'"),
]

COMPLEXITY_ISSUES = [
    (r"if.*elif.*elif.*elif.*elif", "WARNING", "Many elif branches — consider refactoring"),
    (r"try:.*except.*try:.*except", "WARNING", "Nested try/except — consider simplifying"),
]


def _load_history():
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"reviews": []}

def _save_history(data):
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def code_review(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "review").lower()

    if action == "review":
        path = params.get("path", "")
        if not path:
            return "Requires 'path' of file or directory."
        p = Path(path)
        if not p.exists():
            return f"Path not found: {path}"
        if p.is_file():
            return _review_file(p)
        elif p.is_dir():
            return _review_directory(p)

    elif action == "security":
        path = params.get("path", "")
        if not path:
            return "Requires 'path'."
        p = Path(path)
        if not p.exists():
            return f"Path not found: {path}"
        return _security_scan(p)

    elif action == "style":
        path = params.get("path", "")
        if not path:
            return "Requires 'path'."
        p = Path(path)
        if not p.exists():
            return f"Path not found: {path}"
        return _style_check(p)

    elif action == "history":
        data = _load_history()
        reviews = data.get("reviews", [])
        if not reviews:
            return "No review history."
        lines = [f"Review History ({len(reviews)}):"]
        for r in reviews[-10:]:
            lines.append(f"  [{r['timestamp'][:16]}] {r['path']} — {r['issues']} issues")
        return "\n".join(lines)

    elif action == "stats":
        data = _load_history()
        reviews = data.get("reviews", [])
        total_issues = sum(r.get("issues", 0) for r in reviews)
        high = sum(r.get("high", 0) for r in reviews)
        medium = sum(r.get("medium", 0) for r in reviews)
        return (
            f"Code Review Stats:\n"
            f"  Total reviews: {len(reviews)}\n"
            f"  Total issues found: {total_issues}\n"
            f"  HIGH: {high}\n"
            f"  MEDIUM: {medium}\n"
            f"  Last review: {reviews[-1]['timestamp'][:16] if reviews else 'never'}"
        )

    elif action == "quick":
        path = params.get("path", "")
        if not path:
            return "Requires 'path'."
        p = Path(path)
        if not p.exists():
            return f"Path not found: {path}"
        return _quick_review(p)

    return "Actions: review, security, style, history, stats, quick"


def _review_file(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error reading {path}: {e}"

    lines = content.split("\n")
    issues = []

    for i, line in enumerate(lines, 1):
        for pattern, severity, msg in SECURITY_PATTERNS:
            if re.search(pattern, line):
                issues.append((severity, i, msg, line.strip()[:60]))

        for pattern, severity, msg in STYLE_ISSUES:
            if re.search(pattern, line):
                issues.append((severity, i, msg, line.strip()[:60]))

    for pattern, severity, msg in COMPLEXITY_ISSUES:
        full_text = "\n".join(lines)
        if re.search(pattern, full_text):
            issues.append((severity, 0, msg, ""))

    try:
        tree = ast.parse(content)
        func_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
        class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        import_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))
    except SyntaxError:
        func_count = class_count = import_count = 0
        issues.append(("HIGH", 0, "Syntax error — file may not parse", ""))

    high = sum(1 for s, _, _, _ in issues if s == "HIGH")
    medium = sum(1 for s, _, _, _ in issues if s == "MEDIUM")
    warning = sum(1 for s, _, _, _ in issues if s == "WARNING")

    result = [
        f"Code Review: {path.name}",
        f"  Lines: {len(lines)} | Functions: {func_count} | Classes: {class_count} | Imports: {import_count}",
        f"  Issues: {len(issues)} (HIGH: {high}, MEDIUM: {medium}, WARNING: {warning})",
        "",
    ]

    if issues:
        issues.sort(key=lambda x: {"HIGH": 0, "MEDIUM": 1, "WARNING": 2, "INFO": 3}.get(x[0], 4))
        for sev, line_num, msg, ctx in issues[:20]:
            line_ref = f"L{line_num}" if line_num else "---"
            result.append(f"  [{sev}] {line_ref}: {msg}")
            if ctx:
                result.append(f"         {ctx}")
    else:
        result.append("  No issues found! Clean code.")

    _record_review(path, len(issues), high, medium)
    return "\n".join(result)


def _review_directory(path: Path) -> str:
    py_files = list(path.rglob("*.py"))
    if not py_files:
        return f"No .py files in {path}"

    total_issues = 0
    high_count = 0
    file_results = []

    for f in py_files[:50]:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            issues = 0
            high = 0
            for line in content.split("\n"):
                for pattern, severity, _ in SECURITY_PATTERNS:
                    if re.search(pattern, line):
                        issues += 1
                        if severity == "HIGH":
                            high += 1
                for pattern, severity, _ in STYLE_ISSUES:
                    if re.search(pattern, line):
                        issues += 1
            total_issues += issues
            high_count += high
            file_results.append((f.name, issues, high))
        except Exception:
            pass

    lines = [
        f"Directory Review: {path.name} ({len(py_files)} .py files)",
        f"  Total issues: {total_issues} (HIGH: {high_count})",
        "",
    ]

    file_results.sort(key=lambda x: x[1], reverse=True)
    for name, issues, high in file_results[:15]:
        marker = " ⚠️" if high > 0 else ""
        lines.append(f"  {name}: {issues} issues{marker}")

    return "\n".join(lines)


def _security_scan(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    except Exception as e:
        return f"Error: {e}"

    findings = []
    lines = content.split("\n") if content else []

    if path.is_file():
        for i, line in enumerate(lines, 1):
            for pattern, severity, msg in SECURITY_PATTERNS:
                if re.search(pattern, line):
                    findings.append((severity, path.name, i, msg, line.strip()[:60]))
    elif path.is_dir():
        for f in path.rglob("*.py"):
            try:
                fc = f.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(fc.split("\n"), 1):
                    for pattern, severity, msg in SECURITY_PATTERNS:
                        if re.search(pattern, line):
                            findings.append((severity, f.name, i, msg, line.strip()[:60]))
            except Exception:
                pass

    if not findings:
        return f"Security scan: No issues found in {path.name}"

    findings.sort(key=lambda x: {"HIGH": 0, "MEDIUM": 1}.get(x[0], 2))
    result = [f"Security Scan: {path.name} — {len(findings)} findings", ""]
    for sev, fname, line_num, msg, ctx in findings[:20]:
        result.append(f"  [{sev}] {fname}:{line_num}: {msg}")
        if ctx:
            result.append(f"         {ctx}")
    return "\n".join(result)


def _style_check(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    except Exception as e:
        return f"Error: {e}"

    findings = []
    lines = content.split("\n") if content else []

    for i, line in enumerate(lines, 1):
        for pattern, severity, msg in STYLE_ISSUES:
            if re.search(pattern, line):
                findings.append((i, msg, line.strip()[:60]))

    if not findings:
        return f"Style check: No issues found in {path.name}"

    result = [f"Style Check: {path.name} — {len(findings)} findings", ""]
    for line_num, msg, ctx in findings[:20]:
        result.append(f"  L{line_num}: {msg}")
        if ctx:
            result.append(f"       {ctx}")
    return "\n".join(result)


def _quick_review(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    except Exception as e:
        return f"Error: {e}"

    lines = content.split("\n") if content else []
    sec = sum(1 for line in lines for p, s, _ in SECURITY_PATTERNS if s in ("HIGH", "MEDIUM") and re.search(p, line))
    sty = sum(1 for line in lines for p, _, _ in STYLE_ISSUES if re.search(p, line))

    grade = "A" if sec == 0 and sty < 3 else "B" if sec == 0 else "C" if sec < 3 else "D"
    return f"Quick Review: {path.name} — {len(lines)} lines | Security: {sec} | Style: {sty} | Grade: {grade}"


def _record_review(path, issues, high, medium):
    data = _load_history()
    data["reviews"].append({
        "path": str(path),
        "timestamp": datetime.now().isoformat(),
        "issues": issues,
        "high": high,
        "medium": medium,
    })
    data["reviews"] = data["reviews"][-100:]
    _save_history(data)
