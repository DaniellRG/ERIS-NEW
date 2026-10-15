import shutil
import os
import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "file_log.json"


def _resolve_path(p: str) -> str:
    """Resuelve atajos ('escritorio', 'descargas', 'casa'…) y ~ ; cae a $HOME si la carpeta no existe."""
    try:
        from actions.file_editor import resolve_path
        return resolve_path(p)
    except Exception:
        return str(Path(p).expanduser()) if p else "."

FILE_CATEGORIES = {
    "imagen": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"],
    "video": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "documento": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv"],
    "codigo": [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".rs", ".go"],
    "archivo": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "ejecutable": [".exe", ".msi", ".bat", ".cmd", ".ps1"],
}

def file_manager(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "").lower()
    source = parameters.get("source") or parameters.get("path") or ""
    destination = parameters.get("destination") or parameters.get("dest") or ""
    name = parameters.get("name") or ""
    pattern = parameters.get("pattern") or ""

    if player:
        player.write_log(f"📁 File Manager: {action}")

    if action in ("move", "mover"):
        return _move(source, destination)
    elif action in ("copy", "copiar"):
        return _copy(source, destination)
    elif action in ("rename", "renombrar"):
        return _rename(source, name)
    elif action in ("delete", "eliminar", "borrar"):
        return _delete(source)
    elif action in ("organize", "organizar"):
        return _organize(source or str(Path.home() / "Downloads"))
    elif action in ("list", "listar", "contenido"):
        return _list_dir(_resolve_path(source) if source else ".")
    elif action in ("search", "buscar"):
        return _search_files(_resolve_path(source) if source else "", pattern)
    elif action in ("info", "informacion"):
        return _file_info(_resolve_path(source) if source else source)
    elif action in ("create_dir", "crear_carpeta"):
        return _create_dir(source)
    elif action in ("open", "abrir", "open_file"):
        return _open_file(_resolve_path(source) if source else source)
    elif action in ("open_folder", "abrir_carpeta"):
        return _open_folder(_resolve_path(source) if source else source)
    elif action in ("mapa", "map", "casa"):
        return _mapa_casa(parameters)
    else:
        return (
            "Acciones: move, copy, rename, delete, organize, list, search, info, create_dir, open, open_folder, mapa\n"
            "Ejemplo: 'abre documento.pdf' o 'abre la carpeta D:\\Fotos'"
        )

def _move(src, dst):
    if not src or not dst:
        return "Necesito origen y destino. Ej: 'mueve archivo.txt a D:\\Backup'"
    try:
        src_path = Path(src).expanduser()
        dst_path = Path(dst).expanduser()
        if not src_path.exists():
            return f"No encontré: {src}"
        if dst_path.is_dir():
            dst_path = dst_path / src_path.name
        shutil.move(str(src_path), str(dst_path))
        _log_action("move", src, dst)
        return f"Movido: {src_path.name} → {dst_path}"
    except Exception as e:
        return f"Error al mover: {e}"

def _copy(src, dst):
    if not src or not dst:
        return "Necesito origen y destino."
    try:
        src_path = Path(src).expanduser()
        dst_path = Path(dst).expanduser()
        if not src_path.exists():
            return f"No encontré: {src}"
        if dst_path.is_dir():
            dst_path = dst_path / src_path.name
        if src_path.is_dir():
            shutil.copytree(str(src_path), str(dst_path))
        else:
            shutil.copy2(str(src_path), str(dst_path))
        _log_action("copy", src, dst)
        return f"Copiado: {src_path.name} → {dst_path}"
    except Exception as e:
        return f"Error al copiar: {e}"

def _rename(src, new_name):
    if not src or not new_name:
        return "Necesito el archivo y el nuevo nombre."
    try:
        src_path = Path(src).expanduser()
        if not src_path.exists():
            return f"No encontré: {src}"
        new_path = src_path.parent / new_name
        src_path.rename(new_path)
        return f"Renombrado: {src_path.name} → {new_name}"
    except Exception as e:
        return f"Error al renombrar: {e}"

