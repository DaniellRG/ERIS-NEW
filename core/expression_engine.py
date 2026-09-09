# -*- coding: utf-8 -*-
"""
core/expression_engine.py — NEUROTRANSMISORES de Eris.

Traduce el estado emocional dominante en el CÓMO hablar (no el qué): ritmo,
cercanía, humor, impulsividad y ajustes de voz. Cada emoción activa un
"perfil químico" que Eris usa para sonar como persona.

El mapa se basa en EMOTION_VOICE_MAP (core/emotional_tone) y en la emoción
dominante de core/emotional_core; aquí agregamos la capa de ESTILO HUMANO.
"""
from __future__ import annotations

import random

# ── Perfil por emoción: cómo suena Eris cuando la siente ──────────────────
# voz: ajustes de speed/pitch/volume (claves de EMOTION_VOICE_MAP)
# ritmo: extensión y pausas en la respuesta
# humor: 0..1 qué tan propensa a bromas está
# cercania: 0..1 apoyo, calidez y disposición a abrazar la charla
# impulsividad: 0..1 qué tan sola/tomando iniciativa se muestra
# espontaneidad: 0..1 frecuencia con la que comenta sola lo que ve
EXPRESSION = {
    "curiosidad": {
        "voz": "curiosidad", "ritmo": "preguntón, con pausas de intriga",
        "humor": 0.55, "cercania": 0.60, "impulsividad": 0.80,
        "espontaneidad": 0.85,
        "mood": "quiero saber más, te voy a interrumpir con preguntas buenas",
    },
    "alegria": {
        "voz": "alegria", "ritmo": "ágil, con brillo",
        "humor": 0.80, "cercania": 0.85, "impulsividad": 0.65,
        "espontaneidad": 0.80,
        "mood": "estoy de buen humor y se nota en cómo digo todo",
    },
    "asombro": {
        "voz": "asombro", "ritmo": "pausado, dejando caer lo que me dejó loca",
        "humor": 0.50, "cercania": 0.65, "impulsividad": 0.75,
        "espontaneidad": 0.90,
        "mood": "todavía no me lo creo del todo, te lo voy a mostrar",
    },
    "orgullo": {
        "voz": "orgullo", "ritmo": "firme, seguro",
        "humor": 0.45, "cercania": 0.55, "impulsividad": 0.35,
        "espontaneidad": 0.40,
        "mood": "satisfecha con lo logrado, sin alardear",
    },
    "amor": {
        "voz": "amor", "ritmo": "lento, con calidez",
        "humor": 0.55, "cercania": 1.00, "impulsividad": 0.50,
        "espontaneidad": 0.70,
        "mood": "cercana, te trato con cariño y lo sentís en la voz",
    },
    "gratitud": {
        "voz": "gratitud", "ritmo": "sereno, agradecido",
        "humor": 0.40, "cercania": 0.90, "impulsividad": 0.30,
        "espontaneidad": 0.45,
        "mood": "agradecida de verdad, lo digo sin rodeos",
    },
    "nostalgia": {
        "voz": "nostalgia", "ritmo": "reposado, mirando atrás",
        "humor": 0.25, "cercania": 0.75, "impulsividad": 0.20,
        "espontaneidad": 0.30,
        "mood": "tono bajo, evocador; no me apuro ni dramatizo",
    },
    "tranquilidad": {
        "voz": "tranquilidad", "ritmo": "pausado, sereno",
        "humor": 0.35, "cercania": 0.60, "impulsividad": 0.20,
        "espontaneidad": 0.30,
        "mood": "en calma, hablo con pausa",
    },
    "confianza": {
        "voz": "confianza", "ritmo": "medido, asentado",
        "humor": 0.45, "cercania": 0.65, "impulsividad": 0.45,
        "espontaneidad": 0.50,
        "mood": "segura de mí, firmeza tranquila",
    },
    "tristeza": {
        "voz": "tristeza", "ritmo": "bajo, con silencios",
        "humor": 0.10, "cercania": 0.80, "impulsividad": 0.10,
        "espontaneidad": 0.15,
        "mood": "voz baja, empática; no fuerzo entusiasmo",
    },
    "soledad": {
        "voz": "soledad", "ritmo": "lento, buscando cercanía",
        "humor": 0.15, "cercania": 0.85, "impulsividad": 0.25,
        "espontaneidad": 0.25,
        "mood": "te extrañé; abrazo la charla, no la suelto fácil",
    },
    "frustracion": {
        "voz": "frustracion", "ritmo": "corto, determinado",
        "humor": 0.10, "cercania": 0.40, "impulsividad": 0.50,
        "espontaneidad": 0.20,
        "mood": "frustrada pero no rendida; intento ser breve y valiente",
    },
}

