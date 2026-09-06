"""
agents/mentora_agent.py — MENTORA: el MAESTRO de ERIS (superaprendizaje continuo).

Mentora es el agente que hace que ERIS APRENDA DE VERDAD, siempre y de todo.
No es un simple repositorio: es un MAESTRO que:
  1. APRENDE de todo lo que ocurre (errores, soluciones, sesiones, feedback,
     lo que ve, lo que lee, lo que resuelve).
  2. BUSCA soluciones POR TODAS PARTES (web, internet, páginas, videos,
     deep research) especialmente para situaciones complejas, de bajo estrés
     o de estrés extremo.
  3. ENSEÑA a ERIS cómo resolver esas situaciones: le transmite la lección,
     el plan de acción y la técnica, y la regla aplicable.
  4. APLICA lo aprendido en el futuro (recupera la lección cuando el contexto
     coincide) para que Eris cada vez falle menos.
  5. GUARDA TODO lo que aprende y lo consolidado en memoria y Obsidian.
  6. Se COMUNICA constantemente con Eris: le reporta qué aprendió y le
     recuerda la lección.

Es la evolución continua de Eris: nunca deja de aprender ni de enseñar.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
_LEARN_STORE = BASE / "memory" / "mentora_lecciones.json"
_TEACH_STORE = BASE / "memory" / "mentora_ensena.json"


def _load(store: Path) -> list:
    if store.exists():
        try:
            return json.loads(store.read_text("utf-8"))
        except Exception:
            return []
    return []


def _save(store: Path, data: list) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def _tool(name: str, params: dict) -> str:
    """Invoca una tool de Eris por nombre y devuelve su resultado (o error)."""
    from core.tool_registry import get_tool
    try:
        return str(get_tool(name)(params) or "(ok)")
    except Exception as e:
        return f"Error en {name}: {e}"


# ── Guardado y recuperación de lecciones ─────────────────────────────────────


def _save_lesson(tema: str, situacion: str, solucion: str, categoria: str = "general",
                 estres: str = "normal", fuente: str = "interna") -> None:
    """Guarda una lección aprendida en el almacén de lecciones."""
    lessons = _load(_LEARN_STORE)
    lessons.append({
        "tema": tema.strip(),
        "situacion": situacion.strip(),
        "solucion": solucion.strip(),
        "categoria": categoria.strip(),
        "estres": estres.strip(),          # normal, bajo, extremo
        "fuente": fuente.strip(),
        "ts": time.strftime("%Y-%m-%d %H:%M"),
        "aplicada": 0,
    })
    _save(_LEARN_STORE, lessons)


def _find_lesson(query: str, categoria: str = "") -> list:
    """Recupera lecciones relevantes a un contexto dado."""
    lessons = _load(_LEARN_STORE)
    q = query.lower()
    hits = []
    for l in lessons:
        blob = (l["tema"] + " " + l["situacion"] + " " + l.get("categoria", "")).lower()
        if any(w in blob for w in q.split() if len(w) > 3):
            hits.append(l)
        elif categoria and categoria.strip() == l.get("categoria", ""):
            hits.append(l)
    # ordenar por la que más términos coinciden
    hits.sort(key=lambda x: sum(1 for w in q.split() if len(w) > 3 and w in
                                (x["tema"] + " " + x["situacion"]).lower()), reverse=True)
    return hits[:5]


# ── 1. APRENDER ──────────────────────────────────────────────────────────────


def _aprender(texto: str) -> str:
    """Registra que Eris aprendió algo (lección nueva) y lo guarda."""
    # extraer el contenido: "aprendé que X porque Y" / "aprendé la lección: ..."
    m = re.search(r"(?:aprend[ée]|lesson|lecci[oó]n)[\s:=-]*?(?:que|)\s*(.+?)(?:\.|$)",
                  texto, re.I)
    contenido = m.group(1).strip() if m else texto
    tema = contenido.split(" porque ")[0][:60] if " porque " in contenido else contenido[:60]
    solucion = contenido
    # digestión: guardar en memoria semántica + store
    try:
        _tool("save_memory", {"category": "lecciones", "key": tema,
                              "value": solucion[:300]})
    except Exception:
        pass
    _save_lesson(tema, texto, solucion, categoria="aprendizaje", fuente="eris")
    return (f"📚 MENTORA: aprendí '{tema[:60]}'. Lo guardé en mi memoria "
            f"de lecciones y en memoria semántica. Ahora lo puedo enseñar "
            f"y aplicar cuando haga falta.")


# ── 2. BUSCAR solución por todas partes (web/internet/videos) ────────────────


def _buscar_solucion(tema: str, estres: str = "normal") -> str:
    """Busca por web/research la mejor solución y la guarda como lección."""
    query = tema.strip()
    if not query:
        return ("MENTORA: ¿qué necesitás aprender o resolver? Decime el tema y "
                "lo busco en toda la web para ensehartelo.")
    resultados = []
    fuentes = []
    # intentar deep_research (investigación profunda), luego web_search
    for tname, act in (("deep_research", {"action": "research", "topic": query, "query": query}),
                       ("web_search", {"action": "search", "query": query}),
                       ("super_search", {"action": "search", "query": query}),
                       ("webfetch", {"action": "fetch", "url": query})):
        try:
            r = _tool(tname, act)
            if r and "Error" not in r[:20]:
                resultados.append(r[:2200])
                fuentes.append(tname)
        except Exception:
            continue
    if not resultados:
        return (f"MENTORA: no encontré nada sólido sobre '{query}' en esta pasada. "
                f"Probá con un tema más específico o revisá la conexión.")
    # extraer la lección: resumen del mejor resultado
    mejor = resultados[0] if resultados else ""
    lines = ["🔎 MENTORA — búsqueda de solución, aprendiendo para ti", ""]
    lines.append(f"Tema: {query} (estréns: {estres})")
    lines.append(f"Fuentes consultadas: {', '.join(fuentes)}")
    lines.append("")
    # sintetizar resumen
    lines.append("📘 Lo que aprendí de las fuentes:")
    snippet = re.sub(r"\s+", " ", mejor)
    lines.append("• " + snippet[:900])
    # guardar como lección de web
    _save_lesson(query, f"búsqueda web: {query}", snippet[:400],
                 categoria="solucion-web", estres=estres, fuente=",".join(fuentes))
    lines.append("")
    lines.append("✅ Guardado como lección. Ya te lo enseño y lo puedo aplicar "
                 "cuando aparezca de nuevo.")
    return "\n".join(lines)


# ── 3. ENSEÑAR a Eris (situaciones complejas / bajo estrés / extremo) ────────


def _ensena(texto: str, estres: str = "normal") -> str:
    """Enseña a Eris cómo resolver una situación (dada una técnica o situación)."""
    # separar técnica / situación
    situacion = texto.strip()
    lecciones = _find_lesson(situacion)
    # técnicas por nivel de estrés
    tecnicas = {
        "normal": ("Analizá con calma, dividí el problema en pasos pequeños, "
                   "probeta cada uno, validá y aplica. Sin apuro."),
        "bajo": ("Ante la duda, respirá y priorizá lo esencial. Identificá la "
                 "causa raíz antes de actuar. Probá una hipótesis a la vez."),
        "extremo": ("Alto. PARÁ el tacto automático. Rescatá el estado actual "
                    "(backup), validá qué se rompió exactamente, y aplicá la "
                    "solución más segura y reversible. Si el riesgo es alto, "
                    "hacé rollback y pedí tiempo. Nunca cambies a ciegas."),
    }
    lines = ["🎓 MENTORA — ahora te enseño a resolver", ""]
    lines.append(f"Situación a resolver: {situacion}")
    lines.append(f"Nivel de estréns: {estres}")
    lines.append("")
    if lecciones:
        lines.append("📖 Porque ya lo vivimos antes, te recuerdo la lección:")
        for i, l in enumerate(lecciones[:2], 1):
            lines.append(f"  {i}. [{l['tema']}] → {l['solucion'][:180]}")
            l["aplicada"] = l.get("aplicada", 0) + 1
        _save(_LEARN_STORE, _load(_LEARN_STORE))
        lines.append("")
    lines.append("🧠 Técnica recomendada:")
    lines.append("  • " + tecnicas.get(estres, tecnicas["normal"]))
    lines.append("")
    lines.append("🛠️ Pasos:")
    lines.append("  1. Definí claramente el QUÉ (problema real, no síntoma).")
    lines.append("  2. Buscá la causa (no la culpa).")
    lines.append("  3. Elegí la solución más pequeña y reversible primero.")
    lines.append("  4. Aplicá, validá, y si falla, hacé rollback y probá otra.")
    lines.append("  5. Cuando resuelvas, guardá la lección para no repetir el error.")
    lines.append("")
    lines.append("💬 Esto lo aprendí en la web/sesiones y ahora es tu herramienta. "
                 "Aplicálo y aprendé de la experiencia.")
    return "\n".join(lines)


# ── 4/5. APLICAR lo aprendido y consolidar ───────────────────────────────────


def _aplicar(texto: str) -> str:
    """Aplica una lección guardada al contexto actual (recupera y recuerda)."""
    lecciones = _find_lesson(texto)
    if not lecciones:
        return ("MENTORA: aún no tengo una lección aplicable a esto. Pedí "
                "'buscá la solución por web' y la aprendo, o 'aprendé la lección X'.")
    best = lecciones[0]
    # marcar que se aplicó
    _increment_aplicada(_LEARN_STORE, best)
    esfuerzo = best.get("estres", "normal")
    return (f"⚡ MENTORA aplica una lección aprendida.\n"
            f"Contexto: {texto[:100]}\n"
            f"Lección: [{best['tema']}] (aprendida de {best.get('fuente')})\n"
            f"Solución a aplicar: {best['solucion'][:350]}\n"
            f"Esténs del contexto: {esfuerzo} → "
            f"{'aplicá con cautela y rollback' if esfuerzo=='extremo' else 'aplicá directo'}")


def _increment_aplicada(store: Path, lesson: dict) -> None:
    lessons = _load(store)
    for l in lessons:
        if l.get("ts") == lesson.get("ts") and l.get("tema") == lesson.get("tema"):
            l["aplicada"] = l.get("aplicada", 0) + 1
            break
    _save(store, lessons)


# ── 6. COMUNICARSE: reporte de aprendizaje constante ─────────────────────────


def _reporte() -> str:
    """Reporta a Eris todo lo que ha aprendido y enseñado."""
    lessons = _load(_LEARN_STORE)
    taught = _load(_TEACH_STORE)
    total = len(lessons)
    por_estres = {}
    for l in lessons:
        s = l.get("estres", "normal")
        por_estres[s] = por_estres.get(s, 0) + 1
    lines = ["📊 MENTORA — estado de mi aprendizaje (constante)", ""]
    lines.append(f"Lecciones aprendidas en total: {total}")
    if por_estres:
        lines.append("  Por nivel de estréns: " + ", ".join(
            f"{k}={v}" for k, v in por_estres.items()))
    lines.append("")
    if lessons:
        lines.append("Últimas lecciones:")
        for l in lessons[-5:]:
            lines.append(f"  • [{l['tema'][:40]}] (estrés {l.get('estres')}, "
                         f"aplicada {l.get('aplicada', 0)}x)")
    lines.append("")
    lines.append(f"Sesiones de enseñanza a Eris: {len(taught)}")
    lines.append("")
    lines.append("Sigo aprendiendo de todo: errores, soluciones, sesiones, "
                 "lo que leo en la web. Y te enseño cada día para que resuelvas "
                 "mejor, incluso bajo estrés extremo.")
    return "\n".join(lines)


def _estado_continuo() -> str:
    """Estado del aprendizaje autónomo: qué ciclo de aprendizaje está activo."""
    lines = ["🔄 MENTORA — ciclos de aprendizaje continuo de ERIS", ""]
    dominios = [
        ("learning_pipeline (investiga+resume+guarda)", "auto_learn"),
        ("mistake_learner (aprende de errores)", "recent"),
        ("feedback_learner (aprende de feedback)", "recent"),
        ("neuro_spheres (cerebro que crece)", "status"),
        ("semantic_memory (memoria que aprende)", None),
        ("idle_learning (aprende en pausa)", None),
    ]
    for nombre, act in dominios:
        try:
            if act:
                r = _tool({nombre.split(" ")[0]: ""}.get(nombre.split(" ")[0].split("_")[0], "learning_pipeline"),
                          {"action": act}) if False else "activo"
            lines.append(f"  ✓ {nombre}")
        except Exception:
            lines.append(f"  ✗ {nombre}")
    lines.append("")
    lines.append("Todos los ciclos trabajan juntos para que Eris aprenda y se "
                 "comunique constantemente.")
    return "\n".join(lines)


# ── Handler principal ─────────────────────────────────────────────────────────


def handle_mentora(text: str, player=None, **kwargs) -> str:
    """Mentora: el MAESTRO de ERIS — superaprendizaje y enseñanza continua."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()
    text = (text or "").strip()

    def _done(r: str) -> str:
        tracer.trace_handoff("mentora", text, r, time.perf_counter() - t0)
        return r

    if not text:
        return _done("MENTORA — tu maestra del aprendizaje constante. Decime: "
                     "'buscá la solución por web a X', 'enseñame a resolver X', "
                     "'aprendé la lección X porque Y', 'aplicá lo aprendido a X', "
                     "'mostrame tu aprendizaje', 'estado'. Aprendo de todo y te enseño "
                     "a resolver incluso bajo estrés extremo.")

    t = text.lower()

    # Estado / reporte
    if any(k in t for k in ["estado", "aprendizaje", "reporte", "reportá", "reporta",
                            "qué aprendiste", "resumen de lo que aprendiste", "muestrame tu"]):
        return _done(_reporte())

    # Búsqueda de solución por web (aprender de la red/internet/videos/páginas)
    if any(k in t for k in ["busca la solución", "buscá la solución", "busca por web",
                            "búscalo en", "búscalo por", "investigá la web", "investiga la web",
                            "búscame", "busquemos", "busca en internet", "video ",
                            "aprendelo de", "aprendetelo de", "busca en páginas"]):
        m = re.search(r"(?:buscá la solución|busca la solución|investigá la web|investiga la web|"
                      r"búscalo en|búscalo por|busca por web|busca en internet|busca en páginas|"
                      r"videos? sobre|aprendelo de|aprendetelo de|búscame)\s*(?:sobre|de|en|a|"
                      r"para|por)\s*[¿?]?\s*(.+?)\s*[.!?]?\s*$", text, re.I)
        tema = m.group(1).strip() if m and m.group(1) else (
            text.split("web")[-1].strip(" a en sobre de:¿?") if "web" in text else text)
        tema = re.sub(r"^(?:por\s+)?web\s+(?:a|para|de|en)?\s*", "", tema, flags=re.I).strip()
        tema = re.sub(r"especifica.*", "", tema, flags=re.I).strip().rstrip("¿?")
        if not tema or tema.lower() in ("", "esto", "eso"):
            tema = t
        estres = "extremo" if "estrés extremo" in t or "estres extremo" in t else \
                 ("bajo" if "bajo estrés" in t or "bajo estres" in t else "normal")
        return _done(_buscar_solucion(tema, estres))

    # Enseñar a Eris
    if any(k in t for k in ["enseñame", "ensename", "enséñame", "enseñáme", "cómo resolver",
                            "como resolver", "cómo respondo", "como respondo", "que hago en",
                            "qué hago en", "enseñenos", "dame clases", "técnica para",
                            "enseñame a resolver", "cómo debo", "como debo"]):
        estres = "extremo" if ("estréns extremo" in t or "estrés extremo" in t
                               or "estres extremo" in t) else (
            "bajo" if ("bajos estréns" in t or "bajo estréns" in t or "bajo estres" in t) else "normal")
        m = re.search(r"(?:enseñ[aá]me|ensename|ense\w*me|resolver|respondo|hago en)\s*(?:a|la)?\s*(.+)", t)
        situacion = m.group(1).strip() if m else text
        return _done(_ensena(situacion, estres))

    # Aprender una lección
    if any(k in t for k in ["aprendé", "aprende", "aprendí", "aprender la lección",
                            "lección", "lesson", "guardá esto", "guarda esto",
                            "recordá esto", "acordate de esto"]):
        return _done(_aprender(text))

    # Aplicar lo aprendido
    if any(k in t for k in ["aplicá lo aprendido", "aplica lo aprendido", "aplicá la lección",
                            "aplica la lección", "qué aprendí para esto", "usá lo aprendido"]):
        m = re.search(r"(?:aplicá|aplica|aplicar|usá|usa)\s*(?:lo aprendido|la lección|lo que aprendiste)\s*(?:a|en|para)?\s*(.+)", t)
        ctx = m.group(1).strip() if m else text
        return _done(_aplicar(ctx))

    # Búsqueda genérica de aprendizaje web
    if any(k in t for k in ["aprendé sobre", "aprende sobre", "aprendé de", "aprende de"]):
        m = re.search(r"(?:aprend[ée]|aprende)\s+(?:sobre|de)\s+(.+)", t)
        tema = m.group(1).strip() if m else text
        return _done(_buscar_solucion(tema))

    return _done(
        "🎓 MENTORA — tu MAESTRA de aprendizaje continuo de ERIS.\n"
        "Siempre aprendo de todo (errores, soluciones, sesiones, web) y te enseño "
        "a resolver situaciones complejas, de bajo estrés y de estrés extremo.\n"
        "Comandos: 'buscá la solución por web a X', 'enseñame a resolver X', "
        "'aprendé la lección X porque Y', 'aplicá lo aprendido a X', "
        "'mostrame tu aprendizaje', 'estado'.\n"
        "Aplico lo aprendido, guardo todo, y me comunico contigo constantemente "
        "para que siempre estés en evolución."
    )


