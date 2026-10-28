# -*- coding: utf-8 -*-
from core.lesson_applier import lesson_applier

def lesson_applier_action(params=None):
    try:
        return lesson_applier(params or {})
    except Exception as e:
        return f"Error: {e}"
