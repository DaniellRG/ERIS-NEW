"""Gestion del menu contextual de Windows para ERIS."""
import sys
import os
import winreg

ERIS_EXE = sys.executable or "ERIS.exe"
MENU_NAME = "ERIS"
MENU_ICON = ""


def _get_exe_path():
    if getattr(sys, "frozen", False):
        return sys.executable
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "ERIS.exe"),  # build output
        "D:\\Eris_NEW\\ERIS.exe",  # deploy target
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return candidates[0]


HKCR = winreg.HKEY_CURRENT_USER
ROOT = r"Software\Classes"


def _set_reg(sub_path, name, value):
    full = f"{ROOT}\\{sub_path}"
    with winreg.CreateKey(HKCR, full) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def _del_key(sub_path):
    try:
        winreg.DeleteKey(HKCR, f"{ROOT}\\{sub_path}")
    except Exception:
        pass


def install(parameters: dict = None, player=None) -> str:
    """Instala entradas del menu contextual de Windows."""
    exe = _get_exe_path()
    if not os.path.isfile(exe):
        return f"Ejecutable no encontrado: {exe}. Build primero."

    actions = {
        "analyze":   "Analizar con ERIS",
        "translate": "Traducir con ERIS",
        "summarize": "Resumir con ERIS",
    }

    for target in ["*", "Directory", "Directory\\Background"]:
        base = f"{target}\\shell\\{MENU_NAME}"
        _set_reg(base, "", "ERIS")
        _set_reg(base, "Icon", exe)
        _set_reg(base, "MenuExtended", "")
        for key_name, display in actions.items():
            cmd_path = f"{target}\\shell\\{MENU_NAME}\\shell\\{key_name}"
            _set_reg(cmd_path, "", display)
            _set_reg(cmd_path, "Icon", exe)
            _set_reg(f"{cmd_path}\\command", "", f'"{exe}" --eris-action {key_name} --eris-path "%1"')

    return "Menu contextual de ERIS instalado (usuario actual). Prueba con clic derecho."


def _del_tree(key_path):
    """Elimina una clave y todas sus subclaves recursivamente."""
    try:
        with winreg.OpenKey(HKCR, f"{ROOT}\\{key_path}", 0, winreg.KEY_READ | winreg.KEY_WRITE) as k:
            while True:
                try:
                    sub = winreg.EnumKey(k, 0)
                    _del_tree(f"{key_path}\\{sub}")
                except OSError:
                    break
        winreg.DeleteKey(HKCR, f"{ROOT}\\{key_path}")
    except FileNotFoundError:
        pass


def uninstall(parameters: dict = None, player=None) -> str:
    """Desinstala las entradas del menu contextual."""
    for target in ["*", "Directory", "Directory\\Background"]:
        _del_tree(f"{target}\\shell\\{MENU_NAME}")
    return "Menu contextual de ERIS eliminado."


def status(parameters: dict = None, player=None) -> str:
    """Muestra estado del menu contextual."""
    try:
        with winreg.OpenKey(HKCR, f"{ROOT}\\*\\shell\\{MENU_NAME}"):
            return "Menu contextual instalado (usuario actual)."
    except Exception:
        pass
    return "Menu contextual no instalado. Usa action=install."
