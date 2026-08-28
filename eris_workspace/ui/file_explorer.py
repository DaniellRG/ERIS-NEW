"""File explorer panel — bottom section."""
import os
import dearpygui.dearpygui as dpg
from config import COLORS, FILE_EXPLORER_DIRS


def create_file_explorer(state):
    with dpg.group(tag="file_explorer_panel"):
        with dpg.group(horizontal=True):
            dpg.add_text("ARCHIVOS DE ERIS", color=COLORS["accent"])
            dpg.add_spacer(width=10)
            for i, (name, _) in enumerate(FILE_EXPLORER_DIRS):
                cb = lambda s, a, u: _switch_dir(state, u)
                dpg.add_button(label=name, callback=cb, user_data=i, width=80)
        dpg.add_separator()
        with dpg.child_window(tag="file_explorer_win", autosize_x=True, height=120, autosize_y=False):
            dpg.add_text("", color=COLORS["txt"], tag="file_explorer_txt")


def update_file_explorer(state):
    idx = state.file_explorer_dir
    if idx >= len(FILE_EXPLORER_DIRS):
        idx = 0
    name, dirpath = FILE_EXPLORER_DIRS[idx]
    files = []
    try:
        for f in sorted(os.listdir(str(dirpath))):
            fp = os.path.join(str(dirpath), f)
            if os.path.isfile(fp):
                ext = os.path.splitext(f)[1].lower()
                if ext in (".json", ".py", ".md", ".txt", ".log", ".bat", ".sh"):
                    size = os.path.getsize(fp)
                    if size > 1024 * 1024:
                        sz = "{:.1f} MB".format(size / (1024*1024))
                    elif size > 1024:
                        sz = "{:.1f} KB".format(size / 1024)
                    else:
                        sz = "{} B".format(size)
                    files.append((f, sz, ext))
    except Exception:
        files = []

    lines = ["  {}/".format(name)]
    for f, sz, ext in files[:20]:
        icon = "py" if ext == ".py" else "js" if ext == ".json" else "tx"
        lines.append("  [{}] {} ({})".format(icon, f, sz))
    if len(files) > 20:
        lines.append("  ... +{} mas".format(len(files) - 20))
    dpg.set_value("file_explorer_txt", "\n".join(lines))


def _switch_dir(state, idx):
    state.file_explorer_dir = idx
    update_file_explorer(state)
