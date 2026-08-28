import json
import os
import time
from datetime import datetime
from pathlib import Path

try:
    import cv2
    HAS_CV2 = True
    try:
        cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
    except Exception:
        pass
except ImportError:
    HAS_CV2 = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from actions import image_analyzer as _ia

_BASE = Path(__file__).resolve().parent.parent
_SNAP_DIR = _BASE / "snapshots"
_SNAP_DIR.mkdir(exist_ok=True)


def _pick_index(parameters):
    try:
        return int(parameters.get("camera", parameters.get("index", parameters.get("cam", 0))))
    except Exception:
        return 0


def _capture(index=0):
    if not HAS_CV2:
        return None, "OpenCV (cv2) no esta instalado."
    if not HAS_NUMPY:
        return None, "numpy no esta instalado."
    # Intentar con DirectShow primero, luego MSMF, luego default
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, 0] if os.name == "nt" else [0]
    for backend in backends:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            ok, frame = cap.read()
            cap.release()
            if ok and frame is not None:
                return frame, None
    return None, f"No se pudo abrir la camara {index}. Prueba otra con 'camera'."


def _save_snapshot(frame, index=0, tag="cam"):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _SNAP_DIR / f"{tag}_{index}_{stamp}.png"
    cv2.imwrite(str(path), frame)
    return path


def _motion_analysis(index=0, seconds=1.0):
    if not HAS_CV2 or not HAS_NUMPY:
        return None, "OpenCV o numpy no instalados."
    # Intentar con DirectShow primero, luego MSMF, luego default
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, 0] if os.name == "nt" else [0]
    cap = None
    for backend in backends:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            break
    if cap is None or not cap.isOpened():
        return None, f"No se pudo abrir la camara {index}."
    prev = None
    frames = 0
    changed = 0
    max_diff = 0.0
    fps = 10.0
    deadline = time.time() + float(seconds)
    while time.time() < deadline:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if prev is not None:
            diff = cv2.absdiff(prev, gray)
            mean = float(diff.mean())
            max_diff = max(max_diff, mean)
            if mean > 5.0:
                changed += 1
        prev = gray
        frames += 1
        time.sleep(1.0 / fps)
    cap.release()
    if frames == 0:
        return None, "No se capturaron frames."
    ratio = changed / frames
    motion = ratio > 0.3 or max_diff > 8.0
    return {
        "frames": frames,
        "changed_frames": changed,
        "motion_ratio": round(ratio, 2),
        "max_difference": round(max_diff, 2),
        "motion_detected": motion,
    }, None


def _faces_in_frame(frame):
    try:
        if not hasattr(cv2, "data"):
            return None
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if not cascade_path.exists():
            return None
        cascade = cv2.CascadeClassifier(str(cascade_path))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        return list(faces)
    except Exception:
        return None


def _vision_analysis(path, question=None):
    try:
        b64 = _ia._image_to_base64(str(path))
        mime = _ia._get_mime_type(str(path))
        prompt = question or (
            "Analiza esta imagen capturada en vivo por la camara. Describe lo que hay: "
            "personas, objetos, ambiente, texto visible y cualquier actividad notable. Se conciso."
        )
        result, source = _ia._analyze_vision(b64, prompt, mime)
        return result, source
    except Exception as e:
        return f"Error al analizar con vision: {e}", None


def camera_bus(parameters: dict, player=None) -> str:
    action = str(parameters.get("action", "info")).lower()
    index = _pick_index(parameters)
    question = parameters.get("question", parameters.get("prompt", ""))
    analyze = str(parameters.get("analyze", parameters.get("vision", "false"))).lower() in ("1", "true", "yes", "on")

    if action == "info":
        if not HAS_CV2:
            return "OpenCV no esta instalado."
        found = []
        for i in range(4):
            cap = None
            for backend in ([cv2.CAP_DSHOW, cv2.CAP_MSMF, 0] if os.name == "nt" else [0]):
                cap = cv2.VideoCapture(i, backend)
                if cap.isOpened():
                    break
            if cap and cap.isOpened():
                w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                found.append(f"Camara {i}: disponible ({int(w)}x{int(h)})")
            if cap:
                cap.release()
        if not found:
            return "No se detectaron camaras conectadas."
        return "Camaras detectadas:\n" + "\n".join(found)

    if action in ("snapshot", "capture"):
        frame, err = _capture(index)
        if err:
            return f"Error: {err}"
        path = _save_snapshot(frame, index, "snap")
        out = [f"Instantanea guardada: {path}"]
        if analyze:
            result, source = _vision_analysis(path, question)
            out.append(f"\nAnalisis de vision ({source or 'n/a'}):\n{result}")
        else:
            out.append("Usa 'analyze': true para analizarla, o 'read' para una descripcion automatica.")
        return "\n".join(out)

    if action in ("analyze", "read", "see", "mirar", "observar"):
        frame, err = _capture(index)
        if err:
            return f"Error: {err}"
        path = _save_snapshot(frame, index, "snap")
        faces = _faces_in_frame(frame)
        result, source = _vision_analysis(path, question)
        header = f"Vision en vivo - camara {index}\nCaptura: {path}"
        if faces is not None:
            header += f"\nRostros detectados localmente: {len(faces)}"
        return f"{header}\n\n{result}\n\n[Fuente: {source}]" if source else f"{header}\n\n{result}"

    if action in ("motion", "watch", "vigilar"):
        seconds = float(parameters.get("seconds", parameters.get("time", 2)))
        result, err = _motion_analysis(index, seconds)
        if err:
            return f"Error: {err}"
        verdict = "MOVIMIENTO DETECTADO" if result["motion_detected"] else "sin movimiento"
        return (f"Vigilancia camara {index} ({result['frames']} frames en {seconds}s): {verdict}\n"
                f"Frames con cambio: {result['changed_frames']} (ratio {result['motion_ratio']}, diff maxima {result['max_difference']})")

    return ("Acciones disponibles: info, snapshot (capture), analyze/read (captura + vision AI), motion/watch (deteccion de movimiento). "
            "Opciones: camera (indice 0-3), question (para vision), seconds.")
