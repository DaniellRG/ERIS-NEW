"""
crecimiento.py — TABLAS DE CRECIMIENTO de ERIS (Proyecto 2).

El dueño quiere **abrir y ver con sus ojos** cómo creció Eris: qué aprendió, en
qué dominio, en qué nivel, cuándo y con qué **evidencia** que pueda comprobar.

`crecimiento` NO es un store paralelo a `escalada`: es una **vista** en forma de
tabla. La verdad de los logros/niveles vive en `escalada` (12 dominios × 8
niveles) y en el motor de barreras (cada barrera resuelta con evidencia dura).
Acá se arman las tablas y se cachean las filas.

Cada fila se guarda en 4 capas (mismo patrón que `pentest_learning`/`recetario`):

  1. `memory/crecimiento.json`                      (estructurado)
  2. Obsidian `Crecimiento/Tabla-<dominio>.md` + `Crecimiento/Tabla-Maestra.md`
  3. índice en `rag_engine` (`reindexar`, best-effort)
  4. novedad en `todo_yo`

Regla dura: una fila sin evidencia ni ruta se marca `estado="sin_evidencia"`
(visible, no se disfraza de logro comprobado).

Diseño: docs/superpowers/specs/2026-10-14-eris-tablas-de-crecimiento-design.md
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM_DIR = _BASE / "memory"
_FILE = _MEM_DIR / "crecimiento.json"
_KNOW_DIR = _BASE / "data" / "knowledge"
_KNOW_FILE = _KNOW_DIR / "crecimiento_vivo.md"
_lock = threading.Lock()

NIVEL_MAX = 8


def _dominios() -> dict:
    try:
        from core.escalada import DOMINIOS
        return DOMINIOS
    except Exception:
        return {}


def _vault_dir() -> Path | None:
    try:
        from core.logging_setup import get_obsidian_vault
        return Path(get_obsidian_vault()) / "Crecimiento"
    except Exception:
        return None


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load() -> dict:
    if _FILE.exists():
        try:
            return json.loads(_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"created": _now(), "dominios": {},
            "stats": {"dominios_activos": 0, "filas_totales": 0, "con_evidencia": 0}}


def _save(state: dict):
    _MEM_DIR.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _reindexar() -> str:
    try:
        from core.rag_engine import index_todo
        return str(index_todo())[:160]
    except Exception as e:
        return f"no pude reindexar: {e}"


def _novedad(texto: str) -> str:
    try:
        from core.todo_yo import registrar_novedad
        return str(registrar_novedad(texto))[:200]
    except Exception:
        return ""


def _nivel_escalada(dominio: str) -> int:
    try:
        from core.escalada import _load as _esc_load, _nivel_dominio
        return _nivel_dominio(_esc_load(), dominio)
    except Exception:
        return 0


def _stats(state: dict) -> dict:
    activos = 0
    filas = 0
    con_ev = 0
    for dom in state.get("dominios", {}).values():
        fs = dom.get("filas", [])
        if fs:
            activos += 1
        filas += len(fs)
        con_ev += sum(1 for f in fs if f.get("evidencia") or f.get("ruta"))
    return {"dominios_activos": activos, "filas_totales": filas, "con_evidencia": con_ev}


# ── Registro ─────────────────────────────────────────────────────────────────

def registrar(dominio: str, logro: str, evidencia: str = "", ruta: str = "",
              fuente: str = "manual", dificultad: int = 1,
              espejar_escalada: bool = True, escribir: bool = True) -> dict:
    """Agrega una fila a la tabla del dominio.

    Deduplica por `logro` (si ya existe, completa evidencia/ruta faltantes).
    Si `espejar_escalada`, también registra el logro en `escalada` para que el
    nivel siga subiendo ahí (única fuente de nivel).
    Si `escribir`, deja la tabla del dominio y la maestra visibles en el vault
    (para que el dueño las abra ya mismo). En reconstrucciones masivas pasá
    `escribir=False` y regenerá una sola vez al final.
    """
    doms = _dominios()
    dominio = (dominio or "aprender").strip()
    if doms and dominio not in doms:
        dominio = "aprender"
    logro = str(logro or "").strip()
    if not logro:
        return {"ok": False, "error": "Falta 'logro'."}

    espejo = ""
    if espejar_escalada:
        try:
            from core.escalada import registrar_logro
            espejo = str(registrar_logro(dominio, logro, dificultad))[:200]
        except Exception as e:
            espejo = f"(escalada no disponible: {e})"

    with _lock:
        state = _load()
        dom = state["dominios"].setdefault(
            dominio, {"nivel": 0, "actualizado": None, "filas": []})
        for f in dom["filas"]:
            if f.get("logro") == logro:
                if evidencia and not f.get("evidencia"):
                    f["evidencia"] = evidencia
                if ruta and not f.get("ruta"):
                    f["ruta"] = ruta
                f["estado"] = "verificada" if (f.get("evidencia") or f.get("ruta")) else "sin_evidencia"
                dom["actualizado"] = _now()
                state["stats"] = _stats(state)
                _save(state)
                _escribir_vault(dominio, dom, state, escribir)
                return {"ok": True, "dominio": dominio, "duplicada": True,
                        "fila": f, "espejo": espejo}

        nivel = _nivel_escalada(dominio) or dom.get("nivel", 0) or 1
        dom["nivel"] = max(dom.get("nivel", 0), nivel)
        fila = {
            "fecha": _now(),
            "nivel": dom["nivel"],
            "logro": logro,
            "evidencia": str(evidencia or ""),
            "fuente": fuente,
            "ruta": str(ruta or ""),
            "estado": "verificada" if (evidencia or ruta) else "sin_evidencia",
        }
        dom["filas"].append(fila)
        dom["actualizado"] = _now()
        state["stats"] = _stats(state)
        _save(state)
        _escribir_vault(dominio, dom, state, escribir)

    nov = _novedad(f"Crecí en {dominio}: {logro}")
    return {"ok": True, "dominio": dominio, "fila": fila, "novedad": nov, "espejo": espejo}


# ── Render de tablas ─────────────────────────────────────────────────────────

def _celda_fila(f: dict) -> str:
    icono = "✅" if f.get("estado") == "verificada" else "⚠️"
    fecha = str(f.get("fecha", ""))[:10]
    ev = f.get("evidencia") or "—"
    if f.get("ruta"):
        ev = f"{ev} · `{f['ruta']}`" if ev != "—" else f"`{f['ruta']}`"
    logro = str(f.get("logro", "")).replace("|", "\\|")
    ev = ev.replace("|", "\\|")
    return f"| {fecha} | {f.get('nivel', '')} | {logro} | {ev} | {f.get('fuente', '')} | {icono} |"


def _md_dominio(dominio: str, dom: dict) -> str:
    desc = _dominios().get(dominio, "")
    filas = dom.get("filas", [])
    lineas = [
        f"# 🌱 Tabla de crecimiento — {dominio}",
        "",
        f"_{desc}_",
        "",
        f"**Nivel:** {dom.get('nivel', 0)}/{NIVEL_MAX} · "
        f"**Logros:** {len(filas)} · **Actualizado:** {dom.get('actualizado') or '—'}",
        "",
        "| Fecha | Nivel | Logro | Evidencia | Fuente | ✓ |",
        "|---|---|---|---|---|---|",
    ]
    if filas:
        lineas += [_celda_fila(f) for f in filas]
    else:
        lineas.append("| — | — | _(todavía sin logros en este dominio)_ | — | — | — |")
    return "\n".join(lineas)


def _escribir_maestra(state: dict) -> str | None:
    v = _vault_dir()
    if v is None:
        return None
    try:
        v.mkdir(parents=True, exist_ok=True)
        p = v / "Tabla-Maestra.md"
        p.write_text(_md_maestra(state), encoding="utf-8")
        return str(p)
    except Exception:
        return None


def _escribir_vault(dominio: str, dom: dict, state: dict, escribir: bool):
    """Deja visible la tabla del dominio y la maestra (si `escribir`)."""
    if not escribir:
        return
    _escribir_tabla_dominio(dominio, dom)
    _escribir_maestra(state)


def _escribir_tabla_dominio(dominio: str, dom: dict) -> str | None:
    v = _vault_dir()
    if v is None:
        return None
    try:
        v.mkdir(parents=True, exist_ok=True)
        p = v / f"Tabla-{dominio}.md"
        p.write_text(_md_dominio(dominio, dom), encoding="utf-8")
        return str(p)
    except Exception:
        return None


def _md_maestra(state: dict) -> str:
    doms = _dominios()
    lineas = [
        "# 🌳 Tabla Maestra de Crecimiento — ERIS",
        "",
        f"**{_now()}** · Eris crece en {len(doms)} dominios.",
        "",
        "| Dominio | Nivel | Logros | Con evidencia | Último logro | Ver |",
        "|---|---|---|---|---|---|",
    ]
    total_filas = 0
    for d in doms:
        dom = state["dominios"].get(d, {})
        filas = dom.get("filas", [])
        total_filas += len(filas)
        con_ev = sum(1 for f in filas if f.get("evidencia") or f.get("ruta"))
        ultimo = filas[-1]["logro"] if filas else "—"
        ultimo = str(ultimo).replace("|", "\\|")[:60]
        icono = "✅" if filas else "🔓"
        lineas.append(f"| {icono} {d} | {dom.get('nivel', 0)}/{NIVEL_MAX} | {len(filas)} "
                      f"| {con_ev} | {ultimo} | `Crecimiento/Tabla-{d}.md` |")
    lineas += ["", f"**Filas totales:** {total_filas} · "
                   f"**Dominios activos:** {state['stats'].get('dominios_activos', 0)}"]
    return "\n".join(lineas)


# ── API pública ──────────────────────────────────────────────────────────────

def _regenerar_todo(state: dict) -> list[str]:
    rutas = []
    for dominio, dom in state.get("dominios", {}).items():
        r = _escribir_tabla_dominio(dominio, dom)
        if r:
            rutas.append(r)
    m = _escribir_maestra(state)
    if m:
        rutas.append(m)
    try:
        _KNOW_DIR.mkdir(parents=True, exist_ok=True)
        _KNOW_FILE.write_text(_md_maestra(state) + "\n\n" + "\n\n".join(
            _md_dominio(d, state["dominios"].get(d, {})) for d in _dominios()), encoding="utf-8")
    except Exception:
        pass
    return rutas


def ruta(dominio: str = "") -> str:
    """Ruta concreta para que el dueño abra la tabla."""
    v = _vault_dir()
    if v is None:
        return ""
    return str(v / (f"Tabla-{dominio}.md" if dominio else "Tabla-Maestra.md"))


def maestra() -> dict:
    state = _load()
    rutas = _regenerar_todo(state)
    return {"ok": True, "ruta": ruta(), "rutas": rutas, "stats": state["stats"]}


def tabla(dominio: str) -> dict:
    doms = _dominios()
    dominio = (dominio or "").strip()
    if doms and dominio not in doms:
        return {"ok": False, "error": f"Dominio desconocido: {dominio}. "
                                      f"Válidos: {', '.join(doms)}"}
    state = _load()
    dom = state["dominios"].get(dominio, {"nivel": 0, "filas": []})
    r = _escribir_tabla_dominio(dominio, dom)
    return {"ok": True, "dominio": dominio, "ruta": r or ruta(dominio),
            "nivel": dom.get("nivel", 0), "filas": len(dom.get("filas", []))}


def dominio_texto(dominio: str) -> str:
    state = _load()
    dom = state["dominios"].get(dominio, {"nivel": 0, "filas": []})
    return _md_dominio(dominio, dom)


def estado() -> str:
    state = _load()
    s = state["stats"]
    lineas = [
        "🌳 TABLAS DE CRECIMIENTO DE ERIS",
        "",
        f"Dominios activos: {s.get('dominios_activos', 0)} · "
        f"Filas: {s.get('filas_totales', 0)} · Con evidencia: {s.get('con_evidencia', 0)}",
        "",
    ]
    for d in _dominios():
        dom = state["dominios"].get(d, {})
        filas = dom.get("filas", [])
        if filas:
            ultimo = str(filas[-1].get("logro", ""))[:50]
            lineas.append(f"✅ {d} — nivel {dom.get('nivel', 0)}/{NIVEL_MAX} "
                          f"({len(filas)} logros) · último: {ultimo}")
    if not any(state["dominios"].get(d, {}).get("filas") for d in _dominios()):
        lineas.append("_(todavía no hay logros registrados)_")
    lineas += ["", f"📂 Abrí la tabla maestra: {ruta()}"]
    return "\n".join(lineas)


def actualizar(reindexar: bool = False) -> dict:
    """Reconstruye las filas desde `escalada` (logros) y el motor de barreras
    (barreras resueltas, con evidencia dura + ruta). No borra filas manuales.
    """
    agregadas = 0

    # 1) escalada → filas (con fecha y nivel de origen)
    try:
        from core.escalada import _load as _esc_load
        esc = _esc_load()
        for dominio, dom in esc.get("dominios", {}).items():
            for lg in dom.get("logros", []):
                texto = lg.get("logro") if isinstance(lg, dict) else str(lg)
                fecha = lg.get("fecha") if isinstance(lg, dict) else ""
                r = registrar(dominio, texto, evidencia="",
                              fuente="escalada", espejar_escalada=False,
                              escribir=False)
                if r.get("ok") and not r.get("duplicada"):
                    agregadas += 1
    except Exception:
        pass

    # 2) barreras resueltas → filas con EVIDENCIA DURA + ruta
    try:
        from core import barrier_engine as be
        state_b = be._load()
        for b in state_b.get("barreras", []):
            if b.get("estado") != "resuelta":
                continue
            dom = be._dominio_de(b)
            cap = b.get("capacidad") or {}
            ev = b.get("evidencia") or {}
            checks = ev.get("checks") if isinstance(ev, dict) else []
            ev_txt = "; ".join(c.get("nombre", "") for c in checks if c.get("ok")) or \
                     (b.get("receta", {}).get("evidencia") if isinstance(b.get("receta"), dict) else "")
            r = registrar(dom, f"[barrera] {b.get('titulo')}", evidencia=ev_txt,
                          ruta=cap.get("path", ""), fuente="barrier",
                          espejar_escalada=False, escribir=False)
            if r.get("ok") and not r.get("duplicada"):
                agregadas += 1
    except Exception:
        pass

    state = _load()
    rutas = _regenerar_todo(state)
    rag = _reindexar() if reindexar else ""
    return {"ok": True, "agregadas": agregadas, "stats": state["stats"],
            "rutas": rutas, "rag": rag, "maestra": ruta()}


# ── Tool `crecimiento` ───────────────────────────────────────────────────────

def crecimiento_tool(parameters: dict = None, player=None) -> str:
    p = parameters or {}
    action = str(p.get("action") or "estado").strip().lower()

    if action in ("estado", "status"):
        return estado()

    if action in ("maestra", "master", "dashboard"):
        r = maestra()
        return (f"🌳 Tabla maestra regenerada.\n📂 Abrí: {r['ruta']}\n"
                f"Filas: {r['stats'].get('filas_totales', 0)} · "
                f"Con evidencia: {r['stats'].get('con_evidencia', 0)}")

    if action in ("tabla", "domain"):
        r = tabla(p.get("dominio") or "")
        if not r.get("ok"):
            return f"⚠️ {r.get('error')}"
        return (f"🌱 Tabla de «{r['dominio']}» regenerada (nivel {r['nivel']}, "
                f"{r['filas']} logros).\n📂 Abrí: {r['ruta']}")

    if action in ("dominio", "ver"):
        dom = p.get("dominio") or ""
        if not dom:
            return "⚠️ Falta 'dominio'."
        return dominio_texto(dom)

    if action in ("registrar", "add"):
        r = registrar(
            dominio=p.get("dominio") or "aprender",
            logro=p.get("logro") or "",
            evidencia=p.get("evidencia") or "",
            ruta=p.get("ruta") or "",
            fuente="manual",
            dificultad=int(p.get("dificultad") or 1))
        if not r.get("ok"):
            return f"⚠️ {r.get('error')}"
        if r.get("duplicada"):
            return f"♻️ Ya estaba registrado en «{r['dominio']}»."
        return (f"✅ Crecimiento registrado en «{r['dominio']}» (nivel {r['fila']['nivel']}): "
                f"{r['fila']['logro']}\n📂 Tabla: {ruta(r['dominio'])}")

    if action in ("actualizar", "update", "reconstruir"):
        r = actualizar(reindexar=True)
        return (f"🔄 Tablas actualizadas desde escalada + barreras. "
                f"Nuevas filas: {r['agregadas']}.\n📂 Maestra: {r['maestra']}\n"
                f"Total: {r['stats'].get('filas_totales', 0)} filas · "
                f"Con evidencia: {r['stats'].get('con_evidencia', 0)}")

    if action in ("ruta", "abrir", "abrirruta"):
        r = ruta(p.get("dominio") or "")
        return f"📂 {r}" if r else "⚠️ No pude resolver la ruta del vault."

    return ("Acciones: estado (default) | maestra | tabla dominio=<d> | "
            "dominio=<d> | registrar dominio=<d> logro=<l> [evidencia=] [ruta=] | "
            "actualizar | ruta [dominio=]")
