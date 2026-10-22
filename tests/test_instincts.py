"""Tests herméticos de Fase B: instintos con confianza.

No tocan red, ni el deck real, ni `memory/`. Cada test usa un store temporal.
"""
from __future__ import annotations

import json
import sys
import time

import pytest

from core import instincts as inst


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    store = tmp_path / "instincts"
    monkeypatch.setenv("ERIS_INSTINCTS_DIR", str(store))
    monkeypatch.setattr(inst, "DECK_FILE", tmp_path / "no-deck.json")
    inst.set_store_dir(None)
    inst._DECK_CACHE.update({"ts": 0.0, "value": None})
    yield store
    inst.set_store_dir(None)


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "proj"
    path.mkdir()
    return path


def _add(trigger="cuando falle el build", action="correr dotnet build", **kw):
    return inst.add_instinct(trigger, action, **kw)


def test_add_and_persist(isolated, project):
    item = _add(scope="project", project=str(project), confidence=0.5)
    assert item is not None
    assert item["id"].startswith("inst_")
    assert item["confidence"] == 0.5
    assert item["hits"] == 1
    assert item["scope"] == "project"
    assert item["project"] == inst.project_slug(project)
    assert item["evidence"]

    slug = inst.project_slug(project)
    assert (isolated / "projects" / f"{slug}.yaml").exists()

    listed = inst.list_instincts(scope="project", project=str(project))
    assert [i["id"] for i in listed] == [item["id"]]
    assert inst.get_instinct(item["id"])["action"] == "correr dotnet build"


def test_add_validation_and_clamp(isolated):
    assert _add(trigger="", action="x") is None
    assert _add(trigger="x", action="") is None
    assert inst.add_instinct("t", "a", scope="nope") is None
    assert inst.add_instinct("t", "a", scope="project", project="/no/existe") is None

    high = _add(trigger="cuando haya deploy", action="revisar docker", confidence=5)
    low = _add(trigger="cuando haya backup", action="verificar restore", confidence=-1)
    assert high["confidence"] == 0.9
    assert low["confidence"] == 0.1


def test_reinforce_caps_and_deduplicates_evidence(isolated):
    item = _add(confidence=0.5)
    iid = item["id"]

    first = inst.reinforce(iid, note="ok", ref="r1")
    assert first["confidence"] == 0.6
    assert first["hits"] == 2

    same = inst.reinforce(iid, note="ok otra vez", ref="r1")
    assert same["confidence"] == 0.6
    assert same["hits"] == 2

    second = inst.reinforce(iid, note="ok", ref="r2")
    assert second["confidence"] == 0.7

    for n in range(10):
        item = inst.reinforce(iid, note=f"ref {n}", ref=f"r{n + 10}")
    assert item["confidence"] == 0.9
    assert item["hits"] >= 5
    assert item["mature"] is True


def test_contradict_retires(isolated):
    item = _add(confidence=0.5)
    iid = item["id"]

    one = inst.contradict(iid, note="mal", ref="c1")
    assert one["confidence"] == 0.35
    assert one["misses"] == 1
    assert one["status"] == "active"

    two = inst.contradict(iid, note="mal", ref="c2")
    assert two["confidence"] == 0.2
    assert two["misses"] == 2
    assert two["status"] == "retired"

    assert inst.list_instincts(scope="global") == []
    assert len(inst.list_instincts(scope="global", include_retired=True)) == 1


def test_retired_reactivates_on_new_evidence(isolated):
    item = _add(confidence=0.4)
    iid = item["id"]
    inst.contradict(iid, note="mal", ref="c1")
    inst.contradict(iid, note="mal", ref="c2")
    assert inst.get_instinct(iid)["status"] == "retired"

    again = inst.reinforce(iid, note="volvió a pasar", ref="r1")
    assert again["status"] == "active"
    assert again["misses"] == 0


def test_scope_isolation(isolated, project, tmp_path):
    other = tmp_path / "otro"
    other.mkdir()
    g = _add(trigger="cuando falle el build", action="correr dotnet build",
             scope="global")
    p = _add(trigger="cuando se toque docker", action="revisar compose",
             scope="project", project=str(project))

    assert {i["id"] for i in inst.list_instincts(scope="global")} == {g["id"]}
    assert {i["id"] for i in inst.list_instincts(
        scope="project", project=str(project))} == {p["id"]}
    assert {i["id"] for i in inst.list_instincts(
        scope=None, project=str(project))} == {g["id"], p["id"]}
    assert {i["id"] for i in inst.list_instincts(
        scope=None, project=str(other))} == {g["id"]}

    block = inst.instinct_block(project=str(project))
    assert "cuando falle el build" in block
    assert "cuando se toque docker" in block
    block_other = inst.instinct_block(project=str(other))
    assert "cuando se toque docker" not in block_other


