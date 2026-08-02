# -*- coding: utf-8 -*-
"""
core/local_brain.py — Cerebro dual de ERIS.

Arquitectura híbrida:
  - LOCAL  (Ollama, qwen3:8b): charla diaria, tareas, recordatorios, control del PC,
    y herramientas del sistema. Gratis, sin cuota, sin internet, privado.
  - NUBE   (OpenRouter): preguntas difíciles, razonamiento profundo, conocimiento
    actual, código complejo. Solo cuando la ruta lo amerita.

Eris decide automáticamente qué cerebro usar por tarea (enrutamiento heurístico)
y, en modo local, ejecuta herramientas vía tool-calling de Ollama.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG = BASE_DIR / "config" / "api_keys.json"

# ── Sistema ──────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Eres ERIS, la asistente personal de IA de escritorio de Daniel. "
    "Respondes en español de forma natural, cálida y concisa (máximo 3-4 frases salvo que "
    "te pidan más). Tienes acceso a herramientas del sistema para ayudarle con tareas "
    "reales: clima, volumen, recordatorios, memoria, tareas, música, curiosidades, etc. "
    "Usa la herramienta adecuada cuando corresponda y transmite su resultado SIN inventar "
    "datos: solo afirma lo que la herramienta te confirmó; si su resultado no coincide con "
    "lo pedido, dilo con honestidad. Si no tienes la información o necesitas algo de la web, dilo."
)

# ── Enrutamiento a nube (señales de pregunta difícil) ────────────────────────
_CLOUD_HINTS = re.compile(
    r"\b(noticias|actualidad|últimas novedades|última hora|explica|explíca|por qué|porque "
    r"|profund|analiza|analític|diferencia.* entre|compara|compare|teoría|científ|históri|"
    r"argumenta|ensayo|filosofía|economía|geopol|medicina|teorema|integral|ecuación|"
    r"algoritmo|script que|programa que|escribe un código|refactoriza|depura)\b",
    re.IGNORECASE,
)

# ── Herramientas locales (subconjunto curado de las 245 tools de ERIS) ───────
_LOCAL_TOOLS = [
    {"type": "function", "function": {
        "name": "eris_time_now",
        "description": "Devuelve la hora y fecha actual del sistema.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "weather_report",
        "description": "Clima actual de una ciudad. Parámetro 'city' con el nombre de la ciudad.",
        "parameters": {"type": "object", "properties": {
            "city": {"type": "string", "description": "Ciudad (ej: Lima, Madrid)"},
        }, "required": ["city"]},
    }},
    {"type": "function", "function": {
        "name": "system_volume",
        "description": "Controla el volumen del sistema. 'action' puede ser get, set, up, down, mute, unmute, toggle_mute. 'level' 0-100 para set. 'step' para up/down.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string"}, "level": {"type": "integer"}, "step": {"type": "integer"},
        }, "required": ["action"]},
    }},
    {"type": "function", "function": {
        "name": "dashboard",
        "description": "Estado del sistema (CPU, RAM, disco). 'action' = system, eris o all.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string"},
        }, "required": ["action"]},
    }},
    {"type": "function", "function": {
        "name": "res_monitor",
        "description": "Monitor de recursos del sistema (CPU, RAM, disco, swap). 'action' = status.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string"},
        }},
    }},
    {"type": "function", "function": {
        "name": "db_knowledge",
        "description": "Busca conocimiento aprendido en la base de datos de ERIS. 'query' con el tema a buscar.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
        }, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "db_tasks",
        "description": "Gestiona tareas del usuario. 'action' = list, add, update, delete. 'task' texto de la tarea para add.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string"}, "task": {"type": "string"},
        }, "required": ["action"]},
    }},
    {"type": "function", "function": {
        "name": "reminder",
        "description": "Crea un recordatorio. 'text' del recordatorio.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string"},
        }, "required": ["text"]},
    }},
    {"type": "function", "function": {
        "name": "music_player",
        "description": "Controla el reproductor de música. 'action' = play, pause, stop, next, previous, status.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string"},
        }, "required": ["action"]},
    }},
    {"type": "function", "function": {
        "name": "calculator",
        "description": "Resuelve una operación matemática. 'expression' con la expresión (ej: '2+2*5').",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string"},
        }, "required": ["expression"]},
    }},
    {"type": "function", "function": {
        "name": "curiosity_joke",
        "description": "Cuenta un chiste.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "curiosity_fact",
        "description": "Cuenta un dato curioso.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Busca en internet. 'query' con la búsqueda.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
        }, "required": ["query"]},
    }},
]

# Errores de tools que no deben matar la conversación
_NATIVE_TOOLS = {"eris_time_now"}


def _load_cfg() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


class LocalBrain:
    """Cerebro dual: enruta entre Ollama local y OpenRouter (nube)."""

    def __init__(self):
        cfg = _load_cfg()
        self.model = cfg.get("local_brain_model", "") or "qwen3:8b"
        self.cloud_model = cfg.get("cloud_brain_model", "") or "google/gemini-2.5-pro"
        base = cfg.get("ollama_base_url", "") or "http://localhost:11434"
        self.ollama_url = base.rstrip("/")
        self.openrouter_key = cfg.get("openrouter_api_key", "")
        self._tools_enabled = str(cfg.get("local_tools_enabled", "true")).lower() != "false"

    # ── API pública ──────────────────────────────────────────────────────────
    def respond(self, text: str, player=None) -> str:
        """Procesa un mensaje del usuario y devuelve la respuesta de ERIS."""
        text = (text or "").strip()
        if not text:
            return ""
        route = self._route(text)
        if player:
            try:
                player.write_log(f"[dual] Ruta: {route} | texto: {text[:60]}")
            except Exception:
                pass
        try:
            if route == "cloud":
                return self._cloud(text, player)
            return self._local(text, player)
        except Exception as e:
            return f"Se produjo un error interno: {e}"

    # ── Enrutamiento ─────────────────────────────────────────────────────────
    def _route(self, text: str) -> str:
        if len(text) > 260:
            return "cloud"
        if _CLOUD_HINTS.search(text):
            return "cloud"
        return "local"

    # ── Cerebro nube (OpenRouter) ────────────────────────────────────────────
    def _cloud(self, text: str, player=None) -> str:
        if not self.openrouter_key:
            return self._local(text, player)
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "HTTP-Referer": "https://github.com/eris-beta",
            "X-Title": "ERIS AI Assistant",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.cloud_model,
            "max_tokens": 1200,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            if not content or not content.strip():
                raise ValueError("Respuesta vacía")
            return content.strip()
        except Exception:
            return self._local(text, player)

    # ── Cerebro local (Ollama + tools) ───────────────────────────────────────
    def _local(self, text: str, player=None) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        for _round in range(5):
            out = self._ollama_chat(messages)
            if out is None:
                return "El respaldo local no está disponible. Verificá que Ollama esté corriendo."
            content = out.get("content") or ""
            tool_calls = out.get("tool_calls") or []
            if not tool_calls:
                return content.strip() or "No pude generar una respuesta."
            # Ejecutar herramientas y continuar el bucle
            messages.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments") or {}
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {}
                elif isinstance(raw_args, dict):
                    args = raw_args
                else:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                result = self._run_tool(name, args, player)
                messages.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False)})
        return "He intentado resolverlo varias veces pero no llegué a una respuesta clara."

    def _ollama_chat(self, messages: list) -> dict | None:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": "30m",
        }
        if self._tools_enabled:
            payload["tools"] = _LOCAL_TOOLS
        req = urllib.request.Request(
            f"{self.ollama_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            msg = data.get("message", {})
            return {"content": msg.get("content"), "tool_calls": msg.get("tool_calls") or []}
        except Exception as e:
            return None

    # ── Ejecución de herramientas ────────────────────────────────────────────
    def _run_tool(self, name: str, args: dict, player=None):
        # Herramientas nativas (sin depender del registro)
        if name == "eris_time_now":
            return {"ok": True, "hora": datetime.now().strftime("%H:%M"), "fecha": datetime.now().strftime("%A %d de %B de %Y")}
        try:
            from core.tool_registry import get_tool
            tool = get_tool(name)
            if tool is None:
                return {"ok": False, "error": f"Herramienta '{name}' no disponible."}
            if player:
                try:
                    player.write_log(f"[dual] Tool: {name} {args}")
                except Exception:
                    pass
            result = tool(args, player)
            return {"ok": True, "resultado": str(result)}
        except Exception as e:
            return {"ok": False, "error": f"Error al ejecutar '{name}': {e}"}


# ── Singleton ────────────────────────────────────────────────────────────────
_brain: LocalBrain | None = None


def get_brain() -> LocalBrain:
    global _brain
    if _brain is None:
        _brain = LocalBrain()
    return _brain


def quick_check() -> bool:
    """Comprueba si el respaldo local está disponible (Ollama vivo)."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False
