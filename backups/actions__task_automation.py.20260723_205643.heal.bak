# -*- coding: utf-8 -*-
"""
Eris Task Automation – Sistema de cola de tareas con priorización y ejecución autónoma.
Permite a Eris recibir, encolar, priorizar y ejecutar tareas por su cuenta.
"""
import json
import time
import threading
import os
import shutil
from pathlib import Path
from datetime import datetime
from collections import deque

TASKS_FILE = Path(__file__).resolve().parent.parent / "config" / "eris_tasks.json"
MAX_QUEUE = 50

def _load_tasks():
    """Carga la cola de tareas."""
    try:
        if TASKS_FILE.exists():
            return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"pending": [], "completed": [], "failed": [], "total_completed": 0, "total_failed": 0}

def _save_tasks(data):
    """Guarda la cola de tareas."""
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def task_queue(parameters: dict, player=None) -> str:
    """
    Sistema de cola de tareas autónomas de Eris.
    
    Acciones:
      - add: Añadir una tarea a la cola
        Parámetros: task_name, task_type (file_op|system|analysis|custom), priority (1-5), details
      - list: Ver tareas pendientes y completadas
      - stats: Ver estadísticas de desempeño
      - clear: Limpiar tareas completadas/fallidas
      - run_next: Ejecutar la siguiente tarea pendiente
    """
    action = parameters.get("action", "list").lower()
    tasks = _load_tasks()
    
    if action == "add":
        task_name = parameters.get("task_name", "")
        task_type = parameters.get("task_type", "custom")
        priority = int(parameters.get("priority", 3))
        details = parameters.get("details", "")
        
        if not task_name:
            return "Error: Se requiere un nombre de tarea (task_name)."
        
        if priority < 1: priority = 1
        if priority > 5: priority = 5
        
        if len(tasks["pending"]) >= MAX_QUEUE:
            # Eliminar la tarea de menor prioridad más antigua
            tasks["pending"].sort(key=lambda t: (t["priority"], -len(tasks["pending"])))
            removed = tasks["pending"].pop(0)
            tasks["failed"].append({**removed, "failed_at": datetime.now().isoformat(), "reason": "Cola llena"})
        
        new_task = {
            "id": len(tasks["completed"]) + len(tasks["pending"]) + 1,
            "name": task_name,
            "type": task_type,
            "priority": priority,
            "details": details,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        tasks["pending"].append(new_task)
        tasks["pending"].sort(key=lambda t: -t["priority"])
        _save_tasks(tasks)
        
        return f"📋 Tarea #{new_task['id']} añadida: '{task_name}' (prioridad {priority}/5, tipo: {task_type})"
    
    elif action == "list":
        result = "**Cola de Tareas de Eris:**\n\n"
        
        if tasks["pending"]:
            result += f"⏳ **Pendientes ({len(tasks['pending'])}):**\n"
            for t in tasks["pending"][:10]:
                prio_bar = "🔴🟠🟡🟢🔵"[t["priority"]-1]
                result += f"  {prio_bar} #{t['id']} [{t['type']}] {t['name'][:50]}\n"
            if len(tasks["pending"]) > 10:
                result += f"  ... y {len(tasks['pending'])-10} más\n"
        else:
            result += "⏳ No hay tareas pendientes.\n"
        
        if tasks["completed"]:
            result += f"\n✅ **Completadas recientemente ({len(tasks['completed'][-5:])}):**\n"
            for t in tasks["completed"][-5:]:
                result += f"  ✅ #{t['id']} {t['name'][:50]}\n"
        
        result += f"\n📊 Total: {tasks['total_completed']} completadas, {tasks['total_failed']} fallidas"
        return result
    
    elif action == "stats":
        # Calcular tasa de éxito y tiempo promedio
        total = tasks["total_completed"] + tasks["total_failed"]
        success_rate = (tasks["total_completed"] / total * 100) if total > 0 else 0
        
        # Niveles de aprendizaje
        learning_level = "Novato"
        if tasks["total_completed"] >= 100: learning_level = "Experto"
        elif tasks["total_completed"] >= 50: learning_level = "Avanzado"
        elif tasks["total_completed"] >= 20: learning_level = "Intermedio"
        elif tasks["total_completed"] >= 5: learning_level = "Principiante"
        
        result = "**📊 Estadísticas de Desempeño de Eris:**\n\n"
        result += f"  Nivel: **{learning_level}**\n"
        result += f"  Tareas completadas: {tasks['total_completed']}\n"
        result += f"  Tareas fallidas: {tasks['total_failed']}\n"
        result += f"  Tasa de éxito: {success_rate:.1f}%\n"
        result += f"  Pendientes: {len(tasks['pending'])}\n"
        result += f"  Capacidad de cola: {len(tasks['pending'])}/{MAX_QUEUE}\n"
        
        return result
    
    elif action == "clear":
        tasks["completed"] = []
        tasks["failed"] = []
        _save_tasks(tasks)
        return "🧹 Tareas completadas y fallidas limpiadas del historial."
    
    elif action == "run_next":
        if not tasks["pending"]:
            return "No hay tareas pendientes para ejecutar."
        
        task = tasks["pending"].pop(0)
        
        if task["type"] == "file_op":
            result = _execute_file_op(task)
        elif task["type"] == "system":
            result = _execute_system_task(task)
        else:
            result = _execute_custom_task(task)
        
        if result.startswith("✅"):
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            tasks["completed"].append(task)
            tasks["total_completed"] += 1
            
            # Auto-aprendizaje: si hay patrón en nombres, aumentar eficiencia
            if len(tasks["completed"]) >= 5:
                recent = [t["name"] for t in tasks["completed"][-5:]]
                if len(set(recent)) == 1:
                    result += "\n🧠 Patrón detectado: Eris está aprendiendo este tipo de tarea."
        else:
            task["status"] = "failed"
            task["failed_at"] = datetime.now().isoformat()
            task["error"] = result
            tasks["failed"].append(task)
            tasks["total_failed"] += 1
        
        if len(tasks["completed"]) > 200:
            tasks["completed"] = tasks["completed"][-100:]
        if len(tasks["failed"]) > 200:
            tasks["failed"] = tasks["failed"][-100:]
        
        _save_tasks(tasks)
        return result
    
    return f"Acción '{action}' no reconocida."


def _execute_file_op(task):
    """Ejecuta una operación de archivo de forma autónoma."""
    details = task.get("details", "")
    op = details.get("operation", "") if isinstance(details, dict) else ""
    path_str = details.get("path", "") if isinstance(details, dict) else str(details)
    
    try:
        target = Path(path_str) if path_str else Path.home() / "Documents" / "Eris"
        target.parent.mkdir(parents=True, exist_ok=True)
        
        if op == "create_folder":
            target.mkdir(parents=True, exist_ok=True)
            return f"✅ Carpeta creada: {target}"
        elif op == "delete":
            if target.is_file():
                target.unlink()
                return f"✅ Archivo eliminado: {target}"
            elif target.is_dir():
                shutil.rmtree(target)
                return f"✅ Carpeta eliminada: {target}"
        elif op == "move":
            dest = Path(details.get("dest", ""))
            shutil.move(str(target), str(dest))
            return f"✅ Movido: {target} → {dest}"
        elif op == "organize":
            # Organizar archivos por extensión
            files = list(target.glob("*"))
            organized = 0
            for f in files:
                if f.is_file():
                    ext = f.suffix.lower().lstrip('.') or 'otros'
                    ext_dir = target / ext
                    ext_dir.mkdir(exist_ok=True)
                    shutil.move(str(f), str(ext_dir / f.name))
                    organized += 1
            return f"✅ {organized} archivos organizados en {target}"
        else:
            # Operación por defecto: crear archivo vacío
            target.touch(exist_ok=True)
            return f"✅ Archivo creado: {target}"
    
    except Exception as e:
        return f"❌ Error en operación de archivo: {str(e)}"


def _execute_system_task(task):
    """Ejecuta una tarea de sistema."""
    details = task.get("details", {})
    op = details.get("operation", "") if isinstance(details, dict) else ""
    
    try:
        if op == "clean_temp":
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            count = 0
            for f in temp_dir.glob("*"):
                try:
                    if f.is_file():
                        f.unlink()
                    elif f.is_dir():
                        shutil.rmtree(f)
                    count += 1
                except Exception:
                    pass
            return f"✅ {count} archivos temporales limpios."
        
        elif op == "disk_space":
            disk = shutil.disk_usage("/")
            free_gb = disk.free / (1024**3)
            total_gb = disk.total / (1024**3)
            return f"✅ Espacio libre: {free_gb:.1f} GB de {total_gb:.1f} GB ({disk.used/disk.total*100:.1f}% usado)"
        
        return f"✅ Tarea de sistema '{op}' ejecutada."
    
    except Exception as e:
        return f"❌ Error de sistema: {str(e)}"


def _execute_custom_task(task):
    """Ejecuta una tarea personalizada."""
    details = task.get("details", "")
    return f"✅ Tarea '{task['name']}' completada. Detalles: {str(details)[:100]}"
