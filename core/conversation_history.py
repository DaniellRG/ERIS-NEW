"""
Historial de conversaciones — persistencia JSON en data/conversations/.

Cada conversación es un JSON:
    data/conversations/<session_id>.json
    {
      "id":        "20260907-143022",
      "title":     "App CalculoConsumoAgua (Java)",
      "created":   "2026-09-07T14:30:22",
      "updated":   "2026-09-07T15:04:11",
      "messages":  [ {"role": "user"|"eris", "text": "...", "ts": "..."} ],
      "summary":   "resumen comprimido de lo viejo (generado al retomar)"
    }

El título se genera automáticamente desde los primeros mensajes del usuario.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path

from core.logging_setup import BASE_DIR  # type: ignore  (fallback abajo)

CONV_DIR: Path = Path(BASE_DIR) / "data" / "conversations"

# Palabras vacías para el título automático (español)
_STOPWORDS = {
    "hola", "hay", "hey", "eris", "e", "el", "la", "los", "las", "un", "una",
    "unos", "unas", "yo", "me", "mi", "con", "de", "del", "que", "cual",
    "necesito", "quiero", "puedes", "podés", "podes", "ayudar", "ayuda",
    "ayudame", "ayudame", "por", "favor", "como", "cómo", "una", "algo",
    "buenas", "buenos", "dias", "días", "tardes", "noches", "cuando", "donde",
}

_ID_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"
_TITLE_MAX = 60


def ensure_dir() -> Path:
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    return CONV_DIR


def new_session_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _tidy(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip())


def make_title(text: str) -> str:
    """Genera un título corto desde el primer mensaje del usuario."""
    words = _tidy(text).split()
    kept: list[str] = []
    for w in words:
        core_w = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]", "", w).lower()
        if core_w in _STOPWORDS or not core_w:
            continue
        kept.append(w)
        if len(kept) >= 4:
            break
    title = " ".join(kept) if kept else _tidy(text)[:40]
    if len(title) > _TITLE_MAX:
        title = title[:_TITLE_MAX].rstrip() + "…"
    return title or "Conversación"


def list_conversations() -> list[dict]:
    """Lista de {id, title, created, updated, msg_count} ordenada por updated desc."""
    ensure_dir()
    out = []
    for f in CONV_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            msgs = data.get("messages") or []
            out.append({
                "id": f.stem,
                "title": data.get("title") or make_title(msgs[0].get("text", "")) if msgs else f.stem,
                "created": data.get("created", ""),
                "updated": data.get("updated", ""),
                "msg_count": len(msgs),
            })
        except Exception:
            continue
    out.sort(key=lambda c: c["updated"], reverse=True)
    return out


def load_conversation(session_id: str) -> dict:
    ensure_dir()
    f = CONV_DIR / f"{session_id}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"id": session_id, "title": "Conversación", "created": _ts(), "updated": _ts(), "messages": []}


def save_conversation(conv: dict) -> None:
    ensure_dir()
    f = CONV_DIR / f"{conv.get('id') or new_session_id()}.json"
    # JSON UTF-8, indentado, sin espacios extras en separadores
    f.write_text(
        json.dumps(conv, ensure_ascii=False, indent=2).replace("\n ", "\n\t"),
        encoding="utf-8",
    )


def rename_conversation(session_id: str, new_title: str) -> bool:
    """Renombra una conversación. Devuelve True si se persistió."""
    f = CONV_DIR / f"{session_id}.json"
    if not f.exists():
        return False
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return False
    new_title = _tidy(new_title)[:80]
    if not new_title:
        new_title = "Conversación"
    data["title"] = new_title
    f.write_text(
        json.dumps(data, ensure_ascii=False, indent=2).replace("\n ", "\n\t"),
        encoding="utf-8",
    )
    return True


def delete_conversation(session_id: str) -> bool:
    """Elimina una conversación del disco. Devuelve True si existía."""
    f = CONV_DIR / f"{session_id}.json"
    if f.exists():
        try:
            f.unlink()
            return True
        except Exception:
            return False
    return False


def build_resume_context(conv: dict, recent_limit: int = 15, summary_max: int = 1800) -> str:
    """Bloque de texto para inyectar al retomar una conversación vieja:
    últimos N mensajes textuales + resumen comprimido de lo viejo."""
    msgs = conv.get("messages") or []
    if not msgs:
        return ""
    recent = msgs[-recent_limit:]
    older = msgs[:-recent_limit] if len(msgs) > recent_limit else []

    lines: list[str] = []
    if older:
        old_lines = []
        for m in older:
            role = "Usuario" if m.get("role") == "user" else "ERIS"
            txt = re.sub(r"\s+", " ", str(m.get("text", ""))).strip()
            if len(txt) > 120:
                txt = txt[:120] + "…"
            if txt:
                old_lines.append(f"{role}: {txt}")
        digest = " | ".join(old_lines)
        if len(digest) > summary_max:
            digest = digest[:summary_max] + "…"
        paragraphs = ("HABLARON ANTES (resumen de lo viejo): " + digest)
        lines.append(paragraphs[:summary_max + 120])
    if recent:
        lines.append("ÚLTIMOS MENSAJES DE LA CONVERSACIÓN:")
        for m in recent:
            role = "Usuario" if m.get("role") == "user" else "ERIS"
            txt = _tidy(str(m.get("text", "")))
            if len(txt) > 400:
                txt = txt[:400] + "…"
            lines.append(f"{role}: {txt}")
    return "\n".join(lines)