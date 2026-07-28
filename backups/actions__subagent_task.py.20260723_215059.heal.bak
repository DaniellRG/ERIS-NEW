"""subagent_task.py — Lanza un subagente autónomo vía OpenRouter para tareas complejas."""
import json
import urllib.request
import urllib.error
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
API_FILE = BASE_DIR / "config" / "api_keys.json"
RESULTS = {}
_LOCK = threading.Lock()

SYSTEM_PROMPTS = {
    "research": "Eres un investigador autónomo. Busca información detallada y precisa sobre el tema solicitado. Responde en español con datos concretos.",
    "analyze": "Eres un analista de datos. Examina la información proporcionada y entrega un análisis estructurado con conclusiones claras.",
    "code": "Eres un programador experto. Escribe código funcional y bien estructurado según lo solicitado. Incluye solo el código necesario.",
    "write": "Eres un escritor creativo. Redacta contenido claro, bien estructurado y atractivo según lo solicitado.",
    "general": "Eres un agente autónomo delegado por ERIS. Completa la tarea asignada de forma eficiente y entrega resultados claros.",
}

def _get_api_key() -> str:
    if not API_FILE.exists():
        return ""
    try:
        data = json.loads(API_FILE.read_text("utf-8"))
        return data.get("openrouter_api_key", "")
    except Exception:
        return ""

def subagent_task(parameters: dict, player=None) -> str:
    task = parameters.get("task", "").strip()
    mode = parameters.get("mode", "general").strip().lower()
    model = parameters.get("model", "google/gemini-2.5-flash")
    wait = bool(parameters.get("wait", True))
    task_id = parameters.get("task_id", "").strip()

    # Solo task_id: recuperar resultado de background
    if not task and task_id:
        with _LOCK:
            if task_id in RESULTS:
                r = RESULTS.pop(task_id)
                return r
        return f"El subagente {task_id} aún está trabajando o no existe."

    if not task:
        return "Descripción de tarea requerida."

    # Background: lanzar y devolver task_id
    if not wait:
        if not task_id:
            import uuid
            task_id = uuid.uuid4().hex[:8]
        threading.Thread(target=_run_subagent, args=(task_id, task, mode, model, player), daemon=True).start()
        return f"🧠 Subagente lanzado en segundo plano. task_id: {task_id}. Llama subagent_task con solo task_id={task_id} para obtener resultado."

    # Sincrónico: esperar resultado
    return _run_subagent(task_id or "direct", task, mode, model, player)

def _run_subagent(task_id, task, mode, model, player=None):
    api_key = _get_api_key()
    if not api_key:
        result = "No hay API key de OpenRouter en config/api_keys.json."
        with _LOCK:
            RESULTS[task_id] = result
        if player:
            player.write_log(f"🧠 Subagente {task_id}: {result}")
        return result

    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["general"])
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/eris-beta",
        "X-Title": "ERIS SubAgent",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 2000,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ],
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
            if "choices" in data and data["choices"]:
                result = data["choices"][0]["message"]["content"]
            else:
                result = f"Respuesta inesperada: {json.dumps(data)[:500]}"
    except urllib.error.HTTPError as e:
        result = f"HTTP {e.code}: {e.read().decode('utf-8')[:500]}"
    except Exception as e:
        result = f"Error: {e}"

    with _LOCK:
        RESULTS[task_id] = result
    if player:
        player.write_log(f"🧠 Subagente {task_id} ({mode}) completado: {len(result)} chars")
    return result
