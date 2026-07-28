import os
import json
import sys
from pathlib import Path


def configure_gpu():
    """Load config early to determine GPU acceleration settings."""
    gpu_enabled = False
    try:
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).resolve().parent.parent
        cfg_path = base_dir / "config" / "api_keys.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            gpu_enabled = cfg.get("gpu_acceleration", False)
    except Exception:
        pass

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
