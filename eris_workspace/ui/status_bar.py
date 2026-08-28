"""Bottom status bar component."""
import dearpygui.dearpygui as dpg
from config import COLORS


def create_status_bar(state):
    dpg.add_separator()
    with dpg.group(horizontal=True):
        mode = "LIVE" if state.use_live else "Demo"
        dpg.add_text(f"  Eris Workspace 3D v1.0  |  Modo: {mode}  |  "
                     f"Tab: {state.current_tab}",
                     color=COLORS["dim"], tag="status_txt")
        dpg.add_spacer(width=50)
        dpg.add_text("Click en nodo para seleccionar  |  Scroll para zoom",
                     color=(80, 80, 110))
