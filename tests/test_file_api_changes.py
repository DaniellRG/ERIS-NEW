"""
tests/test_file_api_changes.py
──────────────────────────────
Fase 3.2: "nada se rompe". Toda escritura de `core/file_api.py`:

- deja backup en `memory/undo_backups/` (vía `core/file_undo.snapshot_path`),
- dice EXACTAMENTE qué líneas cambió,
- se puede revertir con `deshacer` (action del dispatcher / tool `undo` / CLI).
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from core import file_api  # noqa: E402
from core import file_undo  # noqa: E402


def _isolate(tmp_path, monkeypatch):
    """Aísla backups e índice de undo (nunca toca memory/ ni data/ reales)."""
    bk = tmp_path / "undo_backups"
    bk.mkdir()
    monkeypatch.setattr(file_undo, "_BACKUP_DIR", bk)
    monkeypatch.setattr(file_undo, "_UNDO_LOG", tmp_path / "file_undo.json")
    fbk = tmp_path / "fileapi_backups"
    fbk.mkdir()
    monkeypatch.setattr(file_api, "BACKUP_DIR", fbk)


# ── exactitud de las líneas ──

def test_changed_lines_replace():
    d = file_api.changed_lines("a\nb\nc\n", "a\nB\nc\n")
    assert d["added"] == [2]
    assert d["removed"] == [2]


def test_changed_lines_insert_and_delete():
    ins = file_api.changed_lines("a\nb\n", "a\nb\nc\n")
    assert ins["added"] == [3]
    assert ins["removed"] == []

    dele = file_api.changed_lines("a\nb\nc\n", "a\nc\n")
    assert dele["removed"] == [2]
    assert dele["added"] == []


def test_ranges_compresses():
    assert file_api._ranges([1, 2, 3, 7, 9, 10]) == "1-3,7,9-10"


def test_describe_mentions_line_numbers(tmp_path):
    f = tmp_path / "a.py"
    desc = file_api._describe(str(f), "l1\nl2\nl3\n", "l1\nXX\nl3\n")
    assert "a.py" in desc
    assert "2" in desc
    assert "total 3" in desc


# ── write: dice qué hizo y se puede deshacer ──

def test_write_new_file_reports_and_undo_removes(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    f = tmp_path / "nuevo.txt"

    r = file_api.write_file(str(f), "hola\nmundo\n")
    assert r.success
    assert "Creado" in r.message
    assert "+2 línea(s) [1-2]" in r.message
    assert f.exists()

    out = file_api.file_api({"action": "deshacer"})
    assert "Undo aplicado" in out
    assert not f.exists()  # no existía antes → deshacer lo elimina


def test_write_over_existing_reports_and_undo_restores(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    f = tmp_path / "a.txt"
    f.write_text("uno\ndos\n")

    r = file_api.write_file(str(f), "uno\ndos\ntres\n")
    assert r.success
    assert "Escrito" in r.message
    assert "3" in r.message

    file_api.file_api({"action": "deshacer"})
    assert f.read_text() == "uno\ndos\n"


# ── edit: exactamente qué línea y deshacer ──

def test_edit_reports_exact_line_and_undo(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    f = tmp_path / "a.py"
    f.write_text("l1\nl2\nl3\n")

    r = file_api.edit_file(str(f), "l2", "l2 cambiado")
    assert r.success
    assert "Edit aplicado" in r.message
    assert "2" in r.message
    assert f.read_text() == "l1\nl2 cambiado\nl3\n"

    out = file_api.file_api({"action": "deshacer"})
    assert "Undo aplicado" in out
    assert f.read_text() == "l1\nl2\nl3\n"


# ── multi_edit / insert / delete ──

def test_multi_edit_reports_and_undo(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    f = tmp_path / "m.txt"
    f.write_text("a\nb\nc\n")

    r = file_api.multi_edit(str(f), [{"old": "a", "new": "A"}, {"old": "c", "new": "C"}])
    assert r.success
    assert "2 edits" in r.message
    assert f.read_text() == "A\nb\nC\n"

    file_api.file_api({"action": "deshacer"})
    assert f.read_text() == "a\nb\nc\n"


def test_insert_reports_and_undo(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    f = tmp_path / "i.txt"
    f.write_text("base\n")

    r = file_api.insert_in_file(str(f), after="base\n", text="extra\n")
    assert r.success
    assert "insertado" in r.message
    assert f.read_text() == "base\nextra\n"

    file_api.file_api({"action": "deshacer"})
    assert f.read_text() == "base\n"


def test_delete_reports_and_undo_restores(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    f = tmp_path / "d.txt"
    f.write_text("x\ny\n")

    r = file_api.delete_file(str(f))
    assert r.success
    assert "eliminado" in r.message
    assert not f.exists()

    file_api.file_api({"action": "deshacer"})
    assert f.read_text() == "x\ny\n"


# ── historial y no-doble-snapshot ──

def test_undo_list_shows_history(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    f = tmp_path / "h.txt"
    file_api.write_file(str(f), "1\n")
    out = file_api.file_api({"action": "undo_list"})
    assert "Historial de undo" in out
    assert "file_api" in out


def test_file_api_is_not_double_snapshotted_by_dispatcher():
    # file_api se auto-respalda; el dispatcher ya no lo duplica.
    assert "file_api" not in file_undo._MODIFY_MAP


def test_snapshot_path_records_entry(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    f = tmp_path / "s.txt"
    f.write_text("contenido\n")
    entry = file_undo.snapshot_path(str(f), tool="file_api", action="edit")
    assert entry is not None
    assert entry["existed"] is True
    assert entry["backup"] and Path(entry["backup"]).exists()
    assert len(file_undo._load_log()) == 1


def test_unknown_action_message_lists_deshacer():
    msg = file_api.file_api({"action": "inexistente_xyz"})
    assert "deshacer" in msg
