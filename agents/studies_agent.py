"""
agents/studies_agent.py — ERIS Estudios/Aprendizaje Specialized Agent.
Explica conceptos, arma planes de estudio, resume material, genera quizzes/flashcards
y guarda notas de estudio.
"""
from __future__ import annotations

import re
import time


def _extract_topic(text: str) -> str:
    """Extrae el tema luego de palabras clave."""
    low = text.lower()
    for pat in [
        r"(?:explic[aeá]\s+)(?:me\s+)?(.+)",
        r"(?:qué es|que es|que son|qué son)\s+(.+)",
        r"(?:sobre|acerca de|acerca)\s+(.+)",
        r"(?:tema\s+)",
        r"(?:repas[ao]\s+)(?:de\s+)?(.+)",
        r"(?:quiz\s+de\s+)(.+)",
        r"(?:plane\s*(?:a|á)?\s*de\s*estudio\s*(?:de|para)?\s*)(.+)",
        r"(?:plan\s*de\s*estudio\s*(?:de|para)?\s*)(.+)",
    ]:
        m = re.search(pat, low)
        if m and m.group(1).strip():
            topic = m.group(1)
            for glue in [".", ",", " por favor", " porfa", " a las", " en ", " para el"]:
                idx = topic.find(glue)
                if idx > 0:
                    topic = topic[:idx]
            return topic.strip()
    return ""


def _search_topic(topic: str, player=None) -> str:
    """Busca info del tema y devuelve un digest útil."""
    try:
        from actions.web_search import web_search
        return web_search({"action": "search", "query": topic, "num_results": 4}, player)
    except Exception:
        return ""


def _read_file(path: str) -> str:
    try:
        from core.file_api import file_api
        return file_api({"action": "read", "path": path})
    except Exception:
        return ""


def _save_study_note(text: str) -> str:
    try:
        from actions.save_memory import save_memory
        return save_memory({"category": "estudios", "content": text})
    except Exception:
        return ""


def _make_quiz(topic: str, content: str = "") -> str:
    """Genera 5 preguntas de autoevaluación sobre el tema con lo que haya disponible."""
    lines = [f"📚 Quiz de repaso — {topic.title()}", ""]
    if not content or len(content.strip()) < 40:
        lines.append("(Sin material propio aún; usá '/repaso de <tema>' después de estudiar, "
                     "o pasame un archivo/material para quiz.")
        lines.append("")
        lines.append("Método efectivo: leé el material en voz alta, explicámelo como si yo fuera "
                     "tu alumno, y después te tomo la evaluación. Empezá: 'te explico <tema>' "
                     "para conversar sobre ello.")
        return "\n".join(lines)

    snippets = [l.strip() for l in content.splitlines() if l.strip() and len(l.strip()) > 30]
    snippets = snippets[:5]
    lines.append("Respondé mentalmente y después compará con el material:")
    for i, snip in enumerate(snippets, 1):
        key = _key_phrase(snip)
        lines.append(f"{i}. ¿Qué sabés decirme sobre... {key}?")
        lines.append(f"   → En tu material: {snip[:180]}{'…' if len(snip) > 180 else ''}")
        lines.append("")
    lines.append("¿Lo dominás? Pasame el tema y te hago la versión a libro cerrado.")
    return "\n".join(lines)


def _key_phrase(snippet: str) -> str:
    words = snippet.split()
    if len(words) <= 8:
        return snippet
    # intenta tomar la frase inicial con significado
    stop = (" es ", " son ", " consiste en ", " se refiere a ", " definen ", " se define ")
    low = snippet.lower()
    for s in stop:
        idx = low.find(s)
        if 0 < idx < 60:
            return snippet[:idx + len(s)].strip()
    return " ".join(words[:8])


def _make_plan(topic: str, days: int = 7) -> str:
    lines = [
        f"🎯 Plan de estudio — {topic.title()} ({days} días)",
        "",
        "Principio: estudio espaciado (20-25 min por bloque) + repaso activo.",
        "",
    ]
    d = 1
    topics = [
        "Introducción y vocabulario clave",
        "Conceptos fundamentales",
        "Aplicación práctica / ejemplos",
        "Ejercicios y autoevaluación",
        "Conexiones con temas relacionados",
        "Repaso activo (quiz + flashcards)",
        "Cierre: resumen propio en tus palabras",
    ]
    for i in range(min(days, len(topics))):
        lines.append(f"  Día {d}: {topics[i]}")
        d += 1
    for extra in range(d, days + 1):
        lines.append(f"  Día {extra}: repaso espaciado del material (10 min) + 1 quiz rápido")
    lines.append("")
    lines.append("¿Querés que lo arme como recordatorios diarios? Decime la hora y te lo programo.")
    return "\n".join(lines)


