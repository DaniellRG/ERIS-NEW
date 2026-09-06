"""
core/permission_gate.py — Permission gate for dangerous operations in ERIS.

Automatically detects risky actions and requests user confirmation
before executing them. Supports:
  - File deletion/overwrite
  - Shell commands (rm, del, format, etc.)
  - Git push/force push
  - Network operations
  - System modifications
  - Custom rules

Integration: tool_dispatcher calls gate before executing dangerous tools.
"""
from __future__ import annotations

import re
import time
import json
from pathlib import Path
from typing import Optional, Callable

_BASE = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_PERMISSION_LOG = _DATA_DIR / "permission_log.json"
_PERMISSION_RULES = _DATA_DIR / "permission_rules.json"

_rules_cache: dict = {}
_rules_mtime: float = 0.0


def _reload_rules() -> dict:
    """Lee data/permission_rules.json (cacheado por mtime).
    Formato: {"tool": "allow|ask|deny", "tool.action": "...", "*": "..."}."""
    global _rules_cache, _rules_mtime
    try:
        if _PERMISSION_RULES.exists():
            m = _PERMISSION_RULES.stat().st_mtime
            if m != _rules_mtime:
                raw = json.loads(_PERMISSION_RULES.read_text(encoding="utf-8"))
                _rules_cache = raw if isinstance(raw, dict) else {}
                _rules_mtime = m
            return _rules_cache
    except Exception:
        pass
    return {}

# Risky command patterns
DANGEROUS_COMMANDS = [
    (re.compile(r"\brm\s+(-[rf]+\s+)?/", re.I), "Eliminar archivos/directorios"),
    (re.compile(r"\bdel\s+(/[sfq]\s+)?[A-Z]:\\", re.I), "Eliminar archivos en Windows"),
    (re.compile(r"\bformat\s+[A-Z]:", re.I), "Formatear disco"),
    (re.compile(r"\brmdir\s+(/s\s+)?[A-Z]:\\", re.I), "Eliminar directorio en Windows"),
    (re.compile(r"\bRemove-Item\s+(-Recurse)?\s+\"", re.I), "Eliminar con PowerShell"),
    (re.compile(r"\bgit\s+push\s+--force", re.I), "Git force push"),
    (re.compile(r"\bgit\s+push", re.I), "Git push"),
    (re.compile(r"\bgit\s+reset\s+--hard", re.I), "Git reset hard"),
    (re.compile(r"\bshutdown", re.I), "Apagar/reiniciar sistema"),
    (re.compile(r"\bsystemctl\s+(stop|disable|restart)", re.I), "Detener servicio"),
    (re.compile(r"\bnet\s+user", re.I), "Modificar usuarios"),
]

# Risky tools (tool_name -> risk description)
DANGEROUS_TOOLS = {
    "delete": "Eliminar archivo",
    "write": "Sobreescribir archivo",
    "elevated": "Ejecutar como admin",
    "shell_execute": "ShellExecute COM",
    "force_push": "Git force push",
    "clean": "Git clean (elimina archivos sin trackear)",
}

# Tools that always need confirmation
ALWAYS_CONFIRM = {"elevated", "shell_execute"}

# Tools that are always safe
ALWAYS_SAFE = {"read", "info", "list", "list_history", "session_info", "status", "text", "html", "links", "meta", "screenshot"}


class PermissionResult:
    def __init__(self, allowed: bool, reason: str = "", by_user: bool = True):
        self.allowed = allowed
        self.reason = reason
        self.by_user = by_user
        self.time = time.time()


