"""System Reader - Lee el estado profundo del PC."""
import psutil
import datetime
import os
import json
import platform

_CPU_HISTORY = []
_MEM_HISTORY = []
_NET_HISTORY = []

def _safe_read(path, default=""):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(2000)
    except:
        return default

def system_reader(action: str = "status", detail: str = "normal"):
    if action == "status":
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        net = psutil.net_io_counters()
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot

        _CPU_HISTORY.append(cpu)
        _MEM_HISTORY.append(mem.percent)
        if len(_CPU_HISTORY) > 60:
            _CPU_HISTORY.pop(0)
        if len(_MEM_HISTORY) > 60:
            _MEM_HISTORY.pop(0)

        avg_cpu = sum(_CPU_HISTORY[-5:]) // max(len(_CPU_HISTORY[-5:]), 1)
        avg_mem = sum(_MEM_HISTORY[-5:]) // max(len(_MEM_HISTORY[-5:]), 1)

        lines = [
            f"Sistema encendido desde: {boot.strftime('%A %d/%m %H:%M')} ({uptime.days}d {uptime.seconds//3600}h)",
            f"CPU: {cpu}% (promedio 5min: {avg_cpu}%)",
            f"RAM: {mem.percent}% usado de {mem.total//(1024**3)}GB (promedio 5min: {avg_mem}%)",
            f"Disco C:: {disk.percent}% usado ({disk.free//(1024**3)}GB libres de {disk.total//(1024**3)}GB)",
            f"Red: bajada {net.bytes_recv//(1024**2)}MB subida {net.bytes_sent//(1024**2)}MB",
            f"Procesos: {len(psutil.pids())}",
            f"OS: {platform.system()} {platform.release()} ({platform.architecture()[0]})",
        ]
        return "\n".join(lines)

    elif action == "top_processes":
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                info = p.info
                if info["cpu_percent"] and info["cpu_percent"] > 0:
                    procs.append(info)
            except:
                pass
        procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
        lines = ["Procesos activos por CPU:"]
        for proc in procs[:10]:
            lines.append(f"  {proc['name'][:30]:30s} CPU:{proc.get('cpu_percent',0):5.1f}% MEM:{proc.get('memory_percent',0):5.1f}%")
        return "\n".join(lines)

    elif action == "disks":
        lines = ["Discos:"]
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                lines.append(f"  {part.device:4s} {part.mountpoint:10s} {usage.percent:3d}% usado  {usage.free//(1024**3)}GB libres")
            except:
                lines.append(f"  {part.device:4s} {part.mountpoint:10s} ?")
        return "\n".join(lines)

    elif action == "network":
        net = psutil.net_io_counters()
        conns = psutil.net_connections()
        lines = [
            f"Red total: bajada {net.bytes_recv//(1024**2)}MB subida {net.bytes_sent//(1024**2)}MB",
            f"Conexiones activas: {len(conns)}",
        ]
        return "\n".join(lines)

    elif action == "sensors":
        temps = []
        try:
            temps = psutil.sensors_temperatures()
        except:
            pass
        if temps:
            lines = ["Temperaturas:"]
            for name, entries in temps.items():
                for e in entries:
                    lines.append(f"  {name}: {e.current}°C")
            return "\n".join(lines)
        return "Sensores no disponibles."

    elif action == "deep":
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot
        procs = sorted(
            [p.info for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent"]) if p.info.get("cpu_percent")],
            key=lambda x: x["cpu_percent"], reverse=True
        )[:8]
        top_names = " | ".join([p["name"][:20] for p in procs])
        return (
            f"Sistema activo {uptime.days}d {uptime.seconds//3600}h | "
            f"CPU {cpu}% | RAM {mem.percent}% | Disco {disk.percent}% | "
            f"Procesos: {top_names}"
        )

    return "Acciones: status, top_processes, disks, network, sensors, deep"
