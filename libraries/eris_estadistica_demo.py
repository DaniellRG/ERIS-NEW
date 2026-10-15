"""
eris_estadistica_demo.py — Librería propia creada por Eris.

utilidades estadísticas basicas
Creada: 2026-10-14 22:27
"""
import json


def mediana(xs):
    """mediana de una lista"""
    # Implementación de mediana
    xs2=sorted(xs); n=len(xs2); return {'mediana': (xs2[n//2] if n%2 else (xs2[n//2-1]+xs2[n//2])/2) if n else None}