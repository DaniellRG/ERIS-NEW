# -*- coding: utf-8 -*-
"""
predict_analyze.py — Analisis predictivo de datos (numpy puro).
Analiza una lista de valores o un CSV y da media, tendencia y proyeccion.
Acciones: analyze (values), csv (path+column), help.
"""
from __future__ import annotations
from pathlib import Path


def _linear_forecast(values: list) -> tuple:
    import numpy as np
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    trend = "creciente" if slope > 0 else "decreciente" if slope < 0 else "estable"
    next_val = float(intercept + slope * len(values))
    return trend, round(float(slope), 4), round(next_val, 2)


def predict_analyze(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "analyze").lower()
    import numpy as np

    if action == "analyze":
        values = parameters.get("values") or parameters.get("data") or []
        if isinstance(values, str):
            values = [float(v.strip()) for v in values.replace(";", ",").split(",") if v.strip()]
        if not isinstance(values, list) or not values:
            return "Error: se requiere 'values' (lista de numeros), ej: [10,12,11,15,18]."
        try:
            values = [float(v) for v in values]
        except (TypeError, ValueError):
            return "Error: 'values' debe ser una lista de numeros."
        if len(values) < 2:
            return "Se necesitan al menos 2 valores para analizar."
        arr = np.array(values)
        trend, slope, nxt = _linear_forecast(values)
        lines = [
            "ANALISIS PREDICTIVO",
            f"  Valores: {values}",
            f"  Media: {arr.mean():.2f} | Min: {arr.min()} | Max: {arr.max()}",
            f"  Desviacion: {arr.std():.2f}",
            f"  Tendencia: {trend} (pendiente {slope})",
            f"  Proyeccion siguiente valor: {nxt}",
        ]
        return "\n".join(lines)

    if action == "csv":
        path = Path(parameters.get("path") or parameters.get("file") or "").expanduser()
        column = (parameters.get("column") or "").strip()
        if not path.exists():
            return f"Archivo no encontrado: {path}"
        try:
            import csv
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            return f"Error leyendo CSV: {e}"
        if not rows:
            return "El CSV no tiene filas."
        if column:
            values = []
            for r in rows:
                try:
                    values.append(float(r.get(column, "")))
                except (TypeError, ValueError):
                    continue
            if len(values) < 2:
                return f"No hay suficientes valores numericos en la columna '{column}'."
            trend, slope, nxt = _linear_forecast(values)
            arr = np.array(values)
            return (
                f"CSV: {path.name} | Columna '{column}' ({len(values)} valores)\n"
                f"  Media: {arr.mean():.2f} | Tendencia: {trend} | Proyeccion: {nxt}"
            )
        lines = [f"CSV: {path.name} ({len(rows)} filas) | Columnas: {list(rows[0].keys())}"]
        return "\n".join(lines)

    return "Acciones: analyze (values), csv (path+column)."
