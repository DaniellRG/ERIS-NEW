"""
rgb_control.py - Control real de iluminacion RGB.

Backends soportados (en orden de preferencia):
  1. OpenRGB   - cliente local (openrgb-python) en 127.0.0.1:6742 (requiere la app OpenRGB con SDK habilitado)
  2. WLED      - tira de LEDs por HTTP (http://<ip>/json/state)
  3. Simulacion - sin hardware: registra estado en config/rgb_config.json (honesto)

Acciones: status, devices, set, off, brightness, scene, effect, add_device, remove_device, config.
"""
import json
import time
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor
    HAS_OPENRGB = True
except ImportError:
    HAS_OPENRGB = False

_BASE = Path(__file__).resolve().parent.parent
_CONFIG = _BASE / "config" / "rgb_config.json"

_SCENES = {
    "alive": [(255, 255, 255), (0, 255, 255), (255, 0, 255), (255, 255, 0)],
    "fuego": [(255, 80, 0), (255, 120, 0), (255, 60, 0), (200, 40, 0)],
    "frio": [(0, 120, 255), (0, 160, 255), (60, 60, 255), (0, 200, 255)],
    "pastel": [(255, 180, 200), (180, 220, 255), (200, 255, 200), (255, 230, 180)],
    "noche": [(20, 20, 40), (10, 10, 30), (30, 30, 60), (15, 15, 45)],
}


def _default_config():
    return {
        "backend": "auto",
        "openrgb_host": "127.0.0.1",
        "openrgb_port": 6742,
        "wled_ip": "",
        "wled_port": 80,
        "devices": [],
        "simulate": True,
        "current": {"color": None, "brightness": 100, "effect": None},
    }


def _load_config():
    if not _CONFIG.exists():
        cfg = _default_config()
        try:
            _CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return cfg
    try:
        cfg = json.loads(_CONFIG.read_text(encoding="utf-8"))
        base = _default_config()
        base.update(cfg)
        return base
    except Exception:
        return _default_config()


def _save_config(cfg):
    try:
        _CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _parse_color(color):
    """Acepta 'red', 'red,green,blue', '#FF0000', '255,0,0'."""
    if not color:
        return None
    c = str(color).strip()
    named = {
        "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255),
        "white": (255, 255, 255), "yellow": (255, 255, 0), "cyan": (0, 255, 255),
        "magenta": (255, 0, 255), "orange": (255, 165, 0), "purple": (128, 0, 255),
        "pink": (255, 105, 180), "aqua": (0, 255, 200), "gold": (255, 215, 0),
    }
    if c.lower() in named:
        return named[c.lower()]
    if c.startswith("#"):
        try:
            c = c.lstrip("#")
            if len(c) == 6:
                return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
            if len(c) == 3:
                return tuple(int(x * 2, 16) for x in c)
        except ValueError:
            return None
    parts = [p.strip() for p in c.split(",")]
    if len(parts) == 3:
        try:
            return tuple(max(0, min(255, int(p))) for p in parts)
        except ValueError:
            return None
    return None


def _config_host():
    return _load_config().get("openrgb_host", "127.0.0.1")


def _config_port():
    return int(_load_config().get("openrgb_port", 6742))


def _detect_backend(cfg):
    if cfg.get("backend") in ("openrgb", "wled", "simulate"):
        return cfg["backend"]
    if HAS_OPENRGB:
        try:
            client = OpenRGBClient(cfg["openrgb_host"], cfg["openrgb_port"], timeout=2)
            client.disconnect()
            return "openrgb"
        except Exception:
            pass
    if cfg.get("wled_ip") and HAS_REQUESTS:
        try:
            r = requests.get(f"http://{cfg['wled_ip']}:{cfg['wled_port']}/json/info", timeout=2)
            if r.status_code == 200:
                return "wled"
        except Exception:
            pass
    return "simulate"


# -- Backend: OpenRGB --

def _openrgb_set_color(devices, rgb):
    client = OpenRGBClient(_config_host(), _config_port(), timeout=5)
    try:
        targets = [d for d in client.devices if not devices or d.name in devices]
        if not targets:
            targets = client.devices
        for dev in targets:
            for led in dev.leds:
                led.set_color(RGBColor(*rgb))
        return len(targets)
    finally:
        client.disconnect()


def _openrgb_set_brightness(devices, brightness):
    client = OpenRGBClient(_config_host(), _config_port(), timeout=5)
    try:
        targets = [d for d in client.devices if not devices or d.name in devices]
        if not targets:
            targets = client.devices
        for dev in targets:
            for led in dev.leds:
                c = led.colors[0]
                factor = brightness / 100.0
                led.set_color(RGBColor(int(c.red * factor), int(c.green * factor), int(c.blue * factor)))
        return len(targets)
    finally:
        client.disconnect()


