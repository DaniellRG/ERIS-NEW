"""Screen companion features inspired by capri-desktop.

Includes: screenshot analysis, game controls, stealth mode, clips.
"""

import os
import platform
import subprocess
import threading
import time
from pathlib import Path
from core.platform import safe_print

BASE_DIR = Path(__file__).parent.parent

# State
_STEALTH_MODE = False
_GAME_CONTROLS = {}
_CLIP_BUFFER = []
_CLIP_RECORDING = False
_CLIP_THREAD = None


def screenshot_analyze(prompt: str = "Describe what you see on screen") -> str:
    """Capture screenshot and analyze with vision LLM."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img_path = "/tmp/eris_screen_analysis.png"
        img.save(img_path)

        # Try to analyze with Gemini vision
        try:
            import json
            cfg = json.loads((BASE_DIR / "config" / "api_keys.json").read_text())
            api_key = cfg.get("gemini_api_key", "")
            if api_key:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=api_key)
                with open(img_path, "rb") as f:
                    image_data = f.read()
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[
                        types.Content(role="user", parts=[
                            types.Part(text=prompt),
                            types.Part(inline_data=types.Blob(mime_type="image/png", data=image_data)),
                        ])
                    ]
                )
                return response.text[:1000] if response.text else "No response from vision model"
        except Exception as e:
            safe_print(f"[SCREEN_ANALYZE] Vision error: {e}")

        return f"Screenshot saved to {img_path}. Vision analysis unavailable."
    except Exception as e:
        safe_print(f"[SCREEN_ANALYZE] Error: {e}")
        return f"Error: {e}"


def teach_game_controls(game_name: str, controls: str) -> str:
    """Teach Eris the controls of a game.

    Args:
        game_name: Name of the game
        controls: Controls description (e.g., "WASD to move, Space to jump")
    """
    global _GAME_CONTROLS
    _GAME_CONTROLS[game_name.lower()] = controls
    # Save to file
    import json
    controls_file = BASE_DIR / "data" / "game_controls.json"
    controls_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(controls_file.read_text()) if controls_file.exists() else {}
    except Exception:
        existing = {}
    existing[game_name.lower()] = controls
    controls_file.write_text(json.dumps(existing, indent=2))
    return f"Learned controls for {game_name}: {controls}"


def get_game_controls(game_name: str = "") -> str:
    """Get game controls. If no game specified, list all known games."""
    import json
    controls_file = BASE_DIR / "data" / "game_controls.json"
    try:
        existing = json.loads(controls_file.read_text()) if controls_file.exists() else {}
    except Exception:
        existing = {}

    if game_name:
        game = game_name.lower()
        if game in existing:
            return f"{game_name}: {existing[game]}"
        return f"No controls known for {game_name}. Teach me with: teach_game_controls('{game_name}', 'controls description')"
    if not existing:
        return "No game controls known yet. Teach me with: teach_game_controls('game_name', 'controls description')"
    lines = ["Known game controls:"]
    for game, controls in existing.items():
        lines.append(f"  • {game}: {controls}")
    return "\n".join(lines)


def stealth_mode(enable: bool = True) -> str:
    """Toggle stealth mode (Eris invisible for screen captures).

    When enabled, Eris window is hidden from screenshots and screen recordings.
    """
    global _STEALTH_MODE
    _STEALTH_MODE = enable
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        app = QApplication.instance()
        if app is None:
            return "Error: No Qt application running"
        for w in app.topLevelWidgets():
            if "Eris" in w.windowTitle() or "eris" in w.objectName().lower():
                if enable:
                    w.setWindowFlags(w.windowFlags() | Qt.WindowType.Tool)
                    w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
                else:
                    w.setWindowFlags(w.windowFlags() & ~Qt.WindowType.Tool)
                    w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
                w.show()
                return f"Stealth mode {'enabled' if enable else 'disabled'}"
        return "Eris window not found"
    except Exception as e:
        safe_print(f"[STEALTH] Error: {e}")
        return f"Error: {e}"


def start_clip(duration: int = 30) -> str:
    """Start recording screen clips (last N seconds).

    Args:
        duration: How many seconds to keep in the clip buffer
    """
    global _CLIP_BUFFER, _CLIP_RECORDING, _CLIP_THREAD
    if _CLIP_RECORDING:
        return "Clip recording already active"

    _CLIP_BUFFER = []
    _CLIP_RECORDING = True

    def _record_loop():
        global _CLIP_BUFFER, _CLIP_RECORDING
        from PIL import ImageGrab
        import io
        while _CLIP_RECORDING:
            try:
                img = ImageGrab.grab()
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                _CLIP_BUFFER.append((time.time(), buf.getvalue()))
                # Keep only last N seconds
                cutoff = time.time() - duration
                _CLIP_BUFFER = [(t, d) for t, d in _CLIP_BUFFER if t > cutoff]
            except Exception as e:
                safe_print(f"[CLIP] Error: {e}")
            time.sleep(0.5)  # ~2 fps

    _CLIP_THREAD = threading.Thread(target=_record_loop, daemon=True)
    _CLIP_THREAD.start()
    return f"Clip recording started (keeping last {duration}s)"


def stop_clip() -> str:
    """Stop recording screen clips."""
    global _CLIP_RECORDING, _CLIP_THREAD
    if not _CLIP_RECORDING:
        return "Clip recording not active"
    _CLIP_RECORDING = False
    if _CLIP_THREAD:
        _CLIP_THREAD.join(timeout=3)
    return f"Clip recording stopped ({len(_CLIP_BUFFER)} frames captured)"


def save_clip(output_path: str = "") -> str:
    """Save the last N seconds of recorded screen as an image sequence or GIF.

    Args:
        output_path: Path to save the clip (default: /tmp/eris_clip.gif)
    """
    global _CLIP_BUFFER
    if not _CLIP_BUFFER:
        return "No clip data recorded. Start recording first with start_clip()"

    if not output_path:
        output_path = "/tmp/eris_clip.gif"

    try:
        from PIL import Image
        import io
        frames = []
        for t, data in _CLIP_BUFFER:
            img = Image.open(io.BytesIO(data))
            frames.append(img.copy())

        if len(frames) > 1:
            frames[0].save(output_path, save_all=True, append_images=frames[1:], duration=500, loop=0)
        else:
            frames[0].save(output_path)
        return f"Clip saved: {output_path} ({len(frames)} frames)"
    except Exception as e:
        safe_print(f"[CLIP] Save error: {e}")
        return f"Error saving clip: {e}"


def get_game_controls_list() -> str:
    """List all known game controls."""
    return get_game_controls("")
