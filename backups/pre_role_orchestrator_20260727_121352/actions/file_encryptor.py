import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "encrypted_files.json"

def file_encryptor(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "status").lower()
    filepath = parameters.get("path") or parameters.get("file") or ""
    password = parameters.get("password") or parameters.get("key") or ""

    if player:
        player.write_log(f"🔐 Encriptar: {action}")

    if action in ("encrypt", "encriptar", "proteger"):
        return _encrypt_file(filepath, password)
    elif action in ("decrypt", "desencriptar", "desproteger"):
        return _decrypt_file(filepath, password)
    elif action in ("folder", "carpeta"):
        return _encrypt_folder(filepath, password)
    elif action in ("list", "listar"):
        return _list_encrypted()
    elif action in ("info", "informacion"):
        return _file_info(filepath)
    elif action in ("status", "estado"):
        return _status()
    else:
        return "Acciones: encrypt, decrypt, folder, list, info, status"

def _derive_key(password):
    return hashlib.sha256(password.encode()).digest()

def _encrypt_file(filepath, password):
    if not filepath:
        return "¿Qué archivo querés encriptar?"
    if not password:
        return "Necesitás una contraseña para encriptar."

    path = Path(filepath).expanduser()
    if not path.exists():
        return f"No encontré: {filepath}"

    try:
        key = _derive_key(password)
        output_path = path.with_suffix(path.suffix + ".enc")

        with open(path, "rb") as f:
            data = f.read()

        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ key[i % len(key)])

        with open(output_path, "wb") as f:
            f.write(bytes(encrypted))

        _log_encrypted(filepath, str(output_path), "encrypt")

        return f"🔐 Archivo encriptado: {path.name} → {output_path.name}"
    except Exception as e:
        return f"Error al encriptar: {e}"

def _decrypt_file(filepath, password):
    if not filepath:
        return "¿Qué archivo querés desencriptar?"
    if not password:
        return "Necesitás la contraseña."

    path = Path(filepath).expanduser()
    if not path.exists():
        return f"No encontré: {filepath}"

    try:
        key = _derive_key(password)
        if path.suffix == ".enc":
            output_path = path.with_suffix("")
        else:
            output_path = path.with_suffix(path.suffix + ".dec")

        with open(path, "rb") as f:
            data = f.read()

        decrypted = bytearray()
        for i, byte in enumerate(data):
            decrypted.append(byte ^ key[i % len(key)])

        with open(output_path, "wb") as f:
            f.write(bytes(decrypted))

        _log_encrypted(filepath, str(output_path), "decrypt")

        return f"🔓 Archivo desencriptado: {path.name} → {output_path.name}"
    except Exception as e:
        return f"Error al desencriptar: {e}"

def _encrypt_folder(folder_path, password):
    if not folder_path:
        return "¿Qué carpeta querés encriptar?"
    if not password:
        return "Necesitás una contraseña."

    folder = Path(folder_path).expanduser()
    if not folder.is_dir():
        return f"No encontré la carpeta: {folder_path}"

    count = 0
    errors = []
    for file in folder.rglob("*"):
        if file.is_file() and not file.suffix == ".enc":
            result = _encrypt_file(str(file), password)
            if result.startswith("🔐"):
                count += 1
            else:
                errors.append(f"{file.name}: {result}")

    return f"🔐 Encriptados {count} archivos en {folder.name}" + (f"\nErrores: {len(errors)}" if errors else "")

def _list_encrypted():
    try:
        if DATA_FILE.exists():
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if data:
                lines = []
                for item in data[-10:]:
                    lines.append(f"  [{item.get('time', '')[:16]}] {item.get('action', '')}: {item.get('source', '')}")
                return f"Archivos encriptados recientes:\n" + "\n".join(lines)
        return "No hay registros de encriptación."
    except:
        return "No hay registros."

def _file_info(filepath):
    if not filepath:
        return "¿De qué archivo?"
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

    is_encrypted = path.suffix == ".enc"

    return (
        f"📄 {path.name}\n"
        f"Ruta: {path.parent}\n"
        f"Tamaño: {size_str}\n"
        f"Encriptado: {'Sí' if is_encrypted else 'No'}\n"
        f"Modificado: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}"
    )

def _status():
    try:
        if DATA_FILE.exists():
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            encrypted = sum(1 for d in data if d.get("action") == "encrypt")
            decrypted = sum(1 for d in data if d.get("action") == "decrypt")
            return f"🔐 Encriptador: {encrypted} encriptados, {decrypted} desencriptados en historial."
        return "🔐 Encriptador listo. Sin actividad aún."
    except:
        return "🔐 Encriptador listo."

def _log_encrypted(source, dest, action):
    try:
        data = []
        if DATA_FILE.exists():
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        data.append({
            "source": source, "dest": dest, "action": action,
            "time": datetime.now().isoformat()
        })
        data = data[-100:]
        DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except: pass
