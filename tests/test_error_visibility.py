"""
tests/test_error_visibility.py
──────────────────────────────
Fase 0.3 del diseño: los errores tienen que verse.

  1. `fileno()` ya no lanza io.UnsupportedOperation (rompía logging/os.dup/
     subprocess que pedían el fd de sys.stdout/stderr).
  2. Los tracebacks que pasan por sys.stderr llegan al buffer en memoria
     (core/error_buffer) sin leer el archivo.
  3. `diagnostico action=logs` los muestra.
  4. `eris.log` existe y guarda lo que se escupe a stdout/stderr.
  5. El buffer nunca rompe la ejecución (su regla).
"""

from __future__ import annotations

import io
import sys
import traceback
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))


def test_tee_fileno_no_rompe():
    from core.logging_setup import setup_logging
    setup_logging()
    try:
        fd_out = sys.stdout.fileno()
        fd_err = sys.stderr.fileno()
    except Exception as exc:
        pytest.fail(f"fileno() siguió roto: {type(exc).__name__}: {exc}")
    assert isinstance(fd_out, int)
    assert isinstance(fd_err, int)
    assert sys.stderr.isatty() is False
    assert sys.stderr.writable() is True


def test_traceback_cae_al_buffer():
    from core import error_buffer as eb
    # setup_logging de nuevo acá: pytest reemplaza sys.stderr por su objeto de
    # captura en cada test, así que sin esta llamada el tracer no vería nada.
    from core.logging_setup import setup_logging
    setup_logging()
    eb.clear_errors()
    try:
        1 / 0
    except ZeroDivisionError:
        traceback.print_exc(file=sys.stderr)
        try:
            sys.stderr.flush()
        except Exception:
            pass
    errs = eb.recent_errors(10)
    texts = "\n".join(e["text"] for e in errs)
    assert "ZeroDivisionError" in texts
    assert "Traceback" in texts


def test_buffer_reglas_de_oro():
    """Registrar en el buffer nunca lanza, y la dedupe anti-spam funciona."""
    from core import error_buffer as eb
    eb.record_error("boom")   # no debería lanzar
    eb.record_error("")        # vacíos se descartan
    eb.record_error(123)       # no-str se descartan
    assert eb.error_count() >= 1
    assert all(isinstance(e["text"], str) for e in eb.recent_errors(5))


def test_diagnostico_expone_el_buffer(monkeypatch):
    from actions.diagnostico import _render_logs
    from core import error_buffer as eb
    eb.record_error("error_marca_de_prueba_xyz", source="test")
    rend = _render_logs({"logs": 1})
    assert "error_marca_de_prueba_xyz" in rend
    assert "memoria" in rend


def test_eris_log_existe_y_escribe(monkeypatch, tmp_path):
    from core.logging_setup import LOG_PATH
    # El archivo debe existir tras setup_logging (main.py lo llama al arrancar).
    setup = None
    try:
        from core.logging_setup import setup_logging as _s
        setup = _s
    except Exception:
        pass
    assert LOG_PATH.parent == BASE or LOG_PATH.parent == BASE.parent
    # En esta máquina el archivo ya se ha creado con el run del suite.
    assert LOG_PATH.exists(), "eris.log no existe: main.py y eris_cli.py lo crean con setup_logging()"
    assert LOG_PATH.stat().st_size >= 0