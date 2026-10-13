# -*- coding: utf-8 -*-
"""core/context_builder.py — ARMADO DEL CONTEXTO DEL TURNO (Fase 1 resto).

Extrae de `main.py:_build_config` TODA la construcción del *system prompt*
enriquecido: memoria, semántica, RAG, digest, personalidad, cerebro, relaciones,
vida interior, mundo nuevo I/II, gustos, lecciones, conversación reciente,
contexto compartido, reconexión, resumen de sesión, voz, autoconocimiento,
recuerdos relevantes, estilo activo, verificación y anti-repetición; más el
*smart trim* a `MAX_SYSTEM_CHARS`.

Lo único que queda en `main.py` es lo específico de Gemini Live
(`SpeechConfig`, `tools`, transcripción, `realtime_input_config`,
`LiveConnectConfig`).

Reutilizable: la GUI lo llama con `host=self` (estado vivo de `ErisLive`); la
CLI y los subagentes pueden llamarlo con `host=None` (degradan en silencio a un
contexto sin estado de GUI) o con cualquier objeto que exponga los atributos
opcionales que se leen/escriben:

  _convo_ctx, _shared, _active_task, _last_tool_context, _session_summary,
  _last_text_trigger, _rag_last_hash, _rag_last_time, _active_style,
  _last_rep_nudge

Nunca lanza: cada bloque degrada en silencio si su dependencia falta.
"""

from __future__ import annotations

import json
import time
from datetime import datetime  # noqa: F401  (compat: el original lo importaba)
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent      # raíz del proyecto
_MEM_DIR = _BASE / "memory"


def _g(host, name: str, default=None):
    """Lee un atributo opcional del host sin romper si no está."""
    if host is None:
        return default
    return getattr(host, name, default)


def _set(host, name: str, value) -> None:
    """Escribe un atributo opcional del host sin romper si no se puede."""
    if host is None:
        return
    try:
        setattr(host, name, value)
    except Exception:
        pass


