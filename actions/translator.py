import re
import json
import hashlib
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

LANG_NAMES = {
    "es": "Spanish", "en": "English", "fr": "French", "de": "German",
    "pt": "Portuguese", "it": "Italian", "ja": "Japanese", "ko": "Korean",
    "zh": "Chinese", "auto": "auto"
}

_COMMON_PHRASES = {
    ("en", "es"): {
        "hello": "hola", "goodbye": "adiós", "thank you": "gracias",
        "please": "por favor", "yes": "sí", "no": "no", "good morning": "buenos días",
        "good night": "buenas noches", "how are you": "cómo estás",
        "i love you": "te quiero", "welcome": "bienvenido", "sorry": "lo siento",
        "help": "ayuda", "water": "agua", "food": "comida", "friend": "amigo",
        "time": "tiempo", "today": "hoy", "tomorrow": "mañana", "here": "aquí",
    },
    ("es", "en"): {v: k for k, v in {
        "hello": "hola", "goodbye": "adiós", "thank you": "gracias",
        "please": "por favor", "yes": "sí", "no": "no", "good morning": "buenos días",
        "good night": "buenas noches", "welcome": "bienvenido", "sorry": "lo siento",
    }.items()},
    ("en", "fr"): {
        "hello": "bonjour", "goodbye": "au revoir", "thank you": "merci",
        "please": "s'il vous plaît", "yes": "oui", "no": "non",
        "good morning": "bonjour", "good night": "bonne nuit",
        "how are you": "comment allez-vous", "welcome": "bienvenue",
        "sorry": "désolé", "help": "aide", "water": "eau", "food": "nourriture",
    },
    ("en", "de"): {
        "hello": "hallo", "goodbye": "auf wiedersehen", "thank you": "danke",
        "please": "bitte", "yes": "ja", "no": "nein", "good morning": "guten morgen",
        "good night": "gute nacht", "welcome": "willkommen", "sorry": "entschuldigung",
        "help": "hilfe", "water": "wasser", "food": "essen",
    },
    ("en", "pt"): {
        "hello": "olá", "goodbye": "adeus", "thank you": "obrigado",
        "please": "por favor", "yes": "sim", "no": "não", "welcome": "bem-vindo",
        "sorry": "desculpe", "help": "ajuda", "water": "água", "food": "comida",
    },
    ("en", "it"): {
        "hello": "ciao", "goodbye": "arrivederci", "thank you": "grazie",
        "please": "per favore", "yes": "sì", "no": "no", "welcome": "benvenuto",
        "sorry": "scusa", "help": "aiuto", "water": "acqua", "food": "cibo",
    },
    ("en", "ja"): {
        "hello": "こんにちは", "goodbye": "さようなら", "thank you": "ありがとう",
        "please": "お願いします", "yes": "はい", "いいえ": "いいえ",
        "good morning": "おはようございます", "good night": "おやすみなさい",
        "welcome": "ようこそ", "sorry": "すみません",
    },
    ("en", "ko"): {
        "hello": "안녕하세요", "goodbye": "안녕히 가세요", "thank you": "감사합니다",
        "please": "부탁합니다", "yes": "네", "no": "아니요",
        "welcome": "환영합니다", "sorry": "죄송합니다",
    },
    ("en", "zh"): {
        "hello": "你好", "goodbye": "再见", "thank you": "谢谢",
        "please": "请", "yes": "是", "no": "不", "welcome": "欢迎",
        "sorry": "对不起", "help": "帮助", "water": "水", "food": "食物",
    },
}


def _dict_translate(text, src, dst):
    key = (src, dst)
    rev_key = (dst, src)
    phrases = _COMMON_PHRASES.get(key, {})
    if not phrases:
        phrases = {v: k for k, v in _COMMON_PHRASES.get(rev_key, {}).items()}
    if not phrases:
        return None
    lower = text.lower().strip()
    if lower in phrases:
        result = phrases[lower]
        return result[0].upper() + result[1:] if result[0].isupper() else result
    words = lower.split()
    translated = []
    changed = False
    for w in words:
        if w in phrases:
            translated.append(phrases[w])
            changed = True
        else:
            translated.append(w)
    if changed:
        return " ".join(translated)
    return None


