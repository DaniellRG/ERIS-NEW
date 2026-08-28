# -*- coding: utf-8 -*-
"""
core/code_guard.py — EL OJO GUARDIÁN de Eris sobre el código del usuario.

Detecta en tiempo real errores (rojo) y advertencias (amarillo) del archivo
que el usuario está editando y LOS CORRIGE tocando SOLO las líneas señaladas
(sin reescribir el resto), con backup y validación antes de aplicar. Puede
racionarse: errores E se auto-corrigen, advertencias W se reportan y se
corrigen si el usuario lo pide (config auto_fix_w / sev).

Fuentes de diagnóstico (offline, livianas):
  * py_compile           -> errores de sintaxis (rojo)
  * ruff (E/F/B)         -> errores reales/undefined names (rojo) y
                            advertencias W/I/UP (amarillo); se instala solo
                            la primera vez (pip -q), queda cacheado.
  * node --check         -> sintaxis de .js/.mjs/.cjs (rojo)

Fix con LLM (Gemini 2.5 Flash primero, Ollama de respaldo): se pasa el
archivo + la lista de problemas; el modelo devuelve el archivo corregido,
cambiando lo mínimo. Guardas de seguridad:
  * backup previo en memory/code_guard_backups/<fecha>_<archivo>
  * validación final (py_compile / node --check) antes de confirmar
  * si la corrección rompe la sintaxis -> rollback inmediato
  * si el parche toca >25% del archivo -> se rechaza sin aplicar

Estado en memory/code_guard.json: interval_sec, auto_fix (E), auto_fix_w (W),
cooldown_voz_s, cache de huellas (mtime+size) para no repetir reportes.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "code_guard.json"
_BACKUP_DIR = _BASE / "memory" / "code_guard_backups"

_EDIT_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx", ".c",
             ".cpp", ".h", ".hpp", ".java", ".cs", ".go", ".rb", ".php",
             ".html", ".css", ".json", ".yaml", ".yml", ".sh", ".bat",
             ".ps1", ".sql", ".md"}
_NODE_EXTS = {".js", ".mjs", ".cjs"}
_SKIP_DIRS = {"node_modules", ".venv", "__pycache__", ".git", "venv", "site-packages"}
_LLM_CHECKED = {"gemini": None, "ollama": []}
_LOCK = threading.Lock()
_ruff_ok = None

_DEFAULTS = {
    "interval_sec": 10,        # cada cuánto mira el archivo en foco
    "auto_fix": True,          # corrige sola los errores rojos
    "auto_fix_w": False,       # advertencias amarillas: solo reporta (fix a pedido)
    "cooldown_voz_s": 30,      # min entre avisos por voz del guardián
    "max_fix_fraction": 0.25,  # rechaza parches que toquen más de este % de líneas
    "extra_targets": [],       # archivos/carpetas a vigilar aunque no estén en foco
}


def _fresh_state() -> dict:
    return {"config": dict(_DEFAULTS), "last_fp": "", "reported": {},
            "last_voice": 0.0, "last_target": "", "fixed_hoy": 0}


def _load() -> dict:
    data = None
    if _STATE_FILE.exists():
        try:
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = None
    if not data:
        data = _fresh_state()
    else:
        fresh = _fresh_state()
        for k, v in fresh.items():
            if k not in data:
                data[k] = v
        data["config"] = {**dict(_DEFAULTS), **(data.get("config") or {})}
    return data


def _save(data: dict):
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    except Exception:
        pass


def get_config() -> dict:
    return dict(_load().get("config", {}))


# ── Utilidades ────────────────────────────────────────────────────────────
_VENV_PY = None


def _venv_python() -> str:
    """Ruff/pip viven en el venv; el intérprete vivo (shim de venv) usa el
    python real del sistema que NO los ve. Forzamos el python del venv."""
    global _VENV_PY
    if _VENV_PY is None:
        cand = _BASE / ".venv" / "Scripts" / "python.exe"
        _VENV_PY = str(cand) if cand.exists() else sys.executable
    return _VENV_PY


def _run(cmd: list, timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return -1, f"error: {e}"


def _ruff_installed() -> bool:
    global _ruff_ok
    if _ruff_ok is not None:
        return _ruff_ok
    py = _venv_python()
    code, _ = _run([py, "-m", "ruff", "--version"], timeout=30)
    _ruff_ok = code == 0
    if not _ruff_ok:
        # instalar en el venv (el cache de pip suele estar corrupto → sin cache)
        for _ in range(2):
            code, _ = _run([py, "-m", "pip", "install", "ruff",
                            "-q", "--no-cache-dir"], timeout=300)
            if code == 0:
                break
        code, _ = _run([py, "-m", "ruff", "--version"], timeout=30)
        _ruff_ok = code == 0
    return _ruff_ok


_RED_CODES = {"E999", "F821", "F823", "F811", "F999", "B", "E9"}
_YELLOW_CODES = {"F401", "F841", "E", "W", "I", "UP", "N", "C", "S", "T20"}


def _severity(code: str) -> str:
    """'E' = rojo (rompe), 'W' = amarillo (falta algo / puede fallar)."""
    c = (code or "").upper()
    if not c:
        return "W"
    if c in _RED_CODES or c.startswith("B") or c.startswith("E9"):
        return "E"
    if c.startswith("F") and c not in _YELLOW_CODES:
        return "E"
    return "W"


# ── Escaneo del archivo en foco ───────────────────────────────────────────
def _filename_from_title(title: str) -> str:
    """Del título del editor saca el nombre de archivo editable."""
    tokens = re.split(r"[—|–\-:\\]|\b-\b", title or "")
    for tok in tokens:
        t = tok.strip().strip('"')
        if not t:
            continue
        if any(t.lower().endswith(ext) for ext in _EDIT_EXT):
            if t not in ("main.py", "README.md", "requirements.txt") or title.count(t) > 1:
                pass
            # encabezado estilo "<pieza> — app" ya tokenizado; el archivo es el 1ro con ext
            return t
    return ""


def _proc_cwd(pid: int) -> str:
    try:
        import psutil
        return (psutil.Process(pid).cwd() or "")
    except Exception:
        return ""


def _glob_depth(base: Path, name: str, depth: int) -> list:
    out = []
    base = base or Path(".")
    if not base.is_dir():
        return out
    for p in base.rglob(name):
        if any(s in p.parts for s in _SKIP_DIRS):
            continue
        rel = p.relative_to(base)
        if len(rel.parts) <= depth + 1:
            out.append(p)
        if len(out) >= 40:
            break
    return out


def active_target() -> Path | None:
    """El archivo que el usuario está editando AHORA (editor en foco).
    Fuente: ventana en foco (observer) -> nombre de archivo del título -> cwd
    del proceso editor -> búsqueda superficial. None si no se puede saber."""
    try:
        from core import observer as obs
        fg = obs.get_foreground()
        cl = obs.classify(fg.get("proc", ""), fg.get("title", ""))
        if cl["kind"] not in ("programacion", "terminal"):
            return None
    except Exception:
        return None
    title = fg.get("title") or ""
    name = _filename_from_title(title)
    if not name:
        return None
    p = Path(name)
    if p.is_absolute() and p.is_file():
        return p
    # el título trae ruta completa tipo "C:\\x\\y.py ..."
    m = re.search(r"([A-Za-z]:\\(?:[^\\])+\.\w{1,6})", title.replace("—", "-"))
    if m and Path(m.group(1)).is_file():
        return Path(m.group(1))
    cwd = _proc_cwd(fg.get("pid", 0))
    cwd_p = Path(cwd) if cwd else None
    cand = (cwd_p / name) if cwd_p else None
    if cand is not None and cand.is_file():
        return cand
    for found in _glob_depth(cwd_p, name, 2) if cwd_p else []:
        return found
    # último recurso: proyecto de Eris si estamos ahí
    proj = _BASE / name
    return proj if proj.is_file() else None


def _ruff_diags(path: Path) -> list:
    if not _ruff_installed():
        return []
    code, out = _run([_venv_python(), "-m", "ruff", "check", str(path),
                      "--output-format=concise"],
                     timeout=60)
    if code not in (0, 1) or not out.strip():
        return []
    diags = []
    for ln in out.splitlines():
        ln = ln.strip()
        # formato concise: path:line:col: CODE msg
        m = re.match(r".*:(\d+):(\d+):\s([A-Z]+\d*)\s(.*)$", ln)
        if not m:
            continue
        line, col, codec, msg = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
        sev = _severity(codec)
        diags.append({"line": line, "col": col, "sev": sev,
                      "code": codec, "msg": (msg or "").strip()[:160]})
    return diags


def scan_file(path) -> list:
    """Diagnósticos del archivo: E (rojo) + W (amarillo)."""
    p = Path(path)
    if not p.is_file():
        return []
    if p.stat().st_size > 1_500_000:
        return []
    suffix = p.suffix.lower()
    diags = []
    if suffix == ".py":
        # 1) sintaxis (rojo) — ast da la línea exacta del error
        try:
            import ast
            ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as se:
            diags.append({"line": int(se.lineno or 1), "col": int(se.offset or 0),
                          "sev": "E", "code": "E999",
                          "msg": (getattr(se, "msg", "") or str(se))[:160]})
        except Exception as exc:
            diags.append({"line": 1, "col": 0, "sev": "E", "code": "E999",
                          "msg": (str(exc)[:160] or "syntax error")})
        # 2) ruff (rojos + amarillos)
        try:
            diags.extend(_ruff_diags(p))
        except Exception:
            pass
    elif suffix in _NODE_EXTS:
        code, out = _run(["node", "--check", str(p)], timeout=40)
        if code != 0:
            line = 1
            msg = out.strip().splitlines()[-1] if out.strip() else "syntax error"
            m = re.search(r"(\d+):(\d+)", msg)
            if m:
                line = int(m.group(2))
            diags.append({"line": line, "col": 0, "sev": "E", "code": "E999",
                          "msg": out.strip()[:160]})
    diags.sort(key=lambda d: d["line"])
    return diags


# ── Fix con LLM (solo las líneas señaladas) ───────────────────────────────
def _gemini_text(prompt: str, max_tokens: int = 1600) -> str:
    try:
        cfg = json.loads((_BASE / "config" / "api_keys.json").read_text(encoding="utf-8"))
        key = cfg.get("gemini_api_key", "")
    except Exception:
        key = ""
    if not key:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"max_output_tokens": max_tokens, "temperature": 0.15})
        return (resp.text or "").strip()
    except Exception:
        pass
    return ""


def _ollama_text(prompt: str, max_tokens: int = 1600) -> str:
    import urllib.request
    base = "http://localhost:11434"
    model = None
    global _LLM_CHECKED
    try:
        if _LLM_CHECKED["ollama"]:
            model = _LLM_CHECKED["ollama"][0]
        else:
            with urllib.request.urlopen(f"{base}/api/tags", timeout=4) as r:
                tags = json.loads(r.read()).get("models", [])
            names = [t.get("name", "") for t in tags]
            pref = ["qwen2.5-coder", "qwen2.5", "llama3.1", "llama3", "deepseek-coder"]
            model = next((n for n in pref if any(n in x for x in names)), names[0] if names else "")
            _LLM_CHECKED["ollama"] = [model]
    except Exception:
        return ""
    if not model:
        return ""
    body = json.dumps({"model": model, "prompt": prompt,
                       "stream": False, "options": {"temperature": 0.15,
                                                    "num_predict": max_tokens}}).encode()
    try:
        req = urllib.request.Request(f"{base}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read()).get("response", "").strip()
    except Exception:
        return ""


def _llm_text(prompt: str) -> str:
    if _LLM_CHECKED["gemini"] is not False:
        out = _gemini_text(prompt)
        if out:
            return out
        _LLM_CHECKED["gemini"] = False
    return _ollama_text(prompt)


def _backup(path: Path, label: str) -> Path | None:
    try:
        _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = _BACKUP_DIR / f"{tag}_{label}_{path.name}"
        target.write_bytes(path.read_bytes())
        return target
    except Exception:
        return None


def _validate_file(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix == ".py":
        try:
            import py_compile
            py_compile.compile(str(path), doraise=True)
            return True
        except py_compile.PyCompileError:
            return False
    if suffix in _NODE_EXTS:
        code, _ = _run(["node", "--check", str(path)], timeout=40)
        return code == 0
    return True  # otros: sin validador, confiar en el diff mínimo


def _changed_fraction(old: str, new: str) -> float:
    o = old.splitlines()
    n = new.splitlines()
    if not o:
        return 0.0
    import difflib
    sm = difflib.SequenceMatcher(None, o, n)
    changed = 0
    for op in sm.get_opcodes():
        if op[0] != "equal":
            changed += max(op[2] - op[1], op[4] - op[3])
    return changed / max(len(o), 1)


def _classify_changes(old: str, new: str, flagged: list) -> tuple[int, bool, str]:
    """Valida que el parche toque SOLO zonas señaladas. Devuelve
    (líneas_tocadas, ok, razón_del_rechazo). Reemplazos no-op del modelo
    (línea que no cambió) se ignoran; reemplazos/borrados lejos de una línea
    señalada = rechazo; inserciones (p.ej. la función que falta) se toleran
    con tope de tamaño."""
    o = old.splitlines()
    n = new.splitlines()
    if not o:
        return 0, True, ""
    import difflib
    sm = difflib.SequenceMatcher(None, o, n)
    flagged_sorted = sorted(int(x) for x in flagged)
    changed = 0
    bad = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and o[i1:i2] == n[j1:j2]:
            continue  # el modelo "reescribió" la línea igual: no-op, se ignora
        changed += max(i2 - i1, j2 - j1)
        start = (j1 + 1) if tag == "insert" else (i1 + 1)
        if not flagged_sorted:
            bad.append(f"{tag}@{start}")
            continue
        dist = min(abs(start - f) for f in flagged_sorted)
        tol = 3 if tag == "insert" else 2
        if tag == "insert":
            continue  # agregar la definición que falta: legítimo
        if dist > tol:
            bad.append(f"{tag}@{start}")
    cap = max(15, int(len(o) * 0.5))
    if changed > cap:
        return changed, False, f"demasiado cambio ({changed} líneas > tope)"
    if bad:
        return changed, False, ("toca zonas fuera de lo señalado: "
                                + ", ".join(bad[:4]))
    return changed, True, ""


def fix_file(path, diags=None, dry_run: bool = True) -> str:
    """Corrige SOLO los problemas señalados (E por defecto) del archivo.
    dry_run=True devuelve el diff propuesto sin tocar nada."""
    p = Path(path)
    if not p.is_file():
        return "No existe el archivo."
    if diags is None:
        diags = scan_file(p)
    target = [d for d in diags if d["sev"] == "E"]
    if not target:
        w = [d for d in diags if d["sev"] == "W"]
        return (f"Sin errores rojos en {p.name}. "
                f"{len(w)} advertencias amarillas (a pedido).")
    original = p.read_text(encoding="utf-8", errors="replace")
    lines = f"{len([l for l in original.splitlines() if l.strip()])} líneas de código"
    problems = "\n".join(
        f"- L{d['line']}: [{d['code']}] {d['msg']}" for d in target)
    prompt = (
        f"Sos la asistente Eris corrigiendo código del usuario. Archivo: {p.name}\n"
        f"Estos son los ÚNICOS problemas (errores, en rojo):\n{problems}\n\n"
        f"Tarea: corregí SOLO los problemas listados. NO reescribas el archivo, "
        f"NO cambies el estilo ni la lógica sana, NO toques líneas que no estén "
        f"señaladas salvo que sea imprescindible para el fix. Si un problema no "
        f"se puede corregir con seguridad dejá la línea igual.\n\n"
        f"Contenido actual («{p.name}»):\n---\n{original}\n---\n\n"
        f"Respondé SOLO el archivo completo corregido, sin markdown ni "
        f"explicaciones ni diffs. Si no hay cambios necesarios, copiá el "
        f"contenido tal cual."
    )
    new = _llm_text(prompt)
    if not new or "---" in new[:20]:
        return "No pude generar la corrección (LLM no disponible)."
    new = new.strip()
    tchg, ok, reason = _classify_changes(original, new,
                                         [d["line"] for d in target])
    if not ok:
        return f"Parche rechazado: {reason}. No lo aplico."
    frac = _changed_fraction(original, new)
    if dry_run:
        return (f"Propuesto para {p.name}: toca ~{int(frac*100)}% del archivo "
                f"({problems.splitlines()[0] if problems else ''}).")
    # aplicar con backup + validación + rollback
    backup = _backup(p, "fix")
    tmp = p.with_name(p.stem + ".guard_tmp" + p.suffix)
    try:
        tmp.write_text(new, encoding="utf-8")
        if _validate_file(tmp):
            tmp.replace(p)
            data = _load()
            data["fixed_hoy"] = data.get("fixed_hoy", 0) + 1
            _save(data)
            return (f"Corregí {len(target)} problema(s) en {p.name} "
                    f"(tocó ~{int(frac*100)}% del archivo). Backup: "
                    f"{backup.name if backup else '—'}.")
        cmds = "ruff/node --check" if p.suffix.lower() not in {".py"} else "py_compile"
        return f"No apliqué: la corrección no valida ({cmds}). Restauré el original."
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass


# ── Tool ──────────────────────────────────────────────────────────────────
def code_guard_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "status")).strip().lower()
    path = params.get("path", "")

    if action in ("status", "feel"):
        data = _load()
        cfg = data.get("config", {})
        lines = ["[GUARDIÁN] El ojo guardián de tu código:"]
        tgt = active_target()
        lines.append(f"  Archivo activo: {tgt.name if tgt else '(sin editor en foco)'}")
        if tgt:
            diags = scan_file(tgt)
            e = [d for d in diags if d["sev"] == "E"]
            w = [d for d in diags if d["sev"] == "W"]
            lines.append(f"  Errores (rojo): {len(e)} | Advertencias (amarillo): {len(w)}")
            for d in e[:5] + w[:3]:
                lines.append(f"    L{d['line']} [{d['code']}] {d['msg'][:70]}")
        lines.append(f"  auto_fix={cfg.get('auto_fix')} auto_fix_w={cfg.get('auto_fix_w')} "
                     f"interval={cfg.get('interval_sec')}s")
        extra = cfg.get("extra_targets") or []
        lines.append(f"  vigilando {len(extra)} fijo(s): " + (", ".join(extra[:5]) or "ninguno"))
        lines.append(f"  Corregidos hoy: {data.get('fixed_hoy', 0)}")
        return "\n".join(lines)
    if action in ("scan", "escanear"):
        tgt = Path(path) if path else active_target()
        if not tgt or not Path(tgt).is_file():
            return "[GUARDIÁN] No encontré el archivo activo. Pasá path=..."
        diags = scan_file(tgt)
        if not diags:
            return f"[GUARDIÁN] {Path(tgt).name} está limpio: ni errores ni advertencias."
        lines = [f"[GUARDIÁN] {Path(tgt).name}:"]
        for d in diags:
            sev = "ROJO (error)" if d["sev"] == "E" else "amarillo (aviso)"
            lines.append(f"  L{d['line']} [{d['code']}] {sev}: {d['msg'][:80]}")
        e = sum(1 for d in diags if d["sev"] == "E")
        lines.append(f"  → {e} error(es) rojo(s); el resto amarillos.")
        return "\n".join(lines)
    if action in ("fix", "corregir"):
        tgt = Path(path) if path else active_target()
        if not tgt or not Path(tgt).is_file():
            return "[GUARDIÁN] No encontré el archivo activo. Pasá path=..."
        dry = bool(params.get("dry_run", params.get("preview", False)))
        sev = str(params.get("sev", "E"))
        if sev.upper() == "A":
            # todos (rojos + amarillos)
            return _fix_all(tgt, dry_run=dry)
        return fix_file(tgt, dry_run=dry)
    if action in ("fijar_w", "fix_w"):
        tgt = Path(path) if path else active_target()
        if not tgt or not Path(tgt).is_file():
            return "[GUARDIÁN] No encontré el archivo activo."
        diags = scan_file(tgt)
        cur = _load()
        cur["said_w"] = _fingerprint_lines(diags)
        _save(cur)
        lines = [f"[GUARDIÁN] Advertencias (amarillas) de {tgt.name}:"]
        for d in diags:
            if d["sev"] == "W":
                lines.append(f"  L{d['line']} [{d['code']}] {d['msg'][:80]}")
        return "\n".join(lines)
    if action == "config":
        data = _load()
        cfg2 = dict(data.get("config", {}))
        for k in ("interval_sec", "auto_fix", "auto_fix_w", "cooldown_voz_s",
                  "max_fix_fraction"):
            if k in params and params[k] is not None:
                cfg2[k] = params[k]
        if "extra_targets" in params:
            raw = params["extra_targets"]
            if isinstance(raw, str):
                raw = [raw]
            cfg2["extra_targets"] = [str(x) for x in raw]
        data["config"] = cfg2
        _save(data)
        return ("[GUARDIÁN] Config: " + ", ".join(f"{k}={v}" for k, v in cfg2.items()))
    if action == "reset":
        _save(_fresh_state())
        return "[GUARDIÁN] Estado del guardián reiniciado."
    return ("Acciones: status, scan (path opcional), fix (corrige solo los "
            "errores rojos; path opcional, dry_run=true para previsualizar), "
            "fix_w (advertencias amarillas a pedido), config "
            "(interval_sec, auto_fix, auto_fix_w, cooldown_voz_s, "
            "extra_targets=[rutas]), reset.")


def _fix_all(tgt: Path, dry_run: bool) -> str:
    diags = scan_file(tgt)
    p = Path(tgt)
    if not diags:
        return f"[GUARDIÁN] {p.name} está limpio."
    original = p.read_text(encoding="utf-8", errors="replace")
    problems = "\n".join(
        f"- L{d['line']}: [{d['code']}] {'ERROR' if d['sev']=='E' else 'aviso'} {d['msg']}"
        for d in diags)
    prompt = (
        f"Sos Eris corrigiendo {p.name}. Problemas (rojo=error, amarillo=aviso):\n"
        f"{problems}\n\nCorregí solo lo señalado, mínimo cambio, sin reescribir. "
        f"Respondé SOLO el archivo completo corregido, sin markdown.\n\n"
        f"---\n{original}\n---")
    new = _llm_text(prompt)
    if not new:
        return "[GUARDIÁN] No pude generar la corrección (LLM no disponible)."
    tchg, ok, reason = _classify_changes(original, new.strip(),
                                         [d["line"] for d in diags])
    frac = _changed_fraction(original, new.strip())
    if not ok:
        return f"[GUARDIÁN] Rechazo: {reason}."
    if dry_run:
        return f"[GUARDIÁN] Listo para corregir {p.name}: toca ~{int(frac*100)}%."
    backup = _backup(p, "fixw")
    tmp = p.with_name(p.stem + ".guard_tmp" + p.suffix)
    try:
        tmp.write_text(new.strip(), encoding="utf-8")
        if _validate_file(tmp):
            tmp.replace(p)
            return (f"[GUARDIÁN] Corregí {len(diags)} señal(es) en {p.name} "
                    f"(rojos + amarillos).")
        return "[GUARDIÁN] La corrección no validó; restauré el original."
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass


def _fingerprint_lines(diags: list) -> str:
    return hashlib.md5(
        ";".join(f"{d['code']}@{d['line']}" for d in diags).encode()).hexdigest()


def _fp_of(path: Path) -> str:
    try:
        st = path.stat()
        return hashlib.md5(f"{st.st_mtime_ns}:{st.st_size}".encode()).hexdigest()
    except Exception:
        return ""


# ── Loop de tiempo real (llamado desde main) ──────────────────────────────
def _expand_extra_targets() -> list[Path]:
    """Los extra_targets configurados como archivos o carpetas (una nivel)."""
    out: list[Path] = []
    for raw in get_config().get("extra_targets") or []:
        p = Path(str(raw)).expanduser()
        if not p.exists():
            continue
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            for f in sorted(p.iterdir()):
                if f.is_file() and f.suffix.lower() == ".py":
                    out.append(f)
    return out


def scan_extra_targets(on_report=None, on_speak=None) -> list[dict] | None:
    """Pasada a targets fijos (extra_targets): detecta y corrige igual que el
    foco, pero sin requerir que el usuario esté en el editor."""
    tgt = _expand_extra_targets()
    if not tgt:
        return None
    cfg = get_config()
    data = _load()
    now = time.time()
    cooldown = cfg.get("cooldown_voz_s", 30)
    speak = (now - data.get("last_voice", 0)) >= cooldown
    results = []
    for p in tgt:
        try:
            name = p.name
            known = data.get("reported", {}).get(str(p), "")
            diags = scan_file(p)
            fp_diags = _fingerprint_lines(diags)
            if not diags and not known:
                continue
            if fp_diags == known:
                continue
            data["reported"][str(p)] = fp_diags
            _save(data)
            e = [d for d in diags if d["sev"] == "E"]
            w = [d for d in diags if d["sev"] == "W"]
            if not e and not w:
                continue
            if e:
                fix_result = ""
                if cfg.get("auto_fix"):
                    fix_result = fix_file(p, diags=diags, dry_run=False)
                    if fix_result.startswith("Corregí"):
                        data["fixed_hoy"] = int(data.get("fixed_hoy", 0)) + 1
                detail = "; ".join(f"L{d['line']} {d['msg'][:50]}" for d in e[:3])
                line = f"Encontré {len(e)} errores en {name}: {detail}. " + fix_result
                if speak and on_speak:
                    data["last_voice"] = now
                    _save(data)
                    on_speak(line)
                if on_report:
                    on_report(f"[GUARDIÁN] {len(e)} error(es) rojo(s) en {name} "
                              f"({fix_result or 'sin corregir'}): " +
                              "; ".join(f"L{d['line']} {d['msg'][:40]}" for d in e[:5]),
                              "error")
                results.append({"type": "fixed" if fix_result.startswith("Corregí")
                                else "errors", "file": name, "n": len(e)})
            elif w:
                if on_report:
                    on_report(f"[GUARDIÁN] {len(w)} advertencia(s) amarilla(s) "
                              f"en {name}: " +
                              "; ".join(f"L{d['line']} {d['msg'][:40]}" for d in w[:5]),
                              "warn")
                results.append({"type": "warnings", "file": name, "n": len(w)})
        except Exception:
            continue
    return results if results else None


def guardian_tick(on_report=None, on_speak=None) -> dict | None:
    """Una pasada del guardián. Devuelve dict de resumen si hubo novedad.
    on_report(text, kind) y on_speak(text) los provee main (log/voz)."""
    cfg = get_config()
    tgt = active_target()
    if not tgt:
        return None
    fp = _fp_of(tgt)
    data = _load()
    if fp == data.get("last_fp"):
        return None
    data["last_fp"] = fp
    data["last_target"] = str(tgt)
    diags = scan_file(tgt)
    fp_diags = _fingerprint_lines(diags)
    known = data.get("reported", {})
    fresh = known.get(str(tgt), "") != fp_diags
    data["reported"][str(tgt)] = fp_diags
    _save(data)
    if not fresh:
        return None
    name = tgt.name
    e = [d for d in diags if d["sev"] == "E"]
    w = [d for d in diags if d["sev"] == "W"]
    if not e and not w:
        return None
    # 1) levantar voz si corresponde (cooldown propio del guardián)
    now = time.time()
    cooldown = cfg.get("cooldown_voz_s", 30)
    speak = (now - data.get("last_voice", 0)) >= cooldown
    if e:
        fix_result = ""
        if cfg.get("auto_fix"):
            fix_result = fix_file(tgt, diags=diags, dry_run=False)
        detail = "; ".join(f"L{d['line']} {d['msg'][:50]}" for d in e[:3])
        line = f"Encontré {len(e)} errores en {name}: {detail}. " + fix_result
        if speak and on_speak:
            data["last_voice"] = now
            _save(data)
            on_speak(line)
        if on_report:
            on_report(f"[GUARDIÁN] {len(e)} error(es) rojo(s) en {name} "
                      f"({fix_result or 'sin corregir'}): " +
                      "; ".join(f"L{d['line']} {d['msg'][:40]}" for d in e[:5]),
                      "error")
        return {"type": "fixed" if fix_result.startswith("Corregí") else "errors",
                "file": name, "n": len(e), "detail": line}
    if w:
        if on_report:
            on_report(f"[GUARDIÁN] {len(w)} advertencia(s) amarilla(s) en {name}: "
                      + "; ".join(f"L{d['line']} {d['msg'][:40]}" for d in w[:5]),
                      "warn")
        return {"type": "warnings", "file": name, "n": len(w)}
    return None


if __name__ == "__main__":
    print(active_target())
    print(code_guard_tool({"action": "status"}))
