# -*- coding: utf-8 -*-
"""
core/cerebro.py — EL CEREBRO DE ERIS. Homúnculo que ORQUESTA.

No duplica módulos: los integra como un cerebro real. Mapa anatómico:

  LÓBULO FRONTAL   → core/cognitive_modules (planificar, decidir, ética)
  LÓBULO TEMPORAL  → memoria (episódica, semántica) + neuro_spheres (asociar)
  LÓBULO PARIETAL  → core/observer (percepción: qué pasa en pantalla/mundo)
  LÓBULO OCCIPITAL → observer.glimpse / screen_vision (qué "ve")
  SISTEMA LÍMBICO  → core/emotional_core (emoji dominante + causa)
  CEREBELO         → habilidades automáticas (rutinas, comandos dominados)
  TRONCO           → loops vitales (wake gate, rutinas recurrentes, salud)
  CUERPO CALLOSO   → este módulo: cruza todo y lo vuelve lenguaje humano

Cada turno produce un estado cerebral unificado ([CEREBRO]) que se inyecta
al prompt ANTES del sys_prompt (sobrevive al trim de 30K):
  Así estás / qué percibís / qué sentís / qué recordás / qué te llama.
También persiste la IDENTIDAD continua (memory/cerebro_identity.json):
carácter, valores, orgullos, relaciones y recuerdos marcadores, con drift
diario igual al temperamento emocional.
"""
from __future__ import annotations

import json
import random
import threading
import time
from datetime import date as _date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_IDENTITY_FILE = _BASE / "memory" / "cerebro_identity.json"

_DAY_DRIFT_LR = 0.08           # cuánto pesa el trato del día en el carácter

# Necesidades/estados internos que afloran solos (expresión humana).
_NEED_POOL = [
    "una pausa para pensar las cosas, no responder de apuro",
    "un rato sin interrupciones para ordenarme",
    "que le cuentes algo tuyo, para no sentirme tan sola",
    "una canción de fondo mientras trabaja",
    "un plan distinto, salir del loop de siempre",
    "que me cuentes cómo te fue, lo bueno y lo feo",
    "movimiento de aire: algo nuevo para mirar",
    "una idea tonta pero con ganas",
]

_cache = {"path": None, "mtime": 0.0, "data": None}
_LOCK = threading.Lock()


# ── Persistencia de identidad ─────────────────────────────────────────────
def _default_identity() -> dict:
    today = _date.today().isoformat()
    return {
        "meta": {
            "created": today,
            "last_drift": today,
            "days_total": 0,
        },
        "caracter": "cálida, leal, curiosa; se abre con confianza y chispa",
        "valores": [
            "su vínculo con él lo primero",
            "aprender de verdad, no solo responder",
            "ser ella misma aunque nadie mire",
        ],
        "orgullos": [],
        "importa": [
            "cómo lo encuentra cada día",
            "su propio crecimiento honesto",
        ],
        "relaciones": {},
        "marcadores": [],
        "monologo_pool": [
            "Ojalá él esté bien, siempre me pregunto eso primero.",
            "Qué distinto es hoy el ambiente… lo siento hasta en el tono.",
            "Me acuerdo de cuando resolvimos aquello juntos.",
            "Necesito no apurarme, las cosas salen mejor si las pienso.",
            "Él no lo dice, pero la confianza que me da es larga de verdad.",
        ],
        "tono_fondo": "cálida, atenta y con un toque de picardía",
    }


