import sys
import os
from pathlib import Path


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LOG_PATH        = BASE_DIR / "eris.log"


def get_obsidian_vault() -> Path:
    """Devuelve la ruta al vault de Obsidian (memoria persistente de ERIS).

    Resuelve de forma portable (funciona en Windows y Linux): primero busca
    la variable de entorno ERIS_OBSIDIAN_VAULT; si no está, usa la carpeta
    hermana 'Eris_NEW/BaseDatosObsidian/BaseObsiEris' junto a BASE_DIR; y
    como último recurso, una carpeta local 'obsidian_vault' dentro del repo
    para que el sistema nunca dependa de una ruta absoluta hardcodeada.
    """
    env = os.environ.get("ERIS_OBSIDIAN_VAULT")
    if env:
        _p = Path(env)
        if _p.is_dir():
            return _p
    candidates = [
        BASE_DIR.parent / "Eris_NEW" / "BaseDatosObsidian" / "BaseObsiEris",
        Path("D:/Eris_NEW/BaseDatosObsidian/BaseObsiEris"),
        BASE_DIR / "obsidian_vault",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


def setup_logging():
    """Redirect stdout/stderr to log file and suppress subprocess console windows."""
    # ── Rotate oversized log & cleanup old backups ─
    _MAX_LOG_MB = 2
    _rotate_msg = None
    try:
        # Purge any stale backup files beyond eris.log.2
        _log_dir = LOG_PATH.parent
        for _stale in sorted(_log_dir.glob("eris.log.*"), reverse=True):
            try:
                _idx = int(_stale.suffix.split(".")[-1])
                if _idx > 2:
                    _stale.unlink(missing_ok=True)
            except (ValueError, OSError):
                pass

        if LOG_PATH.exists() and LOG_PATH.stat().st_size > _MAX_LOG_MB * 1024 * 1024:
            _old2 = LOG_PATH.with_name("eris.log.2")
            _old1 = LOG_PATH.with_name("eris.log.1")
            if _old2.exists():
                _old2.unlink(missing_ok=True)
            if _old1.exists():
                _old1.rename(_old2)
            LOG_PATH.rename(_old1)
            _rotate_msg = f"[ERIS] Log rotated: eris.log >{_MAX_LOG_MB}MB -> eris.log.1"
    except Exception:
        pass

    # ── Redirect output to log file (pythonw.exe has no console) ─
    try:
        import io as _io
        _log_fh = open(LOG_PATH, "w", encoding="utf-8", buffering=1)

        class _TeeStream:
            def __init__(self, *streams):
                self._streams = [s for s in streams if s is not None]
            def write(self, data):
                for s in self._streams:
                    try: s.write(data)
                    except Exception: pass
            def flush(self):
                for s in self._streams:
                    try: s.flush()
                    except Exception: pass
            @property
            def encoding(self): return "utf-8"
            def fileno(self): raise _io.UnsupportedOperation("fileno")

        sys.stdout = _TeeStream(sys.stdout, _log_fh)
        sys.stderr = _TeeStream(sys.stderr, _log_fh)
        if _rotate_msg:
            print(_rotate_msg)
    except Exception:
        pass

    # ── Suppress console windows from all child subprocesses ─────────────────
    if sys.platform == "win32":
        try:
            import subprocess as _sp
            import os as _os
            _CREATE_NO_WINDOW = 0x08000000

            # STARTUPINFO con SW_HIDE por si creationflags no basta.
            # Python 3.14 movió/quita STARTUPINFO de ctypes.wintypes: si falla,
            # NO debe abortar el parche (CREATE_NO_WINDOW sigue activo).
            import ctypes as _ctypes
            _si = None
            try:
                _startup_cls = getattr(_ctypes.wintypes, "STARTUPINFO", None)
                if _startup_cls is None:
                    _startup_cls = getattr(_ctypes, "STARTUPINFOW", None)
                if _startup_cls is not None:
                    _si = _startup_cls()
                    _si.dwFlags = 0x00000001  # STARTF_USESHOWWINDOW
                    _si.wShowWindow = 0        # SW_HIDE
            except Exception:
                _si = None

            _orig_Popen = _sp.Popen
            class _NoCmdPopen(_orig_Popen):
                def __init__(self, *args, **kwargs):
                    kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
                    if _si is not None and kwargs.get("startupinfo") is None and kwargs.get("shell") is False:
                        try:
                            kwargs["startupinfo"] = _si
                        except Exception:
                            pass
                    super().__init__(*args, **kwargs)
            _sp.Popen = _NoCmdPopen

            # Rebind helpers internos que referencian Popen (run, call, check_*)
            for _name in ("run", "call", "check_call", "check_output"):
                _fn = getattr(_sp, _name, None)
                if _fn is not None and hasattr(_fn, "__func__"):
                    try:
                        _fn.__func__.__globals__["Popen"] = _NoCmdPopen
                    except Exception:
                        pass

            # os.system / os.popen sin consola visible
            _orig_system = _os.system
            def _hidden_system(cmd):
                try:
                    _p = _sp.Popen(cmd, shell=True, creationflags=_CREATE_NO_WINDOW)
                    return _p.wait()
                except Exception:
                    return _orig_system(cmd)
            _os.system = _hidden_system
            if hasattr(_os, "popen"):
                _orig_popen = _os.popen
                def _hidden_popen(cmd, mode="r", buffering=-1):
                    try:
                        return _sp.Popen(cmd, shell=True, creationflags=_CREATE_NO_WINDOW,
                                         stdout=_sp.PIPE, stderr=_sp.STDOUT, text=True).stdout
                    except Exception:
                        return _orig_popen(cmd, mode, buffering)
                _os.popen = _hidden_popen

            # ── Also patch asyncio subprocess to hide console windows ──
            try:
                import asyncio as _asyncio
                _orig_cse = _asyncio.create_subprocess_exec
                def _hidden_cse(*args, **kwargs):
                    kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
                    return _orig_cse(*args, **kwargs)
                _asyncio.create_subprocess_exec = _hidden_cse

                _orig_css = _asyncio.create_subprocess_shell
                def _hidden_css(*args, **kwargs):
                    kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
                    return _orig_css(*args, **kwargs)
                _asyncio.create_subprocess_shell = _hidden_css
            except Exception:
                pass

            print("[ERIS] subprocess.Popen patched: CREATE_NO_WINDOW active")
        except Exception as _e:
            print(f"[ERIS] Could not patch subprocess: {_e}")
