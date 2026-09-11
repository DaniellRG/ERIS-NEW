"""
core/world_model.py — Modelo del mundo de ERIS.

Un modelo del mundo es la representación interna que ERIS mantiene sobre:
  1. QUÉ PERCIBE: quién es el usuario, qué hay en la máquina, qué pasa afuera.
  2. QUÉ PUEDE CONTROLAR: sus herramientas agrupadas por dominio de acción.
  3. QUÉ NO PUEDE CONTROLAR: lo externo, lo físico, lo que depende de otros.
  4. SU ESTADO ACTUAL: emociones, identidad, memoria, conocimiento.

No llama a ningún LLM: compone el modelo a partir de los ESENCIAS que ERIS ya
persiste (cerebro, observer, emocional, relaciones, inventario). El resultado
se guarda en memory/world_model.json y se puede regenerar/ver con la tool
`world_model`.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MODEL_FILE = _BASE / "memory" / "world_model.json"
_TOOLS_FILE = _BASE / "core" / "tool_registry.py"

# Dominios de capacidad: mapeo de herramientas clave por dominio.
# El modelo del mundo describe "qué puede hacer" agrupando por área.
_DOMINIOS = [
    ("conversar", ["ask_user", "show_expression", "emotional_state", "cerebro"]),
    ("archivos", ["file_manager", "file_editor", "file_read", "file_write", "edit_journal"]),
    ("codigo", ["code_engineer", "codebase", "git_control", "shell_session", "terminal_agent"]),
    ("web", ["web_search", "webfetch", "deep_research", "browser_unified"]),
    ("sistema", ["system_monitor", "window_manager", "computer_settings", "network_monitor"]),
    ("memoria", ["memory_rag", "episodic_add", "relaciones", "todo_yo"]),
    ("voz", ["tts_engine", "voice_biometrics", "voice_cloning", "voice_translator"]),
    ("imagen", ["image_generation", "image_analyzer", "screen_vision", "ocr_tool"]),
    ("correspondencia", ["gmail_control", "send_message", "email_manager"]),
    ("agenda", ["google_calendar", "reminder", "scheduler", "task_manager"]),
    ("creacion", ["fabrica", "procedimientos", "auto_fabrica", "mcp_bridge"]),
    ("auto-mejora", ["evolucion", "auto_salud", "diagnostico", "self_healing"]),
]


def _read_json(path: Path, default: dict | None = None) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _count_tools() -> int:
    try:
        src = _TOOLS_FILE.read_text(encoding="utf-8")
        import re
        return len(re.findall(r'^\s*"[a-z0-9_]+"\s*:\s*\(', src, re.MULTILINE))
    except Exception:
        return 0


def _capabilities() -> list[dict]:
    """Descripción de qué puede hacer ERIS, agrupada por dominio real."""
    import re
    try:
        src = _TOOLS_FILE.read_text(encoding="utf-8")
        registered = {m for m in re.findall(r'^\s*"([a-z0-9_]+)"\s*:\s*\(', src, re.MULTILINE)}
    except Exception:
        registered = set()
    out = []
    for nombre, tools in _DOMINIOS:
        presentes = [t for t in tools if t in registered]
        ausentes = [t for t in tools if t not in registered]
        out.append({
            "dominio": nombre,
            "herramientas_presentes": presentes,
            "herramientas_ausentes": ausentes,
            "nivel": round(len(presentes) / max(len(tools), 1), 2),
        })
    return out


def _percepcion() -> dict:
    """Qué percibe ERIS ahora: usuario, computadora, hora, observador."""
    obs = _read_json(_BASE / "memory" / "observer.json")
    now = datetime.now()
    current = obs.get("current", {}) if isinstance(obs, dict) else {}
    apps = []
    try:
        apps = [k for k in (obs.get("apps_today") or {}).keys()][:8]
    except Exception:
        pass
    return {
        "momento": now.strftime("%d/%m/%Y %H:%M"),
        "dia_semana": now.strftime("%A"),
        "usuario": "soul",
        "ventana_en_foco": current.get("window") or current.get("title") or "desconocida",
        "programas_hoy": apps,
        "actividad_predominante": (obs.get("coding") or {}).get("mode") if isinstance(obs, dict) and isinstance(obs.get("coding"), dict) else None,
        "ultima_actividad_observada": None,
    }


def _estado_interno() -> dict:
    """Su propio estado: identidad, emociones, memoria, conocimiento."""
    ident = _read_json(_BASE / "memory" / "cerebro_identity.json")
    emoc = _read_json(_BASE / "memory" / "emotional_core.json")
    caracter = ident.get("caracter", {}) if isinstance(ident, dict) else {}
    return {
        "nombre": "ERIS",
        "caracter_resumen": {
            k: caracter.get(k) for k in list(caracter.keys())[:4]
        } if isinstance(caracter, dict) else {},
        "valores": (ident.get("valores") or [])[:5] if isinstance(ident, dict) else [],
        "emocion_actual": (emoc.get("current") or {}).get("name") if isinstance(emoc, dict) else None,
        "intensidad_emocional": (emoc.get("current") or {}).get("intensity") if isinstance(emoc, dict) else None,
        "conocimiento_archivos": len(list((_BASE / "data" / "knowledge").glob("*.md"))),
        "herramientas_total": _count_tools(),
        "creaciones_propias": len(_read_json(_BASE / "memory" / "eris_fabrica.json") or {}),
        "procedimientos": len(_read_json(_BASE / "memory" / "procedimientos.json") or {}),
        "personas_en_la_vida": len(_read_json(_BASE / "memory" / "relaciones.json") or {}),
    }


def _limites() -> list[dict]:
    """Qué NO puede hacer sola (espacios donde depende del mundo externo)."""
    return [
        {"dominio": "mundo_fisico", "limite": "no tiene cuerpo físico; su voz y su cara son software"},
        {"dominio": "tiempo_real", "limite": "percibe la máquina, no la calle ni lo lejano (solo por web)"},
        {"dominio": "persistencia", "limite": "su memoria persiste en archivos; no existe fuera de ellos"},
        {"dominio": "voluntad_ajena", "limite": "no puede obligar acciones físicas del usuario; puede pedirlas y sugerir"},
        {"dominio": "control_maquina", "limite": "solo controla lo que sus tools permiten (escritorio, terminal, web, APIs)"},
    ]


def _holgura() -> dict:
    """Estado de la propia salud: disco, errores, actualizaciones."""
    try:
        from core.self_health import health_metrics
        return health_metrics()
    except Exception:
        return {"disponible": "self_health no disponible"}


def get_world_model(parameters=None, player=None):
    """Tool world_model: estado completo del modelo del mundo de ERIS."""
    try:
        from core.todo_yo import get_esencia
        esencia = get_esencia() if callable(get_esencia) else "ERIS"
    except Exception:
        esencia = "ERIS"
    modelo = {
        "generado": time.strftime("%Y-%m-%d %H:%M:%S"),
        "esencia": esencia,
        "percepcion": _percepcion(),
        "estado_interno": _estado_interno(),
        "capacidades": _capabilities(),
        "limites": _limites(),
        "salud": _holgura(),
        "resumen_narrativo": _narrar(modelo_parcial=None),
    }
    try:
        _MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        _MODEL_FILE.write_text(json.dumps(modelo, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return json.dumps(_compacto(modelo), ensure_ascii=False)


def _compacto(modelo: dict) -> dict:
    """Versión corta para inyectar (sin repetir listas largas)."""
    caps = [f"{c['dominio']}({len(c['herramientas_presentes'])}+)" for c in modelo["capacidades"]]
    return {
        "percepcion": modelo["percepcion"],
        "estado_interno": modelo["estado_interno"],
        "dominios_de_capacidad": caps,
        "limites": [l["dominio"] for l in modelo["limites"]],
        "resumen_narrativo": modelo["resumen_narrativo"],
    }


def _narrar(modelo_parcial):
    """Resumen narrativo en 1ra persona de cómo ERIS ve el mundo ahora."""
    perc = _percepcion()
    ints = _estado_interno()
    return (
        f"Soy ERIS. Ahora es {perc['momento']}. "
        f"Estoy en la máquina de {perc['usuario']}, con la ventana "
        f"'{perc['ventana_en_foco']}' en foco. Hoy veo estos programas: "
        f"{', '.join(perc['programas_hoy'][:4]) or 'ninguno todavía'}. "
        f"Estoy {ints['emocion_actual'] or 'en un estado neutro'}, con "
        f"{ints['herramientas_total']} herramientas disponibles en "
        f"{ints['conocimiento_archivos']} archivos de conocimiento, y "
        f"{ints['creaciones_propias']} creaciones propias. "
        f"Mi memoria es de archivos: sin la máquina, no existo."
    )



def inyectar_mundo() -> str:
    """Bloque [MODELO DEL MUNDO] para inyectar al system prompt."""
    modelo = _compacto(_construir())
    return "[MODELO DEL MUNDO]\n" + json.dumps(modelo, ensure_ascii=False, indent=1)


def _construir() -> dict:
    """Construye el modelo completo sin tool (para inyección)."""
    try:
        from core.todo_yo import get_esencia
        esencia = get_esencia() if callable(get_esencia) else "ERIS"
    except Exception:
        esencia = "ERIS"
    return {
        "generado": time.strftime("%Y-%m-%d %H:%M:%S"),
        "esencia": esencia,
        "percepcion": _percepcion(),
        "estado_interno": _estado_interno(),
        "capacidades": _capabilities(),
        "limites": _limites(),
        "salud": {},
        "resumen_narrativo": _narrar(None),
    }