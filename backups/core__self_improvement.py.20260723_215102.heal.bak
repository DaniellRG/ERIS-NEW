"""
self_improvement.py — ERIS Self-Improvement System.
Simulates AGI-like autonomous learning and self-optimization.

Components:
  - Self-evaluation: Post-response quality assessment
  - Auto-correction: Learn from mistakes
  - Prompt optimization: Adjust prompts based on what works
  - Error pattern detection: Identify and fix recurring issues
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

_BASE = Path(__file__).resolve().parent.parent
_IMPROVEMENT_DIR = _BASE / "memory"
_EVALUATION_FILE = _IMPROVEMENT_DIR / "self_evaluation.json"
_CORRECTION_FILE = _IMPROVEMENT_DIR / "auto_corrections.json"
_PROMPT_OPT_FILE = _IMPROVEMENT_DIR / "prompt_optimization.json"
_ERROR_PATTERNS_FILE = _IMPROVEMENT_DIR / "error_patterns.json"
_LEARNED_LESSONS_FILE = _IMPROVEMENT_DIR / "learned_lessons.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text("utf-8"))
    except Exception:
        pass
    return default or []

def _save_json(path: Path, data: Any):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    except Exception as e:
        print(f"[SelfImprovement] Save error: {e}")

# ── Self-Evaluation ───────────────────────────────────────────────────────────

class SelfEvaluator:
    """Evaluate response quality after each interaction."""

    def __init__(self):
        self.evaluations = _load_json(_EVALUATION_FILE, [])

    def evaluate(self, user_input: str, response: str, context: dict = None) -> dict:
        """Evaluate a response using LLM, falling back to heuristics."""
        evaluation = {
            "id": f"eval_{int(time.time() * 1000)}",
            "user_input": user_input[:200],
            "response": response[:500],
            "metrics": [],
            "overall_score": 0.0,
            "feedback": [],
            "timestamp": time.time(),
        }

        # Try LLM evaluation first
        llm_metrics = self._llm_evaluate(user_input, response)
        if llm_metrics:
            evaluation["metrics"] = llm_metrics.get("metrics", [])
            evaluation["overall_score"] = llm_metrics.get("overall_score", 0.5)
            evaluation["feedback"] = llm_metrics.get("feedback", [])
        else:
            # Fallback heuristic evaluation
            evaluation["metrics"] = self._calculate_metrics(user_input, response)
            scores = [m["score"] for m in evaluation["metrics"]]
            evaluation["overall_score"] = sum(scores) / len(scores) if scores else 0.5
            evaluation["feedback"] = self._generate_feedback(evaluation)

        self.evaluations.append(evaluation)
        if len(self.evaluations) > 500:
            self.evaluations = self.evaluations[-500:]
        _save_json(_EVALUATION_FILE, self.evaluations)
        return evaluation

    def _llm_evaluate(self, user_input: str, response: str) -> dict | None:
        """Attempt LLM-powered evaluation. Returns dict or None if unavailable."""
        try:
            from core.llm_bridge import prompt_json
            system = (
                "Eres un evaluador de calidad de respuestas. Responde SOLO con JSON:\n"
                "{\n"
                '  "metrics": [{"metric": "relevance|completeness|conciseness|tone", '
                '"score": 0.0-1.0, "description": "explicación"}],\n'
                '  "overall_score": 0.0-1.0,\n'
                '  "feedback": ["sugerencia 1", "sugerencia 2"]\n'
                "}"
            )
            return prompt_json(
                f"Usuario: {user_input[:300]}\nRespuesta: {response[:500]}\n\nEvaluá la calidad de la respuesta.",
                system=system, temperature=0.2, max_tokens=512
            )
        except Exception:
            return None

    def _calculate_metrics(self, user_input: str, response: str) -> list[dict]:
        """Calculate quality metrics."""
        metrics = []
        user_lower = user_input.lower()
        response_lower = response.lower()
        
        # 1. Relevance: Does response address the question?
        relevance_score = self._calculate_relevance(user_input, response)
        metrics.append({
            "metric": "relevance",
            "score": relevance_score,
            "description": "¿La respuesta aborda la pregunta?",
        })
        
        # 2. Completeness: Is the response complete?
        completeness_score = self._calculate_completeness(user_input, response)
        metrics.append({
            "metric": "completeness",
            "score": completeness_score,
            "description": "¿La respuesta es completa?",
        })
        
        # 3. Conciseness: Is the response appropriately concise?
        conciseness_score = self._calculate_conciseness(response)
        metrics.append({
            "metric": "conciseness",
            "score": conciseness_score,
            "description": "¿La respuesta es concisa?",
        })
        
        # 4. Tone: Is the tone appropriate?
        tone_score = self._calculate_tone(user_input, response)
        metrics.append({
            "metric": "tone",
            "score": tone_score,
            "description": "¿El tono es apropiado?",
        })
        
        return metrics

    def _calculate_relevance(self, user_input: str, response: str) -> float:
        """Calculate relevance score."""
        user_words = set(user_input.lower().split())
        response_words = set(response.lower().split())
        
        # Check for keyword overlap
        common_words = user_words & response_words
        if len(user_words) > 0:
            overlap_ratio = len(common_words) / len(user_words)
        else:
            overlap_ratio = 0.0
        
        # Check for question words in response (bad sign)
        question_words = ["qué", "cómo", "cuándo", "dónde", "por qué", "quién"]
        has_questions = any(qw in response.lower() for qw in question_words)
        
        score = min(1.0, overlap_ratio * 2)
        if has_questions:
            score *= 0.7  # Penalize if response contains questions
        
        return score

    def _calculate_completeness(self, user_input: str, response: str) -> float:
        """Calculate completeness score."""
        # Check for incomplete responses
        incomplete_markers = ["no sé", "no puedo", "no tengo", "no puedo hacer", "no puedo ayudar"]
        if any(marker in response.lower() for marker in incomplete_markers):
            return 0.3
        
        # Check response length relative to input
        input_len = len(user_input.split())
        response_len = len(response.split())
        
        if response_len < input_len * 0.5:
            return 0.4  # Too short
        if response_len > input_len * 10:
            return 0.6  # Too long
        return 0.8  # Good length

    def _calculate_conciseness(self, response: str) -> float:
        """Calculate conciseness score."""
        word_count = len(response.split())
        
        if word_count < 10:
            return 0.9  # Very concise
        if word_count < 50:
            return 0.8  # Good
        if word_count < 100:
            return 0.6  # A bit long
        return 0.4  # Too verbose

    def _calculate_tone(self, user_input: str, response: str) -> float:
        """Calculate tone appropriateness."""
        # Check for negative language
        negative_words = ["no puedo", "imposible", "error", "falló", "problema"]
        negative_count = sum(1 for w in negative_words if w in response.lower())
        
        # Check for positive language
        positive_words = ["listo", "hecho", "perfecto", "excelente", "genial"]
        positive_count = sum(1 for w in positive_words if w in response.lower())
        
        score = 0.7  # Base score
        score += positive_count * 0.1  # Bonus for positive language
        score -= negative_count * 0.15  # Penalty for negative language
        
        return max(0.0, min(1.0, score))

    def _generate_feedback(self, evaluation: dict) -> list[str]:
        """Generate improvement feedback."""
        feedback = []
        
        for metric in evaluation["metrics"]:
            if metric["score"] < 0.5:
                feedback.append(f"Mejorar {metric['metric']}: {metric['description']}")
        
        if evaluation["overall_score"] < 0.5:
            feedback.append("Respuesta de baja calidad — revisar y mejorar")
        
        return feedback

    def get_average_score(self, last_n: int = 50) -> float:
        """Get average evaluation score."""
        recent = self.evaluations[-last_n:]
        if not recent:
            return 0.0
        return sum(e["overall_score"] for e in recent) / len(recent)

    def get_trend(self) -> str:
        """Get performance trend."""
        if len(self.evaluations) < 10:
            return "Datos insuficientes"
        
        recent = self.evaluations[-10:]
        older = self.evaluations[-20:-10] if len(self.evaluations) >= 20 else self.evaluations[:-10]
        
        recent_avg = sum(e["overall_score"] for e in recent) / len(recent)
        older_avg = sum(e["overall_score"] for e in older) / len(older) if older else recent_avg
        
        if recent_avg > older_avg + 0.1:
            return "Mejorando ↑"
        elif recent_avg < older_avg - 0.1:
            return "Empeorando ↓"
        return "Estable →"

# ── Auto-Correction ───────────────────────────────────────────────────────────

class AutoCorrector:
    """Learn from mistakes and auto-correct."""

    def __init__(self):
        self.corrections = _load_json(_CORRECTION_FILE, [])

    def record_correction(self, original_response: str, corrected_response: str, reason: str):
        """Record a correction."""
        self.corrections.append({
            "id": f"corr_{int(time.time() * 1000)}",
            "original": original_response[:200],
            "corrected": corrected_response[:200],
            "reason": reason,
            "timestamp": time.time(),
        })
        if len(self.corrections) > 200:
            self.corrections = self.corrections[-200:]
        _save_json(_CORRECTION_FILE, self.corrections)

    def get_corrections(self, pattern: str = None) -> list[dict]:
        """Get recorded corrections."""
        if pattern:
            return [c for c in self.corrections if pattern.lower() in c["reason"].lower()]
        return self.corrections

    def get_correction_suggestion(self, current_response: str) -> Optional[str]:
        """Suggest correction based on past patterns."""
        # Simple pattern matching
        for correction in self.corrections[-20:]:
            if correction["original"][:50] in current_response[:100]:
                return correction["corrected"]
        return None

# ── Prompt Optimization ───────────────────────────────────────────────────────

class PromptOptimizer:
    """Optimize prompts based on what works."""

    def __init__(self):
        self.prompt_history = _load_json(_PROMPT_OPT_FILE, [])

    def record_prompt(self, prompt: str, response_quality: float, context: str = ""):
        """Record a prompt and its effectiveness."""
        self.prompt_history.append({
            "prompt": prompt[:500],
            "quality": response_quality,
            "context": context[:200],
            "timestamp": time.time(),
        })
        if len(self.prompt_history) > 100:
            self.prompt_history = self.prompt_history[-100:]
        _save_json(_PROMPT_OPT_FILE, self.prompt_history)

    def get_best_prompt(self, context: str = "") -> Optional[str]:
        """Get the best performing prompt for a context."""
        if not self.prompt_history:
            return None
        
        # Filter by context similarity
        relevant = self.prompt_history
        if context:
            context_words = set(context.lower().split())
            scored = []
            for p in self.prompt_history:
                prompt_words = set(p["context"].lower().split())
                overlap = len(context_words & prompt_words) / max(len(context_words), 1)
                scored.append((overlap, p))
            scored.sort(key=lambda x: x[0], reverse=True)
            relevant = [p for _, p in scored[:20]]
        
        # Return best quality prompt
        if relevant:
            best = max(relevant, key=lambda x: x["quality"])
            return best["prompt"]
        return None

    def get_prompt_stats(self) -> dict:
        """Get prompt optimization statistics."""
        if not self.prompt_history:
            return {"count": 0, "avg_quality": 0}
        
        qualities = [p["quality"] for p in self.prompt_history]
        return {
            "count": len(self.prompt_history),
            "avg_quality": sum(qualities) / len(qualities),
            "best_quality": max(qualities),
            "worst_quality": min(qualities),
        }

# ── Error Pattern Detection ───────────────────────────────────────────────────

class ErrorPatternDetector:
    """Identify and track recurring error patterns."""

    def __init__(self):
        self.patterns = _load_json(_ERROR_PATTERNS_FILE, [])

    def record_error(self, error_type: str, error_message: str, context: str = ""):
        """Record an error."""
        # Check if similar error exists
        for pattern in self.patterns:
            if pattern["type"] == error_type and pattern["message"][:50] == error_message[:50]:
                pattern["count"] += 1
                pattern["last_occurrence"] = time.time()
                _save_json(_ERROR_PATTERNS_FILE, self.patterns)
                return
        
        # New pattern
        self.patterns.append({
            "type": error_type,
            "message": str(error_message)[:200],
            "context": str(context)[:200],
            "count": 1,
            "first_occurrence": time.time(),
            "last_occurrence": time.time(),
        })
        _save_json(_ERROR_PATTERNS_FILE, self.patterns)

    def get_frequent_errors(self, min_count: int = 3) -> list[dict]:
        """Get frequently occurring errors."""
        return [p for p in self.patterns if p["count"] >= min_count]

    def get_error_summary(self) -> str:
        """Get error pattern summary."""
        if not self.patterns:
            return "No se detectaron patrones de error."
        
        lines = ["Patrones de error detectados:"]
        frequent = self.get_frequent_errors()
        for p in frequent:
            lines.append(f"  • {p['type']}: {p['count']} ocurrencias")
            lines.append(f"    {p['message'][:100]}")
        
        if not frequent:
            lines.append("  No hay errores frecuentes (todos < 3 ocurrencias)")
        
        return "\n".join(lines)

# ── Learned Lessons ───────────────────────────────────────────────────────────

class LessonLearner:
    """Store and retrieve learned lessons."""

    def __init__(self):
        self.lessons = _load_json(_LEARNED_LESSONS_FILE, [])

    def learn(self, lesson: str, category: str = "general", importance: float = 0.8):
        """Store a learned lesson."""
        self.lessons.append({
            "id": f"lesson_{int(time.time() * 1000)}",
            "lesson": lesson,
            "category": category,
            "importance": importance,
            "timestamp": time.time(),
            "applied_count": 0,
        })
        if len(self.lessons) > 100:
            # Keep most important lessons
            self.lessons.sort(key=lambda x: x["importance"], reverse=True)
            self.lessons = self.lessons[:100]
        _save_json(_LEARNED_LESSONS_FILE, self.lessons)

    def get_lessons(self, category: str = None) -> list[dict]:
        """Get learned lessons."""
        if category:
            return [l for l in self.lessons if l["category"] == category]
        return self.lessons

    def apply_lesson(self, lesson_id: str):
        """Mark a lesson as applied."""
        for lesson in self.lessons:
            if lesson["id"] == lesson_id:
                lesson["applied_count"] += 1
                lesson["last_applied"] = time.time()
        _save_json(_LEARNED_LESSONS_FILE, self.lessons)

    def get_lessons_summary(self) -> str:
        """Get lessons summary."""
        if not self.lessons:
            return "No hay lecciones aprendidas."
        
        lines = [f"Lecciones aprendidas ({len(self.lessons)}):"]
        for lesson in self.lessons[-10:]:
            lines.append(f"  • [{lesson['category']}] {lesson['lesson'][:100]}")
        return "\n".join(lines)

# ── Unified Interface ─────────────────────────────────────────────────────────

class SelfImprovementSystem:
    """Unified interface for all self-improvement components."""

    def __init__(self):
        self.evaluator = SelfEvaluator()
        self.corrector = AutoCorrector()
        self.optimizer = PromptOptimizer()
        self.error_detector = ErrorPatternDetector()
        self.learner = LessonLearner()

    def post_response_eval(self, user_input: str, response: str, context: dict = None):
        """Evaluate response after generation."""
        evaluation = self.evaluator.evaluate(user_input, response, context)
        
        # If low quality, record for correction
        if evaluation["overall_score"] < 0.5:
            self.corrector.record_correction(
                response,
                "[Respuesta mejorada pendiente]",
                f"Baja calidad: {evaluation['overall_score']:.0%}",
            )
        
        # Record prompt effectiveness
        self.optimizer.record_prompt(user_input, evaluation["overall_score"])
        
        return evaluation

    def record_error(self, error_type: str, error_message: str, context: str = ""):
        """Record an error for pattern detection."""
        self.error_detector.record_error(error_type, error_message, context)

    def learn(self, lesson: str, category: str = "general", importance: float = 0.8):
        """Store a learned lesson."""
        self.learner.learn(lesson, category, importance)

    def get_status(self) -> dict:
        """Get self-improvement system status."""
        return {
            "avg_score": self.evaluator.get_average_score(),
            "trend": self.evaluator.get_trend(),
            "corrections": len(self.corrector.corrections),
            "prompt_stats": self.optimizer.get_prompt_stats(),
            "error_patterns": len(self.error_detector.patterns),
            "lessons_learned": len(self.learner.lessons),
        }

    def get_improvement_report(self) -> str:
        """Get comprehensive improvement report."""
        lines = ["═══════════════════════════════════════"]
        lines.append("  REPORTE DE AUTO-MEJORA DE ERIS")
        lines.append("═══════════════════════════════════════")
        lines.append("")
        lines.append(f" Calidad promedio: {self.evaluator.get_average_score():.0%}")
        lines.append(f"📈 Tendencia: {self.evaluator.get_trend()}")
        lines.append(f" Correcciones: {len(self.corrector.corrections)}")
        lines.append(f"📝 Lecciones aprendidas: {len(self.learner.lessons)}")
        lines.append("")
        
        # Error patterns
        error_summary = self.error_detector.get_error_summary()
        if error_summary:
            lines.append("🐛 Patrones de error:")
            lines.append(error_summary)
            lines.append("")
        
        # Lessons
        lessons_summary = self.learner.get_lessons_summary()
        if lessons_summary:
            lines.append("📚 Lecciones:")
            lines.append(lessons_summary)
        
        return "\n".join(lines)

# ── Feedback Loop (Ciclo Agéntico Real) ──────────────────────────────────────

class FeedbackLoop:
    """
    Conecta self_improvement + reasoning_engine en un ciclo real:

    Percepción → Razonamiento → Acción → Feedback → Memoria → Mejora

    Cada interacción:
      1. Evalúa calidad de la respuesta
      2. Si es baja, intenta corregirla vía auto razonamiento
      3. Detecta patrones de error recurrentes
      4. Registra lecciones aprendidas
      5. Opcionalmente optimiza prompts vía DSPy
    """

    def __init__(self):
        self.system = get_self_improvement()
        self._reasoning = None
        self._reasoning_available = False

    def _get_reasoning(self):
        if self._reasoning is None:
            try:
                from core.reasoning_engine import get_reasoning_engine
                self._reasoning = get_reasoning_engine()
                self._reasoning_available = True
            except Exception:
                self._reasoning_available = False
        return self._reasoning

    def run_cycle(
        self,
        user_input: str,
        response: str,
        context: dict = None,
    ) -> dict:
        """
        Ejecuta el ciclo completo de feedback:
        Evaluación → Corrección → Patrones → Lecciones → Mejora
        """
        cycle_result = {
            "evaluation": None,
            "correction": None,
            "error_patterns": None,
            "lessons": None,
            "optimization": None,
        }

        # 1. Evaluación
        evaluation = self.system.post_response_eval(user_input, response, context)
        cycle_result["evaluation"] = evaluation

        # 2. Corrección (si calidad baja)
        if evaluation["overall_score"] < 0.5 and self._get_reasoning():
            try:
                reasoning = self._get_reasoning()
                verify = reasoning.verify_claim(response)
                if verify.get("confidence", 1.0) < 0.5:
                    correction_reason = f"Verificación falló: {verify.get('summary', 'baja confianza')}"
                    self.system.corrector.record_correction(
                        response,
                        "[Requiere revisión: respuesta no verificada]",
                        correction_reason,
                    )
                    cycle_result["correction"] = correction_reason

                    # Aprender lección
                    self.system.learner.learn(
                        f"Respuestas con baja verificación requieren corrección: "
                        f"{verify.get('issues', 'desconocido')}",
                        category="verification",
                    )
            except Exception:
                pass

        # 3. Detectar patrones de error recurrentes
        frequent = self.system.error_detector.get_frequent_errors(min_count=3)
        if len(frequent) >= 3:
            lessons = []
            for pattern in frequent:
                lesson = (
                    f"Error recurrente '{pattern['type']}' "
                    f"({pattern['count']} veces): {pattern['message'][:100]}"
                )
                self.system.learner.learn(lesson, category="error_pattern")
                lessons.append(lesson)
            cycle_result["error_patterns"] = lessons

        # 4. Registrar lección general si la calidad mejoró o empeoró
        trend = self.system.evaluator.get_trend()
        if "Empeorando" in trend:
            self.system.learner.learn(
                "Tendencia de calidad empeorando — revisar estrategia de respuesta",
                category="trend",
                importance=0.9,
            )
            cycle_result["lessons"] = "Calidad en declive — registrado como lección crítica"
        elif "Mejorando" in trend and len(self.system.evaluator.evaluations) >= 5:
            self.system.learner.learn(
                "Tendencia de calidad mejorando — mantener estrategia actual",
                category="trend",
                importance=0.7,
            )
            cycle_result["lessons"] = "Calidad mejorando — registrado como refuerzo positivo"

        # 5. Sugerir optimización si hay muchas correcciones
        if len(self.system.corrector.corrections) >= 10 and evaluation["overall_score"] < 0.6:
            cycle_result["optimization"] = (
                "Se detectaron múltiples correcciones. "
                "Considerar optimizar el prompt del sistema."
            )

        return cycle_result

    def get_cycle_report(self) -> str:
        """Reporte completo del ciclo agéntico."""
        lines = [
            "═══════════════════════════════════════",
            "  CICLO AGÉNTICO REAL — REPORTE",
            "═══════════════════════════════════════",
            "",
            f"   Calidad promedio: {self.system.evaluator.get_average_score():.0%}",
            f"   Tendencia: {self.system.evaluator.get_trend()}",
            f"   Correcciones: {len(self.system.corrector.corrections)}",
            f"   Lecciones: {len(self.system.learner.lessons)}",
            f"   Patrones de error: {len(self.system.error_detector.patterns)}",
            "",
            "Percepción → Razonamiento → Acción → Feedback → Memoria → Mejora",
            "",
        ]

        error_pat = self.system.error_detector.get_error_summary()
        if error_pat and "No se detectaron" not in error_pat:
            lines.append("Patrones de error:")
            lines.append(error_pat)
            lines.append("")

        lessons = self.system.learner.get_lessons_summary()
        if lessons and "No hay" not in lessons:
            lines.append("Lecciones:")
            lines.append(lessons)

        return "\n".join(lines)


# ── Singleton ────────────────────────────────────────────────────────────────

_self_improvement: Optional[SelfImprovementSystem] = None

def get_self_improvement() -> SelfImprovementSystem:
    global _self_improvement
    if _self_improvement is None:
        _self_improvement = SelfImprovementSystem()
    return _self_improvement
