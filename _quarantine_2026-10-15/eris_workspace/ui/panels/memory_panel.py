"""Memory list panel — left side."""
import dearpygui.dearpygui as dpg
from config import NODE_TYPES, COLORS


def create_memory_panel(graph, state):
    with dpg.group(tag="left_panel"):
        dpg.add_text("MEMORIAS DE ERIS", color=COLORS["accent"])
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_button(label="Todos", callback=lambda: _set_filter(graph, state, None), width=60)
            for ntype, info in NODE_TYPES.items():
                dpg.add_button(label=info["label"][:6],
                               callback=lambda s, a, u: _set_filter(graph, state, u),
                               user_data=ntype, width=65)
        dpg.add_separator()
        with dpg.child_window(tag="node_list_win", autosize_x=True, height=850):
            dpg.add_text("", color=COLORS["txt"], tag="node_list_txt")


def _set_filter(graph, state, ftype):
    state.filter_type = ftype
    _rebuild_list(graph, state)


def _rebuild_list(graph, state):
    nodes = graph.nodes
    if state.filter_type:
        nodes = [n for n in nodes if n.node_type == state.filter_type]
    lines = []
    for n in nodes[:30]:
        tag = n.node_type[:3].upper()
        bars = "#" * int(n.confidence * 6) + "." * (6 - int(n.confidence * 6))
        lines.append(f"[{tag}] {n.label[:30]}")
        lines.append(f"   {bars} {n.confidence:.0%}")
    dpg.set_value("node_list_txt", "\n".join(lines) if lines else "No hay nodos")


def rebuild_list(graph, state):
    _rebuild_list(graph, state)
