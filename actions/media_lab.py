"""
actions/media_lab.py — Video/audio con ffmpeg + wf-recorder para ERIS.

Grabar pantalla (wf-recorder, Wayland nativo), grabar audio, convertir,
recortar, GIFs, unir video+audio, info de media.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time

_REC_PIDFILE = "/tmp/eris_record.pid"


def _ff(args, timeout=300):
    bin_ = shutil.which("ffmpeg")
    if not bin_:
        return "Error: ffmpeg no está instalado."
    try:
        r = subprocess.run([bin_, *args], capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            tail = (r.stderr or "").strip().splitlines()
            return f"Error ffmpeg ({r.returncode}): {' '.join(tail[-3:])[:220]}"
        return "(ok)"
    except subprocess.TimeoutExpired:
        return "Error: ffmpeg tardó demasiado."
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def _ffprobe(path: str) -> str:
    bin_ = shutil.which("ffprobe")
    if not bin_ or not os.path.exists(path):
        return f"Error: no existe o falta ffprobe → {path}"
    r = subprocess.run([bin_, "-v", "quiet", "-print_format", "json",
                        "-show_format", "-show_streams", path],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or not r.stdout:
        return f"No se pudo leer: {path}"
    try:
        import json
        j = json.loads(r.stdout)
        fmt = j.get("format", {})
        lines = [f"Formato: {fmt.get('format_name')} | {fmt.get('duration', '?')}s | "
                 f"{int(fmt.get('size', 0))/1024/1024:.1f} MB"]
        for s in j.get("streams", []):
            t = s.get("codec_type")
            if t == "video":
                lines.append(f"Video: {s.get('codec_name')} {s.get('width')}x{s.get('height')} "
                             f"@{s.get('avg_frame_rate','?')} fps")
            elif t == "audio":
                lines.append(f"Audio: {s.get('codec_name')} {s.get('sample_rate')} Hz "
                             f"{s.get('channels','?')} canales")
        return "\n".join(lines)
    except Exception as e:
        return f"Error parseando: {e}"


def media_lab(parameters: dict | None = None, player=None) -> str:
    """Laboratorio multimedia. Acciones: record, stop_record, info, convert,
    trim, gif, audio_record, merge, screenshot."""
    parameters = parameters or {}
    action = (parameters.get("action") or "info").lower()

    if action in ("info", "ver"):
        path = (parameters.get("path") or parameters.get("file") or "").strip()
        if not path:
            return "Falta 'path'."
        return _ffprobe(path)

    if action in ("record", "grabar"):
        out = (parameters.get("out") or parameters.get("output") or
               f"/tmp/eris_grabacion_{int(time.time())}.mp4")
        secs = parameters.get("seconds")
        geo = None
        try:
            if parameters.get("region") or parameters.get("x") is not None:
                x = int(parameters.get("x", 0)); y = int(parameters.get("y", 0))
                w = int(parameters.get("w", parameters.get("width", 800)))
                h = int(parameters.get("h", parameters.get("height", 600)))
                geo = f"{x},{y} {w}x{h}"
        except Exception:
            geo = None
        cmd = ["wf-recorder"]
        if geo:
            cmd += ["-g", geo]
        if parameters.get("audio"):
            dev = parameters.get("audio_device")
            cmd += ["-a" + (dev or "")]
        if parameters.get("fps"):
            cmd += ["-r", str(parameters["fps"])]
        if parameters.get("codec"):
            cmd += ["-c", str(parameters["codec"])]
        cmd += ["-f", out]
        try:
            if secs:
                r = subprocess.run(["timeout", "--preserve-status", "-k", "3",
                                    str(int(secs)), *cmd],
                                   capture_output=True, text=True, timeout=int(secs) + 20)
                return f"Grabado {out}\n" + _ffprobe(out)
            p = subprocess.Popen(cmd, start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(_REC_PIDFILE, "w") as f:
                f.write(str(p.pid))
            return (f"Grabando a {out} (PID {p.pid}). "
                    "Usá action=stop_record para detener y guardar.")
        except FileNotFoundError:
            return "Error: wf-recorder no está instalado (`sudo pacman -S wf-recorder`)."
        except Exception as e:
            return f"Error grabando: {type(e).__name__}: {e}"

    if action in ("stop_record", "detener_grabacion"):
        if not os.path.exists(_REC_PIDFILE):
            return "No hay grabación en curso."
        pid = int(open(_REC_PIDFILE).read().strip())
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception as e:
                return f"Error deteniendo: {e}"
        os.remove(_REC_PIDFILE)
        time.sleep(2)
        return "Grabación detenida (archivo finalizado)."

    if action in ("convert", "convertir"):
        inp = (parameters.get("input") or parameters.get("path") or "").strip()
        out = (parameters.get("output") or parameters.get("out") or "").strip()
        if not inp or not out or not os.path.exists(inp):
            return "Faltan 'input' (existente) y 'output'."
        ext = os.path.splitext(out)[1].lower()
        if ext in (".gif",):
            return media_lab({"action": "gif", "input": inp, "output": out,
                              "fps": parameters.get("fps", 12),
                              "width": parameters.get("width", 640)})
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            args = ["-y", "-i", inp, "-frames:v", "1"]
            if parameters.get("width"):
                args += ["-vf", f"scale={parameters.get('width')}:-1"]
            args += [out]
        else:
            vc = parameters.get("video_codec", "libx264")
            ac = parameters.get("audio_codec", "aac")
            extra = parameters.get("extra")
            args = ["-y", "-i", inp, "-c:v", vc, "-preset", "fast", "-crf", "23",
                    "-c:a", ac, "-movflags", "+faststart"]
            if extra:
                args = args[:2] + str(extra).split() + args[2:]
            args.append(out)
        return _ff(args)

    if action in ("trim", "recortar", "cortar"):
        inp = (parameters.get("input") or parameters.get("path") or "").strip()
        out = (parameters.get("output") or parameters.get("out") or "").strip()
        start = parameters.get("start")
        dur = parameters.get("duration") or parameters.get("t")
        if not inp or not out or not start:
            return "Faltan 'input', 'output' y 'start' (ej: start=00:01:30, duration=10)."
        args = ["-y", "-ss", str(start)]
        if dur:
            args += ["-t", str(dur)]
        args += ["-i", inp, "-c", "copy", "-map", "0", out]
        return _ff(args)

    if action in ("gif",):
        inp = (parameters.get("input") or parameters.get("path") or "").strip()
        out = (parameters.get("output") or parameters.get("out") or "").strip()
        if not inp or not out or not os.path.exists(inp):
            return "Faltan 'input' (existente) y 'output' (.gif)."
        fps = int(parameters.get("fps", 12) or 12)
        w = parameters.get("width")
        vf = f"fps={fps}"
        if w:
            vf += f",scale={w}:-1:flags=lanczos"
        vf += ",split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
        return _ff(["-y", "-i", inp, "-vf", vf, "-loop", "0", out]) + f" → {out}"

    if action in ("audio_record", "grabar_audio"):
        out = (parameters.get("out") or parameters.get("output") or
               f"/tmp/eris_audio_{int(time.time())}.mp3")
        secs = parameters.get("seconds")
        src = parameters.get("source") or "default"
        if not secs:
            return "Falta 'seconds' (duración de la grabación)."
        ext = os.path.splitext(out)[1].lower()
        codec = {"mp3": "libmp3lame", "ogg": "libvorbis", "wav": "pcm_s16le",
                 "flac": "flac"}.get(ext, "libmp3lame")
        args = ["-y", "-f", "pulse", "-i", src, "-t", str(int(secs))]
        if ext == "wav":
            args += ["-c:a", codec, out]
        else:
            args += ["-c:a", codec, "-b:a", "192k", out]
        r = _ff(args, timeout=int(secs) + 30)
        return r + ("\n" + _ffprobe(out) if r == "(ok)" else "")

    if action in ("merge", "unir"):
        vid = (parameters.get("video") or "").strip()
        aud = (parameters.get("audio") or "").strip()
        out = (parameters.get("out") or parameters.get("output") or "merged.mp4").strip()
        if not vid or not aud or not os.path.exists(vid) or not os.path.exists(aud):
            return "Faltan 'video' y 'audio' (existente) y 'out'."
        return _ff(["-y", "-i", vid, "-i", aud,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-shortest", out])

    if action in ("screenshot", "capturar"):
        from actions.screen_vision import _capture_screen_base64
        out = (parameters.get("out") or parameters.get("output") or
               "/tmp/eris_captura.png").strip()
        r = subprocess.run(["grim", out], capture_output=True, text=True)
        if r.returncode == 0:
            return f"Captura guardada: {out}"
        return f"Error grim: {r.stderr.strip() or r.stdout.strip()}"

    return ("Acciones: record (out,seconds,region/x/y/w/h,audio,fps,codec), "
            "stop_record, info (path), convert (input,output,width), "
            "trim (input,output,start,duration), gif (input,output,fps,width), "
            "audio_record (out,seconds,source), merge (video,audio,out), screenshot.")