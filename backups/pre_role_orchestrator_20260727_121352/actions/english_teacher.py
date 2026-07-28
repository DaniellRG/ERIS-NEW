# -*- coding: utf-8 -*-
"""
Eris English Teacher – Profesora de inglés integrada en Eris.
Currículum estructurado A1 → C2 con lecciones, ejercicios,
evaluación de progreso y vocabulario.
"""
import json
import random
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = DATA_DIR / "english_progress.json"

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

LEVEL_NAMES = {
    "A1": "Principiante (Beginner)",
    "A2": "Elemental (Elementary)",
    "B1": "Intermedio (Intermediate)",
    "B2": "Intermedio Alto (Upper Intermediate)",
    "C1": "Avanzado (Advanced)",
    "C2": "Maestría (Mastery)",
}

CURRICULUM = {
    "A1": {
        "title": "Beginner – You start here",
        "grammar": [
            "Verb TO BE (am/is/are)",
            "Subject pronouns (I, you, he, she, it, we, they)",
            "Possessive adjectives (my, your, his, her, our, their)",
            "Articles: a/an/the",
            "Plural nouns (book→books, box→boxes)",
            "Present Simple (I eat, you eat, he eats)",
            "Question words (what, where, when, who, why, how)",
            "Prepositions of place (in, on, at, under, next to)",
            "This/That/These/Those",
            "Numbers, dates, time",
            "Basic adjectives (big, small, hot, cold, good, bad)",
            "Can/Can't for ability",
        ],
        "vocabulary": [
            "Greetings: hello, goodbye, good morning, good night",
            "Family: mother, father, sister, brother, son, daughter",
            "Colors: red, blue, green, yellow, black, white",
            "Food: bread, milk, water, rice, chicken, fish, apple",
            "Body: head, hand, eye, mouth, nose, arm, leg",
            "Clothes: shirt, pants, shoes, hat, jacket, dress",
            "House: door, window, table, chair, bed, kitchen, bathroom",
            "Animals: dog, cat, bird, fish, horse, cow",
            "Weather: sunny, rainy, cloudy, cold, hot, windy",
            "Daily routine: wake up, eat, sleep, work, study, go",
        ],
        "conversation_topics": [
            "Introduce yourself (name, age, country)",
            "Describe your family",
            "Talk about what you have",
            "Order food and drinks",
            "Ask and give directions (basic)",
            "Describe the weather",
            "Talk about your daily routine",
        ],
    },
    "A2": {
        "title": "Elementary – You can handle simple situations",
        "grammar": [
            "Past Simple (regular and common irregular verbs)",
            "Present Continuous (I am doing, he is doing)",
            "Future with 'going to'",
            "Countable and uncountable nouns (some/any)",
            "Comparatives and superlatives (bigger, the biggest)",
            "Adverbs of frequency (always, usually, sometimes, never)",
            "Prepositions of time (in, on, at, from, until)",
            "Imperatives (open the door, don't touch)",
            "There is/There are",
            "Wh- questions in past",
            "Like + -ing (I like swimming)",
        ],
        "vocabulary": [
            "Jobs: teacher, doctor, engineer, nurse, driver, police",
            "Places: school, hospital, bank, park, supermarket, airport",
            "Transportation: car, bus, train, plane, bicycle, taxi",
            "Shopping: price, size, color, cheap, expensive, buy, pay",
            "Feelings: happy, sad, tired, hungry, thirsty, nervous",
            "Hobbies: reading, music, sports, cooking, dancing",
            "Time expressions: yesterday, last week, next month, ago",
            "Directions: left, right, straight, corner, block, street",
        ],
        "conversation_topics": [
            "Talk about your last weekend",
            "Describe a favorite place",
            "Go shopping (prices, sizes)",
            "Make plans for the weekend",
            "Describe a friend or family member",
            "Talk about what you are doing right now",
            "Order at a restaurant",
        ],
    },
    "B1": {
        "title": "Intermediate – You can communicate in most situations",
        "grammar": [
            "Present Perfect (I have visited, she has eaten)",
            "Present Perfect vs Past Simple",
            "Future: will vs going to vs present continuous",
            "Modal verbs: must, have to, should, might, may",
            "Conditionals type 0 and 1 (if it rains, I'll stay)",
            "Passive voice (present and past simple)",
            "Relative clauses (who, which, that, where)",
            "Gerunds and infinitives (I enjoy reading, I want to go)",
            "Quantifiers: too much, too many, enough, not enough",
            "Phrasal verbs (get up, turn off, look for, give up)",
        ],
        "vocabulary": [
            "Travel: passport, luggage, reservation, flight, hotel",
            "Technology: computer, internet, app, download, update",
            "Health: fever, cough, medicine, doctor, hospital, pain",
            "Education: subject, exam, grade, course, professor",
            "Entertainment: movie, show, concert, game, ticket",
            "Relationships: friend, colleague, neighbor, partner",
            "Work: meeting, deadline, boss, salary, project, team",
        ],
        "conversation_topics": [
            "Talk about experiences (have you ever...?)",
            "Describe a trip you took",
            "Discuss movies or TV shows",
            "Talk about future plans and dreams",
            "Explain a simple process (how to cook something)",
            "Give opinions and reasons",
            "Talk about news or current events (simple)",
        ],
    },
    "B2": {
        "title": "Upper Intermediate – Fluency and nuance",
        "grammar": [
            "All conditionals (0, 1, 2, 3) and mixed",
            "Passive voice (all tenses)",
            "Reported speech (He said that... she told me...)",
            "Causative (have/get something done)",
            "Future perfect and future continuous",
            "Modal perfects (should have, could have, might have)",
            "Third conditional (if I had known, I would have...)",
            "Wish and regret (I wish I had..., if only...)",
            "Linking words: however, therefore, nevertheless, moreover",
            "Inversion (never have I seen, not only... but also)",
        ],
        "vocabulary": [
            "Business: negotiation, contract, investment, revenue",
            "Science: research, experiment, theory, analysis, data",
            "Politics: government, election, policy, law, rights",
            "Environment: pollution, climate, renewable, conservation",
            "Abstract concepts: freedom, justice, success, failure",
            "Idioms (break the ice, hit the nail on the head, etc.)",
            "Collocations (make a decision, take a risk, etc.)",
        ],
        "conversation_topics": [
            "Debate a current issue",
            "Express and defend an opinion",
            "Talk about hypothetical situations",
            "Discuss abstract concepts",
            "Explain complex ideas clearly",
            "Negotiate or persuade",
            "Tell a story with detail and emotion",
        ],
    },
    "C1": {
        "title": "Advanced – Sophisticated expression",
        "grammar": [
            "Advanced passive structures",
            "Inversion after negative adverbials",
            "Fronting and cleft sentences (what I need is...)",
            "Ellipsis and substitution",
            "Advanced relative clauses",
            "Nominalization (turning verbs into nouns)",
            "Complex prepositional phrases",
            "Hedging and boosting language",
            "Style: formal vs informal register",
        ],
        "vocabulary": [
            "Academic vocabulary (analyze, synthesize, evaluate)",
            "Professional jargon per field",
            "Nuanced synonyms (angry→furious, happy→ecstatic)",
            "Colloquial expressions and slang",
            "Formal vs informal alternatives",
            "Phrasal verbs advanced (break down, carry out, etc.)",
            "Idioms and proverbs",
        ],
        "conversation_topics": [
            "Give a presentation or speech",
            "Write a formal email or report",
            "Discuss complex social issues",
            "Express subtle emotions and opinions",
            "Use humor and irony in English",
            "Negotiate in professional settings",
        ],
    },
    "C2": {
        "title": "Mastery – Near-native fluency",
        "grammar": [
            "Mastery of all tenses and structures",
            "Subtle nuance in modal usage",
            "Stylistic inversion for effect",
            "Literary and rhetorical devices",
            "Punctuation for effect (dashes, semicolons, colons)",
        ],
        "vocabulary": [
            "Rare and specialized vocabulary",
            "Cultural references and idioms",
            "Regional variations (US vs UK vs Australia)",
            "Wordplay and double meanings",
            "Proverbs and literary quotes",
        ],
        "conversation_topics": [
            "Write poetry or creative texts",
            "Understand and use humor across cultures",
            "Give academic lectures",
            "Write persuasive essays",
            "Master professional and academic writing",
            "Speak naturally in any context",
        ],
    },
}

