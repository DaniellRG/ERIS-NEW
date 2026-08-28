"""
metrics_dashboard.py — Dashboard unificado de métricas para ERIS.

Agrega métricas de todos los sistemas (tools, LLM, cache, errores, costos)
en un solo lugar para monitoreo y diagnóstico.

Métricas tracked:
  - Requests totales y por tool
  - Tiempos de ejecución (avg, p95, max)
  - Tasa de éxito/error
  - Cache hit/miss rate
  - Costo acumulado
  - LLM latency
  - Errores por categoría
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_METRICS_DIR = _BASE / "data" / "metrics"
_FILE = _METRICS_DIR / "dashboard.json"


class MetricsDashboard:
    """Dashboard unificado de métricas."""

    def __init__(self):
        self.data = self._load()

    def _load(self) -> dict:
        try:
            if _FILE.exists():
                return json.loads(_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {
            "tools": {},
            "llm": {"requests": 0, "total_tokens": 0, "errors": 0, "latencies": []},
            "cache": {"hits": 0, "misses": 0},
            "errors": defaultdict(int),
            "sessions": 0,
            "start_time": time.time(),
        }

    def _save(self):
        try:
            _METRICS_DIR.mkdir(parents=True, exist_ok=True)
            # Serializar defaultdict
            data = dict(self.data)
            if isinstance(data.get("errors"), defaultdict):
                data["errors"] = dict(data["errors"])
            _FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def record_tool_call(self, tool_name: str, elapsed: float, success: bool):
        """Registra una llamada a tool."""
        if tool_name not in self.data["tools"]:
            self.data["tools"][tool_name] = {
                "calls": 0, "errors": 0, "total_time": 0, "times": [],
            }
        t = self.data["tools"][tool_name]
        t["calls"] += 1
        t["total_time"] += elapsed
        t["times"].append(elapsed)
        if not success:
            t["errors"] += 1
        # Mantener solo últimos 100 tiempos
        if len(t["times"]) > 100:
            t["times"] = t["times"][-100:]
        self._save()

    def record_llm_request(self, tokens: int = 0, latency: float = 0, error: bool = False):
        """Registra un request LLM."""
        self.data["llm"]["requests"] += 1
        self.data["llm"]["total_tokens"] += tokens
        if error:
            self.data["llm"]["errors"] += 1
        if latency > 0:
            self.data["llm"]["latencies"].append(latency)
            if len(self.data["llm"]["latencies"]) > 200:
                self.data["llm"]["latencies"] = self.data["llm"]["latencies"][-200:]
        self._save()

    def record_cache_hit(self):
        self.data["cache"]["hits"] += 1
        self._save()

    def record_cache_miss(self):
        self.data["cache"]["misses"] += 1
        self._save()

    def record_error(self, category: str):
        self.data["errors"][category] = self.data["errors"].get(category, 0) + 1
        self._save()

    def get_tool_stats(self, tool_name: str) -> dict:
        """Estadísticas de una tool específica."""
        t = self.data["tools"].get(tool_name, {})
        if not t:
            return {}
        times = t.get("times", [])
        avg_time = sum(times) / len(times) if times else 0
        sorted_times = sorted(times)
        p95 = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
        return {
            "calls": t["calls"],
            "errors": t["errors"],
            "success_rate": f"{(t['calls'] - t['errors']) / t['calls'] * 100:.1f}%" if t["calls"] > 0 else "N/A",
            "avg_time": f"{avg_time:.3f}s",
            "p95_time": f"{p95:.3f}s",
        }

    def get_summary(self) -> dict:
        """Resumen completo del dashboard."""
        total_tool_calls = sum(t["calls"] for t in self.data["tools"].values())
        total_tool_errors = sum(t["errors"] for t in self.data["tools"].values())
        llm = self.data["llm"]
        cache = self.data["cache"]
        cache_total = cache["hits"] + cache["misses"]

        latencies = llm.get("latencies", [])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        sorted_lat = sorted(latencies)
        p95_latency = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else 0

        uptime = time.time() - self.data.get("start_time", time.time())

        return {
            "uptime_seconds": round(uptime),
            "tool_calls": total_tool_calls,
            "tool_errors": total_tool_errors,
            "tool_success_rate": f"{(total_tool_calls - total_tool_errors) / total_tool_calls * 100:.1f}%" if total_tool_calls > 0 else "N/A",
            "llm_requests": llm["requests"],
            "llm_tokens": llm["total_tokens"],
            "llm_errors": llm["errors"],
            "llm_avg_latency": f"{avg_latency:.2f}s",
            "llm_p95_latency": f"{p95_latency:.2f}s",
            "cache_hit_rate": f"{cache['hits'] / cache_total * 100:.1f}%" if cache_total > 0 else "N/A",
            "top_tools": self._top_tools(5),
            "errors": dict(self.data.get("errors", {})),
        }

    def _top_tools(self, n: int = 5) -> list[dict]:
        """Top N tools por número de llamadas."""
        sorted_tools = sorted(
            self.data["tools"].items(),
            key=lambda x: x[1]["calls"],
            reverse=True,
        )
        return [
            {"name": name, "calls": t["calls"], "errors": t["errors"]}
            for name, t in sorted_tools[:n]
        ]

    def format_dashboard(self) -> str:
        """Formato legible del dashboard."""
        s = self.get_summary()
        lines = [
            f"Dashboard ERIS (uptime: {s['uptime_seconds']//3600}h {(s['uptime_seconds']%3600)//60}m)",
            f"Tools: {s['tool_calls']} calls, {s['tool_success_rate']} éxito",
            f"LLM: {s['llm_requests']} requests, {s['llm_tokens']:,} tokens, latencia avg {s['llm_avg_latency']}",
            f"Cache: {s['cache_hit_rate']} hit rate",
        ]
        if s["top_tools"]:
            lines.append("Top tools:")
            for t in s["top_tools"]:
                lines.append(f"  {t['name']}: {t['calls']} calls, {t['errors']} errors")
        if s["errors"]:
            lines.append("Errores:")
            for cat, count in sorted(s["errors"].items(), key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"  {cat}: {count}")
        return "\n".join(lines)


# Singleton
_dashboard: MetricsDashboard | None = None


def get_dashboard() -> MetricsDashboard:
    global _dashboard
    if _dashboard is None:
        _dashboard = MetricsDashboard()
    return _dashboard
