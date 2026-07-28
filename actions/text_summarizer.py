import re
import math
from collections import Counter
from string import punctuation

_STOPWORDS_EN = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "was", "are", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "shall", "can", "need", "dare", "ought", "used", "it", "its",
    "this", "that", "these", "those", "i", "me", "my", "myself", "we", "our",
    "ours", "ourselves", "you", "your", "yours", "yourself", "he", "him", "his",
    "she", "her", "they", "them", "their", "what", "which", "who", "whom",
    "if", "then", "else", "when", "where", "how", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "about", "above", "after", "again", "also", "am", "an", "any", "because",
    "before", "below", "between", "into", "through", "during", "up", "down",
    "out", "off", "over", "under", "further", "here", "there", "once"
}

_STOPWORDS_ES = {
    "de", "la", "el", "en", "y", "a", "los", "del", "las", "un", "por", "con",
    "una", "su", "para", "es", "al", "lo", "como", "más", "mas", "pero", "sus",
    "le", "ya", "o", "este", "sí", "si", "porque", "esta", "entre", "cuando",
    "muy", "sin", "sobre", "también", "me", "hasta", "hay", "donde", "quien",
    "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra",
    "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mí", "antes",
    "algunos", "qué", "unos", "yo", "otro", "otras", "otra", "él", "tanto",
    "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual", "poco",
    "ella", "estar", "estas", "algunas", "algo", "nosotros", "mi", "mis",
    "tú", "te", "ti", "tu", "tus", "ellas", "nosotras", "vosotros",
    "vosotras", "os", "mío", "mía", "míos", "mías", "tuyo", "tuya",
    "suyo", "suya", "nuestro", "nuestra", "vuestro", "vuestra",
    "esos", "esas", "estoy", "estás", "está", "estamos", "estáis", "están",
    "esté", "estés", "estemos", "estéis", "estén", "estaré", "estarás",
    "estará", "estaremos", "estaréis", "estarán", "estaría", "estarías",
    "he", "has", "ha", "hemos", "habéis", "han", "había", "habías",
    "ser", "soy", "eres", "somos", "sois", "son", "fue", "fuera", "sido",
    "tiene", "tienen", "tener", "hacer", "poder", "decir", "ir", "ver",
    "dar", "saber", "querer", "llegar", "poner", "venir", "hablar",
    "llevar", "dejar", "seguir", "encontrar", "llamar", "creer", "salir"
}

_ALL_STOPWORDS = _STOPWORDS_EN | _STOPWORDS_ES


def _tokenize(text):
    text = text.lower()
    text = re.sub(r"[^\w\sáéíóúñü]", " ", text)
    words = text.split()
    return [w for w in words if w not in _ALL_STOPWORDS and len(w) > 2]


def _split_sentences(text):
    sentences = re.split(r'(?<=[.!?;:])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def _score_sentences(sentences, word_freq):
    scores = []
    for sent in sentences:
        words = _tokenize(sent)
        if not words:
            scores.append(0)
            continue
        score = sum(word_freq.get(w, 0) for w in words) / max(len(words), 1)
        length_bonus = min(len(words) / 10, 1.0)
        scores.append(score * (0.7 + 0.3 * length_bonus))
    return scores


def _get_word_freq(text):
    words = _tokenize(text)
    freq = Counter(words)
    max_freq = max(freq.values()) if freq else 1
    return {w: c / max_freq for w, c in freq.items()}


def text_summarizer(parameters: dict, player=None) -> str:
    action = parameters.get("action", "summarize")
    text = parameters.get("text", "")
    if not text:
        return "Error: No text provided."

    if action == "summarize":
        n_sentences = parameters.get("sentences", 5)
        sentences = _split_sentences(text)
        if not sentences:
            return "Could not split text into sentences."
        if len(sentences) <= n_sentences:
            return text
        word_freq = _get_word_freq(text)
        scores = _score_sentences(sentences, word_freq)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        selected = sorted(ranked[:n_sentences])
        summary = " ".join(sentences[i] for i in selected)
        return f"--- Summary ({len(selected)}/{len(sentences)} sentences) ---\n{summary}"

    elif action == "extract_keywords":
        n = parameters.get("count", 10)
        words = _tokenize(text)
        freq = Counter(words)
        top = freq.most_common(n)
        if not top:
            return "No keywords found."
        result = "\n".join(f"• {w} (freq: {c})" for w, c in top)
        return f"Top {len(top)} keywords:\n{result}"

    elif action == "tldr":
        sentences = _split_sentences(text)
        if not sentences:
            return text[:200]
        word_freq = _get_word_freq(text)
        scores = _score_sentences(sentences, word_freq)
        best = sentences[scores.index(max(scores))]
        return f"TL;DR: {best}"

    elif action == "bullet_points":
        n = parameters.get("count", 5)
        sentences = _split_sentences(text)
        if not sentences:
            return "No sentences found."
        word_freq = _get_word_freq(text)
        scores = _score_sentences(sentences, word_freq)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        selected = ranked[:n]
        points = [f"• {sentences[i]}" for i in selected]
        return "Key Points:\n" + "\n".join(points)

    elif action == "shorten":
        n_sentences = parameters.get("count", 3)
        sentences = _split_sentences(text)
        if not sentences:
            return text[:200]
        if len(sentences) <= n_sentences:
            return text
        word_freq = _get_word_freq(text)
        scores = _score_sentences(sentences, word_freq)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        selected = sorted(ranked[:n_sentences])
        result = " ".join(sentences[i] for i in selected)
        return result

    return f"Unknown action: {action}. Available: summarize, extract_keywords, tldr, bullet_points, shorten"
