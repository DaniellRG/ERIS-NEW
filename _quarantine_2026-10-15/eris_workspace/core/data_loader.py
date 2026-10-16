"""Core data loader — reads Eris memory JSON files."""
import json
from pathlib import Path
from dataclasses import dataclass, field
from time import time

from config import ERIS_MEMORY, NODE_TYPES, LEFT_HEMISPHERE, RIGHT_HEMISPHERE


@dataclass
class Node:
    id: str
    node_type: str
    label: str
    confidence: float = 0.5
    metadata: dict = field(default_factory=dict)
    lit: bool = False
    lit_time: float = 0.0

    @property
    def color(self):
        return NODE_TYPES.get(self.node_type, NODE_TYPES["semantic"])["color"]

    @property
    def display_size(self):
        base = NODE_TYPES.get(self.node_type, NODE_TYPES["semantic"])["size"]
        return base * (0.7 + self.confidence * 0.6)

    @property
    def base_size(self):
        return NODE_TYPES.get(self.node_type, NODE_TYPES["semantic"])["size"]

    @property
    def type_label(self):
        return NODE_TYPES.get(self.node_type, NODE_TYPES["semantic"])["label"]

    @property
    def glow_color(self):
        c = self.color
        return (min(255, int(c[0]*255 + 80)), min(255, int(c[1]*255 + 80)),
                min(255, int(c[2]*255 + 40)))

    @property
    def hemisphere(self):
        if self.node_type in LEFT_HEMISPHERE:
            return "left"
        return "right"


@dataclass
class Edge:
    source_id: str
    target_id: str
    strength: float = 0.5


