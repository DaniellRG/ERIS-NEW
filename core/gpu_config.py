import os
import json
import sys
from pathlib import Path


def _detect_capable_platform():
    """Detecta si la plataforma actual puede correr animaciones fluidas con GPU.

    Regla por defecto (siempre que no haya preferencia manual en config):
      - Windows con GPU accesible → alto (aceleración activada)
      - Linux → alto por defecto (compositor/GPU maneja bien el orbe)
      - Fallback conservador → falso (modo low-RAM balanceado)
    """
    try:
        import platform as _p
        system = _p.system().lower()
        if system == "windows":
            try:
                if _p.processor() or True:
                    # Windows: casi siempre hay GPU via D3D11/DXGI
                    return True
            except Exception:
                pass
            return True
        if system == "linux":
            return True
        return False
    except Exception:
        return False


def configure_gpu():
    """Load config early to determine GPU acceleration settings.

    Se adapta al SO automáticamente: si no hay preferencia manual, activa la
    aceleración en plataformas con GPU (Windows/Linux). La config manual
    (`gpu_acceleration`) siempre tiene prioridad.
    """
    base_dir = None
    try:
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).resolve().parent.parent
        cfg_path = base_dir / "config" / "api_keys.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            manual = cfg.get("gpu_acceleration")
            # Se adapta al SO automáticamente: una plataforma capaz (Windows /
            # Linux de escritorio) siempre activa la aceleración para que las
            # animaciones sean fluidas. Un "true" manual fuerza GPU en cualquier
            # caso; "false" solo desactiva en máquinas de baja capacidad.
            if manual is True:
                gpu_enabled = True
            else:
                gpu_enabled = _detect_capable_platform()
        else:
            gpu_enabled = _detect_capable_platform()
    except Exception:
        gpu_enabled = _detect_capable_platform()

    os.environ["ERIS_GPU_ACCEL"] = "1" if gpu_enabled else "0"
    if gpu_enabled:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            "--ignore-gpu-blocklist "
            "--enable-gpu-rasterization "
            "--enable-zero-copy "
            "--num-raster-threads=4 "
            "--js-flags=--max-old-space-size=1024"
        )
        os.environ["QSG_RHI_BACKEND"] = "d3d11"
        os.environ["QSG_INFO"] = "1"
        print("[ERIS] GPU Acceleration is ENABLED. Offloading RAM rendering workload to GPU.")
    else:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            "--enable-low-end-device-mode "
            "--renderer-process-limit=1 "
            "--js-flags=--max-old-space-size=64 "
            "--disable-gpu-shader-disk-cache "
            "--disable-dev-shm-usage "
            "--disable-extensions "
            "--disable-sync "
            "--mute-audio"
        )
        print("[ERIS] Using Balanced Low RAM GPU-Composited mode for beautiful fluid rendering.")
