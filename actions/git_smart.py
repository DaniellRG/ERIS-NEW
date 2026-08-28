from __future__ import annotations

"""Git Smart — Intelligent git operations with auto-generated commit messages.

Actions
-------
auto_commit – Analyse staged/unstaged changes and commit with a descriptive message.
status      – Concise repo status summary.
diff        – Show diff for the whole repo or a specific file.
log         – Recent commit history.
branches    – List local branches.
stash       – Stash current changes.
prune_merged – Delete branches already merged into the current branch.
"""

import os
import re
import subprocess
from typing import Any


def _run_git(args: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a git command and return ``(returncode, stdout, stderr)``."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, "", "git is not installed or not on PATH."
    except subprocess.TimeoutExpired:
        return -1, "", "Git command timed out."


def _build_commit_message(status_out: str, diff_out: str) -> str:
    """Analyse changes and produce a conventional-commit-style message."""
    added_files: list[str] = []
    modified_files: list[str] = []
    deleted_files: list[str] = []
    renamed_files: list[str] = []
    untracked_files: list[str] = []

    for line in status_out.splitlines():
        if len(line) < 3:
            continue
        index_status = line[0] if len(line) > 0 else " "
        work_status = line[1] if len(line) > 1 else " "
        filename = line[3:].strip() if len(line) > 3 else ""

        if index_status == "A":
            added_files.append(filename)
        elif index_status == "M" or work_status == "M":
            modified_files.append(filename)
        elif index_status == "D" or work_status == "D":
            deleted_files.append(filename)
        elif index_status == "R":
            renamed_files.append(filename)
        elif line.startswith("??"):
            untracked_files.append(filename)

    parts: list[str] = []

    if added_files:
        parts.append(f"feat: add {', '.join(added_files)}")
    if modified_files:
        parts.append(f"refactor: update {', '.join(modified_files)}")
    if deleted_files:
        parts.append(f"chore: remove {', '.join(deleted_files)}")
    if renamed_files:
        parts.append(f"refactor: rename {', '.join(renamed_files)}")
    if untracked_files:
        parts.append(f"feat: introduce {', '.join(untracked_files)}")

    if not parts:
        parts.append("chore: apply minor changes")

    return "\n".join(parts) if len(parts) <= 1 else parts[0]


def git_smart(parameters: dict = None, player=None) -> str:  # noqa: C901
    """Smart git helper with auto-commit messages and common workflows."""
    params = parameters or {}
    action = str(params.get("action", "status")).strip().lower()
    repo_path = str(params.get("repo_path", ".")).strip()
    filename = str(params.get("file", "")).strip()
    count = int(str(params.get("count", 10)).strip() or 10)
    message = str(params.get("message", "")).strip()
    push = str(params.get("push", "false")).strip().lower() == "true"

    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return f"Error: '{repo_path}' is not a git repository."

    if action == "auto_commit":
        rc, status_out, err = _run_git(["status", "--porcelain"], cwd=repo_path)
        if rc != 0:
            return f"Error getting status: {err}"
        if not status_out:
            return "Nothing to commit — working tree clean."

        _run_git(["add", "-A"], cwd=repo_path)

        rc2, diff_out, _ = _run_git(["diff", "--cached"], cwd=repo_path)
        commit_msg = message or _build_commit_message(status_out, diff_out)

        rc3, out, err3 = _run_git(["commit", "-m", commit_msg], cwd=repo_path)
        if rc3 != 0:
            return f"Commit failed: {err3}"

        result = f"Committed with message:\n  {commit_msg}"
        if push:
            rc4, push_out, push_err = _run_git(["push"], cwd=repo_path)
            if rc4 == 0:
                result += "\nPushed to remote."
            else:
                result += f"\nPush failed: {push_err}"
        return result

    if action == "status":
        rc, out, err = _run_git(["status", "-sb"], cwd=repo_path)
        return out if rc == 0 else f"Error: {err}"

    if action == "diff":
        args = ["diff"]
        if filename:
            args.extend(["--", filename])
        rc, out, err = _run_git(args, cwd=repo_path)
        return out if out else (err if rc != 0 else "No changes.")

    if action == "log":
        rc, out, err = _run_git(["log", f"--oneline", f"-{count}"], cwd=repo_path)
        return out if rc == 0 else f"Error: {err}"

    if action == "branches":
        rc, out, err = _run_git(["branch"], cwd=repo_path)
        return out if rc == 0 else f"Error: {err}"

    if action == "stash":
        args = ["stash"]
        if message:
            args.extend(["push", "-m", message])
        else:
            args.append("push")
        rc, out, err = _run_git(args, cwd=repo_path)
        return out if rc == 0 else f"Error: {err}"

    if action == "prune_merged":
        rc1, current, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        if rc1 != 0:
            return "Error: Could not determine current branch."
        rc2, merged, err2 = _run_git(
            ["branch", "--merged", current, "--no-color"], cwd=repo_path
        )
        if rc2 != 0:
            return f"Error: {err2}"
        branches = [
            b.strip().lstrip("* ")
            for b in merged.splitlines()
            if b.strip() and b.strip().lstrip("* ") not in ("main", "master", current)
        ]
        if not branches:
            return "No merged branches to prune."
        deleted: list[str] = []
        for branch in branches:
            rc3, _, err3 = _run_git(["branch", "-d", branch], cwd=repo_path)
            if rc3 == 0:
                deleted.append(branch)
        return f"Deleted merged branches: {', '.join(deleted)}." if deleted else "No branches could be deleted."

    return f"Error: Unknown action '{action}'."
