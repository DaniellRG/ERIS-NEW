"""
core/lsp_manager.py — Lightweight LSP client for ERIS.

Auto-detects project type, starts appropriate language server,
and provides diagnostics, completions, hover, and go-to-definition.

No heavy dependencies — communicates via JSON-RPC over stdio.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

# ── Language server configurations ──
LSP_SERVERS: dict[str, dict[str, Any]] = {
    "python": {
        "command": "pylsp",
        "args": ["--check-parent-process"],
        "language": "python",
        "extensions": [".py"],
    },
    "typescript": {
        "command": "typescript-language-server",
        "args": ["--stdio"],
        "language": "typescript",
        "extensions": [".ts", ".tsx", ".js", ".jsx"],
    },
    "json": {
        "command": "vscode-json-languageserver",
        "args": ["--stdio"],
        "language": "json",
        "extensions": [".json", ".jsonc"],
    },
    "css": {
        "command": "vscode-css-languageserver",
        "args": ["--stdio"],
        "language": "css",
        "extensions": [".css", ".scss", ".less"],
    },
    "html": {
        "command": "vscode-html-languageserver",
        "args": ["--stdio"],
        "language": "html",
        "extensions": [".html", ".htm"],
    },
    "yaml": {
        "command": "yaml-language-server",
        "args": ["--stdio"],
        "language": "yaml",
        "extensions": [".yaml", ".yml"],
    },
    "markdown": {
        "command": "marksman",
        "args": [],
        "language": "markdown",
        "extensions": [".md", ".mdx"],
    },
}

# ── Global state ──
_active_servers: dict[str, _LSPConnection] = {}
_lock = threading.Lock()


class _LSPConnection:
    """Manages a single LSP server connection via JSON-RPC over stdio."""

    def __init__(self, server_id: str, config: dict, root_uri: str):
        self.server_id = server_id
        self.config = config
        self.root_uri = root_uri
        self._process: subprocess.Popen | None = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._initialized = False
        self._responses: dict[int, Any] = {}
        self._notifications: list[dict] = []
        self._reader_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> bool:
        """Start the language server process."""
        try:
            cmd = self.config["command"]
            args = self.config.get("args", [])
            self._process = subprocess.Popen(
                [cmd] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                bufsize=0,
            )
            self._stop_event.clear()
            self._reader_thread = threading.Thread(
                target=self._read_loop, daemon=True, name=f"lsp-{self.server_id}"
            )
            self._reader_thread.start()

            # Send initialize
            init_params = {
                "processId": os.getpid(),
                "rootUri": self.root_uri,
                "capabilities": {
                    "textDocument": {
                        "completion": {"completionItem": {"snippetSupport": True}},
                        "hover": {"contentFormat": ["markdown", "plaintext"]},
                        "publishDiagnostics": {},
                        "definition": {},
                        "references": {},
                        "synchronization": {"didSave": True},
                    }
                },
            }
            resp = self._send_request("initialize", init_params)
            if resp is not None:
                self._send_notification("initialized", {})
                self._initialized = True
                return True
            return False
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def _read_loop(self):
        """Background thread that reads JSON-RPC messages from stdout."""
        try:
            while not self._stop_event.is_set():
                # Read Content-Length header
                header = self._read_line()
                if not header:
                    break
                content_length = 0
                while header.strip():
                    if header.lower().startswith("content-length:"):
                        content_length = int(header.split(":", 1)[1].strip())
                    header = self._read_line()
                    if not header:
                        break

                if content_length <= 0:
                    continue

                body = self._process.stdout.read(content_length)
                if not body:
                    break

                msg = json.loads(body.decode("utf-8"))
                msg_id = msg.get("id")
                if msg_id is not None and msg_id in self._responses:
                    self._responses[msg_id] = msg
                elif "method" in msg:
                    self._notifications.append(msg)
        except Exception:
            pass

    def _read_line(self) -> str | None:
        """Read a single line from stdout."""
        try:
            line = b""
            while True:
                ch = self._process.stdout.read(1)
                if not ch:
                    return None
                if ch == b"\n":
                    return line.decode("utf-8", errors="replace")
                line += ch
        except Exception:
            return None

    def _send_request(self, method: str, params: dict | None = None, timeout: float = 15.0) -> Any:
        """Send a JSON-RPC request and wait for response."""
        with self._lock:
            self._request_id += 1
            req_id = self._request_id

        msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params:
            msg["params"] = params

        self._responses[req_id] = None
        try:
            raw = json.dumps(msg)
            header = f"Content-Length: {len(raw.encode('utf-8'))}\r\n\r\n"
            self._process.stdin.write(header.encode("utf-8") + raw.encode("utf-8"))
            self._process.stdin.flush()
        except Exception:
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._responses[req_id] is not None:
                resp = self._responses.pop(req_id)
                if "error" in resp:
                    return None
                return resp.get("result")
            time.sleep(0.01)

        self._responses.pop(req_id, None)
        return None

    def _send_notification(self, method: str, params: dict | None = None):
        """Send a JSON-RPC notification (no response expected)."""
        msg = {"jsonrpc": "2.0", "method": method}
        if params:
            msg["params"] = params
        try:
            raw = json.dumps(msg)
            header = f"Content-Length: {len(raw.encode('utf-8'))}\r\n\r\n"
            self._process.stdin.write(header.encode("utf-8") + raw.encode("utf-8"))
            self._process.stdin.flush()
        except Exception:
            pass

    def _text_document_item(self, file_path: str, content: str) -> dict:
        """Build a TextDocumentItem."""
        ext = Path(file_path).suffix
        language = self.config.get("language", "text")
        return {
            "uri": Path(file_path).as_uri(),
            "languageId": language,
            "version": 1,
            "text": content,
        }

    def did_open(self, file_path: str, content: str):
        """Notify server that a file was opened."""
        item = self._text_document_item(file_path, content)
        self._send_notification("textDocument/didOpen", {"textDocument": item})

    def did_save(self, file_path: str, content: str):
        """Notify server that a file was saved."""
        self._send_notification("textDocument/didSave", {
            "textDocument": {"uri": Path(file_path).as_uri()},
            "text": content,
        })

    def diagnostics(self, file_path: str) -> list[dict]:
        """Get diagnostics (errors/warnings) for a file."""
        self.did_open(file_path, "")
        time.sleep(0.5)
        results = []
        for notif in self._notifications:
            if notif.get("method") == "textDocument/publishDiagnostics":
                params = notif.get("params", {})
                if params.get("uri") == Path(file_path).as_uri():
                    results = params.get("diagnostics", [])
        self._notifications.clear()
        return results

    def hover(self, file_path: str, line: int, character: int) -> str | None:
        """Get hover information at position."""
        resp = self._send_request("textDocument/hover", {
            "textDocument": {"uri": Path(file_path).as_uri()},
            "position": {"line": line, "character": character},
        })
        if resp and "contents" in resp:
            contents = resp["contents"]
            if isinstance(contents, dict):
                return contents.get("value", "")
            elif isinstance(contents, str):
                return contents
        return None

    def completion(self, file_path: str, line: int, character: int) -> list[dict]:
        """Get completions at position."""
        resp = self._send_request("textDocument/completion", {
            "textDocument": {"uri": Path(file_path).as_uri()},
            "position": {"line": line, "character": character},
        })
        if resp:
            items = resp if isinstance(resp, list) else resp.get("items", [])
            return [{"label": i.get("label", ""), "kind": i.get("kind", 0), "detail": i.get("detail", "")} for i in items[:20]]
        return []

    def goto_definition(self, file_path: str, line: int, character: int) -> list[dict]:
        """Go to definition."""
        resp = self._send_request("textDocument/definition", {
            "textDocument": {"uri": Path(file_path).as_uri()},
            "position": {"line": line, "character": character},
        })
        if resp:
            locations = resp if isinstance(resp, list) else [resp]
            return [{"file": loc.get("uri", "").replace("file:///", ""), "line": loc.get("range", {}).get("start", {}).get("line", 0)} for loc in locations]
        return []

    def references(self, file_path: str, line: int, character: int) -> list[dict]:
        """Find references."""
        resp = self._send_request("textDocument/references", {
            "textDocument": {"uri": Path(file_path).as_uri()},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": True},
        })
        if resp:
            return [{"file": loc.get("uri", "").replace("file:///", ""), "line": loc.get("range", {}).get("start", {}).get("line", 0)} for loc in resp]
        return []

    def stop(self):
        """Shutdown the language server."""
        self._stop_event.set()
        if self._process:
            try:
                self._send_request("shutdown", timeout=3.0)
                self._send_notification("exit")
            except Exception:
                pass
            try:
                self._process.terminate()
            except Exception:
                pass
        self._initialized = False


def _detect_language(file_path: str) -> str | None:
    """Detect language from file extension."""
    ext = Path(file_path).suffix.lower()
    for server_id, config in LSP_SERVERS.items():
        if ext in config["extensions"]:
            return server_id
    return None


def _get_root_uri(file_path: str) -> str:
    """Find the project root by looking for common markers."""
    p = Path(file_path).resolve()
    markers = [".git", "package.json", "pyproject.toml", "setup.py", "Cargo.toml", "go.mod"]
    for parent in [p] + list(p.parents):
        for marker in markers:
            if (parent / marker).exists():
                return parent.as_uri()
    return p.parent.as_uri()


def _get_connection(file_path: str) -> _LSPConnection | None:
    """Get or create an LSP connection for a file."""
    lang = _detect_language(file_path)
    if not lang:
        return None

    root_uri = _get_root_uri(file_path)
    key = f"{lang}:{root_uri}"

    with _lock:
        if key in _active_servers and _active_servers[key]._initialized:
            return _active_servers[key]

        config = LSP_SERVERS[lang]
        conn = _LSPConnection(lang, config, root_uri)
        if conn.start():
            _active_servers[key] = conn
            return conn
        return None


# ── Public API (called by tool handler) ──

def lsp_diagnostics(file_path: str) -> str:
    """Get errors/warnings for a file."""
    conn = _get_connection(file_path)
    if not conn:
        lang = _detect_language(file_path)
        if not lang:
            return f"No LSP available for {Path(file_path).suffix} files"
        return f"LSP server for {lang} not available (install {LSP_SERVERS[lang]['command']})"

    diags = conn.diagnostics(file_path)
    if not diags:
        return f"No diagnostics for {Path(file_path).name}"

    lines = []
    for d in diags:
        severity = {1: "ERROR", 2: "WARNING", 3: "INFO", 4: "HINT"}.get(d.get("severity", 0), "?")
        msg = d.get("message", "")
        line = d.get("range", {}).get("start", {}).get("line", 0) + 1
        lines.append(f"L{line} [{severity}]: {msg}")
    return f"Diagnostics for {Path(file_path).name}:\n" + "\n".join(lines)


def lsp_hover(file_path: str, line: int, character: int) -> str:
    """Get hover info (type, docs) at position."""
    conn = _get_connection(file_path)
    if not conn:
        return "LSP not available for this file type"
    result = conn.hover(file_path, line, character)
    return result or "No hover info at this position"


def lsp_complete(file_path: str, line: int, character: int) -> str:
    """Get completions at position."""
    conn = _get_connection(file_path)
    if not conn:
        return "LSP not available for this file type"
    items = conn.completion(file_path, line, character)
    if not items:
        return "No completions"
    lines = [f"- {i['label']} ({i['detail']})" for i in items[:15]]
    return "Completions:\n" + "\n".join(lines)


def lsp_goto(file_path: str, line: int, character: int) -> str:
    """Go to definition."""
    conn = _get_connection(file_path)
    if not conn:
        return "LSP not available"
    refs = conn.goto_definition(file_path, line, character)
    if not refs:
        return "No definition found"
    lines = [f"{r['file']}:{r['line']+1}" for r in refs]
    return "Definition(s):\n" + "\n".join(lines)


def lsp_references(file_path: str, line: int, character: int) -> str:
    """Find all references."""
    conn = _get_connection(file_path)
    if not conn:
        return "LSP not available"
    refs = conn.references(file_path, line, character)
    if not refs:
        return "No references found"
    lines = [f"{r['file']}:{r['line']+1}" for r in refs]
    return f"References ({len(refs)}):\n" + "\n".join(lines)


def lsp_status() -> str:
    """Show status of all active LSP connections."""
    if not _active_servers:
        return "No active LSP connections"
    lines = []
    for key, conn in _active_servers.items():
        status = "active" if conn._initialized else "failed"
        lines.append(f"- {conn.server_id} ({conn.root_uri}) — {status}")
    return "LSP connections:\n" + "\n".join(lines)


def lsp_stop_all():
    """Stop all LSP servers."""
    for conn in _active_servers.values():
        conn.stop()
    _active_servers.clear()


# ── Tool handler (called by tool_dispatcher) ──

def lsp_tool(parameters: dict = None, **kwargs) -> str:
    """Unified LSP tool handler."""
    if not parameters:
        return lsp_status()
    action = parameters.get("action", "status")
    file_path = parameters.get("file", parameters.get("path", ""))
    line = int(parameters.get("line", 0)) - 1  # Convert to 0-indexed
    character = int(parameters.get("character", 0))

    if action == "status":
        return lsp_status()
    elif action == "diagnostics":
        if not file_path:
            return "Error: file path required"
        return lsp_diagnostics(file_path)
    elif action == "hover":
        if not file_path:
            return "Error: file path required"
        return lsp_hover(file_path, line, character)
    elif action == "complete":
        if not file_path:
            return "Error: file path required"
        return lsp_complete(file_path, line, character)
    elif action == "goto":
        if not file_path:
            return "Error: file path required"
        return lsp_goto(file_path, line, character)
    elif action == "references":
        if not file_path:
            return "Error: file path required"
        return lsp_references(file_path, line, character)
    elif action == "stop":
        lsp_stop_all()
        return "All LSP servers stopped"
    else:
        return f"Unknown LSP action: {action}. Use: status, diagnostics, hover, complete, goto, references, stop"
