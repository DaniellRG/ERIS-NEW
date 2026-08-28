"""
core/model_config.py
────────────────────
FUENTE ÚNICA DE VERDAD para los nombres de modelos Gemini de ERIS.

Problema que resuelve: Google retira modelos versionados (p.ej. `gemini-2.0-flash`,
`gemini-2.5-pro` dejaron de existir → error 404) y ERIS los tenía cableados en ~20
archivos, rompiéndose en cascada. Este módulo centraliza los nombres y usa por
DEFECTO aliases estables (`gemini-flash-latest`, `gemini-pro-latest`) que Google
mantiene apuntando siempre al modelo más nuevo → nunca se rompen por retiro.

Cómo funciona:
  - Cada "rol" (chat, fast, vision, pro, agent) tiene un default a prueba de futuro.
  - El usuario puede sobrescribir cualquier rol en `config/api_keys.json` con las
    claves `model_gemini_<rol>` (p.ej. `"model_gemini_chat": "gemini-3.6-flash"`).
  - `get_model(role)` → nombre para la API directa de Gemini (sin prefijo).
  - `get_or_model(role)` → nombre con prefijo `google/` para OpenRouter.
  - `chain(role)` → lista [preferido, ...fallbacks] para probar en orden.

Uso recomendado en el resto del código:
    from core.model_config import get_model
    resp = client.models.generate_content(model=get_model("chat"), contents=...)
"""
from __future__ import annotations

import json
from pathlib import Path

# ── Defaults a prueba de futuro (aliases *-latest que Google nunca retira) ─────
# El primero de cada lista es el preferido; el resto son fallbacks en orden.
_DEFAULT_CHAINS: dict[str, list[str]] = {
    # Conversación / respuestas rápidas de texto
    "chat":   ["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"],
    # Tareas ligeras / muy rápidas
    "fast":   ["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"],
    # Razonamiento pesado / calidad
    "pro":    ["gemini-pro-latest", "gemini-flash-latest"],
    # Agentes multi-paso
    "agent":  ["gemini-flash-latest", "gemini-3.1-flash-lite"],
    # Visión (imágenes / pantalla)
    "vision": ["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"],
    # Modelo LIVE de voz (bidiGenerateContent) — NO usa alias -latest
    "live":   ["gemini-3.1-flash-live-preview"],
}

_CFG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"


def _load_cfg() -> dict:
    try:
        return json.loads(_CFG_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def chain(role: str) -> list[str]:
    """
    Devuelve la lista [preferido, ...fallbacks] para un rol.
    Si el usuario definió `model_gemini_<rol>` en config, ese va primero
    (seguido de los fallbacks por defecto, para máxima resiliencia).
    """
    role = (role or "chat").lower()
    base = list(_DEFAULT_CHAINS.get(role, _DEFAULT_CHAINS["chat"]))
    cfg = _load_cfg()
    override = str(cfg.get(f"model_gemini_{role}", "")).strip()
    if override:
        # override primero, sin duplicar
        base = [override] + [m for m in base if m != override]
    return base


def get_model(role: str = "chat") -> str:
    """Nombre del modelo preferido para la API directa de Gemini (sin prefijo)."""
    return chain(role)[0]


def get_or_model(role: str = "chat") -> str:
    """Nombre del modelo preferido con prefijo `google/` para OpenRouter."""
    m = get_model(role)
    return m if m.startswith("google/") else f"google/{m}"


def all_roles() -> list[str]:
    return list(_DEFAULT_CHAINS.keys())


if __name__ == "__main__":
    for r in all_roles():
        print(f"{r:8s} -> {get_model(r):30s} | chain={chain(r)}")
