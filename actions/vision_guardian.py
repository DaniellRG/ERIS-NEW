import threading
import time
import json
from pathlib import Path
from datetime import datetime

_MONITORING = False
_MONITOR_THREAD = None
_LAST_SCAN = ""
_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "vision_guardian.json"
_INJECT_FN = None
_SPEAKING_FN = None
_LAST_INJECTED = ""
_LAST_INJECT_TS = 0.0
_INJECT_COOLDOWN = 90


def vision_guardian(parameters: dict = None, player=None) -> str:
    global _MONITORING, _LAST_SCAN
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "status").strip().lower()

    if action == "enable":
        if _MONITORING:
            return "Vision Guardian ya esta activo."
        _MONITORING = True
        _start_monitor(player)
        return "Vision Guardian activado. Monitoreare la pantalla periodicamente."

    elif action == "disable":
        if not _MONITORING:
            return "Vision Guardian ya esta inactivo."
        _MONITORING = False
        return "Vision Guardian desactivado."

    elif action == "status":
        status = "activado" if _MONITORING else "inactivado"
        last = ""
        if _LAST_SCAN:
            last = "\nUltimo analisis: {}".format(_LAST_SCAN[:16])
        data = _load_data()
        events = len(data.get("events", []))
        return "Vision Guardian {}.{}Eventos registrados: {}".format(status, last, events)

    elif action == "check_now":
        result = _scan_screen(player)
        _LAST_SCAN = datetime.now().isoformat()
        return result

    elif action == "analyze":
        prompt = parameters.get("prompt", parameters.get("query", "Describe que hay en pantalla"))
        path = parameters.get("path", "")
        return _analyze_with_vision(prompt, path, player)

    elif action == "monitor":
        interval = int(parameters.get("interval", 30))
        if interval < 5:
            interval = 5
        _MONITORING = True
        _start_monitor(player, interval)
        return "Monitoreo iniciado cada {} segundos.".format(interval)

    return "Acciones: enable, disable, status, check_now, analyze (analizar imagen), monitor (monitoreo continuo)."


def start(**kwargs) -> None:
    """Arranca el monitoreo en background. kwargs admitidos:
    - inject_fn (callable): inyecta la vista en el contexto del modelo.
    - speaking_fn (callable): devuelve True si Eris está hablando (no inyectar).
    - enabled (bool): activa el monitoreo automatico (default: leer config).
    - interval (int): segundos entre analisis (default: config o 90).
    """
    global _INJECT_FN, _SPEAKING_FN, _MONITORING
    _INJECT_FN = kwargs.get("inject_fn")
    _SPEAKING_FN = kwargs.get("speaking_fn")
    interval = int(kwargs.get("interval", 0) or 0) or _config_interval()
    enabled = kwargs.get("enabled")
    if enabled is None:
        enabled = _is_enabled()
    if enabled:
        _MONITORING = True
    _start_monitor(None, interval)


def _config_interval() -> int:
    try:
        cfg = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        c = json.loads(cfg.read_text(encoding="utf-8"))
        return int(c.get("vision_guardian_interval", 90))
    except Exception:
        return 90


def _is_enabled() -> bool:
    try:
        cfg = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        c = json.loads(cfg.read_text(encoding="utf-8"))
        return bool(c.get("vision_guardian_enabled", True))
    except Exception:
        return True


def _start_monitor(player, interval: int = 60) -> None:
    if interval < 10:
        interval = 10

    def _loop():
        global _LAST_SCAN, _LAST_INJECTED, _LAST_INJECT_TS
        while _MONITORING:
            try:
                result = _scan_screen(player)
                _LAST_SCAN = datetime.now().isoformat()
                _log_event("scan", result[:200])
                if player and "ALERTA" in result:
                    player.write_log("[Vision Guardian] {}".format(result[:100]))
                # Inyectar la vista en el contexto del modelo si cambió y
                # Eris no está hablando (Feature 2: mírame la pantalla sola).
                _maybe_inject(result)
            except Exception:
                pass
            for _ in range(interval):
                if not _MONITORING:
                    return
                time.sleep(1)
    global _MONITOR_THREAD
    if _MONITOR_THREAD and _MONITOR_THREAD.is_alive():
        return
    _MONITOR_THREAD = threading.Thread(target=_loop, daemon=True, name="vision-guardian")
    _MONITOR_THREAD.start()


def _maybe_inject(result: str) -> None:
    """Si la pantalla cambió respecto a la última vista inyectada y Eris no
    está hablando, envía el análisis al contexto del modelo (throttleado).
    Omitimos resultados que son errores o capturas fallidas."""
    global _LAST_INJECTED, _LAST_INJECT_TS
    if not _INJECT_FN:
        return
    s = str(result)
    if any(t in s for t in ("Error", "No se pudo", "no disponible", "degradado")):
        return
    if _SPEAKING_FN:
        try:
            if _SPEAKING_FN():
                return
        except Exception:
            pass
    key = s[:140]
    now = time.time()
    if key != _LAST_INJECTED and (now - _LAST_INJECT_TS) >= _INJECT_COOLDOWN:
        _LAST_INJECTED = key
        _LAST_INJECT_TS = now
        _INJECT_FN("[VISTA EN VIVO] {}\n(Esto lo ves por tus propios ojos, es contexto; usalo si aporta.)".format(s[:300]))
        _log_event("inject", key[:100])


def _scan_screen(player) -> str:
    try:
        from actions.screen_vision import screen_vision
        result = screen_vision({"action": "describe"}, player)
        if not result or "Error" in str(result):
            return "Pantalla: No se pudo analizar."
        return "Analisis de pantalla:\n{}".format(str(result)[:500])
    except Exception as e:
        return "Error analizando pantalla: {}".format(str(e)[:80])


def _analyze_with_vision(prompt: str, path: str, player) -> str:
    try:
        if path:
            from actions.image_analyzer import image_analyzer
            return image_analyzer({"action": "analyze", "path": path, "prompt": prompt}, player)
        else:
            from actions.screen_vision import screen_vision
            return screen_vision({"action": "custom", "query": prompt}, player)
    except Exception as e:
        return "Error en analisis visual: {}".format(str(e)[:80])


def _log_event(event_type: str, detail: str):
    try:
        data = _load_data()
        data.setdefault("events", []).append({
            "type": event_type, "detail": detail[:200],
            "time": datetime.now().isoformat(),
        })
        if len(data["events"]) > 100:
            data["events"] = data["events"][-100:]
        _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _load_data() -> dict:
    if _DATA_FILE.exists():
        try:
            return json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}