def _delete(src):
    if not src:
        return "¿Qué querés eliminar?"
    try:
        src_path = Path(src).expanduser()
        if not src_path.exists():
            return f"No encontré: {src}"
        if src_path.is_dir():
            shutil.rmtree(str(src_path))
        else:
            src_path.unlink()
        _log_action("delete", src, "")
        return f"Eliminado: {src_path.name}"
    except Exception as e:
        return f"Error al eliminar: {e}"

def _organize(directory):
    dir_path = Path(directory).expanduser()
    if not dir_path.is_dir():
        return f"No encontré la carpeta: {directory}"

    moved = 0
    for file in dir_path.iterdir():
        if file.is_file():
            ext = file.suffix.lower()
            category = "otros"
            for cat, exts in FILE_CATEGORIES.items():
                if ext in exts:
                    category = cat
                    break
            dest_dir = dir_path / category
            dest_dir.mkdir(exist_ok=True)
            dest = dest_dir / file.name
            if not dest.exists():
                shutil.move(str(file), str(dest))
                moved += 1

    return f"Organizados {moved} archivos en {dir_path.name}"

def _list_dir(directory):
    dir_path = Path(directory).expanduser()
    if not dir_path.is_dir():
        return f"No encontré: {directory}"

    try:
        items = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    except PermissionError:
        return f"Sin permiso para leer: {directory}"
    lines = []
    total_items = 0
    for item in items:
        total_items += 1
        if len(lines) >= 30:
            continue
        try:
            if item.is_symlink() and not item.exists():
                lines.append(f"🔗 {item.name} (enlace roto)")
                continue
            if item.is_dir():
                lines.append(f"📁 {item.name}/")
            else:
                size = item.stat().st_size
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.1f}MB"
                elif size > 1024:
                    size_str = f"{size/1024:.1f}KB"
                else:
                    size_str = f"{size}B"
                lines.append(f"📄 {item.name} ({size_str})")
        except (OSError, PermissionError):
            lines.append(f"❓ {item.name} (inaccesible)")

    remaining = total_items - 30
    result = f"Contenido de {dir_path.name} ({len(lines)}{'+' + str(remaining) if remaining > 0 else ''}):\n"
    result += "\n".join(lines)
    return result
    result += "\n".join(lines)
    return result

def _search_files(directory, pattern):
    if not pattern:
        return "¿Qué nombre o extensión buscás?"
    dir_path = Path(directory or ".").expanduser().resolve()
    # Ruta a un ARCHIVO: buscar en su propia carpeta (rglob solo sirve en directorios)
    if dir_path.is_file():
        if pattern.lower() in dir_path.name.lower():
            return f"El archivo coincide: {dir_path}"
        dir_path = dir_path.parent
    elif not dir_path.is_dir():
        # ruta inexistente: buscar el nombre pedido en raíces habituales (con tope, sin .venv/node_modules)
        alt = Path(directory).expanduser()
        needles = [alt.name.lower(), pattern.lower()]
        if alt.name:
            roots = [Path.home(), Path("/home/soul/Eris_NEW")]
            scanned = 0
            for rt in roots:
                if not rt.is_dir():
                    continue
                for r, ds, fns in os.walk(rt):
                    ds[:] = [d for d in ds if d not in (".venv", "venv", "node_modules",
                                                        "__pycache__", ".git", ".cache")]
                    scanned += 1
                    if scanned > 400:
                        break
                    if any(n in f.lower() for f in fns for n in needles if n):
                        return _search_files(r, pattern)
                if scanned > 400:
                    break
        return f"No encontré: {directory}"

    matches = []
    for item in dir_path.rglob(f"*{pattern}*"):
        if len(matches) >= 20:
            break
        if any(part in ("__pycache__", "node_modules", ".git") for part in item.parts):
            continue
        matches.append(str(item))

    if matches:
        return f"Encontré {len(matches)} resultados en {dir_path}:\n" + "\n".join(matches[:20])
    return f"No encontré archivos con '{pattern}' en {dir_path}"

