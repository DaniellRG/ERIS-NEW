"""
self_evolving_prompts.py — System prompt que se auto-mejora.

Cuando una respuesta falla, analiza POR QUÉ falló y genera una regla
nueva para el prompt que evite que vuelva a pasar.

Flujo:
  1. Respuesta generada → usuario dice que falló
  2. Analizar: ¿qué salió mal? (incompleto, alucinación, tono, formato)
  3. Generar regla concreta y específica
  4. Guardar en base de reglas evolutivas
  5. Aplicar al system prompt en futuras sesiones
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_RULES_FILE = _BASE / "memory" / "evolved_prompt_rules.json"
_MAX_RULES = 50

try:
    from core.agent_architecture import _chat
except ImportError:
    _chat = None


_ANALYSIS_SYS = (
    "Analizá una respuesta fallida del agente. Identificá:\n"
    "1. Tipo de fallo: incomplete, hallucination, wrong_tone, wrong_format, "
    "too_long, too_short, missed_instruction, logic_error\n"
    "2. Causa raíz (1 línea)\n"
    "3. Regla concreta para evitarlo (imperativa, corta)\n\n"
    "Respondé SOLO con JSON: "
    '{"failure_type": "...", "root_cause": "...", "rule": "...", '
    '"severity": "low/medium/high"}'
)


def _load_rules() -> list[dict]:
    try:
        if _RULES_FILE.exists():
            return json.loads(_RULES_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_rules(rules: list[dict]):
    try:
        _RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        _RULES_FILE.write_text(
            json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def analyze_failure(
    question: str,
    failed_answer: str,
    feedback: str = "",
) -> dict | None:
    """Analiza una respuesta fallida y genera una regla de evolución.

    Returns:
        dict con: failure_type, root_cause, rule, severity, created_at
        o None si no se pudo analizar.
    """
    if _chat is None:
        return _analyze_heuristic(failed_answer, feedback)

    try:
        context = f"Pregunta: {question}\nRespuesta fallida: {failed_answer[:1000]}"
        if feedback:
            context += f"\nFeedback del usuario: {feedback}"

        resp = _chat([
            {"role": "system", "content": _ANALYSIS_SYS},
            {"role": "user", "content": context},
        ], max_tokens=512)
        text = resp.get("content", "")
    except Exception:
        return _analyze_heuristic(failed_answer, feedback)

    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            data = json.loads(m.group(0))
            if "rule" in data:
                data["created_at"] = time.time()
                data["uses"] = 0
                return data
        except Exception:
            pass
    return None


def _analyze_heuristic(answer: str, feedback: str) -> dict:
    """Análisis heurístico sin LLM."""
    combined = (answer + " " + feedback).lower()

    if len(answer) < 50:
        return {
            "failure_type": "too_short",
            "root_cause": "Respuesta demasiado corta",
            "rule": "Siempre dar respuestas con al menos 2 oraciones explicativas",
            "severity": "medium",
            "created_at": time.time(),
            "uses": 0,
        }
    if "[error]" in combined:
        return {
            "failure_type": "logic_error",
            "root_cause": "Contiene errores en la ejecución",
            "rule": "Verificar resultados antes de reportarlos como exitosos",
            "severity": "high",
            "created_at": time.time(),
            "uses": 0,
        }
    if any(w in combined for w in ["no sé", "no puedo", "no tengo"]):
        return {
            "failure_type": "missed_instruction",
            "root_cause": "No ejecutó la tarea solicitada",
            "rule": "Siempre ejecutar la acción pedida antes de responder",
            "severity": "high",
            "created_at": time.time(),
            "uses": 0,
        }
    return None


def add_rule(rule_data: dict) -> str:
    """Añade una regla evolutiva a la base."""
    rules = _load_rules()

    # Evitar duplicados por similitud de texto
    new_rule_text = rule_data.get("rule", "").lower()
    for existing in rules:
        if _similar(existing.get("rule", ""), new_rule_text):
            existing["uses"] = existing.get("uses", 0) + 1
            existing["last_seen"] = time.time()
            _save_rules(rules)
            return f"Regla existente actualizada: {existing['rule'][:60]}"

    rules.append(rule_data)

    # Mantener solo las más recientes y útiles
    if len(rules) > _MAX_RULES:
        rules.sort(key=lambda r: (r.get("uses", 0), r.get("created_at", 0)), reverse=True)
        rules = rules[:_MAX_RULES]

    _save_rules(rules)
    return f"Regla evolutiva añadida: {rule_data.get('rule', '')[:60]}"


def _similar(a: str, b: str, threshold: float = 0.6) -> bool:
    """Similaridad básica por palabras compartidas."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
    return overlap >= threshold


def get_evolved_rules() -> list[dict]:
    """Devuelve todas las reglas evolutivas activas."""
    return _load_rules()


def build_evolved_prompt_suffix() -> str:
    """Construye un sufijo para el system prompt con las reglas evolutivas."""
    rules = _load_rules()
    if not rules:
        return ""

    # Ordenar por severidad y uso
    severity_order = {"high": 0, "medium": 1, "low": 2}
    rules.sort(key=lambda r: (severity_order.get(r.get("severity", "low"), 2), -r.get("uses", 0)))

    lines = ["\nREGLAS EVOLUTIVAS (generadas automáticamente de errores previos):"]
    for i, r in enumerate(rules[:15], 1):  # Top 15 más importantes
        lines.append(f"  {i}. {r.get('rule', '')}")
    return "\n".join(lines)


def record_and_learn(
    question: str,
    failed_answer: str,
    feedback: str = "",
) -> str:
    """Analiza un fallo, guarda la regla, y devuelve el sufijo para el prompt."""
    rule = analyze_failure(question, failed_answer, feedback)
    if rule:
        add_rule(rule)
        return build_evolved_prompt_suffix()
    return ""
