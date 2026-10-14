"""
recetario.py — Recetario de soluciones de ERIS (wrapper FINO sobre lo existente).

**No es un store nuevo** (diseño §5.8b): une dos cosas que ya existen —
`mistake_learner` (problema → causa → solución) y `procedimientos` (receta de
pasos)— para reconocer y **reutilizar al instante** un problema ya vivido.

Acá vive la parte **local** que usa el acopio (§5.2b paso 1). F7 le agrega las
4 capas (data/knowledge/recetario, Obsidian, `rag_engine`) y el recall.
"""
from __future__ import annotations


def buscar(query: str, limite: int = 5) -> list[dict]:
    """Busca recetas locales (mistakes + procedimientos) para `query`."""
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

    return out[:max(1, int(limite))]


def guardar(problema: str, solucion: str, pasos: list = None,
            causa: str = "", categoria: str = "barrera", intencion: str = "") -> dict:
    """Guarda una receta en las fuentes locales (mistake + procedimiento).

    Las 4 capas y el índice semántico los agrega F7; acá queda lo reutilizable.
    """
    res = {"problema": problema, "guardado_en": []}
    try:
        from core.mistake_learner import record_mistake
        m = record_mistake(pattern=problema, cause=causa, solution=solucion,
                           category=categoria, severity="medium")
        res["guardado_en"].append("mistake_learner")
        res["mistake_id"] = m.get("id")
    except Exception as e:
        res["error_mistake"] = str(e)[:200]
    if pasos:
        try:
            from core.procedimientos import guardar_procedimiento
            guardar_procedimiento(nombre=problema[:40] or "receta", descripcion=solucion,
                                  pasos=pasos, intencion=intencion or problema, origen="recetario")
            res["guardado_en"].append("procedimientos")
        except Exception as e:
            res["error_procedimiento"] = str(e)[:200]
    res["ok"] = bool(res["guardado_en"])
    return res
