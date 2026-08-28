from __future__ import annotations

"""SSH Remote — Execute commands and transfer files over SSH via paramiko.

Actions
-------
connect      – Open an SSH session to a remote host.
exec         – Run a command on the active connection.
upload       – Upload a local file to the remote host.
download     – Download a remote file to the local system.
disconnect   – Close a specific session or all sessions.
list_sessions – Show currently active SSH sessions.
"""

import os
from typing import Any

try:
    import paramiko
except ImportError:
    paramiko = None  # type: ignore[assignment,misc]

_sessions: dict[str, paramiko.SSHClient] = {}


def _fmt_exc(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def ssh_remote(parameters: dict = None, player=None) -> str:  # noqa: C901
    """Manage SSH sessions, execute commands, and transfer files."""
    if paramiko is None:
        return "Error: paramiko is not installed. Run: pip install paramiko"

    params = parameters or {}
    action = str(params.get("action", "list_sessions")).strip().lower()
    host = str(params.get("host", "")).strip()
    port = int(str(params.get("port", 22)).strip() or 22)
    username = str(params.get("username", "")).strip()
    password_or_key_path = str(params.get("password_or_key_path", "")).strip()
    key_path = str(params.get("key_path", "")).strip()
    command = str(params.get("command", "")).strip()
    local_path = str(params.get("local_path", "")).strip()
    remote_path = str(params.get("remote_path", "")).strip()

    if action == "connect":
        if not host:
            return "Error: No host provided."
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            connect_kwargs: dict[str, Any] = {"hostname": host, "port": port}
            if username:
                connect_kwargs["username"] = username
            if key_path and os.path.isfile(key_path):
                connect_kwargs["key_filename"] = key_path
            elif password_or_key_path:
                connect_kwargs["password"] = password_or_key_path
            client.connect(**connect_kwargs)
            _sessions[host] = client
            return f"Connected to {host}:{port}."
        except Exception as exc:
            return f"Connection error: {_fmt_exc(exc)}"

    if action == "exec":
        if not host:
            return "Error: No host specified."
        if host not in _sessions:
            return f"Error: No active session for '{host}'. Use 'connect' first."
        if not command:
            return "Error: No command provided."
        try:
            _, stdout, stderr = _sessions[host].exec_command(command, timeout=30)
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
            parts: list[str] = []
            if out:
                parts.append(f"STDOUT:\n{out}")
            if err:
                parts.append(f"STDERR:\n{err}")
            return "\n".join(parts) if parts else "(no output)"
        except Exception as exc:
            return f"Exec error: {_fmt_exc(exc)}"

    if action == "upload":
        if not host or host not in _sessions:
            return f"Error: No active session for '{host}'."
        if not local_path or not remote_path:
            return "Error: Both local_path and remote_path required."
        if not os.path.isfile(local_path):
            return f"Error: Local file '{local_path}' not found."
        try:
            sftp = _sessions[host].open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            return f"Uploaded '{local_path}' → '{remote_path}'."
        except Exception as exc:
            return f"Upload error: {_fmt_exc(exc)}"

    if action == "download":
        if not host or host not in _sessions:
            return f"Error: No active session for '{host}'."
        if not remote_path or not local_path:
            return "Error: Both remote_path and local_path required."
        try:
            sftp = _sessions[host].open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            return f"Downloaded '{remote_path}' → '{local_path}'."
        except Exception as exc:
            return f"Download error: {_fmt_exc(exc)}"

    if action == "disconnect":
        target = host if host else None
        closed: list[str] = []
        if target and target in _sessions:
            _sessions[target].close()
            del _sessions[target]
            closed.append(target)
        elif target:
            return f"Error: No session for '{target}'."
        else:
            for h in list(_sessions):
                _sessions[h].close()
                del _sessions[h]
                closed.append(h)
        return f"Disconnected: {', '.join(closed)}." if closed else "No sessions to close."

    if action == "list_sessions":
        if not _sessions:
            return "No active sessions."
        lines = [f"  • {h}" for h in _sessions]
        return f"Active sessions ({len(_sessions)}):\n" + "\n".join(lines)

    return f"Error: Unknown action '{action}'."
