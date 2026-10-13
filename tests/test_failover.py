"""
tests/test_failover.py
──────────────────────
Fase 0.7: la cadena de failover tiene que ser REAL.

Definición de hecho del plan (`docs/superpowers/plans/2026-10-12-...-plan.md`):
un test que **caiga** el backend primario y compruebe que el secundario responde.

Además se fija la segunda mitad de la 0.7: `backend_name` no puede mentir
(antes omitía xKiro) y Ollama solo cuenta si el server responde de verdad
(el plan pedía "decidir qué hacer con Ollama"; la decisión es: último recurso,
disponible solo si `_check_ollama()` lo alcanza — nada de prometer un respaldo
apagado).

Los tests construyen la instancia sin correr `__init__` (que toca red, config y
key_manager): se usa `object.__new__` y se stubean los `_chat_*` para probar la
lógica de fallthrough aislando la red.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from core.gemini_text_chat import GeminiTextChat  # noqa: E402


# ── helpers ────────────────────────────────────────────────────────────────

def _bare(**flags) -> GeminiTextChat:
    """Instancia sin __init__ (sin red/config)."""
    c = object.__new__(GeminiTextChat)
    c._history = []
    c._use_gemini = flags.get("gemini", False)
    c._use_openrouter = flags.get("openrouter", False)
    c._use_xkairo = flags.get("xkairo", False)
    c._use_groq = flags.get("groq", False)
    c._use_ollama = flags.get("ollama", False)
    c._openrouter_model = "openrouter-model"
    c._xkairo_model = "xkairo-model"
    c._groq_model = "groq-model"
    c._ollama_model = "ollama-model"

    async def _noop() -> bool:
        return False

    c._compact_history = _noop  # type: ignore[assignment]
    return c


def _stub_backend(chat: GeminiTextChat, name: str, reply: str, calls: list[str]):
    """Asigna un `_chat_<name>` falso que registra la llamada y devuelve `reply`."""
    async def _fake(user_text: str, on_token=None) -> str:
        calls.append(name)
        return reply

    setattr(chat, f"_chat_{name}", _fake)


# ── backend_name honesto (bug 0.7) ──────────────────────────────────────────

def test_pick_backend_follows_real_order(monkeypatch):
    monkeypatch.setattr("core.gemini_text_chat._get_chat_model", lambda: "gm")
    c = _bare(gemini=True, openrouter=True, xkairo=True, groq=True, ollama=True)
    assert c._pick_backend() == "gemini:gm"
    c._use_gemini = False
    assert c._pick_backend() == "openrouter:openrouter-model"
    c._use_openrouter = False
    assert c._pick_backend() == "xkairo:xkairo-model"
    c._use_xkairo = False
    assert c._pick_backend() == "groq:groq-model"
    c._use_groq = False
    assert c._pick_backend() == "ollama:ollama-model"


def test_pick_backend_includes_xkairo_when_alone():
    """REGRESIÓN 0.7: si SOLO xKiro está disponible, backend_name mentía 'none'."""
    c = _bare(xkairo=True)
    assert c._pick_backend() == "xkairo:xkairo-model"


def test_pick_backend_none_when_nothing_available():
    """Ollama apagado/inalcanzable no se cuenta: no se promete un respaldo muerto."""
    assert _bare()._pick_backend() == "none"


# ── fallthrough real: cae el primario, responde el secundario ───────────────

def test_primary_fails_secondary_answers():
    c = _bare(gemini=True, openrouter=True)
    calls: list[str] = []
    _stub_backend(c, "gemini", "Error de Gemini: 429 cuota agotada", calls)
    _stub_backend(c, "openrouter", "respuesta del secundario", calls)

    out = asyncio.run(c.chat("hola"))
    assert out == "respuesta del secundario"
    assert calls == ["gemini", "openrouter"]


def test_gemini_falls_through_to_xkairo():
    c = _bare(gemini=True, xkairo=True)
    calls: list[str] = []
    _stub_backend(c, "gemini", "Error de Gemini: 400 INVALID_ARGUMENT", calls)
    _stub_backend(c, "xkairo", "respuesta de xKiro", calls)

    out = asyncio.run(c.chat("hola"))
    assert out == "respuesta de xKiro"
    assert calls == ["gemini", "xkairo"]


def test_chain_walks_until_ollama_last_resort():
    """Toda la nube cae: Ollama (local) cierra la cadena."""
    c = _bare(gemini=True, openrouter=True, xkairo=True, groq=True, ollama=True)
    calls: list[str] = []
    _stub_backend(c, "gemini", "Error de Gemini: caído", calls)
    _stub_backend(c, "openrouter", "Error de OpenRouter: 401", calls)
    _stub_backend(c, "xkairo", "Error de xKiro: sin key", calls)
    _stub_backend(c, "groq", "Error de Groq: timeout", calls)
    _stub_backend(c, "ollama", "respuesta local de Ollama", calls)

    out = asyncio.run(c.chat("hola"))
    assert out == "respuesta local de Ollama"
    assert calls == ["gemini", "openrouter", "xkairo", "groq", "ollama"]


def test_no_available_backend_is_honest():
    """Sin ningún backend no se inventa una respuesta."""
    c = _bare()
    out = asyncio.run(c.chat("hola"))
    assert out == "No hay backend de lenguaje disponible."


def test_error_reply_from_last_cloud_backend_does_not_pretend_success():
    """Un backend que devuelve 'Error de X' no se acepta como respuesta."""
    c = _bare(groq=True)  # sin ollama → la cadena queda vacía
    calls: list[str] = []
    _stub_backend(c, "groq", "Error de Groq: 429", calls)

    out = asyncio.run(c.chat("hola"))
    assert calls == ["groq"]
    assert out.startswith("No hay backend")
