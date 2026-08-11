"""
program_manager.py — ERIS Program Manager.
Instala, desinstala, ejecuta y lista programas usando:
  - winget (Windows Package Manager, viene con Windows 11)
  - Chocolatey (si está instalado)
  - Registro de Windows (para desinstalar)
  - PowerShell (para ejecutar y listar)

REGLA DE SEGURIDAD: SIEMPRE pide confirmación antes de instalar/desinstalar.
"""
from __future__ import annotations

import json
import subprocess
import re
from pathlib import Path
from typing import Any

# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_cmd(cmd: list[str], timeout: int = 60) -> str:
    """Run command and return stdout. Cross-platform."""
    try:
        import sys
        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x08000000  # CREATE_NO_WINDOW
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=creationflags,
            encoding="utf-8",
            errors="ignore",
        )
        return result.stdout or ""
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s"
    except Exception as e:
        return f"Error: {e}"

def _run_cmd_details(cmd: list[str], timeout: int = 60) -> tuple[str, str, int]:
    """Run command and return (stdout, stderr, returncode)."""
    try:
        import sys
        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x08000000
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=creationflags, encoding="utf-8", errors="ignore",
        )
        return (result.stdout or "", result.stderr or "", result.returncode)
    except subprocess.TimeoutExpired:
        return ("", f"Timeout after {timeout}s", -1)
    except Exception as e:
        return ("", f"Error: {e}", -1)


def _run_sudo_cmd(cmd: list[str], password: str | None = None, timeout: int = 300) -> str:
    """
    Run a command with sudo.
    If password is given, uses 'echo password | sudo -S cmd'.
    If not, uses 'sudo -n cmd' (non-interactive) to detect if password is needed.
    Returns output on success, or a special marker if password is required.
    """
    import shlex
    cmd_str = " ".join(shlex.quote(c) for c in cmd)

    if password:
        # Password provided — use echo | sudo -S
        full_cmd = f"echo {shlex.quote(password)} | sudo -S {cmd_str}"
        out, err, rc = _run_cmd_details(["bash", "-c", full_cmd], timeout=timeout)
        if rc != 0:
            return f"Error de sudo: {err or out}"
        return out or "Listo."

    # No password — try non-interactive sudo first
    sudo_check = ["sudo", "-n"] + cmd
    out, err, rc = _run_cmd_details(sudo_check, timeout=timeout)
    if rc == 0:
        return out or "Listo."

    # Check if sudo needs a password
    err_lower = (err + out).lower()
    if "password" in err_lower or "contrase" in err_lower or "a password is required" in err_lower:
        return "__SUDO_NEEDS_PASSWORD__"
    return f"Error de sudo: {err or out}"


def _run_ps(script: str, timeout: int = 60) -> str:
    """Run PowerShell script and return output (Windows only)."""
    import sys
    if sys.platform != "win32":
        return "PowerShell not available on this platform"
    cmd = ["powershell", "-NoProfile", "-Command", script]
    return _run_cmd(cmd, timeout)

def _winget_available() -> bool:
    """Check if winget is installed."""
    import sys
    if sys.platform != "win32":
        return False
    try:
        output = _run_cmd(["winget", "--version"], timeout=5)
        return bool(output.strip()) and "error" not in output.lower()
    except Exception:
        return False

def _choco_available() -> bool:
    """Check if Chocolatey is installed."""
    import sys
    if sys.platform != "win32":
        return False
    try:
        output = _run_cmd(["choco", "--version"], timeout=5)
        return bool(output.strip()) and "error" not in output.lower()
    except Exception:
        return False

def _apt_available() -> bool:
    """Check if apt is available (Linux)."""
    import sys
    if sys.platform != "linux":
        return False
    import shutil
    return shutil.which("apt") is not None

def _dnf_available() -> bool:
    """Check if dnf is available (Linux)."""
    import sys
    if sys.platform != "linux":
        return False
    import shutil
    return shutil.which("dnf") is not None

def _pacman_available() -> bool:
    """Check if pacman is available (Linux)."""
    import sys
    if sys.platform != "linux":
        return False
    import shutil
    return shutil.which("pacman") is not None

def _paru_available() -> bool:
    """Check if paru is available (Arch AUR helper)."""
    import sys
    if sys.platform != "linux":
        return False
    import shutil
    return shutil.which("paru") is not None

def _yay_available() -> bool:
    """Check if yay is available (Arch AUR helper)."""
    import sys
    if sys.platform != "linux":
        return False
    import shutil
    return shutil.which("yay") is not None

def _flatpak_available() -> bool:
    """Check if flatpak is available (Linux)."""
    import sys
    if sys.platform != "linux":
        return False
    import shutil
    return shutil.which("flatpak") is not None

def _snap_available() -> bool:
    """Check if snap is available (Linux)."""
    import sys
    if sys.platform != "linux":
        return False
    import shutil
    return shutil.which("snap") is not None

def _get_package_manager() -> str:
    """Return the best available package manager for the platform."""
    import sys
    if sys.platform == "win32":
        if _winget_available():
            return "winget"
        if _choco_available():
            return "choco"
        return "none"
    elif sys.platform == "linux":
        if _paru_available():
            return "paru"
        if _yay_available():
            return "yay"
        if _pacman_available():
            return "pacman"
        if _flatpak_available():
            return "flatpak"
        if _snap_available():
            return "snap"
        if _apt_available():
            return "apt"
        if _dnf_available():
            return "dnf"
        return "none"
    return "none"

# ── List installed programs ──────────────────────────────────────────────────

def _list_winget() -> list[dict]:
    """List programs via winget."""
    results = []
    try:
        output = _run_cmd(["winget", "list", "--accept-source-agreements"], timeout=30)
        lines = output.strip().split("\n")
        # Skip header lines
        for line in lines[3:]:
            parts = line.split()
            if len(parts) >= 3:
                name = " ".join(parts[:-2])
                version = parts[-2]
                source = parts[-1]
                results.append({
                    "name": name,
                    "version": version,
                    "source": source,
                    "id": name.lower().replace(" ", "-"),
                })
    except Exception:
        pass
    return results