def _file_info(filepath):
    if not filepath:
        return "¿De qué archivo querés info?"
    path = Path(filepath).expanduser()
    if not path.exists():
        return f"No encontré: {filepath}"

    stat = path.stat()
    size = stat.st_size
    if size > 1024*1024:
        size_str = f"{size/(1024*1024):.1f} MB"
    elif size > 1024:
        size_str = f"{size/1024:.1f} KB"
    else:
        size_str = f"{size} bytes"

    return (
        f"📄 {path.name}\n"
        f"Ruta: {path.parent}\n"
        f"Tamaño: {size_str}\n"
        f"Tipo: {'Carpeta' if path.is_dir() else path.suffix or 'Sin extensión'}\n"
        f"Creado: {datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M')}\n"
        f"Modificado: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}"
    )

def _create_dir(path):
    if not path:
        return "¿Dónde querés crear la carpeta?"
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return f"Carpeta creada: {path}"
    except Exception as e:
        return f"Error al crear carpeta: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# MAPA DE LA CASA — dónde vive cada cosa en esta PC
# ─────────────────────────────────────────────────────────────────────────────
_PROJECT_MARKERS = ("package.json", "pyproject.toml", "requirements.txt", "setup.py",
                    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts",
                    "composer.json", "Gemfile", "Makefile", "CMakeLists.txt", "CMakeCache.txt",
                    "*.sln", "*.csproj", "*.fsproj", "*.uproject", "*.xcodeproj", "*.ipynb")
_SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git", ".cache", ".local",
              "site-packages", ".npm", ".nuget", ".dotnet", ".rustup", ".cargo", "snap",
              "target", "bin", "obj", "dist", "build", ".mozilla", ".config"}


def _looks_like_project(d: Path) -> str:
    import fnmatch
    try:
        names = [e.name for e in os.scandir(d)]
    except (OSError, PermissionError):
        return ""
    for marker in _PROJECT_MARKERS:
        if marker.startswith("*"):
            if any(fnmatch.fnmatch(n, marker) for n in names):
                return marker.lstrip("*")
        elif marker in names:
            return marker
    if ".git" in names:
        return ".git"
    return ""


def _detect_projects(root: Path, max_depth: int = 3, limit: int = 60):
    """Encuentra carpetas de proyecto (git/npm/pip/cargo/dotnet/…) hasta max_depth."""
    found = []
    root = root.resolve()
    for r, dirs, _files in os.walk(root):
        rel_depth = len(Path(r).relative_to(root).parts)
        if rel_depth >= max_depth:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        marker = _looks_like_project(Path(r))
        if marker and Path(r) != root:
            found.append({"ruta": str(Path(r)), "marca": marker})
            if len(found) >= limit:
                break
    return found