COMMON_MISTAKES = {
    "spanish_speakers": [
        ("false friend", "Actually (actualmente→actually, not 'actually' meaning 'currently')"),
        ("false friend", "Library vs Bookstore (biblioteca≠librería)"),
        ("false friend", "Sensitive vs Sensible (sensible≠sensitive)"),
        ("false friend", "Realize vs Make reality (realizar≠to realize)"),
        ("false friend", "Constipated vs Congested (constipado≠constipated)"),
        ("grammar", "Do/Does omission: 'He speaks' NOT 'He speak'"),
        ("grammar", "Adjective position: 'The red car' NOT 'the car red'"),
        ("grammar", "Subject always present: 'It is cold' NOT 'Is cold'"),
        ("grammar", "Double negatives: 'I don't have anything' NOT 'I don't have nothing'"),
        ("pronunciation", "V vs B: 'very' vs 'berry'"),
        ("pronunciation", "H sound: 'hotel' with H, not silent"),
        ("pronunciation", "TH sound: 'think' vs 'sink' vs 'that'"),
        ("vocabulary", "Make vs Do: 'make a decision' NOT 'do a decision'"),
        ("vocabulary", "Know vs Meet: 'I met him' NOT 'I knew him (first time)'"),
        ("vocabulary", "In vs On vs At: prepositions of time/place"),
    ],
    "general": [
        ("grammar", "Its vs It's: possessive vs contraction"),
        ("grammar", "Your vs You're"),
        ("grammar", "There/Their/They're"),
        ("grammar", "To/Too/Two"),
        ("grammar", "Then vs Than"),
        ("pronunciation", "Silent letters: 'knee', 'write', 'hour'"),
        ("pronunciation", "Schwa sound: the most common vowel sound"),
    ],
}


