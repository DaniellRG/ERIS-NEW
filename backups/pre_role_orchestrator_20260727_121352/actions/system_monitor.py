# -*- coding: utf-8 -*-
"""system_monitor.py — Full system monitoring for ERIS."""
import os
import time
import psutil


def system_monitor(parameters: dict = None, player=None) -> str:
    """Full system monitor: cpu, ram, disk, network, gpu, battery, processes, uptime."""
    params = parameters or {}
    action = params.get("action", "report").lower().strip()

    try:
        if action == "cpu":
            return _cpu_info()
        elif action == "ram" or action == "memory":
            return _ram_info()
        elif action == "disk":
            return _disk_info(params.get("path", "C:\\"))
        elif action == "network" or action == "net":
            return _network_info()
        elif action == "gpu":
            return _gpu_info()
        elif action == "battery":
            return _battery_info()
        elif action == "temperature" or action == "temp":
            return _temp_info()
        elif action == "uptime":
            return _uptime_info()
        elif action == "processes" or action == "procs":
            return _process_list(params.get("sort", "cpu"), params.get("count", 10))
        elif action == "kill":
            return _kill_process(params.get("name", ""), params.get("pid", 0))
        elif action == "report":
            return _full_report()
        else:
            return _full_report()
    except Exception as e:
        return f"Error en system_monitor: {e}"


def _cpu_info() -> str:
    cpu_pct = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    freq_str = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"
    try:
        load1, load5, load15 = os.getloadavg()
        load_str = f"Load: {load1:.1f} / {load5:.1f} / {load15:.1f}"
    except (OSError, AttributeError):
        load_str = ""
    msg = f"CPU: {cpu_pct}% | Cores: {cpu_count} | Freq: {freq_str}"
    if load_str:
        msg += f" | {load_str}"
    return msg


def _ram_info() -> str:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    used_gb = vm.used / (1024**3)
    total_gb = vm.total / (1024**3)
    avail_gb = vm.available / (1024**3)
    msg = f"RAM: {vm.percent}% | Usada: {used_gb:.1f}/{total_gb:.1f} GB | Disponible: {avail_gb:.1f} GB"
    if swap.total > 0:
        msg += f"\nSwap: {swap.percent}% | {swap.used/(1024**3):.1f}/{swap.total/(1024**3):.1f} GB"
    return msg


def _disk_info(path: str = "C:\\") -> str:
    try:
        usage = psutil.disk_usage(path)
        read_bytes = psutil.disk_io_counters().read_bytes if psutil.disk_io_counters() else 0
        write_bytes = psutil.disk_io_counters().write_bytes if psutil.disk_io_counters() else 0
        msg = (
            f"Disco {path}: {usage.percent}% | "
            f"Usado: {usage.used/(1024**3):.1f}/{usage.total/(1024**3):.1f} GB | "
            f"Libre: {usage.free/(1024**3):.1f} GB"
        )
        msg += f"\nI/O: Read {read_bytes/(1024**3):.2f} GB | Write {write_bytes/(1024**3):.2f} GB"
        return msg
    except Exception as e:
        return f"Error leyendo disco: {e}"


def _network_info() -> str:
    counters = psutil.net_io_counters()
    sent_gb = counters.bytes_sent / (1024**3)
    recv_gb = counters.bytes_recv / (1024**3)
    msg = f"Red: Enviado {sent_gb:.2f} GB | Recibido {recv_gb:.2f} GB | Paquetes: {counters.packets_sent} env / {counters.packets_recv} rec"

    # Active connections count
    try:
        conns = psutil.net_connections(kind="inet")
        listening = sum(1 for c in conns if c.status == "LISTEN")
        established = sum(1 for c in conns if c.status == "ESTABLISHED")
        msg += f"\nConexiones: {listening} escuchando | {established} activas"
    except (psutil.AccessDenied, PermissionError):
        pass

    # WiFi info if available
    try:
        import subprocess
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=5, creationflags=0x08000000
        )
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("SSID") and ":" in line:
                msg += f"\nWiFi: {line.split(':', 1)[1].strip()}"
            elif line.startswith("Signal") and ":" in line:
                msg += f" | Señal: {line.split(':', 1)[1].strip()}"
            elif line.startswith("Speed") and ":" in line:
                msg += f" | Velocidad: {line.split(':', 1)[1].strip()}"
    except Exception:
        pass

    return msg


