"""Detail panel — right side."""
import dearpygui.dearpygui as dpg
from config import NODE_TYPES, COLORS


def create_detail_panel(graph):
    with dpg.group(tag="right_panel"):
        dpg.add_text("DETALLE DEL NODO", color=COLORS["accent"])
        dpg.add_separator()
        with dpg.child_window(tag="detail_win", autosize_x=True, height=200):
            dpg.add_text("Click en un nodo para ver detalles",
                         color=COLORS["dim"], tag="detail_title")
            dpg.add_text("", color=COLORS["txt"], tag="detail_type")
            dpg.add_text("", color=COLORS["txt"], tag="detail_id")
            dpg.add_text("Confianza:", color=COLORS["dim"], tag="detail_conf_label")
            dpg.add_progress_bar(tag="detail_conf_bar", default_value=0.0, width=-1)
            dpg.add_text("", color=COLORS["txt"], tag="detail_meta")
        dpg.add_separator()
        dpg.add_text("CONEXIONES", color=COLORS["accent"])
        with dpg.child_window(tag="conn_win", autosize_x=True, height=200):
            dpg.add_text("", color=COLORS["txt"], tag="conn_txt")


def show_detail(graph, node):
    if not node:
        dpg.set_value("detail_title", "Click en un nodo para ver detalles")
        dpg.set_value("detail_type", "")
        dpg.set_value("detail_id", "")
        dpg.set_value("detail_conf_label", "Confianza:")
        dpg.set_value("detail_conf_bar", 0.0)
        dpg.set_value("detail_meta", "")
        dpg.set_value("conn_txt", "")
        return

    ti = NODE_TYPES.get(node.node_type, {})
    dpg.set_value("detail_title", node.label)
    dpg.set_value("detail_type", "Tipo: " + ti.get("label", "?"))
    dpg.set_value("detail_id", "ID: " + node.id)
    dpg.set_value("detail_conf_label",
                  "Confianza: {:.0%}".format(node.confidence))
    dpg.set_value("detail_conf_bar", node.confidence)

    meta_lines = []
    for k, v in node.metadata.items():
        meta_lines.append("{}: {}".format(k, str(v)[:50]))
    dpg.set_value("detail_meta", "\n".join(meta_lines) if meta_lines else "")

    conns = graph.get_connections(node.id)
    if conns:
        cl = []
        for cn, st in sorted(conns, key=lambda x: -x[1])[:8]:
            bars = "#" * int(st * 10) + "." * (10 - int(st * 10))
            cl.append(cn.label[:26])
            cl.append("   {} {:.0%}".format(bars, st))
        dpg.set_value("conn_txt", "\n".join(cl))
    else:
        dpg.set_value("conn_txt", "Sin conexiones")
