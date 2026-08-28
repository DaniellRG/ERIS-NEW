# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import hashlib
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(r"D:\Eris_Source\data\multi_ai_config.json")
API_KEYS_PATH = Path(r"D:\Eris_Source\config\api_keys.json")

DEFAULT_CONFIG = {
    "providers": {
        "ollama": {
            "enabled": True,
            "base_url": "http://localhost:11434",
            "models": ["qwen3:8b", "llama3:8b"],
            "priority": 1,
            "categories": ["chat", "general"],
            "max_tokens": 4096
        },
        "openrouter": {
            "enabled": True,
            "api_key": "",
            "base_url": "https://openrouter.ai/api/v1",
            "models": ["google/gemini-flash-latest"],
            "priority": 2,
            "categories": ["code", "analysis"],
            "max_tokens": 8192
        },
        "openai": {
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "models": ["gpt-4o-mini"],
            "priority": 3,
            "categories": ["creative", "translation"]
        },
        "anthropic": {
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.anthropic.com/v1",
            "models": ["claude-sonnet-4-20250514"],
            "priority": 4,
            "categories": ["code", "analysis"]
        }
    },
    "routing": {
        "code": ["openrouter", "ollama"],
        "chat": ["ollama", "openrouter"],
        "creative": ["openai", "openrouter"],
        "analysis": ["openrouter", "anthropic"],
        "translation": ["openai", "ollama"]
    }
}


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(json.dumps(DEFAULT_CONFIG))


def _save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _load_api_keys() -> dict:
    if API_KEYS_PATH.exists():
        with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _call_ollama(base_url: str, model: str, message: str, system: str = "") -> str:
    payload = {"model": model, "prompt": message, "stream": False}
    if system:
        payload["system"] = system
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("response", "")


def _call_openai_compatible(base_url: str, api_key: str, model: str, message: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 4096
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    if "openrouter.ai" in base_url:
        headers["HTTP-Referer"] = "https://eris-ai.local"
        headers["X-Title"] = "Eris AI"
    url = f"{base_url}/chat/completions"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def _call_anthropic(base_url: str, api_key: str, model: str, message: str, system: str = "") -> str:
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": message}]
    }
    if system:
        payload["system"] = system
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    url = f"{base_url}/messages"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["content"][0]["text"]


def _send_to_provider(provider_name: str, provider_cfg: dict, message: str, system: str = "", model_override: str = "") -> str:
    api_keys = _load_api_keys()
    model = model_override if model_override else (provider_cfg.get("models", [""])[0] if provider_cfg.get("models") else "")
    if not model:
        return "[Error] No model configured for this provider"
    base_url = provider_cfg.get("base_url", "")
    api_key = provider_cfg.get("api_key", "")
    if not api_key and provider_name in api_keys:
        api_key = api_keys[provider_name]
    if provider_name == "ollama":
        return _call_ollama(base_url, model, message, system)
    elif provider_name == "anthropic":
        return _call_anthropic(base_url, api_key, model, message, system)
    else:
        return _call_openai_compatible(base_url, api_key, model, message, system)


def _get_provider_status(provider_name: str, provider_cfg: dict) -> dict:
    if not provider_cfg.get("enabled", False):
        return {"name": provider_name, "enabled": False, "status": "disabled", "latency_ms": None}
    try:
        api_keys = _load_api_keys()
        api_key = provider_cfg.get("api_key", "")
        if not api_key and provider_name in api_keys:
            api_key = api_keys[provider_name]
        if provider_name == "ollama":
            base_url = provider_cfg.get("base_url", "http://localhost:11434")
            req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
            start = time.time()
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
            latency = int((time.time() - start) * 1000)
            return {"name": provider_name, "enabled": True, "status": "online", "latency_ms": latency}
        else:
            base_url = provider_cfg.get("base_url", "")
            model = provider_cfg.get("models", [""])[0] if provider_cfg.get("models") else ""
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            if "openrouter.ai" in base_url:
                headers["HTTP-Referer"] = "https://eris-ai.local"
                headers["X-Title"] = "Eris AI"
            req = urllib.request.Request(f"{base_url}/models", headers=headers, method="GET")
            start = time.time()
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            latency = int((time.time() - start) * 1000)
            return {"name": provider_name, "enabled": True, "status": "online", "latency_ms": latency}
    except Exception as e:
        return {"name": provider_name, "enabled": True, "status": f"error: {str(e)[:80]}", "latency_ms": None}


def _best_provider_for_task(task_type: str, config: dict) -> list[str]:
    routing = config.get("routing", {})
    providers = config.get("providers", {})
    chain = routing.get(task_type, [])
    result = []
    for pname in chain:
        pcfg = providers.get(pname, {})
        if pcfg.get("enabled", False):
            result.append(pname)
    if not result:
        enabled = [(pname, pcfg.get("priority", 99)) for pname, pcfg in providers.items() if pcfg.get("enabled", False)]
        enabled.sort(key=lambda x: x[1])
        result = [p[0] for p in enabled]
    return result


