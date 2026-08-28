"""
reflection.py — Reflection loop para ERIS.

Antes de dar una respuesta final, el agente se auto-evalúa:
  1. ¿La respuesta es completa? ¿respondí TODO lo que preguntó?
  2. ¿Hay algo que no verifiqué?
  3. ¿Los datos son correctos o estoy inventando?
  4. ¿Hay un error lógico o de razonamiento?

Flujo:
  - El LLM genera una respuesta.
  - Un segundo paso de reflexión la evalúa con preguntas concretas.
  - Si detecta problemas, corrige la respuesta.
  - Si está OK, la devuelve tal cual.

Esto reduce alucinaciones y respuestas incompletas.
"""
from __future__ import annotations

import re

try:
    from core.agent_architecture import _chat
except ImportError:
    _chat = None


_REFLECT_SYS = (
    "Sos un verificador de calidad de respuestas. Dada la pregunta del usuario "
    "y una respuesta propuesta, evaluá si es correcta, completa y útil.\n\n"
    "Respondé EXACTAMENTE con este formato JSON (sin texto extra):\n"
    '{"ok": true/false, "issues": ["problema1", "problema2"], '
    '"score": 0-10, "improved": "versión mejorada o vacía si no hace falta"}\n\n'
    "Criterios de evaluación:\n"
    "- ¿La respuesta es completa? (responde TODO lo que se preguntó)\n"
    "- ¿Los datos son correctos? (no alucinar información)\n"
    "- ¿Hay algo que no se verificó y debería?\n"
    "- ¿El tono es apropiado? (no ser preachy, ser directo)\n"
    "- ¿Hay errores lógicos o de razonamiento?\n\n"
    "Si la respuesta es buena, devolvé ok=true y improved vacío.\n"
    "Si tiene problemas, devolvé ok=false con los issues y improved como versión corregida."
)


def _parse_reflection(text: str) -> dict | None:
    """Parsea el JSON de reflexión."""
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        data = __import__("json").loads(m.group(0))
        if isinstance(data, dict) and "ok" in data:
            return data
    except Exception:
        pass
    return None


def reflect(question: str, answer: str, max_retries: int = 1) -> dict:
    """Ejecuta el loop de reflexión sobre una respuesta.

    Args:
        question: Pregunta original del usuario.
        answer: Respuesta generada por el agente.
        max_retries: Cuántas veces intentar mejorar si hay issues.

    Returns:
        dict con keys: ok, issues, score, improved, final_answer
    """
    if _chat is None:
        return {
            "ok": True,
            "issues": [],
            "score": 5,
            "improved": "",
            "final_answer": answer,
            "reflections": 0,
        }

    current_answer = answer
    all_issues = []
    reflections = 0

    for attempt in range(max_retries + 1):
        reflections += 1
        try:
            resp = _chat([
                {"role": "system", "content": _REFLECT_SYS},
                {"role": "user", "content": f"Pregunta: {question}\n\nRespuesta:\n{current_answer}"},
            ], max_tokens=800)
            text = resp.get("content", "")
        except Exception:
            break

        result = _parse_reflection(text)
        if result is None:
            break

        all_issues.extend(result.get("issues", []))

        if result.get("ok", False):
            return {
                "ok": True,
                "issues": all_issues,
                "score": result.get("score", 7),
                "improved": "",
                "final_answer": current_answer,
                "reflections": reflections,
            }

        improved = result.get("improved", "").strip()
        if improved:
            current_answer = improved
        else:
            break

    return {
        "ok": len(all_issues) == 0,
        "issues": all_issues,
        "score": 5,
        "improved": current_answer if current_answer != answer else "",
        "final_answer": current_answer,
        "reflections": reflections,
    }


def quick_check(answer: str, max_len: int = 50) -> str:
    """Chequeo rápido sin LLM: detecta problemas obvios en la respuesta."""
    issues = []
    if not answer.strip():
        issues.append("Respuesta vacía")
    if len(answer) > 10000:
        issues.append(f"Respuesta muy larga ({len(answer)} chars)")
    if answer.count("[ERROR]") > 3:
        issues.append("Múltiples errores en la respuesta")
    if re.search(r"(no sé|no puedo|no tengo información|no estoy seguro)", answer, re.IGNORECASE):
        issues.append("Respuesta contiene incertidumbre explícita")
    if not issues:
        return ""
    return f"Chequeo rápido: {'; '.join(issues)}"
