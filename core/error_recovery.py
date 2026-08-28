"""
error_recovery.py — Recuperación inteligente de errores para herramientas.

Cuando una tool falla, en vez de simplemente reportar el error, intenta:
  1. Diagnosticar la causa raíz
  2. Buscar alternativas (otra tool que haga lo mismo)
  3. Ajustar parámetros y reintentar
  4. Reportar un error accionable (no solo el traceback)

Flujo:
  Tool falla → error_recovery(result, tool_name, args) →
    ¿tiene alternativa? → probar alternativa → si funciona, devolver resultado
    ¿tiene fix obvio? → aplicar fix → reintentar
    ¿es transitorio? → retry con backoff
    ¿es fatal? → reportar con contexto
"""
from __future__ import annotations

import time
import re
import json

try:
    from core.tool_registry import get_tool
except ImportError:
    get_tool = None


# ── Mapa de alternativas ────────────────────────────────────────────────────

ALTERNATIVES = {
    "web_search": ["super_search", "deep_research", "webfetch"],
    "file_read": ["codebase"],
    "file_write": ["file_edit"],
    "file_edit": ["file_write"],
    "codebase": ["file_read"],
    "shell": ["exec_python"],
    "exec_python": ["shell"],
    "obsidian_note": ["file_write", "document_creator"],
    "document_creator": ["file_write"],
    "github_pr": ["git_control"],
    "git_control": ["shell"],
    "voice_clone": ["tts_engine"],
    "tts_engine": ["edge_tts"],
    "image_generation": ["web_search"],
    "web_search": ["webfetch"],
}

# ── Patrones de error y fixes automáticos ────────────────────────────────────

AUTO_FIXES = [
    {
        "pattern": re.compile(r"FileNotFoundError.*'([^']+)'", re.IGNORECASE),
        "fix": "check_path_exists",
        "description": "Archivo no existe",
    },
    {
        "pattern": re.compile(r"Permission denied.*'([^']+)'", re.IGNORECASE),
        "fix": "check_permissions",
        "description": "Permiso denegado",
    },
    {
        "pattern": re.compile(r"ModuleNotFoundError.*'([^']+)'", re.IGNORECASE),
        "fix": "suggest_install",
        "description": "Módulo no instalado",
    },
    {
        "pattern": re.compile(r"JSONDecodeError", re.IGNORECASE),
        "fix": "fix_json",
        "description": "JSON inválido",
    },
    {
        "pattern": re.compile(r"ConnectionRefused|ConnectionError", re.IGNORECASE),
        "fix": "retry_with_backoff",
        "description": "Conexión rechazada",
    },
    {
        "pattern": re.compile(r"Timeout|timed? out", re.IGNORECASE),
        "fix": "retry_with_backoff",
        "description": "Timeout",
    },
    {
        "pattern": re.compile(r"Rate limit|429|too many requests", re.IGNORECASE),
        "fix": "retry_with_backoff",
        "description": "Rate limited",
    },
]

# ── Transitorio vs fatal ────────────────────────────────────────────────────

TRANSIENT_INDICATORS = [
    "timeout", "connection", "refused", "reset", "broken pipe",
    "429", "rate limit", "temporary", "transient", "retry",
]

FATAL_INDICATORS = [
    "permission denied", "access denied", "not found", "does not exist",
    "invalid syntax", "type error", "value error", "key error",
]


