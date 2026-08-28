"""Top menu bar component."""
import dearpygui.dearpygui as dpg
from config import COLORS


def create_menu_bar(graph, state):
    with dpg.group(horizontal=True):
        dpg.add_text("  ERIS WORKSPACE 3D", color=COLORS["accent"])
        dpg.add_spacer(width=20)
        s = graph.get_stats()
        dpg.add_text(f"Nodos: {s['total_nodes']}  |  Conexiones: {s['total_edges']}  |  "
                     f"Conf: {s['avg_confidence']:.0%}", color=COLORS["txt"], tag="stats_txt")
        dpg.add_spacer(width=20)
        dpg.add_text("[R] Refresh  [L] Live  [H] Help  [ESC] Exit",
                     color=COLORS["dim"])
    dpg.add_separator()