def _list_registry() -> list[dict]:
    """List programs via Windows Registry."""
    results = []
    try:
        reg_paths = [
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        for reg_path in reg_paths:
            output = _run_cmd(["reg", "query", reg_path], timeout=10)
            for line in output.strip().split("\n"):
                if "Uninstall" in line and "\\" in line:
                    key = line.strip()
                    name_out = _run_cmd(["reg", "query", key, "/v", "DisplayName"], timeout=5)
                    version_out = _run_cmd(["reg", "query", key, "/v", "DisplayVersion"], timeout=5)
                    uninstall_out = _run_cmd(["reg", "query", key, "/v", "UninstallString"], timeout=5)
                    
                    name = ""
                    version = ""
                    uninstall = ""
                    
                    for out in [name_out, version_out, uninstall_out]:
                        match = re.search(r'REG_SZ\s+(.+)', out)
                        if match:
                            val = match.group(1).strip()
                            if "DisplayName" in out:
                                name = val
                            elif "DisplayVersion" in out:
                                version = val
                            elif "UninstallString" in out:
                                uninstall = val
                    
                    if name:
                        results.append({
                            "name": name,
                            "version": version,
                            "source": "Registry",
                            "id": name.lower().replace(" ", "-"),
                            "uninstall_string": uninstall,
                        })
    except Exception:
        pass
    return results

# ── List installed programs (Linux) ──────────────────────────────────────────

def _list_apt() -> list[dict]:
    """List programs via apt (Debian/Ubuntu)."""
    results = []
    try:
        output = _run_cmd(["dpkg", "--list"], timeout=30)
        for line in output.strip().split("\n"):
            if line.startswith("ii "):
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[1]
                    version = parts[2]
                    results.append({
                        "name": name,
                        "version": version,
                        "source": "apt",
                        "id": name,
                    })
    except Exception:
        pass
    return results

def _list_dnf() -> list[dict]:
    """List programs via dnf (Fedora/RHEL)."""
    results = []
    try:
        output = _run_cmd(["dnf", "list", "installed"], timeout=30)
        for line in output.strip().split("\n"):
            if "@" in line or ".rpm" in line:
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0].split(".")[0]
                    version = parts[1] if len(parts) > 1 else ""
                    results.append({
                        "name": name,
                        "version": version,
                        "source": "dnf",
                        "id": name,
                    })
    except Exception:
        pass
    return results

def _list_pacman() -> list[dict]:
    """List programs via pacman (Arch)."""
    results = []
    try:
        output = _run_cmd(["pacman", "-Q"], timeout=30)
        for line in output.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                version = parts[1]
                results.append({
                    "name": name,
                    "version": version,
                    "source": "pacman",
                    "id": name,
                })
    except Exception:
        pass
    return results

def _list_flatpak() -> list[dict]:
    """List programs via flatpak."""
    results = []
    try:
        output = _run_cmd(["flatpak", "list", "--app"], timeout=30)
        for line in output.strip().split("\n"):
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    name = parts[1]
                    app_id = parts[0]
                    results.append({
                        "name": name,
                        "version": "",
                        "source": "flatpak",
                        "id": app_id,
                    })
    except Exception:
        pass
    return results

def _list_snap() -> list[dict]:
    """List programs via snap."""
    results = []
    try:
        output = _run_cmd(["snap", "list"], timeout=30)
        lines = output.strip().split("\n")
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 3:
                name = parts[0]
                version = parts[2]
                results.append({
                    "name": name,
                    "version": version,
                    "source": "snap",
                    "id": name,
                })
    except Exception:
        pass
    return results

# ── Install programs (Linux) ─────────────────────────────────────────────────

def _install_apt(name: str, silent: bool = True, password: str | None = None) -> str:
    """Install program via apt (Debian/Ubuntu)."""
    cmd = ["apt", "install", "-y", name]
    result = _run_sudo_cmd(cmd, password=password)
    if result == "__SUDO_NEEDS_PASSWORD__":
        return "⚠️ Para instalar necesito la contraseña sudo. Decímela y la uso para continuar."
    return f"Resultado de instalación (apt):\n{result}"

def _install_dnf(name: str, silent: bool = True, password: str | None = None) -> str:
    """Install program via dnf (Fedora/RHEL)."""
    cmd = ["dnf", "install", "-y", name]
    result = _run_sudo_cmd(cmd, password=password)
    if result == "__SUDO_NEEDS_PASSWORD__":
        return "⚠️ Para instalar necesito la contraseña sudo. Decímela y la uso para continuar."
    return f"Resultado de instalación (dnf):\n{result}"

def _install_paru(name: str, silent: bool = True, password: str | None = None) -> str:
    """Install program via paru (Arch AUR)."""
    cmd = ["paru", "-S", "--noconfirm", name]
    result = _run_sudo_cmd(cmd, password=password)
    if result == "__SUDO_NEEDS_PASSWORD__":
        return "⚠️ Para instalar necesito la contraseña sudo. Decímela y la uso para continuar."
    return f"Resultado de instalación (paru):\n{result}"

def _install_yay(name: str, silent: bool = True, password: str | None = None) -> str:
    """Install program via yay (Arch AUR)."""
    cmd = ["yay", "-S", "--noconfirm", name]
    result = _run_sudo_cmd(cmd, password=password)
    if result == "__SUDO_NEEDS_PASSWORD__":
        return "⚠️ Para instalar necesito la contraseña sudo. Decímela y la uso para continuar."
    return f"Resultado de instalación (yay):\n{result}"

