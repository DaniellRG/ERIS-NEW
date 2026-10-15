"""
zone_policy.py — Política de ZONAS de ERIS (diseño §6).

Traduce "protegido" vs "libre" a reglas concretas, legibles y editables por el
dueño en `config/zone_policy.json`. La usan:
  - el árbitro de riesgo `core/permission_gate.py` (el punto común a TODOS los
    caminos de ejecución), y
  - el motor de barreras (`core/barrier_engine.py`) para su pre-chequeo.

Reglas:
  - **protegida** (SO, datos personales, red de casa) → SIEMPRE pide OK.
  - **libre** (su propio proyecto/workspace/lab) → puede sola.
  - **desconocida** → no es zona protegida por sí misma; la decide el riesgo
    normal del árbitro.

Sin archivo, usa los valores por defecto de acá (fail-safe: la protección no
depende de que exista el archivo).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_POLICY_FILE = _BASE / "config" / "zone_policy.json"

_cache: dict | None = None
_mtime: float = 0.0


def _default() -> dict:
    return {
        "protegida": [
            {"regla": "so", "motivo": "Sistema operativo", "patrones": [
                "/etc/", "/usr/", "/boot/", "/sys/", "/proc/", "/dev/sd", "/dev/nvme",
                "/dev/mmcblk", "mkfs", "fdisk", "parted", "dd if=", "dd of=", "grub",
                "update-grub", "sudo ", "doas ", "su -", "systemctl ", "systemd",
                "journalctl", "apt install", "apt-get install", "apt remove",
                "pacman -s", "dnf install", "yum install", "chmod 777 /",
            ]},
            {"regla": "personal", "motivo": "Datos personales", "patrones": [
                "~/.ssh", "/.ssh/", "id_rsa", "id_ed25519", "known_hosts",
                "authorized_keys", "~/.gnupg", "/.gnupg/", ".password-store",
                "keyrings", "login data", ".mozilla/", "google-chrome", "/chromium/",
                "~/.bash_history", "/.zsh_history", "cookies", "documentos del usuario",
            ]},
            {"regla": "red", "motivo": "Red de casa", "patrones": [
                "0.0.0.0", "bind 0.0.0.0", "upnp", "iptables", "nft ", "router",
                "192.168.0.", "192.168.1.", "10.0.0.", "ssid", "public ip",
                "ipinfo.io", "ifconfig.me", "wpa_passphrase", "nmcli dev",
            ]},
        ],
        "libre": [
            {"regla": "proyecto", "motivo": "Su propio proyecto", "patrones": [
                "eris-new/", "eris-new ", "libraries/", "actions/custom/",
                "skills/user_created/", "data/barreras", "data/pentest", "workspace",
            ]},
            {"regla": "lab", "motivo": "Laboratorio aislado", "patrones": ["192.168.56."]},
        ],
    }


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _load() -> dict:
    global _cache, _mtime
    try:
        if _POLICY_FILE.exists():
            m = _POLICY_FILE.stat().st_mtime
            if m != _mtime or _cache is None:
                raw = json.loads(_POLICY_FILE.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and ("protegida" in raw or "libre" in raw):
                    _cache = raw
                    _mtime = m
                    return _cache
    except Exception:
        pass
    return _default()


def evaluar_zona(texto: str) -> dict:
    """Clasifica un texto (comando/ruta/parámetro) en protegida/libre/desconocida."""
    t = _norm(texto)
    if not t:
        return {"zona": "desconocida", "motivo": "", "regla": "", "match": ""}
    pol = _load()
    for regla in pol.get("protegida", []):
        for p in regla.get("patrones", []):
            if _norm(p) in t:
                return {"zona": "protegida", "motivo": regla.get("motivo", ""),
                        "regla": regla.get("regla", ""), "match": p}
    for regla in pol.get("libre", []):
        for p in regla.get("patrones", []):
            if _norm(p) in t:
                return {"zona": "libre", "motivo": regla.get("motivo", ""),
                        "regla": regla.get("regla", ""), "match": p}
    return {"zona": "desconocida", "motivo": "", "regla": "", "match": ""}


def es_protegida(texto: str) -> bool:
    return evaluar_zona(texto).get("zona") == "protegida"


# Campos de una llamada a tool que SÍ se evalúan por zona (operaciones reales).
# Se excluyen a propósito query/text/description (una búsqueda sobre "sudo" no
# es una operación sobre la zona) para no generar falsos positivos.
_CAMPOS_OPERATIVOS = (
    "command", "cmd", "path", "file", "filepath", "file_path", "dir", "directory",
    "target", "url", "host", "bind", "interface", "source", "destination",
)


def texto_de(tool_name: str, params: dict) -> str:
    """Arma el texto a evaluar por zona para una llamada (best-effort)."""
    if not isinstance(params, dict):
        return ""
    partes = []
    for k in _CAMPOS_OPERATIVOS:
        v = params.get(k)
        if isinstance(v, str) and v.strip():
            partes.append(v)
    return " ".join(partes)
