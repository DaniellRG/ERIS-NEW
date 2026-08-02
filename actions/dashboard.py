# -*- coding: utf-8 -*-
"""
dashboard.py — Panel de estado del sistema y de ERIS.
Acciones: system (CPU/RAM/disco/bateria), eris (estado de ERIS), all.
"""
from __future__ import annotations


def _system_info() -> list[str]:
    import psutil
    lines = []
    cpu = psutil.cpu_percent(interval=0.3)
    lines.append(f"  CPU: {cpu}% ({psutil.cpu_count()} nucleos)")
    mem = psutil.virtual_memory()
    lines.append(f"  RAM: {mem.percent}% ({mem.used // (1024**3)}/{mem.total // (1024**3)} GB)")
    disk = psutil.disk_usage("C:\\")
    lines.append(f"  Disco C: {disk.percent}% ({disk.free // (1024**3)} GB libres)")
    try:
        bat = psutil.sensors_battery()
        if bat:
            lines.append(f"  Bateria: {bat.percent}%{' (cargando)' if bat.power_plugged else ''}")
    except Exception:
        pass
    return lines


def _eris_info(player) -> list[str]:
    lines = []
    lines.append(f"  Estado: {getattr(player, '_fallback_mode', False) and 'FALLBACK/OFFLINE' or 'ONLINE'}")
    lines.append(f"  Modo activacion por nombre: {getattr(player, '_wake_mode', True)}")
    lines.append(f"  Gate de activacion: {'abierto' if getattr(player, '_wake_gate_open', True) else 'cerrado'}")
    if hasattr(player, "_session_id"):
        lines.append(f"  Sesion: {player._session_id[:12]}")
    try:
        from core.tool_registry import get_all_tool_names
        lines.append(f"  Herramientas registradas: {len(get_all_tool_names())}")
    except Exception:
        pass
    try:
        from actions.eris_db import memory_all
        mem = memory_all(limit=1)
        from core.semantic_memory import get_memory_system
        ms = get_memory_system()
        n = 0
        try:
            n = len(ms.get_recent(limit=1000))
        except Exception:
            pass
        lines.append(f"  Recuerdos recientes: {n}")
    except Exception:
        pass
    return lines


def dashboard(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "all").lower()
    out = []
    if action in ("system", "all"):
        out.append("SISTEMA:")
        try:
            out += _system_info()
        except Exception as e:
            out.append(f"  Error: {e}")
    if action in ("eris", "all"):
        out.append("ERIS:")
        try:
            out += _eris_info(player)
        except Exception as e:
            out.append(f"  Error: {e}")
    if not out:
        out.append("Acciones: system, eris, all.")
    return "\n".join(out)
