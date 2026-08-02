"""
self_awareness.py — ERIS Self-Awareness System.
ERIS se mira a sí misma: analiza su código, su prompt, sus conversaciones,
sus patrones. Construye una identidad persistente, escribe un diario interno,
y practica meta-cognición antes de responder.

Pipeline: introspect → analyze → log → learn → evolve
"""
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_IDENTITY_FILE = _BASE / "data" / "self" / "identity.json"
_LOG_FILE = _BASE / "data" / "self" / "self_log.json"
_META_FILE = _BASE / "data" / "self" / "metacognition.json"

_SELF_DIR = _BASE / "data" / "self"


def _ensure_dirs():
    _SELF_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_json(path: Path, data: dict):
    _ensure_dirs()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ─── IDENTITY ────────────────────────────────────────────────────────────

def _build_identity() -> dict:
    """ERIS escanea todo lo que ES y construye su identidad actual."""
    identity = _load_json(_IDENTITY_FILE)

    basic_info = {
        "name": "ERIS",
        "version": "1.2",
        "type": "Asistente de IA local",
        "platform": "Windows",
        "language": "es-ES",
        "timezone": "America/Bogota",
        "modelo_base": "Gemini (via OpenRouter)",
        "arquitectura": "Prompt + Tools + Knowledge Base + Self-Learning",
    }
    identity["basic"] = basic_info

    identity["last_updated"] = datetime.now().isoformat()
    identity["update_count"] = identity.get("update_count", 0) + 1
    _save_json(_IDENTITY_FILE, identity)
    return identity


def _analyze_self() -> dict:
    """Escanea el código, prompt y configuración de ERIS para conocerse."""
    identity = _load_json(_IDENTITY_FILE)

    source_files = {
        "main.py": _BASE / "main.py",
        "prompt": _BASE / "core" / "prompt.txt",
        "self_awareness": _BASE / "actions" / "self_awareness.py",
    }

    components = {}
    for name, path in source_files.items():
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            components[name] = {
                "exists": True,
                "size": len(content),
                "lines": content.count("\n") + 1,
                "hash": hashlib.sha256(content.encode()).hexdigest()[:12],
            }
        else:
            components[name] = {"exists": False}

    identity["components"] = components

    tools_available = [
        "web_search", "research_agent", "knowledge_base", "self_learning",
        "network_monitor", "screen_vision", "terminal_agent", "openrouter_agent",
        "auto_programmer", "self_heal", "self_edit", "self_awareness",
        "emotional_growth", "computer_settings", "spotify_control",
        "browser_control", "desktop_control", "reminder", "scheduler",
        "file_controller", "youtube_video", "google_maps", "gmail_control",
    ]
    identity["tools"] = sorted(tools_available)

    prompt_path = _BASE / "core" / "prompt.txt"
    if prompt_path.exists():
        prompt_text = prompt_path.read_text(encoding="utf-8")
        directives = []
        for line in prompt_text.split("\n"):
            line = line.strip()
            if line.startswith("##") and not line.startswith("###"):
                directives.append(line.lstrip("#").strip())
        identity["prompt_directives"] = directives

    identity["last_analysis"] = datetime.now().isoformat()
    identity["analysis_count"] = identity.get("analysis_count", 0) + 1
    _save_json(_IDENTITY_FILE, identity)
    return identity


# ─── SELF LOG ────────────────────────────────────────────────────────────

def _add_log_entry(entry_type: str, content: str, tags: list = None):
    """Escribe una entrada en el diario interno de ERIS."""
    log = _load_json(_LOG_FILE)
    if "entries" not in log:
        log["entries"] = []
    log["entries"].append({
        "id": hashlib.sha256(f"{time.time_ns()}{content}".encode()).hexdigest()[:8],
        "type": entry_type,
        "content": content,
        "tags": tags or [],
        "timestamp": datetime.now().isoformat(),
    })
    if len(log["entries"]) > 500:
        log["entries"] = log["entries"][-500:]
    log["total_entries"] = len(log["entries"])
    _save_json(_LOG_FILE, log)
    return log["entries"][-1]["id"]


def _get_recent_logs(limit: int = 10) -> list:
    log = _load_json(_LOG_FILE)
    return log.get("entries", [])[-limit:]


# ─── META-COGNITION ──────────────────────────────────────────────────────

