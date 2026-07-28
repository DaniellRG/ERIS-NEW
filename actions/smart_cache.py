"""
smart_cache.py — Cache inteligente LRU con TTL para respuestas frecuentes.
Evita recomputación de resultados costosos (RAG queries, code review, etc.)
"""
import json
import time
import hashlib
from collections import OrderedDict
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_CACHE_FILE = _BASE / "data" / "smart_cache.json"
_STATS_FILE = _BASE / "data" / "cache_stats.json"

DEFAULT_TTL = 300  # 5 minutes
MAX_ENTRIES = 500
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


class LRUCache:
    def __init__(self, max_entries=MAX_ENTRIES, default_ttl=DEFAULT_TTL):
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self._cache = OrderedDict()
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}

    def get(self, key: str):
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["created_at"] < entry["ttl"]:
                self._cache.move_to_end(key)
                entry["access_count"] = entry.get("access_count", 0) + 1
                entry["last_accessed"] = time.time()
                self._stats["hits"] += 1
                return entry["value"]
            else:
                del self._cache[key]
                self._stats["misses"] += 1
                return None
        self._stats["misses"] += 1
        return None

    def set(self, key: str, value, ttl: int = None):
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self.max_entries:
            self._cache.popitem(last=False)
            self._stats["evictions"] += 1
        self._cache[key] = {
            "value": value,
            "created_at": time.time(),
            "ttl": ttl or self.default_ttl,
            "access_count": 0,
            "last_accessed": time.time(),
        }
        self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self):
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)

    def get_stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        return {
            **self._stats,
            "total": total,
            "hit_rate": round(hit_rate * 100, 1),
            "entries": len(self._cache),
            "max_entries": self.max_entries,
        }

    def cleanup(self):
        now = time.time()
        expired = [k for k, v in self._cache.items()
                   if now - v["created_at"] >= v["ttl"]]
        for k in expired:
            del self._cache[k]
        return len(expired)

    def export(self) -> dict:
        return {k: {"value": v["value"], "created_at": v["created_at"],
                     "ttl": v["ttl"], "access_count": v.get("access_count", 0)}
                for k, v in self._cache.items()}

    def import_data(self, data: dict):
        for k, v in data.items():
            if time.time() - v["created_at"] < v["ttl"]:
                self._cache[k] = v
                self._cache.move_to_end(k)


_cache = LRUCache()


def smart_cache(parameters: dict = None, player=None) -> str:
    """Cache inteligente."""
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "get":
        return _cache_get(params)
    elif action == "set":
        return _cache_set(params)
    elif action == "delete":
        return _cache_delete(params)
    elif action == "clear":
        return _cache_clear()
    elif action == "cleanup":
        return _cache_cleanup()
    elif action == "stats":
        return _cache_stats()
    elif action == "top":
        return _cache_top(params)
    elif action == "status":
        return _get_status()
    elif action == "save":
        return _save_to_disk()
    elif action == "load":
        return _load_from_disk()
    elif action == "invalidate":
        return _invalidate_pattern(params)
    elif action == "warm":
        return _warm_cache()
    elif action == "export":
        return _export_cache()
    return "Acciones: get, set, delete, clear, cleanup, stats, top, status, save, load, invalidate, warm, export"


def _cache_get(params: dict) -> str:
    key = params.get("key", "")
    if not key:
        return "Error: se requiere 'key'"
    value = _cache.get(key)
    if value is not None:
        preview = str(value)[:200]
        return "Cache HIT [{}]:\n{}".format(key, preview)
    return "Cache MISS: {}".format(key)


def _cache_set(params: dict) -> str:
    key = params.get("key", "")
    value = params.get("value", "")
    ttl = int(params.get("ttl", DEFAULT_TTL))
    if not key:
        return "Error: se requiere 'key'"
    _cache.set(key, value, ttl)
    return "Cache SET: {} (TTL={}s)".format(key, ttl)


def _cache_delete(params: dict) -> str:
    key = params.get("key", "")
    if _cache.delete(key):
        return "Cache DELETE: {}".format(key)
    return "No encontrado: {}".format(key)


def _cache_clear() -> str:
    count = _cache.size()
    _cache.clear()
    return "Cache cleared: {} entries eliminados".format(count)


def _cache_cleanup() -> str:
    removed = _cache.cleanup()
    return "Cleanup: {} entries expirados eliminados".format(removed)


def _cache_stats() -> str:
    stats = _cache.get_stats()
    lines = [
        "═══ CACHE STATS ═══",
        "",
        "  Entries:    {}/{}".format(stats["entries"], stats["max_entries"]),
        "  Hits:       {}".format(stats["hits"]),
        "  Misses:     {}".format(stats["misses"]),
        "  Hit Rate:   {}%".format(stats["hit_rate"]),
        "  Sets:       {}".format(stats["sets"]),
        "  Evictions:  {}".format(stats["evictions"]),
    ]
    return "\n".join(lines)


def _cache_top(params: dict) -> str:
    limit = int(params.get("limit", 10))
    entries = []
    for k, v in _cache._cache.items():
        entries.append({
            "key": k,
            "access_count": v.get("access_count", 0),
            "ttl_remaining": max(0, int(v["ttl"] - (time.time() - v["created_at"]))),
        })
    entries.sort(key=lambda x: x["access_count"], reverse=True)
    lines = ["═══ TOP CACHE ENTRIES ═══", ""]
    for e in entries[:limit]:
        lines.append("  {} (hits={}, TTL={}s)".format(
            e["key"], e["access_count"], e["ttl_remaining"]))
    return "\n".join(lines)


def _get_status() -> str:
    stats = _cache.get_stats()
    return "Cache: {}/{} entries, {}% hit rate, {} hits, {} misses".format(
        stats["entries"], stats["max_entries"], stats["hit_rate"],
        stats["hits"], stats["misses"])


def _save_to_disk() -> str:
    data = _cache.export()
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
    return "Cache guardado: {} entries".format(len(data))


def _load_from_disk() -> str:
    if not _CACHE_FILE.exists():
        return "No hay cache en disco"
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        _cache.import_data(data)
        return "Cache cargado: {} entries".format(_cache.size())
    except Exception as e:
        return "Error cargando cache: {}".format(str(e))


def _invalidate_pattern(params: dict) -> str:
    pattern = params.get("pattern", "")
    if not pattern:
        return "Error: se requiere 'pattern'"
    removed = 0
    keys = list(_cache._cache.keys())
    for k in keys:
        if pattern in k:
            _cache.delete(k)
            removed += 1
    return "Invalidados: {} entries con pattern '{}'".format(removed, pattern)


def _warm_cache() -> str:
    """Precarga el cache con datos frecuentes."""
    warmed = 0
    try:
        from core.tool_registry import get_tool
        for tool_name in ["system_monitor", "self_awareness", "document_rag"]:
            f = get_tool(tool_name)
            if f:
                key = "warm:{}".format(tool_name)
                result = f(parameters={"action": "status"})
                _cache.set(key, str(result), ttl=600)
                warmed += 1
    except:
        pass
    return "Cache warmed: {} entries precargados".format(warmed)


def _export_cache() -> str:
    data = _cache.export()
    lines = ["═══ CACHE EXPORT ({}) ═══".format(len(data)), ""]
    for k, v in list(data.items())[:20]:
        lines.append("  {} — hits={}, TTL={}s".format(
            k, v.get("access_count", 0), v.get("ttl", 0)))
    return "\n".join(lines)