def _install_pacman(name: str, silent: bool = True, password: str | None = None) -> str:
    """Install program via pacman (Arch)."""
    cmd = ["pacman", "-S", "--noconfirm", name]
    result = _run_sudo_cmd(cmd, password=password)
    if result == "__SUDO_NEEDS_PASSWORD__":
        return "⚠️ Para instalar necesito la contraseña sudo. Decímela y la uso para continuar."
    return f"Resultado de instalación (pacman):\n{result}"

def _install_flatpak(name: str, silent: bool = True, password: str | None = None) -> str:
    """Install program via flatpak."""
    cmd = ["flatpak", "install", "-y", "flathub", name]
    return _run_cmd(cmd, timeout=300)

def _install_snap(name: str, silent: bool = True, password: str | None = None) -> str:
    """Install program via snap."""
    cmd = ["snap", "install", name]
    result = _run_sudo_cmd(cmd, password=password)
    if result == "__SUDO_NEEDS_PASSWORD__":
        return "⚠️ Para instalar necesito la contraseña sudo. Decímela y la uso para continuar."
    return f"Resultado de instalación (snap):\n{result}"

# ── Uninstall programs (Linux) ───────────────────────────────────────────────

def _uninstall_apt(name: str, silent: bool = True, password: str | None = None) -> str:
    """Uninstall program via apt."""
    cmd = ["apt", "remove", "-y", name]
    result = _run_sudo_cmd(cmd, password=password)
    if result == "__SUDO_NEEDS_PASSWORD__":
        return "⚠️ Para desinstalar necesito la contraseña sudo. Decímela y la uso para continuar."
    return f"Resultado de desinstalación (apt):\n{result}"

def _uninstall_dnf(name: str, silent: bool = True, password: str | None = None) -> str:
    """Uninstall program via dnf."""
    cmd = ["dnf", "remove", "-y", name]
    result = _run_sudo_cmd(cmd, password=password)
    if result == "__SUDO_NEEDS_PASSWORD__":
        return "⚠️ Para desinstalar necesito la contraseña sudo. Decímela y la uso para continuar."
    return f"Resultado de desinstalación (dnf):\n{result}"

def _uninstall_pacman(name: str, silent: bool = True, password: str | None = None) -> str:
    """Uninstall program via pacman."""
    cmd = ["pacman", "-R", "--noconfirm", name]
    result = _run_sudo_cmd(cmd, password=password)
    if result == "__SUDO_NEEDS_PASSWORD__":
        return "⚠️ Para desinstalar necesito la contraseña sudo. Decímela y la uso para continuar."
    return f"Resultado de desinstalación (pacman):\n{result}"

def _uninstall_flatpak(name: str, silent: bool = True, password: str | None = None) -> str:
    """Uninstall program via flatpak."""
    cmd = ["flatpak", "uninstall", "-y", name]
    return _run_cmd(cmd, timeout=300)

def _uninstall_snap(name: str, silent: bool = True, password: str | None = None) -> str:
    """Uninstall program via snap."""
    cmd = ["snap", "remove", name]
    result = _run_sudo_cmd(cmd, password=password)
    if result == "__SUDO_NEEDS_PASSWORD__":
        return "⚠️ Para desinstalar necesito la contraseña sudo. Decímela y la uso para continuar."
    return f"Resultado de desinstalación (snap):\n{result}"

# ── Install programs ─────────────────────────────────────────────────────────

def _resolve_winget_id(name: str) -> dict | None:
    """Busca en winget y devuelve la mejor coincidencia con su ID exacto."""
    cands = _search_winget(name)
    if not cands:
        return None
    nl = name.strip().lower()

    def score(c: dict) -> int:
        s = 0
        cid, cname = c["id"].lower(), c["name"].lower()
        if cid == nl or cname == nl:
            s += 100
        if nl in cid or nl in cname:
            s += 40
        if cname.startswith(nl):
            s += 10
        m = c.get("match", "").lower()
        if m.startswith("moniker:"):
            moniker = m.split("moniker:", 1)[1].strip()
            if moniker == nl:
                s += 60
            elif nl in moniker:
                s += 25
        return s

    winget_cands = [c for c in cands if c.get("source", "").lower() == "winget"]
    pool = winget_cands or cands
    return max(pool, key=score)


def _install_winget(name: str, silent: bool = True) -> str:
    """Instala un programa via winget resolviendo primero su ID exacto.

    Paso a paso: buscar → resolver ID → descargar/instalar → reportar.
    """
    resolved = _resolve_winget_id(name)
    pid = resolved["id"] if resolved else name
    label = f"{resolved['name']} ({pid}) v{resolved.get('version', '?')}" if resolved else name

    steps = [f"1. Buscando '{name}' en winget... OK → {label}"]

    cmd = ["winget", "install", "--id", pid,
           "--accept-source-agreements", "--accept-package-agreements",
           "--disable-interactivity"]
    if silent:
        cmd.append("--silent")

    steps.append(f"2. Descargando e instalando {pid} (puede tardar)...")
    out, err, rc = _run_cmd_details(cmd, timeout=900)
    if rc == 0 or "successfully" in out.lower() or "instalado" in out.lower():
        steps.append(f"3. ✅ Instalación completada ({label}).")
    else:
        detail = (out + "\n" + err).strip()
        steps.append(f"3. ❌ La instalación falló (código {rc}).\nSalida de winget:\n{detail[:1500]}")
        steps.append("   → Verificá el ID exacto con program_manager(action='search', name=...) o instalá manualmente.")
    return "\n".join(steps)

def _install_choco(name: str, silent: bool = True) -> str:
    """Install program via Chocolatey."""
    cmd = ["choco", "install", name, "-y"]
    if silent:
        cmd.append("--silent")
    output = _run_cmd(cmd, timeout=300)
    return output

