"""Terminal panel — real-time activity logs."""
import time
import dearpygui.dearpygui as dpg
from config import COLORS


def create_terminal_panel(state):
    with dpg.group(tag="terminal_panel"):
        with dpg.group(horizontal=True):
            dpg.add_text("ERIS EN VIVO", color=COLORS["accent"])
            dpg.add_spacer(width=10)
            dpg.add_button(label="Clear", callback=lambda: _clear_terminal(state), width=60)
        dpg.add_separator()
        with dpg.child_window(tag="terminal_win", autosize_x=True, height=380, autosize_y=False):
            dpg.add_text("", color=COLORS["txt"], tag="terminal_txt")


def update_terminal(state):
    if not state.terminal_logs:
        return
    lines = []
    for log in list(state.terminal_logs)[:30]:
        ts = time.strftime("%H:%M", time.localtime(log["time"]))
        lvl = log["level"]
        if lvl == "error":
            color_tag = "[ERR]"
        elif lvl == "warning":
            color_tag = "[WRN]"
        else:
            color_tag = "[INF]"
        lines.append("{} {} {}".format(ts, color_tag, log["msg"]))
    dpg.set_value("terminal_txt", "\n".join(lines))


def _clear_terminal(state):
    state.terminal_logs.clear()
    dpg.set_value("terminal_txt", "Terminal limpiada")
