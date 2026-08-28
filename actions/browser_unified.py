# -*- coding: utf-8 -*-
"""
browser_unified.py — Browser automation unificada para Eris.
Reemplaza browser_auto, smart_browser, web_scraper (parte Playwright).

Acciones:
  navigate    — Abrir URL
  back        — Volver
  forward     — Adelante
  reload      — Recargar
  text        — Obtener texto de la página
  html        — Obtener HTML de un selector
  links       — Obtener links
  meta        — Metadatos (title, OG tags, etc)
  click       — Click en selector CSS
  fill        — Llenar input
  type        — Escribir con delay (como humano)
  select      — Seleccionar option en dropdown
  check       — Checkbox on/off
  scroll      — Scroll up/down
  hover       — Hover sobre elemento
  key         — Presionar tecla
  wait        — Esperar elemento
  screenshot  — Captura de pantalla
  pdf         — Generar PDF
  js          — Ejecutar JavaScript
  upload      — Subir archivo
  tabs        — Listar/crear/cerrar tabs
  save        — Guardar cookies/sesión
  status      — Info del browser
"""
from __future__ import annotations

import json
from typing import Any


def _get_manager():
    from core.browser_manager import get_browser_manager
    return get_browser_manager()


def browser_unified(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()
    mgr = _get_manager()

    # ── Ensure browser is running ──
    if action not in ("status",):
        if not mgr._ensure():
            # Try starting with default settings
            if not mgr.start(headless=False):
                return "Error: No se pudo iniciar el navegador."

    try:
        if action == "navigate":
            url = params.get("url", "")
            if not url:
                return "Error: se necesita 'url'."
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            r = mgr.navigate(url)
            if r["ok"]:
                return f"Abierto: {r['title']}\nURL: {r['url']}\nStatus: {r['status']}"
            return f"Error: {r['error']}"

        elif action == "back":
            r = mgr.go_back()
            return f"Volví a: {r.get('url', '?')}" if r["ok"] else f"Error: {r['error']}"

        elif action == "forward":
            r = mgr.go_forward()
            return f"Adelante: {r.get('url', '?')}" if r["ok"] else f"Error: {r['error']}"

        elif action == "reload":
            r = mgr.reload()
            return f"Recargado: {r.get('url', '?')}" if r["ok"] else f"Error: {r['error']}"

        elif action == "text":
            sel = params.get("selector", "body")
            max_chars = int(params.get("max_chars", 8000))
            r = mgr.get_text(sel, max_chars)
            if r["ok"]:
                return r["text"]
            return f"Error: {r['error']}"

        elif action == "html":
            sel = params.get("selector", "body")
            max_chars = int(params.get("max_chars", 20000))
            r = mgr.get_html(sel, max_chars)
            if r["ok"]:
                return r["html"]
            return f"Error: {r['error']}"

        elif action == "links":
            sel = params.get("selector", "a")
            r = mgr.get_links(sel)
            if r["ok"]:
                if not r["links"]:
                    return "No se encontraron links."
                lines = [f"{i+1}. {l['text'][:60]} → {l['href']}" for i, l in enumerate(r["links"][:30])]
                return f"{len(r['links'])} links encontrados:\n" + "\n".join(lines)
            return f"Error: {r['error']}"

        elif action == "meta":
            r = mgr.get_metadata()
            if r["ok"]:
                m = r["meta"]
                lines = [f"{k}: {v}" for k, v in m.items() if v]
                return "\n".join(lines)
            return f"Error: {r['error']}"

        elif action == "click":
            sel = params.get("selector", "")
            if not sel:
                return "Error: se necesita 'selector'."
            r = mgr.click(sel)
            return f"Click: {sel}" if r["ok"] else f"Error: {r['error']}"

        elif action == "fill":
            sel = params.get("selector", "")
            val = params.get("value", "")
            if not sel:
                return "Error: se necesita 'selector'."
            r = mgr.fill(sel, val)
            return f"Llenado: {sel}" if r["ok"] else f"Error: {r['error']}"

        elif action == "type":
            sel = params.get("selector", "")
            val = params.get("value", "")
            delay = int(params.get("delay", 50))
            if not sel:
                return "Error: se necesita 'selector'."
            r = mgr.type_text(sel, val, delay)
            return f"Escrito en {sel}" if r["ok"] else f"Error: {r['error']}"

        elif action == "select":
            sel = params.get("selector", "")
            val = params.get("value", "")
            if not sel:
                return "Error: se necesita 'selector'."
            r = mgr.select_option(sel, val)
            return f"Seleccionado: {val}" if r["ok"] else f"Error: {r['error']}"

        elif action == "check":
            sel = params.get("selector", "")
            checked = params.get("checked", True)
            if not sel:
                return "Error: se necesita 'selector'."
            r = mgr.check(sel, checked)
            return f"Checkbox {'marcado' if checked else 'desmarcado'}" if r["ok"] else f"Error: {r['error']}"

        elif action == "scroll":
            direction = params.get("direction", "down")
            amount = int(params.get("amount", 500))
            r = mgr.scroll(direction, amount)
            return f"Scroll {direction} {amount}px" if r["ok"] else f"Error: {r['error']}"

        elif action == "hover":
            sel = params.get("selector", "")
            if not sel:
                return "Error: se necesita 'selector'."
            r = mgr.hover(sel)
            return f"Hover: {sel}" if r["ok"] else f"Error: {r['error']}"

        elif action == "key":
            key = params.get("key", "")
            if not key:
                return "Error: se necesita 'key' (ej: Enter, Tab, Escape)."
            r = mgr.press_key(key)
            return f"Tecla: {key}" if r["ok"] else f"Error: {r['error']}"

        elif action == "wait":
            sel = params.get("selector", "")
            timeout = int(params.get("timeout", 10000))
            if not sel:
                return "Error: se necesita 'selector'."
            r = mgr.wait_for(sel, timeout)
            return f"Elemento encontrado: {sel}" if r["ok"] else f"Timeout: {sel} no apareció"

        elif action == "screenshot":
            full_page = params.get("full_page", False)
            sel = params.get("selector")
            r = mgr.screenshot(full_page=full_page, selector=sel)
            if r["ok"]:
                return f"Screenshot guardado: {r['path']}"
            return f"Error: {r['error']}"

        elif action == "pdf":
            path = params.get("path")
            r = mgr.generate_pdf(path)
            if r["ok"]:
                return f"PDF generado: {r['path']}"
            return f"Error: {r['error']}"

        elif action == "js":
            expr = params.get("expression", "")
            if not expr:
                return "Error: se necesita 'expression'."
            r = mgr.evaluate(expr)
            if r["ok"]:
                return f"Resultado: {r['result']}"
            return f"Error: {r['error']}"

        elif action == "upload":
            sel = params.get("selector", "input[type=file]")
            path = params.get("path", "")
            if not path:
                return "Error: se necesita 'path' del archivo."
            r = mgr.upload_file(sel, path)
            return f"Archivo subido: {path}" if r["ok"] else f"Error: {r['error']}"

        elif action == "tabs":
            sub = params.get("sub", "list")
            if sub == "list":
                r = mgr.list_tabs()
                if r["ok"]:
                    lines = [f"{'*' if t['active'] else ' '} {t['name']}: {t['title'][:40]} — {t['url'][:60]}" for t in r["tabs"]]
                    return "\n".join(lines)
                return f"Error: {r['error']}"
            elif sub == "new":
                url = params.get("url")
                name = params.get("name")
                r = mgr.new_tab(url, name)
                if r["ok"]:
                    return f"Nuevo tab '{r['tab']}': {r.get('url', '')}"
                return f"Error: {r['error']}"
            elif sub == "close":
                name = params.get("name")
                r = mgr.close_tab(name)
                return f"Tab '{name}' cerrado" if r["ok"] else f"Error: {r['error']}"
            elif sub == "switch":
                name = params.get("name", "")
                r = mgr.switch_tab(name)
                return f"Tab activo: {name}" if r["ok"] else f"Error: {r['error']}"
            return f"Subacción desconocida: {sub}"

        elif action == "save":
            r = mgr.save_session()
            return "Sesión guardada (cookies)" if r["ok"] else f"Error: {r['error']}"

        elif action == "clear_cookies":
            r = mgr.clear_cookies()
            return "Cookies limpiadas" if r["ok"] else f"Error: {r['error']}"

        elif action == "play":
            # YouTube: navigate + search + play first result
            query = params.get("query", "")
            url = params.get("url", "")
            if url:
                # Direct URL — just navigate
                r = mgr.navigate(url)
                if r["ok"]:
                    import time
                    time.sleep(2)
                    # Try to click play button if video exists
                    mgr.evaluate("document.querySelector('video') && document.querySelector('video').play()")
                    return f"Reproduciendo: {url}"
                return f"Error: {r['error']}"
            elif query:
                # Search YouTube and play first result
                r = mgr.navigate("https://www.youtube.com/results?search_query=" + query.replace(" ", "+"))
                if not r["ok"]:
                    return f"Error: {r['error']}"
                import time
                time.sleep(3)
                # Click first video result
                mgr.click("ytd-video-renderer:first-child #video-title")
                time.sleep(3)
                title = mgr.evaluate("document.title")
                title_str = title.get("result", "video") if title.get("ok") else "video"
                return f"Reproduciendo en YouTube: {title_str}"
            return "Error: se necesita 'query' o 'url'."

        elif action == "status":
            info = mgr.get_info()
            lines = [
                f"Activo: {info['started']}",
                f"Modo: {'headless' if info['headless'] else 'visible'}",
                f"Tabs: {info['tabs']}",
                f"Tab activo: {info['active_tab']}",
                f"URL: {info.get('current_url', 'ninguna')}",
                f"Título: {info.get('current_title', 'ninguno')}",
            ]
            return "\n".join(lines)

        else:
            return (
                f"Acción '{action}' no reconocida.\n"
                "Acciones: navigate, back, forward, reload, text, html, links, meta, "
                "click, fill, type, select, check, scroll, hover, key, wait, "
                "screenshot, pdf, js, upload, tabs, save, clear_cookies, play, status"
            )

    except Exception as e:
        return f"Error en browser: {str(e)[:200]}"
