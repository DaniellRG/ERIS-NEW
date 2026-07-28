import shutil
import os
import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "file_log.json"

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
        return _list_dir(source or ".")
    elif action in ("search", "buscar"):
        return _search_files(source, pattern)
    elif action in ("info", "informacion"):
        return _file_info(source)
    elif action in ("create_dir", "crear_carpeta"):
        return _create_dir(source)
    elif action in ("open", "abrir", "open_file"):
        return _open_file(source)
    elif action in ("open_folder", "abrir_carpeta"):
        return _open_folder(source)
    else:
        return (
            "Acciones: move, copy, rename, delete, organize, list, search, info, create_dir, open, open_folder\n"
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

    items = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    lines = []
    for item in items[:30]:
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

    remaining = len(list(dir_path.iterdir())) - 30
    result = f"Contenido de {dir_path.name} ({len(lines)}{'+' + str(remaining) if remaining > 0 else ''}):\n"
    result += "\n".join(lines)
    return result

def _search_files(directory, pattern):
    if not pattern:
        return "¿Qué nombre o extensión buscás?"
    dir_path = Path(directory or ".").expanduser()
    if not dir_path.is_dir():
        return f"No encontré: {directory}"

    matches = []
    for item in dir_path.rglob(f"*{pattern}*"):
        if len(matches) >= 20:
            break
        matches.append(str(item))

    if matches:
        return f"Encontré {len(matches)} resultados:\n" + "\n".join(matches[:20])
    return f"No encontré archivos con '{pattern}' en {dir_path.name}"

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
    except: pass

def _open_file(path):
    if not path:
        return "Especifico que archivo abrir"
    p = Path(path).expanduser()
    if not p.exists():
        return "No encontre: {}".format(path)
    try:
        os.startfile(str(p))
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
        os.startfile(str(p))
        _log_action("open_folder", str(p), "")
        return "Carpeta abierta: {}".format(p)
    except Exception as e:
        return "Error abriendo carpeta: {}".format(str(e)[:60])
