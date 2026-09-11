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


def _read_lines():
    try:
        if not _JOURNAL.exists():
            return []
        return _JOURNAL.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []


def edit_journal(parameters=None, player=None) -> str:
    """Tool de historial de ediciones: recent, search, stats, log."""
    import json as _json
    try:
        params = _json.loads(parameters) if isinstance(parameters, str) else (parameters or {})
    except Exception:
        params = {}
    action = (params.get("action") or "recent").lower()
    try:
        n = int(params.get("n", 20))
    except Exception:
        n = 20
    if action in ("recent", "ultimas"):
        return recent(n)
    if action in ("search", "buscar"):
        needle = (params.get("query") or params.get("term") or "").lower()
        matches = []
        for ln in _read_lines():
            try:
                r = _json.loads(ln)
            except Exception:
                continue
            blob = " ".join(str(v) for v in r.values()).lower()
            if needle in blob:
                detail = r.get("detail", "") or ""
                if detail:
                    detail = " — " + detail
                matches.append(f"{r.get('ts','?')} [{r.get('type','?')}] {r.get('path','?')}{detail}")
            if len(matches) >= n:
                break
        return "\n".join(matches) if matches else f"Sin coincidencias para '{needle}'."
    if action in ("stats", "resumen"):
        counts = {}
        for ln in _read_lines():
            try:
                r = _json.loads(ln)
            except Exception:
                continue
            t = r.get("type", "?")
            counts[t] = counts.get(t, 0) + 1
        return _json.dumps({"total": len(_read_lines()), "por_tipo": counts}, ensure_ascii=False)
    if action in ("log", "registrar"):
        log(params.get("type", "write"), params.get("path", ""), params.get("detail", ""))
        return _json.dumps({"status": "ok"})
    return _json.dumps({"error": f"Acción '{action}'. Usa: recent, search, stats, log."}, ensure_ascii=False)
