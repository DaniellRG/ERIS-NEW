import json
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_CONFIG = _BASE / "config" / "smart_home_config.json"

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False


def _default_config():
    return {
        "home_assistant": {"url": "", "token": ""},
        "mqtt": {"host": "", "port": 1883, "username": "", "password": "", "topic_prefix": "eris"},
        "simulate": True,
        "devices": [
            {"id": "light_living", "name": "Luz de sala", "type": "light", "location": "Sala", "entity_id": "light.living_room", "state": "off"},
            {"id": "light_bedroom", "name": "Luz de habitacion", "type": "light", "location": "Habitacion", "entity_id": "light.bedroom", "state": "off"},
            {"id": "ac_room", "name": "Aire acondicionado", "type": "climate", "location": "Habitacion", "entity_id": "climate.bedroom", "state": "off"},
            {"id": "tv_living", "name": "Televisor", "type": "switch", "location": "Sala", "entity_id": "switch.tv_living", "state": "off"},
            {"id": "cam_door", "name": "Camara de entrada", "type": "camera", "location": "Entrada", "entity_id": "camera.door", "state": "on"},
        ],
        "scenes": [],
    }


def _load_config():
    if not _CONFIG.exists():
        _default = _default_config()
        try:
            _CONFIG.write_text(json.dumps(_default, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return _default
    try:
        return json.loads(_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return _default_config()


def _save_config(cfg):
    try:
        _CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _find_device(cfg, name_or_id):
    q = (name_or_id or "").strip().lower()
    for d in cfg.get("devices", []):
        if d.get("id", "").lower() == q or d.get("name", "").lower() == q:
            return d
    return None


def _ha_base(cfg):
    return cfg.get("home_assistant", {}).get("url", "").rstrip("/")


def _ha_ready(cfg):
    ha = cfg.get("home_assistant", {})
    return bool(ha.get("url") and ha.get("token") and HAS_REQUESTS)


def _ha_headers(cfg):
    return {"Authorization": f"Bearer {cfg['home_assistant']['token']}", "Content-Type": "application/json"}


def _control_ha(cfg, device, state, params):
    domain = device.get("type") or "switch"
    service = "turn_on" if state == "on" else "turn_off"
    payload = {"entity_id": device.get("entity_id")}
    for k in ("brightness", "brightness_pct", "color_temp", "temperature", "volume"):
        if k in params:
            payload[k] = params[k]
    url = f"{_ha_base(cfg)}/api/services/{domain}/{service}"
    try:
        r = requests.post(url, json=payload, headers=_ha_headers(cfg), timeout=10)
        if r.status_code in (200, 201, 204):
            return True, None
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def _control_mqtt(cfg, device, state, params):
    if not HAS_MQTT:
        return False, "paho-mqtt no instalado"
    mq = cfg.get("mqtt", {})
    prefix = mq.get("topic_prefix", "eris")
    topic = f"{prefix}/{device.get('id', device.get('name', 'device'))}"
    if state == "on" and any(k in params for k in ("brightness", "temperature")):
        payload = json.dumps({"state": state, **{k: params[k] for k in ("brightness", "temperature", "volume") if k in params}})
    else:
        payload = "on" if state == "on" else "off"
    try:
        client = mqtt.Client()
        if mq.get("username"):
            client.username_pw_set(mq.get("username"), mq.get("password") or None)
        client.connect(mq["host"], int(mq.get("port", 1883)), 5)
        client.publish(topic, payload, qos=1, retain=True)
        client.disconnect()
        return True, None
    except Exception as e:
        return False, str(e)


def _status_text(cfg):
    lines = ["Estado de integracion domotica:"]
    if _ha_ready(cfg):
        try:
            r = requests.get(f"{_ha_base(cfg)}/api/", headers=_ha_headers(cfg), timeout=5)
            if r.status_code == 200:
                states = requests.get(f"{_ha_base(cfg)}/api/states", headers=_ha_headers(cfg), timeout=8)
                n = len(states.json()) if states.status_code == 200 else 0
                lines.append(f"Home Assistant: conectado ({_ha_base(cfg)}) - {n} entidades visibles")
            else:
                lines.append(f"Home Assistant: error HTTP {r.status_code}")
        except Exception as e:
            lines.append(f"Home Assistant: sin conexion ({e})")
    else:
        lines.append("Home Assistant: no configurado (agrega 'url' y 'token' en config/smart_home_config.json)")
    mq = cfg.get("mqtt", {})
    if mq.get("host"):
        lines.append(f"MQTT: configurado ({mq['host']}:{mq.get('port', 1883)}) - {'cliente OK' if HAS_MQTT else 'falta paho-mqtt'}")
    else:
        lines.append("MQTT: no configurado")
    lines.append(f"Modo simulacion: {'ACTIVO (sin dispositivos reales; los estados solo se prueban)' if cfg.get('simulate', False) else 'inactivo'}")
    return "\n".join(lines)


def _devices_text(cfg):
    devices = cfg.get("devices", [])
    if not devices:
        return "No hay dispositivos registrados."
    lines = [f"Dispositivos ({len(devices)}):"]
    for d in devices:
        state = "ON" if str(d.get("state", "off")).lower() in ("on", "1", "true") else "off"
        lines.append(f"- {d.get('name')} [{d.get('type')}] ({d.get('location')}) -> {state} (entity: {d.get('entity_id')})")
    return "\n".join(lines)


def _apply_state(cfg, device, state, params):
    device["state"] = state
    for k in ("brightness", "brightness_pct", "color_temp", "temperature", "volume"):
        if k in params:
            device[k] = params[k]
    _save_config(cfg)


def smart_home(parameters: dict, player=None) -> str:
    action = str(parameters.get("action", "status")).lower()
    cfg = _load_config()
    device_arg = parameters.get("name", parameters.get("device", parameters.get("id", "")))
    state = str(parameters.get("state", parameters.get("value", ""))).lower()

    if action in ("status", "test"):
        return _status_text(cfg)

    if action in ("devices", "list", "list_devices"):
        return _devices_text(cfg)

    if action in ("control", "set", "toggle"):
        if not device_arg:
            return "Error: indica el dispositivo con 'name' o 'id'. Ej: 'Enciende la luz de sala'."
        device = _find_device(cfg, device_arg)
        if not device:
            return f"Dispositivo '{device_arg}' no encontrado. Disponibles:\n{_devices_text(cfg)}"
        if action == "toggle":
            state = "off" if str(device.get("state", "off")).lower() in ("on", "1", "true") else "on"
        if state not in ("on", "off"):
            return f"Estado invalido '{state}'. Usa 'on' u 'off'."
        params = {k: parameters[k] for k in ("brightness", "brightness_pct", "color_temp", "temperature", "volume") if k in parameters}
        used = "simulacion"
        if _ha_ready(cfg):
            ok, err = _control_ha(cfg, device, state, params)
            if not ok:
                return f"Error en Home Assistant: {err}"
            used = "Home Assistant"
        elif cfg.get("mqtt", {}).get("host"):
            ok, err = _control_mqtt(cfg, device, state, params)
            if not ok:
                return f"Error en MQTT: {err}"
            used = "MQTT"
        elif cfg.get("simulate", False):
            _apply_state(cfg, device, state, params)
            extra = ""
            if params:
                extra = f" (ajustes: {', '.join(f'{k}={v}' for k, v in params.items())})"
            return f"Modo simulacion: {device.get('name')} -> {state.upper()}{extra}"
        else:
            return "No hay Home Assistant ni MQTT configurados. Configura config/smart_home_config.json o activa 'simulate'."
        _apply_state(cfg, device, state, params)
        return f"{device.get('name')} -> {state.upper()} (via {used})"

    if action in ("all_off", "apagar_todo"):
        done = []
        for d in cfg.get("devices", []):
            if d.get("type") in ("light", "switch", "climate"):
                d["state"] = "off"
                done.append(d.get("name"))
        _save_config(cfg)
        return f"Apagados: {', '.join(done)}" if done else "No hay dispositivos para apagar."

    if action in ("scene", "activate_scene"):
        scene_id = parameters.get("scene_id", parameters.get("scene", ""))
        scenes = cfg.get("scenes", [])
        target = next((s for s in scenes if str(s.get("id", "")) == str(scene_id) or str(s.get("name", "")) == str(scene_id)), None)
        if not target:
            names = [f"{s.get('name')} ({s.get('id')})" for s in scenes] or ["(ninguna configurada)"]
            return f"Escena '{scene_id}' no encontrada. Escenas disponibles: {', '.join(names)}"
        if _ha_ready(cfg) and target.get("entity_id"):
            try:
                r = requests.post(f"{_ha_base(cfg)}/api/services/scene/turn_on", json={"entity_id": target["entity_id"]}, headers=_ha_headers(cfg), timeout=10)
                return f"Escena '{target.get('name')}' activada en Home Assistant (HTTP {r.status_code})"
            except Exception as e:
                return f"Error al activar escena: {e}"
        return f"Escena '{target.get('name')}' activada (modo simulacion)."

    if action in ("add_device", "register_device"):
        name = parameters.get("name", "")
        if not name:
            return "Error: 'name' es obligatorio."
        new_id = parameters.get("id") or ("dev_" + name.lower().replace(" ", "_"))
        new_dev = {
            "id": new_id,
            "name": name,
            "type": parameters.get("type", "switch"),
            "location": parameters.get("location", "General"),
            "entity_id": parameters.get("entity_id", ""),
            "state": "off",
        }
        cfg.setdefault("devices", []).append(new_dev)
        _save_config(cfg)
        return f"Dispositivo registrado: {name} ({new_id})"

    return ("Acciones disponibles: status, devices, control (name/device + state on|off [+ brightness/temperature/volume]), "
            "all_off, scene (scene_id), add_device. Config: config/smart_home_config.json")
