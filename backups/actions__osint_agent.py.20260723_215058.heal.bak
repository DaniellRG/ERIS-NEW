# -*- coding: utf-8 -*-
"""
Eris OSINT Agent – Recopilación de inteligencia de fuentes abiertas.
Busca información pública sobre emails, usernames, dominios, IPs.
Usa web scraping, APIs públicas y搜索引擎.
"""
import re
import json
import socket
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OSINT_LOG = DATA_DIR / "osint_log.json"


def _log_search(search_type: str, query: str, results_count: int):
    """Log OSINT searches."""
    try:
        data = []
        if OSINT_LOG.exists():
            data = json.loads(OSINT_LOG.read_text(encoding="utf-8"))
        data.append({
            "time": datetime.now().isoformat(),
            "type": search_type,
            "query": query,
            "results": results_count,
        })
        # Keep last 100 searches
        OSINT_LOG.write_text(json.dumps(data[-100:], indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _check_email_breach(email: str) -> list:
    """Check if email appears in known breaches (using HaveIBeenPwned-like approach)."""
    if not HAS_REQUESTS:
        return [{"error": "requests not available"}]

    results = []
    # Check via HIBP API (public, rate limited)
    try:
        headers = {"User-Agent": "Eris-OSINT/1.0"}
        r = requests.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote_plus(email)}",
            headers=headers,
            timeout=10,
        )
        if r.status_code == 200:
            breaches = r.json()
            for b in breaches:
                results.append({
                    "breach": b.get("Name", ""),
                    "date": b.get("BreachDate", ""),
                    "data_classes": b.get("DataClasses", []),
                    "pwn_count": b.get("PwnCount", 0),
                })
        elif r.status_code == 404:
            results.append({"info": "Email not found in known breaches"})
        else:
            results.append({"info": f"HIBP API: status {r.status_code}"})
    except Exception as e:
        results.append({"error": str(e)})

    return results


def _search_username_platforms(username: str) -> list:
    """Check if username exists on common platforms."""
    if not HAS_REQUESTS:
        return [{"error": "requests not available"}]

    platforms = {
        "GitHub": f"https://github.com/{username}",
        "Twitter/X": f"https://twitter.com/{username}",
        "Instagram": f"https://www.instagram.com/{username}/",
        "Reddit": f"https://www.reddit.com/user/{username}",
        "TikTok": f"https://www.tiktok.com/@{username}",
        "YouTube": f"https://www.youtube.com/@{username}",
        "Twitch": f"https://www.twitch.tv/{username}",
        "Pinterest": f"https://www.pinterest.com/{username}/",
        "Spotify": f"https://open.spotify.com/user/{username}",
        "LinkedIn": f"https://www.linkedin.com/in/{username}",
        "Steam": f"https://steamcommunity.com/id/{username}",
        "Telegram": f"https://t.me/{username}",
        "Keybase": f"https://keybase.io/{username}",
        "Medium": f"https://medium.com/@{username}",
        "DeviantArt": f"https://www.deviantart.com/{username}",
    }

    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    for platform, url in platforms.items():
        try:
            r = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
            status = "FOUND" if r.status_code == 200 else "NOT FOUND"
            if r.status_code == 200:
                # Check for common "not found" indicators
                text = r.text.lower()
                if any(x in text for x in ["this page isn't available", "sorry, this page", "user not found", "does not exist"]):
                    status = "NOT FOUND"
            results.append({
                "platform": platform,
                "url": url,
                "status": status,
            })
            _log_search("username", f"{platform}/{username}", 1 if status == "FOUND" else 0)
        except Exception:
            results.append({
                "platform": platform,
                "url": url,
                "status": "ERROR",
            })

    return results


