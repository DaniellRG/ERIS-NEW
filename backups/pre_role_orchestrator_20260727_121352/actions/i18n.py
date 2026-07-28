"""
actions/i18n.py — Internationalization system for ERIS.
Translate messages, manage language packs, auto-detect language.
"""
import json
import os
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_LANG_DIR = _BASE / "data" / "languages"
_STATE_FILE = _BASE / "data" / "i18n_state.json"

LANGUAGES = {
    "es": {"name": "Español", "native": "Español", "dir": "ltr"},
    "en": {"name": "English", "native": "English", "dir": "ltr"},
    "pt": {"name": "Português", "native": "Português", "dir": "ltr"},
    "fr": {"name": "Français", "native": "Français", "dir": "ltr"},
    "de": {"name": "Deutsch", "native": "Deutsch", "dir": "ltr"},
    "it": {"name": "Italiano", "native": "Italiano", "dir": "ltr"},
    "ja": {"name": "日本語", "native": "日本語", "dir": "ltr"},
    "ko": {"name": "한국어", "native": "한국어", "dir": "ltr"},
    "zh": {"name": "中文", "native": "中文", "dir": "ltr"},
    "ar": {"name": "العربية", "native": "العربية", "dir": "rtl"},
}

COMMON_STRINGS = {
    "greeting": {
        "es": "¡Hola! ¿En qué puedo ayudarte?",
        "en": "Hello! How can I help you?",
        "pt": "Olá! Como posso ajudar?",
        "fr": "Bonjour! Comment puis-je vous aider?",
        "de": "Hallo! Wie kann ich Ihnen helfen?",
        "it": "Ciao! Come posso aiutarti?",
        "ja": "こんにちは！何かお手伝いできますか？",
        "ko": "안녕하세요! 무엇을 도와드릴까요?",
        "zh": "你好！我能帮你什么？",
        "ar": "مرحبا! كيف يمكنني مساعدتك؟",
    },
    "goodbye": {
        "es": "¡Hasta luego!",
        "en": "Goodbye!",
        "pt": "Adeus!",
        "fr": "Au revoir!",
        "de": "Auf Wiedersehen!",
        "it": "Arrivederci!",
        "ja": "さようなら！",
        "ko": "안녕히 가세요!",
        "zh": "再见！",
        "ar": "مع السلامة!",
    },
    "error": {
        "es": "Ocurrió un error",
        "en": "An error occurred",
        "pt": "Ocorreu um erro",
        "fr": "Une erreur s'est produite",
        "de": "Ein Fehler ist aufgetreten",
        "it": "Si è verificato un errore",
        "ja": "エラーが発生しました",
        "ko": "오류가 발생했습니다",
        "zh": "发生错误",
        "ar": "حدث خطأ",
    },
    "task_complete": {
        "es": "Tarea completada",
        "en": "Task complete",
        "pt": "Tarefa concluída",
        "fr": "Tâche terminée",
        "de": "Aufgabe abgeschlossen",
        "it": "Compito completato",
        "ja": "タスク完了",
        "ko": "작업 완료",
        "zh": "任务完成",
        "ar": "اكتملت المهمة",
    },
    "thinking": {
        "es": "Pensando...",
        "en": "Thinking...",
        "pt": "Pensando...",
        "fr": "Réflexion...",
        "de": "Denke nach...",
        "it": "Pensiero...",
        "ja": "考え中...",
        "ko": "생각 중...",
        "zh": "思考中...",
        "ar": "جاري التفكير...",
    },
    "searching": {
        "es": "Buscando...",
        "en": "Searching...",
        "pt": "Pesquisando...",
        "fr": "Recherche...",
        "de": "Suche...",
        "it": "Ricerca...",
        "ja": "検索中...",
        "ko": "검색 중...",
        "zh": "搜索中...",
        "ar": "جاري البحث...",
    },
    "welcome_back": {
        "es": "¡Bienvenido de nuevo!",
        "en": "Welcome back!",
        "pt": "Bem-vindo de volta!",
        "fr": "Bon retour!",
        "de": "Willkommen zurück!",
        "it": "Bentornato!",
        "ja": "おかえりなさい！",
        "ko": "돌아오셨군요!",
        "zh": "欢迎回来！",
        "ar": "مرحبا بعودتك!",
    },
    "help": {
        "es": "¿Necesitas ayuda?",
        "en": "Do you need help?",
        "pt": "Precisa de ajuda?",
        "fr": "Besoin d'aide?",
        "de": "Brauchen Sie Hilfe?",
        "it": "Hai bisogno di aiuto?",
        "ja": "助けが必要ですか？",
        "ko": "도움이 필요하신가요?",
        "zh": "需要帮助吗？",
        "ar": "هل تحتاج مساعدة؟",
    },
    "saving": {
        "es": "Guardando...",
        "en": "Saving...",
        "pt": "Salvando...",
        "fr": "Sauvegarde...",
        "de": "Speichere...",
        "it": "Salvataggio...",
        "ja": "保存中...",
        "ko": "저장 중...",
        "zh": "保存中...",
        "ar": "جاري الحفظ...",
    },
    "loading": {
        "es": "Cargando...",
        "en": "Loading...",
        "pt": "Carregando...",
        "fr": "Chargement...",
        "de": "Lade...",
        "it": "Caricamento...",
        "ja": "読み込み中...",
        "ko": "로딩 중...",
        "zh": "加载中...",
        "ar": "جاري التحميل...",
    },
}


