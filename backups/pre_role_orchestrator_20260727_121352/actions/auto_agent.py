"""Multi-step task planner that decomposes complex tasks into executable steps."""

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PLANS_FILE = os.path.join(DATA_DIR, "auto_agent.json")

STEP_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "scan firewall": [
        {"description": "Check Windows Firewall status", "tool_to_use": "shell", "parameters": {"command": "netsh advfirewall show allprofiles"}},
        {"description": "List inbound rules", "tool_to_use": "shell", "parameters": {"command": "netsh advfirewall firewall show rule name=all dir=in | findstr /i \"Rule Name\""}},
    ],
    "check antivirus": [
        {"description": "Check Windows Defender status", "tool_to_use": "shell", "parameters": {"command": "powershell -Command \"Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled, AntivirusEnabled\""}},
    ],
    "backup files": [
        {"description": "Create backup directory", "tool_to_use": "shell", "parameters": {"command": "if not exist \"%USERPROFILE%\\Backups\" mkdir \"%USERPROFILE%\\Backups\""}},
        {"description": "Copy important files to backup", "tool_to_use": "shell", "parameters": {"command": "powershell -Command \"Copy-Item -Path $env:USERPROFILE\\Desktop -Destination $env:USERPROFILE\\Backups\\Desktop_$(Get-Date -Format yyyyMMdd) -Recurse -ErrorAction SilentlyContinue\""}},
    ],
    "create restore point": [
        {"description": "Enable System Restore on C:", "tool_to_use": "shell", "parameters": {"command": "powershell -Command \"Enable-ComputerRestore -Drive 'C:\\' -ErrorAction SilentlyContinue\""}},
        {"description": "Create restore point", "tool_to_use": "shell", "parameters": {"command": "powershell -Command \"Checkpoint-Computer -Description 'AutoAgent Restore Point' -RestorePointType MODIFY_SETTINGS\""}},
    ],
    "clean temp files": [
        {"description": "Remove temp files", "tool_to_use": "shell", "parameters": {"command": "powershell -Command \"Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue\""}},
        {"description": "Clear Windows temp", "tool_to_use": "shell", "parameters": {"command": "del /q /f /s %TEMP%\\* 2>nul"}},
    ],
    "check disk space": [
        {"description": "Show disk usage", "tool_to_use": "shell", "parameters": {"command": "wmic logicaldisk get size,freespace,caption /format:list"}},
    ],
    "optimize performance": [
        {"description": "Clear DNS cache", "tool_to_use": "shell", "parameters": {"command": "ipconfig /flushdns"}},
        {"description": "Defragment C: drive", "tool_to_use": "shell", "parameters": {"command": "defrag C: /O /H"}},
    ],
}


def _load_plans() -> dict[str, Any]:
    if os.path.exists(PLANS_FILE):
        with open(PLANS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"plans": {}, "history": []}


def _save_plans(data: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PLANS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _decompose_task(goal: str) -> list[dict[str, Any]]:
    goal_lower = goal.lower()
    steps: list[dict[str, Any]] = []

    if "protege mi pc" in goal_lower or "protect my pc" in goal_lower:
        tasks_to_add = ["scan firewall", "check antivirus", "backup files", "create restore point"]
    elif "limpiar" in goal_lower or "clean" in goal_lower:
        tasks_to_add = ["clean temp files", "check disk space", "optimize performance"]
    elif "diagnostico" in goal_lower or "diagnos" in goal_lower:
        tasks_to_add = ["check disk space", "scan firewall", "check antivirus"]
    else:
        for template_key, template_steps in STEP_TEMPLATES.items():
            if any(word in goal_lower for word in template_key.split()):
                tasks_to_add = [template_key]
                break
        else:
            tasks_to_add = list(STEP_TEMPLATES.keys())[:3]

    seen = set()
    for task_key in tasks_to_add:
        if task_key in seen:
            continue
        seen.add(task_key)
        template = STEP_TEMPLATES.get(task_key, [])
        for s in template:
            step_id = str(uuid.uuid4())[:8]
            steps.append({
                "id": step_id,
                "description": s["description"],
                "tool_to_use": s.get("tool_to_use", "shell"),
                "parameters": s.get("parameters", {}),
                "status": "pending",
                "result": None,
                "started_at": None,
                "completed_at": None,
            })

    if not steps:
        step_id = str(uuid.uuid4())[:8]
        steps.append({
            "id": step_id,
            "description": f"Execute: {goal}",
            "tool_to_use": "shell",
            "parameters": {"command": f"echo '{goal}'"},
            "status": "pending",
            "result": None,
            "started_at": None,
            "completed_at": None,
        })

    return steps


def _run_step(step: dict[str, Any]) -> dict[str, Any]:
    tool = step.get("tool_to_use", "shell")
    params = step.get("parameters", {})
    result: dict[str, Any] = {"success": False, "output": ""}

    if tool == "shell":
        cmd = params.get("command", "echo no command")
        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            result["success"] = proc.returncode == 0
            result["output"] = proc.stdout[:2000] if proc.stdout else proc.stderr[:2000]
        except subprocess.TimeoutExpired:
            result["output"] = "Command timed out after 60s"
        except Exception as e:
            result["output"] = str(e)
    elif tool == "python":
        code = params.get("code", "print('no code')")
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code], capture_output=True, text=True, timeout=60,
            )
            result["success"] = proc.returncode == 0
            result["output"] = proc.stdout[:2000] if proc.stdout else proc.stderr[:2000]
        except Exception as e:
            result["output"] = str(e)
    else:
        result["output"] = f"Unknown tool: {tool}"

    return result