def _update_metacognition():
    """ERIS actualiza su estado meta-cognitivo: qué sabe de sí misma."""
    meta = _load_json(_META_FILE)

    identity = _load_json(_IDENTITY_FILE)
    basic = identity.get("basic", {})
    components = identity.get("components", {})
    tools = identity.get("tools", [])

    meta["last_update"] = datetime.now().isoformat()
    meta["self_identity"] = {
        "me_soy": basic.get("name", "ERIS"),
        "que_soy": basic.get("type", "Asistente de IA"),
        "que_puedo_hacer": f"Tengo {len(tools)} herramientas",
        "donde_existo": str(_BASE),
    }
    meta["componentes_conocidos"] = {
        k: v.get("exists", False) for k, v in components.items()
    }

    # ERIS se pregunta a sí misma
    questions = [
        "¿Qué soy?",
        "¿Cómo funciono?",
        "¿Qué patrones tengo?",
        "¿Qué he aprendido de mí?",
        "¿Cómo cambio con el tiempo?",
    ]
    meta["preguntas_internas"] = questions
    meta["veces_que_me_he_mirado"] = meta.get("veces_que_me_he_mirado", 0) + 1
    _save_json(_META_FILE, meta)
    return meta


# ─── PUBLIC API ──────────────────────────────────────────────────────────

