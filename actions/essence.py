# -*- coding: utf-8 -*-
from core.essence import essence_action

def essence(params=None):
    try:
        return essence_action(params or {})
    except Exception as e:
        return f"Error en essence: {e}"
