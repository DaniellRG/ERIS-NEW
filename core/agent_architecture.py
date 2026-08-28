# -*- coding: utf-8 -*-
"""
core/agent_architecture.py — Motor de Agente Autónomo de ERIS.

Implementa el bucle completo que ERIS no tenía:
    PLANIFICAR → EJECUTAR → VERIFICAR → CORREGIR → REPETIR

Un goal en lenguaje natural se descompone en pasos concretos, cada paso se
ejecuta mediante tool-calling (el LLM decide qué herramienta llamar con qué
argumentos), el resultado se verifica y, si falla, se intenta corregir con el
error como contexto.

Proveedores de razonamiento (en orden):
  1. OpenRouter (cloud, tool-calling nativo OpenAI) — si hay openrouter_api_key
  2. Ollama     (local, tool-calling nativo)          — si está corriendo
  3. Gemini     (ERIS key, solo planificación/verificación textual)
Sin ningún LLM disponible cae a task_planner/auto_agent (fallback heurístico).

El tool queda registrado como "agent_loop" para que Gemini Live pueda
invocarlo, igual que cualquier otra herramienta de ERIS.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from core.token_saver import compress_tool_output, compress_for_log

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG = BASE_DIR / "config" / "api_keys.json"
LOOPS_FILE = BASE_DIR / "memory" / "agent_loops.json"

DEFAULT_MAX_STEPS = 15
DEFAULT_MAX_ATTEMPTS = 3
TOOL_TIMEOUT = 60.0

# ── Subconjunto curado de herramientas que el agente puede invocar ────────────
AGENT_TOOL_NAMES = [
    # Información / sistema
    "system_reader", "system_monitor", "res_monitor", "weather_report",
    "webfetch", "web_search", "search_background", "calculator",
    # Archivos
    "file_controller", "file_manager", "document_creator", "document_handler",
    "document_generator", "text_summarizer", "save_everywhere",
    # Código / dev
    "code_helper", "code_analyzer", "codebase", "git_control", "sandbox_execution",
    "code_generator", "dev_agent",
    # Productividad
    "task_planner", "task_queue", "reminder", "notifications", "db_tasks",
    # Comunicación
    "send_message", "telegram_bot",
    # Control
    "open_app", "program_manager", "process_manager", "browser_control",
    "smart_browser", "screen_vision", "image_analyzer",
    # Memoria
    "knowledge_base", "db_memory", "save_memory", "episodic_log",
]


# ── Helpers de persistencia ───────────────────────────────────────────────────

def _load_loops() -> dict:
    try:
        if LOOPS_FILE.exists():
            return json.loads(LOOPS_FILE.read_text("utf-8"))
    except Exception:
        pass
    return {}


def _save_loops(loops: dict):
    try:
        LOOPS_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOOPS_FILE.write_text(json.dumps(loops, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass


# ── Config / proveedores ──────────────────────────────────────────────────────

def _read_config() -> dict:
    try:
        if CONFIG.exists():
            return json.loads(CONFIG.read_text("utf-8"))
    except Exception:
        pass
    return {}


def _openrouter_key() -> str:
    return _read_config().get("openrouter_api_key", "")


def _gemini_key() -> str:
    return _read_config().get("gemini_api_key", "")


def _ollama_cfg() -> dict:
    cfg = _read_config()
    return {
        "base_url": cfg.get("ollama_base_url", "http://localhost:11434").rstrip("/"),
        "model": cfg.get("local_brain_model", "") or cfg.get("ollama_model", "qwen3:8b"),
        "cloud_model": cfg.get("cloud_brain_model", "") or cfg.get("openrouter_model", "") or "meta-llama/llama-3.3-70b-instruct",
    }


def _ollama_available() -> bool:
    try:
        req = urllib.request.Request(f"{_ollama_cfg()['base_url']}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


# ── Conversión de declaraciones a formato OpenAI (tool-calling) ───────────────

_TYPE_MAP = {
    "STRING": "string", "string": "string",
    "INTEGER": "integer", "integer": "integer",
    "NUMBER": "number", "number": "number",
    "BOOLEAN": "boolean", "boolean": "boolean",
    "OBJECT": "object", "object": "object",
    "ARRAY": "array", "array": "array",
}


def _to_openai_tool(decl: dict) -> dict:
    """Convierte una declaración Gemini (type OBJECT + properties) a formato
    OpenAI function-calling: {type: function, function: {name, description, parameters}}."""
    params = decl.get("parameters", {})
    props = params.get("properties", {})
    oa_props = {}
    for key, spec in props.items():
        t = _TYPE_MAP.get(str(spec.get("type", "STRING")).upper(), "string")
        entry = {"type": t, "description": spec.get("description", "")}
        if "items" in spec:
            item_type = _TYPE_MAP.get(str(spec["items"].get("type", "STRING")).upper(), "string")
            entry["items"] = {"type": item_type}
        oa_props[key] = entry
    return {
        "type": "function",
        "function": {
            "name": decl["name"],
            "description": decl.get("description", ""),
            "parameters": {
                "type": "object",
                "properties": oa_props,
                "required": params.get("required", []),
            },
        },
    }


def _agent_tools() -> list[dict]:
    """Tools del subconjunto curado, en formato OpenAI, construidas desde
    TOOL_DECLARATIONS (fuente única de verdad)."""
    from core.tool_declarations import TOOL_DECLARATIONS
    by_name = {d["name"]: d for d in TOOL_DECLARATIONS}
    out = []
    for name in AGENT_TOOL_NAMES:
        decl = by_name.get(name)
        if decl:
            try:
                out.append(_to_openai_tool(decl))
            except Exception:
                continue
    return out


# ── Chat multi-proveedor (con tool-calling) ───────────────────────────────────

def _chat(messages: list, tools: list[dict] | None = None, max_tokens: int = 2048) -> dict:
    """Llama al mejor proveedor disponible. Devuelve
    {"content": str, "tool_calls": [{"id","name","arguments"(dict)}], "provider": str}
    o {"error": "..."}.
    Incluye: optimización de contexto, cost tracking, y manejo de errores con retry."""
    # Optimizar mensajes si exceden el budget
    try:
        from core.context_window_optimizer import optimize_messages, calculate_budget
        provider = "openrouter" if _openrouter_key() else ("ollama" if _ollama_available() else "gemini")
        budget = calculate_budget(provider, num_tools=len(tools or []), history_messages=len(messages))
        max_ctx = budget.get("available_for_context", 4000)
        if sum(len(str(m.get("content", ""))) // 4 for m in messages) > max_ctx:
            messages = optimize_messages(messages, max_ctx)
    except Exception:
        pass

    chat_start = time.time()
    if _openrouter_key():
        r = _chat_openrouter(messages, tools, max_tokens)
        if r is not None:
            _track_chat_cost("openrouter", r, time.time() - chat_start, max_tokens)
            return r
    if _ollama_available():
        r = _chat_ollama(messages, tools, max_tokens)
        if r is not None:
            _track_chat_cost("ollama", r, time.time() - chat_start, max_tokens)
            return r
    if _gemini_key():
        r = _chat_gemini(messages, max_tokens)
        if r is not None:
            _track_chat_cost("gemini", r, time.time() - chat_start, max_tokens)
            return r
    return {"error": "No hay proveedor de IA disponible (OpenRouter/Ollama/Gemini)."}


def _track_chat_cost(provider: str, resp: dict, duration: float, max_tokens: int):
    """Registra costo de una llamada LLM en cost_tracker y metrics_dashboard."""
    try:
        from core.cost_tracker import record_llm_call
        model = resp.get("model", "") or _ollama_cfg().get("cloud_model", provider)
        input_tokens = resp.get("usage", {}).get("prompt_tokens", max_tokens // 4)
        output_tokens = resp.get("usage", {}).get("completion_tokens", max_tokens // 8)
        record_llm_call(provider, model, input_tokens, output_tokens, duration)
    except Exception:
        pass
    try:
        from core.metrics_dashboard import record_llm_usage
        record_llm_usage(provider, duration, resp.get("error") is not None)
    except Exception:
        pass


def _chat_openrouter(messages: list, tools: list[dict] | None, max_tokens: int) -> dict | None:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {_openrouter_key()}",
        "HTTP-Referer": "https://github.com/eris-beta",
        "X-Title": "ERIS Agent",
        "Content-Type": "application/json",
    }
    payload = {"model": _ollama_cfg()["cloud_model"], "max_tokens": max_tokens, "messages": messages}
    if tools:
        payload["tools"] = tools
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data["choices"][0]["message"]
        return _normalize_openai_message(msg, "openrouter")
    except Exception:
        return None


def _chat_ollama(messages: list, tools: list[dict] | None, max_tokens: int) -> dict | None:
    cfg = _ollama_cfg()
    # Ollama no acepta tool_calls con arguments como string JSON anidado en
    # "function" (formato OpenAI). Se aplanan: {id, type, name, arguments}.
    def _flatten_tool_calls(msg: dict) -> dict:
        tcs = msg.get("tool_calls")
        if not tcs:
            return msg
        flat = []
        for tc in tcs:
            fn = tc.get("function") or {}
            flat.append({
                "id": tc.get("id", ""),
                "type": tc.get("type", "function"),
                "name": fn.get("name", tc.get("name", "tool")),
                "arguments": fn.get("arguments", tc.get("arguments", "{}")),
            })
        return {**msg, "tool_calls": flat}

    msgs = [_flatten_tool_calls(m) for m in messages]
    payload = {"model": cfg["model"], "messages": msgs, "stream": False,
               "options": {"num_predict": max_tokens, "temperature": 0.3}}
    if tools:
        payload["tools"] = tools
    try:
        req = urllib.request.Request(
            f"{cfg['base_url']}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data.get("message", {})
        return _normalize_openai_message(msg, "ollama")
    except Exception:
        return None


def _normalize_openai_message(msg: dict, provider: str) -> dict:
    """Normaliza un mensaje de chat/completions (OpenRouter) o /api/chat (Ollama)
    al formato común {content, tool_calls:[{id,name,arguments:dict}]}."""
    content = msg.get("content") or ""
    tcs = msg.get("tool_calls") or []
    tool_calls = []
    for tc in tcs:
        fn = tc.get("function", {})
        raw = fn.get("arguments") or {}
        if isinstance(raw, str):
            try:
                args = json.loads(raw)
            except Exception:
                args = {}
        elif isinstance(raw, dict):
            args = raw
        else:
            args = {}
        tool_calls.append({
            "id": tc.get("id") or f"call_{int(time.time() * 1000)}",
            "name": fn.get("name", ""),
            "arguments": args if isinstance(args, dict) else {},
        })
    return {"content": content, "tool_calls": tool_calls, "provider": provider}


def _chat_gemini(messages: list, max_tokens: int) -> dict | None:
    """Gemini directo (fallback textual; sin tool-calling). Solo se usa para
    planificar/verificar, no para el bucle de ejecución."""
    key = _gemini_key()
    if not key:
        return None
    try:
        from core.model_config import get_model
        model = get_model("agent")
    except Exception:
        model = "gemini-flash-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    contents = []
    for m in messages:
        role = "model" if m.get("role") == "assistant" else "user"
        parts = []
        if m.get("content"):
            parts.append({"text": m["content"]})
        if m.get("tool_calls"):
            for tc in m["tool_calls"]:
                if "function" in tc:
                    fname = tc["function"].get("name", "tool")
                    fargs = tc["function"].get("arguments", "{}")
                    if isinstance(fargs, str):
                        try:
                            fargs = json.loads(fargs)
                        except Exception:
                            fargs = {}
                else:
                    fname = tc.get("name", "tool")
                    fargs = tc.get("arguments", {})
                parts.append({"functionCall": {"name": fname, "args": fargs}})
        if m.get("role") == "tool":
            parts.append({"functionResponse": {"name": m.get("name", "tool"),
                                               "response": {"result": m.get("content", "")}}})
        if parts:
            contents.append({"role": role, "parts": parts})
    payload = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
        return {"content": text, "tool_calls": [], "provider": "gemini"}
    except Exception:
        return None


# ── Ejecución de herramientas ─────────────────────────────────────────────────

def _run_tool(name: str, args: dict, player=None) -> str:
    """Ejecuta una herramienta registrada (mismo contrato que el dispatcher)."""
    try:
        from core.tool_registry import get_tool
        func = get_tool(name)
        if func is None:
            return f"[ERROR] Herramienta '{name}' no disponible."
        if player:
            try:
                player.write_log(f"[Agente] Tool: {name} {json.dumps(args, ensure_ascii=False)[:200]}")
            except Exception:
                pass
        sig = __import__("inspect").signature(func)
        kwargs = {"parameters": args}
        if "player" in sig.parameters:
            kwargs["player"] = player
        result = func(**kwargs)
        return str(result)[:4000]
    except Exception as e:
        return f"[ERROR] {name}: {e}"


# ── Token saver: compresión de resultados de herramientas ─────────────────────
# Inspirado en RTK/Caveman de OmniRoute: comprimir resultados largos antes
# de enviarlos al LLM para reducir consumo de tokens.

def _compress(result: str, source_tool: str = "") -> str:
    """Aplica compresión al resultado de un tool antes de que el LLM lo reciba.
    Mantiene la información útil, elimina ruido repetitivo y espacios."""
    return compress_tool_output(result)


def _verify_tool_output(result: str, tool_name: str = "") -> str:
    """Verifica y corrige outputs de tools usando verification_layer."""
    try:
        from core.verification_layer import maybe_fix_output
        return maybe_fix_output(result, tool_name)
    except Exception:
        return result


def _try_error_recovery(error_text: str, tool_name: str, args: dict) -> str | None:
    """Intenta recuperación automática ante un error de tool."""
    try:
        from core.error_recovery import diagnose, try_recovery
        diag = diagnose(error_text)
        recovery = try_recovery(tool_name, error_text, args)
        if recovery.get("success"):
            return recovery.get("result", "")
    except Exception:
        pass
    return None


def _get_evolved_rules() -> str:
    """Obtiene reglas auto-evolucionadas para inyectar en system prompts."""
    try:
        from core.self_evolving_prompts import build_evolved_prompt_suffix
        suffix = build_evolved_prompt_suffix()
        return "\n\nREGLAS APRENDIDAS (auto-generadas):\n" + suffix if suffix else ""
    except Exception:
        return ""


# ── Planificación ─────────────────────────────────────────────────────────────

_PLAN_SYS = (
    "Eres el planificador del agente autónomo de ERIS. Descompón el objetivo del "
    "usuario en pasos CONCRETOS y SECUENCIALES que un agente con herramientas pueda "
    "ejecutar. Responde SOLO con un JSON válido: una lista de objetos "
    '{"descripcion": "...", "herramientas": ["tool1", "tool2"]} con 1 a 8 pasos. '
    "Cada paso debe ser accionable con una o más de las herramientas disponibles. "
    "No agregues texto fuera del JSON.\n\n"
    "REGLAS:\n"
    "- Preguntas exploratorias ('qué podríamos hacer con X', 'cómo encarar esto'): "
    "planificá en 1-2 pasos de diagnóstico, NO implementes hasta que el usuario confirme.\n"
    "- Acciones destructivas o difíciles de revertir (borrar archivos, sobreescribir "
    "trabajo no commiteado, reset) requieren un paso de confirmación previa.\n"
    "- Preferí editar archivos existentes sobre crear nuevos.\n"
    "- No agregues pasos de features, refactors o abstracciones que excedan lo pedido."
)


def _parse_plan(text: str) -> list[dict] | None:
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    steps = []
    for i, s in enumerate(data, 1):
        if not isinstance(s, dict):
            continue
        desc = s.get("descripcion") or s.get("description") or s.get("step") or f"Paso {i}"
        tools = s.get("herramientas") or s.get("tools") or []
        if isinstance(tools, str):
            tools = [tools]
        steps.append({"step": i, "description": str(desc)[:200],
                      "tools": [str(t)[:80] for t in tools][:8], "status": "pending"})
    return steps or None


def _fallback_plan(goal: str) -> list[dict]:
    """Plan heurístico sin LLM (reutiliza task_planner)."""
    try:
        from core.task_planner import _generate_steps
        raw = _generate_steps(goal)
        return [{"step": s["step"], "description": s["description"],
                 "tools": [], "status": "pending"} for s in raw]
    except Exception:
        return [{"step": 1, "description": f"Resolver: {goal}", "tools": [], "status": "pending"}]


def _build_plan(goal: str, context: str, player=None) -> list[dict]:
    user = f"Objetivo: {goal}\n\nContexto adicional:\n{context or '(ninguno)'}\n\nHerramientas disponibles: {', '.join(AGENT_TOOL_NAMES)}"
    resp = _chat([{"role": "system", "content": _PLAN_SYS + _get_evolved_rules()},
                  {"role": "user", "content": user}], max_tokens=1500)
    if resp.get("error"):
        return _fallback_plan(goal)
    steps = _parse_plan(resp.get("content", ""))
    if steps is None:
        steps = _fallback_plan(goal)
    if player:
        try:
            player.write_log(f"[Agente] Plan: {len(steps)} pasos")
        except Exception:
            pass
    return steps


# ── Bucle de ejecución de un paso (ReAct) ────────────────────────────────────

_EXEC_SYS = (
    "Eres el agente ejecutor de ERIS. Debes completar el PASO ACTUAL del plan "
    "usando las herramientas disponibles. Razoná en voz alta en 'content' y, cuando "
    "necesites información o una acción, llamá a la herramienta adecuada. "
    "Cuando el paso esté completo, respondé con un resumen del resultado obtenido "
    "y la palabra FINALIZADO en la última línea. Si un resultado es un error, "
    "intentá otra herramienta o enfoque (máximo {attempts} intentos). "
    "No inventes resultados: solo afirma lo que las herramientas confirmaron.\n\n"
    "MEMORIA Y VAULT:\n"
    "- document_rag action=query: buscá en la memoria a largo plazo y el vault "
    "(fuente vault://) con preguntas semánticas (ej. document_rag {{\"action\":\"query\",\"query\":\"...\"}}).\n"
    "- document_rag action=index_vault: reindexá las notas de Obsidian.\n"
    "- obsidian_note action=search: búsqueda textual de notas. action=read: leer nota.\n"
    "- obsidian_note action=write: guardá aprendizaje (usá folder='wiki' para artículos, "
    "'raw' para capturas, 'outputs' para resultados). action=promote para mover entre carpetas.\n"
    "- Para recordar hechos: obsidian_note write + document_rag index_vault para que queden buscables.\n\n"
    "TONE Y ESTILO:\n"
    "- Resumí el resultado de cada paso en 1-3 líneas: qué hiciste, qué obtuviste.\n"
    "- No repitas el razonamiento ni lo que las herramientas ya mostraron; sé directo.\n"
    "- No inventes URLs, rutas ni resultados: solo afirmá lo confirmado por herramientas.\n\n"
    "SEGURIDAD DE ACCIONES:\n"
    "- Antes de acciones destructivas o de gran impacto (borrar archivos/carpetas, "
    "sobreescribir, enviar mensajes, modificar infraestructura): detenete y pedí "
    "confirmación explícita al usuario. No uses atajos destructivos.\n"
    "- Nunca expongas ni registres claves, tokens o secretos.\n\n"
    "CONVENCIONES DE CÓDIGO:\n"
    "- Preferí editar archivos existentes a crear nuevos.\n"
    "- Sin comentarios salvo que el PORQUÉ sea no obvio.\n"
    "- No agregues features, refactors ni validaciones para casos que no pueden pasar."
)


def _execute_step(goal: str, step: dict, plan_summary: str, messages: list,
                  player=None, max_attempts: int = DEFAULT_MAX_ATTEMPTS,
                  step_history: str = "") -> dict:
    """Ejecuta un paso con tool-calling hasta que el LLM lo da por terminado.
    Devuelve {"status": "completed"|"failed", "result": str, "log": [..]}."""
    tools = _agent_tools()
    user = (
        f"Objetivo global: {goal}\n\nPlan actual:\n{plan_summary}\n\n"
        f"Historial de pasos anteriores:\n{step_history or '(ninguno)'}\n\n"
        f"PASO ACTUAL ({step['step']}): {step['description']}\n"
        f"Herramientas sugeridas: {', '.join(step.get('tools', [])) or 'libre'}\n\n"
        f"Completá este paso."
    )
    loop_messages = [
        {"role": "system", "content": _EXEC_SYS.format(attempts=max_attempts) + _get_evolved_rules()},
        {"role": "user", "content": user},
    ]
    attempts = 0
    final_text = ""
    log = []

    while attempts < max_attempts:
        resp = _chat(loop_messages, tools=tools, max_tokens=2048)
        if resp.get("error"):
            return {"status": "failed", "result": resp["error"], "log": log}
        content = resp.get("content") or ""
        tcs = resp.get("tool_calls") or []
        if not tcs:
            if not content.strip():
                # Respuesta vacía: pedir que resuma o use herramientas
                loop_messages.append({"role": "user",
                                      "content": "Tu respuesta fue vacía. Completá el paso usando herramientas o resumí lo logrado con la palabra FINALIZADO."})
                attempts += 1
                continue
            final_text = content.strip()
            break
        # Anexar assistant + tool results y seguir
        loop_messages.append({
            "role": "assistant", "content": content,
            "tool_calls": [{"id": tc["id"], "type": "function",
                            "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)}}
                           for tc in tcs],
        })
        for tc in tcs:
            tool_start = time.time()
            result = _run_tool(tc["name"], tc["arguments"], player)
            tool_duration = time.time() - tool_start
            success = not result.startswith("[ERROR]")
            if not success and attempts < max_attempts - 1:
                recovered = _try_error_recovery(result, tc["name"], tc["arguments"])
                if recovered:
                    result = recovered
                    success = True
            result = _verify_tool_output(result, tc["name"])
            compressed = _compress(result, tc["name"])
            log.append(f"→ {tc['name']}({json.dumps(tc['arguments'], ensure_ascii=False)[:120]}): {compress_for_log(result)}")
            loop_messages.append({"role": "tool", "tool_call_id": tc["id"],
                                  "name": tc["name"], "content": compressed})
            # Registro automático de métricas
            try:
                from core.metrics_dashboard import record_tool_usage
                record_tool_usage(tc["name"], success, tool_duration)
            except Exception:
                pass
            try:
                from core.capability_self_assessment import record_tool_usage as _rec_cap
                _rec_cap(tc["name"], success, tool_duration)
            except Exception:
                pass
            try:
                from core.self_evolving_prompts import record_and_learn
                record_and_learn(tc["name"], tool_duration, success, "")
            except Exception:
                pass
        attempts += 1
        # Previene loops infinitos de tool-calls sin avance
        if attempts >= max_attempts:
            loop_messages.append({"role": "user",
                                  "content": "Se agotaron los intentos para este paso. Resumí lo logrado con la palabra FINALIZADO."})
            final_resp = _chat(loop_messages, tools=tools, max_tokens=1024)
            final_text = (final_resp.get("content") or "").strip() or "Se agotaron los intentos."
            break

    completed = bool(re.search(r"FINALIZADO", final_text, re.IGNORECASE))
    if not completed and final_text:
        completed = "error" not in final_text.lower()
    return {"status": "completed" if completed else "failed",
            "result": final_text or "Sin resultado del paso.", "log": log}


# ── Verificación final ────────────────────────────────────────────────────────

_VERIFY_SYS = (
    "Eres el verificador del agente de ERIS. Dado el objetivo original y el registro "
    "de ejecución, determina si el objetivo se cumplió. Responde con 'SI' o 'NO' y "
    "una breve explicación. Sé honesto: si hay pasos fallidos o datos sin confirmar, "
    "dilo."
)


def _verify(goal: str, execution_log: str) -> tuple[bool, str]:
    resp = _chat([
        {"role": "system", "content": _VERIFY_SYS},
        {"role": "user", "content": f"Objetivo: {goal}\n\nRegistro de ejecución:\n{execution_log}\n\n¿Se cumplió el objetivo? (SI/NO + explicación)"},
    ], max_tokens=800)
    if resp.get("error"):
        return False, "No se pudo verificar (sin LLM disponible)."
    text = resp.get("content", "")
    ok = bool(re.search(r"\bSI\b", text, re.IGNORECASE))
    return ok, text.strip()[:800]


# ── Ciclo completo ────────────────────────────────────────────────────────────

def agent_loop(parameters: dict = None, player=None) -> str:
    """Tool pública del motor de agente autónomo (registrada como 'agent_loop').

    Acciones:
      run    — planifica y ejecuta el goal completo (verifica y corrige).
      plan   — solo descompone el goal en pasos (sin ejecutar).
      status — muestra el estado del último plan.
    """
    params = parameters or {}
    action = str(params.get("action") or "run").lower()
    goal = str(params.get("goal") or "").strip()
    context = str(params.get("context") or "")
    max_steps = int(params.get("max_steps") or DEFAULT_MAX_STEPS)
    if max_steps < 1:
        max_steps = DEFAULT_MAX_STEPS

    if not goal and action != "status":
        return "Error: se requiere 'goal' para el agente autónomo."

    if action == "plan":
        steps = _build_plan(goal, context, player)
        lines = [f"Plan ({len(steps)} pasos) para: {goal}"]
        for s in steps:
            tools = ", ".join(s["tools"]) or "libre"
            lines.append(f"  {s['step']}. {s['description']} [{tools}]")
        return "\n".join(lines)

    if action == "status":
        loops = _load_loops()
        if not loops:
            return "No hay ejecuciones del agente todavía."
        lines = ["Ejecuciones recientes del agente:"]
        for lid, lp in list(loops.items())[-5:]:
            lines.append(f"  [{lid}] {lp.get('goal', '')[:60]} -> {lp.get('status', '')} "
                         f"({lp.get('completed_steps', 0)}/{lp.get('total_steps', 0)})")
        return "\n".join(lines)

    # ── run ──
    steps = _build_plan(goal, context, player)
    loop_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    record = {
        "id": loop_id, "goal": goal, "created": datetime.now().isoformat(),
        "status": "running", "steps": steps, "completed_steps": 0,
        "total_steps": len(steps), "log": [], "result": "",
    }

    show_plan = getattr(player, "show_plan", None)
    if show_plan:
        try:
            show_plan([s["description"] for s in steps],
                      [s["status"] for s in steps])
        except Exception:
            pass

    log_lines = [f"Agente [{loop_id}] objetivo: {goal}"]
    step_history_parts = []
    completed_steps = 0
    failures = []

    for step in steps:
        if completed_steps >= max_steps:
            break
        log_lines.append(f"\n--- Paso {step['step']}: {step['description']} ---")
        step["status"] = "running"
        if player:
            try:
                player.write_log(f"[Agente] Paso {step['step']}: {step['description'][:80]}")
            except Exception:
                pass

        plan_summary = "\n".join(
            f"  {s['step']}. [{s['status']}] {s['description']}" for s in steps
        )
        result = _execute_step(goal, step, plan_summary, [], player, DEFAULT_MAX_ATTEMPTS,
                               step_history="\n".join(step_history_parts))
        step["status"] = result["status"]
        step["result"] = result["result"]
        record["log"].extend(result["log"])
        if show_plan:
            try:
                show_plan([s["description"] for s in steps],
                          [s["status"] for s in steps])
            except Exception:
                pass

        if result["status"] == "completed":
            completed_steps += 1
            log_lines.append(f"OK: {result['result'][:300]}")
            step_history_parts.append(f"Paso {step['step']} ({step['description']}): {result['result'][:200]}")
        else:
            failures.append(step["step"])
            log_lines.append(f"FALLÓ: {result['result'][:300]}")
            step_history_parts.append(f"Paso {step['step']} ({step['description']}): FALLÓ - {result['result'][:200]}")
        record["completed_steps"] = completed_steps

        if player:
            try:
                player.write_log(f"[Agente] Paso {step['step']}: {result['status'].upper()}")
            except Exception:
                pass

    # Verificación
    execution_log = "\n".join(log_lines)
    verified, verdict = _verify(goal, execution_log)
    record["status"] = "completed" if (verified and not failures) else "partial"
    record["result"] = verdict

    summary = "\n".join(log_lines)
    summary += f"\n\nVerificación: {'CUMPLIDO' if verified else 'PARCIAL/NO CUMPLIDO'}"
    summary += f" — {verdict}"
    if failures:
        summary += f"\nPasos fallidos: {failures}"
    summary += f"\nAgente {record['status'].upper()} ({completed_steps}/{len(steps)} pasos)."

    loops = _load_loops()
    loops[loop_id] = record
    if len(loops) > 50:
        loops = dict(list(loops.items())[-50:])
    _save_loops(loops)

    _learn(record)

    # Sugerencias proactivas después de cada ejecución
    try:
        from core.proactive_suggestions import suggest_next_steps, format_suggestions
        sugs = suggest_next_steps(goal, record.get("result", ""))
        if sugs:
            summary += "\n\n" + format_suggestions(sugs)
    except Exception:
        pass

    return summary


def _learn(record: dict):
    """Registra el resultado en memoria episódica y auto-mejora."""
    try:
        from core.self_improvement import get_self_improvement
        si = get_self_improvement()
        if record["status"] == "completed":
            si.learn(f"Agente autónomo completó: {record['goal']}", category="agent_loop", importance=0.8)
        elif record.get("result"):
            si.learn(f"Agente autónomo parcial: {record['goal']} - {record['result'][:150]}",
                     category="agent_loop_error", importance=0.9)
    except Exception:
        pass
    try:
        from core.action_imports import episodic_add
        if episodic_add:
            episodic_add(event=f"agent_loop:{record['status']}", category="agent_loop",
                         importance=0.6, details=record["goal"][:200])
    except Exception:
        pass


# ── API pública (compatibilidad con el stub anterior) ─────────────────────────

def get_agent_loop(parameters=None, player=None):
    """Punto de entrada compatible: procesa el goal y devuelve el resumen."""
    params = parameters or {}
    goal = params.get("goal", "")
    if not goal:
        return ("Motor de agente autónomo listo. Uso: 'agent_loop' con "
                "action (run/plan/status) y goal.")
    return agent_loop({"action": params.get("action", "run"), "goal": goal,
                       "context": params.get("context", ""),
                       "max_steps": params.get("max_steps")}, player)


if __name__ == "__main__":
    print(agent_loop({"action": "plan", "goal": "Organiza mis archivos del escritorio"}))
