"""
platform.py — ERIS Cross-Platform Abstraction Layer.
Detects the OS and provides unified interfaces for Windows and Linux.
100% additive — Windows functionality is preserved, Linux is added.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional

# ── Platform detection ────────────────────────────────────────────────────────

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform == "darwin"

def is_windows() -> bool:
    """Return True if running on Windows."""
    return IS_WINDOWS

def is_linux() -> bool:
    """Return True if running on Linux."""
    return IS_LINUX

def is_macos() -> bool:
    """Return True if running on macOS."""
    return IS_MACOS

def get_platform_name() -> str:
    """Return human-readable platform name."""
    if IS_WINDOWS:
        return "Windows"
    elif IS_LINUX:
        return "Linux"
    elif IS_MACOS:
        return "macOS"
    return "Unknown"

# ── Python executable ─────────────────────────────────────────────────────────

def get_python_executable() -> str:
    """Return the appropriate Python executable for the platform."""
    if IS_WINDOWS:
        return "python.exe"
    return "python3"

def get_python_interpreter() -> str:
    """Return the Python interpreter for subprocess calls."""
    if IS_WINDOWS:
        return "python.exe"
    return "python3"

# ── Browser paths ─────────────────────────────────────────────────────────────

def get_browser_paths() -> List[str]:
    """Return list of possible browser executable paths."""
    if IS_WINDOWS:
        return [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
    elif IS_LINUX:
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/firefox",
            "/usr/bin/firefox-esr",
            "/usr/bin/microsoft-edge",
            "/usr/bin/brave-browser",
            "/usr/bin/vivaldi",
            "/snap/bin/chromium",
            "/snap/bin/firefox",
            "/snap/bin/microsoft-edge",
        ]
        # Filter to existing paths
        return [p for p in paths if Path(p).exists()]
    elif IS_MACOS:
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Firefox.app/Contents/MacOS/firefox",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Safari.app/Contents/MacOS/Safari",
        ]
    return []

def find_browser() -> Optional[str]:
    """Find the first available browser on the system."""
    for path in get_browser_paths():
        if Path(path).exists():
            return path
    # Fallback: search PATH
    browsers = ["google-chrome", "chromium", "firefox", "microsoft-edge", "brave-browser"]
    for browser in browsers:
        found = shutil.which(browser)
        if found:
            return found
    return None

# ── Ollama paths ──────────────────────────────────────────────────────────────

def get_ollama_paths() -> List[Path]:
    """Return list of possible Ollama executable paths."""
    if IS_WINDOWS:
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        return [
            Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe" if local_appdata else Path(),
            Path("C:/Program Files/Ollama/ollama.exe"),
            Path("C:/Ollama/ollama.exe"),
        ]
    elif IS_LINUX:
        return [
            Path("/usr/bin/ollama"),
            Path("/usr/local/bin/ollama"),
            Path.home() / ".local" / "bin" / "ollama",
            Path("/snap/bin/ollama"),
            Path("/opt/ollama/ollama"),
        ]
    elif IS_MACOS:
        return [
            Path("/usr/local/bin/ollama"),
            Path("/opt/homebrew/bin/ollama"),
        ]
    return []

def find_ollama() -> Optional[Path]:
    """Find the Ollama executable on the system."""
    for path in get_ollama_paths():
        if path.exists():
            return path
    # Fallback: search PATH
    found = shutil.which("ollama")
    if found:
        return Path(found)
    return None

# ── Package manager ───────────────────────────────────────────────────────────

def get_package_manager() -> Optional[str]:
    """Return the system package manager for the platform."""
    if IS_WINDOWS:
        # Check winget first, then choco
        if shutil.which("winget"):
            return "winget"
        if shutil.which("choco"):
            return "choco"
        return "winget"  # Default for Windows 10/11
    
    elif IS_LINUX:
        # Check in order of preference
        # Universal first, then distro-specific
        universal = ["flatpak", "snap"]
        distro_specific = ["apt", "dnf", "pacman", "yum", "zypper", "apk"]
        
        for pm in universal + distro_specific:
            if shutil.which(pm):
                return pm
        
        return None
    
    return None

def get_package_manager_info() -> dict:
    """Return detailed package manager info."""
    pm = get_package_manager()
    
    if IS_WINDOWS:
        if pm == "winget":
            return {
                "name": "winget",
                "install_cmd": "winget install --id {package} --silent",
                "uninstall_cmd": "winget uninstall --id {package} --silent",
                "search_cmd": "winget search {package}",
                "list_cmd": "winget list",
            }
        elif pm == "choco":
            return {
                "name": "choco",
                "install_cmd": "choco install {package} -y",
                "uninstall_cmd": "choco uninstall {package} -y",
                "search_cmd": "choco search {package}",
                "list_cmd": "choco list --local-only",
            }
    
    elif IS_LINUX:
        if pm == "apt":
            return {
                "name": "apt",
                "install_cmd": "sudo apt install -y {package}",
                "uninstall_cmd": "sudo apt remove -y {package}",
                "search_cmd": "apt search {package}",
                "list_cmd": "dpkg --list",
                "sudo_required": True,
            }
        elif pm == "dnf":
            return {
                "name": "dnf",
                "install_cmd": "sudo dnf install -y {package}",
                "uninstall_cmd": "sudo dnf remove -y {package}",
                "search_cmd": "dnf search {package}",
                "list_cmd": "dnf list installed",
                "sudo_required": True,
            }
        elif pm == "pacman":
            return {
                "name": "pacman",
                "install_cmd": "sudo pacman -S --noconfirm {package}",
                "uninstall_cmd": "sudo pacman -R --noconfirm {package}",
                "search_cmd": "pacman -Ss {package}",
                "list_cmd": "pacman -Q",
                "sudo_required": True,
            }
        elif pm == "flatpak":
            return {
                "name": "flatpak",
                "install_cmd": "flatpak install -y flathub {package}",
                "uninstall_cmd": "flatpak uninstall -y {package}",
                "search_cmd": "flatpak search {package}",
                "list_cmd": "flatpak list",
                "sudo_required": False,
            }
        elif pm == "snap":
            return {
                "name": "snap",
                "install_cmd": "sudo snap install {package}",
                "uninstall_cmd": "sudo snap remove {package}",
                "search_cmd": "snap search {package}",
                "list_cmd": "snap list",
                "sudo_required": True,
            }
    
    return {"name": pm or "unknown", "install_cmd": "", "uninstall_cmd": "", "search_cmd": "", "list_cmd": ""}

# ── Security scanner ──────────────────────────────────────────────────────────

def get_security_scanner() -> Optional[str]:
    """Return the available security scanner for the platform."""
    if IS_WINDOWS:
        return "defender"
    
    elif IS_LINUX:
        # Check for ClamAV first (most common)
        if shutil.which("clamscan"):
            return "clamav"
        # Check for RKHunter
        if shutil.which("rkhunter"):
            return "rkhunter"
        # Check for chkrootkit
        if shutil.which("chkrootkit"):
            return "chkrootkit"
        return None
    
    return None

def get_security_scanner_info() -> dict:
    """Return detailed security scanner info."""
    scanner = get_security_scanner()
    
    if scanner == "defender":
        return {
            "name": "Windows Defender",
            "available": True,
            "scan_file_cmd": 'MpCmdRun.exe -Scan -ScanType 3 -File "{path}"',
            "scan_folder_cmd": 'MpCmdRun.exe -Scan -ScanType 2 -Path "{path}"',
            "quick_scan_cmd": "MpCmdRun.exe -Scan -ScanType 1",
            "mp_path": r"C:\Program Files\Windows Defender\MpCmdRun.exe",
        }
    
    elif scanner == "clamav":
        return {
            "name": "ClamAV",
            "available": True,
            "scan_file_cmd": 'clamscan "{path}"',
            "scan_folder_cmd": 'clamscan -r "{path}"',
            "quick_scan_cmd": "clamscan --bell -i /home",
            "clamscan_path": shutil.which("clamscan"),
        }
    
    elif scanner == "rkhunter":
        return {
            "name": "RKHunter",
            "available": True,
            "scan_file_cmd": 'rkhunter --check --skip-keypress',
            "scan_folder_cmd": 'rkhunter --check --skip-keypress',
            "quick_scan_cmd": "rkhunter --check --skip-keypress",
            "rkhunter_path": shutil.which("rkhunter"),
        }
    
    return {"name": scanner or "none", "available": False}

# ── Screen capture ────────────────────────────────────────────────────────────

def is_wayland() -> bool:
    """Detect if running under Wayland display server."""
    if not IS_LINUX:
        return False
    return os.environ.get("XDG_SESSION_TYPE") == "wayland"

def is_x11() -> bool:
    """Detect if running under X11 display server."""
    if not IS_LINUX:
        return False
    session_type = os.environ.get("XDG_SESSION_TYPE", "")
    display = os.environ.get("DISPLAY", "")
    return session_type == "x11" or (not session_type and display)

def get_screen_capture_command() -> Optional[str]:
    """Return the appropriate screen capture command for the platform."""
    if IS_WINDOWS:
        return "windows_gdi"  # Uses PIL.ImageGrab
    
    elif IS_LINUX:
        # Check for Wayland first
        if is_wayland():
            if shutil.which("grim"):
                return "grim"
            if shutil.which("gnome-screenshot"):
                return "gnome-screenshot"
        
        # X11 fallbacks
        if shutil.which("scrot"):
            return "scrot"
        if shutil.which("maim"):
            return "maim"
        if shutil.which("gnome-screenshot"):
            return "gnome-screenshot"
        if shutil.which("import"):  # ImageMagick
            return "import"
        
        return None
    
    return None

def get_screen_capture_deps() -> List[str]:
    """Return list of recommended screen capture dependencies."""
    if IS_WINDOWS:
        return []  # PIL.ImageGrab works out of the box
    
    elif IS_LINUX:
        if is_wayland():
            return ["grim", "slurp"]
        else:
            return ["scrot", "maim"]
    
    return []

# ── Shell command ─────────────────────────────────────────────────────────────

def get_shell_command() -> List[str]:
    """Return the appropriate shell for subprocess calls."""
    if IS_WINDOWS:
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command"]
    return ["bash", "-c"]

def get_shell_interpreter() -> str:
    """Return the shell interpreter path."""
    if IS_WINDOWS:
        return "powershell.exe"
    return "/bin/bash"

# ── VBScript interpreter ─────────────────────────────────────────────────────

def get_vbs_interpreter() -> Optional[str]:
    """Return VBScript interpreter or None if not available."""
    if IS_WINDOWS:
        vbs_path = r"C:\Windows\System32\cscript.exe"
        if Path(vbs_path).exists():
            return vbs_path
    return None

# ── MessageBox (Windows only) ─────────────────────────────────────────────────

def show_messagebox(title: str, message: str, icon: str = "info"):
    """Show a message box. Uses Windows API on Windows, prints on Linux."""
    if IS_WINDOWS:
        try:
            import ctypes
            icon_map = {
                "info": 0x40,
                "warning": 0x30,
                "error": 0x10,
                "question": 0x20,
            }
            ctypes.windll.user32.MessageBoxW(
                0, message, title, icon_map.get(icon, 0x40)
            )
        except Exception:
            print(f"[{title}] {message}")
    else:
        print(f"[{title}] {message}")

# ── Subprocess flags ──────────────────────────────────────────────────────────

def get_subprocess_creation_flags() -> int:
    """Return subprocess creation flags for the platform."""
    if IS_WINDOWS:
        try:
            import subprocess
            return getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        except Exception:
            return 0
    return 0

# ── AppUserModelID (Windows only) ─────────────────────────────────────────────

def set_app_user_model_id(app_id: str = "ERIS.Assistant.v2.2.CrossPlatform"):
    """Set AppUserModelID for Windows taskbar grouping. No-op on Linux."""
    if IS_WINDOWS:
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

# ── Desktop file (Linux only) ─────────────────────────────────────────────────

def get_desktop_file_content() -> str:
    """Return .desktop file content for Linux."""
    return """[Desktop Entry]
