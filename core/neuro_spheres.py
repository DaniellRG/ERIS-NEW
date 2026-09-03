"""
neuro_spheres.py — Sistema de Dos Esferas Interconectadas de Eris
Cerebro visual que crece con cada interacción. Guarda nodos en Obsidian.
Inspirado en Wichito's Neuro + JCySharp's simulated consciousness.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from core.logging_setup import get_obsidian_vault

_BASE = Path(__file__).resolve().parent.parent
_OBSIDIAN_VAULT = get_obsidian_vault()
_NEURO_DIR = _OBSIDIAN_VAULT / "NeuroSpheres"
_STATE_FILE = _BASE / "memory" / "neuro_spheres_state.json"

# ── Carpetas de las esferas
SPHERES = {
    "aprendizaje": _NEURO_DIR / "Aprendizaje",
    "memoria": _NEURO_DIR / "Memoria",
    "emociones": _NEURO_DIR / "Emociones",
    "habilidad": _NEURO_DIR / "Habilidad",
    "codigo": _NEURO_DIR / "Codigo",
    "ejecucion": _NEURO_DIR / "Ejecucion",
    "investigacion": _NEURO_DIR / "Investigacion",
    "solucion": _NEURO_DIR / "Solucion",
    "error": _NEURO_DIR / "Error",
    "bug": _NEURO_DIR / "Bug",
    "diagnostico": _NEURO_DIR / "Diagnostico",
}

# ── Tipos de nodos
NODE_TYPES = {
    "aprendizaje": {
        "desc": "Algo que Eris aprendio de una interaccion",
        "color": "#3498db",  # azul
        "icon": "lightbulb",
    },
    "memoria": {
        "desc": "Conexion entre aprendizajes o recuerdos",
        "color": "#2ecc71",  # verde
        "icon": "link",
    },
    "emocion": {
        "desc": "Registro emocional de una experiencia",
        "color": "#e74c3c",  # rojo
        "icon": "heart",
    },
    "habilidad": {
        "desc": "Nueva habilidad o capacidad aprendida",
        "color": "#9b59b6",  # purpura
        "icon": "star",
    },
    "preferencia": {
        "desc": "Preferencia o patron del usuario",
        "color": "#f39c12",  # naranja
        "icon": "user",
    },
    "error": {
        "desc": "Error encontrado: que fallo, por que, y como se soluciono",
        "color": "#e74c3c",  # rojo
        "icon": "alert",
    },
    "bug": {
        "desc": "Bug detectado: sintaxis, logica, runtime, o compilacion",
        "color": "#c0392b",  # rojo oscuro
        "icon": "bug",
    },
    "solucion": {
        "desc": "Solucion aplicada: que funciono y por que",
        "color": "#27ae60",  # verde brillante
        "icon": "check",
    },
    "diagnostico": {
        "desc": "Diagnostico completo: analisis, causa raiz, pasos para resolver",
        "color": "#2980b9",  # azul oscuro
        "icon": "search",
    },
}

# ── Cache
_cache: dict = {"mtime": 0.0, "state": None}


def _load_state() -> dict:
    try:
        mtime = _STATE_FILE.stat().st_mtime
        if _cache["state"] is not None and _cache["mtime"] == mtime:
            return _cache["state"]
        data = json.loads(_STATE_FILE.read_text("utf-8"))
        _cache.update(mtime=mtime, state=data)
        return data
    except Exception:
        default = {
            "total_nodes": 0,
            "total_connections": 0,
            "nodes": {},  # node_id → {sphere, type, title, force, connections, created, last_used}
            "last_add": None,
            "last_connect": None,
            "growth_history": [],  # [{timestamp, action, node_id}]
        }
        _cache.update(mtime=0.0, state=default)
        return default


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")
    _cache.update(mtime=_STATE_FILE.stat().st_mtime, state=state)


def _ensure_dirs():
    """Crea las carpetas en Obsidian si no existen."""
    for sphere_path in SPHERES.values():
        sphere_path.mkdir(parents=True, exist_ok=True)


def _create_md_node(node_id: str, sphere: str, node_type: str, title: str, 
                     content: str, connections: List[str], force: int) -> Path:
    """Crea un archivo .md en Obsidian para un nodo."""
    _ensure_dirs()
    
    sphere_path = SPHERES.get(sphere, SPHERES["aprendizaje"])
    type_info = NODE_TYPES.get(node_type, NODE_TYPES["aprendizaje"])
    
    # Frontmatter
    frontmatter = {
        "tipo": node_type,
        "esfera": sphere,
        "fuerza": force,
        "color": type_info["color"],
        "icon": type_info["icon"],
        "fecha_creacion": datetime.now().isoformat(),
        "ultimo_uso": datetime.now().isoformat(),
        "conexiones": connections,
    }
    
    # Convertir frontmatter a YAML
    fm_lines = ["---"]
    for key, value in frontmatter.items():
        if isinstance(value, list):
            fm_lines.append(f"{key}:")
            for item in value:
                fm_lines.append(f"  - {item}")
        else:
            fm_lines.append(f"{key}: {value}")
    fm_lines.append("---")
    fm_lines.append("")
    
    # Contenido del nodo
    body = f"# {title}\n\n{content}\n"
    
    # Agregar conexiones como links de Obsidian
    if connections:
        body += "\n## Conexiones\n\n"
        for conn in connections:
            body += f"- [[{conn}]]\n"
    
    # Escribir archivo
    filename = f"{node_id}.md"
    filepath = sphere_path / filename
    filepath.write_text("\n".join(fm_lines) + body, "utf-8")
    
    return filepath


def _update_index(sphere: str):
    """Actualiza el _INDEX.md de una esfera."""
    _ensure_dirs()
    
    sphere_path = SPHERES[sphere]
    index_path = sphere_path / "_INDEX.md"
    
    state = _load_state()
    nodes_in_sphere = [
        (nid, info) for nid, info in state["nodes"].items()
        if info["sphere"] == sphere
    ]
    
    content = f"# {sphere.title()} — NeuroSpheres\n\n"
    content += f"Total de nodos: {len(nodes_in_sphere)}\n\n"
    
    for node_id, info in sorted(nodes_in_sphere, key=lambda x: x[1].get("force", 0), reverse=True):
        force_bar = "█" * min(info.get("force", 1), 10)
        content += f"- [[{node_id}|{info.get('title', node_id)}]] {force_bar}\n"
    
    index_path.write_text(content, "utf-8")


# ═══════════════════════════════════════════════════════════════════
# API pública
# ═══════════════════════════════════════════════════════════════════

def get_status() -> dict:
    """Estado actual del cerebro."""
    state = _load_state()
    
    spheres_count = {}
    for sphere_name in SPHERES:
        spheres_count[sphere_name] = len([
            n for n in state["nodes"].values() if n["sphere"] == sphere_name
        ])
    
    return {
        "total_nodes": state["total_nodes"],
        "total_connections": state["total_connections"],
        "spheres": spheres_count,
        "last_add": state.get("last_add"),
        "last_connect": state.get("last_connect"),
    }


def add_node(sphere: str, node_type: str, title: str, content: str, 
             connections: Optional[List[str]] = None, force: int = 1) -> dict:
    """Agrega un nodo nuevo al cerebro. Evita duplicados por titulo."""
    state = _load_state()
    
    # Validar esfera
    if sphere not in SPHERES:
        return {"error": f"Esfera '{sphere}' no válida. Opciones: {list(SPHERES.keys())}"}
    
    # Validar tipo
    if node_type not in NODE_TYPES:
        return {"error": f"Tipo '{node_type}' no válido. Opciones: {list(NODE_TYPES.keys())}"}
    
    # Evitar duplicados: si ya existe un nodo con el mismo titulo, actualizarlo
    title_lower = title.strip().lower()
    for existing_id, existing_node in state["nodes"].items():
        if existing_node.get("title", "").strip().lower() == title_lower:
            # Actualizar nodo existente en vez de crear duplicado
            existing_node["last_used"] = datetime.now().isoformat()
            existing_node["force"] = max(existing_node.get("force", 1), force)
            if content and content != existing_node.get("content", ""):
                existing_node["content"] = content
            # Agregar conexiones nuevas
            if connections:
                for c in connections:
                    if c in state["nodes"] and c not in existing_node.get("connections", []):
                        existing_node.setdefault("connections", []).append(c)
            _save_state(state)
            return {"status": "updated", "node_id": existing_id, "title": title}
    
    # Generar ID único
    timestamp = int(time.time() * 1000)
    node_id = f"{sphere}_{timestamp}"
    
    # Verificar conexiones
    connections = connections or []
    valid_connections = [c for c in connections if c in state["nodes"]]
    
    # Crear nodo en memoria
    state["nodes"][node_id] = {
        "sphere": sphere,
        "type": node_type,
        "title": title,
        "content": content,
        "force": force,
        "connections": valid_connections,
        "created": datetime.now().isoformat(),
        "last_used": datetime.now().isoformat(),
    }
    
    state["total_nodes"] += 1
    state["total_connections"] += len(valid_connections)
    state["last_add"] = datetime.now().isoformat()
    
    # Agregar al historial de crecimiento
    state["growth_history"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "add",
        "node_id": node_id,
        "sphere": sphere,
        "type": node_type,
    })
    
    # Limitar historial a 100 entradas
    if len(state["growth_history"]) > 100:
        state["growth_history"] = state["growth_history"][-100:]
    
    # Guardar estado
    _save_state(state)
    
    # Crear archivo en Obsidian
    filepath = _create_md_node(node_id, sphere, node_type, title, content, valid_connections, force)
    
    # Actualizar índice
    _update_index(sphere)
    
    # Actualizar nodos conectados (agregar referencia inversa)
    for conn_id in valid_connections:
        if conn_id in state["nodes"]:
            if node_id not in state["nodes"][conn_id]["connections"]:
                state["nodes"][conn_id]["connections"].append(node_id)
    _save_state(state)
    
    return {
        "success": True,
        "node_id": node_id,
        "sphere": sphere,
        "type": node_type,
        "title": title,
        "connections": len(valid_connections),
        "file": str(filepath),
    }


def connect_nodes(node_id_a: str, node_id_b: str) -> dict:
    """Conecta dos nodos existentes."""
    state = _load_state()
    
    if node_id_a not in state["nodes"]:
        return {"error": f"Nodo '{node_id_a}' no encontrado"}
    if node_id_b not in state["nodes"]:
        return {"error": f"Nodo '{node_id_b}' no encontrado"}
    
    # Evitar auto-conexión
    if node_id_a == node_id_b:
        return {"error": "No se puede conectar un nodo consigo mismo"}
    
    # Agregar conexiones bidireccionales
    node_a = state["nodes"][node_id_a]
    node_b = state["nodes"][node_id_b]
    
    if node_id_b not in node_a["connections"]:
        node_a["connections"].append(node_id_b)
        state["total_connections"] += 1
    
    if node_id_a not in node_b["connections"]:
        node_b["connections"].append(node_id_a)
        state["total_connections"] += 1
    
    state["last_connect"] = datetime.now().isoformat()
    
    # Actualizar timestamps
    node_a["last_used"] = datetime.now().isoformat()
    node_b["last_used"] = datetime.now().isoformat()
    
    # Historial
    state["growth_history"].append({
        "timestamp": datetime.now().isoformat(),
        "action": "connect",
        "node_a": node_id_a,
        "node_b": node_id_b,
    })
    
    _save_state(state)
    
    # Reconstruir archivos Obsidian con nuevas conexiones
    for nid in [node_id_a, node_id_b]:
        node = state["nodes"][nid]
        _create_md_node(
            nid, node["sphere"], node["type"], node["title"],
            f"Nodo de tipo {node['type']}", node["connections"], node["force"]
        )
    
    return {
        "success": True,
        "connected": [node_id_a, node_id_b],
        "total_connections": state["total_connections"],
    }


def strengthen_node(node_id: str, amount: int = 1) -> dict:
    """Fortalece un nodo (aumenta su fuerza)."""
    state = _load_state()
    
    if node_id not in state["nodes"]:
        return {"error": f"Nodo '{node_id}' no encontrado"}
    
    node = state["nodes"][node_id]
    node["force"] = min(node["force"] + amount, 100)
    node["last_used"] = datetime.now().isoformat()
    
    _save_state(state)
    
    # Actualizar archivo en Obsidian
    _create_md_node(
        node_id, node["sphere"], node["type"], node["title"],
        f"Nodo de tipo {node['type']}", node["connections"], node["force"]
    )
    
    return {
        "success": True,
        "node_id": node_id,
        "new_force": node["force"],
    }


def query_nodes(query: str, sphere: Optional[str] = None, 
                node_type: Optional[str] = None) -> List[dict]:
    """Busca nodos por título o contenido."""
    state = _load_state()
    results = []
    
    query_lower = query.lower()
    
    for node_id, info in state["nodes"].items():
        # Filtro por esfera
        if sphere and info["sphere"] != sphere:
            continue
        
        # Filtro por tipo
        if node_type and info["type"] != node_type:
            continue
        
        # Búsqueda en título
        if query_lower in info.get("title", "").lower():
            results.append({"node_id": node_id, **info})
            continue
        
        # Búsqueda en conexiones
        for conn in info.get("connections", []):
            if query_lower in conn.lower():
                results.append({"node_id": node_id, **info})
                break
    
    # Ordenar por fuerza (más fuertes primero)
    results.sort(key=lambda x: x.get("force", 0), reverse=True)
    
    return results


def get_growth_history(limit: int = 20) -> List[dict]:
    """Obtiene el historial de crecimiento del cerebro."""
    state = _load_state()
    return state["growth_history"][-limit:]


def get_node(node_id: str) -> Optional[dict]:
    """Obtiene información de un nodo específico."""
    state = _load_state()
    if node_id in state["nodes"]:
        return {"node_id": node_id, **state["nodes"][node_id]}
    return None


def get_all_nodes(sphere: Optional[str] = None) -> List[dict]:
    """Obtiene todos los nodos, opcionalmente filtrados por esfera."""
    state = _load_state()
    nodes = []
    
    for node_id, info in state["nodes"].items():
        if sphere and info["sphere"] != sphere:
            continue
        nodes.append({"node_id": node_id, **info})
    
    # Ordenar por fuerza
    nodes.sort(key=lambda x: x.get("force", 0), reverse=True)
    
    return nodes


# ═══════════════════════════════════════════════════════════════════
# Tool handler
# ═══════════════════════════════════════════════════════════════════

def neuro_spheres(parameters: dict, player=None, speak=None) -> str:
    """Tool handler para neuro_spheres."""
    action = parameters.get("action", "status")
    
    if action == "status":
        status = get_status()
        spheres_info = "\n".join([
            f"  - {name}: {count} nodos"
            for name, count in status["spheres"].items()
        ])
        return (
            f"🧠 NeuroSpheres — Estado del Cerebro\n"
            f"Total nodos: {status['total_nodes']}\n"
            f"Total conexiones: {status['total_connections']}\n"
            f"Esferas:\n{spheres_info}\n"
            f"Último nodo: {status.get('last_add', 'Nunca')}\n"
            f"Última conexión: {status.get('last_connect', 'Nunca')}"
        )
    
    elif action == "add":
        sphere = parameters.get("sphere", "aprendizaje")
        node_type = parameters.get("type", "aprendizaje")
        title = parameters.get("title", "Sin título")
        content = parameters.get("content", "")
        connections = parameters.get("connections", [])
        force = parameters.get("force", 1)
        
        result = add_node(sphere, node_type, title, content, connections, force)
        
        if "error" in result:
            return f"❌ Error: {result['error']}"
        
        return (
            f"✅ Nodo creado: {result['node_id']}\n"
            f"Esfera: {result['sphere']}\n"
            f"Tipo: {result['type']}\n"
            f"Título: {result['title']}\n"
            f"Conexiones: {result['connections']}\n"
            f"Archivo: {result['file']}"
        )
    
    elif action == "connect":
        node_a = parameters.get("node_a")
        node_b = parameters.get("node_b")
        
        if not node_a or not node_b:
            return "❌ Se necesitan 'node_a' y 'node_b'"
        
        result = connect_nodes(node_a, node_b)
        
        if "error" in result:
            return f"❌ Error: {result['error']}"
        
        return (
            f"✅ Conexión creada\n"
            f"Nodos: {result['connected']}\n"
            f"Total conexiones: {result['total_connections']}"
        )
    
    elif action == "strengthen":
        node_id = parameters.get("node_id")
        amount = parameters.get("amount", 1)
        
        if not node_id:
            return "❌ Se necesita 'node_id'"
        
        result = strengthen_node(node_id, amount)
        
        if "error" in result:
            return f"❌ Error: {result['error']}"
        
        return f"✅ Nodo {node_id} fortalecido. Nueva fuerza: {result['new_force']}"
    
    elif action == "query":
        query = parameters.get("query", "")
        sphere = parameters.get("sphere")
        node_type = parameters.get("type")
        
        results = query_nodes(query, sphere, node_type)
        
        if not results:
            return f"🔍 No se encontraron nodos para: {query}"
        
        lines = [f"🔍 Resultados para '{query}':"]
        for r in results[:10]:
            lines.append(f"  - [{r['sphere']}] {r.get('title', r['node_id'])} (fuerza: {r.get('force', 0)})")
        
        return "\n".join(lines)
    
    elif action == "history":
        limit = parameters.get("limit", 20)
        history = get_growth_history(limit)
        
        if not history:
            return "📜 Sin historial de crecimiento"
        
        lines = ["📜 Historial de crecimiento:"]
        for h in history:
            action_type = h.get("action", "?")
            if action_type == "add":
                lines.append(f"  + {h.get('node_id', '?')} ({h.get('sphere', '?')})")
            elif action_type == "connect":
                lines.append(f"  ↔ {h.get('node_a', '?')} ↔ {h.get('node_b', '?')}")
            else:
                lines.append(f"  ? {action_type}")
        
        return "\n".join(lines)
    
    elif action == "nodes":
        sphere = parameters.get("sphere")
        nodes = get_all_nodes(sphere)
        
        if not nodes:
            return "📭 Sin nodos"
        
        lines = [f"📋 Nodos ({len(nodes)}):"]
        for n in nodes:
            lines.append(
                f"  - [{n['sphere']}] {n.get('title', n['node_id'])} "
                f"(tipo: {n.get('type', '?')}, fuerza: {n.get('force', 0)}, "
                f"conexiones: {len(n.get('connections', []))})"
            )
        
        return "\n".join(lines)
    
    elif action == "learn":
        result = learn_from_sessions()
        return (
            f"🧠 Auto-aprendizaje completado\n"
            f"Nodos creados: {result['created']}\n"
            f"Saltados (duplicados): {result['skipped']}\n"
            f"Total nodos: {result['total_nodes']}"
        )
    
    else:
        return (
            f"❌ Acción '{action}' no válida\n"
            f"Acciones disponibles: status, add, connect, strengthen, query, history, nodes, learn"
        )


# ═══════════════════════════════════════════════════════════════════
# Auto-aprendizaje desde sesiones reales
# ═══════════════════════════════════════════════════════════════════

_DATA_DIR = _BASE / "data"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return None


def _read_log_lines(path: Path, max_lines: int = 100) -> List[str]:
    try:
        lines = path.read_text("utf-8").strip().splitlines()
        return lines[-max_lines:]
    except Exception:
        return []


def learn_from_sessions() -> dict:
    """Analiza datos de sesiones reales y crea nodos automáticamente."""
    created = 0
    skipped = 0
    state = _load_state()
    existing_titles = {
        n.get("title", "").strip().lower()
        for n in state["nodes"].values()
    }

    # ── 1. Lear from session analytics ──
    analytics = _read_json(_DATA_DIR / "session_analytics.json")
    if analytics and "sessions" in analytics:
        topics_seen = set()
        tools_seen = set()
        for sess in analytics["sessions"][-20:]:
            for t in sess.get("topics", []):
                topics_seen.add(t)
            for tool in sess.get("tools_used", []):
                tools_seen.add(tool)

        for topic in topics_seen:
            title = f"Tema investigado: {topic}"
            if title.lower() not in existing_titles:
                r = add_node("investigacion", "aprendizaje", title,
                             f"El usuario preguntó sobre '{topic}' en una sesión real.",
                             force=3)
                if r.get("success"):
                    created += 1
                else:
                    skipped += 1

        for tool in tools_seen:
            title = f"Tool usada en sesión: {tool}"
            if title.lower() not in existing_titles:
                r = add_node("habilidad", "habilidad", title,
                             f"La tool '{tool}' se usó en una sesión real del usuario.",
                             force=2)
                if r.get("success"):
                    created += 1
                else:
                    skipped += 1

    # ── 2. Learn from search history ──
    searches = _read_json(_DATA_DIR / "search_history.json")
    if isinstance(searches, list):
        query_topics = {}
        for entry in searches[-50:]:
            q = entry.get("query", "").strip()
            if q:
                query_topics[q] = entry.get("time", "")
        for query, time in list(query_topics.items())[-15:]:
            title = f"Búsqueda: {query}"
            if title.lower() not in existing_titles:
                r = add_node("investigacion", "aprendizaje", title,
                             f"El usuario buscó: '{query}'",
                             force=2)
                if r.get("success"):
                    created += 1
                else:
                    skipped += 1

    # ── 3. Learn from idle learning log ──
    idle_lines = _read_log_lines(_DATA_DIR / "idle_learning.log", 50)
    for line in idle_lines:
        line = line.strip()
        if not line or len(line) < 20:
            continue
        # Extract key insight from line
        if ":" in line:
            topic = line.split(":", 1)[0].strip()
        else:
            topic = line[:80]
        title = f"Aprendizaje idle: {topic}"
        if title.lower() not in existing_titles:
            r = add_node("aprendizaje", "aprendizaje", title,
                         line[:500], force=1)
            if r.get("success"):
                created += 1
            else:
                skipped += 1

    # ── 4. Learn from code review history ──
    reviews = _read_json(_DATA_DIR / "code_review_history.json")
    if isinstance(reviews, list):
        for entry in reviews[-10:]:
            filename = entry.get("filename", entry.get("file", ""))
            if filename:
                title = f"Código revisado: {Path(filename).name}"
                if title.lower() not in existing_titles:
                    summary = entry.get("summary", entry.get("issues", "Revisión de código"))
                    if isinstance(summary, list):
                        summary = "; ".join(str(s) for s in summary[:3])
                    r = add_node("codigo", "aprendizaje", title,
                                 str(summary)[:500], force=2)
                    if r.get("success"):
                        created += 1
                    else:
                        skipped += 1

    # ── 5. Learn from deep research ──
    research = _read_json(_DATA_DIR / "deep_research_history.json")
    if isinstance(research, list):
        for entry in research[-10:]:
            topic = entry.get("topic", entry.get("query", ""))
            if topic:
                title = f"Investigación profunda: {topic}"
                if title.lower() not in existing_titles:
                    summary = entry.get("summary", entry.get("result", ""))
                    r = add_node("investigacion", "aprendizaje", title,
                                 str(summary)[:500], force=3)
                    if r.get("success"):
                        created += 1
                    else:
                        skipped += 1

    return {
        "created": created,
        "skipped": skipped,
        "total_nodes": state["total_nodes"] + created,
    }
