"""Audio transcriber module using faster-whisper for local transcription."""

import json
import os
import time
import tempfile
import wave
import subprocess
from pathlib import Path
from datetime import datetime

SUPPORTED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}
DATA_DIR = Path(__file__).parent / "data"
HISTORY_FILE = DATA_DIR / "audio_transcriptions.json"


def _load_history() -> list:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_history(history: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_whisper_model(model_size="base"):
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        return model
    except ImportError:
        return None
    except Exception:
        return None


def _record_clipboard_audio(duration=5) -> str | None:
    try:
        tmp_path = os.path.join(tempfile.gettempdir(), "clipboard_recording.wav")
        if os.name == 'nt':
            powershell_cmd = (
                f'powershell -Command "'
                f'Add-Type -AssemblyName System.Speech; '
                f'$recorder = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, 16, 1); '
                f'$source = New-Object System.Speech.Recognition.SpeechRecognitionEngine; '
                f'"'
            )
            return None
        else:
            subprocess.run(
                ["ffmpeg", "-f", "pulse", "-i", "default", "-t", str(duration),
                 "-ar", "16000", "-ac", "1", tmp_path, "-y"],
                capture_output=True, timeout=duration + 5
            )
            if os.path.exists(tmp_path):
                return tmp_path
    except Exception:
        return None
    return None


def audio_transcriber(parameters: dict, player=None) -> str:
    action = parameters.get("action", "transcribe")

    if action == "transcribe":
        file_path = parameters.get("file_path") or parameters.get("file", "")
        model_size = parameters.get("model_size") or parameters.get("model", "base")
        language = parameters.get("language", None)

        if not file_path:
            return "Error: No file path provided. Use 'file' parameter."

        file_path = os.path.expanduser(file_path)
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        ext = Path(file_path).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return f"Error: Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"

        model = _get_whisper_model(model_size)
        if model is None:
            return (
                "Error: faster-whisper not available. "
                "Install with: pip install faster-whisper"
            )

        try:
            kwargs = {}
            if language:
                kwargs["language"] = language

            segments, info = model.transcribe(file_path, **kwargs)
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            full_text = " ".join(text_parts)
            detected_lang = info.language if info else "unknown"
            duration = info.duration if info else 0

            entry = {
                "timestamp": datetime.now().isoformat(),
                "file": file_path,
                "language": detected_lang,
                "duration_seconds": round(duration, 2),
                "text": full_text,
                "model": model_size
            }
            history = _load_history()
            history.append(entry)
            _save_history(history)

            result = (
                f"Transcription ({detected_lang}, {duration:.1f}s):\n"
                f"{'=' * 50}\n"
                f"{full_text}\n"
                f"{'=' * 50}\n"
                f"Segments: {len(text_parts)} | Model: {model_size}"
            )
            return result

        except Exception as e:
            return f"Error transcribing: {e}"

    elif action == "transcribe_clipboard":
        model_size = parameters.get("model_size") or parameters.get("model", "base")
        duration = parameters.get("duration", 5)

        audio_file = _record_clipboard_audio(duration)
        if not audio_file:
            return (
                "Error: Could not record audio. "
                "On Linux, ensure ffmpeg and PulseAudio are available. "
                "On Windows, direct microphone recording is not yet supported via stdlib."
            )

        result = audio_transcriber({
            "action": "transcribe",
            "file": audio_file,
            "model": model_size
        }, player)

        try:
            os.unlink(audio_file)
        except OSError:
            pass

        return result

    elif action == "languages":
        languages = {
            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
            "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ja": "Japanese",
            "zh": "Chinese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
            "ru": "Russian", "pl": "Polish", "tr": "Turkish", "vi": "Vietnamese",
            "th": "Thai", "sv": "Swedish", "da": "Danish", "fi": "Finnish",
            "no": "Norwegian", "uk": "Ukrainian", "cs": "Czech", "el": "Greek",
            "he": "Hebrew", "ro": "Romanian", "hu": "Hungarian", "id": "Indonesian",
            "ms": "Malay", "tl": "Tagalog", "bg": "Bulgarian", "hr": "Croatian",
            "sk": "Slovak", "lt": "Lithuanian", "lv": "Latvian", "et": "Estonian",
            "sl": "Slovenian", "ca": "Catalan", "fa": "Farsi", "bn": "Bengali",
            "sw": "Swahili", "ta": "Tamil", "ur": "Urdu"
        }
        lines = ["Supported Languages (faster-whisper/Whisper):", "=" * 40]
        for code, name in sorted(languages.items()):
            lines.append(f"  {code}: {name}")
        lines.append(f"\nTotal: {len(languages)} languages")
        lines.append("Pass language code via 'language' parameter to specify.")
        return "\n".join(lines)

    elif action == "history":
        limit = parameters.get("limit", 20)
        history = _load_history()

        if not history:
            return "No transcription history found."

        recent = history[-limit:]
        lines = [f"Transcription History (showing last {len(recent)} of {len(history)}):", "=" * 60]
        for i, entry in enumerate(recent, 1):
            ts = entry.get("timestamp", "unknown")
            lang = entry.get("language", "?")
            text_preview = entry.get("text", "")[:80]
            file_name = os.path.basename(entry.get("file", "unknown"))
            lines.append(f"  {i}. [{ts}] ({lang}) {file_name}")
            lines.append(f"     \"{text_preview}{'...' if len(entry.get('text', '')) > 80 else ''}\"")
        return "\n".join(lines)

    elif action == "list_models":
        return ("Modelos de transcripción disponibles (faster-whisper):\n"
                "  - tiny   (~75 MB, rápido, menos preciso)\n"
                "  - base   (~145 MB, balance)\n"
                "  - small  (~460 MB, preciso)\n"
                "  - medium (~1.5 GB, muy preciso)\n"
                "  - large-v3 (~3 GB, máxima precisión)\n"
                "Parámetro 'model' para elegir (default base). Requiere: pip install faster-whisper")

    elif action == "transcribe_mic":
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return "Para transcribir desde el micrófono necesito instalar faster-whisper: pip install faster-whisper"
        return "transcribe_mic aún no está implementado. Usá 'transcribe' con un archivo o el Modo Suspención con Vosk."

    else:
        return f"Error: Unknown action '{action}'. Available: transcribe, transcribe_mic, list_models, transcribe_clipboard, languages, history"
