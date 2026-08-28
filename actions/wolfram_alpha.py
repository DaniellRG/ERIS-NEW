"""wolfram_alpha.py — Respuestas computacionales vía Wolfram Alpha. Requiere 'wolfram_app_id' en config/api_keys.json."""
import json
import os
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
API_KEYS_FILE = os.path.join(BASE_DIR, "config", "api_keys.json")
_BASE = "https://api.wolframalpha.com/v2"


def _get_key():
    try:
        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("wolfram_app_id", "")
    except Exception:
        return ""


def _translate_query(q: str) -> str:
    """Traducción heurística ES->EN para consultas comunes de Wolfram (que solo entiende inglés)."""
    import re
    s = q.strip()
    _phrases = [
        ("velocidad de la luz", "speed of light"),
        ("velocidad del sonido", "speed of sound"),
        ("constante de planck", "planck constant"),
        ("velocidad de escape", "escape velocity"),
        ("de la tierra", "of the earth"),
        ("de la luna", "of the moon"),
        ("de la", "of the"),
        ("del ", "of the "),
        ("de los", "of the"),
        ("de las", "of the"),
    ]
    for sp, en in _phrases:
        if sp in s.lower():
            s = re.sub(sp, en, s, flags=re.IGNORECASE)
    _words = {
        "masa": "mass", "tierra": "Earth", "luna": "Moon", "sol": "Sun",
        "gravedad": "gravity", "distancia": "distance", "fuerza": "force",
        "energia": "energy", "energía": "energy", "peso": "weight",
        "velocidad": "speed", "volumen": "volume", "densidad": "density",
        "area": "area", "área": "area", "perimetro": "perimeter", "perímetro": "perimeter",
    }
    for sp, en in _words.items():
        s = re.sub(rf"\b{sp}\b", en, s, flags=re.IGNORECASE)
    s = s.replace("% de ", "% of ")
    s = s.replace("por ciento de ", "% of ")
    s = s.replace("porciento de ", "% of ")
    s = s.replace("por ciento", "%")
    s = s.replace("porciento", "%")
    for pre in ("cuánto es ", "cuanto es ", "cual es ", "cuál es ", "qué es ", "que es ", "calcular "):
        if s.lower().startswith(pre):
            s = s[len(pre):]
            break
    s = s.rstrip("?.¿")
    s = s.strip()
    return s


def _fetch(url: str, timeout: int = 10):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_pods(xml: str) -> list[str]:
    import re
    results = []
    # Extraer <pod>...</pod> y de cada uno el primer <plaintext>
    for pod in re.findall(r"<pod[^>]*>(.*?)</pod>", xml, re.S):
        text = re.search(r"<plaintext[^>]*>(.*?)</plaintext>", pod, re.S)
        if text:
            val = text.group(1).strip()
            if val:
                results.append(val)
    return results


def wolfram_alpha(parameters: dict, player=None) -> str:
    """Responde preguntas computacionales: matemáticas, unidades, datos de ciencia."""
    key = _get_key()
    if not key:
        return ("Wolfram Alpha no configurado: falta 'wolfram_app_id' en config/api_keys.json. "
                "AppID gratis en https://products.wolframalpha.com/api")
    query = parameters.get("query") or parameters.get("question") or ""
    if not query.strip():
        return "Indicá la consulta con 'query' (ej. '15% de 800', 'masa de la Tierra')."
    try:
        q = urllib.parse.quote(_translate_query(query.strip()))
        url = f"{_BASE}/query?appid={key}&input={q}&format=plaintext&output=json"
        data = json.loads(_fetch(url))
        result = None
        pods = data.get("queryresult", {}).get("pods", [])
        # Priorizar el pod "Result" (respuesta directa), luego el primero útil
        for pod in pods:
            if pod.get("title", "").strip().lower() == "result":
                for sub in pod.get("subpods", []):
                    if sub.get("plaintext"):
                        result = sub["plaintext"]
                        break
                if result:
                    break
        if result is None:
            for pod in pods:
                for sub in pod.get("subpods", []):
                    if sub.get("plaintext"):
                        result = sub["plaintext"]
                        break
                if result:
                    break
        if result is None:
            return "Wolfram Alpha no encontró una respuesta para esa consulta."
        # Acotar a las primeras líneas útiles
        lines = [l for l in result.splitlines() if l.strip()][:6]
        msg = "\n".join(lines)
        if player:
            player.write_log(f"🧮 {msg[:300]}")
        return msg
    except Exception as e:
        return f"No pude consultar Wolfram Alpha: {e}"
