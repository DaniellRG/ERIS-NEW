"""ask_user.py — Hace una pregunta estructurada al usuario con opciones.

Soporta menú interactivo estilo opencode:
  * single (una opción) o multi (varias)
  * recommended: opción destacada con ⭐
  * allow_custom: el usuario puede escribir su propia respuesta
  * default: placeholder del campo custom
Devuelve [RESPUESTA] con el índice, la lista de índices o el texto custom.
"""
import json


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "si", "y")
    return bool(value)


def ask_user(parameters: dict, player=None) -> str:
    question = parameters.get("question", "").strip()
    options = parameters.get("options", [])
    allow_custom = bool(parameters.get("allow_custom", False))
    default = parameters.get("default", "")
    multi = _to_bool(parameters.get("multi", False))
    recommended = parameters.get("recommended", "")

    # options: llega como lista (registro del dispatcher) o string separado por coma
    if isinstance(options, str):
        options = [o.strip() for o in options.split(",") if o.strip()]
    elif not isinstance(options, list):
        options = list(options or [])

    if not question:
        q = "Pregunta requerida."
        if options:
            return q + " Opciones: " + ", ".join(options)
        return q

    # Bloqueante real: si la UI expone ask() (diálogo modal interactivo), espera respuesta.
    ask = getattr(player, "ask", None)
    if ask is not None:
        try:
            answer = ask(question, options, timeout=120,
                         multi=multi, recommended=recommended,
                         allow_custom=allow_custom, default=default)
            if answer is not None and answer != "skip":
                return f"[RESPUESTA] {answer}"
        except Exception:
            pass

    # Fallback textual (CLI / sin UI)
    if options:
        lines = [f"[PREGUNTA] {question}"]
        for i, opt in enumerate(options, 1):
            star = " ⭐" if recommended and (
                (isinstance(recommended, int) and recommended == i - 1)
                or str(recommended).strip().lower() == str(opt).strip().lower()
            ) else ""
            lines.append(f"  {i}. {opt}{star}")
        if allow_custom:
            lines.append("  (o di tu propia respuesta)")
        if default:
            lines.append(f"  (por defecto: {default})")
        lines.append("[Responde con el número, texto, o 'skip']")
        result = "\n".join(lines)
    else:
        result = f"[PREGUNTA] {question}"
        if default:
            result += f" (por defecto: {default})"

    if player:
        player.write_log(f"❓ Preguntando al usuario: {question}")
    return result