"""Graph view — 2-hemisphere brain with mouse controls."""
import time
import math
import dearpygui.dearpygui as dpg
from config import COLORS, ROTATION_SPEED, GLOW_COLOR, NODE_GLOW_SIZE
from core.graph_engine import layout_brain_hemispheres, project_3d_to_2d


positions_3d = {}
node_info = {}


def create_graph_view(graph, state):
    with dpg.group(tag="brain_panel"):
        with dpg.group(horizontal=True):
            dpg.add_text("CEREBRO DE ERIS", color=COLORS["accent"])
            dpg.add_spacer(width=5)
            rot_label = "Rotacion: ON" if state.auto_rotate else "Rotacion: OFF"
            dpg.add_button(label=rot_label, callback=_toggle_rotate,
                          tag="rotate_btn", width=100)
        with dpg.group(horizontal=True):
            dpg.add_text("  IZQUIERDO  ", color=(100, 180, 255))
            dpg.add_spacer(width=300)
            dpg.add_text("  DERECHO  ", color=(255, 150, 100))
        with dpg.plot(label="", height=300, width=-1, tag="plot3d", no_title=True):
            dpg.add_plot_axis(dpg.mvXAxis, label="", no_tick_labels=True, tag="x_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="", no_tick_labels=True, tag="y_axis")


def _toggle_rotate(sender, app_data, user_data):
    from core.state import state
    state.auto_rotate = not state.auto_rotate
    label = "Rotacion: ON" if state.auto_rotate else "Rotacion: OFF"
    try:
        dpg.set_item_label("rotate_btn", label)
    except Exception:
        pass


def on_mouse_wheel(sender, app_data, user_data):
    from core.state import state
    state.cam_dist = max(4.0, min(30.0, state.cam_dist - app_data * 0.8))


def on_right_click(sender, app_data, user_data):
    from core.state import state
    state.is_dragging = True
    mouse_pos = dpg.get_mouse_pos()
    state.drag_last_x = mouse_pos[0]
    state.drag_last_y = mouse_pos[1]


def on_right_drag(sender, app_data, user_data):
    from core.state import state
    if not state.is_dragging:
        return
    mouse_pos = dpg.get_mouse_pos()
    dx = mouse_pos[0] - state.drag_last_x
    dy = mouse_pos[1] - state.drag_last_y
    state.cam_rot_y += dx * 0.3
    state.cam_rot_x = max(-80, min(80, state.cam_rot_x + dy * 0.3))
    state.drag_last_x = mouse_pos[0]
    state.drag_last_y = mouse_pos[1]


def on_right_release(sender, app_data, user_data):
    from core.state import state
    state.is_dragging = False


def compute_layout(graph):
    global positions_3d, node_info
    positions_3d = layout_brain_hemispheres(graph.nodes, graph.edges, iterations=40)
    node_info = {}
    for n in graph.nodes:
        c = n.color
        node_info[n.id] = {
            "rgb": (int(c[0]*255), int(c[1]*255), int(c[2]*255)),
            "size": n.display_size,
            "lit": n.lit,
            "hemisphere": n.hemisphere,
        }


def select_node(nid, graph, state):
    state.selected_node_id = nid
    for n in graph.nodes:
        n.lit = (n.id == nid)
    compute_layout(graph)
    draw_graph(graph, state)


def draw_graph(graph, state):
    global positions_3d, node_info
    if not positions_3d:
        compute_layout(graph)

    if state.auto_rotate and not state.is_dragging:
        state.cam_rot_y += ROTATION_SPEED

    try:
        for tag in list(dpg.get_item_children("x_axis", 1) or []):
            dpg.delete_item(tag)
    except Exception:
        pass

    for e in graph.edges:
        if e.source_id in positions_3d and e.target_id in positions_3d:
            p1 = project_3d_to_2d(positions_3d[e.source_id], state.cam_rot_x, state.cam_rot_y, state.cam_dist)
            p2 = project_3d_to_2d(positions_3d[e.target_id], state.cam_rot_x, state.cam_rot_y, state.cam_dist)
            is_connected = (e.source_id == state.selected_node_id or e.target_id == state.selected_node_id)
            src_h = node_info.get(e.source_id, {}).get("hemisphere", "left")
            tgt_h = node_info.get(e.target_id, {}).get("hemisphere", "left")
            is_cross = src_h != tgt_h

            if is_connected:
                color = (120, 180, 255, 220)
            elif is_cross:
                color = (200, 160, 100, 100)
            else:
                color = (80, 80, 120, 50)

            tag_e = "edge_{}_{}".format(e.source_id, e.target_id)
            dpg.add_line_series([p1[0], p2[0]], [p1[1], p2[1]],
                               parent="x_axis", label="", tag=tag_e)
            with dpg.theme() as eth:
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, color)
            dpg.bind_item_theme(tag_e, eth)

    by_color = {}
    glow_points = {"xs": [], "ys": []}

    for nid, info in node_info.items():
        if nid not in positions_3d:
            continue
        p = project_3d_to_2d(positions_3d[nid], state.cam_rot_x, state.cam_rot_y, state.cam_dist)
        rgb = info["rgb"]
        is_selected = (nid == state.selected_node_id)

        if is_selected:
            glow_points["xs"].append(p[0])
            glow_points["ys"].append(p[1])

        if rgb not in by_color:
            by_color[rgb] = {"xs": [], "ys": []}
        by_color[rgb]["xs"].append(p[0])
        by_color[rgb]["ys"].append(p[1])

    for c, data in by_color.items():
        tag = "scat_{}_{}_{}".format(c[0], c[1], c[2])
        dpg.add_scatter_series(data["xs"], data["ys"], parent="x_axis", label="", tag=tag)
        with dpg.theme() as st:
            with dpg.theme_component(dpg.mvScatterSeries):
                dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, c + (230,))
                dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, (255, 255, 255, 180))
                dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Circle)
                dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 8)
                dpg.add_theme_color(dpg.mvPlotCol_Line, (0, 0, 0, 0))
            dpg.bind_item_theme(tag, st)

    if glow_points["xs"]:
        tag_glow = "glow_ring"
        dpg.add_scatter_series(glow_points["xs"], glow_points["ys"],
                               parent="x_axis", label="", tag=tag_glow)
        with dpg.theme() as gt:
            with dpg.theme_component(dpg.mvScatterSeries):
                dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, GLOW_COLOR + (100,))
                dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, GLOW_COLOR + (200,))
                dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Circle)
                dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, NODE_GLOW_SIZE)
                dpg.add_theme_color(dpg.mvPlotCol_Line, (0, 0, 0, 0))
            dpg.bind_item_theme(tag_glow, gt)

    dpg.set_axis_limits("x_axis", -5, 5)
    dpg.set_axis_limits("y_axis", -4, 4)
