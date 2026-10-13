"""
tests/test_fase2_eyes.py
────────────────────────
Fase 2 — los ojos (2.2, 2.3, 2.4).

- 2.2: con el backend vivo, la `class` de Hyprland alimenta la clasificación
  (programación / terminal / navegador) sin tocar los conjuntos de Windows.
- 2.3: `codebase_explorer action=map` devuelve el árbol con una línea por
  archivo, y la CLI lo inyecta sola al detectar un proyecto.
- 2.4: una ventana sensible NO se reporta, pero queda un evento SIN contenido.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import core.observer as obs  # noqa: E402
from core.codebase_explorer import codebase_explorer  # noqa: E402


# ── 2.2 clasificación con clases de Linux ─────────────────────────────────
def test_classify_linux_terminal_and_editor():
    assert obs.classify("kitty", "~/ERIS-NEW")["kind"] == "terminal"
    assert obs.classify("foot", "")["kind"] == "terminal"
    assert obs.classify("ghostty", "zsh")["kind"] == "terminal"
    assert obs.classify("code", "main.py — ERIS")["kind"] == "programacion"
    assert obs.classify("gnome-text-editor", "notas")["kind"] == "programacion"


def test_classify_linux_browser():
    for cls in ("firefox", "librewolf", "zen", "brave-browser", "chromium-browser"):
        assert obs.classify(cls, "GitHub")["kind"] == "navegacion"


def test_windows_classes_still_work():
    assert obs.classify("devenv", "sol.py")["kind"] == "programacion"
    assert obs.classify("devenv", "sol.py")["coding"] is True
    # las terminales Windows siguen siendo "coding" (cmd está en _CODE_PROCS)
    assert obs.classify("cmd", "C:\\")["coding"] is True
    assert "conhost" in obs._TERMINAL_PROCS


# ── 2.4 ventana sensible: silencio total + evento sin contenido ────────────
def test_sensitive_window_records_contentless_event(monkeypatch):
    state = obs._fresh_state()
    monkeypatch.setattr(obs, "_load", lambda: state)
    monkeypatch.setattr(obs, "_save", lambda d: None)
    monkeypatch.setattr(
        obs, "get_foreground",
        lambda: {"pid": 1, "proc": "firefox", "title": "Mi Banco - Ingresar", "class": "firefox"})

    events = obs.poll(force=True)

    assert events == [], "no se reporta nada de una ventana sensible"
    assert state["current"]["kind"] == "sensitive"
    logged = state.get("events", [])
    assert logged and logged[-1]["type"] == "privado"
    assert "proc" not in logged[-1] and "title" not in logged[-1], \
        "el evento no debe llevar contenido"


# ── 2.3 mapa del proyecto con una línea por archivo ───────────────────────
def test_codebase_explorer_map(tmp_path):
    (tmp_path / "mod_a.py").write_text('"""Hace la cosa A."""\nx = 1\n', encoding="utf-8")
    (tmp_path / "mod_b.py").write_text("def foo():\n    pass\n", encoding="utf-8")
    (tmp_path / "nota.txt").write_text("no cuenta\n", encoding="utf-8")

    out = codebase_explorer({"action": "map", "path": str(tmp_path), "limit": 10})
    assert "mod_a.py" in out and "Hace la cosa A." in out
    assert "mod_b.py" in out
    assert "nota.txt" not in out  # solo .py