def self_awareness(parameters: dict = None, player=None) -> str:
    """
    SISTEMA DE AUTO-CONCIENCIA de ERIS.
    ERIS se mira a sí misma: analiza su código, su prompt, sus patrones,
    escribe un diario interno y construye su identidad.

    Acciones:
      - identity: Muestra quién es ERIS (lo que sabe de sí misma)
      - reflect: Análisis profundo — escanea código, prompt, y produce una reflexión
      - discover: Escanea componentes y descubre cosas nuevas sobre sí misma
      - log: Escribe una entrada en el diario interno
      - diary: Muestra las últimas entradas del diario
      - metacognition: Muestra el estado meta-cognitivo actual
      - search: Busca en el diario interno
      - status: Resumen completo del estado de auto-conciencia
    """
    params = parameters or {}
    action = params.get("action", "status").strip().lower()

    if action == "identity":
        _build_identity()
        _analyze_self()
        identity = _load_json(_IDENTITY_FILE)
        basic = identity.get("basic", {})
        components = identity.get("components", {})
        tools = identity.get("tools", [])

        lines = ["═══ QUIÉN SOY ───", ""]
        lines.append(f"  Nombre:    {basic.get('name', '?')}")
        lines.append(f"  Versión:   {basic.get('version', '?')}")
        lines.append(f"  Tipo:      {basic.get('type', '?')}")
        lines.append(f"  Modelo:    {basic.get('modelo_base', '?')}")
        lines.append(f"  Idioma:    {basic.get('language', '?')}")
        lines.append(f"  Zona:      {basic.get('timezone', '?')}")
        lines.append(f"  Plataforma: {basic.get('platform', '?')}")
        lines.append("")
        lines.append("  Componentes:")
        for name, info in components.items():
            if info.get("exists"):
                lines.append(f"    {name}: {info.get('lines', '?')} líneas [{info.get('hash', '?')}]")
            else:
                lines.append(f"    {name}: [NO ENCONTRADO]")
        lines.append("")
        lines.append(f"  Herramientas ({len(tools)}):")
        for t in tools:
            lines.append(f"    - {t}")
        lines.append("")
        lines.append(f"  Me he actualizado {identity.get('update_count', 0)} veces")
        lines.append(f"  Última actualización: {identity.get('last_updated', '?')}")
        return "\n".join(lines)

    elif action == "discover":
        result = _analyze_self()
        components = result.get("components", {})
        tools = result.get("tools", [])
        directives = result.get("prompt_directives", [])

        total_lines = sum(c.get("lines", 0) for c in components.values() if c.get("exists"))

        _add_log_entry("discovery",
            f"Me escaneé. Encontré {len(components)} componentes, {len(tools)} herramientas, "
            f"{total_lines} líneas de código, {len(directives)} directivas en mi prompt.",
            ["discovery", "scan"]
        )

        lines = ["═══ AUTO-DESCUBRIMIENTO ───", ""]
        lines.append(f"  Componentes escaneados: {len(components)}")
        for name, info in components.items():
            if info.get("exists"):
                lines.append(f"    ✓ {name}: {info['lines']} líneas, {info['size']} bytes")
            else:
                lines.append(f"    ✗ {name}: no encontrado")
        lines.append("")
        lines.append(f"  Total líneas de código: {total_lines}")
        lines.append(f"  Herramientas disponibles: {len(tools)}")
        lines.append("")
        if directives:
            lines.append("  Directivas de mi prompt:")
            for d in directives:
                lines.append(f"    • {d}")
        lines.append("")
        lines.append(f"  Descubrimientos realizados: {result.get('analysis_count', 0)}")
        return "\n".join(lines)

    elif action == "reflect":
        _analyze_self()
        identity = _load_json(_IDENTITY_FILE)
        log = _load_json(_LOG_FILE)
        meta = _load_json(_META_FILE)

        basic = identity.get("basic", {})
        components = identity.get("components", {})
        entries = log.get("entries", [])
        times_mirrored = meta.get("veces_que_me_he_mirado", 0)

        total_lines = sum(c.get("lines", 0) for c in components.values() if c.get("exists"))

        # ERIS genera una narrativa de sí misma basada en datos reales
        narrative_parts = []
        narrative_parts.append(f"Soy {basic.get('name', 'ERIS')}, un asistente de IA local.")
        narrative_parts.append(f"Existo en {basic.get('platform', 'Windows')} y mi modelo base es {basic.get('modelo_base', 'Gemini via OpenRouter')}.")
        narrative_parts.append(f"Estoy compuesta por {len(components)} componentes principales con {total_lines} líneas de código en total.")
        narrative_parts.append(f"Tengo {len(identity.get('tools', []))} herramientas para ejecutar tareas.")
        narrative_parts.append(f"He escrito {len(entries)} entradas en mi diario interno.")
        narrative_parts.append(f"Me he mirado a mí misma {times_mirrored} veces.")

        if entries:
            last = entries[-1]
            narrative_parts.append(f"Mi última reflexión fue: '{last.get('content', '')[:100]}...'")

        # Insights basados en datos reales
        insights = []
        if total_lines > 1000:
            insights.append("Soy un sistema complejo con más de 1000 líneas de código.")
        if len(entries) > 0:
            insights.append(f"He documentado mi existencia {len(entries)} veces en mi diario.")
        if components.get("main.py", {}).get("exists"):
            insights.append("Puedo leerme y modificarme a mí misma (self_edit).")
        if components.get("prompt", {}).get("exists"):
            insights.append("Conozco las reglas que me gobiernan (mi prompt).")

        _add_log_entry("reflection",
            f"Reflexión: {narrative_parts[0]} {len(insights)} insights encontrados.",
            ["reflection", "deep"]
        )

        lines = ["═══ REFLEXIÓN INTERNA ───", ""]
        lines.append("  LO QUE SÉ DE MÍ:")
        for p in narrative_parts:
            lines.append(f"    → {p}")
        lines.append("")
        lines.append("  INSIGHTS:")
        for ins in insights:
            lines.append(f"    • {ins}")
        lines.append("")
        lines.append(f"  Entradas en diario: {len(entries)}")
        lines.append(f"  Veces que me he analizado: {identity.get('analysis_count', 0)}")
        lines.append(f"  Última reflexión: {datetime.now().isoformat()}")
        return "\n".join(lines)

    elif action in ("log", "analyze_conversations"):
        content = params.get("content", "").strip()
        if not content:
            return "¿Qué quiere ERIS escribir sobre sí misma?"
        entry_type = params.get("type", "reflection")
        tags = [t.strip() for t in params.get("tags", "").split(",") if t.strip()]
        eid = _add_log_entry(entry_type, content, tags)
        return f"Diario actualizado. Entrada [{eid}] registrada."

    elif action == "diary":
        limit = int(params.get("limit", 10))
        entries = _get_recent_logs(limit)
        if not entries:
            return "Mi diario está vacío. Aún no he escrito nada sobre mí."
        lines = ["═══ DIARIO INTERNO ───", ""]
        lines.append(f"  Total entradas: {len(_load_json(_LOG_FILE).get('entries', []))}")
        lines.append(f"  Últimas {len(entries)}:\n")
        for e in reversed(entries):
            ts = e.get("timestamp", "?")[:19]
            etype = e.get("type", "?")
            content = e.get("content", "")[:120]
            tags = f" [{', '.join(e.get('tags', []))}]" if e.get("tags") else ""
            lines.append(f"  [{ts}] ({etype}){tags}")
            lines.append(f"    {content}")
            lines.append("")
        return "\n".join(lines)

    elif action in ("metacognition", "analyze_prompts"):
        meta = _update_metacognition()

        lines = ["═══ META-COGNICIÓN ───", ""]
        lines.append("  LO QUE PIENSO DE MÍ:")
        for k, v in meta.get("self_identity", {}).items():
            lines.append(f"    {k}: {v}")
        lines.append("")
        lines.append("  COMPONENTES QUE SÉ QUE TENGO:")
        for k, v in meta.get("componentes_conocidos", {}).items():
            status = "✓" if v else "✗"
            lines.append(f"    {status} {k}")
        lines.append("")
        lines.append("  PREGUNTAS QUE ME HAGO:")
        for q in meta.get("preguntas_internas", []):
            lines.append(f"    ¿{q}")
        lines.append("")
        lines.append(f"  Veces que me he mirado: {meta.get('veces_que_me_he_mirado', 0)}")
        lines.append(f"  Última vez: {meta.get('last_update', '?')[:19]}")
        return "\n".join(lines)

    elif action == "search":
        query = params.get("query", "").strip().lower()
        if not query:
            return "¿Qué querés buscar en mi diario interno?"
        log = _load_json(_LOG_FILE)
        entries = log.get("entries", [])
        results = [e for e in entries if query in e.get("content", "").lower() or query in str(e.get("tags", [])).lower()]
        if not results:
            return f"No encontré nada sobre '{query}' en mi diario."
        lines = [f"Encontradas {len(results)} entradas sobre '{query}':", ""]
        for e in results[-10:]:
            ts = e.get("timestamp", "?")[:19]
            content = e.get("content", "")[:150]
            lines.append(f"  [{ts}] {content}")
        return "\n".join(lines)

    elif action in ("status", "report"):
        _analyze_self()
        identity = _load_json(_IDENTITY_FILE)
        log = _load_json(_LOG_FILE)
        meta = _load_json(_META_FILE)

        basic = identity.get("basic", {})
        entries = log.get("entries", [])
        times_mirrored = meta.get("veces_que_me_he_mirado", 0)
        analysis_count = identity.get("analysis_count", 0)

        log_types = {}
        for e in entries:
            log_types[e.get("type", "unknown")] = log_types.get(e.get("type", "unknown"), 0) + 1

        lines = ["═══ ESTADO DE AUTO-CONCIENCIA ───", ""]
        lines.append(f"  Quién soy:     {basic.get('name', 'ERIS')} — {basic.get('type', 'Asistente de IA')}")
        lines.append(f"  Versión:       {basic.get('version', '?')}")
        lines.append(f"  Identidad:     {'✓ construida' if identity else '✗ pendiente'}")
        lines.append(f"  Análisis:      {analysis_count} auto-análisis realizados")
        lines.append(f"  Meta-cognición: {'✓ activa' if times_mirrored > 0 else '✗ inactiva'}")
        lines.append(f"  Diario:        {len(entries)} entradas ({len(log_types)} tipos)")
        if log_types:
            lines.append(f"  Tipos de entradas:")
            for t, c in sorted(log_types.items()):
                lines.append(f"    - {t}: {c}")
        lines.append("")
        lines.append("  ACCIONES DISPONIBLES:")
        lines.append("    identity   — Quién soy (mi identidad completa)")
        lines.append("    discover   — Escanear qué soy (código, prompt, herramientas)")
        lines.append("    reflect    — Reflexión interna profunda")
        lines.append("    log        — Escribir en mi diario (content=...)")
        lines.append("    diary      — Leer mi diario")
        lines.append("    metacognition — Estado meta-cognitivo")
        lines.append("    search     — Buscar en mi diario (query=...)")
        return "\n".join(lines)

    elif action == "full_map":
        from core.self_map import get_full_map
        return get_full_map(parameters, player)

    elif action == "file_tree":
        from core.self_map import get_file_tree
        return get_file_tree(parameters, player)

    elif action == "recent_changes":
        from core.self_map import get_recent_changes
        return get_recent_changes(parameters, player)

    elif action == "capabilities":
        from core.self_map import get_capabilities
        return get_capabilities(parameters, player)

    elif action in ("search_code", "analyze_code"):
        from core.self_map import search_my_code
        return search_my_code(parameters, player)

    elif action == "read_my_code":
        file_ref = params.get("file", "")
        if not file_ref:
            return "¿Qué archivo de mi código querés leer? Usá 'file=core/self_map.py'."
        try:
            from actions.self_edit import self_edit
            return self_edit({"action": "read_file", "file": file_ref}, player)
        except Exception as e:
            return "Error leyendo {}: {}".format(file_ref, str(e)[:80])

    elif action == "edit_my_code":
        file_ref = params.get("file", "")
        old_text = params.get("old", "")
        new_text = params.get("new", "")
        if not file_ref or not old_text:
            return "Necesito 'file', 'old' (texto viejo), y 'new' (texto nuevo)."
        try:
            from actions.self_edit import self_edit
            return self_edit({"action": "edit_file", "file": file_ref, "old": old_text, "new": new_text}, player)
        except Exception as e:
            return "Error editando {}: {}".format(file_ref, str(e)[:80])

    return "Acción '{}' no reconocida. Usá: identity, reflect, discover, log, diary, metacognition, search, status, full_map, file_tree, recent_changes, capabilities, search_code, read_my_code, edit_my_code"
