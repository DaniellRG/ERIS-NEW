"""
app_discovery.py — Application discovery and management for ERIS
Scans for installed apps via:
- Windows: Registry (HKLM/HKCU Uninstall), Start Menu shortcuts, PATH, Get-StartApps
- Linux: .desktop files, package managers
Detects newly installed apps since last scan
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

_SYSTEM = platform.system()
_WIN = _SYSTEM == "Windows"
_LINUX = _SYSTEM == "Linux"
_MAC = _SYSTEM == "Darwin"

_ESTIMATE_APPS_PATH = Path(__file__).resolve().parent.parent / "memory" / "known_apps.json"
_SCAN_HISTORY_PATH = Path(__file__).resolve().parent.parent / "memory" / "app_scan_history.json"


def _get_win_apps_from_registry() -> list[dict]:
    """Scan Windows registry Uninstall keys for installed applications."""
    apps = []
    reg_paths = [
        r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        r"HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        r"HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    ]
    for reg_path in reg_paths:
        try:
            ps_cmd = (
                f"Get-ItemProperty '{reg_path}' -ErrorAction SilentlyContinue "
                f"| Where-Object {{ $_.DisplayName }} "
                f"| Select-Object DisplayName, DisplayVersion, InstallLocation, Publisher "
                f"| ConvertTo-Json -Compress"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout and result.stdout.strip() not in ("", "[]", "{}"):
                data = json.loads(result.stdout)
                if not isinstance(data, list):
                    data = [data]
                for item in data:
                    name = (item.get("DisplayName") or "").strip()
                    if name:
                        apps.append({
                            "name": name,
                            "version": (item.get("DisplayVersion") or "").strip(),
                            "path": (item.get("InstallLocation") or "").strip(),
                            "publisher": (item.get("Publisher") or "").strip(),
                            "source": "registry",
                        })
        except Exception as e:
            print(f"[AppDiscovery] Registry scan error ({reg_path}): {e}")
    return apps


def _get_win_apps_from_startmenu() -> list[dict]:
    """Scan Start Menu for .lnk shortcuts."""
    apps = []
    try:
        start_menu = os.path.join(os.environ.get("APPDATA", ""),
                                  "Microsoft", "Windows", "Start Menu", "Programs")
        if os.path.isdir(start_menu):
            for root, dirs, files in os.walk(start_menu):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        name = os.path.splitext(f)[0]
                        full_path = os.path.join(root, f)
                        apps.append({
                            "name": name,
                            "path": full_path,
                            "source": "start_menu",
                        })
        common_start = os.path.join(os.environ.get("PROGRAMDATA", ""),
                                    "Microsoft", "Windows", "Start Menu", "Programs")
        if os.path.isdir(common_start) and common_start != start_menu:
            for root, dirs, files in os.walk(common_start):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        name = os.path.splitext(f)[0]
                        full_path = os.path.join(root, f)
                        if not any(a["name"] == name for a in apps):
                            apps.append({
                                "name": name,
                                "path": full_path,
                                "source": "start_menu",
                            })
    except Exception as e:
        print(f"[AppDiscovery] Start Menu scan error: {e}")

    system32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
    known_system_apps = [
        "notepad.exe", "calc.exe", "mspaint.exe", "cmd.exe",
        "powershell.exe", "explorer.exe", "taskmgr.exe",
        "control.exe", "regedit.exe", "msconfig.exe",
    ]
    for exe_name in known_system_apps:
        exe_path = os.path.join(system32, exe_name)
        if os.path.exists(exe_path):
            name = os.path.splitext(exe_name)[0].capitalize()
            if not any(a["name"].lower() == name.lower() for a in apps):
                apps.append({
                    "name": name,
                    "path": exe_path,
                    "source": "system",
                })
    return apps


def _get_win_apps_from_path() -> list[dict]:
    """Find executables available in PATH."""
    apps = []
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    seen = set()
    for dir_path in path_dirs:
        if not dir_path or not os.path.isdir(dir_path):
            continue
        try:
            for f in os.listdir(dir_path):
                if f.lower().endswith(".exe") and f.lower() not in seen:
                    seen.add(f.lower())
                    name = os.path.splitext(f)[0]
                    apps.append({
                        "name": name,
                        "path": os.path.join(dir_path, f),
                        "source": "path",
                    })
        except Exception:
            pass
    return apps


def _get_win_apps_from_startapps() -> list[dict]:
    """Use PowerShell Get-StartApps to find all Start Menu registered apps."""
    apps = []
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=15
        )
        if result.stdout and result.stdout.strip() not in ("", "[]", "{}"):
            data = json.loads(result.stdout)
            if not isinstance(data, list):
                data = [data]
            for item in data:
                name = (item.get("Name") or "").strip()
                app_id = (item.get("AppID") or "").strip()
                if name and not any(a["name"] == name for a in apps):
                    apps.append({
                        "name": name,
                        "app_id": app_id,
                        "source": "startapps",
                    })
    except Exception as e:
        print(f"[AppDiscovery] Get-StartApps error: {e}")
    return apps


def _get_linux_apps() -> list[dict]:
    """Discover installed apps on Linux via .desktop files and package managers."""
    apps = []
    desktop_dirs = [
        "/usr/share/applications",
        "/usr/local/share/applications",
        os.path.expanduser("~/.local/share/applications"),
        "/var/lib/flatpak/exports/share/applications",
        os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
    ]
    for dd in desktop_dirs:
        if os.path.isdir(dd):
            try:
                for f in os.listdir(dd):
                    if f.endswith(".desktop"):
                        full = os.path.join(dd, f)
                        try:
                            with open(full, "r", encoding="utf-8") as fh:
                                content = fh.read()
                            name = None
                            exec_path = None
                            for line in content.splitlines():
                                if line.startswith("Name=") and not name:
                                    name = line.split("=", 1)[1].strip()
                                if line.startswith("Exec=") and not exec_path:
                                    exec_path = line.split("=", 1)[1].strip()
                                    exec_path = exec_path.split("%")[0].strip()
                            if name:
                                apps.append({
                                    "name": name,
                                    "path": exec_path or full,
                                    "source": "desktop",
                                })
                        except Exception:
                            pass
            except Exception:
                pass
    return apps


def _get_mac_apps() -> list[dict]:
    """Discover installed apps on macOS via /Applications."""
    apps = []
    app_dirs = ["/Applications", os.path.expanduser("~/Applications")]
    for ad in app_dirs:
        if os.path.isdir(ad):
            try:
                for f in os.listdir(ad):
                    if f.endswith(".app"):
                        name = f.replace(".app", "")
                        apps.append({
                            "name": name,
                            "path": os.path.join(ad, f),
                            "source": "applications",
                        })
            except Exception:
                pass
    return apps


def discover_all_apps(include_path: bool = False) -> list[dict]:
    """Discover ALL installed applications on the system."""
    all_apps = []
    seen_names = set()

    if _WIN:
        sources = [
            ("registry", _get_win_apps_from_registry()),
            ("start_menu", _get_win_apps_from_startmenu()),
            ("startapps", _get_win_apps_from_startapps()),
        ]
        if include_path:
            sources.append(("path", _get_win_apps_from_path()))

    elif _LINUX:
        sources = [("linux", _get_linux_apps())]
    elif _MAC:
        sources = [("mac", _get_mac_apps())]
    else:
        sources = []

    for source_name, app_list in sources:
        for app in app_list:
            name = app["name"]
            if name.lower() not in seen_names:
                seen_names.add(name.lower())
                all_apps.append(app)

    return all_apps


def save_known_apps(apps: list[dict]):
    """Save the list of known apps for change detection."""
    try:
        _ESTIMATE_APPS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(apps),
            "apps": sorted(apps, key=lambda a: a["name"].lower()),
        }
        _ESTIMATE_APPS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[AppDiscovery] Error saving known apps: {e}")


def load_known_apps() -> list[dict]:
    """Load previously saved list of known apps."""
    try:
        if _ESTIMATE_APPS_PATH.exists():
            data = json.loads(_ESTIMATE_APPS_PATH.read_text(encoding="utf-8"))
            return data.get("apps", [])
    except Exception:
        pass
    return []


def detect_new_apps() -> list[dict]:
    """Compare current apps with saved list and return newly detected ones."""
    current = discover_all_apps()
    previous = load_known_apps()
    previous_names = {a["name"].lower() for a in previous}
    new_apps = [a for a in current if a["name"].lower() not in previous_names]
    if new_apps:
        save_known_apps(current)
    return new_apps


def search_apps(query: str, apps: list[dict] = None) -> list[dict]:
    """Search for apps by name, fuzzy matching."""
    if apps is None:
        apps = load_known_apps()
        if not apps:
            apps = discover_all_apps()

    q = query.lower().strip()
    if not q:
        return apps[:50]

    results = []
    for app in apps:
        name = app.get("name", "").lower()
        if q in name:
            results.append(app)

    if not results:
        for app in apps:
            name = app.get("name", "").lower()
            score = 0
            for word in q.split():
                if word in name:
                    score += 1
            if score > 0:
                results.append(app)

    return results[:30]


def get_app_status() -> str:
    """Get a summary of discovered applications."""
    apps = load_known_apps()
    if not apps:
        apps = discover_all_apps()
        save_known_apps(apps)

    categories = {}
    for app in apps:
        source = app.get("source", "unknown")
        categories.setdefault(source, 0)
        categories[source] += 1

    summary = f"Total aplicaciones detectadas: {len(apps)}\n"
    for source, count in sorted(categories.items()):
        summary += f"  {source}: {count}\n"

    popular = [a["name"] for a in apps[:20] if a.get("name")]
    if popular:
        summary += f"\nApps principales:\n  " + ", ".join(popular[:15])
        if len(popular) > 15:
            summary += f" ... y {len(apps) - 15} más"

    return summary


def find_app_path(app_name: str) -> str | None:
    """Find the full path to an application by name."""
    apps = load_known_apps()
    if not apps:
        apps = discover_all_apps()

    q = app_name.lower().strip()
    for app in apps:
        if app.get("name", "").lower() == q:
            return app.get("path") or app.get("app_id")

    for app in apps:
        if q in app.get("name", "").lower():
            return app.get("path") or app.get("app_id")

    exe = shutil.which(app_name)
    if exe:
        return exe
    exe = shutil.which(app_name + ".exe")
    if exe:
        return exe
    return None


def app_discovery(parameters: dict = None, player=None) -> str:
    """Main entry point for App Discovery tool.

    Actions:
      scan — discover all installed apps now
      list — show all known apps (optionally filtered by query)
      search — search apps by name
      detect_new — find newly installed apps since last scan
      status — summary of discovered apps
      find — find path to a specific app
    """
    params = parameters or {}
    action = params.get("action", "status").lower().strip()
    query = params.get("query", "") or params.get("name", "") or params.get("app_name", "")

    if player:
        player.write_log(f"[AppDiscovery] {action}" + (f": {query}" if query else ""))

    if action == "scan":
        apps = discover_all_apps(include_path=True)
        save_known_apps(apps)
        return f"Escaneo completo. {len(apps)} aplicaciones detectadas."

    elif action == "list":
        apps = load_known_apps()
        if not apps:
            apps = discover_all_apps()
            save_known_apps(apps)
        if query:
            apps = search_apps(query, apps)
        count = len(apps)
        names = [a["name"] for a in apps[:50]]
        result = f"Aplicaciones ({count}):\n  " + "\n  ".join(names)
        if count > 50:
            result += f"\n  ... y {count - 50} más"
        return result

    elif action == "search":
        if not query:
            return "Especificá un nombre para buscar."
        apps = load_known_apps()
        if not apps:
            apps = discover_all_apps()
        results = search_apps(query, apps)
        if not results:
            return f"No se encontraron apps con '{query}'."
        return f"Resultados para '{query}' ({len(results)}):\n  " + "\n  ".join(
            f"{a['name']}" + (f" - {a.get('path', '')}" if a.get('path') else "")
            for a in results[:20]
        )

    elif action == "detect_new":
        new = detect_new_apps()
        if not new:
            return "No se detectaron aplicaciones nuevas desde el último escaneo."
        return f"Nuevas aplicaciones detectadas ({len(new)}):\n  " + "\n  ".join(
            a["name"] for a in new[:20]
        )

    elif action == "status":
        return get_app_status()

    elif action == "find":
        if not query:
            return "Especificá el nombre de la app."
        path = find_app_path(query)
        if path:
            return f"App '{query}' encontrada en: {path}"
        return f"App '{query}' no encontrada."

    elif action == "init":
        apps = discover_all_apps()
        save_known_apps(apps)
        return f"Inicializado: {len(apps)} apps detectadas."

    else:
        return (
            "Acciones disponibles:\n"
            "  scan — escanear todas las apps instaladas\n"
            "  list — listar apps conocidas (opcional: query=filtro)\n"
            "  search query=nombre — buscar apps por nombre\n"
            "  detect_new — detectar apps nuevas\n"
            "  status — resumen de apps detectadas\n"
            "  find name=app — encontrar ruta de una app\n"
            "  init — escaneo inicial (se ejecuta automáticamente al iniciar ERIS)"
        )