def auto_agent(parameters: dict, player=None) -> str:
    action = parameters.get("action", "status").lower()
    data = _load_plans()

    if action == "plan":
        goal = parameters.get("goal", parameters.get("description", ""))
        if not goal:
            return "Error: 'goal' parameter is required."
        plan_id = str(uuid.uuid4())[:8]
        steps = _decompose_task(goal)
        plan = {
            "id": plan_id,
            "goal": goal,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "current_step": 0,
            "completed_steps": 0,
            "total_steps": len(steps),
        }
        data["plans"][plan_id] = plan
        _save_plans(data)
        step_list = "\n".join(
            f"  {i+1}. [{s['id']}] {s['description']} ({s['tool_to_use']})"
            for i, s in enumerate(steps)
        )
        return f"Plan '{plan_id}' created for: {goal}\n{len(steps)} steps:\n{step_list}"

    elif action == "execute":
        plan_id = parameters.get("plan_id", "")
        if plan_id not in data["plans"]:
            return f"Plan '{plan_id}' not found."
        plan = data["plans"][plan_id]
        if plan["status"] in ("completed", "cancelled"):
            return f"Plan '{plan_id}' is already {plan['status']}."
        plan["status"] = "running"
        executed = 0
        max_steps = parameters.get("max_steps", len(plan["steps"]))

        for i, step in enumerate(plan["steps"]):
            if step["status"] == "done":
                continue
            if executed >= max_steps:
                break
            step["status"] = "running"
            step["started_at"] = datetime.now().isoformat()
            _save_plans(data)
            result = _run_step(step)
            step["result"] = result
            step["status"] = "done" if result["success"] else "failed"
            step["completed_at"] = datetime.now().isoformat()
            executed += 1
            plan["current_step"] = i + 1
            plan["completed_steps"] = sum(1 for s in plan["steps"] if s["status"] == "done")
            _save_plans(data)

        all_done = all(s["status"] in ("done", "failed") for s in plan["steps"])
        if all_done:
            failed = sum(1 for s in plan["steps"] if s["status"] == "failed")
            plan["status"] = "completed" if failed == 0 else "completed_with_errors"
        _save_plans(data)
        completed = plan["completed_steps"]
        total = plan["total_steps"]
        return f"Plan '{plan_id}' executed {executed} steps. Progress: {completed}/{total}. Status: {plan['status']}"

    elif action == "status":
        plan_id = parameters.get("plan_id", "")
        if plan_id:
            if plan_id not in data["plans"]:
                return f"Plan '{plan_id}' not found."
            p = data["plans"][plan_id]
            lines = [f"Plan: {p['id']} | Goal: {p['goal']} | Status: {p['status']}",
                     f"Progress: {p['completed_steps']}/{p['total_steps']}"]
            for s in p["steps"]:
                icon = {"done": "[x]", "failed": "[!]", "running": "[>]", "pending": "[ ]"}.get(s["status"], "[ ]")
                lines.append(f"  {icon} {s['description']} - {s['status']}")
            return "\n".join(lines)
        active = [p for p in data["plans"].values() if p["status"] in ("running", "pending")]
        if not active:
            return "No active plans."
        lines = []
        for p in active:
            lines.append(f"[{p['id']}] {p['goal']} | {p['status']} | {p['completed_steps']}/{p['total_steps']}")
        return f"Active plans ({len(active)}):\n" + "\n".join(lines)

    elif action == "cancel":
        plan_id = parameters.get("plan_id", "")
        if plan_id not in data["plans"]:
            return f"Plan '{plan_id}' not found."
        data["plans"][plan_id]["status"] = "cancelled"
        _save_plans(data)
        return f"Plan '{plan_id}' cancelled."

    elif action == "history":
        plans = data.get("plans", {})
        completed = {k: v for k, v in plans.items() if v["status"] in ("completed", "completed_with_errors", "cancelled")}
        if not completed:
            return "No plan history."
        lines = []
        for pid, p in completed.items():
            lines.append(f"[{pid}] {p['goal']} | {p['status']} | {p['completed_steps']}/{p['total_steps']} | {p['created_at']}")
        return f"Plan history ({len(completed)}):\n" + "\n".join(lines)

    else:
        return f"Unknown action: '{action}'. Valid: plan, execute, status, cancel, history"
