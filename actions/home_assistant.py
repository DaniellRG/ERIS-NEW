# -*- coding: utf-8 -*-
"""
home_assistant.py — Integración con Home Assistant.
Acciones:
  states    — Estado de todas las entidades
  lights    — Control de luces (on/off/brightness/color)
  switch    — Encender/apagar switches
  climate   — Control de clima (temperatura, modo)
  media     — Control de medios (play/pause/vol)
  notify    — Enviar notificación a HA
  entities  — Buscar entidades
  service   — Llamar a cualquier servicio
Configuración en config/api_keys.json → home_assistant: {url, token}
"""
from __future__ import annotations

import json
import requests
from pathlib import Path
from typing import Any


def _get_config():
    cfg_path = Path(r"D:\Eris_Source\config\api_keys.json")
    if not cfg_path.exists():
        return {}
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return cfg.get("home_assistant", {})
    except Exception:
        return {}


def _ha_get(cfg, endpoint):
    url = f"{cfg['url'].rstrip('/')}/api/{endpoint}"
    headers = {"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def _ha_post(cfg, endpoint, data=None):
    url = f"{cfg['url'].rstrip('/')}/api/{endpoint}"
    headers = {"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json=data or {}, timeout=10)
    r.raise_for_status()
    return r.json() if r.text else {}


def home_assistant(parameters: dict = None, player=None) -> str:
    """Tool: Control de domótica vía Home Assistant."""
    params = parameters or {}
    action = str(params.get("action", "states")).lower().strip()
    cfg = _get_config()

    if not cfg.get("url") or not cfg.get("token"):
        return "Home Assistant no configurado. Agregá 'home_assistant' en config/api_keys.json con url y token."

    try:
        if action == "states":
            states = _ha_get(cfg, "states")
            max_entities = min(int(params.get("max_entities", 25)), 50)
            domain_filter = str(params.get("domain", "")).strip()
            filtered = states
            if domain_filter:
                filtered = [s for s in states if s["entity_id"].startswith(domain_filter)]
            filtered = filtered[:max_entities]
            if not filtered:
                return "Sin entidades" + (f" del dominio {domain_filter}" if domain_filter else "")
            lines = [f"**Entidades ({len(filtered)}):**\n"]
            for s in filtered:
                eid = s["entity_id"]
                state = s["state"]
                attrs = s.get("attributes", {})
                friendly = attrs.get("friendly_name", "")
                extra = ""
                if "brightness" in attrs:
                    extra = f" 💡{attrs['brightness']}"
                if "temperature" in attrs:
                    extra = f" 🌡️{attrs['temperature']}°"
                lines.append(f"• **{friendly}** ({eid}): {state}{extra}")
            return "\n".join(lines)

        if action == "lights":
            entity_id = str(params.get("entity_id", "")).strip()
            cmd = str(params.get("command", "toggle")).lower().strip()
            brightness = params.get("brightness")
            if not entity_id:
                states = _ha_get(cfg, "states")
                lights = [s for s in states if s["entity_id"].startswith("light.")]
                if not lights:
                    return "Sin luces encontradas."
                lines = ["**Luces:**\n"]
                for l in lights[:20]:
                    name = l.get("attributes", {}).get("friendly_name", l["entity_id"])
                    state = "🟢" if l["state"] == "on" else "⚫"
                    bri = l.get("attributes", {}).get("brightness", "")
                    lines.append(f"{state} {name} ({l['entity_id']})" + (f" {bri}/255" if bri else ""))
                return "\n".join(lines)
            data = {"entity_id": entity_id}
            if cmd == "on":
                if brightness is not None:
                    data["brightness"] = int(brightness)
                _ha_post(cfg, "services/light/turn_on", data)
                return f"💡 {entity_id} encendida"
            elif cmd == "off":
                _ha_post(cfg, "services/light/turn_off", data)
                return f"💡 {entity_id} apagada"
            else:
                _ha_post(cfg, "services/light/toggle", data)
                return f"💡 {entity_id} toggled"

        if action == "switch":
            entity_id = str(params.get("entity_id", "")).strip()
            cmd = str(params.get("command", "toggle")).lower().strip()
            if not entity_id:
                return "Necesitás entity_id. Ej: switch.cocina"
            data = {"entity_id": entity_id}
            svc = {"on": "turn_on", "off": "turn_off", "toggle": "toggle"}.get(cmd, "toggle")
            _ha_post(cfg, f"services/switch/{svc}", data)
            return f"🔌 {entity_id} → {cmd}"

        if action == "climate":
            entity_id = str(params.get("entity_id", "")).strip()
            temp = params.get("temperature")
            hvac_mode = str(params.get("mode", "")).strip()
            if not entity_id:
                states = _ha_get(cfg, "states")
                climates = [s for s in states if s["entity_id"].startswith("climate.")]
                if not climates:
                    return "Sin entidades climate."
                lines = ["**Clima:**\n"]
                for c in climates:
                    name = c.get("attributes", {}).get("friendly_name", c["entity_id"])
                    lines.append(f"• {name}: {c['state']} | 🌡️{c.get('attributes', {}).get('current_temperature', '?')}° → {c.get('attributes', {}).get('temperature', '?')}°")
                return "\n".join(lines)
            if temp:
                _ha_post(cfg, "services/climate/set_temperature", {"entity_id": entity_id, "temperature": float(temp)})
            if hvac_mode:
                _ha_post(cfg, "services/climate/set_hvac_mode", {"entity_id": entity_id, "hvac_mode": hvac_mode})
            return f"🌡️ {entity_id} actualizado"

        if action == "media":
            entity_id = str(params.get("entity_id", "")).strip()
            cmd = str(params.get("command", "toggle")).lower().strip()
            vol = params.get("volume")
            if not entity_id:
                states = _ha_get(cfg, "states")
                media = [s for s in states if s["entity_id"].startswith("media_player.")]
                if not media:
                    return "Sin media players."
                lines = ["**Media Players:**\n"]
                for m in media[:10]:
                    name = m.get("attributes", {}).get("friendly_name", m["entity_id"])
                    lines.append(f"• {name}: {m['state']}")
                return "\n".join(lines)
            if cmd in ("play", "pause", "stop", "toggle"):
                svc = {"play": "media_play", "pause": "media_pause", "stop": "media_stop", "toggle": "media_play_pause"}[cmd]
                _ha_post(cfg, f"services/media_player/{svc}", {"entity_id": entity_id})
            if vol is not None:
                _ha_post(cfg, "services/media_player/volume_set", {"entity_id": entity_id, "volume_level": float(vol) / 100})
            return f"🎵 {entity_id} → {cmd}"

        if action == "notify":
            message = str(params.get("message", "")).strip()
            title = str(params.get("title", "Eris")).strip()
            if not message:
                return "Necesitás un mensaje."
            _ha_post(cfg, "services/notify/notify", {"message": message, "title": title})
            return f"📢 Notificación enviada: {title}"

        if action == "entities":
            query = str(params.get("query", "")).lower().strip()
            if not query:
                return "Necesitás un término de búsqueda."
            states = _ha_get(cfg, "states")
            found = [s for s in states if query in s["entity_id"].lower() or query in s.get("attributes", {}).get("friendly_name", "").lower()][:20]
            if not found:
                return f"Sin resultados para '{query}'"
            lines = [f"**Entidades '{query}' ({len(found)}):**\n"]
            for s in found:
                lines.append(f"• {s['entity_id']}: {s['state']}")
            return "\n".join(lines)

        if action == "service":
            domain = str(params.get("domain", "")).strip()
            service_name = str(params.get("service", "")).strip()
            data = params.get("data", {})
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    data = {}
            if not domain or not service_name:
                return "Necesitás domain y service. Ej: domain='light' service='turn_on'"
            _ha_post(cfg, f"services/{domain}/{service_name}", data or {"entity_id": "all"})
            return f"✅ Servicio {domain}.{service_name} ejecutado"

    except Exception as e:
        return f"Error Home Assistant: {str(e)[:200]}"

    return "Acciones: states, lights, switch, climate, media, notify, entities, service"
