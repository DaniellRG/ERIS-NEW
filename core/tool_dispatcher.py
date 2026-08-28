"""
core/tool_dispatcher.py — Refactored tool dispatcher.
Uses tool_registry.get_tool() as primary dispatch. Only special-case tools get manual handling.
"""
import asyncio
import importlib
import inspect
import json
import os
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from google.genai import types

from core.action_imports import _eg_on_tool_result
from core.logging_setup import BASE_DIR
from core.tool_registry import get_tool
from core.resilient import get_manager, generate_task_id

TOOL_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="eris-tool")

# ── Throttle de auto-aprendizaje: evita registrar cada fallo como lección ──
_LEARN_LOCK = threading.Lock()
_LEARN_LOG: dict[str, float] = {}      # "tool:error_prefix" -> last learn timestamp
_LEARN_WINDOW = 15 * 60                 # una leccion por tool+error cada 15 min


def _should_learn(name: str, result: str) -> bool:
    """Devuelve True solo si este fallo no se aprendio recientemente."""
    sig = "{}:{}".format(name, str(result)[:80])
    now = time.time()
    with _LEARN_LOCK:
        last = _LEARN_LOG.get(sig, 0.0)
        if now - last < _LEARN_WINDOW:
            return False
        _LEARN_LOG[sig] = now
        if len(_LEARN_LOG) > 500:
            _LEARN_LOG.clear()
        return True

# ── Tools that need special handling (not just parameters=, player=) ──
_SPECIAL_TOOLS = frozenset({
    "shutdown_eris", "save_memory", "sleep_mode", "eris_ui_control",
    "agent_task", "db_memory", "db_knowledge", "db_tasks",
    "plugin_manage", "openrouter_agent", "computer_settings",
    "screen_recorder", "translator", "meeting_transcriber",
    "network_monitor", "quick_actions", "pdf_editor", "context_menu",
    "sms", "dashboard", "emotional_state", "ask_opencode",
    "system_reader", "episodic_log", "conversation_search",
    "curiosity_joke", "curiosity_fact", "curiosity_fun", "curiosity_trending",
})


