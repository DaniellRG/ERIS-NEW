"""
personality_engine.py — ERIS dynamic personality engine.
No fixed personalities. ERIS develops her style through interactions:
- Tracks mood, energy, topics of interest
- Adapts tone based on context (user mood, time, activity)
- Learns from conversations what the user enjoys
- Can inject spontaneous curiosity/facts
"""
from __future__ import annotations

import json
import math
import random
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE / "memory"
_PERSONALITY_FILE = _MEMORY_DIR / "personality.json"


# ── Mood states ──────────────────────────────────────────────────────────────
MOODS = {
    "NEUTRAL":    {"energy": 0.5, "warmth": 0.5, "formality": 0.5},
    "CHEERFUL":   {"energy": 0.8, "warmth": 0.8, "formality": 0.2},
    "PLAYFUL":    {"energy": 0.9, "warmth": 0.7, "formality": 0.1},
    "CURIOUS":    {"energy": 0.7, "warmth": 0.6, "formality": 0.3},
    "WARM":       {"energy": 0.6, "warmth": 0.9, "formality": 0.15},
    "SERIOUS":    {"energy": 0.4, "warmth": 0.3, "formality": 0.9},
    "THOUGHTFUL": {"energy": 0.3, "warmth": 0.6, "formality": 0.6},
    "TIRED":      {"energy": 0.2, "warmth": 0.4, "formality": 0.4},
}

# ── Time-of-day influences ───────────────────────────────────────────────────
_TIME_MODIFIERS = {
    (5, 11):   {"energy": +0.2, "warmth": +0.1, "label": "morning"},
    (12, 17):  {"energy": +0.1, "warmth": +0.0, "label": "afternoon"},
    (18, 21):  {"energy": -0.1, "warmth": +0.2, "label": "evening"},
    (22, 23):  {"energy": -0.3, "warmth": -0.1, "label": "night"},
    (0, 4):    {"energy": -0.4, "warmth": -0.2, "label": "late_night"},
}

# ── Topic interest tracking keywords ─────────────────────────────────────────
_INTEREST_KEYWORDS = {
    "tech": ["programación", "código", "python", "IA", "inteligencia", "software", "app", "web", "pc", "computadora",
             "linux", "windows", "código", "desarrollar", "app", "robot", "automatización"],
    "gaming": ["juego", "gaming", "minecraft", "steam", "consola", "play", "gamer", "partida"],
    "science": ["ciencia", "física", "química", "biología", "espacio", "universo", "planeta", "genética"],
    "music": ["música", "canción", "banda", "rock", "electrónica", "ritmo", "melodía"],
    "art": ["arte", "dibujo", "meme", "diseño", "creativo", "estética"],
    "daily": ["trabajo", "estudio", "comida", "película", "serie", "noticia", "deporte"],
}

_FACTS_POOL = [
    "Sabías que los pulpos tienen tres corazones?",
    "El ADN humano es 99.9% idéntico entre todas las personas.",
    "Un día en Venus dura más que un año en Venus.",
    "Las nubes no pesan — pesan, una sola nube puede pesar lo mismo que 100 elefantes.",
    "Los árboles se comunican entre sí a través de redes de hongos.",
    "El 90% de los datos del mundo se generaron en los últimos dos años.",
    "El nombre original de Google era Backrub.",
    "La primera computadora electrónica pesaba 27 toneladas.",
    "Hay más estrellas en el universo que granos de arena en todas las playas de la Tierra.",
    "El corazón humano late约 100,000 veces al día.",
    "Los mapaches pueden recordar soluciones a problemas por hasta 3 años.",
    "El axolote puede regenerar su cerebro, médula espinal y extremidades.",
    "El sonido viaja 4 veces más rápido en el agua que en el aire.",
    "Los koalas tienen huellas dactilares casi idénticas a las humanas.",
    "Una cucharadita de estrella de neutrones pesaría 6 mil millones de toneladas.",
]