def handle_studies(text: str, player=None, **kwargs) -> str:
    """Handle study/learning requests: explicar, resumir, plan, quiz, notas."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()
    try:
        text_lower = text.lower()
        topic = _extract_topic(text) or text.strip()

        # ── Quiz / Flashcards / Repaso ──
        if any(k in text_lower for k in ["quiz", "flashcard", "examen", "evaluame", "evaluación",
                                         "repaso", "preguntame", "autoevaluaci"]):
            path = re.search(r'[\w\\:/]+\.\w+', text)
            content = _read_file(path.group(0)) if path else ""
            topic = _extract_topic(text) or (path.group(0) if path else "tu materia")
            result = _make_quiz(topic, content)

        # ── Explicar un concepto ──
        elif any(k in text_lower for k in ["explica", "explicá", "explíca", "qué es", "que es",
                                           "que son", "qué son", "define", "sobre", "acerca de",
                                           "explicame", "explicáme"]):
            if not topic or len(topic) < 3:
                result = ("¿Qué tema querés que te explique? Por ejemplo: "
                          "'explicame qué es la entropía' o 'contame sobre el Renacimiento'.")
            else:
                if player:
                    player.write_log("📖 Buscando información sobre el tema...")
                digest = _search_topic(topic, player)
                if digest:
                    result = f"📖 {topic.title()}:\n\n{digest}"
                else:
                    result = (f"📖 No pude buscar ahora sobre '{topic}' (sin conexión/API). "
                              "Una forma: pasame un texto/material y te lo explico con ejemplos.")
                result += "\n\n💡 ¿Querés que te arme un plan de estudio o un quiz de repaso?"

        # ── Resumen de material / documento ──
        elif any(k in text_lower for k in ["resume", "resumí", "resumen", "sintetiza",
                                           "resumime", "resumíme", "me resumís"]):
            path = re.search(r'[\w\\:/]+\.\w+', text)
            if path:
                content = _read_file(path.group(0))
                if content and "Error" not in content:
                    lines = content.splitlines()
                    title = path.group(0).split("\\")[-1]
                    result = (f"📄 Resumen de {title}\n\n"
                              + "\n".join(l.strip() for l in lines[:30] if l.strip())
                              + ("\n…" if len(lines) > 30 else ""))
                else:
                    result = "No pude leer ese archivo. ¿La ruta es correcta?"
            else:
                # resumir texto pegado después de "resumí:"
                m = re.search(r"(?:resumi|resume|resumí|sintetiza)\s*:?\s*(.+)", text.lower())
                if m and m.group(1).strip() and len(m.group(1).strip()) > 20:
                    raw = m.group(1).strip()
                    comp = " ".join(raw.split())
                    result = f"📄 Resumen:\n\n{comp[:600]}{'…' if len(comp) > 600 else ''}"
                else:
                    result = ("Pasame material y lo resumo. Puede ser un archivo "
                              "('resumí C:\\ruta\\archivo.txt') o texto pegado "
                              "('resumí: <tu texto>').")

        # ── Plan de estudio ──
        elif any(k in text_lower for k in ["plan de estudio", "plan de estudios", "plane de estudio",
                                           "cronograma de estudio", "agenda de estudio"]):
            days = 7
            m = re.search(r"(\d+)\s*(d[ií]as?|semanas?)", text_lower)
            if m:
                n = int(m.group(1))
                days = n * 7 if m.group(2).startswith("sem") else n
                days = min(max(days, 1), 90)
            topic = _extract_topic(text) or "el tema"
            result = _make_plan(topic, days)

        # ── Guardar nota de estudio ──
        elif any(k in text_lower for k in ["anota", "anotá", "guarda esta nota", "guardá esta nota",
                                           "guarda esto", "nota de estudio", "apunte"]):
            m = re.search(r"(?:anot[áa]|guard[áa]|apunt)\s*:?\s*(.+)", text.lower())
            content = m.group(1).strip() if m and m.group(1).strip() else topic
            if len(content) < 4:
                result = "¿Qué querés que anote? Ej: 'anotá: la diferencia entre meiosis y mitosis'"
            else:
                saved = _save_study_note(content)
                result = f"📝 Nota de estudio guardada: {content[:120]}" + (f"\n{saved}" if saved and "Error" not in saved else "")

        # ── fallback ──
        else:
            result = (
                "Soy tu agente de Estudios/Aprendizaje 📚. Puedo:\n"
                "- 'Explicame qué es <tema>' → investigo y te explico\n"
                "- 'Resumí <archivo o texto>' → te saco el resumen\n"
                "- 'Armame un plan de estudio de <tema> (N días)'\n"
                "- 'Quiz de repaso de <tema>' → preguntas de autoevaluación\n"
                "- 'Anotá: <idea>' → guardo una nota de estudio"
            )

        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("studies_agent", text, result, elapsed)
        return result

    except Exception as e:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("studies_agent", text, "", elapsed, success=False, error=str(e))
        return f"Error en StudiesAgent: {e}"