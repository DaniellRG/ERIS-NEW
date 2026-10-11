#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eris Obsidian Distiller (append-only, hybrid JSON + MD)
-------------------------------------------------------
Destila aprendizajes, correcciones, errores, fixes, decisiones y trazas a Obsidian
sin tocar la memoria operativa JSON. Usa rutas portables con get_obsidian_vault().
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from core.logging_setup import get_obsidian_vault
except Exception:
    def get_obsidian_vault() -> Path:
        env = os.environ.get("ERIS_OBSIDIAN_VAULT")
        if env:
            return Path(env).expanduser()
        return Path.home() / "ERIS" / "Eris_NEW" / "BaseDatosObsidian" / "BaseObsiEris"


VAULT = get_obsidian_vault()
VAULT.mkdir(parents=True, exist_ok=True)

# Carpetas destino
APR_DIR = VAULT / "Aprendizaje"
KPD_DIR = VAULT / "Conocimiento-Profundo"
LOGS_DIR = VAULT / "Logs"

for d in (APR_DIR, KPD_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

_APR_LOG = LOGS_DIR / "Aprendizajes.md"
_INDEX_HASH = VAULT / ".obsidian" / ".eris_distill_hash.json"
(_INDEX_HASH.parent).mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now().isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest()[:16]


def _load_hashes() -> Dict[str, str]:
    try:
        if _INDEX_HASH.exists():
            return json.loads(_INDEX_HASH.read_text("utf-8", errors="replace"))
        return {}
    except Exception:
        return {}


def _save_hashes(h: Dict[str, str]) -> None:
    try:
        _INDEX_HASH.write_text(json.dumps(h, ensure_ascii=False, indent=2), "utf-8")
    except Exception:
        pass


def _yaml_frontmatter(data: Dict[str, Any]) -> str:
    lines = ["---"]
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                # limpiar saltos
                s = str(item).replace("\n", " ").strip()
                lines.append(f"  - {s}")
        else:
            s = str(v).replace("\n", " ").strip()
            lines.append(f"{k}: {s}")
    lines.append("---")
    return "\n".join(lines)


def _append_log(entry: str) -> None:
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _APR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"- [{ts}] {entry}\n")
    except Exception:
        pass


def distill_event(
    kind: str = "aprendizaje",
    title: str = "Aprendizaje",
    summary: str = "",
    details: str = "",
    tags: Optional[List[str]] = None,
    links: Optional[List[str]] = None,
    force_md: bool = False,
) -> Optional[Path]:
    """
    Destila un evento a Obsidian (append-only). Deduplica por hash de resumen+detalles.
    kind: aprendizaje|correccion|error|fix|decision|traza|accion
    """
    if not summary and not details:
        return None

    base = f"{kind}|{title}|{summary}|{details}"
    h = _hash(base)
    hashes = _load_hashes()
    if h in hashes:
        return None  # ya existe

    tags = list(tags or [])
    tags = [t.lower() for t in tags if t]
    if kind not in tags:
        tags.append(kind)

    links = list(links or [])
    ts = _now()
    slug = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{h}"

    # Elegir carpeta: correccion/error/fix → Aprendizaje o Conocimiento-Profundo según fuerza
    target_dir = APR_DIR
    if kind in ("correccion", "fix", "decision"):
        target_dir = KPD_DIR
    if force_md:
        target_dir = KPD_DIR

    fname = f"{kind}_{slug}.md"
    path = target_dir / fname

    fm = {
        "created": ts,
        "updated": ts,
        "kind": kind,
        "title": title,
        "tags": tags,
        "links": links,
    }

    body_parts = []
    if title:
        body_parts.append(f"# {title}\n")
    if summary:
        body_parts.append(f"## Resumen\n\n{summary}\n")
    if details:
        body_parts.append(f"## Detalles\n\n{details}\n")
    if links:
        body_parts.append("## Enlaces\n\n")
        for l in links:
            body_parts.append(f"- [[{l}]]\n")

    content = _yaml_frontmatter(fm) + "\n" + "".join(body_parts)

    try:
        path.write_text(content, "utf-8")
        hashes[h] = str(path.relative_to(VAULT))
        _save_hashes(hashes)
        _append_log(f"{kind}: {title} → {path.name}")
        return path
    except Exception:
        return None


def distill_from_text(text: str, context: str = "") -> Optional[Path]:
    t = (text or "").lower()
    if not t.strip():
        return None
    if any(k in t for k in ("arreglé", "arregle", "fix", "corregí", "corregi", "solucion", "resolv")):
        kind = "correccion"
        title = "Corrección aplicada"
    elif any(k in t for k in ("error", "fallo", "crash", "traceback", "exception")):
        kind = "error"
        title = "Incidencia"
    elif any(k in t for k in ("aprend", "lección", "lesson", "descubr")):
        kind = "aprendizaje"
        title = "Aprendizaje"
    elif any(k in t for k in ("decid", "decisión")):
        kind = "decision"
        title = "Decisión"
    elif any(k in t for k in ("complet", "termin", "cre", "gener", "implement", "configur")):
        kind = "accion"
        title = "Acción ejecutada"
    else:
        kind = "traza"
        title = "Traza"

    summary = text.strip()[:400]
    details = (context or text).strip()
    return distill_event(kind=kind, title=title, summary=summary, details=details)


# alias
append_learning = distill_event
