import time
import pyautogui
import pygetwindow as gw

def browser_control(parameters: dict, player=None) -> str:
    action = parameters.get("action", "")
    browser_keywords = ["Chrome", "Edge", "Firefox", "Brave", "Opera"]
    target_window = None
    for win in gw.getAllWindows():
        if win.title.strip():
            for kw in browser_keywords:
                if kw.lower() in win.title.lower():
                    target_window = win; break
        if target_window: break
    if not target_window:
        return "No se encontro navegador abierto."

    try:
        try:
            if target_window.isMinimized: target_window.restore()
        except: pass
        try: target_window.activate()
        except: pass
        time.sleep(0.2)

        if action == "go_to":
            url = parameters.get("url", "")
            if not url: return "Error: Falta URL."
            pyautogui.hotkey('ctrl', 'l'); time.sleep(0.1)
            pyautogui.write(url, interval=0.005); pyautogui.press('enter')
            return f"Navegando a {url}."

        elif action == "search":
            query = parameters.get("query", "")
            if not query: return "Error: Falta query."
            pyautogui.hotkey('ctrl', 'l'); time.sleep(0.1)
            pyautogui.write(query, interval=0.005); pyautogui.press('enter')
            return f"Buscando '{query}'."

        elif action == "new_tab":
            url = parameters.get("url", "")
            pyautogui.hotkey('ctrl', 't'); time.sleep(0.3)
            if url: pyautogui.write(url, interval=0.01); pyautogui.press('enter')
            return f"Pestana nueva {('en '+url) if url else 'abierta'}."

        elif action == "close_tab":
            pyautogui.hotkey('ctrl', 'w')
            return "Pestana cerrada."

        elif action == "scroll":
            direction = parameters.get("direction", "down")
            pyautogui.press('pgdn' if direction == "down" else 'pgup')
            return f"Scroll pagina {direction}."

        elif action == "scroll_mouse":
            direction = parameters.get("direction", "down")
            amount = int(parameters.get("amount", 25))
            for i in range(amount):
                pyautogui.scroll(-18 if direction == "down" else 18)
                time.sleep(0.015)
            return f"Scroll fluido {direction} ({amount}x18)."

        elif action == "scroll_up":
            amount = int(parameters.get("amount", 30))
            for i in range(amount):
                pyautogui.scroll(25); time.sleep(0.01)
            # Also do Page Up for big jumps
            pyautogui.press('pgup')
            return f"Scroll ARRIBA ({amount}x25 + pgup)."

        elif action == "scroll_down":
            amount = int(parameters.get("amount", 30))
            for i in range(amount):
                pyautogui.scroll(-25); time.sleep(0.01)
            return f"Scroll ABAJO ({amount}x25)."

        elif action == "play_pause":
            pyautogui.press('space')
            return "Play/Pause ejecutado."

        elif action == "select_result_smart":
            """Usa vision AI para encontrar y clickear el resultado correcto."""
            index = int(parameters.get("index", 1))
            site = parameters.get("site", "google")
            
            # Get API key directly from config
            try:
                import json as _json
                from pathlib import Path as _Path
                import sys as _sys
                
                # Try multiple paths for config
                config_paths = [
                    _Path(_sys.executable).parent / "config" / "api_keys.json",
                    _Path(__file__).resolve().parent.parent / "config" / "api_keys.json",
                    _Path("config/api_keys.json"),
                ]
                key = ""
                for cp in config_paths:
                    if cp.exists():
                        try:
                            key = _json.loads(cp.read_text("utf-8")).get("openrouter_api_key", "")
                            if key: break
                        except: pass
                
                if not key:
                    return browser_control({"action": "select_result", "index": index, "site": site}, player)
                
                # Capture screen
                try:
                    from mss import mss
                    from PIL import Image
                    import base64, io
                    with mss() as sct:
                        monitor = sct.monitors[1]  # primary monitor
                        img = Image.frombytes("RGB", (monitor["width"], monitor["height"]), sct.grab(monitor).bgra, "raw", "BGRX")
                        # capture centered region for search results
                        w, h = img.size
                        crop = img.crop((0, int(h*0.15), w, int(h*0.85)))
                        cw, ch = crop.size
                        if max(cw, ch) > 1200:
                            ratio = 1200 / max(cw, ch)
                            crop = crop.resize((int(cw*ratio), int(ch*ratio)), Image.LANCZOS)
                        buf = io.BytesIO()
                        crop.save(buf, format="JPEG", quality=70)
                        b64 = base64.b64encode(buf.getvalue()).decode()
                except Exception as cap_err:
                    return browser_control({"action": "select_result", "index": index, "site": site}, player)
                
                import json as _json2, urllib.request as _ur
                prompt = (
                    f"Esta es una pagina de busqueda. Dame SOLO las coordenadas X,Y del CENTRO del enlace del resultado #{index}. "
                    f"El resultado #1 es el primer resultado de la busqueda (no la barra de direcciones, no anuncios). "
                    f"Responde SOLO 'X,Y' sin nada mas."
                )
                body = _json2.dumps({
                    "model": "google/gemini-2.5-flash",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}],
                    "max_tokens": 50
                }).encode()
                req = _ur.Request(
                    "https://openrouter.ai/api/v1/chat/completions",
                    data=body,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                )
                with _ur.urlopen(req, timeout=15) as resp:
                    response = _json2.loads(resp.read())["choices"][0]["message"]["content"].strip()
                
                import re
                nums = re.findall(r'\d+', response)
                if len(nums) >= 2:
                    x, y = int(nums[0]), int(nums[1])
                    screen_w, screen_h = pyautogui.size()
                    
                    try:
                        from actions.human_mouse import move_to, click as hm_click
                        move_to(x=x, y=y, speed="smooth")
                        time.sleep(0.05)
                        hm_click()
                    except:
                        pyautogui.moveTo(x, y, duration=0.3)
                        time.sleep(0.1)
                        pyautogui.click()
                    
                    time.sleep(0.5)
                    return f"Resultado #{index} clickeado via VISION en ({x}, {y})."
            except Exception:
                pass
            
            # Fallback: use calculated positions
            return browser_control({"action": "select_result", "index": index, "site": site}, player)

        elif action == "select_result":
            index = int(parameters.get("index", 1))
            site = parameters.get("site", "google")
            screen_w, screen_h = pyautogui.size()
            
            if site == "google":
                # Google results: calculate click position based on screen
                # Results start ~30% from top, each ~92px apart, links at ~28% from left
                base_y = int(screen_h * 0.30)
                step_y = 92
                target_x = int(screen_w * 0.30)
                target_y = base_y + (index - 1) * step_y
                
                # Scroll to bring target into view if needed
                if target_y > screen_h * 0.8:
                    pyautogui.press('pgdn')
                    time.sleep(0.3)
                    target_y = base_y
                
                try:
                    from actions.human_mouse import move_to, click as hm_click
                    move_to(x=target_x, y=target_y, speed="smooth")
                    time.sleep(0.05)
                    hm_click()
                except:
                    pyautogui.moveTo(target_x, target_y, duration=0.3)
                    time.sleep(0.1)
                    pyautogui.click()
                
                time.sleep(0.5)
                return f"Resultado Google #{index} clickeado en ({target_x}, {target_y})."
            
            elif site == "youtube":
                base_y = int(screen_h * 0.28)
                step_y = 108
                target_x = screen_w // 2
                target_y = base_y + (index - 1) * step_y
                
                try:
                    from actions.human_mouse import move_to, click as hm_click
                    move_to(x=target_x, y=target_y, speed="smooth")
                    time.sleep(0.05)
                    hm_click()
                except:
                    pyautogui.moveTo(target_x, target_y, duration=0.3)
                    time.sleep(0.1)
                    pyautogui.click()
                
                time.sleep(0.5)
                return f"Video YouTube #{index} clickeado en ({target_x}, {target_y})."
            
            else:
                pyautogui.click(screen_w // 2, screen_h // 2); time.sleep(0.2)
                total_tabs = 10 + (index-1)*3
                for _ in range(total_tabs):
                    pyautogui.press('tab'); time.sleep(0.03)
                pyautogui.press('enter'); time.sleep(0.3)
                return f"Resultado #{index} (Tab method). {total_tabs} tabs."
            index = int(parameters.get("index", 1))
            tabs = int(parameters.get("tabs", 20))
            screen_w, screen_h = pyautogui.size()
            pyautogui.click(screen_w // 2, screen_h // 2); time.sleep(0.2)
            total_tabs = tabs + (index-1)*2
            for _ in range(total_tabs):
                pyautogui.press('tab'); time.sleep(0.04)
            pyautogui.press('enter'); time.sleep(0.5)
            return f"Elemento #{index}. {total_tabs} tabs."

        elif action == "search_info":
            query = parameters.get("query", "")
            index = int(parameters.get("index", 1))
            if not query: return "Error: Falta query."
            encoded = query.replace(' ', '+')
            # Use current tab, don't open new one
            pyautogui.hotkey('ctrl', 'l'); time.sleep(0.2)
            pyautogui.write(f"google.com/search?q={encoded}", interval=0.005)
            pyautogui.press('enter')
            # Wait for page to load, dismiss dialogs
            time.sleep(2)
            pyautogui.press('escape'); time.sleep(0.5)
            pyautogui.press('escape'); time.sleep(1)
            return browser_control({"action": "select_result_smart", "index": index, "site": "google"}, player)

        elif action == "play_direct":
            query = parameters.get("query", "")
            index = int(parameters.get("index", 1))
            if not query: return "Error: Falta query."
            encoded = query.replace(' ', '+')
            # Use current tab
            pyautogui.hotkey('ctrl', 'l'); time.sleep(0.2)
            pyautogui.write(f"youtube.com/results?search_query={encoded}", interval=0.001)
            pyautogui.press('enter'); time.sleep(3)
            # Click video using thumbnail
            return browser_control({"action": "click_thumbnail", "index": index}, player)

        elif action == "scan_results":
            import pyperclip
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a'); time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'c'); time.sleep(0.3)
            try: text = pyperclip.paste()[:1000]
            except: text = ""
            return f"Visible: {text}"

        elif action == "read_page":
            import pyperclip
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a'); time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'c'); time.sleep(0.3)
            try: text = pyperclip.paste()[:2000]
            except: text = "(vacio)"
            return f"Texto: {text}"

        elif action == "click_element":
            description = parameters.get("description", "")
            index = int(parameters.get("index", 1))
            if not description: return "Error: Falta description."
            tabs = 15 + (index-1)*3
            screen_w, screen_h = pyautogui.size()
            pyautogui.click(screen_w // 2, screen_h // 2); time.sleep(0.2)
            for _ in range(tabs):
                pyautogui.press('tab'); time.sleep(0.05)
            pyautogui.press('enter'); time.sleep(0.3)
            return f"'{description}' clickeado. {tabs} tabs."

        elif action == "skip_ad":
            time.sleep(5)
            pyautogui.press('tab'); time.sleep(0.1)
            pyautogui.press('enter'); time.sleep(0.5)
            return "Intento de saltar anuncio."

        elif action == "go_back":
            pyautogui.hotkey('alt', 'left'); time.sleep(1)
            return "Pagina anterior."

        elif action == "mouse_move":
            x = int(parameters.get("x", -1))
            y = int(parameters.get("y", -1))
            if x < 0 or y < 0: return "Error: Necesito x e y."
            try:
                from actions.human_mouse import move_to
                return move_to(x=x, y=y, speed="smooth")
            except:
                pyautogui.moveTo(x, y, duration=0.15)
                return f"Mouse a ({x},{y})."

        elif action == "mouse_click":
            x = int(parameters.get("x", -1))
            y = int(parameters.get("y", -1))
            try:
                from actions.human_mouse import move_to, click as hm_click
                if x >= 0 and y >= 0: move_to(x=x, y=y, speed="smooth"); time.sleep(0.01)
                return hm_click()
            except:
                if x >= 0: pyautogui.moveTo(x, y, duration=0.15)
                pyautogui.click()
                return "Click."

        elif action == "mouse_double_click":
            x = int(parameters.get("x", -1))
            y = int(parameters.get("y", -1))
            try:
                from actions.human_mouse import move_to, double_click as hm_dclick
                if x >= 0 and y >= 0: move_to(x=x, y=y, speed="smooth"); time.sleep(0.01)
                return hm_dclick()
            except:
                if x >= 0: pyautogui.moveTo(x, y, duration=0.15)
                pyautogui.doubleClick()
                return "Doble click."

        elif action == "click_thumbnail":
            index = int(parameters.get("index", 1))
            screen_w, screen_h = pyautogui.size()
            target_x = screen_w // 2
            target_y = int(screen_h * 0.28) + (index-1) * 108
            try:
                from actions.human_mouse import move_to, click as hm_click
                move_to(x=target_x, y=target_y, speed="smooth")
                time.sleep(0.01)
                return hm_click()
            except:
                pyautogui.moveTo(target_x, target_y, duration=0.15)
                pyautogui.click()
            time.sleep(0.5)
            return f"Thumbnail #{index} clickeado."

        elif action == "click_title":
            index = int(parameters.get("index", 1))
            screen_w, screen_h = pyautogui.size()
            target_x = screen_w // 3
            target_y = int(screen_h * 0.36) + (index-1) * 108
            try:
                from actions.human_mouse import move_to, click as hm_click
                move_to(x=target_x, y=target_y, speed="smooth")
                time.sleep(0.01)
                return hm_click()
            except:
                pyautogui.moveTo(target_x, target_y, duration=0.15)
                pyautogui.click()
            time.sleep(0.5)
            return f"Titulo #{index} clickeado."

        else:
            return f"Accion '{action}' no reconocida."

    except Exception as e:
        return f"Error: {e}"
