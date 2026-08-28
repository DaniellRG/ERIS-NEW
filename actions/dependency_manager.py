# -*- coding: utf-8 -*-
"""
dependency_manager.py — Gestión de dependencias de ERIS.

Detecta imports rotos en el proyecto y los instala (pip). Acciones:
  scan    — recorre todos los .py, extrae imports de terceros y reporta los faltantes.
  install — instala 'packages' (lista o texto separado por espacios).
  auto    — scan + instala automáticamente los que faltan.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

_STDLIB = None


def _stdlib() -> set:
    global _STDLIB
    if _STDLIB is None:
        _STDLIB = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()
    return _STDLIB


def _third_party_imports() -> set:
    import re
    found = set()
    pat = re.compile(r"^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)")
    for p in PROJECT_DIR.rglob("*.py"):
        if (".git" in p.parts or "backups" in p.parts or "node_modules" in p.parts
                or ".venv" in p.parts or "venv" in p.parts):
            continue
        try:
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith(("import ", "from ")):
                        m = pat.match(line)
                        if m:
                            found.add(m.group(1).split(".")[0])
        except Exception:
            continue
    return found


def _missing(pkgs: set) -> list:
    import importlib.util
    local = {p.stem for p in PROJECT_DIR.rglob("*.py")
             if ".venv" not in p.parts and "venv" not in p.parts} | {p.stem for p in PROJECT_DIR.rglob("*.pyw")
             if ".venv" not in p.parts and "venv" not in p.parts}
    missing = []
    for name in sorted(pkgs):
        if name in _stdlib() or name in ("core", "actions", "ui", "tests", "tools", "memory"):
            continue
        if name == "__main__" or name in local:
            continue
        # nombres propios del proyecto o fragmentos (Footer, Nav, etc.)
        if len(name) < 3 or name[0].isupper():
            continue
        try:
            if importlib.util.find_spec(name) is None:
                missing.append(name)
        except (ImportError, AttributeError, ValueError):
            missing.append(name)
        except Exception:
            pass
    return missing


def _pip_install(pkgs: list) -> str:
    if not pkgs:
        return "Sin paquetes que instalar."
    cmd = [sys.executable, "-m", "pip", "install"]
    cmd.extend(pkgs)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return ((r.stdout or "") + (r.stderr or ""))[-2000:]
    except Exception as e:
        return f"[pip error] {e}"


def dependency_manager(parameters: dict = None, player=None) -> str:
    """Gestión de dependencias. Acciones: scan (imports faltantes), install (instala 'packages',
    lista o texto separado por espacios), auto (scan + instala faltantes)."""
    action = str(parameters.get("action") or "scan").lower()
    packages = parameters.get("packages")

    if action == "install":
        if isinstance(packages, str):
            pkgs = [p.strip() for p in packages.replace(",", " ").split() if p.strip()]
        elif isinstance(packages, list):
            pkgs = [str(p).strip() for p in packages if str(p).strip()]
        else:
            return "Error: se requiere 'packages' (lista o texto) para instalar."
        if player:
            try:
                player.write_log(f"[deps] instalando {', '.join(pkgs[:10])}")
            except Exception:
                pass
        return _pip_install(pkgs)

    if action == "scan":
        found = _third_party_imports()
        missing = _missing(found)
        if not missing:
            return "Scan OK: no hay imports rotos."
        return (f"Imports faltantes ({len(missing)}):\n" + "\n".join(missing)
                + "\nUsa action='install' con esos paquetes o action='auto'.")

    if action == "auto":
        found = _third_party_imports()
        missing = _missing(found)
        if player:
            try:
                player.write_log(f"[deps] {len(missing)} faltantes, instalando...")
            except Exception:
                pass
        return _pip_install(missing)

    return "Accion no valida. Disponibles: scan, install, auto."