def build_system_prompt(host=None) -> str:
    """Arma el *system instruction* completo (bloques + sys_prompt + trim).

    Es el cuerpo extraído de `main.py:_build_config`. Devuelve el texto listo
    para `system_instruction`. Nunca lanza.
    """
    from core.time_utils import get_time_context
    from core.prompt_loader import load_system_prompt
    from memory.memory_manager import load_memory, format_memory_for_prompt

    memory     = load_memory()
    mem_str    = format_memory_for_prompt(memory)
    sys_prompt = load_system_prompt()

    # ── Inject real memory context (partes aparte, ANTES del sys_prompt
    #    para que sobrevivan al truncado) ──
    memory_context = ""
    try:
        from actions.eris_db import memory_all, episodic_recent
        mems = memory_all(5)
        if mems:
            memory_context += "[MEMORIAS]\n"
            for m in mems[:4]:
                memory_context += f"- {m['key']}: {str(m['value'])[:120]}\n"
        eps = episodic_recent(8)
        if eps:
            _clean_eps = [e for e in eps
                          if e.get("category") != "idle_learning"
                          and "no encontre" not in str(e.get("event", "")).lower()]
            if _clean_eps:
                memory_context += "\n[EVENTOS RECIENTES]\n"
                for e in _clean_eps[:3]:
                    memory_context += f"- {e['event'][:120]}\n"
    except Exception:
        pass

    # ── Memoria semántica (semantic.json / episodic.json): lectura directa,
    #    barata, sin embeddings — la memoria semántica se usa en el prompt ──
    semantic_context = ""
    try:
        _sem_file = _MEM_DIR / "semantic.json"
        _epi_file = _MEM_DIR / "episodic.json"
        if _sem_file.exists():
            _facts = json.loads(_sem_file.read_text(encoding="utf-8"))
            if isinstance(_facts, list) and _facts:
                _clean_facts = []
                for f in _facts:
                    _subj = str(f.get("subject", ""))
                    _obj  = str(f.get("object", ""))
                    _low  = (_subj + " " + _obj).lower()
                    if "aprendi sobre" in _low or "no encontre" in _low or "no se encontraron" in _low:
                        continue
                    if float(f.get("confidence", 0) or 0) < 0.45:
                        continue
                    _clean_facts.append(f)
                if _clean_facts:
                    semantic_context += "[HECHOS SEMANTICOS]\n"
                    for f in _clean_facts[-4:]:
                        semantic_context += "- {} {} {} (conf {:.0f}%)\n".format(
                            str(f.get("subject", ""))[:60],
                            str(f.get("predicate", ""))[:30],
                            str(f.get("object", ""))[:80],
                            float(f.get("confidence", 0) or 0),
                        )
        if _epi_file.exists():
            _epi = json.loads(_epi_file.read_text(encoding="utf-8"))
            if isinstance(_epi, list) and _epi:
                _clean_epi = []
                for e in _epi:
                    _evt = str(e.get("event", ""))
                    if "no encontre" in _evt.lower() or "no se encontraron" in _evt.lower():
                        continue
                    _clean_epi.append(e)
                if _clean_epi:
                    semantic_context += "\n[EPISODIOS SEMANTICOS]\n"
                    for e in _clean_epi[-3:]:
                        semantic_context += "- {} (imp {:.1f})\n".format(
                            str(e.get("event", ""))[:120],
                            float(e.get("importance", 0) or 0),
                        )
    except Exception:
        pass

    # ── RAG knowledge context: solo si Ollama responde rápido
    #    (evita el stall de 30s por timeout de embed al reconectar) ──
    rag_context = ""
    try:
        from core.llm_bridge import ping as _ollama_ping
        from core.rag_pipeline import query_documents, stats
        if _ollama_ping(1.0):
            _rag_stats = stats()
            if _rag_stats.get("documents", 0) > 0:
                # Usar la conversación reciente (sobrevive a reconexiones)
                # como base de la query, NO memory.keys() (conocimiento genérico).
                _recent = _g(host, "_convo_ctx", None) or []
                _query_txt = " ".join(_recent[-4:]).strip()
                if not _query_txt:
                    _query_txt = "temas principales"
                _rag_results = query_documents(_query_txt[:500], top_k=4)
                if _rag_results:
                    rag_context = "[CONOCIMIENTO INDEXADO]\n"
                    for r in _rag_results:
                        rag_context += f"- {r['filename']}: {r['text'][:200]}\n"
    except Exception:
        pass

    # ── Digest diario (memoria de largo plazo) ──
    digest_block = ""
    try:
        from core.daily_digest import inject_digest
        digest_block = inject_digest()
    except Exception:
        pass

    # Get time context (from worldtimeapi.org or system fallback)
    time_ctx = get_time_context()

    parts = [time_ctx]

    # ── Inject emotional state & personality into prompt ──
    # (antes de sys_prompt para que sobrevivan al truncado de 32K)
    try:
        from actions.emotional_growth import _load as _eg_load, get_prompt_injection
        from core.personality_engine import get_tone_for_response
        from core.emotional_state import get_tone_instruction as _state_tone
        from actions.relationship import inject_relationship
        from core.style_engine import inject_style
        from core.emotional_core import get_core_injection
        _eg_state = _eg_load()
        _injection = get_prompt_injection(_eg_state)
        _tone = get_tone_for_response()
        parts.append(f"[PERSONALIDAD] {_tone}")
        parts.append(f"[EMOCION] {_injection}")
        _sentir = get_core_injection()
        if _sentir:
            parts.append(_sentir)
        try:
            from core.observer import get_situation_injection
            _sit = get_situation_injection()
            if _sit:
                parts.append(_sit)
        except Exception:
            pass
        _state_tone_txt = _state_tone() if _state_tone else ""
        if _state_tone_txt:
            parts.append(f"[TONO] {_state_tone_txt}")
        _rel = inject_relationship()
        if _rel:
            parts.append(_rel)
        _style = inject_style()
        if _style:
            parts.append(_style)
    except Exception:
        pass

    # ── CEREBRO: homúnculo (estado cerebral unificado) + expresión humana.
    #    Se inyecta ANTES del sys_prompt (sobrevive al trim de 30K). ──
    try:
        from core.cerebro import get_brain_state
        from core.expression_engine import get_expression_injection
        _cerebro_block = get_brain_state(text="")
        if _cerebro_block:
            parts.append(_cerebro_block)
        from core.expression_engine import get_expression_injection, get_saludo_vivo
        _expr_block = get_expression_injection()
        if _expr_block:
            parts.append(_expr_block)
        _saludo_block = get_saludo_vivo()
        if _saludo_block:
            parts.append(_saludo_block)
    except Exception:
        pass

    # ── RELACIONES: vida social (multi-persona) y VIDA INTERIOR:
    #    rituales/huellas/diario. Inyectadas ANTES del sys_prompt
    #    (sobreviven al trim). ──
    try:
        from core.relaciones import inject_relaciones_vivas
        _relaciones = inject_relaciones_vivas()
        if _relaciones:
            parts.append(_relaciones)
    except Exception:
        pass
    try:
        from core.vida_interna import maybe_ritual, inject_vida, recuperar_huella
        _ritual_txt = maybe_ritual()
        _huella_txt = recuperar_huella()
        _vida = inject_vida(_ritual_txt, _huella_txt)
        if _vida:
            parts.append(_vida)
    except Exception:
        pass

    # ── MUNDO NUEVO: autoimagen, temas propios, ambiente, sueños, voz.
    #    Bloques breves; ANTES del sys_prompt (sobreviven al trim). ──
    try:
        from core.autoimagen import get_autoimagen
        _autoimg = get_autoimagen()
        if _autoimg:
            parts.append(_autoimg)
    except Exception:
        pass
    try:
        from core.intereses import inyect_intereses
        _interes = inyect_intereses()
        if _interes:
            parts.append(_interes)
    except Exception:
        pass
    try:
        from core.ambiente import inyect_ambiente
        _amb = inyect_ambiente()
        if _amb:
            parts.append(_amb)
    except Exception:
        pass
    try:
        from core.suenos import ilustrar_si_hay_sueno_nuevo, inyect_suenos
        try:
            ilustrar_si_hay_sueno_nuevo()  # dispara en hilo, no bloquea
        except Exception:
            pass
        _sueno = inyect_suenos()
        if _sueno:
            parts.append(_sueno)
    except Exception:
        pass
    try:
        from core.expression_engine import get_voz_propia
        _vozb = get_voz_propia()
        if _vozb:
            parts.append(_vozb)
    except Exception:
        pass

    # ── MUNDO NUEVO II: caprichos, reloj, momentos, bienestar, cuadernos, cierre.
    #    Bloques breves; ANTES del sys_prompt (sobreviven al trim). ──
    try:
        from core.caprichos import inyect_caprichos
        _capr = inyect_caprichos()
        if _capr:
            parts.append(_capr)
    except Exception:
        pass
    try:
        from core.tiempo_interno import inyect_tiempo_interno
        _tiemp = inyect_tiempo_interno()
        if _tiemp:
            parts.append(_tiemp)
    except Exception:
        pass
    try:
        from core.festejos import inyect_festejos
        _feste = inyect_festejos()
        if _feste:
            parts.append(_feste)
    except Exception:
        pass
    try:
        from core.bienestar import inyect_bienestar
        _biens = inyect_bienestar()
        if _biens:
            parts.append(_biens)
    except Exception:
        pass
    try:
        from core.cuadernos import inyect_cuadernos
        _cuad = inyect_cuadernos()
        if _cuad:
            parts.append(_cuad)
    except Exception:
        pass
    try:
        from core.despedidas import inyect_despedidas
        _desp = inyect_despedidas()
        if _desp:
            parts.append(_desp)
    except Exception:
        pass

    # ── Inject gustos into prompt ──
    try:
        from actions.gustos import inject_gustos
        _gustos = inject_gustos()
        if _gustos:
            parts.append(_gustos)
    except Exception:
        pass

    if memory_context:
        parts.append(memory_context)
    if semantic_context:
        parts.append(semantic_context)
    if rag_context:
        parts.append(rag_context)
    if digest_block:
        parts.append(digest_block)
    if mem_str:
        parts.append(mem_str)
    # ── Lecciones aprendidas y correcciones: el auto-aprendizaje SÍ impacta
    #    respuestas futuras (solo lecciones de calidad, sin placeholders) ──
    learning_context = ""
    try:
        _lessons_file = _MEM_DIR / "learned_lessons.json"
        _corrections_file = _MEM_DIR / "auto_corrections.json"
        if _lessons_file.exists():
            _lessons = json.loads(_lessons_file.read_text(encoding="utf-8"))
            if isinstance(_lessons, list):
                _good = [l for l in _lessons
                         if not str(l.get("lesson", "")).startswith("[Sin corrección")
                         and str(l.get("lesson", "")).strip()]
                if _good:
                    learning_context += "[LECCIONES APRENDIDAS]\n"
                    for l in _good[-5:]:
                        _cat = l.get("category", "general")
                        _txt = str(l.get("lesson", ""))[:160]
                        learning_context += f"- [{_cat}] {_txt}\n"
        if _corrections_file.exists():
            _corr = json.loads(_corrections_file.read_text(encoding="utf-8"))
            if isinstance(_corr, list):
                _good = [c for c in _corr
                         if str(c.get("corrected", "")).strip()
                         and not str(c.get("corrected", "")).startswith("[Sin corrección")]
                if _good:
                    learning_context += "\n[CORRECCIONES RECIENTES (evitar estos errores)]\n"
                    for c in _good[-3:]:
                        learning_context += f"- {str(c.get('reason', ''))[:100]} → {str(c.get('corrected', ''))[:120]}\n"
        if learning_context:
            parts.append(learning_context)
    except Exception:
        pass
    # ── Contexto de conversación reciente (sobrevive a reconexiones) ──
    _convo_ctx = _g(host, "_convo_ctx", None)
    if _convo_ctx:
        parts.append(
            "[CONTEXTO DE CONVERSACIÓN RECIENTE (lo que veníamos haciendo)]\n"
            + "\n".join(_convo_ctx)
        )
    # ── Contexto compartido (Fase 1.2): proyecto, archivo activo, app en foco
    #    y modo solo-lectura. La conversación y el resumen ya se inyectan
    #    arriba, así que acá van omitidos para no duplicar. ──
    try:
        _shared = _g(host, "_shared", None)
        if _shared is not None:
            _shared_block = _shared.context_block(include_convo=False, include_summary=False)
            if _shared_block:
                parts.append(_shared_block)
    except Exception:
        pass
    # ── Tarea activa: si se cortó a mitad, Eris DEBE continuar ──
    _active = _g(host, "_active_task", "")
    _tool_ctx = _g(host, "_last_tool_context", "")
    if _active or _tool_ctx:
        reconnect_block = (
            "[⚠️ IMPORTANTE: RECONEXIÓN DE SESIÓN]\n"
            "Tu conexión con Gemini se cortó y se reconectó automáticamente. "
            "NO es una conversación nueva. Estabas en medio de una tarea.\n"
        )
        if _active:
            reconnect_block += f"TAREA EN CURSO: {_active}\n"
        if _tool_ctx:
            reconnect_block += f"ÚLTIMO CONTEXTO: {_tool_ctx}\n"
        reconnect_block += (
            "CONTINUÁ exactamente donde te quedaste. "
            "NO saludes de nuevo. NO preguntes qué querés hacer. "
            "Retomá la tarea interrumpida como si nada hubiera pasado.\n"
            "Si ya terminaste la tarea, informá el resultado.\n"
        )
        parts.append(reconnect_block)
    # ── Resumen de sesión larga: lo ya descartado, comprimido ──
    _session_summary = _g(host, "_session_summary", None)
    if _session_summary:
        parts.append(
            "[RESUMEN DE SESIÓN LARGA (historial más viejo, comprimido)]\n"
            + _session_summary
        )
    # ── Instrucción de voz: evitar los sonidos de relleno ("mmm"/"um")
    #    que el modelo emite al arrancar la respuesta (suenan a "mmmmm"
    #    distorsionado por el altavoz). ──
    parts.append(
        "[VOZ] Al responder por voz NO emitas sonidos de relleno ni "
        "vocalizaciones (mmm, um, ah, eh, mmmh). Empezá a hablar "
        "directamente con la respuesta, sin humedades ni arrastres."
    )
    # ── AUTOCONOCIMIENTO VIVO: el mapa integral de Eris, SIEMPRE presente.
    #    Así sabe qué es, qué tiene (cuerpo/mente/corazón/herramientas) y
    #    qué novedades de su evolución le llegaron. Inyectado ANTES del
    #    sys_prompt → sobrevive al trim. ──
    try:
        from core.todo_yo import inyect_todo_yo
        _tuyo = inyect_todo_yo()
        if _tuyo:
            parts.append(_tuyo)
    except Exception:
        pass
    parts.append(sys_prompt)

    # ── RECUERDOS RELEVANTES: búsqueda semántica en la memoria total
    #    (vault + memory + knowledge) sobre lo último que dijo el usuario.
    #    Throttle: solo recalcula si pasó 45s y el tema cambió (hash distinto).
    #    Se inyecta ANTES del sys_prompt; degrada en silencio sin índice. ──
    try:
        import hashlib as _hl
        from core.rag_engine import recall_texto, _EMBED_FILE, _META_FILE
        _rec_q = _g(host, "_last_text_trigger", "") or ""
        _rec_h = _hl.md5(_rec_q.encode()).hexdigest()[:10]
        _rec_now = time.time()
        _last_h = _g(host, "_rag_last_hash", "")
        _last_t = _g(host, "_rag_last_time", 0.0)
        if (len(_rec_q) >= 15 and _rec_h != _last_h
                and (_rec_now - _last_t) >= 45
                and _EMBED_FILE.exists() and _META_FILE.exists()):
            _rec_block = recall_texto(_rec_q, 3)
            if _rec_block:
                parts.insert(-1, _rec_block)
            _set(host, "_rag_last_hash", _rec_h)
            _set(host, "_rag_last_time", _rec_now)
    except Exception:
        pass

    # ── ESTILO ACTIVO: la variante ganadora del A/B automático de prompts.
    #    Se recarga una vez por sesión (cache) para no leer disco por turno. ──
    try:
        from core.ab_automated import get_active_style
        if _g(host, "_active_style", None) is None:
            _set(host, "_active_style", get_active_style())
        _active_style = _g(host, "_active_style", None)
        if _active_style:
            parts.insert(-1, _active_style)
    except Exception:
        pass

    # ── VERIFICACIÓN: la evidencia REAL de las últimas tools + corrección
    #    si en el turno anterior Eris afirmó un éxito que no pasó. ──
    try:
        from core.truth_audit import evidence_block
        _ev = evidence_block()
        if _ev:
            parts.insert(-1, _ev)
    except Exception:
        pass

    # ── Guardrail anti-repetición: si su última respuesta repitió una
    #    muletilla/construcción reciente, se lo avisa ANTES de responder
    #    para que lo haga distinto. Máx 1 nudge cada ~2 turnos. ──
    try:
        from core.repetition_guard import recent_replies, block
        _recents = recent_replies()
        if _recents:
            _rb = block(_recents[-1])
            if _rb:
                _now_rg = time.time()
                if (_g(host, "_last_rep_nudge", 0.0) + 60.0) < _now_rg:
                    _set(host, "_last_rep_nudge", _now_rg)
                    parts.insert(-1, _rb)
    except Exception:
        pass

    # ── Smart trim: nunca cortar lo esencial (personalidad, relación,
    #    estilo, memoria, digest). Se recorta solo la cola del prompt base.
    #    30000 chars ≈ ~7.5K tokens. Gemini Live (native audio) deja de
    #    responder (timeout → runtime lo ve como 1011 y reconecta en loop)
    #    con system_instruction > ~40K. Verificado con probes: 20-30K OK,
    #    60K muerto. El prompt base completo (~136K) se recorta; las
    #    secciones críticas (identidad, motores 3D) están al inicio y
    #    sobreviven. ──
    MAX_SYSTEM_CHARS = 30000
    system_text = "\n".join(parts)
    if len(system_text) > MAX_SYSTEM_CHARS:
        _essential = "\n".join(parts[:-1])
        _budget = MAX_SYSTEM_CHARS - len(_essential) - 80
        if _budget > 2000:
            sys_prompt = sys_prompt[:_budget] + "\n[CONTEXTO TRUNCADO]"
            system_text = _essential + "\n" + sys_prompt
        else:
            system_text = system_text[:MAX_SYSTEM_CHARS] + "\n[CONTEXTO TRUNCADO]"
    return system_text


__all__ = ["build_system_prompt"]
