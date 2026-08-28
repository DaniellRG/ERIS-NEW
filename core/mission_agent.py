"""core/mission_agent.py — El PROTOCOLO OPERATIVO de ERIS (estilo opencode).

Estructura cualquier tarea (chica o grande) en fases con método:
  1) MISIÓN:  cuaderno de trabajo persistido (objetivo + proyecto + pasos).
  2) EXPLORAR: mapear el proyecto (árbol, grep, leer README/código clave)
               ANTES de tocar, para entender el PORQUÉ de la app.
  3) PLAN:    pasos tickeados (done/blocked).
  4) EDITAR:  cambios mínimos y quirúrgicos con backup + validación + rollback
               (reutiliza la maquinaria segura de code_guard).
  5) VERIFICAR: correr validadores (ruff/py_compile/node) y opcionalmente
               pytest; NO declarar 'listo' hasta que esté verde.
  6) APRENDER: guardar lo entendido del proyecto para la próxima (loop de
               superación: cada misión deja conocimiento acumulado).

Estado: memory/missions/<id>/mission.json (+ memory/missions/current.json).
"""
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

try:
    from core.code_guard import (
        _NODE_EXTS,
        _changed_fraction,
        _run,
        _validate_file,
        _venv_python,
    )
except Exception:  # import aislado en tests/módulo
    _NODE_EXTS = {".js", ".mjs", ".cjs"}
    from core.code_guard import (
        _changed_fraction,
        _run,
        _validate_file,
        _venv_python,
    )

_BASE = Path(__file__).resolve().parent.parent
_MISSIONS = _BASE / "memory" / "missions"
_CURRENT = _MISSIONS / "current.json"
_PROJECTS = _BASE / "memory" / "proyectos"
_BACKUPS = _BASE / "memory" / "mission_backups"
_MEJORAS = _BASE / "memory" / "mejoras"

_SKIP = {"node_modules", ".venv", "__pycache__", ".git", "venv", "site-packages",
         ".pytest_cache", ".mypy_cache", "backups", "missions", "mejoras"}
_MAX_SEG = 2_000_000  # no leer archivos gigantes

PROTOCOLO = """PROTOCOLO OPERATIVO DE ERIS (para CUALQUIER tarea, chica o grande):
1. ENTENDER: nunca tocar sin entender. Explorar el contexto (proyecto,
   archivos, qué pide el usuario) antes de actuar.
2. PLANEAR: si hay más de un paso, anotar el plan y seguirlo tickeando.
3. HACER: cambios mínimos y quirúrgicos, con backup y rollback. Nada mágico.
4. VERIFICAR: probar con el sistema real (tests/lint/compilar/ejecutar).
   NUNCA decir "listo" si no comprobé que funciona.
5. APRENDER: guardar lo entendido para la próxima vez y superarse.
Reglas: preguntar si falta información; si algo no funciona, diagnosticar y
reintentar; nunca inventar resultados; los cambios sobre el propio código de
Eris siempre con backup previo."""


# ── Estado de misiones ──────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().isoformat()


def _id_from(objetivo: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (objetivo or "").lower())[:40].strip("_")
    return time.strftime("%Y%m%d_%H%M%S") + "_" + (slug or "mision")


def fresh_mission(objetivo: str, proyecto: str = "") -> dict:
    return {
        "id": _id_from(objetivo),
        "titulo": (objetivo or "")[:120],
        "objetivo": objetivo or "",
        "proyecto": proyecto or str(_BASE),
        "fase": "inicio",
        "pasos": [],
        "log": [],
        "contexto": [],
        "aprendizaje": [],
        "created_at": _now(),
        "updated_at": _now(),
        "cerrada": False,
    }


def _mission_dir(mission_id: str) -> Path:
    return _MISSIONS / mission_id


def _mission_file(mission_id: str) -> Path:
    return _mission_dir(mission_id) / "mission.json"


