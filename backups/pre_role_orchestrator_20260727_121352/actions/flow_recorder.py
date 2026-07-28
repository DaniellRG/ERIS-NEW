"""
flow_recorder.py — Grabador de flujos: grabar acciones del usuario y repetirlas (macros).
Registra clicks, teclas, delays, y las reproduce exactamente.
"""
import json
import time
import threading
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_MACROS_DIR = _BASE / "data" / "macros"
_ACTIVE_MACRO = None
_RECORDING = False
_RECORD_START = None
_ACTIONS = []


def flow_recorder(parameters: dict = None, player=None) -> str:
    """
    Grabador de flujos/macros.
    Acciones: start, stop, list, play, save, delete, info, pause, resume
    """
    params = parameters or {}
    action = params.get("action", "list").lower()

    if action == "start":
        return _start_recording(params)
    elif action == "stop":
        return _stop_recording()
    elif action == "list":
        return _list_macros()
    elif action == "play":
        return _play_macro(params)
    elif action == "save":
        return _save_macro(params)
    elif action == "delete":
        return _delete_macro(params)
    elif action == "info":
        return _macro_info(params)
    elif action == "status":
        return _get_status()
    elif action == "add_step":
        return _add_manual_step(params)
    elif action == "edit":
        return _edit_macro(params)
    elif action == "duplicate":
        return _duplicate_macro(params)
    return "Acciones: start, stop, list, play, save, delete, info, status, add_step, edit, duplicate"


def _start_recording(params: dict) -> str:
    global _RECORDING, _ACTIONS, _RECORD_START, _ACTIVE_MACRO

    if _RECORDING:
        return "Ya hay una grabación en curso. Detenla primero con stop"

    _ACTIVE_MACRO = params.get("name", "macro_{}".format(int(time.time())))
    _ACTIONS = []
    _RECORDING = True
    _RECORD_START = time.time()

    try:
        import pyautogui
        _start_keyboard_listener()
        _start_mouse_listener()
    except ImportError:
        pass

    return "Grabación iniciada: '{}'. Di 'stop' cuando quieras parar".format(_ACTIVE_MACRO)


def _stop_recording() -> str:
    global _RECORDING, _ACTIONS, _RECORD_START, _ACTIVE_MACRO

    if not _RECORDING:
        return "No hay grabación en curso"

    _RECORDING = False
    duration = time.time() - _RECORD_START if _RECORD_START else 0
    name = _ACTIVE_MACRO

    if _ACTIONS:
        _MACROS_DIR.mkdir(parents=True, exist_ok=True)
        macro = {
            "name": name,
            "created": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "total_steps": len(_ACTIONS),
            "actions": _ACTIONS,
        }
        path = _MACROS_DIR / "{}.json".format(name)
        path.write_text(json.dumps(macro, indent=2, ensure_ascii=False), encoding="utf-8")
        result = "Grabación '{}' detenida. {} pasos, {:.1f}s. Guardado en {}".format(
            name, len(_ACTIONS), duration, str(path))
    else:
        result = "Grabación '{}' detenida pero sin acciones registradas".format(name)

    _ACTIVE_MACRO = None
    _ACTIONS = []
    return result


def _list_macros() -> str:
    _MACROS_DIR.mkdir(parents=True, exist_ok=True)
    files = list(_MACROS_DIR.glob("*.json"))
    if not files:
        return "No hay macros guardadas"

    results = ["Macros guardadas ({}):".format(len(files))]
    for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            macro = json.loads(f.read_text(encoding="utf-8"))
            name = macro.get("name", f.stem)
            steps = macro.get("total_steps", len(macro.get("actions", [])))
            duration = macro.get("duration_seconds", 0)
            created = macro.get("created", "?")[:10]
            results.append("  {} | {} pasos | {:.1f}s | {}".format(name, steps, duration, created))
        except Exception:
            results.append("  {} (error leyendo)".format(f.stem))
    return "\n".join(results)


