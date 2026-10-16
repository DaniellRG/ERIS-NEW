"""3D Brain Graph — Bright nodes on dark background."""
import math
import random
from ursina import *
from data_models import Node, Edge, NODE_TYPES, GraphData


class BrainNode(Entity):
    def __init__(self, node_data: Node, position=(0, 0, 0)):
        r = min(255, int(node_data.color[0] * 300))
        g = min(255, int(node_data.color[1] * 300))
        b = min(255, int(node_data.color[2] * 300))

        super().__init__(
            model="sphere",
            color=color.rgb(r, g, b),
            scale=node_data.base_size * 2.0,
            position=position,
            collider="sphere",
        )
        self.node_data = node_data
        self.base_color = self.color
        self.base_scale = self.scale_x

    def glow(self, intensity=1.0):
        r = min(255, int((self.node_data.color[0] + 0.5 * intensity) * 255))
        g = min(255, int((self.node_data.color[1] + 0.5 * intensity) * 255))
        b = min(255, int((self.node_data.color[2] + 0.5 * intensity) * 255))
        self.color = color.rgb(r, g, b)
        self.scale = self.base_scale * (1.0 + 0.3 * intensity)

    def dim(self):
        self.color = self.base_color
        self.scale = self.base_scale


class BrainEdge:
    def __init__(self, node_a, node_b, strength):
        self.node_a = node_a
        self.node_b = node_b
        self.strength = strength
        self.entity = None
        self._create()

    def _create(self):
        pa = self.node_a.world_position
        pb = self.node_b.world_position
        dist = max((pb - pa).length(), 0.01)
        bright = int(50 + self.strength * 150)
        alpha = int(60 + self.strength * 195)
        self.entity = Entity(
            model="cube",
            color=color.rgb(bright, bright, min(255, int(bright * 1.1)), alpha),
            scale=(dist, 0.015, 0.015),
            position=(pa + pb) / 2,
        )
        self._orient()

    def _orient(self):
        if not self.entity:
            return
        pa = self.node_a.world_position
        pb = self.node_b.world_position
        d = (pb - pa).length()
        if d < 0.01:
            return
        self.entity.position = (pa + pb) / 2
        self.entity.look_at(self.node_b)
        self.entity.scale_x = d

    def update_positions(self):
        self._orient()


class BrainGraph3D:
    def __init__(self, graph_data):
        self.graph_data = graph_data
        self.node_entities = {}
        self.edge_entities = []
        self.selected_node = None
        self.on_node_selected = None
        self._layout()

    def _layout(self):
        random.seed(42)
        nodes = self.graph_data.nodes
        groups = {}
        for n in nodes:
            groups.setdefault(n.node_type, []).append(n)

        angles = {
            "semantic": 0, "episodic": 1.0, "goal": 2.1,
            "emotion": 3.14, "neurosphere": 4.2, "working": 5.2, "autonomy": 0.5,
        }
        radii = {
            "semantic": 2.8, "episodic": 3.2, "goal": 2.2,
            "emotion": 0.8, "neurosphere": 4.5,
            "working": 3.8, "autonomy": 4.2,
        }

        for ntype, gnodes in groups.items():
            ba = angles.get(ntype, 0)
            r = radii.get(ntype, 3)
            for i, n in enumerate(gnodes):
                a = ba + (i / max(len(gnodes), 1)) * 2.2
                x = math.cos(a) * r + random.uniform(-0.2, 0.2)
                y = random.uniform(-1.0, 1.0) + (i % 3) * 0.35
                z = math.sin(a) * r + random.uniform(-0.2, 0.2)
                self.node_entities[n.id] = BrainNode(n, (x, y, z))

        for edge in self.graph_data.edges:
            a = self.node_entities.get(edge.source_id)
            b = self.node_entities.get(edge.target_id)
            if a and b:
                self.edge_entities.append(BrainEdge(a, b, edge.strength))

    def rebuild(self):
        for e in self.edge_entities:
            if e.entity:
                destroy(e.entity)
        self.edge_entities.clear()
        self.node_entities.clear()
        self._layout()

    def apply_force_directed(self, iterations=1, k=0.01):
        pos = {nid: Vec3(e.position.x, e.position.y, e.position.z)
               for nid, e in self.node_entities.items()}

        for _ in range(iterations):
            forces = {nid: Vec3(0, 0, 0) for nid in pos}
            nids = list(pos.keys())
            for i in range(len(nids)):
                for j in range(i + 1, len(nids)):
                    d = pos[nids[i]] - pos[nids[j]]
                    dist = max(d.length(), 0.1)
                    f = d * (k * 2 / (dist * dist))
                    forces[nids[i]] += f
                    forces[nids[j]] -= f

            for edge in self.graph_data.edges:
                if edge.source_id in pos and edge.target_id in pos:
                    d = pos[edge.source_id] - pos[edge.target_id]
                    dist = max(d.length(), 0.1)
                    f = d * (dist * k * 0.5 * edge.strength)
                    forces[edge.source_id] -= f
                    forces[edge.target_id] += f

            for nid in pos:
                f = forces[nid]
                pos[nid] += Vec3(max(-0.1, min(0.1, f.x)),
                                 max(-0.1, min(0.1, f.y)),
                                 max(-0.1, min(0.1, f.z)))

        for nid, p in pos.items():
            if nid in self.node_entities:
                self.node_entities[nid].position = p
        for e in self.edge_entities:
            e.update_positions()

    def select_node(self, node_id):
        if self.selected_node and self.selected_node in self.node_entities:
            self.node_entities[self.selected_node].dim()
        self.selected_node = node_id
        if node_id in self.node_entities:
            self.node_entities[node_id].glow(1.0)
            for cn, st in self.graph_data.get_connections(node_id):
                if cn.id in self.node_entities:
                    self.node_entities[cn.id].glow(0.5)
            if self.on_node_selected:
                self.on_node_selected(self.graph_data.get_node_by_id(node_id))
