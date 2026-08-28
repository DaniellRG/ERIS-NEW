from __future__ import annotations

"""Password Vault — Local encrypted password manager using Fernet (cryptography).

Actions
-------
init          – Create a new vault locked with a master password.
add           – Store a new credential entry.
get           – Retrieve a password (requires master).
list          – List stored sites (no secrets).
search        – Search entries by keyword.
delete        – Remove an entry.
generate      – Create a cryptographically random password.
export        – Export the vault as encrypted JSON.
change_master – Re-encrypt the vault with a new master password.
"""

import base64
import json
import os
import secrets
import string
from typing import Any

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    Fernet = None  # type: ignore[assignment,misc]

_VAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vault.enc")
_META_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vault_meta.json")
os.makedirs(os.path.dirname(_VAULT_PATH), exist_ok=True)


def _derive_key(master: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480_000)
    return base64.urlsafe_b64encode(kdf.derive(master.encode("utf-8")))


def _load_meta() -> dict[str, Any]:
    if os.path.isfile(_META_PATH):
        with open(_META_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _save_meta(meta: dict[str, Any]) -> None:
    with open(_META_PATH, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)


def _decrypt_vault(master: str) -> dict[str, Any]:
    meta = _load_meta()
    if not meta:
        return {}
    if Fernet is None:
        raise RuntimeError("cryptography is not installed.")
    salt = base64.b64decode(meta["salt"])
    key = _derive_key(master, salt)
    f = Fernet(key)
    with open(_VAULT_PATH, "rb") as fh:
        encrypted = fh.read()
    decrypted = f.decrypt(encrypted)
    return json.loads(decrypted.decode("utf-8"))


def _encrypt_vault(data: dict[str, Any], master: str) -> None:
    if Fernet is None:
        raise RuntimeError("cryptography is not installed.")
    meta = _load_meta()
    salt = base64.b64decode(meta["salt"]) if "salt" in meta else os.urandom(16)
    if "salt" not in meta:
        _save_meta({"salt": base64.b64encode(salt).decode()})
    key = _derive_key(master, salt)
    f = Fernet(key)
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    with open(_VAULT_PATH, "wb") as fh:
        fh.write(f.encrypt(payload))


def vault_passwords(parameters: dict = None, player=None) -> str:  # noqa: C901, PLR0912
    """Encrypted local password vault."""
    if Fernet is None:
        return "Error: cryptography is not installed. Run: pip install cryptography"

    params = parameters or {}
    action = str(params.get("action", "list")).strip().lower()
    master = str(params.get("master", "")).strip()
    site = str(params.get("site", "")).strip()
    username = str(params.get("username", "")).strip()
    password = str(params.get("password", "")).strip()
    notes = str(params.get("notes", "")).strip()
    category = str(params.get("category", "")).strip()
    query = str(params.get("query", "")).strip()
    new_master = str(params.get("new_master", "")).strip()
    old_master = str(params.get("old_master", "")).strip()
    length = int(str(params.get("length", 16)).strip() or 16)
    include_symbols = str(params.get("include_symbols", "true")).strip().lower() != "false"

    if action == "init":
        if not master:
            return "Error: Master password required."
        meta = _load_meta()
        if "salt" in meta and os.path.isfile(_VAULT_PATH):
            return "Error: Vault already exists. Use change_master to update."
        salt = os.urandom(16)
        _save_meta({"salt": base64.b64encode(salt).decode()})
        _encrypt_vault({"entries": []}, master)
        return "Vault initialized."

    if action == "add":
        if not master or not site:
            return "Error: Master password and site required."
        try:
            vault = _decrypt_vault(master)
        except Exception:
            return "Error: Invalid master password."
        vault.setdefault("entries", [])
        vault["entries"].append({
            "site": site,
            "username": username,
            "password": password,
            "notes": notes,
            "category": category,
            "created": __import__("datetime").datetime.now().isoformat(),
        })
        _encrypt_vault(vault, master)
        return f"Entry added for '{site}'."

    if action == "get":
        if not master or not site:
            return "Error: Master password and site required."
        try:
            vault = _decrypt_vault(master)
        except Exception:
            return "Error: Invalid master password."
        for entry in vault.get("entries", []):
            if entry.get("site", "").lower() == site.lower():
                return json.dumps(entry, indent=2, ensure_ascii=False)
        return f"Error: No entry found for '{site}'."

    if action == "list":
        if not master:
            return "Error: Master password required."
        try:
            vault = _decrypt_vault(master)
        except Exception:
            return "Error: Invalid master password."
        entries = vault.get("entries", [])
        if category:
            entries = [e for e in entries if e.get("category", "").lower() == category.lower()]
        if not entries:
            return "Vault is empty." if not category else f"No entries in category '{category}'."
        sites = [f"  • {e.get('site', '?')} [{e.get('category', 'uncat')}] — {e.get('username', '')}" for e in entries]
        return f"Entries ({len(sites)}):\n" + "\n".join(sites)

    if action == "search":
        if not master:
            return "Error: Master password required."
        q = query.lower()
        if not q:
            return "Error: No query provided."
        try:
            vault = _decrypt_vault(master)
        except Exception:
            return "Error: Invalid master password."
        matches = [e for e in vault.get("entries", []) if q in e.get("site", "").lower() or q in e.get("username", "").lower() or q in e.get("notes", "").lower()]
        if not matches:
            return f"No results for '{query}'."
        lines = [f"  • {e.get('site', '?')} — {e.get('username', '')}" for e in matches]
        return f"Results ({len(matches)}):\n" + "\n".join(lines)

    if action == "delete":
        if not master or not site:
            return "Error: Master password and site required."
        try:
            vault = _decrypt_vault(master)
        except Exception:
            return "Error: Invalid master password."
        before = len(vault.get("entries", []))
        vault["entries"] = [e for e in vault.get("entries", []) if e.get("site", "").lower() != site.lower()]
        after = len(vault["entries"])
        if before == after:
            return f"Error: No entry found for '{site}'."
        _encrypt_vault(vault, master)
        return f"Deleted entry for '{site}'."

    if action == "generate":
        chars = string.ascii_letters + string.digits
        if include_symbols:
            chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
        pw = "".join(secrets.choice(chars) for _ in range(length))
        return f"Generated password: {pw}"

    if action == "export":
        if not master:
            return "Error: Master password required."
        try:
            vault = _decrypt_vault(master)
        except Exception:
            return "Error: Invalid master password."
        export_path = os.path.join(os.path.dirname(_VAULT_PATH), "vault_export.json.enc")
        payload = json.dumps(vault, ensure_ascii=False).encode("utf-8")
        meta = _load_meta()
        salt = base64.b64decode(meta["salt"])
        key = _derive_key(master, salt)
        f = Fernet(key)
        with open(export_path, "wb") as fh:
            fh.write(f.encrypt(payload))
        return f"Vault exported to: {export_path}"

    if action == "change_master":
        if not old_master or not new_master:
            return "Error: Both old_master and new_master required."
        try:
            vault = _decrypt_vault(old_master)
        except Exception:
            return "Error: Invalid current master password."
        salt = os.urandom(16)
        _save_meta({"salt": base64.b64encode(salt).decode()})
        _encrypt_vault(vault, new_master)
        return "Master password changed successfully."

    return f"Error: Unknown action '{action}'."
