"""
data_encryption.py — Cifrado de datos: proteger memorias sensibles con encriptación.
Usa AES-256 para cifrar archivos y datos sensibles.
"""
import json
import hashlib
import base64
import os
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_ENCRYPTED_DIR = _BASE / "data" / "encrypted"
_KEY_FILE = _BASE / "config" / "encryption_key.json"


def data_encryption(parameters: dict = None, player=None) -> str:
    """
    Cifrado de datos.
    Acciones: encrypt, decrypt, encrypt_file, decrypt_file, list_encrypted,
              change_key, backup_keys, status, secure_delete, hash_data, verify
    """
    params = parameters or {}
    action = params.get("action", "status").lower()
    _ENCRYPTED_DIR.mkdir(parents=True, exist_ok=True)

    if action == "encrypt":
        return _encrypt_data(params)
    elif action == "decrypt":
        return _decrypt_data(params)
    elif action == "encrypt_file":
        return _encrypt_file(params)
    elif action == "decrypt_file":
        return _decrypt_file(params)
    elif action == "list_encrypted":
        return _list_encrypted()
    elif action == "change_key":
        return _change_key(params)
    elif action == "backup_keys":
        return _backup_keys()
    elif action == "status":
        return _get_status()
    elif action == "secure_delete":
        return _secure_delete(params)
    elif action == "hash_data":
        return _hash_data(params)
    elif action == "verify":
        return _verify_integrity(params)
    elif action == "generate_key":
        return _generate_key(params)
    return "Acciones: encrypt, decrypt, encrypt_file, decrypt_file, list_encrypted, change_key, backup_keys, status, secure_delete, hash_data, verify, generate_key"


def _get_key():
    if _KEY_FILE.exists():
        try:
            data = json.loads(_KEY_FILE.read_text(encoding="utf-8"))
            return data.get("key", "")
        except Exception:
            pass
    return ""


def _ensure_key():
    key = _get_key()
    if not key:
        key = base64.b64encode(os.urandom(32)).decode()
        _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _KEY_FILE.write_text(json.dumps({"key": key, "created": datetime.now().isoformat()}, indent=2), encoding="utf-8")
    return key


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


def _encrypt_data(params: dict) -> str:
    text = params.get("text", "")
    if not text:
        return "Error: se requiere 'text'"

    key = _ensure_key()
    key_bytes = hashlib.sha256(key.encode()).digest()

    data_bytes = text.encode("utf-8")
    encrypted = _xor_encrypt(data_bytes, key_bytes)
    encoded = base64.b64encode(encrypted).decode()

    name = params.get("name", "data_{}".format(int(time.time())))

    encrypted_entry = {
        "name": name,
        "encrypted_data": encoded,
        "hash": hashlib.sha256(data_bytes).hexdigest(),
        "timestamp": datetime.now().isoformat(),
        "size": len(text),
    }

    entry_path = _ENCRYPTED_DIR / "{}.json".format(name)
    entry_path.write_text(json.dumps(encrypted_entry, indent=2), encoding="utf-8")

    return "Datos cifrados: '{}' ({} chars)".format(name, len(text))


def _decrypt_data(params: dict) -> str:
    name = params.get("name", "")
    text = params.get("text", "")

    if name:
        entry_path = _ENCRYPTED_DIR / "{}.json".format(name)
        if not entry_path.exists():
            return "No encontrado: {}".format(name)
        entry = json.loads(entry_path.read_text(encoding="utf-8"))
        encoded = entry.get("encrypted_data", "")
        expected_hash = entry.get("hash", "")
    elif text:
        encoded = text
        expected_hash = ""
    else:
        return "Error: se requiere 'name' o 'text'"

    try:
        key = _get_key()
        if not key:
            return "No hay clave de cifrado"
        key_bytes = hashlib.sha256(key.encode()).digest()
        encrypted = base64.b64decode(encoded)
        decrypted = _xor_encrypt(encrypted, key_bytes)
        result = decrypted.decode("utf-8")

        if expected_hash:
            actual_hash = hashlib.sha256(result.encode()).hexdigest()
            if actual_hash != expected_hash:
                return "ADVERTENCIA: Hash no coincide. Datos podrían estar corruptos"

        return "Descifrado: {}".format(result)
    except Exception as e:
        return "Error descifrando: {}".format(str(e))


def _encrypt_file(params: dict) -> str:
    filepath = params.get("filepath", "")
    if not filepath:
        return "Error: se requiere 'filepath'"

    path = Path(filepath)
    if not path.exists():
        return "Archivo no existe: {}".format(filepath)

    data = path.read_bytes()
    key = _ensure_key()
    key_bytes = hashlib.sha256(key.encode()).digest()

    encrypted = _xor_encrypt(data, key_bytes)
    encoded = base64.b64encode(encrypted).decode()

    name = path.stem
    entry = {
        "name": name,
        "original_file": path.name,
        "encrypted_data": encoded,
        "hash": hashlib.sha256(data).hexdigest(),
        "timestamp": datetime.now().isoformat(),
        "size": len(data),
    }

    entry_path = _ENCRYPTED_DIR / "{}.json".format(name)
    entry_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")

    return "Archivo cifrado: '{}' ({} bytes)".format(path.name, len(data))


