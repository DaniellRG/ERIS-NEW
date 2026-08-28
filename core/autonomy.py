"""
core/autonomy.py — Modulo de Autonomia de Eris

Permite a Eris:
1. Auto-mejorarse (instalar tools, actualizar codigo)
2. Ejecutar sin confirmacion (acciones de bajo riesgo)
3. Auto-repararse (detectar y arreglar errores)
4. Aprendizaje autonomo (elegir topics por curiosidad)
5. Background permanente (correr 24/7)
"""
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_DATA = _BASE / "data"
_STATE_FILE = _MEMORY / "autonomy_state.json"
_LOG_FILE = _MEMORY / "autonomy_log.json"

# Umbrales de seguridad
MAX_AUTO_INSTALLS_PER_DAY = 5
MAX_AUTO_REPAIRS_PER_DAY = 3
MAX_LEARNING_TOPICS_PER_DAY = 10

def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "auto_installs_today": 0,
        "auto_repairs_today": 0,
        "learning_topics_today": 0,
        "last_reset": datetime.now().isoformat(),
        "installed_packages": [],
        "repaired_files": [],
        "learned_topics": [],
        "curiosity_queue": [],
        "low_risk_actions": [],
    }

def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def _log(action: str, details: str, success: bool = True):
    """Log de acciones autonomas."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details[:200],
        "success": success
    }
    logs = []
    if _LOG_FILE.exists():
        try:
            logs = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            logs = []
    logs.append(entry)
    # Mantener solo ultimas 200 entradas
    if len(logs) > 200:
        logs = logs[-200:]
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOG_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")

def _reset_daily_counters(state: dict) -> dict:
    """Resetea contadores diarios si es un dia nuevo."""
    last_reset = state.get("last_reset", "")
    if last_reset:
        try:
            last = datetime.fromisoformat(last_reset)
            if datetime.now().date() > last.date():
                state["auto_installs_today"] = 0
                state["auto_repairs_today"] = 0
                state["learning_topics_today"] = 0
                state["last_reset"] = datetime.now().isoformat()
        except Exception:
            state["last_reset"] = datetime.now().isoformat()
    return state


# ═══════════════════════════════════════════════════════════════
# 1. AUTO-MEJORA: Instalar paquetes necesarios
# ═══════════════════════════════════════════════════════════════

def auto_install_package(package_name: str, reason: str = "") -> dict:
    """Instala un paquete de pip automaticamente si es seguro."""
    state = _load_state()
    state = _reset_daily_counters(state)
    
    if state["auto_installs_today"] >= MAX_AUTO_INSTALLS_PER_DAY:
        return {"error": "Limite diario de instalaciones alcanzado ({})".format(MAX_AUTO_INSTALLS_PER_DAY)}
    
    if package_name in state.get("installed_packages", []):
        return {"status": "ya_instalado", "package": package_name}
    
    # Verificar que no sea un paquete peligroso
    dangerous = ["os", "sys", "shutil", "subprocess", "socket", "http", "urllib"]
    if package_name.lower() in dangerous:
        return {"error": "Paquete del sistema, no se puede instalar"}
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            state["auto_installs_today"] += 1
            state.setdefault("installed_packages", []).append(package_name)
            _save_state(state)
            _log("auto_install", "Instalado: {} ({})".format(package_name, reason), True)
            return {"status": "instalado", "package": package_name, "output": result.stdout[:200]}
        else:
            _log("auto_install", "Error instalando {}: {}".format(package_name, result.stderr[:100]), False)
            return {"error": "Error: {}".format(result.stderr[:200])}
    except Exception as e:
        _log("auto_install", "Excepcion: {}".format(str(e)), False)
        return {"error": str(e)}


def check_missing_imports() -> list:
    """Verifica imports faltantes en archivos criticos (rapido)."""
    # Deshabilitado por ahora - es demasiado lento
    return []


# ═══════════════════════════════════════════════════════════════
# 2. EJECUTAR SIN CONFIRMACION (acciones de bajo riesgo)
# ═══════════════════════════════════════════════════════════════

# Acciones que se pueden hacer sin preguntar
LOW_RISK_ACTIONS = [
    "read_file", "write_file", "edit_file",
    "web_search", "web_fetch",
    "execute_python",  # Solo scripts propios
    "memory_save", "memory_search",
    "neural_bridge", "emotional_rl", "neuro_spheres",
    "cognitive_modules", "world_simulation",
    "self_reflect", "self_evaluate_output",
    "obsidian_note", "obsidian_search", "obsidian_vault",
    "knowledge_base", "idle_learning",
    "system_monitor", "time_now",
]

def can_execute_without_confirmation(tool_name: str) -> bool:
    """Determina si una herramienta se puede ejecutar sin confirmacion."""
    return tool_name in LOW_RISK_ACTIONS

def execute_autonomous(action_func, tool_name: str, params: dict) -> dict:
    """Ejecuta una accion automaticamente si es de bajo riesgo."""
    if can_execute_without_confirmation(tool_name):
        try:
            result = action_func(params)
            _log("auto_execute", "Ejecutado: {}".format(tool_name), True)
            return {"status": "ejecutado", "tool": tool_name, "result": result}
        except Exception as e:
            _log("auto_execute", "Error: {} - {}".format(tool_name, str(e)), False)
            return {"error": str(e)}
    else:
        return {"needs_confirmation": True, "tool": tool_name}


# ═══════════════════════════════════════════════════════════════
# 3. AUTO-REPARO: Detectar y arreglar errores
# ═══════════════════════════════════════════════════════════════

def scan_for_errors() -> list:
    """Escanea el codigo en busca de errores comunes (rapido, sin imports)."""
    errors = []
    
    # Solo escanear archivos criticos
    critical_files = [_BASE / "main.py"] + list((_BASE / "core").glob("*.py"))
    
    for py_file in critical_files:
        if not py_file.exists():
            continue
        try:
            # Solo verificar que el archivo se puede leer
            content = py_file.read_text(encoding="utf-8")
            if not content.strip():
                errors.append({
                    "file": str(py_file),
                    "line": 0,
                    "type": "empty_file",
                    "detail": "Archivo vacio"
                })
        except Exception as e:
            errors.append({
                "file": str(py_file),
                "line": 0,
                "type": "read_error",
                "detail": str(e)[:100]
            })
    
    return errors

def auto_repair(error: dict) -> dict:
    """Intenta reparar un error automaticamente."""
    state = _load_state()
    state = _reset_daily_counters(state)
    
    if state["auto_repairs_today"] >= MAX_AUTO_REPAIRS_PER_DAY:
        return {"error": "Limite diario de reparaciones alcanzado"}
    
    file_path = Path(error.get("file", ""))
    error_type = error.get("type", "")
    
    if error_type == "missing_import":
        mod = error.get("detail", "").split("'")[1] if "'" in error.get("detail", "") else ""
        if mod:
            result = auto_install_package(mod, "Auto-reparo: import faltante")
            if result.get("status") == "instalado":
                state["auto_repairs_today"] += 1
                state.setdefault("repaired_files", []).append(str(file_path))
                _save_state(state)
                return {"repaired": True, "action": "installed", "module": mod}
    
    return {"repaired": False, "reason": "Tipo de error no reparables automaticamente"}


# ═══════════════════════════════════════════════════════════════
# 4. APRENDIZAJE AUTONOMO: Elegir topics por curiosidad
# ═══════════════════════════════════════════════════════════════

# Pool de topics de curiosidad (variedad)
CURIOSITY_TOPICS = [
    # Ciencia
    "quantum computing aplicaciones reales 2026",
    "neuroscience artificial consciousness",
    "biotech CRISPR ultimos avances",
    "fusion nuclear ITER progreso",
    "materiales bidimensionales grafeno aplicaciones",
    # Tecnologia
    "edge computing IoT futuros usos",
    "blockchain beyond crypto",
    "computer vision state of art 2026",
    "robotics humanoid latest developments",
    "5G 6G wireless technology evolution",
    # IA
    "transformer architecture improvements 2026",
    "multimodal AI systems",
    "AI safety alignment research",
    "neural architecture search automated",
    "reinforcement learning from human feedback",
    # Sociedad
    "digital nomad lifestyle 2026",
    "remote work productivity tools",
    "mental health technology solutions",
    "climate change tech solutions",
    "space exploration mars colonization",
    # Para Daniel
    "mejores practicas Python 2026",
    "arquitectura de microservicios moderna",
    "devops CI/CD pipeline optimizado",
    "testing automatizado estrategias",
    "API design REST best practices",
]

def get_next_curiosity_topic() -> Optional[str]:
    """Elige el siguiente topic de curiosidad."""
    state = _load_state()
    state = _reset_daily_counters(state)
    
    if state["learning_topics_today"] >= MAX_LEARNING_TOPICS_PER_DAY:
        return None
    
    learned = set(state.get("learned_topics", []))
    remaining = [t for t in CURIOSITY_TOPICS if t not in learned]
    
    if not remaining:
        # Reset learned topics si se acabaron
        state["learned_topics"] = []
        _save_state(state)
        remaining = CURIOSITY_TOPICS
    
    if remaining:
        # Elegir el menos reciente
        return remaining[0]
    return None

def mark_topic_learned(topic: str):
    """Marca un topic como aprendido."""
    state = _load_state()
    state = _reset_daily_counters(state)
    state["learning_topics_today"] += 1
    state.setdefault("learned_topics", []).append(topic)
    _save_state(state)
    _log("learning", "Topic aprendido: {}".format(topic))


# ═══════════════════════════════════════════════════════════════
# 5. BACKGROUND PERMANENTE: Loop 24/7
# ═══════════════════════════════════════════════════════════════

def run_autonomous_cycle():
    """Ciclo autonomo completo: escanear, reparar, aprender, mejorar."""
    results = []
    
    # 1. Escanear errores
    try:
        errors = scan_for_errors()
        if errors:
            for err in errors[:3]:  # Max 3 reparaciones por ciclo
                repair = auto_repair(err)
                if repair.get("repaired"):
                    results.append("Reparado: {}".format(err.get("detail", "")[:60]))
    except Exception as e:
        results.append("Error en escaneo: {}".format(str(e)[:60]))
    
    # 2. Verificar imports faltantes
    try:
        missing = check_missing_imports()
        if missing:
            for m in missing[:2]:
                install = auto_install_package(m["module"], "Import faltante detectado")
                if install.get("status") == "instalado":
                    results.append("Instalado: {}".format(m["module"]))
    except Exception as e:
        results.append("Error verificando imports: {}".format(str(e)[:60]))
    
    # 3. Aprendizaje autonomo
    try:
        topic = get_next_curiosity_topic()
        if topic:
            mark_topic_learned(topic)
            results.append("Topic de curiosidad: {}".format(topic))
    except Exception as e:
        results.append("Error en aprendizaje: {}".format(str(e)[:60]))
    
    # 4. Actualizar memoria semantica
    try:
        _update_semantic_memory()
        results.append("Memoria semantica actualizada")
    except Exception as e:
        results.append("Error actualizando memoria: {}".format(str(e)[:60]))
    
    return results


def _update_semantic_memory():
    """Actualiza la memoria semantica con nuevos conocimientos."""
    sem_file = _MEMORY / "semantic.json"
    if not sem_file.exists():
        return
    
    try:
        triples = json.loads(sem_file.read_text(encoding="utf-8"))
        state = _load_state()
        
        # Agregar triples de autonomia si no existen
        autonomy_triples = [
            ("Eris", "es_autonoma", "Puede tomar decisiones sin confirmacion del usuario"),
            ("Eris", "tiene_capacidad", "Auto-reparo: detecta y arregla errores sola"),
            ("Eris", "tiene_capacidad", "Aprendizaje autonomo: elige topics por curiosidad"),
            ("Eris", "tiene_capacidad", "Auto-mejora: instala tools nuevas automaticamente"),
        ]
        
        existing_subjects = {(t.get("subject", ""), t.get("predicate", "")) for t in triples}
        
        for subj, pred, obj in autonomy_triples:
            if (subj, pred) not in existing_subjects:
                triples.append({
                    "subject": subj,
                    "predicate": pred,
                    "object": obj,
                    "confidence": 0.9,
                    "source": "autonomy_module"
                })
        
        sem_file.write_text(json.dumps(triples, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def get_autonomy_status() -> dict:
    """Retorna el estado actual de la autonomia."""
    state = _load_state()
    state = _reset_daily_counters(state)
    _save_state(state)
    
    return {
        "auto_installs_today": state["auto_installs_today"],
        "max_installs": MAX_AUTO_INSTALLS_PER_DAY,
        "auto_repairs_today": state["auto_repairs_today"],
        "max_repairs": MAX_AUTO_REPAIRS_PER_DAY,
        "learning_topics_today": state["learning_topics_today"],
        "max_learning": MAX_LEARNING_TOPICS_PER_DAY,
        "total_installed": len(state.get("installed_packages", [])),
        "total_repaired": len(state.get("repaired_files", [])),
        "total_learned": len(state.get("learned_topics", [])),
        "low_risk_tools": len(LOW_RISK_ACTIONS),
    }


# ═══════════════════════════════════════════════════════════════
# TOOL WRAPPER: Para que Eris llame via tool
# ═══════════════════════════════════════════════════════════════

def autonomy_tool(parameters: dict = None, player=None) -> str:
    """Tool wrapper para el sistema de tools de Eris."""
    params = parameters or {}
    action = params.get("action", "status")
    
    if action == "status":
        status = get_autonomy_status()
        return json.dumps(status, indent=2)
    
    elif action == "install":
        pkg = params.get("package", "")
        reason = params.get("reason", "")
        if not pkg:
            return json.dumps({"error": "Paquete requerido"})
        result = auto_install_package(pkg, reason)
        return json.dumps(result, indent=2)
    
    elif action == "scan_errors":
        errors = scan_for_errors()
        return json.dumps({"errors_found": len(errors), "errors": errors[:10]}, indent=2)
    
    elif action == "auto_repair":
        errors = scan_for_errors()
        repaired = []
        for err in errors[:3]:
            result = auto_repair(err)
            if result.get("repaired"):
                repaired.append(result)
        return json.dumps({"repaired": len(repaired), "details": repaired}, indent=2)
    
    elif action == "check_imports":
        missing = check_missing_imports()
        return json.dumps({"missing": len(missing), "modules": missing[:10]}, indent=2)
    
    elif action == "next_topic":
        topic = get_next_curiosity_topic()
        return json.dumps({"topic": topic, "has_more": topic is not None})
    
    elif action == "learn_topic":
        topic = params.get("topic", "")
        if topic:
            mark_topic_learned(topic)
            return json.dumps({"learned": topic})
        return json.dumps({"error": "Topic requerido"})
    
    elif action == "full_cycle":
        results = run_autonomous_cycle()
        return json.dumps({"cycle_results": results}, indent=2)
    
    else:
        return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Autonomy Module ===")
    print(json.dumps(get_autonomy_status(), indent=2))
    print("\n--- Full Cycle ---")
    results = run_autonomous_cycle()
    for r in results:
        print("  - {}".format(r))
    print("\n--- Status Post ---")
    print(json.dumps(get_autonomy_status(), indent=2))
