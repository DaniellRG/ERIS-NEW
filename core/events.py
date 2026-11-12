# -*- coding: utf-8 -*-
"""
core/events.py — Event bus pub/sub para desacoplar GUI del núcleo.

Permite que ErisLive (núcleo) emita eventos sin saber quién escucha, y que
la UI (o cualquier daemon) se suscriba a los que le interese. Thread-safe:
una copia de la lista de handlers se toma bajo lock antes de invocar, así
un handler puede desuscribirse o lanzar sin tumbar el bus ni a los demás.

Uso:
    from core.events import get_event_bus
    bus = get_event_bus()
    bus.on("nueva_respuesta", mi_handler)
    bus.emit("nueva_respuesta", texto="Hola")

No importa PyQt6 ni modulos pesados: solo stdlib. Importable desde main.py,
eris_cli.py y cualquier subagente/daemon.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable, Optional


class EventBus:
    """Bus de eventos pub/sub, thread-safe."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._lock = threading.RLock()

    def on(self, event: str, handler: Callable) -> None:
        """Registra `handler` para `event`."""
        with self._lock:
            self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable) -> None:
        """Elimina `handler` de `event` si estaba registrado."""
        with self._lock:
            handlers = self._handlers.get(event, [])
            if handler in handlers:
                handlers.remove(handler)

    def emit(self, event: str, *args, **kwargs) -> None:
        """Emite `event` a todos los handlers registrados.

        Se toma una copia de la lista bajo lock, por lo que un handler puede
        llamarse a `off` durante la emisión sin afectar el recorrido actual.
        Un handler que lanza excepcion no detiene a los demas."""
        with self._lock:
            handlers = list(self._handlers.get(event, []))
        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception:
                # Un handler que falla no debe tumbar el bus ni a los demás.
                pass


_bus: Optional[EventBus] = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Devuelve el bus de eventos del proceso (singleton, lo crea la primera
    vez)."""
    global _bus
    if _bus is None:
        with _bus_lock:
            if _bus is None:
                _bus = EventBus()
    return _bus
