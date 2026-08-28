"""
plan_adaptation.py — Adaptación dinámica de planes para el agente de ERIS.

Cuando un paso del plan falla, en vez de repetir el mismo plan completo,
re-planifica dinámicamente con el contexto del fallo.

Flujo:
  1. Ejecutar paso del plan
  2. Si falla, analizar el error
  3. Generar un plan adaptado que:
     - Omite el paso fallido si es innecesario
     - Usa una herramienta alternativa
     - Ajusta los parámetros
     - Inserta pasos de diagnóstico
  4. Continuar con el plan adaptado
"""
from __future__ import annotations

import json
import re

try:
    from core.agent_architecture import _chat, _build_plan
except ImportError:
    _chat = None
    _build_plan = None


_ADAPT_SYS = (
    "Sos un re-planificador del agente de ERIS. Un paso del plan falló. "
    "Dado el plan original, el paso fallido y el error, generá un plan "
    "adaptado que esquive el problema.\n\n"
    "Reglas:\n"
    "- NO repitas el paso que falló exactamente igual.\n"
    "- Si el error es de herramienta, usá una alternativa.\n"
    "- Si el error es de parámetros, ajustalos.\n"
    "- Si el paso es innecesario, eliminalo.\n"
    "- Agregá un paso de diagnóstico si el error es ambiguo.\n"
    "- Mantener el objetivo original.\n\n"
    "Respondé SOLO con un JSON válido: "
    '{"adapted_steps": [{"descripcion": "...", "herramientas": ["tool1"]}], '
    '"reasoning": "por qué se adaptó así"}'
)


def adapt_plan(
    original_plan: list[dict],
    failed_step: dict,
    error: str,
    goal: str,
    completed_steps: list[str] = None,
) -> dict | None:
    """Adapta un plan cuando un paso falla.

    Args:
        original_plan: Plan original completo.
        failed_step: El paso que falló.
        error: Mensaje de error del paso.
        goal: Objetivo original.
        completed_steps: Pasos ya completados (para no repetir).

    Returns:
        dict con adapted_steps y reasoning, o None si no se pudo adaptar.
    """
    if _chat is None:
        return None

    completed = completed_steps or []
    completed_text = "\n".join(f"  ✓ {s}" for s in completed) if completed else "  (ninguno)"

    plan_text = "\n".join(
        f"  {s.get('step', '?')}. {s.get('description', '')} [{', '.join(s.get('tools', []))}]"
        for s in original_plan
    )

    try:
        resp = _chat([
            {"role": "system", "content": _ADAPT_SYS},
            {"role": "user", "content": (
                f"Objetivo: {goal}\n\n"
                f"Plan original:\n{plan_text}\n\n"
                f"Pasos completados:\n{completed_text}\n\n"
                f"Paso fallido: {failed_step.get('description', '?')}\n"
                f"Error: {error}\n\n"
                f"Generá un plan adaptado."
            )},
        ], max_tokens=1024)
        text = resp.get("content", "")
    except Exception:
        return None

    # Parsear respuesta
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        if "adapted_steps" in data and isinstance(data["adapted_steps"], list):
            return data
    except Exception:
        pass
    return None


def should_adapt(error: str, max_retries: int = 2, retry_count: int = 0) -> bool:
    """Determina si vale la pena adaptar el plan o simplemente reintentar.

    Args:
        error: Mensaje de error.
        max_retries: Máximo de reintentos antes de adaptar.
        retry_count: Cuántos reintentos ya se hicieron.

    Returns:
        True si se debe adaptar, False si se debe reintentar.
    """
    if retry_count >= max_retries:
        return True

    # Errores que indican que reintentar no sirve (hay que adaptar)
    adapt_indicators = [
        "no such file",
        "permission denied",
        "not found",
        "not available",
        "not installed",
        "connection refused",
        "timeout",
        "rate limit",
        "quota exceeded",
    ]
    error_lower = error.lower()
    for indicator in adapt_indicators:
        if indicator in error_lower:
            return True

    return False


def merge_plans(original: list[dict], adapted: list[dict], completed: list[str]) -> list[dict]:
    """Mergea el plan original con la adaptación, preservando lo completado.

    Args:
        original: Plan original.
        adapted: Pasos adaptados.
        completed: Descripciones de pasos ya completados.

    Returns:
        Nuevo plan mergeado.
    """
    # Empezar con los pasos completados (marcados como done)
    merged = []
    completed_set = {c.lower().strip() for c in completed}

    for step in original:
        desc = step.get("description", "").lower().strip()
        if any(c in desc or desc in c for c in completed_set):
            step["status"] = "completed"
            merged.append(step)

    # Agregar pasos adaptados
    for i, step in enumerate(adapted, 1):
        if isinstance(step, dict):
            step["step"] = len(merged) + i
            step["status"] = "pending"
            merged.append(step)

    return merged
