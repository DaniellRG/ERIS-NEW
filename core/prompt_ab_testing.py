"""
prompt_ab_testing.py — A/B testing de prompts para ERIS.

Prueba variantes de system prompts y mide cuál funciona mejor.
Guarda métricas (tokens usados, calidad percibida, completitud) y
selecciona automáticamente la variante ganadora.

Flujo:
  1. Definir variantes de prompt
  2. Ejecutar ambas con la misma pregunta
  3. Evaluar resultados
  4. Actualizar estadísticas
  5. Seleccionar la mejor variante
"""
from __future__ import annotations

import json
import time
import random
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_METRICS_FILE = _BASE / "data" / "prompt_ab_metrics.json"


class PromptABTest:
    """Gestiona tests A/B de prompts."""

    def __init__(self, experiment_name: str, variants: list[dict]):
        """
        Args:
            experiment_name: Nombre del experimento.
            variants: Lista de [{name, prompt, weight}] donde weight es probabilidad de selección.
        """
        self.experiment = experiment_name
        self.variants = variants
        self.metrics = self._load_metrics()

    def _load_metrics(self) -> dict:
        try:
            if _METRICS_FILE.exists():
                data = json.loads(_METRICS_FILE.read_text(encoding="utf-8"))
                return data.get(self.experiment, {"variants": {}, "total_tests": 0})
        except Exception:
            pass
        return {"variants": {}, "total_tests": 0}

    def _save_metrics(self):
        try:
            all_data = {}
            if _METRICS_FILE.exists():
                all_data = json.loads(_METRICS_FILE.read_text(encoding="utf-8"))
            all_data[self.experiment] = self.metrics
            _METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
            _METRICS_FILE.write_text(
                json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def select_variant(self) -> dict:
        """Selecciona una variante basada en pesos y rendimiento histórico."""
        weights = []
        for v in self.variants:
            name = v["name"]
            base_weight = v.get("weight", 1.0)
            # Ajustar peso por rendimiento histórico
            stats = self.metrics.get("variants", {}).get(name, {})
            win_rate = stats.get("win_rate", 0.5)
            adjusted_weight = base_weight * (0.5 + win_rate)
            weights.append(adjusted_weight)

        # Selección ponderada
        total = sum(weights)
        r = random.random() * total
        cumulative = 0
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                return self.variants[i]
        return self.variants[-1]

    def record_result(self, variant_name: str, score: float, tokens_used: int = 0):
        """Registra el resultado de un test."""
        if variant_name not in self.metrics["variants"]:
            self.metrics["variants"][variant_name] = {
                "tests": 0, "total_score": 0, "wins": 0,
                "total_tokens": 0, "win_rate": 0.5,
            }
        v = self.metrics["variants"][variant_name]
        v["tests"] += 1
        v["total_score"] += score
        v["total_tokens"] += tokens_used

        # Determinar si fue "ganador" (score > threshold)
        if score >= 7:
            v["wins"] += 1

        # Recalcular win rate
        if v["tests"] > 0:
            v["win_rate"] = v["wins"] / v["tests"]

        self.metrics["total_tests"] += 1
        self._save_metrics()

    def get_winner(self) -> dict | None:
        """Devuelve la variante con mejor rendimiento."""
        best = None
        best_rate = 0
        for v in self.variants:
            stats = self.metrics.get("variants", {}).get(v["name"], {})
            rate = stats.get("win_rate", 0.5)
            tests = stats.get("tests", 0)
            # Necesitamos al menos 3 tests para confiar
            if tests >= 3 and rate > best_rate:
                best_rate = rate
                best = v
        return best

    def get_report(self) -> str:
        """Genera un reporte del estado del test A/B."""
        lines = [f"Experimento: {self.experiment}", f"Tests totales: {self.metrics['total_tests']}"]
        for v in self.variants:
            name = v["name"]
            stats = self.metrics.get("variants", {}).get(name, {})
            tests = stats.get("tests", 0)
            rate = stats.get("win_rate", 0)
            avg_score = stats.get("total_score", 0) / tests if tests > 0 else 0
            lines.append(f"  {name}: {tests} tests, win_rate={rate:.1%}, avg_score={avg_score:.1f}")
        winner = self.get_winner()
        if winner:
            lines.append(f"Ganadora: {winner['name']}")
        return "\n".join(lines)