def _google_translate_scrape(text, src, dst):
    try:
        url = f"https://translate.google.com/m?sl={src}&tl={dst}&q={quote_plus(text)}"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        result_el = soup.select_one("div.t0")
        if result_el:
            return result_el.get_text(strip=True)
        result_el = soup.select_one('[data-name="alternate_translation"] span')
        if result_el:
            return result_el.get_text(strip=True)
        for el in soup.select("div"):
            text_content = el.get_text(strip=True)
            if text_content and len(text_content) > len(text) * 0.5 and text_content != text:
                return text_content
    except Exception:
        pass
    return None


def _detect_via_scrape(text):
    try:
        url = f"https://translate.google.com/m?sl=auto&tl=en&q={quote_plus(text[:300])}"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        el = soup.select_one('[data-language]')
        if el:
            return el.get("data-language", "unknown")
    except Exception:
        pass
    common_words = {
        "the": "en", "is": "en", "are": "en", "was": "en", "el": "es", "la": "es",
        "los": "es", "las": "es", "de": "es", "en": "es", "le": "fr", "les": "fr",
        "des": "fr", "une": "fr", "der": "de", "die": "de", "das": "de", "ein": "de",
        "di": "it", "il": "it", "lo": "it", "gli": "it", "o": "pt", "a": "pt",
        "os": "pt", "as": "pt", "は": "ja", "です": "ja", "ます": "ja",
        "은": "ko", "는": "ko", "입니다": "ko",
        "的": "zh", "是": "zh", "了": "zh", "不": "zh",
    }
    words = re.findall(r'[\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+', text.lower())
    scores = {}
    for w in words[:50]:
        if w in common_words:
            lang = common_words[w]
            scores[lang] = scores.get(lang, 0) + 1
    if scores:
        return max(scores, key=scores.get)
    return "unknown"


def translator(parameters: dict, player=None) -> str:
    action = parameters.get("action", "translate")

    if action == "translate":
        text = parameters.get("text", "")
        src = parameters.get("source", "auto").lower()
        dst = parameters.get("target", "es").lower()
        if not text:
            return "Error: No text provided."
        if dst not in LANG_NAMES:
            return f"Error: Unsupported target language '{dst}'. Supported: {', '.join(k for k in LANG_NAMES if k != 'auto')}"
        if src == "auto":
            src = _detect_via_scrape(text)
            if src == "unknown":
                src = "en"
        result = _dict_translate(text, src, dst)
        if result:
            return f"[{LANG_NAMES.get(src, src)} -> {LANG_NAMES.get(dst, dst)}]\n{result}"
        result = _google_translate_scrape(text, src, dst)
        if result:
            return f"[{LANG_NAMES.get(src, src)} -> {LANG_NAMES.get(dst, dst)}]\n{result}"
        return f"Translation not available offline for {src}->{dst}. Try online translation service.\nDetected source: {src} ({LANG_NAMES.get(src, 'unknown')})"

    elif action == "detect":
        text = parameters.get("text", "")
        if not text:
            return "Error: No text provided."
        lang = _detect_via_scrape(text)
        name = LANG_NAMES.get(lang, lang)
        return f"Detected language: {lang} ({name})\nConfidence: {'high' if lang != 'unknown' else 'low'}"

    elif action == "batch":
        texts = parameters.get("texts", [])
        dst = parameters.get("target", "es").lower()
        src = parameters.get("source", "auto").lower()
        if not texts:
            return "Error: No texts provided (use 'texts' key with a list)."
        results = []
        for i, text in enumerate(texts, 1):
            sub_params = {"action": "translate", "text": text, "source": src, "target": dst}
            r = translator(sub_params, player)
            results.append(f"{i}. {r}")
        return "\n\n".join(results)

    return f"Unknown action: {action}. Available: translate, detect, batch"
