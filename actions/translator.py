from __future__ import annotations

"""Translator — Text translation via ``deep-translator`` (Google).

Actions
-------
translate – Translate text between languages (auto-detect source).
languages – List all supported language codes.
batch     – Translate a list of texts in one call.
"""

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None  # type: ignore[assignment,misc]

_LANG_MAP: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-CN": "Chinese (Simplified)",
    "zh-TW": "Chinese (Traditional)",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "sv": "Swedish",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "cs": "Czech",
    "ro": "Romanian",
    "el": "Greek",
    "hu": "Hungarian",
    "uk": "Ukrainian",
    "he": "Hebrew",
    "fi": "Finnish",
    "no": "Norwegian",
    "da": "Danish",
}


def _pick_default_target(source_lang: str) -> str:
    """Return a sensible default target language based on detected source."""
    return "en" if source_lang.startswith("es") else "es"


def translator(parameters: dict = None, player=None) -> str:  # noqa: C901
    """Translate text, list languages, or batch-translate."""
    if GoogleTranslator is None:
        return "Error: deep-translator is not installed. Run: pip install deep-translator"

    params = parameters or {}
    action = str(params.get("action", "translate")).strip().lower()
    text = str(params.get("text", "")).strip()
    source = str(params.get("source", "auto")).strip() or "auto"
    target = str(params.get("target", "")).strip()
    texts_raw = params.get("texts", None)

    if action == "translate":
        if not text:
            return "Error: No text provided."
        if target == "auto" or not target:
            target = _pick_default_target(source)
        try:
            translator_obj = GoogleTranslator(source=source, target=target)
            result = translator_obj.translate(text)
            return result if result else "Error: Translation returned empty result."
        except Exception as exc:
            return f"Translation error: {exc}"

    if action == "languages":
        lines = [f"{code} — {name}" for code, name in sorted(_LANG_MAP.items())]
        return "Supported languages:\n" + "\n".join(lines)

    if action == "batch":
        if not texts_raw or not isinstance(texts_raw, list):
            return "Error: Provide 'texts' as a list of strings."
        if target == "auto" or not target:
            target = _pick_default_target(source)
        results: list[str] = []
        try:
            translator_obj = GoogleTranslator(source=source, target=target)
            for item in texts_raw:
                t = str(item).strip()
                if not t:
                    results.append("(empty)")
                    continue
                translated = translator_obj.translate(t)
                results.append(translated if translated else "(empty)")
        except Exception as exc:
            return f"Batch translation error: {exc}"
        numbered = [f"{i + 1}. {r}" for i, r in enumerate(results)]
        return "Translations:\n" + "\n".join(numbered)

    return f"Error: Unknown action '{action}'."
