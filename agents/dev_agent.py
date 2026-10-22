"""
agents/dev_agent.py — ERIS Development Specialized Agent.
Handles code help, git, codebase analysis, knowledge base, dev tasks.
"""
from __future__ import annotations

import time
import unicodedata
from typing import Optional

def _norm(s):
    """Normalize text: remove accents, lowercase."""
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower()

def handle_dev(text: str, player=None, **kwargs) -> str:
    """Handle development-related requests."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()

    text_lower = text.lower()
    text_norm = _norm(text_lower)

    try:
        # File creation / project creation
        # FIX 2026-10-21: sin paths Windows hardcodeados (D:\PruebaEris creaba
        # basura con nombre inválido en Linux) y SIN declarar "Listo" sin
        # verificar el archivo real en disco. Solo se escribe si el pedido trae
        # ruta absoluta explícita; si falta, se pide en vez de inventarla.
        file_kw = ["crear archivo", "escribir archivo", "create file", "write file",
                     "main.py", "requirements", "readme", "script", "downloader",
                     "hacer un programa", "make a", "build", "crear python",
                     "instalar dependencias", "pip install", "archivo", "hello.py"]
        if any(_norm(kw) in text_norm for kw in file_kw):
            import os
            import re
            from core.file_api import write_file as _wf

            def _explicit_dir():
                """Ruta absoluta explícita en el pedido (Linux /… o Windows
                C:\\…). None si no hay: nunca se inventa una ubicación."""
                m = re.search(
                    r'((?:[A-Za-z]:\\|(?<![\w:/])/)[\w.\-~/]+(?:/[\w.\-~]+)+)',
                    text)
                if not m:
                    return None
                cand = m.group(1).strip().rstrip('/.,;:')
                if cand.startswith('//') or len(cand) < 2:
                    return None
                return cand

            def _verify_on_disk(fpath):
                """Reporte basado en el disco real, no en la intención."""
                if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
                    return (f"Listo: {fpath} escrito y verificado en disco "
                            f"({os.path.getsize(fpath)} bytes).")
                return (f"⚠️ {fpath} NO quedó escrito. No declares la tarea "
                        f"hecha: revisá la ruta y los permisos.")

            _fname_match = re.search(r'(\w+\.\w+)', text)
            _fname = _fname_match.group(1) if _fname_match else None
            _target_dir = _explicit_dir()

            if "downloader" in text_lower and "youtube" in text_lower:
                # Proyecto downloader — requiere ruta explícita del usuario
                if not _target_dir:
                    result = ("Para armar el proyecto downloader necesito la ruta "
                              "absoluta exacta (ej: /home/soul/Documents/PYTHON/"
                              "downloader). No invento ubicaciones.")
                else:
                    os.makedirs(_target_dir, exist_ok=True)

                    main_py = '''"""
YouTube Downloader - Created by ERIS
Usage: python main.py <youtube_url>
"""
import shutil
import subprocess
import sys
import os

YT_DLP = shutil.which("yt-dlp") or "yt-dlp"

def download(url: str, output_dir: str = "."):
    """Download a YouTube video in best quality."""
    cmd = [
        YT_DLP,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", os.path.join(output_dir, "%(title)s.%(ext)s"),
        url
    ]

    print(f"Downloading: {url}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("Download complete!")
        return True
    else:
        print(f"Error: {result.stderr}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <youtube_url>")
        sys.exit(1)
    download(sys.argv[1])
'''

                    requirements = "yt-dlp>=2024.1.1\n"

                    readme = """# YouTube Downloader

Simple YouTube video downloader using yt-dlp.

## Usage

```bash
python main.py <youtube_url>
```

## Requirements

- Python 3.8+
- yt-dlp (installed via requirements.txt)

## Installation

```bash
pip install -r requirements.txt
```
"""

                    _written = []
                    for _fn, _ct in (("main.py", main_py),
                                     ("requirements.txt", requirements),
                                     ("README.md", readme)):
                        _fp = os.path.join(_target_dir, _fn)
                        _wf(_fp, _ct)
                        _written.append(
                            f"- {_fn}: "
                            f"{'OK' if os.path.isfile(_fp) else 'FALLÓ'}")
                    result = (f"Proyecto downloader en {_target_dir} "
                              f"(archivos verificados en disco):\n"
                              + "\n".join(_written))

            elif not _fname:
                result = "¿Qué archivo necesitás que cree? Decime nombre y contenido."
            elif not _target_dir:
                result = (f"Para crear {_fname} necesito la ruta absoluta exacta "
                          f"(ej: /home/soul/Documents/archivo/{_fname}). "
                          "No invento ubicaciones.")
            else:
                os.makedirs(_target_dir, exist_ok=True)
                fpath = os.path.join(_target_dir, _fname)
                # Detect content hints
                if "print" in text_norm and "hola" in text_norm:
                    content = 'print("Hola Mundo")\n'
                elif "print" in text_norm:
                    # Extract what to print
                    print_match = re.search(r'print\s*\(\s*["\'](.+?)["\']', text)
                    if print_match:
                        content = f'print("{print_match.group(1)}")\n'
                    else:
                        content = 'print("Hello World")\n'
                else:
                    content = f'# {_fname} - Created by ERIS\n'

                _wf(fpath, content)
                result = _verify_on_disk(fpath)

        # Code helper
        elif any(kw in text_lower for kw in ["codigo", "code", "funcion", "function", "clase", "class", "programar"]):
            from actions.code_helper import code_helper
            result = code_helper(parameters={"action": "help"}, player=player)

        # Git
        elif any(kw in text_lower for kw in ["git", "commit", "push", "pull", "branch", "repo", "repositorio"]):
            try:
                from actions.git_control import git_control
                if "status" in text_lower or "estado" in text_lower:
                    result = git_control(parameters={"action": "status"}, player=player)
                elif "commit" in text_lower:
                    result = git_control(parameters={"action": "commit"}, player=player)
                elif "push" in text_lower:
                    result = git_control(parameters={"action": "push"}, player=player)
                elif "pull" in text_lower:
                    result = git_control(parameters={"action": "pull"}, player=player)
                else:
                    result = git_control(parameters={"action": "status"}, player=player)
            except Exception:
                result = "El control de Git no está disponible en este momento."

        elif any(kw in text_lower for kw in ["codebase", "analizar codigo", "estructura del proyecto"]):
            try:
                from actions.codebase import codebase
                result = codebase(parameters={"action": "analyze"}, player=player)
            except Exception:
                result = "El análisis de codebase no está disponible en este momento."

        elif any(kw in text_lower for kw in ["tarea de desarrollo", "dev task", "agent task"]):
            try:
                from actions.agent_task import agent_task
                result = agent_task(parameters={"action": "run"}, player=player)
            except Exception:
                result = "El agente de tareas no está disponible en este momento."

        else:
            result = (
                "Puedo ayudarte con desarrollo:\n"
                "- 'Crear archivo X' → Creo archivos de código\n"
                "- 'Hacer un downloader/scraper/bot' → Creo el proyecto completo\n"
                "- 'Ayuda con codigo' → Asistencia de programación\n"
                "- 'Git status' → Estado del repositorio\n"
                "- 'Git commit/push/pull' → Operaciones de Git\n"
                "- 'Analiza codebase' → Análisis del proyecto"
            )

        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("dev_agent", text, result, elapsed)
        return result

    except Exception as e:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("dev_agent", text, "", elapsed, success=False, error=str(e))
        return f"Error en DevAgent: {e}"
