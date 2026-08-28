"""Evolución continua de ERIS.

Autoconocimiento vivo (inventario real de herramientas), auditoría de salud
(447 tools importan y se resuelven), persistencia de TODO en Obsidian, y un
bucle antir-estancamiento: cada tick aplica una micro-mejora real sobre su
propio código (con backup + validación + rollback) o consolida conocimiento.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

_BASE = Path(r"D:\Eris_Source")
_MEM = _BASE / "memory"
_STATE = _MEM / "self_evolution_state.json"
_BACKUP_DIR = _MEM / "self_evol_backups"
_KNOW = _BASE / "data" / "knowledge"
_DOC = _KNOW / "eris_inventario_vivo.md"
_VAULT = Path(r"D:\Eris_NEW\BaseDatosObsidian\BaseObsiEris")

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
    """Genera 'eris_inventario_vivo.md' (su mapa de capacidades real)."""
    tools = _declared_tools()
    groups = {}
    for t in tools:
        key = t["name"].split("_")[0]
        groups.setdefault(key, []).append(t)
    lines = ["# ERIS — INVENTARIO VIVO DE CAPACIDADES",
             f"Generado: {_now()} · {len(tools)} tools declaradas.",
             ""]
    for key in sorted(groups):
        lines.append(f"## {key}")
        for t in groups[key]:
            desc = t["description"].replace("\n", " ")[:110]
            lines.append(f"- `{t['name']}` — {desc}")
        lines.append("")
    _KNOW.mkdir(parents=True, exist_ok=True)
    _DOC.write_text("\n".join(lines), encoding="utf-8")
    return len(tools)


def inventory() -> str:
    n = build_inventory_md()
    title = f"Inventario de Capacidades ({n})"
    rel = vault_note("Tools", title, _DOC.read_text(encoding="utf-8"))
    _save_state({"last_inventory": _now(), "tools": n, "doc": str(_DOC)})
    return (f"Inventario regenerado: {n} tools. Vault: {rel} · "
            f"doc: {_DOC}")


def _rectify_counts() -> list:
    """Normaliza el conteo de tools en prompt/README/AGENTS al número real."""
    actual = len(_declared_tools())
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
        return out
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
            "(dry_run, targets) | tick | learn (titulo, contenido) | log "
            "(tag, lineas).")