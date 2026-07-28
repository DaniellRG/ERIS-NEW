import os
import json
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MONITOR_FILE = os.path.join(DATA_DIR, "darkweb_monitor.json")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
API_KEYS_FILE = os.path.join(CONFIG_DIR, "api_keys.json")

HIBP_API = "https://haveibeenpwned.com/api/v3"
HIBP_HEADERS = {"User-Agent": "Eris-Security-Monitor"}


def _load_data():
    if os.path.exists(MONITOR_FILE):
        with open(MONITOR_FILE, "r") as f:
            return json.load(f)
    return {"checks": [], "alerts": [], "results": []}


def _save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MONITOR_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _get_api_key():
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, "r") as f:
            keys = json.load(f)
        return keys.get("hibp_api_key", "")
    return ""


def _hibp_request(endpoint, api_key=None):
    if not api_key:
        api_key = _get_api_key()
    url = f"{HIBP_API}/{endpoint}"
    headers = dict(HIBP_HEADERS)
    if api_key:
        headers["hibp-api-key"] = api_key

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data, None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return [], None
        elif e.code == 401:
            return None, "API key required. Set 'hibp_api_key' in config/api_keys.json"
        elif e.code == 429:
            return None, "Rate limited. Wait before making more requests."
        return None, f"HTTP {e.code}: {e.read().decode()}"
    except Exception as e:
        return None, str(e)


def darkweb_monitor(parameters: dict, player=None) -> str:
    action = parameters.get("action", "check").lower()

    if action == "check":
        return _check_exposure(parameters)
    elif action == "alerts":
        return _set_alerts(parameters)
    elif action == "history":
        return _check_history(parameters)
    elif action == "report":
        return _generate_report(parameters)
    elif action == "scan_email":
        return _scan_email(parameters)
    else:
        return f"Unknown action: {action}. Valid: check, alerts, history, report, scan_email"


def _check_exposure(parameters: dict):
    email = parameters.get("email", "")
    domain = parameters.get("domain", "")

    if email:
        return _scan_email({"email": email})
    elif domain:
        return _scan_domain(domain)
    return "Provide 'email' or 'domain' parameter."


def _scan_email(parameters: dict):
    email = parameters.get("email", "")
    if not email:
        return "'email' parameter required."

    breaches, err = _hibp_request(f"breachedaccount/{urllib.parse.quote(email)}?truncateResponse=false")
    if err:
        return f"Error checking email: {err}"

    data = _load_data()
    check_record = {
        "email": email,
        "timestamp": datetime.now().isoformat(),
        "breach_count": len(breaches) if breaches else 0
    }

    result_entry = {
        "email": email,
        "breaches": [],
        "timestamp": datetime.now().isoformat()
    }

    if breaches:
        lines = [f"Breaches found for {email} ({len(breaches)}):"]
        for b in breaches:
            breach_info = {
                "name": b.get("Name", ""),
                "title": b.get("Title", ""),
                "domain": b.get("Domain", ""),
                "date": b.get("BreachDate", ""),
                "data_classes": b.get("DataClasses", []),
                "pwn_count": b.get("PwnCount", 0)
            }
            result_entry["breaches"].append(breach_info)
            lines.append(
                f"  - {b.get('Title', 'Unknown')} | "
                f"Date: {b.get('BreachDate', 'N/A')} | "
                f"Records: {b.get('PwnCount', 'N/A'):,} | "
                f"Data: {', '.join(b.get('DataClasses', [])[:3])}"
            )
    else:
        lines = [f"No breaches found for {email}."]

    data["checks"].append(check_record)
    data["results"].append(result_entry)
    if len(data["checks"]) > 200:
        data["checks"] = data["checks"][-200:]
        data["results"] = data["results"][-200:]
    _save_data(data)

    return "\n".join(lines)