def _load_state():
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"current_language": "es", "fallback": "en"}

def _save_state(state):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def _load_custom_strings():
    _LANG_DIR.mkdir(parents=True, exist_ok=True)
    custom = {}
    for f in _LANG_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            lang = f.stem
            custom[lang] = data
        except Exception:
            pass
    return custom


def i18n(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "status":
        state = _load_state()
        custom = _load_custom_strings()
        return (
            f"I18n Status:\n"
            f"  Current language: {state.get('current_language', 'es')}\n"
            f"  Fallback: {state.get('fallback', 'en')}\n"
            f"  Supported languages: {len(LANGUAGES)}\n"
            f"  Built-in strings: {len(COMMON_STRINGS)}\n"
            f"  Custom string packs: {len(custom)}"
        )

    elif action == "set_language":
        lang = params.get("language", "es").lower()
        if lang not in LANGUAGES:
            return f"Language '{lang}' not supported. Available: {', '.join(LANGUAGES.keys())}"
        state = _load_state()
        state["current_language"] = lang
        _save_state(state)
        return f"Language set to: {LANGUAGES[lang]['name']} ({LANGUAGES[lang]['native']})"

    elif action == "get_string":
        key = params.get("key", "")
        if not key:
            return "Requires 'key'."
        state = _load_state()
        lang = params.get("language", state.get("current_language", "es"))
        string_data = COMMON_STRINGS.get(key, {})
        if lang in string_data:
            return string_data[lang]
        elif state.get("fallback") in string_data:
            return string_data[state["fallback"]]
        return f"String not found: {key} ({lang})"

    elif action == "translate_batch":
        keys = params.get("keys", "").split(",") if params.get("keys") else []
        if not keys:
            return "Requires 'keys' (comma-separated)."
        state = _load_state()
        lang = params.get("language", state.get("current_language", "es"))
        lines = [f"Translations ({lang}):"]
        for key in keys:
            key = key.strip()
            string_data = COMMON_STRINGS.get(key, {})
            translation = string_data.get(lang, string_data.get(state.get("fallback", "en"), f"[{key}]"))
            lines.append(f"  {key}: {translation}")
        return "\n".join(lines)

    elif action == "languages":
        state = _load_state()
        current = state.get("current_language", "es")
        lines = ["Supported Languages:"]
        for code, info in LANGUAGES.items():
            marker = " ←" if code == current else ""
            lines.append(f"  {code}: {info['name']} ({info['native']}){marker}")
        return "\n".join(lines)

    elif action == "add_string":
        key = params.get("key", "")
        value = params.get("value", "")
        lang = params.get("language", "es")
        if not key or not value:
            return "Requires 'key' and 'value'."
        custom = _load_custom_strings()
        if lang not in custom:
            custom[lang] = {}
        custom[lang][key] = value
        _LANG_DIR.mkdir(parents=True, exist_ok=True)
        (_LANG_DIR / f"{lang}.json").write_text(
            json.dumps(custom[lang], indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return f"String added: {key} = {value} ({lang})"

    elif action == "auto_detect":
        text = params.get("text", "")
        if not text:
            return "Requires 'text' to detect language."
        detected = _detect_language(text)
        return f"Detected language: {detected}"

    elif action == "help":
        state = _load_state()
        lang = state.get("current_language", "es")
        lines = [f"I18n Help ({lang}):"]
        for key in ["greeting", "goodbye", "error", "task_complete", "thinking", "searching", "welcome_back", "help"]:
            string_data = COMMON_STRINGS.get(key, {})
            lines.append(f"  {key}: {string_data.get(lang, '?')}")
        return "\n".join(lines)

    return "Actions: status, set_language, get_string, translate_batch, languages, add_string, auto_detect, help"


def _detect_language(text):
    text_lower = text.lower()
    lang_patterns = {
        "es": ["hola", "gracias", "por favor", "cómo", "qué", "cuándo", "dónde", "buenos", "buenas", "señor", "ayuda"],
        "en": ["hello", "thank", "please", "how", "what", "when", "where", "good", "morning", "help"],
        "pt": ["olá", "obrigado", "por favor", "como", "o quê", "bom", "dia", "ajuda"],
        "fr": ["bonjour", "merci", "s'il vous plaît", "comment", "quoi", "quand", "où", "bon"],
        "de": ["hallo", "danke", "bitte", "wie", "was", "wann", "wo", "guten"],
        "it": ["ciao", "grazie", "per favore", "come", "cosa", "quando", "dove", "buono"],
        "ja": ["こんにちは", "ありがとう", "ください", "どう", "何", "いつ", "どこ", "おはよう"],
        "ko": ["안녕하세요", "감사합니다", "주세요", "어떻게", "무엇", "언제", "어디"],
        "zh": ["你好", "谢谢", "请", "怎么", "什么", "什么时候", "哪里", "早上好"],
        "ar": ["مرحبا", "شكرا", "من فضلك", "كيف", "ماذا", "متى", "أين", "صباح"],
    }
    scores = {}
    for lang, patterns in lang_patterns.items():
        score = sum(1 for p in patterns if p in text_lower)
        if score > 0:
            scores[lang] = score
    if scores:
        return max(scores, key=scores.get)
    return "unknown"
