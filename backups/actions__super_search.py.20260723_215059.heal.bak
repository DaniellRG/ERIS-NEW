"""
super_search.py — ERIS Super Search Engine.
Búsqueda multi-estrategia en Windows y Linux:
   Windows:
     1. Windows Search Index (instantáneo)
     2. PowerShell Get-ChildItem (rápido)
     3. CMD dir /s /b (clásico)
     4. where.exe (PATH + directorios)
     5. Registro de Windows (programas instalados)
     6. AppData / ProgramData (configs ocultas)
     7. Búsqueda por contenido (Select-String)
     8. Python rglob (último recurso)

   Linux:
     1. fd (ultrarrápido, indexado)
     2. locate/mlocate (base de datos indexada)
     3. find (estándar, profundo)
     4. grep -r (contenido dentro de archivos)
     5. pacman -Ql / dpkg -L (archivos de paquetes)
     6. whereis / which / type (ejecutables en PATH)
     7. Python rglob (último recurso)

Cada estrategia tiene timeout para no colgar ERIS.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

_OS = "Linux" if sys.platform.startswith("linux") else "Windows"

# ── Timeouts per strategy (seconds) ───────────────────────────────────────────
_TIMEOUT_INDEX   = 5
_TIMEOUT_PS      = 15
_TIMEOUT_CMD     = 15
_TIMEOUT_WHERE   = 10
_TIMEOUT_CONTENT = 30
_TIMEOUT_WMI     = 10

# ── Safe paths to search ──────────────────────────────────────────────────────
_FORBIDDEN_PATHS = {
    "C:/Windows/System32",
    "C:/Windows/WinSxS",
    "C:/Windows/Installer",
    "C:/Windows/assembly",
    "C:/$Recycle.Bin",
    "C:/System Volume Information",
} if _OS == "Windows" else set()

def _is_safe(path: str) -> bool:
    """Check if path is safe to search."""
    if not _FORBIDDEN_PATHS:
        return True
    p = path.replace("\\", "/").lower()
    for forbidden in _FORBIDDEN_PATHS:
        if p.startswith(forbidden.lower()):
            return False
    return True

def _run_cmd(cmd: list[str], timeout: int = 10, encoding: str = "utf-8") -> str:
    """Run a command and return stdout. Returns empty string on error."""
    try:
        kwargs = dict(capture_output=True, text=True, timeout=timeout, encoding=encoding, errors="ignore")
        if _OS == "Windows":
            kwargs["creationflags"] = 0x08000000
        result = subprocess.run(cmd, **kwargs)
        return result.stdout or ""
    except subprocess.TimeoutExpired:
        return ""
    except Exception:
        return ""

def _parse_size(size_str: str) -> int:
    """Convert size string like '1MB', '500KB', '2GB' to bytes."""
    size_str = size_str.strip().upper()
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if size_str.endswith(suffix):
            try:
                return int(float(size_str[:-len(suffix)].strip()) * mult)
            except ValueError:
                return 0
    try:
        return int(size_str)
    except ValueError:
        return 0

def _format_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

# ── Strategy 1: Windows Search Index ─────────────────────────────────────────

def _search_windows_index(name: str, extension: str = "", max_results: int = 20) -> list[dict]:
    """Search using Windows Search Index (instant if indexed)."""
    results = []
    try:
        # Escape single quotes for SQL
        name_escaped = name.replace("'", "''")
        
        query = f"""
        SELECT TOP {max_results} System.ItemPathDisplay, System.Size, System.DateModified
        FROM SystemIndex
        WHERE System.FileName LIKE '%{name_escaped}%'
        """
        if extension:
            ext_escaped = extension.replace("'", "''").lstrip(".")
            query += f" AND System.FileExtension = '.{ext_escaped}'"
        
        query += " ORDER BY System.DateModified DESC"

        ps_cmd = [
            "powershell", "-NoProfile", "-Command",
            f"""
            $conn = New-Object -ComObject ADODB.Connection
            $rs = New-Object -ComObject ADODB.Recordset
            $conn.Open("Provider=Search.CollatorDSO;Extended Properties='Application=Windows';")
            $rs.Open("{query}", $conn)
            while (-not $rs.EOF) {{
                $path = $rs.Fields.Item("System.ItemPathDisplay").Value
                $size = $rs.Fields.Item("System.Size").Value
                $mod = $rs.Fields.Item("System.DateModified").Value
                Write-Output "$path|$size|$mod"
                $rs.MoveNext()
            }}
            $rs.Close()
            $conn.Close()
            """
        ]
        output = _run_cmd(ps_cmd, timeout=_TIMEOUT_INDEX)
        
        for line in output.strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 2)
                path = parts[0]
                if _is_safe(path):
                    try:
                        size = int(parts[1]) if parts[1] else 0
                    except ValueError:
                        size = 0
                    mod_date = parts[2] if len(parts) > 2 else ""
                    results.append({
                        "path": path,
                        "name": Path(path).name,
                        "size": size,
                        "size_str": _format_size(size),
                        "modified": mod_date[:19] if mod_date else "",
                        "source": "Windows Index",
                    })
    except Exception:
        pass
    
    return results

# ── Strategy 2: PowerShell Get-ChildItem ──────────────────────────────────────

def _search_powershell(name: str, extension: str = "", path: str = "", 
                       max_results: int = 20, modified_after: str = "",
                       size_min: str = "", size_max: str = "") -> list[dict]:
    """Search using PowerShell Get-ChildItem -Recurse."""
    results = []
    try:
        search_path = path or "C:/Users"
        if not _is_safe(search_path):
            search_path = str(Path.home())
        
        # Build filter
        filter_str = f"*{name}*" if name else "*"
        if extension:
            filter_str = f"*{extension}" if not name else f"*{name}*{extension}"
        
        ps_script = f"""
        $ErrorActionPreference = 'SilentlyContinue'
        $results = Get-ChildItem -Path "{search_path}" -Filter "{filter_str}" -Recurse -File -ErrorAction SilentlyContinue
        $count = 0
        foreach ($f in $results) {{
            if ($count -ge {max_results}) {{ break }}
            $size = $f.Length
            $mod = $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            Write-Output "$($f.FullName)|$size|$mod"
            $count++
        }}
        """
        
        # Add date filter if specified
        if modified_after:
            ps_script = f"""
            $ErrorActionPreference = 'SilentlyContinue'
            $cutoff = [datetime]"{modified_after}"
            $results = Get-ChildItem -Path "{search_path}" -Filter "{filter_str}" -Recurse -File -ErrorAction SilentlyContinue | Where-Object {{ $_.LastWriteTime -gt $cutoff }}
            $count = 0
            foreach ($f in $results) {{
                if ($count -ge {max_results}) {{ break }}
                $size = $f.Length
                $mod = $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
                Write-Output "$($f.FullName)|$size|$mod"
                $count++
            }}
            """
        
        # Add size filter if specified
        if size_min or size_max:
            size_filter = ""
            if size_min:
                min_bytes = _parse_size(size_min)
                size_filter += f"$_.Length -ge {min_bytes}"
            if size_max:
                max_bytes = _parse_size(size_max)
                if size_filter:
                    size_filter += " -and "
                size_filter += f"$_.Length -le {max_bytes}"
            
            ps_script = f"""
            $ErrorActionPreference = 'SilentlyContinue'
            $results = Get-ChildItem -Path "{search_path}" -Filter "{filter_str}" -Recurse -File -ErrorAction SilentlyContinue | Where-Object {{ {size_filter} }}
            $count = 0
            foreach ($f in $results) {{
                if ($count -ge {max_results}) {{ break }}
                $size = $f.Length
                $mod = $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
                Write-Output "$($f.FullName)|$size|$mod"
                $count++
            }}
            """
        
        output = _run_cmd(["powershell", "-NoProfile", "-Command", ps_script], timeout=_TIMEOUT_PS)
        
        for line in output.strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 2)
                path = parts[0]
                if _is_safe(path):
                    try:
                        size = int(parts[1])
                    except ValueError:
                        size = 0
                    mod_date = parts[2] if len(parts) > 2 else ""
                    results.append({
                        "path": path,
                        "name": Path(path).name,
                        "size": size,
                        "size_str": _format_size(size),
                        "modified": mod_date,
                        "source": "PowerShell",
                    })
    except Exception:
        pass
    
    return results

# ── Strategy 3: CMD dir /s /b ─────────────────────────────────────────────────

def _search_cmd(name: str, extension: str = "", path: str = "", 
                max_results: int = 20) -> list[dict]:
    """Search using CMD dir /s /b."""
    results = []
    try:
        search_path = path or "C:\\Users"
        if not _is_safe(search_path):
            search_path = str(Path.home())
        
        search_pattern = f"*{name}*{extension}" if name else f"*{extension}"
        if not name and not extension:
            search_pattern = "*"
        
        cmd = ["cmd", "/c", f'dir /s /b "{search_path}\\{search_pattern}"']
        output = _run_cmd(cmd, timeout=_TIMEOUT_CMD)
        
        count = 0
        for line in output.strip().split("\n"):
            if count >= max_results:
                break
            path = line.strip()
            if path and _is_safe(path):
                try:
                    p = Path(path)
                    if p.is_file():
                        size = p.stat().st_size
                        mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        results.append({
                            "path": path,
                            "name": p.name,
                            "size": size,
                            "size_str": _format_size(size),
                            "modified": mod,
                            "source": "CMD dir",
                        })
                        count += 1
                except Exception:
                    pass
    except Exception:
        pass
    
    return results

# ── Strategy 4: where.exe ─────────────────────────────────────────────────────

def _search_where(name: str, max_results: int = 20) -> list[dict]:
    """Search using where.exe /r."""
    results = []
    try:
        cmd = ["where", "/r", "C:\\", name]
        output = _run_cmd(cmd, timeout=_TIMEOUT_WHERE)
        
        count = 0
        for line in output.strip().split("\n"):
            if count >= max_results:
                break
            path = line.strip()
            if path and _is_safe(path):
                try:
                    p = Path(path)
                    if p.is_file():
                        size = p.stat().st_size
                        mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        results.append({
                            "path": path,
                            "name": p.name,
                            "size": size,
                            "size_str": _format_size(size),
                            "modified": mod,
                            "source": "where.exe",
                        })
                        count += 1
                except Exception:
                    pass
    except Exception:
        pass
    
    return results

# ── Strategy 5: Registry (installed programs) ─────────────────────────────────

def _search_registry(name: str, max_results: int = 20) -> list[dict]:
    """Search Windows Registry for installed programs."""
    results = []
    try:
        reg_paths = [
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        
        for reg_path in reg_paths:
            cmd = ["reg", "query", reg_path, "/s", "/f", name, "/d"]
            output = _run_cmd(cmd, timeout=5)
            
            for line in output.strip().split("\n"):
                if len(results) >= max_results:
                    break
                if "DisplayName" in line or "InstallLocation" in line:
                    # Extract value
                    match = re.search(r'REG_SZ\s+(.+)', line)
                    if match:
                        value = match.group(1).strip()
                        if name.lower() in value.lower():
                            results.append({
                                "path": value,
                                "name": value,
                                "size": 0,
                                "size_str": "N/A",
                                "modified": "",
                                "source": "Registry",
                            })
    except Exception:
        pass
    
    return results

# ── Strategy 6: AppData / ProgramData ─────────────────────────────────────────

def _search_special_dirs(name: str, extension: str = "", max_results: int = 20) -> list[dict]:
    """Search in AppData, ProgramData, Program Files."""
    results = []
    try:
        special_dirs = [
            os.environ.get("APPDATA", ""),
            os.environ.get("LOCALAPPDATA", ""),
            os.environ.get("ProgramData", ""),
            r"C:\Program Files",
            r"C:\Program Files (x86)",
        ]
        
        filter_str = f"*{name}*{extension}" if name else f"*{extension}"
        if not name and not extension:
            filter_str = "*"
        
        for dir_path in special_dirs:
            if not dir_path or not _is_safe(dir_path):
                continue
            if not os.path.exists(dir_path):
                continue
            
            ps_script = f"""
            $ErrorActionPreference = 'SilentlyContinue'
            $results = Get-ChildItem -Path "{dir_path}" -Filter "{filter_str}" -Recurse -File -Depth 3 -ErrorAction SilentlyContinue
            $count = 0
            foreach ($f in $results) {{
                if ($count -ge {max_results}) {{ break }}
                $size = $f.Length
                $mod = $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
                Write-Output "$($f.FullName)|$size|$mod"
                $count++
            }}
            """
            output = _run_cmd(["powershell", "-NoProfile", "-Command", ps_script], timeout=10)
            
            for line in output.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 2)
                    path = parts[0]
                    if _is_safe(path):
                        try:
                            size = int(parts[1])
                        except ValueError:
                            size = 0
                        mod_date = parts[2] if len(parts) > 2 else ""
                        results.append({
                            "path": path,
                            "name": Path(path).name,
                            "size": size,
                            "size_str": _format_size(size),
                            "modified": mod_date,
                            "source": "Special Dirs",
                        })
            
            if results:
                break
    except Exception:
        pass
    
    return results

# ── Strategy 7: Search file content ───────────────────────────────────────────

def _search_content(query: str, path: str = "", extension: str = "", 
                    max_results: int = 20) -> list[dict]:
    """Search for text content inside files using PowerShell Select-String."""
    results = []
    try:
        search_path = path or str(Path.home())
        if not _is_safe(search_path):
            search_path = str(Path.home())
        
        filter_str = f"*{extension}" if extension else "*"
        
        ps_script = f"""
        $ErrorActionPreference = 'SilentlyContinue'
        $results = Select-String -Path "{search_path}\\{filter_str}" -Pattern "{query}" -CaseSensitive:$false -List | Select-Object -First {max_results}
        foreach ($r in $results) {{
            $line = $r.LineNumber
            $path = $r.Path
            $text = ($r.Line -replace '[|]', '').Substring(0, [Math]::Min(100, $r.Line.Length))
            Write-Output "$path|$line|$text"
        }}
        """
        
        output = _run_cmd(["powershell", "-NoProfile", "-Command", ps_script], timeout=_TIMEOUT_CONTENT)
        
        for line in output.strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 2)
                path = parts[0]
                if _is_safe(path):
                    line_num = parts[1] if len(parts) > 1 else ""
                    content = parts[2] if len(parts) > 2 else ""
                    results.append({
                        "path": path,
                        "name": Path(path).name,
                        "size": 0,
                        "size_str": "N/A",
                        "modified": "",
                        "source": "Content Search",
                        "line": line_num,
                        "content_preview": content[:100],
                    })
    except Exception:
        pass
    
    return results

# ── Strategy 8: Python rglob (fallback) ───────────────────────────────────────

def _search_python(name: str, extension: str = "", path: str = "", 
                   max_results: int = 20, deep: bool = False) -> list[dict]:
    """Fallback search using Python pathlib rglob."""
    results = []
    try:
        search_path = Path(path) if path else Path.home()
        if not _is_safe(str(search_path)):
            search_path = Path.home()
        if not search_path.exists():
            return []
        
        max_dirs = 5000 if deep else 1000
        dir_count = 0
        
        for item in search_path.rglob("*"):
            if item.is_dir():
                dir_count += 1
                if dir_count > max_dirs:
                    break
                continue
            if not item.is_file():
                continue
            if extension and item.suffix.lower() != extension.lower():
                continue
            if name and name.lower() not in item.name.lower():
                continue
            
            try:
                size = item.stat().st_size
                mod = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                results.append({
                    "path": str(item),
                    "name": item.name,
                    "size": size,
                    "size_str": _format_size(size),
                    "modified": mod,
                    "source": "Python rglob",
                })
            except Exception:
                pass
            
            if len(results) >= max_results:
                break
    except Exception:
        pass
    
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# ── Linux-specific strategies ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

def _search_linux_fd(name: str, path: str = "", max_results: int = 50) -> list[dict]:
    """Search using fd (Rust find tool, fastest)."""
    results = []
    try:
        search_path = path or "/"
        extra = []
        if max_results:
            extra = ["--max-results", str(max_results)]
        cmd = ["fd", "--no-ignore", "-i", name, search_path] + extra
        output = _run_cmd(cmd, timeout=30)
        for line in output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                p = Path(line)
                if p.exists():
                    size = p.stat().st_size if p.is_file() else 0
                    mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if p.exists() else ""
                    results.append({
                        "path": str(p),
                        "name": p.name,
                        "size": size,
                        "size_str": _format_size(size),
                        "modified": mod,
                        "source": "fd",
                    })
            except Exception:
                pass
    except Exception:
        pass
    return results

def _search_linux_locate(name: str, path: str = "", max_results: int = 50) -> list[dict]:
    """Search using mlocate/locate indexed database."""
    results = []
    try:
        search_path = path or "/"
        cmd = ["locate", "-i", "-l", str(max_results), "--existing", f"*{name}*"]
        output = _run_cmd(cmd, timeout=15)
        for line in output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if search_path and search_path != "/" and not str(line).startswith(search_path):
                continue
            try:
                p = Path(line)
                if p.exists():
                    size = p.stat().st_size if p.is_file() else 0
                    mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if p.exists() else ""
                    results.append({
                        "path": str(p),
                        "name": p.name,
                        "size": size,
                        "size_str": _format_size(size),
                        "modified": mod,
                        "source": "locate",
                    })
            except Exception:
                pass
    except Exception:
        pass
    return results

def _search_linux_find(name: str, path: str = "", max_results: int = 50) -> list[dict]:
    """Search using standard find command."""
    results = []
    try:
        search_path = path or "/"
        cmd = ["find", search_path, "-iname", f"*{name}*"]
        if not path or path == "/":
            cmd += ["-maxdepth", "10"]
        output = _run_cmd(cmd, timeout=60)
        for line in output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                p = Path(line)
                if p.exists():
                    size = p.stat().st_size if p.is_file() else 0
                    mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if p.exists() else ""
                    results.append({
                        "path": str(p),
                        "name": p.name,
                        "size": size,
                        "size_str": _format_size(size),
                        "modified": mod,
                        "source": "find",
                    })
            except Exception:
                pass
            if len(results) >= max_results:
                break
    except Exception:
        pass
    return results

def _search_linux_grep(query: str, path: str = "", extension: str = "", max_results: int = 20) -> list[dict]:
    """Search file contents using grep -r."""
    results = []
    try:
        search_path = path or os.path.expanduser("~")
        include = f"--include=*{extension}" if extension else ""
        cmd = ["grep", "-r", "-l", "-i", query, search_path]
        if include:
            cmd.insert(-2, include)
        output = _run_cmd(cmd, timeout=30)
        for line in output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                p = Path(line)
                if p.exists() and p.is_file():
                    size = p.stat().st_size
                    mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    results.append({
                        "path": str(p),
                        "name": p.name,
                        "size": size,
                        "size_str": _format_size(size),
                        "modified": mod,
                        "source": "grep",
                    })
            except Exception:
                pass
            if len(results) >= max_results:
                break
    except Exception:
        pass
    return results

def _search_linux_installed(name: str, max_results: int = 20) -> list[dict]:
    """Search for installed packages (pacman/dpkg) that match name."""
    results = []
    try:
        # Try pacman first (Arch-based)
        pkg_cmd = ["pacman", "-Qq"]
        pkg_out = _run_cmd(pkg_cmd, timeout=10)
        if pkg_out:
            for pkg in pkg_out.strip().split("\n"):
                if name.lower() in pkg.lower():
                    # Get package files
                    files_out = _run_cmd(["pacman", "-Ql", pkg], timeout=5)
                    file_count = len([l for l in files_out.strip().split("\n") if l.strip() and "/" in l])
                    results.append({
                        "path": f"pacman: {pkg}",
                        "name": pkg,
                        "size": 0,
                        "size_str": "N/A",
                        "modified": "",
                        "source": f"pacman ({file_count} archivos)",
                    })
                    if len(results) >= max_results:
                        break

        # Try dpkg-query as fallback
        if not results:
            dpkg_out = _run_cmd(["dpkg-query", "-W", f"*{name}*"], timeout=10)
            if dpkg_out:
                for line in dpkg_out.strip().split("\n")[:max_results]:
                    if line.strip():
                        results.append({
                            "path": f"dpkg: {line.strip()}",
                            "name": line.strip(),
                            "size": 0,
                            "size_str": "N/A",
                            "modified": "",
                            "source": "dpkg",
                        })
    except Exception:
        pass
    return results

def _search_linux_which(name: str, max_results: int = 10) -> list[dict]:
    """Search for executables using which, whereis, type."""
    results = []
    try:
        # which
        out = _run_cmd(["which", name], timeout=5)
        for line in out.strip().split("\n"):
            line = line.strip()
            if line and Path(line).exists():
                results.append({
                    "path": line,
                    "name": name,
                    "size": 0,
                    "size_str": "N/A",
                    "modified": "",
                    "source": "which",
                })

        # whereis
        out = _run_cmd(["whereis", name], timeout=5)
        for line in out.strip().split("\n"):
            for word in line.split()[1:]:
                word = word.strip()
                if word and Path(word).exists() and not any(r["path"] == word for r in results):
                    results.append({
                        "path": word,
                        "name": name,
                        "size": 0,
                        "size_str": "N/A",
                        "modified": "",
                        "source": "whereis",
                    })
                    if len(results) >= max_results:
                        break
    except Exception:
        pass
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# ── Main search orchestrator ──────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

def _deduplicate_results(all_results: list[dict]) -> list[dict]:
    """Remove duplicates based on path."""
    seen = set()
    unique = []
    for r in all_results:
        path_key = r["path"].lower()
        if path_key not in seen:
            seen.add(path_key)
            unique.append(r)
    return unique

def super_search_engine(
    name: str = "",
    extension: str = "",
    path: str = "",
    content: str = "",
    max_results: int = 20,
    modified_after: str = "",
    size_min: str = "",
    size_max: str = "",
    deep: bool = False,
) -> str:
    """
    Multi-strategy search engine for ERIS.
    Tries multiple search methods until results are found.
    """
    all_results = []
    strategies_used = []
    
    # ── If searching by content ──────────────────────────────────────────────
    if content:
        if _OS == "Linux":
            strategies_used.append("grep")
            results = _search_linux_grep(content, path=path, extension=extension, max_results=max_results)
        else:
            strategies_used.append("Content Search")
            results = _search_content(content, path=path, extension=extension, max_results=max_results)
        all_results.extend(results)
        if all_results:
            return _format_results(all_results, strategies_used)
    
    if _OS == "Linux":
        # ── Linux strategy priority ──────────────────────────────────────────
        if name:
            # Strategy L1: fd (ultra rápido)
            strategies_used.append("fd")
            results = _search_linux_fd(name, path=path, max_results=max_results)
            all_results.extend(results)
            if all_results:
                return _format_results(all_results, strategies_used)
            
            # Strategy L2: locate (indexado)
            strategies_used.append("locate")
            results = _search_linux_locate(name, path=path, max_results=max_results)
            all_results.extend(results)
            if all_results:
                return _format_results(all_results, strategies_used)
            
            # Strategy L3: find for deep search
            if deep:
                strategies_used.append("find")
                results = _search_linux_find(name, path=path, max_results=max_results)
                all_results.extend(results)
                if all_results:
                    return _format_results(all_results, strategies_used)
        
        # Strategy L4: rglob (deep fallback)
        strategies_used.append("Python rglob")
        results = _search_python(name, extension=extension, path=path, max_results=max_results, deep=deep)
        all_results.extend(results)
        
        return _format_results(all_results, strategies_used)
    
    # ── Windows strategy priority ────────────────────────────────────────────
    # Strategy 1: Windows Search Index (fastest)
    if name:
        strategies_used.append("Windows Index")
        results = _search_windows_index(name, extension=extension, max_results=max_results)
        all_results.extend(results)
        if all_results:
            return _format_results(all_results, strategies_used)
    
    # Strategy 2: PowerShell (fast)
    strategies_used.append("PowerShell")
    results = _search_powershell(
        name=name, extension=extension, path=path,
        max_results=max_results, modified_after=modified_after,
        size_min=size_min, size_max=size_max
    )
    all_results.extend(results)
    if all_results:
        return _format_results(all_results, strategies_used)
    
    # Strategy 3: Special dirs (AppData, Program Files, etc.)
    if name:
        strategies_used.append("Special Dirs")
        results = _search_special_dirs(name, extension=extension, max_results=max_results)
        all_results.extend(results)
        if all_results:
            return _format_results(all_results, strategies_used)
    
    # Strategy 4: CMD dir /s
    strategies_used.append("CMD dir")
    results = _search_cmd(name, extension=extension, path=path, max_results=max_results)
    all_results.extend(results)
    if all_results:
        return _format_results(all_results, strategies_used)
    
    # Strategy 5: where.exe
    if name:
        strategies_used.append("where.exe")
        results = _search_where(name, max_results=max_results)
        all_results.extend(results)
        if all_results:
            return _format_results(all_results, strategies_used)
    
    # Strategy 6: Registry (for programs)
    if name:
        strategies_used.append("Registry")
        results = _search_registry(name, max_results=max_results)
        all_results.extend(results)
        if all_results:
            return _format_results(all_results, strategies_used)
    
    # Strategy 7: Python rglob (last resort)
    strategies_used.append("Python rglob")
    results = _search_python(name, extension=extension, path=path, max_results=max_results, deep=deep)
    all_results.extend(results)
    
    return _format_results(all_results, strategies_used)

def _format_results(results: list[dict], strategies: list[str]) -> str:
    """Format search results for display."""
    if not results:
        strategies_str = ", ".join(strategies) if strategies else "all methods"
        return f"No se encontraron resultados usando: {strategies_str}."
    
    # Deduplicate
    results = _deduplicate_results(results)
    
    lines = [f"✅ Encontrados {len(results)} archivo(s):"]
    lines.append(f"   Estrategias usadas: {', '.join(strategies)}")
    lines.append("")
    
    for i, r in enumerate(results, 1):
        line = f"  {i}. 📄 {r['name']}"
        if r.get("size_str") and r["size_str"] != "N/A":
            line += f" ({r['size_str']})"
        line += f"\n     📍 {r['path']}"
        if r.get("modified"):
            line += f"\n     📅 {r['modified']}"
        line += f"\n     🔍 {r['source']}"
        if r.get("content_preview"):
            line += f"\n     💬 ...{r['content_preview']}..."
        if r.get("line"):
            line += f" (línea {r['line']})"
        lines.append(line)
    
    return "\n".join(lines)

# ── Tool function ─────────────────────────────────────────────────────────────

def super_search(parameters: dict, player=None, **kwargs) -> str:
    """
    Búsqueda avanzada multi-estrategia en toda la PC.
    
    parameters:
        action: 'find_file' | 'find_folder' | 'find_content' | 'find_app' | 'find_recent' | 'find_by_type' | 'find_by_date' | 'find_everything'
        name: nombre del archivo o patrón
        extension: extensión específica (.pdf, .exe, etc.)
        path: dónde buscar (default: todo el sistema)
        content: buscar texto DENTRO de archivos
        max_results: máximo resultados (default: 20)
        modified_after: archivos modificados después de fecha (YYYY-MM-DD)
        size_min: tamaño mínimo (ej: '1MB', '500KB')
        size_max: tamaño máximo (ej: '100MB', '1GB')
        deep: búsqueda exhaustiva (True/False)
    """
    params = parameters or {}
    action = params.get("action", "find_file").lower()
    
    if player:
        player.write_log(f"🔍 Super search: {action} {params.get('name', '')}")
    
    if action in ("find_file", "find", "buscar", "search"):
        return super_search_engine(
            name=params.get("name", ""),
            extension=params.get("extension", ""),
            path=params.get("path", ""),
            max_results=int(params.get("max_results", 20)),
            modified_after=params.get("modified_after", ""),
            size_min=params.get("size_min", ""),
            size_max=params.get("size_max", ""),
            deep=params.get("deep", False) or params.get("deep_search", False),
        )
    
    elif action in ("find_content", "content", "texto", "inside"):
        return super_search_engine(
            content=params.get("content", ""),
            name=params.get("name", ""),
            extension=params.get("extension", ""),
            path=params.get("path", ""),
            max_results=int(params.get("max_results", 20)),
        )
    
    elif action in ("find_app", "app", "programa", "program"):
        name = params.get("name", "")
        if _OS == "Linux":
            results = _search_linux_installed(name, max_results=int(params.get("max_results", 20)))
            if not results:
                results = _search_linux_which(name, max_results=int(params.get("max_results", 10)))
            if not results:
                results = _search_linux_find(name, path="/usr/share/applications", max_results=int(params.get("max_results", 20)))
            return _format_results(results, ["pacman/dpkg", "which/whereis", "find"])
        results = _search_registry(name, max_results=int(params.get("max_results", 20)))
        if not results:
            results = _search_special_dirs(name, max_results=int(params.get("max_results", 20)))
        if not results:
            results = _search_powershell(name, path=r"C:\Program Files", max_results=int(params.get("max_results", 20)))
        return _format_results(results, ["Registry", "Special Dirs", "PowerShell"])
    
    elif action in ("find_recent", "recent", "reciente", "hoy"):
        days = int(params.get("days", 7))
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return super_search_engine(
            name=params.get("name", ""),
            extension=params.get("extension", ""),
            path=params.get("path", str(Path.home())),
            max_results=int(params.get("max_results", 20)),
            modified_after=cutoff,
        )
    
    elif action in ("find_by_type", "type", "tipo", "extension"):
        ext = params.get("extension", params.get("type", ""))
        if not ext.startswith("."):
            ext = f".{ext}"
        return super_search_engine(
            name="",
            extension=ext,
            path=params.get("path", ""),
            max_results=int(params.get("max_results", 20)),
        )
    
    elif action in ("find_by_date", "date", "fecha"):
        return super_search_engine(
            name=params.get("name", ""),
            extension=params.get("extension", ""),
            path=params.get("path", ""),
            max_results=int(params.get("max_results", 20)),
            modified_after=params.get("modified_after", ""),
        )
    
    elif action in ("find_everything", "everything", "todo", "completo"):
        return super_search_engine(
            name=params.get("name", ""),
            extension=params.get("extension", ""),
            path=params.get("path", ""),
            max_results=int(params.get("max_results", 50)),
            deep=True,
        )
    
    return f"Acción '{action}' desconocida. Opciones: find_file, find_content, find_app, find_recent, find_by_type, find_by_date, find_everything."
