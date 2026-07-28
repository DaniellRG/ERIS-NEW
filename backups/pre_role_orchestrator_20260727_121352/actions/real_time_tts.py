import os
import json
import queue
import threading
import subprocess
import tempfile
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
PROFILES_FILE = os.path.join(CONFIG_DIR, "voice_profiles.json")

_state = {
    "current_voice": "en-US-AriaNeural",
    "speed": "+0%",
    "pitch": "+0Hz",
    "volume": "+0%",
    "playing": False,
    "paused": False,
    "queue": [],
    "current_text": ""
}

_playback_queue = queue.Queue()
_worker_thread = None
_worker_running = False


def _load_voice_config():
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, "r") as f:
            data = json.load(f)
        active = data.get("active_profile", "default")
        profile = data.get("profiles", {}).get(active, {})
        return {
            "voice": profile.get("voice", _state["current_voice"]),
            "speed": profile.get("speed", _state["speed"]),
            "pitch": profile.get("pitch", _state["pitch"]),
            "volume": profile.get("volume", _state["volume"])
        }
    return {}


def _speak_edge_tts(text, voice=None, speed=None, pitch=None, volume=None):
    voice = voice or _state["current_voice"]
    speed = speed or _state["speed"]
    pitch = pitch or _state["pitch"]
    volume = volume or _state["volume"]

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()

    rate = speed if speed.startswith(("-","+")) else f"+{speed}%"
    pitch_str = pitch if pitch.startswith(("-","+")) else f"+{pitch}"
    vol = volume if volume.startswith(("-","+")) else f"+{volume}%"

    cmd = [
        "edge-tts",
        "--voice", voice,
        "--rate", rate,
        "--pitch", pitch_str,
        "--volume", vol,
        "--text", text,
        "--write-media", tmp.name
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return None, f"edge-tts error: {result.stderr}"

        if os.name == 'nt':
            os.startfile(tmp.name)
        else:
            subprocess.Popen(["mpg123", tmp.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return tmp.name, None
    except FileNotFoundError:
        return None, "edge-tts not installed. Run: pip install edge-tts"
    except subprocess.TimeoutExpired:
        return None, "TTS generation timed out"
    except Exception as e:
        return None, str(e)


def _worker():
    global _worker_running
    _worker_running = True
    while _worker_running:
        try:
            item = _playback_queue.get(timeout=1)
            if item is None:
                break
            text = item.get("text", "")
            _state["current_text"] = text
            _state["playing"] = True
            _state["paused"] = False
            _speak_edge_tts(text)
            _state["playing"] = False
            _state["current_text"] = ""
            _playback_queue.task_done()
        except queue.Empty:
            continue
    _worker_running = False


def real_time_tts(parameters: dict, player=None) -> str:
    action = parameters.get("action", "speak").lower()

    if action == "speak":
        return _speak(parameters)
    elif action == "stop":
        return _stop()
    elif action == "pause":
        return _pause()
    elif action == "resume":
        return _resume()
    elif action == "speed":
        return _set_speed(parameters)
    elif action == "voice":
        return _set_voice(parameters)
    elif action == "queue":
        return _add_to_queue(parameters)
    elif action == "status":
        return _get_status()
    else:
        return f"Unknown action: {action}. Valid: speak, stop, pause, resume, speed, voice, queue, status"


def _ensure_worker():
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_worker, daemon=True)
        _worker_thread.start()


def _speak(parameters: dict):
    text = parameters.get("text", "")
    if not text:
        return "'text' parameter required."

    immediate = parameters.get("immediate", True)
    if immediate:
        _state["current_text"] = text
        _state["playing"] = True
        _state["paused"] = False

        def _speak_async():
            filename, err = _speak_edge_tts(text)
            _state["playing"] = False
            _state["current_text"] = ""
            if err:
                pass

        threading.Thread(target=_speak_async, daemon=True).start()
        return f"Speaking: '{text[:80]}{'...' if len(text) > 80 else ''}'"
    else:
        _ensure_worker()
        _playback_queue.put({"text": text})
        return f"Queued: '{text[:80]}{'...' if len(text) > 80 else ''}'"


def _stop():
    _state["playing"] = False
    _state["paused"] = False
    _state["current_text"] = ""

    while not _playback_queue.empty():
        try:
            _playback_queue.get_nowait()
        except queue.Empty:
            break

    if os.name == 'nt':
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", "mpv.exe"],
                capture_output=True, timeout=5
            )
            subprocess.run(
                ["taskkill", "/F", "/IM", "ffplay.exe"],
                capture_output=True, timeout=5
            )
        except Exception:
            pass
    return "Playback stopped."


def _pause():
    if not _state["playing"]:
        return "Nothing is currently playing."
    _state["paused"] = True
    return "Playback paused."


def _resume():
    if not _state["paused"]:
        return "Nothing is paused."
    _state["paused"] = False
    return "Playback resumed."


def _set_speed(parameters: dict):
    speed = parameters.get("speed", "+0%")
    _state["speed"] = speed
    return f"Speed set to: {speed}"


def _set_voice(parameters: dict):
    voice = parameters.get("voice", "")
    if not voice:
        return f"Current voice: {_state['current_voice']}"
    _state["current_voice"] = voice
    if "pitch" in parameters:
        _state["pitch"] = parameters["pitch"]
    if "volume" in parameters:
        _state["volume"] = parameters["volume"]
    return f"Voice set to: {voice}"


def _add_to_queue(parameters: dict):
    text = parameters.get("text", "")
    if not text:
        return "'text' parameter required."

    _ensure_worker()
    _playback_queue.put({"text": text})
    return f"Added to queue ({_playback_queue.qsize()} items): '{text[:60]}...'"


def _get_status():
    lines = [
        f"Playing: {_state['playing']}",
        f"Paused: {_state['paused']}",
        f"Voice: {_state['current_voice']}",
        f"Speed: {_state['speed']}",
        f"Pitch: {_state['pitch']}",
        f"Volume: {_state['volume']}",
        f"Queue size: {_playback_queue.qsize()}"
    ]
    if _state["current_text"]:
        lines.append(f"Current: '{_state['current_text'][:60]}...'")
    return "\n".join(lines)