class PermissionGate:
    """
    Checks if a tool call is risky and requests confirmation if needed.

    Usage:
        gate = get_permission_gate()
        gate.set_ui_callback(my_ui_ask_function)
        result = gate.check("terminal_agent", {"action": "run", "command": "rm -rf /"})
        if not result.allowed:
            return "Permiso denegado"
    """

    def __init__(self):
        self._ui_callback: Callable | None = None
        self._auto_approve = set()  # Tools that are auto-approved
        self._auto_deny = set()     # Tools that are auto-denied
        self._trusted_sessions: dict = {}  # user -> expiry time

    def set_ui_callback(self, callback: Callable):
        """Set the UI callback for asking permission. callback(question) -> bool"""
        self._ui_callback = callback

    def set_auto_approve(self, tools: set):
        """Tools that never need confirmation."""
        self._auto_approve = tools | ALWAYS_SAFE

    def set_auto_deny(self, tools: set):
        """Tools that are always denied."""
        self._auto_deny = tools

    def trust_session(self, user: str, minutes: int = 30):
        """Trust all actions for N minutes."""
        self._trusted_sessions[user] = time.time() + (minutes * 60)

    def is_trusted(self, user: str = "default") -> bool:
        expiry = self._trusted_sessions.get(user, 0)
        if time.time() < expiry:
            return True
        self._trusted_sessions.pop(user, None)
        return False

    def _match_rule(self, tool_name: str, params: dict) -> str | None:
        """Resuelve la regla explícita más específica para esta llamada."""
        try:
            rules = _reload_rules()
            action = params.get("action") if isinstance(params, dict) else None
            ordered = [tool_name]
            if action:
                ordered.append(f"{tool_name}.{action}")
            for key in ordered:
                if key in rules:
                    return rules[key]
            return rules.get("*")
        except Exception:
            return None

    def assess_risk(self, tool_name: str, params: dict) -> tuple[bool, str, str]:
        """
        Assess risk of a tool call.
        Returns: (needs_confirmation, risk_level, description)
        risk_level: safe, low, medium, high, critical
        """
        if tool_name in self._auto_approve:
            return False, "safe", ""

        if tool_name in self._auto_deny:
            return True, "critical", f"Tool bloqueada: {tool_name}"

        # ── Políticas explícitas (data/permission_rules.json): allow | ask | deny ──
        rule = self._match_rule(tool_name, params)
        if rule == "deny":
            return True, "critical", f"Bloqueada por política (permission_rules.json): {tool_name}"
        if rule == "ask":
            return True, "medium", f"Confirmación requerida por política (permission_rules.json): {tool_name}"
        if rule == "allow":
            return False, "safe", ""

        if tool_name in ALWAYS_CONFIRM:
            return True, "high", DANGEROUS_TOOLS.get(tool_name, f"Tool riesgosa: {tool_name}")

        # Check tool-level risk
        if tool_name in DANGEROUS_TOOLS:
            return True, "medium", DANGEROUS_TOOLS[tool_name]

        # Check command-level risk for terminal commands
        if tool_name == "terminal_agent":
            cmd = params.get("command", "") or params.get("cmd", "")
            for pattern, desc in DANGEROUS_COMMANDS:
                if pattern.search(cmd):
                    return True, "high", f"{desc}: {cmd[:80]}"

        # Check file overwrite risk
        if tool_name in ("file_editor", "file_controller", "file_api"):
            action = params.get("action", "")
            if action == "delete":
                path = params.get("path", "") or params.get("file", "")
                return True, "high", f"Eliminar: {path}"
            if action == "write":
                path = params.get("path", "") or params.get("file", "")
                if path and Path(path).exists():
                    return True, "medium", f"Sobreescribir: {path}"

        # Git push without force
        if tool_name == "git_control":
            action = params.get("action", "")
            if action == "push":
                return True, "medium", "Git push"
            if action in ("force_push", "filter_branch"):
                return True, "high", f"Git {action}"

        return False, "safe", ""

    def check(self, tool_name: str, params: dict, user: str = "default") -> PermissionResult:
        """
        Check if a tool call needs permission.
        Returns PermissionResult with allowed=True/False.
        """
        needs_confirm, risk, desc = self.assess_risk(tool_name, params)

        if not needs_confirm:
            return PermissionResult(True, "safe")

        # Bloques duros por política (deny) — NO dependen del UI ni de
        # sesión confiable. Una tool "deny" es un rechazo absoluto.
        if risk == "critical" and (desc.startswith("Bloqueada") or desc.startswith("Tool bloqueada")):
            self._log_decision(tool_name, params, False, "denied_by_policy")
            return PermissionResult(False, "denied_by_policy")

        if self.is_trusted(user):
            self._log_decision(tool_name, params, True, "trusted_session")
            return PermissionResult(True, "trusted_session")

        # Request permission via UI callback
        if self._ui_callback:
            try:
                question = f"[RIESGO {risk.upper()}] {desc}\n\nTool: {tool_name}\n¿Ejecutar?"
                allowed = self._ui_callback(question)
                self._log_decision(tool_name, params, allowed, "user")
                return PermissionResult(allowed, "user" if allowed else "denied_by_user")
            except Exception:
                self._log_decision(tool_name, params, False, "callback_error")
                return PermissionResult(False, "callback_error")

        # No UI available — allow by default (backward compatible)
        self._log_decision(tool_name, params, True, "no_ui")
        return PermissionResult(True, "no_ui_available")

    def _log_decision(self, tool_name: str, params: dict, allowed: bool, reason: str):
        try:
            log = []
            if _PERMISSION_LOG.exists():
                log = json.loads(_PERMISSION_LOG.read_text(encoding="utf-8"))
            log.append({
                "tool": tool_name,
                "params_preview": str(params)[:200],
                "allowed": allowed,
                "reason": reason,
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            if len(log) > 200:
                log = log[-200:]
            _PERMISSION_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


# Singleton
_gate: PermissionGate | None = None


def get_permission_gate() -> PermissionGate:
    global _gate
    if _gate is None:
        _gate = PermissionGate()
    return _gate


def permission_policy_tool(parameters=None, player=None) -> str:
    """Tool `permission_policy` — gestiona las políticas allow/ask/deny
    estilo opencode (data/permission_rules.json). Acciones: view, allow,
    ask, deny, trust, untrust, reset."""
    global _rules_mtime
    params = parameters or {}
    action = (params.get("action") or "view").strip().lower()
    tool = (params.get("tool") or "").strip()
    tool_action = (params.get("tool_action") or "").strip()
    try:
        minutes = int(params.get("minutes") or 30)
    except Exception:
        minutes = 30
    gate = get_permission_gate()
    rules = _reload_rules()
    key = tool if not tool_action else f"{tool}.{tool_action}"

    if action in ("view", "list", "rules", "status"):
        lines = [f"{k} → {v}" for k, v in rules.items() if k != "$comment"]
        auto = " | ".join(sorted(gate._auto_approve - set(ALWAYS_SAFE))) or "—"
        denied = " | ".join(sorted(gate._auto_deny)) or "—"
        trusted = "sí" if gate.is_trusted() else "no"
        body = "\n".join(lines) or "(sin reglas explícitas)"
        return (
            "Políticas de permisos (data/permission_rules.json):\n{}\n"
            "Auto-aprobadas: {}\nBloqueadas: {}\nSesión de confianza: {}".format(
                body, auto, denied, trusted)
        )

    if action in ("allow", "ask", "deny"):
        if not key:
            return "Falta 'tool'. Ej: permission_policy action=deny tool=shutdown_eris tool_action=..."
        rules[key] = action
        try:
            _PERMISSION_RULES.write_text(
                json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            return "No pude escribir las reglas: {}".format(e)
        _rules_cache.clear()
        _rules_mtime = 0.0
        # Reconstruir los conjuntos automáticos a partir de reglas exactas de tool
        ap = set(ALWAYS_SAFE) | {k for k, v in rules.items() if v == "allow" and "." not in k}
        dn = {k for k, v in rules.items() if v == "deny" and "." not in k}
        gate.set_auto_approve(ap)
        gate.set_auto_deny(dn)
        return "Regla aplicada: {} → {}. Efectiva ya.".format(key, action)

    if action in ("trust",):
        gate.trust_session("default", minutes)
        return "Sesión confiable por {} minutos (no pedirá confirmación).".format(minutes)

    if action in ("untrust", "clear_trust"):
        gate._trusted_sessions.pop("default", None)
        return "Sesión de confianza revocada."

    if action == "reset":
        try:
            _PERMISSION_RULES.unlink(missing_ok=True)
        except Exception:
            pass
        _rules_cache.clear()
        _rules_mtime = 0.0
        gate.set_auto_approve(set(ALWAYS_SAFE))
        gate.set_auto_deny(set())
        return "Políticas reseteadas: vuelve la heurística por defecto."

    return "Acciones válidas de permission_policy: view, allow, ask, deny, trust, untrust, reset."