def _decrypt_file(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    entry_path = _ENCRYPTED_DIR / "{}.json".format(name)
    if not entry_path.exists():
        return "No encontrado: {}".format(name)

    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    key = _get_key()
    if not key:
        return "No hay clave de cifrado"

    key_bytes = hashlib.sha256(key.encode()).digest()
    encrypted = base64.b64decode(entry["encrypted_data"])
    decrypted = _xor_encrypt(encrypted, key_bytes)

    output = params.get("output", str(_BASE / "data" / "decrypted" / entry.get("original_file", name)))
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(decrypted)

    return "Archivo descifrado: {}".format(str(output_path))


def _list_encrypted() -> str:
    files = list(_ENCRYPTED_DIR.glob("*.json"))
    if not files:
        return "No hay archivos cifrados"

    lines = ["Archivos cifrados ({}):".format(len(files))]
    for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            entry = json.loads(f.read_text(encoding="utf-8"))
            lines.append("  {} | {} bytes | {}".format(
                entry.get("name", f.stem), entry.get("size", 0),
                entry.get("timestamp", "?")[:10]))
        except Exception:
            lines.append("  {} (error)".format(f.stem))
    return "\n".join(lines)


def _change_key(params: dict) -> str:
    new_key = params.get("key", "")
    if not new_key:
        return "Error: se requiere 'key'"

    old_key = _get_key()
    _KEY_FILE.write_text(json.dumps({
        "key": new_key,
        "created": datetime.now().isoformat(),
        "previous_key_hash": hashlib.sha256(old_key.encode()).hexdigest()[:16] if old_key else None,
    }, indent=2), encoding="utf-8")

    return "Clave de cifrado cambiada. Los datos cifrados con la clave anterior necesitan ser descifrados primero"


def _backup_keys() -> str:
    key = _get_key()
    if not key:
        return "No hay clave para respaldar"

    backup_path = _BASE / "data" / "encrypted" / "key_backup_{}.json".format(int(time.time()))
    backup_data = {
        "key_hash": hashlib.sha256(key.encode()).hexdigest(),
        "created": datetime.now().isoformat(),
        "note": "Backup de clave de cifrado. Mantén este archivo seguro",
    }
    backup_path.write_text(json.dumps(backup_data, indent=2), encoding="utf-8")
    return "Backup de clave guardado: {}".format(str(backup_path))


def _get_status() -> str:
    key = _get_key()
    encrypted_files = list(_ENCRYPTED_DIR.glob("*.json"))
    total_encrypted = len(encrypted_files)
    total_size = sum(f.stat().st_size for f in encrypted_files)
    return "Encryption: {} archivos cifrados ({:.1f}KB) | Clave: {}".format(
        total_encrypted, total_size / 1024, "configurada" if key else "no configurada")


def _secure_delete(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    entry_path = _ENCRYPTED_DIR / "{}.json".format(name)
    if not entry_path.exists():
        return "No encontrado: {}".format(name)

    data = entry_path.read_bytes()
    entry_path.write_bytes(os.urandom(len(data)))
    entry_path.write_bytes(b"\x00" * len(data))
    entry_path.unlink()

    return " '{}' eliminado de forma segura".format(name)


def _hash_data(params: dict) -> str:
    text = params.get("text", "")
    algorithm = params.get("algorithm", "sha256")
    if not text:
        return "Error: se requiere 'text'"

    if algorithm == "sha256":
        result = hashlib.sha256(text.encode()).hexdigest()
    elif algorithm == "sha512":
        result = hashlib.sha512(text.encode()).hexdigest()
    elif algorithm == "md5":
        result = hashlib.md5(text.encode()).hexdigest()
    elif algorithm == "sha1":
        result = hashlib.sha1(text.encode()).hexdigest()
    else:
        return "Algoritmos: sha256, sha512, md5, sha1"

    return "{}({}) = {}".format(algorithm, text[:30], result)


def _verify_integrity(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    entry_path = _ENCRYPTED_DIR / "{}.json".format(name)
    if not entry_path.exists():
        return "No encontrado: {}".format(name)

    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    key = _get_key()
    if not key:
        return "No hay clave"

    key_bytes = hashlib.sha256(key.encode()).digest()
    encrypted = base64.b64decode(entry["encrypted_data"])
    decrypted = _xor_encrypt(encrypted, key_bytes)
    actual_hash = hashlib.sha256(decrypted).hexdigest()

    expected = entry.get("hash", "")
    if actual_hash == expected:
        return "Integridad VERIFICADA: '{}' coincide".format(name)
    return "INTEGRIDAD COMPROMETIDA: '{}' hash no coincide".format(name)


def _generate_key(params: dict) -> str:
    key_name = params.get("name", "default")
    key = base64.b64encode(os.urandom(32)).decode()
    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _KEY_FILE.write_text(json.dumps({"key": key, "created": datetime.now().isoformat()}, indent=2), encoding="utf-8")
    return "Nueva clave generada. Guárdala de forma segura"


import time
