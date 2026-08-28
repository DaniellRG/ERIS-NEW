"""
ERIS Proactive Monitoring — Monitoreo continuo de URLs, APIs, crypto, feeds.
Detecta cambios y notifica al usuario proactivamente.
"""
import json
import time
import hashlib
import threading
from pathlib import Path
from typing import Optional

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "monitors"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_MONITORS_FILE = _DATA_DIR / "monitors.json"
_ALERTS_FILE = _DATA_DIR / "alerts.json"
_running = False
_monitor_thread = None


def _load_monitors() -> dict:
    if _MONITORS_FILE.exists():
        with open(_MONITORS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"monitors": [], "last_check": None}


def _save_monitors(data: dict):
    with open(_MONITORS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_alerts() -> list:
    if _ALERTS_FILE.exists():
        with open(_ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_alerts(alerts: list):
    # Keep last 200 alerts
    alerts = alerts[-200:]
    with open(_ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)


def add_monitor(name: str, url: str = None, monitor_type: str = "url",
                check_interval: int = 300, keywords: list = None,
                crypto_symbol: str = None, api_url: str = None,
                threshold: float = None) -> dict:
    """Add a new monitor."""
    data = _load_monitors()
    monitor = {
        "id": hashlib.md5(f"{name}{url or api_url or crypto_symbol}".encode()).hexdigest()[:12],
        "name": name,
        "type": monitor_type,  # url, crypto, api, feed
        "url": url,
        "api_url": api_url,
        "crypto_symbol": crypto_symbol,
        "check_interval": check_interval,
        "keywords": keywords or [],
        "threshold": threshold,
        "last_content_hash": None,
        "last_value": None,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_checked": None,
        "active": True,
    }
    data["monitors"].append(monitor)
    _save_monitors(data)
    return {"ok": True, "id": monitor["id"], "name": name}


def remove_monitor(monitor_id: str) -> dict:
    data = _load_monitors()
    before = len(data["monitors"])
    data["monitors"] = [m for m in data["monitors"] if m["id"] != monitor_id]
    if len(data["monitors"]) < before:
        _save_monitors(data)
        return {"ok": True, "removed": monitor_id}
    return {"ok": False, "error": "Monitor not found"}


def list_monitors() -> dict:
    data = _load_monitors()
    return {"monitors": data["monitors"], "count": len(data["monitors"])}


def check_monitor(monitor: dict) -> Optional[dict]:
    """Check a single monitor and return alert if changed."""
    try:
        import requests

        if monitor["type"] == "url" and monitor.get("url"):
            resp = requests.get(monitor["url"], timeout=15, headers={"User-Agent": "Eris-Monitor/1.0"})
            content = resp.text
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

            if monitor.get("last_content_hash") and content_hash != monitor["last_content_hash"]:
                # Check keywords
                keyword_hit = None
                for kw in (monitor.get("keywords") or []):
                    if kw.lower() in content.lower():
                        keyword_hit = kw
                        break
                alert = {
                    "monitor_id": monitor["id"],
                    "monitor_name": monitor["name"],
                    "type": "url_change",
                    "url": monitor["url"],
                    "message": f"Cambio detectado en '{monitor['name']}'" + (f" (keyword: {keyword_hit})" if keyword_hit else ""),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "keyword_hit": keyword_hit,
                }
                monitor["last_content_hash"] = content_hash
                return alert
            monitor["last_content_hash"] = content_hash

        elif monitor["type"] == "crypto" and monitor.get("crypto_symbol"):
            symbol = monitor["crypto_symbol"].upper()
            resp = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd&include_24hr_change=true",
                timeout=15,
            )
            data = resp.json()
            price_data = data.get(symbol.lower(), {})
            price = price_data.get("usd")
            change_24h = price_data.get("usd_24h_change", 0)

            if price is not None:
                prev = monitor.get("last_value")
                if prev is not None and monitor.get("threshold"):
                    diff_pct = abs(price - prev) / prev * 100 if prev else 0
                    if diff_pct >= monitor["threshold"]:
                        alert = {
                            "monitor_id": monitor["id"],
                            "monitor_name": monitor["name"],
                            "type": "crypto_alert",
                            "message": f"{symbol}: ${price:.2f} ({change_24h:+.1f}% 24h) — cambio {'subida' if price > prev else 'baja'} de {diff_pct:.1f}%",
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "price": price,
                            "prev_price": prev,
                            "change_pct": round(diff_pct, 2),
                        }
                    else:
                        alert = None
                else:
                    alert = None
                monitor["last_value"] = price
                if alert:
                    return alert

        elif monitor["type"] == "api" and monitor.get("api_url"):
            resp = requests.get(monitor["api_url"], timeout=15)
            content_hash = hashlib.sha256(resp.text.encode()).hexdigest()[:16]
            if monitor.get("last_content_hash") and content_hash != monitor["last_content_hash"]:
                alert = {
                    "monitor_id": monitor["id"],
                    "monitor_name": monitor["name"],
                    "type": "api_change",
                    "url": monitor["api_url"],
                    "message": f"Cambio en API '{monitor['name']}'",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                monitor["last_content_hash"] = content_hash
                return alert
            monitor["last_content_hash"] = content_hash

    except Exception as e:
        print(f"[Monitor] Error checking '{monitor['name']}': {e}")
    return None


def check_all_monitors() -> list:
    """Check all active monitors and return alerts."""
    data = _load_monitors()
    alerts = _load_alerts()
    new_alerts = []

    for monitor in data["monitors"]:
        if not monitor.get("active", True):
            continue
        # Check interval
        last_checked = monitor.get("last_checked")
        if last_checked:
            elapsed = time.time() - time.mktime(time.strptime(last_checked, "%Y-%m-%d %H:%M:%S"))
            if elapsed < monitor.get("check_interval", 300):
                continue

        alert = check_monitor(monitor)
        monitor["last_checked"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if alert:
            new_alerts.append(alert)
            alerts.append(alert)

    _save_monitors(data)
    _save_alerts(alerts)
    return new_alerts


def get_recent_alerts(limit: int = 10) -> list:
    alerts = _load_alerts()
    return alerts[-limit:]


def monitoring_tool(parameters: dict = None, player=None) -> str:
    """Tool entry point."""
    params = parameters or {}
    action = params.get("action", "list").lower()

    if action == "add":
        name = params.get("name", "")
        if not name:
            return "Error: se necesita 'name'."
        monitor_type = params.get("type", "url")
        result = add_monitor(
            name=name,
            url=params.get("url"),
            monitor_type=monitor_type,
            check_interval=int(params.get("interval", 300)),
            keywords=params.get("keywords", "").split(",") if params.get("keywords") else [],
            crypto_symbol=params.get("symbol"),
            api_url=params.get("api_url"),
            threshold=float(params["threshold"]) if params.get("threshold") else None,
        )
        return f"Monitor '{name}' creado (ID: {result['id']})." if result["ok"] else result["error"]

    elif action == "remove":
        mid = params.get("id", "")
        result = remove_monitor(mid)
        return f"Monitor '{mid}' eliminado." if result["ok"] else result["error"]

    elif action == "list":
        data = list_monitors()
        if not data["monitors"]:
            return "No hay monitors activos."
        lines = []
        for m in data["monitors"]:
            status = "ON" if m.get("active", True) else "OFF"
            lines.append(f"  [{status}] {m['name']} ({m['type']}) — último check: {m.get('last_checked', 'nunca')}")
        return f"Monitors ({data['count']}):\n" + "\n".join(lines)

    elif action == "check":
        alerts = check_all_monitors()
        if not alerts:
            return "Sin alertas nuevas."
        return "Alertas:\n" + "\n".join(f"  - {a['message']}" for a in alerts)

    elif action == "alerts":
        limit = int(params.get("limit", 10))
        alerts = get_recent_alerts(limit)
        if not alerts:
            return "Sin alertas recientes."
        return "Alertas recientes:\n" + "\n".join(f"  [{a['timestamp']}] {a['message']}" for a in alerts)

    return f"Acción '{action}' no reconocida. Usa: add, remove, list, check, alerts"
