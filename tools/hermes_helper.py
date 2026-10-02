#!/usr/bin/env python3
"""hermes_helper.py — CLI helper documentado por AGENTS.md.

Flags: "pregunta", --task, --status, --compartir, --estado-real, --sesion
"""
import sys
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import argparse


def main():
    p = argparse.ArgumentParser(description="Hermes CLI helper")
    p.add_argument("pregunta", nargs="?")
    p.add_argument("--task")
    p.add_argument("--status", action="store_true")
    p.add_argument("--compartir")
    p.add_argument("--estado-real")
    p.add_argument("--sesion")
    args = p.parse_args()

    if args.status:
        try:
            import core.hermes_bridge as hb
            print("bridge_up=" + str(hb.bridge_up()) + " port=" + str(hb._PORT))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
        return 0
    if args.task:
        try:
            import core.hermes_bridge as hb
            r = hb.enviar_a_hermes(args.task)
            print(json.dumps(r))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
        return 0
    if args.pregunta:
        try:
            import core.hermes_bridge as hb
            r = hb.consultar_a_hermes(args.pregunta)
            print(json.dumps(r))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
        return 0
    print(json.dumps({"status": "ok", "helper": "hermes_helper"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
