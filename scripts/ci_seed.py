#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ci_seed.py — Crea los archivos de datos mínimos que test_all.py exige y que
están fuera del repo por .gitignore. Pensado para CI (clon fresco).

No sobreescribe archivos existentes.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

_SEEDS = {
    "memory/long_term.json": {},
    "memory/episodic.json": [],
    "memory/semantic.json": {},
    "memory/neuro_spheres_state.json": {},
    "config/api_keys.json": {},
}


def main() -> int:
    created = []
    for rel, payload in _SEEDS.items():
        path = BASE / rel
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        created.append(rel)

    if created:
        print(f"[ci_seed] creados: {created}")
    else:
        print("[ci_seed] nada que crear (todo existe)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