def _mapa_casa(parameters: dict, player=None) -> str:
    """Escanea la máquina y devuelve (y guarda) el mapa de 'la casa' de Eris."""
    home = Path.home()
    proyectos = _detect_projects(home)
    # carpetas de primer nivel de la casa
    primeras = []
    primeras_nombres = []
    try:
        for e in sorted(os.scandir(home), key=lambda x: x.name.lower()):
            if e.name.startswith("."):
                continue
            try:
                if e.is_dir():
                    n = sum(1 for _ in os.scandir(e.path))
                    primeras.append(f"📁 {e.name}/ ({n} elementos)")
                else:
                    primeras.append(f"📄 {e.name}")
                primeras_nombres.append(e.name)
            except (OSError, PermissionError):
                primeras.append(f"❓ {e.name} (inaccesible)")
                primeras_nombres.append(e.name)
    except (OSError, PermissionError):
        pass

    # apps instaladas (lanzadores .desktop)
    apps = []
    for d in ("/usr/share/applications", "/usr/local/share/applications",
              str(home / ".local/share/applications")):
        try:
            for e in os.scandir(d):
                if e.name.endswith(".desktop") and "wine" not in e.name.lower():
                    apps.append(e.name[:-8])
        except (OSError, PermissionError):
            continue
    apps = sorted(set(apps))

    # discos montados
    discos = []
    try:
        for line in open("/proc/mounts", encoding="utf-8", errors="replace"):
            parts = line.split()
            if len(parts) >= 3 and parts[2] in ("ext4", "btrfs", "xfs", "vfat", "ntfs", "exfat", "f2fs"):
                discos.append(f"{parts[1]} ({parts[2]})")
    except Exception:
        pass

    atajos = {}
    for k in ("escritorio", "descargas", "documentos", "casa", "proyectos"):
        atajos[k] = str(_resolve_path(k))

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    md = [f"# 🏠 Mapa de la casa de Eris ({ts})", "",
          f"Máquina: `{home}` · Proyectos detectados: {len(proyectos)} · Apps: {len(apps)}", ""]
    md.append("## Atajos de la casa")
    md += [f"- **{k}** → `{v}`" for k, v in atajos.items()]
    md.append("")
    md.append("## Carpetas de primer nivel")
    md += [f"- {p}" for p in primeras]
    md.append("")
    md.append("## Proyectos de código (por marca de build)")
    md += [f"- `{p['ruta']}` ({p['marca']})" for p in proyectos] or ["- (ninguno detectado)"]
    md.append("")
    md.append("## Discos montados")
    md += [f"- {d}" for d in discos] or ["- (n/a)"]
    md.append("")
    md.append(f"## Aplicaciones instaladas ({len(apps)})")
    md.append(", ".join(apps[:120]) if apps else "(n/a)")
    md.append("")
    texto = "\n".join(md)

    destino = Path(__file__).resolve().parent.parent / "data" / "knowledge" / "mapa_de_la_casa.md"
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        guardado = f"Mapa guardado en: {destino}"
    except Exception as e:
        guardado = f"(no se pudo guardar el mapa: {e})"

    if player:
        try:
            player.write_log(f"🏠 Mapa de la casa: {len(proyectos)} proyectos, {len(apps)} apps")
        except Exception:
            pass

    lines = [f"🏠 Mapa de la casa ({home})", "", "Atajos:"]
    lines += [f"  • {k} → {v}" for k, v in atajos.items()]
    lines.append(f"\nProyectos de código ({len(proyectos)}):")
    lines += [f"  • {p['ruta']} ({p['marca']})" for p in proyectos[:25]] or ["  • (ninguno)"]
    lines.append(f"\nCarpetas de primer nivel: {', '.join(primeras_nombres[:30])}")
    lines.append(f"Apps instaladas: {len(apps)} · Discos: {len(discos)}")
    lines.append(guardado)
    return "\n".join(lines)

def _log_action(action, src, dst):
    try:
        log = []
        if DATA_FILE.exists():
            log = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        log.append({
            "action": action, "source": src, "dest": dst,
            "time": datetime.now().isoformat()
        })
        log = log[-100:]
        DATA_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    except (json.JSONDecodeError, OSError): pass

def _system_open(path):
    """Abre una ruta con el programa por defecto (multiplataforma)."""
    if os.name == "nt":
        os.startfile(str(path))
    else:
        import subprocess
        import sys
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, str(path)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _open_file(path):
    if not path:
        return "Especifico que archivo abrir"
    p = Path(path).expanduser()
    if not p.exists():
        return "No encontre: {}".format(path)
    try:
        _system_open(p)
        _log_action("open", str(p), "")
        return "Abriendo: {} ({})".format(p.name, p.suffix or "sin extension")
    except Exception as e:
        return "Error abriendo {}: {}".format(p.name, str(e)[:60])

def _open_folder(path):
    if not path:
        path = str(Path.home())
    p = Path(path).expanduser()
    if not p.exists():
        return "No encontre: {}".format(path)
    if not p.is_dir():
        return "No es una carpeta: {}".format(path)
    try:
        _system_open(p)
        _log_action("open_folder", str(p), "")
        return "Carpeta abierta: {}".format(p)
    except Exception as e:
        return "Error abriendo carpeta: {}".format(str(e)[:60])
