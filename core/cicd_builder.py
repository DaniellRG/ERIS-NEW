"""CI/CD pipeline builder for Eris."""
import json
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent

TEMPLATES = {
    "github_actions_python": {
        "name": "Python CI/CD",
        "file": ".github/workflows/ci.yml",
        "content": """name: Python CI/CD
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ --cov=src
      - run: python -m flake8 src/
"""
    },
    "github_actions_node": {
        "name": "Node.js CI/CD",
        "file": ".github/workflows/ci.yml",
        "content": """name: Node.js CI/CD
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test
      - run: npm run build
"""
    },
    "github_actions_docker": {
        "name": "Docker CI/CD",
        "file": ".github/workflows/docker.yml",
        "content": """name: Docker Build & Push
on: push
jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: user/app:latest
"""
    },
}

def cicd_builder_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"templates": list(TEMPLATES.keys()), "count": len(TEMPLATES)})
    elif action == "list":
        templates = [{"id": k, "name": v["name"], "file": v["file"]} for k, v in TEMPLATES.items()]
        return json.dumps({"templates": templates})
    elif action == "preview":
        template_id = params.get("template", "")
        if template_id not in TEMPLATES:
            return json.dumps({"error": "Template not found", "available": list(TEMPLATES.keys())})
        t = TEMPLATES[template_id]
        return json.dumps({"template": t["name"], "file": t["file"], "content": t["content"]})
    elif action == "generate":
        template_id = params.get("template", "")
        output_dir = params.get("output_dir", ".")
        if template_id not in TEMPLATES:
            return json.dumps({"error": "Template not found"})
        t = TEMPLATES[template_id]
        out = Path(output_dir) / t["file"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(t["content"], encoding="utf-8")
        return json.dumps({"status": "generated", "file": str(out), "template": t["name"]})
    elif action == "custom":
        name = params.get("name", "custom")
        content = params.get("content", "")
        output_dir = params.get("output_dir", ".")
        if not content:
            return json.dumps({"error": "Content required"})
        out = Path(output_dir) / ".github" / "workflows" / "{}.yml".format(name)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return json.dumps({"status": "generated", "file": str(out)})
    return json.dumps({"error": "Unknown action"})
