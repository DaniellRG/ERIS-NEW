# -*- coding: utf-8 -*-
"""
memory_curation.py — CURADORA DE MEMORIA de ERIS (nativo, sin servicios externos).

Inspirado en el concepto de "memoria gestionada" (un agente que decide qué se
conserva, qué contradice, qué expira y qué se recuerda puntualmente), pero
implementado 100% local y en términos del propio estado de ERIS.

Tres capacidades:

1. POLÍTICAS DE EXPIRACIÓN (forgetting gestionado)
   Retención por tipo + reglas con nombre + preset. Un recuerdo es `active`
   o `expired` (marcado con fecha y regla que lo jubiló). Nada se borra: el
   contenido sobrevive, sale de la inyección marcado [EXPIRED] y se restaura.

2. RECONCILIACIÓN DE CONFLICTOS
   Cuando un hecho nuevo contradice uno previo (misma clave, valor distinto)
   NO se sobreescribe en silencio: ambos quedan versionados y etiquetados para
   revisión. Se resuelven quedándose con el nuevo, el viejo o ambos.

3. RECUERDO PUNTUAL (point-in-time recall)
   Timeline append-only de cambios. `--as-of` reconstruye qué creía ERIS en
   una fecha; `--changed-since` devuelve qué cambió desde entonces (recuerdos
   curados y archivos de memoria tocados).

Datos:
  data/curation_timeline.jsonl  — ledger append-only (eventos)
  data/curation_estate.json     — estado canónico actual (recuerdos curados)
  data/curation_policies.json   — tabla de retención + reglas + presets
  data/curation_snapshots.jsonl — hashes de memory/*.json por fecha
"""
from __future__ import annotations

import hashlib
import json
import re
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

_BASE = Path(__file__).resolve().parent.parent
_TIMELINE = _BASE / "data" / "curation_timeline.jsonl"
_ESTATE_FILE = _BASE / "data" / "curation_estate.json"
_POLICIES_FILE = _BASE / "data" / "curation_policies.json"
_SNAPSHOTS = _BASE / "data" / "curation_snapshots.jsonl"
_MEMORY_DIR = _BASE / "memory"

_lock = threading.Lock()

TIPOS = [
    "instruction", "fact", "decision", "goal", "commitment", "preference",
    "relationship", "context", "event", "learning", "observation",
    "artifact", "error",
]

# Retención por defecto (días) — la tabla que la regla "vence a la tabla".
_DEFAULT_RETENTION = {
    "instruction": None,   # None = nunca expira
    "fact": None,
    "goal": None,
    "preference": None,
    "relationship": None,
    "commitment": 365,
    "decision": 90,
    "learning": 180,
    "context": 7,
    "event": 30,
    "observation": 14,
    "artifact": 90,
    "error": 30,
}

