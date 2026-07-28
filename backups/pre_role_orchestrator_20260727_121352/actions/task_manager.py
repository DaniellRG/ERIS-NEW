"""Task Manager - ver procesos, matar procesos."""
import subprocess

def task_manager(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list")
    process_name = parameters.get("process", "")
    pid = parameters.get("pid", 0)

    if action in ("list", "top"):
        try:
            ps_cmd = (
                "Get-Process | Sort-Object CPU -Descending | Select-Object -First 20 | "
                "Format-Table Name, Id, @{N='CPU(s)';E={[math]::Round($_.CPU,1)}}, "
                "@{N='RAM(MB)';E={[math]::Round($_.WorkingSet64/1MB,1)}}, "
                "@{N='Threads';E={$_.Threads.Count}} -AutoSize"
            )
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=15)
            output = r.stdout.strip()
            return ("Procesos (Top 20):\n" + output) if output else "No se pudieron listar procesos."
        except Exception as e:
            return f"Error: {e}"

    elif action == "search":
        name = process_name or "*"
        try:
            ps_cmd = (
                f"Get-Process -Name '*{name}*' | "
                "Format-Table Name, Id, @{N='CPU(s)';E={[math]::Round($_.CPU,1)}}, "
                "@{N='RAM(MB)';E={[math]::Round($_.WorkingSet64/1MB,1)}} -AutoSize"
            )
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=15)
            output = r.stdout.strip()
            return (f"Buscando '{name}':\n" + output) if output else f"No encontrado: {name}"
        except Exception as e:
            return f"Error: {e}"

    elif action == "kill":
        try:
            if pid:
                r = subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True, text=True, timeout=10)
                return f"PID {pid} terminado."
            elif process_name:
                r = subprocess.run(["taskkill", "/IM", f"{process_name}.exe", "/F"],
                    capture_output=True, text=True, timeout=10)
                return f"{process_name} terminado."
            return "Necesito 'process' o 'pid'."
        except Exception as e:
            return f"Error: {e}"

    elif action == "count":
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-Process).Count"],
                capture_output=True, text=True, timeout=10)
            count = r.stdout.strip()
            return f"Procesos activos: {count}"
        except Exception as e:
            return f"Error: {e}"

    elif action == "details":
        if not process_name and not pid:
            return "Necesito 'process' o 'pid'."
        target = f"-Name '{process_name}'" if process_name else f"-Id {pid}"
        try:
            ps_cmd = (
                f"Get-Process {target} | Select-Object Name, Id, CPU, "
                "@{N='RAM(MB)';E={[math]::Round($_.WorkingSet64/1MB,1)}}, "
                "StartTime, Responding, Path"
            )
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=10)
            return r.stdout.strip() or "Proceso no encontrado."
        except Exception as e:
            return f"Error: {e}"

    return "Acciones: list, search, kill, count, details"
