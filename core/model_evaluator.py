"""Model evaluator for Eris."""
import json
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "model_eval.json"

def _load() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"evaluations": [], "benchmarks": []}

def _save(data: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def model_evaluator_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        data = _load()
        return json.dumps({"evaluations": len(data.get("evaluations", [])), "benchmarks": len(data.get("benchmarks", []))})
    elif action == "evaluate":
        model = params.get("model", "unknown")
        prompt = params.get("prompt", "")
        expected = params.get("expected", "")
        metric = params.get("metric", "accuracy")
        if not prompt:
            return json.dumps({"error": "Prompt required"})
        start = time.time()
        data = _load()
        eval_entry = {
            "model": model,
            "prompt": prompt[:200],
            "expected": expected[:200],
            "metric": metric,
            "timestamp": datetime.now().isoformat(),
            "latency_ms": round((time.time() - start) * 1000),
        }
        data.setdefault("evaluations", []).append(eval_entry)
        if len(data["evaluations"]) > 200:
            data["evaluations"] = data["evaluations"][-200:]
        _save(data)
        return json.dumps({"status": "recorded", "evaluation": eval_entry})
    elif action == "benchmark":
        models = params.get("models", [])
        prompts = params.get("prompts", [])
        if not models or not prompts:
            return json.dumps({"error": "Models and prompts required"})
        results = []
        for model in models:
            for prompt in prompts:
                start = time.time()
                results.append({
                    "model": model,
                    "prompt": prompt[:100],
                    "latency_ms": round((time.time() - start) * 1000),
                })
        data = _load()
        data.setdefault("benchmarks", []).append({"timestamp": datetime.now().isoformat(), "results": results})
        _save(data)
        return json.dumps({"results": results, "total": len(results)})
    elif action == "history":
        data = _load()
        evals = data.get("evaluations", [])[-20:]
        return json.dumps({"evaluations": evals})
    return json.dumps({"error": "Unknown action"})