def _load_progress() -> dict:
    try:
        if PROGRESS_FILE.exists():
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "current_level": "A1",
        "lessons_completed": 0,
        "vocabulary_learned": [],
        "common_mistakes": [],
        "conversation_topics_done": [],
        "exercises_done": 0,
        "started": datetime.now().isoformat(),
        "last_session": None,
        "streak_days": 0,
    }


def _save_progress(data: dict):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_lesson(level: str, topic: str = "grammar") -> str:
    """Get a specific lesson from the curriculum."""
    if level not in CURRICULUM:
        return f"Level '{level}' not found. Available: {', '.join(LEVELS)}"
    lvl = CURRICULUM[level]
    result = f"# {level} – {lvl['title']}\n\n"
    if topic == "grammar":
        result += "## Grammar\n\n"
        for i, g in enumerate(lvl["grammar"], 1):
            result += f"{i}. {g}\n"
    elif topic == "vocabulary":
        result += "## Vocabulary\n\n"
        for i, v in enumerate(lvl["vocabulary"], 1):
            result += f"{i}. {v}\n"
    elif topic == "conversation":
        result += "## Conversation Topics\n\n"
        for i, c in enumerate(lvl["conversation_topics"], 1):
            result += f"{i}. {c}\n"
    elif topic == "all":
        result += "## Grammar\n\n"
        for i, g in enumerate(lvl["grammar"], 1):
            result += f"{i}. {g}\n"
        result += "\n## Vocabulary\n\n"
        for i, v in enumerate(lvl["vocabulary"], 1):
            result += f"{i}. {v}\n"
        result += "\n## Conversation Topics\n\n"
        for i, c in enumerate(lvl["conversation_topics"], 1):
            result += f"{i}. {c}\n"
    else:
        return f"Topic '{topic}' not found. Available: grammar, vocabulary, conversation, all"
    return result


