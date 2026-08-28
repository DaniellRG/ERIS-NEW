"""
core/voice_translator.py — Translate text and speak in target language for ERIS.
Actions:
  translate_speak  — Translate text AND speak it in the target language
  translate_text   — Just translate (no speech)
  detect_language  — Detect language of input text
  speak_in         — Speak text in a specific language

Uses deep_translator for translation + core.tts_engine for TTS.
Falls back to pyttsx3 if TTS engine is unavailable.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

# ─── Translation ──────────────────────────────────────────────────────────────

_TranslatorClass = None
try:
    from deep_translator import GoogleTranslator
    _TranslatorClass = GoogleTranslator
except ImportError:
    try:
        from googletrans import Translator as GoogleTranslator
        _TranslatorClass = GoogleTranslator
    except ImportError:
        _TranslatorClass = None

_LANG_MAP = {
    "en": "en", "english": "en", "inglés": "en", "ingles": "en",
    "es": "es", "spanish": "es", "español": "es", "espanol": "es",
    "fr": "fr", "french": "fr", "francés": "fr", "frances": "fr",
    "de": "de", "german": "de", "alemán": "de", "aleman": "de",
    "it": "it", "italian": "it", "italiano": "it",
    "pt": "pt", "portuguese": "pt", "portugués": "pt", "portugues": "pt",
    "ja": "ja", "japanese": "ja", "japonés": "ja", "japones": "ja",
    "ko": "ko", "korean": "ko", "coreano": "ko",
    "zh": "zh-CN", "chinese": "zh-CN", "chino": "zh-CN",
    "ru": "ru", "russian": "ru", "ruso": "ru",
    "ar": "ar", "arabic": "ar", "árabe": "ar", "arabe": "ar",
    "hi": "hi", "hindi": "hi",
    "nl": "nl", "dutch": "nl", "holandés": "nl", "holandes": "nl",
    "pl": "pl", "polish": "pl", "polaco": "pl",
    "tr": "tr", "turkish": "tr", "turco": "tr",
    "sv": "sv", "swedish": "sv", "sueco": "sv",
    "da": "da", "danish": "da", "danés": "da", "danes": "da",
    "fi": "fi", "finnish": "fi", "finlandés": "fi", "finlandes": "fi",
    "no": "no", "norwegian": "no", "noruego": "no",
    "uk": "uk", "ukrainian": "uk", "ucraniano": "uk",
    "cs": "cs", "czech": "cs", "checo": "cs",
    "el": "el", "greek": "el", "griego": "el",
    "he": "he", "hebrew": "he", "hebreo": "he",
    "th": "th", "thai": "th", "tailandés": "th", "tailandes": "th",
    "vi": "vi", "vietnamese": "vi", "vietnamita": "vi",
    "id": "id", "indonesian": "id", "indonesio": "id",
    "ms": "ms", "malay": "ms", "malayo": "ms",
}


def _resolve_lang(lang: str) -> str:
    """Resolve a language name/code to the Google Translate code."""
    lang = lang.strip().lower()
    return _LANG_MAP.get(lang, lang)


def _translate_text(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """Translate text using deep_translator."""
    if not text.strip():
        return ""

    target = _resolve_lang(target_lang)
    source = _resolve_lang(source_lang) if source_lang and source_lang != "auto" else "auto"

    if _TranslatorClass is None:
        return "[Traducción no disponible: deep_translator y googletrans no instalados]"

    try:
        translator = _TranslatorClass(source=source, target=target)
        result = translator.translate(text)
        return result if isinstance(result, str) else str(result)
    except Exception as e:
        return f"[Error de traducción: {e}]"


def _detect_lang(text: str) -> str:
    """Detect the language of a text."""
    if not text.strip():
        return "auto"

    if _TranslatorClass is None:
        return "auto (detector no disponible)"

    try:
        if hasattr(_TranslatorClass, "detect"):
            translator = _TranslatorClass(source="auto", target="en")
            detected = translator.detect(text)
            if isinstance(detected, dict):
                return detected.get("lang", "unknown")
            return str(detected)
        return "auto (detect no soportado)"
    except Exception:
        return "auto"


# ─── TTS Integration ──────────────────────────────────────────────────────────

async def _speak_text(text: str, lang: str = "es") -> bool:
    """Speak text using ERIS TTS engine, with lang-appropriate backend/voice."""
    try:
        from core.tts_engine import synthesize, get_backend
        backend = get_backend()

        voice = None
        edge_voice_map = {
            "es": "es-AR-ElenaNeural",
            "en": "en-US-JennyNeural",
            "fr": "fr-FR-DeniseNeural",
            "de": "de-DE-KatjaNeural",
            "it": "it-IT-ElsaNeural",
            "pt": "pt-BR-FranciscaNeural",
            "ja": "ja-JP-NanamiNeural",
            "ko": "ko-KR-SunHiNeural",
            "zh": "zh-CN-XiaoxiaoNeural",
            "ru": "ru-RU-SvetlanaNeural",
            "ar": "ar-SA-ZariyahNeural",
            "hi": "hi-IN-SwaraNeural",
        }

        lang_code = _resolve_lang(lang).split("-")[0]
        if backend == "edge":
            voice = edge_voice_map.get(lang_code, "es-AR-ElenaNeural")

        pcm = await synthesize(text, backend=backend, voice=voice)
        if pcm and len(pcm) > 0:
            try:
                import numpy as np
                import sounddevice as sd
                from core.audio_config import RECEIVE_SAMPLE_RATE
                audio = np.frombuffer(pcm, dtype=np.int16)
                sd.play(audio, RECEIVE_SAMPLE_RATE)
                sd.wait()
                return True
            except Exception:
                pass

        return False
    except Exception:
        return False


def _speak_sync(text: str, lang: str = "es") -> bool:
    """Synchronous wrapper for _speak_text."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _speak_text(text, lang))
                return future.result(timeout=15)
        else:
            return loop.run_until_complete(_speak_text(text, lang))
    except Exception:
        try:
            return asyncio.run(_speak_text(text, lang))
        except Exception:
            return False


