# -*- coding: utf-8 -*-
"""
core/tracer.py — Trazado de handoffs multi-agente.
Registra cada delegación de un agente en un log JSON para diagnóstico.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path

_TRACE_DIR = Path(__file__).resolve().parent.parent / "data"
_TRACE_FILE = _TRACE_DIR / "handoff_trace.json"

_lock = threading.Lock()
_MAX_ENTRIES = 200


class HandoffTracer:
    """Registra handoffs de agentes en un archivo JSON (con rotación)."""

    def trace_handoff(self, agent: str, text: str, result: str,
                      elapsed: float, success: bool = True, error: str = ""):
        entry = {
            "agent": agent,
            "text": str(text)[:200],
            "result": str(result)[:500],
            "elapsed": round(float(elapsed or 0), 3),
            "success": bool(success),
            "error": str(error)[:200],
            "timestamp": datetime.now().isoformat(),
        }
        with _lock:
            try:
                _TRACE_DIR.mkdir(parents=True, exist_ok=True)
                entries = []
                if _TRACE_FILE.exists():
                    try:
                        entries = json.loads(_TRACE_FILE.read_text("utf-8"))
                        if not isinstance(entries, list):
                            entries = []
                    except Exception:
                        entries = []
                entries.append(entry)
                entries = entries[-_MAX_ENTRIES:]
                _TRACE_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False), "utf-8")
            except Exception:
                pass


_tracer = HandoffTracer()
_tracer_lock = threading.Lock()


def get_tracer() -> HandoffTracer:
    return _tracer