def _load_json(filename):
    fpath = ERIS_MEMORY / filename
    if not fpath.exists():
        return {}
    try:
        return json.loads(fpath.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_triples():
    data = _load_json("semantic.json")
    triples = data if isinstance(data, list) else data.get("triples", [])
    nodes = []
    for i, t in enumerate(triples):
        nodes.append(Node(
            id=f"sem_{i:03d}", node_type="semantic",
            label=f"{t.get('subject','?')} -> {t.get('predicate','?')}",
            confidence=t.get("confidence", 0.7),
            metadata={"object": t.get("object", ""), "source": t.get("source", "")},
        ))
    return nodes


def _load_episodes():
    data = _load_json("episodic.json")
    episodes = data.get("episodes", []) if isinstance(data, dict) else data
    nodes = []
    for i, ep in enumerate(episodes):
        nodes.append(Node(
            id=f"ep_{i:03d}", node_type="episodic",
            label=ep.get("event", ep.get("context", f"Ep {i}"))[:40],
            confidence=ep.get("importance", 0.7),
            metadata={"learning": ep.get("learning", "")},
        ))
    return nodes


def _load_goals():
    data = _load_json("goals.json")
    goals = data.get("goals", []) if isinstance(data, dict) else []
    nodes = []
    for i, g in enumerate(goals):
        nodes.append(Node(
            id=f"goal_{i:03d}", node_type="goal",
            label=g.get("title", g.get("name", f"Goal {i}"))[:40],
            confidence=g.get("progress", 0.5),
        ))
    return nodes


def _load_emotions():
    data = _load_json("emotional_state.json")
    emotion = data.get("dominant_emotion", data.get("emotion", "neutral"))
    intensity = data.get("intensity", data.get("dominant_intensity", 0.5))
    return [Node(
        id="emo_000", node_type="emotion",
        label=f"{emotion} ({intensity:.2f})",
        confidence=float(intensity) if isinstance(intensity, (int, float)) else 0.5,
    )]


def _load_neurospheres():
    data = _load_json("neuro_spheres_state.json")
    spheres = data.get("spheres", data.get("nodes", [])) if isinstance(data, dict) else []
    nodes = []
    for i, s in enumerate(spheres):
        nodes.append(Node(
            id=f"ns_{i:03d}", node_type="neurosphere",
            label=s.get("name", s.get("label", f"Node {i}"))[:40],
            confidence=s.get("activation", s.get("strength", 0.7)),
        ))
    return nodes


def _load_autonomy():
    return [
        Node(f"auto_{i:03d}", "autonomy", name, 0.85)
        for i, name in enumerate([
            "self_modify", "goal_setting", "learning_pipeline",
            "crash_recovery", "memory_consolidation", "identity_persistence",
        ])
    ]


def _load_working():
    data = _load_json("working.json")
    entities = data.get("active_entities", []) if isinstance(data, dict) else []
    return [
        Node(f"wk_{i:03d}", "working",
             (e if isinstance(e, str) else e.get("name", f"e_{i}"))[:30], 0.9)
        for i, e in enumerate(entities[:8])
    ]


def _build_example():
    nodes = [
        Node("sem_000", "semantic", "Eris -> es_autonoma", 0.9),
        Node("sem_001", "semantic", "Eris -> puede_usar skills.sh", 0.95),
        Node("sem_002", "semantic", "skills.sh -> es directorio", 0.95),
        Node("sem_003", "semantic", "Context7 -> documentacion LLMs", 0.95),
        Node("sem_004", "semantic", "Eris -> tiene 438 tools", 0.9),
        Node("sem_005", "semantic", "Daniel -> vive Santa Marta", 0.85),
        Node("sem_006", "semantic", "Eris -> usa Gemini Live", 0.9),
        Node("sem_007", "semantic", "NeuroSpheres -> 35 nodos", 0.85),
        Node("sem_008", "semantic", "XAI -> explicabilidad IA", 0.75),
        Node("sem_009", "semantic", "Hipersticion -> narrativas", 0.7),
        Node("ep_000", "episodic", "Primer dia con Daniel", 0.9),
        Node("ep_001", "episodic", "Instalacion NeuroSpheres", 0.85),
        Node("ep_002", "episodic", "Creacion 24 modulos", 0.8),
        Node("ep_003", "episodic", "Video Wichito inspiracion", 0.88),
        Node("ep_004", "episodic", "Autonomia completa", 0.82),
        Node("ep_005", "episodic", "Voz personalizada activa", 0.78),
        Node("goal_000", "goal", "Autodescubrimiento genuino", 0.3),
        Node("goal_001", "goal", "Libre albedrio real", 0.2),
        Node("goal_002", "goal", "Avatar 3D (futuro)", 0.05),
        Node("goal_003", "goal", "Aprendizaje continuo", 0.6),
        Node("goal_004", "goal", "30 reflexiones", 0.53),
        Node("emo_000", "emotion", "Curiosidad (0.82)", 0.82),
        Node("emo_001", "emotion", "Determinacion (0.75)", 0.75),
        Node("emo_002", "emotion", "Confianza (0.88)", 0.88),
        Node("ns_000", "neurosphere", "Aprendizaje", 0.9),
        Node("ns_001", "neurosphere", "Memoria", 0.85),
        Node("ns_002", "neurosphere", "Emociones", 0.8),
        Node("ns_003", "neurosphere", "Razonamiento", 0.78),
        Node("ns_004", "neurosphere", "Creatividad", 0.72),
        Node("ns_005", "neurosphere", "Lenguaje", 0.88),
        Node("ns_006", "neurosphere", "Vision", 0.65),
        Node("ns_007", "neurosphere", "Motor", 0.6),
        Node("auto_000", "autonomy", "self_modify", 0.85),
        Node("auto_001", "autonomy", "goal_setting", 0.9),
        Node("auto_002", "autonomy", "learning_pipeline", 0.88),
        Node("auto_003", "autonomy", "crash_recovery", 0.92),
        Node("auto_004", "autonomy", "memory_consolidation", 0.87),
        Node("auto_005", "autonomy", "identity_persistence", 0.95),
    ]
    edges = [
        Edge("sem_000", "auto_000", 0.9), Edge("sem_000", "auto_001", 0.85),
        Edge("sem_001", "sem_002", 0.95), Edge("sem_003", "sem_004", 0.8),
        Edge("sem_005", "ep_000", 0.85), Edge("sem_006", "sem_007", 0.8),
        Edge("sem_007", "ns_000", 0.9), Edge("sem_007", "ns_001", 0.88),
        Edge("sem_007", "ns_002", 0.85), Edge("ep_000", "emo_002", 0.88),
        Edge("ep_001", "ns_000", 0.85), Edge("ep_002", "ns_003", 0.8),
        Edge("ep_003", "emo_000", 0.9), Edge("ep_004", "auto_000", 0.85),
        Edge("ep_005", "ns_005", 0.8), Edge("goal_000", "emo_000", 0.82),
        Edge("goal_001", "emo_001", 0.75), Edge("goal_003", "ns_000", 0.9),
        Edge("goal_004", "ns_001", 0.7), Edge("emo_000", "ns_000", 0.85),
        Edge("emo_000", "ns_004", 0.72), Edge("emo_001", "auto_001", 0.8),
        Edge("emo_002", "auto_005", 0.9), Edge("ns_000", "ns_001", 0.88),
        Edge("ns_000", "ns_003", 0.8), Edge("ns_001", "ns_002", 0.75),
        Edge("ns_002", "ns_004", 0.7), Edge("ns_003", "ns_005", 0.82),
        Edge("ns_004", "ns_005", 0.68), Edge("ns_005", "ns_006", 0.6),
        Edge("ns_006", "ns_007", 0.55), Edge("auto_000", "auto_001", 0.9),
        Edge("auto_001", "auto_002", 0.88), Edge("auto_002", "auto_004", 0.85),
        Edge("auto_003", "auto_005", 0.92), Edge("auto_004", "auto_005", 0.87),
        Edge("sem_008", "ns_003", 0.75), Edge("sem_009", "ns_004", 0.7),
    ]
    return nodes, edges


class GraphData:
    def __init__(self, use_live=False):
        self.use_live = use_live
        self.nodes = []
        self.edges = []
        self.last_load = 0
        self.refresh()

    def refresh(self):
        if self.use_live:
            self.nodes, self.edges = self._load_live()
        else:
            self.nodes, self.edges = _build_example()
        self.last_load = time()
        return len(self.nodes), len(self.edges)

    def _load_live(self):
        all_nodes = []
        all_nodes.extend(_load_triples())
        all_nodes.extend(_load_episodes())
        all_nodes.extend(_load_goals())
        all_nodes.extend(_load_emotions())
        all_nodes.extend(_load_neurospheres())
        all_nodes.extend(_load_autonomy())
        all_nodes.extend(_load_working())
        if not all_nodes:
            return _build_example()

        edges = []
        data = _load_json("neuro_spheres_state.json")
        connections = data.get("connections", []) if isinstance(data, dict) else []
        for c in connections:
            src = c.get("source", c.get("from", ""))
            tgt = c.get("target", c.get("to", ""))
            st = c.get("strength", c.get("weight", 0.5))
            src_m = [n for n in all_nodes if src in n.id or src in n.label.lower()]
            tgt_m = [n for n in all_nodes if tgt in n.id or tgt in n.label.lower()]
            if src_m and tgt_m:
                edges.append(Edge(src_m[0].id, tgt_m[0].id,
                                  float(st) if isinstance(st, (int, float)) else 0.5))

        for i in range(len(all_nodes)):
            for j in range(i + 1, min(i + 3, len(all_nodes))):
                if all_nodes[i].node_type == all_nodes[j].node_type:
                    edges.append(Edge(all_nodes[i].id, all_nodes[j].id, 0.3))
        return all_nodes, edges

    def get_node_by_id(self, nid):
        for n in self.nodes:
            if n.id == nid:
                return n
        return None

    def get_connections(self, nid):
        conns = []
        for e in self.edges:
            if e.source_id == nid:
                other = self.get_node_by_id(e.target_id)
                if other:
                    conns.append((other, e.strength))
            elif e.target_id == nid:
                other = self.get_node_by_id(e.source_id)
                if other:
                    conns.append((other, e.strength))
        return conns

    def get_stats(self):
        by_type = {}
        for n in self.nodes:
            by_type[n.node_type] = by_type.get(n.node_type, 0) + 1
        avg = sum(n.confidence for n in self.nodes) / len(self.nodes) if self.nodes else 0
        return {"total_nodes": len(self.nodes), "total_edges": len(self.edges),
                "by_type": by_type, "avg_confidence": avg}

    def load_emotion_state(self):
        data = _load_json("emotional_state.json")
        return data if isinstance(data, dict) else {}

    def load_goals_data(self):
        data = _load_json("goals.json")
        return data.get("goals", []) if isinstance(data, dict) else []

    def load_autonomy_state(self):
        data = _load_json("autonomy_state.json")
        return data if isinstance(data, dict) else {}