def _whois_lookup(domain: str) -> dict:
    """Basic WHOIS-style lookup using web."""
    if not HAS_REQUESTS:
        return {"error": "requests not available"}

    result = {"domain": domain}

    # DNS lookup
    try:
        ips = socket.getaddrinfo(domain, None)
        result["ips"] = list(set([addr[4][0] for addr in ips]))
    except Exception:
        result["ips"] = []

    # Try to get more info via web
    try:
        headers = {"User-Agent": "Eris-OSINT/1.0"}
        r = requests.get(f"https://dns.google/resolve?name={domain}&type=A", headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            result["dns_records"] = [
                {"name": a.get("name"), "type": a.get("type"), "data": a.get("data")}
                for a in data.get("Answer", [])
            ]
    except Exception:
        pass

    # MX records
    try:
        r = requests.get(f"https://dns.google/resolve?name={domain}&type=MX", headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            result["mx_records"] = [
                {"name": a.get("name"), "priority": a.get("TTL"), "data": a.get("data")}
                for a in data.get("Answer", [])
            ]
    except Exception:
        pass

    _log_search("whois", domain, len(result.get("ips", [])))
    return result


def _ip_lookup(ip: str) -> dict:
    """IP geolocation and info."""
    if not HAS_REQUESTS:
        return {"error": "requests not available"}

    result = {"ip": ip}
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,org,as,mobile,proxy,hosting", timeout=5)
        if r.status_code == 200:
            data = r.json()
            result.update(data)
    except Exception:
        pass

    _log_search("ip", ip, 1)
    return result


def _email_info(email: str) -> dict:
    """Gather info about an email address."""
    result = {"email": email}

    # Basic validation
    parts = email.split("@")
    if len(parts) != 2:
        result["valid"] = False
        return result
    result["valid"] = True
    result["domain"] = parts[1]

    # Check domain MX
    try:
        import subprocess
        ns = subprocess.run(
            ["nslookup", "-type=MX", parts[1]],
            capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace"
        )
        result["mx_found"] = "mail exchanger" in ns.stdout.lower()
        mx_lines = [l.strip() for l in ns.stdout.split("\n") if "mail exchanger" in l.lower()]
        result["mx_servers"] = mx_lines[:3]
    except Exception:
        result["mx_found"] = None

    # Check breaches
    result["breaches"] = _check_email_breach(email)

    _log_search("email", email, len(result.get("breaches", [])))
    return result


def _search_web(query: str, count: int = 5) -> list:
    """Search the web for information using DuckDuckGo Lite."""
    if not HAS_REQUESTS:
        return [{"error": "requests not available"}]

    results = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(
            f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}",
            headers=headers,
            timeout=10,
        )
        if r.status_code == 200:
            # Parse lite results
            text = r.text
            links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*class="result-link"[^>]*>([^<]*)</a>', text)
            snippets = re.findall(r'<td class="result-snippet">(.*?)</td>', text, re.DOTALL)
            for i, (url, title) in enumerate(links[:count]):
                snip = snippets[i].strip() if i < len(snippets) else ""
                snip = re.sub(r"<[^>]+>", "", snip).strip()
                results.append({
                    "title": title.strip(),
                    "url": url,
                    "snippet": snip[:200],
                })
    except Exception:
        pass

    _log_search("web", query, len(results))
    return results


def osint_agent(parameters: dict, player=None) -> str:
    """
    Agente de OSINT (Open Source Intelligence) para Eris.
    Busca información pública sobre emails, usuarios, dominios e IPs.

    Acciones:
      - email: Buscar info de un email (breaches, MX, validación)
      - username: Verificar username en múltiples plataformas
      - domain: WHOIS y DNS de un dominio
      - ip: Geolocalización y info de una IP
      - web: Búsqueda web general
      - breach: Verificar si un email está en filtraciones conocidas
      - full_report: Reporte completo de un objetivo. Parametros: target (email/username/domain)
      - history: Ver historial de búsquedas OSINT
    """
    action = parameters.get("action", "web").lower()

    if action == "email":
        email = parameters.get("target", "")
        if not email:
            return "Error: Se requiere 'target' (email address)."
        info = _email_info(email)
        result = f"**📧 Email Intelligence: {email}**\n\n"
        result += f"Valid: {'✓' if info.get('valid') else '✗'}\n"
        result += f"Domain: {info.get('domain', '?')}\n"
        if info.get("mx_found") is not None:
            result += f"MX Records: {'✓ Found' if info['mx_found'] else '✗ Not found'}\n"
            for mx in info.get("mx_servers", []):
                result += f"  - {mx}\n"
        if info.get("breaches"):
            result += f"\n**Breaches ({len(info['breaches'])}):**\n"
            for b in info["breaches"][:10]:
                if "breach" in b:
                    result += f"  - **{b['breach']}** ({b.get('date', '?')}) — {', '.join(b.get('data_classes', [])[:3])} — {b.get('pwn_count', 0)} accounts\n"
                elif "info" in b:
                    result += f"  - {b['info']}\n"
        return result

    elif action == "username":
        username = parameters.get("target", "")
        if not username:
            return "Error: Se requiere 'target' (username)."
        results = _search_username_platforms(username)
        found = [r for r in results if r["status"] == "FOUND"]
        not_found = [r for r in results if r["status"] == "NOT FOUND"]
        result = f"**👤 Username Intelligence: {username}**\n\n"
        result += f"Found on **{len(found)}** platforms:\n"
        for r in found:
            result += f"  ✓ {r['platform']}: {r['url']}\n"
        if not_found:
            result += f"\nNot found on {len(not_found)} platforms.\n"
        return result

    elif action == "domain":
        domain = parameters.get("target", "")
        if not domain:
            return "Error: Se requiere 'target' (domain)."
        info = _whois_lookup(domain)
        result = f"**🌐 Domain Intelligence: {domain}**\n\n"
        if info.get("ips"):
            result += f"IPs: {', '.join(info['ips'])}\n"
        if info.get("dns_records"):
            result += "\nDNS Records:\n"
            for rec in info["dns_records"]:
                result += f"  {rec['type']} → {rec['data']}\n"
        if info.get("mx_records"):
            result += "\nMX Records:\n"
            for mx in info["mx_records"]:
                result += f"  {mx['data']} (priority: {mx.get('priority', '?')})\n"
        return result

    elif action == "ip":
        ip = parameters.get("target", "")
        if not ip:
            return "Error: Se requiere 'target' (IP address)."
        info = _ip_lookup(ip)
        result = f"**📍 IP Intelligence: {ip}**\n\n"
        for k, v in info.items():
            if k != "ip" and v:
                result += f"  {k}: {v}\n"
        return result

    elif action == "web":
        query = parameters.get("query", parameters.get("target", ""))
        if not query:
            return "Error: Se requiere 'query' o 'target'."
        count = int(parameters.get("count", 5))
        results = _search_web(query, count)
        result = f"**🔍 Web Search: {query}**\n\n"
        for i, r in enumerate(results, 1):
            result += f"{i}. **{r['title']}**\n   {r['url']}\n   {r.get('snippet', '')}\n\n"
        if not results:
            result += "No results found.\n"
        return result

    elif action == "breach":
        email = parameters.get("target", "")
        if not email:
            return "Error: Se requiere 'target' (email)."
        breaches = _check_email_breach(email)
        result = f"**🔓 Breach Check: {email}**\n\n"
        for b in breaches:
            if "breach" in b:
                result += f"  - **{b['breach']}** ({b.get('date', '?')})\n    Data: {', '.join(b.get('data_classes', [])[:5])}\n    Accounts: {b.get('pwn_count', 0)}\n\n"
            elif "info" in b:
                result += f"  {b['info']}\n"
        return result

    elif action == "full_report":
        target = parameters.get("target", "")
        if not target:
            return "Error: Se requiere 'target'."

        result = f"# 📋 Full OSINT Report: {target}\n\n"
        result += f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"

        # Determine type
        if "@" in target:
            result += "## Email Analysis\n"
            info = _email_info(target)
            result += f"Valid: {'✓' if info.get('valid') else '✗'}\n"
            result += f"Domain: {info.get('domain', '?')}\n"
            if info.get("breaches"):
                result += f"Breaches: {len(info['breaches'])}\n"
                for b in info["breaches"][:5]:
                    if "breach" in b:
                        result += f"  - {b['breach']}: {', '.join(b.get('data_classes', [])[:3])}\n"
        elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target):
            result += "## IP Analysis\n"
            info = _ip_lookup(target)
            for k, v in info.items():
                if k != "ip" and v:
                    result += f"  {k}: {v}\n"
        elif "." in target and " " not in target:
            result += "## Domain Analysis\n"
            info = _whois_lookup(target)
            if info.get("ips"):
                result += f"IPs: {', '.join(info['ips'])}\n"
            if info.get("dns_records"):
                for rec in info["dns_records"]:
                    result += f"  {rec['type']} → {rec['data']}\n"
        else:
            result += "## Username Search\n"
            results = _search_username_platforms(target)
            found = [r for r in results if r["status"] == "FOUND"]
            result += f"Found on **{len(found)}** platforms:\n"
            for r in found:
                result += f"  ✓ {r['platform']}: {r['url']}\n"

        # Web search
        result += "\n## Web Search\n"
        web_results = _search_web(target, 3)
        for r in web_results:
            result += f"  - {r['title']}: {r['url']}\n"

        return result

    elif action == "history":
        try:
            if OSINT_LOG.exists():
                data = json.loads(OSINT_LOG.read_text(encoding="utf-8"))
                result = f"**📜 OSINT Search History ({len(data)} searches)**\n\n"
                for entry in data[-15:]:
                    result += f"  [{entry['time'][:16]}] {entry['type']}: {entry['query']} ({entry['results']} results)\n"
                return result
        except Exception:
            pass
        return "No search history yet."

    available = "email | username | domain | ip | web | breach | full_report | history"
    return f"Action '{action}' not found. Available: {available}"