Name=E.R.I.S
Comment=AI Voice Assistant - Personal AI with voice, vision, and multi-agent system
Exec=/opt/eris/eris
Icon=/opt/eris/assets/ICOERIS.ico
Terminal=false
Type=Application
Categories=Utility;Development;
Keywords=ai;assistant;voice;vision;
"""

# ── System info ───────────────────────────────────────────────────────────────

def get_system_info() -> dict:
    """Return comprehensive system information."""
    info = {
        "platform": get_platform_name(),
        "is_windows": IS_WINDOWS,
        "is_linux": IS_LINUX,
        "is_macos": IS_MACOS,
        "python_executable": get_python_executable(),
        "browser": find_browser(),
        "ollama": str(find_ollama()) if find_ollama() else None,
        "package_manager": get_package_manager(),
        "security_scanner": get_security_scanner(),
        "screen_capture": get_screen_capture_command(),
        "display_server": "wayland" if is_wayland() else ("x11" if is_x11() else "unknown"),
    }
    return info


# ── Safe print (Windows cp1252 compatible) ─────────────────────────────────


def safe_print(msg: str):
    """Print with Windows-safe encoding — strips emoji that break cp1252."""
    try:
        print(msg)
    except UnicodeEncodeError:
        safe = msg.encode("ascii", errors="replace").decode()
        print(safe)
