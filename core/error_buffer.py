"""
core/error_buffer.py
────────────────────
Buffer en memoria de los errores recientes de Eris, consultable.

Por qué existe
──────────────
Los errores pueden pasar desapercibidos: `_TeeStream` de `logging_setup`
escribía y se tragaba las excepciones en silencio, y un traceback en `eris.log`
no le dice nada a nadie hasta que se va a leer el archivo a mano. Este buffer
registra en memoria los últimos tracebacks/errores que ven la luz por
`sys.stderr` y los expone:

  - al chat, vía `diagnostico action=logs`/`errores`,
  - al guardián/auto_salud, que puede consultar `recent_errors()`,
  - a la UI, cuando quiera pintarlos.

Es solo memoria: no duplica `eris.log`, no escribe nada en disco. Si el proceso
se cae, el buffer muere con él (para eso está `eris.log` con rotación).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Optional

__all__ = ["record_error", "recent_errors", "clear_errors", "error_count", "MAX_ERRORS"]

#: Cuántos errores retener. Suficiente para pintar la última hora; barato.
MAX_ERRORS = 200

_lock = threading.RLock()
#: deque[dict]: time, text, source. Los más nuevos al final.
_errors: deque[dict] = deque(maxlen=MAX_ERRORS)
_newest_ts: float = 0.0


def record_error(text: str, *, source: str = "runtime", context: Optional[dict] = None) -> None:
    """Registra un error en el buffer (thread-safe, nunca lanza)."""
    global _newest_ts
    if not isinstance(text, str) or not text.strip():
        return
    try:
        with _lock:
            _errors.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "ts": time.time(),
                "text": text.strip()[:2000],
                "source": source,
                "context": context or {},
            })
            _newest_ts = time.time()
    except Exception:
        pass  # el buffer nunca rompe la ejecución: esa es su regla


def recent_errors(n: int = 50) -> list[dict]:
    """Los últimos `n` errores, del más reciente al más viejo."""
    with _lock:
        out = list(_errors)
    return list(reversed(out[-n:]))


def error_count() -> int:
    """Cuántos errores hay registrados desde el arranque (o el último clear)."""
    with _lock:
        return len(_errors)


def clear_errors() -> int:
    """Vacía el buffer. Devuelve cuántos errores había."""
    global _newest_ts
    with _lock:
        n = len(_errors)
        _errors.clear()
        _newest_ts = 0.0
        return n


def last_error() -> Optional[dict]:
    """El error más reciente, o None."""
    with _lock:
        return _errors[-1] if _errors else None