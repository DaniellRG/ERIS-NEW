"""Dashboard web auto-generado de ERIS: stats del sistema."""
import json
import os
import platform
import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler


DASHBOARD_PORT = 8766
_server = None
_thread = None


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ERIS Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a1a;color:#e0e0e0;font-family:-apple-system,system-ui,sans-serif;padding:20px}
h1{background:linear-gradient(135deg,#a855f7,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:28px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-bottom:20px}
.card{background:rgba(255,255,255,.04);border:1px solid rgba(168,85,247,.15);border-radius:12px;padding:16px}
.card h3{color:#a855f7;font-size:14px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.card .value{font-size:28px;font-weight:700;color:#fff}
.card .sub{font-size:12px;color:#888;margin-top:4px}
table{width:100%;border-collapse:collapse;margin-top:8px}
td{padding:6px 8px;border-bottom:1px solid rgba(255,255,255,.05);font-size:13px}
td:last-child{text-align:right;font-family:monospace}
.refresh{text-align:center;padding:12px;color:#555;font-size:12px}
</style>
</head>
<body>
<h1>ERIS Dashboard</h1>
<div class="grid" id="stats">
  <div class="card"><h3>CPU</h3><div class="value" id="cpu">-</div></div>
  <div class="card"><h3>RAM</h3><div class="value" id="ram">-</div><div class="sub" id="ram-detail"></div></div>
  <div class="card"><h3>Disco</h3><div class="value" id="disk">-</div></div>
  <div class="card"><h3>Red</h3><div class="value" id="net">-</div><div class="sub" id="net-detail"></div></div>
  <div class="card"><h3>Procesos</h3><div class="value" id="procs">-</div></div>
  <div class="card"><h3>Uptime</h3><div class="value" id="uptime">-</div></div>
</div>
<div class="card"><h3>Sistema</h3><table id="sysinfo"></table></div>
<div class="card"><h3>Procesos Top</h3><table id="top"></table></div>
<div class="refresh">Actualizando cada 5s</div>
<script>
async function load(){try{
  const r=await fetch('/api/stats'),d=await r.json();
  document.getElementById('cpu').textContent=d.cpu+'%';
  document.getElementById('ram').textContent=d.ram_percent+'%';
  document.getElementById('ram-detail').textContent=(d.ram_used/1024).toFixed(1)+'/'+(d.ram_total/1024).toFixed(1)+' GB';
  document.getElementById('disk').textContent=d.disk_percent+'%';
  document.getElementById('disk').style.color=d.disk_percent>90?'#ff453a':'#fff';
  document.getElementById('net').textContent=d.net_rx;
  document.getElementById('net-detail').textContent='RX: '+d.net_rx_raw+' | TX: '+d.net_tx_raw;
  document.getElementById('procs').textContent=d.procs;
  document.getElementById('uptime').textContent=d.uptime;
  var st='';for(var k in d.sysinfo)st+='<tr><td>'+k+'</td><td>'+d.sysinfo[k]+'</td></tr>';
  document.getElementById('sysinfo').innerHTML=st;
  var tp='';d.top.forEach(function(p){tp+='<tr><td>'+p.name+'</td><td>'+p.cpu+'%</td></tr>'});
  document.getElementById('top').innerHTML=tp;
}catch(e){}
setTimeout(load,5000)}
load();
</script>
</body>
</html>"""


def _get_stats() -> dict:
    stats = {"cpu": 0, "ram_percent": 0, "ram_used": 0, "ram_total": 0,
             "disk_percent": 0, "net_rx": "0", "net_tx_raw": "0", "net_rx_raw": "0",
             "procs": 0, "uptime": "0", "sysinfo": {}, "top": []}
    try:
        import psutil
        stats["cpu"] = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        stats["ram_percent"] = mem.percent
        stats["ram_used"] = mem.used / 1024 / 1024
        stats["ram_total"] = mem.total / 1024 / 1024
        disk = psutil.disk_usage("/")
        stats["disk_percent"] = disk.percent
        net = psutil.net_io_counters()
        def fmt(b):
            if b > 1_000_000_000: return f"{b/1_000_000_000:.1f} GB"
            if b > 1_000_000: return f"{b/1_000_000:.1f} MB"
            if b > 1_000: return f"{b/1_000:.1f} KB"
            return f"{b} B"
        stats["net_rx"] = fmt(net.bytes_recv)
        stats["net_rx_raw"] = fmt(net.bytes_recv)
        stats["net_tx_raw"] = fmt(net.bytes_sent)
        stats["procs"] = len(psutil.pids())
        boot = psutil.boot_time()
        stats["uptime"] = str(round((time.time() - boot) / 3600, 1)) + "h"
        stats["sysinfo"] = {
            "Hostname": socket.gethostname(),
            "Sistema": platform.system() + " " + platform.release(),
            "CPU": platform.processor() or "N/A",
            "Cores": str(psutil.cpu_count(logical=False) or "N/A"),
        }
        top_procs = sorted(psutil.process_iter(["name", "cpu_percent"]),
                           key=lambda p: p.info.get("cpu_percent", 0) or 0, reverse=True)[:10]
        stats["top"] = [{"name": p.info.get("name", "?"), "cpu": p.info.get("cpu_percent", 0) or 0} for p in top_procs]
    except Exception:
        pass
    return stats


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/stats":
            data = json.dumps(_get_stats()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == "/":
            body = DASHBOARD_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


def start_dashboard(parameters: dict = None, player=None) -> str:
    """Inicia el dashboard web."""
    global _server, _thread
    if _server:
        return f"Dashboard ya activo en http://localhost:{DASHBOARD_PORT}"

    _server = HTTPServer(("0.0.0.0", DASHBOARD_PORT), _Handler)
    _thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _thread.start()
    return f"Dashboard iniciado: http://localhost:{DASHBOARD_PORT}"


def stop_dashboard(parameters: dict = None, player=None) -> str:
    """Detiene el dashboard."""
    global _server
    if not _server:
        return "Dashboard no activo."
    _server.shutdown()
    _server = None
    return "Dashboard detenido."


def dashboard_status(parameters: dict = None, player=None) -> str:
    """Estado del dashboard."""
    if _server:
        return f"Dashboard activo en http://localhost:{DASHBOARD_PORT}"
    return "Dashboard inactivo. Usa action=start."
