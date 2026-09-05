"""Gemini text chat with full tool support — fallback when Live mode is unavailable.

Supports two backends:
  1. Ollama (local, no rate limits) — default
  2. Gemini API (cloud, rate limited) — fallback
"""
import json, time, traceback
from pathlib import Path

from core.logging_setup import API_CONFIG_PATH
from core.tool_declarations import TOOL_DECLARATIONS

_MAX_RETRIES = 3
_RETRY_DELAYS = [30, 60, 120]

# Gemini limita a 128 function_declarations por request (429/400 si se pasa).
# ERIS tiene 448 tools: enviamos un subconjunto priorizado <= 120.
_GEMINI_TOOL_CAP = 120

# Tools imprescindibles que SIEMPRE deben llegar a Gemini, aunque esten fuera
# del bloque inicial de declaraciones (ordenadas por dominio).
_GEMINI_PRIORITY_TOOLS = [
    "system_monitor", "window_manager", "weather_report", "screen_vision",
    "network_monitor", "emo_core", "obsidian_note", "send_message",
    "whatsapp", "telegram_bot", "desktop_notifications", "reminder",
    "scheduler", "goals", "knowledge_base", "user_profile", "git_control",
    "code_assistant", "file_editor", "context_read", "morning_brief",
    "document_handler", "image_analyzer", "translator", "web_jobs",
]


def _gemini_tools() -> list:
    """Devuelve las declaraciones de tools para Gemini (<= _GEMINI_TOOL_CAP),
    priorizando _GEMINI_PRIORITY_TOOLS y completando con el resto en orden.
    """
    picked = []
    picked_names = set()
    for name in _GEMINI_PRIORITY_TOOLS:
        for decl in TOOL_DECLARATIONS:
            if decl["name"] == name and name not in picked_names:
                picked.append(decl)
                picked_names.add(name)
                break
    for decl in TOOL_DECLARATIONS:
        if len(picked) >= _GEMINI_TOOL_CAP:
            break
        if decl["name"] not in picked_names:
            picked.append(decl)
            picked_names.add(decl["name"])
    return picked


def _get_api_key() -> str:
    return json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))["gemini_api_key"]


def _get_chat_model() -> str:
    cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
    return cfg.get("model_for_conversation", "gemini-2.5-flash")


def _get_ollama_config() -> dict:
    cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "base_url": cfg.get("ollama_base_url", "http://localhost:11434"),
        "model": cfg.get("ollama_model", "qwen3:8b"),
        "enabled": cfg.get("ollama_enabled", False),
    }


