"""Instintos con confianza (Fase B).

Un instinto es una regla atómica `trigger -> acción` con evidencia y una
confianza de 0.1 a 0.9. Se alimenta de:

- correcciones del usuario (capturadas desde `main.py:_remember`),
- patrones minados de `data/command_deck.json` (fallo -> éxito y familias de
  comandos repetidas),
- altas manuales por CLI.

Se inyecta en el system prompt como `[INSTINTOS APRENDIDOS]` (máx. 5 líneas /
700 caracteres) y nunca lanza hacia afuera: si algo falla, se loguea en
`memory/instincts/instincts.log` y el turno sigue normal.

Uso:
    from core.instincts import observe_user_message, instinct_block
    observe_user_message("Usuario: no declares listo sin probar")
    print(instinct_block())

CLI:
    python -m core.instincts list
    python -m core.instincts add --trigger "..." --action "..." --scope project \
        --project /ruta/al/proyecto
    python -m core.instincts mine --dry-run
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    import yaml
except Exception:  # pragma: no cover - PyYAML es dependencia real
    yaml = None

BASE = Path(__file__).resolve().parent.parent
DEFAULT_STORE = BASE / "memory" / "instincts"
DECK_FILE = BASE / "data" / "command_deck.json"

MIN_CONF = 0.1
MAX_CONF = 0.9
START_CORRECTION = 0.3
START_DECK = 0.4
START_MANUAL = 0.5
REINFORCE_DELTA = 0.10
CONTRADICT_DELTA = 0.15
RETIRE_BELOW = 0.2
RETIRE_MISSES = 2
MATURE_CONF = 0.8
MATURE_HITS = 5
INJECT_MIN_CONF = 0.5
INJECT_LIMIT = 5
INJECT_MAX_CHARS = 700
MINE_MIN_AGE_DAYS = 30
MINE_PAIR_WINDOW_S = 600
MINE_MIN_REPEATS = 3
MINE_INTERVAL_S = 24 * 3600

_LOCK = threading.RLock()
_STORE_OVERRIDE: Optional[Path] = None
_DECK_CACHE: dict[str, Any] = {"ts": 0.0, "value": None}

_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+-[0-9a-f]{6}$")
_KV_RE = re.compile(r"(?:^|, )([A-Za-z_][A-Za-z0-9_]*)=")
_CD_RE = re.compile(
    r"(?:^|&&|;|\|)\s*cd\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s&;|]+))"
)

_WHITELIST = (
    "dotnet", "npm", "npx", "pytest", "python3", "python", "pip", "ruff",
    "mypy", "go", "cargo", "make", "git", "curl", "bash", "sh", "node",
    "docker",
)

_CORRECTION_STRONG = (
    "no es asi", "esta mal", "te equivocaste", "no era eso", "no declares",
    "sin probar", "no inventes", "corregi", "mal ahi", "no funciona asi",
)
_CORRECTION_WEAK = (
    "sino", "tenes que", "debes", "deberias", "en vez de", "lo que pedi",
    "en realidad", "de otra forma",
)
_COURTESY = (
    "no, gracias", "no gracias", "no, esta bien", "no esta bien",
    "no hace falta", "no te preocupes", "no, tranquila", "no pasa nada",
)

_STOPWORDS = set(
    "a al algo algunas algunos ante antes como con contra cual cuando de del "
    "desde donde dos el ella ellas ellos en entre era eres es esa esas ese eso "
    "esos esta estas este esto estos fue ha hasta hay la las le les lo los mas "
    "me mi mis mucho muchos muy nada ni no nos nosotros o os otra otras otro "
    "otros para pero poco por porque que quien quienes se sea ser si sin sobre "
    "son su sus te tiene todo todos tu tus un una uno unos y ya yo".split()
)


# ─────────────────────────────────────────────────────────────────────────────
# Store y locks
# ─────────────────────────────────────────────────────────────────────────────

def set_store_dir(path: os.PathLike | str | None) -> None:
    """Redirige el store (solo tests). `None` vuelve al default/env."""
    global _STORE_OVERRIDE
    _STORE_OVERRIDE = Path(path).expanduser() if path else None


def _store_dir() -> Path:
    if _STORE_OVERRIDE is not None:
        return _STORE_OVERRIDE
    env = os.environ.get("ERIS_INSTINCTS_DIR")
    return Path(env).expanduser() if env else DEFAULT_STORE


def _global_path() -> Path:
    return _store_dir() / "global.yaml"


def _project_path(slug: str) -> Path:
    return _store_dir() / "projects" / f"{_safe_filename(slug)}.yaml"


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "project")) or "project"


def _flock(handle, exclusive: bool) -> None:
    """Lock de archivo portable; si no hay backend, sigue sin lock."""
    try:
        import fcntl  # type: ignore
        fcntl.flock(handle.fileno(),
                    fcntl.LOCK_EX if exclusive else fcntl.LOCK_UN)
        return
    except Exception:
        pass
    try:
        import msvcrt  # type: ignore
        handle.seek(0)
        if exclusive:
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except Exception:
        pass


@contextmanager
def _file_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    handle = open(lock_path, "a+", encoding="utf-8")
    try:
        _flock(handle, True)
        yield
    finally:
        try:
            _flock(handle, False)
        finally:
            handle.close()


def _now_iso(now: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if now is None else now).isoformat(
        timespec="seconds"
    )


def _log(msg: str) -> None:
    try:
        store = _store_dir()
        store.mkdir(parents=True, exist_ok=True)
        log_path = store / "instincts.log"
        if log_path.exists() and log_path.stat().st_size > 256_000:
            try:
                log_path.replace(log_path.with_suffix(".log.1"))
            except Exception:
                pass
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{_now_iso()}] {msg}\n")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Texto / evidencia
# ─────────────────────────────────────────────────────────────────────────────

def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: Any) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9]+", _norm(value))
        if len(word) >= 3 and word not in _STOPWORDS
    }


def _jaccard(a: Iterable[str] | str, b: Iterable[str] | str) -> float:
    sa = set(_tokens(a)) if isinstance(a, str) else set(a)
    sb = set(_tokens(b)) if isinstance(b, str) else set(b)
    if not sa or not sb:
        return 0.0
    union = len(sa | sb)
    return len(sa & sb) / union if union else 0.0


def _similarity(a: str, b: str) -> float:
    """Jaccard o contención: castiga menos las correcciones cortas."""
    sa, sb = _tokens(a), _tokens(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    return max(inter / len(sa | sb), inter / min(len(sa), len(sb)))


def _redact(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._\-]+", r"\1[REDACTED]", text)
    text = re.sub(
        r"(?i)((?:password|passwd|token|api[_-]?key|secret)\s*[=:]\s*)"
        r"[^\s,;]+",
        r"\1[REDACTED]",
        text,
    )
    text = re.sub(r"\b(?:sk|gsk|pk|rk)_[A-Za-z0-9_\-]{8,}\b", "[REDACTED]", text)
    text = re.sub(r"\bAIza[0-9A-Za-z_\-]{16,}\b", "[REDACTED]", text)
    text = re.sub(
        r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}\b",
        "[REDACTED]",
        text,
    )
    return text


def _clean_text(value: Any, limit: int = 240) -> str:
    text = _redact(re.sub(r"\s+", " ", str(value or "")).strip())
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _evidence(now: str, kind: str, ref: str, note: Any) -> dict:
    return {
        "ts": now,
        "kind": str(kind or "manual"),
        "ref": str(ref or f"manual:{time.time_ns()}"),
        "note": _clean_text(note, 240),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Proyecto
# ─────────────────────────────────────────────────────────────────────────────

def project_slug(path: os.PathLike | str) -> str:
    """Slug estable `<basename>-<sha1(path)[:6]>` para un directorio real."""
    p = Path(path).expanduser()
    if not p.exists() or not p.is_dir():
        raise ValueError(f"proyecto inválido (no es un directorio): {path}")
    p = p.resolve()
    root = p
    for candidate in (p, *p.parents):
        if (candidate / ".git").exists():
            root = candidate
            break
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", root.name) or "project"
    digest = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:6]
    return f"{name}-{digest}"


def _normalize_project(project: os.PathLike | str | None) -> tuple[str, Optional[str]]:
    if project is None or str(project).strip() == "":
        return "global", None
    raw = str(project).strip()
    if _SLUG_RE.match(raw):
        return "project", raw
    candidate = Path(raw).expanduser()
    if candidate.exists() and candidate.is_dir():
        return "project", project_slug(candidate)
    # Nombre suelto que existe bajo el cwd (comodidad para el CLI).
    local = (Path.cwd() / raw).expanduser()
    if local.exists() and local.is_dir():
        return "project", project_slug(local)
    raise ValueError(
        f"proyecto ambiguo: {raw!r}; pasá un path existente o un slug nombre-6hex"
    )


def _project_from_command(command: str) -> Optional[str]:
    match = _CD_RE.search(command or "")
    if not match:
        return None
    raw = next((g for g in match.groups() if g), "")
    raw = os.path.expanduser(raw.strip().strip("'\""))
    if not raw or not os.path.isabs(raw):
        return None
    try:
        return project_slug(raw)
    except Exception:
        return None


def _current_project(now: float | None = None) -> Optional[str]:
    """Último proyecto real detectado en el deck (cache de 30 s)."""
    stamp = time.time() if now is None else float(now)
    with _LOCK:
        cached_ts = float(_DECK_CACHE.get("ts") or 0.0)
        if stamp - cached_ts < 30.0:
            return _DECK_CACHE.get("value")
    value = None
    try:
        data = json.loads(DECK_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for item in reversed(data):
                kv = _parse_args(str(item.get("args", "")))
                slug = _project_from_command(kv.get("command", ""))
                if slug:
                    value = slug
                    break
    except Exception:
        pass
    with _LOCK:
        _DECK_CACHE["ts"] = stamp
        _DECK_CACHE["value"] = value
    return value


# ─────────────────────────────────────────────────────────────────────────────
# YAML
# ─────────────────────────────────────────────────────────────────────────────

def _empty_doc() -> dict:
    return {"version": 1, "instincts": []}


def _load_path(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        if yaml is None:
            raise RuntimeError("PyYAML no disponible")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data is None:
            return []
        if isinstance(data, list):
            data = {"version": 1, "instincts": data}
        if not isinstance(data, dict) or not isinstance(data.get("instincts"), list):
            raise ValueError("estructura YAML inválida")
        return [i for i in data["instincts"] if isinstance(i, dict)]
    except Exception as exc:
        try:
            backup = path.with_name(f"{path.name}.corrupt-{int(time.time())}")
            path.replace(backup)
            _log(f"YAML corrupto: {path} -> {backup} ({exc})")
        except Exception:
            _log(f"YAML corrupto sin backup: {path} ({exc})")
        return []


def _save_path(path: Path, instincts: list[dict]) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML no disponible")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{threading.get_ident()}")
    payload = yaml.safe_dump(
        {"version": 1, "instincts": instincts},
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    tmp.write_text(payload, encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass
    os.replace(tmp, path)


def _iter_paths() -> list[Path]:
    store = _store_dir()
    paths = [store / "global.yaml"]
    projects = store / "projects"
    if projects.exists():
        paths.extend(sorted(projects.glob("*.yaml")))
    return paths


# ─────────────────────────────────────────────────────────────────────────────
# Instintos: creación / refuerzo / contradicción
# ─────────────────────────────────────────────────────────────────────────────

def _find_similar(
    items: list[dict], trigger: str, action: str, source: str = "manual",
    dedup_key: str | None = None,
) -> Optional[dict]:
    best = None
    best_score = 0.0
    for item in items:
        if item.get("status") != "active":
            continue
        # Clave exacta para instintos minados: evita fusionar familias
        # distintas que comparten path/plantilla (dotnet vs pytest, etc.).
        if dedup_key:
            if str(item.get("dedup_key") or "") == dedup_key:
                return item
            continue
        if item.get("dedup_key"):
            continue
        combined = _similarity(
            f"{trigger} {action}",
            f"{item.get('trigger', '')} {item.get('action', '')}",
        )
        # Las correcciones llevan el contexto de la última respuesta en el
        # trigger; para que una repetición refuerce, comparamos también la
        # acción sola. En manual exigimos trigger+acción.
        if source == "correction":
            score = max(combined, _similarity(action, str(item.get("action", ""))))
        else:
            score = combined
        if score >= 0.6 and score > best_score:
            best, best_score = item, score
    return best


def _new_instinct(
    trigger: str,
    action: str,
    scope: str,
    project: Optional[str],
    confidence: float,
    source: str,
    evidence: list[dict],
    dedup_key: str | None = None,
) -> dict:
    now = _now_iso()
    conf = round(min(MAX_CONF, max(MIN_CONF, float(confidence))), 2)
    inst = {
        "id": f"inst_{datetime.now():%Y%m%d}_{secrets.token_hex(3)}",
        "trigger": _clean_text(trigger, 240),
        "action": _clean_text(action, 240),
        "confidence": conf,
        "hits": 1,
        "misses": 0,
        "mature": False,
        "scope": scope,
        "project": project if scope == "project" else None,
        "status": "active",
        "source": source,
        "created": now,
        "updated": now,
        "last_seen": now,
        "evidence": evidence[-10:],
    }
    if dedup_key:
        inst["dedup_key"] = str(dedup_key)
    return inst


def _normalize_evidence(
    raw: Any, kind: str, ref: str, note: Any, now: str
) -> list[dict]:
    entries: list[dict] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                entries.append(
                    _evidence(
                        str(item.get("ts") or now),
                        str(item.get("kind") or kind),
                        str(item.get("ref") or ref),
                        item.get("note", ""),
                    )
                )
            elif str(item).strip():
                entries.append(_evidence(now, kind, ref, item))
    elif raw:
        entries.append(_evidence(now, kind, ref, raw))
    if not entries:
        entries.append(_evidence(now, kind, ref, note))
    return entries[-10:]


def _apply_reinforce(
    inst: dict, note: Any, kind: str, ref: str, now: str
) -> dict:
    evidence = list(inst.get("evidence") or [])
    if ref and any(
        str(e.get("kind")) == kind and str(e.get("ref")) == ref for e in evidence
    ):
        return inst
    evidence.append(_evidence(now, kind, ref, note))
    inst["evidence"] = evidence[-10:]
    inst["confidence"] = round(
        min(MAX_CONF, float(inst.get("confidence", MIN_CONF)) + REINFORCE_DELTA), 2
    )
    inst["hits"] = int(inst.get("hits", 0)) + 1
    if inst.get("status") == "retired":
        inst["status"] = "active"
        inst["misses"] = 0
    inst["last_seen"] = now
    inst["updated"] = now
    inst["mature"] = (
        float(inst["confidence"]) >= MATURE_CONF
        and int(inst["hits"]) >= MATURE_HITS
    )
    return inst


def _apply_contradict(
    inst: dict, note: Any, kind: str, ref: str, now: str
) -> dict:
    evidence = list(inst.get("evidence") or [])
    if ref and any(
        str(e.get("kind")) == kind and str(e.get("ref")) == ref for e in evidence
    ):
        return inst
    evidence.append(_evidence(now, kind, ref, note))
    inst["evidence"] = evidence[-10:]
    inst["confidence"] = round(
        max(MIN_CONF, float(inst.get("confidence", MIN_CONF)) - CONTRADICT_DELTA), 2
    )
    inst["misses"] = int(inst.get("misses", 0)) + 1
    inst["mature"] = False
    inst["last_seen"] = now
    inst["updated"] = now
    if (
        float(inst["confidence"]) < RETIRE_BELOW
        or int(inst["misses"]) >= RETIRE_MISSES
    ):
        inst["status"] = "retired"
    return inst


def add_instinct(
    trigger: str,
    action: str,
    scope: str = "global",
    project: os.PathLike | str | None = None,
    confidence: float = START_MANUAL,
    evidence: Any = None,
    source: str = "manual",
    dedup_key: str | None = None,
) -> Optional[dict]:
    """Crea (o refuerza, si es similar) un instinto. Devuelve el dict o None."""
    try:
        trigger = _clean_text(trigger, 240)
        action = _clean_text(action, 240)
        if not trigger or not action:
            _log("add_instinct: trigger/action vacíos")
            return None
        if scope not in ("global", "project"):
            _log(f"add_instinct: scope inválido {scope!r}")
            return None
        if scope == "project":
            scope, project = _normalize_project(project)
        else:
            scope, project = "global", None
        path = _global_path() if scope == "global" else _project_path(str(project))
        now = _now_iso()
        ref = f"manual:{time.time_ns()}"
        entries = _normalize_evidence(evidence, source, ref, trigger, now)
        dedup_ref = str(entries[0].get("ref") or ref)
        with _LOCK:
            with _file_lock(path):
                items = _load_path(path)
                existing = _find_similar(items, trigger, action, source, dedup_key)
                if existing is not None:
                    _apply_reinforce(existing, trigger, source, dedup_ref, now)
                    _save_path(path, items)
                    return existing
                inst = _new_instinct(
                    trigger, action, scope, project, confidence, source, entries,
                    dedup_key,
                )
                items.append(inst)
                _save_path(path, items)
                return inst
    except Exception as exc:
        _log(f"add_instinct: {exc}")
        return None


def observe_user_message(
    text: str,
    last_response: str = "",
    project: os.PathLike | str | None = None,
) -> Optional[dict]:
    """Detecta una corrección del usuario y la graba/refuerza. Sin LLM."""
    try:
        raw = str(text or "").strip()
        if raw.startswith("Usuario: "):
            raw = raw[len("Usuario: "):].strip()
        if not raw or raw.startswith("ERIS:"):
            return None
        if not _is_correction(raw):
            return None
        action = _extract_action(raw)
        trigger = _extract_trigger(raw, last_response)
        if not action:
            return None
        candidates: list[Any] = []
        if project is not None:
            candidates.append(project)
        candidates.append(_current_project())
        scope, slug = "global", None
        for candidate in candidates:
            if not candidate:
                continue
            try:
                scope, slug = _normalize_project(candidate)
                break
            except ValueError as exc:
                _log(f"observe_user_message: {exc}")
        path = _global_path() if scope == "global" else _project_path(str(slug))
        now = _now_iso()
        ref = f"chat:{time.time_ns()}"
        evidence = [_evidence(now, "correction", ref, raw)]
        with _LOCK:
            with _file_lock(path):
                items = _load_path(path)
                existing = _find_similar(items, trigger, action, "correction")
                if existing is not None:
                    _apply_reinforce(existing, raw, "correction", ref, now)
                    _save_path(path, items)
                    return existing
                inst = _new_instinct(
                    trigger, action, scope, slug, START_CORRECTION,
                    "correction", evidence,
                )
                items.append(inst)
                _save_path(path, items)
                return inst
    except Exception as exc:
        _log(f"observe_user_message: {exc}")
        return None


def _is_correction(text: str) -> bool:
    norm = _norm(text)
    if len(norm) < 12:
        return False
    if any(cue in norm for cue in _COURTESY):
        return False
    if any(cue in norm for cue in _CORRECTION_STRONG):
        return True
    return norm.startswith("no,") and any(cue in norm for cue in _CORRECTION_WEAK)


def _extract_action(text: str) -> str:
    match = re.search(r"(?i)\bsino\b\s*(.+)", text)
    return _clean_text(match.group(1) if match else text, 240)


def _extract_trigger(text: str, last_response: str) -> str:
    last = _clean_text(last_response, 120)
    if last.startswith("ERIS:"):
        last = last[len("ERIS:"):].strip()
    if last:
        return _clean_text(f"cuando el usuario corrija algo como: {last}", 240)
    return "cuando el usuario corrija algo similar"


def _locate(instinct_id: str) -> tuple[Optional[Path], Optional[dict]]:
    for path in _iter_paths():
        for item in _load_path(path):
            if str(item.get("id")) == str(instinct_id):
                return path, item
    return None, None


def reinforce(
    instinct_id: str, note: str = "", kind: str = "manual", ref: str = ""
) -> Optional[dict]:
    try:
        path, inst = _locate(instinct_id)
        if path is None or inst is None:
            return None
        now = _now_iso()
        ref = ref or f"manual:{time.time_ns()}"
        with _LOCK:
            with _file_lock(path):
                items = _load_path(path)
                target = next(
                    (i for i in items if str(i.get("id")) == str(instinct_id)),
                    None,
                )
                if target is None:
                    return None
                _apply_reinforce(target, note or "refuerzo manual", kind, ref, now)
                _save_path(path, items)
                return target
    except Exception as exc:
        _log(f"reinforce: {exc}")
        return None


def contradict(
    instinct_id: str, note: str = "", kind: str = "manual", ref: str = ""
) -> Optional[dict]:
    try:
        path, inst = _locate(instinct_id)
        if path is None or inst is None:
            return None
        now = _now_iso()
        ref = ref or f"manual:{time.time_ns()}"
        with _LOCK:
            with _file_lock(path):
                items = _load_path(path)
                target = next(
                    (i for i in items if str(i.get("id")) == str(instinct_id)),
                    None,
                )
                if target is None:
                    return None
                _apply_contradict(
                    target, note or "contradicción manual", kind, ref, now
                )
                _save_path(path, items)
                return target
    except Exception as exc:
        _log(f"contradict: {exc}")
        return None


def retire(instinct_id: str, reason: str = "") -> Optional[dict]:
    try:
        path, inst = _locate(instinct_id)
        if path is None or inst is None:
            return None
        now = _now_iso()
        with _LOCK:
            with _file_lock(path):
                items = _load_path(path)
                target = next(
                    (i for i in items if str(i.get("id")) == str(instinct_id)),
                    None,
                )
                if target is None:
                    return None
                target["status"] = "retired"
                target["updated"] = now
                target["evidence"] = (
                    list(target.get("evidence") or [])
                    + [_evidence(now, "manual", f"manual:{time.time_ns()}",
                                 reason or "retirado manualmente")]
                )[-10:]
                _save_path(path, items)
                return target
    except Exception as exc:
        _log(f"retire: {exc}")
        return None


def list_instincts(
    scope: str | None = None,
    project: os.PathLike | str | None = None,
    include_retired: bool = False,
) -> list[dict]:
    try:
        items: list[dict] = []
        if scope in (None, "global"):
            items.extend(_load_path(_global_path()))
        if scope in (None, "project"):
            slug = None
            if project is not None:
                try:
                    _, slug = _normalize_project(project)
                except ValueError as exc:
                    _log(f"list_instincts: {exc}")
                    slug = _current_project()
            else:
                slug = _current_project()
            if slug:
                items.extend(_load_path(_project_path(slug)))
        seen: set[str] = set()
        out: list[dict] = []
        for item in items:
            iid = str(item.get("id", ""))
            if not iid or iid in seen:
                continue
            seen.add(iid)
            if not include_retired and item.get("status") != "active":
                continue
            out.append(item)
        out.sort(
            key=lambda i: (float(i.get("confidence", 0)),
                           str(i.get("updated", ""))),
            reverse=True,
        )
        return out
    except Exception as exc:
        _log(f"list_instincts: {exc}")
        return []


def get_instinct(instinct_id: str) -> Optional[dict]:
    try:
        _, inst = _locate(instinct_id)
        return inst
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Inyección en el prompt
# ─────────────────────────────────────────────────────────────────────────────

def _recency(updated: Any, now: float) -> float:
    try:
        ts = datetime.fromisoformat(str(updated)).timestamp()
        days = max(0.0, (now - ts) / 86400.0)
        return max(0.0, 1.0 - days / 30.0)
    except Exception:
        return 0.0


def _match_score(query: str, inst: dict) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    return max(
        _jaccard(q, _tokens(inst.get("trigger", ""))),
        _jaccard(q, _tokens(inst.get("action", ""))),
    )


def instinct_block(
    project: os.PathLike | str | None = None,
    user_text: str = "",
    limit: int = INJECT_LIMIT,
) -> str:
    try:
        limit = max(0, min(int(limit), 10))
        if limit == 0:
            return ""
        items = [
            i for i in list_instincts(scope=None, project=project)
            if float(i.get("confidence", 0)) >= INJECT_MIN_CONF
        ]
        if not items:
            return ""
        now = time.time()
        scored = [
            (
                float(i.get("confidence", 0))
                + 0.2 * _match_score(user_text, i)
                + 0.1 * _recency(i.get("updated"), now),
                float(i.get("confidence", 0)),
                i,
            )
            for i in items
        ]
        scored.sort(key=lambda t: (t[0], t[1], str(t[2].get("id", ""))),
                     reverse=True)
        header = "[INSTINTOS APRENDIDOS]"
        lines: list[str] = []
        for _score, conf, inst in scored:
            trigger = _clean_text(inst.get("trigger", ""), 120)
            action = _clean_text(inst.get("action", ""), 160)
            if not trigger or not action:
                continue
            line = f"- ({conf:.1f}) {trigger} → {action}"
            if len(line) > 240:
                line = line[:237].rstrip() + "..."
            if line in lines:
                continue
            current = "\n".join([header] + lines)
            if len(current) + 1 + len(line) > INJECT_MAX_CHARS:
                room = INJECT_MAX_CHARS - len(current) - 1
                if room < 40:
                    break
                line = line[: max(0, room - 3)].rstrip() + "..."
                if len(current) + 1 + len(line) > INJECT_MAX_CHARS:
                    break
            lines.append(line)
            if len(lines) >= limit:
                break
        return "\n".join([header] + lines) if lines else ""
    except Exception as exc:
        _log(f"instinct_block: {exc}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Minado del deck
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args(args: str) -> dict[str, str]:
    text = str(args or "")
    matches = list(_KV_RE.finditer(text))
    out: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        out[match.group(1)] = text[start:end].rstrip(", ")
    return out


def _family(command: str, tool: str) -> str:
    if not command:
        return tool or "?"
    low = command.lower()
    for name in _WHITELIST:
        if re.search(rf"(?:^|[\s/;&|]){re.escape(name)}(?:\s|$)", low):
            return name
    for part in re.split(r"&&|;|\|", command):
        token = part.strip().split()[0] if part.strip() else ""
        token = token.strip("'\"")
        if token and token not in ("cd", "export", "sudo"):
            return _safe_filename(Path(token).name)
    return tool or "?"


def _mine_candidates(deck_path: Path, now: float) -> list[dict]:
    try:
        data = json.loads(deck_path.read_text(encoding="utf-8"))
    except Exception as exc:
        _log(f"mine: no se pudo leer {deck_path} ({exc})")
        return []
    if not isinstance(data, list):
        return []
    cutoff = now - MINE_MIN_AGE_DAYS * 86400
    parsed: list[dict] = []
    for item in data:
        try:
            ts = float(item.get("ts") or 0)
        except Exception:
            continue
        if ts < cutoff or ts > now + 3600:
            continue
        status = str(item.get("status", "")).lower()
        if status not in ("done", "error"):
            continue
        kv = _parse_args(str(item.get("args", "")))
        command = kv.get("command", "")
        tool = str(item.get("tool", ""))
        parsed.append(
            {
                "ts": ts,
                "tool": tool,
                "status": status,
                "family": _family(command, tool),
                "project": _project_from_command(command),
                "snippet": _clean_text(command or str(item.get("args", "")), 160),
            }
        )
    parsed.sort(key=lambda x: x["ts"])

    candidates: list[dict] = []
    seen: set[tuple] = set()
    fixed_groups: set[tuple] = set()

    for idx, err in enumerate(parsed):
        if err["status"] != "error":
            continue
        for ok in parsed[idx + 1:]:
            if ok["ts"] - err["ts"] > MINE_PAIR_WINDOW_S:
                break
            if ok["status"] != "done":
                continue
            key = (err["project"], err["tool"], err["family"])
            if (ok["project"], ok["tool"], ok["family"]) != key:
                continue
            if key in fixed_groups:
                break
            fixed_groups.add(key)
            where = f" en {err['project']}" if err["project"] else ""
            trigger = f"cuando {err['tool']} {err['family']} falle{where}"
            action = (
                "revisar el error y reintentar con el comando que funcionó: "
                f"{ok['snippet']}"
            )
            ev = [
                _evidence(_now_iso(err["ts"]), "deck", f"deck:{err['ts']:.0f}",
                          err["snippet"]),
                _evidence(_now_iso(ok["ts"]), "deck", f"deck:{ok['ts']:.0f}",
                          ok["snippet"]),
            ]
            cand = {
                "trigger": _clean_text(trigger, 240),
                "action": _clean_text(action, 240),
                "confidence": START_DECK,
                "scope": "project" if err["project"] else "global",
                "project": err["project"],
                "source": "deck",
                "evidence": ev,
                "dedup_key": (
                    f"deck:{err['project'] or 'global'}:{err['tool']}:"
                    f"{err['family']}"
                ),
            }
            sig = (cand["trigger"], cand["action"])
            if sig not in seen:
                seen.add(sig)
                candidates.append(cand)
            break

    groups: dict[tuple, list[dict]] = {}
    for item in parsed:
        if item["status"] == "done":
            groups.setdefault(
                (item["project"], item["tool"], item["family"]), []
            ).append(item)
    for (project, tool, family), entries in groups.items():
        if len(entries) < MINE_MIN_REPEATS:
            continue
        if (project, tool, family) in fixed_groups:
            continue
        latest = entries[-1]
        where = f" en {project}" if project else ""
        trigger = f"para {tool} {family}{where}"
        action = f"usar el comando que ya funcionó: {latest['snippet']}"
        cand = {
            "trigger": _clean_text(trigger, 240),
            "action": _clean_text(action, 240),
            "confidence": START_DECK,
            "scope": "project" if project else "global",
            "project": project,
            "source": "deck",
            "evidence": [
                _evidence(_now_iso(latest["ts"]), "deck",
                          f"deck:{latest['ts']:.0f}", latest["snippet"])
            ],
            "dedup_key": f"deck:{project or 'global'}:{tool}:{family}",
        }
        sig = (cand["trigger"], cand["action"])
        if sig not in seen:
            seen.add(sig)
            candidates.append(cand)
    return candidates


def mine_from_deck(
    deck_path: os.PathLike | str | None = None,
    dry_run: bool = False,
    now: float | None = None,
) -> list[dict]:
    try:
        now = float(now if now is not None else time.time())
        path = Path(deck_path).expanduser() if deck_path else DECK_FILE
        candidates = _mine_candidates(path, now)
        if dry_run:
            return candidates
        out: list[dict] = []
        for cand in candidates:
            inst = add_instinct(
                cand["trigger"],
                cand["action"],
                scope=cand["scope"],
                project=cand.get("project"),
                confidence=cand["confidence"],
                evidence=cand.get("evidence"),
                source="deck",
                dedup_key=cand.get("dedup_key"),
            )
            if inst:
                out.append(inst)
        _log(f"mine: {len(out)} instintos desde {path}")
        return out
    except Exception as exc:
        _log(f"mine_from_deck: {exc}")
        return []


def mine_if_due(now: float | None = None) -> int:
    try:
        now = float(now if now is not None else time.time())
        store = _store_dir()
        store.mkdir(parents=True, exist_ok=True)
        stamp = store / ".mine_stamp"
        with _LOCK:
            try:
                last = float(stamp.read_text(encoding="utf-8").strip())
            except Exception:
                last = 0.0
            if now - last < MINE_INTERVAL_S:
                return 0
            stamp.write_text(str(now), encoding="utf-8")
        return len(mine_from_deck(now=now))
    except Exception as exc:
        _log(f"mine_if_due: {exc}")
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="core.instincts")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="crear un instinto")
    p_add.add_argument("--trigger", required=True)
    p_add.add_argument("--action", required=True)
    p_add.add_argument("--scope", choices=["global", "project"], default="global")
    p_add.add_argument("--project", default=None)
    p_add.add_argument("--confidence", type=float, default=START_MANUAL)

    p_list = sub.add_parser("list", help="listar instintos")
    p_list.add_argument("--scope", choices=["global", "project"], default=None)
    p_list.add_argument("--project", default=None)
    p_list.add_argument("--all", action="store_true", help="incluir retirados")

    p_show = sub.add_parser("show", help="ver un instinto")
    p_show.add_argument("id")

    p_re = sub.add_parser("reinforce", help="subir confianza")
    p_re.add_argument("id")
    p_re.add_argument("--note", default="")
    p_re.add_argument("--ref", default="")

    p_con = sub.add_parser("contradict", help="bajar confianza")
    p_con.add_argument("id")
    p_con.add_argument("--note", default="")
    p_con.add_argument("--ref", default="")

    p_ret = sub.add_parser("retire", help="retirar")
    p_ret.add_argument("id")
    p_ret.add_argument("--reason", default="")

    p_mine = sub.add_parser("mine", help="minar el deck")
    p_mine.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "add":
        inst = add_instinct(
            args.trigger, args.action, scope=args.scope,
            project=args.project, confidence=args.confidence, source="manual",
        )
        if inst is None:
            print("ERROR: no se pudo crear el instinto "
                  "(trigger/acción vacíos o proyecto inválido)")
            return 1
        _print_json(inst)
        return 0
    if args.cmd == "list":
        _print_json(list_instincts(
            scope=args.scope, project=args.project,
            include_retired=bool(args.all),
        ))
        return 0
    if args.cmd == "show":
        inst = get_instinct(args.id)
        if inst is None:
            print(f"ERROR: no existe {args.id}")
            return 1
        _print_json(inst)
        return 0
    if args.cmd == "reinforce":
        inst = reinforce(args.id, note=args.note, ref=args.ref)
        if inst is None:
            print(f"ERROR: no existe {args.id}")
            return 1
        _print_json(inst)
        return 0
    if args.cmd == "contradict":
        inst = contradict(args.id, note=args.note, ref=args.ref)
        if inst is None:
            print(f"ERROR: no existe {args.id}")
            return 1
        _print_json(inst)
        return 0
    if args.cmd == "retire":
        inst = retire(args.id, reason=args.reason)
        if inst is None:
            print(f"ERROR: no existe {args.id}")
            return 1
        _print_json(inst)
        return 0
    if args.cmd == "mine":
        _print_json(mine_from_deck(dry_run=bool(args.dry_run)))
        return 0
    return 2


__all__ = [
    "add_instinct", "observe_user_message", "reinforce", "contradict",
    "retire", "list_instincts", "get_instinct", "instinct_block",
    "mine_from_deck", "mine_if_due", "project_slug", "set_store_dir",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
