# -*- coding: utf-8 -*-
"""
Eris Web Job Reception – Servidor web local para recibir tareas de clientes.
Panel privado con validación, encolado y ejecución de trabajos.
"""
import json
import threading
import uuid
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from collections import deque

app = Flask(__name__)

JOBS_FILE = Path(__file__).resolve().parent.parent / "config" / "eris_web_jobs.json"
MAX_PENDING = 30
JOB_QUEUE = deque()

# HTML template for the job panel
PANEL_HTML = r'''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Eris AI – Panel de Trabajos</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:#0a0a12;color:#e0e0e0;font-family:'Segoe UI',sans-serif;min-height:100vh}
        .header{background:linear-gradient(135deg,#1a0533,#0d1b2a);padding:20px 30px;border-bottom:2px solid #a855f7;display:flex;justify-content:space-between;align-items:center}
        .header h1{color:#a855f7;font-size:24px;letter-spacing:2px}
        .header .stats{display:flex;gap:20px}
        .stat{background:rgba(168,85,247,.1);padding:8px 16px;border-radius:8px;text-align:center}
        .stat .num{color:#a855f7;font-size:20px;font-weight:bold}
        .stat .lbl{font-size:11px;color:#888;text-transform:uppercase}
        .container{max-width:1200px;margin:30px auto;padding:0 30px;display:grid;grid-template-columns:1fr 1fr;gap:20px}
        .panel{background:rgba(15,10,30,.8);border:1px solid rgba(168,85,247,.2);border-radius:12px;padding:20px}
        .panel h2{color:#a855f7;font-size:16px;margin-bottom:15px;text-transform:uppercase;letter-spacing:1px}
        .job{background:rgba(255,255,255,.03);border-left:3px solid #a855f7;padding:12px 15px;margin-bottom:10px;border-radius:4px}
        .job.priority-5{border-left-color:#ff3b30}
        .job.priority-4{border-left-color:#ff9500}
        .job.priority-3{border-left-color:#ffcc00}
        .job.priority-2{border-left-color:#34c759}
        .job.priority-1{border-left-color:#5ac8fa}
        .job .name{font-weight:bold;color:#fff;font-size:14px}
        .job .meta{font-size:11px;color:#888;margin-top:4px}
        .job .type{background:rgba(168,85,247,.2);padding:2px 8px;border-radius:4px;font-size:10px;margin-left:8px}
        .job .details{font-size:12px;color:#aaa;margin-top:6px}
        .form-group{margin-bottom:12px}
        .form-group label{display:block;font-size:12px;color:#888;margin-bottom:4px}
        .form-group input,.form-group textarea,.form-group select{width:100%;background:rgba(255,255,255,.05);border:1px solid rgba(168,85,247,.3);color:#fff;padding:8px 12px;border-radius:6px;font-size:13px}
        .form-group textarea{min-height:80px;resize:vertical}
        .btn{background:linear-gradient(135deg,#a855f7,#7c3aed);color:#fff;border:none;padding:10px 24px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:bold;letter-spacing:1px}
        .btn:hover{opacity:.9}
        .btn.danger{background:linear-gradient(135deg,#ff3b30,#dc2626)}
        .empty{text-align:center;color:#555;padding:40px;font-style:italic}
        @media(max-width:768px){.container{grid-template-columns:1fr}}
    </style>
</head>
<body>
<div class="header">
    <h1>⚡ ERIS AI – Panel de Trabajos</h1>
    <div class="stats">
        <div class="stat"><div class="num">{{pending}}</div><div class="lbl">Pendientes</div></div>
        <div class="stat"><div class="num">{{completed}}</div><div class="lbl">Completados</div></div>
        <div class="stat"><div class="num">{{failed}}</div><div class="lbl">Fallidos</div></div>
    </div>
</div>
<div class="container">
    <div class="panel">
        <h2>📋 Nuevo Trabajo</h2>
        <form method="POST" action="/api/submit">
            <div class="form-group"><label>Nombre del trabajo</label><input name="name" required placeholder="Ej: Auditar facturas Q2"></div>
            <div class="form-group"><label>Tipo</label><select name="type"><option value="analysis">Análisis</option><option value="file_op">Operación de archivos</option><option value="report">Reporte</option><option value="research">Investigación</option><option value="custom">Personalizado</option></select></div>
            <div class="form-group"><label>Prioridad (1-5)</label><input name="priority" type="number" min="1" max="5" value="3"></div>
            <div class="form-group"><label>Detalles / Instrucciones</label><textarea name="details" placeholder="Describe qué necesitas que Eris haga..."></textarea></div>
            <button class="btn" type="submit">📤 Enviar Trabajo</button>
        </form>
    </div>
    <div class="panel">
        <h2>⏳ Cola de Trabajos</h2>
        {% if jobs %}
        {% for job in jobs %}
        <div class="job priority-{{job.priority}}">
            <span class="name">#{{job.id}} {{job.name}}</span><span class="type">{{job.type}}</span>
            <div class="meta">Prioridad {{job.priority}} | {{job.created_at[:19]}}</div>
            <div class="details">{{job.details[:120]}}</div>
        </div>
        {% endfor %}
        {% else %}
        <div class="empty">Sin trabajos pendientes. ¡Envía uno!</div>
        {% endif %}
    </div>
</div>
</body>
</html>
'''

