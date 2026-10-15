"""
rea_engine.py — INGENIERÍA INVERSA con REA (morluto/rea) para ERIS.

Eris "absorbe" REA: una caja de **207 herramientas** de ingeniería inversa
(binarios nativos, apps JS/Electron, .NET, APKs, firmware, webs, capturas de
red, WASM, EVM, Go/Rust/SQLite...). Se expone como **una** tool propia (`rea`)
que corre el CLI de REA con `--json` y **guarda la evidencia completa en un
archivo que el dueño puede abrir**.

Por qué una sola tool (y no 207): el chat Gemini tiene tope de 128
`function_declarations`; una tool estable con passthrough total (`action=comando`)
da acceso a **todo** REA sin reventar el tope, y el skill
`reverse-engineer-anything` enseña el enrutado por tipo de objetivo.

Capas (mismo patrón que `pentest_learning`/`crecimiento`):
  1. `data/rea_evidence/<ts>_<cmd>.json`  (evidencia cruda, VISIBLE)
  2. `memory/rea_engine.json`             (índice de corridas + versión)
  3. índice en `rag_engine` (best-effort)
  4. novedad en `todo_yo` (al primer uso exitoso)

El servidor MCP de REA se registra en `memory/mcp_config.json` (acción `mcp`);
las 207 tools quedan como `mcp_rea_*` vía el puente `core/mcp_bridge`. Es
**stdio puro**: no abre puertos.

Diseño: docs/superpowers/specs/2026-10-14-eris-absorbe-rea-design.md
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM_DIR = _BASE / "memory"
_STATE_FILE = _MEM_DIR / "rea_engine.json"
_EVID_DIR = _BASE / "data" / "rea_evidence"
_KNOW_DIR = _BASE / "data" / "knowledge"
_KNOW_FILE = _KNOW_DIR / "ingenieria_inversa.md"
_MCP_CONFIG = _MEM_DIR / "mcp_config.json"
_SKILL_DIR = _BASE / "skills" / "user_created" / "reverse-engineer-anything"

_DEFAULT_SPEC = "rea-agents@6.5.0"
_DEFAULT_TIMEOUT = 300
_MAX_CORRIDAS = 40
_lock = threading.Lock()

# Comandos amables → comando real del CLI de REA.
_ATAJOS = {
    "analizar": "analyze",
    "analiza": "analyze",
    "js": "analyze-javascript-application",
    "javascript": "analyze-javascript-application",
    "electron": "analyze-javascript-application",
    "web": "analyze-web-bundle",
    "go": "inspect-go-binary",
    "rust": "inspect-rust-binary",
    "sqlite": "inspect-sqlite-database",
    "layout": "inspect-binary-layout",
    "elf": "inspect-binary-layout",
    "decompilar": "decompile",
    "decompila": "decompile",
    "abrir": "open-binary",
    "binario": "open-binary",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _spec() -> str:
    return (os.environ.get("ERIS_REA_SPEC") or "").strip() or _DEFAULT_SPEC


def _base_cmd() -> list[str]:
    """Comando base para invocar REA: `rea` si existe, si no `npx -y <spec>`."""
    env_cmd = (os.environ.get("ERIS_REA_CMD") or "").strip()
    if env_cmd:
        import shlex as _sh
        return _sh.split(env_cmd)
    rea = shutil.which("rea")
    if rea:
        return [rea]
    npx = shutil.which("npx") or "npx"
    return [npx, "-y", _spec()]


# ── Persistencia ─────────────────────────────────────────────────────────────

def _load() -> dict:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"version": "", "primera_corrida": "", "corridas": [], "novedad_dada": False}


def _save(state: dict) -> None:
    try:
        _MEM_DIR.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ── Ejecución del CLI ────────────────────────────────────────────────────────

def _run(extra: list[str], timeout: int = _DEFAULT_TIMEOUT):
    cmd = _base_cmd() + [str(x) for x in extra]
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    env["npm_config_yes"] = "true"
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, p.stdout or "", p.stderr or ""
    except FileNotFoundError as e:
        return 127, "", f"comando no encontrado: {e}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout tras {timeout}s"
    except Exception as e:  # pragma: no cover
        return 1, "", f"error al ejecutar REA: {e}"


def _loads(text: str):
    """Extrae el primer JSON válido de la salida de REA (ignora warnings de npm)."""
    t = (text or "").strip()
    if not t:
        return None
    try:
        return json.loads(t)
    except Exception:
        pass
    for i, ch in enumerate(t):
        if ch in "{[":
            try:
                return json.JSONDecoder().raw_decode(t[i:])[0]
            except Exception:
                break
    return None


def _ev_id(obj) -> str:
    if isinstance(obj, dict):
        for k in ("evidence_id",):
            if isinstance(obj.get(k), str) and obj[k].startswith("ev_"):
                return obj[k]
        for v in obj.values():
            r = _ev_id(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _ev_id(v)
            if r:
                return r
    return ""


def _save_evidence(comando: str, obj, stdout: str) -> str:
    """Guarda la corrida completa (JSON o texto) en un archivo abrible."""
    try:
        _EVID_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = re.sub(r"[^a-z0-9-]+", "-", comando.lower())[:48].strip("-") or "rea"
        path = _EVID_DIR / f"{ts}_{slug}.json"
        payload = {"generado": _now(), "comando": comando,
                   "resultado": obj if obj is not None else (stdout or "")}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
    except Exception:
        return ""


def _record(comando: str, ok: bool, evidence_id: str, archivo: str) -> None:
    with _lock:
        state = _load()
        if not state.get("primera_corrida"):
            state["primera_corrida"] = _now()
        state.setdefault("corridas", []).append({
            "ts": _now(), "comando": comando, "ok": bool(ok),
            "evidence_id": evidence_id, "archivo": archivo,
        })
        state["corridas"] = state["corridas"][-_MAX_CORRIDAS:]
        _save(state)


def _version() -> str:
    state = _load()
    if state.get("version"):
        return state["version"]
    rc, out, _ = _run(["--version"], timeout=120)
    v = (out or "").strip().splitlines()[-1].strip() if out else ""
    if rc == 0 and v:
        with _lock:
            s = _load()
            s["version"] = v
            _save(s)
        return v
    return ""


def _reindexar() -> None:
    try:
        from core.rag_engine import reindexar
        reindexar()
    except Exception:
        pass


def _novedad(texto: str) -> None:
    try:
        from core.todo_yo import registrar_novedad
        registrar_novedad(texto)
    except Exception:
        pass


# ── Resumen de resultados (no vuelca el grafo entero al contexto) ────────────

def _resumen_resultado(obj) -> dict:
    o = obj.get("data") if isinstance(obj, dict) and isinstance(obj.get("data"), dict) else obj
    if not isinstance(o, dict):
        return {"tipo": type(o).__name__}
    out = {"evidence_id": _ev_id(o), "operacion": o.get("operation")}
    subj = o.get("subject") if isinstance(o.get("subject"), dict) else {}
    if subj:
        out["objetivo"] = subj.get("name") or subj.get("local_path")
        out["formato"] = subj.get("format")
        out["sha256"] = (subj.get("digest") or {}).get("sha256") if isinstance(subj.get("digest"), dict) else None
    nr = o.get("normalized_result") if isinstance(o.get("normalized_result"), dict) else {}
    g = nr.get("graph") if isinstance(nr.get("graph"), dict) else {}
    if g:
        out["nodos"] = len(g.get("nodes") or [])
        out["aristas"] = len(g.get("edges") or [])
    if isinstance(nr.get("statistics"), dict):
        out["estadisticas"] = nr["statistics"]
    if isinstance(nr.get("summary"), (str, dict, list)):
        s = json.dumps(nr["summary"], ensure_ascii=False)
        out["resumen"] = s[:900] + ("…" if len(s) > 900 else "")
    if isinstance(o.get("limitations"), list):
        out["limitaciones"] = o["limitations"][:8]
    return out


def _resumen_capacidades(obj) -> dict:
    base = obj.get("data") if isinstance(obj, dict) and isinstance(obj.get("data"), dict) else obj
    caps = base.get("capabilities") if isinstance(base, dict) else None
    if caps is None and isinstance(base, dict):
        caps = base.get("providers")
    if not isinstance(caps, list):
        return {"nota": "no se pudo resumir 'capabilities'",
                "claves": list(obj)[:12] if isinstance(obj, dict) else []}
    hay, faltan = [], []
    for p in caps:
        if not isinstance(p, dict):
            continue
        if isinstance(p.get("provider"), dict):
            pid = p["provider"].get("id")
        else:
            pid = p.get("id") or p.get("name")
        grupos = p.get("groups") or p.get("capabilities") or p.get("tools") or []
        if not isinstance(grupos, list):
            continue
        ops_ok = 0
        motivo = ""
        for gp in grupos:
            if not isinstance(gp, dict):
                continue
            ops = gp.get("operations") if isinstance(gp.get("operations"), list) else None
            n = len(ops) if ops else 1
            if gp.get("available") is False:
                motivo = motivo or str(gp.get("reason") or gp.get("availability_code") or "")
            elif gp.get("available", True):
                ops_ok += n
        if ops_ok:
            hay.append({"provider": pid, "operaciones": ops_ok})
        elif motivo:
            faltan.append({"provider": pid, "motivo": motivo[:140]})
    out = {"providers_disponibles": hay, "providers_no_disponibles": faltan}
    # Motores de análisis (Ghidra/Hopper/IDA/rizin): acá se ve si hay motor nativo.
    cands = obj.get("analysis_provider_candidates") if isinstance(obj, dict) else None
    if isinstance(cands, list):
        out["proveedores_analisis"] = [
            {"provider": (c.get("provider") or {}).get("id"),
             "estado": (c.get("availability") or {}).get("status"),
             "motivo": str((c.get("availability") or {}).get("reason") or "")[:160]}
            for c in cands if isinstance(c, dict)
        ]
    return out


# ── MCP: registrar el server de REA en Eris ──────────────────────────────────

def mcp_ensure() -> dict:
    """Asegura que el server MCP `rea` esté en memory/mcp_config.json."""
    cfg = {"standard_servers": []}
    try:
        if _MCP_CONFIG.exists():
            cfg = json.loads(_MCP_CONFIG.read_text(encoding="utf-8")) or {"standard_servers": []}
    except Exception:
        cfg = {"standard_servers": []}
    servers = cfg.setdefault("standard_servers", [])
    base = _base_cmd()
    entry = {"name": "rea", "enabled": True,
             "command": base[0], "args": [str(x) for x in base[1:]] + ["mcp"]}
    for i, s in enumerate(servers):
        if s.get("name") == "rea":
            servers[i] = entry
            break
    else:
        servers.append(entry)
    try:
        _MCP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        _MCP_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "config": str(_MCP_CONFIG), "server": entry}
    except Exception as e:
        return {"ok": False, "error": str(e), "server": entry}


def mcp_status() -> dict:
    out = {"configurado": False, "conectado": None, "tools": None}
    try:
        if _MCP_CONFIG.exists():
            cfg = json.loads(_MCP_CONFIG.read_text(encoding="utf-8"))
            out["configurado"] = any(s.get("name") == "rea" for s in cfg.get("standard_servers", []))
    except Exception:
        pass
    try:
        from actions.mcp_standard import get_status, list_tools
        out["estado"] = get_status("rea")
        try:
            out["tools"] = len(list_tools("rea"))
        except Exception:
            pass
    except Exception as e:
        out["estado"] = f"n/a: {e}"
    return out


# ── Estado general ───────────────────────────────────────────────────────────

def estado() -> dict:
    ver = _version()
    return {
        "ok": bool(ver),
        "rea_version": ver or "(no detectada)",
        "node": (shutil.which("node") or "(no)"),
        "npx": (shutil.which("npx") or "(no)"),
        "comando_base": " ".join(_base_cmd()),
        "skill_instalada": _SKILL_DIR.exists(),
        "mcp": mcp_status(),
        "evidencia_dir": str(_EVID_DIR),
        "corridas": len(_load().get("corridas", [])),
        "atajos": sorted(_ATAJOS.keys()),
    }


# ── Tool ─────────────────────────────────────────────────────────────────────

def _ferror(msg: str, **extra) -> dict:
    d = {"ok": False, "error": msg}
    d.update(extra)
    return d


def rea_tool(parameters=None, player=None, **kwargs) -> dict:
    """Ingeniería inversa con REA. Acciones en `estado()` y `_ATAJOS` + comando."""
    params = parameters
    if isinstance(parameters, str):
        try:
            params = json.loads(parameters)
        except Exception:
            params = {}
    params = params if isinstance(params, dict) else {}
    action = (params.get("action") or "estado").strip().lower()

    if action in ("estado", "status"):
        return estado()

    if action in ("mcp", "mcp_estado", "conectar"):
        sub = (params.get("sub") or params.get("modo") or "estado").strip().lower()
        if sub in ("config", "registrar", "ensure", "agregar"):
            return mcp_ensure()
        if sub in ("conectar", "connect", "bridge"):
            r = mcp_ensure()
            try:
                from core.mcp_bridge import bridge_standard_tools
                res = bridge_standard_tools()
                reg = [x for x in res if x.get("registered")]
                return {"ok": True, "registro": r, "tools_bridged": len(reg),
                        "errores": [x for x in res if x.get("error")]}
            except Exception as e:
                return {"ok": True, "registro": r, "bridge_error": str(e)}
        return mcp_status()

    if action in ("evidencia", "evidencias"):
        return _evidencias(params)

    if action == "doctor":
        rc, out, err = _run(["mcp", "doctor", "--json"], timeout=180)
        obj = _loads(out)
        archivo = _save_evidence("mcp-doctor", obj, out)
        _record("mcp-doctor", rc == 0, _ev_id(obj), archivo)
        if isinstance(obj, dict):
            inv = obj.get("inventory") or {}
            tools = inv.get("tools") if isinstance(inv, dict) else None
            return {"ok": bool(obj.get("healthy")), "healthy": obj.get("healthy"),
                    "tools": tools, "servidor": obj.get("server"),
                    "checks": obj.get("checks"), "archivo_evidencia": archivo,
                    "stderr": (err or "")[:300] if rc != 0 else ""}
        return {"ok": rc == 0, "raw": out[:1500], "error": err[:400], "archivo_evidencia": archivo}

    if action in ("capacidades", "capabilities", "proveedores"):
        rc, out, err = _run(["capabilities", "--json"], timeout=180)
        obj = _loads(out)
        archivo = _save_evidence("capabilities", obj, out)
        _record("capabilities", rc == 0, "", archivo)
        if obj is None:
            return _ferror("REA no devolvió JSON", stderr=err[:400], archivo_evidencia=archivo)
        res = _resumen_capacidades(obj)
        res.update({"ok": True, "archivo_evidencia": archivo})
        return res

    if action in ("comandos", "herramientas", "comandos_rea"):
        rc, out, err = _run(["--help"], timeout=120)
        nombres = []
        for line in (out or "").splitlines():
            s = line.strip()
            if not s or s.startswith(("Usage", "Commands", "Global", "rea ", "--")):
                continue
            tok = s.split()[0]
            if tok and all(c.isalnum() or c in "-_" for c in tok) and len(tok) > 2:
                nombres.append(tok)
        nombres = sorted(set(nombres))
        archivo = _save_evidence("comandos", {"comandos": nombres}, out)
        return {"ok": rc == 0, "total": len(nombres), "primeros": nombres[:60],
                "archivo_evidencia": archivo}

    # Comandos que operan sobre una ruta
    if action in _ATAJOS:
        cmd = _ATAJOS[action]
        path = params.get("path") or params.get("ruta") or params.get("arg") or ""
        if not path:
            return _ferror(f"'{action}' necesita 'path' (archivo o carpeta a analizar).")
        p = Path(str(path)).expanduser()
        if not p.exists():
            return _ferror(f"no existe la ruta: {p}")
        extra = [cmd, str(p)]
        opciones = params.get("opciones")
        if isinstance(opciones, str) and opciones.strip():
            extra += opciones.split()
        elif isinstance(opciones, list):
            extra += [str(x) for x in opciones]
        timeout = int(params.get("timeout") or _DEFAULT_TIMEOUT)
        rc, out, err = _run(extra + ["--json"], timeout=timeout)
        obj = _loads(out)
        archivo = _save_evidence(cmd, obj, out)
        _record(cmd, rc == 0 and obj is not None, _ev_id(obj), archivo)
        if obj is None:
            return _ferror(f"REA no devolvió JSON para '{cmd}'",
                           rc=rc, stderr=err[:500], archivo_evidencia=archivo)
        res = _resumen_resultado(obj)
        res.update({"ok": True, "comando": cmd, "archivo_evidencia": archivo})
        _primer_uso_novedad(cmd, res.get("evidence_id"))
        return res

    if action in ("comando", "ejecutar", "raw", "cli"):
        cmd = (params.get("comando") or params.get("cmd") or "").strip()
        if not cmd:
            return _ferror("'comando' necesita 'comando' (p. ej. 'analyze-javascript-application').")
        extra = [cmd]
        arg = params.get("arg") or params.get("path") or params.get("ruta")
        if arg:
            extra.append(str(Path(str(arg)).expanduser()))
        opciones = params.get("opciones") or params.get("args")
        if isinstance(opciones, str) and opciones.strip():
            import shlex as _sh
            extra += _sh.split(opciones)
        elif isinstance(opciones, list):
            extra += [str(x) for x in opciones]
        if params.get("json", True) is not False:
            extra.append("--json")
        timeout = int(params.get("timeout") or _DEFAULT_TIMEOUT)
        rc, out, err = _run(extra, timeout=timeout)
        obj = _loads(out)
        archivo = _save_evidence(cmd, obj, out)
        _record(cmd, rc == 0, _ev_id(obj), archivo)
        res = _resumen_resultado(obj) if obj is not None else {"salida": (out or "")[:1500]}
        res.update({"ok": rc == 0, "comando": cmd, "rc": rc,
                    "archivo_evidencia": archivo, "stderr": (err or "")[:400] if rc != 0 else ""})
        if rc == 0:
            _primer_uso_novedad(cmd, res.get("evidence_id"))
        return res

    return _ferror(f"acción desconocida: '{action}'. Usá estado, doctor, capacidades, "
                   "comandos, evidencia, mcp, uno de los atajos "
                   f"({', '.join(sorted(_ATAJOS))}) o 'comando'.")


def _evidencias(params: dict) -> dict:
    try:
        _EVID_DIR.mkdir(parents=True, exist_ok=True)
        archivos = sorted(_EVID_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception as e:
        return _ferror(str(e))
    ver = params.get("archivo") or params.get("name")
    if ver:
        p = _EVID_DIR / str(ver)
        if not p.exists():
            cand = [a for a in archivos if str(ver) in a.name]
            p = cand[0] if cand else p
        try:
            txt = p.read_text(encoding="utf-8")
            if len(txt) <= 20000:
                return {"ok": True, "archivo": str(p), "contenido": json.loads(txt)}
            obj = json.loads(txt)
            return {"ok": True, "archivo": str(p), "bytes": len(txt),
                    "nota": "evidencia grande: devuelvo claves + comando; leé el archivo completo",
                    "comando": obj.get("comando"), "claves": list(obj.get("resultado", obj))[:20]
                    if isinstance(obj.get("resultado", obj), dict) else None}
        except Exception as e:
            return _ferror(str(e))
    return {"ok": True, "dir": str(_EVID_DIR),
            "ultimos": [{"archivo": a.name, "bytes": a.stat().st_size} for a in archivos[:15]]}


def _primer_uso_novedad(cmd: str, evidence_id: str = "") -> None:
    state = _load()
    if state.get("novedad_dada"):
        return
    _novedad(f"Absorbí REA: ya hago ingeniería inversa (ejecuté '{cmd}'"
             + (f", evidencia {evidence_id[:14]}…" if evidence_id else "") + ").")
    with _lock:
        s = _load()
        s["novedad_dada"] = True
        _save(s)
    _reindexar()


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(estado(), ensure_ascii=False, indent=2))