def _scan_domain(domain):
    breaches, err = _hibp_request(f"breaches/{domain}")
    if err:
        return f"Error checking domain: {err}"

    data = _load_data()
    check_record = {
        "domain": domain,
        "timestamp": datetime.now().isoformat(),
        "breach_count": len(breaches) if breaches else 0
    }

    if breaches:
        lines = [f"Breaches involving {domain} ({len(breaches)}):"]
        for b in breaches[:20]:
            lines.append(
                f"  - {b.get('Title', 'Unknown')} | "
                f"Date: {b.get('BreachDate', 'N/A')} | "
                f"Records: {b.get('PwnCount', 'N/A'):,}"
            )
    else:
        lines = [f"No breaches found involving domain: {domain}"]

    data["checks"].append(check_record)
    _save_data(data)
    return "\n".join(lines)


def _set_alerts(parameters: dict):
    data = _load_data()
    sub_action = parameters.get("sub_action", "add")

    if sub_action == "add":
        email = parameters.get("email", "")
        if not email:
            return "'email' parameter required."
        alert = {
            "email": email,
            "created": datetime.now().isoformat(),
            "enabled": True
        }
        data["alerts"].append(alert)
        _save_data(data)
        return f"Alert set for: {email}. You'll be notified of new breaches."

    elif sub_action == "remove":
        email = parameters.get("email", "")
        data["alerts"] = [a for a in data["alerts"] if a.get("email") != email]
        _save_data(data)
        return f"Alert removed for: {email}"

    elif sub_action == "list":
        alerts = data.get("alerts", [])
        if not alerts:
            return "No alerts configured."
        lines = [f"Monitoring Alerts ({len(alerts)}):"]
        for a in alerts:
            status = "active" if a.get("enabled") else "disabled"
            lines.append(f"  - {a['email']} ({status}, set: {a.get('created', 'N/A')})")
        return "\n".join(lines)

    return "Unknown sub_action. Use: add, remove, list"


def _check_history(parameters: dict):
    data = _load_data()
    checks = data.get("checks", [])
    limit = parameters.get("limit", 20)
    if not checks:
        return "No check history."

    recent = checks[-limit:]
    lines = [f"Check History ({len(recent)} of {len(checks)}):"]
    for c in reversed(recent):
        target = c.get("email") or c.get("domain", "Unknown")
        count = c.get("breach_count", 0)
        lines.append(f"  [{c['timestamp']}] {target}: {count} breach(es)")
    return "\n".join(lines)


def _generate_report(parameters: dict):
    data = _load_data()
    results = data.get("results", [])
    if not results:
        return "No results to report. Run a scan first."

    lines = [
        "Dark Web Exposure Report",
        f"Generated: {datetime.now().isoformat()}",
        f"Total scans: {len(data.get('checks', []))}",
        "=" * 50
    ]

    total_breaches = 0
    all_data_classes = set()
    for r in results:
        breaches = r.get("breaches", [])
        total_breaches += len(breaches)
        email = r.get("email", "Unknown")
        if breaches:
            lines.append(f"\n{email}:")
            for b in breaches:
                lines.append(f"  - {b.get('name', 'N/A')} ({b.get('date', 'N/A')})")
                for dc in b.get("data_classes", []):
                    all_data_classes.add(dc)
        else:
            lines.append(f"\n{email}: Clean")

    lines.append(f"\nSummary:")
    lines.append(f"  Total emails checked: {len(results)}")
    lines.append(f"  Total breaches found: {total_breaches}")
    if all_data_classes:
        lines.append(f"  Data types exposed: {', '.join(sorted(all_data_classes))}")

    if data.get("alerts"):
        lines.append(f"\nActive alerts: {len(data['alerts'])}")

    report = "\n".join(lines)
    report_path = os.path.join(DATA_DIR, "darkweb_report.txt")
    with open(report_path, "w") as f:
        f.write(report)
    lines.append(f"\nReport saved to: {report_path}")
    return "\n".join(lines)
