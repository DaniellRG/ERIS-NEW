"""Generate, store, and run code scripts from natural language descriptions."""

import ast
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SCRIPTS_DIR = os.path.join(DATA_DIR, "generated_scripts")
INDEX_FILE = os.path.join(DATA_DIR, "generated_scripts_index.json")

TEMPLATES: dict[str, dict[str, str]] = {
    "python_hello": {
        "language": "python",
        "code": '#!/usr/bin/env python3\nprint("Hello, World!")\n',
    },
    "python_file_ops": {
        "language": "python",
        "code": (
            "import os\nimport shutil\n\n"
            "def list_files(path='.'):\n"
            "    for f in os.listdir(path):\n"
            "        print(f)\n\n"
            "list_files()\n"
        ),
    },
    "python_web_request": {
        "language": "python",
        "code": (
            "import urllib.request\n\n"
            "url = 'https://httpbin.org/get'\n"
            "req = urllib.request.Request(url)\n"
            "with urllib.request.urlopen(req, timeout=10) as resp:\n"
            "    print(resp.read().decode())\n"
        ),
    },
    "powershell_system_info": {
        "language": "powershell",
        "code": (
            "Get-ComputerInfo | Select-Object CsName, WindowsVersion, OsArchitecture, "
            "CsProcessors, CsTotalPhysicalMemory | Format-List\n"
        ),
    },
    "powershell_cleanup": {
        "language": "powershell",
        "code": (
            "# Cleanup temporary files\n"
            "Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue\n"
            "Write-Host 'Temp files cleaned.'\n"
        ),
    },
    "batch_backup": {
        "language": "batch",
        "code": (
            '@echo off\n'
            'set SRC=%USERPROFILE%\\Documents\n'
            'set DEST=%USERPROFILE%\\Backups\\%DATE:~-4%%DATE:~4,2%%DATE:~7,2%\n'
            'if not exist "%DEST%" mkdir "%DEST%"\n'
            'xcopy "%SRC%" "%DEST%" /E /I /H /Y\n'
            'echo Backup complete to %DEST%\n'
        ),
    },
}

CODE_DESCRIPTIONS: dict[str, str] = {
    "list files": 'import os\nfor f in os.listdir("."):\n    print(f)',
    "system info": (
        "import platform, os\n"
        "print(f'System: {platform.system()} {platform.release()}')\n"
        "print(f'Processor: {platform.processor()}')\n"
        "print(f'Python: {platform.python_version()}')\n"
    ),
    "disk usage": (
        "import shutil\n"
        "total, used, free = shutil.disk_usage('/')\n"
        "print(f'Total: {total // (1024**3)} GB')\n"
        "print(f'Used:  {used // (1024**3)} GB')\n"
        "print(f'Free:  {free // (1024**3)} GB')\n"
    ),
    "ping test": (
        "import subprocess, sys\n"
        "target = '8.8.8.8'\n"
        "flag = '-n' if sys.platform == 'win32' else '-c'\n"
        "result = subprocess.run(['ping', flag, '4', target], capture_output=True, text=True)\n"
        "print(result.stdout)\n"
    ),
    "process list": (
        "import os\n"
        "os.system('tasklist' if os.name == 'nt' else 'ps aux')\n"
    ),
    "hello world": 'print("Hello, World!")',
    "fibonacci": (
        "def fib(n):\n"
        "    a, b = 0, 1\n"
        "    for _ in range(n):\n"
        "        a, b = b, a + b\n"
        "    return a\n"
        "\n"
        "for i in range(20):\n"
        "    print(f'fib({i}) = {fib(i)}')\n"
    ),
    "password generator": (
        "import secrets, string\n"
        "length = 16\n"
        "chars = string.ascii_letters + string.digits + string.punctuation\n"
        "pw = ''.join(secrets.choice(chars) for _ in range(length))\n"
        "print(f'Generated password: {pw}')\n"
    ),
    "file search": (
        "import os, sys\n"
        "keyword = sys.argv[1] if len(sys.argv) > 1 else '.py'\n"
        "for root, dirs, files in os.walk('.'):\n"
        "    for f in files:\n"
        "        if keyword in f:\n"
        "            print(os.path.join(root, f))\n"
    ),
}


def _load_index() -> dict[str, Any]:
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"scripts": {}}


