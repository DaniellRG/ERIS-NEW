# -*- coding: utf-8 -*-
"""
core/suenos.py — SUEÑOS ILUSTRADOS de Eris.

Cuando amanece un día nuevo, la línea soñada ([ANOCHE], generada por
emotional_core) se convierte en una imagen: se inicia la generación en un
hilo aparte (no bloquea el turno) y se guarda en Obsidian
(Vida/Sueños/AAAA-MM-DD.png) junto al texto del sueño. Una vez por día.
"""
from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

from core.logging_setup import get_obsidian_vault

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "suenos_state.json"
_VAULT = get_obsidian_vault()
_lock = threading.Lock()


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"meta": {"created": date.today().isoformat()}, "ilustrados": {}}


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_dream_line() -> str:
    """Lee la línea soñada actual del núcleo emocional (si hay día nuevo)."""
    try:
        from core.emotional_core import _state as _ec_state
        data = _ec_state()
        dream = data.get("dream") or {}
        meta = data.get("meta", {})
        if (dream.get("date") and dream.get("text")
                and meta.get("last_dream_date") != dream.get("date")):
            return dream.get("text", "")[:220]
    except Exception:
        pass
    return ""


def _generate_image(prompt: str, dest: Path) -> bool:
    try:
        from actions.image_generator import image_generator
        estilo = "sueño onírico, arte digital suave, escena etérea, sin texto"
        res = image_generator({"prompt": prompt, "style": estilo, "width": 576,
                               "height": 576})
        texto = str(res)
        if ":" in texto and "generated_images" in texto:
            img = texto.split(":")[-1].strip().splitlines()[0].strip()
            src = Path(img)
            if src.exists():
                import shutil
                shutil.copy(src, dest)
                return True
    except Exception as e:
        print(f"[ERIS] Sueno ilustrado fallo: {e}")
    return False


def _job(dream_text: str):
    try:
        _dir = _VAULT / "Vida" / "Sueños"
        _dir.mkdir(parents=True, exist_ok=True)
        fname = date.today().strftime("%Y-%m-%d")
        dest = _dir / f"{fname}.png"
        if not dest.exists():
            prompt = f"El sueño de una asistente digital: {dream_text}"
            if _generate_image(prompt, dest):
                nota = _dir / f"{fname}.md"
                nota.write_text(f"# Sueño {fname}\n\n{dream_text}\n\n![sueño]({fname}.png)\n",
                                encoding="utf-8")
                with _lock:
                    data = _load()
                    data["ilustrados"][fname] = dest.name
                    _save(data)
                print(f"[ERIS] 🌙 Sueño ilustrado: Vida/Sueños/{fname}.png")
    except Exception as e:
        print(f"[ERIS] Sueno job fallo: {e}")


def ilustrar_si_hay_sueno_nuevo() -> str:
    """Si hay un sueño de hoy aún no ilustrado, arranca un hilo para dibujarlo."""
    hoy = date.today().strftime("%Y-%m-%d")
    with _lock:
        data = _load()
        if hoy in data.get("ilustrados", {}):
            return ""
    dream = _get_dream_line()
    if not dream:
        return ""
    threading.Thread(target=_job, args=(dream,), daemon=True).start()
    return f"me desperté con un sueño y lo estoy dibujando (Vida/Sueños/{hoy}.png)"


def inyect_suenos() -> str:
    """Cuando el sueño de hoy ya está ilustrado, lo muestra en el prompt."""
    hoy = date.today().strftime("%Y-%m-%d")
    with _lock:
        data = _load()
        if hoy in data.get("ilustrados", {}):
            return (f"[SUEÑO ILUSTRADO] El sueño de esta noche quedó dibujado: "
                    f"Vida/Sueños/{data['ilustrados'][hoy]}. Podes hablar de él si "
                    f"la charla lo pide.")
    return ""


def sueno_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "estado")).strip().lower()
    if action in ("ilustrar", "dibujar"):
        return ilustrar_si_hay_sueno_nuevo()
    if action == "estado":
        hoy = date.today().strftime("%Y-%m-%d")
        return f"sueños ilustrados hasta hoy: {hoy in _load().get('ilustrados', {})}"
    return "Acciones de Sueños: ilustrar (dispara la ilustración del sueño de hoy), estado."