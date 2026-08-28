# -*- coding: utf-8 -*-
"""edit_journal.py — Bitácora append-only de ediciones de archivos.
Registra cada write/edit/create/delete/rename/move para verificación
anti-alucinación y auto-conocimiento de la sesión."""
import json
import time
from pathlib import Path

_JOURNAL = Path(__file__).resolve().parent.parent / "data" / "edit_journal.jsonl"


def log(entry_type: str, path: str, detail: str = "") -> None:
    try:
        _JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": str(entry_type),
            "path": str(path),
            "detail": str(detail),
        }
        with _JOURNAL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def recent(n: int = 20) -> str:
    try:
        if not _JOURNAL.exists():
            return "Sin bitácora de ediciones aún."
        lines = _JOURNAL.read_text(encoding="utf-8").splitlines()[-n:]
        out = []
        for ln in lines:
            try:
                r = json.loads(ln)
            except Exception:
                continue
            detail = r.get("detail", "") or ""
            if detail:
                detail = " — " + detail
            out.append(f"{r.get('ts','?')} [{r.get('type','?')}] {r.get('path','?')}{detail}")
        if not out:
            return "Sin bitácora de ediciones aún."
        return "\n".join(out)
    except Exception as e:
        return f"Error leyendo bitácora: {e}"
