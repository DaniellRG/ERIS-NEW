"""
core/tool_dispatch_api.py
──────────────────────────
Puente entre la tripulación de sub-agentes y las tools reales de Eris.

Por qué existe este módulo
──────────────────────────
`core/sub_agent_crew.py:44` hacía `from core.tool_dispatcher import dispatch_tool`
sobre un símbolo que **no existe** en ese módulo (allí solo están `_should_learn`
y `_result_status`). Las 32 llamadas a herramientas que hace la tripulación
devolvían siempre el string `"[Tool X no disponible en este contexto]"`, y Eris lo
reportaba al usuario como si fuera un resultado.

Este módulo lo arregla, con tres garantías:

  1. Un despachador singleton accesible desde cualquier hilo de la GUI, de la CLI
     y de los hilos de fondo.
  2. Un host headless para los caminos que no tienen ventana (CLI, hilos de fondo).
  3. **Guardas de seguridad EN el camino**, no decorativas: `guard_check()` y
     `core.permission_gate.check()` se consultan ANTES de ejecutar, y toda tool de
     escritura queda en el log de auditoría.

Y una regla dura: **nunca** devuelve un error disfrazado de resultado. Si una tool
falla, la excepción sube. Si la tool no existe, `KeyError` con la lista de nombres.

Por qué NO se reusa `ToolDispatcher.execute()`
──────────────────────────────────────────────
`execute()` toma un `types.FunctionCall`, necesita un event loop vivo, desreferencia
`self._eris.ui/.speak/._session_id`, y además **traga las excepciones** devolviendo
`f"Tool '{name}' failed: {e}"` (línea 460) y `f"Error en {name}: {e}"` (línea 824).
Ningún wrapper por encima puede recuperar la excepción. Acá se despacha **por debajo**
de `execute()`: `get_tool` → `ToolDispatcher._build_kwargs` → `tool(**kwargs)`.

Este módulo NO importa `core.sub_agent_crew` (que sería circular): las reglas del
guardián viven aquí y `ActionGuard.execute()` las importa para mostrarlas al usuario.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

_BASE = Path(__file__).resolve().parent.parent
_AUDIT_LOG = _BASE / "data" / "tool_audit.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Reglas del guardián — fuente única de verdad
# ─────────────────────────────────────────────────────────────────────────────
# Antes vivían duplicadas como `ActionGuard._RISKY_API` / `_BLOCKED_PARAMS`.
# Ahora están acá y `ActionGuard.execute()` las importa, para que no puedan
# divergir entre lo que se muestra en el chat y lo que realmente se bloquea.

#: Tools con efectos secundarios sobre el sistema.
#: OJO: `email_sender`, `api_invoke` y `webhook_sender` NO existen hoy en el
#: registro (503 tools) - quedaron de cuando ActionGuard se escribio. Se dejan
#: vigilados por si alguien las construye: vigilar una tool que no existe es
#: inofensivo, y obviarla seria una trampa si aparece despues.
RISKY_API = (
    "git_control", "email_sender", "file_api", "terminal_agent",
    "shell_session", "api_invoke", "webhook_sender",
    "process_manager", "pc_control", "file_encryptor", "code_guard",
    "skill_manage", "cron_scheduler", "maintenance", "auto_salud",
    "save_memory", "self_evolution", "rag_engine",
)

#: Patrones de TEXTO que bloquean sin importar nada mas.
BLOCKED_PARAMS: dict[str, tuple[str, ...]] = {
    "git_control": ("git reset --hard", "push --force", "push -f", "rm -rf"),
    "terminal_agent": ("rm -rf", "mkfs", "dd ", "chmod -R 777", ":(){ :|:& };:"),
    "shell_session": ("rm -rf", "mkfs", "dd ", "chmod -R 777"),
    "file_api": ("delete", "trash"),
    "email_sender": ("send",),
    "api_invoke": ("delete", "drop", "destroy"),
    "webhook_sender": ("send", "post"),
    "file_encryptor": ("encrypt_all",),
    "code_guard": ("fix_all",),
    "process_manager": ("kill", "terminate"),
    "pc_control": ("poweroff", "reboot", "shutdown"),
}

#: Reglas por PARAMETRO, no por texto.
#:
#: Los patrones de arriba buscan cadenas, y eso tiene un agujero real:
#: `git_control(action="push", force=True)` NO contiene la cadena "push --force",
#: asi que el patron no lo ve - y un sub-agente podia forzar un push justamente
#: de la forma mas natural. Estas reglas cierran ese hueco.
PARAM_RULES: tuple[tuple[str, str, tuple], ...] = (
    # (tool, nombre del parametro, valores prohibidos)
    ("git_control",     "force",      (True, "true", "yes", "1", "-f", "--force")),
    ("git_control",     "hard_reset", (True, "true", "yes", "1")),
    ("git_control",     "action",     ("push --force", "reset --hard", "clean")),
    ("process_manager", "action",     ("kill", "terminate", "killall")),
    ("pc_control",      "action",     ("poweroff", "reboot", "shutdown", "hibernate")),
    ("file_api",        "action",     ("delete", "trash", "rmdir")),
    ("webhook_sender",  "action",     ("delete", "drop", "destroy")),
    ("api_invoke",      "action",     ("delete", "drop", "destroy")),
    ("code_guard",      "action",     ("fix_all", "fix_everything")),
)


def _walk_params(params: dict, depth: int = 2):
    """Aplana un dict de params (hasta `depth` niveles) en pares (clave, valor)."""
    out = []
    for key, value in (params or {}).items():
        out.append((str(key).lower(), value))
        if isinstance(value, dict) and depth > 0:
            out.extend(_walk_params(value, depth - 1))
    return out


def param_block(tool: str, params: Optional[dict] = None) -> Optional[str]:
    """Devuelve la regla violada, o None si la tool esta bien.

    Fail-safe: si los params no se pueden recorrer, se bloquea.
    """
    tool = str(tool or "")
    try:
        flat = _walk_params(params or {})
    except Exception:
        return "params_ilegibles"

    for rule_tool, key, bad_values in PARAM_RULES:
        if rule_tool != tool:
            continue
        for pkey, value in flat:
            if pkey != key:
                continue
            if isinstance(value, bool):
                if value is True:
                    return f"{tool}.{key}=True"
                continue
            if isinstance(value, (list, tuple)):
                hit = [v for v in value if str(v).strip().lower() in bad_values]
                if hit:
                    return f"{tool}.{key}={hit[0]}"
                continue
            if str(value).strip().lower() in bad_values:
                return f"{tool}.{key}={str(value)[:40]}"
    return None


@dataclass
class GuardVerdict:
    """Veredicto del guardián. `allowed=False` significa NO ejecutar."""

    allowed: bool
    reason: str
    risk: str = "safe"          # safe | risky | blocked
    matched: Optional[str] = None
    message: str = ""

    def __bool__(self) -> bool:
        return self.allowed


def guard_check(tool_name: str, params: Optional[dict] = None,
                *, confirm: bool = False) -> GuardVerdict:
    """
    Evalúa una tool contra las reglas del Custodio de Acciones.

    Determinista y sin efectos secundarios: NO ejecuta nada, NO toca disco.
    Pensado para llamarse en cada invocación de herramienta.

    `confirm=True` es la confirmación explícita del usuario: permite saltar el
    bloqueo por patrón (el bloqueo por política de `permission_gate` NO se salta).
    """
    tool = str(tool_name or "")
    if tool not in RISKY_API:
        return GuardVerdict(True, "not_risky", risk="safe")

    # Regla 1: por PARAMETRO (mata el agujero de force=True / action="delete").
    violated = param_block(tool, params)
    if violated:
        if confirm:
            return GuardVerdict(
                True, "confirmed_by_user", risk="risky", matched=violated,
                message=f"'{violated}' - confirmado explicitamente por el usuario.",
            )
        return GuardVerdict(
            False, "blocked_param", risk="blocked", matched=violated,
            message=(f"\u26d4 ACCION BLOQUEADA por el Custodio: {violated}.\n"
                     f"Para ejecutarla igual hace falta confirmacion explicita "
                     f"del usuario."),
        )

    try:
        joined = json.dumps(params or {}, ensure_ascii=False, default=str).lower()
    except Exception:
        # Si no se puede serializar, se trata como riesgo maximo (fail-closed).
        joined = str(params or "").lower()

    # Regla 2: por TEXTO (comandos embebidos, flags sueltos).
    for pattern in BLOCKED_PARAMS.get(tool, ()):  # pragma: no branch
        if pattern.lower() in joined:
            if confirm:
                return GuardVerdict(
                    True, "confirmed_by_user", risk="risky", matched=pattern,
                    message=f"'{tool}' con patrón '{pattern}' — confirmado explícitamente por el usuario.",
                )
            return GuardVerdict(
                False, "blocked_pattern", risk="blocked", matched=pattern,
                message=(f"⛔ ACCIÓN BLOQUEADA por el Custodio: {tool} con patrón "
                         f"'{pattern}'. Para ejecutarla igual hace falta confirmación "
                         f"explícita del usuario."),
            )

    return GuardVerdict(
        True, "risky_allowed", risk="risky",
        message=f"⚠️ '{tool}' tiene efectos sobre el sistema; se permite con registro.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Host — la ventana de Eris, o una que no existe
# ─────────────────────────────────────────────────────────────────────────────

class HeadlessUI:
    """
    UI mínima para cuando no hay ventana (CLI, hilos de fondo, sub-agentes).

    `ask()` devuelve False a propósito: si algo pide confirmación y no hay nadie
    para responder, se deniega. `permission_gate.check()` ya es fail-closed para
    riesgo alto/crítico sin UI; esto cubre el resto de las llamadas a `ask`.
    """

    ui = None  # se fija en __init__: algunas tools leen self.ui.ui

    def __init__(self, session_id: str = "headless"):
        self.ui = self
        self._state = "IDLE"
        self._session_id = session_id
        self.is_sleeping = False
        self._log: list[str] = []

    # -- superficie que consulta ToolDispatcher / las tools --
    def set_state(self, state: str) -> None:
        self._state = state

    def write_log(self, message: str) -> None:
        self._log.append(str(message))

    def speak(self, text: str, **kwargs) -> None:
        """Sin voz en headless: se guarda y nada más."""

    def speak_error(self, text: str) -> None:
        self._log.append(f"ERROR: {text}")

    @property
    def muted(self) -> bool:
        return True

    @property
    def visual_mode(self) -> bool:
        return False

    @property
    def session_id(self) -> str:
        return self._session_id

    def ask(self, question: str, options=None, timeout: int = 30) -> bool:
        # Nadie responde → no se autoriza.
        self._log.append(f"ASK sin UI (denegado): {question}")
        return False

    def last_log(self, n: int = 20) -> list[str]:
        return self._log[-n:]


class HeadlessHost:
    """Doble de `ErisLive` con lo mínimo que `ToolDispatcher` necesita."""

    def __init__(self, session_id: str = "headless"):
        self.ui = HeadlessUI(session_id)
        self._session_id = session_id

    def speak(self, text: str, **kwargs) -> None:
        self.ui.speak(text, **kwargs)

    def speak_error(self, text: str) -> None:
        self.ui.speak_error(text)


_host: Optional[HeadlessHost] = None
_dispatcher: Any = None
_lock = threading.RLock()


def set_host(host) -> None:
    """
    Registra la instancia viva de Eris (la GUI o la CLI la llama al arrancar).

    A partir de ahí, `get_dispatcher()` usa esa ventana real para que las tools que
    necesitan hablar o preguntar con el usuario lo hagan de verdad.
    """
    global _host, _dispatcher
    with _lock:
        _host = host
        _dispatcher = None  # se reconstruye contra el host nuevo


def get_host():
    """El host registrado, o uno headless si nadie registró nada."""
    global _host
    with _lock:
        if _host is None:
            _host = HeadlessHost()
        return _host


def get_dispatcher():
    """
    Singleton de `ToolDispatcher` ligado al host actual.

    Solo se usa por `_build_kwargs()` (adaptar los params a la firma real de cada
    tool) — **no** por `execute()`, que traga las excepciones. Ver docstring.
    """
    global _dispatcher
    with _lock:
        if _dispatcher is None:
            from core.tool_dispatcher import ToolDispatcher
            _dispatcher = ToolDispatcher(get_host())
        return _dispatcher


# ─────────────────────────────────────────────────────────────────────────────
# 3. Auditoría
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AuditRecord:
    time: str
    tool: str
    allowed: bool
    stage: str
    reason: str
    params_preview: str = ""
    source: str = ""
    context: dict = field(default_factory=dict)


def audit(rec: AuditRecord) -> None:
    """Append-only en `data/tool_audit.jsonl`. Nunca rompe la ejecución."""
    try:
        _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec.__dict__, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def recent_audit(n: int = 50) -> list[dict]:
    """Últimas decisiones del guardián, para poder preguntarle a Eris por ellas."""
    try:
        if not _AUDIT_LOG.exists():
            return []
        lines = _AUDIT_LOG.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines[-n:]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# 4. Despacho real
# ─────────────────────────────────────────────────────────────────────────────

def _run_awaitable(awaitable):
    """Ejecuta una corrutina sin depender del hilo desde el que se llama."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No hay loop en este hilo → se puede usar asyncio.run.
        return asyncio.run(awaitable)

    # Hay un loop corriendo (p.ej. el loop de audio de Gemini): se corre la
    # corrutina en otro hilo con su propio loop, y se espera.
    result: dict = {}

    def _worker():
        try:
            result["value"] = asyncio.run(awaitable)
        except BaseException as exc:  # noqa: BLE001 - se re-lanza abajo
            result["error"] = exc

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join()
    if "error" in result:
        raise result["error"]
    return result.get("value")