def _get_exercise(level: str, count: int = 3) -> str:
    """Generate a practice exercise for the given level."""
    if level not in CURRICULUM:
        return f"Level '{level}' not found."
    lvl = CURRICULUM[level]
    grammar_pts = random.sample(lvl["grammar"], min(count, len(lvl["grammar"])))
    vocab_pts = random.sample(lvl["vocabulary"], min(2, len(lvl["vocabulary"])))
    result = f"## 📝 Practice Exercise ({level})\n\n"
    result += "### Translate to English:\n\n"
    # Simple translation exercises based on grammar
    translation_exercises = {
        "A1": [
            ("Yo soy Daniel.", "I am Daniel."),
            ("Ella es mi hermana.", "She is my sister."),
            ("El gato está en la mesa.", "The cat is on the table."),
            ("Tengo dos perros.", "I have two dogs."),
            ("¿Cómo te llamas?", "What's your name?"),
        ],
        "A2": [
            ("Ayer fui al parque.", "Yesterday I went to the park."),
            ("Ella está cocinando ahora.", "She is cooking now."),
            ("Voy a viajar mañana.", "I am going to travel tomorrow."),
            ("Este libro es más interesante.", "This book is more interesting."),
            ("¿Has visitado algún museo?", "Have you visited any museum?"),
        ],
        "B1": [
            ("Nunca he comido sushi.", "I have never eaten sushi."),
            ("Si estudias, aprobarás el examen.", "If you study, you will pass the exam."),
            ("El libro fue escrito por García Márquez.", "The book was written by García Márquez."),
            ("Deberías hacer ejercicio regularmente.", "You should exercise regularly."),
            ("Estoy acostumbrado a levantarme temprano.", "I am used to waking up early."),
        ],
        "B2": [
            ("Si hubiera sabido, habría venido antes.", "If I had known, I would have come earlier."),
            ("Me dijeron que la reunión se canceló.", "I was told that the meeting was canceled."),
            ("Ojalá hubiera estudiado más inglés.", "I wish I had studied more English."),
            ("No solo aprendió inglés, sino también francés.", "Not only did she learn English, but also French."),
        ],
        "C1": [
            ("Difícilmente podría haber imaginado un resultado mejor.", "Hardly could I have imagined a better outcome."),
            ("Lo que necesitamos es una estrategia más clara.", "What we need is a clearer strategy."),
            ("A pesar de las dificultades, el proyecto se completó a tiempo.", "Despite the difficulties, the project was completed on time."),
        ],
        "C2": [],
    }
    if level in translation_exercises and translation_exercises[level]:
        exs = random.sample(translation_exercises[level], min(3, len(translation_exercises[level])))
        for i, (es, en) in enumerate(exs, 1):
            result += f"{i}. {es}\n"
        result += "\n*(Check your answers with me!)*\n\n"
    result += f"### Practice these grammar points:\n\n"
    for g in grammar_pts:
        result += f"- {g}\n"
    result += f"\n### Vocabulary to use:\n\n"
    for v in vocab_pts:
        result += f"- {v}\n"
    result += f"\nWrite a short paragraph using these. I'll correct it! 📝"
    return result


