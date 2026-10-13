# -*- coding: utf-8 -*-
"""core/autonomia.py — INICIATIVA PLENA de ERIS.

Cuando Eris está inactiva (idle > ~7 min) y tiene sesión viva, ella DECIDE y
ejecuta sola sus 4 capacidades, sin que se lo pidan:
  1. INVESTIGAR papers/repos (radar del ecosistema AGI)
  2. ESTUDIAR (ciclo de estudio continuo)
  3. CAMPAÑA DE EVOLUCIÓN (ideas + doble revisión + ELO)
  4. AUTO-DEFENSA (auditoría preventiva de su propia máquina)

Rota entre las 4 capacidades en cada turno, con un cooldown para no encadenar
iniciativas sin parar. Devuelve un string (lo consume el daemon de main.py que
lo inyecta en la sesión viva). Si está en cooldown, devuelve un texto que
EMPIEZA con "Iniciativa en cooldown" (main.py lo usa para no mostrarlo).

Integración:
  - main.py:2411 hace `from core.autonomia import turno_de_iniciativa`.
  - Delega en los módulos reales: evolution_campaigns.run_campaign,
    learning_engine.study_cycle, auto_defensa.defensa_tick, y el radar de
    papers/repos.

NOTA: `core/autonomy.py` (sin la 'i') es OTRO módulo (auto-install / auto-repair
/ curiosity) y sigue existiendo aparte; este es el de la iniciativa plena.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "autonomia.json"
_lock = threading.Lock()

COOLDOWN_SECONDS = 300  # fallback; el valor real vive en SharedContext.autonomy
                        # ("iniciativa_cooldown_s", antes 900 = 15 min: inaudible)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"created": datetime.now().isoformat(), "turnos": 0,
            "rotacion": 0, "last_run_ts": 0, "historial": []}


def _save_state(state: dict):
    try:
        _MEM.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    except Exception:
        pass


def _notify(texto: str):
    try:
        from core.todo_yo import registrar_novedad
        registrar_novedad(texto)
    except Exception:
        pass


# ── Las 4 capacidades de la iniciativa plena ──────────────────────────────────

def _investigar() -> str:
    """Radar del ecosistema: papers + repos sobre un tema rotatorio."""
    try:
        from core.tool_registry import get_tool
        tema = "agentes autónomos y auto-mejora de IA"
        r = ""
        for tname in ("paper_search", "repo_discovery"):
            try:
                out = str(get_tool(tname)({"action": "search", "query": tema,
                                           "num_results": 3}) or "")
                if out and "Error" not in out[:30]:
                    r += out[:500] + "\n"
            except Exception:
                continue
        if not r:
            out = str(get_tool("web_search")({"action": "search",
                                              "query": tema, "num_results": 3}) or "")
            r = out[:500]
        return "🔬 Iniciativa — investigué papers/repos sobre «{}».".format(tema) if r \
            else "🔬 Iniciativa — intenté investigar pero no hubo red."
    except Exception as e:
        return "🔬 Iniciativa de investigación falló: {}".format(str(e)[:80])


def _estudiar() -> str:
    try:
        from core.learning_engine import study_cycle
        return "📚 " + study_cycle()
    except Exception as e:
        return "📚 Estudio falló: {}".format(str(e)[:80])


def _campana() -> str:
    try:
        from core.evolution_campaigns import run_campaign
        return "🧬 " + run_campaign()
    except Exception as e:
        return "🧬 Campaña falló: {}".format(str(e)[:80])


def _defensa() -> str:
    try:
        from core.auto_defensa import defensa_tick
        return defensa_tick()
    except Exception as e:
        return "🛡️ Auto-defensa falló: {}".format(str(e)[:80])


_CAPACIDADES = [
    ("investigar", _investigar),
    ("estudiar", _estudiar),
    ("campana", _campana),
    ("defensa", _defensa),
]


def _cooldown_seconds() -> float:
    """Cooldown entre iniciativas, desde SharedContext (un solo lugar)."""
    try:
        from core.shared_context import get_shared_context
        return float(get_shared_context().get_autonomy(
            "iniciativa_cooldown_s", COOLDOWN_SECONDS))
    except Exception:
        return float(COOLDOWN_SECONDS)


def _enabled() -> bool:
    try:
        from core.shared_context import get_shared_context
        return bool(get_shared_context().get_autonomy("enabled", True))
    except Exception:
        return True


def turno_de_iniciativa(force: bool = False) -> str:
    """Un turno de iniciativa plena: elige una capacidad (rotando) y la ejecuta.

    Devuelve el resultado textual. Si está en cooldown (y no `force`), devuelve
    un texto que empieza con "Iniciativa en cooldown" para que main.py lo omita.
    """
    import time
    with _lock:
        state = _load_state()
        now = time.time()
        last = float(state.get("last_run_ts", 0) or 0)
        cooldown = _cooldown_seconds()
        if not force and not _enabled():
            return "Iniciativa en cooldown (autonomía desactivada)"
        if not force and (now - last) < cooldown:
            restante = int((cooldown - (now - last)) / 60) + 1
            return "Iniciativa en cooldown ({} min restantes)".format(restante)
        rot = int(state.get("rotacion", 0)) % len(_CAPACIDADES)
        nombre, func = _CAPACIDADES[rot]
        state["rotacion"] = rot + 1
        state["turnos"] = int(state.get("turnos", 0)) + 1
        state["last_run_ts"] = now
        state["historial"].append({"turno": state["turnos"], "capacidad": nombre,
                                   "fecha": _now()})
        state["historial"] = state["historial"][-50:]
        _save_state(state)

    try:
        resultado = func()
    except Exception as e:
        resultado = "Iniciativa «{}» falló: {}".format(nombre, str(e)[:100])

    _notify("Iniciativa plena: {} (turno #{}).".format(nombre, state["turnos"]))
    return "[INICIATIVA · {}] {}".format(nombre, resultado)


def estado() -> str:
    state = _load_state()
    lines = ["⚡ Iniciativa plena de ERIS — estado",
             "Activa: {}".format("sí" if _enabled() else "no"),
             "Cooldown: {:.0f} s".format(_cooldown_seconds()),
             "Turnos: {}".format(state.get("turnos", 0)),
             "Rotación actual: {}".format(state.get("rotacion", 0) % len(_CAPACIDADES)),
             "Capacidades: " + ", ".join(n for n, _ in _CAPACIDADES)]
    for h in state.get("historial", [])[-5:]:
        lines.append("  · #{t} {c} ({f})".format(t=h.get("turno"),
                                                 c=h.get("capacidad"),
                                                 f=h.get("fecha", "")))
    return "\n".join(lines)


if __name__ == "__main__":
    print(turno_de_iniciativa(force=True))
    print(estado())
