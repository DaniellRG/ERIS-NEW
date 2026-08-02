# -*- coding: utf-8 -*-
"""
setup_integrations.py — Asistente para conectar integraciones de ERIS.

Que obtiene el usuario (gratis, en pocos minutos):
  1. Telegram Bot Token   ->  habla con @BotFather en Telegram: /newbot
  2. OpenWeather API Key  ->  https://home.openweathermap.org/api_keys  (opcional, el clima ya funciona con wttr.in)
  3. TMDB API Key         ->  https://www.themoviedb.org/settings/api  (opcional)
  4. Email (Gmail)        ->  https://myaccount.google.com/apppasswords  (requiere 2FA activado)

Uso:
  .venv\\Scripts\\python.exe config\\setup_integrations.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CFG_PATH = BASE_DIR / "config" / "api_keys.json"
EMAIL_CFG_PATH = BASE_DIR / "config" / "email_credentials.json"


def _load_cfg() -> dict:
    if not CFG_PATH.exists():
        return {}
    try:
        return json.loads(CFG_PATH.read_text(encoding="utf-8-sig"))
    except Exception as e:
        print(f"[!] No se pudo leer api_keys.json: {e}")
        sys.exit(1)


def _save_cfg(cfg: dict):
    CFG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print("[OK] api_keys.json guardado.")


def _ask(label: str, key: str, current: str = "", secret: bool = False):
    cur = str(current or "").strip()
    prompt = f"  {label}"
    if cur:
        prompt += f" (actual: {cur[:8]}...)" if secret and cur else f" (actual: {cur})"
    print(prompt + ":")
    value = input("  > ").strip()
    if not value and cur:
        value = cur
    return value


def _test_telegram(token: str) -> bool:
    if not token:
        return False
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        if data.get("ok"):
            bot = data["result"].get("username", "?")
            print(f"  [OK] Bot de Telegram conectado: @{bot}")
            return True
        print(f"  [!] Telegram respondio pero no fue ok: {data}")
    except Exception as e:
        print(f"  [!] No se pudo conectar a Telegram: {e}")
    return False


def _setup_email():
    if EMAIL_CFG_PATH.exists():
        try:
            existing = json.loads(EMAIL_CFG_PATH.read_text(encoding="utf-8"))
            print(f"  Credenciales de email ya existen: {existing.get('email','')}")
        except Exception:
            existing = {}
    else:
        existing = {}
        print("  (Gmail: usa una CONTRASEÑA DE APLICACION, no tu contraseña normal)")
    email = _ask("Email (Gmail)", "email", str(existing.get("email", "")))
    if email:
        app_pw = _ask("Contraseña de aplicación", "password", "", secret=True)
        imap = _ask("Servidor IMAP", "imap_server", existing.get("imap_server", "imap.gmail.com"))
        smtp = _ask("Servidor SMTP", "smtp_server", existing.get("smtp_server", "smtp.gmail.com"))
        data = {
            "email": email,
            "password": app_pw,
            "imap_server": imap,
            "smtp_server": smtp,
            "imap_port": existing.get("imap_port", 993),
            "smtp_port": existing.get("smtp_port", 587),
        }
        EMAIL_CFG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print("[OK] email_credentials.json guardado.")
    else:
        print("  (Omitido)")


def main():
    print("=" * 60)
    print("  ERIS - Asistente de integraciones")
    print("=" * 60)
    cfg = _load_cfg()

    print("\n1) TELEGRAM (opcional)")
    print("   Paso 1: habla con @BotFather en Telegram y crea un bot con /newbot")
    print("   Paso 2: copia el token que te da (formato 123456:ABC...)\n")
    tok = _ask("Token del bot", "telegram_bot_token", cfg.get("telegram_bot_token", ""), secret=True)
    if tok:
        cfg["telegram_bot_token"] = tok
        _test_telegram(tok)
    _save_cfg(cfg)

    print("\n2) OPENWEATHER (opcional, el clima ya funciona con wttr.in)")
    owa = _ask("OpenWeather API Key", "openweather_api_key", cfg.get("openweather_api_key", ""), secret=True)
    if owa:
        cfg["openweather_api_key"] = owa
    _save_cfg(cfg)

    print("\n3) TMDB (opcional, para recomendaciones de cine)")
    tmdb = _ask("TMDB API Key (v3)", "tmdb_api_key", cfg.get("tmdb_api_key", ""), secret=True)
    if tmdb:
        cfg["tmdb_api_key"] = tmdb
    _save_cfg(cfg)

    print("\n4) EMAIL (opcional, Gmail IMAP/SMTP)")
    _setup_email()

    print("\n" + "=" * 60)
    print("  Configuracion finalizada. Reinicia ERIS para aplicar los cambios.")
    print("  Herramientas que se activaran: telegram_bot, email_manager, gmail_control.")
    print("=" * 60)


if __name__ == "__main__":
    main()
