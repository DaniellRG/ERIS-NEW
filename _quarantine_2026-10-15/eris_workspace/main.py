"""Eris Workspace 3D — Centro de Comando Grid 2x2."""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dearpygui.dearpygui as dpg
from config import COLORS, TAB_LIST, AUTO_REFRESH_INTERVAL
from core.data_loader import GraphData
from core.state import state
from ui.theme import setup_theme
from ui.graph_view import create_graph_view, compute_layout, draw_graph, select_node, on_mouse_wheel, on_right_click, on_right_drag, on_right_release
from ui.terminal_panel import create_terminal_panel, update_terminal
from ui.file_explorer import create_file_explorer, update_file_explorer
from ui.panels.detail_panel import create_detail_panel, show_detail
from ui.popup import create_help_popup, toggle_help

dpg.create_context()
setup_theme()

graph = GraphData(use_live=False)
graph.refresh()
state.add_log("Workspace iniciado con {} nodos".format(len(graph.nodes)))
state.add_terminal("Eris Workspace 3D iniciado")
state.add_terminal("Cargando {} nodos y {} conexiones".format(len(graph.nodes), len(graph.edges)))

create_help_popup()

with dpg.window(tag="main_win", no_title_bar=True, no_resize=True, no_move=True,
                width=1920, height=1080, pos=[0, 0]):

    with dpg.group(horizontal=True):
        dpg.add_text("  ERIS WORKSPACE", color=COLORS["accent"])
        dpg.add_spacer(width=15)
        for tab in TAB_LIST:
            dpg.add_button(label=tab,
                          callback=lambda s, a, u: _switch_tab(u),
                          user_data=tab, width=85)
        dpg.add_spacer(width=30)
        s = graph.get_stats()
        dpg.add_text("Nodos: {} | Conf: {:.0%}".format(
            s["total_nodes"], s["avg_confidence"]),
            color=COLORS["dim"], tag="stats_txt")
        dpg.add_spacer(width=15)
        dpg.add_text("[R]Refresh [L]Live [Space]Rotar [H]Help [ESC]Exit",
                     color=COLORS["dim"])
    dpg.add_separator()

    with dpg.group(horizontal=True):
        create_graph_view(graph, state)
        dpg.add_spacer(width=3)
        create_terminal_panel(state)

    dpg.add_separator()

    with dpg.group(horizontal=True):
        create_file_explorer(state)
        dpg.add_spacer(width=3)
        create_detail_panel(graph)

    dpg.add_separator()
    with dpg.group(horizontal=True):
        dpg.add_text("  Eris Workspace 3D v2.0  |  Demo  |  Tab: Memory",
                     color=COLORS["dim"], tag="status_txt")
        dpg.add_spacer(width=50)
        dpg.add_text("Rueda=Zoom | Clic der=Rotar | Click=Seleccionar",
                     color=(80, 80, 110))


def _switch_tab(tab_name):
    state.current_tab = tab_name
    state.add_log("Tab cambiado a: {}".format(tab_name))
    state.add_terminal("Tab cambiado a: {}".format(tab_name))
    try:
        dpg.set_value("status_txt",
                      "  Eris Workspace 3D v2.0  |  {}  |  Tab: {}".format(
                          "LIVE" if state.use_live else "Demo", tab_name))
    except Exception:
        pass


def input(key):
    if key == 256:  # ESC
        dpg.destroy_context()
    elif key == 82:  # R
        graph.refresh()
        compute_layout(graph)
        draw_graph(graph, state)
        state.add_terminal("Refresh: {} nodos".format(len(graph.nodes)))
        update_file_explorer(state)
        try:
            s = graph.get_stats()
            dpg.set_value("stats_txt", "Nodos: {} | Conf: {:.0%}".format(
                s["total_nodes"], s["avg_confidence"]))
        except Exception:
            pass
    elif key == 76:  # L
        graph.use_live = not graph.use_live
        state.use_live = graph.use_live
        graph.refresh()
        compute_layout(graph)
        draw_graph(graph, state)
        mode = "LIVE" if graph.use_live else "Demo"
        state.add_terminal("Modo: {}".format(mode))
        try:
            dpg.set_value("status_txt", "  Eris Workspace 3D v2.0  |  {}  |  Tab: {}".format(
                mode, state.current_tab))
        except Exception:
            pass
    elif key == 32:  # Space
        state.auto_rotate = not state.auto_rotate
        label = "Rotacion: ON" if state.auto_rotate else "Rotacion: OFF"
        try:
            dpg.set_item_label("rotate_btn", label)
        except Exception:
            pass
    elif key == 72:  # H
        toggle_help()


with dpg.handler_registry():
    dpg.add_key_press_handler(callback=input)
    dpg.add_mouse_wheel_handler(callback=on_mouse_wheel)
    dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Right, callback=on_right_click)
    dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Right, callback=on_right_drag)
    dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Right, callback=on_right_release)

compute_layout(graph)
draw_graph(graph, state)
update_file_explorer(state)

for i in range(3):
    state.simulate_tick()
update_terminal(state)

dpg.create_viewport(title="Eris Workspace 3D", width=1920, height=1080)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main_win", True)

last_refresh = time.time()
last_sim = time.time()

while dpg.is_dearpygui_running():
    now = time.time()

    if state.auto_rotate and not state.is_dragging:
        draw_graph(graph, state)

    if now - last_sim >= 5.0:
        state.simulate_tick()
        update_terminal(state)
        last_sim = now

    if now - last_refresh >= AUTO_REFRESH_INTERVAL:
        graph.refresh()
        compute_layout(graph)
        draw_graph(graph, state)
        update_file_explorer(state)
        last_refresh = now
        try:
            s = graph.get_stats()
            dpg.set_value("stats_txt", "Nodos: {} | Conf: {:.0%}".format(
                s["total_nodes"], s["avg_confidence"]))
        except Exception:
            pass

    dpg.render_dearpygui_frame()

dpg.destroy_context()
