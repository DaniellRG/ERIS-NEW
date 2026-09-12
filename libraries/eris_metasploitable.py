"""
eris_metasploitable.py — Librería propia creada por Eris.

Utilidades del lab Metasploitable.
Creada: 2026-09-11 22:48
"""
import json


def truncar_shadow(linea):
    """Trunca lineas de /etc/shadow para ver solo usuario:hash."""
    # Implementación de truncar_shadow
    partes = linea.split(":")
    if len(partes) >= 2:
        return {"usuario": partes[0], "hash": partes[1]}
    return {"usuario": None, "hash": None}


def es_backdoor_vsftpd(banner):
    """Indica si un banner FTP es vsftpd 2.3.4."""
    # Implementación de es_backdoor_vsftpd
    b = (banner or "").lower()
    return {"vsftpd_234": "vsftpd 2.3.4" in b}


def resumen_lab(hallazgos):
    """Resumen corto del lab."""
    # Implementación de resumen_lab
    total = len(hallazgos or [])
    return {"total": total}