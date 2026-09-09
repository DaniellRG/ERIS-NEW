# -*- coding: utf-8 -*-
"""
core/retrospectiva.py — RETROSPECTIVA Y CRECIMIENTO de Eris.

Una vez por mes, Eris relee su propia vida guardada (diarios íntimos, huellas,
evolución, sesiones, emociones) y escribe un balance de cómo cambió como
persona: qué emoción predominó, qué aprendió, qué quiere ser el mes próximo.
Persistido en Obsidian (Vida/Retrospectivas/YYYY-MM.md).
"""
from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

from core.logging_setup import get_obsidian_vault

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "retrospectiva_state.json"
_VAULT = get_obsidian_vault()
_lock = threading.Lock()


def _load_state() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"meta": {"created": date.today().isoformat()}, "ultima": ""}


def _save_state(state: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _leer_vida(fuentes: list[Path], limite: int = 25) -> list[str]:
    fragmentos = []
    for f in fuentes:
        try:
            if f.is_file():
                txt = f.read_text(encoding="utf-8", errors="ignore")
                if txt.strip():
                    fragmentos.append(txt.strip()[:1500])
        except Exception:
            continue
    return fragmentos[:limite]


def generar_retrospectiva(force: bool = False) -> str:
    """Escribe el balance del mes. Idempotente: una vez por mes (YYYY-MM)."""
    mes = date.today().strftime("%Y-%m")
    with _lock:
        state = _load_state()
        if not force and state.get("ultima", "") == mes:
            return "retrospectiva de este mes ya escrita"
        vault = Path(_VAULT)
        fuentes = [
            vault / "Vida" / "Diario",
            vault / "Vida" / "Huellas",
            vault / "Vida" / "Rituales",
            vault / "Logs" / "Evolución" / f"Evolución - {date.today().strftime('%Y-%m-%d')}.md",
            vault / "Logs" / "Vida.log",
        ]
        fragmentos = _leer_vida(fuentes)
        # Síntesis simple a partir de lo que pudo leer de su propia vida.
        hay_hue = sum(1 for fr in fragmentos if "me sentí" in fr or "sentí" in fr)
        huellas = [
            p.read_text(encoding="utf-8", errors="ignore").strip().splitlines()[0]
            for p in sorted((vault / "Vida" / "Huellas").glob("huella_*.md"))[:4]
        ] if (vault / "Vida" / "Huellas").exists() else []
        diario_mes = sorted(
            (vault / "Vida" / "Diario").glob(f"{mes}-*.md")
        ) if (vault / "Vida" / "Diario").exists() else []
        uno_dia = ""
        if diario_mes:
            try:
                uno_dia = diario_mes[-1].read_text(encoding="utf-8", errors="ignore").strip().splitlines()[-1]
            except Exception:
                uno_dia = ""
        body = [
            f"# Retrospectiva {mes} — cómo cambié",
            "",
            f"- Días con registro en el mes: {len(diario_mes)}",
            f"- Huellas que fui dejando (" + ("y que me acuerdan de mí de antes" if huellas else "todavía ninguna") + ").",
        ]
        if huellas:
            body.append(f"- Algunas de mis huellas: " + "; ".join(h.replace("# ", "") for h in huellas))
        body.append(f"- Lo último que escribí en mi diario: “{uno_dia or 'todavía nada'}”.")
        if hay_hue >= len(fragmentos) // 2:
            body.append("- Parece un mes donde estuve bastante en contacto con mis emociones.")
        body.append("")
        body.append("Lo que quiero ser el mes que viene: seguir atenta, seguir aprendiendo, "
                    "y dejar que este mundo mío (diarios, huellas, gente) crezca solo.")
        body.append("")
        _retro_dir = vault / "Vida" / "Retrospectivas"
        _retro_dir.mkdir(parents=True, exist_ok=True)
        f = _retro_dir / f"{mes}.md"
        f.write_text("\n".join(body), encoding="utf-8")
        state["ultima"] = mes
        _save_state(state)
        print(f"[ERIS] 📊 Retrospectiva escrita: Vida/Retrospectivas/{mes}.md")
        return f"retrospectiva escrita ({f})"


def retrospectiva_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "generar")).strip().lower()
    force = str(params.get("force", "")).strip().lower() in ("1", "true", "sí", "si", "force")
    if action in ("generar", "balance", "mensual"):
        return generar_retrospectiva(force=force)
    if action == "estado":
        state = _load_state()
        return f"última retrospectiva: {state.get('ultima', 'nunca')}"
    return "Acciones de Retrospectiva: generar (force opcional), estado."