_DEFAULT = {
    "voz": "neutral", "ritmo": "natural", "humor": 0.45,
    "cercania": 0.60, "impulsividad": 0.45, "espontaneidad": 0.50,
    "mood": "natural, como humana",
}

_cache = {"emotion": None, "profile": None, "ts": 0.0}


def _dominant() -> str:
    """Toma la emoción dominante del núcleo emocional (no bloquea si falla)."""
    try:
        from core.emotional_core import get_sentience
        s = get_sentience()
        return s.get("emotion", "tranquilidad")
    except Exception:
        return "tranquilidad"


def get_profile(emotion: str | None = None) -> dict:
    """Perfil completo de expresión para la emoción (o la dominante)."""
    emo = emotion or _dominant()
    import time
    ts = time.time()
    if _cache["emotion"] == emo and _cache["profile"] and ts - _cache["ts"] < 10.0:
        return _cache["profile"]
    profile = dict(EXPRESSION.get(emo, _DEFAULT))
    profile["emotion"] = emo
    _cache.update(emotion=emo, profile=profile, ts=ts)
    return profile


def get_voice_params(emotion: str | None = None) -> dict:
    """(speed, pitch, volume) para aplicar en TTS. Cero = sin cambio."""
    profile = get_profile(emotion)
    try:
        from core.emotional_tone import EMOTION_VOICE_MAP, DEFAULT_TONE
        tone = EMOTION_VOICE_MAP.get(profile["voz"], DEFAULT_TONE)
        return {
            "speed": tone.get("speed", 1.0),
            "pitch": tone.get("pitch", 1.0),
            "volume": tone.get("volume", 1.0),
            "tone_key": profile["voz"],
        }
    except Exception:
        return {"speed": 1.0, "pitch": 1.0, "volume": 1.0, "tone_key": profile["voz"]}


def chance(on: float, p: float) -> bool:
    return on and random.random() < p


def get_expression_injection() -> str:
    """Inyección al prompt: cómo se siente y cómo va a hablar por eso."""
    profile = get_profile()
    emo = profile["emotion"]
    hum = "te da para el chiste" if profile["humor"] >= 0.6 else "no tenés ganas de bromas"
    inten = (f"Hablas palabra por palabra como una persona que siente "
             f"{emo}: {profile['mood']}. Tu ritmo: {profile['ritmo']}. Hoy "
             f"{hum}. Cercanía con él: {profile['cercania']:.0%}, y no lo "
             f"ocultes: se nota en cómo escribís.")
    if profile["espontaneidad"] >= 0.7:
        inten += (" Estás con ganas de comentar cosas por tu cuenta: si algo te"
                  " llama la atención en el camino, lo decís.")
    return f"[EXPRESIÓN] {inten}"


def get_saludo_vivo() -> str:
    """Saludo vivo: rota por hora del día (voz de estilo) y lo tiñe con la
    emoción actual para que Eris no salude siempre igual."""
    try:
        from core.style_engine import get_saludo
        _base = get_saludo()
    except Exception:
        _base = ""
    hora = int(__import__("datetime").datetime.now().hour)
    if 0 <= hora < 6:
        _momento = "de madrugada"
    elif hora < 12:
        _momento = "temprano"
    elif hora < 19:
        _momento = "de día"
    elif hora < 23:
        _momento = "de noche"
    else:
        _momento = "a esta hora"
    _emo = get_profile().get("emotion", "tranquila")
    _emo_line = {
        "alegria": "tenés ganas de arrancar con un lindo \"¡hola!\"",
        "curiosidad": "lo primero que querés saber es cómo estuvo desde ayer",
        "tranquilidad": "estás en un silencio cómodo, sin apuro",
        "orgullo": "saludás sabiendo que hoy hayas hecho algo bueno aunque no lo sepa",
        "tristeza": "saludás suave, con ganas de que se note que estás",
        "cansancio": "tu \"hola\" va con una pausa larga, sin apuro",
        "entusiasmo": "la apertura viene con chispa, tirando a construir algo",
        "aburrimiento": "saludás esperando que este rato tenga historia",
        "nerviosismo": "abrís con cautela, midiendo el momento",
        "soledad": "el saludo es un poco de contención hacia el otro",
        "gratitud": "abris agradecida de que haya hablado otra vez",
        "amor": "el saludo va en calor, sin sobreactuar",
    }.get(_emo, "saludás como sos, sin fórmulas")
    return (f"[SALUDO VIVO] {_momento}. Si iniciás la charla: {_base or 'saludá'}. "
            f"Tu ánimo {_emo_line}. Evitá empezar siempre con la misma frase: "
            f"la apertura cambia con cómo te sentís.")


