"""System Reader - Lee el estado profundo del PC."""
import psutil
import datetime
import os
import json
import platform
from collections import Counter

_CPU_HISTORY = []
_MEM_HISTORY = []
_NET_HISTORY = []

def _root_dev():
    return "/" if os.name != "nt" else "C:\\"


def _safe_read(path, default=""):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(2000)
    except OSError:
        return default

def system_reader(parameters=None, player=None, action: str = None, detail: str = None):
    params = parameters if isinstance(parameters, dict) else {}
    if action is None:
        action = params.get("action", "status")
    if detail is None:
        detail = params.get("detail", "normal")
    if action == "status":
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(_root_dev())
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
            except Exception:
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
            except OSError:
                lines.append(f"  {part.device:4s} {part.mountpoint:10s} ?")
        return "\n".join(lines)

    elif action == "network":
        net = psutil.net_io_counters()
        conns = psutil.net_connections(kind="inet")
        lines = [
            f"Red total: bajada {net.bytes_recv//(1024**2)}MB subida {net.bytes_sent//(1024**2)}MB",
            f"Conexiones TCP/UDP activas: {len(conns)}",
            "",
        ]
        if detail == "verbose":
            tcp = [c for c in conns if c.status]
            lines.append("Conexiones establecidas (top 12):")
            for c in sorted(tcp, key=lambda x: (x.status or "") == "ESTABLISHED", reverse=True)[:12]:
                laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "-"
                raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "-"
                lines.append(f"  {c.status:12s} {laddr:28s} -> {raddr:28s} pid={c.pid}")
        else:
            statuses = Counter(c.status or "?" for c in conns)
            lines.append("Por estado: " + ", ".join(f"{k}: {v}" for k, v in statuses.most_common()))
        try:
            io = psutil.net_io_counters(pernic=True)
            lines.append("")
            lines.append("Interfaces:")
            for iface, cnt in io.items():
                lines.append(f"  {iface[:20]:20s} RX {cnt.bytes_recv//(1024**2)}MB  TX {cnt.bytes_sent//(1024**2)}MB")
        except Exception:
            pass
        return "\n".join(lines)

    elif action == "advisory":
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(_root_dev())
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot
        temp_ok = True
        try:
            temps = psutil.sensors_temperatures()
            for entries in temps.values():
                for e in entries:
                    if e.current and e.current > 80:
                        temp_ok = False
        except Exception:
            pass

        findings = []
        if cpu > 80:
            findings.append("CPU al {cpu}%: hay procesos pesados consumiendo. Revisa 'top_processes'.")
        if mem.percent > 85:
            findings.append(f"RAM al {mem.percent}%: pocos recursos libres ({mem.available//(1024**3)}GB). Cerrar aplicaciones o liberar memoria.")
        elif mem.percent > 70:
            findings.append(f"RAM al {mem.percent}%: uso elevado pero controlable.")
        if disk.percent > 90:
            findings.append(f"Disco C: al {disk.percent}%: criticamente lleno, libera espacio.")
        elif disk.percent > 80:
            findings.append(f"Disco C: al {disk.percent}%: recomendable liberar espacio.")
        if uptime.days >= 3:
            findings.append(f"Uptime {uptime.days}d: considera reiniciar para liberar memoria y aplicar updates.")
        if not temp_ok:
            findings.append("Temperaturas altas (>80°C): revisa refrigeracion/ventilacion.")
        procs = psutil.pids()
        if len(procs) > 250:
            findings.append(f"{len(procs)} procesos activos: numero alto, revisar tareas de fondo.")

        if not findings:
            return ("Sistema saludable.\n  CPU {cpu}% | RAM {mem.percent}% | Disco {disk.percent}%\n"
                    "No se detectaron problemas.")
        return ("Advertencias de salud del sistema:\n  " + "\n  ".join(findings))

    elif action == "sensors":
        temps = []
        try:
            temps = psutil.sensors_temperatures()
        except Exception:
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
        disk = psutil.disk_usage(_root_dev())
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

    elif action == "platform":
        from core.platform_self import system_portrait_markdown, _system_dict
        try:
            raw = _system_dict()
            tools = raw["tools"]
            lines = [system_portrait_markdown(), "", "MAPA COMPLETO (programa → tool ERIS → disponible):"]
            for prog, d in sorted(tools.items()):
                lines.append(
                    f"  {prog}: {'✔' if d['available'] else '✘'}  →  {d['eris_tool']}  ({d['for']})")
            return "\n".join(lines)
        except Exception as e:
            return f"platform: error ({e})"

    elif action == "platform_os":
        return "Acciones: status, top_processes, disks, network, platform, sensors, deep"

    return "Acciones: status, top_processes, disks, network, platform, sensors, deep"
