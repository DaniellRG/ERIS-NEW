"""UI Panels for Eris Workspace — sidebar, detail panel, top bar."""
from ursina import *
from data_models import NODE_TYPES, GraphData


class TopBar(Entity):
    def __init__(self, graph_data: GraphData, **kwargs):
        super().__init__(
            parent=camera.ui,
            model="quad",
            color=color.rgb(15, 15, 25, 220),
            scale=(2.2, 0.06),
            position=(0, 0.46),
            **kwargs,
        )
        self.graph_data = graph_data
        self.title = Text(
            text="Eris Workspace 3D",
            origin=(0, 0), scale=16, color=color.rgb(100, 200, 255),
            position=(-0.7, 0),
        )
        self.stats_text = Text(
            text="", origin=(0, 0), scale=12, color=color.rgb(180, 180, 200),
            position=(0.15, 0),
        )
        self.refresh_text = Text(
            text="[R] Refresh  [T] Panels  [F] Focus  [ESC] Salir",
            origin=(0, 0), scale=9, color=color.rgb(120, 120, 140),
            position=(0.5, 0),
        )

    def update_stats(self):
        stats = self.graph_data.get_stats()
        by_type = stats["by_type"]
        parts = []
        for ntype, info in NODE_TYPES.items():
            count = by_type.get(ntype, 0)
            if count > 0:
                parts.append(f"{info['label']}: {count}")
        self.stats_text.text = (
            f"Nodos: {stats['total_nodes']}  |  "
            f"Conexiones: {stats['total_edges']}  |  "
            f"Confianza: {stats['avg_confidence']:.0%}  |  "
            + "  ".join(parts)
        )


class SidebarPanel(Entity):
    def __init__(self, graph_data: GraphData, **kwargs):
        super().__init__(
            parent=camera.ui,
            model="quad",
            color=color.rgb(12, 12, 20, 200),
            scale=(0.42, 0.92),
            position=(-0.79, 0),
            **kwargs,
        )
        self.graph_data = graph_data
        self.visible = True
        self.filter_type = None

        self.title = Text(
            text="Memorias de Eris",
            origin=(-0.5, 0.5), scale=14, color=color.rgb(100, 200, 255),
            position=(-0.19, 0.42),
        )

        self.filter_buttons = []
        y_pos = 0.36
        all_btn = Button(
            text="Todos", color=color.rgb(40, 40, 60), highlight_color=color.rgb(60, 60, 90),
            position=(-0.05, y_pos), scale=(0.15, 0.03),
        )
        all_btn.on_click = lambda: self.set_filter(None)
        self.filter_buttons.append(("all", all_btn))

        for i, (ntype, info) in enumerate(NODE_TYPES.items()):
            y_pos -= 0.04
            btn = Button(
                text=info["label"][:8], color=color.rgb(
                    int(info["color"][0] * 80), int(info["color"][1] * 80), int(info["color"][2] * 80)
                ),
                highlight_color=color.rgb(
                    int(info["color"][0] * 120), int(info["color"][1] * 120), int(info["color"][2] * 120)
                ),
                position=(-0.05 + (i % 2) * 0.2, y_pos),
                scale=(0.15, 0.03),
            )
            btn.node_type = ntype
            btn.on_click = lambda t=ntype: self.set_filter(t)
            self.filter_buttons.append((ntype, btn))

        self.node_list_text = Text(
            text="", origin=(-0.5, 0.5), scale=9, color=color.rgb(170, 170, 190),
            position=(-0.19, 0.18),
        )
        self._update_list()

    def set_filter(self, ntype):
        self.filter_type = ntype
        self._update_list()

    def _update_list(self):
        nodes = self.graph_data.nodes
        if self.filter_type:
            nodes = [n for n in nodes if n.node_type == self.filter_type]

        lines = []
        for n in nodes[:20]:
            c = NODE_TYPES.get(n.node_type, NODE_TYPES["semantic"])["color"]
            conf_bar = "#" * int(n.confidence * 8) + "." * (8 - int(n.confidence * 8))
            lines.append(f"[{n.node_type[:3].upper()}] {n.label[:28]}")
            lines.append(f"  {conf_bar} {n.confidence:.0%}")

        self.node_list_text.text = "\n".join(lines) if lines else "No hay nodos"

    def toggle(self):
        self.visible = not self.visible
        self.title.visible = self.visible
        self.node_list_text.visible = self.visible
        for _, btn in self.filter_buttons:
            btn.visible = self.visible


class DetailPanel(Entity):
    def __init__(self, graph_data: GraphData, **kwargs):
        super().__init__(
            parent=camera.ui,
            model="quad",
            color=color.rgb(12, 12, 20, 200),
            scale=(0.42, 0.92),
            position=(0.79, 0),
            **kwargs,
        )
        self.graph_data = graph_data
        self.visible = True

        self.title = Text(
            text="Detalle del Nodo",
            origin=(-0.5, 0.5), scale=14, color=color.rgb(100, 200, 255),
            position=(-0.19, 0.42),
        )

        self.detail_text = Text(
            text="Click en un nodo\npara ver detalles",
            origin=(-0.5, 0.5), scale=10, color=color.rgb(170, 170, 190),
            position=(-0.19, 0.34),
        )

        self.connections_text = Text(
            text="", origin=(-0.5, 0.5), scale=9, color=color.rgb(170, 170, 190),
            position=(-0.19, 0.0),
        )

    def show_node(self, node):
        if not node:
            self.detail_text.text = "Click en un nodo\npara ver detalles"
            self.connections_text.text = ""
            return

        c = node.color
        type_info = NODE_TYPES.get(node.node_type, {})
        lines = [
            f"Tipo: {type_info.get('label', '?')}",
            f"",
            f"ID: {node.id}",
            f"Label: {node.label}",
            f"Confianza: {node.confidence:.0%}",
            f"",
            f"Barra:",
            "#" * int(node.confidence * 20),
        ]

        for k, v in node.metadata.items():
            val = str(v)[:50] if v else "-"
            lines.append(f"{k}: {val}")

        self.detail_text.text = "\n".join(lines)

        connections = self.graph_data.get_connections(node.id)
        if connections:
            conn_lines = [f"Conexiones ({len(connections)}):"]
            for cn, strength in sorted(connections, key=lambda x: -x[1])[:10]:
                bar = "#" * int(strength * 6)
                conn_lines.append(f"  {cn.label[:25]} [{bar}] {strength:.0%}")
            self.connections_text.text = "\n".join(conn_lines)
        else:
            self.connections_text.text = "Sin conexiones"

    def toggle(self):
        self.visible = not self.visible
        self.title.visible = self.visible
        self.detail_text.visible = self.visible
        self.connections_text.visible = self.visible
