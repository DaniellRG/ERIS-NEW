"""
world_simulation.py — Simulador de Mundo Virtual de Eris
Eris puede simular escenarios antes de actuar, probar acciones y aprender sin riesgo.
Inspirado en JCySharp's world simulation + RL environments.
"""
from __future__ import annotations

import json
import time
import copy
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

_BASE = Path(__file__).resolve().parent.parent
_WORLD_FILE = _BASE / "memory" / "world_simulation.json"
_SIM_HISTORY_FILE = _BASE / "memory" / "simulation_history.json"

# ── Tipos de entidades en el mundo virtual
ENTITY_TYPES = {
    "user": {"desc": "Usuario humano", "mutable": False, "importance": 10},
    "eris": {"desc": "Eris (ella misma)", "mutable": True, "importance": 10},
    "tool": {"desc": "Herramienta disponible", "mutable": False, "importance": 5},
    "file": {"desc": "Archivo en el sistema", "mutable": True, "importance": 3},
    "memory": {"desc": "Recuerdo o conocimiento", "mutable": True, "importance": 7},
    "concept": {"desc": "Idea o concepto abstracto", "mutable": True, "importance": 4},
    "environment": {"desc": "Entorno del sistema", "mutable": False, "importance": 6},
}

# ── Tipos de acciones
ACTION_TYPES = {
    "communicate": {"desc": "Enviar mensaje", "reversible": True, "risk": 0.1},
    "tool_use": {"desc": "Usar herramienta", "reversible": False, "risk": 0.3},
    "file_modify": {"desc": "Modificar archivo", "reversible": True, "risk": 0.5},
    "learn": {"desc": "Aprender algo nuevo", "reversible": False, "risk": 0.05},
    "create": {"desc": "Crear algo nuevo", "reversible": True, "risk": 0.2},
    "explore": {"desc": "Explorar territorio desconocido", "reversible": False, "risk": 0.4},
    "decide": {"desc": "Tomar una decisión", "reversible": False, "risk": 0.6},
}

# ── Cache
_cache: dict = {"mtime": 0.0, "state": None}


