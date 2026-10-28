# -*- coding: utf-8 -*-
"""
core/action_repeat_guard.py — Evita repetir acciones innecesarias.

Cuando Eris ya hizo una investigación/búsqueda/lectura para resolver algo
similar, no debe repetirla. Solo permite repetir cuando se trata de:
  - Programar/codificar/editar/corregir código
  - Probar/verificar/correr tests/build
  - Diagnosticar/depurar cuando algo realmente falló
  - Trabajos que requieren validación iterativa

"Ya lo hice" vale. No repetir por costumbre.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from collections import deque
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_FILE = _BASE / "memory" / "action_repeat_guard.json"

# Acciones que SÍ pueden repetirse (trabajo iterativo)
REPEAT_ALLOWED = {
    "file_edit", "file_write", "safe_edit", "patch_file",
    "terminal_agent", "shell_execute", "shell_session",
    "code_assistant", "code_helper", "ide_integration",
    "test_runner", "run_tests", "pytest",
    "git_control", "git_commit", "git_push",
    "debugger", "diagnostico", "code_guard",
    "self_edit", "fix_file",
}

# Acciones que NO deberían repetirse si ya se hicieron para lo mismo
INVESTIGATIVE = {
    "web_search", "webfetch", "deep_research", "super_search",
    "file_read", "file_manager", "read_file", "knowledge_base",
    "memory_retrieve", "semantic_search", "rag_search",
    "learning_engine", "investigar",
}

_STOPWORDS = {"que", "como", "para", "con", "del", "una", "los", "las", "por", "sin", "sobre", "hay", "quiero", "necesito", "puedes", "haz"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^\w\s]", " ", s.lower()).strip()


def _tokens(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9_]{3,}", _norm(s)) if t not in _STOPWORDS}


def _load() -> dict:
    try:
        if _FILE.exists():
            d = json.loads(_FILE.read_text(encoding="utf-8"))
            if isinstance(d, dict): return d
    except Exception:
        pass
    return {"history": [], "by_query": {}}


def _save(d: dict):
    try:
        _FILE.parent.mkdir(parents=True, exist_ok=True)
        # Keep last 50
        hist = d.get("history", [])
        d["history"] = hist[-50:]
        _FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def record_action(tool: str, args: dict = None, query: str = "", result_summary: str = ""):
    """Registra que se hizo una acción para un pedido."""
    try:
        d = _load()
        now = time.time()
        entry = {
            "tool": tool,
            "query": _norm(query)[:200],
            "args_key": _norm(json.dumps(args or {}, default=str))[:120],
            "ts": now,
            "ok": "error" not in str(result_summary).lower()[:50]
        }
        d["history"].append(entry)
        # index by query signature
        sig = " ".join(sorted(_tokens(query)))[:60]
        if sig:
            d["by_query"].setdefault(sig, []).append({"tool": tool, "ts": now})
        _save(d)
    except Exception:
        pass


def should_repeat(tool: str, args: dict = None, query: str = "") -> tuple[bool, str]:
    """True si DEBE repetirse, False si debería evitarlo."""
    tool = tool or ""
    if tool in REPEAT_ALLOWED:
        return True, ""  # iterativo, permitir
    
    if tool not in INVESTIGATIVE:
        return True, ""
    
    # Es investigativo - revisar si ya lo hizo para mismo query
    d = _load()
    hist = d.get("history", [])
    now = time.time()
    qtok = _tokens(query)
    if not qtok:
        return True, ""
    
    # Buscar coincidencias recientes (últimos 10 min)
    for h in reversed(hist[-20:]):
        if h.get("tool") != tool:
            continue
        if now - float(h.get("ts", 0)) > 600:  # 10 min
            continue
        hq = h.get("query", "")
        htok = set(hq.split()) if hq else set()
        if htok and (qtok & htok):
            overlap = len(qtok & htok) / max(1, len(qtok))
            if overlap >= 0.4:  # 40% similar
                return False, f"Ya investigué esto antes con {tool}. No repetir innecesariamente."
    
    return True, ""


def inject_reminder(query: str = "") -> str:
    """Inyecta recordatorio en contexto si hay acciones repetidas evitables."""
    if not query:
        return ""
    d = _load()
    hist = d.get("history", [])
    now = time.time()
    qtok = _tokens(query)
    if not qtok or not hist:
        return ""
    
    done = []
    for h in reversed(hist[-15:]):
        if now - float(h.get("ts", 0)) > 900:  # 15 min
            continue
        if h.get("tool") in REPEAT_ALLOWED:
            continue
        hq = h.get("query", "")
        htok = set(hq.split()) if hq else set()
        if htok and (qtok & htok) and len(qtok & htok)/max(1,len(qtok)) >= 0.35:
            done.append(h.get("tool"))
    
    if done:
        unique = list(dict.fromkeys(done))
        return f"[NO REPETIR] Ya hice {', '.join(unique[:3])} para algo muy similar recientemente. Si ya tengo la respuesta, usala directamente. Solo repetir si el resultado fue insuficiente o cambió el pedido."
    return ""


def status() -> str:
    d = _load()
    return f"Acciones registradas: {len(d.get('history',[]))}"


__all__ = ["record_action", "should_repeat", "inject_reminder", "status", "REPEAT_ALLOWED", "INVESTIGATIVE"]