def _play_macro(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    path = _MACROS_DIR / "{}.json".format(name)
    if not path.exists():
        return "Macro no encontrada: {}".format(name)

    try:
        macro = json.loads(path.read_text(encoding="utf-8"))
        actions = macro.get("actions", [])
        if not actions:
            return "Macro '{}' vacía".format(name)

        speed = float(params.get("speed", 1.0))
        repeat = int(params.get("repeat", 1))
        delay = float(params.get("delay", 0.5))

        return _execute_actions(actions, speed, repeat, delay, name)
    except Exception as e:
        return "Error reproduciendo macro: {}".format(str(e))


def _execute_actions(actions, speed, repeat, delay, name):
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
    except ImportError:
        return "Error: pyautogui no instalado (pip install pyautogui)"

    results = []
    for rep in range(repeat):
        results.append("Repetición {}/{} de '{}'".format(rep + 1, repeat, name))
        for i, action in enumerate(actions):
            action_type = action.get("type", "")
            wait = action.get("delay", delay) / speed

            try:
                if action_type == "click":
                    x = action.get("x", 0)
                    y = action.get("y", 0)
                    button = action.get("button", "left")
                    pyautogui.click(x, y, button=button)
                elif action_type == "double_click":
                    x = action.get("x", 0)
                    y = action.get("y", 0)
                    pyautogui.doubleClick(x, y)
                elif action_type == "right_click":
                    x = action.get("x", 0)
                    y = action.get("y", 0)
                    pyautogui.rightClick(x, y)
                elif action_type == "type":
                    text = action.get("text", "")
                    pyautogui.typewrite(text, interval=0.02)
                elif action_type == "hotkey":
                    keys = action.get("keys", [])
                    if keys:
                        pyautogui.hotkey(*keys)
                elif action_type == "key":
                    key = action.get("key", "")
                    pyautogui.press(key)
                elif action_type == "move":
                    x = action.get("x", 0)
                    y = action.get("y", 0)
                    pyautogui.moveTo(x, y, duration=0.3)
                elif action_type == "scroll":
                    clicks = action.get("clicks", 3)
                    pyautogui.scroll(clicks)
                elif action_type == "drag":
                    x1, y1 = action.get("x1", 0), action.get("y1", 0)
                    x2, y2 = action.get("x2", 0), action.get("y2", 0)
                    pyautogui.moveTo(x1, y1)
                    pyautogui.drag(x2 - x1, y2 - y1, duration=0.5)
                elif action_type == "wait":
                    pass

                if wait > 0:
                    time.sleep(wait)
            except Exception as e:
                results.append("  Error en paso {}: {}".format(i, str(e)))

    return "\n".join(results) if results else "Macro '{}' ejecutada ({} pasos x {} repeticiones)".format(
        name, len(actions), repeat)


def _save_macro(params: dict) -> str:
    name = params.get("name", "manual_macro")
    actions = params.get("actions", [])
    if not actions:
        return "Error: se requiere 'actions' (lista de pasos)"

    _MACROS_DIR.mkdir(parents=True, exist_ok=True)
    macro = {
        "name": name,
        "created": datetime.now().isoformat(),
        "duration_seconds": 0,
        "total_steps": len(actions),
        "actions": actions,
    }
    path = _MACROS_DIR / "{}.json".format(name)
    path.write_text(json.dumps(macro, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Macro '{}' guardada con {} pasos".format(name, len(actions))


def _delete_macro(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    path = _MACROS_DIR / "{}.json".format(name)
    if path.exists():
        path.unlink()
        return "Macro '{}' eliminada".format(name)
    return "Macro no encontrada: {}".format(name)


def _macro_info(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    path = _MACROS_DIR / "{}.json".format(name)
    if not path.exists():
        return "Macro no encontrada: {}".format(name)
    macro = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        "Macro: {}".format(macro.get("name")),
        "Creada: {}".format(macro.get("created", "?")),
        "Pasos: {}".format(macro.get("total_steps", 0)),
        "Duración: {:.1f}s".format(macro.get("duration_seconds", 0)),
        "Acciones:",
    ]
    for i, a in enumerate(macro.get("actions", [])):
        lines.append("  {}. {} | {}".format(i + 1, a.get("type", "?"), json.dumps(a, ensure_ascii=False)[:80]))
    return "\n".join(lines)


def _get_status() -> str:
    if _RECORDING:
        elapsed = time.time() - _RECORD_START if _RECORD_START else 0
        return "🔴 GRABANDO '{}' | {:.1f}s | {} pasos".format(
            _ACTIVE_MACRO, elapsed, len(_ACTIONS))
    macros = list(_MACROS_DIR.glob("*.json")) if _MACROS_DIR.exists() else []
    return "Grabadora lista | {} macros guardadas".format(len(macros))


def _add_manual_step(params: dict) -> str:
    global _ACTIONS
    step = {
        "type": params.get("type", "wait"),
        "delay": float(params.get("delay", 0.5)),
    }
    step.update({k: v for k, v in params.items() if k not in ("type", "delay", "action", "name")})
    _ACTIONS.append(step)
    return "Paso agregado: {} (total: {})".format(step["type"], len(_ACTIONS))


def _edit_macro(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    path = _MACROS_DIR / "{}.json".format(name)
    if not path.exists():
        return "Macro no encontrada: {}".format(name)
    macro = json.loads(path.read_text(encoding="utf-8"))
    if "new_name" in params:
        macro["name"] = params["new_name"]
    if "actions" in params:
        macro["actions"] = params["actions"]
        macro["total_steps"] = len(params["actions"])
    path.write_text(json.dumps(macro, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Macro '{}' editada".format(name)


def _duplicate_macro(params: dict) -> str:
    name = params.get("name", "")
    new_name = params.get("new_name", name + "_copy")
    if not name:
        return "Error: se requiere 'name'"
    path = _MACROS_DIR / "{}.json".format(name)
    if not path.exists():
        return "Macro no encontrada: {}".format(name)
    macro = json.loads(path.read_text(encoding="utf-8"))
    macro["name"] = new_name
    macro["created"] = datetime.now().isoformat()
    new_path = _MACROS_DIR / "{}.json".format(new_name)
    new_path.write_text(json.dumps(macro, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Macro duplicada: '{}' → '{}'".format(name, new_name)


def _start_keyboard_listener():
    try:
        from pynput import keyboard

        def on_press(key):
            if not _RECORDING:
                return False
            try:
                if hasattr(key, 'char') and key.char:
                    _ACTIONS.append({
                        "type": "type", "text": key.char,
                        "delay": time.time() - (_ACTIONS[-1].get("_ts", _RECORD_START) if _ACTIONS else _RECORD_START),
                        "_ts": time.time()
                    })
                else:
                    _ACTIONS.append({
                        "type": "key", "key": str(key),
                        "delay": time.time() - (_ACTIONS[-1].get("_ts", _RECORD_START) if _ACTIONS else _RECORD_START),
                        "_ts": time.time()
                    })
            except Exception:
                pass

        thread = threading.Thread(target=lambda: keyboard.Listener(on_press=on_press).run(), daemon=True)
        thread.start()
    except ImportError:
        pass


def _start_mouse_listener():
    try:
        from pynput import mouse

        def on_click(x, y, button, pressed):
            if not _RECORDING or not pressed:
                return
            btn = "left" if button == mouse.Button.left else "right" if button == mouse.Button.right else "middle"
            _ACTIONS.append({
                "type": "click", "x": x, "y": y, "button": btn,
                "delay": time.time() - (_ACTIONS[-1].get("_ts", _RECORD_START) if _ACTIONS else _RECORD_START),
                "_ts": time.time()
            })

        thread = threading.Thread(target=lambda: mouse.Listener(on_click=on_click).run(), daemon=True)
        thread.start()
    except ImportError:
        pass
