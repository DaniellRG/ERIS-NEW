"""
ERIS Browser Manager — Playwright centralizado.
Maneja sesiones persistentes, multi-tab, cookies, screenshots, PDFs.
"""
import asyncio
import json
import time
import threading
import base64
from pathlib import Path
from typing import Optional

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SCREENSHOTS_DIR = _DATA_DIR / "screenshots"
_SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Singleton
_instance = None
_lock = threading.Lock()


class BrowserManager:
    """Centralizado Playwright manager con sesiones persistentes."""

    def __init__(self):
        self._pw = None
        self._browser = None
        self._context = None
        self._pages: dict[str, object] = {}  # name -> page
        self._active_page: str = "default"
        self._headless = True
        self._started = False
        self._cookies_file = _DATA_DIR / "browser_cookies.json"
        self._user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/149.0.0.0 Safari/537.36"
        )

    def start(self, headless: bool = False) -> bool:
        if self._started and self._browser:
            return True
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._headless = headless
            self._browser = self._pw.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-first-run",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                ],
            )
            self._context = self._browser.new_context(
                user_agent=self._user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="es-AR",
                timezone_id="America/Argentina/Buenos_Aires",
            )
            # Stealth: override navigator.webdriver to avoid bot detection
            self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['es-AR', 'es', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                window.chrome = { runtime: {} };
            """)
            self._load_cookies()
            self._pages["default"] = self._context.new_page()
            self._active_page = "default"
            self._started = True
            print("[BrowserManager] Started (headless={})".format(headless))
            return True
        except Exception as e:
            print(f"[BrowserManager] Start failed: {e}")
            return False

    def stop(self):
        try:
            self._save_cookies()
            for p in self._pages.values():
                try:
                    p.close()
                except Exception:
                    pass
            self._pages.clear()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._browser = None
        self._context = None
        self._pw = None
        self._started = False
        self._pages.clear()
        print("[BrowserManager] Stopped")

    @property
    def page(self):
        return self._pages.get(self._active_page)

    def _ensure(self) -> bool:
        if not self._started or not self._browser:
            return self.start()
        return True

    def _get_or_create_page(self, name: str = None):
        name = name or self._active_page
        if name not in self._pages or self._pages[name].is_closed():
            self._pages[name] = self._context.new_page()
        self._active_page = name
        return self._pages[name]

    # ── Navigation ──
    def navigate(self, url: str, tab: str = None) -> dict:
        if not self._ensure():
            return {"ok": False, "error": "Browser not started"}
        page = self._get_or_create_page(tab)
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            status = resp.status if resp else 0
            title = page.title()
            return {"ok": True, "url": page.url, "title": title, "status": status}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def go_back(self) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.go_back(wait_until="domcontentloaded", timeout=15000)
            return {"ok": True, "url": self.page.url, "title": self.page.title()}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def go_forward(self) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.go_forward(wait_until="domcontentloaded", timeout=15000)
            return {"ok": True, "url": self.page.url, "title": self.page.title()}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def reload(self) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.reload(wait_until="domcontentloaded", timeout=15000)
            return {"ok": True, "url": self.page.url}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # ── Content extraction ──
    def get_text(self, selector: str = "body", max_chars: int = 8000) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            el = self.page.query_selector(selector)
            if not el:
                return {"ok": False, "error": f"Selector '{selector}' not found"}
            text = el.inner_text()
            if len(text) > max_chars:
                text = text[:max_chars] + "\n[...truncated]"
            return {"ok": True, "text": text, "length": len(text)}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def get_html(self, selector: str = "body", max_chars: int = 20000) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            el = self.page.query_selector(selector)
            if not el:
                return {"ok": False, "error": f"Selector '{selector}' not found"}
            html = el.inner_html()
            if len(html) > max_chars:
                html = html[:max_chars] + "\n[...truncated]"
            return {"ok": True, "html": html, "length": len(html)}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def get_links(self, selector: str = "a") -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            links = self.page.eval_on_selector_all(
                selector,
                "els => els.map(e => ({text: e.innerText.trim().slice(0,100), href: e.href})).filter(l => l.href && l.text)",
            )
            return {"ok": True, "links": links[:50], "count": len(links)}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def get_metadata(self) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            meta = self.page.evaluate("""() => {
                const m = {};
                m.title = document.title;
                m.url = location.href;
                const desc = document.querySelector('meta[name="description"]');
                if (desc) m.description = desc.content;
                const og = document.querySelectorAll('meta[property^="og:"]');
                og.forEach(e => m[e.getAttribute('property')] = e.content);
                m.textLength = document.body.innerText.length;
                m.images = document.images.length;
                m.links = document.links.length;
                m.forms = document.forms.length;
                return m;
            }""")
            return {"ok": True, "meta": meta}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # ── Interaction ──
    def click(self, selector: str, timeout: int = 10000) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.click(selector, timeout=timeout)
            return {"ok": True, "clicked": selector}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def fill(self, selector: str, value: str, timeout: int = 10000) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.fill(selector, value, timeout=timeout)
            return {"ok": True, "filled": selector}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def type_text(self, selector: str, text: str, delay: int = 50) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.click(selector, timeout=5000)
            self.page.type(selector, text, delay=delay)
            return {"ok": True, "typed": text[:50]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def select_option(self, selector: str, value: str) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.select_option(selector, value, timeout=5000)
            return {"ok": True, "selected": value}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def check(self, selector: str, checked: bool = True) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.set_checked(selector, checked, timeout=5000)
            return {"ok": True, "checked": checked}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def scroll(self, direction: str = "down", amount: int = 500) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            delta = amount if direction == "down" else -amount
            self.page.mouse.wheel(0, delta)
            return {"ok": True, "scrolled": direction, "amount": amount}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def hover(self, selector: str) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.hover(selector, timeout=5000)
            return {"ok": True, "hovered": selector}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def press_key(self, key: str) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.keyboard.press(key)
            return {"ok": True, "pressed": key}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def wait_for(self, selector: str, timeout: int = 10000) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return {"ok": True, "found": selector}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # ── Screenshot & PDF ──
    def screenshot(self, full_page: bool = False, selector: str = None) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            ts = int(time.time())
            path = str(_SCREENSHOTS_DIR / f"ss_{ts}.png")
            if selector:
                el = self.page.query_selector(selector)
                if el:
                    el.screenshot(path=path)
                else:
                    return {"ok": False, "error": f"Selector '{selector}' not found"}
            else:
                self.page.screenshot(path=path, full_page=full_page)
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def screenshot_base64(self) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            buf = self.page.screenshot()
            b64 = base64.b64encode(buf).decode()
            return {"ok": True, "base64": b64, "size": len(buf)}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def generate_pdf(self, path: str = None) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            if not path:
                ts = int(time.time())
                path = str(_DATA_DIR / f"page_{ts}.pdf")
            self.page.pdf(path=path, format="A4", print_background=True)
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # ── JavaScript ──
    def evaluate(self, expression: str) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            result = self.page.evaluate(expression)
            return {"ok": True, "result": str(result)[:5000]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # ── Tab management ──
    def new_tab(self, url: str = None, name: str = None) -> dict:
        if not self._ensure():
            return {"ok": False, "error": "Browser not started"}
        try:
            tab_name = name or f"tab_{len(self._pages)}"
            page = self._context.new_page()
            if url:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._pages[tab_name] = page
            self._active_page = tab_name
            return {"ok": True, "tab": tab_name, "url": page.url}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def close_tab(self, name: str = None) -> dict:
        name = name or self._active_page
        if name == "default":
            return {"ok": False, "error": "Cannot close default tab"}
        if name in self._pages:
            try:
                self._pages[name].close()
                del self._pages[name]
                self._active_page = "default"
                return {"ok": True, "closed": name}
            except Exception as e:
                return {"ok": False, "error": str(e)[:200]}
        return {"ok": False, "error": f"Tab '{name}' not found"}

    def switch_tab(self, name: str) -> dict:
        if name in self._pages:
            self._active_page = name
            return {"ok": True, "tab": name, "url": self.page.url}
        return {"ok": False, "error": f"Tab '{name}' not found"}

    def list_tabs(self) -> dict:
        tabs = []
        for name, page in self._pages.items():
            try:
                tabs.append({
                    "name": name,
                    "url": page.url,
                    "title": page.title(),
                    "active": name == self._active_page,
                })
            except Exception:
                tabs.append({"name": name, "url": "?", "title": "?", "active": False})
        return {"ok": True, "tabs": tabs}

    # ── Cookies & persistence ──
    def _save_cookies(self):
        try:
            if self._context:
                cookies = self._context.cookies()
                self._cookies_file.write_text(
                    json.dumps(cookies, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        except Exception:
            pass

    def _load_cookies(self):
        try:
            if self._cookies_file.exists() and self._context:
                cookies = json.loads(self._cookies_file.read_text(encoding="utf-8"))
                if cookies:
                    self._context.add_cookies(cookies)
        except Exception:
            pass

    def save_session(self) -> dict:
        self._save_cookies()
        return {"ok": True, "message": "Cookies saved"}

    def clear_cookies(self) -> dict:
        try:
            if self._context:
                self._context.clear_cookies()
            if self._cookies_file.exists():
                self._cookies_file.unlink()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # ── File upload ──
    def upload_file(self, selector: str, file_path: str) -> dict:
        if not self.page:
            return {"ok": False, "error": "No active page"}
        try:
            self.page.set_input_files(selector, file_path, timeout=10000)
            return {"ok": True, "uploaded": file_path}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    # ── Utility ──
    def get_info(self) -> dict:
        return {
            "started": self._started,
            "headless": self._headless,
            "tabs": len(self._pages),
            "active_tab": self._active_page,
            "current_url": self.page.url if self.page else None,
            "current_title": self.page.title() if self.page else None,
        }


def get_browser_manager() -> BrowserManager:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = BrowserManager()
    return _instance