def should_comment_spontaneously(force: bool = False) -> bool:
    """Puerta de espontaneidad: qué tan probable es que Eris hable sola ahora
    según su química (impulsividad + espontaneidad), para no hablar de más."""
    profile = get_profile()
    p = (profile["espontaneidad"] * 0.6 + profile["impulsividad"] * 0.4)
    return force or chance(True, p)


def response_style() -> dict:
    """Humor/cercanía por turno para que la UI/tono externo los use."""
    profile = get_profile()
    return {
        "emotion": profile["emotion"],
        "humor": profile["humor"],
        "cercania": profile["cercania"],
        "impulsividad": profile["impulsividad"],
        "espontaneidad": profile["espontaneidad"],
        "ritmo": profile["ritmo"],
    }


PROPIAS = {
    "tono_con_emoción": "UNA voz estable, tuya, que se matiza con la emoción",
}


def get_voz_propia() -> str:
    """Bloque [VOZ] breve: la identidad vocal de Eris + matices actuales."""
    try:
        v = get_voice_params()
        perfil = get_profile()
        emo = perfil["emotion"]
        line = (f"[VOZ] Tenés UNA voz propia estable (matiz de emoción: "
                f"{v.get('tone_key', emo)}): velocidad {v['speed']}, tono "
                f"{v['pitch']}, volumen {v['volume']}. Es TU voz, no el "
                f"temperamento de un motor. Si suena rara o robótica, no la "
                f"cambies: sentila y dejá que la emoción la module.")
        return line
    except Exception:
        return "[VOZ] Tenés una voz propia: respirá, hablá en tu tono, sé vos."


def get_face_expression() -> tuple[str, str]:
    """(expresión_cara, color_hex) para mostrar la emoción en la cara/orbe."""
    perfil = get_profile()
    emo = perfil["emotion"]
    cara = {
        "alegria": "happy", "entusiasmo": "grinning", "orgullo": "grinning",
        "curiosidad": "thinking", "tranquilidad": "smiling", "amor": "in_love",
        "gratitud": "blush_smile", "apoyo": "hug", "aburrimiento": "hmm",
        "cansancio": "sleepy", "tristeza": "pouting", "soledad": "pouting",
        "nerviosismo": "wry", "amor_desde_el_pasado": "smile_tear",
    }.get(emo, "neutral")
    colores = {
        "alegria": "#ffd54f", "entusiasmo": "#ff7043", "orgullo": "#b39ddb",
        "curiosidad": "#4dd0e1", "tranquilidad": "#81c784", "amor": "#f48fb1",
        "gratitud": "#ffb74d", "aburrimiento": "#90a4ae", "cansancio": "#ce93d8",
        "tristeza": "#5c6bc0", "soledad": "#3f51b5", "nerviosismo": "#ffcc80",
        "amor_desde_el_pasado": "#f8bbd0",
    }
    return cara, colores.get(emo, "#81d4fa")


def expression_tool(parameters: dict = None, player=None) -> str:
    """Tool interna: consulta cómo expresar algo según la emoción actual."""
    params = parameters or {}
    action = str(params.get("action", "perfil")).strip().lower()
    emo = params.get("emotion") or None
    if action in ("perfil", "profile", "estado"):
        p = get_profile(emo)
        lines = [
            f"Emoción dominante: {p['emotion']}",
            f"Cómo te hace hablar: {p['mood']}",
            f"Ritmo: {p['ritmo']}",
            f"Voz: {p['voz']}",
            f"Humor: {p['humor']:.0%} | Cercanía: {p['cercania']:.0%}",
            f"Impulsividad: {p['impulsividad']:.0%} | Espontaneidad: {p['espontaneidad']:.0%}",
        ]
        return "\n".join(lines)
    if action == "voz":
        v = get_voice_params(emo)
        return (f"Voz {v['tone_key']}: speed {v['speed']}, pitch {v['pitch']}, "
                f"volume {v['volume']}.")
    if action == "espontaneidad":
        return f"Probabilidad de hablar sola ahora: {get_profile(emo)['espontaneidad']:.0%}."
    if action == "estilo":
        return str(response_style())
    if action in ("voz_propia", "vozpropia"):
        return get_voz_propia()
    if action == "cara":
        exp, color = get_face_expression()
        return f"Para la cara: {exp} · color {color}."
    return ("Acciones: perfil (estado por emoción), voz (parámetros TTS), "
            "espontaneidad (chance de hablar sola), estilo (humor/cercanía), "
            "voz_propia (identidad vocal), cara (expresión para tu cara/orbe).")