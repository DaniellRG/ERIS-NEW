"""Guardrail anti-repetición en runtime para ERIS.

Complementa el bloque del prompt: detecta MEDIBLE cuándo Eris vuelve a usar
muletillas, aperturas o construcciones idénticas a respuestas recientes, y
devuelve texto [NO TE REPITAS] para que main.py lo inyecte en el contexto y
ella misma se corrija. Sin dependencias pesadas (solo stdlib).

Alimentado desde turn_complete (remember_reply) y consultado desde
_build_config (block). Persiste la cola de respuestas recientes.
"""
import json
import re
from collections import Counter
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_QUEUE_FILE = _BASE / "memory" / "repetition_guard.json"

_MAX_RECENT = 12          # cuántas respuestas recientes recordar
_BIGRAM_OVERLAP = 0.45    # fracción de bigramas compartidos → repetitivo
_NGRAM_HIT = 6            # n-grama idéntico tal cual (>=6 palabras) → repetitivo
_OPENING_MANY = 3         # misma apertura en >=3 de las últimas 8 → muletilla


def _norm(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"[^\wáéíóúñü\s-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _tokens(text: str) -> list[str]:
    return _norm(text).split()


def _bigrams(text: str) -> set[tuple[str, str]]:
    tok = _tokens(text)
    return {(tok[i], tok[i + 1]) for i in range(len(tok) - 1)}


def _ngrams(tok: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tok[i:i + n]) for i in range(len(tok) - n + 1)}


def _load() -> dict:
    try:
        if _QUEUE_FILE.exists():
            return json.loads(_QUEUE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save(state: dict):
    try:
        _QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _QUEUE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except Exception:
        pass


def recent_replies() -> list[str]:
    return _load().get("recent", [])


def remember_reply(text: str):
    """Guarda la respuesta final de Eris en la cola de recientes."""
    if not text or len(text.strip()) < 10:
        return
    st = _load()
    rec = st.get("recent", []) or []
    rec.append(text.strip())
    rec = rec[-_MAX_RECENT:]
    st["recent"] = rec
    _save(st)


def check(text: str) -> tuple[bool, str]:
    """Devuelve (es_repetitiva, evidencia). Evidencia = frase que ya dijo."""
    if not text or len(_norm(text)) < 12:
        return False, ""
    st = _load()
    rec = st.get("recent", []) or []
    if not rec:
        return False, ""

    cur_bg = _bigrams(text)
    if not cur_bg:
        return False, ""
    cur_tok = _tokens(text)
    cur_5 = _ngrams(cur_tok, 5)
    best_ov, best_ev = 0.0, ""
    for prev in rec[-8:]:
        if prev.strip() == text.strip():
            return True, text.strip()
        pb = _bigrams(prev)
        if pb:
            ov = len(cur_bg & pb) / len(cur_bg)
            if ov > best_ov:
                best_ov, best_ev = ov, prev.strip()
        shared = (cur_5 & _ngrams(_tokens(prev), 5))
        if shared:
            frag = " ".join(sorted(shared)[0])
            return True, frag

    if best_ov >= _BIGRAM_OVERLAP:
        return True, best_ev

    opening = tuple(cur_tok[:2])
    if opening:
        cnt = Counter(tuple(_tokens(p)[:2])
                      for p in rec[-8:]
                      if len(_tokens(p)) >= 2
                      and tuple(_tokens(p)[:2]) == opening)
        if cnt[opening] >= _OPENING_MANY and len(rec) >= 4:
            return True, " ".join(opening)

    return False, ""


def block(text: str, max_len: int = 140) -> str:
    """Texto a inyectar en el contexto si la respuesta es repetitiva."""
    rep, ev = check(text)
    if not rep:
        return ""
    short = (ev or text)[:max_len]
    return (f"[NO TE REPITAS] Otra de tus respuestas recientes ya expresó casi "
            f"lo mismo: «{short}…». Esta vez abrí distinto, cambiá la "
            f"construcción y el orden de ideas — no repitás frases ni muletillas.")


def status() -> str:
    st = _load()
    rec = st.get("recent", []) or []
    return json.dumps({"respuestas_recordadas": len(rec),
                       "ultimas": [r[:60] for r in rec[-3:]]},
                      ensure_ascii=False, indent=2)