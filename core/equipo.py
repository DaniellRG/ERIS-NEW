# -*- coding: utf-8 -*-
"""core/equipo.py — CONCIENCIA DEL EQUIPO.

Lo que hace (Fase "equipo", 2026-10-13):

1. `pulso()`      -> resumen compacto y barato de la máquina (CPU, RAM, disco,
                     batería), cacheado ~20s, para inyectar en el prompt.
2. `ventanas()`   -> lista CONCISA de ventanas abiertas (no solo el foco),
                     saltando las sensibles. Para el prompt.
3. `eventos()`    -> umbrales (RAM/CPU/disco/batería) con cooldown persistente;
                     `linea_evento()` los vuelve una frase natural para que Eris
                     comente sola cuando algo se dispara.

Nunca lanza: si falta psutil o algo falla, degrada en silencio (devuelve "" / []).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE = _BASE / "memory" / "equipo.json"

# Umbrales (porcentaje) y enfriamiento entre comentarios del mismo tipo.
_UMBRAL = {"ram": 90, "cpu": 90, "disco": 90, "bateria": 15}
_COOLDOWN = 1800.0            # 30 min
_DISCO = "C:\\" if os.name == "nt" else "/"

_cache = {"t": 0.0, "txt": ""}


def _psutil():
    try:
        import psutil
        return psutil
    except Exception:
        return None


def _prime() -> None:
    """Primera medición de psutil.cpu_percent (la 1ª llamada devuelve 0.0)."""
    ps = _psutil()
    if ps is not None:
        try:
            ps.cpu_percent(interval=None)
        except Exception:
            pass


_prime()


def pulso(force: bool = False) -> str:
    """Resumen compacto del estado de la máquina (cacheado ~20s)."""
    now = time.time()
    if not force and _cache["txt"] and (now - _cache["t"]) < 20:
        return _cache["txt"]
    ps = _psutil()
    if ps is None:
        return ""
    try:
        cpu = ps.cpu_percent(interval=None)
        vm = ps.virtual_memory()
        parts = [f"CPU {cpu:.0f}%",
                 f"RAM {vm.percent:.0f}% ({vm.used / 1e9:.1f}/{vm.total / 1e9:.1f} GB)"]
        try:
            du = ps.disk_usage(_DISCO)
            parts.append(f"Disco {du.percent:.0f}%")
        except Exception:
            pass
        try:
            b = ps.sensors_battery()
            if b is not None:
                parts.append(f"Batería {b.percent:.0f}%"
                             + (" (cargando)" if b.power_plugged else ""))
        except Exception:
            pass
        txt = " · ".join(parts)
        _cache.update(t=now, txt=txt)
        return txt
    except Exception:
        return ""


def ventanas(max_n: int = 10) -> str:
    """Lista concisa de ventanas abiertas (proc: título), sin las sensibles."""
    try:
        from core.window_detect import list_windows
        wins = list_windows(max_n + 6)
    except Exception:
        return ""
    try:
        from core.observer import _is_sensitive
    except Exception:
        def _is_sensitive(_p, _t):
            return False
    lines = []
    for w in wins:
        proc = (w.get("proc") or "?").strip()[:22]
        title = (w.get("title") or "").strip()
        if _is_sensitive(proc, title):
            lines.append(f"  - {proc}: (pantalla privada)")
        else:
            lines.append(f"  - {proc}: {title[:55] or '(sin título)'}")
        if len(lines) >= max_n:
            break
    if not lines:
        return ""
    return "[PANTALLA — ventanas abiertas ahora]\n" + "\n".join(lines)


# ── Estado con cooldowns (persistido) ──────────────────────────────────────
def _load() -> dict:
    if _STATE.exists():
        try:
            return json.loads(_STATE.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def _save(st: dict) -> None:
    try:
        _STATE.parent.mkdir(parents=True, exist_ok=True)
        _STATE.write_text(json.dumps(st, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    except Exception:
        pass


def _ok(st: dict, key: str, now: float) -> bool:
    return (now - float((st.get("cooldowns") or {}).get(key, 0) or 0)) >= _COOLDOWN


def _mark(st: dict, key: str, now: float) -> None:
    st.setdefault("cooldowns", {})[key] = now


def eventos() -> list:
    """Eventos NUEVOS del equipo según umbrales (con cooldown). Lista de dicts."""
    ps = _psutil()
    if ps is None:
        return []
    now = time.time()
    st = _load()
    out = []
    try:
        vm = ps.virtual_memory()
        if vm.percent >= _UMBRAL["ram"] and _ok(st, "ram", now):
            _mark(st, "ram", now)
            out.append({"type": "ram_alta", "value": round(vm.percent)})
    except Exception:
        pass
    try:
        cpu = ps.cpu_percent(interval=None)
        if cpu >= _UMBRAL["cpu"]:
            st["cpu_streak"] = int(st.get("cpu_streak", 0) or 0) + 1
            if st["cpu_streak"] >= 2 and _ok(st, "cpu", now):
                _mark(st, "cpu", now)
                out.append({"type": "cpu_alta", "value": round(cpu)})
        else:
            st["cpu_streak"] = 0
    except Exception:
        pass
    try:
        du = ps.disk_usage(_DISCO)
        if du.percent >= _UMBRAL["disco"] and _ok(st, "disco", now):
            _mark(st, "disco", now)
            out.append({"type": "disco_lleno", "value": round(du.percent)})
    except Exception:
        pass
    try:
        b = ps.sensors_battery()
        if (b is not None and b.percent <= _UMBRAL["bateria"]
                and not b.power_plugged and _ok(st, "bateria", now)):
            _mark(st, "bateria", now)
            out.append({"type": "bateria_baja", "value": round(b.percent)})
    except Exception:
        pass
    st["last"] = now
    _save(st)
    return out


def linea_evento(ev: dict) -> str:
    """Frase natural (es-AR) para un evento del equipo, o '' si no aplica."""
    import random
    t = ev.get("type", "")
    v = ev.get("value")
    if t == "ram_alta":
        return random.choice([
            f"Che, la RAM está al {v}%. Si abrís algo pesado más, va a empezar a sufrir.",
            f"Te aviso: la memoria está al {v}%, bastante cargada. ¿Cierro algo?",
        ])
    if t == "cpu_alta":
        return random.choice([
            f"El CPU viene sostenido al {v}%. Algo está trabajando fuerte por acá.",
            f"Ojo, el procesador está al {v}% hace un rato. ¿Todo bien o lo miramos?",
        ])
    if t == "disco_lleno":
        return random.choice([
            f"El disco está al {v}%, se viene llenando. Después te ayudo a limpiar.",
            f"Che, el disco al {v}%. Hay que hacer lugar en algún momento.",
        ])
    if t == "bateria_baja":
        return random.choice([
            f"La batería está al {v}%. ¿Lo enchufás?",
            f"Batería al {v}%, te queda poco. Enchufalo si podés.",
        ])
    return ""


__all__ = ["pulso", "ventanas", "eventos", "linea_evento"]
