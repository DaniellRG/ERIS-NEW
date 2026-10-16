# -*- coding: utf-8 -*-
"""
Eris Resource Manager – Monitoreo y optimización de recursos del sistema.
Controla CPU, RAM, disco y procesos para mantener la estabilidad.
"""
import psutil
import os
import gc
import time
from pathlib import Path
from datetime import datetime

def res_monitor(parameters: dict, player=None) -> str:
    """
    Monitor de recursos del sistema – supervisa y reporta el estado de CPU, RAM, disco.
    
    Acciones:
      - status: Reporte completo del estado actual
      - optimize: Liberar RAM y recursos no utilizados
      - top_processes: Ver los procesos que más consumen
      - alerts: Verificar si hay condiciones de alerta
    """
    action = parameters.get("action", "status").lower()
    
    if action == "status":
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot = datetime.fromtimestamp(psutil.boot_time())
            
            result = "**🖥️ Estado del Sistema:**\n\n"
            result += f"  **CPU:** {cpu:.1f}% | Núcleos: {psutil.cpu_count(logical=False)} físicos / {psutil.cpu_count()} lógicos\n"
            result += f"  **RAM:** {mem.percent:.1f}% | {mem.used/(1024**3):.1f}/{mem.total/(1024**3):.1f} GB\n"
            
            # Barras visuales
            bar_len = 10
            cpu_bar = "█" * int(cpu / 10) + "░" * (bar_len - int(cpu / 10))
            ram_bar = "█" * int(mem.percent / 10) + "░" * (bar_len - int(mem.percent / 10))
            result += f"  CPU [{cpu_bar}] {cpu:.1f}%\n"
            result += f"  RAM [{ram_bar}] {mem.percent:.1f}%\n\n"
            
            result += f"  **Disco:** {disk.percent:.1f}% usado | Libre: {disk.free/(1024**3):.1f} GB\n"
            result += f"  **Uptime:** desde {boot.strftime('%H:%M')}\n"
            
            # Alertas
            alerts = []
            if cpu > 80: alerts.append("⚠️ CPU alta")
            if mem.percent > 85: alerts.append("⚠️ RAM crítica")
            if disk.percent > 90: alerts.append("⚠️ Disco casi lleno")
            if alerts:
                result += f"\n  {', '.join(alerts)}"
            
            return result
        except Exception as e:
            return f"Error al obtener métricas: {str(e)}"
    
    elif action == "optimize":
        results = []
        
        # Liberar RAM via garbage collector
        gc.collect()
        results.append("🧹 Garbage collector ejecutado")
        
        # Cerrar procesos que consumen mucha RAM (solo los no críticos)
        freed = 0
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                if proc.info['memory_percent'] and proc.info['memory_percent'] > 10:
                    proc_name = proc.info['name'].lower()
                    # No cerrar procesos del sistema
                    if proc_name in ('chrome.exe', 'msedge.exe', 'firefox.exe'):
                        results.append(f"⚠️ {proc.info['name']} consume {proc.info['memory_percent']:.1f}% RAM")
                    elif 'python' not in proc_name and 'system' not in proc_name:
                        pass  # No matar procesos automáticamente
            except Exception:
                pass
        
        # Limpiar carpeta temp
        import tempfile
        temp_dir = Path(tempfile.gettempdir())
        temp_count = 0
        for f in list(temp_dir.glob("*"))[:100]:
            try:
                if f.is_file() and (time.time() - f.stat().st_mtime) > 86400:  # > 1 día
                    f.unlink()
                    temp_count += 1
            except Exception:
                pass
        
        results.append(f"🧹 {temp_count} archivos temporales viejos eliminados")
        
        return "✅ **Optimización completada:**\n" + "\n".join(f"  {r}" for r in results)
    
    elif action == "top_processes":
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except Exception:
                pass
        
        # Ordenar por CPU
        processes.sort(key=lambda p: p['cpu_percent'] or 0, reverse=True)
        
        result = "**📊 Top 10 procesos por CPU:**\n\n"
        for p in processes[:10]:
            name = (p['name'] or '?')[:25]
            cpu = p['cpu_percent'] or 0
            mem = p['memory_percent'] or 0
            result += f"  {name:25s} CPU: {cpu:5.1f}%  RAM: {mem:5.1f}%\n"
        
        return result
    
    elif action == "alerts":
        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        alerts = []
        if cpu > 85:
            alerts.append({"level": "critical", "msg": f"CPU al {cpu:.0f}% - Sistema sobrecargado"})
        elif cpu > 60:
            alerts.append({"level": "warning", "msg": f"CPU al {cpu:.0f}% - Carga elevada"})
        
        if mem.percent > 90:
            alerts.append({"level": "critical", "msg": f"RAM al {mem.percent:.0f}% - Riesgo de colapso"})
        elif mem.percent > 70:
            alerts.append({"level": "warning", "msg": f"RAM al {mem.percent:.0f}% - Memoria escasa"})
        
        if disk.percent > 95:
            alerts.append({"level": "critical", "msg": f"Disco al {disk.percent:.0f}% - Sin espacio"})
        
        if not alerts:
            return "✅ Sin alertas. Sistema estable."
        
        result = "**⚠️ Alertas del Sistema:**\n\n"
        for a in alerts:
            icon = "🔴" if a["level"] == "critical" else "🟡"
            result += f"  {icon} {a['msg']}\n"
        
        return result
    
    return f"Acción '{action}' no reconocida."


def res_protect(parameters: dict, player=None) -> str:
    """
    Protección contra sobrecarga – si el sistema está al límite, entra en modo seguro.
    Reduce consumo priorizando estabilidad sobre velocidad.
    """
    cpu = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory()
    
    if cpu > 90 or mem.percent > 92:
        # Modo de emergencia
        gc.collect()
        
        # Reducir prioridad de procesos no críticos
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid']):
            try:
                if proc.info['pid'] != current_pid:
                    p = psutil.Process(proc.info['pid'])
                    if p.nice() == 0:  # Prioridad normal
                        p.nice(5)  # Bajar prioridad
            except Exception:
                pass
        
        return "🔴 **Modo Overloaded activado.** Reduciendo consumo. Priorizando estabilidad."
    
    elif cpu > 70 or mem.percent > 75:
        gc.collect()
        return "🟡 **Precaución.** Recursos elevados. Liberando memoria y monitoreando."
    
    else:
        return "✅ Sistema estable. No se requiere protección."
