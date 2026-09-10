"""opencode_bridge.py — Puente Eris ↔ opencode."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from core.platform import safe_print

BASE_DIR = Path(__file__).resolve().parent.parent


def _find_opencode() -> str:
    """Localizar el binario de opencode: env var > PATH > rutas conocidas."""
    env = os.environ.get("OPENCODE_BIN", "").strip()
    if env:
        if os.path.isfile(env):
            return env
        safe_print(f"[OpenCode] OPENCODE_BIN configurado pero no existe: {env}")

    found = shutil.which("opencode")
    if found:
        return found

    if os.name == "nt":
        cand = Path(os.environ.get("APPDATA", Path.home())) / "npm" / "opencode.cmd"
        if cand.is_file():
            return str(cand)
        cand = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / "opencode" / "opencode.exe"
        if cand.is_file():
            return str(cand)

    for p in (
        Path.home() / ".local" / "bin" / "opencode",
        Path.home() / ".local" / "share" / "mise" / "installs" / "opencode" / "latest" / "opencode",
        Path.home() / ".opencode" / "bin" / "opencode",
    ):
        if p.is_file():
            return str(p)
    return ""


OPENCODE_BIN = _find_opencode()
MEMORY_DIR = BASE_DIR / "memory" / "opencode"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_FILE = MEMORY_DIR / "lessons.json"


def _load_memory() -> list[dict]:
    try:
        return json.loads(MEMORY_FILE.read_text("utf-8"))
    except Exception:
        return []


def _save_memory(entries: list[dict]):
    MEMORY_FILE.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), "utf-8"
    )


def _learn(problem: str, solution: str, directory: str = ""):
    entries = _load_memory()
    entries.append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "problem": problem,
        "solution": solution,
        "directory": directory,
    })
    # Keep last 500 lessons
    _save_memory(entries[-500:])


def _format_entries(entries: list[dict], limit: int = 5) -> str:
    if not entries:
        return "No hay lecciones aprendidas aún."
    lines = ["Lecciones aprendidas de opencode:"]
    for e in entries[-limit:]:
        prob = e["problem"][:80]
        sol = e["solution"][:200]
        lines.append(f"- Problema: {prob}")
        lines.append(f"  Solución: {sol}")
        lines.append("")
    return "\n".join(lines)


def _format_lessons(limit: int = 5) -> str:
    return _format_entries(_load_memory(), limit)


def opencode_task(
    description: str,
    directory: str | None = None,
    session_id: str | None = None,
    player=None,
) -> str:
    if not os.path.isfile(OPENCODE_BIN):
        return (
            f"opencode no encontrado en {OPENCODE_BIN}. "
            "Instalalo para usar esta función."
        )

    workdir = directory or str(BASE_DIR)
    if not os.path.isdir(workdir):
        return f"Directorio no encontrado: {workdir}"

    cmd = [
        OPENCODE_BIN, "run", description,
        "--dir", workdir,
        "--dangerously-skip-permissions",
        "--format", "json",
    ]
    if session_id:
        cmd.extend(["--session", session_id])

    if player:
        player.write_log(f"SYS: Delegando a opencode: {description[:80]}…")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            shell=False,
            env={**os.environ, "OPENCODE_SERVER_PORT": "0"},
        )
    except subprocess.TimeoutExpired:
        return "opencode tardó más de 5 minutos y fue cancelado."
    except Exception as e:
        return f"Error ejecutando opencode: {e}"

    output = ""
    if result.stdout:
        output += result.stdout.strip()
    if result.stderr:
        # Extract only meaningful lines
        stderr_lines = [
            l for l in result.stderr.splitlines()
            if "WARN" not in l and "INFO" not in l and "log level" not in l
        ]
        if stderr_lines:
            output += "\n" + "\n".join(stderr_lines[-10:])

    if not output:
        output = f"opencode terminó con código {result.returncode}"

    # Detect "Session not found" and retry without session_id
    if session_id and ("Session not found" in output or "session not found" in output.lower()):
        safe_print(f"[OpenCode] ⚠️ Sesión '{session_id}' no encontrada — reintentando sin --session")
        if player:
            player.write_log("SYS: Sesión no encontrada, creando nueva...")
        cmd_retry = [
            OPENCODE_BIN, "run", description,
            "--dir", workdir,
            "--dangerously-skip-permissions",
            "--format", "json",
        ]
        try:
            result = subprocess.run(
                cmd_retry,
                capture_output=True,
                text=True,
                timeout=300,
                env={**os.environ, "OPENCODE_SERVER_PORT": "0"},
            )
        except Exception:
            pass
        else:
            output = ""
            if result.stdout:
                output += result.stdout.strip()
            if result.stderr:
                stderr_lines = [
                    l for l in result.stderr.splitlines()
                    if "WARN" not in l and "INFO" not in l and "log level" not in l
                ]
                if stderr_lines:
                    output += "\n" + "\n".join(stderr_lines[-10:])
            if not output:
                output = f"opencode terminó con código {result.returncode} (intento sin sesión)"

    # Save to memory (learning)
    _learn(description, output, workdir)

    if player:
        player.write_log(f"SYS: opencode completado (código {result.returncode})")

    return output


def recall_lessons(query: str = "", limit: int = 5) -> str:
    entries = _load_memory()
    if not entries:
        return "No hay lecciones aprendidas aún."

    if query:
        q = query.lower()
        entries = [
            e for e in entries
            if q in e["problem"].lower() or q in e["solution"].lower()
        ]

    return _format_entries(entries, limit)
