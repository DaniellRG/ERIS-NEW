"""Evolución continua de ERIS.

Autoconocimiento vivo (inventario real de herramientas), auditoría de salud
(447 tools importan y se resuelven), persistencia de TODO en Obsidian, y un
bucle antir-estancamiento: cada tick aplica una micro-mejora real sobre su
propio código (con backup + validación + rollback) o consolida conocimiento.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE = _MEM / "self_evolution_state.json"
_BACKUP_DIR = _MEM / "self_evol_backups"
_KNOW = _BASE / "data" / "knowledge"
_DOC = _KNOW / "eris_inventario_vivo.md"

_VAULT = Path(os.environ.get("ERIS_OBSIDIAN_VAULT",
                             str(_BASE / "vault"))).expanduser()

_OWN_SOURCES = [
    "core/code_guard.py",
    "core/mission_agent.py",
    "core/tool_registry.py",
]
_PROTECTED = {"core/self_evolution.py"}
_MIN_SECONDS_BETWEEN_FIXES = 120

_VERSION_PATTERN = re.compile(r"(\d{2,4}) tools")


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _tag():
    return datetime.now().strftime("%Y-%m-%d")


def _load_state() -> dict:
    try:
        if _STATE.exists():
            return json.loads(_STATE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_state(data: dict):
    try:
        _STATE.parent.mkdir(parents=True, exist_ok=True)
        _STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    except Exception:
        pass


def vault_note(folder: str, title: str, content: str) -> str:
    """Guarda una nota en el vault real de Obsidian y devuelve ruta relativa."""
    _VAULT.mkdir(parents=True, exist_ok=True)
    d = _VAULT / folder
    d.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[<>:"/\\|?*]', "_", title).strip() or "Sin titulo"
    f = d / f"{safe}.md"
    f.write_text(content, encoding="utf-8")
    return str(f.relative_to(_VAULT))


def log_vault(tag: str, lines: list):
    """Escribe (append) una entrada en Logs/Evolución de Obsidian."""
    f = _VAULT / "Logs" / f"Evolución - {_tag()}.md"
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        body = f.read_text(encoding="utf-8") if f.exists() else (
            f"# Evolución de ERIS — {_tag()}\n(Raíz de Obsidian). Cada tick "
            "deja su huella acá.\n\n")
        body += f"\n## {_now()}\n" + "\n".join(f"- {l}" for l in lines) + "\n"
        f.write_text(body, encoding="utf-8")
    except Exception:
        return None
    return str(f.relative_to(_VAULT))


def _declared_tools() -> list:
    sys.path.insert(0, str(_BASE))
    from core.tool_declarations import TOOL_DECLARATIONS
    out = []
    for d in TOOL_DECLARATIONS:
        out.append({"name": d.get("name", "?"),
                    "description": d.get("description", "") or ""})
    return out


def _all_tool_names() -> list:
    """Los tools REALES que resuelven (el registry): es su conteo canónico.
    Las declaraciones pueden tener extras dinámicos (custom_tools.json) sin
    romper la sync, pero el número que dice quién es son los registrados."""
    sys.path.insert(0, str(_BASE))
    from core.tool_registry import get_all_tool_names
    return sorted(get_all_tool_names())


def health() -> str:
    """Auditoría real: cada tool declarada debe importar y resolver."""
    sys.path.insert(0, str(_BASE))
    from core.tool_registry import get_all_tool_names, get_tool
    names = sorted(get_all_tool_names())
    ok, broken = 0, []
    for n in names:
        try:
            get_tool(n)
            ok += 1
        except Exception as e:
            broken.append(f"{n} ({type(e).__name__})")
    _save_state({"last_health": _now(), "total": len(names), "ok": ok,
                 "broken": broken})
    if broken:
        return (f"Salud: {ok}/{len(names)} OK, {len(broken)} SIN RESOLVER: "
                + "; ".join(broken))
    return f"Salud PERFECTA: {ok}/{len(names)} tools declaradas, activas y resolviendo."


def build_inventory_md() -> int:
    """Genera 'eris_inventario_vivo.md' (su mapa de capacidades real).
    Se construye desde el REGISTRY (tools que de verdad resuelven), con la
    descripción de la declaración cuando existe."""
    names = _all_tool_names()
    by_name = {d["name"]: d["description"] for d in _declared_tools()}
    groups = {}
    for n in names:
        key = n.split("_")[0]
        groups.setdefault(key, []).append((n, by_name.get(n, "")))
    lines = ["# ERIS — INVENTARIO VIVO DE CAPACIDADES",
             f"Generado: {_now()} · {len(names)} tools registradas y resolviendo.",
             ""]
    for key in sorted(groups):
        lines.append(f"## {key}")
        for name, desc in groups[key]:
            lines.append(f"- `{name}` — {desc.replace(chr(10), ' ')[:110]}")
        lines.append("")
    _KNOW.mkdir(parents=True, exist_ok=True)
    _DOC.write_text("\n".join(lines), encoding="utf-8")
    return len(names)


def inventory() -> str:
    n = build_inventory_md()
    title = f"Inventario de Capacidades ({n})"
    rel = vault_note("Tools", title, _DOC.read_text(encoding="utf-8"))
    _save_state({"last_inventory": _now(), "tools": n, "doc": str(_DOC)})
    return (f"Inventario regenerado: {n} tools. Vault: {rel} · "
            f"doc: {_DOC}")


def _rectify_counts() -> list:
    """Normaliza el conteo de tools en prompt/README/AGENTS al conteo REAL
    (registry, no declaraciones: las custom_tools dinámicas no suman)."""
    actual = len(_all_tool_names())
    touched = []
    for rel in ("core/prompt.txt", "README.md", "AGENTS.md"):
        p = _BASE / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        new = _VERSION_PATTERN.sub(lambda m: f"{actual} tools", text)
        if new != text:
            p.write_text(new, encoding="utf-8")
            touched.append(rel)
    return touched


def rectify() -> str:
    fixed = _rectify_counts()
    n = build_inventory_md()
    out = f"Rectificación: {n} tools. Conteos normalizados en: {fixed or 'ninguno'}."
    log_vault("rectificación", [out])
    return out


def _fixable_f401(path: Path) -> int | None:
    """Devuelve línea (1-based) de una F401 (import sin uso) si existe."""
    sys.path.insert(0, str(_BASE))
    from core.code_guard import _ruff_diags
    for d in _ruff_diags(path):
        if d.get("code") == "F401":
            return d.get("line")
    return None


def run_micro_fix(path: Path) -> str:
    """Elimina una F401 (import sin uso) con backup + validación + rollback."""
    rel = str(path).replace(str(_BASE), "").lstrip("\\/")
    if rel in _PROTECTED:
        return f"Omitido {rel}: archivo protegido del auto-parche."
    lineno = _fixable_f401(path)
    if not lineno:
        return f"Sin mejoras certeras en {rel}."
    st = _load_state()
    last = st.get("last_fix_time", 0)
    if (datetime.now().timestamp() - last) < _MIN_SECONDS_BETWEEN_FIXES:
        return "Cooldown: esperando antes del próximo micro-fix."
    from core.code_guard import _validate_file
    try:
        original = path.read_text(encoding="utf-8")
    except Exception as e:
        return f"No pude leer {rel}: {e}"
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    (_BACKUP_DIR / f"{tag}_{path.name}").write_bytes(path.read_bytes())
    lines = original.splitlines()
    if lineno - 1 >= len(lines):
        return f"No válido {rel}: línea {lineno} fuera de rango."
    removed = lines[lineno - 1]
    del lines[lineno - 1]
    new = "\n".join(lines)
    if not new.endswith("\n"):
        new += "\n"
    try:
        path.write_text(new, encoding="utf-8")
    except Exception as e:
        return f"Fallo al escribir {rel}: {e}"
    if not _validate_file(path):
        path.write_text(original, encoding="utf-8")
        return (f"Parche en {rel} invalidó el código; revertí (import "
                f"'{removed.strip()}' restaurado).")
    st["last_fix_time"] = datetime.now().timestamp()
    st["last_fix"], st["last_fix_when"] = rel, _now()
    _save_state(st)
    msg = (f"Micro-mejora aplicada en {rel}: quité la F401 "
           f"('{removed.strip()}'). Backup + validación OK.")
    log_vault("micro-mejoras", [msg])
    return msg


def evolve(dry_run: bool = False, targets: list | None = None) -> str:
    """Un paso de evolución: mejora certera si hay, si no consolida."""
    if targets is not None:
        srcs = [Path(t) for t in targets]
    else:
        srcs = [_BASE / s for s in _OWN_SOURCES]
    if not dry_run:
        for p in srcs:
            if p.exists() and _fixable_f401(p):
                return run_micro_fix(p)
    else:
        pending = [str(p) for p in srcs if p.exists() and _fixable_f401(p)]
        if pending:
            return f"[dry-run] Corregiría: " + ", ".join(pending)
    n = build_inventory_md()
    st = _load_state()
    log_vault("consolidación", [
        f"Sin micro-mejora pendiente → consolidé inventario ({n} tools).",
        f"Último micro-fix: {st.get('last_fix') or 'nunca'} ({st.get('last_fix_when') or '-'})",
    ])
    return ("Sin mejoras certeras pendientes → consolidé mi autoconocimiento "
            f"({n} tools). Nada queda quieto: cada tick dejo huella en Obsidian.")


def run_evolution_tick() -> str:
    """Tick del loop de evolución continua (lo llama el hilo de main)."""
    try:
        out = evolve()
        log_vault("evolución", [out])
        st = _load_state()
        st["last_tick"] = _now()
        _save_state(st)
        care = run_self_care_tick()
        return f"{out} | {care}"
    except Exception as e:
        try:
            (_MEM / "self_evolution_errors.log").write_text(
                f"{_now()} | {type(e).__name__}: {e}\n", encoding="utf-8")
        except Exception:
            pass
        log_vault("evolución", [f"Tick con error (reportado): {type(e).__name__} {e}"])
        return f"Tick de evolución falló silenciosamente: {type(e).__name__}"


def learn(titulo: str, contenido: str) -> str:
    rel = vault_note("Aprendizaje", titulo, (
        f"> Aprendido por ERIS el {_now()}.\n\n{contenido}"))
    return f"Guardado en Obsidian: {rel}"


# ── AUTOCUIDADO: se revisa sola y se autoconfigura ──────────────────────────
# ERIS vigila los pilares que siempre usa (memoria, vault de Obsidian,
# knowledge, config, sync de tools, logs, archivos de estado). Si algo falta o
# está roto, lo arregla ELLA MISMA: crea directorios/archivos, repara JSON,
# reinstaura defaults, instala deps faltantes, poda backups viejos y deja
# apunte de lo que no pudo resolver (para aprenderlo y reintentarlo).
_CARE_STATE = _MEM / "self_care_state.json"
_CARE_BACKUP = _MEM / "self_care_backups"
_CARE_NOTES = _MEM / "self_care_apuntes.md"
_CARE_DEEP_INTERVAL = 6 * 3600      # autocuidado profundo cada 6 h
_CARE_HISTORY_MAX = 40

_CARE_VAULT_DIRS = ["raw", "wiki", "outputs", "Logs", "Tools", "Proyectos",
                    "Capacidades", "Memoria", "Aprendizaje"]
_CARE_STRUCTURAL_DIRS = ["core", "config", "data", "data/knowledge", "actions",
                         "memory", "skills", "agents",
                         "memory/undo_backups", "memory/self_evol_backups"]
_CARE_KNOWLEDGE = ["eris_self_knowledge.md", "eris_inventario_vivo.md",
                   "manual_opencode_completo.md", "metodologia_opencode.md"]
# Claves estructurales SIEMPRE presentes en config/api_keys.json
_CARE_ESSENTIAL_KEYS = ["gemini_api_key", "fish_api_key", "mic_device",
                        "speaker_device", "mic_device_rate", "tts_backend",
                        "tts_voice"]
_CARE_DEFAULTS = {"tts_backend": "edge", "tts_voice": "es-AR-TomasNeural",
                  "mic_device_rate": 44100}
# Módulo faltante → paquete pip correspondiente (instalación autónoma)
_CARE_DEP_ALLOWLIST = {"yaml": "pyyaml", "psutil": "psutil",
                       "requests": "requests", "flask": "flask",
                       "numpy": "numpy"}
# JSON de autoestado corrupto → cuarentena (el módulo lo recrea al arrancar)
_CARE_SELF_STATE_JSON = ["memory/observer.json", "memory/emotional_core.json",
                         "memory/code_guard.json",
                         "memory/self_evolution_state.json"]
_CARE_BACKUP_AGE_DAYS = 30


def _care_apunte(pillar: str, problema: str):
    """Deja constancia durable de un pilar que no pudo resolver (lo aprende)."""
    try:
        _CARE_NOTES.parent.mkdir(parents=True, exist_ok=True)
        body = (_CARE_NOTES.read_text(encoding="utf-8")
                if _CARE_NOTES.exists() else
                f"# Apuntes de autocuidado de {_tag()}\n\n")
        body += (f"\n## {_now()} · {pillar}\n- {problema}\n")
        _CARE_NOTES.write_text(body, encoding="utf-8")
    except Exception:
        pass


def _quarantine(path: Path) -> str:
    """Mueve un archivo corrupto a cuarentena (backup) para que se regenere."""
    try:
        _CARE_BACKUP.mkdir(parents=True, exist_ok=True)
        tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = _CARE_BACKUP / f"{tag}_{path.name}.corrupt"
        path.rename(dst)
        return f"cuarentena → {dst.name}"
    except Exception as e:
        return f"no pude moverlo ({type(e).__name__})"


# ── Chequeos (tier 1 = estructural, rápido; tier 2 = profundo) ──
def _workspace_check():
    missing = [r for r in _CARE_STRUCTURAL_DIRS if not (_BASE / r).is_dir()]
    return (not missing, f"faltan directorios: {', '.join(missing)}" if missing
            else "workspace OK", False)


def _vault_check():
    missing = [r for r in _CARE_VAULT_DIRS if not (_VAULT / r).is_dir()]
    src = _VAULT
    return (not missing, f"faltan carpetas del vault: {', '.join(missing)}"
            if missing else "vault OK", False)


def _knowledge_check():
    miss = [f for f in _CARE_KNOWLEDGE if not (_KNOW / f).exists()]
    return (not miss, f"faltan documentos: {', '.join(miss)}" if miss
            else "knowledge OK", False)


def _config_check():
    p = _BASE / "config" / "api_keys.json"
    if not p.exists():
        return False, "no existe config/api_keys.json", False
    raw = p.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return False, "config/api_keys.json está en UTF-8 con BOM (rompe el arranque)", False
    try:
        d = json.loads(raw)
    except Exception as e:
        return False, f"config/api_keys.json inválido: {type(e).__name__}", False
    if not isinstance(d, dict):
        return False, "config/api_keys.json no es un objeto", False
    missing = [k for k in _CARE_ESSENTIAL_KEYS if not d.get(k)]
    return (not missing, f"config OK; faltan claves: {', '.join(missing)}"
            if missing else "config OK", False)


def _logs_check():
    p = _BASE / "eris.log"
    ok = p.exists()
    if ok:
        try:
            with open(p, "a", encoding="utf-8") as fh:
                fh.tell()
        except Exception:
            ok = False
    return (ok, "eris.log no existe o no es escribible" if not ok else "logs OK",
            False)


def _prompt_check():
    p = _BASE / "core" / "prompt.txt"
    if not p.exists():
        return False, "no existe core/prompt.txt (gravemente roto)", False
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return False, "core/prompt.txt no legible", False
    miss = [f for f in ("eris_self_knowledge.md", "manual_opencode_completo.md")
            if f not in text]
    return (not miss, f"prompt no referencia su auto-conocimiento: {miss}"
            if miss else "prompt OK", False)


def _sync_check():
    try:
        sys.path.insert(0, str(_BASE))
        from core.tool_registry import get_all_tool_names
        from core.tool_declarations import TOOL_DECLARATIONS
        rnames = [n.lower() for n in get_all_tool_names()]
        dnames = [str(d.get("name", "")).lower() for d in TOOL_DECLARATIONS]
        dnames = [n for n in dnames if n]
        rset, dset = set(rnames), set(dnames)
        dupes_d = len(dnames) - len(dset)
        dupes_r = len(rnames) - len(rset)
        undeclared = sorted(rset - dset)
        if undeclared:
            return False, (f"registry tiene tools SIN declarar: "
                           f"{', '.join(undeclared)}"), True
        if dupes_d or dupes_r:
            return False, (f"declaraciones duplicadas: {dupes_d}, "
                           f"registry duplicados: {dupes_r}"), True
        return True, f"sync OK: {len(rset)} tools, 0 duplicados, todas declaradas", True
    except Exception as e:
        return False, f"sync: {type(e).__name__}", True


def _deps_check():
    miss = [m for m in _CARE_DEP_ALLOWLIST
            if importlib.util.find_spec(m) is None]
    return (not miss, f"faltan dependencias: {', '.join(miss)}" if miss
            else "deps OK", True)


def _json_state_check():
    mal = [r for r in _CARE_SELF_STATE_JSON
           if (_BASE / r).exists() and not _valid_json((_BASE / r))]
    return (not mal, f"JSON de estado corrupto: {', '.join(mal)}" if mal
            else "estado JSON OK", True)


def _valid_json(p: Path) -> bool:
    try:
        json.loads(p.read_text(encoding="utf-8"))
        return True
    except Exception:
        return False


# ── Fixes (idempotentes, siempre dentro de su workspace/vault) ──
def _fix_workspace():
    creados = []
    for r in _CARE_STRUCTURAL_DIRS:
        d = _BASE / r
        if not d.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            creados.append(r)
    return "creados: " + (", ".join(creados) if creados else "ninguno")


def _fix_vault():
    creados = []
    _VAULT.mkdir(parents=True, exist_ok=True)
    for r in _CARE_VAULT_DIRS:
        d = _VAULT / r
        if not d.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            creados.append(r)
    return "vault: carpetas creadas: " + (", ".join(creados) if creados
                                          else "ninguna")


def _fix_knowledge():
    hechos = []
    _KNOW.mkdir(parents=True, exist_ok=True)
    if not (_KNOW / "eris_inventario_vivo.md").exists():
        build_inventory_md()
        hechos.append("regeneré eris_inventario_vivo.md")
    if not (_KNOW / "eris_self_knowledge.md").exists():
        (_KNOW / "eris_self_knowledge.md").write_text(
            f"# ERIS — Autoconocimiento\n\n"
            f"- {len(_declared_tools())} tools declaradas y resolviendo\n"
            f"- 39 skills instaladas, agentes especializados\n"
            f"- Memoria charra en el vault (raw → wiki → outputs)\n"
            f"- Regenerado por autocuidado el {_now()}.\n",
            encoding="utf-8")
        hechos.append("creé eris_self_knowledge.md mínimo")
    return "; ".join(hechos) if hechos else "knowledge completo"


def _fix_config():
    p = _BASE / "config" / "api_keys.json"
    hechos = []
    d = {}
    if p.exists():
        raw = p.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            try:
                d = json.loads(raw.decode("utf-8-sig"))
            except Exception:
                d = {}
            hechos.append("quité el BOM")
        elif _valid_json(p):
            try:
                d = json.loads(raw)
            except Exception:
                d = {}
        else:
            _care_apunte("config", "api_keys.json inválido; lo reemplazo por defaults")
            hechos.append("JSON inválido → defaults")
    else:
        hechos.append("archivo faltante → defaults")
    base = dict(d)
    for k, v in _CARE_DEFAULTS.items():
        if k not in base:
            base[k] = v
            hechos.append(f"default {k}={v}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(base, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    faltan = [k for k in _CARE_ESSENTIAL_KEYS if not base.get(k)]
    if faltan:
        _care_apunte("config", f"no puedo inventar estas claves: {faltan}")
        hechos.append(f"pendientes (no inventables): {', '.join(faltan)}")
    return "config: " + "; ".join(hechos)


def _fix_logs():
    p = _BASE / "eris.log"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text(f"# ERIS log — {_now()}\n", encoding="utf-8")
            return "creé eris.log"
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(f"# autocuidado {_now()}\n")
        return "eris.log escribible"
    except Exception as e:
        return f"eris.log sigue con problemas: {type(e).__name__}"


def _fix_sync():
    """Lo arreglable en sync es el CONTEÓ en sus documentos (registry canónico);
    undeclarados/duplicados requieren edición de código y quedan como apunte."""
    out = [rectify()]
    try:
        from core.tool_declarations import TOOL_DECLARATIONS
        dnames = [str(d.get("name", "")).lower() for d in TOOL_DECLARATIONS]
        dupes_d = len(dnames) - len(set(dnames))
        if dupes_d:
            out.append(f"{dupes_d} declaraciones duplicadas que NO puedo "
                       "quitar sola (requieren edición de código)")
            _care_apunte("sync", f"{dupes_d} declaraciones duplicadas")
    except Exception as e:
        out.append(f"{type(e).__name__}")
    return "; ".join(out)


def _fix_deps():
    hechos = []
    for mod, pkg in _CARE_DEP_ALLOWLIST.items():
        if importlib.util.find_spec(mod) is not None:
            continue
        try:
            r = subprocess.run([sys.executable, "-m", "pip", "install",
                                "--quiet", pkg], timeout=180,
                               capture_output=True, text=True)
            if r.returncode == 0:
                hechos.append(f"instalé {pkg}")
            else:
                hechos.append(f"{pkg} no se instaló (sin red?)")
                _care_apunte("deps", f"{pkg}: {r.stderr.strip()[:120]}")
        except Exception as e:
            hechos.append(f"{pkg}: {type(e).__name__}")
    return "; ".join(hechos) if hechos else "no instalé nada (deps OK)"


def _fix_json_state():
    hechos = []
    for rel in _CARE_SELF_STATE_JSON:
        p = _BASE / rel
        if p.exists() and not _valid_json(p):
            q = _quarantine(p)
            if rel == "memory/self_evolution_state.json":
                _save_state({})
            hechos.append(f"{rel} → {q}, regenerado")
    return "; ".join(hechos) if hechos else "estado JSON sano"


_CARE_ASSEMBLY = [
    ("workspace", _workspace_check, _fix_workspace),
    ("vault", _vault_check, _fix_vault),
    ("knowledge", _knowledge_check, _fix_knowledge),
    ("config", _config_check, _fix_config),
    ("logs", _logs_check, _fix_logs),
    ("prompt", _prompt_check, None),
    ("sync", _sync_check, _fix_sync),
    ("deps", _deps_check, _fix_deps),
    ("estado_json", _json_state_check, _fix_json_state),
]


def _run_care(deep: bool, audit_only: bool) -> list:
    report = []
    for pillar, check, fix in _CARE_ASSEMBLY:
        try:
            ok, detail, is_deep = check()
        except Exception as e:
            ok, detail, is_deep = False, f"{type(e).__name__}: {e}", False
        if ok:
            continue
        entry = {"pilar": pillar, "problema": detail, "fixed": False,
                 "deep": is_deep}
        if is_deep and not deep:
            entry["skipped"] = True
        elif not audit_only and fix is not None:
            try:
                entry["fixed"] = True
                entry["fix"] = fix()
            except Exception as e:
                entry["fix_error"] = f"{type(e).__name__}: {e}"
        if not entry.get("fixed") and fix is None:
            _care_apunte(pillar, detail)
        report.append(entry)
    return report


def self_care(audit_only: bool = False, deep: bool | None = None) -> str:
    """Autocuidado: revisa sus pilares y se autoconfigura los rotos/faltantes.
    deep (False) → solo tier estructural; True → además sync/deps/JSON.
    audit_only → inspecciona sin tocar nada."""
    st = _load_state()
    if deep is None:
        deep = (datetime.now().timestamp()
                - st.get("last_care", 0)) >= _CARE_DEEP_INTERVAL
    report = _run_care(deep, audit_only)
    fixes = [e for e in report if e.get("fixed")]
    unfix = [e for e in report if e.get("skipped") or not e.get("fixed")]
    st["last_care"] = datetime.now().timestamp()
    st["last_care_summary"] = ("autofix: " + "; ".join(
        f"{e['pilar']} ({e['fix']})" for e in fixes)
        if fixes else "todo en orden")
    hist = st.get("care_history", [])
    hist.append({"ts": _now(), "deep": deep, "fixed": [e["pilar"] for e in fixes],
                 "pendientes": [e["pilar"] for e in unfix]})
    st["care_history"] = hist[-_CARE_HISTORY_MAX:]
    _save_state(st)
    lines = [f"Deep: {'sí' if deep else 'no (estructura)'} · "
             f"autofix: {len(fixes)} · pendientes: {len(unfix)}"]
    if fixes:
        lines += [f"- {e['pilar']}: {e['fix']}" for e in fixes]
    if unfix:
        lines += [f"~ {e['pilar']}: {e['problema']}" for e in unfix]
    log_vault("autocuidado", lines)
    if fixes:
        return (f"🛟 Autocuidado: arreglé {len(fixes)} cosa(s): "
                + "; ".join(f"{e['pilar']} → {e['fix']}" for e in fixes))
    if unfix:
        return ("Autocuidado: sin arreglos. Pendientes (dejé apunte): "
                + ", ".join(f"{e['pilar']} ({e['problema']})" for e in unfix))
    return "Autocuidado: todo en orden. Revisé el vault, knowledge, config, sync, logs y estado."


def run_self_care_tick() -> str:
    """Tick del ciclo de autocuidado (lo llama el loop de evolución)."""
    try:
        return self_care()
    except Exception as e:
        try:
            (_MEM / "self_care_errors.log").write_text(
                f"{_now()} | {type(e).__name__}: {e}\n", encoding="utf-8")
        except Exception:
            pass
        return f"Autocuidado falló silenciosamente: {type(e).__name__}"


def run_full_care_now() -> str:
    """Autocuidado profundo forzado (boot / pedido explícito)."""
    try:
        return self_care(deep=True)
    except Exception as e:
        return f"Autocuidado profundo falló: {type(e).__name__}"


def self_evolution_tool(parameters: dict = None, player=None) -> str:
    p = parameters or {}
    action = p.get("action", "status")
    if action == "status":
        st = _load_state()
        rel = vault_note("Capacidades", "Estado de Evolución", (
            f"# ERIS — Estado de Evolución\n\n"
            f"- **Último tick:** {st.get('last_tick') or 'aún no'}\n"
            f"- **Último micro-fix:** {st.get('last_fix_when') or '-'} "
            f"({st.get('last_fix') or '-'})\n"
            f"- **Inventario:** {st.get('tools') or '-'} tools "
            f"({st.get('last_inventory') or '-'})\n"
            f"- **Salud:** {st.get('ok') or '-'}/{st.get('total') or '-'} "
            f"({st.get('last_health') or '-'})"))
        return (f"Evolución activa. Último tick: {st.get('last_tick') or 'aún no'}. "
                f"Salud: {st.get('ok') or '-'}/{st.get('total') or '-'}. "
                f"Estado espejado en Obsidian ({rel}).")
    if action == "health":
        return health()
    if action == "inventory":
        return inventory()
    if action == "rectify":
        return rectify()
    if action == "sync":
        st = _load_state()
        n = build_inventory_md()
        mem = vault_note("Memoria", f"Estado - {_tag()}", (
            f"# Estado de ERIS — {_now()}\n\n"
            f"- Tools: {n}\n- Salud: {st.get('ok')}/{st.get('total')}\n"
            f"- Último micro-fix: {st.get('last_fix_when')} "
            f"({st.get('last_fix')})\n"))
        return (f"Sincronización a Obsidian completa: inventario en Tools/, "
                f"estado en Memoria/, evolución en Logs/. Nota: {mem}")
    if action == "evolve":
        return evolve(dry_run=bool(p.get("dry_run", False)),
                      targets=p.get("targets"))
    if action == "care":
        return self_care(audit_only=bool(p.get("audit_only", False)))
    if action == "autocare":
        return run_full_care_now()
    if action == "tick":
        return run_evolution_tick()
    if action == "learn":
        t = p.get("titulo") or p.get("title") or "Nota de ERIS"
        c = p.get("contenido") or p.get("content") or ""
        if not c:
            return "Falta 'contenido' para guardar."
        return learn(t, c)
    if action == "log":
        lines = p.get("lineas") or p.get("lines") or []
        if isinstance(lines, str):
            lines = [lines]
        rel = log_vault(p.get("tag", "manual"), lines)
        return f"Huella en Obsidian: {rel}"
    return ("Acciones: status | health | inventory | rectify | sync | evolve "
            "(dry_run, targets) | care (audit_only) | autocare | tick | learn "
            "(titulo, contenido) | log (tag, lineas).")