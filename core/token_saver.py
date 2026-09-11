"""
token_saver.py — Compresión de resultados de herramientas (token saver).

Inspirado en la compresión RTK/Caveman de OmniRoute: cuando un tool devuelve
una respuesta larga, se comprime antes de enviarla al LLM para ahorrar tokens.

Compresión aplicada:
1. Eliminación de líneas vacías repetidas (máx 1)
2. Truncación inteligente: conservar inicio + fin con marcador del medio
3. Eliminación de ANSI escapes, timestamps irrelevantes, logs repetidos
4. Límite configurable por config.json (token_saver_limit, default 2000 chars)
"""
import json
import re
from pathlib import Path

_DEFAULT_LIMIT = 2000
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.json"


def _read_limit() -> int:
    try:
        cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return int(cfg.get("token_saver_limit", _DEFAULT_LIMIT))
    except Exception:
        return _DEFAULT_LIMIT


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
_MULTIPLE_BLANKS_RE = re.compile(r"\n{3,}")
_REPEAT_LINE_RE = re.compile(r"^([^\n]{10,})\n(\1\n)+", re.MULTILINE)


def compress_tool_output(text: str, limit: int | None = None) -> str:
    """Comprime la salida de una herramienta para reducir tokens antes de
    enviarla al LLM. Mantiene la información útil, elimina ruido.

    Args:
        text: Texto crudo del tool.
        limit: Máximo de caracteres (default: config/config.json → token_saver_limit).
    Returns:
        Texto comprimido.
    """
    if not text:
        return text

    if limit is None:
        limit = _read_limit()

    s = str(text)

    # 1. Eliminar ANSI escapes
    s = _ANSI_RE.sub("", s)

    # 2. Colapsar líneas vacías repetidas (máximo 1 salto doble)
    s = _MULTIPLE_BLANKS_RE.sub("\n\n", s)

    # 3. Eliminar líneas repetidas idénticas consecutivas (logs repetidos)
    lines = s.splitlines()
    deduped = []
    prev = None
    repeat_count = 0
    for ln in lines:
        if ln == prev:
            repeat_count += 1
            if repeat_count >= 2:
                if repeat_count == 2:
                    deduped.append("  [repetido N veces omitido]")
                continue
        else:
            repeat_count = 0
            prev = ln
        deduped.append(ln)
    s = "\n".join(deduped)

    # 4. Eliminar whitespace trailing por línea
    s = "\n".join(ln.rstrip() for ln in s.splitlines())

    # 5. Truncar si excede el límite: conservar 60% inicio + 40% final
    if len(s) <= limit:
        return s

    head_size = int(limit * 0.6)
    tail_size = limit - head_size - 60  # 60 chars para el marcador
    if tail_size < 100:
        tail_size = 100
        head_size = limit - tail_size - 60

    head = s[:head_size]
    tail = s[-tail_size:]
    total_removed = len(s) - limit + 60

    return (
        f"{head}\n\n"
        f"── [token_saver: {total_removed} chars omitidos] ──\n\n"
        f"{tail}"
    )


def compress_for_log(text: str, max_len: int = 120) -> str:
    """Versión ligera para líneas de log: solo elimina saltos y acorta."""
    s = str(text).replace("\n", " ").strip()
    return s[:max_len] + ("…" if len(s) > max_len else "")


def get_status() -> dict:
    """Estado del token saver para /status o debug."""
    return {
        "enabled": True,
        "limit": _read_limit(),
        "config_path": str(_CONFIG_PATH),
    }


def token_saver(parameters=None, player=None) -> str:
    """Tool compactador de salidas: compress, status, config."""
    import json as _json
    try:
        params = _json.loads(parameters) if isinstance(parameters, str) else (parameters or {})
    except Exception:
        params = {}
    action = (params.get("action") or "status").lower()
    if action in ("compress", "comprimir"):
        text = params.get("text", "")
        limit = params.get("limit")
        try:
            limit = int(limit) if limit else None
        except Exception:
            limit = None
        out = compress_tool_output(text, limit)
        saved = max(0, len(str(text)) - len(out))
        return _json.dumps({"chars_original": len(str(text)), "chars_final": len(out), "ahorrados": saved, "output": out}, ensure_ascii=False)
    if action in ("status", "estado"):
        return _json.dumps(get_status(), ensure_ascii=False)
    if action in ("config", "set_limit"):
        try:
            new_limit = int(params.get("limit", _DEFAULT_LIMIT))
        except Exception:
            new_limit = _DEFAULT_LIMIT
        try:
            cfg = _json.loads(_CONFIG_PATH.read_text(encoding="utf-8")) if _CONFIG_PATH.exists() else {}
        except Exception:
            cfg = {}
        cfg["token_saver_limit"] = new_limit
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(_json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return _json.dumps({"status": "ok", "token_saver_limit": new_limit}, ensure_ascii=False)
    return _json.dumps({"error": f"Acción '{action}'. Usa: compress, status, config."}, ensure_ascii=False)
