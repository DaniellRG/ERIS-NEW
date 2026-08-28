# -*- coding: utf-8 -*-
"""
core/command_deck.py — COLA DE COMANDOS (Command Deck) de ERIS.

Registra cada intent ejecutado (tool call del LLM) con su status y resultado,
para que el HUD muestre "qué se va a ejecutar / qué se ejecutó" al estilo
JARVIS. Backend: data/command_deck.json (append-only, top N, sin base de datos).
"""
import json
import threading
import time
from pathlib import Path

_DECK_FILE = Path(__file__).resolve().parent.parent / "data" / "command_deck.json"
_MAX_ENTRIES = 60
_RUNNING_TIMEOUT = 180  # segundos: un "running" colgado se marca done(timeout) al render
_LOCK = threading.Lock()

# Map pequeño tool -> agente (no importamos agent_router para no acoplar)
_TOOL_AGENT = {
    # DevAgent
    "terminal_agent": "Dev", "git_control": "Dev", "code_generator": "Dev",
    "code_copilot": "Dev", "test_runner": "Dev", "code_assistant": "Dev",
    "ide_integration": "Dev", "code_helper": "Dev", "file_read": "Dev",
    "file_write": "Dev", "file_edit": "Dev", "file_api": "Dev",
    # WebAgent
    "web_search": "Web", "browser_navigate": "Web", "webfetch": "Web",
    "super_search": "Web", "deep_research": "Web", "browser_unified": "Web",
    "just_scrape": "Web", "research": "Web",
    # CommAgent
    "email_manager": "Comm", "calendar_manager": "Comm", "reminders": "Comm",
    "whatsapp_web": "Comm", "telegram_bot": "Comm", "notification_center": "Comm",
    # MediaAgent
    "music_player": "Media", "image_analyzer": "Media", "screen_vision": "Vision",
    "ocr_reader": "Vision", "camera_bus": "Vision",
    # StudiesAgent
    "studies_agent": "Studies", "quiz_agent": "Studies", "flashcards": "Studies",
    # SecurityAgent
    "security_shield": "Security", "cybersecurity": "Security", "osint_agent": "Security",
    "credential_recovery": "Security", "active_firewall": "Security",
    "ransomware_shield": "Security", "keylogger_detector": "Security",
    "disk_wiper": "Security", "file_encryptor": "Security",
    # FileAgent / Core
    "file_manager": "File", "pdf_manager": "File", "document_creator": "File",
    "template_engine": "File", "data_analyst": "Data", "data_viz": "Data",
    "context_engine": "Context", "memory_rag": "Memory", "save_memory": "Memory",
}


def _agent_for(tool: str) -> str:
    return _TOOL_AGENT.get(tool, "")


def _short_args(args: dict) -> str:
    items = []
    for k, v in (args or {}).items():
        try:
            s = str(v).replace("\n", " ")
        except Exception:
            s = "?"
        if len(s) > 60:
            s = s[:57] + "..."
        items.append(f"{k}={s}")
    joined = ", ".join(items)
    return joined[:160]


def _load() -> list:
    if _DECK_FILE.exists():
        try:
            data = json.loads(_DECK_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def _save(deck: list):
    try:
        _DECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DECK_FILE.write_text(
            json.dumps(deck, indent=1, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def log_intent(tool: str, args: dict = None, status: str = "running",
               result: str = "", agent: str = ""):
    """Registra un intent ejecutado por el LLM.

    status='running'  → agrega una entrada nueva al tope.
    status='done'/'error' → cierra la última entrada 'running' del mismo tool.
    """
    if not tool:
        return
    now = time.time()
    with _LOCK:
        deck = _load()
        if status in ("done", "error"):
            for entry in deck:
                if entry.get("tool") == tool and entry.get("status") == "running":
                    entry["status"] = status
                    entry["result"] = (result or "")[:160]
                    entry["ts_end"] = now
                    break
            else:
                deck.insert(0, {
                    "ts": now, "tool": tool,
                    "args": _short_args(args or {}),
                    "status": status, "result": (result or "")[:160],
                    "agent": agent or _agent_for(tool),
                    "ts_end": now,
                })
        else:
            deck.insert(0, {
                "ts": now, "tool": tool,
                "args": _short_args(args or {}),
                "status": "running",
                "agent": agent or _agent_for(tool),
            })
        deck = deck[:_MAX_ENTRIES]
        _save(deck)


def read_deck(limit: int = 30) -> list:
    """Devuelve el deck aplicando envejecimiento de 'running' colgados."""
    with _LOCK:
        deck = _load()
    now = time.time()
    for entry in deck:
        if entry.get("status") == "running":
            start = entry.get("ts") or now
            if now - start > _RUNNING_TIMEOUT:
                entry["status"] = "done"
                entry["result"] = "(timeout)"
    return deck[:limit]


def deck_status() -> dict:
    with _LOCK:
        deck = _load()
    running = sum(1 for e in deck if e.get("status") == "running")
    pending = sum(1 for e in deck if e.get("status") == "pending")
    total = len(deck)
    return {"running": running, "pending": pending, "total": total}


def clear_deck():
    with _LOCK:
        _save([])