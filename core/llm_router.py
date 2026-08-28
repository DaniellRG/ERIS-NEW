"""
ERIS Local LLM Router — Routing inteligente entre Gemini, Ollama, OpenRouter.
Selecciona el mejor modelo según: costo, latencia, calidad, disponibilidad.
"""
import json
import time
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "llm_router"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_STATS_FILE = _DATA_DIR / "routing_stats.json"

# Model tiers: quality (1-10), cost_per_1k_tokens, avg_latency_ms, requires_internet
MODEL_REGISTRY = {
    "gemini-live": {"quality": 9, "cost": 0.0, "latency": 800, "internet": True, "provider": "gemini", "capabilities": ["voice", "tools", "multimodal"]},
    "gemini-flash": {"quality": 8, "cost": 0.000075, "latency": 400, "internet": True, "provider": "gemini", "capabilities": ["tools", "multimodal"]},
    "gemini-pro": {"quality": 9, "cost": 0.0005, "latency": 600, "internet": True, "provider": "gemini", "capabilities": ["tools", "multimodal"]},
    "ollama-mistral": {"quality": 6, "cost": 0.0, "latency": 1200, "internet": False, "provider": "ollama", "capabilities": ["tools"]},
    "ollama-llama3": {"quality": 6, "cost": 0.0, "latency": 1000, "internet": False, "provider": "ollama", "capabilities": ["tools"]},
    "ollama-gemma2": {"quality": 7, "cost": 0.0, "latency": 900, "internet": False, "provider": "ollama", "capabilities": ["tools"]},
    "openrouter-claude": {"quality": 10, "cost": 0.003, "latency": 700, "internet": True, "provider": "openrouter", "capabilities": ["tools", "multimodal"]},
    "openrouter-gpt4": {"quality": 9, "cost": 0.01, "latency": 600, "internet": True, "provider": "openrouter", "capabilities": ["tools", "multimodal"]},
}


def _load_stats() -> dict:
    if _STATS_FILE.exists():
        with open(_STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"calls": {}, "errors": {}}


def _save_stats(stats: dict):
    with open(_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def record_call(model: str, latency_ms: float, tokens_used: int = 0, success: bool = True):
    stats = _load_stats()
    if model not in stats["calls"]:
        stats["calls"][model] = {"total": 0, "success": 0, "total_latency": 0, "total_tokens": 0}
    stats["calls"][model]["total"] += 1
    if success:
        stats["calls"][model]["success"] += 1
    stats["calls"][model]["total_latency"] += latency_ms
    stats["calls"][model]["total_tokens"] += tokens_used
    if not success:
        stats["errors"][model] = stats["errors"].get(model, 0) + 1
    _save_stats(stats)


def select_model(requirements: dict = None) -> dict:
    """
    Select the best model based on requirements.
    requirements: {quality_min, max_cost_per_1k, max_latency_ms, needs_internet, needs_tools, needs_voice}
    """
    req = requirements or {}
    quality_min = req.get("quality_min", 5)
    max_cost = req.get("max_cost_per_1k", 0.05)
    max_latency = req.get("max_latency_ms", 3000)
    needs_internet = req.get("needs_internet", None)
    needs_tools = req.get("needs_tools", True)
    needs_voice = req.get("needs_voice", False)

    candidates = []
    for name, info in MODEL_REGISTRY.items():
        if info["quality"] < quality_min:
            continue
        if info["cost"] > max_cost:
            continue
        if info["latency"] > max_latency:
            continue
        if needs_internet is not None and info["internet"] != needs_internet:
            continue
        if needs_tools and "tools" not in info["capabilities"]:
            continue
        if needs_voice and "voice" not in info["capabilities"]:
            continue
        # Score: quality / (cost * 1000 + 1) * (1 / (latency/1000 + 1))
        score = info["quality"] / (info["cost"] * 1000 + 1) * (1 / (info["latency"] / 1000 + 1))
        candidates.append((name, score, info))

    candidates.sort(key=lambda x: x[1], reverse=True)
    if not candidates:
        return {"selected": None, "reason": "No model matches requirements."}

    best = candidates[0]
    return {
        "selected": best[0],
        "score": round(best[1], 4),
        "quality": best[2]["quality"],
        "cost_per_1k": best[2]["cost"],
        "latency_ms": best[2]["latency"],
        "provider": best[2]["provider"],
        "alternatives": [{"name": c[0], "score": round(c[1], 4)} for c in candidates[1:4]],
    }


def get_model_stats(model: str = None) -> dict:
    stats = _load_stats()
    if model:
        return stats["calls"].get(model, {})
    return stats["calls"]


def llm_router_tool(parameters: dict = None, player=None) -> str:
    """Tool entry point."""
    params = parameters or {}
    action = params.get("action", "select").lower()

    if action == "select":
        req = {
            "quality_min": int(params.get("quality_min", 5)),
            "max_cost_per_1k": float(params.get("max_cost", 0.05)),
            "max_latency_ms": int(params.get("max_latency", 3000)),
            "needs_tools": params.get("needs_tools", "true").lower() == "true",
            "needs_voice": params.get("needs_voice", "false").lower() == "true",
        }
        result = select_model(req)
        if not result["selected"]:
            return "Ningún modelo cumple los requisitos."
        output = f"Modelo seleccionado: {result['selected']}\n"
        output += f"  Calidad: {result['quality']}/10 | Costo: ${result['cost_per_1k']:.6f}/1k tokens | Latencia: ~{result['latency_ms']}ms\n"
        output += f"  Provider: {result['provider']}"
        if result["alternatives"]:
            output += f"\n  Alternativas: {', '.join(a['name'] for a in result['alternatives'])}"
        return output

    elif action == "registry":
        return "Modelos disponibles:\n" + "\n".join(
            f"  - {name}: Q={info['quality']}, cost=${info['cost']:.6f}, latency={info['latency']}ms, {'ON' if info['internet'] else 'LOCAL'}"
            for name, info in MODEL_REGISTRY.items()
        )

    elif action == "stats":
        model = params.get("model")
        stats = get_model_stats(model)
        if not stats:
            return "Sin estadísticas."
        if model:
            s = stats
            avg_latency = s["total_latency"] / s["total"] if s["total"] else 0
            return f"{model}: {s['total']} llamadas, {s['success']} exitosas, latencia promedio: {avg_latency:.0f}ms"
        return "Stats:\n" + "\n".join(
            f"  {m}: {s['total']} calls, {s['success']} ok"
            for m, s in stats.items()
        )

    return f"Acción '{action}' no reconocida. Usa: select, registry, stats"
