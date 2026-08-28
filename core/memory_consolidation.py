"""
core/memory_consolidation.py — Consolidacion de memoria para Eris

Consolida memoria vieja en resumenes, elimina duplicados, optimiza.
"""
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "memory_consolidation_state.json"
_LOG_FILE = _MEMORY / "memory_consolidation_log.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_consolidation": None, "consolidations": 0, "entries_removed": 0}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _log(action: str, details: str):
    entry = {"timestamp": datetime.now().isoformat(), "action": action, "details": details[:200]}
    logs = []
    if _LOG_FILE.exists():
        try:
            logs = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            logs = []
    logs.append(entry)
    if len(logs) > 50:
        logs = logs[-50:]
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOG_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


def consolidate_semantic() -> dict:
    """Consolida memoria semantica: elimina triples duplicados."""
    sem_file = _MEMORY / "semantic.json"
    if not sem_file.exists():
        return {"status": "sin_archivo"}

    try:
        triples = json.loads(sem_file.read_text(encoding="utf-8"))
        original_count = len(triples)

        seen = set()
        unique = []
        for t in triples:
            key = hashlib.md5(json.dumps(t, sort_keys=True).encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                unique.append(t)

        removed = original_count - len(unique)
        if removed > 0:
            sem_file.write_text(json.dumps(unique, indent=2, ensure_ascii=False), encoding="utf-8")

        return {"removed": removed, "remaining": len(unique), "original": original_count}
    except Exception as e:
        return {"error": str(e)}


def consolidate_episodic() -> dict:
    """Consolida episodios viejos en resumenes."""
    ep_file = _MEMORY / "episodic.json"
    if not ep_file.exists():
        return {"status": "sin_archivo"}

    try:
        episodes = json.loads(ep_file.read_text(encoding="utf-8"))
        if len(episodes) <= 10:
            return {"status": "pocos_episodios", "count": len(episodes)}

        old = episodes[:-10]
        recent = episodes[-10:]

        summary = {
            "type": "consolidated_summary",
            "timestamp": datetime.now().isoformat(),
            "episodes_consolidated": len(old),
            "key_learnings": [],
        }

        for ep in old:
            learning = ep.get("learning", "")
            if learning:
                summary["key_learnings"].append(learning[:100])

        recent.append(summary)
        ep_file.write_text(json.dumps(recent, indent=2, ensure_ascii=False), encoding="utf-8")

        return {"consolidated": len(old), "remaining": len(recent)}
    except Exception as e:
        return {"error": str(e)}


def consolidate_working() -> dict:
    """Consolida memoria working: elimina entidades viejas."""
    work_file = _MEMORY / "working.json"
    if not work_file.exists():
        return {"status": "sin_archivo"}

    try:
        data = json.loads(work_file.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "entities" in data:
            entities = data["entities"]
            if len(entities) > 20:
                data["entities"] = entities[-20:]
                work_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                return {"removed": len(entities) - 20}
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}


def create_weekly_summary() -> dict:
    """Crea resumen semanal de actividad."""
    summary_file = _MEMORY / "weekly_summary.json"
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    summary = {
        "week_ending": now.isoformat(),
        "generated": now.isoformat(),
    }

    auto_file = _MEMORY / "autonomy_state.json"
    if auto_file.exists():
        try:
            auto = json.loads(auto_file.read_text(encoding="utf-8"))
            summary["topics_learned"] = len(auto.get("learned_topics", []))
            summary["packages_installed"] = len(auto.get("installed_packages", []))
        except Exception:
            pass

    goals_file = _MEMORY / "goals.json"
    if goals_file.exists():
        try:
            goals = json.loads(goals_file.read_text(encoding="utf-8"))
            summary["goals_completed"] = len(goals.get("completed", []))
        except Exception:
            pass

    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    _log("weekly_summary", "Resumen semanal creado")
    return summary


def full_consolidation() -> dict:
    """Ejecuta consolidacion completa."""
    results = {}
    results["semantic"] = consolidate_semantic()
    results["episodic"] = consolidate_episodic()
    results["working"] = consolidate_working()
    results["weekly"] = create_weekly_summary()

    state = _load_state()
    state["last_consolidation"] = datetime.now().isoformat()
    state["consolidations"] += 1
    _save_state(state)
    _log("full_consolidation", "Consolidacion completa")
    return results


def memory_consolidation_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        state = _load_state()
        return json.dumps(state, indent=2)
    elif action == "consolidate":
        return json.dumps(full_consolidation(), indent=2, default=str)
    elif action == "semantic":
        return json.dumps(consolidate_semantic(), indent=2)
    elif action == "episodic":
        return json.dumps(consolidate_episodic(), indent=2)
    elif action == "weekly":
        return json.dumps(create_weekly_summary(), indent=2, default=str)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Memory Consolidation ===")
    print(memory_consolidation_tool({"action": "status"}))
    print(memory_consolidation_tool({"action": "consolidate"}))