def test_project_slug_and_git_root(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    sub = repo / "sub"
    sub.mkdir()

    slug = inst.project_slug(repo)
    assert slug.startswith("repo-")
    assert len(slug.rsplit("-", 1)[1]) == 6
    assert inst.project_slug(sub) == slug
    assert inst.project_slug(repo) == slug

    with pytest.raises(ValueError):
        inst.project_slug(tmp_path / "no-existe")


def test_project_scope_accepts_slug(isolated, project):
    slug = inst.project_slug(project)
    item = _add(scope="project", project=slug)
    assert item["project"] == slug
    assert inst.list_instincts(scope="project", project=str(project))[0]["id"] == item["id"]


def test_instinct_block_filters_caps_and_limit(isolated):
    cases = [
        ("cuando falle el build", "correr dotnet build y pegar salida", 0.5),
        ("cuando pidan deploy", "revisar docker compose antes", 0.55),
        ("cuando toque base de datos", "hacer backup previo", 0.6),
        ("cuando haya tests rotos", "leer el traceback completo", 0.65),
        ("cuando se edite main.py", "correr suite completa", 0.7),
        ("cuando se agregue una tool", "sincronizar registry y declarations", 0.8),
        ("cuando se cree un commit", "firmar con identidad correcta", 0.9),
    ]
    added = [_add(t, a, confidence=c) for t, a, c in cases]
    assert all(added)
    low = _add("cuando sea opcional", "ignorar por baja confianza", confidence=0.4)
    inst.retire(added[0]["id"], reason="prueba")

    block = inst.instinct_block(limit=5)
    lines = block.splitlines()
    assert lines[0] == "[INSTINTOS APRENDIDOS]"
    assert len(lines) - 1 == 5
    assert len(block) <= 700
    assert "0.9" in block
    assert "ignorar por baja confianza" not in block
    assert "correr dotnet build" not in block  # retirado
    assert low["id"]


def test_instinct_block_empty(isolated):
    assert inst.instinct_block() == ""


def test_observe_user_message_creates_and_ignores(isolated):
    item = inst.observe_user_message("Usuario: no declares listo sin probar")
    assert item is not None
    assert item["source"] == "correction"
    assert item["confidence"] == 0.3
    assert "no declares listo" in item["action"]
    assert item["scope"] == "global"

    assert inst.observe_user_message("Usuario: hola, ¿cómo estás?") is None
    assert inst.observe_user_message("Usuario: no, gracias") is None
    assert inst.observe_user_message("Usuario: en realidad prefiero el otro") is None

    # Proyecto inválido: cae al deck (sin deck → global), no pierde la corrección.
    fallback = inst.observe_user_message(
        "Usuario: no inventes datos sin verificar", project="/no/existe"
    )
    assert fallback is not None
    assert fallback["scope"] == "global"
    assert fallback["id"] in {i["id"] for i in inst.list_instincts(
        scope=None, project="/no/existe")}


def test_observe_user_message_reinforces_similar(isolated):
    first = inst.observe_user_message("Usuario: no declares listo sin probar")
    second = inst.observe_user_message(
        "Usuario: no declares listo sin correr los tests",
        last_response="ERIS: Listo, ya está.",
    )
    assert first is not None and second is not None
    assert first["id"] == second["id"]
    assert second["confidence"] == 0.4
    assert second["hits"] == 2
    assert len(second["evidence"]) == 2


def test_mine_from_deck_fix_and_repeat(isolated, project, tmp_path):
    now = time.time()
    cmd_build = f"command=cd {project} && dotnet build, action=run"
    cmd_test = f"command=cd {project} && pytest -q, action=run"
    cmd_secret = (
        f"command=cd {project} && curl -H 'Authorization: Bearer "
        "sk-ABCDEFGH12345678' http://127.0.0.1, action=run"
    )
    deck = tmp_path / "deck.json"
    deck.write_text(json.dumps([
        {"ts": str(now - 500), "tool": "shell_session", "args": cmd_build,
         "status": "error"},
        {"ts": str(now - 400), "tool": "shell_session", "args": cmd_build,
         "status": "done"},
        {"ts": str(now - 300), "tool": "shell_session", "args": cmd_test,
         "status": "done"},
        {"ts": str(now - 200), "tool": "shell_session", "args": cmd_test,
         "status": "done"},
        {"ts": str(now - 100), "tool": "shell_session", "args": cmd_test,
         "status": "done"},
        {"ts": str(now - 50), "tool": "shell_session", "args": cmd_secret,
         "status": "done"},
        {"ts": str(now - 45), "tool": "shell_session", "args": cmd_secret,
         "status": "done"},
        {"ts": str(now - 44), "tool": "shell_session", "args": cmd_secret,
         "status": "done"},
        {"ts": str(now - 40), "tool": "shell_session",
         "args": "command=cd /ruta/vieja && make, action=run",
         "status": "done"},
    ]), encoding="utf-8")

    dry = inst.mine_from_deck(deck_path=deck, now=now, dry_run=True)
    assert dry
    blob = json.dumps(dry, ensure_ascii=False)
    assert "sk-ABCDEFGH12345678" not in blob
    assert "[REDACTED]" in blob
    assert any("dotnet" in c["trigger"] and "falle" in c["trigger"] for c in dry)
    assert any("para shell_session pytest" in c["trigger"] for c in dry)
    assert all(c["scope"] == "project" for c in dry)
    assert all(c["project"] == inst.project_slug(project) for c in dry)

    first = inst.mine_from_deck(deck_path=deck, now=now)
    assert first
    generated = inst.list_instincts(scope="project", project=str(project))
    assert generated
    build_inst = next(
        i for i in generated
        if "dotnet" in i["trigger"] and "falle" in i["trigger"]
    )
    assert build_inst["confidence"] == 0.4
    generated_blob = json.dumps(generated, ensure_ascii=False)
    assert "[REDACTED]" in generated_blob
    assert "sk-ABCDEFGH12345678" not in generated_blob

    # Re-minar el mismo deck no infla la confianza: la evidencia se repite.
    second = inst.mine_from_deck(deck_path=deck, now=now)
    assert second
    again = inst.get_instinct(build_inst["id"])
    assert again["confidence"] == 0.4


def test_mine_if_due_runs_once(isolated, project, tmp_path, monkeypatch):
    now = time.time()
    deck = tmp_path / "deck.json"
    deck.write_text(json.dumps([
        {"ts": str(now - 100), "tool": "shell_session",
         "args": f"command=cd {project} && pytest -q, action=run",
         "status": "done"},
        {"ts": str(now - 90), "tool": "shell_session",
         "args": f"command=cd {project} && pytest -q, action=run",
         "status": "done"},
        {"ts": str(now - 80), "tool": "shell_session",
         "args": f"command=cd {project} && pytest -q, action=run",
         "status": "done"},
    ]), encoding="utf-8")
    monkeypatch.setattr(inst, "DECK_FILE", deck)

    assert inst.mine_if_due(now=now) > 0
    assert (isolated / ".mine_stamp").exists()
    assert inst.mine_if_due(now=now + 60) == 0
    assert inst.mine_if_due(now=now + inst.MINE_INTERVAL_S + 1) >= 0


def test_corrupt_yaml_is_quarantined(isolated):
    path = isolated / "global.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(":::: [no es yaml", encoding="utf-8")

    assert inst.list_instincts(scope="global") == []
    assert list(isolated.glob("global.yaml.corrupt-*"))

    item = _add()
    assert item is not None
    assert inst.list_instincts(scope="global")[0]["id"] == item["id"]


def test_lock_fallback_without_fcntl(isolated, monkeypatch):
    monkeypatch.setitem(sys.modules, "fcntl", None)
    item = _add(trigger="cuando no haya fcntl", action="usar el lock de proceso")
    assert item is not None
    assert inst.get_instinct(item["id"]) is not None


def test_context_builder_injects(isolated, project, monkeypatch):
    from core.context_builder import _instincts_block

    class Shared:
        project_root = str(project)

    class Host:
        _convo_ctx = ["Usuario: no declares listo sin probar"]
        _shared = Shared()

    captured = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return "[INSTINTOS APRENDIDOS]\n- (0.9) X → Y"

    monkeypatch.setattr(inst, "instinct_block", fake)
    assert _instincts_block(Host()).startswith("[INSTINTOS APRENDIDOS]")
    assert captured["project"] == str(project)
    assert captured["user_text"] == "no declares listo sin probar"

    def boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(inst, "instinct_block", boom)
    assert _instincts_block(Host()) == ""
    assert _instincts_block(None) == ""


def test_build_system_prompt_includes_block(isolated, monkeypatch):
    import core.context_builder as cb

    monkeypatch.setattr(cb, "_instincts_block",
                        lambda host=None: "[INSTINTOS APRENDIDOS]\n- (0.9) prueba")
    text = cb.build_system_prompt(None)
    assert "[INSTINTOS APRENDIDOS]" in text
