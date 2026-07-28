"""ask_user.py — Hace una pregunta estructurada al usuario con opciones."""
import json

def ask_user(parameters: dict, player=None) -> str:
    question = parameters.get("question", "").strip()
    options = parameters.get("options", [])
    allow_custom = bool(parameters.get("allow_custom", False))
    default = parameters.get("default", "")

    if not question:
        return "Pregunta requerida."

    if options:
        lines = [f"[PREGUNTA] {question}"]
        for i, opt in enumerate(options, 1):
            lines.append(f"  {i}. {opt}")
        if allow_custom:
            lines.append(f"  (o di tu propia respuesta)")
        if default:
            lines.append(f"  (por defecto: {default})")
        lines.append("[Responde con el número, texto, o 'skip']")
        result = "\n".join(lines)
    else:
        result = f"[PREGUNTA] {question}"

    if player:
        player.write_log(f"❓ Preguntando al usuario: {question}")
    return result
