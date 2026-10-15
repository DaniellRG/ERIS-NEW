"""
recetario.py — Recetario de soluciones de ERIS (wrapper FINO sobre lo existente).

**No es un store nuevo** (diseño §5.8b): une dos cosas que ya existen —
`mistake_learner` (problema → causa → solución) y `procedimientos` (receta de
pasos)— para reconocer y **reutilizar al instante** un problema ya vivido.

Cada barrera —resuelta o escalada— deja una receta que se guarda en 4 capas
(mismo patrón que `pentest_learning`):

  1. `data/knowledge/recetario/*.md` (texto buscable),
  2. Obsidian (baúl del dueño): `Vida/Recetario/*.md`,
  3. índice semántico en `rag_engine` (`reindexar` / recall de la bóveda),
  4. novedad en `todo_yo` + `escalada.registrar_logro(dominio="aprender")`.

`buscar()` consulta las fuentes locales (mistake + procedimiento), los .md del
recetario y, si está disponible, el `rag_engine`.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_RECETAS_DIR = _BASE / "data" / "knowledge" / "recetario"


def _slug(texto: str, maxlen: int = 50) -> str:
    s = re.sub(r"[^\w\s-]", "", str(texto or "")).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    return (s[:maxlen].strip("-") or "receta")


def _vault_recetas_dir() -> Path | None:
    try:
        from core.logging_setup import get_obsidian_vault
        return Path(get_obsidian_vault()) / "Vida" / "Recetario"
    except Exception:
        return None


def _novedad(texto: str) -> str:
    try:
        from core.todo_yo import registrar_novedad
        return str(registrar_novedad(texto))
    except Exception:
        return ""


def _logro(logro: str) -> str:
    try:
        from core.escalada import registrar_logro
        return str(registrar_logro(dominio="aprender", logro=logro))
    except Exception:
        return ""


# ── Construcción de la receta ────────────────────────────────────────────────

def receta_de_barrera(b: dict) -> dict:
    """Deriva una receta legible a partir de una barrera del motor (§5.8b)."""
    cap = b.get("capacidad") or {}
    diag = b.get("diagnostico") or {}
    plan = b.get("plan") or {}
    ev = b.get("evidencia") or {}
    intentos = b.get("intentos") or []
    rechazados = b.get("rechazados") or []

    errores = [str(i.get("error", ""))[:160] for i in intentos if i.get("error")]
    caminos = []
    for r in rechazados:
        enf = r.get("enfoque") or r.get("motivo")
        if enf:
            caminos.append(f"{enf} ({r.get('motivo', '')})".strip())
    for alt in (plan.get("alternativas") or [])[:4]:
        if isinstance(alt, dict):
            caminos.append(str(alt.get("enfoque") or alt.get("plan") or alt)[:120])
        else:
            caminos.append(str(alt)[:120])

    solucion = ""
    if cap:
        solucion = f"{cap.get('capacidad')} ({cap.get('tipo')}, {cap.get('creada_vs_reutilizada')})"
        if cap.get("como_se_creo"):
            solucion += f" vía {cap.get('como_se_creo')}"

    return {
        "problema": b.get("titulo") or b.get("descripcion") or "barrera",
        "senales": b.get("descripcion") or "",
        "diagnostico": diag.get("tipo") or diag.get("falta") or "",
        "solucion": solucion or "escalada (sin capacidad propia todavía)",
        "pasos": plan.get("pasos") or [],
        "enfoque": plan.get("enfoque") or "",
        "errores": errores,
        "caminos": caminos,
        "evidencia": "; ".join(c.get("nombre", "") for c in ev.get("checks", []) if c.get("ok")),
        "comprobar": cap.get("path") or "",
        "estado": b.get("estado") or "",
        "barrera_id": b.get("id") or "",
        "goal_ref": b.get("goal_ref") or {},
    }


def _md(receta: dict) -> str:
    def lista(items):
        return "\n".join(f"- {x}" for x in items) if items else "- _(ninguno)_"

    return (
        f"# Receta: {receta['problema']}\n\n"
        f"- **Categoría:** barrera\n"
        f"- **Señales (para reconocerlo):** {receta.get('senales') or '—'}\n"
        f"- **Diagnóstico (qué faltaba):** {receta.get('diagnostico') or '—'}\n"
        f"- **Solución:** {receta.get('solucion')}\n"
        f"- **Enfoque:** {receta.get('enfoque') or '—'}\n\n"
        f"## Pasos\n{lista(receta.get('pasos'))}\n\n"
        f"## Errores en el camino\n{lista(receta.get('errores'))}\n\n"
        f"## Caminos alternativos\n{lista(receta.get('caminos'))}\n\n"
        f"## Evidencia / cómo comprobarlo\n"
        f"- Evidencia: {receta.get('evidencia') or '—'}\n"
        f"- Ruta: `{receta.get('comprobar') or '—'}`\n\n"
        f"_Guardada: {time.strftime('%Y-%m-%d %H:%M')} · barrera `{receta.get('barrera_id')}` "
        f"· estado `{receta.get('estado')}`_\n"
    )


# ── Búsqueda ─────────────────────────────────────────────────────────────────

def _buscar_md(query: str, limite: int = 5) -> list[dict]:
    out = []
    q = (query or "").lower()
    if not q or not _RECETAS_DIR.exists():
        return out
    for md in sorted(_RECETAS_DIR.glob("*.md")):
        try:
            texto = md.read_text(encoding="utf-8")
        except Exception:
            continue
        if any(tok in texto.lower() for tok in q.split()):
            out.append({"fuente": "recetario_md",
                        "problema": md.stem.replace("-", " "),
                        "solucion": texto[:400], "path": str(md)})
        if len(out) >= limite:
            break
    return out


def buscar(query: str, limite: int = 5) -> list[dict]:
    """Busca recetas (locales: mistakes + procedimientos + .md + rag)."""
    if not query:
        return []
    out: list[dict] = []

    try:
        from core.mistake_learner import get_related_mistakes
        for m in get_related_mistakes(query):
            out.append({
                "fuente": "mistake",
                "problema": m.get("pattern", ""),
                "causa": m.get("cause", ""),
                "solucion": m.get("solution", ""),
                "resuelto": bool(m.get("resolved")),
            })
    except Exception:
        pass

    try:
        from core.procedimientos import buscar_por_intencion
        for p in buscar_por_intencion(query):
            out.append({
                "fuente": "procedimiento",
                "problema": p.get("intencion") or p.get("nombre", ""),
                "solucion": p.get("descripcion", ""),
                "pasos": p.get("pasos", []),
                "veces_usado": p.get("veces_usado", 0),
            })
    except Exception:
        pass

    out.extend(_buscar_md(query, limite=limite))

    # Recall semántico (best-effort; si no hay índice/modelo, no rompe).
    if len(out) < limite:
        try:
            from core.rag_engine import recall
            for r in (recall(query, top_k=max(1, limite - len(out))) or []):
                out.append({"fuente": "rag",
                            "problema": r.get("name", ""),
                            "solucion": (r.get("content", "") or "")[:400],
                            "path": r.get("path", "")})
        except Exception:
            pass

    return out[:max(1, int(limite))]


# ── Guardado en las 4 capas ──────────────────────────────────────────────────

def guardar(problema: str = "", solucion: str = "", pasos: list = None,
            causa: str = "", categoria: str = "barrera", intencion: str = "",
            barrera: dict = None, evidencia: str = "", senales: str = "",
            errores: list = None, caminos: list = None, comprobar: str = "",
            reindexar_rag: bool = True) -> dict:
    """Guarda una receta. Si se pasa `barrera`, deriva la receta del motor.

    Escribe las 4 capas (§5.8b) y, además, en `mistake_learner` +
    `procedimientos` (no es un store nuevo).
    """
    if barrera:
        r = receta_de_barrera(barrera)
        problema = problema or r["problema"]
    else:
        r = {
            "problema": problema, "solucion": solucion,
            "pasos": pasos or [], "diagnostico": "",
            "errores": errores or [], "caminos": caminos or [],
            "evidencia": evidencia, "comprobar": comprobar,
            "senales": senales, "enfoque": intencion,
            "estado": categoria, "barrera_id": "", "goal_ref": {},
        }
    problema = problema or r["problema"]
    solucion = solucion or r["solucion"]
    pasos = pasos or r.get("pasos") or []

    res = {"problema": problema, "guardado_en": [], "capas": {}}

    # Fuente local 1: mistake_learner (problema → causa → solución).
    try:
        from core.mistake_learner import record_mistake
        m = record_mistake(pattern=problema, cause=causa or r.get("diagnostico", ""),
                           solution=solucion, category=categoria, severity="medium")
        res["guardado_en"].append("mistake_learner")
        res["mistake_id"] = m.get("id")
    except Exception as e:
        res["error_mistake"] = str(e)[:200]

    # Fuente local 2: procedimientos (receta de pasos).
    if pasos:
        try:
            from core.procedimientos import guardar_procedimiento
            guardar_procedimiento(nombre=problema[:60], descripcion=solucion,
                                  pasos=pasos, intencion=intencion or problema,
                                  origen="recetario")
            res["guardado_en"].append("procedimiento")
        except Exception as e:
            res["error_procedimiento"] = str(e)[:200]

    # Capa 1: data/knowledge/recetario/<slug>.md
    final = receta_completa(r, problema, solucion, pasos, evidencia, senales,
                            errores, caminos, comprobar)
    cuerpo = _md(final)
    try:
        _RECETAS_DIR.mkdir(parents=True, exist_ok=True)
        p = _RECETAS_DIR / f"{_slug(problema)}.md"
        p.write_text(cuerpo, encoding="utf-8")
        res["capas"]["knowledge"] = str(p)
        res["guardado_en"].append("data/knowledge/recetario")
    except Exception as e:
        res["error_md"] = str(e)[:200]

    # Capa 2: Obsidian Vida/Recetario/
    vault = _vault_recetas_dir()
    if vault is not None:
        try:
            vault.mkdir(parents=True, exist_ok=True)
            p = vault / f"{_slug(problema)}.md"
            p.write_text(cuerpo, encoding="utf-8")
            res["capas"]["obsidian"] = str(p)
            res["guardado_en"].append("obsidian")
        except Exception as e:
            res["error_obsidian"] = str(e)[:200]

    # Capa 4: novedad en todo_yo + logro en escalada (dominio aprender).
    try:
        res["capas"]["novedad"] = _novedad(f"Sumé una receta nueva al recetario: «{problema}».")
        res["guardado_en"].append("todo_yo")
    except Exception:
        pass
    try:
        res["capas"]["logro"] = _logro(f"Receta nueva: {problema}")
        res["guardado_en"].append("escalada")
    except Exception:
        pass

    # Capa 3: índice semántico (reindexar es pesado → best-effort).
    if reindexar_rag:
        try:
            res["capas"]["rag"] = reindexar()
            res["guardado_en"].append("rag_engine")
        except Exception as e:
            res["error_rag"] = str(e)[:200]

    return res


def receta_completa(r, problema, solucion, pasos, evidencia, senales, errores, caminos, comprobar):
    r = dict(r)
    r.update({"problema": problema or r.get("problema", ""),
              "solucion": solucion or r.get("solucion", ""),
              "pasos": pasos or r.get("pasos", []),
              "evidencia": evidencia or r.get("evidencia", ""),
              "senales": senales or r.get("senales", ""),
              "errores": errores or r.get("errores", []),
              "caminos": caminos or r.get("caminos", []),
              "comprobar": comprobar or r.get("comprobar", "")})
    return r


def reindexar() -> str:
    """Reconstruye el índice semántico (rápido si no hay modelo: best-effort)."""
    try:
        from core.rag_engine import index_todo
        return str(index_todo())[:200]
    except Exception as e:
        return f"no pude reindexar: {e}"
