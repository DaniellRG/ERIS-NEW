# -*- coding: utf-8 -*-
"""
res_protect.py — Proteccion de recursos: detecta y detiene procesos que consumen de mas.
Acciones: kill (matar por nombre/PID), check (detectar consumidores), status.
"""
from __future__ import annotations


def _find(term: str):
    import psutil
    matches = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            if term.lower() in (p.info["name"] or "").lower():
                matches.append(p)
        except Exception:
            continue
    return matches


def res_protect(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "check").lower()

    try:
        import psutil
    except ImportError:
        return "Error: falta psutil. Instalalo con: pip install psutil"

    if action == "kill":
        name = (parameters.get("name") or "").strip()
        try:
            pid = int(parameters.get("pid") or 0)
        except (TypeError, ValueError):
            pid = 0
        if not name and not pid:
            return "Error: se requiere 'name' o 'pid'."
        killed = []
        if pid:
            try:
                p = psutil.Process(pid)
                p.terminate()
                killed.append(f"PID {pid} ({p.name()})")
            except Exception as e:
                return f"Error matando PID {pid}: {e}"
        else:
            for p in _find(name):
                try:
                    p.terminate()
                    killed.append(f"PID {p.pid} ({p.name()})")
                except Exception:
                    continue
        if not killed:
            return f"No se encontro ningun proceso '{name}'."
        return "Procesos terminados: " + ", ".join(killed)

    # CHECK: procesos con alto consumo
    threshold = float(parameters.get("threshold", 50))
    procs = sorted(
        psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
        key=lambda p: (p.info["cpu_percent"] or 0),
        reverse=True,
    )
    heavy = []
    for p in procs[:15]:
        cpu = p.info["cpu_percent"] or 0
        mem = p.info["memory_percent"] or 0
        if cpu > threshold or mem > 40:
            heavy.append(f"  PID {p.info['pid']}: {p.info['name']} CPU {cpu:.0f}% MEM {mem:.0f}%")
    if not heavy:
        return "No hay procesos con consumo excesivo."
    lines = ["Procesos con consumo alto:"]
    lines += heavy
    lines.append("¿Queres que mate alguno? Usa kill (name o pid).")
    return "\n".join(lines)
