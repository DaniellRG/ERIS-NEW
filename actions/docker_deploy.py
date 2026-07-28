"""
actions/docker_deploy.py — Docker deployment for ERIS.
Build, run, manage Docker containers for ERIS.
"""
import json
import os
import subprocess
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_DOCKERFILE = _BASE / "Dockerfile"
_COMPOSE_FILE = _BASE / "docker-compose.yml"

DOCKERFILE_CONTENT = """FROM python:3.12-slim

WORKDIR /eris

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc g++ portaudio19-dev ffmpeg && \\
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080 8765 8888

HEALTHCHECK --interval=30s --timeout=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["python", "main.py"]
"""

COMPOSE_CONTENT = """version: "3.8"

services:
  eris:
    build: .
    container_name: eris
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "8765:8765"
      - "8888:8888"
    volumes:
      - ./data:/eris/data
      - ./config:/eris/config
      - ./plugins:/eris/plugins
    environment:
      - ERIS_ENV=production
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    container_name: eris-ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

volumes:
  ollama_data:
"""


def _run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, shell=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1


def docker_deploy(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "status":
        stdout, stderr, code = _run_cmd("docker ps --filter name=eris --format {{.Names}} {{.Status}}")
        ollama_out, _, _ = _run_cmd("docker ps --filter name=eris-ollama --format {{.Names}} {{.Status}}")
        lines = ["Docker Status:"]
        lines.append(f"  ERIS: {stdout if stdout else 'Not running'}")
        lines.append(f"  Ollama: {ollama_out if ollama_out else 'Not running'}")
        has_dockerfile = _DOCKERFILE.exists()
        has_compose = _COMPOSE_FILE.exists()
        lines.append(f"  Dockerfile: {'exists' if has_dockerfile else 'missing'}")
        lines.append(f"  docker-compose.yml: {'exists' if has_compose else 'missing'}")
        return "\n".join(lines)

    elif action == "init":
        return _init_docker_files()

    elif action == "build":
        if not _DOCKERFILE.exists():
            return "No Dockerfile. Run 'action=init' first."
        stdout, stderr, code = _run_cmd("docker build -t eris:latest .")
        if code == 0:
            return f"Build successful!\n{stdout[-200:] if stdout else 'OK'}"
        return f"Build failed:\n{stderr[-300:] if stderr else 'Unknown error'}"

    elif action == "run":
        detach = params.get("detach", "true")
        flag = "-d" if detach.lower() in ("true", "1", "yes") else ""
        stdout, stderr, code = _run_cmd(f"docker run {flag} --name eris -p 8080:8080 -p 8765:8765 -p 8888:8888 -v {_BASE}/data:/eris/data -v {_BASE}/config:/eris/config eris:latest")
        if code == 0:
            return f"ERIS container started!\n{stdout}"
        return f"Failed to start:\n{stderr[-300:]}"

    elif action == "stop":
        stdout, stderr, code = _run_cmd("docker stop eris")
        if code == 0:
            return "ERIS container stopped."
        return f"Failed: {stderr}"

    elif action == "restart":
        stdout, stderr, code = _run_cmd("docker restart eris")
        if code == 0:
            return "ERIS container restarted."
        return f"Failed: {stderr}"

    elif action == "rm":
        stdout, stderr, code = _run_cmd("docker rm -f eris")
        if code == 0:
            return "ERIS container removed."
        return f"Failed: {stderr}"

    elif action == "logs":
        lines = int(params.get("lines", "50"))
        stdout, stderr, code = _run_cmd(f"docker logs --tail {lines} eris")
        return stdout if stdout else stderr if stderr else "No logs."

    elif action == "compose_up":
        if not _COMPOSE_FILE.exists():
            return "No docker-compose.yml. Run 'action=init' first."
        stdout, stderr, code = _run_cmd("docker compose up -d")
        if code == 0:
            return f"Compose up successful!\n{stdout[-200:]}"
        return f"Failed:\n{stderr[-300:]}"

    elif action == "compose_down":
        stdout, stderr, code = _run_cmd("docker compose down")
        if code == 0:
            return "Compose down."
        return f"Failed: {stderr}"

    elif action == "compose_status":
        stdout, stderr, code = _run_cmd("docker compose ps")
        return stdout if stdout else "No compose services running."

    elif action == "shell":
        stdout, stderr, code = _run_cmd("docker exec -it eris bash -c 'python --version && pip list | wc -l'")
        return stdout if stdout else stderr

    elif action == "pull_ollama":
        stdout, stderr, code = _run_cmd("docker pull ollama/ollama:latest")
        if code == 0:
            return "Ollama image pulled."
        return f"Failed: {stderr[-200:]}"

    elif action == "exec":
        cmd = params.get("cmd", "ls")
        stdout, stderr, code = _run_cmd(f"docker exec eris {cmd}")
        return stdout if stdout else stderr

    return "Actions: status, init, build, run, stop, restart, rm, logs, compose_up, compose_down, compose_status, shell, pull_ollama, exec"


def _init_docker_files():
    created = []
    if not _DOCKERFILE.exists():
        _DOCKERFILE.write_text(DOCKERFILE_CONTENT, encoding="utf-8")
        created.append("Dockerfile")
    if not _COMPOSE_FILE.exists():
        _COMPOSE_FILE.write_text(COMPOSE_CONTENT, encoding="utf-8")
        created.append("docker-compose.yml")

    if created:
        return f"Created: {', '.join(created)}. Now run 'action=build' to build the image."
    return "Dockerfile and docker-compose.yml already exist."