def english_teacher(parameters: dict, player=None) -> str:
    """
    Profesora de ingles integrada en Eris.

    Acciones:
      - curriculum: Mostrar el currículum completo A1-C2
      - lesson: Obtener lección de un nivel. Parametros: level (A1-C2), topic (grammar|vocabulary|conversation|all)
      - exercise: Generar ejercicio de práctica. Parametros: level (A1-C2), count (default 3)
      - progress: Mostrar progreso del aprendizaje
      - assess: Evaluar nivel actual basado en conversación. Parameter: skill (grammar|vocabulary|pronunciation|all)
      - mistakes: Ver errores comunes (para hispanohablantes)
      - advance: Subir de nivel (cuando el usuario domina el actual)
      - save_lesson: Guardar la lección actual en Obsidian vault
    """
    action = parameters.get("action", "curriculum").lower()
    data = _load_progress()

    if action == "curriculum":
        result = "**📚 English Curriculum A1 → C2**\n\n"
        for level in LEVELS:
            lvl = CURRICULUM[level]
            current = " ◀ YOU ARE HERE" if level == data["current_level"] else ""
            result += f"**{level}** – {lvl['title']}{current}\n"
            result += f"  📖 {len(lvl['grammar'])} grammar points | {len(lvl['vocabulary'])} vocab topics | {len(lvl['conversation_topics'])} conversation topics\n\n"
        result += f"\nYour current level: **{data['current_level']}** | Lessons completed: {data['lessons_completed']} | Exercises: {data['exercises_done']}"
        return result

    elif action == "lesson":
        level = parameters.get("level", data["current_level"]).upper()
        topic = parameters.get("topic", "all")
        return _get_lesson(level, topic)

    elif action == "exercise":
        level = parameters.get("level", data["current_level"]).upper()
        count = int(parameters.get("count", 3))
        data["exercises_done"] += 1
        _save_progress(data)
        return _get_exercise(level, count)

    elif action == "progress":
        result = f"**📊 English Learning Progress**\n\n"
        result += f"Current level: **{data['current_level']}** ({LEVEL_NAMES.get(data['current_level'], '')})\n"
        result += f"Lessons completed: {data['lessons_completed']}\n"
        result += f"Exercises done: {data['exercises_done']}\n"
        result += f"Vocabulary learned: {len(data['vocabulary_learned'])} words\n"
        result += f"Conversation topics covered: {len(data['conversation_topics_done'])}\n"
        if data.get("started"):
            result += f"Started: {data['started'][:10]}\n"
        if data.get("last_session"):
            result += f"Last session: {data['last_session'][:19]}\n"
        if data.get("common_mistakes"):
            result += f"\nCommon mistakes tracked: {len(data['common_mistakes'])}\n"
        return result

    elif action == "assess":
        # Quick self-assessment questions
        skill = parameters.get("skill", "all")
        result = "**🔍 Quick Level Self-Assessment**\n\n"
        result += "Rate yourself 1-5 on these:\n\n"
        if skill in ("grammar", "all"):
            result += "**Grammar:**\n"
            result += "1. I can say 'I am' and 'you are' correctly\n"
            result += "2. I can talk about the past (I went, I ate)\n"
            result += "3. I can use present perfect (I have visited)\n"
            result += "4. I can use conditionals (if I had, I would)\n"
            result += "5. I can use advanced structures (inversion, etc.)\n\n"
        if skill in ("vocabulary", "all"):
            result += "**Vocabulary:**\n"
            result += "1. I know basic words (food, family, colors)\n"
            result += "2. I can talk about work and hobbies\n"
            result += "3. I can discuss abstract topics\n"
            result += "4. I use idioms and collocations\n"
            result += "5. I know specialized vocabulary\n\n"
        if skill in ("pronunciation", "all"):
            result += "**Pronunciation:**\n"
            result += "1. I can say the TH sound correctly\n"
            result += "2. I can distinguish V and B\n"
            result += "3. I use the schwa sound naturally\n"
            result += "4. My intonation sounds natural\n"
            result += "5. People understand me easily\n\n"
        result += "Tell me your scores and I'll recommend your level!"
        return result

    elif action == "mistakes":
        lang = parameters.get("language", "spanish").lower()
        result = "**⚠️ Common Mistakes**\n\n"
        if lang == "spanish":
            result += "For Spanish speakers:\n\n"
            for cat, mistake in COMMON_MISTAKES["spanish_speakers"]:
                icon = {"false friend": "🔀", "grammar": "📐", "pronunciation": "🔊", "vocabulary": "📝"}.get(cat, "•")
                result += f"{icon} {mistake}\n"
        result += "\n**General mistakes:**\n\n"
        for cat, mistake in COMMON_MISTAKES["general"]:
            result += f"  • {mistake}\n"
        return result

    elif action == "advance":
        current = data["current_level"]
        idx = LEVELS.index(current)
        if idx >= len(LEVELS) - 1:
            return "🎉 You are already at the highest level (C2)! You've mastered English!"
        next_level = LEVELS[idx + 1]
        data["current_level"] = next_level
        data["lessons_completed"] += 1
        data["last_session"] = datetime.now().isoformat()
        _save_progress(data)
        return (
            f"🎉 **Congratulations!** You advanced from **{current}** to **{next_level}**!\n\n"
            f"New level: {next_level} – {LEVEL_NAMES[next_level]}\n\n"
            f"Ready for the next challenge? Use `lesson` to see what's new in {next_level}!"
        )

    elif action == "save_lesson":
        level = parameters.get("level", data["current_level"]).upper()
        topic = parameters.get("topic", "all")
        lesson = _get_lesson(level, topic)
        try:
            from actions.obsidian_brain import obsidian_note
            obsidian_note({
                "action": "write",
                "title": f"English Lesson {level} – {topic}",
                "folder": "Aprendizaje",
                "content": lesson,
                "tags": f"english,lesson,{level.lower()},{topic}"
            })
            return f"📚 Lesson saved to your Obsidian vault! (Aprendizaje/English Lesson {level} – {topic}.md)"
        except Exception as e:
            return f"Could not save to Obsidian: {e}"

    available = "curriculum | lesson | exercise | progress | assess | mistakes | advance | save_lesson"
    return f"Action '{action}' not found. Available: {available}"