def _load_jobs():
    try:
        if JOBS_FILE.exists():
            return json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"pending": [], "completed": [], "failed": [], "total_completed": 0, "total_failed": 0}

def _save_jobs(data):
    JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    JOBS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

@app.route("/")
def panel():
    jobs = _load_jobs()
    return render_template_string(
        PANEL_HTML,
        pending=len(jobs["pending"]),
        completed=jobs["total_completed"],
        failed=jobs["total_failed"],
        jobs=jobs["pending"]
    )

@app.route("/api/submit", methods=["POST"])
def submit_job():
    jobs = _load_jobs()
    
    name = request.form.get("name", "").strip()
    job_type = request.form.get("type", "custom")
    priority = int(request.form.get("priority", 3))
    details = request.form.get("details", "").strip()
    
    if not name:
        return jsonify({"error": "Se requiere nombre del trabajo"}), 400
    
    if priority < 1: priority = 1
    if priority > 5: priority = 5
    
    if len(jobs["pending"]) >= MAX_PENDING:
        return jsonify({"error": f"Cola llena (máx {MAX_PENDING} trabajos). Intenta más tarde."}), 429
    
    job = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "type": job_type,
        "priority": priority,
        "details": details,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "source": "web"
    }
    
    jobs["pending"].append(job)
    jobs["pending"].sort(key=lambda j: -j["priority"])
    _save_jobs(jobs)
    
    return panel()

@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    jobs = _load_jobs()
    return jsonify(jobs)

@app.route("/api/jobs/next", methods=["GET"])
def get_next_job():
    """Eris (Python) calls this to get the next job to execute."""
    jobs = _load_jobs()
    if not jobs["pending"]:
        return jsonify({"job": None})
    
    job = jobs["pending"].pop(0)
    _save_jobs(jobs)
    return jsonify({"job": job})

@app.route("/api/jobs/<job_id>/complete", methods=["POST"])
def complete_job(job_id):
    """Eris marks a job as completed."""
    jobs = _load_jobs()
    for j in jobs["pending"]:
        if j["id"] == job_id:
            j["status"] = "completed"
            j["completed_at"] = datetime.now().isoformat()
            jobs["completed"].append(j)
            jobs["pending"].remove(j)
            jobs["total_completed"] += 1
            _save_jobs(jobs)
            return jsonify({"status": "ok"})
    return jsonify({"error": "Trabajo no encontrado"}), 404