def _openrgb_off(devices):
    return _openrgb_set_color(devices, (0, 0, 0))


def _openrgb_device_list():
    client = OpenRGBClient(_config_host(), _config_port(), timeout=5)
    try:
        return [d.name for d in client.devices]
    finally:
        client.disconnect()


# -- Backend: WLED --

def _wled_url(cfg, path=""):
    return f"http://{cfg['wled_ip']}:{cfg['wled_port']}{path}"


def _wled_set_color(cfg, rgb):
    payload = {"seg": [{"col": [[rgb[0], rgb[1], rgb[2]]], "on": True}]}
    r = requests.post(_wled_url(cfg, "/json/state"), json=payload, timeout=5)
    return r.status_code in (200, 201)


def _wled_set_brightness(cfg, brightness):
    r = requests.post(_wled_url(cfg, "/json/state"), json={"bri": int(brightness)}, timeout=5)
    return r.status_code in (200, 201)


def _wled_off(cfg):
    r = requests.post(_wled_url(cfg, "/json/state"), json={"on": False}, timeout=5)
    return r.status_code in (200, 201)


# -- Simulacion --

def _sim_state(cfg, key, value):
    cfg.setdefault("current", {})
    cfg["current"][key] = value
    _save_config(cfg)


def _status(cfg, backend):
    devices = []
    if backend == "openrgb":
        try:
            devices = _openrgb_device_list()
        except Exception as e:
            devices = [f"error: {e}"]
    elif backend == "wled":
        devices = [f"WLED {cfg.get('wled_ip')}"]
    else:
        devices = [d.get("name", d.get("id", "device")) for d in cfg.get("devices", [])]

    cur = cfg.get("current", {})
    lines = [
        "=== RGB CONTROL ===",
        f"  Backend:      {backend}",
        f"  Dispositivos: {len(devices)}",
    ]
    for d in devices[:10]:
        lines.append(f"    - {d}")
    if cur.get("color"):
        lines.append(f"  Color:        {cur['color']}")
    if cur.get("brightness"):
        lines.append(f"  Brillo:       {cur['brightness']}%")
    if cur.get("effect"):
        lines.append(f"  Efecto:       {cur['effect']}")
    lines.append("  Escenas:      " + ", ".join(sorted(_SCENES.keys())))
    lines.append("  Backends:     auto, openrgb, wled, simulate")
    lines.append("  Acciones:     status, devices, set, off, brightness, scene, effect, add_device, remove_device, config")
    return "\n".join(lines)


def _set_backend(cfg, params):
    target = str(params.get("backend") or "").strip().lower()
    if target not in ("auto", "openrgb", "wled", "simulate"):
        return f"Backend invalido: {target}. Usa: auto, openrgb, wled, simulate"
    cfg["backend"] = target
    if params.get("wled_ip"):
        cfg["wled_ip"] = params["wled_ip"]
    if params.get("openrgb_host"):
        cfg["openrgb_host"] = params["openrgb_host"]
    _save_config(cfg)
    return f"Backend configurado: {target}"