_PRESETS = {
    "conservative": {k: (v * 3 if v else None) for k, v in _DEFAULT_RETENTION.items()},
    "balanced": dict(_DEFAULT_RETENTION),
    "aggressive": {k: (max(1, v // 2) if v else None) for k, v in _DEFAULT_RETENTION.items()},
}


# ─────────────────────────── helpers ───────────────────────────

def _new_id(key: str, ts: str) -> str:
    import uuid as _uuid
    return "mem_" + hashlib.md5(f"{key}:{ts}:{_uuid.uuid4().hex[:8]}".encode()).hexdigest()[:10]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_json(path: Path, default: Any = None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json(path: Path, data) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def _append_event(event: dict):
    try:
        _TIMELINE.parent.mkdir(parents=True, exist_ok=True)
        with _TIMELINE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _load_timeline(max_events: int = 200_000) -> list[dict]:
    if not _TIMELINE.exists():
        return []
    out = []
    with _TIMELINE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out[-max_events:]


def _load_estate() -> list[dict]:
    return _read_json(_ESTATE_FILE, []) or []


def _save_estate(estate: list[dict]) -> bool:
    return _write_json(_ESTATE_FILE, estate)


def _load_policies() -> dict:
    pol = _read_json(_POLICIES_FILE)
    if not isinstance(pol, dict) or "retention" not in pol:
        pol = {
            "preset": "balanced",
            "retention": dict(_DEFAULT_RETENTION),
            "rules": [],
            "purge_expired_after": None,
        }
        _write_json(_POLICIES_FILE, pol)
    return pol


def _dehydrate_record(rec: dict) -> dict:
    return {
        "id": rec.get("id"),
        "key": rec.get("key"),
        "type": rec.get("type", "fact"),
        "text": rec.get("text"),
        "value": rec.get("value"),
        "confidence": rec.get("confidence", 0.7),
    }


def _fmt_dt(iso: Optional[str], fmt: str = "%d/%m/%Y") -> str:
    if not iso:
        return "?"
    try:
        return datetime.fromisoformat(iso).strftime(fmt)
    except Exception:
        return iso[:10]


def _expiry_for(rec: dict, policies: dict) -> Optional[str]:
    retention = policies.get("retention", _DEFAULT_RETENTION)
    created = rec.get("created")
    if not created:
        return None
    try:
        created_dt = datetime.fromisoformat(created)
    except Exception:
        return None
    # Reglas con nombre primero; la primera que matchea gana.
    for rule in policies.get("rules", []):
        match = rule.get("match", {})
        if self_ := (match.get("type") or match.get("key")):
            pass
        tipo = match.get("type")
        if tipo and tipo != rec.get("type"):
            continue
        key = match.get("key")
        if key and key != rec.get("key"):
            continue
        conf = match.get("confidence_below")
        if conf is not None and not (rec.get("confidence", 0) < conf):
            continue
        ea = rule.get("expire_after")
        if ea in (None, "never"):
            return None
        td = _to_timedelta(ea)
        if td is None:
            return None
        return (created_dt + td).isoformat(timespec="seconds")
    days = retention.get(rec.get("type"))
    if not days:
        return None
    return (created_dt + timedelta(days=float(days))).isoformat(timespec="seconds")


def _to_timedelta(spec) -> Optional[timedelta]:
    if spec is None or spec == "never":
        return None
    if isinstance(spec, str):
        m = re.match(r"^\s*(\d+)\s*d\s*$", spec)
        if m:
            return timedelta(days=float(m.group(1)))
        try:
            return timedelta(days=float(spec))
        except Exception:
            return None
    try:
        return timedelta(days=float(spec))
    except Exception:
        return None


def _is_expired(rec: dict) -> bool:
    return rec.get("status") == "expired"


# ─────────────────────────── recordar (core) ───────────────────────────

def record(key: str, text: str, tipo: str = "fact", value: Any = None,
           confidence: float = 0.7, tags: Optional[list] = None,
           source: str = "curator", player=None) -> dict:
    """Crea o actualiza un recuerdo curado. Detecta conflictos, no sobreescribe."""
    key = (key or "").strip()
    text = (text or "").strip()
    if not key:
        return {"ok": False, "error": "Necesito una clave (key)."}
    if not text:
        return {"ok": False, "error": "Necesito el texto del recuerdo."}
    if tipo not in TIPOS:
        return {"ok": False, "error": f"Tipo inválido. Válidos: {', '.join(TIPOS)}"}
    ts = _now()
    with _lock:
        estate = _load_estate()
        prev = next((r for r in estate if r.get("key") == key), None)
        v_norm = str(value) if value is not None else text.lower()
        if prev is not None:
            p_norm = str(prev.get("value")) if prev.get("value") is not None else (prev.get("text") or "").lower()
            conflict = (prev.get("text") or "").strip().lower() != text.lower() and v_norm and p_norm and v_norm != p_norm
            if conflict:
                cid = hashlib.md5(f"{key}:{ts}".encode()).hexdigest()[:8]
                rec = {
                    "id": _new_id(key, ts),
                    "key": key, "type": tipo, "text": text, "value": value,
                    "confidence": float(confidence), "tags": tags or [],
                    "source": source, "created": ts, "updated": ts,
                    "status": "active", "expired_at": None, "expire_reason": None,
                    "expire_rule": None, "needs_review": True,
                }
                estate.append(rec)
                _save_estate(estate)
                _append_event({"ts": ts, "event": "conflict",
                               "id": rec["id"], "key": key, "type": tipo,
                               "prev_text": prev.get("text"), "new_text": text,
                               "prev": _dehydrate_record(prev)})
                return {"ok": True, "conflict": True, "id": rec["id"],
                        "msg": f"Conflicto detectado en '{key}': nueva creencia {tipo} guardada como versión nueva (ambas quedan para revisión)."}
            prev["text"] = text
            prev["value"] = value
            prev["type"] = tipo
            prev["confidence"] = float(confidence)
            prev["tags"] = list(dict.fromkeys((prev.get("tags") or []) + (tags or [])))
            prev["source"] = source
            prev["updated"] = ts
            _save_estate(estate)
            _append_event({"ts": ts, "event": "update", "id": prev["id"], "key": key,
                           "type": tipo, "text": text, "value": value})
            return {"ok": True, "update": True, "id": prev["id"], "msg": f"Recuerdo '{key}' actualizado."}
        rec = {
            "id": _new_id(key, ts),
            "key": key, "type": tipo, "text": text, "value": value,
            "confidence": float(confidence), "tags": tags or [],
            "source": source, "created": ts, "updated": ts,
            "status": "active", "expired_at": None, "expire_reason": None,
            "expire_rule": None, "needs_review": False,
        }
        estate.append(rec)
        _save_estate(estate)
        _append_event({"ts": ts, "event": "record", "id": rec["id"], "key": key,
                       "type": tipo, "text": text, "value": value,
                       "confidence": confidence, "tags": tags or []})
        return {"ok": True, "id": rec["id"], "msg": f"Recuerdo {tipo} '{key}' guardado."}


# ─────────────────────────── recall puntual ───────────────────────────

def estate_changes_since(iso_date: str) -> list[dict]:
    """Recuerdos curados con cambios posteriores a la fecha (--changed-since)."""
    changes = []
    for ev in _load_timeline():
        if ev.get("ts", "") <= iso_date:
            continue
        if ev.get("event") in ("record", "update", "expire", "restore"):
            changes.append(ev)
    return changes


def _files_hash() -> dict:
    """Hashes actuales de memory/*.json (para snapshots y changed_since de archivos)."""
    out = {}
    if not _MEMORY_DIR.exists():
        return out
    for f in sorted(_MEMORY_DIR.glob("*.json")):
        try:
            out[f.name] = hashlib.md5(f.read_bytes()).hexdigest()
        except Exception:
            out[f.name] = "?"
    return out


def files_changed_since(iso_date: str) -> list[str]:
    """Archivos de memory/*.json cuyo contenido cambió desde la fecha."""
    if not _SNAPSHOTS.exists():
        return ["(sin snapshots previos — ejecutá 'snapshot' para empezar a trackear)"]
    snap_ts = None
    snap = {}
    for line in _SNAPSHOTS.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("ts", "") <= iso_date:
            snap_ts, snap = ev.get("ts"), ev.get("hashes", {})
        elif snap_ts is None:
            snap_ts, snap = ev.get("ts"), ev.get("hashes", {})
            break
    if snap_ts is None:
        return ["(no hay snapshot en/antes de esa fecha — ejecutá 'snapshot' para empezar a trackear)"]
    cur = _files_hash()
    changed = [name for name in snap if snap.get(name) and snap.get(name) != cur.get(name)]
    new = [name for name in cur if name not in snap]
    return changed + new


def recall(query: Optional[str] = None, tipo: Optional[str] = None,
           as_of: Optional[str] = None, changed_since: Optional[str] = None,
           include_expired: bool = False, top: Optional[int] = None) -> list[dict]:
    """Recuerdo puntual sobre los recuerdos curados.

    as_of        → reconstruye el estado de qué creía ERIS en esa fecha.
    changed_since→ cambios (record/update/expire/restore) posteriores a esa fecha.
    """
    estate = _load_estate()
    records: list[dict] = list(estate)

    if as_of:
        # Reconstrucción punto-en-tiempo: últimos eventos hasta as_of por id.
        last = {}
        for ev in _load_timeline():
            if ev.get("ts", "") > as_of:
                continue
            eid = ev.get("id")
            if not eid:
                continue
            if ev.get("event") == "record":
                last[eid] = {"id": eid, "key": ev.get("key"), "type": ev.get("type", "fact"),
                             "text": ev.get("text"), "value": ev.get("value"),
                             "confidence": ev.get("confidence", 0.7), "created": ev.get("ts")}
            elif ev.get("event") == "update":
                if eid in last:
                    last[eid].update({"text": ev.get("text"), "value": ev.get("value"),
                                      "type": ev.get("type", last[eid].get("type", "fact"))})
                else:
                    last[eid] = {"id": eid, "key": ev.get("key"), "type": ev.get("type", "fact"),
                                 "text": ev.get("text"), "value": ev.get("value"),
                                 "confidence": 0.7, "created": ev.get("ts")}
            elif ev.get("event") == "restore":
                if eid in last:
                    last[eid]["created"] = ev.get("ts")
            elif ev.get("event") == "expire":
                if eid in last:
                    last[eid]["created"] = "2099-01-01T00:00:00"  # fuera del horizonte = no existía aún
        records = [r for r in last.values() if r.get("created", "") < "2099-01-01"]

    if changed_since:
        ids = {ev.get("id") for ev in estate_changes_since(changed_since) if ev.get("id")}
        if ids:
            records = [r for r in estate if r.get("id") in ids]
        else:
            return []

    if tipo:
        records = [r for r in records if r.get("type") == tipo]
    if not include_expired:
        keep, expired = [], []
        for r in records:
            if _is_expired(r):
                expired.append(r)
            else:
                keep.append(r)
        records = keep
    if query:
        q = (query or "").lower()
        records = [r for r in records if q in (r.get("key") or "").lower()
                   or q in (r.get("text") or "").lower()
                   or any(q in (t or "").lower() for t in (r.get("tags") or []))]
    if top:
        records = records[:top]
    verbose = []
    for r in records:
        copy = dict(r)
        if _is_expired(copy):
            copy["_banner"] = f"[EXPIRED] ({_fmt_dt(copy.get('expired_at'))} — {copy.get('expire_reason')})"
            if include_expired:
                verbose.append(copy)
            continue
        verbose.append(copy)
    return verbose


# ─────────────────────────── expiración (sweep) ───────────────────────────

def expire(rid: str, reason: str = "decisión propia") -> dict:
    with _lock:
        estate = _load_estate()
        rec = next((r for r in estate if r.get("id") == rid), None)
        if not rec:
            return {"ok": False, "error": f"No encontré el recuerdo {rid}."}
        if _is_expired(rec):
            return {"ok": False, "error": "Ya está expirado."}
        ts = _now()
        rec["status"] = "expired"
        rec["expired_at"] = ts
        rec["expire_reason"] = reason
        rec["expire_rule"] = "manual"
        _save_estate(estate)
        _append_event({"ts": ts, "event": "expire", "id": rid, "key": rec.get("key"), "type": rec.get("type"),
                       "reason": reason})
        return {"ok": True, "msg": f"{rec.get('key')} expirado."}


def restore(rid: str) -> dict:
    with _lock:
        estate = _load_estate()
        rec = next((r for r in estate if r.get("id") == rid), None)
        if not rec:
            return {"ok": False, "error": f"No encontré el recuerdo {rid}."}
        if not _is_expired(rec):
            return {"ok": False, "error": "No está expirado."}
        ts = _now()
        rec["status"] = "active"
        rec["expired_at"] = None
        rec["expire_reason"] = None
        rec["expire_rule"] = None
        _save_estate(estate)
        _append_event({"ts": ts, "event": "restore", "id": rid, "key": rec.get("key"), "type": rec.get("type")})
        return {"ok": True, "msg": f"{rec.get('key')} restaurado."}


def run_sweep(dry_run: bool = False) -> dict:
    """Aplica la política de retención. Expira lo que supera su regla, marca con
    fecha + regla. Nada se borra. Con dry_run=True solo lista candidatos."""
    with _lock:
        policies = _load_policies()
        estate = _load_estate()
        now = datetime.now()
        candidates = []
        expired_now = 0
        for rec in estate:
            if _is_expired(rec):
                continue
            due = _expiry_for(rec, policies)
            rule_name = "manual"
            if due:
                try:
                    due_dt = datetime.fromisoformat(due)
                except Exception:
                    continue
                if due_dt <= now:
                    candidates.append((rec, due, rule_name))
            else:
                # Regla "never" o retención None → nunca expira.
                continue
        if dry_run:
            return {"ok": True, "dry": True, "candidates": len(candidates),
                    "lines": [f"  • {r.get('id')} {r.get('key')} ({r.get('type')}) — vence {_fmt_dt(due)}" for r, due, _ in candidates]}
        for rec, due, rule_name in candidates:
            ts = _now()
            rec["status"] = "expired"
            rec["expired_at"] = ts
            rec["expire_reason"] = f"política: vence {_fmt_dt(due)}"
            rec["expire_rule"] = rule_name or "retention"
            expired_now += 1
            _append_event({"ts": ts, "event": "expire", "id": rec.get("id"),
                           "key": rec.get("key"), "type": rec.get("type"),
                           "reason": rec["expire_reason"]})
        _save_estate(estate)
        return {"ok": True, "expired": expired_now,
                "msg": f"Sweep: {expired_now} recuerdos expirados por política (restaurables con 'restore')."}


def set_preset(name: str, force_review: bool = False) -> dict:
    if name not in _PRESETS:
        return {"ok": False, "error": f"Presets: {', '.join(_PRESETS)}"}
    policies = _load_policies()
    policies["preset"] = name
    policies["retention"] = dict(_PRESETS[name])
    _write_json(_POLICIES_FILE, policies)
    if not force_review:
        return {"ok": True, "msg": f"Preset '{name}' aplicado a la tabla de retención (no se ejecutó el sweep)."}
    res = run_sweep()
    return {"ok": True, "msg": f"Preset '{name}' aplicado. {res.get('msg')}"}


# ─────────────────────────── conflictos ───────────────────────────

def list_conflicts() -> list[dict]:
    """Conflictos sin resolver (recuerdos con needs_review o eventos kind=conflict)."""
    conflicted = [r for r in _load_estate() if r.get("needs_review")]
    timeline = [ev for ev in _load_timeline() if ev.get("event") == "conflict"]
    out = []
    for ev in timeline:
        rid = ev.get("id")
        rec = next((r for r in _load_estate() if r.get("id") == rid), None)
        if not rec:
            continue
        out.append({"id": rid, "resolved": not rec.get("needs_review", False),
                    "key": ev.get("key"), "type": ev.get("type"),
                    "prev": ev.get("prev_text"), "new": ev.get("new_text"),
                    "since": ev.get("ts")})
    return out


def resolve_conflict(rid: str, keep: str = "new", player=None) -> dict:
    """Resuelve un conflicto: keep='new' (nueva gana) | 'old' (vieja gana) | 'both'.
    Las dos versiones ya coexisten en el estate; resolver solo decide el estado."""
    if keep not in ("new", "old", "both"):
        return {"ok": False, "error": "keep debe ser new | old | both."}
    with _lock:
        estate = _load_estate()
        tickets = [r for r in estate if r.get("id") == rid]
        if not tickets:
            return {"ok": False, "error": f"Conflicto {rid} no encontrado."}
        target = tickets[0]
        key = target.get("key")
        prev_text = None
        for ev in _load_timeline():
            if ev.get("event") == "conflict" and ev.get("id") == rid:
                prev_text = ev.get("prev_text")
                break
        if keep in ("new", "both"):
            target["needs_review"] = False
        if keep == "old":
            target["needs_review"] = False
            target["status"] = "expired"
            target["expired_at"] = _now()
            target["expire_reason"] = "resuelto: ganó la versión vieja"
            target["expire_rule"] = "conflict-resolution"
        _save_estate(estate)
        _append_event({"ts": _now(), "event": "resolve", "id": rid, "key": key, "keep": keep})
        return {"ok": True, "msg": f"Conflicto '{key}' resuelto manteniendo: {keep}."}


# ─────────────────────────── snapshot de archivos ───────────────────────────

def snapshot_files() -> dict:
    """Snapshot de hashes de memory/*.json en el timeline de snapshots."""
    ts = _now()
    hashes = _files_hash()
    try:
        _SNAPSHOTS.parent.mkdir(parents=True, exist_ok=True)
        with _SNAPSHOTS.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": ts, "hashes": hashes}, ensure_ascii=False) + "\n")
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "ts": ts, "archivos": len(hashes)}


# ─────────────────────────── tool ───────────────────────────

def curar_memoria(parameters: dict = None, player=None) -> str:
    """Tool: CURADORA DE MEMORIA. Políticas de expiración, conflictos y recall puntual."""
    params = parameters or {}
    # Aliases tolerados (el modelo a veces usa add/save/buscar/expirar…)
    _alias = {
        "add": "record", "save": "record", "nuevo": "record", "crear": "record",
        "search": "recall", "buscar": "recall", "conflikts": "conflicts",
        "expirar": "sweep", "expirados": "recall",
        "aplicar_policy": "policy",
    }
    action = str(params.get("action", "status")).lower().strip()
    action = _alias.get(action, action)

    if action == "status":
        estate = _load_estate()
        active = sum(1 for r in estate if not _is_expired(r))
        expired = len(estate) - active
        pending = len([r for r in estate if r.get("needs_review")])
        pol = _load_policies()
        tl = _load_timeline()
        return (f"Curadora de memoria: {len(estate)} recuerdos curados "
                f"({active} activos, {expired} expirados), {pending} conflictos sin resolver. "
                f"Preset de retención: {pol.get('preset', 'balanced')}. "
                f"Timeline: {len(tl)} eventos. Acciones: record, recall, as_of, changed_since, "
                f"sweep, expire, restore, conflicts, resolve, policy, snapshot.")

    # ── recordar / actualizar ──
    if action in ("record", "remember"):
        res = record(params.get("key", ""), params.get("text", ""),
                     params.get("type", "fact"), params.get("value"),
                     float(params.get("confidence", 0.7)), params.get("tags"))
        return res.get("msg", str(res))

    # ── recall puntual general ──
    if action == "recall":
        res = recall(params.get("query"), params.get("type"), None,
                     None, bool(params.get("include_expired")), int(params.get("top", 10)))
        if not res:
            return "Sin recuerdos que matcheen (o lista vacía)."
        lines = ["**Recall (curados):**"]
        for r in res:
            banner = r.pop("_banner", "")
            tag = f" {banner}" if banner else ""
            tags = f" #{' #'.join(r.get('tags') or [])}" if r.get("tags") else ""
            lines.append(f"• [{r.get('type')}] {r.get('key')}{tag}: {str(r.get('text'))[:200]}{tags}")
        return "\n".join(lines)

    # ── qué creía ERIS en tal fecha (--as-of) ──
    if action == "as_of":
        fecha = str(params.get("as_of", "")).strip()
        if not fecha:
            return "Necesito 'as_of' con la fecha (YYYY-MM-DD o ISO)."
        res = recall(as_of=fecha, include_expired=True, top=int(params.get("top", 15)))
        if not res:
            return f"Sin recuerdos curados activos hacia {fecha[:10]}."
        lines = [f"**Qué creía ERIS hacia {fecha[:10]} (point-in-time):**"]
        for r in res:
            lines.append(f"• [{r.get('type')}] {r.get('key')}: {str(r.get('text'))[:200]}")
        return "\n".join(lines)

    # ── qué cambió desde tal fecha (--changed-since) ──
    if action == "changed_since":
        fecha = str(params.get("changed_since", "")).strip()
        if not fecha:
            return "Necesito 'changed_since' con la fecha (YYYY-MM-DD o ISO)."
        evs = estate_changes_since(fecha)
        files = files_changed_since(fecha)
        lines = [f"**Cambios desde {fecha[:10]}:**"]
        if evs:
            for ev in evs[:int(params.get("top", 15))]:
                kind = {"record": "➕ nuevo", "update": "✏️ actualizado", "expire": "⏳ expirado",
                        "restore": "↩️ restaurado"}.get(ev.get("event"), ev.get("event"))
                lines.append(f"• {kind} {ev.get('key')} ({ev.get('type')}) — {_fmt_dt(ev.get('ts'))}")
        else:
            lines.append("• Sin cambios en recuerdos curados.")
        lines.append("**Archivos de memoria tocados:**")
        lines += [f"  – {f}" for f in files[:int(params.get("top", 10))]]
        return "\n".join(lines)

    # ── expiración ──
    if action == "sweep":
        res = run_sweep(dry_run=bool(params.get("dry", False)))
        if res.get("dry"):
            lines = [f"Candidatos a expirar ({res.get('candidates')}):"] + res.get("lines", [])
            return "\n".join(lines) or "Nada por expirar."
        return res.get("msg", str(res))

    if action == "expire":
        res = expire(params.get("id", ""), str(params.get("reason", "decisión propia")))
        return res.get("msg", str(res))

    if action == "restore":
        res = restore(params.get("id", ""))
        return res.get("msg", str(res))

    # ── conflictos ──
    if action == "conflicts":
        conflicts = list_conflicts()
        unresolved = [c for c in conflicts if not c.get("resolved")]
        if not unresolved:
            return "Sin conflictos sin resolver."
        lines = [f"**Conflictos sin resolver ({len(unresolved)}):**"]
        for c in unresolved:
            lines.append(f"• {c['id']} [{c.get('type')}] {c.get('key')} (desde {_fmt_dt(c.get('since'))})")
            lines.append(f"    vieja: {str(c.get('prev'))[:120]}")
            lines.append(f"    nueva: {str(c.get('new'))[:120]}")
        return "\n".join(lines)

    if action == "resolve":
        res = resolve_conflict(params.get("id", ""), str(params.get("keep", "new")))
        return res.get("msg", str(res))

    # ── políticas ──
    if action == "policy":
        pol = _load_policies()
        sub = str(params.get("sub", "show")).lower().strip()
        if sub == "list":
            lines = ["**Presets de retención (días por tipo):**"]
            for name, table in _PRESETS.items():
                short = ", ".join(f"{k}={v if v else '∞'}" for k, v in sorted(table.items()))
                lines.append(f"• {name}: {short}")
            return "\n".join(lines)
        if sub == "apply":
            res = set_preset(str(params.get("preset", "")).strip(),
                             force_review=bool(params.get("sweep", False)))
            return res.get("msg", str(res))
        table = pol.get("retention", {})
        short = ", ".join(f"{k}={v if v else '∞'}" for k, v in sorted(table.items()))
        rules = pol.get("rules", [])
        line_rules = ("; ".join(f"rule {r.get('name')}: {r.get('match')} → {r.get('expire_after')}" for r in rules)
                      if rules else "sin reglas con nombre")
        return (f"Política actual: preset {pol.get('preset', 'balanced')}\n"
                f"Retención: {short}\nReglas: {line_rules}\n"
                f"Stats: {sum(1 for r in _load_estate() if not _is_expired(r))} activos, "
                f"{sum(1 for r in _load_estate() if _is_expired(r))} expirados.")

    if action == "snapshot":
        res = snapshot_files()
        return f"Snapshot de {res.get('archivos', 0)} archivos de memoria guardado ({res.get('ts', '?')})."

    return ("Acciones: status, record (key/text/type), recall (query/type/top), as_of (as_of=YYYY-MM-DD), "
            "changed_since (changed_since=YYYY-MM-DD), sweep (dry=bool), expire (id/reason), restore (id), "
            "conflicts, resolve (id/keep=new|old|both), policy (sub=show|list|apply, preset, sweep), snapshot.")