"""
core/session_summaries.py — Resúmenes de sesión livianos.

Versión NO intrusiva de "recordar": no persiste el historial completo (eso
se removió a propósito). Guarda en memoria el epílogo de la conversación
actual y, al cerrarse, escribe un resumen de unas líneas en Obsidian
(Proyectos/) + un índice local acotado. Al despertar, Eris lee los últimos
resúmenes como contexto para retomar el hilo sin seguir hablando.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

from core.logging_setup import get_obsidian_vault

_BASE = Path(__file__).resolve().parent.parent
_INDEX_FILE = _BASE / "memory" / "session_summaries.json"
_MAX_RECORD = 60                 # máx intercambios en buffer de memoria
_MAX_INDEX = 20                  # máx resúmenes locales conservados
_MAX_SUMMARY_CHARS = 900         # longitud del resumen de sesión

_lock = threading.Lock()
_buffer: list[tuple[str, str, str]] = []   # (ts, user, eris)
_summary: list[str] = []


def record_exchange(user_text: str = "", eris_text: str = ""):
    """Acumula el intercambio actual SOLO en memoria (nunca a disco)."""
    user = (user_text or "").strip()
    eris = (eris_text or "").strip()
    if not user and not eris:
        return
    with _lock:
        _buffer.append((datetime.now().isoformat(timespec="minutes"), user, eris))
        if len(_buffer) > _MAX_RECORD:
            del _buffer[:len(_buffer) - _MAX_RECORD]


def _fold_buffer() -> str:
    """Comprime el buffer en un epílogo de unas líneas (sin LLM, sin costo)."""
    with _lock:
        rows = list(_buffer)
    out = []
    for ts, user, eris in rows:
        line = f"[{ts[11:16]}] ({user[:200] if user else '…'}) → {eris[:220] if eris else '…'}"
        out.append(line)
    blob = "\n".join(out)
    if len(blob) > _MAX_SUMMARY_CHARS:
        blob = blob[: _MAX_SUMMARY_CHARS] + "…"
    return blob


def _vault_path() -> Path:
    vault = get_obsidian_vault()
    try:
        return vault / "Proyectos"
    except Exception:
        return _BASE / "obsidian_vault" / "Proyectos"


def _load_index() -> list[dict]:
    if _INDEX_FILE.exists():
        try:
            data = json.loads(_INDEX_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def _save_index(entries: list[dict]):
    try:
        _INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        _INDEX_FILE.write_text(
            json.dumps(entries[-_MAX_INDEX:], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def finalize_session_summary() -> str | None:
    """Cierra la sesión actual: escribe el resumen en Obsidian + índice local.

    Devuelve la ruta del archivo creado, o None si no hubo nada que resumir.
    """
    blob = _fold_buffer()
    if not blob.strip():
        return None
    now = datetime.now()
    slug = now.strftime("%Y-%m-%d_%H%M")
    folder = _vault_path()
    try:
        folder.mkdir(parents=True, exist_ok=True)
        note = (
            f"# Resumen de sesión {slug}\n\n"
            f"_{now.strftime('%d/%m/%Y %H:%M')}_\n\n"
            f"{blob}\n"
        )
        path = folder / f"sesion_{slug}.md"
        path.write_text(note, encoding="utf-8")
    except Exception as e:
        print(f"[ERIS] ⚠️ No se pudo escribir resumen en vault: {e}")
        return None
    # Índice local acotado (contexto al despertar, sin historial completo)
    entries = _load_index()
    entries.append({"ts": now.isoformat(), "slug": slug,
                    "path": str(path), "tail": blob[-400:]})
    _save_index(entries)
    total = _fold_and_clear()
    print(f"[ERIS] 💾 Resumen de sesión guardado: {path} ({len(note)}b, total {total})")
    return str(path)


def _fold_and_clear() -> int:
    global _summary, _buffer
    with _lock:
        n = len(_buffer)
        _summary = _buffer[-8:]
        _buffer = []
    return n


def load_recent_summaries(limit: int = 3) -> list[str]:
    """Últimos resúmenes locales (para inyectar contexto al despertar)."""
    entries = _load_index()
    if not entries:
        return []
    texts = []
    for e in entries[-limit:]:
        first = ""
        if e.get("tail"):
            first = e["tail"].splitlines()[0][:120]
        if not first:
            first = e.get("slug", "")
        texts.append(f"[Sesión {e['ts'][:16]}] {first}")
    return texts


def sesiones(parameters=None, player=None) -> str:
    """Tool de resúmenes de sesión: reciente, epilogo, cerrar, indice."""
    import json as _json
    try:
        params = _json.loads(parameters) if isinstance(parameters, str) else (parameters or {})
    except Exception:
        params = {}
    action = (params.get("action") or "reciente").lower()
    try:
        n = int(params.get("n", 3))
    except Exception:
        n = 3

    if action in ("reciente", "ultimas", "contexto"):
        rec = load_recent_summaries(limit=n)
        if not rec:
            return "Aún no hay resúmenes de sesiones anteriores."
        return "\n".join("— " + r for r in rec)

    if action in ("epilogo", "buffer", "actual"):
        blob = _fold_buffer()
        if not blob.strip():
            return "La sesión actual aún no tiene intercambios (o ya se cerró)."
        return blob

    if action in ("cerrar", "finalizar", "resumen"):
        path = finalize_session_summary()
        if not path:
            return "No había nada que resumir en la sesión actual."
        return f"Resumen de sesión guardado en: {path}"

    if action in ("indice", "lista", "historial"):
        entries = _load_index()
        if not entries:
            return "Aún no hay resúmenes registrados."
        return "\n".join(
            f"• {e['ts'][:16]} — {e['slug']}" for e in entries[-20:]
        )

    return _json.dumps({"error": f"Acción '{action}'. Usa: reciente, epilogo, cerrar, indice."}, ensure_ascii=False)