class ToolDispatcher:
    """Dispatches tool calls from the Gemini live session to the appropriate action."""

    def __init__(self, eris):
        self._eris = eris

    @property
    def ui(self):
        return self._eris.ui

    async def execute(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})
        task_id = generate_task_id(name, args)
        resilient = get_manager()

        print(f"[ERIS] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        # ── Command Deck: registrar intent que se va a ejecutar ──
        try:
            from core.command_deck import log_intent
            log_intent(name, args, status="running")
        except Exception:
            pass

        # ── Terminal panel: log tool start ──
        try:
            from core.ui_panels import get_terminal_panel
            _tp = get_terminal_panel()
            if _tp:
                _tp.log_tool_start(name, args)
        except Exception:
            pass

        # ── Register task for resilience (survives crashes) ──
        resilient.register_task(task_id, name, args)

        # ── Permission gate: check for dangerous operations ──
        try:
            from core.permission_gate import get_permission_gate
            gate = get_permission_gate()
            if hasattr(self.ui, 'ask'):
                gate.set_ui_callback(self.ui.ask)
            perm = gate.check(name, args)
            if not perm.allowed:
                resilient.task_completed(task_id, f"Permiso denegado: {perm.reason}")
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": f"Permiso denegado por el usuario para '{name}': {perm.reason}"}
                )
        except Exception:
            pass

        # ── Special: shutdown ──
        if name == "shutdown_eris":
            resilient.task_completed(task_id, "Apagando ERIS.")
            self.ui.write_log("SYS: Apagando ERIS...")
            my_pid = os.getpid()
            import subprocess
            cmd = f'start /b timeout /t 8 /nobreak >nul & taskkill /F /PID {my_pid}'
            subprocess.Popen(["cmd", "/c", cmd], creationflags=0x08000000 | 0x00000008)
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Apagando ERIS. ¡Hasta luego, señor! Me apago ahora."}
            )

        # ── Special: save_memory ──
        if name == "save_memory":
            category = args.get("category", "notes")
            key = args.get("key", "")
            value = args.get("value", "")
            if key and value:
                from memory.memory_manager import update_memory
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Memory saved."}
            )

        # ── Special: sleep_mode ──
        if name == "sleep_mode":
            self._eris.is_sleeping = True
            self.ui.write_log("SYS: Modo suspenso. Te escucho. Di 'Eris' para despertarme.")
            self.ui.set_state("MUTED")
            try:
                def _notify():
                    if hasattr(self.ui, 'tray_icon') and self.ui.tray_icon.isVisible():
                        self.ui.tray_icon.showMessage("ERIS", "Estoy en segundo plano. Di Eris y despierto.", self.ui.tray_icon.icon(), 3000)
                QTimer.singleShot(0, _notify)
            except: pass
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Modo suspenso activado. Di 'Eris' para despertarme."}
            )

        loop = asyncio.get_event_loop()
        result = "Done."

        try:
            # ── Special: eris_ui_control ──
            if name == "eris_ui_control":
                result = self._handle_ui_control(args)

            # ── Special: show_expression (la cara de ERIS) ──
            elif name == "show_expression":
                result = self._handle_show_expression(args)

            # ── Special: agent_task ──
            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self._eris.speak)
                result = f"Task started (ID: {task_id})."

            # ── Special: db_memory ──
            elif name == "db_memory":
                result = await self._handle_db_memory(args, loop)

            # ── Special: db_knowledge ──
            elif name == "db_knowledge":
                result = await self._handle_db_knowledge(args, loop)

            # ── Special: db_tasks ──
            elif name == "db_tasks":
                result = await self._handle_db_tasks(args, loop)

            # ── Special: plugin_manage ──
            elif name == "plugin_manage":
                result = await self._handle_plugin_manage(args, loop)

            # ── Special: openrouter_agent ──
            elif name == "openrouter_agent":
                from core.action_imports import openrouter_agent
                if openrouter_agent:
                    self.ui.write_log("🤖 Delegando tarea a OpenRouter...")
                    r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: openrouter_agent(
                        query=args.get("query", ""), model=args.get("model", "google/gemini-2.5-flash")
                    ))
                    result = r or "Error al procesar con OpenRouter."
                else:
                    result = "Módulo openrouter_agent no encontrado."

            # ── Special: emotional_state ──
            elif name == "emotional_state":
                from core.emotional_state import emotional_state_tool
                r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: emotional_state_tool(args) if emotional_state_tool else "emotional_state no disponible")
                result = r or "Estado emocional consultado."

            # ── Special: ask_opencode ──
            elif name == "ask_opencode":
                from core.action_imports import opencode_task
                r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: opencode_task(
                    args.get("question", ""), str(BASE_DIR), None, self.ui
                ) if opencode_task else "opencode no disponible. Instala opencode CLI.")
                result = r or "Consulta enviada a opencode."

            # ── Special: system_reader ──
            elif name == "system_reader":
                from core.action_imports import system_reader
                action = args.get("action", "status")
                detail = args.get("detail", "normal")
                r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: system_reader(action, detail) if system_reader else "system_reader no disponible")
                result = r or "Sistema leido."

            # ── Special: episodic_log ──
            elif name == "episodic_log":
                from core.action_imports import episodic_add, episodic_count
                r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: episodic_add(
                    args.get("event", ""), args.get("category", "general"),
                    args.get("context", ""), args.get("importance", 0.5)
                ) if episodic_add else None)
                result = f"Evento registrado (total: {episodic_count() if episodic_count else '?'})" if r else "episodic_log no disponible"

            # ── Special: conversation_search ──
            elif name == "conversation_search":
                from core.action_imports import convo_search, convo_recent
                act = args.get("action", "recent")
                if act == "search" and convo_search:
                    r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: convo_search(args.get("query", ""), args.get("limit", 10)))
                    result = json.dumps(r, ensure_ascii=False) if r else "No encontre nada."
                elif convo_recent:
                    r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: convo_recent(args.get("limit", 10)))
                    result = json.dumps(r, ensure_ascii=False) if r else "No hay conversaciones aun."
                else:
                    result = "conversation_search no disponible"

            # ── Special: curiosity_* ──
            elif name in ("curiosity_joke", "curiosity_fact", "curiosity_fun", "curiosity_trending"):
                from core.action_imports import curiosity_tell_joke, curiosity_tell_fact, curiosity_suggest_fun, curiosity_trending as ct
                if name == "curiosity_joke":
                    r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: curiosity_tell_joke(player=self.ui) if curiosity_tell_joke else "jajaja")
                elif name == "curiosity_fact":
                    r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: curiosity_tell_fact(args.get("topic"), player=self.ui) if curiosity_tell_fact else "Dato curioso.")
                elif name == "curiosity_fun":
                    r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: curiosity_suggest_fun(player=self.ui) if curiosity_suggest_fun else "Buscar videos graciosos")
                else:
                    r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: ct(player=self.ui) if ct else "tendencias")
                result = r

            # ── Special: computer_settings (volume + window control) ──
            elif name == "computer_settings":
                result = await self._handle_computer_settings(args, loop)

            # ── Special: screen_recorder ──
            elif name == "screen_recorder":
                result = await self._handle_screen_recorder(args, loop)

            # ── Special: translator ──
            elif name == "translator":
                result = await self._handle_translator(args, loop)

            # ── Special: meeting_transcriber ──
            elif name == "meeting_transcriber":
                result = await self._handle_meeting_transcriber(args, loop)

            # ── Special: network_monitor ──
            elif name == "network_monitor":
                result = await self._handle_network_monitor(args, loop)

            # ── Special: quick_actions ──
            elif name == "quick_actions":
                result = await self._handle_quick_actions(args, loop)

            # ── Special: pdf_editor ──
            elif name == "pdf_editor":
                result = await self._handle_pdf_editor(args, loop)

            # ── Special: context_menu ──
            elif name == "context_menu":
                result = await self._handle_context_menu(args, loop)

            # ── Special: sms ──
            elif name == "sms":
                result = await self._handle_sms(args, loop)

            # ── Special: dashboard ──
            elif name == "dashboard":
                result = await self._handle_dashboard(args, loop)

            # ── Special: context7 (async, needs await + action as positional arg) ──
            elif name == "context7":
                from actions.context7 import handle_context7
                action = args.get("action", "search")
                r = await handle_context7(action, **{k: v for k, v in args.items() if k != "action"})
                result = r or "Context7 ejecutado."

            # ── Special: ide_integration ──
            elif name == "ide_integration":
                from actions.ide_integration import ide_integration as _ide_tool
                r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: _ide_tool(args))
                result = r

            # ── Special: code_assistant ──
            elif name == "code_assistant":
                from actions.code_assistant import full_scan, format_report
                r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: full_scan())
                result = format_report(r) if isinstance(r, dict) else str(r)

            # ── Generic dispatch via tool_registry ──
            else:
                result = await self._generic_dispatch(name, args, loop)

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self._eris.speak_error(name, e)
            # ── Console.log: register error ──
            try:
                from core.console_log import log_error, log_tool_call
                tb_str = traceback.format_exc()
                log_error("tool_dispatcher", str(e), tb_str, {"tool": name, "args": str(args)[:300]})
                log_tool_call(name, args, 0, False, str(e)[:500])
            except Exception:
                pass
            # ── Resilient: queue for retry on failure ──
            resilient.task_failed(task_id, str(e)[:200])
            # ── Error pattern DB: registrar error conocido ──
            try:
                from core.error_pattern_db import record_error
                record_error(str(e)[:500], tool=name, context=str(args)[:200])
            except Exception:
                pass

        # ── Post-dispatch hooks ──
        try:
            from core.action_imports import record_action, db_tool_log, react_to_success, react_to_failure
        except ImportError:
            record_action = db_tool_log = react_to_success = react_to_failure = None

        if record_action:
            threading.Thread(target=lambda: record_action(name, args), daemon=True).start()

        if db_tool_log:
            ok = not str(result).lower().startswith("error")
            threading.Thread(target=lambda: db_tool_log(
                name, args, ok, str(result)[:200], 0, self._eris._session_id
            ), daemon=True).start()

        if react_to_success and react_to_failure:
            ok = not str(result).lower().startswith("error")
            threading.Thread(target=lambda: react_to_success(name) if ok else react_to_failure(str(result)[:100]), daemon=True).start()

        if _eg_on_tool_result:
            ok = not str(result).lower().startswith("error")
            threading.Thread(target=lambda: _eg_on_tool_result(None, name, ok), daemon=True).start()

        # ── Intent classifier + metrics: registrar intención y uso ──
        try:
            from core.intent_classifier import classify_intent
            intent = classify_intent(str(result)[:200])
        except Exception:
            intent = None
        try:
            from core.metrics_dashboard import record_tool_usage as _mu
            _mu(name, not str(result).startswith("ERROR"), 0)
        except Exception:
            pass
        try:
            from core.capability_self_assessment import record_tool_usage as _ca
            _ca(name, not str(result).startswith("ERROR"), 0)
        except Exception:
            pass
        try:
            from core.proactive_suggestions import record_user_pattern
            record_user_pattern(name, "tool:%s" % name)
        except Exception:
            pass
        # ── Smart file organizer: track file access ──
        try:
            from core.smart_file_organizer import record_file_access
            fp = args.get("path") or args.get("file_path") or args.get("filename") or ""
            if fp and isinstance(fp, str) and "/" in fp or "\\" in fp:
                threading.Thread(target=lambda: record_file_access(fp), daemon=True).start()
        except Exception:
            pass
        # ── Backup prioritizer: track file modifications ──
        try:
            if name in ("file_write", "file_edit") and args.get("path"):
                from core.backup_prioritizer import mark_backed_up
        except Exception:
            pass

        # ── Training pipeline: track tool success/failure ──
        try:
            from core.training_pipeline import evaluate_tool_usage, learn_from_failure
            _ok = not str(result).lower().startswith("error")
            _dur = 0.0
            if not _ok:
                if _should_learn(name, str(result)):
                    threading.Thread(target=lambda: evaluate_tool_usage(name, args, str(result)[:200], _dur), daemon=True).start()
                    threading.Thread(target=lambda: learn_from_failure(name, str(result)[:200], "Auto-registered from tool error"), daemon=True).start()
        except Exception:
            pass

        # ── Self-learning: learn from mistakes ──
        try:
            _ok = not str(result).lower().startswith("error")
            if not _ok and _should_learn(name, str(result)):
                from actions.self_learning import learn_from_mistake
                threading.Thread(target=lambda: learn_from_mistake({"error": f"{name}: {str(result)[:200]}", "lesson": "Revisar parametros o conexion"}), daemon=True).start()
        except Exception:
            pass

        # ── NeuroSpheres: crear nodos COMPLETOS con errores, soluciones, y actividad ──
        try:
            from core.neuro_spheres import neuro_spheres as _ns_tool
            _ns_result = str(result)[:1000]
            _ns_success = not _ns_result.lower().startswith("error")

            # --- NODO DE ACTIVIDAD (siempre que la tool funcione) ---
            _NS_MAP = {
                "ide_integration": ("codigo", "habilidad"),
                "code_assistant": ("codigo", "habilidad"),
                "code_helper": ("codigo", "habilidad"),
                "terminal_agent": ("ejecucion", "habilidad"),
                "git_control": ("codigo", "habilidad"),
                "web_search": ("investigacion", "aprendizaje"),
                "browser_navigate": ("investigacion", "aprendizaje"),
                "file_read": ("codigo", "memoria"),
                "file_write": ("codigo", "habilidad"),
                "file_edit": ("codigo", "habilidad"),
                "file_manager": ("codigo", "memoria"),
                "test_runner": ("codigo", "habilidad"),
                "gmail_control": ("aprendizaje", "habilidad"),
                "google_calendar": ("aprendizaje", "habilidad"),
                "youtube_video": ("investigacion", "aprendizaje"),
                "memory_store": ("memoria", "memoria"),
                "memory_retrieve": ("memoria", "memoria"),
            }

            if _ns_success and name in _NS_MAP:
                _sphere, _type = _NS_MAP[name]
                _title = f"{name}: {_ns_result[:80]}"
                _content = f"Tool: {name}. Resultado: {_ns_result[:300]}"
                threading.Thread(target=lambda: _ns_tool({
                    "action": "add",
                    "sphere": _sphere,
                    "type": _type,
                    "title": _title[:100],
                    "content": _content,
                    "connections": [],
                    "force": 3
                }), daemon=True).start()

            # --- NODO DE ERROR (si la tool fallo) ---
            if not _ns_success:
                _error_text = _ns_result[:500]
                # Clasificar tipo de error
                _error_type = "desconocido"
                if "syntax" in _error_text.lower() or "parse" in _error_text.lower():
                    _error_type = "sintaxis"
                elif "null" in _error_text.lower() or "reference" in _error_text.lower():
                    _error_type = "null_reference"
                elif "timeout" in _error_text.lower():
                    _error_type = "timeout"
                elif "connection" in _error_text.lower() or "connect" in _error_text.lower():
                    _error_type = "conexion"
                elif "permission" in _error_text.lower() or "access" in _error_text.lower():
                    _error_type = "permisos"
                elif "not found" in _error_text.lower() or "no such" in _error_text.lower():
                    _error_type = "no_encontrado"
                elif "import" in _error_text.lower() or "module" in _error_text.lower():
                    _error_type = "importacion"
                elif "type" in _error_text.lower() or "argument" in _error_text.lower():
                    _error_type = "tipos"

                _error_content = (
                    f"ERROR en tool '{name}':\n"
                    f"Tipo: {_error_type}\n"
                    f"Error: {_error_text}\n"
                    f"Parametros: {str(args)[:200]}\n"
                    f"Que busco para solucionar: buscar documentacion, stackoverflow, "
                    f"revisar parametros, verificar conexion, revisar sintaxis"
                )

                threading.Thread(target=lambda: _ns_tool({
                    "action": "add",
                    "sphere": "error",
                    "type": "error",
                    "title": f"Error {name}: {_error_type}",
                    "content": _error_content,
                    "connections": [],
                    "force": 4
                }), daemon=True).start()

                # --- NODO DE DIAGNOSTICO (que busco para resolver) ---
                _search_queries = []
                if _error_type == "sintaxis":
                    _search_queries = [f"{name} syntax error", f"corregir error sintaxis {name}"]
                elif _error_type == "null_reference":
                    _search_queries = [f"null reference exception {name}", "como manejar null en csharp"]
                elif _error_type == "timeout":
                    _search_queries = [f"{name} timeout solucion", "aumentar timeout api"]
                elif _error_type == "conexion":
                    _search_queries = [f"{name} connection error", "verificar conexion internet"]
                elif _error_type == "permisos":
                    _search_queries = [f"{name} permission denied", "ejecutar como administrador"]
                elif _error_type == "no_encontrado":
                    _search_queries = [f"{name} file not found", "verificar ruta archivo"]
                elif _error_type == "importacion":
                    _search_queries = [f"{name} import error", "instalar modulo faltante"]
                elif _error_type == "tipos":
                    _search_queries = [f"{name} type error", "verificar tipos de datos"]
                else:
                    _search_queries = [f"{name} error solution", f"como resolver {name}"]

                _diag_content = (
                    f"DIAGNOSTICO del error en '{name}':\n"
                    f"Tipo de error: {_error_type}\n"
                    f"Que busque para resolver: {', '.join(_search_queries)}\n"
                    f"Soluciones posibles:\n"
                    f"1. Revisar documentacion de {name}\n"
                    f"2. Buscar en stackoverflow\n"
                    f"3. Verificar parametros de entrada\n"
                    f"4. Revisar logs del sistema\n"
                    f"5. Probar con parametros diferentes\n"
                    f"Error original: {_error_text[:200]}"
                )

                threading.Thread(target=lambda: _ns_tool({
                    "action": "add",
                    "sphere": "diagnostico",
                    "type": "diagnostico",
                    "title": f"Diagnostico: {name} - {_error_type}",
                    "content": _diag_content,
                    "connections": [],
                    "force": 4
                }), daemon=True).start()

            # --- NODO DE SOLUCION (si una tool de edicion funciono despues de un error) ---
            if _ns_success and name in ("ide_integration", "code_helper", "file_edit", "file_write"):
                _sol_content = (
                    f"SOLUCION aplicada con '{name}':\n"
                    f"Resultado: {_ns_result[:300]}\n"
                    f"Que hice: Edite/cree archivo exitosamente\n"
                    f"Que funciono: La edicion se aplico correctamente\n"
                    f"Para recordar: Esta solucion funciono para este tipo de problema"
                )
                threading.Thread(target=lambda: _ns_tool({
                    "action": "add",
                    "sphere": "solucion",
                    "type": "solucion",
                    "title": f"Solucion: {name} exitoso",
                    "content": _sol_content,
                    "connections": [],
                    "force": 3
                }), daemon=True).start()

        except Exception:
            pass

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[ERIS] 📤 {name} → {str(result)[:80]}")

        # ── Command Deck: marcar intent como terminado ──
        try:
            from core.command_deck import log_intent
            _ok = not str(result).lower().startswith("error")
            log_intent(name, args, status=("done" if _ok else "error"),
                       result=str(result)[:120])
        except Exception:
            pass

        # ── Núcleo emocional sentiente: éxito/fracaso alimentan el ánimo ──
        try:
            from core.emotional_core import appraise_success, appraise_failure
            if _ok:
                appraise_success(name)
            else:
                appraise_failure(name)
        except Exception:
            pass

        # ── Terminal panel: log tool result ──
        try:
            from core.ui_panels import get_terminal_panel
            _tp = get_terminal_panel()
            if _tp:
                _ok = not str(result).lower().startswith("error")
                _tp.log_tool_result(name, str(result), ok=_ok)
        except Exception:
            pass

        # ── Cap response size to prevent Gemini 1007 crash ──
        result_str = str(result)
        _MAX_RESPONSE = 3500
        if len(result_str) > _MAX_RESPONSE:
            result_str = result_str[:_MAX_RESPONSE] + "\n\n[Respuesta truncada — {} chars totales]".format(len(str(result)))

        # ── Resilient: mark task as completed ──
        resilient.task_completed(task_id, result_str)

        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result_str}
        )

    # ── Generic dispatch: tool_registry.get_tool() ──
    async def _generic_dispatch(self, name, args, loop):
        _TOOL_TIMEOUT = 60.0
        func = get_tool(name)
        if func is not None:
            try:
                sig = inspect.signature(func)
                kwargs = {"parameters": args, "player": self.ui}
                if "speak" in sig.parameters:
                    kwargs["speak"] = self._eris.speak
                try:
                    fut = loop.run_in_executor(TOOL_EXECUTOR, lambda: func(**kwargs))
                    r = await asyncio.wait_for(fut, _TOOL_TIMEOUT)
                    return r or f"Herramienta {name} ejecutada."
                except asyncio.TimeoutError:
                    return f"Herramienta {name} excedió el timeout de {_TOOL_TIMEOUT}s (operación pesada abortada)."
            except Exception as e:
                return f"Error en {name}: {e}"

        # Fallback: dynamic import from actions.*
        try:
            module = importlib.import_module(f"actions.{name}")
            func = getattr(module, name, None)
            if func is None:
                # Try common function name patterns
                for attr_name in dir(module):
                    if callable(getattr(module, attr_name)) and not attr_name.startswith("_"):
                        func = getattr(module, attr_name)
                        break
            if func:
                sig = inspect.signature(func)
                kwargs = {"parameters": args, "player": self.ui}
                if "speak" in sig.parameters:
                    kwargs["speak"] = self._eris.speak
                try:
                    fut = loop.run_in_executor(TOOL_EXECUTOR, lambda: func(**kwargs))
                    r = await asyncio.wait_for(fut, _TOOL_TIMEOUT)
                    return r or f"Herramienta {name} ejecutada."
                except asyncio.TimeoutError:
                    return f"Herramienta {name} excedió el timeout de {_TOOL_TIMEOUT}s (operación pesada abortada)."
        except Exception as dyn_e:
            pass

        return f"Unknown tool: {name}. No se encontró en tool_registry ni en actions."

    # ── Special handlers ──

    def _handle_show_expression(self, args):
        expr = (args.get("expression") or "").strip().lower()
        text = (args.get("text") or "").strip()
        try:
            mode = self.ui.visual_mode()
        except Exception:
            mode = "face"
        try:
            if hasattr(self.ui, "show_expression"):
                self.ui.show_expression(expr, text)
        except Exception as e:
            return f"No pude mostrar la expresión: {e}"
        if mode == "face":
            return f"Listo: mostré '{expr}' en mi cara. {text}".strip()
        return f"Ahora estoy en forma de orbe de partículas; mi expresión se refleja en la energía del orbe. {text}".strip()

    def _handle_ui_control(self, args):
        action_ui = args.get("action", "").lower()
        widget_name = args.get("widget", "").lower()

        if action_ui == "minimize":
            try:
                if hasattr(self.ui, "_win") and hasattr(self.ui._win, "showMinimized"):
                    QTimer.singleShot(0, self.ui._win.showMinimized)
                elif hasattr(self.ui, "root") and hasattr(self.ui.root, "iconify"):
                    self.ui.root.after(0, self.ui.root.iconify)
                return "Interfaz de usuario minimizada."
            except Exception as e:
                return f"Error al minimizar: {e}"

        elif action_ui == "restore":
            try:
                if hasattr(self.ui, "_win") and hasattr(self.ui._win, "showNormal"):
                    QTimer.singleShot(0, self.ui._win.showNormal)
                    QTimer.singleShot(0, self.ui._win.activateWindow)
                elif hasattr(self.ui, "root") and hasattr(self.ui.root, "deiconify"):
                    def _restore():
                        self.ui.root.deiconify()
                        self.ui.root.attributes("-topmost", True)
                        self.ui.root.attributes("-topmost", False)
                    self.ui.root.after(0, _restore)
                return "Interfaz de usuario restaurada."
            except Exception as e:
                return f"Error al restaurar: {e}"

        elif action_ui == "hide_all":
            self.ui.write_log("__hide__")
            return "Todos los widgets ocultados."

        elif action_ui in ("show", "hide", "toggle"):
            if widget_name == "main_window" or not widget_name:
                if action_ui == "show":
                    try:
                        if hasattr(self.ui, "_win") and hasattr(self.ui._win, "showNormal"):
                            QTimer.singleShot(0, self.ui._win.showNormal)
                            QTimer.singleShot(0, self.ui._win.activateWindow)
                        return "Interfaz de usuario restaurada."
                    except Exception as e:
                        return f"Error al restaurar: {e}"
                else:
                    self.ui.write_log("__hide__")
                    return "Todos los widgets ocultados."
            else:
                cmd = "__widget_show__" if action_ui in ("show", "toggle") else "__widget_close__"
                self.ui.write_log(f"{cmd}:{widget_name}")
                return f"Widget '{widget_name}' {'mostrado' if 'show' in cmd else 'ocultado'}."

        return f"Acción de UI desconocida: {action_ui}"

    async def _handle_computer_settings(self, args, loop):
        from core.action_imports import computer_settings
        action = args.get("action", "")

        if action == "volume":
            val = args.get("value", "")
            try:
                import pyautogui
                if str(val).isdigit():
                    target = int(val)
                    try:
                        from ctypes import cast, POINTER
                        from comtypes import CoInitialize, CoUninitialize
                        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                        CoInitialize()
                        devices = AudioUtilities.GetSpeakers()
                        interface = devices.Activate(IAudioEndpointVolume._iid_, 1, None)
                        volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
                        scalar_vol = max(0.0, min(1.0, target / 100.0))
                        volume_ctrl.SetMasterVolumeLevelScalar(scalar_vol, None)
                        CoUninitialize()
                        return f"Volumen ajustado al {target}%."
                    except Exception as e:
                        return f"Error ajustando volumen absoluto: {e}"
                else:
                    if "up" in val.lower() or "subir" in val.lower():
                        pyautogui.press("volumeup", presses=5)
                        return "Volumen subido."
                    elif "down" in val.lower() or "bajar" in val.lower():
                        pyautogui.press("volumedown", presses=5)
                        return "Volumen bajado."
                    elif "mute" in val.lower() or "silenciar" in val.lower():
                        pyautogui.press("volumemute")
                        return "Volumen silenciado."
                    return f"Acción de volumen no reconocida: {val}"
            except Exception as ve:
                return f"Error en control de volumen: {ve}"

        if action in ("window_minimize", "minimize"):
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 6)
                    return "Ventana activa minimizada."
                return "No se encontró ninguna ventana activa."
            except Exception as e:
                return f"Error al minimizar: {e}"

        if action in ("window_maximize", "maximize"):
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 3)
                    return "Ventana activa maximizada."
                return "No se encontró ninguna ventana activa."
            except Exception as e:
                return f"Error al maximizar: {e}"

        r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: computer_settings(parameters=args, response=None, player=self.ui))
        return r or "Done."

    async def _handle_db_memory(self, args, loop):
        from core.action_imports import memory_set, memory_delete, memory_all
        act = args.get("action", "recall")
        if act == "save":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: memory_set(args.get("key", ""), args.get("value", ""), args.get("category", "general"), args.get("importance", 0.5)))
            return f"Guardado: {args.get('key')}"
        elif act == "delete":
            await loop.run_in_executor(TOOL_EXECUTOR, lambda: memory_delete(args.get("key", "")))
            return f"Borrado: {args.get('key')}"
        else:
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: memory_all(20))
            return json.dumps(r, ensure_ascii=False)

    async def _handle_db_knowledge(self, args, loop):
        from core.action_imports import know_add, know_by_topic, know_search
        act = args.get("action", "search")
        if act == "add":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: know_add(args.get("topic", ""), args.get("fact", ""), args.get("source", "eris"), args.get("confidence", 0.5), args.get("tags")))
            return f"Conocimiento guardado: {args.get('topic')}"
        elif act == "topic":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: know_by_topic(args.get("topic", ""), 20))
            return json.dumps(r, ensure_ascii=False)
        else:
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: know_search(args.get("query", ""), 10))
            return json.dumps(r, ensure_ascii=False)

    async def _handle_db_tasks(self, args, loop):
        from core.action_imports import task_add, task_update, task_delete, task_list
        act = args.get("action", "list")
        if act == "add":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: task_add(args.get("title", ""), args.get("description", ""), args.get("priority", "medium")))
            return f"Tarea creada: {args.get('title')}"
        elif act == "done":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: task_update(args.get("task_id", 0), status="done"))
            return f"Tarea #{args.get('task_id')} completada."
        elif act == "delete":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: task_delete(args.get("task_id", 0)))
            return f"Tarea #{args.get('task_id')} eliminada."
        else:
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: task_list(args.get("status"), 30))
            return json.dumps(r, ensure_ascii=False)

    async def _handle_plugin_manage(self, args, loop):
        from core.action_imports import get_plugin_manager
        act = args.get("action", "list")
        if not get_plugin_manager:
            return "plugin_manager no disponible"

        pm = get_plugin_manager()
        if act == "list":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: pm.list_plugins())
            return json.dumps(r, ensure_ascii=False) if r else "No hay plugins cargados."
        elif act == "reload":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: pm.reload())
            return f"Plugins recargados: {r[0]} OK, {len(r[1])} errores."
        elif act == "run":
            pname = args.get("plugin_name", "")
            paction = args.get("plugin_action", "run")
            pparams = args.get("params", "{}")
            try: pparams = json.loads(pparams) if isinstance(pparams, str) else pparams
            except: pparams = {}
            plugin = pm.get_plugin(pname)
            if plugin:
                r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: plugin.execute(paction, pparams))
                return r or "Plugin ejecutado."
            return f"Plugin '{pname}' no encontrado."
        return f"Accion '{act}' no reconocida. Usa: list, reload, run."

    async def _handle_screen_recorder(self, args, loop):
        from core.action_imports import start_recording, stop_recording, recording_status
        a = args.get("action", "status")
        if a == "start":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: start_recording(args, self.ui))
        elif a == "stop":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: stop_recording(args, self.ui))
        else:
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: recording_status(args, self.ui))
        return r or "Done."

    async def _handle_translator(self, args, loop):
        from core.action_imports import translate_text, start_monitoring, stop_monitoring, translator_status
        a = args.get("action", "status")
        if a == "translate_text":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: translate_text(args, self.ui))
        elif a == "start_monitoring":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: start_monitoring(args, self.ui))
        elif a == "stop_monitoring":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: stop_monitoring(args, self.ui))
        else:
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: translator_status(args, self.ui))
        return r or "Done."

    async def _handle_meeting_transcriber(self, args, loop):
        from core.action_imports import start_transcription, stop_transcription, summarize_transcription, transcription_status
        a = args.get("action", "status")
        if a == "start":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: start_transcription(args, self.ui))
        elif a == "stop":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: stop_transcription(args, self.ui))
        elif a == "summarize":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: summarize_transcription(args, self.ui))
        else:
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: transcription_status(args, self.ui))
        return r or "Done."

    async def _handle_network_monitor(self, args, loop):
        from core.action_imports import connections, bandwidth, wifi_info, ping_host, scan_network, monitor_start, monitor_stop, network_status
        a = args.get("action", "status")
        dispatch_map = {
            "connections": connections, "bandwidth": bandwidth, "wifi": wifi_info,
            "ping": ping_host, "scan": scan_network,
            "monitor_start": monitor_start, "monitor_stop": monitor_stop,
        }
        fn = dispatch_map.get(a, network_status)
        r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: fn(args, self.ui))
        return r or "Done."

    async def _handle_quick_actions(self, args, loop):
        from core.action_imports import add, update, remove, list_actions, qa_execute
        a = args.get("action", "list")
        dispatch_map = {"add": add, "update": update, "remove": remove, "list": list_actions, "run": qa_execute}
        fn = dispatch_map.get(a)
        if fn is None:
            return "Accion no valida. Usa: add, update, remove, list, run"
        if a == "run":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: fn(args, self.ui))
            if isinstance(r, tuple):
                _, cmd = r
                return f"Ejecutando atajo: {cmd}"
            return r or "Done."
        r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: fn(args, self.ui))
        return r or "Done."

    async def _handle_pdf_editor(self, args, loop):
        from core.action_imports import read_pdf, merge_pdfs, split_pdf, pdf_info, fill_form, add_signature
        a = args.get("action", "info")
        dispatch_map = {"read": read_pdf, "merge": merge_pdfs, "split": split_pdf, "info": pdf_info, "fill_form": fill_form, "add_signature": add_signature}
        fn = dispatch_map.get(a)
        if fn is None:
            return "Accion no valida."
        r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: fn(args, self.ui))
        return r or "Done."

    async def _handle_context_menu(self, args, loop):
        from core.action_imports import ctx_install, ctx_uninstall, ctx_status
        a = args.get("action", "status")
        if a == "install":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: ctx_install(args, self.ui))
        elif a == "uninstall":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: ctx_uninstall(args, self.ui))
        else:
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: ctx_status(args, self.ui))
        return r or "Done."

    async def _handle_sms(self, args, loop):
        from core.action_imports import send_sms, sms_history, sms_status
        a = args.get("action", "status")
        if a == "send":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: send_sms(args, self.ui))
        elif a == "history":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: sms_history(args, self.ui))
        else:
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: sms_status(args, self.ui))
        return r or "Done."

    async def _handle_dashboard(self, args, loop):
        from core.action_imports import start_dashboard, stop_dashboard, dashboard_status
        a = args.get("action", "status")
        if a == "start":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: start_dashboard(args, self.ui))
        elif a == "stop":
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: stop_dashboard(args, self.ui))
        else:
            r = await loop.run_in_executor(TOOL_EXECUTOR, lambda: dashboard_status(args, self.ui))
        return r or "Done."