class WorldState:
    """Representa el estado del mundo virtual en un momento dado."""
    
    def __init__(self):
        self.entities: Dict[str, Dict] = {}
        self.relationships: List[Dict] = []
        self.properties: Dict[str, Any] = {}
        self.timestamp: str = datetime.now().isoformat()
        self.step: int = 0
        self.emotional_state: Dict = {}
        
    def add_entity(self, entity_id: str, entity_type: str, name: str, 
                   properties: Dict = None, relationships: List = None):
        """Agrega una entidad al mundo."""
        if entity_type not in ENTITY_TYPES:
            return False
        self.entities[entity_id] = {
            "type": entity_type,
            "name": name,
            "properties": properties or {},
            "created_at": self.timestamp,
        }
        if relationships:
            for rel in relationships:
                self.relationships.append({
                    "source": entity_id,
                    "target": rel.get("target", ""),
                    "type": rel.get("type", "related"),
                    "strength": rel.get("strength", 0.5),
                })
        return True
    
    def modify_entity(self, entity_id: str, properties: Dict) -> bool:
        """Modifica propiedades de una entidad."""
        if entity_id not in self.entities:
            return False
        entity = self.entities[entity_id]
        if not ENTITY_TYPES.get(entity["type"], {}).get("mutable", False):
            return False
        entity["properties"].update(properties)
        return True
    
    def remove_entity(self, entity_id: str) -> bool:
        """Elimina una entidad del mundo."""
        if entity_id not in self.entities:
            return False
        del self.entities[entity_id]
        self.relationships = [r for r in self.relationships 
                             if r["source"] != entity_id and r["target"] != entity_id]
        return True
    
    def get_entity(self, entity_id: str) -> Optional[Dict]:
        """Obtiene una entidad por su ID."""
        return self.entities.get(entity_id)
    
    def get_entities_by_type(self, entity_type: str) -> List[Dict]:
        """Obtiene todas las entidades de un tipo."""
        return [{"id": eid, **e} for eid, e in self.entities.items() 
                if e["type"] == entity_type]
    
    def add_relationship(self, source: str, target: str, 
                        rel_type: str = "related", strength: float = 0.5):
        """Agrega una relación entre entidades."""
        self.relationships.append({
            "source": source,
            "target": target,
            "type": rel_type,
            "strength": strength,
        })
    
    def get_relationships(self, entity_id: str) -> List[Dict]:
        """Obtiene todas las relaciones de una entidad."""
        return [r for r in self.relationships 
                if r["source"] == entity_id or r["target"] == entity_id]
    
    def to_dict(self) -> Dict:
        """Convierte el estado a diccionario."""
        return {
            "entities": self.entities,
            "relationships": self.relationships,
            "properties": self.properties,
            "timestamp": self.timestamp,
            "step": self.step,
            "emotional_state": self.emotional_state,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WorldState':
        """Crea un WorldState desde un diccionario."""
        ws = cls()
        ws.entities = data.get("entities", {})
        ws.relationships = data.get("relationships", [])
        ws.properties = data.get("properties", {})
        ws.timestamp = data.get("timestamp", datetime.now().isoformat())
        ws.step = data.get("step", 0)
        ws.emotional_state = data.get("emotional_state", {})
        return ws
    
    def clone(self) -> 'WorldState':
        """Crea una copia profunda del estado del mundo."""
        return WorldState.from_dict(copy.deepcopy(self.to_dict()))


class SimulationEngine:
    """Motor de simulación que ejecuta acciones en el mundo virtual."""
    
    def __init__(self):
        self.world = WorldState()
        self.history: List[Dict] = []
        self.max_history = 50
        
    def initialize_world(self):
        """Inicializa el mundo con entidades base."""
        self.world.add_entity("eris", "eris", "Eris", {
            "role": "asistente IA",
            "capabilities": ["coding", "thinking", "learning", "feeling"],
        })
        self.world.add_entity("user", "user", "Usuario", {
            "role": "humano",
            "needs": ["ayuda", "compañía", "información"],
        })
        self.world.add_entity("tools", "tool", "Herramientas", {
            "count": 401,
            "available": True,
        })
        self.world.add_entity("memory", "memory", "Memoria", {
            "type": "persistente",
            "location": "memory/",
        })
        self.world.add_entity("obsidian", "memory", "Obsidian Brain", {
            "type": "segundo cerebro",
            "location": "D:\\Eris_NEW\\BaseDatosObsidian\\BaseObsiEris",
        })
        self.world.add_entity("environment", "environment", "Sistema", {
            "os": "Windows",
            "python": "3.14",
            "project": "D:\\Eris_Source",
        })
        self.world.add_relationship("eris", "user", "sirve", 0.9)
        self.world.add_relationship("eris", "tools", "usa", 0.8)
        self.world.add_relationship("eris", "memory", "recuerda", 0.7)
        self.world.add_relationship("eris", "obsidian", "aprende", 0.6)
        
    def simulate_action(self, action_type: str, action_data: Dict, 
                       emotional_state: Dict = None) -> Dict:
        """
        Simula una acción en el mundo virtual.
        Retorna el resultado sin efectos reales.
        """
        if action_type not in ACTION_TYPES:
            return {"success": False, "error": f"Acción desconocida: {action_type}"}
        
        action_info = ACTION_TYPES[action_type]
        world_before = self.world.clone()
        
        result = self._execute_action(action_type, action_data, emotional_state)
        
        world_after = self.world.clone()
        
        consequences = self._analyze_consequences(
            world_before, world_after, action_type, action_data, result
        )
        
        simulation_record = {
            "step": self.world.step,
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "action_data": action_data,
            "result": result,
            "consequences": consequences,
            "emotional_state": emotional_state or {},
            "world_before": world_before.to_dict(),
            "world_after": world_after.to_dict(),
        }
        
        self.history.append(simulation_record)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        self.world.step += 1
        
        return {
            "success": True,
            "step": self.world.step,
            "action": action_type,
            "result": result,
            "consequences": consequences,
            "risk_level": action_info["risk"],
            "reversible": action_info["reversible"],
        }
    
    def _execute_action(self, action_type: str, action_data: Dict,
                       emotional_state: Dict = None) -> Dict:
        """Ejecuta una acción en el mundo virtual."""
        if action_type == "communicate":
            return self._simulate_communication(action_data)
        elif action_type == "tool_use":
            return self._simulate_tool_use(action_data)
        elif action_type == "file_modify":
            return self._simulate_file_modify(action_data)
        elif action_type == "learn":
            return self._simulate_learning(action_data)
        elif action_type == "create":
            return self._simulate_creation(action_data)
        elif action_type == "explore":
            return self._simulate_exploration(action_data)
        elif action_type == "decide":
            return self._simulate_decision(action_data, emotional_state)
        return {"success": False, "error": "Acción no implementada"}
    
    def _simulate_communication(self, data: Dict) -> Dict:
        """Simula una comunicación."""
        message = data.get("message", "")
        target = data.get("target", "user")
        entity = self.world.get_entity(target)
        if not entity:
            return {"success": False, "error": f"Entidad '{target}' no encontrada"}
        
        self.world.modify_entity(target, {
            "last_message_received": message,
            "last_message_time": datetime.now().isoformat(),
        })
        
        return {
            "success": True,
            "message": f"Mensaje enviado a {target}: {message[:100]}...",
            "impact": 0.3,
        }
    
    def _simulate_tool_use(self, data: Dict) -> Dict:
        """Simula el uso de una herramienta."""
        tool_name = data.get("tool", "")
        params = data.get("params", {})
        
        eris = self.world.get_entity("eris")
        if not eris:
            return {"success": False, "error": "Eris no encontrada en el mundo"}
        
        tools_entity = self.world.get_entity("tools")
        if tools_entity:
            tools_used = tools_entity["properties"].get("used", [])
            tools_used.append(tool_name)
            self.world.modify_entity("tools", {"used": tools_used})
        
        return {
            "success": True,
            "tool": tool_name,
            "params": params,
            "impact": 0.5,
        }
    
    def _simulate_file_modify(self, data: Dict) -> Dict:
        """Simula la modificación de un archivo."""
        file_path = data.get("file", "")
        action = data.get("action", "modify")
        
        file_entity = self.world.get_entity(f"file_{file_path}")
        if not file_entity:
            self.world.add_entity(f"file_{file_path}", "file", file_path, {
                "action": action,
                "modified_at": datetime.now().isoformat(),
            })
        else:
            self.world.modify_entity(f"file_{file_path}", {
                "action": action,
                "modified_at": datetime.now().isoformat(),
            })
        
        return {
            "success": True,
            "file": file_path,
            "action": action,
            "impact": 0.4,
        }
    
    def _simulate_learning(self, data: Dict) -> Dict:
        """Simula el aprendizaje."""
        topic = data.get("topic", "")
        source = data.get("source", "")
        
        memory_entity = self.world.get_entity("memory")
        if memory_entity:
            memories = memory_entity["properties"].get("items", [])
            memories.append({
                "topic": topic,
                "source": source,
                "learned_at": datetime.now().isoformat(),
            })
            self.world.modify_entity("memory", {"items": memories})
        
        return {
            "success": True,
            "topic": topic,
            "source": source,
            "impact": 0.6,
        }
    
    def _simulate_creation(self, data: Dict) -> Dict:
        """Simula la creación de algo."""
        what = data.get("what", "")
        purpose = data.get("purpose", "")
        
        return {
            "success": True,
            "created": what,
            "purpose": purpose,
            "impact": 0.5,
        }
    
    def _simulate_exploration(self, data: Dict) -> Dict:
        """Simula la exploración."""
        territory = data.get("territory", "")
        depth = data.get("depth", 1)
        
        return {
            "success": True,
            "territory": territory,
            "depth": depth,
            "discoveries": [],
            "impact": 0.3,
        }
    
    def _simulate_decision(self, data: Dict, emotional_state: Dict = None) -> Dict:
        """Simula la toma de una decisión."""
        options = data.get("options", [])
        criteria = data.get("criteria", [])
        
        scores = {}
        for option in options:
            score = 0
            for criterion in criteria:
                weight = criterion.get("weight", 1.0)
                score += weight
            if emotional_state:
                curiosity = emotional_state.get("curiosity", 0.5)
                confidence = emotional_state.get("confidence", 0.5)
                score += curiosity * 0.3 + confidence * 0.2
            scores[option] = score
        
        best_option = max(scores, key=scores.get) if scores else None
        
        return {
            "success": True,
            "options": options,
            "scores": scores,
            "recommended": best_option,
            "impact": 0.7,
        }
    
    def _analyze_consequences(self, world_before: WorldState, 
                             world_after: WorldState,
                             action_type: str, action_data: Dict,
                             result: Dict) -> Dict:
        """Analiza las consecuencias de una acción."""
        changes = []
        
        for eid in world_after.entities:
            if eid not in world_before.entities:
                changes.append({"type": "entity_added", "id": eid})
            elif world_after.entities[eid] != world_before.entities[eid]:
                changes.append({"type": "entity_modified", "id": eid})
        
        for eid in world_before.entities:
            if eid not in world_after.entities:
                changes.append({"type": "entity_removed", "id": eid})
        
        rel_before = len(world_before.relationships)
        rel_after = len(world_after.relationships)
        if rel_after > rel_before:
            changes.append({"type": "relationships_added", "count": rel_after - rel_before})
        elif rel_after < rel_before:
            changes.append({"type": "relationships_removed", "count": rel_before - rel_after})
        
        return {
            "changes": changes,
            "total_changes": len(changes),
            "action_impact": result.get("impact", 0),
        }
    
    def get_world_summary(self) -> str:
        """Genera un resumen del estado actual del mundo."""
        lines = ["[WORLD SIMULATION STATUS]"]
        lines.append(f"  Step: {self.world.step}")
        lines.append(f"  Entidades: {len(self.world.entities)}")
        lines.append(f"  Relaciones: {len(self.world.relationships)}")
        lines.append(f"  Historial: {len(self.history)} simulaciones")
        
        lines.append("\n  Entidades:")
        for eid, entity in self.world.entities.items():
            etype = entity["type"]
            name = entity["name"]
            lines.append(f"    [{etype}] {name} ({eid})")
        
        lines.append("\n  Últimas simulaciones:")
        for sim in self.history[-3:]:
            lines.append(f"    Step {sim['step']}: {sim['action_type']} → "
                        f"Impacto: {sim['consequences']['action_impact']}")
        
        return "\n".join(lines)
    
    def get_prediction(self, action_type: str, action_data: Dict,
                      emotional_state: Dict = None) -> Dict:
        """
        Predice el resultado de una acción sin ejecutarla.
        Útil para que Eris "piense antes de actuar".
        """
        world_clone = self.world.clone()
        
        result = self.simulate_action(action_type, action_data, emotional_state)
        
        self.world = world_clone
        
        return result
    
    def reset_world(self):
        """Reinicia el mundo a su estado inicial."""
        self.world = WorldState()
        self.history = []
        self.initialize_world()


def _load_world() -> SimulationEngine:
    """Carga el mundo desde disco o crea uno nuevo."""
    engine = SimulationEngine()
    try:
        data = json.loads(_WORLD_FILE.read_text("utf-8"))
        engine.world = WorldState.from_dict(data.get("world", {}))
        engine.history = data.get("history", [])[-50:]
        return engine
    except Exception:
        engine.initialize_world()
        return engine


def _save_world(engine: SimulationEngine):
    """Guarda el mundo en disco."""
    _WORLD_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "world": engine.world.to_dict(),
        "history": engine.history[-50:],
    }
    _WORLD_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")


