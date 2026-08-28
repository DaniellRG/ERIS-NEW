"""weather_report.py — Clima por ciudad. OpenWeather si hay key, fallback a wttr.in."""
import urllib.request
import urllib.parse
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
API_KEYS_FILE = os.path.join(BASE_DIR, "config", "api_keys.json")


def _get_cfg():
    try:
        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _openweather(city: str) -> str:
    cfg = _get_cfg()
    key = cfg.get("openweather_api_key", "")
    if not key:
        return None
    q = city if city else cfg.get("openweather_city", "Lima")
    url = (f"https://api.openweathermap.org/data/2.5/weather"
           f"?q={urllib.parse.quote(q)}&appid={key}&units=metric&lang=es")
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    main = data.get("main", {})
    temp = main.get("temp")
    feels = main.get("feels_like")
    hum = main.get("humidity")
    wind = data.get("wind", {}).get("speed")
    desc = (data.get("weather") or [{}])[0].get("description", "").title()
    parts = [f"Clima en {data.get('name', city)}: {desc}, {temp:.0f}°C"]
    if feels is not None:
        parts.append(f"(sensación {feels:.0f}°C)")
    if hum is not None:
        parts.append(f", humedad {hum}%")
    if wind is not None:
        parts.append(f", viento {wind:.1f} m/s")
    return "".join(parts)


def _wttrin(city: str) -> str:
    encoded_city = urllib.parse.quote(city)
    url = f"https://wttr.in/{encoded_city}?format=%C+%t+%h+%w"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=5) as response:
        data = response.read().decode("utf-8").strip()
    return f"Clima actual en {city}: {data}"


def weather_action(parameters: dict, player=None) -> str:
    """Clima por ciudad. Usa OpenWeather si está configurado, si no wttr.in."""
    city = parameters.get("city", "").strip() or "Lima"
    report = None
    try:
        report = _openweather(city)
    except Exception:
        report = None
    if not report:
        try:
            report = _wttrin(city)
        except Exception as e:
            msg = f"No pude obtener el clima de {city}: {e}"
            if player:
                player.write_log(f"⚠️ {msg}")
            return ("Tengo problemas para conectar con el servicio del clima ahora mismo. "
                    "Puedo buscar online si querés.")
    if player:
        player.write_log(f"🌤️ {report}")
    return report
