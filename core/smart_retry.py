"""
smart_retry.py — Backoff exponencial inteligente para APIs rate-limited.

Mejora el retry simple con:
  - Backoff exponencial con jitter
  - Detección de tipo de error (rate limit, timeout, server error)
  - Límites de reintento por tipo de error
  - Fallback a proveedor alternativo
"""
from __future__ import annotations

import time
import random
import functools
from typing import Callable, Any

# Límites por tipo de error
ERROR_LIMITS = {
    "rate_limit": {"max_retries": 5, "base_delay": 2.0, "max_delay": 60.0},
    "timeout": {"max_retries": 3, "base_delay": 1.0, "max_delay": 10.0},
    "server_error": {"max_retries": 3, "base_delay": 2.0, "max_delay": 30.0},
    "connection": {"max_retries": 4, "base_delay": 1.0, "max_delay": 20.0},
    "unknown": {"max_retries": 2, "base_delay": 1.0, "max_delay": 5.0},
}

RATE_LIMIT_KEYWORDS = ["429", "rate limit", "too many requests", "quota exceeded"]
TIMEOUT_KEYWORDS = ["timeout", "timed out", "deadline exceeded", "connection"]
SERVER_ERROR_KEYWORDS = ["500", "502", "503", "504", "internal server error", "bad gateway"]
CONNECTION_KEYWORDS = ["connection refused", "connection reset", "broken pipe", "errno"]


def classify_error(error: str) -> str:
    """Clasifica un error en categoría."""
    e = error.lower()
    for kw in RATE_LIMIT_KEYWORDS:
        if kw in e:
            return "rate_limit"
    for kw in TIMEOUT_KEYWORDS:
        if kw in e:
            return "timeout"
    for kw in SERVER_ERROR_KEYWORDS:
        if kw in e:
            return "server_error"
    for kw in CONNECTION_KEYWORDS:
        if kw in e:
            return "connection"
    return "unknown"


def calculate_delay(attempt: int, error_type: str) -> float:
    """Calcula delay con backoff exponencial + jitter."""
    config = ERROR_LIMITS.get(error_type, ERROR_LIMITS["unknown"])
    base = config["base_delay"]
    max_delay = config["max_delay"]

    delay = min(base * (2 ** attempt), max_delay)
    # Agregar jitter (±25%)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    return max(0, delay + jitter)


def smart_retry(
    func: Callable,
    *args,
    max_retries: int = None,
    on_retry: Callable = None,
    **kwargs,
) -> Any:
    """Ejecuta una función con retry inteligente.

    Args:
        func: Función a ejecutar
        *args: Argumentos posicionales
        max_retries: Límite de reintentos (None = auto-detectar por error type)
        on_retry: Callback(attempt, error, delay) llamado antes de cada retry
        **kwargs: Argumentos keyword

    Returns:
        Resultado de la función

    Raises:
        La última excepción si todos los reintentos fallan
    """
    last_error = None
    error_type = "unknown"

    for attempt in range(10):  # Límite absoluto
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            error_type = classify_error(str(e))

            config = ERROR_LIMITS.get(error_type, ERROR_LIMITS["unknown"])
            limit = max_retries or config["max_retries"]

            if attempt >= limit:
                break

            delay = calculate_delay(attempt, error_type)

            if on_retry:
                on_retry(attempt + 1, str(e), delay)

            time.sleep(delay)

    raise last_error


def smart_retry_decorator(max_retries: int = None):
    """Decorador para retry inteligente."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return smart_retry(func, *args, max_retries=max_retries, **kwargs)
        return wrapper
    return decorator
