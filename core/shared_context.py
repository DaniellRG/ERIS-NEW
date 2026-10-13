"""core/shared_context.py — el contexto único por proceso (Fase 1.1).

UN SOLO CEREBRO. Hasta ahora la GUI, la CLI y los subagentes vivían en islas:
cada uno guardaba su propio historial y adivinaba el proyecto/archivo en foco.
Este módulo es la fuente de verdad compartida: qué se venía hablando, el
resumen de la sesión, la raíz del proyecto, el archivo activo, la app en foco,
la identidad y si el contexto es de solo lectura.

Decisiones de diseño:

- **Sin Qt, sin red, sin deps pesadas**: importable desde `main.py`,
  `eris_cli.py` y cualquier subagente sin arrastrar la GUI.
- **Thread-safe**: `main.py` corre varios hilos (`_observe_loop`,
  `_sub_agents_loop`, `_routines_loop`), así que cada mutación toma un lock.
- **Nunca lanza**: leer/mutar el contexto jamás debe tumbar un hilo. Todo lo
  que puede fallar (detectar la raíz del proyecto, leer el foco) degrada a un
  valor vacío honesto.
- **Un singleton por proceso** (`get_shared_context()`), con
  `reset_shared_context()` para los tests.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Optional

# Cuántos turnos de conversación reciente se conservan (los últimos N).
_CONVO_MAX = 12
# Fragmentos como máximo en el bloque de prompt (para no inflar el contexto).
_CONVO_BLOCK_N = 4

# Marcadores para detectar la raíz de un proyecto subiendo por el árbol.
_PROJECT_MARKERS = (
    ".git", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "docker-compose.yml", "Dockerfile", ".hg", ".svn",
)

_DEFAULT_IDENTITY = {
    "name": "Eris",
    "language": "es-AR",
    "kind": "asistente",
}


class SharedContext:
    """Estado vivo compartido por GUI, CLI y subagentes (singleton por proceso)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.convo_ctx: list[str] = []
        self.session_summary: str = ""
        self.project_root: Optional[str] = None
        self.active_file: Optional[str] = None
        self.foreground_app: Optional[str] = None
        self.identity: dict = dict(_DEFAULT_IDENTITY)
        self.read_only: bool = False
        self.updated_at: float = time.time()

    # ── conversación reciente ──────────────────────────────────────────────

    def note(self, text: str) -> None:
        """Registra un fragmento del intercambio (usuario o Eris). Acotado a N."""
        if text is None:
            return
        text = str(text).strip()
        if not text:
            return
        with self._lock:
            self.convo_ctx.append(text)
            if len(self.convo_ctx) > _CONVO_MAX:
                del self.convo_ctx[: -_CONVO_MAX]
            self.updated_at = time.time()

    def set_conversation(self, items) -> None:
        """Reemplaza el historial reciente (p. ej. al reconectar)."""
        with self._lock:
            self.convo_ctx = [str(x).strip() for x in (items or []) if str(x).strip()]
            del self.convo_ctx[: -_CONVO_MAX]
            self.updated_at = time.time()

    def recent_convo(self, n: int = _CONVO_BLOCK_N) -> list[str]:
        with self._lock:
            return list(self.convo_ctx[-n:]) if n else []

    def set_session_summary(self, summary: str) -> None:
        with self._lock:
            self.session_summary = str(summary or "")
            self.updated_at = time.time()

    # ── proyecto / archivo / foco ──────────────────────────────────────────

    def detect_project_root(self, hint: Optional[str] = None) -> Optional[str]:
        """Sube por el árbol desde `hint` (o cwd) buscando un marcador de proyecto.

        Devuelve la primera carpeta con marcador; si no encuentra ninguno, el
        `hint`/cwd. Nunca lanza: en caso de error devuelve None."""
        try:
            start = Path(hint or os.getcwd()).expanduser()
            if start.is_file():
                start = start.parent
            start = start.resolve()
            for candidate in [start, *start.parents]:
                if any((candidate / marker).exists() for marker in _PROJECT_MARKERS):
                    self.set_project_root(str(candidate))
                    return str(candidate)
            self.set_project_root(str(start))
            return str(start)
        except Exception:
            return None

    def set_project_root(self, root: Optional[str]) -> None:
        with self._lock:
            self.project_root = str(root) if root else None
            self.updated_at = time.time()

    def set_active_file(self, path: Optional[str]) -> None:
        with self._lock:
            self.active_file = str(path) if path else None
            self.updated_at = time.time()

    def set_foreground_app(self, app: Optional[str]) -> None:
        with self._lock:
            self.foreground_app = str(app) if app else None
            self.updated_at = time.time()

    def set_read_only(self, flag: bool) -> None:
        with self._lock:
            self.read_only = bool(flag)
            self.updated_at = time.time()

    def set_identity(self, **fields) -> None:
        with self._lock:
            self.identity.update({k: v for k, v in fields.items() if v is not None})
            self.updated_at = time.time()

    # ── salida para el prompt y para los subagentes ─────────────────────────

    def context_block(self) -> str:
        """Bloque de texto para inyectar en el prompt. Vacío si no hay nada."""
        lines: list[str] = []
        with self._lock:
            recent = self.convo_ctx[-_CONVO_BLOCK_N:]
            summary = self.session_summary
            root = self.project_root
            active = self.active_file
            fg = self.foreground_app
            ro = self.read_only
        if root:
            lines.append(f"Proyecto: {root}")
        if active:
            lines.append(f"Archivo activo: {active}")
        if fg:
            lines.append(f"App en foco: {fg}")
        if ro:
            lines.append("Modo: SOLO LECTURA (no editar archivos)")
        if summary:
            lines.append(f"Resumen de sesión: {summary}")
        if recent:
            lines.append("Venimos hablando: " + " | ".join(recent))
        if not lines:
            return ""
        return "[CONTEXTO COMPARTIDO]\n" + "\n".join(f"- {l}" for l in lines)

    def as_dict(self) -> dict:
        """Vista serializable para pasársela a los subagentes (`execute(task, ctx)`)."""
        with self._lock:
            return {
                "convo_ctx": list(self.convo_ctx),
                "session_summary": self.session_summary,
                "project_root": self.project_root,
                "active_file": self.active_file,
                "foreground_app": self.foreground_app,
                "identity": dict(self.identity),
                "read_only": self.read_only,
            }

    def snapshot(self) -> dict:
        d = self.as_dict()
        d["updated_at"] = self.updated_at
        return d

    def clear(self) -> None:
        with self._lock:
            self.convo_ctx = []
            self.session_summary = ""
            self.project_root = None
            self.active_file = None
            self.foreground_app = None
            self.identity = dict(_DEFAULT_IDENTITY)
            self.read_only = False
            self.updated_at = time.time()


_singleton: Optional[SharedContext] = None
_singleton_lock = threading.Lock()


def get_shared_context() -> SharedContext:
    """Devuelve el contexto compartido del proceso (lo crea la primera vez)."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = SharedContext()
    return _singleton


def reset_shared_context() -> SharedContext:
    """Descarta el singleton y devuelve uno limpio (para tests)."""
    global _singleton
    with _singleton_lock:
        _singleton = SharedContext()
    return _singleton