def _save_index(data: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _validate_python(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"


def _generate_from_description(description: str, language: str = "python") -> str:
    desc_lower = description.lower().strip()
    for key, code in CODE_DESCRIPTIONS.items():
        if key in desc_lower or desc_lower in key:
            return code
    if "hello" in desc_lower:
        return 'print("Hello, World!")'
    if "list" in desc_lower and "file" in desc_lower:
        return "import os\nfor f in os.listdir('.'):\n    print(f)"
    if "ping" in desc_lower:
        return "import subprocess\nsubprocess.run(['ping', '-n', '4', '8.8.8.8'])"
    if "backup" in desc_lower:
        return "import shutil, os\nsrc = os.path.expanduser('~/Documents')\ndst = os.path.expanduser(f'~/Backup_{os.getpid()}')\nos.makedirs(dst, exist_ok=True)\nfor f in os.listdir(src):\n    try:\n        shutil.copy2(os.path.join(src, f), dst)\n    except Exception:\n        pass\nprint('Done')"
    if "clean" in desc_lower or "temp" in desc_lower:
        return "import os, shutil\ntemp = os.environ.get('TEMP', '/tmp')\nfor f in os.listdir(temp):\n    try:\n        p = os.path.join(temp, f)\n        if os.path.isfile(p):\n            os.remove(p)\n        elif os.path.isdir(p):\n            shutil.rmtree(p)\n    except Exception:\n        pass\nprint('Cleaned')"
    return f'print("TODO: Implement - {description}")'


def code_generator(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list").lower()
    os.makedirs(SCRIPTS_DIR, exist_ok=True)

    if action == "generate":
        description = parameters.get("description", parameters.get("code", ""))
        language = parameters.get("language", "python").lower()
        if not description:
            return "Error: 'description' parameter is required."
        code = _generate_from_description(description, language)
        if language == "python":
            valid, msg = _validate_python(code)
            if not valid:
                return f"Generated code has syntax errors: {msg}\nCode:\n{code}"
        script_id = str(uuid.uuid4())[:8]
        filename = f"{script_id}_{language}.{'py' if language == 'python' else 'ps1' if language == 'powershell' else 'bat'}"
        filepath = os.path.join(SCRIPTS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        index = _load_index()
        index["scripts"][script_id] = {
            "id": script_id,
            "filename": filename,
            "filepath": filepath,
            "language": language,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "run_count": 0,
        }
        _save_index(index)
        return f"Script generated: {filename}\nLanguage: {language}\nDescription: {description}\nCode:\n{code}"

    elif action == "save":
        code = parameters.get("code", "")
        language = parameters.get("language", "python").lower()
        filename = parameters.get("filename", "")
        if not code:
            return "Error: 'code' parameter is required."
        if language == "python":
            valid, msg = _validate_python(code)
            if not valid:
                return f"Syntax error: {msg}"
        if not filename:
            ext = {"python": ".py", "powershell": ".ps1", "batch": ".bat"}.get(language, ".txt")
            script_id = str(uuid.uuid4())[:8]
            filename = f"{script_id}{ext}"
        filepath = os.path.join(SCRIPTS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        index = _load_index()
        script_id = filename.split("_")[0] if "_" in filename else str(uuid.uuid4())[:8]
        index["scripts"][script_id] = {
            "id": script_id,
            "filename": filename,
            "filepath": filepath,
            "language": language,
            "description": parameters.get("description", "user provided"),
            "created_at": datetime.now().isoformat(),
            "run_count": 0,
        }
        _save_index(index)
        return f"Script saved: {filepath}"

    elif action == "run":
        script_id = parameters.get("script_id", "")
        index = _load_index()
        if script_id not in index["scripts"]:
            return f"Script '{script_id}' not found."
        meta = index["scripts"][script_id]
        filepath = meta["filepath"]
        language = meta["language"]
        if not os.path.exists(filepath):
            return f"Script file not found: {filepath}"
        try:
            if language == "python":
                result = subprocess.run(
                    [sys.executable, filepath],
                    capture_output=True, text=True, timeout=30,
                )
            elif language == "powershell":
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", filepath],
                    capture_output=True, text=True, timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
            elif language == "batch":
                result = subprocess.run(
                    filepath, capture_output=True, text=True, timeout=30,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
            else:
                return f"Unsupported language: {language}"
            output = result.stdout[:3000] if result.stdout else result.stderr[:3000]
            meta["run_count"] = meta.get("run_count", 0) + 1
            meta["last_run"] = datetime.now().isoformat()
            _save_index(index)
            return f"Script '{meta['filename']}' executed (exit code: {result.returncode}):\n{output}"
        except subprocess.TimeoutExpired:
            return "Script execution timed out (30s)."
        except Exception as e:
            return f"Error running script: {e}"

    elif action == "list":
        index = _load_index()
        scripts = index.get("scripts", {})
        if not scripts:
            return "No generated scripts."
        lines = []
        for sid, s in scripts.items():
            lines.append(
                f"[{sid}] {s['filename']} | {s['language']} | "
                f"runs: {s.get('run_count', 0)} | {s['description'][:50]}"
            )
        return f"Generated scripts ({len(scripts)}):\n" + "\n".join(lines)

    elif action == "template":
        template_name = parameters.get("name", "")
        if not template_name:
            lines = [f"  {k}: {v['language']}" for k, v in TEMPLATES.items()]
            return f"Available templates:\n" + "\n".join(lines)
        if template_name in TEMPLATES:
            t = TEMPLATES[template_name]
            return f"Template '{template_name}' ({t['language']}):\n{t['code']}"
        matches = [k for k in TEMPLATES if template_name in k]
        if matches:
            t = TEMPLATES[matches[0]]
            return f"Template '{matches[0]}' ({t['language']}):\n{t['code']}"
        return f"Template '{template_name}' not found. Use 'template' with no name to list."

    else:
        return f"Unknown action: '{action}'. Valid: generate, save, run, list, template"