def _speak_fallback(text: str) -> bool:
    """Fallback TTS using pyttsx3."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception:
        return False


# ─── Main function ────────────────────────────────────────────────────────────

def voice_translator(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "translate_text")).strip().lower()

    if player:
        try:
            player.write_log(f"[VoiceTranslator] action={action}")
        except Exception:
            pass

    if action == "translate_speak":
        return _translate_speak(params)
    elif action == "translate_text":
        return _translate_only(params)
    elif action == "detect_language":
        return _detect(params)
    elif action == "speak_in":
        return _speak_in(params)
    return "Actions: translate_speak, translate_text, detect_language, speak_in"


def _translate_speak(params: dict) -> str:
    """Translate text and speak it in the target language."""
    text = str(params.get("text", "")).strip()
    target_lang = str(params.get("target_lang", "en")).strip()
    source_lang = str(params.get("source_lang", "auto")).strip()

    if not text:
        return "Falta el parámetro 'text' para traducir."

    translated = _translate_text(text, target_lang, source_lang)

    if translated.startswith("["):
        return f"Traducción: {translated}\n(No se pudo reproducir audio)"

    spoken = _speak_sync(translated, target_lang)
    if not spoken:
        spoken = _speak_fallback(translated)

    lang_name = {v: k for k, v in _LANG_MAP.items()}.get(
        _resolve_lang(target_lang), target_lang
    )
    status = " (audio reproducido)" if spoken else " (audio no disponible)"
    return f"[{lang_name}] {translated}{status}"


def _translate_only(params: dict) -> str:
    """Translate text without speaking."""
    text = str(params.get("text", "")).strip()
    target_lang = str(params.get("target_lang", "es")).strip()
    source_lang = str(params.get("source_lang", "auto")).strip()

    if not text:
        return "Falta el parámetro 'text' para traducir."

    translated = _translate_text(text, target_lang, source_lang)
    return f"[{source_lang} → {target_lang}] {translated}"


def _detect(params: dict) -> str:
    """Detect the language of input text."""
    text = str(params.get("text", "")).strip()
    if not text:
        return "Falta el parámetro 'text' para detectar idioma."

    detected = _detect_lang(text)
    return f"Idioma detectado: {detected}\nTexto: {text[:100]}"


def _speak_in(params: dict) -> str:
    """Speak text in a specific language (no translation, just TTS)."""
    text = str(params.get("text", "")).strip()
    lang = str(params.get("lang", "es")).strip()

    if not text:
        return "Falta el parámetro 'text' para reproducir."

    spoken = _speak_sync(text, lang)
    if not spoken:
        spoken = _speak_fallback(text)

    status = "reproducido" if spoken else "no disponible"
    return f"Audio {status}: {text[:80]}"