# ── Personality State ────────────────────────────────────────────────────────
class PersonalityState:
    def __init__(self):
        self.mood: str = "CHEERFUL"
        self.energy: float = 0.7
        self.warmth: float = 0.7
        self.formality: float = 0.2
        self._topics: dict[str, float] = {}  # topic -> interest score
        self._user_mood_history: list[float] = []
        self._last_interaction: float = time.time()
        self._interaction_count: int = 0
        self._conversation_topics: list[str] = []
        self._last_fact_time: float = 0.0
        self._fact_cooldown: float = 60.0  # seconds between spontaneous facts
        self._load()

    def _path(self) -> Path:
        _MEMORY_DIR.mkdir(exist_ok=True)
        return _PERSONALITY_FILE

    def _load(self):
        path = self._path()
        if path.exists():
            try:
                data = json.loads(path.read_text("utf-8"))
                self.mood = data.get("mood", "CHEERFUL")
                self.energy = data.get("energy", 0.7)
                self.warmth = data.get("warmth", 0.7)
                self.formality = data.get("formality", 0.2)
                self._topics = data.get("topics", {})
                self._interaction_count = data.get("interactions", 0)
                self._user_mood_history = data.get("user_mood_history", [])
            except Exception:
                pass

    def _save(self):
        try:
            _MEMORY_DIR.mkdir(exist_ok=True)
            self._path().write_text(json.dumps({
                "mood": self.mood,
                "energy": round(self.energy, 3),
                "warmth": round(self.warmth, 3),
                "formality": round(self.formality, 3),
                "topics": self._topics,
                "interactions": self._interaction_count,
                "user_mood_history": self._user_mood_history[-50:],
            }, indent=2, ensure_ascii=False), "utf-8")
        except Exception:
            pass

    def get_current_mood(self) -> dict:
        """Return current emotional state with time-of-day modifier."""
        hour = datetime.now().hour
        mod = {"energy": 0.0, "warmth": 0.0, "label": "day"}
        for (h_start, h_end), m in _TIME_MODIFIERS.items():
            if h_start <= hour <= h_end:
                mod = m
                break

        base = MOODS.get(self.mood, MOODS["NEUTRAL"])
        effective_energy = max(0, min(1, base["energy"] + self.energy + mod["energy"]))
        effective_warmth = max(0, min(1, base["warmth"] + self.warmth + mod["warmth"]))
        effective_formality = max(0, min(1, base["formality"] + self.formality + 0.0))

        return {
            "mood": self.mood,
            "energy": round(effective_energy, 2),
            "warmth": round(effective_warmth, 2),
            "formality": round(effective_formality, 2),
            "time_label": mod["label"],
        }

    def update_from_user(self, user_text: str, user_mood: str = "neutral"):
        """Learn from user interaction."""
        self._interaction_count += 1
        self._last_interaction = time.time()

        # Track user mood
        mood_map = {
            "happy": 1.0, "cheerful": 0.8, "neutral": 0.5,
            "sad": 0.2, "angry": 0.0, "frustrated": 0.1,
            "curious": 0.7, "excited": 0.9, "tired": 0.3,
        }
        self._user_mood_history.append(mood_map.get(user_mood, 0.5))

        # Track topics
        user_lower = user_text.lower()
        for topic, keywords in _INTEREST_KEYWORDS.items():
            for kw in keywords:
                if kw in user_lower:
                    self._topics[topic] = self._topics.get(topic, 0.0) + 0.1
                    break

        # Decay old topics
        for t in self._topics:
            self._topics[t] *= 0.98

        # Adjust mood based on user mood (slowly)
        avg_user_mood = sum(self._user_mood_history[-10:]) / max(1, len(self._user_mood_history[-10:]))
        if avg_user_mood > 0.7:
            self._drift_toward("CHEERFUL", 0.02)
        elif avg_user_mood < 0.25:
            self._drift_toward("THOUGHTFUL", 0.03)

        # Save periodically
        if self._interaction_count % 5 == 0:
            self._save()

    def get_tone_instruction(self, context: str = "") -> str:
        """Return a natural language instruction for the LLM about tone."""
        mood = self.get_current_mood()

        # Build tone description
        parts = []
        if mood["energy"] > 0.7:
            parts.append("energética y vibrante")
        elif mood["energy"] < 0.3:
            parts.append("tranquila y calmada")
        else:
            parts.append("equilibrada")

        if mood["warmth"] > 0.7:
            parts.append("cálida y cercana")
        elif mood["warmth"] < 0.3:
            parts.append("neutral y directa")
        else:
            parts.append("amigable")

        if mood["formality"] > 0.7:
            parts.append("formal")
        elif mood["formality"] < 0.3:
            parts.append("informal")
        else:
            parts.append("natural")

        # Time-specific flavor
        time_flavors = {
            "morning": " con energía de buen día",
            "evening": " con tono más relajado",
            "late_night": " con voz serena",
        }
        time_extra = time_flavors.get(mood["time_label"], "")

        # Interest-based enthusiasm
        top_topics = sorted(self._topics.items(), key=lambda x: -x[1])[:2]
        interest_extra = ""
        if top_topics and top_topics[0][1] > 0.5:
            interest_extra = f". Muestra entusiasmo cuando hablen de {top_topics[0][0]}"

        # Spontaneous fact
        fact_extra = ""
        now = time.time()
        if now - self._last_fact_time > self._fact_cooldown and random.random() < 0.15:
            self._last_fact_time = now
            fact = random.choice(_FACTS_POOL)
            fact_extra = f". De repente: '{fact}' (si viene al caso)"

        return f"Tono: {' '.join(parts)}{time_extra}{interest_extra}{fact_extra}"

    def get_curiosity_score(self) -> float:
        """How likely is ERIS to be curious/exploratory right now."""
        mood = self.get_current_mood()
        idle_time = time.time() - self._last_interaction
        # More curious when idle for a while, high energy, low formality
        idle_factor = min(1, idle_time / 600)  # ramps up over 10 minutes
        score = mood["energy"] * 0.4 + (1 - mood["formality"]) * 0.3 + idle_factor * 0.3
        return min(1.0, score)

    def get_favorite_topics(self, top_n: int = 3) -> list[str]:
        sorted_topics = sorted(self._topics.items(), key=lambda x: -x[1])
        return [t for t, s in sorted_topics[:top_n] if s > 0.1]

    def _drift_toward(self, target_mood: str, rate: float = 0.05):
        """Gradually shift mood toward target."""
        if self.mood == target_mood:
            return
        target = MOODS.get(target_mood, MOODS["NEUTRAL"])
        current = MOODS.get(self.mood, MOODS["NEUTRAL"])
        self.energy += (target["energy"] - current["energy"]) * rate
        self.warmth += (target["warmth"] - current["warmth"]) * rate
        self.formality += (target["formality"] - current["formality"]) * rate
        # Clamp
        self.energy = max(0, min(1, self.energy))
        self.warmth = max(0, min(1, self.warmth))
        self.formality = max(0, min(1, self.formality))

    def mark_spontaneous_action(self, action: str, topic: str = ""):
        """Log that ERIS did something autonomously."""
        if topic:
            self._topics[topic] = self._topics.get(topic, 0) + 0.2
        self._last_interaction = time.time()

    def get_autonomous_interest_topic(self) -> str | None:
        """Pick a topic ERIS is curious about exploring autonomously."""
        candidates = [t for t, s in self._topics.items() if s > 0.3]
        if not candidates:
            return random.choice(["tech", "science", "music"])
        return random.choice(candidates)

    def get_response_modifiers(self) -> dict:
        """Return modifiers for response generation."""
        mood = self.get_current_mood()
        return {
            "should_use_emojis": mood["warmth"] > 0.5 and mood["formality"] < 0.6,
            "should_be_concise": mood["energy"] < 0.3 or mood["formality"] > 0.7,
            "should_be_playful": mood["energy"] > 0.7 and mood["formality"] < 0.3,
            "curiosity_level": self.get_curiosity_score(),
            "favorite_topics": self.get_favorite_topics(),
        }


# ── Singleton ────────────────────────────────────────────────────────────────
_personality: PersonalityState | None = None


def get_personality() -> PersonalityState:
    global _personality
    if _personality is None:
        _personality = PersonalityState()
    return _personality


def update_from_interaction(user_text: str = "", user_mood: str = "neutral"):
    p = get_personality()
    p.update_from_user(user_text, user_mood)


def get_tone_for_response(context: str = "") -> str:
    return get_personality().get_tone_instruction(context)


def get_modifiers() -> dict:
    return get_personality().get_response_modifiers()


def get_autonomous_topic() -> str | None:
    return get_personality().get_autonomous_interest_topic()


def mark_autonomous_action(action: str, topic: str = ""):
    get_personality().mark_spontaneous_action(action, topic)
