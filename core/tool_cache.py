"""
tool_cache.py — Caché semántico de resultados de herramientas para ERIS.

Si el usuario (o el agente) pregunta lo mismo o similar, reutiliza el
resultado cacheado en vez de re-ejecutar la herramienta.

Caché:
  - Clave: hash de (tool_name + args serializados)
  - TTL: configurable por tool (default 300s = 5 min)
  - Límite: máximo 200 entradas (LRU)
  - Stats: hits/misses para métricas
"""
from __future__ import annotations

import json
import time
import hashlib
import threading
from pathlib import Path
from collections import OrderedDict

_BASE = Path(__file__).resolve().parent.parent
_CACHE_FILE = _BASE / "data" / "tool_cache.json"

# TTL por defecto (segundos)
_DEFAULT_TTL = 300
_MAX_ENTRIES = 200

# Tools que NUNCA se cachean (efectos secundarios)
_NO_CACHE = {
    "shell", "file_write", "file_delete", "file_edit", "self_edit",
    "agent_loop", "task_planner", "memory_consolidation", "task_scheduler",
    "github_pr", "github_push",
}


class ToolCache:
    """Caché LRU con TTL para resultados de herramientas."""

    def __init__(self, max_entries: int = _MAX_ENTRIES):
        self._cache: OrderedDict = OrderedDict()
        self._max = max_entries
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._load()

    def _load(self):
        try:
            if _CACHE_FILE.exists():
                data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        self._cache[k] = v
        except Exception:
            pass

    def _save(self):
        try:
            _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            # Guardar solo entradas no expiradas
            now = time.time()
            valid = {k: v for k, v in self._cache.items()
                     if v.get("expires", 0) > now}
            _CACHE_FILE.write_text(
                json.dumps(valid, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def _key(self, tool_name: str, args: dict) -> str:
        raw = f"{tool_name}:{json.dumps(args, sort_keys=True, ensure_ascii=False)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get(self, tool_name: str, args: dict) -> str | None:
        """Busca en caché. Devuelve el resultado o None si no está/expiró."""
        if tool_name in _NO_CACHE:
            return None

        key = self._key(tool_name, args)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.get("expires", 0) < time.time():
                del self._cache[key]
                self._misses += 1
                return None
            # Mover al final (más reciente)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.get("result")

    def set(self, tool_name: str, args: dict, result: str, ttl: int = _DEFAULT_TTL):
        """Guarda un resultado en caché."""
        if tool_name in _NO_CACHE:
            return
        if len(result) > 50000:  # No cachear resultados enormes
            return

        key = self._key(tool_name, args)
        with self._lock:
            self._cache[key] = {
                "tool": tool_name,
                "result": result,
                "created": time.time(),
                "expires": time.time() + ttl,
            }
            # LRU eviction
            while len(self._cache) > self._max:
                self._cache.popitem(last=False)
            self._save()

    def stats(self) -> dict:
        """Estadísticas del caché."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "entries": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{self._hits/total*100:.1f}%" if total > 0 else "0%",
                "max_entries": self._max,
            }

    def clear(self):
        """Limpia todo el caché."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._save()

    def cleanup_expired(self) -> int:
        """Elimina entradas expiradas. Devuelve cuántas se eliminaron."""
        now = time.time()
        removed = 0
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.get("expires", 0) < now]
            for k in expired:
                del self._cache[k]
                removed += 1
            if removed:
                self._save()
        return removed


# Singleton
_tool_cache: ToolCache | None = None


def get_tool_cache() -> ToolCache:
    global _tool_cache
    if _tool_cache is None:
        _tool_cache = ToolCache()
    return _tool_cache


def cached_tool_call(tool_name: str, args: dict, func, *func_args, **func_kwargs) -> str:
    """Ejecuta una tool con caché: si el resultado está cacheado, lo reutiliza."""
    cache = get_tool_cache()
    cached = cache.get(tool_name, args)
    if cached is not None:
        return cached

    result = func(*func_args, **func_kwargs)
    result_str = str(result)
    cache.set(tool_name, args, result_str)
    return result_str
