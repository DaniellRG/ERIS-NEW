"""Help popup."""
import dearpygui.dearpygui as dpg


def create_help_popup():
    with dpg.window(label="Help", tag="help_win", show=False, width=350, height=300,
                    pos=[300, 200]):
        dpg.add_text("CONTROLES DEL WORKSPACE", color=(100, 180, 255))
        dpg.add_separator()
        controls = [
            ("R", "Refresh datos"),
            ("L", "Cambiar Demo/Live"),
            ("H", "Este help"),
            ("ESC", "Salir"),
            ("Click nodo", "Seleccionar y ver detalle"),
        ]
        for key, desc in controls:
            dpg.add_text("  {}:  {}".format(key, desc), color=(180, 180, 200))


def toggle_help():
    if dpg.is_item_shown("help_win"):
        dpg.hide_item("help_win")
    else:
        dpg.show_item("help_win")