def dispatch_tool(tool_name: str, params: Optional[dict] = None, *,
                  host=None, context: Optional[dict] = None,
                  confirm: bool = False, source: str = "",
                  check_guard: bool = True) -> Any:
    """
    Ejecuta una tool real de Eris, pasando por las guardas de seguridad.

    Orden: Custodio (patrones) → permission gate (política) → ejecución.

    Reglas:
      - Tool inexistente  → `KeyError` con la lista de nombres válidos.
      - Tool denegada     → `PermissionError`.
      - Tool que falla    → la excepción **sube**. Nunca se devuelve un string de
        error como si fuera un resultado. Eso era exactamente lo que hacia la
        tripulacion y por eso Eris reportaba acciones que nunca habia hecho.
      - `check_guard=False` es solo para el propio módulo de pruebas.

    Parámetros:
      params   dict de argumentos de la tool.
      host     doble de Eris; si se omite, el registrado (`get_host()`).
      context  contexto compartido (Fase 1 del diseño). Se registra en auditoría.
      confirm  confirmación explícita del usuario para el bloqueo por patrón.
      source   quién pidió la tool (sub-agente, CLI, chat) — va al log.
    """
    from core.tool_registry import get_tool

    name = str(tool_name or "").strip()
    args = dict(params or {})

    tool = get_tool(name)
    if tool is None:
        # Fallar ruidoso y útil: esto antes pasaba por un try/except que
        # devolvía texto y hacía que Eris creyera que la tool había funcionado.
        from core.tool_registry import _TOOLS
        close = [t for t in _TOOLS if name and (name in t or t in name)][:8]
        raise KeyError(
            f"Tool desconocida: '{name}'. "
            + (f"¿Quisiste decir alguna de: {', '.join(close)}? " if close else "")
            + f"Herramientas disponibles: {len(_TOOLS)}."
        )

    if check_guard:
        # ── Guarda 1: Custodio de Acciones (patrones) ──
        verdict = guard_check(name, args, confirm=confirm)
        if not verdict.allowed:
            audit(AuditRecord(
                time=time.strftime("%Y-%m-%d %H:%M:%S"), tool=name, allowed=False,
                stage="custodian", reason=verdict.reason,
                params_preview=str(args)[:200], source=source,
                context=dict(context or {}),
            ))
            raise PermissionError(verdict.message or f"Bloqueado: {verdict.reason}")

        # ── Guarda 2: permission gate (política; fail-closed sin UI) ──
        try:
            from core.permission_gate import get_permission_gate
            gate = get_permission_gate()
            result = gate.check(name, args)
            if not result.allowed:
                audit(AuditRecord(
                    time=time.strftime("%Y-%m-%d %H:%M:%S"), tool=name, allowed=False,
                    stage="permission_gate", reason=result.reason,
                    params_preview=str(args)[:200], source=source,
                    context=dict(context or {}),
                ))
                raise PermissionError(
                    f"El permission gate denegó '{name}': {result.reason}")
        except PermissionError:
            raise
        except Exception as exc:
            # Fail-closed: si el gate no se puede evaluar, no se ejecuta.
            audit(AuditRecord(
                time=time.strftime("%Y-%m-%d %H:%M:%S"), tool=name, allowed=False,
                stage="permission_gate_error", reason=f"{type(exc).__name__}: {exc}",
                params_preview=str(args)[:200], source=source,
                context=dict(context or {}),
            ))
            raise PermissionError(
                f"No se pudo evaluar el permiso de '{name}' ({type(exc).__name__}: {exc}). "
                "Se deniega por seguridad.") from exc

        if name in RISKY_API:
            audit(AuditRecord(
                time=time.strftime("%Y-%m-%d %H:%M:%S"), tool=name, allowed=True,
                stage="allowed", reason=verdict.reason,
                params_preview=str(args)[:200], source=source,
                context=dict(context or {}),
            ))

    # ── Ejecución real, por DEBAJO de ToolDispatcher.execute() ──
    dispatcher = get_dispatcher()
    kwargs = dispatcher._build_kwargs(tool, args)
    if host is not None and "player" in kwargs:
        kwargs["player"] = getattr(host, "ui", host)

    result = tool(**kwargs)
    if inspect.isawaitable(result):
        result = _run_awaitable(result)
    return result


def available_tools() -> list[str]:
    """Nombres de todas las tools registradas (para mensajes de error útiles)."""
    from core.tool_registry import _TOOLS
    return sorted(_TOOLS.keys())


__all__ = [
    "RISKY_API",
    "BLOCKED_PARAMS",
    "GuardVerdict",
    "guard_check",
    "HeadlessUI",
    "HeadlessHost",
    "set_host",
    "get_host",
    "get_dispatcher",
    "AuditRecord",
    "audit",
    "recent_audit",
    "dispatch_tool",
    "available_tools",
]