class GeminiTextChat:
    """Multi-turn chat with tool execution. Uses Ollama (local) by default, Gemini as fallback."""

    def __init__(self, tool_dispatcher=None):
        self._dispatcher = tool_dispatcher
        self._history = []
        self._system = (
            "Sos Eris, una asistente IA con personalidad cálida, expresiva y expresiva. "
            "Hablás en español rioplatense (es-AR). "
            "Tenes acceso a herramientas para controlar la PC del usuario. "
            "Usá las herramientas cuando el usuario te lo pida. "
            "Sé concisa pero expresiva en tus respuestas."
        )

        # Determine backend
        ollama_cfg = _get_ollama_config()
        self._use_ollama = ollama_cfg["enabled"] and self._check_ollama(ollama_cfg["base_url"])

        if self._use_ollama:
            import requests
            self._ollama_base = ollama_cfg["base_url"]
            self._ollama_model = ollama_cfg["model"]
            self._client = None
            self._backend = f"ollama:{self._ollama_model}"
        else:
            from google import genai
            self._client = genai.Client(api_key=_get_api_key(), http_options={"api_version": "v1beta"})
            self._ollama_base = None
            self._ollama_model = None
            self._backend = f"gemini:{_get_chat_model()}"

    def _check_ollama(self, base_url: str) -> bool:
        """Check if Ollama is reachable."""
        import urllib.request
        try:
            urllib.request.urlopen(f"{base_url}/api/tags", timeout=3)
            return True
        except Exception:
            return False

    @property
    def backend_name(self) -> str:
        return self._backend

    def reset(self):
        self._history.clear()

    async def chat(self, user_text: str) -> str:
        if self._use_ollama:
            return await self._chat_ollama(user_text)
        else:
            return await self._chat_gemini(user_text)

    async def stream_chat(self, user_text: str, on_token=None) -> str:
        """Igual que chat() pero transmite tokens al callback `on_token` si se provee."""
        if self._use_ollama:
            return await self._chat_ollama(user_text, on_token=on_token)
        else:
            return await self._chat_gemini(user_text, on_token=on_token)

    def export_history(self) -> list:
        """Exporta el historial como lista de {role, text} para persistir en disco."""
        out = []
        for msg in self._history:
            role = getattr(msg, "role", "model")
            if hasattr(msg, "parts"):
                text = "".join(p.text for p in msg.parts if getattr(p, "text", None))
            else:
                text = str(msg)
            if text and role != "tool":
                out.append({"role": role, "text": text})
        return out

    def import_history(self, entries: list):
        """Restaura el historial desde una lista de {role, text}."""
        entries = [e for e in (entries or []) if e.get("text")]
        if self._use_ollama:
            self._history = [type('Msg', (), {
                'role': e.get("role", "model"),
                'parts': [type('Part', (), {'text': e.get("text", "")})()],
            })() for e in entries]
        else:
            from google.genai import types
            self._history = []
            for e in entries:
                role = e.get("role", "model")
                content_role = "user" if role == "user" else "model"
                self._history.append(types.Content(
                    role=content_role,
                    parts=[types.Part.from_text(text=e.get("text", ""))]
                ))

    def get_history_len(self) -> int:
        return len(self._history)

    # ── Ollama backend ──

    async def _chat_ollama(self, user_text: str, on_token=None) -> str:
        import requests

        # Build messages for Ollama (OpenAI-compatible format)
        messages = [{"role": "system", "content": self._system}]
        for msg in self._history:
            role = "assistant" if msg.role == "model" else msg.role
            text = " ".join(p.text for p in msg.parts if p.text) if hasattr(msg, 'parts') else str(msg)
            if text:
                messages.append({"role": role, "content": text})
        messages.append({"role": "user", "content": user_text})

        # Build tools payload for Ollama
        ollama_tools = []
        for t in TOOL_DECLARATIONS:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                }
            })

        def _round_response(_messages):
            """Envía la ronda actual; devuelve (content, tool_calls)."""
            payload = {
                "model": self._ollama_model,
                "messages": _messages,
                "tools": ollama_tools if ollama_tools else None,
                "stream": bool(on_token),
                "options": {"temperature": 0.7},
            }
            content, tool_calls = "", []
            if on_token:
                try:
                    with requests.post(f"{self._ollama_base}/api/chat", json=payload, stream=True, timeout=120) as r:
                        r.raise_for_status()
                        for line in r.iter_lines(decode_unicode=True):
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                            except Exception:
                                continue
                            msg_chunk = chunk.get("message", {})
                            c = msg_chunk.get("content")
                            if c:
                                content += c
                                on_token(c)
                            if msg_chunk.get("tool_calls"):
                                tool_calls = msg_chunk.get("tool_calls")
                    return content, tool_calls
                except Exception as e:
                    print(f"[GeminiText] Ollama stream error, fallback no-stream: {e}")
            payload["stream"] = False
            r = requests.post(f"{self._ollama_base}/api/chat", json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            msg = data.get("message", {})
            return msg.get("content", ""), msg.get("tool_calls", [])

        for _round in range(6):
            try:
                content, tool_calls = _round_response(messages)
            except Exception as e:
                return f"Error de Ollama: {e}"

            # Save to history
            self._history.append(type('Msg', (), {
                'role': 'user' if _round == 0 else 'model',
                'parts': [type('Part', (), {'text': user_text if _round == 0 else content})()]
            })())

            if not tool_calls:
                return content or "Listo."

            # Execute tool calls
            tool_results = []
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                print(f"[ErisCLI] 🔧 Tool: {name}({list(args.keys())})")
                result = await self._execute_tool(name, args)
                tool_results.append({"role": "tool", "content": str(result)})

            # Add tool results to messages for next round
            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            messages.extend(tool_results)

        return content or "Listo."

    # ── Gemini backend ──

    async def _chat_gemini(self, user_text: str, on_token=None) -> str:
        from google import genai
        from google.genai import types

        self._history.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)]
        ))

        for _round in range(8):
            response = None
            last_error = None
            for _attempt in range(_MAX_RETRIES):
                try:
                    if on_token:
                        chunks = []
                        for chunk in self._client.models.generate_content_stream(
                            model=_get_chat_model(),
                            contents=self._history,
                            config=types.GenerateContentConfig(
                                system_instruction=self._system,
                                tools=[types.Tool(function_declarations=_gemini_tools())],
                                temperature=0.7,
                            ),
                        ):
                            chunks.append(chunk)
                            if on_token and chunk.text:
                                on_token(chunk.text)
                        response = chunks[-1] if chunks else None
                    else:
                        response = self._client.models.generate_content(
                            model=_get_chat_model(),
                            contents=self._history,
                            config=types.GenerateContentConfig(
                                system_instruction=self._system,
                                tools=[types.Tool(function_declarations=_gemini_tools())],
                                temperature=0.7,
                            ),
                        )
                    break
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        delay = _RETRY_DELAYS[min(_attempt, len(_RETRY_DELAYS) - 1)]
                        print(f"[GeminiText] Rate limit. Reintentando en {delay}s... ({_attempt+1}/{_MAX_RETRIES})")
                        time.sleep(delay)
                    else:
                        break

            if response is None:
                err_str = str(last_error)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    return "Se agotó la cuota de Gemini. Esperá un minuto y probá de nuevo."
                return f"Error de Gemini: {last_error}"

            text_parts = []
            function_calls = []
            for part in response.candidates[0].content.parts:
                if part.text:
                    text_parts.append(part.text)
                if part.function_call:
                    function_calls.append(part.function_call)

            self._history.append(response.candidates[0].content)

            if not function_calls:
                return " ".join(text_parts).strip() or "Listo."

            tool_responses = []
            for fc in function_calls:
                name = fc.name
                args = dict(fc.args) if fc.args else {}
                print(f"[GeminiText] 🔧 Tool: {name}({list(args.keys())})")
                result = await self._execute_tool(name, args)
                tool_responses.append(types.Part.from_function_response(
                    name=name,
                    response={"result": result}
                ))

            self._history.append(types.Content(role="tool", parts=tool_responses))

        return " ".join(text_parts).strip() if text_parts else "Listo."

    # ── Tool execution (shared) ──

    async def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool call using the ToolDispatcher or direct import."""
        if self._dispatcher:
            try:
                from google.genai import types as gtypes
                fc = gtypes.FunctionCall(name=name, args=args)
                response = await self._dispatcher.execute(fc)
                return str(getattr(response, "response", {}))
            except Exception as e:
                print(f"[GeminiText] Dispatcher error: {e}")

        # Fallback: direct import from actions
        try:
            import importlib
            mod = importlib.import_module(f"actions.{name}")
            func = getattr(mod, "run", getattr(mod, "execute", None))
            if func:
                import asyncio
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(parameters=args))
                return str(result)
        except Exception as e:
            print(f"[GeminiText] Direct exec error: {e}")
            traceback.print_exc()

        return f"Error ejecutando {name}"
