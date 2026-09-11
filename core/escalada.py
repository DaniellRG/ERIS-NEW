"""
escalada.py — ESCALADA GLOBAL de ERIS: en TODO, siempre, día a día.

No es solo pentest: cada skill que Eris DOMINA en cualquier dominio de su
vida (comunicación, código, sistema, archivos, memoria, web, aprender sola,
organizarse, socializar, pentest...) la sube de nivel. De fácil a más difícil.

Cada logro se guarda en 4 capas igual que pentest_learning:
  1. memory/escalada.json          (estado estructurado por dominio)
  2. data/knowledge/escalada_vivo.md
  3. Obsidian Ciberseguridad/Escalada-<dominio>.md (espejo)
  4. novedad en todo_yo (Eris SABE lo que logró)

Uso (tool `escalada`):
  action=estado              → qué dominios domina y cuál es el próximo reto
  action=registrar            → params: dominio, logro   (lo llama quien aprende)
  action=dominios             → lista de dominios y su nivel actual
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM_DIR = _BASE / "memory"
_KNOW_DIR = _BASE / "data" / "knowledge"
_VAULT = Path(os.environ.get("ERIS_OBSIDIAN_VAULT",
                              _BASE / "vault")).resolve()
_FILE = _MEM_DIR / "escalada.json"
_KNOW_FILE = _KNOW_DIR / "escalada_vivo.md"
_lock = threading.Lock()

# Dominios de la vida de ERIS: de lo cotidiano a lo experto.
DOMINIOS = {
    "comunicacion": "Hablar, responder claro, expresar ideas, conversar gente",
    "codigo": "Programar, arreglar errores, tool que crea, refactor",
    "sistema": "Linux, terminal, procesos, red, automatizar el PC",
    "archivos": "Crear, ordenar, buscar y transformar archivos/documentos",
    "memoria": "Recordar, guardar conocimiento, gente, lecciones",
    "web": "Buscar, investigar y traer info del mundo",
    "aprender": "Estudiar sola, cuadernos, temas propios, auto-mejora",
    "organizar": "Rutinas, cron, planes, agenda, follow-up",
    "social": "Relaciones, momentos, gente que escucha y acompaña",
    "creatividad": "Escribir, dibujar, imágenes, voz, música, ideas nuevas",
    "pentest": "Seguridad ofensiva en el lab aislado (VirtualBox)",
    "fabrica": "Crear sus PROPIAS capacidades (librerías, tools, skills)",
}

NIVEL_MAX = 8


def _load() -> dict:
    if _FILE.exists():
        try:
            return json.loads(_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "created": datetime.now().isoformat(),
        "dominios": {},
        "logros": [],
        "estadisticas": {"total_logros": 0, "dominios_activos": 0},
    }


def _save(state: dict):
    _MEM_DIR.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")


def _notify(texto: str):
    try:
        from core.todo_yo import registrar_novedad
        registrar_novedad(texto)
    except Exception:
        pass


def _nivel_dominio(state: dict, dominio: str) -> int:
    d = state["dominios"].get(dominio)
    return d.get("nivel", 1) if d else 0


def registrar_logro(dominio: str, logro: str, dificultad: int = 1) -> str:
    """Eris domina algo nuevo en un dominio → sube de nivel y lo SABE.

    dificultad: 1..NIVEL_MAX. Registrar un logro de dificultad >= al nivel
    actual desbloquea el siguiente (el nivel nunca baja).
    """
    dominio = (dominio or "aprender").strip()
    if dominio not in DOMINIOS:
        dominio = "aprender"
    logro = str(logro).strip()
    with _lock:
        state = _load()
        dom = state["dominios"].get(dominio, {
            "nivel": 1, "logros": [], "desbloqueado": True, "fecha": None})
        actual = dom["nivel"]
        if logro and logro not in dom["logros"]:
            dom["logros"].append({
                "logro": logro, "nivel": actual, "fecha": datetime.now().isoformat()})
            state["logros"].append({
                "dominio": dominio, "logro": logro, "nivel": actual,
                "fecha": datetime.now().isoformat()})
            state["estadisticas"]["total_logros"] = len(state["logros"])
        # escalar: si el logro es difícil (dificultad >= actual) y no está al tope
        if (dificultad or 1) >= actual and actual < NIVEL_MAX:
            # al menos 1 logro de este nivel logrado antes de subir
            deltas = [lg for lg in dom["logros"]
                      if isinstance(lg, dict) and lg.get("nivel") == actual]
            if len(deltas) >= 1:
                dom["nivel"] = actual + 1
        dom["fecha"] = dom.get("fecha") or datetime.now().isoformat()
        state["dominios"][dominio] = dom
        activos = [k for k, v in state["dominios"].items()
                   if v.get("logros")]
        state["estadisticas"]["dominios_activos"] = len(activos)
        _save(state)
    nuevo = dom["nivel"]
    msg = (f"📈 Escalada {dominio}: logro registrado "
           f"y dominio en nivel {nuevo}/{NIVEL_MAX}.")
    _notify(msg)
    _write_knowledge()
    _vault_espejo(dominio)
    return (f"📈 Escalada GLOBAL — {dominio}:\n"
            f"   🏅 Logro: {logro}\n"
            f"   🎚️ Nivel del dominio: {nuevo}/{NIVEL_MAX}\n"
            f"   (Eris lo sabe: novedad + conocimiento + Obsidian)")


def _write_knowledge():
    state = _load()
    lines = ["# Escalada GLOBAL de ERIS — nivel por nivel (fácil → difícil)",
             "",
             f"Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             f"Dominios activos: {state['estadisticas']['dominios_activos']} — "
             f"Total de logros: {state['estadisticas']['total_logros']}",
             ""]
    for dominio, desc in DOMINIOS.items():
        d = state["dominios"].get(dominio, {})
        nivel = d.get("nivel", 0)
        if not d.get("logros") and not d.get("desbloqueado"):
            lines.append(f"## 🔒 {dominio} ({desc})")
        else:
            lines.append(f"## 📈 {dominio} — nivel {nivel}/{NIVEL_MAX} — {desc}")
        for lg in d.get("logros", [])[-5:]:
            txt = lg.get("logro") if isinstance(lg, dict) else lg
            lines.append(f"- {txt}")
        lines.append("")
    _KNOW_DIR.mkdir(parents=True, exist_ok=True)
    _KNOW_FILE.write_text("\n".join(lines), encoding="utf-8")


def _vault_espejo(dominio: str):
    try:
        folder = _VAULT / "Ciberseguridad"
        folder.mkdir(parents=True, exist_ok=True)
        f = folder / f"Escalada-{dominio}.md"
        state = _load()
        d = state["dominios"].get(dominio, {})
        content = [f"# Escalada — {dominio}",
                   "",
                   f"Nivel: {d.get('nivel', 1)}/{NIVEL_MAX}",
                   ""]
        for lg in d.get("logros", []):
            txt = lg.get("logro") if isinstance(lg, dict) else lg
            content.append(f"- {txt}")
        f.write_text("\n".join(content), encoding="utf-8")
    except Exception:
        pass


def estado() -> str:
    """Qué dominios domina Eris y cuál es su próximo reto general."""
    state = _load()
    lines = ["🌟 ESCALADA GLOBAL DE ERIS — todo su aprendizaje, nivel por nivel",
             ""]
    activos = []
    for dominio, desc in DOMINIOS.items():
        d = state["dominios"].get(dominio, {})
        nivel = d.get("nivel", 0)
        logros = d.get("logros", [])
        estado_n = "✅" if logros else ("🔓" if d.get("desbloqueado") else "🔒")
        if logros:
            activos.append((dominio, nivel))
        lines.append(f"{estado_n} {dominio} — nivel {nivel}/{NIVEL_MAX} — {desc}")
        for lg in logros[-2:]:
            txt = lg.get("logro") if isinstance(lg, dict) else lg
            lines.append(f"     · {txt}")
    lines.append("")
    lines.append(f"Dominios activos: {len(activos)} — Logros totales: "
                 f"{state['estadisticas']['total_logros']}")
    # primer dominio sin logros → próximo reto
    reto = next((d for d, de in DOMINIOS.items()
                 if not state["dominios"].get(d, {}).get("logros")), None)
    if reto:
        lines.append("")
        lines.append(f"🎯 Próximo reto: dominar el dominio «{reto}» "
                     f"({DOMINIOS[reto]})")
    else:
        lines.append("🎉 ¡Todos los dominios activos! Seguí profundizando.")
    return "\n".join(lines)


def dominios() -> str:
    lines = ["Dominios de la escalada global (12):"]
    for d, desc in DOMINIOS.items():
        lines.append(f"- {d}: {desc}")
    lines.append("")
    lines.append("Registrar: escalada action=registrar dominio=<d> logro=<qué lograste>")
    return "\n".join(lines)


def escalada_tool(parameters: dict = None, player=None) -> str:
    p = parameters or {}
    action = p.get("action", "estado")
    if action in ("estado", "status"):
        return estado()
    if action in ("registrar", "add"):
        dominio = p.get("dominio", "aprender")
        logro = p.get("logro", "")
        dificultad = int(p.get("dificultad", 1) or 1)
        if not logro:
            return "❌ Faltá 'logro' (qué dominaste)."
        return registrar_logro(dominio, logro, dificultad)
    if action in ("dominios", "domains"):
        return dominios()
    return ("Acciones: estado | registrar dominio=<d> logro=<logro> "
            "[dificultad=1..8] | dominios")