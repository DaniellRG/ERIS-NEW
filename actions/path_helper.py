# -*- coding: utf-8 -*-
"""
path_helper.py — Robust Windows special folder path resolver for ERIS.
Handles OneDrive redirection, Spanish localizations, and standard fallbacks.
"""
import os
import ctypes
from pathlib import Path
import platform as _plat
_IS_WIN = _plat.system() == "Windows"
if not _IS_WIN:
    class _Noop:
        def __call__(self, *a, **kw): return 0
        def __getitem__(self, k): return _Noop()
        def __getattr__(self, n): return _Noop()
    _WIN32 = _Noop()
    _KERNEL32 = _Noop()
    _SHELL32 = _Noop()
    _WINMM = _Noop()
else:
    import ctypes as _ctypes
    _WIN32 = _ctypes.windll.user32
    _KERNEL32 = _ctypes.windll.kernel32
    _SHELL32 = _ctypes.windll.shell32
    _WINMM = _ctypes.windll.winmm

def _xdg_dir(varname: str):
    """Lee XDG_DESKTOP_DIR/XDG_DOWNLOAD_DIR/... de ~/.config/user-dirs.dirs (Linux)."""
    try:
        cfg = Path.home() / ".config" / "user-dirs.dirs"
        if not cfg.exists():
            return None
        for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith(varname + "="):
                raw = line.split("=", 1)[1].strip().strip('"')
                raw = raw.replace("$HOME", str(Path.home())).replace("${HOME}", str(Path.home()))
                p = Path(raw).expanduser()
                return p
    except Exception:
        pass
    return None


def get_special_folder(csidl: int) -> Path:
    """Gets the path of a Windows special folder using SHGetFolderPathW."""
    if not _IS_WIN:
        return None
    try:
        from ctypes import wintypes
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        # CSIDL constants: 0 = CSIDL_DESKTOP, 5 = CSIDL_PERSONAL (Documents)
        if _SHELL32.SHGetFolderPathW(None, csidl, None, 0, buf) == 0:
            p = Path(buf.value)
            if p.exists():
                return p
    except Exception:
        pass
    return None

def get_desktop_path() -> Path:
    """Returns the user's actual Desktop path, checking API, OneDrive, and fallbacks."""
    # 1. Try SHGetFolderPathW (CSIDL_DESKTOP = 0)
    p = get_special_folder(0)
    if p:
        return p

    # 2. Linux/XDG: respetar XDG_DESKTOP_DIR si apunta a una carpeta real
    xdg = _xdg_dir("XDG_DESKTOP_DIR")
    if xdg and xdg.is_dir():
        return xdg

    # 3. Try common OneDrive and localized directories
    home = Path.home()
    candidates = [
        home / "OneDrive" / "Desktop",
        home / "OneDrive" / "Escritorio",
        home / "Desktop",
        home / "Escritorio"
    ]
    for c in candidates:
        if c.exists():
            return c
            
    # 4. Fallback to standard environment or home
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        dp = Path(user_profile) / "Desktop"
        if dp.exists():
            return dp
            
    return home

def get_documents_path() -> Path:
    """Returns the user's actual Documents path."""
    # 1. Try SHGetFolderPathW (CSIDL_PERSONAL = 5)
    p = get_special_folder(5)
    if p:
        return p

    xdg = _xdg_dir("XDG_DOCUMENTS_DIR")
    if xdg and xdg.is_dir():
        return xdg

    # 2. Try common OneDrive and localized directories
    home = Path.home()
    candidates = [
        home / "OneDrive" / "Documents",
        home / "OneDrive" / "Documentos",
        home / "Documents",
        home / "Documentos"
    ]
    for c in candidates:
        if c.exists():
            return c
            
    # 3. Fallback to standard environment or home
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        dp = Path(user_profile) / "Documents"
        if dp.exists():
            return dp
            
    return home

def get_downloads_path() -> Path:
    """Returns the user's actual Downloads path."""
    home = Path.home()

    xdg = _xdg_dir("XDG_DOWNLOAD_DIR")
    if xdg and xdg.is_dir():
        return xdg

    # Check registry or standard locations
    candidates = [
        home / "Downloads",
        home / "Descargas",
        home / "OneDrive" / "Downloads",
        home / "OneDrive" / "Descargas"
    ]
    for c in candidates:
        if c.exists():
            return c
            
    return home
