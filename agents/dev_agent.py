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
        file_kw = ["crear archivo", "escribir archivo", "create file", "write file",
                     "main.py", "requirements", "readme", "script", "downloader",
                     "hacer un programa", "make a", "build", "crear python",
                     "instalar dependencias", "pip install", "archivo", "hello.py"]
        if any(_norm(kw) in text_norm for kw in file_kw):
            from core.file_api import file_api, write_file, create_dir
            import os

            result_lines = []

            # Detect if user wants a specific project structure
            if "downloader" in text_lower and "youtube" in text_lower:
                # Create YouTube downloader project
                project_dir = "D:\\PruebaEris"
                os.makedirs(project_dir, exist_ok=True)

                main_py = '''"""
YouTube Downloader - Created by ERIS
Usage: python main.py <youtube_url>
"""
import subprocess
import sys
import os

YT_DLP = r"D:\\Eris_Source\\.venv\\Scripts\\yt-dlp.exe"

def download(url: str, output_dir: str = "."):
    """Download a YouTube video in best quality."""
    if not os.path.exists(YT_DLP):
        print("Error: yt-dlp not found at", YT_DLP)
        return False
    
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

                write_file(os.path.join(project_dir, "main.py"), main_py)
                write_file(os.path.join(project_dir, "requirements.txt"), requirements)
                write_file(os.path.join(project_dir, "README.md"), readme)

                result = f"Proyecto YouTube Downloader creado en {project_dir}:\n- main.py (descargador)\n- requirements.txt\n- README.md"

            else:
                # Generic file creation — detect filename and content from request
                import re
                from core.file_api import write_file as _wf, create_dir as _cd

                # Extract filename from text
                fname_match = re.search(r'(\w+\.\w+)', text)
                fname = fname_match.group(1) if fname_match else None

                # Extract target directory
                dir_match = re.search(r'([A-Z]:\\[^\s"]+|D:\\\w+)', text)
                target_dir = dir_match.group(1) if dir_match else "D:\\PruebaEris"
                os.makedirs(target_dir, exist_ok=True)

                if fname:
                    fpath = os.path.join(target_dir, fname)
                    # Detect content hints
                    content = ""
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
                        content = f'# {fname} - Created by ERIS\n'

                    _wf(fpath, content)
                    result = f"Listo, {fname} creado en {target_dir}"
                else:
                    result = "¿Qué archivo necesitás que cree? Nombre y contenido."

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