@app.route("/api/jobs/<job_id>/fail", methods=["POST"])
def fail_job(job_id):
    jobs = _load_jobs()
    error_msg = request.json.get("error", "Desconocido") if request.is_json else "Desconocido"
    for j in jobs["pending"]:
        if j["id"] == job_id:
            j["status"] = "failed"
            j["error"] = error_msg
            j["failed_at"] = datetime.now().isoformat()
            jobs["failed"].append(j)
            jobs["pending"].remove(j)
            jobs["total_failed"] += 1
            _save_jobs(jobs)
            return jsonify({"status": "ok"})
    return jsonify({"error": "Trabajo no encontrado"}), 404

@app.route("/api/stats")
def stats():
    jobs = _load_jobs()
    return jsonify({
        "pending": len(jobs["pending"]),
        "completed": jobs["total_completed"],
        "failed": jobs["total_failed"],
        "total": jobs["total_completed"] + jobs["total_failed"]
    })

def start_server(host="127.0.0.1", port=5555):
    """Inicia el servidor web en un hilo separado."""
    thread = threading.Thread(target=app.run, kwargs={
        "host": host, "port": port, "debug": False, "use_reloader": False
    }, daemon=True)
    thread.start()
    return f"http://{host}:{port}"

def web_jobs(parameters: dict, player=None) -> str:
    """
    Sistema de recepción de trabajos vía web.
    
    Acciones:
      - start: Iniciar el servidor web (puerto 5555 por defecto)
      - stop: Detener el servidor
      - status: Ver estado del servidor y cola de trabajos
      - next: Obtener el siguiente trabajo pendiente para ejecutar
      - complete: Marcar un trabajo como completado (requiere job_id)
      - fail: Marcar un trabajo como fallido (requiere job_id)
    """
    action = parameters.get("action", "status").lower()
    
    if action == "start":
        port = int(parameters.get("port", 5555))
        url = start_server(port=port)
        return f"🌐 Servidor web iniciado en {url}\nPanel de trabajos: {url}"
    
    elif action == "status":
        jobs = _load_jobs()
        return (
            f"📊 **Estado del Panel de Trabajos:**\n\n"
            f"  Pendientes: {len(jobs['pending'])}\n"
            f"  Completados: {jobs['total_completed']}\n"
            f"  Fallidos: {jobs['total_failed']}\n"
            f"  Capacidad: {len(jobs['pending'])}/{MAX_PENDING}"
        )
    
    elif action == "next":
        jobs = _load_jobs()
        if not jobs["pending"]:
            return "No hay trabajos pendientes."
        
        job = jobs["pending"].pop(0)
        _save_jobs(jobs)
        return (
            f"📋 **Trabajo #{job['id']}**: {job['name']}\n"
            f"  Tipo: {job['type']} | Prioridad: {job['priority']}/5\n"
            f"  Detalles: {job['details'][:200]}"
        )
    
    elif action == "complete":
        job_id = parameters.get("job_id", "")
        if not job_id:
            return "Error: Se requiere job_id"
        jobs = _load_jobs()
        for j in jobs["pending"]:
            if j["id"] == job_id:
                j["status"] = "completed"
                j["completed_at"] = datetime.now().isoformat()
                jobs["completed"].append(j)
                jobs["pending"].remove(j)
                jobs["total_completed"] += 1
                _save_jobs(jobs)
                return f"✅ Trabajo #{job_id} completado."
        return f"❌ Trabajo #{job_id} no encontrado."
    
    elif action == "fail":
        job_id = parameters.get("job_id", "")
        error = parameters.get("error", "Error desconocido")
        if not job_id:
            return "Error: Se requiere job_id"
        jobs = _load_jobs()
        for j in jobs["pending"]:
            if j["id"] == job_id:
                j["status"] = "failed"
                j["error"] = error
                j["failed_at"] = datetime.now().isoformat()
                jobs["failed"].append(j)
                jobs["pending"].remove(j)
                jobs["total_failed"] += 1
                _save_jobs(jobs)
                return f"❌ Trabajo #{job_id} marcado como fallido."
        return f"❌ Trabajo #{job_id} no encontrado."
    
    return f"Acción '{action}' no reconocida. Usa: start, status, next, complete, fail"