def _install_file(path: str, silent: bool = True) -> str:
    """Install from local file (.exe, .msi)."""
    p = Path(path)
    if not p.exists():
        return f"Archivo no encontrado: {path}"
    
    ext = p.suffix.lower()
    if ext == ".msi":
        cmd = ["msiexec", "/i", str(p), "/qn"] if silent else ["msiexec", "/i", str(p)]
    elif ext == ".exe":
        cmd = [str(p)]
        if silent:
            cmd.extend(["/S", "/silent", "/quiet", "/VERYSILENT"])
    else:
        return f"Formato no soportado: {ext}. Use .exe o .msi"
    
    output = _run_cmd(cmd, timeout=600)
    return output

# ── Download programs ────────────────────────────────────────────────────────

def _download_winget(name: str, dest_dir: str = "") -> str:
    """Descarga un programa via winget SIN instalarlo (instalador en disco)."""
    import sys
    if sys.platform != "win32":
        return "La descarga via winget solo está disponible en Windows."
    resolved = _resolve_winget_id(name)
    pid = resolved["id"] if resolved else name
    label = f"{resolved['name']} ({pid})" if resolved else name

    dest = dest_dir.strip() or str(Path.home() / "Downloads" / "ERIS_downloads")
    try:
        Path(dest).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return f"No pude crear la carpeta de descargas: {e}"

    steps = [f"1. Buscando '{name}' en winget... OK → {label}",
             f"2. Descargando instalador de {pid} en: {dest} (puede tardar)..."]
    cmd = ["winget", "download", "--id", pid, "-d", dest,
           "--accept-source-agreements", "--accept-package-agreements",
           "--disable-interactivity"]
    out, err, rc = _run_cmd_details(cmd, timeout=900)
    if rc == 0 or "successfully" in out.lower():
        files = [f.name for f in Path(dest).iterdir() if f.is_file()]
        steps.append(f"3. ✅ Instalador descargado en {dest}: {', '.join(files)[:300]}")
    else:
        steps.append(f"3. ❌ La descarga falló (código {rc}).\nSalida de winget:\n{(out + err).strip()[:1200]}")
    return "\n".join(steps)

# ── Uninstall programs ───────────────────────────────────────────────────────
def _uninstall_winget(name: str) -> str:
    """Uninstall program via winget."""
    cmd = ["winget", "uninstall", "--name", name, "--silent", "--accept-source-agreements"]
    output = _run_cmd_details(cmd, timeout=300)
    out, err, rc = output
    if rc == 0 or "successfully" in out.lower() or "desinstalado" in out.lower():
        return out
    resolved = _resolve_winget_id(name)
    if resolved:
        cmd2 = ["winget", "uninstall", "--id", resolved["id"], "--silent",
                "--accept-source-agreements", "--accept-package-agreements"]
        out2, err2, rc2 = _run_cmd_details(cmd2, timeout=300)
        if rc2 == 0 or "successfully" in out2.lower():
            return out2
        return f"Intento fallido. Salida: {(out + err + out2 + err2)[:800]}"
    return out or f"No se encontró '{name}' para desinstalar."

def _uninstall_registry(name: str, uninstall_string: str = "") -> str:
    """Uninstall via registry uninstall string."""
    if uninstall_string:
        # Clean up the uninstall string
        cmd = uninstall_string.strip()
        if cmd.startswith("MsiExec"):
            cmd = cmd.replace("/I", "/X").replace("/i", "/X") + " /qn"
        try:
            output = _run_cmd(["cmd", "/c", cmd], timeout=300)
            return output
        except Exception as e:
            return f"Error ejecutando uninstall: {e}"
    return f"No se encontró uninstall string para '{name}'"

# ── Run programs ─────────────────────────────────────────────────────────────

def _run_program(name_or_path: str, args: str = "") -> str:
    """Run a program by name or path. Cross-platform."""
    import sys
    import shutil
    
    p = Path(name_or_path)
    if p.exists() and p.is_file():
        cmd = [str(p)]
        if args:
            cmd.extend(args.split())
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = 0x08000000  # CREATE_NO_WINDOW
            subprocess.Popen(cmd, creationflags=creationflags)
            return f"✅ Programa ejecutado: {p.name}"
        except Exception as e:
            return f"Error ejecutando: {e}"
    else:
        # Try to find in PATH
        try:
            if sys.platform == "win32":
                output = _run_cmd(["where", name_or_path], timeout=5)
            else:
                output = _run_cmd(["which", name_or_path], timeout=5)
            if output.strip():
                path = output.strip().split("\n")[0]
                cmd = [path]
                if args:
                    cmd.extend(args.split())
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW)
                return f"✅ Programa ejecutado: {name_or_path} ({path})"
            return f"Programa no encontrado: {name_or_path}"
        except Exception as e:
            return f"Error buscando programa: {e}"

# ── Search programs ──────────────────────────────────────────────────────────

def _search_winget(query: str) -> list[dict]:
    """Search for programs in winget repository, parsing columns by header."""
    results = []
    try:
        output = _run_cmd(["winget", "search", query, "--accept-source-agreements"], timeout=30)
        results = _parse_winget_table(output)
    except Exception:
        pass
    return results

def _parse_winget_table(output: str) -> list[dict]:
    """Parsea la tabla de winget (search/list) usando la fila de cabecera.

    La salida es una tabla con columnas variables: Name, Id, Version,
    Match (solo en search) y Source. Encuentra la cabecera y corta cada
    fila por las posiciones reales de las columnas.
    """
    lines = [l for l in output.splitlines() if l.strip()]
    header_idx = None
    for i, l in enumerate(lines):
        if "Name" in l and "Id" in l and "Version" in l and "Source" in l:
            header_idx = i
            break
    if header_idx is None:
        return []

    header = lines[header_idx]
    has_match = "Match" in header
    bounds = [0]
    for token in ("Id", "Version", "Match", "Source"):
        idx = header.find(token)
        if idx > 0:
            bounds.append(idx)
    bounds = sorted(set(bounds))

    results = []
    for l in lines[header_idx + 1:]:
        stripped = l.strip()
        if not stripped or set(stripped) <= {"-", " "}:
            continue
        cells = []
        for j, b in enumerate(bounds):
            end = bounds[j + 1] if j + 1 < len(bounds) else len(l)
            cells.append(l[b:end].strip())
        if len(cells) < 2 or not cells[1]:
            continue
        results.append({
            "name": cells[0],
            "id": cells[1],
            "version": cells[2] if len(cells) > 2 else "",
            "match": cells[3] if has_match and len(cells) > 3 else "",
            "source": cells[-1],
        })
    return results

