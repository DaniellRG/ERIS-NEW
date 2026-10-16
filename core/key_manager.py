#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyManager — Auto-gestión de API keys de Eris.

Arquitectura:
  1. VALIDACIÓN: probamos keys on-the-fly antes de usarlas (ping → 200 = vivo).
  2. ROTACIÓN: si una key da 401, la marcamos vencida y la invalidamos via API
     (cuando el provider lo soporta — OpenRouter y xKiro lo permiten).
  3. CREACIÓN/SCOPING: Eris genera sub-keys efímeras (scoped, TTL) vía xKiro
     (que sí soporta scoped-token generation). Para providers que no lo soportan
     (Nous), Eris solicita una key nueva al usuario vía el canal /chat.
  4. FALLBACK: si no hay provider con scoping, Eris emite una solicitud al usuario
     con el motivo exacto ("necesito una key OpenRouter para acceder a claude-3").
"""
from __future__ import annotations
import json, os, time, sys, traceback
from pathlib import Path
from typing import Optional, Dict, Any, List

# ── Paths ──
_BASE = Path(__file__).resolve().parent.parent
_CONFIG = _BASE / "config" / "api_keys.json"
_BACKUP_DIR = _BASE / "config" / "key_backups"
_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# ── Providers configurables con capacidad de scoped-token ──
# Cada provider: endpoint base, endpoint de keys, método de creación
# 'scope_support': True = puede crear sub-keys vía API (solo xKiro en este momento)
# 'invalidation_support': True = puede invalidar keys vía API
_PROVIDERS = {
    "xkiro": {
        "base_url": "https://api.xkiro.com/v1",
        "keys_endpoint": "https://api.xkiro.com/v1/api-keys",
        "scope_support": True,          # <-- Eris PUEDE crear sub-keys acá
        "invalidation_support": True,
        "name": "xKiro",
        "free_models": [
            "deepseek/deepseek-chat",
            "z-ai/glm-4-flash",
            "nvidia/nemotron-4-340b-reward",
        ],
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "keys_endpoint": "https://openrouter.ai/api/v1/keys",
        "scope_support": False,         # OpenRouter NO crea sub-keys vía API
        "invalidation_support": True,
        "name": "OpenRouter",
        "free_models": ["meta-llama/llama-70b", "mistralai/mistral-7b"],
    },
    "nous": {
        "base_url": "https://inference-api.nousresearch.com/v1",
        "keys_endpoint": None,
        "scope_support": False,
        "invalidation_support": False,
        "name": "Nous Portal",
        "free_models": ["meituan/longcat-2.5-preview:free", "poolside/laguna-s-2.1:free"],
    },
}

# Key activa de xKiro (para scoped token creation)
_XKIRO_ADMIN_KEY = os.environ.get("XKIRO_API_KEY", "")

# Cache de validación (TTL en segundos)
_VALIDATION_CACHE: Dict[str, Dict] = {}
_CACHE_TTL = 60.0  # 1 minuto


def _load_config() -> dict:
    """Carga config/api_keys.json."""
    try:
        return json.loads(_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config(cfg: dict) -> None:
    """Guarda config, con backup previo."""
    try:
        # Backup rotativo (últimas 5)
        backup = _BACKUP_DIR / f"keys_{int(time.time())}.json"
        _CONFIG.replace(backup) if _CONFIG.exists() else None
        backups = sorted(_BACKUP_DIR.glob("keys_*.json"), reverse=True)
        for old in backups[5:]:
            old.unlink(missing_ok=True)
        _CONFIG.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[KeyManager] error guardando config: {e}", file=sys.stderr)


def _http(path: str, method: str = "GET", headers: Optional[Dict] = None,
          data: Optional[dict] = None, provider: str = "openrouter"):
    """HTTP minimalista (usa requests si está disponible, urllib como fallback)."""
    try:
        import requests
    except ImportError:
        import urllib.request, urllib.error
        url = f"{_PROVIDERS[provider]['base_url']}/{path}" if not path.startswith("http") else path
        req = urllib.request.Request(url, method=method)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        if data:
            body = json.dumps(data).encode()
            req.add_header("Content-Type", "application/json")
            req.data = body
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            code = resp.getcode()
            body = resp.read().decode()
            return code, body
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()
        except Exception as e:
            return 0, str(e)

    base = _PROVIDERS[provider]["base_url"]
    url = f"{base}/{path}" if not path.startswith("http") else path
    resp = requests.request(method, url, headers=headers,
                            json=data if data else None, timeout=15)
    return resp.status_code, resp.text


def validate_key(provider_key: str, provider: str = "openrouter") -> bool:
    """Valida una key contra el provider con un ping ligero (model list).

    Cachea resultado por _CACHE_TTL segundos para evitar throttling.
    """
    # Cache lookup
    cache_key = f"{provider}:{provider_key}"
    now = time.time()
    if cache_key in _VALIDATION_CACHE:
        entry = _VALIDATION_CACHE[cache_key]
        if now - entry["ts"] < _CACHE_TTL:
            return entry["valid"]

    prov = _PROVIDERS.get(provider)
    if not prov:
        _VALIDATION_CACHE[cache_key] = {"valid": False, "ts": now}
        return False

    code, body = _http("models", method="GET",
                       headers={"Authorization": f"Bearer {provider_key}"},
                       provider=provider)
    valid = 200 <= code < 300
    _VALIDATION_CACHE[cache_key] = {"valid": valid, "ts": now}
    return valid


def invalidate_key(provider_key: str, provider: str = "openrouter") -> bool:
    """Invalida (revoca) una key vía API si el provider lo soporta."""
    prov = _PROVIDERS.get(provider, {})
    if not prov.get("invalidation_support"):
        return False
    code, _ = _http("api-keys", method="POST",
                    headers={"Authorization": f"Bearer {provider_key}",
                             "Content-Type": "application/json"},
                    data={"key_id": "current"}, provider=provider)
    return code in (200, 204)


def request_scoped_key(provider: str = "xkiro", purpose: str = "",
                       ttl_minutes: int = 60) -> Optional[str]:
    """Crea un scoped sub-key efímero vía xKiro (la única provider con scope_support).

    NOTA: la mayoría de providers OpenAI-compatible (incluyendo xKiro) NO exponen
    un endpoint de creación de keys vía API — las keys se crean desde el dashboard
    web. Este método intenta varios endpoints comunes por si el provider lo soporta;
    si ninguno funciona, devuelve None → el caller (Eris) pide la key al usuario.

    Eris no puede CREAR keys desde cero sin el dashboard. Lo que SÍ puede:
      - validar keys on-the-fly (probar antes de usar)
      - detectar y marcar keys vencidas (401)
      - invalidar keys vencidas vía API (si el provider lo permite)
      - solicitar al usuario una key nueva vía el canal /chat con el motivo exacto
    """
    prov = _PROVIDERS.get(provider, {})
    if not prov.get("scope_support"):
        return None

    admin_key = _XKIRO_ADMIN_KEY or _load_config().get("xkairo_admin_key", "")
    if not admin_key:
        return None

    # Intentar varios endpoints comunes de scoped-key creation.
    # Cada proveedor usa un formato distinto; probamos los más frecuentes.
    candidates = [
        ("api-keys/create", {"name": f"eris-{purpose}-{int(time.time())}",
                             "expires_in": ttl_minutes * 60,
                             "scopes": ["chat", "models"]}),
        ("api-keys", {"name": f"eris-{purpose}",
                      "expires_in": ttl_minutes * 60,
                      "permissions": ["chat"]}),
        ("v1/api-keys", {"name": f"eris-{purpose}", "ttl": ttl_minutes}),
        ("keys/create", {"name": f"eris-{purpose}", "expires_in": ttl_minutes * 60}),
    ]
    for path, body in candidates:
        code, resp_body = _http(path, method="POST",
                                headers={"Authorization": f"Bearer {admin_key}",
                                         "Content-Type": "application/json"},
                                data=body, provider=provider)
        if 200 <= code < 300:
            try:
                data = json.loads(resp_body)
                new_key = data.get("key") or data.get("api_key") or data.get("token")
                if new_key:
                    cfg = _load_config()
                    cfg.setdefault("scoped_keys", {})[new_key] = {
                        "provider": provider,
                        "purpose": purpose,
                        "expires_at": time.time() + (ttl_minutes * 60),
                        "source": "auto-created",
                    }
                    _save_config(cfg)
                    return new_key
            except Exception:
                pass

    # Ningún endpoint soportado → no se puede crear scoped key vía API.
    # Eris deberá solicitar una key al usuario (resolve_key lo maneja).
    return None


def get_working_key(preferred_provider: str = "openrouter",
                    purpose: str = "") -> Optional[dict]:
    """Devuelve la mejor key disponible para un provider.

    Prioridad:
      1. Key explícita en config para ese provider (validada on-the-fly).
      2. Scoped sub-key auto-creada (solo xKiro).
      3. None → el caller (Eris) pide al usuario vía /chat.
    """
    cfg = _load_config()

    # 1. Key principal del provider
    key_field = {"openrouter": "openrouter_api_key",
                 "xkiro": "xkairo_admin_key",   # xKiro usa la key admin para todo
                 "nous": "openrouter_api_key"}.get(preferred_provider)
    if key_field:
        key = cfg.get(key_field, "")
        if key and validate_key(key, preferred_provider):
            return {"key": key, "provider": preferred_provider, "source": "config"}

    # 2. Scoped key (auto-creada)
    scoped = cfg.get("scoped_keys", {})
    now = time.time()
    for k, info in scoped.items():
        if info.get("provider") == preferred_provider:
            if info.get("expires_at", 0) > now and validate_key(k, preferred_provider):
                return {"key": k, "provider": preferred_provider, "source": "scoped"}
            # Expirada → limpiar
            scoped.pop(k, None)
    if scoped != cfg.get("scoped_keys", {}):
        _save_config(cfg)

    # 3. Intentar crear scoped (solo xKiro soporta)
    if _PROVIDERS.get(preferred_provider, {}).get("scope_support"):
        new_key = request_scoped_key(preferred_provider, purpose)
        if new_key:
            return {"key": new_key, "provider": preferred_provider,
                    "source": "auto-created"}

    return None  # → Eris pide al usuario


def request_key_from_user(purpose: str, provider: str = "openrouter",
                          reason: str = "") -> str:
    """Genera el mensaje que Eris enviará al usuario para pedir una key nueva.

    Se invierte vía el canal /chat (HTTP POST) o CLI.
    """
    prov_name = _PROVIDERS.get(provider, {}).get("name", provider)
    msg = (
        f"🔑 Necesito una API key nueva para {prov_name} ({provider}).\n"
        f"Motivo: {reason or purpose}\n"
        f"Podés crear una en el dashboard y pasármela por acá.\n"
        f"Mientras, usaré fallbacks."
    )
    return msg


# Anti-spam (auditoría 2026-10-15, MEDIA M7): los llamadores resolvían la key en
# CADA turno al armar la config de chat y volvían a imprimir el pedido → el log
# se llenaba de repetidos. `should_announce()` deja avisar UNA vez por proveedor
# cada cooldown (y vuelve a avisar recién si sigue faltando la key).
_LAST_ANNOUNCE: dict[str, float] = {}
_ANNOUNCE_COOLDOWN = 6 * 3600  # 6 h


def should_announce(provider: str) -> bool:
    """True si corresponde anunciar el pedido de key de `provider` (throttle)."""
    import time as _t
    now = _t.time()
    if now - _LAST_ANNOUNCE.get(provider, 0.0) >= _ANNOUNCE_COOLDOWN:
        _LAST_ANNOUNCE[provider] = now
        return True
    return False


def rotate_on_401(provider: str, old_key: str) -> Optional[dict]:
    """Reacciona a un 401: invalida la key (si se puede) y busca reemplazo."""
    prov = _PROVIDERS.get(provider, {})
    # Intentar invalidar la key vencida
    if prov.get("invalidation_support"):
        try:
            invalidate_key(old_key, provider)
        except Exception:
            pass

    # Buscar key de reemplazo (scoped o pedir al user)
    replacement = get_working_key(preferred_provider=provider,
                                  purpose="rotation-after-401")
    if replacement:
        return replacement
    return None  # → Eris pide al usuario


# ── Interfaz para que el dispatcher Eris la llame ──
def resolve_key(provider: str = "openrouter", purpose: str = "") -> dict:
    """Entry point principal: resuelve una key válida o devuelve instrucciones
    para pedir una al usuario.

    Returns: {"key": "...", "provider": "...", "source": "..."}  OR
             {"need_user_input": True, "message": "..."}
    """
    result = get_working_key(preferred_provider=provider, purpose=purpose)
    if result:
        return result

    # Ninguna key disponible → pedir al usuario
    reason = {
        "xkiro": "acceso a modelos premium (Claude, GPT-5)",
        "openrouter": "acceso a modelos premium (Claude, GPT-5)",
        "nous": "backend principal de Nous Portal",
    }.get(provider, "acceso a modelos")
    return {
        "need_user_input": True,
        "message": request_key_from_user(purpose, provider, reason),
        "provider": provider,
    }
