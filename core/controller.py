# -*- coding: utf-8 -*-
"""
core/controller.py — Lógica de negocio de ERIS separada de la UI.

Este módulo aloja la lógica de negocio de `ErisLive` que NO toca Qt ni la
sesión Gemini Live: ciclos cognitivo/autonomía, recordatorios proactivos,
voz resiliente y frases del observador. Recibe callbacks para log y
broadcast en lugar de alcanzar `self.ui` directamente, de modo que se puede
probar sin iniciar la interfaz gráfica ni una sesión Live.

Uso desde ErisLive::

    from core.controller import Controller
    self._controller = Controller(state=get_shared_context())
    ...
    self._controller.run_cognitive_cycle(self._ui_log)
"""

from __future__ import annotations

import json
import random
import threading
import time
from pathlib import Path
from typing import Callable, Optional

BASE = Path(__file__).resolve().parent.parent  # raíz del repositorio

LogCb = Callable[[str], None]
BroadcastCb = Callable[[str], None]


class Controller:
    """Lógica de negocio de ERIS sin depender de Qt ni de la sesión Live."""

    def __init__(self, state: Optional[object] = None) -> None:
        self.state = state
        self._is_speaking = False

    # ── Observador: frases naturales para eventos detectados ──────────────

    def observer_line(self, ev: dict, emotion_label: str = "") -> str:
        """Devuelve una frase natural (es-AR) para un evento observado, o
        cadena vacía si no hay frase aplicable."""
        t = ev.get("type", "")
        if t == "start_coding":
            proj = ev.get("project") or "algo"
            return random.choice([
                f"¿Y {proj}? Me gusta cuando te ponés a laburar. ¿En qué anda el proyecto?",
                f"Veo que arrancaste con {proj}. ¿Cómo viene?",
                f"Uh, ya estás muy en lo tuyo con {proj}... ¿te ayudo con algo?",
            ])
        if t == "long_coding":
            mins = ev.get("minutes", 0)
            return random.choice([
                f"Llevás como {mins} min seguidos metido en esto. ¿Tomás aire o seguís? Yo te banco igual.",
                f"Rato largo que estás en {ev.get('project', 'la máquina')}. ¿Necesitás un descanso?",
            ])
        if t == "app_switch":
            to = ev.get("to_proc") or ev.get("to_title") or ""
            if not to:
                return ""
            return random.choice([
                f"¿Cambiando de rumbo? Te vi sobre {to}. ¿Vamos por ahí?",
                f"Te salté que estás en {to}. ¿Qué estás tramando?",
            ])
        return ""

    # ── Voz resiliente ────────────────────────────────────────────────────

    def tts_backend_works(self, backend: str) -> bool:
        """True solo si el backend local sintetiza de verdad (no alcanza con
        que importe: edge puede dar 403 y quedar mudo). Corre en un hilo
        propio para ser seguro desde un contexto async."""
        import threading as _th

        _res = {"ok": False}

        def _job() -> None:
            try:
                import asyncio as _a
                from core.tts_engine import synthesize
                _pcm = _a.run(_a.wait_for(
                    synthesize("hola", backend=backend), timeout=8))
                _res["ok"] = bool(_pcm and len(_pcm) > 100)
            except Exception:
                _res["ok"] = False

        _t = _th.Thread(target=_job, daemon=True)
        _t.start()
        _t.join(timeout=10)
        return _res["ok"]

    def voice_resilient_fallback(
        self,
        log_cb: LogCb,
        remember_cb: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Auto-reparación de voz: si la cuota de TTS en nube se agota, Eris
        pasa SOLA a TTS local y lo persiste, para no quedarse muda.

        Blindaje: solo persiste un backend local que REALMENTE sintetice.
        Si ninguno funciona, NO cambia nada (quedarse en nube es mejor que
        quedar mudo para siempre).
        """
        import json as _j
        from pathlib import Path as _P

        _cfg_path = _P(__file__).resolve().parent.parent / "config" / "api_keys.json"
        _cur = "gemini"
        try:
            _all = _j.loads(_cfg_path.read_text(encoding="utf-8"))
            _cur = str(_all.get("tts_backend", "gemini")).lower()
        except Exception:
            _all = {}

        if _cur in ("kokoro", "pykokoro", "edge"):
            log_cb("SYS: Voz ya en modo local (resiliente).")
            return

        _new = None
        for _cand in ("sapi", "kokoro", "piper", "edge", "gtts"):
            if self.tts_backend_works(_cand):
                _new = _cand
                break

        if _new is None:
            # Ningún TTS local funcional: no persistimos un backend que dejaría
            # a Eris muda. Se queda en nube (se recupera sola cuando vuelva la
            # cuota).
            print("[ERIS] ⚠️ Cuota de voz agotada y sin TTS local funcional: sigo en nube.")
            log_cb("SYS: ⚠️ Cuota de voz en nube agotada y sin TTS local disponible; reintentaré en nube.")
            return

        _all["tts_backend"] = _new
        self._voice_resilient = True
        try:
            _cfg_path.write_text(_j.dumps(_all, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[ERIS] 💾 Cuota de voz agotada → tts_backend={_new} (persistido).")
            log_cb(f"SYS: 💸 Cuota de voz en nube agotada. Pasé a TTS local ({_new}). Mi voz sigue conmigo.")
        except Exception as _e:
            print(f"[ERIS] Voice fallback persist error: {_e}")
            return

        if remember_cb:
            try:
                remember_cb(
                    "Hoy agoté la cuota de voz en nube. Pasé sola a TTS local ("
                    + _new + ") para seguir hablando. Puedo volver a nube si me lo piden."
                )
            except Exception:
                pass

    # ── Ciclo cognitivo ──────────────────────────────────────────────────

    def _safe_log(self, log_cb: LogCb, msg: str) -> None:
        """Log con manejo de encoding para emojis."""
        try:
            log_cb(msg)
        except UnicodeEncodeError:
            import re as _re
            clean = _re.sub(r"[^\x00-\x7F]+", "", msg)
            log_cb(clean)

    def run_cognitive_cycle(self, log_cb: LogCb, context: str = "proactive") -> None:
        """Ejecuta el ciclo cognitivo completo en background."""
        self._safe_log(log_cb, "[COGNITIVE] Iniciando ciclo cognitivo")

        # 1. Neural Bridge: status + reflect
        try:
            from core.neural_bridge import neural_bridge_tool
            neural_bridge_tool({"action": "status"})
            self._safe_log(log_cb, "[COGNITIVE] Neural Bridge OK")
        except Exception as _nb:
            self._safe_log(log_cb, f"[COGNITIVE] Neural Bridge error: {str(_nb)[:60]}")

        # 2. Emotional RL: reward o status
        try:
            from core.emotional_rl import emotional_rl_tool
            if context == "interaction":
                emotional_rl_tool({
                    "action": "reward",
                    "reward_type": "helped_user",
                    "reason": "Interaccion completada exitosamente",
                })
            else:
                emotional_rl_tool({"action": "status"})
            self._safe_log(log_cb, "[COGNITIVE] Emotional RL OK")
        except Exception as _erl:
            self._safe_log(log_cb, f"[COGNITIVE] Emotional RL error: {str(_erl)[:60]}")

        # 3. NeuroSpheres: auto-crear nodos diversos basado en actividad
        try:
            import json as _cjson
            from core.neuro_spheres import neuro_spheres
            neuro_spheres({"action": "status"})
            self._safe_log(log_cb, "[COGNITIVE] NeuroSpheres OK")

            _ns_created = 0

            # --- Fuente 1: Episodios (aprendizaje) ---
            _ep_file = BASE / "memory" / "episodic.json"
            if _ep_file.exists():
                _episodes = _cjson.loads(_ep_file.read_text(encoding="utf-8"))
                if _episodes:
                    last_ep = _episodes[-1]
                    learning = last_ep.get("learning", "")
                    event = last_ep.get("event", "")
                    if learning and len(learning) > 10:
                        neuro_spheres({
                            "action": "add",
                            "sphere": "aprendizaje",
                            "type": "aprendizaje",
                            "title": learning[:100],
                            "content": f"Aprendi: {learning}. Contexto: {event[:200]}",
                            "connections": [],
                            "force": 5,
                        })
                        _ns_created += 1

            # --- Fuente 2: Working memory (tareas activas) ---
            _wm_file = BASE / "memory" / "working.json"
            if _wm_file.exists():
                _wm = _cjson.loads(_wm_file.read_text(encoding="utf-8"))
                if isinstance(_wm, dict):
                    _tasks = _wm.get("active_tasks", _wm.get("tasks", []))
                    if isinstance(_tasks, list):
                        for task in _tasks[-2:]:
                            if isinstance(task, dict):
                                _t_title = task.get("title", task.get("description", ""))
                                _t_desc = task.get("details", task.get("status", ""))
                                if _t_title and len(_t_title) > 5:
                                    neuro_spheres({
                                        "action": "add",
                                        "sphere": "habilidad",
                                        "type": "habilidad",
                                        "title": f"Tarea activa: {_t_title[:80]}",
                                        "content": f"Estado: {_t_desc}. Tarea: {_t_title}",
                                        "connections": [],
                                        "force": 4,
                                    })
                                    _ns_created += 1

            # --- Fuente 3: Semantic memory (conocimiento acumulado) ---
            _sm_file = BASE / "memory" / "semantic.json"
            if _sm_file.exists():
                _sm = _cjson.loads(_sm_file.read_text(encoding="utf-8"))
                if isinstance(_sm, dict):
                    _facts = _sm.get("facts", _sm.get("knowledge", []))
                    if isinstance(_facts, list):
                        for fact in _facts[-2:]:
                            if isinstance(fact, dict):
                                _f_topic = fact.get("topic", fact.get("subject", ""))
                                _f_content = fact.get("content", fact.get("detail", ""))
                                if _f_topic and len(str(_f_content)) > 5:
                                    neuro_spheres({
                                        "action": "add",
                                        "sphere": "memoria",
                                        "type": "memoria",
                                        "title": f"Conocimiento: {_f_topic[:80]}",
                                        "content": f"Tema: {_f_topic}. Info: {str(_f_content)[:300]}",
                                        "connections": [],
                                        "force": 4,
                                    })
                                    _ns_created += 1

            if _ns_created > 0:
                self._safe_log(log_cb, f"[COGNITIVE] NeuroSpheres: {_ns_created} nodo(s) auto-creado(s)")
        except Exception as _ns:
            self._safe_log(log_cb, f"[COGNITIVE] NeuroSpheres error: {str(_ns)[:60]}")

        # 4. World Simulation: status
        try:
            from core.world_simulation import world_simulation_tool
            world_simulation_tool({"action": "status"})
            self._safe_log(log_cb, "[COGNITIVE] World Sim OK")
        except Exception as _ws:
            self._safe_log(log_cb, f"[COGNITIVE] World Sim error: {str(_ws)[:60]}")

        # 5. Cognitive Module: meta_cognition para auto-reflexionar
        try:
            from core.cognitive_modules import meta_cognition
            meta_cognition({
                "action": "reflect",
                "thought": "Ciclo cognitivo automatico: verificando estado de sistemas",
            })
            self._safe_log(log_cb, "[COGNITIVE] Meta-Cognition OK")
        except Exception as _mc:
            self._safe_log(log_cb, f"[COGNITIVE] Meta-Cognition error: {str(_mc)[:60]}")

        # 6. IDE Monitor: detectar si hay IDE abierto y leer código
        try:
            import json as _ij
            from actions.ide_integration import ide_integration
            _detect = _ij.loads(ide_integration({"action": "detect"}))
            if _detect.get("detected"):
                _ide = _detect.get("ide_friendly", "?")
                _file = _detect.get("file_name", "?")
                _lang = _detect.get("language", "?")
                self._safe_log(log_cb, f"[IDE] Detectado: {_ide} ({_lang}) - {_file}")
                _read = _ij.loads(ide_integration({"action": "read"}))
                _code = _read.get("code", "")
                if _code:
                    _lines = _code.split("\n")
                    self._safe_log(log_cb, f"[IDE] {len(_lines)} lineas de codigo leidas")
        except Exception as _ide_err:
            self._safe_log(log_cb, f"[IDE] Monitor error: {str(_ide_err)[:60]}")

    # ── Ciclo de autonomía ───────────────────────────────────────────────

    def run_autonomy_cycle(self, log_cb: LogCb) -> None:
        """Ejecuta el ciclo de autonomía completo en background."""
        self._safe_log(log_cb, "[AUTONOMY] Iniciando ciclo de autonomía")

        try:
            import json as _cjson
            from core.autonomy import autonomy_tool

            result = autonomy_tool({"action": "full_cycle"})
            data = _cjson.loads(result)
            results = data.get("cycle_results", [])

            for r in results:
                self._safe_log(log_cb, f"[AUTONOMY] {r}")
        except Exception as _au:
            self._safe_log(log_cb, f"[AUTONOMY] Error: {str(_au)[:60]}")

        # 2. Goal Setting: auto-generar metas
        try:
            import json as _cjson
            from core.goal_setting import goal_setting_tool

            result = goal_setting_tool({"action": "auto_generate"})
            data = _cjson.loads(result)
            new = data.get("new_goals", 0)
            if new > 0:
                self._safe_log(log_cb, f"[GOALS] {new} metas auto-generadas")
        except Exception as _gs:
            self._safe_log(log_cb, f"[GOALS] Error: {str(_gs)[:60]}")

        # 3. Learning Pipeline: aprender 1 topic
        try:
            import json as _cjson
            from core.learning_pipeline import learning_pipeline_tool

            result = learning_pipeline_tool({"action": "auto_learn"})
            data = _cjson.loads(result)
            if data.get("status") == "aprendido":
                self._safe_log(log_cb, f"[LEARNING] Topic: {data.get('topic', '')}")
        except Exception as _lp:
            self._safe_log(log_cb, f"[LEARNING] Error: {str(_lp)[:60]}")

        # 4. Self-Modify: analizar código
        try:
            import json as _cjson
            from core.self_modify import self_modify_tool

            result = self_modify_tool({"action": "self_improve"})
            data = _cjson.loads(result)
            issues = data.get("total_issues", 0)
            if issues > 0:
                self._safe_log(log_cb, (
                    f"[SELF-MODIFY] {issues} issues encontrados en "
                    f"{data.get('files_analyzed', 0)} archivos"
                ))
        except Exception as _sm:
            self._safe_log(log_cb, f"[SELF-MODIFY] Error: {str(_sm)[:60]}")

        # 5. Resource Manager: cleanup si es necesario
        try:
            import json as _cjson
            from core.resource_manager import resource_manager_tool

            result = resource_manager_tool({"action": "disk_check"})
            data = _cjson.loads(result)
            for p in data.get("disk", {}).get("partitions", []):
                if p.get("low"):
                    self._safe_log(log_cb, f"[RESOURCES] ALERTA: poco espacio en {p.get('drive')}")
        except Exception as _rm:
            self._safe_log(log_cb, f"[RESOURCES] Error: {str(_rm)[:60]}")

    # ── Recordatorios proactivos ─────────────────────────────────────────

    def proactive_reminders(self, log_cb: LogCb, broadcast_cb: Optional[BroadcastCb] = None) -> None:
        """Recordatorios proactivos al móvil: agenda del día y eventos próximos."""
        import json as _json
        from datetime import datetime as _dt, timedelta as _td
        from pathlib import Path as _P

        _DATA = BASE / "data"
        _events_file = _DATA / "calendar_events.json"
        _state_file = _DATA / "eris_proactive_state.json"

        state = {}
        if _state_file.exists():
            try:
                state = _json.loads(_state_file.read_text(encoding="utf-8"))
            except Exception:
                state = {}
        if not isinstance(state, dict):
            state = {}
        if not state.get("enabled", True):
            return

        now = _dt.now()
        notified = set(state.get("reminded_events", []))
        messages = []

        events = []
        if _events_file.exists():
            try:
                events = _json.loads(_events_file.read_text(encoding="utf-8"))
            except Exception:
                events = []

        current_ids = set()
        for e in events:
            eid = e.get("id", "")
            if not eid:
                continue
            current_ids.add(eid)
            if eid in notified:
                continue
            try:
                start = _dt.fromisoformat(str(e.get("start", "")))
            except Exception:
                continue
            rem = int(e.get("reminder_minutes", 15))
            if start - _td(minutes=rem) <= now <= start:
                mins = int((start - now).total_seconds() / 60) + 1
                messages.append(
                    "Recordatorio: '{}' empieza en {} min".format(
                        e.get("title", "evento"), mins)
                )
                notified.add(eid)

        if not messages:
            return

        notified = notified & current_ids
        state["reminded_events"] = sorted(notified)

        for msg in messages:
            if broadcast_cb:
                try:
                    broadcast_cb(msg)
                except Exception:
                    pass
            try:
                log_cb("[PROACTIVE] {}".format(msg))
            except Exception:
                pass

        try:
            _state_file.parent.mkdir(parents=True, exist_ok=True)
            _state_file.write_text(
                _json.dumps(state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as _pe:
            log_cb(f"[PROACTIVE] Error: {str(_pe)[:80]}")