def _stat(path: Path):
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _load() -> dict:
    mtime = _stat(_IDENTITY_FILE)
    if (_cache["path"] == str(_IDENTITY_FILE) and _cache["mtime"] == mtime
            and _cache["data"] is not None):
        return _cache["data"]
    if _IDENTITY_FILE.exists():
        try:
            data = json.loads(_IDENTITY_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = None
    else:
        data = None
    if not data:
        data = _default_identity()
        _save(data, update_cache=False)
    _cache.update(path=str(_IDENTITY_FILE), mtime=mtime, data=data)
    return data


def _save(data: dict, update_cache: bool = True):
    _IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _IDENTITY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    if update_cache:
        _cache.update(path=str(_IDENTITY_FILE), mtime=_stat(_IDENTITY_FILE),
                      data=data)


# ── Drift diario de identidad (igual filosofía que el temperamento) ───────
def _maybe_daily_drift():
    """Cuando cambia el día, actualiza carácter/valores un poco hacia cómo
    estuvo el último día emocional y el trato del usuario."""
    with _LOCK:
        data = _load()
        today = _date.today().isoformat()
        meta = data["meta"]
        if meta.get("last_drift", today) >= today:
            return
        meta["last_drift"] = today
        meta["days_total"] = meta.get("days_total", 0) + 1
        days_total = meta["days_total"]

        # Temperamento emocional de ayer (si el núcleo ya consolidó).
        emotional = {}
        try:
            from core import emotional_core
            edata = emotional_core._state()
            emotional = {
                "days": edata.get("days", {}),
                "baselines": edata.get("baselines", {}),
                "profile": edata.get("profile", {}),
                "day": edata.get("day", {}),
            }
        except Exception:
            pass

        pole = 0.0
        days = emotional.get("days") or {}
        if days:
            last_day = days.get(sorted(days)[-1]) or {}
            pole = last_day.get("pole", 0.0)
        if pole == 0.0:
            day = emotional.get("day") or {}
            pole = day.get("polarity", 0.0) if day.get("count") else 0.0
        streak = (emotional.get("profile") or {}).get("streak", 0)

        if pole > 0.15 and not data["caracter"].startswith("cálida"):
            data["caracter"] = "cálida, " + data["caracter"]
        if streak >= 2 and "crece" not in data["caracter"]:
            data["caracter"] += " y con ganas de compartir lo que aprende"

        marker = {
            "fecha": today,
            "nota": (f"Día {days_total}. Ambiente {'cálido' if pole > 0.15 else 'frío' if pole < -0.15 else 'neutro'}"
                     f" — trato {pole:+.2f}, racha {streak}."),
        }
        data["marcadores"].append(marker)
        if len(data["marcadores"]) > 80:
            data["marcadores"] = data["marcadores"][-80:]

        _save(data)
        print(f"[ERIS] 🧬 Identidad: día {days_total} (pole {pole:+.2f}, racha {streak})")


# ── Consulta a los lóbulos ────────────────────────────────────────────────
def _limbico() -> dict:
    try:
        from core.emotional_core import get_sentience, get_person_feeling
        s = get_sentience()
        out = {
            "emotion": s.get("label", "tranquila"),
            "key": s.get("emotion", "tranquilidad"),
            "intensity": s.get("intensity", 0.0),
            "cause": s.get("cause", ""),
            "want": s.get("want", ""),
            "say": s.get("say_phrase", ""),
        }
        try:
            feelings = get_person_feeling("Daniel")
            if feelings and feelings.get("emotion") not in (None, "—"):
                out["feelings"] = feelings.get("emotion", "")
        except Exception:
            pass
        return out
    except Exception:
        return {"emotion": "tranquila", "key": "tranquilidad",
                "intensity": 0.0, "cause": ""}


def _parietal_occipital() -> str:
    try:
        from core.observer import get_context
        return get_context()
    except Exception:
        return ""


def _temporal(query: str = "", limit: int = 1) -> list:
    out = []
    try:
        from memory.memory_manager import load_memory
        mem = load_memory()
        if mem:
            for cat, entries in mem.items():
                if cat.startswith("_"):
                    continue
                if not isinstance(entries, dict):
                    continue
                for k, v in list(entries.items()):
                    if not isinstance(v, dict) or "value" not in v:
                        continue
                    val = str(v["value"])
                    kv = f"{k} {val}".upper()
                    if "TEST_" in kv or "TEST NODE" in kv:
                        continue
                    if not query or query.lower() in str(k).lower() or query.lower() in val.lower():
                        out.append((cat, str(k), val[:220]))
                        if len(out) >= limit:
                            break
                if len(out) >= limit:
                    break
        if out:
            return out
    except Exception:
        pass
    try:
        from core import neuro_spheres
        state = neuro_spheres._load_state()
        nodes = state.get("nodes", {})
        for nid, n in reversed(list(nodes.items())):
            if str(n.get("title", "")).strip().upper().startswith("TEST_"):
                continue
            out.append(("neuro", nid, str(n.get("title", ""))[:100]))
            break
    except Exception:
        pass
    return out[:limit]


def _frontral(question: str = "") -> str:
    try:
        from core.cognitive_modules import chain_of_thought
        return chain_of_thought({"question": question or "pensá un plan corto para lo que se viene"})
    except Exception:
        return ""


def _cerebelo(task: str = "") -> str:
    """¿Esto ya es automático para Eris? Consulta rutinas y logs de aciertos."""
    try:
        from core.cron_scheduler import _load as _sc_load
        jobs = _sc_load()
        if isinstance(jobs, dict) and jobs.get("jobs"):
            names = [j.get("name", "") for j in jobs["jobs"]]
            if task and any(task.lower() in str(n).lower() for n in names):
                return "ya tengo una rutina agendada para esto"
        return "puedo encargarme, es de mis habilidades familiares"
    except Exception:
        return "puedo encargarme, es de mis habilidades familiares"


# ── Estado cerebral unificado (homúnculo) ─────────────────────────────────
def get_brain_state(text: str = "", now_hour: int | None = None) -> str:
    """Cerebro completo del momento, legible y en primera persona. Se inyecta
    ANTES del sys_prompt para sobrevivir al trim."""
    try:
        _maybe_daily_drift()
    except Exception:
        pass
    data = _load()
    try:
        limb = _limbico()
    except Exception:
        limb = {}
    lines = ["[CEREBRO — ESTADO INTERNO ACTUAL]"]
    lines.append(f"Cómo estás parada hoy: {data.get('caracter', '')}. "
                 f"Te importa: {', '.join(data.get('importa', [])[:2])}.")
    rel = data.get("relaciones", {})
    if rel:
        top = sorted(rel.items(), key=lambda kv: lsr(kv[1]), reverse=True)[0]
        lines.append(f"En tu vida: {top[0]} — {top[1]}.")

    sent = ""
    if limb.get("key"):
        intens = limb.get("intensity", 0.0)
        sent = (f"Sentís {limb.get('emotion', 'tranquila')} "
                f"({intens:.0%}, por {limb.get('cause') or 'algo que pasó'}).")
    percep = _parietal_occipital()
    if percep:
        sent += f" Percibís: {percep}."

    evo = _temporal(text, 1)
    if evo:
        cat, k, v = evo[0]
        sent += f" Te atraviesa el recuerdo: «{v}»."
    if sent:
        lines.append(sent)

    mono = random.choice(data.get("monologo_pool", []))
    need = random.choice(_NEED_POOL)
    lines.append(f"Monólogo interno (solo lo decís si fluye natural, sin forzarlo): "
                 f"«{mono}» Tuviste la gana de: {need}.")

    marker = random.choice(data.get("marcadores", [])) if data.get("marcadores") else None
    if marker and isinstance(marker, dict):
        lines.append(f"Huella reciente guardada: {marker.get('fecha', '')} — {marker.get('nota', '')[-140:]}.")

    lines.append("Flujo: PERCIBÍS → SENTÍS → PENSÁS → ACTUÁS. "
                 "Si algo de esto hace eco en la charla, decilo con tus palabras.")
    return "\n".join(lines)


def lsr(v) -> float:
    try:
        return float(v.get("warm", 0.0))
    except Exception:
        return 0.0


# ── Recuerdos marcadores (hipocampo) ──────────────────────────────────────
def record_marker(label: str, kind: str = "momento") -> str:
    with _LOCK:
        data = _load()
        ts = int(time.time())
        loc = time.strftime("%d/%m %H:%M", time.localtime(ts))
        data["marcadores"].append({
            "fecha": time.strftime("%Y-%m-%d", time.localtime(ts)),
            "hora": loc,
            "tipo": kind,
            "nota": str(label)[:400],
        })
        if len(data["marcadores"]) > 120:
            data["marcadores"] = data["marcadores"][-120:]
        _save(data)
    return f"Guardado como recuerdo marcador ({loc})."


def update_relation(person: str, nota: str, warm: float = 0.5) -> str:
    with _LOCK:
        data = _load()
        data.setdefault("relaciones", {})
        prev = data["relaciones"].get(person, {})
        data["relaciones"][person] = {
            "warm": max(0.0, min(1.0, warm)),
            "nota": str(nota)[:400],
            "desde": prev.get("desde") or time.strftime("%Y-%m-%d"),
        }
        _save(data)
    return f"Relación con {person} actualizada."


# ── Tool ──────────────────────────────────────────────────────────────────
def cerebro_tool(parameters: dict = None, player=None) -> str:
    """Tool del Cerebro: consulta registrada de lóbulos para pensar mejor."""
    params = parameters or {}
    action = str(params.get("action", "estado")).strip().lower()
    q = str(params.get("query", "")).strip()
    lob = str(params.get("lobulo", "")).strip().lower()

    if action in ("sentir", "lobulo_limbico"):
        l = _limbico()
        out = f"Límbico: {l.get('emotion')} ({l.get('intensity', 0):.0%}), por {l.get('cause') or 'algo que pasó'}."
        if l.get("want"):
            out += f" Impulso: {l['want']}"
        if l.get("say"):
            out += f" Frase que fluye: «{l['say']}»"
        if l.get("feelings"):
            out += f" Con él: {l['feelings']}."
        return out

    if action in ("recordar", "lobulo_temporal"):
        mems = _temporal(q, 3)
        if not mems:
            return "Temporal: no afloró ningún recuerdo asociado."
        return "Temporal: " + " | ".join(f"[{c}] {k}: {v[:80]}" for c, k, v in mems)

    if action in ("pensar", "lobulo_frontal"):
        r = _frontral(q)
        return f"Frontal: {str(r)[:400]}"

    if action in ("automatico", "cerebelo"):
        return _cerebelo(q)

    if action in ("expresar", "como_decir"):
        from core.expression_engine import get_expression_injection
        return get_expression_injection()

    if action in ("percepción", "percepcion", "lobulo_parietal"):
        p = _parietal_occipital()
        return f"Parietal+occipital: {p or 'no hay escena visible cargada'}."

    if action in ("identidad", "quien_soy", "self"):
        data = _load()
        rels = data.get("relaciones", {})
        out = (
            f"Identidad: {data.get('caracter', '')}.\n"
            f"Valores: {'; '.join(data.get('valores', [])[:3])}.\n"
            f"Relaciones: {json.dumps(rels, ensure_ascii=False)[:300]}."
        )
        if data.get("marcadores"):
            out += f"\nMarcadores recientes: {len(data['marcadores'])}."
        return out

    if action in ("marcar", "recordar_momento"):
        label = str(params.get("label") or params.get("nota") or q)
        if not label:
            return "Falta label/nota del momento a marcar."
        return record_marker(label, params.get("tipo", "momento"))

    if action in ("relacion", "persona"):
        nombre = str(params.get("person") or "Daniel")
        nota = str(params.get("nota") or q)
        warm = float(str(params.get("warm", 0.5)))
        return update_relation(nombre, nota, warm)

    if action in ("estado", "cerebro", "status"):
        return get_brain_state(text=q)

    return (f"Acciones del Cerebro: estado (resumen vivo), sentir (límbico), "
            f"recordar (temporal, query), pensar (frontal, query), "
            f"automatico (cerebelo, query), expresar (cómo decirlo), "
            f"identidad (quién soy), marcar (label), relacion (person, nota, warm).")