#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — Vuelve a generar core/prompt.txt a partir de las secciones modulares
en core/prompts/ (fuente de verdad: ORDER.txt + *.md).

Uso:
    python core/prompts/build.py
"""
from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE.parent / "prompt.txt"


def build() -> str:
    order_path = BASE / "ORDER.txt"
    order = [
        ln.strip()
        for ln in order_path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    parts = []
    for name in order:
        # Concatenar tal cual: cada archivo conserva sus saltos de línea
        # originales del prompt fuente. Sin rstrip ni añadidos, para que la
        # reconstrucción sea byte-a-byte idéntica al prompt.txt original.
        parts.append((BASE / name).read_text(encoding="utf-8"))
    OUT.write_text("".join(parts), encoding="utf-8")
    return OUT.read_text(encoding="utf-8")


if __name__ == "__main__":
    build()
