"""Grabación de pantalla con mss + opencv + audio opcional."""
import os
import threading
import time
from pathlib import Path


_recording = False
_thread = None
_output_path = None


def _record_worker(output: str, fps: int = 15, duration: int = 30, with_audio: bool = False, region: str = ""):
    global _output_path
    import cv2
    import mss
    import numpy as np

    sct = mss.mss()
    monitor = sct.monitors[1]
    if region:
        parts = region.replace(" ", "").split(",")
        if len(parts) == 4:
            monitor = {"top": int(parts[1]), "left": int(parts[0]), "width": int(parts[2]), "height": int(parts[3])}

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    w, h = monitor["width"], monitor["height"]
    out = cv2.VideoWriter(output, fourcc, fps, (w, h))
    audio_thread = None
    audio_data = []

    if with_audio:
        import sounddevice as sd
        import queue

        q = queue.Queue()

        def _audio_callback(indata, frames, time_info, status):
            q.put(indata.copy())

        def _record_audio():
            with sd.InputStream(samplerate=44100, channels=2, callback=_audio_callback):
                while _recording:
                    try:
                        audio_data.append(q.get(timeout=0.1))
                    except Exception:
                        pass

        audio_thread = threading.Thread(target=_record_audio, daemon=True)
        audio_thread.start()

    start = time.time()
    while _recording and (duration <= 0 or time.time() - start < duration):
        img = sct.grab(monitor)
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        out.write(frame)

    out.release()
    sct.close()

    if audio_thread:
        audio_thread.join(timeout=2)
        if audio_data:
            import soundfile as sf
            audio_arr = np.concatenate(audio_data, axis=0)
            audio_path = output.replace(".mp4", "_audio.wav")
            sf.write(audio_path, audio_arr, 44100)
            _try_merge_audio(output, audio_path)

    _output_path = output


def _try_merge_audio(video_path: str, audio_path: str):
    """Merge audio into video using ffmpeg if available."""
    import subprocess
    merged = video_path.replace(".mp4", "_with_audio.mp4")
    try:
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-i", audio_path,
             "-c:v", "copy", "-c:a", "aac", "-shortest", merged,
             "-y"],
            capture_output=True, timeout=120,
        )
        os.remove(audio_path)
    except Exception:
        pass


def start_recording(parameters: dict = None, player=None) -> str:
    """Inicia grabación de pantalla."""
    global _recording, _thread

    if _recording:
        return "Ya estoy grabando."

    params = parameters or {}
    duration = int(params.get("duration", 30))
    fps = int(params.get("fps", 15))
    with_audio = params.get("with_audio", "false").lower() in ("true", "1", "yes")
    region = params.get("region", "")
    name = params.get("name", f"grabacion_{int(time.time())}")

    out_dir = Path.home() / "Videos" / "ERIS"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = str(out_dir / f"{name}.mp4")

    _recording = True
    _thread = threading.Thread(
        target=_record_worker,
        args=(output, fps, duration, with_audio, region),
        daemon=True,
    )
    _thread.start()

    parts = [f"Grabando {duration}s a {fps}fps"]
    if with_audio:
        parts.append("con audio")
    if region:
        parts.append(f"región: {region}")
    parts.append(f"-> {output}")
    return " ".join(parts)


def stop_recording(parameters: dict = None, player=None) -> str:
    """Detiene la grabación actual."""
    global _recording
    if not _recording:
        return "No hay grabación activa."
    _recording = False
    if _thread:
        _thread.join(timeout=5)
    msg = f"Grabacion guardada en: {_output_path}" if _output_path else "Grabacion detenida."
    return msg


def recording_status(parameters: dict = None, player=None) -> str:
    """Muestra estado de la grabación."""
    if _recording:
        return "Grabando..." + (f" -> {_output_path}" if _output_path else "")
    return "Sin grabacion activa." + (f" Ultima: {_output_path}" if _output_path else "")