def _gpu_info() -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,temperature.gpu,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, creationflags=0x08000000
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 5:
                name, mem_used, mem_total, temp, util = parts[0], parts[1], parts[2], parts[3], parts[4]
                return f"GPU: {name} | VRAM: {mem_used}/{mem_total} MB | Temp: {temp}°C | Uso: {util}%"
    except Exception:
        pass

    try:
        import wmi
        c = wmi.WMI()
        gpus = c.Win32_VideoController()
        if gpus:
            gpu = gpus[0]
            vram_mb = (gpu.AdapterRAM or 0) / (1024**2)
            return f"GPU: {gpu.Name} | VRAM: {vram_mb:.0f} MB | Driver: {gpu.DriverVersion}"
    except Exception:
        pass

    return "GPU: Info no disponible (instalá nvidia-smi o wmi)"


def _battery_info() -> str:
    battery = psutil.sensors_battery()
    if not battery:
        return "Batería: No detectada (desktop o sin batería)"
    plugged = "Cargando" if battery.power_plugged else "Sin carga"
    time_left = ""
    if battery.secsleft > 0 and not battery.power_plugged:
        mins = battery.secsleft // 60
        hours = mins // 60
        mins = mins % 60
        time_left = f" | Tiempo restante: {hours}h {mins}m"
    elif battery.power_plugged:
        time_left = " | Tiempo para cargar: calculando..."
    return f"Batería: {battery.percent}% ({plugged}){time_left}"


def _temp_info() -> str:
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return "Temperatura: No disponible (requiere sensores del SO)"
        lines = []
        for name, entries in temps.items():
            for entry in entries[:3]:
                current = entry.current or 0
                high = entry.high or 0
                label = entry.label or name
                status = "⚠️ CRÍTICO" if current > high and high > 0 else "OK"
                lines.append(f"  {label}: {current:.1f}°C (max: {high:.1f}°C) [{status}]")
        return "Temperaturas:\n" + "\n".join(lines)
    except Exception as e:
        return f"Temperatura: No disponible ({e})"


def _uptime_info() -> str:
    boot = psutil.boot_time()
    uptime_secs = time.time() - boot
    days = int(uptime_secs // 86400)
    hours = int((uptime_secs % 86400) // 3600)
    mins = int((uptime_secs % 3600) // 60)
    boot_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot))
    return f"Uptime: {days}d {hours}h {mins}m | Encendido desde: {boot_time}"


def _process_list(sort_by: str = "cpu", count: int = 10) -> str:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            info = p.info
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if sort_by == "ram" or sort_by == "memory":
        procs.sort(key=lambda x: x.get("memory_percent", 0) or 0, reverse=True)
    else:
        procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)

    lines = [f"Top {count} procesos (por {sort_by}):"]
    for p in procs[:count]:
        name = (p.get("name", "?") or "?")[:25]
        cpu = p.get("cpu_percent", 0) or 0
        ram = (p.get("memory_percent", 0) or 0)
        pid = p.get("pid", 0)
        status = p.get("status", "?")
        lines.append(f"  {pid:>6} | {name:<25} | CPU: {cpu:>5.1f}% | RAM: {ram:>5.1f}% | {status}")
    return "\n".join(lines)


def _kill_process(name: str = "", pid: int = 0) -> str:
    if not name and not pid:
        return "Error: Se requiere 'name' o 'pid' para kill."

    killed = 0
    if pid:
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=5)
            return f"Proceso {pid} ({p.name()}) terminado."
        except psutil.NoSuchProcess:
            return f"Proceso {pid} no encontrado."
        except psutil.TimeoutExpired:
            p.kill()
            return f"Proceso {pid} forzado a terminar."
    else:
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if name.lower() in (p.info.get("name", "") or "").lower():
                    p.terminate()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if killed:
            return f"{killed} proceso(s) con nombre '{name}' terminado(s)."
        return f"No se encontraron procesos con nombre '{name}'."


def _full_report() -> str:
    parts = [_cpu_info(), _ram_info(), _disk_info(), _battery_info(), _uptime_info()]
    # Network (brief)
    try:
        counters = psutil.net_io_counters()
        parts.append(f"Red: RX {counters.bytes_recv/(1024**2):.0f} MB | TX {counters.bytes_sent/(1024**2):.0f} MB")
    except Exception:
        pass
    # GPU (brief)
    gpu = _gpu_info()
    if "no disponible" not in gpu.lower():
        parts.append(gpu)
    return "\n".join(parts)