def _search_pacman(query: str) -> list[dict]:
    """Search for packages in Arch official repos via pacman."""
    results = []
    if not _pacman_available():
        return results
    try:
        output = _run_cmd(["pacman", "-Ss", query], timeout=30)
        for line in output.strip().split("\n"):
            if not line or line.startswith(" "):
                continue
            parts = line.split()
            if len(parts) >= 2:
                repo_pkg = parts[0]
                version = parts[1].strip("(").strip(")")
                if "/" in repo_pkg:
                    repo, pkg_name = repo_pkg.split("/", 1)
                else:
                    pkg_name = repo_pkg
                    repo = "?"
                desc = " ".join(parts[2:]) if len(parts) > 2 else ""
                results.append({
                    "name": pkg_name,
                    "version": version,
                    "source": f"pacman/{repo}",
                    "id": pkg_name,
                    "description": desc,
                })
    except Exception:
        pass
    return results

def _search_aur(query: str) -> list[dict]:
    """Search for packages in AUR via paru or yay."""
    results = []
    helper = None
    if _paru_available():
        helper = "paru"
    elif _yay_available():
        helper = "yay"
    if not helper:
        return results
    try:
        output = _run_cmd([helper, "-Ss", query], timeout=30)
        for line in output.strip().split("\n"):
            if not line or line.startswith(" "):
                continue
            parts = line.split()
            if len(parts) >= 2:
                repo_pkg = parts[0]
                version = parts[1].strip("(").strip(")")
                if "/" in repo_pkg:
                    repo, pkg_name = repo_pkg.split("/", 1)
                else:
                    pkg_name = repo_pkg
                    repo = "?"
                desc = " ".join(parts[2:]) if len(parts) > 2 else ""
                results.append({
                    "name": pkg_name,
                    "version": version,
                    "source": f"{helper}/{repo}",
                    "id": pkg_name,
                    "description": desc,
                })
    except Exception:
        pass
    return results

def _search_flatpak(query: str) -> list[dict]:
    """Search for Flatpak applications."""
    results = []
    if not _flatpak_available():
        return results
    try:
        output = _run_cmd(["flatpak", "search", query], timeout=30)
        for line in output.strip().split("\n"):
            if not line or line.startswith("Name"):
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                results.append({
                    "name": parts[0].strip(),
                    "version": parts[1].strip() if len(parts) > 1 else "?",
                    "source": "flatpak",
                    "id": parts[2].strip() if len(parts) > 2 else parts[0].strip(),
                    "description": parts[-1].strip() if len(parts) > 3 else "",
                })
            else:
                p = line.split()
                if len(p) >= 2:
                    results.append({
                        "name": p[0],
                        "version": p[1] if len(p) > 1 else "?",
                        "source": "flatpak",
                        "id": p[0],
                        "description": " ".join(p[2:]) if len(p) > 2 else "",
                    })
    except Exception:
        pass
    return results

def _search_apt(query: str) -> list[dict]:
    """Search for packages in apt repositories."""
    results = []
    if not _apt_available():
        return results
    try:
        output = _run_cmd(["apt-cache", "search", query], timeout=30)
        for line in output.strip().split("\n"):
            if not line:
                continue
            if " - " in line:
                pkg_name, desc = line.split(" - ", 1)
            else:
                pkg_name = line.split()[0] if line.split() else line
                desc = ""
            results.append({
                "name": pkg_name.strip(),
                "version": "?",
                "source": "apt",
                "id": pkg_name.strip(),
                "description": desc.strip(),
            })
    except Exception:
        pass
    return results

def _search_dnf(query: str) -> list[dict]:
    """Search for packages in dnf repositories."""
    results = []
    if not _dnf_available():
        return results
    try:
        output = _run_cmd(["dnf", "search", query], timeout=30)
        for line in output.strip().split("\n"):
            if not line or "=" in line or ":" in line:
                continue
            if ".x86_64" in line or ".noarch" in line or ".src" in line:
                parts = line.split()
                if len(parts) >= 1:
                    pkg_name = parts[0].split(".")[0]
                    results.append({
                        "name": pkg_name,
                        "version": parts[-1] if len(parts) > 2 else "?",
                        "source": "dnf",
                        "id": pkg_name,
                        "description": " ".join(parts[1:-2]) if len(parts) > 3 else "",
                    })
    except Exception:
        pass
    return results

def _search_snap(query: str) -> list[dict]:
    """Search for Snap packages."""
    results = []
    if not _snap_available():
        return results
    try:
        output = _run_cmd(["snap", "find", query], timeout=30)
        for line in output.strip().split("\n"):
            if not line or line.startswith("Name") or "Name " in line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                results.append({
                    "name": parts[0],
                    "version": parts[1] if len(parts) > 1 else "?",
                    "source": "snap",
                    "id": parts[0],
                    "description": " ".join(parts[2:]) if len(parts) > 2 else "",
                })
    except Exception:
        pass
    return results

# ── Smart Install ────────────────────────────────────────────────────────────