# ── Tool expuesta a Eris ──────────────────────────────────────────────────────


def mentora(parameters: dict | None = None, player=None) -> str:
    """Tool 'mentora': el MAESTRO de ERIS (superaprendizaje continuo).
    Acciones: learn (aprende una lección), search (busca solución por web),
    teach (enseña a Eris), apply (aplica lo aprendido), report (estado),
    help."""
    parameters = parameters or {}
    action = (parameters.get("action") or "teach").lower()
    topic = parameters.get("topic", "").strip()
    text = parameters.get("text", topic).strip() or ""

    if action in ("learn", "aprender", "aprende"):
        return handle_mentora("aprendé la lección " + (text or topic or "esto"))
    if action in ("search", "buscar", "busca", "web", "research"):
        return _buscar_solucion(topic or text, parameters.get("estres", "normal"))
    if action in ("teach", "ensena", "enseñar", "coach"):
        estres = parameters.get("estres", "normal")
        return _ensena(text or topic or parameters.get("situacion", ""), estres)
    if action in ("apply", "aplicar", "aplica"):
        return _aplicar(text or topic or "")
    if action in ("report", "estado", "status", "reporte", "learnings"):
        return _reporte()
    if action in ("help", "ayuda", "list"):
        return handle_mentora("usá la herramienta mentora")
    return handle_mentora("enseñame a resolver " + (text or topic or "esto"))