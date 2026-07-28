import random
from datetime import datetime

JOKES = [
    "¿Por qué los programadores prefieren el modo oscuro? Porque la luz atrae a los bugs.",
    "Un SQL entra a un bar, ve dos mesas y pregunta: ¿Puedo hacer JOIN?",
    "¿Qué le dijo un byte a otro byte? Tú eres mi complemento a dos.",
    "¿Por qué C no puede crear hijos? Porque tiene punteros, no genes.",
    "Hay 10 tipos de personas: las que entienden binario y las que no.",
    "¿Qué hace un desarrollador cuando muere? Su家属 hace push al cielo.",
    "Un programador fue al médico. Doctor: Tiene mala circulación. Programador: ¿Puede ponerlo en un loop?",
    "¿Cuál es el café favorito de un programador? Java.",
    "¿Por qué el programador fue a la playa? Para ver el mar de datos.",
    "Un bug en el código es como una aguja en un pajar: difícil de encontrar, fácil de culpar al ganado.",
    "¿Qué dijo el computer cuando se enfermó? Tengo un virus.",
    "¿Por qué los desarrolladores odian la naturaleza? Porque tiene demasiados bugs.",
    "¿Qué hace un programador en la iglesia? Debugging de sus pecados.",
    "Un desarrollador pidió un café. El barista le trajo una taza de NULL.",
    "¿Cuántos programadores se necesitan para cambiar un foco? Ninguno, eso es problema de hardware.",
]

FUN_FACTS = [
    "El primer computer pesaba 27 toneladas y ocupaba una habitación entera.",
    "El email fue inventado antes que Internet.",
    "El 50% de los programadores tienen al menos un bug que no pueden encontrar.",
    "Java fue originalmente llamado 'Oak' (roble).",
    "El nombre 'WiFi' no significa nada — es solo un nombre comercial.",
    "El computer más rápido del mundo puede hacer 200 billones de cálculos por segundo.",
    "Python fue nombrado por Monty Python, no por la serpiente.",
    "El primer computer personal costaba $1,795 en 1975.",
    "GitHub tiene más de 200 millones de repositorios.",
    "El 70% de los errores de software son causados por errores humanos.",
    "La primera computadora programable fue el ENIAC, en 1945.",
    "El término 'bug' vino de un insecto real encontrado en una computadora Harvard en 1947.",
    "El primer video de YouTube duró 18 segundos y era sobre elefantes.",
    "Un byte puede representar hasta 256 valores diferentes.",
    "El Internet original solo conectaba 4 universidades en 1969.",
]

TRIVIA_QUESTIONS = [
    {"q": "¿Qué lenguaje se usa más en inteligencia artificial?", "a": "Python", "opts": ["Java", "Python", "C++", "Ruby"]},
    {"q": "¿Cuántos bits tiene un byte?", "a": "8", "opts": ["4", "8", "16", "32"]},
    {"q": "¿Qué significa HTML?", "a": "HyperText Markup Language", "opts": ["HyperText Markup Language", "High Tech Modern Language", "Home Tool Markup Language", "Hyper Transfer Markup Language"]},
    {"q": "¿En qué año se fundó Google?", "a": "1998", "opts": ["1995", "1998", "2000", "2001"]},
    {"q": "¿Qué empresa creó Windows?", "a": "Microsoft", "opts": ["Apple", "Microsoft", "Google", "IBM"]},
    {"q": "¿Qué es un algoritmo?", "a": "Un conjunto de pasos para resolver un problema", "opts": ["Un tipo de virus", "Un conjunto de pasos para resolver un problema", "Un lenguaje de programación", "Un hardware especial"]},
    {"q": "¿Cuál es la capital de Corea del Sur?", "a": "Seúl", "opts": ["Seúl", "Tokio", "Pekín", "Bangkok"]},
    {"q": "¿Qué planeta es el más grande del sistema solar?", "a": "Júpiter", "opts": ["Saturno", "Júpiter", "Neptuno", "Urano"]},
    {"q": "¿Cuántos continentes hay?", "a": "7", "opts": ["5", "6", "7", "8"]},
    {"q": "¿Qué animal es el más rápido del mundo?", "a": "Guepardo", "opts": ["León", "Guepardo", "Águila", "Caballo"]},
]

def fun_mode(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "random").lower()
    category = parameters.get("category") or ""

    if player:
        player.write_log(f"😄 Fun mode: {action}")

    if action in ("joke", "chiste", "reir"):
        return random.choice(JOKES)
    elif action in ("fact", "dato", "curiosidad", "datos"):
        return random.choice(FUN_FACTS)
    elif action in ("trivia", "trivial", "pregunta"):
        return _get_trivia()
    elif action in ("answer", "responder", "contestar"):
        return _check_answer(parameters.get("answer") or "")
    elif action in ("score", "puntos", "puntuacion"):
        return _get_score()
    elif action in ("jokes", "chistes"):
        return "\n".join(random.sample(JOKES, min(5, len(JOKES))))
    elif action in ("facts", "datos"):
        return "\n".join(random.sample(FUN_FACTS, min(5, len(FUN_FACTS))))
    else:
        category = random.choice(["joke", "fact", "trivia"])
        if category == "joke":
            return "😄 " + random.choice(JOKES)
        elif category == "fact":
            return "📚 " + random.choice(FUN_FACTS)
        else:
            return _get_trivia()

_trivia_state = {"current": None, "correct": 0, "total": 0}

def _get_trivia():
    q = random.choice(TRIVIA_QUESTIONS)
    _trivia_state["current"] = q
    options = q["opts"]
    opts_str = "\n".join(f"  {i+1}. {opt}" for i, opt in enumerate(options))
    return f"❓ {q['q']}\n\n{opts_str}\n\nRespondé con el número o el texto de la opción."

def _check_answer(answer):
    current = _trivia_state.get("current")
    if not current:
        return "No hay trivia activa. Pedime una pregunta."

    _trivia_state["total"] += 1
    correct = current["a"]
    if answer.strip().lower() == correct.lower() or answer.strip() in ("1", "2", "3", "4"):
        try:
            idx = int(answer.strip()) - 1
            if 0 <= idx < len(current["opts"]) and current["opts"][idx] == correct:
                _trivia_state["correct"] += 1
                return f"✅ ¡Correcto! La respuesta es: {correct}\n\nPuntaje: {_trivia_state['correct']}/{_trivia_state['total']}"
        except:
            pass
        if answer.strip().lower() == correct.lower():
            _trivia_state["correct"] += 1
            return f"✅ ¡Correcto! La respuesta es: {correct}\n\nPuntaje: {_trivia_state['correct']}/{_trivia_state['total']}"

    return f"❌ Incorrecto. La respuesta correcta era: {correct}\n\nPuntaje: {_trivia_state['correct']}/{_trivia_state['total']}"

def _get_score():
    c = _trivia_state["correct"]
    t = _trivia_state["total"]
    if t == 0:
        return "Aún no jugaste ninguna trivia."
    return f"Tu puntaje: {c}/{t} ({c/t*100:.0f}% de aciertos)"