def rgb_control(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action") or "status").lower().strip()
    cfg = _load_config()

    if action == "config":
        return _set_backend(cfg, params)

    if action == "devices":
        backend = _detect_backend(cfg)
        if backend == "openrgb":
            try:
                devs = _openrgb_device_list()
                return "Dispositivos OpenRGB:\n  " + "\n  ".join(devs) if devs else "Sin dispositivos OpenRGB"
            except Exception as e:
                return f"Error OpenRGB: {e}"
        if backend == "wled":
            return f"WLED en {cfg.get('wled_ip')}:{cfg.get('wled_port')}"
        devs = cfg.get("devices", [])
        if not devs:
            return "Simulacion: sin dispositivos. Usa 'add_device name=Mi RGB' para crear uno."
        return "Dispositivos simulados:\n  " + "\n  ".join(f"{d.get('name', d.get('id'))}" for d in devs)

    if action == "status":
        return _status(cfg, _detect_backend(cfg))

    if action == "set":
        color = _parse_color(params.get("color"))
        if color is None:
            return "Color invalido. Ejemplos: 'red', '#FF8800', '0,255,0'"
        backend = _detect_backend(cfg)
        device_names = params.get("device")
        devices = [device_names] if device_names else []
        try:
            if backend == "openrgb" and HAS_OPENRGB:
                count = _openrgb_set_color(devices, color)
                _sim_state(cfg, "color", str(color))
                _sim_state(cfg, "effect", None)
                return f"RGB seteado a {color} en {count} dispositivo(s) (OpenRGB)"
            if backend == "wled":
                if _wled_set_color(cfg, color):
                    _sim_state(cfg, "color", str(color))
                    _sim_state(cfg, "effect", None)
                    return f"RGB seteado a {color} (WLED)"
                return "Error enviando color a WLED"
            _sim_state(cfg, "color", str(color))
            _sim_state(cfg, "effect", None)
            return f"[simulacion] Color seteado a {color}. Configura OpenRGB o WLED para control real (action=config)."
        except Exception as e:
            return f"Error al setear color: {e}"

    if action == "off":
        backend = _detect_backend(cfg)
        device_names = params.get("device")
        devices = [device_names] if device_names else []
        try:
            if backend == "openrgb" and HAS_OPENRGB:
                count = _openrgb_off(devices)
                _sim_state(cfg, "color", None)
                return f"RGB apagado en {count} dispositivo(s)"
            if backend == "wled":
                if _wled_off(cfg):
                    _sim_state(cfg, "color", None)
                    return "WLED apagado"
                return "Error apagando WLED"
            _sim_state(cfg, "color", None)
            return "[simulacion] RGB apagado."
        except Exception as e:
            return f"Error al apagar: {e}"

    if action in ("brightness", "brillo"):
        try:
            brightness = max(0, min(100, int(params.get("brightness", params.get("value", 100)))))
        except (ValueError, TypeError):
            return "Brillo invalido (0-100)"
        backend = _detect_backend(cfg)
        try:
            if backend == "openrgb" and HAS_OPENRGB:
                count = _openrgb_set_brightness([], brightness)
                _sim_state(cfg, "brightness", brightness)
                return f"Brillo seteado a {brightness}% en {count} dispositivo(s)"
            if backend == "wled":
                if _wled_set_brightness(cfg, brightness):
                    _sim_state(cfg, "brightness", brightness)
                    return f"WLED brillo -> {brightness}%"
                return "Error enviando brillo a WLED"
            _sim_state(cfg, "brightness", brightness)
            return f"[simulacion] Brillo seteado a {brightness}%."
        except Exception as e:
            return f"Error al setear brillo: {e}"

    if action == "scene":
        scene = str(params.get("scene") or params.get("name") or "").lower().strip()
        if scene not in _SCENES:
            return f"Escena invalida. Disponibles: {', '.join(sorted(_SCENES.keys()))}"
        backend = _detect_backend(cfg)
        try:
            if backend in ("openrgb", "wled"):
                for rgb in _SCENES[scene]:
                    if backend == "openrgb":
                        _openrgb_set_color([], rgb)
                    else:
                        _wled_set_color(cfg, rgb)
                    time.sleep(0.4)
            _sim_state(cfg, "color", f"scene:{scene}")
            _sim_state(cfg, "effect", scene)
            return f"Escena '{scene}' aplicada ({backend})."
        except Exception as e:
            return f"Error aplicando escena: {e}"

    if action == "effect":
        effect = str(params.get("effect") or params.get("name") or "").lower().strip()
        if effect in ("rainbow", "breath", "wave"):
            backend = _detect_backend(cfg)
            _sim_state(cfg, "effect", effect)
            if backend in ("openrgb", "wled"):
                return f"Efecto '{effect}' solicitado en {backend}. Para efectos persistentes configura la escena desde la app (OpenRGB/WLED)."
            return f"[simulacion] Efecto '{effect}' activado (requiere backend real para verse)."
        return "Efectos: rainbow, breath, wave"

    if action in ("add_device", "remove_device"):
        name = str(params.get("name") or params.get("device") or "").strip()
        if not name:
            return "Se requiere 'name' para add_device/remove_device"
        devices = cfg.setdefault("devices", [])
        if action == "add_device":
            if any(d.get("name") == name or d.get("id") == name for d in devices):
                return f"Dispositivo '{name}' ya existe"
            devices.append({"id": f"rgb_{len(devices) + 1}", "name": name, "type": "rgb"})
            _save_config(cfg)
            return f"Dispositivo simulado '{name}' agregado"
        devices[:] = [d for d in devices if d.get("name") != name and d.get("id") != name]
        _save_config(cfg)
        return f"Dispositivo '{name}' eliminado"

    return "Acciones: status, devices, set, off, brightness, scene, effect, add_device, remove_device, config"
