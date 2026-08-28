"""API tester for Eris."""
import json
import time
import urllib.request
import urllib.error
import urllib.parse

def api_tester_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"status": "ready", "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]})
    elif action == "request":
        url = params.get("url", "")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        body = params.get("body", "")
        timeout = params.get("timeout", 10)
        if not url:
            return json.dumps({"error": "URL required"})
        try:
            data = body.encode("utf-8") if body else None
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            start = time.time()
            resp = urllib.request.urlopen(req, timeout=timeout)
            elapsed = round((time.time() - start) * 1000)
            resp_body = resp.read().decode("utf-8", errors="replace")[:5000]
            resp_headers = dict(resp.headers)
            return json.dumps({
                "status": resp.status,
                "elapsed_ms": elapsed,
                "headers": resp_headers,
                "body": resp_body,
                "url": url,
                "method": method,
            })
        except urllib.error.HTTPError as e:
            return json.dumps({"status": e.code, "error": str(e), "url": url, "method": method})
        except Exception as e:
            return json.dumps({"error": str(e)[:300], "url": url, "method": method})
    elif action == "health_check":
        url = params.get("url", "")
        if not url:
            return json.dumps({"error": "URL required"})
        try:
            start = time.time()
            resp = urllib.request.urlopen(url, timeout=5)
            elapsed = round((time.time() - start) * 1000)
            return json.dumps({"url": url, "healthy": resp.status == 200, "status": resp.status, "latency_ms": elapsed})
        except Exception as e:
            return json.dumps({"url": url, "healthy": False, "error": str(e)[:200]})
    return json.dumps({"error": "Unknown action"})
