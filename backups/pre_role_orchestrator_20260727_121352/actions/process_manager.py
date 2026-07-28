"""Process manager module for managing system processes."""

import os
import signal
import subprocess
import time
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def _require_psutil() -> str | None:
    if not HAS_PSUTIL:
        return "Error: psutil not installed. Install with: pip install psutil"
    return None


def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def _format_time(seconds: float) -> str:
    try:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        if d > 0:
            return f"{d}d {h}h {m}m"
        elif h > 0:
            return f"{h}h {m}m"
        else:
            return f"{m}m {s}s"
    except (ValueError, TypeError):
        return "unknown"


def _find_process(identifier: str) -> list:
    results = []
    try:
        pid = int(identifier)
        try:
            proc = psutil.Process(pid)
            return [proc]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return []
    except ValueError:
        pass

    name_lower = identifier.lower()
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if proc.info["name"] and name_lower in proc.info["name"].lower():
                results.append(proc)
            elif proc.info["exe"] and name_lower in os.path.basename(proc.info["exe"]).lower():
                results.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return results


def process_manager(parameters: dict, player=None) -> str:
    err = _require_psutil()
    if err:
        return err

    action = parameters.get("action", "list")

    if action == "list":
        sort_by = parameters.get("sort", "cpu")
        limit = parameters.get("limit", 30)

        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info", "status", "username"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"] or "unknown",
                    "cpu": info["cpu_percent"] or 0,
                    "mem_pct": info["memory_percent"] or 0,
                    "mem_bytes": info["memory_info"].rss if info["memory_info"] else 0,
                    "status": info["status"] or "",
                    "user": info["username"] or ""
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        reverse = True
        if sort_by == "cpu":
            procs.sort(key=lambda p: p["cpu"], reverse=True)
        elif sort_by == "mem":
            procs.sort(key=lambda p: p["mem_pct"], reverse=True)
        elif sort_by == "name":
            procs.sort(key=lambda p: p["name"].lower(), reverse=False)
            reverse = False
        elif sort_by == "pid":
            procs.sort(key=lambda p: p["pid"], reverse=False)
            reverse = False
        else:
            procs.sort(key=lambda p: p["cpu"], reverse=True)

        display = procs[:limit]

        lines = [
            f"Running Processes ({len(procs)} total, showing {len(display)}):",
            f"{'PID':>8}  {'Name':<30}  {'CPU%':>6}  {'Mem%':>6}  {'Memory':>10}  {'Status':<10}",
            "-" * 80,
        ]
        for p in display:
            cpu_str = f"{p['cpu']:.1f}" if p["cpu"] else "0.0"
            mem_str = f"{p['mem_pct']:.1f}" if p["mem_pct"] else "0.0"
            mem_bytes = _format_bytes(p["mem_bytes"])
            name_short = p["name"][:30]
            flag = ""
            if p["cpu"] > 10 or p["mem_pct"] > 5:
                flag = " <-- HIGH"
            lines.append(
                f"{p['pid']:>8}  {name_short:<30}  {cpu_str:>6}  {mem_str:>6}  {mem_bytes:>10}  {p['status']:<10}{flag}"
            )

        cpu_total = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        lines.append("")
        lines.append(f"System: CPU {cpu_total:.1f}% | RAM {_format_bytes(mem.used)}/{_format_bytes(mem.total)} ({mem.percent:.1f}%)")
        return "\n".join(lines)

    elif action == "kill":
        identifier = parameters.get("name", "") or str(parameters.get("pid", ""))
        force = parameters.get("force", False)
        if not identifier:
            return "Error: 'name' or 'pid' parameter required."

        procs = _find_process(identifier)
        if not procs:
            return f"Error: No process found matching '{identifier}'."

        killed = 0
        failed = 0
        details = []
        for proc in procs:
            try:
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                killed += 1
                details.append(f"  Terminated: PID {proc.pid} ({proc.name()})")
            except psutil.AccessDenied:
                failed += 1
                details.append(f"  Access denied: PID {proc.pid} ({proc.name()})")
            except psutil.NoSuchProcess:
                pass

        result = f"Kill results for '{identifier}': {killed} terminated, {failed} access denied\n"
        result += "\n".join(details)
        return result

    elif action == "priority":
        identifier = parameters.get("name", "") or str(parameters.get("pid", ""))
        level = parameters.get("level", "normal")

        if not identifier:
            return "Error: 'name' or 'pid' parameter required."

        procs = _find_process(identifier)
        if not procs:
            return f"Error: No process found matching '{identifier}'."

        priority_map = {
            "realtime": psutil.REALTIME_PRIORITY_CLASS if hasattr(psutil, 'REALTIME_PRIORITY_CLASS') else None,
            "high": psutil.HIGH_PRIORITY_CLASS if hasattr(psutil, 'HIGH_PRIORITY_CLASS') else None,
            "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS if hasattr(psutil, 'ABOVE_NORMAL_PRIORITY_CLASS') else None,
            "normal": psutil.NORMAL_PRIORITY_CLASS if hasattr(psutil, 'NORMAL_PRIORITY_CLASS') else None,
            "below_normal": psutil.BELOW_NORMAL_PRIORITY_CLASS if hasattr(psutil, 'BELOW_NORMAL_PRIORITY_CLASS') else None,
            "low": psutil.IDLE_PRIORITY_CLASS if hasattr(psutil, 'IDLE_PRIORITY_CLASS') else None,
        }

        if os.name != 'nt':
            nice_map = {"realtime": -20, "high": -10, "above_normal": -5, "normal": 0, "below_normal": 5, "low": 19}
            results = []
            for proc in procs:
                try:
                    nice_val = nice_map.get(level, 0)
                    proc.nice(nice_val)
                    results.append(f"  Set priority of PID {proc.pid} ({proc.name()}) to {level}")
                except psutil.AccessDenied:
                    results.append(f"  Access denied: PID {proc.pid}")
            return f"Priority changes:\n" + "\n".join(results)

        ps_level = priority_map.get(level)
        if ps_level is None:
            available = ", ".join(k for k, v in priority_map.items() if v is not None)
            return f"Error: Invalid level '{level}'. Available: {available}"

        results = []
        for proc in procs:
            try:
                proc.nice(ps_level)
                results.append(f"  Set priority of PID {proc.pid} ({proc.name()}) to {level}")
            except psutil.AccessDenied:
                results.append(f"  Access denied: PID {proc.pid}")
        return "Priority changes:\n" + "\n".join(results)

    elif action == "memory":
        top_n = parameters.get("limit", 20)

        procs = []
        for proc in psutil.process_iter(["pid", "name", "memory_info", "memory_percent"]):
            try:
                info = proc.info
                if info["memory_info"]:
                    procs.append({
                        "pid": info["pid"],
                        "name": info["name"] or "unknown",
                        "rss": info["memory_info"].rss,
                        "vms": info["memory_info"].vms,
                        "pct": info["memory_percent"] or 0
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda p: p["rss"], reverse=True)
        display = procs[:top_n]

        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        lines = [
            "Memory Usage:",
            f"  Total: {_format_bytes(mem.total)} | Used: {_format_bytes(mem.used)} ({mem.percent:.1f}%) | Free: {_format_bytes(mem.available)}",
            f"  Swap: {_format_bytes(swap.total)} | Used: {_format_bytes(swap.used)} ({swap.percent:.1f}%)",
            "",
            f"Top {len(display)} processes by memory:",
            f"{'PID':>8}  {'Name':<30}  {'RSS':>12}  {'VMS':>12}  {'%':>6}",
            "-" * 75,
        ]
        for p in display:
            lines.append(
                f"{p['pid']:>8}  {p['name'][:30]:<30}  {_format_bytes(p['rss']):>12}  {_format_bytes(p['vms']):>12}  {p['pct']:>5.1f}%"
            )
        return "\n".join(lines)

    elif action == "cpu":
        top_n = parameters.get("limit", 20)
        interval = min(parameters.get("interval", 1), 10)

        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "num_threads"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"] or "unknown",
                    "cpu": info["cpu_percent"] or 0,
                    "threads": info["num_threads"] or 0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda p: p["cpu"], reverse=True)
        display = procs[:top_n]
        total_cpu = psutil.cpu_percent(interval=interval)
        cpu_count = psutil.cpu_count()

        lines = [
            f"CPU Usage: {total_cpu:.1f}% ({cpu_count} cores)",
            "",
            f"Top {len(display)} processes by CPU:",
            f"{'PID':>8}  {'Name':<30}  {'CPU%':>6}  {'Threads':>8}",
            "-" * 60,
        ]
        for p in display:
            flag = " <--" if p["cpu"] > 10 else ""
            lines.append(
                f"{p['pid']:>8}  {p['name'][:30]:<30}  {p['cpu']:>5.1f}%  {p['threads']:>8}{flag}"
            )
        return "\n".join(lines)

    elif action == "startup":
        sub = parameters.get("sub_action", "list")

        if sub == "list":
            if os.name != 'nt':
                return "Startup management is only supported on Windows."

            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Format-Table -AutoSize"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return f"Startup Programs:\n{result.stdout}"
                else:
                    return f"Error: {result.stderr}"
            except Exception as e:
                return f"Error listing startup programs: {e}"

        elif sub == "add":
            name = parameters.get("name", "")
            command = parameters.get("command", "")
            if not name or not command:
                return "Error: 'name' and 'command' required."

            if os.name != 'nt':
                return "Startup management is only supported on Windows."

            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     f'New-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" '
                     f'-Name "{name}" -Value "{command}" -PropertyType String -Force'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return f"Added startup entry: {name} -> {command}"
                return f"Error: {result.stderr}"
            except Exception as e:
                return f"Error: {e}"

        elif sub == "remove":
            name = parameters.get("name", "")
            if not name:
                return "Error: 'name' required."

            if os.name != 'nt':
                return "Startup management is only supported on Windows."

            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     f'Remove-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" '
                     f'-Name "{name}" -Force'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return f"Removed startup entry: {name}"
                return f"Error: {result.stderr}"
            except Exception as e:
                return f"Error: {e}"

        return f"Error: Unknown sub_action '{sub}'. Available: list, add, remove"

    elif action == "cleanup":
        cpu_threshold = parameters.get("cpu_threshold", 10)
        mem_threshold_mb = parameters.get("mem_threshold", 500)
        dry_run = parameters.get("dry_run", True)

        heavy = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = proc.info
                mem_mb = info["memory_info"].rss / (1024 * 1024) if info["memory_info"] else 0
                cpu = info["cpu_percent"] or 0
                if cpu > cpu_threshold or mem_mb > mem_threshold_mb:
                    heavy.append({
                        "pid": info["pid"],
                        "name": info.name(),
                        "cpu": cpu,
                        "mem_mb": mem_mb,
                        "proc": proc
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        heavy.sort(key=lambda p: p["cpu"] + p["mem_mb"] / 10, reverse=True)

        if not heavy:
            return f"No heavy processes found (CPU>{cpu_threshold}% or RAM>{mem_threshold_mb}MB)."

        lines = [
            f"{'DRY RUN - ' if dry_run else ''}Heavy Processes (>{cpu_threshold}% CPU or >{mem_threshold_mb}MB RAM):",
            f"{'PID':>8}  {'Name':<30}  {'CPU%':>6}  {'Memory':>10}",
            "-" * 60,
        ]

        killed = 0
        for p in heavy:
            lines.append(f"{p['pid']:>8}  {p['name'][:30]:<30}  {p['cpu']:>5.1f}%  {_format_bytes(int(p['mem_mb'] * 1024 * 1024)):>10}")
            if not dry_run:
                try:
                    p["proc"].terminate()
                    killed += 1
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    lines.append(f"           Access denied or already terminated")

        lines.append(f"\nFound {len(heavy)} heavy processes. {'(dry run - no processes killed)' if dry_run else f'Killed {killed} processes.'}")
        return "\n".join(lines)

    elif action == "info":
        identifier = parameters.get("name", "") or str(parameters.get("pid", ""))
        if not identifier:
            return "Error: 'name' or 'pid' required."

        procs = _find_process(identifier)
        if not procs:
            return f"Error: No process found matching '{identifier}'."

        proc = procs[0]
        try:
            info = proc.as_dict(attrs=[
                "pid", "ppid", "name", "exe", "cmdline", "status",
                "create_time", "cpu_percent", "cpu_times",
                "memory_info", "memory_percent", "num_threads",
                "num_fds" if hasattr(proc, "num_fds") else "threads",
                "username", "cwd"
            ])
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            return f"Error getting process info: {e}"

        mem = info.get("memory_info")
        cpu_times = info.get("cpu_times")

        lines = [
            f"Process Info: {info.get('name', 'unknown')}",
            "=" * 50,
            f"  PID: {info.get('pid')}",
            f"  PPID: {info.get('ppid')}",
            f"  Status: {info.get('status')}",
            f"  User: {info.get('username', 'N/A')}",
            f"  Executable: {info.get('exe', 'N/A')}",
            f"  CWD: {info.get('cwd', 'N/A')}",
            f"  Command: {' '.join(info.get('cmdline', [])) if info.get('cmdline') else 'N/A'}",
            f"  Created: {datetime.fromtimestamp(info['create_time']).strftime('%Y-%m-%d %H:%M:%S') if info.get('create_time') else 'N/A'}",
            f"  Uptime: {_format_time(time.time() - info['create_time']) if info.get('create_time') else 'N/A'}",
            f"  CPU%: {info.get('cpu_percent', 0):.1f}%",
            f"  Threads: {info.get('num_threads', 'N/A')}",
            f"  Memory RSS: {_format_bytes(mem.rss) if mem else 'N/A'}",
            f"  Memory VMS: {_format_bytes(mem.vms) if mem else 'N/A'}",
            f"  Memory %: {info.get('memory_percent', 0):.1f}%",
        ]

        if cpu_times:
            lines.append(f"  CPU User: {_format_time(cpu_times.user)}")
            lines.append(f"  CPU System: {_format_time(cpu_times.system)}")

        return "\n".join(lines)

    else:
        return (
            f"Error: Unknown action '{action}'. Available:\n"
            "  list, kill, priority, memory, cpu, startup, cleanup, info"
        )
