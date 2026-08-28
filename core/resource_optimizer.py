"""
resource_optimizer.py — Optimización de recursos del sistema.

Monitorea y optimiza CPU, RAM, disco, y procesos:
  - Detecta procesos que consumen demasiado
  - Sugiere limpieza de archivos temporales
  - Optimiza uso de memoria del propio agente
  - Alerta sobre condiciones de resource pressure
"""
from __future__ import annotations

import os
import json
import time
import shutil
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent


def get_system_resources() -> dict:
    """Obtiene estado actual de recursos del sistema."""
    resources = {
        "timestamp": time.time(),
        "platform": os.name,
    }

    try:
        import psutil
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu_percent = psutil.cpu_percent(interval=0.5)

        resources.update({
            "cpu_percent": cpu_percent,
            "cpu_count": psutil.cpu_count(),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_percent": mem.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_percent": round(disk.used / disk.total * 100, 1),
            "top_processes": _get_top_processes(),
        })
    except ImportError:
        resources.update(_basic_resource_check())

    return resources


def _basic_resource_check() -> dict:
    """Check básico sin psutil."""
    resources = {}
    try:
        temp_dir = Path(os.environ.get("TEMP", "/tmp"))
        temp_size = sum(f.stat().st_size for f in temp_dir.rglob("*") if f.is_file())
        resources["temp_files_size_mb"] = round(temp_size / (1024**2), 2)
    except Exception:
        pass

    try:
        project_size = sum(f.stat().st_size for f in _BASE.rglob("*") if f.is_file())
        resources["project_size_mb"] = round(project_size / (1024**2), 2)
    except Exception:
        pass

    return resources


def _get_top_processes(n: int = 5) -> list[dict]:
    """Obtiene los N procesos que más memoria consumen."""
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
            try:
                info = p.info
                if info.get("memory_percent", 0) > 0.1:
                    procs.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "memory_percent": round(info.get("memory_percent", 0), 1),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x["memory_percent"], reverse=True)
        return procs[:n]
    except ImportError:
        return []


def get_temp_files_size() -> dict:
    """Calcula tamaño de archivos temporales."""
    temp_dirs = [
        Path(os.environ.get("TEMP", "/tmp")),
        Path.home() / ".cache",
        _BASE / "data" / "cache",
    ]
    total = 0
    breakdown = {}
    for d in temp_dirs:
        if d.exists():
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            breakdown[str(d)] = round(size / (1024**2), 2)
            total += size
    return {"total_mb": round(total / (1024**2), 2), "breakdown": breakdown}


def clean_temp_files(dry_run: bool = True) -> dict:
    """Limpia archivos temporales del proyecto.

    Args:
        dry_run: Si True, solo reporta sin borrar
    """
    cache_dir = _BASE / "data" / "cache"
    temp_patterns = ["*.tmp", "*.pyc", "__pycache__", "*.log.old"]

    files_to_clean = []
    if cache_dir.exists():
        for f in cache_dir.rglob("*"):
            if f.is_file():
                files_to_clean.append(str(f))

    # __pycache__
    for pycache in _BASE.rglob("__pycache__"):
        if pycache.is_dir():
            for f in pycache.glob("*"):
                files_to_clean.append(str(f))

    total_size = sum(Path(f).stat().st_size for f in files_to_clean if Path(f).exists())

    if not dry_run:
        for f in files_to_clean:
            try:
                Path(f).unlink(missing_ok=True)
            except Exception:
                pass

    return {
        "files_found": len(files_to_clean),
        "total_size_mb": round(total_size / (1024**2), 2),
        "cleaned": not dry_run,
    }


def get_optimization_suggestions() -> list[dict]:
    """Genera sugerencias de optimización."""
    suggestions = []
    resources = get_system_resources()

    # RAM
    ram_pct = resources.get("ram_percent", 0)
    if ram_pct > 85:
        suggestions.append({
            "category": "memory",
            "severity": "high",
            "message": "RAM al %.0f%% — Considerar cerrar procesos o reiniciar servicios" % ram_pct,
            "action": "close_heavy_processes",
        })
    elif ram_pct > 70:
        suggestions.append({
            "category": "memory",
            "severity": "medium",
            "message": "RAM al %.0f%% — Monitorear uso" % ram_pct,
            "action": "monitor",
        })

    # Disco
    disk_pct = resources.get("disk_percent", 0)
    if disk_pct > 90:
        suggestions.append({
            "category": "disk",
            "severity": "high",
            "message": "Disco al %.0f%% — Limpiar archivos temporales urgente" % disk_pct,
            "action": "clean_temp",
        })
    elif disk_pct > 80:
        suggestions.append({
            "category": "disk",
            "severity": "medium",
            "message": "Disco al %.0f%% — Considerar limpieza" % disk_pct,
            "action": "clean_temp",
        })

    # CPU
    cpu_pct = resources.get("cpu_percent", 0)
    if cpu_pct > 90:
        suggestions.append({
            "category": "cpu",
            "severity": "high",
            "message": "CPU al %.0f%% — Posible proceso atascado" % cpu_pct,
            "action": "check_processes",
        })

    # Cache del proyecto
    cache_info = get_temp_files_size()
    if cache_info.get("total_mb", 0) > 100:
        suggestions.append({
            "category": "cache",
            "severity": "medium",
            "message": "Cache del proyecto: %.1f MB — Considerar limpiar" % cache_info["total_mb"],
            "action": "clean_project_cache",
        })

    return suggestions


def optimize_memory() -> dict:
    """Optimiza uso de memoria del agente."""
    import gc
    collected = gc.collect()

    # Limpiar caches internas
    cleared = 0
    try:
        from core.tool_cache import get_tool_cache
        cache = get_tool_cache()
        cache.clear()
        cleared += 1
    except Exception:
        pass

    return {
        "gc_collected": collected,
        "caches_cleared": cleared,
        "message": "Memoria optimizada: %d objetos GC, %d caches limpiados" % (collected, cleared),
    }


def format_resources(resources: dict) -> str:
    """Formatea estado de recursos."""
    lines = ["Recursos del sistema:"]
    if "cpu_percent" in resources:
        lines.append("  CPU: %.0f%% (%d cores)" % (resources["cpu_percent"], resources.get("cpu_count", 0)))
    if "ram_percent" in resources:
        lines.append("  RAM: %.1f%% (%.1f / %.1f GB)" % (
            resources["ram_percent"], resources["ram_used_gb"], resources["ram_total_gb"]))
    if "disk_percent" in resources:
        lines.append("  Disco: %.1f%% (%.1f / %.1f GB)" % (
            resources["disk_percent"], resources["disk_used_gb"], resources["disk_total_gb"]))
    if "project_size_mb" in resources:
        lines.append("  Proyecto: %.1f MB" % resources["project_size_mb"])

    suggestions = get_optimization_suggestions()
    if suggestions:
        lines.append("\nSugerencias:")
        for s in suggestions:
            icon = {"high": "!!", "medium": "!", "low": "-"}.get(s["severity"], "?")
            lines.append("  [%s] %s" % (icon, s["message"]))

    return "\n".join(lines)
