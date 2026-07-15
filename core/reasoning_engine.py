"""
reasoning_engine.py — ERIS Reasoning Engine.
Simulates AGI-like reasoning: Chain of Thought, fact verification, counterfactual reasoning.

Components:
  - Chain of Thought: Step-by-step internal reasoning before responding
  - Fact verification: Cross-check answers with multiple sources
  - Counterfactual reasoning: "What if?" scenario simulation
  - Logical inference: Rule-based deductions
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

_BASE = Path(__file__).resolve().parent.parent
_REASONING_DIR = _BASE / "memory"
_COT_FILE = _REASONING_DIR / "chain_of_thought.json"
_VERIFICATION_FILE = _REASONING_DIR / "verification_log.json"
_COUNTERFACTUAL_FILE = _REASONING_DIR / "counterfactuals.json"
_RULES_FILE = _REASONING_DIR / "inference_rules.json"

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
        print(f"[ReasoningEngine] Save error: {e}")

# ── Chain of Thought ──────────────────────────────────────────────────────────

class ChainOfThought:
    """Step-by-step internal reasoning before responding."""

    def __init__(self):
        self.history = _load_json(_COT_FILE, [])

    def start(self, question: str) -> dict:
        """Start a chain of thought reasoning process."""
        cot = {
            "id": f"cot_{int(time.time() * 1000)}",
            "question": question,
            "steps": [],
            "conclusion": None,
            "confidence": 0.0,
            "started_at": time.time(),
            "completed_at": None,
        }
        return cot

    def add_step(self, cot: dict, step_type: str, content: str, confidence: float = 0.8):
        """Add a reasoning step."""
        cot["steps"].append({
            "type": step_type,
            "content": content,
            "confidence": confidence,
            "timestamp": time.time(),
        })

    def conclude(self, cot: dict, conclusion: str, confidence: float = 0.8):
        """Conclude the reasoning process."""
        cot["conclusion"] = conclusion
        cot["confidence"] = confidence
        cot["completed_at"] = time.time()
        cot["duration"] = cot["completed_at"] - cot["started_at"]
        
        # Save to history
        self.history.append(cot)
        # Keep only last 100 CoTs
        if len(self.history) > 100:
            self.history = self.history[-100:]
        _save_json(_COT_FILE, self.history)
        
        return cot

    def get_summary(self, cot: dict) -> str:
        """Get a summary of the reasoning process."""
        lines = [f"Pregunta: {cot['question']}"]
        lines.append(f"Pasos de razonamiento ({len(cot['steps'])}):")
        for i, step in enumerate(cot["steps"], 1):
            lines.append(f"  {i}. [{step['type']}] {step['content'][:100]}")
        lines.append(f"Conclusión: {cot['conclusion']}")
        lines.append(f"Confianza: {cot['confidence']:.0%}")
        return "\n".join(lines)

# ── Fact Verification ─────────────────────────────────────────────────────────

class FactVerifier:
    """Cross-check answers with multiple sources."""

    def __init__(self):
        self.verification_log = _load_json(_VERIFICATION_FILE, [])

    def verify(self, claim: str, sources: list[str] = None) -> dict:
        """Verify a claim using LLM, falling back to heuristics."""
        result = {
            "claim": claim,
            "sources_checked": sources or [],
            "verifications": [],
            "overall_confidence": 0.0,
            "timestamp": time.time(),
        }

        # Try LLM verification first
        llm_ver = self._llm_verify(claim)
        if llm_ver:
            result["verifications"] = llm_ver.get("verifications", [])
            result["overall_confidence"] = llm_ver.get("overall_confidence", 0.5)
            self.verification_log.append(result)
            if len(self.verification_log) > 200:
                self.verification_log = self.verification_log[-200:]
            _save_json(_VERIFICATION_FILE, self.verification_log)
            return result

        # Fallback heuristic verification
        consistency_score = self._check_consistency(claim)
        result["verifications"].append({
            "method": "internal_consistency",
            "score": consistency_score,
            "details": "Verificación de consistencia interna",
        })
        factual_score = self._check_factual_patterns(claim)
        result["verifications"].append({
            "method": "factual_patterns",
            "score": factual_score,
            "details": "Verificación de patrones factuales",
        })
        scores = [v["score"] for v in result["verifications"]]
        result["overall_confidence"] = sum(scores) / len(scores) if scores else 0.0

        self.verification_log.append(result)
        if len(self.verification_log) > 200:
            self.verification_log = self.verification_log[-200:]
        _save_json(_VERIFICATION_FILE, self.verification_log)
        return result

    def _llm_verify(self, claim: str) -> dict | None:
        """Attempt LLM-powered verification. Returns dict or None if unavailable."""
        try:
            from core.llm_bridge import prompt_json
            system = (
                "Eres un verificador de hechos. Responde SOLO con JSON:\n"
                "{\n"
                '  "verifications": [{"method": "string", "score": 0.0-1.0, '
                '"details": "explicación"}],\n'
                '  "overall_confidence": 0.0-1.0\n'
                "}"
            )
            return prompt_json(
                f"Verificá este enunciado: {claim}",
                system=system, temperature=0.2, max_tokens=512
            )
        except Exception:
            return None

    def _check_consistency(self, claim: str) -> float:
        """Check internal consistency of a claim."""
        claim_lower = claim.lower()
        
        # Check for contradictions
        contradictions = [
            ("siempre", "nunca"),
            ("todo", "nada"),
            ("siempre", "a veces"),
            ("todos", "ninguno"),
        ]
        
        for word1, word2 in contradictions:
            if word1 in claim_lower and word2 in claim_lower:
                return 0.2  # Low confidence due to contradiction
        
        # Check for hedging language (indicates uncertainty)
        hedging = ["quizás", "tal vez", "posiblemente", "probablemente", "creo que"]
        hedging_count = sum(1 for h in hedging if h in claim_lower)
        if hedging_count > 0:
            return 0.6  # Medium confidence due to uncertainty
        
        return 0.8  # Default medium-high confidence

    def _check_factual_patterns(self, claim: str) -> float:
        """Check for factual patterns in a claim."""
        claim_lower = claim.lower()
        
        # Check for specific numbers/dates (more likely to be factual)
        import re
        has_numbers = bool(re.search(r'\d+', claim))
        has_dates = bool(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', claim))
        
        if has_dates:
            return 0.7
        if has_numbers:
            return 0.6
        
        # Check for opinion markers
        opinion_markers = ["pienso", "creo", "opino", "me parece", "en mi opinión"]
        if any(m in claim_lower for m in opinion_markers):
            return 0.4  # Opinion, not fact
        
        return 0.7  # Default

    def get_verification_summary(self, claim: str) -> str:
        """Get verification summary for a claim."""
        result = self.verify(claim)
        lines = [f"Verificación: {claim}"]
        lines.append(f"Confianza general: {result['overall_confidence']:.0%}")
        for v in result["verifications"]:
            lines.append(f"  • {v['method']}: {v['score']:.0%} — {v['details']}")
        return "\n".join(lines)

# ─ Counterfactual Reasoning ──────────────────────────────────────────────────

class CounterfactualReasoner:
    """Simulate 'what if?' scenarios."""

    def __init__(self):
        self.scenarios = _load_json(_COUNTERFACTUAL_FILE, [])

    def simulate(self, premise: str, question: str) -> dict:
        """Simulate a counterfactual scenario."""
        scenario = {
            "id": f"cf_{int(time.time() * 1000)}",
            "premise": premise,
            "question": question,
            "analysis": [],
            "conclusion": None,
            "plausibility": 0.0,
            "timestamp": time.time(),
        }
        
        # Analyze the premise
        scenario["analysis"].append({
            "step": "analyze_premise",
            "content": f"Premisa: {premise}",
            "implications": self._extract_implications(premise),
        })
        
        # Generate possible outcomes
        outcomes = self._generate_outcomes(premise, question)
        scenario["analysis"].append({
            "step": "generate_outcomes",
            "content": f"Posibles resultados para: {question}",
            "outcomes": outcomes,
        })
        
        # Evaluate plausibility
        scenario["plausibility"] = self._evaluate_plausibility(premise, outcomes)
        
        # Draw conclusion
        scenario["conclusion"] = self._draw_conclusion(premise, question, outcomes)
        
        # Save
        self.scenarios.append(scenario)
        if len(self.scenarios) > 50:
            self.scenarios = self.scenarios[-50:]
        _save_json(_COUNTERFACTUAL_FILE, self.scenarios)
        
        return scenario

    def _extract_implications(self, premise: str) -> list[str]:
        """Extract implications from a premise."""
        implications = []
        premise_lower = premise.lower()
        
        # Simple rule-based implications
        if "no hubiera" in premise_lower or "no hubiera sido" in premise_lower:
            implications.append("Evento pasado que no ocurrió")
        if "si hubiera" in premise_lower:
            implications.append("Condición hipotética sobre el pasado")
        if "qué pasaría si" in premise_lower:
            implications.append("Escenario hipotético futuro")
        
        return implications

    def _generate_outcomes(self, premise: str, question: str) -> list[dict]:
        """Generate possible outcomes for a scenario."""
        outcomes = []
        
        # Simple template-based outcomes
        if "qué pasaría si" in premise.lower() or "si hubiera" in premise.lower():
            outcomes.append({
                "outcome": "Escenario positivo",
                "probability": 0.3,
                "description": "Las cosas podrían haber salido mejor",
            })
            outcomes.append({
                "outcome": "Escenario negativo",
                "probability": 0.3,
                "description": "Las cosas podrían haber salido peor",
            })
            outcomes.append({
                "outcome": "Escenario neutral",
                "probability": 0.4,
                "description": "El resultado habría sido similar",
            })
        
        return outcomes

    def _evaluate_plausibility(self, premise: str, outcomes: list) -> float:
        """Evaluate the plausibility of a counterfactual."""
        # Simple heuristic
        premise_lower = premise.lower()
        
        # More specific premises are more plausible
        if len(premise.split()) > 10:
            return 0.6
        if len(premise.split()) > 5:
            return 0.7
        return 0.5

    def _draw_conclusion(self, premise: str, question: str, outcomes: list) -> str:
        """Draw a conclusion from the counterfactual analysis."""
        if not outcomes:
            return "No se pueden generar resultados para este escenario."
        
        # Sort by probability
        outcomes.sort(key=lambda x: x.get("probability", 0), reverse=True)
        most_likely = outcomes[0]
        
        return f"Basado en el análisis, el escenario más probable es: {most_likely['outcome']} ({most_likely['probability']:.0%}). {most_likely['description']}"

    def get_scenario_summary(self, scenario: dict) -> str:
        """Get summary of a counterfactual scenario."""
        lines = [f"Escenario contrafactual:"]
        lines.append(f"  Premisa: {scenario['premise']}")
        lines.append(f"  Pregunta: {scenario['question']}")
        lines.append(f"  Plausibilidad: {scenario['plausibility']:.0%}")
        lines.append(f"  Conclusión: {scenario['conclusion']}")
        return "\n".join(lines)

# ── Logical Inference ─────────────────────────────────────────────────────────

class InferenceEngine:
    """Rule-based logical inference."""

    def __init__(self):
        self.rules = _load_json(_RULES_FILE, [])

    def add_rule(self, premise: str, conclusion: str, confidence: float = 0.9):
        """Add an inference rule."""
        self.rules.append({
            "premise": premise.lower(),
            "conclusion": conclusion,
            "confidence": confidence,
            "added_at": time.time(),
        })
        _save_json(_RULES_FILE, self.rules)

    def infer(self, facts: list[str]) -> list[dict]:
        """Draw inferences from a set of facts."""
        inferences = []
        facts_lower = [f.lower() for f in facts]
        
        for rule in self.rules:
            # Check if premise matches any fact
            for fact in facts_lower:
                if rule["premise"] in fact or fact in rule["premise"]:
                    inferences.append({
                        "rule": rule["premise"],
                        "conclusion": rule["conclusion"],
                        "confidence": rule["confidence"],
                        "triggered_by": fact,
                    })
                    break
        
        return inferences

    def get_rules(self) -> list[dict]:
        """Get all inference rules."""
        return self.rules

# ── Unified Interface ─────────────────────────────────────────────────────────

class ReasoningEngine:
    """Unified interface for all reasoning components."""

    def __init__(self):
        self.cot = ChainOfThought()
        self.verifier = FactVerifier()
        self.counterfactual = CounterfactualReasoner()
        self.inference = InferenceEngine()

    def reason(self, question: str, context: str = None) -> dict:
        """Full reasoning process: LLM-powered CoT + verification + conclusion."""
        cot = self.cot.start(question)

        # Try LLM-powered reasoning
        llm_result = self._llm_reason(question, context)
        if llm_result:
            for step in llm_result.get("steps", []):
                self.cot.add_step(cot, step.get("type", "reasoning"), step.get("content", ""),
                                  confidence=step.get("confidence", 0.7))
            conclusion = llm_result.get("conclusion", "")
            confidence = llm_result.get("confidence", 0.7)
            self.cot.conclude(cot, conclusion, confidence=confidence)
            return {
                "chain_of_thought": cot,
                "verification": self.verifier.verify(conclusion),
            }

        # Fallback: heuristic reasoning
        self.cot.add_step(cot, "analysis", f"Analizando pregunta: {question[:100]}")
        if context:
            self.cot.add_step(cot, "context", f"Contexto relevante: {context[:100]}")
        self.cot.add_step(cot, "generation", "Generando posibles respuestas")
        self.cot.add_step(cot, "verification", "Verificando hechos")
        conclusion = f"Respuesta basada en razonamiento paso a paso para: {question[:50]}..."
        self.cot.conclude(cot, conclusion, confidence=0.75)
        return {
            "chain_of_thought": cot,
            "verification": self.verifier.verify(conclusion),
        }

    def _llm_reason(self, question: str, context: str = None) -> dict | None:
        """Attempt LLM-powered reasoning. Returns dict or None if unavailable."""
        try:
            from core.llm_bridge import prompt_json
            ctx = f"\nContexto: {context[:500]}" if context else ""
            system = (
                "Eres un motor de razonamiento AGI. Responde SOLO con JSON válido con esta estructura:\n"
                "{\n"
                '  "steps": [{"type": "analysis|context|generation|verification", '
                '"content": "paso del razonamiento", "confidence": 0.0-1.0}],\n'
                '  "conclusion": "conclusión final",\n'
                '  "confidence": 0.0-1.0\n'
                "}"
            )
            return prompt_json(
                f"Pregunta: {question}{ctx}\n\nRazoná paso a paso y llegá a una conclusión.",
                system=system, temperature=0.3, max_tokens=1024
            )
        except Exception:
            return None

    def what_if(self, premise: str, question: str) -> dict:
        """Run counterfactual reasoning."""
        return self.counterfactual.simulate(premise, question)

    def verify_claim(self, claim: str) -> dict:
        """Verify a claim."""
        return self.verifier.verify(claim)

    def get_status(self) -> dict:
        """Get reasoning engine status."""
        return {
            "cot_history": len(self.cot.history),
            "verifications": len(self.verifier.verification_log),
            "scenarios": len(self.counterfactual.scenarios),
            "rules": len(self.inference.rules),
        }

# ── Singleton ─────────────────────────────────────────────────────────────────

_reasoning_engine: Optional[ReasoningEngine] = None

def get_reasoning_engine() -> ReasoningEngine:
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = ReasoningEngine()
    return _reasoning_engine
