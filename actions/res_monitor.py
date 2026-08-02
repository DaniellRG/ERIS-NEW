# -*- coding: utf-8 -*-
"""
res_monitor.py — Monitoreo de recursos del sistema (CPU/RAM/disco/red/redes).
Acciones: status, top (procesos top).
"""
from __future__ import annotations


def res_monitor(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "status").lower()

    try:
        import psutil
    except ImportError:
        return "Error: falta psutil. Instalalo con: pip install psutil"

    if action == "top":
        n = int(parameters.get("limit", 10))
        procs = sorted(
            psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
            key=lambda p: p.info["memory_percent"] or 0,
            reverse=True,
        )[:n]
        lines = [f"Procesos top por memoria ({n}):"]
        for p in procs:
            try:
                lines.append(
                    f"  PID {p.info['pid']}: {p.info['name']} "
                    f"CPU {p.info['cpu_percent'] or 0}% MEM {p.info['memory_percent'] or 0:.1f}%"
                )
            except Exception:
                continue
        return "\n".join(lines)

    cpu = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("C:\\")
    net = psutil.net_io_counters()
    lines = [
        "RECURSOS DEL SISTEMA",
        f"  CPU: {cpu}%",
        f"  RAM: {mem.percent}% (usada {mem.used // (1024**3)} GB)",
        f"  Swap: {swap.percent}%",
        f"  Disco C: {disk.percent}% ({disk.free // (1024**3)} GB libres)",
        f"  Red: enviados {net.bytes_sent // (1024**2)} MB, recibidos {net.bytes_recv // (1024**2)} MB",
    ]
    try:
        bat = psutil.sensors_battery()
        if bat:
            lines.append(f"  Bateria: {bat.percent}%{' (cargando)' if bat.power_plugged else ''}")
    except Exception:
        pass
    return "\n".join(lines)
