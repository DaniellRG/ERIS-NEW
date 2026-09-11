"""
core/eris_fabrica.py — La Fábrica de Eris

Eris crea SUS PROPIAS capacidades: librerías de Python (módulos reutilizables
con funciones reales), tools nuevas (usable de inmediato en runtime y tras
reinicio) y skills (user_created). Todo queda inventariado en
`memory/eris_fabrica.json` y listo para USARSE.

A diferencia de tool_creation (stubs genéricos), aquí Eris entrega el CÓDIGO
REAL de sus funciones/librerías y la fábrica las compila, prueba, registra y
expone para ejecución inmediata vía `usar_libreria`.
"""
import importlib
import json
import re
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_LIB_BASE = _BASE / "libraries"
_CUSTOM_ACTIONS = _BASE / "actions" / "custom"
_SKILLS_DIR = _BASE / "skills" / "user_created"
_STATE_FILE = _BASE / "memory" / "eris_fabrica.json"
_CUSTOM_TOOLS_JSON = _BASE / "actions" / "custom_tools.json"
_BACKUP_DIR = _BASE / "memory" / "eris_fabrica_backups"

_MAX_BACKUPS = 8  # versiones por creación

# Para importar las librerías propias desde cualquier módulo.
if str(_LIB_BASE) not in sys.path:
    sys.path.insert(0, str(_LIB_BASE))