def verify_installation(name: str) -> str:
    """Verify if a program is installed. Checks PATH and package managers."""
    import shutil
    import sys

    # Check if binary exists in PATH
    if shutil.which(name):
        path = shutil.which(name)
        return f"✅ '{name}' está instalado en: {path}"

    # Check common binary names derived from the package name
    for bin_name in [name, name.lower(), name.replace("-", ""), name.replace("_", "")]:
        if shutil.which(bin_name):
            return f"✅ '{name}' está instalado en: {shutil.which(bin_name)}"

    # Check via package managers on Linux
    if sys.platform == "linux":
        pm = _get_package_manager()
        if pm in ("paru", "yay", "pacman"):
            out = _run_cmd(["pacman", "-Q", name], timeout=10)
            if out and "error" not in out.lower():
                return f"✅ '{name}' está instalado (pacman):\n{out.strip()}"
            out = _run_cmd(["pacman", "-Q", name.lower()], timeout=10)
            if out and "error" not in out.lower():
                return f"✅ '{name}' está instalado (pacman):\n{out.strip()}"
        elif pm == "apt":
            out = _run_cmd(["dpkg", "-l", name], timeout=10)
            if out and "ii " in out:
                return f"✅ '{name}' está instalado (apt)."
        elif pm == "dnf":
            out = _run_cmd(["rpm", "-q", name], timeout=10)
            if out and "not installed" not in out.lower():
                return f"✅ '{name}' está instalado (rpm)."
        if _flatpak_available():
            out = _run_cmd(["flatpak", "list", "--app"], timeout=15)
            if name.lower() in out.lower():
                return f"✅ '{name}' está instalado como Flatpak."
        if _snap_available():
            out = _run_cmd(["snap", "list"], timeout=10)
            if name.lower() in out.lower():
                return f"✅ '{name}' está instalado como Snap."

    # Windows: verificar via winget y Registro
    if sys.platform == "win32" and _winget_available():
        resolved = _resolve_winget_id(name)
        if resolved:
            out, err, rc = _run_cmd_details(
                ["winget", "list", "--id", resolved["id"], "--accept-source-agreements"], timeout=30)
            if rc == 0 and resolved["id"].lower() in (out + err).lower():
                return (f"✅ '{name}' está instalado: {resolved['name']} "
                        f"({resolved['id']}) v{resolved.get('version', '?')}.")
        out = _run_cmd(["winget", "list", "--accept-source-agreements"], timeout=30)
        for line in out.splitlines():
            if name.lower() in line.lower() and "id" not in line.lower().split()[:1]:
                return f"✅ '{name}' está instalado (winget): {line.strip()}"
        try:
            reg = _list_registry()
            for p in reg:
                if name.lower() in p["name"].lower():
                    return f"✅ '{name}' está instalado (Registro): {p['name']} v{p.get('version', '?')}"
        except Exception:
            pass

    return f"❌ No se pudo verificar que '{name}' esté instalado."


def suggest_alternatives(query: str) -> list[dict]:
    """Suggest alternative packages by searching across all available sources."""
    import sys
    all_results = []

    if sys.platform == "linux":
        all_results.extend(_search_pacman(query))
        all_results.extend(_search_aur(query))
        all_results.extend(_search_flatpak(query))
        all_results.extend(_search_snap(query))
    elif sys.platform == "win32":
        all_results.extend(_search_winget(query))

    return all_results


def smart_install(name: str, silent: bool = True, password: str | None = None) -> str:
    """
    Smart install: try primary package manager, then fall back to AUR/Flatpak/Snap.
    If the exact package isn't found, suggests alternatives.
    """
    import sys

    if sys.platform == "win32":
        pm = _get_package_manager()
        if pm == "winget":
            return _install_winget(name, silent=silent)
        elif pm == "choco":
            return _install_choco(name, silent=silent)
        return "Ni winget ni Chocolatey están disponibles."

    # Linux
    pm = _get_package_manager()
    installers = []

    if pm in ("paru", "yay"):
        helper = "paru" if pm == "paru" else "yay"
        installers.append(("AUR", lambda: _install_paru(name, silent, password)))
    elif pm == "pacman":
        installers.append(("pacman", lambda: _install_pacman(name, silent, password)))
    elif pm == "apt":
        installers.append(("apt", lambda: _install_apt(name, silent, password)))
    elif pm == "dnf":
        installers.append(("dnf", lambda: _install_dnf(name, silent, password)))

    if _flatpak_available():
        installers.append(("flatpak", lambda: _install_flatpak(name, silent, password)))
    if _snap_available():
        installers.append(("snap", lambda: _install_snap(name, silent, password)))

    if not installers:
        return "No hay ningún gestor de paquetes disponible."

    results = []
    for source_name, install_fn in installers:
        if "AUR" in source_name or source_name in ("pacman", "paru", "yay"):
            try:
                out = _run_cmd(["pacman", "-Si", name], timeout=10)
                if "error" not in out.lower() and out.strip():
                    result = install_fn()
                    results.append(f"[{source_name}] {result}")
                    if "✅" in result or "correctamente" in result:
                        return f"✅ '{name}' instalado via {source_name}.\n{result}"
                    continue
            except Exception:
                pass
            try:
                out = _run_cmd(["pacman", "-Si", name.lower()], timeout=10)
                if "error" not in out.lower() and out.strip():
                    result = install_fn()
                    results.append(f"[{source_name}] {result}")
                    if "✅" in result or "correctamente" in result:
                        return f"✅ '{name}' instalado via {source_name}.\n{result}"
            except Exception:
                pass

        if source_name == "flatpak":
            try:
                out = _run_cmd(["flatpak", "search", name], timeout=15)
                if name.lower() in out.lower():
                    result = install_fn()
                    results.append(f"[{source_name}] {result}")
                    if "✅" in result or "correctamente" in result:
                        return f"✅ '{name}' instalado via {source_name}.\n{result}"
            except Exception:
                pass

        if source_name == "snap":
            try:
                out = _run_cmd(["snap", "find", name], timeout=15)
                if name.lower() in out.lower():
                    result = install_fn()
                    results.append(f"[{source_name}] {result}")
                    if "✅" in result or "correctamente" in result:
                        return f"✅ '{name}' instalado via {source_name}.\n{result}"
            except Exception:
                pass

    # Try installing directly with the primary package manager
    for source_name, install_fn in installers:
        if source_name not in ("AUR", "pacman", "yay", "paru"):
            continue
        result = install_fn()
        results.append(f"[{source_name}] {result}")
        if "✅" in result or "correctamente" in result:
            return f"✅ '{name}' instalado via {source_name}.\n{result}"

    # If all failed, search for alternatives
    alternatives = suggest_alternatives(name)
    if alternatives:
        alt_lines = [f"  • {a['name']} ({a.get('source', '?')}) - {a.get('description', '')[:80]}" for a in alternatives[:10]]
        return (
            f"No se pudo instalar '{name}'.\n"
            f"Resultados:\n" + "\n".join(results) + "\n\n"
            f"📋 Alternativas encontradas:\n" + "\n".join(alt_lines)
        )

    return (
        f"No se pudo instalar '{name}'.\n"
        f"Resultados:\n" + "\n".join(results)
    )


