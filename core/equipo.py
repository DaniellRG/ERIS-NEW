# -*- coding: utf-8 -*-
"""core/equipo.py — CONCIENCIA DEL EQUIPO.

Lo que hace (Fase "equipo", 2026-10-13):

1. `pulso()`      -> resumen compacto y barato de la máquina (CPU, RAM, disco,
                     batería, temperaturas de CPU/GPU/NVMe), cacheado ~20s, para
                     inyectar en el prompt.
2. `ventanas()`   -> lista CONCISA de ventanas abiertas (no solo el foco),
                     saltando las sensibles. Para el prompt.
3. `eventos()`    -> umbrales (RAM/CPU/disco/batería/temperatura) con cooldown
                     persistente; `linea_evento()` los vuelve una frase natural
                     para que Eris comente sola cuando algo se dispara.
4. `temperaturas()` -> °C disponibles (cpu/gpu/nvme), solo lo que exista.

Nunca lanza: si falta psutil o algo falla, degrada en silencio (devuelve "" / []).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE = _BASE / "memory" / "equipo.json"

# Umbrales (porcentaje / °C) y enfriamiento entre comentarios del mismo tipo.
_UMBRAL = {"ram": 90, "cpu": 90, "disco": 90, "bateria": 15,
           "temp": 85, "temp_nvme": 70}
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


def temperaturas() -> dict:
    """Temperaturas (°C) disponibles: {"cpu":.., "gpu":.., "nvme":..}.

    Mapea sensores reales (k10temp/coretemp→cpu, amdgpu→gpu, nvme→nvme).
    Devuelve solo lo que existe. Nunca lanza.
    """
    ps = _psutil()
    if ps is None:
        return {}
    try:
        sensors = ps.sensors_temperatures() or {}
    except Exception:
        return {}
    out: dict[str, int] = {}
    try:
        for name, entries in sensors.items():
            low = str(name or "").lower()
            pick = None
            for e in entries:
                cur = getattr(e, "current", None)
                if cur is None:
                    continue
                label = str(getattr(e, "label", "") or "").lower()
                if label in ("tctl", "tdie"):
                    pick = cur
                    break
                if pick is None:
                    pick = cur
            if pick is None:
                continue
            if any(k in low for k in ("k10temp", "coretemp", "zenpower", "cpu_thermal")):
                out["cpu"] = round(pick)
            elif any(k in low for k in ("amdgpu", "radeon")):
                out["gpu"] = round(pick)
            elif "nvme" in low:
                out["nvme"] = round(pick)
    except Exception:
        pass
    return out


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
        try:
            temps = temperaturas()
            if temps.get("cpu") is not None:
                parts.append(f"CPU {temps['cpu']}°")
            if temps.get("gpu") is not None:
                parts.append(f"GPU {temps['gpu']}°")
            if temps.get("nvme") is not None:
                parts.append(f"NVMe {temps['nvme']}°")
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
    try:
        temps = temperaturas()
        t_cpu, t_gpu = temps.get("cpu"), temps.get("gpu")
        tmax = max([x for x in (t_cpu, t_gpu) if x is not None], default=None)
        if tmax is not None and tmax >= _UMBRAL["temp"] and _ok(st, "temp", now):
            _mark(st, "temp", now)
            out.append({"type": "temp_alta", "value": tmax,
                        "cpu": t_cpu, "gpu": t_gpu})
        nv = temps.get("nvme")
        if nv is not None and nv >= _UMBRAL["temp_nvme"] and _ok(st, "temp_nvme", now):
            _mark(st, "temp_nvme", now)
            out.append({"type": "nvme_caliente", "value": nv})
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
    if t == "temp_alta":
        return random.choice([
            f"Che, está levantando temperatura ({v}°). Nada crítico, pero ojo con lo que exijas.",
            f"El equipo viene calentito ({v}°). ¿Le bajamos un poco el ritmo?",
        ])
    if t == "nvme_caliente":
        return random.choice([
            f"El disco NVMe está a {v}°, algo cálido. Buen momento para no exigirlo.",
            f"Ojo que el SSD viene a {v}°. Se banca, pero lo sigo.",
        ])
    return ""


__all__ = ["pulso", "ventanas", "eventos", "linea_evento", "temperaturas"]
