"""
core/multilang_learning.py — Aprendizaje multilanguage para Eris

Aprende en cualquier idioma automaticamente.
"""
import json
import re
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "multilang_state.json"

LANGUAGES = {
    "es": "Espanol",
    "en": "English",
    "pt": "Portugues",
    "fr": "Francais",
    "de": "Deutsch",
    "it": "Italiano",
    "ja": "Japones",
    "zh": "Chino",
}

COMMON_WORDS = {
    "es": ["el", "la", "los", "las", "de", "del", "en", "es", "que", "por", "con", "para", "como", "mas", "pero", "este", "esta"],
    "en": ["the", "is", "at", "which", "on", "a", "an", "and", "or", "but", "in", "with", "to", "for", "of", "this", "that"],
    "pt": ["o", "a", "os", "as", "de", "do", "da", "em", "que", "por", "com", "para", "como", "mais", "mas", "este", "esta"],
    "fr": ["le", "la", "les", "de", "du", "des", "en", "est", "que", "pour", "avec", "comme", "plus", "mais", "ce", "cette"],
}


def detect_language(text: str) -> dict:
    """Detecta el idioma de un texto."""
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    scores = {}
    for lang, common in COMMON_WORDS.items():
        score = sum(1 for w in words if w in common)
        scores[lang] = score

    if not scores or max(scores.values()) == 0:
        return {"language": "unknown", "confidence": 0}

    best = max(scores, key=scores.get)
    confidence = scores[best] / max(len(words), 1)

    return {
        "language": best,
        "language_name": LANGUAGES.get(best, best),
        "confidence": round(min(confidence * 5, 1.0), 2),
        "scores": scores,
    }


def translate_term(term: str, from_lang: str, to_lang: str = "es") -> dict:
    """Traduce un termino basico (lookup en diccionario interno)."""
    translations = {
        ("en", "es"): {
            "artificial intelligence": "inteligencia artificial",
            "machine learning": "aprendizaje automatico",
            "deep learning": "aprendizaje profundo",
            "neural network": "red neuronal",
            "quantum computing": "computacion cuantica",
            "blockchain": "cadena de bloques",
            "cloud computing": "computacion en la nube",
            "data science": "ciencia de datos",
            "natural language": "lenguaje natural",
            "computer vision": "vision por computadora",
        },
        ("pt", "es"): {
            "inteligencia artificial": "inteligencia artificial",
            "aprendizado de maquina": "aprendizaje automatico",
            "computacao": "computacion",
        },
    }

    key = (from_lang, to_lang)
    if key in translations:
        lower = term.lower()
        if lower in translations[key]:
            return {"original": term, "translated": translations[key][lower], "confidence": 1.0}

    return {"original": term, "translated": term, "confidence": 0, "note": "Sin traduccion disponible"}


def learn_multilang(topic: str, content: str) -> dict:
    """Aprende un topic en cualquier idioma y guarda en español."""
    detection = detect_language(content)
    lang = detection.get("language", "unknown")

    sem_file = _MEMORY / "semantic.json"
    triples = []
    if sem_file.exists():
        try:
            triples = json.loads(sem_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    triple = {
        "subject": topic,
        "predicate": "aprendido_en",
        "object": "Idioma: {} - {}".format(lang, content[:200]),
        "confidence": detection.get("confidence", 0.5),
        "source": "multilang_learning",
        "language": lang,
        "timestamp": datetime.now().isoformat(),
    }
    triples.append(triple)

    sem_file.parent.mkdir(parents=True, exist_ok=True)
    sem_file.write_text(json.dumps(triples, indent=2, ensure_ascii=False), encoding="utf-8")

    state = _load_state()
    state.setdefault("languages_used", [])
    if lang not in state["languages_used"]:
        state["languages_used"].append(lang)
    state["total_learned"] = state.get("total_learned", 0) + 1
    _save_state(state)

    return {
        "status": "aprendido",
        "topic": topic,
        "language": lang,
        "language_name": LANGUAGES.get(lang, lang),
        "confidence": detection.get("confidence", 0),
    }


def get_multilang_status() -> dict:
    state = _load_state()
    return {
        "total_learned": state.get("total_learned", 0),
        "languages_used": state.get("languages_used", []),
        "available_languages": list(LANGUAGES.values()),
    }


def multilang_learning_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_multilang_status(), indent=2)
    elif action == "detect":
        text = params.get("text", "")
        if not text:
            return json.dumps({"error": "Texto requerido"})
        return json.dumps(detect_language(text), indent=2)
    elif action == "translate":
        term = params.get("term", "")
        from_lang = params.get("from_lang", "en")
        to_lang = params.get("to_lang", "es")
        return json.dumps(translate_term(term, from_lang, to_lang), indent=2)
    elif action == "learn":
        topic = params.get("topic", "")
        content = params.get("content", "")
        if not topic or not content:
            return json.dumps({"error": "topic y content requeridos"})
        return json.dumps(learn_multilang(topic, content), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Multi-Language ===")
    print(multilang_learning_tool({"action": "status"}))
    print(multilang_learning_tool({"action": "detect", "text": "The quick brown fox jumps over the lazy dog"}))
    print(multilang_learning_tool({"action": "detect", "text": "El rapido zorro marron salta sobre el perro perezoso"}))
