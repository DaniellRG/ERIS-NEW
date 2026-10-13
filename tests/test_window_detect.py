"""
tests/test_window_detect.py
───────────────────────────
Fase 2.1: `core/window_detect.py` es el módulo común de los ojos.

Verifica el contrato que consumen el observer y la integración con IDEs:
- Los DOS backends quedan vivos (Windows definido e inerte fuera de Windows;
  Hyprland parsea `hyprctl -j`).
- La ventana activa va primero en `list_windows` (lo que espera
  `detect_active_ide_wayland`, que asume `titles[0]` = activa).
- Dedup, tope, y que NADA lanza: ante basura devuelve vacío honesto.
- El observer delega en este módulo (y su guard de sensibles sigue intacto).
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import core.window_detect as wd  # noqa: E402
import core.observer as obs  # noqa: E402


EMPTY = {"pid": 0, "proc": "", "title": "", "class": ""}


def test_normalize_proc():
    assert wd.normalize_proc("Code.EXE") == "code"
    assert wd.normalize_proc("notepad64") == "notepad"
    assert wd.normalize_proc("") == ""
    assert wd.normalize_proc(None) == ""


def test_windows_backend_alive_but_inert_off_windows():
    # El backend Windows existe siempre (no se compila afuera).
    assert callable(wd.fg_hwnd) and callable(wd.window_title)
    assert callable(wd.window_rect) and callable(wd._win_list_windows)
    if not wd.is_windows():
        assert wd.fg_hwnd() == 0
        assert wd.window_title(1) == ""
        assert wd.window_rect(1) is None
        assert wd._win_get_foreground() == EMPTY


def test_foreground_from_hypr(monkeypatch):
    monkeypatch.setattr(wd, "_IS_WIN", False)
    monkeypatch.setattr(wd, "_hypr_json",
                        lambda *a: {"class": "kitty", "title": "~", "pid": 123})
    fg = wd.get_foreground()
    assert fg["proc"] == "kitty"
    assert fg["class"] == "kitty"
    assert fg["title"] == "~"
    assert fg["pid"] == 123


def test_foreground_falls_back_to_x11(monkeypatch):
    monkeypatch.setattr(wd, "_IS_WIN", False)
    monkeypatch.setattr(wd, "_hypr_json", lambda *a: None)
    monkeypatch.setattr(wd, "_x11_get_foreground",
                        lambda: {"pid": 7, "proc": "xterm", "title": "t", "class": ""})
    assert wd.get_foreground()["proc"] == "xterm"


def test_list_windows_active_first(monkeypatch):
    def fake(*args):
        if args and args[0] == "clients":
            return [
                {"address": "0x2", "class": "firefox", "title": "Web", "pid": 2},
                {"address": "0x1", "class": "code", "title": "main.py", "pid": 1},
            ]
        if args and args[0] == "activewindow":
            return {"address": "0x1"}
        return None

    monkeypatch.setattr(wd, "_IS_WIN", False)
    monkeypatch.setattr(wd, "_hypr_json", fake)
    ws = wd.list_windows()
    assert ws[0]["proc"] == "code"          # la activa (0x1) va primero
    assert {w["proc"] for w in ws} == {"code", "firefox"}


def test_list_windows_dedup_and_limit(monkeypatch):
    def fake(*args):
        if args and args[0] == "clients":
            return [{"address": f"0x{i}", "class": "code", "title": f"T{i}", "pid": i}
                    for i in range(10)]
        return None

    monkeypatch.setattr(wd, "_IS_WIN", False)
    monkeypatch.setattr(wd, "_hypr_json", fake)
    assert len(wd.list_windows(3)) == 3
    # títulos repetidos -> dedup
    monkeypatch.setattr(wd, "_hypr_json",
                        lambda *a: ([{"class": "code", "title": "T", "pid": i}
                                     for i in range(5)] if a and a[0] == "clients" else None))
    assert len(wd.list_windows(10)) == 1


def test_get_active_class(monkeypatch):
    monkeypatch.setattr(wd, "get_foreground",
                        lambda: {"class": "code", "proc": "code", "title": "", "pid": 1})
    assert wd.get_active_class() == "code"


def test_never_raises_on_garbage(monkeypatch):
    def boom(*a):
        raise RuntimeError("hyprctl explotó")

    monkeypatch.setattr(wd, "_IS_WIN", False)
    monkeypatch.setattr(wd, "_hypr_json", boom)
    assert wd.get_foreground() == EMPTY
    assert wd.list_windows() == []


def test_observer_delegates_to_window_detect(monkeypatch):
    monkeypatch.setattr(obs, "_wd_get_foreground",
                        lambda: {"pid": 9, "proc": "code", "title": "x", "class": "code"})
    assert obs.get_foreground()["proc"] == "code"
    monkeypatch.setattr(obs, "_wd_list_windows", lambda n=25: [{"proc": "a"}])
    assert obs.list_open_windows(5) == [{"proc": "a"}]


def test_observer_sensitive_guard_still_private():
    assert obs._is_sensitive("chrome", "Banco Galicia - Ingresá") is True
    assert obs._is_sensitive("code", "main.py - ERIS") is False
