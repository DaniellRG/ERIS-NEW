"""Docker management for Eris."""
import json
import subprocess
from pathlib import Path

def _run(cmd: str) -> dict:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return {"ok": r.returncode == 0, "output": r.stdout.strip()[:2000], "error": r.stderr.strip()[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

def docker_manager_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        r = _run("docker info --format '{{.ServerVersion}}'")
        return json.dumps({"installed": r["ok"], "version": r.get("output", ""), "error": r.get("error", "")})
    elif action == "containers":
        r = _run("docker ps -a --format '{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}'")
        containers = []
        for line in r.get("output", "").split("\n"):
            if line.strip():
                parts = line.split("|")
                if len(parts) >= 4:
                    containers.append({"id": parts[0], "name": parts[1], "status": parts[2], "image": parts[3]})
        return json.dumps({"containers": containers, "count": len(containers)})
    elif action == "images":
        r = _run("docker images --format '{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedAt}}'")
        images = []
        for line in r.get("output", "").split("\n"):
            if line.strip():
                parts = line.split("|")
                if len(parts) >= 2:
                    images.append({"name": parts[0], "size": parts[1]})
        return json.dumps({"images": images, "count": len(images)})
    elif action == "logs":
        name = params.get("name", "")
        lines = params.get("lines", "50")
        if not name:
            return json.dumps({"error": "Container name required"})
        r = _run("docker logs {} --tail {}".format(name, lines))
        return json.dumps({"container": name, "logs": r.get("output", "")[:3000]})
    elif action == "compose_up":
        path = params.get("path", ".")
        r = _run("docker compose -f {}/docker-compose.yml up -d".format(path))
        return json.dumps({"status": "started" if r["ok"] else "error", "output": r.get("output", r.get("error", ""))})
    elif action == "compose_down":
        path = params.get("path", ".")
        r = _run("docker compose -f {}/docker-compose.yml down".format(path))
        return json.dumps({"status": "stopped" if r["ok"] else "error", "output": r.get("output", r.get("error", ""))})
    elif action == "build":
        name = params.get("name", "")
        path = params.get("path", ".")
        if not name:
            return json.dumps({"error": "Image name required"})
        r = _run("docker build -t {} {}".format(name, path))
        return json.dumps({"status": "built" if r["ok"] else "error", "output": r.get("output", r.get("error", ""))[:1000]})
    elif action == "run":
        image = params.get("image", "")
        name = params.get("name", "")
        ports = params.get("ports", "")
        if not image:
            return json.dumps({"error": "Image required"})
        cmd = "docker run -d"
        if name:
            cmd += " --name {}".format(name)
        if ports:
            cmd += " -p {}".format(ports)
        cmd += " {}".format(image)
        r = _run(cmd)
        return json.dumps({"status": "running" if r["ok"] else "error", "output": r.get("output", r.get("error", ""))})
    elif action == "stop":
        name = params.get("name", "")
        if not name:
            return json.dumps({"error": "Container name required"})
        r = _run("docker stop {}".format(name))
        return json.dumps({"status": "stopped" if r["ok"] else "error"})
    elif action == "remove":
        name = params.get("name", "")
        if not name:
            return json.dumps({"error": "Container name required"})
        r = _run("docker rm {}".format(name))
        return json.dumps({"status": "removed" if r["ok"] else "error"})
    return json.dumps({"error": "Unknown action"})
