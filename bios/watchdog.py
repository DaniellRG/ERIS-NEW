import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta

_heartbeat_time = None
_heartbeat_lock = threading.Lock()
_watchdog_active = False
_crash_history = []
_rules = {}

def load_rules(rules_path=None):
    if rules_path is None:
        rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")
    global _rules
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            _rules = json.load(f).get("rules", {})
    except Exception:
        _rules = {}
    return _rules

def heartbeat():
    global _heartbeat_time
    with _heartbeat_lock:
        _heartbeat_time = time.monotonic()

def get_heartbeat():
    with _heartbeat_lock:
        return _heartbeat_time

def record_crash():
    global _crash_history
    now = time.monotonic()
    _crash_history.append(now)
    window = _rules.get("crash_window_minutes", 5) * 60
    cutoff = now - window
    _crash_history = [t for t in _crash_history if t > cutoff]
    return len(_crash_history)

def should_enter_recovery():
    threshold = _rules.get("crash_threshold", 3)
    count = record_crash()
    return count >= threshold

def watchdog_loop(stop_event):
    global _watchdog_active
    _watchdog_active = True
    interval = _rules.get("heartbeat_interval_seconds", 10)
    timeout = interval * 3

    while not stop_event.is_set():
        time.sleep(interval)
        hb = get_heartbeat()
        if hb is not None:
            elapsed = time.monotonic() - hb
            if elapsed > timeout:
                _on_watchdog_timeout(elapsed)
    _watchdog_active = False

def _on_watchdog_timeout(elapsed):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base, "memory")
    os.makedirs(log_dir, exist_ok=True)
    try:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "watchdog_timeout",
            "elapsed_seconds": round(elapsed, 1)
        }
        log_path = os.path.join(log_dir, "watchdog_log.json")
        existing = []
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.append(entry)
        if len(existing) > 20:
            existing = existing[-20:]
        tmp = log_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        os.replace(tmp, log_path)
    except Exception:
        pass

def get_crash_count():
    threshold = _rules.get("crash_threshold", 3)
    return record_crash()
