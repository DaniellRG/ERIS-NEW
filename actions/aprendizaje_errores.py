# -*- coding: utf-8 -*-
from core.aprendizaje_errores import aprendizaje_errores


def aprendizaje_errores_action(params=None, player=None):
    try:
        return aprendizaje_errores(params or {})
    except Exception as e:
        return f"Error en aprendizaje_errores: {e}"
