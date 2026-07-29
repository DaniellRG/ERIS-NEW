"""
actions/vscode_controller.py — Controla VS Code desde ERIS.
Usa la CLI de 'code' para abrir carpetas, archivos, editar, buscar,
y puede lanzar live-server + file watcher para feedback visual en tiempo real.
"""
import json
import os
import subprocess
import threading
import time
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_WATCHERS = {}
_LIVE_SERVERS = {}

def vscode_controller(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "").lower()
    path = parameters.get("path") or parameters.get("ruta") or ""
    file_path = parameters.get("file") or parameters.get("archivo") or ""
    line = parameters.get("line", 1)
    col = parameters.get("col", 1)
    folder = parameters.get("folder") or parameters.get("carpeta") or ""
    port = parameters.get("port", 5500)
    cmd = parameters.get("command") or parameters.get("comando") or ""
    query = parameters.get("query") or parameters.get("buscar") or ""

    if player:
        player.write_log(f"🖥️ VS Code: {action}")

    if action in ("open", "abrir"):
        if not path:
            path = str(_BASE_DIR)
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return f"No existe: {path}"
        r = _code_cli(["--new-window", path])
        if player:
            player.write_log(f"  Abierto: {path}")
        return f"VS Code abierto: {path}"

    elif action in ("open_file", "abrir_archivo", "goto", "ir_a"):
        if not file_path:
            return "Necesito 'file' (ruta del archivo)"
        full = _resolve_path(file_path)
        if not os.path.exists(full):
            return f"No existe: {full}"
        r = _code_cli(["--goto", f"{full}:{line}:{col}"])
        return f"Abierto {os.path.basename(full)} en linea {line}:{col}"

    elif action in ("open_folder", "abrir_carpeta"):
        if not folder:
            folder = str(_BASE_DIR)
        folder = os.path.abspath(folder)
        if not os.path.isdir(folder):
            return f"No existe la carpeta: {folder}"
        r = _code_cli(["--new-window", folder])
        return f"Carpeta abierta: {folder}"

    elif action in ("diff", "comparar"):
        file1 = parameters.get("file1", "")
        file2 = parameters.get("file2", "")
        if not file1 or not file2:
            return "Necesito 'file1' y 'file2' para comparar"
        f1, f2 = _resolve_path(file1), _resolve_path(file2)
        r = _code_cli(["--diff", f1, f2])
        return f"Comparando: {os.path.basename(f1)} ↔ {os.path.basename(f2)}"

    elif action in ("reopen", "reabrir"):
        r = _code_cli(["--reuse-window", path or str(_BASE_DIR)])
        return "VS Code reabierto en misma ventana"

    elif action in ("install_ext", "instalar_ext"):
        ext = parameters.get("extension", "")
        if not ext:
            return "Necesito 'extension' (ej: ms-python.python)"
        r = _code_cli(["--install-extension", ext])
        return f"Extension instalada: {ext}" if "success" in r.lower() else r

    elif action in ("list_ext", "listar_ext"):
        try:
            r = subprocess.run(["code", "--list-extensions"], capture_output=True, text=True, timeout=15)
            exts = r.stdout.strip().split("\n") if r.stdout.strip() else []
            return f"Extensiones ({len(exts)}):\n" + "\n".join(exts[:30])
        except Exception as e:
            return f"Error: {e}"

    elif action in ("exec_cmd", "ejecutar"):
        if not cmd:
            return "Necesito 'command' para ejecutar en VS Code"
        r = _code_cli(["--command", cmd])
        return f"Comando ejecutado: {cmd}"

    elif action in ("live_server", "servidor"):
        if not folder:
            folder = str(_BASE_DIR)
        folder = os.path.abspath(folder)
        if not os.path.isdir(folder):
            return f"No existe la carpeta: {folder}"
        return _start_live_server(folder, port, player)

    elif action in ("stop_server", "detener_servidor"):
        return _stop_live_server(path or str(_BASE_DIR))

    elif action in ("watch", "vigilar"):
        if not folder:
            folder = str(_BASE_DIR)
        folder = os.path.abspath(folder)
        return _start_watcher(folder, cmd or "python -m http.server", player)

    elif action in ("stop_watch", "detener_vigilar"):
        return _stop_watcher(path or str(_BASE_DIR))

    elif action in ("new_file", "nuevo_archivo"):
        if not file_path:
            return "Necesito 'file' con la ruta del nuevo archivo"
        full = _resolve_path(file_path)
        content = parameters.get("content", "")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        Path(full).write_text(content, encoding="utf-8")
        r = _code_cli([full])
        return f"Archivo creado y abierto: {full}"

    elif action in ("search", "buscar"):
        if not query:
            return "Necesito 'query' para buscar en VS Code"
        r = _code_cli(["--search", query])
        return f"Buscando: {query}"

    elif action in ("status", "estado"):
        return _status()

    else:
        return (
            "Acciones VS Code:\n"
            "  open (path=) — Abrir carpeta en nueva ventana\n"
            "  open_file (file=, line=, col=) — Abrir archivo en linea X\n"
            "  open_folder (folder=) — Abrir carpeta\n"
            "  diff (file1=, file2=) — Comparar archivos\n"
            "  install_ext (extension=) — Instalar extension\n"
            "  list_ext — Listar extensiones\n"
            "  exec_cmd (command=) — Ejecutar comando VS Code\n"
            "  live_server (folder=, port=) — Servidor local con recarga\n"
            "  stop_server — Detener servidor\n"
            "  watch (folder=, command=) — Vigilar cambios en carpeta\n"
            "  stop_watch — Detener vigia\n"
            "  new_file (file=, content=) — Crear archivo y abrirlo\n"
            "  search (query=) — Buscar en proyecto\n"
            "  reopen — Reabrir en misma ventana\n"
            "  status — Estado de servidores y watchers"
        )


