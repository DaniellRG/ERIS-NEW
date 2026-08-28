"""
cost_tracker.py — Rastreador de costos y tokens para ERIS.

Cuenta tokens por request, calcula costo por proveedor, y mantiene
métricas acumuladas para presupuesto y optimización.

Costos por 1M tokens (actualizados 2024-2025):
  - OpenRouter: varía por modelo, promedio $0.50-3.00
  - Gemini Flash: $0.075 input, $0.30 output
  - Gemini Pro: $1.25 input, $5.00 output
  - Ollama: $0 (local)
  - Groq: $0.05-0.27 (varía)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_METRICS_DIR = _BASE / "data" / "cost_metrics"
_DAILY_FILE = _METRICS_DIR / "daily.json"
_SESSION_FILE = _METRICS_DIR / "session.json"

# Costos por 1M tokens (USD) — {provider: {model: {input, output}}}
COST_TABLE = {
    "openrouter": {
        "_default": {"input": 1.0, "output": 3.0},
        "meta-llama/llama-3.3-70b-instruct": {"input": 0.10, "output": 0.10},
        "openai/gpt-4o": {"input": 2.50, "output": 10.0},
        "anthropic/claude-sonnet-4": {"input": 3.0, "output": 15.0},
        "google/gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    },
    "gemini": {
        "gemini-flash-latest": {"input": 0.075, "output": 0.30},
        "gemini-pro-latest": {"input": 1.25, "output": 5.0},
    },
    "ollama": {
        "_default": {"input": 0, "output": 0},
    },
    "groq": {
        "_default": {"input": 0.05, "output": 0.27},
    },
}

# Estimación: 1 token ≈ 4 caracteres
CHARS_PER_TOKEN = 4


class CostTracker:
    """Rastrea costos de LLM por sesión y acumulado."""

    def __init__(self):
        self.session_stats = defaultdict(lambda: {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0})
        self.daily_stats = self._load_daily()

    def _load_daily(self) -> dict:
        try:
            if _DAILY_FILE.exists():
                return json.loads(_DAILY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_daily(self):
        try:
            _METRICS_DIR.mkdir(parents=True, exist_ok=True)
            _DAILY_FILE.write_text(
                json.dumps(self.daily_stats, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _today(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def estimate_tokens(self, text: str) -> int:
        """Estima tokens desde texto."""
        return max(1, len(str(text)) // CHARS_PER_TOKEN)

    def calculate_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calcula costo en USD."""
        provider_costs = COST_TABLE.get(provider, COST_TABLE.get("openrouter", {}))
        model_costs = provider_costs.get(model, provider_costs.get("_default", {"input": 1.0, "output": 3.0}))

        input_cost = (input_tokens / 1_000_000) * model_costs["input"]
        output_cost = (output_tokens / 1_000_000) * model_costs["output"]
        return round(input_cost + output_cost, 8)

    def record_request(
        self,
        provider: str,
        model: str,
        input_text: str = "",
        output_text: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        tool_name: str = "",
        elapsed: float = 0,
    ) -> dict:
        """Registra un request y su costo.

        Returns:
            dict con: input_tokens, output_tokens, cost, cumulative_session
        """
        if not input_tokens and input_text:
            input_tokens = self.estimate_tokens(input_text)
        if not output_tokens and output_text:
            output_tokens = self.estimate_tokens(output_text)

        cost = self.calculate_cost(provider, model, input_tokens, output_tokens)

        # Session stats
        key = f"{provider}/{model}"
        self.session_stats[key]["requests"] += 1
        self.session_stats[key]["input_tokens"] += input_tokens
        self.session_stats[key]["output_tokens"] += output_tokens
        self.session_stats[key]["cost"] += cost

        # Daily stats
        today = self._today()
        if today not in self.daily_stats:
            self.daily_stats[today] = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        self.daily_stats[today]["requests"] += 1
        self.daily_stats[today]["input_tokens"] += input_tokens
        self.daily_stats[today]["output_tokens"] += output_tokens
        self.daily_stats[today]["cost"] += cost
        self._save_daily()

        cumulative = sum(s["cost"] for s in self.session_stats.values())

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "cumulative_session": round(cumulative, 6),
        }

    def get_session_summary(self) -> dict:
        """Resumen de la sesión actual."""
        total_requests = sum(s["requests"] for s in self.session_stats.values())
        total_input = sum(s["input_tokens"] for s in self.session_stats.values())
        total_output = sum(s["output_tokens"] for s in self.session_stats.values())
        total_cost = sum(s["cost"] for s in self.session_stats.values())

        return {
            "total_requests": total_requests,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": round(total_cost, 6),
            "by_provider": dict(self.session_stats),
        }

    def get_daily_summary(self, date: str = None) -> dict:
        """Resumen de un día específico."""
        if date is None:
            date = self._today()
        return self.daily_stats.get(date, {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0})

    def format_status(self) -> str:
        """Formato legible del estado."""
        s = self.get_session_summary()
        lines = [
            f"Sesión: {s['total_requests']} requests, {s['total_input_tokens']:,} in / {s['total_output_tokens']:,} out tokens",
            f"Costo sesión: ${s['total_cost_usd']:.6f}",
        ]
        for provider, stats in s["by_provider"].items():
            lines.append(f"  {provider}: {stats['requests']} req, ${stats['cost']:.6f}")
        daily = self.get_daily_summary()
        lines.append(f"Hoy: {daily['requests']} requests, ${daily['cost']:.6f}")
        return "\n".join(lines)


# Singleton
_cost_tracker: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
