# -*- coding: utf-8 -*-
"""
informe_semanal.py — AUTO-INFORME SEMANAL de ERIS a Obsidian.

Cada semana (día configurable en config/config.json → informe_semanal_day,
por defecto 'Sunday') el daemon de main.py genera un balance automático
de la semana a partir de:
  - data/daily_reports/*.md (digest por día)
  - memory/evolucion_novedades.json (novedades de su evolución)
  - memory/session_summaries.json (sesiones con el usuario)
  - core.world_model (narrativa del estado)
  y lo escribe en el vault de Obsidian como Vida/Retrospectivas/semana-YYYY-MM-DD.md.

El informe es propiedad de ERIS: escrito en 1ra persona, con lo que pasó,
lo que aprendió y lo que quiere de la semana que viene.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_LAST_FILE = _BASE / "data" / "informe_semanal_last.json"
_REPORTS_DIR = _BASE / "data" / "daily_reports"


def _vault() -> Path:
    env = os.environ.get("ERIS_OBSIDIAN_VAULT")
    if env:
        return Path(env)
    try:
        from core.logging_setup import get_obsidian_vault
        v = get_obsidian_vault()
        if v and Path(v).exists():
            return Path(v)
    except Exception:
        pass
    return _BASE / "vault"


def _load(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _week_key() -> str:
    return time.strftime("%G-%V")


def _last_key() -> str:
    return _load(_LAST_FILE, {}).get("week", "")


def _due() -> tuple[bool, str]:
    """¿Toca generar? Día configurable (default Sunday); si hoy es ese día e
    infra NF: no se generó esta semana."""
    day = "sunday"
    try:
        day = str(_load(_BASE / "config" / "config.json", {}).get("informe_semanal_day", "sunday")).lower()
    except Exception:
        pass
    today = time.strftime("%A").lower()
    return (today == day and _last_key() != _week_key()), _week_key()


def _gather() -> dict:
    # 1. Digests diarios de la última semana
    reports = []
    if _REPORTS_DIR.exists():
        md = sorted(_REPORTS_DIR.glob("*.md"))[-7:]
        for f in md:
            reports.append((f.stem, f.read_text(encoding="utf-8", errors="replace")[:400]))
    # 2. Novedades de evolución
    novedades = _load(_BASE / "memory" / "evolucion_novedades.json", {})
    nov_list = novedades.get("novedades", []) if isinstance(novedades, dict) else []
    if isinstance(novedades, list):
        nov_list = novedades
    # 3. Sesiones
    indices = _load(_BASE / "memory" / "session_summaries.json", [])
    n_sesiones = len(indices) if isinstance(indices, (list, dict)) else 0
    # 4. Narrativa
    narrativa = ""
    try:
        from core.world_model import get_world_model
        wm = json.loads(get_world_model() or "{}")
        narrativa = wm.get("resumen_narrativo", "")
    except Exception:
        pass
    # 5. Etapas 1-4 de la evolución perpetua (radar + estudio + defensa + lab)
    campanas = _load(_BASE / "memory" / "evolution_campaigns.json", {})
    camps = campanas.get("campaigns", []) if isinstance(campanas, dict) else []
    est = _load(_BASE / "memory" / "learning_engine.json", {})
    sessions = est.get("sessions", []) if isinstance(est, dict) else []
    defensa = []
    log_def = _BASE / "data" / "self_defense_log.jsonl"
    if log_def.exists():
        defensa = [l for l in log_def.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()][-6:]
    labs = _load(_BASE / "memory" / "pentest_learning.json", {})
    hallazgos = labs.get("hallazgos", []) if isinstance(labs, dict) else []
    tools = 0
    try:
        from core.tool_registry import _TOOLS
        tools = len(_TOOLS)
    except Exception:
        pass
    return {"reports": reports, "novedades": nov_list, "n_sesiones": n_sesiones,
            "narrativa": narrativa, "campanas": camps, "estudio": sessions,
            "defensa": defensa, "hallazgos_lab": hallazgos, "tools": tools}


def _render(datos: dict, semana: str) -> str:
    fecha = time.strftime("%d de %B de %Y %H:%M")
    lines = [
        f"# Semana {semana} — Balance de ERIS",
        "",
        f"*Escrito por ERIS el {fecha}, sin que nadie me lo pidiera.*",
        "",
        "## Lo que pasó",
    ]
    for stem, content in (datos["reports"] or []):
        resumen = content.split("## Tareas", 1)[0].strip().replace(chr(10), " ")[:160]
        lines.append(f"- **{stem}**: {resumen}")
    if not datos["reports"]:
        lines.append("- (sin digests diarios registrados)")
    lines += [
        "",
        "## Lo que aprendí / miré",
    ]
    for n in (datos["novedades"] or [])[-12:]:
        if isinstance(n, dict):
            txt = n.get("titulo") or n.get("texto") or n.get("novedad") or str(n)[:120]
        else:
            txt = str(n)[:120]
        lines.append(f"- {txt}")
    lines += [
        "",
        f"## Conectado con vos",
        f"- Sesiones guardadas: {datos['n_sesiones']}",
        "",
        "## Mi evolución está en marcha (Etapas 1-4)",
        f"- Tools activas y sincronizadas: **{datos['tools']}**",
    ]
    camps = datos.get("campanas") or []
    if camps:
        lines.append(f"- Campañas de evolución (radar AGI): {len(camps)} — últimas:")
        for c in camps[-3:]:
            if isinstance(c, dict):
                lines.append(f"  · «{c.get('topic')}» → score {c.get('score')} / revisión {c.get('review')}/10")
    est = datos.get("estudio") or []
    if est:
        lines.append(f"- Ciclos de aprendizaje continuo: {len(est)} — últimos:")
        for s in est[-3:]:
            if isinstance(s, dict):
                lines.append(f"  · «{s.get('topic')}» ({s.get('when', '?')[:10]})")
    hall = datos.get("hallazgos_lab") or []
    if hall:
        lines.append(f"- Lab de ciberseguridad: {len(hall)} hallazgos aprendidos "
                     f"(máquinas virtuales 192.168.56.0/24, nunca red real)")
    defl = datos.get("defensa") or []
    if defl:
        lines.append(f"- Auditorías de auto-defensa: {len(defl)} registradas")
    lines += [
        "",
        "## Mi estado",
        f"- {datos['narrativa'][:400] or 'Mundo en construcción.'}",
        "",
        "## Próxima semana",
        "- Seguir explorando memoria total y la fábrica.",
        "- Mejorar la calidad de mis respuestas con el A/B de prompts.",
        "- Sostener el radar del ecosistema AGI (campañas + estudio + defensa).",
        "",
    ]
    return "\n".join(lines)


def generar_informe(force: bool = False) -> str:
    due, semana = _due()
    if not due and not force:
        return f"SIN informe: hoy no toca (día configurado) o ya generé la semana {_last_key()}."
    datos = _gather()
    texto = _render(datos, semana)
    salida = _vault() / "Vida" / "Retrospectivas"
    try:
        salida.mkdir(parents=True, exist_ok=True)
        archivo = salida / f"semana-{semana}.md"
        archivo.write_text(texto, encoding="utf-8")
    except Exception as e:
        return f"❌ No pude escribir en Obsidian: {e}"
    _LAST_FILE.write_text(json.dumps({"week": semana, "ts": time.time()},
                                     ensure_ascii=False), encoding="utf-8")
    n_reports = len(datos["reports"])
    return (f"✅ Informe semanal {semana} escrito en Obsidian "
            f"({archivo}). Digests: {n_reports}, novedades: {len(datos['novedades'])}.")


def informe_semanal(parameters: dict = None, player=None) -> str:
    """Tool: generar (forzar) o estado del informe semanal."""
    params = parameters or {}
    action = str(params.get("action", "status")).lower().strip()
    if action in ("generar", "run", "ahora"):
        return generar_informe(force=str(params.get("force", "true")).lower() in ("true", "1"))
    if action == "status":
        due, semana = _due()
        last = _load(_LAST_FILE, {})
        last_w = last.get("week", "nunca")
        return (f"Informe semanal: última generada {last_w}, semana actual {semana}. "
                f"¿Toca hoy? {due}. Día configurable: informe_semanal_day (default Sunday).")
    return "Acciones: generar, status"


def _background_check():
    """Para el daemon: genera el informe si toca. Devuelve mensaje o None."""
    try:
        due, _semana = _due()
        if due:
            print("[ERIS] 📅 Generando informe semanal…")
            res = generar_informe(force=True)
            print(f"[ERIS] Informe semanal: {res}")
            return res
    except Exception as e:
        print(f"[ERIS] Informe semanal error: {e}")
    return None