def _code_cli(args: list) -> str:
    try:
        result = subprocess.run(
            ["code"] + args,
            capture_output=True, text=True, timeout=15,
            creationflags=0x08000000,
        )
        output = result.stdout.strip() or result.stderr.strip() or "OK"
        return output[:500]
    except FileNotFoundError:
        return "Error: 'code' CLI no disponible. Instala VS Code y agregalo al PATH."
    except subprocess.TimeoutExpired:
        return "Timeout: VS Code tardo mas de 15s"
    except Exception as e:
        return f"Error: {e}"


def _resolve_path(file_path: str) -> str:
    p = Path(file_path)
    if p.is_absolute():
        return str(p)
    return str(_BASE_DIR / file_path)


def _start_live_server(folder: str, port: int, player=None) -> str:
    key = folder.lower()
    if key in _LIVE_SERVERS:
        return f"Ya hay un servidor corriendo en {folder} (puerto {_LIVE_SERVERS[key]['port']}). Usa stop_server primero."

    try:
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command",
             f"python -m http.server {port} --directory '{folder}'"],
            creationflags=0x08000000,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        _LIVE_SERVERS[key] = {"proc": proc, "port": port, "folder": folder, "start": time.time()}
        # Also open browser
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")
        if player:
            player.write_log(f"  Live server: http://localhost:{port} en {folder}")
        return f"Servidor iniciado: http://localhost:{port}\nArchivos servidos desde: {folder}\nAbierto en el navegador."
    except Exception as e:
        return f"Error iniciando servidor: {e}"


def _stop_live_server(folder: str) -> str:
    key = folder.lower()
    if key not in _LIVE_SERVERS:
        # Try to find the closest
        for k, v in list(_LIVE_SERVERS.items()):
            if folder.lower() in k or k in folder.lower():
                key = k
                break
        else:
            return "No hay servidor activo en esa ruta"

    info = _LIVE_SERVERS.pop(key)
    try:
        info["proc"].terminate()
        info["proc"].wait(timeout=5)
    except Exception:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(info["proc"].pid)], capture_output=True, timeout=5)
        except Exception:
            pass
    return f"Servidor detenido (puerto {info['port']})"


def _start_watcher(folder: str, command: str, player=None) -> str:
    key = folder.lower()
    if key in _WATCHERS:
        return f"Ya hay un watcher en {folder}"

    watcher_script = f"""
$watcher = New-Object FileSystemWatcher
$watcher.Path = '{folder}'
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true
$action = {{ 
    $name = $Event.SourceEventArgs.Name
    $change = $Event.SourceEventArgs.ChangeType
    Write-Host "[CHANGE] $change : $name"
    if ($name -like '*.html' -or $name -like '*.css' -or $name -like '*.js') {{
        try {{ {command} }} catch {{ }}
    }}
}}
Register-ObjectEvent $watcher "Changed" -Action $action | Out-Null
Register-ObjectEvent $watcher "Created" -Action $action | Out-Null
Register-ObjectEvent $watcher "Deleted" -Action $action | Out-Null
Write-Host "Watcher iniciado en: {folder}"
while($true) {{ Start-Sleep -Seconds 60 }}
"""
    try:
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", watcher_script],
            creationflags=0x08000000,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        _WATCHERS[key] = {"proc": proc, "folder": folder, "command": command, "start": time.time()}
        if player:
            player.write_log(f"  Watcher iniciado en: {folder}")
        return f"Watcher iniciado en: {folder}\nDetecta cambios en .html, .css, .js y ejecuta: {command}"
    except Exception as e:
        return f"Error iniciando watcher: {e}"


def _stop_watcher(folder: str) -> str:
    key = folder.lower()
    if key not in _WATCHERS:
        for k, v in list(_WATCHERS.items()):
            if folder.lower() in k or k in folder.lower():
                key = k
                break
        else:
            return "No hay watcher activo en esa ruta"
    info = _WATCHERS.pop(key)
    try:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(info["proc"].pid)], capture_output=True, timeout=5)
    except Exception:
        pass
    return f"Watcher detenido: {info['folder']}"


def _status() -> str:
    lines = ["📊 VS Code Controller Status"]
    if _LIVE_SERVERS:
        lines.append(f"\nServidores activos ({len(_LIVE_SERVERS)}):")
        for k, v in _LIVE_SERVERS.items():
            elapsed = int(time.time() - v["start"])
            lines.append(f"  • :{v['port']} → {v['folder']} ({elapsed}s activo)")
    else:
        lines.append("\nServidores: ninguno")
    if _WATCHERS:
        lines.append(f"\nWatchers activos ({len(_WATCHERS)}):")
        for k, v in _WATCHERS.items():
            elapsed = int(time.time() - v["start"])
            lines.append(f"  • {v['folder']} ({elapsed}s activo)")
    else:
        lines.append("\nWatchers: ninguno")
    return "\n".join(lines)
