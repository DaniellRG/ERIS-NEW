"""Changelog generator from git for Eris."""
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

def changelog_generator_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"status": "ready"})
    elif action == "generate":
        path = params.get("path", ".")
        days = params.get("days", 30)
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            r = subprocess.run(
                "git log --since='{}' --pretty=format:'%h|%s|%an|%ad' --date=short".format(since),
                shell=True, capture_output=True, text=True, cwd=path, timeout=15
            )
            if not r.stdout.strip():
                return json.dumps({"note": "No commits found", "path": path})
            lines = r.stdout.strip().split("\n")
            changelog = {}
            for line in lines:
                parts = line.strip("'").split("|", 3)
                if len(parts) >= 3:
                    hash_val, message, author = parts[0], parts[1], parts[2]
                    date = parts[3] if len(parts) > 3 else ""
                    if date not in changelog:
                        changelog[date] = []
                    category = "other"
                    msg_lower = message.lower()
                    if any(w in msg_lower for w in ["feat", "add", "new", "implement"]):
                        category = "features"
                    elif any(w in msg_lower for w in ["fix", "bug", "patch", "resolve"]):
                        category = "fixes"
                    elif any(w in msg_lower for w in ["refactor", "clean", "improve"]):
                        category = "improvements"
                    elif any(w in msg_lower for w in ["doc", "readme", "comment"]):
                        category = "docs"
                    elif any(w in msg_lower for w in ["test", "spec"]):
                        category = "tests"
                    changelog[date].append({"hash": hash_val, "message": message, "author": author, "category": category})
            md = "# Changelog\n\n"
            for date in sorted(changelog.keys(), reverse=True):
                md += "## {} ({})\n\n".format(date, len(changelog[date]))
                for entry in changelog[date]:
                    md += "- `{}` {} ({})\n".format(entry["hash"], entry["message"], entry["author"])
                md += "\n"
            output = params.get("output", "")
            if output:
                Path(output).write_text(md, encoding="utf-8")
            return json.dumps({"changelog": md[:3000], "total_commits": len(lines), "output": output or "inline"})
        except Exception as e:
            return json.dumps({"error": str(e)[:300]})
    elif action == "since_tag":
        tag = params.get("tag", "")
        path = params.get("path", ".")
        if not tag:
            return json.dumps({"error": "Tag required"})
        try:
            r = subprocess.run(
                "git log {}..HEAD --pretty=format:'%h|%s|%an|%ad' --date=short".format(tag),
                shell=True, capture_output=True, text=True, cwd=path, timeout=15
            )
            lines = r.stdout.strip().split("\n") if r.stdout.strip() else []
            commits = []
            for line in lines:
                parts = line.strip("'").split("|", 3)
                if len(parts) >= 2:
                    commits.append({"hash": parts[0], "message": parts[1]})
            return json.dumps({"since": tag, "commits": commits, "count": len(commits)})
        except Exception as e:
            return json.dumps({"error": str(e)[:300]})
    return json.dumps({"error": "Unknown action"})
