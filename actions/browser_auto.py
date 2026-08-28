# -*- coding: utf-8 -*-
"""
browser_auto.py — Automatización de navegador con Playwright headless/visible.
Acciones:
  open      — Abrir URL
  screenshot — Capturar pantalla de la página
  scrape    — Extraer texto de la página
  click     — Hacer click en un selector CSS
  type      — Escribir texto en un input
  evaluate  — Ejecutar JavaScript en la página
  links     — Extraer todos los links
  close     — Cerrar el navegador
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any

_browser = None
_page = None
_playwright = None

_SCREENSHOT_DIR = Path(r"D:\Eris_Source\data\screenshots")
_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_playwright():
    global _playwright, _browser, _page
    if _playwright is not None:
        return True
    try:
        from playwright.sync_api import sync_playwright
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
        _page = _browser.new_page()
        return True
    except Exception as e:
        print(f"[browser_auto] Error Playwright: {e}")
        return False


def _close_browser():
    global _playwright, _browser, _page
    try:
        if _page:
            _page.close()
        if _browser:
            _browser.close()
        if _playwright:
            _playwright.stop()
    except Exception:
        pass
    _playwright = _browser = _page = None


def browser_auto(parameters: dict = None, player=None) -> str:
    """Tool: Automatización de navegador (Playwright)."""
    params = parameters or {}
    action = str(params.get("action", "open")).lower().strip()

    if action == "close":
        _close_browser()
        return "Navegador cerrado."

    if not _ensure_playwright():
        return "No pude iniciar Playwright. Verificá: playwright install chromium"

    global _page

    try:
        if action == "open":
            url = str(params.get("url", "")).strip()
            if not url:
                return "Necesitás una URL. Ej: 'https://example.com'"
            if not url.startswith("http"):
                url = "https://" + url
            _page.goto(url, timeout=30000, wait_until="domcontentloaded")
            title = _page.title()
            return f"✅ Abierta: {title}\nURL: {_page.url}"

        if action == "screenshot":
            name = f"shot_{int(os.times()[4])}.png"
            path = _SCREENSHOT_DIR / name
            _page.screenshot(path=str(path), full_page=False)
            return f"Screenshot guardado: {path}"

        if action == "scrape":
            max_chars = min(int(params.get("max_chars", 3000)), 10000)
            text = _page.inner_text("body")
            text = text[:max_chars]
            title = _page.title()
            return f"**{title}**\n\n{text}"

        if action == "click":
            selector = str(params.get("selector", "")).strip()
            if not selector:
                return "Necesitás un selector CSS. Ej: 'button.submit'"
            _page.click(selector, timeout=10000)
            return f"Click en: {selector}"

        if action == "type":
            selector = str(params.get("selector", "")).strip()
            text = str(params.get("text", "")).strip()
            if not selector or not text:
                return "Necesitás selector y texto."
            _page.fill(selector, text, timeout=10000)
            return f"Escrito en {selector}: {text[:50]}"

        if action == "evaluate":
            script = str(params.get("script", "")).strip()
            if not script:
                return "Necesitás código JavaScript."
            result = _page.evaluate(script)
            return json.dumps(result, ensure_ascii=False, default=str)[:3000]

        if action == "links":
            max_links = min(int(params.get("max_links", 30)), 50)
            links = _page.eval_on_selector_all("a[href]", "els => els.map(e => ({text: e.innerText.trim().slice(0,80), href: e.href}))")
            links = [l for l in links if l.get("text") and l.get("href")][:max_links]
            if not links:
                return "No encontré links en la página."
            lines = [f"**Links en {_page.title()}:**\n"]
            for l in links:
                lines.append(f"• [{l['text']}]({l['href']})")
            return "\n".join(lines)

        return f"Acciones: open, screenshot, scrape, click, type, evaluate, links, close"

    except Exception as e:
        return f"Error en browser_auto ({action}): {str(e)[:200]}"