def _save(m: dict):
    try:
        m["updated_at"] = _now()
        d = _mission_dir(m["id"])
        d.mkdir(parents=True, exist_ok=True)
        (_mission_file(m["id"])).write_text(
            json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
        _CURRENT.parent.mkdir(parents=True, exist_ok=True)
        _CURRENT.write_text(m["id"], encoding="utf-8")
    except Exception:
        pass


def _load(mission_id: str = "") -> dict | None:
    if not mission_id:
        if not _CURRENT.exists():
            return None
        mission_id = _CURRENT.read_text(encoding="utf-8").strip()
    f = _mission_file(mission_id)
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def current_mission() -> dict | None:
    m = _load()
    return m if m and not m.get("cerrada") else None


def _log(m: dict, evento: str):
    m.setdefault("log", []).append(f"[{time.strftime('%H:%M')}] {evento}")
    if len(m["log"]) > 200:
        m["log"] = m["log"][-200:]
    m["phasic"] = None
    m["fase"] = evento.split(" ")[0].lower()
    _save(m)


# ── 2) EXPLORAR: entender antes de tocar ─────────────────────────────────

def _tree(path: Path, depth: int) -> list[str]:
    out = []
    try:
        entries = sorted(path.iterdir())
    except Exception:
        return out
    for e in entries:
        if e.name in _SKIP or e.name.startswith("."):
            continue
        pad = "  " * max(0, depth)
        if e.is_dir():
            out.append(f"{pad}{e.name}/")
            if depth > 0:
                out.extend(_tree(e, depth - 1))
        else:
            out.append(f"{pad}{e.name}")
    return out[:400]


def _read_excerpt(p: Path, max_lines: int = 60) -> str:
    try:
        if p.stat().st_size > _MAX_SEG:
            return f"(archivo muy grande: {p.stat().st_size} bytes, no leído)"
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        clipped = lines[:max_lines]
        return "\n".join(clipped) + ("\n..." if len(lines) > max_lines else "")
    except Exception as e:
        return f"(no pude leer: {str(e)[:60]})"


def explore(proyecto: str = "", max_depth: int = 2, buscar: str = "") -> dict:
    """Mapea el proyecto: árbol + grep de símbolo + extractos de archivos
    clave. Devuelve todo en 'texto' para que ERIS entienda el contexto."""
    base = Path(proyecto) if proyecto else _BASE
    if not base.exists() or not base.is_dir():
        return {"ok": False, "texto": f"No encuentro la carpeta {base}"}
    parts = ["🌳 ÁRBOL DEL PROYECTO", f"  {base}", *(_tree(base, max_depth))]
    # archivos clave
    clave = []
    for pat in ("README*", "readme*", "pyproject.toml", "setup.py", "requirements.txt",
                "package.json", "main.py", "AGENTS.md", "config.json"):
        g = list(base.glob(pat))[:1]
        clave.extend(g)
    if not clave:
        clave = [base / "main.py"] if (base / "main.py").exists() else []
    if clave:
        parts.append("\n📄 ARCHIVOS CLAVE")
        for f in clave[:6]:
            parts.append(f"── {f.relative_to(base) if f.is_relative_to(base) else f.name}")
            parts.append(_read_excerpt(f))
    if buscar:
        parts.append(f"\n🔎 BÚSQUEDA: {buscar}")
        import subprocess
        rg = _run(["rg", "-n", "-m", "15", buscar, str(base),
                   "-g", "!.venv/*", "-g", "!node_modules/*",
                   "-g", "!__pycache__/*", "-g", "!backups/*"], timeout=60)
        hits = [l for l in (rg[1] or "").splitlines()][:40]
        parts.extend(hits or ["(sin coincidencias)"])
    texto = "\n".join(parts)
    return {"ok": True, "proyecto": str(base), "texto": texto[:9000],
            "archivos_clave": [str(f) for f in clave][:6]}


# ── 4) EDITAR: cambio mínimo seguro ──────────────────────────────────────

def _backup(p: Path) -> str | None:
    try:
        _BACKUPS.mkdir(parents=True, exist_ok=True)
        b = _BACKUPS / f"{time.strftime('%Y%m%d_%H%M%S')}_patch_{p.name}"
        b.write_text(p.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        return b.name
    except Exception:
        return None


def _line_diff_count(old: str, new: str) -> int:
    import difflib
    o, n = old.splitlines(), new.splitlines()
    sm = difflib.SequenceMatcher(None, o, n)
    changed = 0
    for op in sm.get_opcodes():
        if op[0] != "equal":
            changed += max(op[2] - op[1], op[4] - op[3])
    return changed


def edit(file: str, content: str, confirm: bool = False) -> str:
    """Aplica el nuevo contenido con backup previo, valida y hace rollback
    si rompe. Rechaza cambios gigantes sin confirmación. Es la manera de
    tocar el código de ERIS o del usuario de forma segura."""
    p = Path(file)
    if not p.is_file():
        return f"No encuentro el archivo {p}"
    try:
        original = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"No pude leer {p}: {str(e)[:60]}"
    new = content
    if new == original:
        return "El contenido es idéntico al actual: no hay nada que cambiar."
    ln = _line_diff_count(original, new)
    flines = len(original.splitlines())
    frac_ok = 0.95 if confirm else 0.4
    # piso de líneas: un tope porcentual puro castiga archivos chicos
    tope = max(20, int(flines * frac_ok))
    if ln > tope or (flines > 30 and ln / flines > frac_ok):
        return (f"Cambio demasiado grande para aplicarlo solo: tocaría "
                f"{int(ln / max(flines,1) * 100)}% del archivo ({ln} líneas). "
                f"Ajustá el contenido o confirmá que es intencional (confirm=true).")
    bk = _backup(p)
    try:
        p.write_text(new, encoding="utf-8")
    except Exception as e:
        return f"No pude escribir: {str(e)[:60]}"
    if not _validate_file(p):
        if bk:
            try:
                p.write_text((_BACKUPS / bk).read_text(encoding="utf-8"),
                             encoding="utf-8")
            except Exception:
                pass
        return (f"El cambio rompe el archivo (no compila): lo restauré. "
                f"Backup: {bk}")
    frag = f"Backup: {bk}." if bk else ""
    return (f"Aplicado sobre {p.name} ({ln} líneas afectadas, "
            f"{int(ln / max(flines,1) * 100)}%). {frag} "
            f"Validado: compila. Verificá el resultado con mission verify.")


# ── 5) VERIFICAR: nadie dice 'listo' sin pruebas ─────────────────────────

def verify(path: str = "", tests: bool = False) -> dict:
    """Corre validadores sobre el archivo o carpeta. Devuelve verde rojo."""
    base = Path(path) if path else _BASE
    targets = [base] if base.is_file() else sorted(
        f for f in base.rglob("*")
        if f.is_file() and f.suffix.lower() in (".py", ".js", ".mjs", ".cjs")
        and not any(sk in f.parts for sk in _SKIP))
    malos = []
    check = 0
    for t in targets[:250]:
        suf = t.suffix.lower()
        if suf == ".py":
            ok = _validate_file(t)
            if ok:
                code, out = _run([_venv_python(), "-m", "ruff", "check", str(t),
                                  "--output-format=concise"], timeout=60)
                ok = code in (0, 1)
                out = (out or "").strip()
                if code == 1 and out:
                    malos.append(f"{t.name}: {out.splitlines()[0][:90]}")
                    ok = False
            else:
                malos.append(f"{t.name}: no compila")
        elif suf in _NODE_EXTS:
            code, _ = _run(["node", "--check", str(t)], timeout=40)
            if code != 0:
                malos.append(f"{t.name}: sintaxis JS inválida")
                ok = False
            else:
                ok = True
        else:
            continue
        check += 1
    res = {"ok": not malos, "archivos_checkeados": check,
           "problemas": malos[:20], "tests": False}
    if tests and base.is_dir():
        tdir = base / "tests"
        if not tdir.exists():
            cands = [d for d in base.glob("test*.py")] or [base / "test_all.py"]
            if cands and cands[0].exists():
                tdir = base
        if tdir.exists():
            code, out = _run([_venv_python(), "-m", "pytest", str(tdir),
                              "-q", "--tb=line"], timeout=300)
            res["tests"] = True
            res["tests_ok"] = code == 0
            res["tests_report"] = (out or "")[-600:]
            if code != 0:
                res["ok"] = False
    return res


# ── 6) APRENDER: loop de superación ─────────────────────────────────────

def _project_slug(d: Path) -> str:
    name = d.name if d.name not in ("", ".") else "eris"
    return re.sub(r"[^a-z0-9]+", "_", name.lower())[:40].strip("_")


def learn(m: dict, notas: str) -> str:
    m.setdefault("aprendizaje", []).append(notas)
    # memoria por proyecto (persiste entre misiones)
    proj = Path(m.get("proyecto", _BASE))
    slug = _project_slug(proj)
    pf = _PROJECTS / f"{slug}.json"
    pf.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
    except Exception:
        data = {}
    data.setdefault("proyecto", str(proj))
    data.setdefault("aprendizaje", []).append({"fecha": _now(), "nota": notas})
    data["aprendizaje"] = data["aprendizaje"][-30:]
    data["contexto_clave"] = list(dict.fromkeys(
        (data.get("contexto_clave") or []) + [str(c) for c in m.get("contexto", [])]))
    pf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    _save(m)
    return f"Guardado. La próxima misión sobre {slug} arranca con este contexto."


def propose_mejora(nota: str):
    """Si la misión tocó el código de ERIS, registrar sugerencia de mejora."""
    try:
        _MEJORAS.mkdir(parents=True, exist_ok=True)
        f = _MEJORAS / f"{time.strftime('%Y%m%d_%H%M%S')}.json"
        f.write_text(json.dumps({"fecha": _now(), "sugerencia": nota[:300]},
                                indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# ── Tool ──────────────────────────────────────────────────────────────────

def _status_text(m: dict | None) -> str:
    if not m:
        return "No hay misión activa. Usá action=start con un objetivo."
    pasos = m.get("pasos", [])
    tick = sum(1 for x in pasos if x.get("estado") == "done")
    lines = [f"📌 MISIÓN: {m.get('titulo')}",
             f"  proyecto: {m.get('proyecto')}",
             f"  fase: {m.get('fase')} | pasos: {tick}/{len(pasos)}"]
    for p in pasos:
        marca = "✅" if p.get("estado") == "done" else ("⛔" if p.get("estado") == "blocked" else "⬜")
        lines.append(f"  {marca} {p.get('n')}. {p.get('desc','')[:80]}")
    if m.get("contexto"):
        lines.append(f"  contexto: {len(m['contexto'])} extracto(s)")
    if m.get("aprendizaje"):
        lines.append(f"  aprendido: {len(m['aprendizaje'])} nota(s)")
    return "\n".join(lines)


def mission_tool(params: dict = None, player=None) -> str:
    params = params or {}
    action = str(params.get("action", "status")).lower()
    m = current_mission()
    try:
        if action in ("start", "nueva"):
            m = fresh_mission(str(params.get("objetivo", "") or "Misión sin nombre"),
                              str(params.get("proyecto", "") or ""))
            _save(m)
            _log(m, "mision abierta")
            base = Path(m["proyecto"])
            if base.exists():
                exp = explore(str(base), max_depth=int(params.get("max_depth", 2)))
                m["contexto"] = (m.get("contexto") or []) + (
                    [{"archivos_clave": exp.get("archivos_clave", [])}])
                _save(m)
                return ("Cuaderno abierto:\n" + _status_text(m) +
                        "\n\n🌳 Contexto inicial del proyecto:\n" + exp["texto"][:1500])
            return "Cuaderno abierto:\n" + _status_text(m)
        m = current_mission()
        if action in ("plan", "pasos"):
            if not m:
                return "Primero abrí una misión (action=start)."
            pasos = params.get("pasos") or []
            if isinstance(pasos, str):
                import ast as _ast
                try:
                    pasos = _ast.literal_eval(pasos)
                except Exception:
                    pasos = [s for s in re.split(r"\n|;", pasos) if s.strip()]
            m["pasos"] = [{"n": i + 1, "desc": str(x)[:160], "estado": "pending"}
                          for i, x in enumerate(pasos)]
            _log(m, "plan")
            return "Plan armado:\n" + _status_text(m)
        if action in ("step", "tick"):
            if not m:
                return "No hay misión activa."
            n = int(params.get("n", 1))
            estado = str(params.get("estado", "done")).lower()
            for p in m.get("pasos", []):
                if p.get("n") == n:
                    p["estado"] = estado
                    _log(m, f"paso {n} {estado}")
                    return f"Paso {n} → {estado}.\n" + _status_text(m)
            return f"No existe el paso {n}."
        if action in ("explore", "explorar"):
            if not m:
                return "Primero abrí una misión."
            exp = explore(str(params.get("path") or m.get("proyecto", "")),
                          max_depth=int(params.get("max_depth", 2)),
                          buscar=params.get("buscar") or "")
            if exp["ok"]:
                m["contexto"] = (m.get("contexto") or []) + [{"tree":
                    str(exp.get("archivos_clave"))}]
                _log(m, "explorar")
            return exp.get("texto", exp.get("ok", False))
        if action in ("read", "leer"):
            if not m:
                return "Primero abrí una misión."
            path = params.get("path") or params.get("file") or ""
            if not path:
                return "Pasá path=... con el archivo a leer."
            p = Path(path)
            if p.is_dir():
                parts = [f"📁 {p}/", *(_tree(p, 1))]
                return "\n".join(parts[:120])
            if not p.is_file():
                return f"No encuentro {p}"
            full = _read_excerpt(p, max_lines=int(params.get("max_lines", 80)))
            m["contexto"] = (m.get("contexto") or []) + [{"file": str(p)}]
            _log(m, "leer")
            return full[:12000]
        if action in ("edit", "editar"):
            if not m:
                return "Primero abrí una misión."
            file = str(params.get("file") or params.get("path") or "")
            content = params.get("content") or ""
            if not file or not content:
                return "Pasá file=... y content=... (el contenido NUEVO completo)."
            r = edit(file, content, confirm=bool(params.get("confirm", False)))
            if r.startswith("Aplicado"):
                _log(m, "editar " + Path(file).name)
            return r
        if action in ("verify", "verificar"):
            if not m:
                return "Primero abrí una misión."
            res = verify(str(params.get("path") or m.get("proyecto", "")),
                         tests=bool(params.get("tests", False)))
            txt = [f"Verificación: {'✅ VERDE' if res['ok'] else '❌ ROJO'}",
                   f"  archivos checkeados: {res.get('archivos_checkeados', 0)}"]
            txt += [f"  ⚠ {x}" for x in res.get("problemas", [])[:10]]
            if res.get("tests"):
                txt.append(f"  pytest: {'OK' if res.get('tests_ok') else 'FALLA'} · {res.get('tests_report','')[-200:].strip()}")
            if res["ok"]:
                _log(m, "verificar verde")
                txt.append("\nEstado: tu trabajo está LISTO según el protocolo.")
            else:
                txt.append("\nFaltan correcciones. No cierres la misión todavía.")
            return "\n".join(txt)
        if action in ("learn", "aprender"):
            if not m:
                return "Primero abrí una misión."
            notas = params.get("notas") or params.get("content") or ""
            if not notas:
                return "Pasá notas=... con lo que aprendiste del proyecto."
            return learn(m, notas)
        if action in ("close", "cerrar"):
            if not m:
                return "No hay misión activa."
            m["cerrada"] = True
            _log(m, "cerrar")
            summary = (
                f"✅ MISION CERRADA: {m.get('titulo')}\n"
                f"  pasos: {sum(1 for x in m.get('pasos',[]) if x.get('estado')=='done')}/"
                f"{len(m.get('pasos',[]))} "
                f"aprendizajes: {len(m.get('aprendizaje',[]))}")
            _CURRENT.write_text("", encoding="utf-8")
            try:
                from core.self_evolution import vault_note
                slug = re.sub(r"[^a-z0-9_\- ]", "", str(m.get("titulo", "").lower()))[:40]
                content = (f"# Misión: {m['titulo']}\n\n"
                           f"- **Inicio:** {m.get('inicio','')}\n"
                           f"- **Cierre:** {_now()}\n"
                           f"- **Proyecto:** {m.get('proyecto') or '-'}\n\n"
                           f"## Objetivo\n{m.get('objetivo','')}\n\n"
                           f"## Aprendizaje (persistido)\n"
                           + ("\n".join(f"- {a}" for a in m.get("aprendizaje", [])) or "- ninguno aún"))
                rel = vault_note("Proyectos", f"Misión - {slug}", content)
                summary += f"\n  espejada en Obsidian: {rel}"
            except Exception:
                pass
            return summary
        if action in ("list", "lista"):
            if not _MISSIONS.exists():
                return "Todavía no hay misiones."
            out = []
            for d in sorted(_MISSIONS.iterdir()):
                if d.name == "current.json":
                    continue
                f = d / "mission.json"
                if f.exists():
                    try:
                        dd = json.loads(f.read_text(encoding="utf-8"))
                        out.append(f"{dd.get('id')} · {dd.get('titulo','')[:50]} "
                                   f"· {dd.get('fase')}"
                                   + (" · cerrada" if dd.get("cerrada") else ""))
                    except Exception:
                        pass
            return "Misiones:\n" + "\n".join(out[:20]) if out else "No hay misiones aún."
        if action in ("resume", "retomar"):
            mid = str(params.get("id") or "")
            mm = _load(mid)
            if not mm:
                return f"No encuentro la misión {mid}. Miralas con action=list."
            _save(mm)
            return _status_text(mm)
        if action in ("status", "estado"):
            return _status_text(m)
        return ("Acciones: start (objetivo, proyecto), plan (pasos=list), explore "
                "(path, max_depth, buscar), read (path), edit (file, content), "
                "verify (path, tests), step (n, estado), learn (notas), close, "
                "list, resume (id), status.")
    except Exception as e:
        return f"[MISIÓN] Error: {str(e)[:160]}"


if __name__ == "__main__":
    print(PROTOCOLO)
    print(mission_tool({"action": "start", "objetivo": "probar misión"}))