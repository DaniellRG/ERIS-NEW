import sys
from pathlib import Path


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LOG_PATH        = BASE_DIR / "eris.log"


def setup_logging():
    """Redirect stdout/stderr to log file and suppress subprocess console windows."""
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
    except Exception:
        pass

    # ── Suppress console windows from all child subprocesses ─────────────────
    if sys.platform == "win32":
        try:
            import ctypes as _ctypes
            if _ctypes.windll.kernel32.GetConsoleWindow() == 0:
                import subprocess as _sp
                _CREATE_NO_WINDOW = 0x08000000
                _orig_Popen = _sp.Popen
                class _NoCmdPopen(_orig_Popen):
                    def __init__(self, *args, **kwargs):
                        kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
                        super().__init__(*args, **kwargs)
                _sp.Popen = _NoCmdPopen
                print("[ERIS] subprocess.Popen patched: CREATE_NO_WINDOW active")
        except Exception as _e:
            print(f"[ERIS] Could not patch subprocess: {_e}")
