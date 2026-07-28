import json
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
API_FILE = BASE_DIR / "config" / "api_keys.json"

def _get_api_key() -> str:
    if not API_FILE.exists():
        return ""
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return data.get("openrouter_api_key", "")
    except Exception:
        return ""

def _get_ollama_cfg() -> dict:
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return {
            "base_url": data.get("ollama_base_url", "http://localhost:11434"),
            "model": data.get("ollama_model", "phi"),
        }
    except Exception:
        return {"base_url": "http://localhost:11434", "model": "phi"}

def _chat_with_ollama(query: str) -> str:
    """Fallback local via Ollama (sin internet)."""
    cfg = _get_ollama_cfg()
    base_url = cfg["base_url"]
    model = cfg["model"]

    # Check if Ollama is available
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status != 200:
                return ""
    except Exception:
        return ""

    payload = {
        "model": model,
        "prompt": query,
        "system": "Eres un Agente Especialista delegado por ERIS. Responde de forma clara y directa en español.",
        "stream": False,
        "options": {
            "num_predict": 1500,
            "temperature": 0.3,
        }
    }

    try:
        req = urllib.request.Request(
            f"{base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", "")
    except Exception:
        return ""

def openrouter_agent(query: str, model: str = "google/gemini-2.5-flash") -> str:
    """
    Delega una tarea de texto compleja.
    Intenta OpenRouter primero, luego Ollama local como fallback.
    """
    # 1) Try OpenRouter (cloud)
    api_key = _get_api_key()
    if api_key:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/eris-beta",
            "X-Title": "ERIS AI Assistant",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "max_tokens": 1500,
            "messages": [
                {"role": "system", "content": "Eres un Agente Especialista delegado por ERIS. Responde de forma clara y directa en español."},
                {"role": "user", "content": query}
            ]
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    return response_data["choices"][0]["message"]["content"]
        except Exception:
            pass  # Fall through to Ollama
    
    # 2) Fallback: Ollama local (sin internet)
    result = _chat_with_ollama(query)
    if result:
        return f"[Local/Ollama] {result}"

    return "No hay ningún proveedor de IA disponible (OpenRouter sin API key, Ollama no corriendo)."