if str(_CUSTOM_ACTIONS) not in sys.path:
    sys.path.insert(0, str(_CUSTOM_ACTIONS))


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            st = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(st, dict) and "items" in st:
                return st
        except Exception:
            pass
    return {"items": [], "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()}


def _save_state(st: dict):
    st["updated_at"] = datetime.now().isoformat()
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_name(raw: str) -> str:
    s = re.sub(r"[^a-z0-9_]", "", (raw or "").lower().strip().replace(" ", "_"))
    return s[:64]


def _state_item(name: str) -> dict | None:
    st = _load_state()
    return next((i for i in st["items"] if i["name"] == name), None)


def _snapshot(name: str, motivo: str = "") -> str | None:
    """Guarda una copia de seguridad de una creación (antes de tocar/borrar)."""
    it = _state_item(name)
    if it is None:
        return None
    src = Path(it["path"])
    if not src.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = _BACKUP_DIR / name / ts
    try:
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / src.name)
        # Guardar también el metadato
        (dest / "meta.json").write_text(
            json.dumps({"name": name, "tipo": it["type"], "motivo": motivo,
                        "creado": it.get("created", "")},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
        _prune_backups(name)
        return str(dest)
    except Exception:
        return None


def _prune_backups(name: str):
    """Mantiene como máximo _MAX_BACKUPS versiones por creación."""
    d = _BACKUP_DIR / name
    if not d.exists():
        return
    versions = sorted(d.iterdir(), key=lambda p: p.name)
    while len(versions) > _MAX_BACKUPS:
        try:
            shutil.rmtree(versions.pop(0))
        except Exception:
            break


def _versiones(name_: str) -> list:
    d = _BACKUP_DIR / name_
    if not d.exists():
        return []
    vers = []
    for p in sorted(d.iterdir(), key=lambda p: p.name, reverse=True):
        meta = {}
        mf = p / "meta.json"
        if mf.exists():
            try:
                meta = json.loads(mf.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        vers.append({"version": p.name, "fecha": meta.get("creado", p.name[:15]),
                     "motivo": meta.get("motivo", ""), "tipo": meta.get("tipo", ""),
                     "path": str(p)})
    return vers


def restaurar(name: str, version: str = "") -> dict:
    """Restaura una creación desde una versión guardada (aunque esté borrada)."""
    it = _state_item(name)
    vers = _versiones(name)
    if not vers:
        return {"error": f"No hay backups para '{name}'."}
    if not version:
        version = vers[0]["version"]
    src_dir = _BACKUP_DIR / name / version
    if not src_dir.exists():
        return {"error": f"No existe la versión '{version}'. Disponibles: "
                         f"{[v['version'] for v in vers]}"}
    # Reconstruir ruta destino: desde inventario o desde el backup meta
    target = None
    if it is not None:
        target = Path(it["path"])
    else:
        meta = {}
        mf = src_dir / "meta.json"
        if mf.exists():
            try:
                meta = json.loads(mf.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        tipo = meta.get("tipo", "")
        if tipo == "libreria":
            target = _LIB_BASE / f"{name}.py"
        elif tipo == "tool":
            target = _CUSTOM_ACTIONS / f"{name}.py"
        elif tipo == "skill":
            target = _SKILLS_DIR / name / "SKILL.md"
        else:
            return {"error": f"No sé dónde restaurar una creacion de tipo '{tipo}'."}
    # Snapshot del estado actual antes de restaurar (si aún existe)
    _snapshot(name, motivo=f"previo a restaurar {version}")
    # Contenido real (el archivo/dir principal, sin el meta.json)
    files = [f for f in src_dir.iterdir() if f.name != "meta.json"]
    if not files:
        return {"error": "Backup vacío."}
    try:
        for f in files:
            if f.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(f, target)
            else:
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
    except Exception as e:
        return {"error": f"Error restaurando: {e}"}
    msg = "Todo el contenido fue repuesto. Si era una tool, reiniciá Eris o volvé a registrarla con la fábrica."
    if it is None:
        msg += " La creación no estaba en el inventario; se restauró el archivo. "
        msg += "Usá la fábrica (crear_libreria/crear_tool/crear_skill o su equivalente) para re-registrarla."
    return {"status": "restaurada", "name": name, "version": version,
            "path": str(target), "nota": msg}


# ─────────────────────────────────────────────────────────────────────
# LIBRERÍAS
# ─────────────────────────────────────────────────────────────────────
def crear_libreria(name: str, purpose: str = "", functions: list = None,
                   autor: str = "Eris") -> dict:
    """Crea un módulo de Python con funciones REALES en libraries/<name>.py."""
    safe = _safe_name(name) or "mi_libreria"
    if not safe.startswith("eris_"):
        lib_name = "eris_" + safe
    else:
        lib_name = safe
    file_path = _LIB_BASE / (lib_name + ".py")
    if file_path.exists():
        return {"error": f"La librería {lib_name} ya existe."}

    fun_codes = []
    for fn in (functions or []):
        fname = re.sub(r"[^a-z0-9_]", "", (fn.get("name") or "procesar").lower())
        desc = (fn.get("description") or "").strip()
        params = fn.get("params") or fn.get("parameters") or fn.get("args") or []
        if isinstance(params, str):
            params = [p.strip() for p in params.replace(",", " ").split() if p.strip()]
        body = (fn.get("code") or fn.get("cuerpo") or f"    return {{'ok': True, 'fn': '{fname}'}}").strip()
        if not body.startswith("def "):
            body_indented = "\n".join("    " + l for l in body.splitlines())
            body = f"    # Implementación de {fname}\n{body_indented}"
        if params:
            sig = ", ".join(params)
            fun_codes.append(f"def {fname}({sig}):\n    \"\"\"{desc}\"\"\"\n{body}")
        else:
            fun_codes.append(f"def {fname}(**kwargs):\n    \"\"\"{desc}\"\"\"\n{body}")
    code = (
        '"""\n'
        f"{lib_name}.py — Librería propia creada por {autor}.\n\n"
        f"{purpose or 'Sin descripción.'}\n"
        f"Creada: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        '"""\n'
        "import json\n\n\n"
        + "\n\n\n".join(fun_codes)
    )
    _LIB_BASE.mkdir(parents=True, exist_ok=True)
    file_path.write_text(code, encoding="utf-8")

    # Compilar
    try:
        import py_compile
        py_compile.compile(str(file_path), doraise=True)
    except Exception as e:
        file_path.unlink(missing_ok=True)
        return {"error": f"Error de sintaxis en la librería: {e}"}

    # Probar import
    try:
        mod = importlib.import_module(lib_name)
        importlib.reload(mod)
        fns = [f for f in dir(mod) if callable(getattr(mod, f)) and not f.startswith("_")]
    except Exception as e:
        file_path.unlink(missing_ok=True)
        return {"error": f"Error importando la librería: {e}"}

    st = _load_state()
    st["items"] = [i for i in st["items"] if i["name"] != lib_name]
    st["items"].append({
        "name": lib_name,
        "type": "libreria",
        "path": str(file_path),
        "purpose": purpose,
        "functions": fns,
        "created": datetime.now().isoformat(),
    })
    _save_state(st)
    return {"status": "creada", "tipo": "libreria", "name": lib_name,
            "file": str(file_path), "functions": fns,
            "modo_uso": f'Usá fabrica con action="usar_libreria", name="{lib_name}", function="<función>", params={{...}}'}


def usar_libreria(name: str, function: str, params: str = "{}") -> dict:
    """Importa una librería creada por Eris y ejecuta una de sus funciones."""
    safe = _safe_name(name)
    if not safe.startswith("eris_"):
        safe = "eris_" + safe
    if not (str(_LIB_BASE) in sys.path):
        sys.path.insert(0, str(_LIB_BASE))
    try:
        mod = importlib.import_module(safe)
    except Exception as e:
        return {"error": f"No existe la librería {safe}: {e}"}
    if not hasattr(mod, function):
        return {"error": f"{safe} no tiene la función '{function}'. Disponibles: "
                         f"{[f for f in dir(mod) if callable(getattr(mod, f)) and not f.startswith('_')]}"}
    try:
        raw = params if isinstance(params, dict) else json.loads(params or "{}")
    except Exception:
        return {"error": "params debe ser un objeto JSON válido."}
    try:
        result = getattr(mod, function)(**raw)
    except Exception as e:
        return {"error": f"Error ejecutando {function}: {e}\n{traceback.format_exc(limit=3)}"}
    try:
        return json.loads(json.dumps(result, ensure_ascii=False, default=str))
    except Exception:
        return {"resultado": str(result)}


# ─────────────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────────────
def _declaration_from_spec(name: str, description: str, props: dict) -> dict:
    decl = {
        "name": name,
        "description": description,
        "parameters": {"type": "OBJECT",
                       "properties": props,
                       "required": []},
    }
    return decl


def crear_tool(name: str, description: str, funciones: list = None) -> dict:
    """Crea una tool nueva: módulo real en actions/custom/, registrada en
    runtime (usable YA) y con declaración persistida para el reinicio."""
    safe = _safe_name(name) or "mi_tool"
    file_path = _CUSTOM_ACTIONS / (safe + ".py")
    _CUSTOM_ACTIONS.mkdir(parents=True, exist_ok=True)
    if file_path.exists():
        return {"error": f"Ya existe la tool {safe}. Borrala primero (action=borrar)."}

    # Mapa action → función, generado desde `funciones`
    action_lines = []
    fn_defs = []
    for fn in (funciones or []):
        act = re.sub(r"[^a-z0-9_]", "", (fn.get("action") or fn.get("name") or "procesar").lower())
        fname = re.sub(r"[^a-z0-9_]", "", (fn.get("fn_name") or act or "procesar").lower())
        desc = (fn.get("description") or "").strip()
        body = (fn.get("code") or "return {'status': 'ok', 'ok': True}").strip()
        body_lines = body.splitlines()
        if not (body_lines and body_lines[0].lstrip().startswith("def ")):
            body_ok = "\n".join("    " + l if l.strip() else "" for l in body_lines)
        else:
            body_ok = body
        action_lines.append(
            f"    if action == '{act}':\n"
            f"        return {fname}(params)\n"
        )
        fn_defs.append(
            f"def {fname}(params: dict):\n"
            f"    \"\"\"{desc}\"\"\"\n"
            f"{body_ok}\n"
        )
    module_code = (
        '"""\n'
        f"{safe}.py — Tool creada por Eris en runtime.\n\n{description}\n"
        f"Creada: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        '"""\n'
        "import json\n\n\n"
        f"def {safe}_tool(parameters=None, player=None):\n"
        "    params = parameters or {}\n"
        "    action = str(params.get('action') or 'status').lower().strip()\n"
        "    if action == 'status':\n"
        "        return json.dumps({'tool': '" + safe + "', 'status': 'activa'}, ensure_ascii=False)\n"
        + "\n".join(action_lines) +
        "\n" + f"    return json.dumps({{'tool': '{safe}', 'action': action, 'status': 'ok'}}, ensure_ascii=False)\n"
        + "\n\n\n" + "\n\n".join(fn_defs)
    )
    file_path.write_text(module_code, encoding="utf-8")

    # Compilar
    try:
        import py_compile
        py_compile.compile(str(file_path), doraise=True)
    except Exception as e:
        file_path.unlink(missing_ok=True)
        return {"error": f"Error de sintaxis en la tool: {e}"}

    # Importar y registrar en runtime
    try:
        spec = importlib.util.spec_from_file_location(safe, file_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        func = getattr(mod, f"{safe}_tool")
    except Exception as e:
        file_path.unlink(missing_ok=True)
        return {"error": f"Error cargando la tool generada: {e}"}
    try:
        from core.tool_registry import register_tool
        register_tool(safe, func)
    except Exception:
        pass

    # Persistir declaración (para que sobreviva al reinicio)
    props = {"action": {"type": "STRING",
                        "description": "Acción a ejecutar: status u otra definida."}}
    for fn in (funciones or []):
        act = re.sub(r"[^a-z0-9_]", "", (fn.get("action") or fn.get("name") or "procesar").lower())
        if act not in ("status",):
            props[act] = {"type": "STRING",
                          "description": (fn.get("description") or f"Ejecutar {act}")}
    props["params"] = {"type": "STRING",
                       "description": "JSON opcional con parámetros de la acción."}
    decl = _declaration_from_spec(safe, description, props)
    try:
        custom = []
        if _CUSTOM_TOOLS_JSON.exists():
            try:
                custom = json.loads(_CUSTOM_TOOLS_JSON.read_text(encoding="utf-8"))
            except Exception:
                custom = []
        if not isinstance(custom, list):
            custom = []
        if safe not in [t.get("name") for t in custom if isinstance(t, dict)]:
            custom.append(decl)
            _CUSTOM_TOOLS_JSON.write_text(
                json.dumps(custom, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    st = _load_state()
    st["items"] = [i for i in st["items"] if i["name"] != safe]
    st["items"].append({
        "name": safe,
        "type": "tool",
        "path": str(file_path),
        "description": description,
        "declaration": decl,
        "created": datetime.now().isoformat(),
    })
    _save_state(st)
    return {"status": "creada", "tipo": "tool", "name": safe,
            "file": str(file_path),
            "disponible_ya": True,
            "modo_uso": f'Invocá la tool "{safe}" directamente (ya registrada en runtime) con action="..."'}


# ─────────────────────────────────────────────────────────────────────
# SKILLS
# ─────────────────────────────────────────────────────────────────────
def crear_skill(name: str, description: str, pasos: str = "") -> dict:
    """Crea una skill user_created con su SKILL.md, usable por skill_registry."""
    safe = re.sub(r"[^a-z0-9_\-]", "", (name or "mi_skill").lower().strip().replace(" ", "_"))
    skill_dir = _SKILLS_DIR / safe
    if skill_dir.exists():
        return {"error": f"La skill {safe} ya existe."}
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        f"name: {safe}\n"
        f"description: {description}\n"
        "---\n\n"
        "# " + safe + "\n\n"
        + (pasos or ("Descripción: " + description))
        + "\n"
    )
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    try:
        from core.skill_registry import _scan_all_skills
        _scan_all_skills()
    except Exception:
        pass
    st = _load_state()
    st["items"] = [i for i in st["items"] if i["name"] != safe]
    st["items"].append({
        "name": safe, "type": "skill", "path": str(skill_dir),
        "description": description, "created": datetime.now().isoformat()})
    _save_state(st)
    return {"status": "creada", "tipo": "skill", "name": safe,
            "path": str(skill_dir),
            "modo_uso": f'La skill "{safe}" ya es visible para el usuario (apply_skill si corresponde).'}


# ─────────────────────────────────────────────────────────────────────
# COMMON
# ─────────────────────────────────────────────────────────────────────
def listar() -> dict:
    st = _load_state()
    items = st.get("items", [])
    if not items:
        return {"creadas": [], "total": 0,
                "nota": "Todavía no creaste nada con tu fábrica. Proba crear_libreria con funciones reales."}
    resumen = [{"name": i["name"], "tipo": i["type"],
                "funciones": i.get("functions", []),
                "created": i["created"].split("T")[0]} for i in items]
    return {"creadas": resumen, "total": len(items)}


def detalle(name: str) -> dict:
    it = _state_item(name)
    if it is None:
        return {"error": f"No encontré '{name}'. Proba con action=listar."}
    return it


def borrar(name: str) -> dict:
    it = _state_item(name)
    if it is None:
        return {"error": f"No encontré '{name}'."}
    # Versionar antes de borrar: nada se pierde para siempre
    _snapshot(name, motivo="borrado")
    try:
        p = Path(it["path"])
        if p.exists():
            if p.is_dir():
                import shutil
                shutil.rmtree(p)
            else:
                p.unlink()
    except Exception:
        pass
    if it["type"] == "tool":
        try:
            from core.tool_registry import get_tool
            pass
        except Exception:
            pass
        # Eliminar declaración persistida
        try:
            if _CUSTOM_TOOLS_JSON.exists():
                custom = json.loads(_CUSTOM_TOOLS_JSON.read_text(encoding="utf-8"))
                custom = [t for t in custom if isinstance(t, dict) and t.get("name") != name]
                _CUSTOM_TOOLS_JSON.write_text(json.dumps(custom, indent=2, ensure_ascii=False),
                                             encoding="utf-8")
        except Exception:
            pass
    st = _load_state()
    st["items"] = [i for i in st["items"] if i["name"] != name]
    _save_state(st)
    return {"status": "borrada", "name": name}


# ─────────────────────────────────────────────────────────────────────
# TOOL ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────
def eris_fabrica(parameters=None, player=None) -> str:
    """Tool fábrica de Eris: crear y usar sus propias librerías/tools/skills."""
    params = parameters or {}
    action = str(params.get("action") or "listar").lower().strip()

    def _ok(data: dict) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)

    if action in ("listar", "status", "list"):
        return _ok(listar())
    if action == "detalle":
        return _ok(detalle(params.get("name", "")))
    if action == "borrar":
        return _ok(borrar(params.get("name", "")))
    if action in ("versiones", "backups", "versionar"):
        return _ok({"versions": _versiones(params.get("name", "")),
                    "name": params.get("name", "")})
    if action in ("restaurar", "rollback"):
        return _ok(restaurar(params.get("name", ""), params.get("version", "")))

    if action == "crear_libreria":
        functions = params.get("functions") or params.get("funciones") or []
        if isinstance(functions, str):
            try:
                functions = json.loads(functions)
            except Exception:
                return _ok({"error": "functions debe ser una lista JSON de {name, description, code}."})
        return _ok(crear_libreria(
            name=params.get("name", ""),
            purpose=params.get("purpose", params.get("descripcion", "")),
            functions=functions,
            autor=params.get("autor", "Eris")))

    if action in ("usar_libreria", "usar", "llamar"):
        return _ok(usar_libreria(
            name=params.get("name", ""),
            function=params.get("function", params.get("funcion", "")),
            params=params.get("params", params.get("arguments", "{}"))))

    if action == "crear_tool":
        funciones = params.get("funciones") or params.get("functions") or []
        if isinstance(funciones, str):
            try:
                funciones = json.loads(funciones)
            except Exception:
                return _ok({"error": "funciones debe ser una lista JSON de {action, description, code}."})
        return _ok(crear_tool(
            name=params.get("name", ""),
            description=params.get("description", params.get("descripcion", "")),
            funciones=funciones))

    if action == "crear_skill":
        return _ok(crear_skill(
            name=params.get("name", ""),
            description=params.get("description", params.get("descripcion", "")),
            pasos=params.get("pasos", params.get("content", ""))))

    return _ok({"error": f"Acción desconocida: {action}. Acciones: listar, detalle, borrar, versiones, restaurar, "
                          "crear_libreria, usar_libreria, crear_tool, crear_skill"})