#!/usr/bin/env python3
"""eris_askpass.py — Askpass para sudo de ERIS.

Muestra un diálogo gráfico pidiendo la contraseña (en el momento) cuando
Eris ejecuta un comando root. Sigue el protocolo sudo askpass: imprime la
contraseña en stdout; cancela (salida != 0) si el usuario cierra el diálogo.

La contraseña NUNCA se guarda ni se loguea: vive solo en el flujo
sudo->stdout y se descarta al terminar.
"""
import os
import sys


def _dialog_tk():
    try:
        import tkinter as tk
        from tkinter import simpledialog
    except Exception:
        return None
    try:
        root = tk.Tk()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        root.withdraw()
        pw = simpledialog.askstring(
            "ERIS — Permiso de administrador",
            "Eris necesita la contraseña para ejecutar como root:",
            show="*",
            parent=root,
        )
        try:
            root.destroy()
        except Exception:
            pass
        return pw
    except Exception:
        return None


def _dialog_zenity():
    try:
        import subprocess
        r = subprocess.run(
            ["zenity", "--password",
             "--title=ERIS — Permiso de administrador",
             "--text=Eris necesita la contraseña para ejecutar como root:"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            return r.stdout.strip("\n")
        return None
    except Exception:
        return None


def main():
    pw = _dialog_tk()
    if pw is None:
        pw = _dialog_zenity()
    if pw:
        sys.stdout.write(pw + "\n")
        sys.stdout.flush()
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()