class ErrorRecovery:
    """Motor de recuperación inteligente de errores."""

    def __init__(self):
        self.recovery_log = []

    def diagnose(self, error: str, tool_name: str, args: dict) -> dict:
        """Diagnostica un error y sugiere acción.

        Returns:
            dict con: error_type, is_transitory, is_fatal, suggested_action,
                      alternatives, auto_fix, description
        """
        error_lower = error.lower()

        # Detectar tipo de error
        is_transitory = any(ind in error_lower for ind in TRANSIENT_INDICATORS)
        is_fatal = any(ind in error_lower for ind in FATAL_INDICATORS)

        # Buscar auto-fix
        auto_fix = None
        for af in AUTO_FIXES:
            m = af["pattern"].search(error)
            if m:
                auto_fix = {
                    "type": af["fix"],
                    "description": af["description"],
                    "match": m.group(0),
                    "groups": m.groups(),
                }
                break

        # Buscar alternativas
        alternatives = ALTERNATIVES.get(tool_name, [])

        # Determinar acción sugerida
        if auto_fix and auto_fix["type"] == "retry_with_backoff":
            suggested = "retry_backoff"
        elif auto_fix and auto_fix["type"] in ("check_path_exists", "check_permissions"):
            suggested = "fix_and_retry"
        elif alternatives:
            suggested = "try_alternative"
        elif is_transitory:
            suggested = "retry"
        elif is_fatal:
            suggested = "report"
        else:
            suggested = "report"

        return {
            "error_type": auto_fix["type"] if auto_fix else "unknown",
            "is_transitory": is_transitory,
            "is_fatal": is_fatal,
            "suggested_action": suggested,
            "alternatives": alternatives,
            "auto_fix": auto_fix,
            "description": auto_fix["description"] if auto_fix else error[:200],
        }

    def _apply_fix(self, diagnosis: dict, args: dict) -> str | None:
        """Apply an automatic fix based on diagnosis. Returns fix description or None."""
        fix = diagnosis.get("auto_fix")
        if not fix:
            return None

        fix_type = fix.get("type", "")
        groups = fix.get("groups", ())

        if fix_type == "suggest_install":
            module = groups[0] if groups else ""
            if module:
                return f"pip install {module}"

        elif fix_type == "fix_json":
            path = args.get("path", "") or args.get("file", "")
            if path:
                try:
                    import json as _json
                    with open(path, "r", encoding="utf-8") as f:
                        raw = f.read()
                    # Try to fix common JSON issues
                    fixed = raw.strip()
                    if fixed.endswith(",}"):
                        fixed = fixed[:-2] + "}"
                    if fixed.endswith(",]"):
                        fixed = fixed[:-2] + "]"
                    _json.loads(fixed)  # validate
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(fixed)
                    return f"JSON corregido en {path}"
                except Exception:
                    pass

        elif fix_type == "check_path_exists":
            path = groups[0] if groups else ""
            if path:
                import os
                if not os.path.exists(path):
                    parent = os.path.dirname(path)
                    if parent and os.path.isdir(parent):
                        return f"El directorio padre existe: {parent}. Crear archivo nuevo."
                    return f"La ruta no existe y el padre tampoco: {path}"

        elif fix_type == "check_permissions":
            path = groups[0] if groups else ""
            if path:
                import os
                if os.path.exists(path):
                    if not os.access(path, os.W_OK):
                        return f"Sin permisos de escritura en {path}. Necesitás admin."
                return f"Verificar permisos de: {path}"

        return None

    def try_recovery(
        self,
        error: str,
        tool_name: str,
        args: dict,
        player=None,
        max_retries: int = 2,
    ) -> dict | None:
        """Intenta recuperarse de un error. Aplica fixes automáticamente cuando es posible.

        Returns:
            dict con: recovered, result, tool_used, retries, diagnosis, fix_applied
            o None si no se pudo recuperar.
        """
        diagnosis = self.diagnose(error, tool_name, args)

        # 0. Apply auto-fix if available
        fix_applied = self._apply_fix(diagnosis, args)
        if fix_applied and get_tool:
            func = get_tool(tool_name)
            if func:
                try:
                    import inspect
                    sig = inspect.signature(func)
                    kwargs = {"parameters": args}
                    if "player" in sig.parameters:
                        kwargs["player"] = player
                    result = func(**kwargs)
                    result_str = str(result)[:4000]
                    if "error" not in result_str.lower():
                        return {
                            "recovered": True,
                            "result": result_str,
                            "tool_used": tool_name,
                            "retries": 0,
                            "diagnosis": diagnosis,
                            "fix_applied": fix_applied,
                        }
                except Exception:
                    pass

        # 1. Intentar alternativas
        if diagnosis["suggested_action"] == "try_alternative" and diagnosis["alternatives"]:
            for alt_name in diagnosis["alternatives"][:2]:
                if get_tool is None:
                    continue
                func = get_tool(alt_name)
                if func is None:
                    continue
                try:
                    import inspect
                    sig = inspect.signature(func)
                    kwargs = {"parameters": args}
                    result = func(**kwargs)
                    result_str = str(result)[:4000]
                    if "error" not in result_str.lower() and len(result_str) > 10:
                        self.recovery_log.append({
                            "original_tool": tool_name,
                            "recovery_tool": alt_name,
                            "success": True,
                        })
                        return {
                            "recovered": True,
                            "result": result_str,
                            "tool_used": alt_name,
                            "retries": 0,
                            "diagnosis": diagnosis,
                            "fix_applied": None,
                        }
                except Exception:
                    continue

        # 2. Retry con backoff para errores transitorios
        if diagnosis["suggested_action"] in ("retry_backoff", "retry"):
            for attempt in range(max_retries):
                backoff = (2 ** attempt) * 0.5
                time.sleep(backoff)
                if get_tool:
                    func = get_tool(tool_name)
                    if func:
                        try:
                            import inspect
                            sig = inspect.signature(func)
                            kwargs = {"parameters": args}
                            if "player" in sig.parameters:
                                kwargs["player"] = player
                            result = func(**kwargs)
                            result_str = str(result)[:4000]
                            if "error" not in result_str.lower():
                                return {
                                    "recovered": True,
                                    "result": result_str,
                                    "tool_used": tool_name,
                                    "retries": attempt + 1,
                                    "diagnosis": diagnosis,
                                    "fix_applied": fix_applied,
                                }
                        except Exception:
                            continue

        return None


# Singleton
_error_recovery: ErrorRecovery | None = None


def get_error_recovery() -> ErrorRecovery:
    global _error_recovery
    if _error_recovery is None:
        _error_recovery = ErrorRecovery()
    return _error_recovery


def smart_retry(error: str, tool_name: str, args: dict, player=None) -> dict | None:
    """API de alto nivel: intenta recuperarse de un error de tool."""
    return get_error_recovery().try_recovery(error, tool_name, args, player)