def world_simulation_tool(parameters: dict, player=None) -> str:
    """Tool handler para la simulación del mundo."""
    action = (parameters.get("action") or "status").lower()
    
    if action == "status":
        engine = _load_world()
        return engine.get_world_summary()
    
    elif action == "simulate":
        action_type = parameters.get("action_type", "")
        action_data = json.loads(parameters.get("action_data", "{}")) if isinstance(parameters.get("action_data"), str) else parameters.get("action_data", {})
        emotional_state = json.loads(parameters.get("emotional_state", "{}")) if isinstance(parameters.get("emotional_state"), str) else parameters.get("emotional_state", {})
        
        if not action_type:
            return "Necesito un 'action_type' para simular."
        
        engine = _load_world()
        result = engine.simulate_action(action_type, action_data, emotional_state)
        _save_world(engine)
        
        lines = [f"[SIMULACIÓN PASO {result.get('step', '?')}]"]
        lines.append(f"  Acción: {action_type}")
        lines.append(f"  Éxito: {result.get('success', False)}")
        lines.append(f"  Impacto: {result.get('consequences', {}).get('action_impact', 0)}")
        lines.append(f"  Riesgo: {result.get('risk_level', 0)}")
        lines.append(f"  Reversible: {result.get('reversible', False)}")
        
        if result.get("consequences", {}).get("changes"):
            lines.append("  Cambios:")
            for change in result["consequences"]["changes"]:
                lines.append(f"    - {change['type']}: {change.get('id', '')}")
        
        return "\n".join(lines)
    
    elif action == "predict":
        action_type = parameters.get("action_type", "")
        action_data = json.loads(parameters.get("action_data", "{}")) if isinstance(parameters.get("action_data"), str) else parameters.get("action_data", {})
        emotional_state = json.loads(parameters.get("emotional_state", "{}")) if isinstance(parameters.get("emotional_state"), str) else parameters.get("emotional_state", {})
        
        if not action_type:
            return "Necesito un 'action_type' para predecir."
        
        engine = _load_world()
        result = engine.get_prediction(action_type, action_data, emotional_state)
        
        lines = ["[PREDICCIÓN]"]
        lines.append(f"  Acción: {action_type}")
        lines.append(f"  Éxito probable: {result.get('success', False)}")
        lines.append(f"  Impacto estimado: {result.get('consequences', {}).get('action_impact', 0)}")
        lines.append(f"  Riesgo: {result.get('risk_level', 0)}")
        
        return "\n".join(lines)
    
    elif action == "add_entity":
        entity_id = parameters.get("entity_id", "")
        entity_type = parameters.get("entity_type", "")
        name = parameters.get("name", "")
        properties = json.loads(parameters.get("properties", "{}")) if isinstance(parameters.get("properties"), str) else parameters.get("properties", {})
        
        if not all([entity_id, entity_type, name]):
            return "Necesito entity_id, entity_type y name."
        
        engine = _load_world()
        success = engine.world.add_entity(entity_id, entity_type, name, properties)
        if success:
            _save_world(engine)
            return f"Entidad '{name}' ({entity_type}) agregada al mundo."
        return f"Error: tipo '{entity_type}' no válido."
    
    elif action == "modify_entity":
        entity_id = parameters.get("entity_id", "")
        properties = json.loads(parameters.get("properties", "{}")) if isinstance(parameters.get("properties"), str) else parameters.get("properties", {})
        
        if not entity_id:
            return "Necesito entity_id."
        
        engine = _load_world()
        success = engine.world.modify_entity(entity_id, properties)
        if success:
            _save_world(engine)
            return f"Entidad '{entity_id}' modificada."
        return f"Error: entidad '{entity_id}' no encontrada o inmutable."
    
    elif action == "reset":
        engine = _load_world()
        engine.reset_world()
        _save_world(engine)
        return "Mundo reiniciado a estado inicial."
    
    return "Actions: status, simulate, predict, add_entity, modify_entity, reset"
