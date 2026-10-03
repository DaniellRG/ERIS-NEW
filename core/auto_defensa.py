# -*- coding: utf-8 -*-
"""core/auto_defensa.py — AUTO-DEFENSA PREVENTIVA de ERIS.

Audita la PROPIA máquina (nunca ataca nada): compara puertos loopback vs
expuestos, busca sudo NOPASSWD, updates pendientes, permisos de
/etc/passwd|shadow|sudoers, presencia de sshd y CVEs críticos conocidos del
lab. El pentest real queda SOLO en el lab VirtualBox 192.168.56.0/24
(`pentest_lab`).

Persistencia:
  - data/self_defense_log.jsonl   (bitácora append-only, una línea por tick)
  - data/self_defense_state.json  (último informe + hallazgos)

Integración:
  - `defensa_tick()` lo llama `core/self_evolution.run_evolution_tick` (cada 9
    ticks).
  - `auto_defensa` es el alias expuesto como tool que consume
    `core/action_imports.py`.

Todo es defensivo y read-only: solo lee estado del sistema. Degrada elegante
si falta una herramienta del SO (devuelve texto, nunca crashea).
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import threading
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_DATA = _BASE / "data"
_LOG_FILE = _DATA / "self_defense_log.jsonl"
_STATE_FILE = _DATA / "self_defense_state.json"
_lock = threading.Lock()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _run(cmd: list, timeout: int = 8) -> str:
    """Ejecuta un comando read-only; '' si falla o no existe."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + (r.stderr or "")
    except Exception:
        return ""


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"created": datetime.now().isoformat(), "ticks": 0, "ultimo": None,
            "hallazgos": []}


def _save_state(state: dict):
    try:
        _DATA.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    except Exception:
        pass


def _log(entry: dict):
    try:
        _DATA.mkdir(parents=True, exist_ok=True)
        with open(str(_LOG_FILE), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _notify(texto: str):
    try:
        from core.todo_yo import registrar_novedad
        registrar_novedad(texto)
    except Exception:
        pass


# ── Auditorías (read-only, defensivas) ────────────────────────────────────────

def _auditar_puertos() -> list:
    """Puertos en escucha: separa loopback (ok) de expuestos (a revisar)."""
    hallazgos = []
    out = _run(["ss", "-tlnH"]) or _run(["netstat", "-tln"])
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        local = ""
        for p in parts:
            if ":" in p and not p.startswith(("LISTEN", "tcp", "udp")):
                local = p
                break
        if not local:
            continue
        addr = local.rsplit(":", 1)[0]
        if addr in ("127.0.0.1", "[::1]", "::1"):
            continue
        hallazgos.append("Puerto expuesto fuera de loopback: {}".format(local))
    return hallazgos[:10]


def _auditar_sudo() -> list:
    out = _run(["sudo", "-n", "-l"]) if platform.system() != "Windows" else ""
    if "NOPASSWD" in out:
        return ["sudo NOPASSWD detectado (revisar /etc/sudoers)"]
    return []


def _auditar_permisos() -> list:
    hallazgos = []
    if platform.system() == "Windows":
        return hallazgos
    for f in ("/etc/passwd", "/etc/shadow", "/etc/sudoers"):
        out = _run(["stat", "-c", "%a %n", f]).strip()
        if out:
            hallazgos.append("Permisos {} ".format(out))
    return hallazgos


def _auditar_updates() -> list:
    hallazgos = []
    if platform.system() == "Windows":
        return hallazgos
    # No ejecutamos el update completo: solo contamos pendientes si hay caché.
    out = _run(["bash", "-lc", "checkupdates 2>/dev/null | wc -l"], timeout=12)
    n = out.strip().splitlines()[-1].strip() if out.strip() else ""
    if n.isdigit() and int(n) > 0:
        hallazgos.append("{} actualizaciones pendientes".format(n))
    return hallazgos


def _auditar_sshd() -> list:
    hallazgos = []
    out = _run(["ss", "-tlnH"]) 
    if ":22 " in out or ":22\n" in out or out.rstrip().endswith(":22"):
        hallazgos.append("sshd escuchando en puerto 22 (verificar si es intencional)")
    return hallazgos


def _cves_lab() -> list:
    """CVEs críticos conocidos del lab (referencia defensiva, no ataque)."""
    return [
        "CVE-2011-2523 (vsftpd 2.3.4 backdoor) — vigilar si un FTP expuesto usa esa versión",
        "CVE-2007-2447 (Samba usermap_script RCE) — vigilar Samba antiguo expuesto",
    ]


def _auditar() -> dict:
    hallazgos = []
    hallazgos += _auditar_puertos()
    hallazgos += _auditar_sudo()
    hallazgos += _auditar_permisos()
    hallazgos += _auditar_updates()
    hallazgos += _auditar_sshd()
    return {
        "fecha": _now(),
        "plataforma": "{} {}".format(platform.system(), platform.release()),
        "hallazgos": hallazgos,
        "cves_vigilados": _cves_lab(),
        "veredicto": "sin hallazgos críticos" if not hallazgos else "{} puntos a revisar".format(len(hallazgos)),
    }


# ── Tick ──────────────────────────────────────────────────────────────────────

def defensa_tick() -> str:
    """Un tick de auto-defensa: audita la máquina y registra la bitácora."""
    with _lock:
        state = _load_state()
        state["ticks"] = int(state.get("ticks", 0)) + 1
        informe = _auditar()
        state["ultimo"] = informe
        state["hallazgos"] = informe["hallazgos"][-20:]
        _save_state(state)
        _log({"tick": state["ticks"], **informe})

    resumen = ("🛡️ Auto-defensa #{}: {} ({}).".format(
        state["ticks"], informe["veredicto"],
        "; ".join(informe["hallazgos"][:3]) if informe["hallazgos"] else "todo en orden"))
    if informe["hallazgos"]:
        _notify("Auto-defensa detectó: {}".format("; ".join(informe["hallazgos"][:2])))
    return resumen


def auto_defensa(parameters: dict = None, player=None) -> str:
    """Tool `auto_defensa`: corre un tick o reporta el último informe."""
    p = parameters or {}
    action = p.get("action", "tick")
    if action in ("tick", "run", "auditar"):
        return defensa_tick()
    if action in ("status", "estado"):
        state = _load_state()
        inf = state.get("ultimo") or {}
        lines = ["🛡️ Auto-defensa — estado",
                 "Ticks: {}".format(state.get("ticks", 0)),
                 "Último: {}".format(inf.get("fecha", "-")),
                 "Veredicto: {}".format(inf.get("veredicto", "-"))]
        for h in inf.get("hallazgos", [])[:10]:
            lines.append("  · " + h)
        return "\n".join(lines)
    if action in ("cves", "cves_lab"):
        return "\n".join("· " + c for c in _cves_lab())
    return "Acciones: tick | status | cves"


if __name__ == "__main__":
    print(defensa_tick())
    print(auto_defensa({"action": "status"}))
