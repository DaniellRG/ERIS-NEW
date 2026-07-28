"""
core/updater.py - Sistema de actualizaciones de ERIS.
Verifica nuevas versiones via GitHub Releases API.
Descarga, hace backup y aplica actualizaciones automaticamente.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import threading
import urllib.request
import urllib.error
import zipfile
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_VERSION_FILE = _BASE_DIR / "core" / "version.py"
_API_CONFIG = _BASE_DIR / "config" / "api_keys.json"

# Directorios y archivos que NUNCA se sobrescriben durante un update
_PROTECTED_DIRS = {".venv", "backups", "data", "config", "__pycache__"}
_PROTECTED_FILES = {"eris.log", "eris_state.json", "api_keys.json"}


def current_version() -> str:
    """Lee la version actual desde core/version.py."""
    try:
        text = _VERSION_FILE.read_text(encoding="utf-8")
        match = re.search(r'ERIS_VERSION\s*=\s*["\']([^"\']+)["\']', text)
        if match:
            return match.group(1)
    except Exception:
        pass
    return "0.0.0"


def _get_repo() -> str | None:
    """Obtiene el repo de GitHub configurado para updates."""
    try:
        cfg = json.loads(_API_CONFIG.read_text(encoding="utf-8"))
        repo = cfg.get("update_github_repo", "")
        enabled = cfg.get("update_enabled", True)
        if repo and enabled:
            return repo
    except Exception:
        pass
    return None


def _parse_version(v: str) -> tuple:
    """Convierte '1.2.3' en (1, 2, 3) para comparacion."""
    parts = re.findall(r"\d+", v)
    return tuple(int(p) for p in parts[:3]) if parts else (0, 0, 0)


def check_for_update() -> dict | None:
    """
    Verifica si hay una nueva version en GitHub Releases.
    Retorna dict con version, current, notes, url, size_mb o None si no hay update / no hay repo.
    """
    repo = _get_repo()
    if not repo:
        return None  # No hay repo configurado - no es error, solo no verifica

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ERIS-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return None

    latest_tag = data.get("tag_name", "") or data.get("name", "")
    if not latest_tag:
        return None

    latest_ver = latest_tag.lstrip("v")
    current_ver = current_version()

    if _parse_version(latest_ver) <= _parse_version(current_ver):
        return None  # Ya esta actualizado

    # Extraer info del release
    notes = data.get("body", "Sin notas de version.")
    assets = data.get("assets", [])
    download_url = ""
    size_bytes = 0
    for asset in assets:
        name = asset.get("name", "").lower()
        if name.endswith(".zip"):
            download_url = asset.get("browser_download_url", "")
            size_bytes = asset.get("size", 0)
            break

    if not download_url:
        download_url = data.get("zipball_url", "")

    size_mb = round(size_bytes / (1024 * 1024), 1) if size_bytes else 0

    return {
        "version": latest_ver,
        "current": current_ver,
        "notes": notes[:500],
        "url": download_url,
        "size_mb": size_mb,
    }


def _download_sha256(url: str) -> str | None:
    """Download SHA-256 hash from a .sha256 file next to the ZIP URL."""
    sha_url = url + ".sha256"
    try:
        req = urllib.request.Request(sha_url, headers={"User-Agent": "ERIS-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8").strip().split()[0]
    except Exception:
        return None


def _verify_sha256(file_path: str, expected: str) -> bool:
    """Verify file matches expected SHA-256 hash."""
    import hashlib
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest().lower() == expected.lower()
    except Exception:
        return False


def _verify_integrity() -> list[str]:
    """Verify critical files exist and are parseable after update. Returns list of issues."""
    issues = []
    critical = [
        _BASE_DIR / "main.py",
        _BASE_DIR / "ui.py",
        _BASE_DIR / "core" / "prompt.txt",
    ]
    for f in critical:
        if not f.exists():
            issues.append(f"Archivo critico faltante: {f.name}")
            continue
        if f.suffix == ".py":
            try:
                import py_compile
                py_compile.compile(str(f), doraise=True)
            except py_compile.PyCompileError as e:
                issues.append(f"Error de sintaxis en {f.name}: {e}")
    return issues


def _is_busy() -> bool:
    """Check if ERIS is currently executing a tool (non-blocking heuristic)."""
    try:
        import psutil
        proc = psutil.Process()
        for _ in proc.children():
            if _.status() == "running":
                return True
    except Exception:
        pass
    return False


def rollback(timestamp: str = "") -> tuple[bool, str]:
    """
    Restore files from a backup. If timestamp is empty, use the most recent backup.
    Returns (success, message).
    """
    backup_base = _BASE_DIR / "backups"
    if not backup_base.exists():
        return False, "No hay directorio de backups."

    if timestamp:
        backup_dir = backup_base / f"update_backup_{timestamp}"
    else:
        backups = sorted(backup_base.glob("update_backup_*"), reverse=True)
        if not backups:
            return False, "No hay backups disponibles."
        backup_dir = backups[0]
        timestamp = backup_dir.name.replace("update_backup_", "")

    if not backup_dir.exists():
        return False, f"Backup no encontrado: update_backup_{timestamp}"

    restored = 0
    errors = []
    for f in backup_dir.rglob("*"):
        if f.is_file():
            target = _BASE_DIR / f.relative_to(backup_dir)
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(f), str(target))
                restored += 1
            except Exception as e:
                errors.append(str(e))

    if errors:
        return True, f"Rollback parcial desde update_backup_{timestamp}: {restored} archivos restaurados, {len(errors)} errores: {'; '.join(errors[:3])}"
    return True, f"Rollback completado desde update_backup_{timestamp}: {restored} archivos restaurados."


def restart_app() -> None:
    """Restart ERIS application."""
    import sys
    python = sys.executable
    script = sys.argv[0]
    os.execl(python, python, script)


def apply_update(url: str, *, auto_restart: bool = False) -> tuple[bool, str]:
    """
    Descarga el ZIP de actualizacion, verifica SHA-256, hace backup y aplica los cambios.
    Preserva config/, data/, .venv/, y archivos protegidos.
    Retorna (exito, mensaje).
    """
    if not url:
        return False, "No se proporciono URL de actualizacion."

    if _is_busy():
        return False, "ERIS está ejecutando comandos. Esperá a que termine antes de actualizar."

    repo = _get_repo()
    if not repo and not url.startswith("http"):
        return False, "No hay repo de actualizacion configurado en api_keys.json."

    tmp_dir = None
    try:
        # Descargar ZIP
        tmp_dir = tempfile.mkdtemp(prefix="eris_update_")
        zip_path = os.path.join(tmp_dir, "update.zip")

        req = urllib.request.Request(url, headers={"User-Agent": "ERIS-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(zip_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)

        # Verificar SHA-256 si está disponible
        expected_hash = _download_sha256(url)
        if expected_hash:
            if not _verify_sha256(zip_path, expected_hash):
                return False, "La verificacion SHA-256 del ZIP descargado fallo. La descarga puede estar corrupta o no es oficial."
        else:
            import logging
            logging.getLogger("updater").warning("No se pudo verificar SHA-256 (sin archivo .sha256 en el release)")

        # Extraer ZIP
        extract_dir = os.path.join(tmp_dir, "extracted")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Encontrar el directorio raiz del proyecto dentro del ZIP
        project_root = extract_dir
        entries = os.listdir(extract_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
            project_root = os.path.join(extract_dir, entries[0])

        # Backup de archivos que se van a sobrescribir
        backup_dir = str(_BASE_DIR / "backups" / f"update_backup_{_timestamp()}")
        os.makedirs(backup_dir, exist_ok=True)

        # Aplicar archivos (preservando protegidos)
        updated_count = 0
        skipped_count = 0

        for dirpath, dirnames, filenames in os.walk(project_root):
            rel_dir = os.path.relpath(dirpath, project_root)
            top_dir = rel_dir.split(os.sep)[0] if rel_dir != "." else ""
            if top_dir in _PROTECTED_DIRS:
                continue

            for filename in filenames:
                if filename in _PROTECTED_FILES:
                    skipped_count += 1
                    continue

                src = os.path.join(dirpath, filename)
                dst_rel = os.path.relpath(src, project_root)
                dst = str(_BASE_DIR / dst_rel)

                os.makedirs(os.path.dirname(dst), exist_ok=True)

                if os.path.exists(dst):
                    backup_path = os.path.join(backup_dir, dst_rel)
                    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                    shutil.copy2(dst, backup_path)

                shutil.copy2(src, dst)
                updated_count += 1

        # Verificar integridad post-actualizacion
        integrity_issues = _verify_integrity()
        if integrity_issues:
            return False, f"Actualizacion completada pero con errores de integridad: {'; '.join(integrity_issues)}. Usa rollback() para restaurar."

        msg = f"Actualizacion aplicada: {updated_count} archivos actualizados, {skipped_count} protegidos preservados. Backup en: {backup_dir}"

        # Auto-restart si se solicito
        if auto_restart:
            import threading
            threading.Thread(target=restart_app, daemon=False).start()
            return True, msg + " Reiniciando ERIS..."

        return True, msg

    except urllib.error.URLError as e:
        return False, f"Error de red al descargar: {e}"
    except zipfile.BadZipFile:
        return False, "El archivo descargado no es un ZIP valido."
    except Exception as e:
        return False, f"Error aplicando actualizacion: {e}"
    finally:
        if tmp_dir and os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except Exception:
                pass


def check_in_background(callback) -> None:
    """
    Verifica updates en un thread daemon (no bloquea el startup).
    Si hay update nuevo, llama callback(info_dict).
    """
    def _check():
        try:
            import time
            time.sleep(5)  # Esperar a que ERIS arranque completamente
            info = check_for_update()
            if info and callback:
                callback(info)
        except Exception:
            pass  # Silencioso - no romper el startup

    t = threading.Thread(target=_check, daemon=True, name="ERIS-UpdateChecker")
    t.start()


def _timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")
