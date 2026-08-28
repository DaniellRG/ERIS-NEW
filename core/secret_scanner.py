"""Secret scanner for Eris."""
import re
import json
from pathlib import Path

PATTERNS = {
    "aws_key": {"pattern": r"AKIA[0-9A-Z]{16}", "severity": "high", "description": "AWS Access Key"},
    "aws_secret": {"pattern": r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})", "severity": "high", "description": "AWS Secret Key"},
    "github_token": {"pattern": r"gh[pousr]_[A-Za-z0-9_]{36,255}", "severity": "high", "description": "GitHub Token"},
    "private_key": {"pattern": r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----", "severity": "critical", "description": "Private Key"},
    "password_assign": {"pattern": r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"]([^'\"]{6,})", "severity": "high", "description": "Password Assignment"},
    "api_key": {"pattern": r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"]([A-Za-z0-9_\-]{20,})", "severity": "medium", "description": "API Key"},
    "secret_assign": {"pattern": r"(?i)(secret|token)\s*[=:]\s*['\"]([A-Za-z0-9_\-]{20,})", "severity": "medium", "description": "Secret/Token"},
    "database_url": {"pattern": r"(?i)(mysql|postgres|mongodb|redis)://[^\s\"']+", "severity": "high", "description": "Database URL"},
    "email_password": {"pattern": r"(?i)[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}.*password", "severity": "medium", "description": "Email with password"},
}

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env", ".env.example"}
EXCLUDE_FILES = {".env", "requirements.txt", "package-lock.json"}

def secret_scanner_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"patterns": list(PATTERNS.keys()), "count": len(PATTERNS)})
    elif action == "scan":
        path = params.get("path", ".")
        extensions = params.get("extensions", [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".env", ".cfg", ".ini", ".conf", ".toml"])
        max_file_size = params.get("max_size", 1000000)
        findings = []
        scanned = 0
        try:
            for f in Path(path).rglob("*"):
                if f.is_dir():
                    continue
                if f.name in EXCLUDE_FILES:
                    continue
                if any(d in f.parts for d in EXCLUDE_DIRS):
                    continue
                if f.suffix not in extensions:
                    continue
                if f.stat().st_size > max_file_size:
                    continue
                scanned += 1
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    for name, info in PATTERNS.items():
                        for match in re.finditer(info["pattern"], content):
                            line_num = content[:match.start()].count("\n") + 1
                            findings.append({
                                "file": str(f),
                                "line": line_num,
                                "type": name,
                                "severity": info["severity"],
                                "description": info["description"],
                                "match": match.group()[:50] + "..." if len(match.group()) > 50 else match.group(),
                            })
                except Exception:
                    pass
        except Exception as e:
            return json.dumps({"error": str(e)[:300]})
        return json.dumps({"findings": findings, "count": len(findings), "files_scanned": scanned})
    elif action == "scan_file":
        file_path = params.get("file", "")
        if not file_path or not Path(file_path).exists():
            return json.dumps({"error": "File not found"})
        findings = []
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
            for name, info in PATTERNS.items():
                for match in re.finditer(info["pattern"], content):
                    line_num = content[:match.start()].count("\n") + 1
                    findings.append({"file": file_path, "line": line_num, "type": name, "severity": info["severity"], "description": info["description"]})
        except Exception as e:
            return json.dumps({"error": str(e)[:200]})
        return json.dumps({"findings": findings, "count": len(findings), "file": file_path})
    return json.dumps({"error": "Unknown action"})