def tool_multi_ai_hub(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "status")
    config = _load_config()

    if action == "status":
        providers = config.get("providers", {})
        if not providers:
            return "No hay proveedores configurados."
        lines = ["=== Estado de proveedores IA ==="]
        for pname, pcfg in providers.items():
            st = _get_provider_status(pname, pcfg)
            model = pcfg.get("models", ["N/A"])[0] if pcfg.get("models") else "N/A"
            pri = pcfg.get("priority", "?")
            lines.append(f"  [{pname}] Estado: {st['status']} | Modelo: {model} | Prioridad: {pri} | Latencia: {st['latency_ms']}ms")
        return "\n".join(lines)

    elif action == "providers":
        providers = config.get("providers", {})
        if not providers:
            return "No hay proveedores configurados."
        lines = ["=== Proveedores disponibles ==="]
        for pname, pcfg in providers.items():
            enabled = "Activo" if pcfg.get("enabled", False) else "Inactivo"
            cats = ", ".join(pcfg.get("categories", []))
            models = ", ".join(pcfg.get("models", []))
            lines.append(f"  {pname} ({enabled}) - Categorias: {cats} | Modelos: {models}")
        return "\n".join(lines)

    elif action == "chat":
        message = parameters.get("message", "")
        if not message:
            return "Debes proporcionar un mensaje."
        provider = parameters.get("provider", "")
        model = parameters.get("model", "")
        system = parameters.get("system", "")
        providers = config.get("providers", {})
        if provider and provider in providers:
            pcfg = providers[provider]
            if not pcfg.get("enabled", False):
                return f"El proveedor '{provider}' está deshabilitado. Intenta con otro."
            try:
                response = _send_to_provider(provider, pcfg, message, system, model)
                return f"[{provider}] {response}"
            except Exception as e:
                return f"Error con {provider}: {str(e)}"
        else:
            chain = _best_provider_for_task("chat", config)
            last_error = ""
            for pname in chain:
                pcfg = providers.get(pname, {})
                if not pcfg.get("enabled", False):
                    continue
                try:
                    response = _send_to_provider(pname, pcfg, message, system, model)
                    return f"[{pname}] {response}"
                except Exception as e:
                    last_error = f"{pname}: {str(e)}"
                    continue
            if last_error:
                return f"Todos los proveedores fallaron. Ultimo error: {last_error}"
            return "No hay proveedores habilitados disponibles."

    elif action == "route":
        message = parameters.get("message", "")
        if not message:
            return "Debes proporcionar un mensaje."
        task_type = parameters.get("task_type", "chat")
        providers = config.get("providers", {})
        chain = _best_provider_for_task(task_type, config)
        if not chain:
            return f"No hay proveedores disponibles para la tarea '{task_type}'."
        last_error = ""
        for pname in chain:
            pcfg = providers.get(pname, {})
            if not pcfg.get("enabled", False):
                continue
            try:
                response = _send_to_provider(pname, pcfg, message)
                return f"[Enrutado a {pname} para {task_type}] {response}"
            except Exception as e:
                last_error = f"{pname}: {str(e)}"
                continue
        if last_error:
            return f"Fallo el enrutamiento. Ultimo error: {last_error}"
        return "No se pudo en ningun proveedor."

    elif action == "config":
        provider = parameters.get("provider", "")
        if not provider:
            return "Debes especificar un proveedor."
        providers = config.get("providers", {})
        if provider not in providers:
            providers[provider] = {
                "enabled": True,
                "api_key": "",
                "base_url": "",
                "models": [],
                "priority": 5,
                "categories": [],
                "max_tokens": 4096
            }
        pcfg = providers[provider]
        if "api_key" in parameters and parameters["api_key"]:
            pcfg["api_key"] = parameters["api_key"]
        if "model" in parameters and parameters["model"]:
            if parameters["model"] not in pcfg.get("models", []):
                pcfg.setdefault("models", []).append(parameters["model"])
        if "priority" in parameters:
            pcfg["priority"] = int(parameters["priority"])
        if "categories" in parameters:
            cats = parameters["categories"]
            if isinstance(cats, str):
                cats = [c.strip() for c in cats.split(",")]
            pcfg["categories"] = cats
        if "enabled" in parameters:
            pcfg["enabled"] = bool(parameters["enabled"])
        if "base_url" in parameters and parameters["base_url"]:
            pcfg["base_url"] = parameters["base_url"]
        config["providers"] = providers
        _save_config(config)
        return f"Proveedor '{provider}' configurado correctamente."

    elif action == "benchmark":
        providers = config.get("providers", {})
        test_prompt = "Responde solo con: OK"
        lines = ["=== Benchmark de proveedores ==="]
        for pname, pcfg in providers.items():
            if not pcfg.get("enabled", False):
                lines.append(f"  [{pname}] Omitido (deshabilitado)")
                continue
            try:
                start = time.time()
                response = _send_to_provider(pname, pcfg, test_prompt)
                elapsed = int((time.time() - start) * 1000)
                lines.append(f"  [{pname}] OK - {elapsed}ms - Respuesta: {response[:60]}")
            except Exception as e:
                lines.append(f"  [{pname}] ERROR - {str(e)[:80]}")
        return "\n".join(lines)

    elif action == "fallback":
        chain = parameters.get("chain", "")
        task_type = parameters.get("task_type", "chat")
        if chain:
            if isinstance(chain, str):
                chain = [c.strip() for c in chain.split(",")]
            config.setdefault("routing", {})[task_type] = chain
            _save_config(config)
            return f"Cadena de fallback para '{task_type}': {' -> '.join(chain)}"
        routing = config.get("routing", {})
        lines = ["=== Cadenas de fallback ==="]
        for ttype, chain_list in routing.items():
            lines.append(f"  {ttype}: {' -> '.join(chain_list)}")
        return "\n".join(lines)

    return f"Accion desconocida: {action}. Acciones disponibles: status, chat, providers, config, route, benchmark, fallback"