# ── Tool function ─────────────────────────────────────────────────────────────

def program_manager(parameters: dict, player=None, **kwargs) -> str:
    """
    Gestiona programas: instalar, desinstalar, ejecutar, listar, buscar.
    
    parameters:
        action: 'install' | 'uninstall' | 'run' | 'list' | 'search' | 'update' | 'verify'
        name: nombre del programa
        path: ruta del instalador local
        silent: instalación silenciosa (default: True)
        args: argumentos extra
        confirm: confirmación del usuario (obligatorio para install/uninstall)
    """
    params = parameters or {}
    action = params.get("action", "list").lower()
    name = params.get("name", "")
    path = params.get("path", "")
    silent = params.get("silent", True)
    args = params.get("args", "")
    confirm = params.get("confirm", False)
    password = params.get("password", None)
    
    if player:
        player.write_log(f"📦 Program Manager: {action} {name or path}")
    
    # ─ LIST ──────────────────────────────────────────────────────────────────
    if action in ("list", "listar", "installed"):
        import sys
        programs = []
        
        if sys.platform == "win32":
            if _winget_available():
                programs = _list_winget()
            if not programs:
                programs = _list_registry()
        elif sys.platform == "linux":
            pm = _get_package_manager()
            if pm in ("paru", "yay", "pacman"):
                programs = _list_pacman()
            elif pm == "apt":
                programs = _list_apt()
            elif pm == "dnf":
                programs = _list_dnf()
            elif pm == "flatpak":
                programs = _list_flatpak()
            elif pm == "snap":
                programs = _list_snap()
        
        if not programs:
            return "No se pudieron listar los programas instalados."
        
        lines = [f"📦 Programas instalados ({len(programs)}):"]
        for p in programs[:50]:
            lines.append(f"  • {p['name']} v{p.get('version', '?')} [{p.get('source', '?')}]")
        if len(programs) > 50:
            lines.append(f"  ... y {len(programs) - 50} más")
        return "\n".join(lines)
    
    # ── SEARCH ────────────────────────────────────────────────────────────────
    elif action in ("search", "buscar"):
        if not name:
            return "Especificá el nombre del programa a buscar."
        
        import sys
        results = []
        
        if sys.platform == "win32":
            if _winget_available():
                results = _search_winget(name)
        elif sys.platform == "linux":
            results = suggest_alternatives(name)
        
        if not results:
            return f"No se encontraron programas con '{name}'."
        
        sources = set(r.get('source', '?') for r in results)
        lines = [f"🔍 Resultados para '{name}' ({len(results)} de {', '.join(sorted(sources))}):"]
        for r in results[:20]:
            desc = r.get('description', '')
            desc_str = f" - {desc[:80]}" if desc else ""
            lines.append(f"  • {r['name']} v{r.get('version', '?')} [ID: {r.get('id', '?')}] [{r.get('source', '?')}]{desc_str}")
        lines.append("")
        lines.append("Para instalar: program_manager(action='install', name='NOMBRE_DEL_PROGRAMA', password='...')")
        return "\n".join(lines)
    
    # ── DOWNLOAD ──────────────────────────────────────────────────────────────
    elif action in ("download", "descargar"):
        import sys
        if sys.platform != "win32":
            return "La descarga via winget solo está disponible en Windows."
        if not name:
            return "Especificá el nombre del programa a descargar."
        return _download_winget(name, path)
    
    # ── INSTALL ───────────────────────────────────────────────────────────────
    elif action in ("install", "instalar"):
        import sys
        if not name and not path:
            return "Especificá el nombre del programa o la ruta del instalador."
        
        if path:
            # Local file install (Windows only)
            if sys.platform == "win32":
                p = Path(path)
                if not confirm:
                    return (
                        f"⚠️ Voy a instalar desde: {p.name}\n"
                        f"   Tamaño: {_format_size(p.stat().st_size) if p.exists() else 'N/A'}\n"
                        f"   ¿Confirmás la instalación? Respondé 'sí, instalá' para continuar."
                    )
                return _install_file(path, silent=silent)
            else:
                return "La instalación desde archivo local solo está disponible en Windows."
        
        # Cross-platform install
        pm = _get_package_manager()

        # Mostrar el ID exacto que se instalará (clave para que funcione)
        resolved = None
        if sys.platform == "win32" and pm == "winget" and name:
            try:
                resolved = _resolve_winget_id(name)
            except Exception:
                resolved = None

        if not confirm:
            target = f"{resolved['name']} (ID: {resolved['id']})" if resolved else name
            return (
                f"⚠️ Voy a instalar '{name}' usando {pm}.\n"
                f"   Paquete a instalar: {target}\n"
                f"   ¿Confirmás la instalación? Respondé 'sí, instalá' para continuar."
            )
        
        if sys.platform == "win32":
            if pm == "winget":
                output = _install_winget(name, silent=silent)
                return f"Resultado de instalación:\n{output}"
            elif pm == "choco":
                output = _install_choco(name, silent=silent)
                return f"Resultado de instalación (choco):\n{output}"
            else:
                return "Ni winget ni Chocolatey están disponibles. Instalá winget desde Microsoft Store."
        
        elif sys.platform == "linux":
            return smart_install(name, silent=silent, password=password)
        
        return f"Package manager '{pm}' no soportado."
    
    # ── VERIFY ─────────────────────────────────────────────────────────────────
    elif action in ("verify", "verificar", "check", "status"):
        if not name:
            return "Especificá el nombre del programa a verificar."
        return verify_installation(name)
    
    # ── UNINSTALL ─────────────────────────────────────────────────────────────
    elif action in ("uninstall", "desinstalar", "remove", "eliminar"):
        import sys
        if not name:
            return "Especificá el nombre del programa a desinstalar."
        
        if not confirm:
            return (
                f"⚠️ Voy a desinstalar '{name}'.\n"
                f"   Esta acción no se puede deshacer.\n"
                f"   ¿Confirmás la desinstalación? Respondé 'sí, desinstalá' para continuar."
            )
        
        pm = _get_package_manager()
        
        if sys.platform == "win32":
            if pm == "winget":
                output = _uninstall_winget(name)
                if "successfully" in output.lower() or "éxito" in output.lower():
                    return f"✅ '{name}' desinstalado correctamente."
                return f"Resultado de desinstalación:\n{output}"
            
            # Fallback to registry
            registry_programs = _list_registry()
            for p in registry_programs:
                if name.lower() in p["name"].lower():
                    if p.get("uninstall_string"):
                        return _uninstall_registry(p["name"], p["uninstall_string"])
            
            return f"No se encontró '{name}' para desinstalar."
        
        elif sys.platform == "linux":
            if pm in ("paru", "yay", "pacman"):
                output = _uninstall_pacman(name, silent=silent, password=password)
                return output if "⚠️" in output else f"Resultado de desinstalación ({pm}):\n{output}"
            elif pm == "apt":
                output = _uninstall_apt(name, silent=silent, password=password)
                return output if "⚠️" in output else f"Resultado de desinstalación (apt):\n{output}"
            elif pm == "dnf":
                output = _uninstall_dnf(name, silent=silent, password=password)
                return output if "⚠️" in output else f"Resultado de desinstalación (dnf):\n{output}"
            elif pm == "flatpak":
                output = _uninstall_flatpak(name, silent=silent, password=password)
                return output if "⚠️" in output else f"Resultado de desinstalación (flatpak):\n{output}"
            elif pm == "snap":
                output = _uninstall_snap(name, silent=silent, password=password)
                return output if "⚠️" in output else f"Resultado de desinstalación (snap):\n{output}"
            else:
                return f"No se encontró '{name}' para desinstalar."
        
        return f"No se encontró '{name}' para desinstalar."
    
    # ── RUN ───────────────────────────────────────────────────────────────────
    elif action in ("run", "ejecutar", "open", "abrir", "launch", "iniciar"):
        if not name and not path:
            return "Especificá el nombre o ruta del programa a ejecutar."
        return _run_program(name or path, args)
    
    # ── UPDATE ────────────────────────────────────────────────────────────────
    elif action in ("update", "actualizar", "upgrade"):
        import sys
        if not confirm:
            return (
                f"⚠️ Voy a actualizar todos los programas instalados.\n"
                f"   ¿Confirmás? Respondé 'sí, actualizá' para continuar."
            )
        
        pm = _get_package_manager()
        
        if sys.platform == "win32":
            if pm == "winget":
                output = _run_cmd(["winget", "upgrade", "--all", "--silent", "--accept-source-agreements", "--accept-package-agreements"], timeout=600)
                return f"Resultado de actualización:\n{output}"
            return "winget no está disponible."
        
        elif sys.platform == "linux":
            if pm in ("paru", "yay"):
                result = _run_sudo_cmd([pm, "-Syu", "--noconfirm"], password=password)
                if result == "__SUDO_NEEDS_PASSWORD__":
                    return "⚠️ Para actualizar necesito la contraseña sudo. Decímela y la uso para continuar."
                return f"Resultado de actualización ({pm}):\n{result}"
            elif pm == "apt":
                result = _run_sudo_cmd(["apt", "update"], password=password)
                if result == "__SUDO_NEEDS_PASSWORD__":
                    return "⚠️ Para actualizar necesito la contraseña sudo. Decímela y la uso para continuar."
                result2 = _run_sudo_cmd(["apt", "upgrade", "-y"], password=password)
                return f"Resultado de actualización (apt):\n{result}\n{result2}"
            elif pm == "dnf":
                result = _run_sudo_cmd(["dnf", "upgrade", "-y"], password=password)
                if result == "__SUDO_NEEDS_PASSWORD__":
                    return "⚠️ Para actualizar necesito la contraseña sudo. Decímela y la uso para continuar."
                return f"Resultado de actualización (dnf):\n{result}"
            elif pm == "pacman":
                result = _run_sudo_cmd(["pacman", "-Syu", "--noconfirm"], password=password)
                if result == "__SUDO_NEEDS_PASSWORD__":
                    return "⚠️ Para actualizar necesito la contraseña sudo. Decímela y la uso para continuar."
                return f"Resultado de actualización (pacman):\n{result}"
            elif pm == "flatpak":
                output = _run_cmd(["flatpak", "update", "-y"], timeout=600)
                return f"Resultado de actualización (flatpak):\n{output}"
            elif pm == "snap":
                result = _run_sudo_cmd(["snap", "refresh"], password=password)
                if result == "__SUDO_NEEDS_PASSWORD__":
                    return "⚠️ Para actualizar necesito la contraseña sudo. Decímela y la uso para continuar."
                return f"Resultado de actualización (snap):\n{result}"
            return "No hay package manager disponible para actualizar."
        
        return f"Package manager '{pm}' no soportado para actualización."
    
    else:
        return f"Acción '{action}' desconocida. Opciones: install, uninstall, run, list, search, update, verify."

def _format_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"
