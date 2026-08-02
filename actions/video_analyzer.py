# -*- coding: utf-8 -*-
"""
video_analyzer.py — Analizador de videos de YouTube.
Descarga videos, extrae subtítulos, transcribe audio con Whisper,
y genera resúmenes con IA. También hace research web como fallback.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VIDEO_CACHE = DATA_DIR / "video_cache"
HISTORY_FILE = DATA_DIR / "video_history.json"

# Get ffmpeg/ffprobe path
try:
    import imageio_ffmpeg
    _FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    _FFMPEG_DIR = os.path.dirname(_FFMPEG_EXE)
    FFMPEG_PATH = _FFMPEG_EXE
    _FFMPEG_LOCATION = _FFMPEG_DIR
    # Ensure ffprobe exists alongside ffmpeg
    _ffprobe = os.path.join(_FFMPEG_DIR, "ffprobe.exe")
    if not os.path.exists(_ffprobe):
        try:
            import shutil
            shutil.copy2(_FFMPEG_EXE, _ffprobe)
        except Exception:
            pass
except Exception:
    FFMPEG_PATH = "ffmpeg"
    _FFMPEG_LOCATION = None


def _log(msg):
    print(f"[video_analyzer] {msg}")


def _get_history() -> list:
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_history(entry: dict):
    history = _get_history()
    history.append(entry)
    VIDEO_CACHE.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history[-100:], indent=2, ensure_ascii=False), encoding="utf-8")


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def _get_video_info(url: str) -> dict:
    """Get video metadata without downloading."""
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
            'ffmpeg_location': _FFMPEG_LOCATION,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", ""),
                "description": info.get("description", "")[:2000],
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", ""),
                "upload_date": info.get("upload_date", ""),
                "view_count": info.get("view_count", 0),
                "like_count": info.get("like_count", 0),
                "thumbnail": info.get("thumbnail", ""),
                "categories": info.get("categories", []),
                "tags": info.get("tags", []),
                "subtitles": list(info.get("subtitles", {}).keys()),
                "auto_captions": list(info.get("automatic_captions", {}).keys()),
            }
    except Exception as e:
        return {"error": str(e)}


def _download_subtitles(url: str, video_id: str) -> str:
    """Try to download manual or auto-generated subtitles."""
    try:
        import yt_dlp
        subs_dir = VIDEO_CACHE / video_id
        subs_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['es', 'en', 'pt', 'fr', 'de', 'auto'],
            'subtitlesformat': 'vtt/srt/best',
            'outtmpl': str(subs_dir / '%(id)s.%(ext)s'),
            'ffmpeg_location': _FFMPEG_LOCATION,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            ydl.download([url])

        # Find downloaded subtitle files
        for ext in ['vtt', 'srt', 'ass']:
            for f in subs_dir.glob(f"*.{ext}"):
                content = f.read_text(encoding="utf-8", errors="replace")
                # Clean subtitle formatting
                cleaned = _clean_subtitle(content)
                if len(cleaned.strip()) > 50:
                    return cleaned
        return ""
    except Exception as e:
        _log(f"Subtitle download failed: {e}")
        return ""


def _clean_subtitle(content: str) -> str:
    """Clean VTT/SRT subtitle formatting."""
    # Remove VTT headers and timestamps
    lines = content.split("\n")
    cleaned = []
    seen = set()
    for line in lines:
        line = line.strip()
        # Skip timestamps, headers, empty lines
        if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r'^[\d:,.]+ --> [\d:,.]+', line):
            continue
        if re.match(r'^\d+$', line):
            continue
        # Remove HTML tags
        line = re.sub(r'<[^>]+>', '', line)
        line = re.sub(r'&amp;', '&', line)
        line = re.sub(r'&lt;', '<', line)
        line = re.sub(r'&gt;', '>', line)
        line = re.sub(r'&#39;', "'", line)
        line = re.sub(r'&quot;', '"', line)
        # Deduplicate consecutive lines
        if line and line not in seen:
            seen.add(line)
            cleaned.append(line)
    return " ".join(cleaned)


def _transcribe_audio(url: str, video_id: str) -> str:
    """Download audio and transcribe with faster-whisper."""
    try:
        import yt_dlp
        subs_dir = VIDEO_CACHE / video_id
        subs_dir.mkdir(parents=True, exist_ok=True)

        # Download best audio stream (raw, no postprocessing)
        _log("Downloading audio...")
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'outtmpl': str(subs_dir / f'{video_id}.%(ext)s'),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find the downloaded audio file
        audio_path = None
        for f in subs_dir.glob(f"{video_id}.*"):
            if f.suffix in ['.mp3', '.wav', '.m4a', '.opus', '.webm', '.m4a']:
                audio_path = f
                break

        if not audio_path or not audio_path.exists():
            return "Error: Could not download audio"

        # Convert to mp3 with ffmpeg directly (avoids yt-dlp postprocessor ffprobe requirement)
        mp3_path = subs_dir / f"{video_id}.mp3"
        if audio_path.suffix != '.mp3':
            _log(f"Converting {audio_path.suffix} to mp3...")
            try:
                import subprocess
                subprocess.run(
                    [FFMPEG_PATH, '-i', str(audio_path), '-vn', '-acodec', 'libmp3lame',
                     '-ar', '16000', '-ac', '1', '-y', str(mp3_path)],
                    capture_output=True, timeout=300,
                )
                if mp3_path.exists():
                    audio_path = mp3_path
            except Exception as conv_e:
                _log(f"Conversion failed, using original: {conv_e}")

        if not audio_path.exists():
            return "Error: Audio file missing after download"

        _log(f"Audio: {audio_path.name} ({audio_path.stat().st_size / 1024 / 1024:.1f} MB)")

        # Transcribe with faster-whisper
        _log("Transcribing with Whisper...")
        from faster_whisper import WhisperModel

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=3,
            language=None,
            vad_filter=True,
        )

        _log(f"Detected language: {info.language} (prob: {info.language_probability:.2f})")

        transcript_parts = [segment.text.strip() for segment in segments]
        transcript = " ".join(transcript_parts)

        # Clean up audio files
        try:
            audio_path.unlink()
            if mp3_path and mp3_path.exists() and mp3_path != audio_path:
                mp3_path.unlink()
        except Exception:
            pass

        return transcript if transcript else "Error: Transcription empty"
    except Exception as e:
        _log(f"Transcription failed: {e}")
        return f"Error: {e}"


def _generate_summary(transcript: str, info: dict) -> str:
    """Generate a structured summary from transcript."""
    title = info.get("title", "Unknown")
    uploader = info.get("uploader", "Unknown")
    duration = info.get("duration", 0)
    mins = duration // 60
    secs = duration % 60

    summary = f"# Resumen: {title}\n\n"
    summary += f"**Canal:** {uploader}\n"
    summary += f"**Duración:** {mins}:{secs:02d}\n\n"

    if info.get("description"):
        desc = info["description"][:500]
        summary += f"**Descripción:** {desc}\n\n"

    if len(transcript) < 100:
        summary += f"**Transcripción:** {transcript}\n"
        return summary

    # Split into chunks for analysis
    words = transcript.split()
    chunk_size = 800
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))

    summary += f"**Transcripción completa:** ({len(words)} palabras)\n\n"

    # Key points extraction
    summary += "## Puntos clave\n\n"
    for i, chunk in enumerate(chunks[:10]):
        sentences = re.split(r'[.!?]+', chunk)
        key_sentences = [s.strip() for s in sentences if len(s.strip()) > 30][:3]
        for s in key_sentences:
            summary += f"- {s}.\n"
        summary += "\n"

    return summary


def _get_local_metadata(file_path: str) -> dict:
    import cv2
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        return {"error": "Could not open video file"}
    info = {
        "file": os.path.basename(file_path),
        "size_bytes": os.path.getsize(file_path),
        "fps": round(cap.get(cv2.CAP_PROP_FPS), 2),
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "duration_sec": round(cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1), 2),
    }
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    if fourcc:
        codec = chr(fourcc & 0xFF) + chr((fourcc >> 8) & 0xFF) + chr((fourcc >> 16) & 0xFF) + chr((fourcc >> 24) & 0xFF)
        info["codec"] = codec.strip()
    cap.release()
    return info


def _extract_keyframes(file_path: str, max_frames: int = 8) -> list:
    import cv2
    import base64
    import io
    from PIL import Image

    cap = cv2.VideoCapture(file_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release()
        return []
    step = max(total // max_frames, 1)
    frames_b64 = []
    for i in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        frames_b64.append(b64)
        if len(frames_b64) >= max_frames:
            break
    cap.release()
    return frames_b64


def _analyze_local_video(file_path: str, prompt: str = "") -> str:
    meta = _get_local_metadata(file_path)
    if "error" in meta:
        return f"Error: {meta['error']}"

    lines = [
        f"**Video Analysis: {meta['file']}**",
        "=" * 60,
        f"Size: {meta['size_bytes'] / 1024 / 1024:.1f} MB",
        f"Resolution: {meta['width']}x{meta['height']}",
        f"FPS: {meta['fps']}",
        f"Duration: {int(meta['duration_sec'] // 60)}:{int(meta['duration_sec'] % 60):02d}",
        f"Frames: {meta['frame_count']}",
    ]
    if meta.get("codec"):
        lines.append(f"Codec: {meta['codec']}")
    lines.append("")

    frames_b64 = _extract_keyframes(file_path)
    if not frames_b64:
        lines.append("Could not extract frames from video.")
        return "\n".join(lines)

    lines.append(f"Extracted {len(frames_b64)} keyframes for AI analysis.")
    lines.append("")

    # Send frames + prompt to Gemini
    try:
        from memory.config_manager import get_gemini_key
        import requests

        api_key = get_gemini_key()
        if not api_key:
            lines.append("Gemini API key not configured. Showing frames only.")
            return "\n".join(lines)

        user_prompt = prompt.strip() or (
            "Analiza este video frame por frame. Describe: "
            "1) Qué tipo de contenido es (tutorial, gameplay, entrevista, etc.) "
            "2) Escenas principales detectadas "
            "3) Texto visible importante "
            "4) Acciones o eventos clave "
            "Da un resumen completo en español."
        )

        parts = [{"text": user_prompt}]
        for b64 in frames_b64:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
        }
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            result_parts = candidates[0].get("content", {}).get("parts", [])
            ai_text = " ".join(p.get("text", "") for p in result_parts if "text" in p)
            if ai_text:
                lines.append("**AI Analysis:**")
                lines.append(ai_text)
            else:
                lines.append("Gemini returned empty response.")
        else:
            lines.append(f"Gemini error: {json.dumps(data, indent=2)[:500]}")
    except ImportError:
        lines.append("Could not import Gemini modules. Frame extraction only.")
    except Exception as e:
        lines.append(f"Gemini analysis error: {e}")

    return "\n".join(lines)


def video_analyzer(parameters: dict, player=None) -> str:
    """
    Analizador de videos de YouTube y archivos locales.

    Acciones:
      - info: Info del video de YouTube. Parametros: url
      - subtitles: Extraer subtítulos del video. Parametros: url
      - transcribe: Descargar audio y transcribir con Whisper. Parametros: url
      - summarize: Resumen completo (subtítulos o transcripción). Parametros: url
      - research: Research web sobre el tema del video. Parametros: url
      - full: Análisis completo: info + subtítulos/transcripción + resumen. Parametros: url
      - local: Analizar video local (.mp4, .avi, .mov, .mkv). Parametros: file, prompt (opcional)
      - local_audio: Extraer y transcribir audio de video local. Parametros: file
      - history: Historial de videos analizados
    """
    action = parameters.get("action", "info").lower()

    if action == "history":
        history = _get_history()
        if not history:
            return "No videos analyzed yet."
        result = "**Video Analysis History**\n\n"
        for h in history[-10:]:
            result += f"  [{h.get('time', '?')[:16]}] {h.get('title', '?')} ({h.get('method', '?')})\n"
        return result

    if action in ("local", "local_audio"):
        file_path = parameters.get("file", "")
        if not file_path:
            return "Error: Se requiere 'file' con la ruta del video local"
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"
        ext = Path(file_path).suffix.lower()
        if ext not in (".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v", ".mpg", ".mpeg"):
            return f"Error: Unsupported video format '{ext}'. Supported: .mp4, .avi, .mov, .mkv, .webm, .flv, .wmv, .m4v"

        if action == "local":
            result = _analyze_local_video(file_path, parameters.get("prompt", ""))
            _save_history({
                "time": datetime.now().isoformat(),
                "title": os.path.basename(file_path),
                "video_id": file_path,
                "method": "local_vision",
            })
            return result

        elif action == "local_audio":
            result = "**Transcribing audio from local video...**\n"
            try:
                from faster_whisper import WhisperModel
                import subprocess
                import tempfile

                # Extract audio to temp file using ffmpeg
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    audio_path = tmp.name
                _log("Extracting audio with ffmpeg...")
                subprocess.run(
                    [FFMPEG_PATH, "-i", file_path, "-vn", "-acodec", "libmp3lame", "-ar", "16000",
                     "-ac", "1", "-y", audio_path],
                    capture_output=True, timeout=600,
                )

                if not os.path.exists(audio_path):
                    return result + "Error: Could not extract audio"

                result += f"**Audio extracted:** {os.path.getsize(audio_path) / 1024:.1f} KB\n\n"
                _log("Transcribing with Whisper...")
                model = WhisperModel("base", device="cpu", compute_type="int8")
                segments, info = model.transcribe(audio_path, beam_size=3, language=None, vad_filter=True)
                transcript = " ".join(s.text.strip() for s in segments)
                try:
                    os.unlink(audio_path)
                except Exception:
                    pass
                result += f"**Transcript:** ({len(transcript)} chars, lang: {info.language})\n\n"
                result += transcript[:5000]
                if len(transcript) > 5000:
                    result += f"\n\n... (truncated, {len(transcript)} total chars)"
                return result
            except ImportError:
                return result + "Error: faster-whisper not installed"
            except Exception as e:
                return result + f"Error: {e}"

    url = parameters.get("url", "").strip()
    if not url:
        return "Error: Se requiere 'url' del video de YouTube o 'file' para video local.\nActions: info, subtitles, transcribe, summarize, research, full, local, local_audio, history"

    video_id = _extract_video_id(url)
    if not video_id:
        return f"No se pudo extraer el ID del video de: {url}"

    full_url = f"https://www.youtube.com/watch?v={video_id}"

    if action == "info":
        result = "**Video Info**\n\n"
        result += "Fetching metadata...\n"
        info = _get_video_info(full_url)
        if "error" in info:
            return f"Error: {info['error']}"
        result += f"**Title:** {info.get('title', '?')}\n"
        result += f"**Channel:** {info.get('uploader', '?')}\n"
        duration = info.get('duration', 0)
        result += f"**Duration:** {duration // 60}:{duration % 60:02d}\n"
        result += f"**Views:** {info.get('view_count', 0):,}\n"
        result += f"**Upload date:** {info.get('upload_date', '?')}\n"
        result += f"**Categories:** {', '.join(info.get('categories', []))}\n"
        result += f"**Tags:** {', '.join(info.get('tags', [])[:10])}\n"
        result += f"**Subtitles available:** {', '.join(info.get('subtitles', []))}\n"
        result += f"**Auto-captions:** {', '.join(info.get('auto_captions', [])[:5])}\n"
        if info.get('description'):
            result += f"\n**Description:**\n{info['description'][:800]}\n"
        return result

    elif action == "subtitles":
        result = "**Extracting subtitles...**\n\n"
        info = _get_video_info(full_url)
        subs = _download_subtitles(full_url, video_id)
        if subs:
            result += f"**Subtitles found!** ({len(subs)} chars)\n\n"
            result += subs[:5000]
            if len(subs) > 5000:
                result += f"\n\n... ({len(subs) - 5000} more chars)"
            _save_history({
                "time": datetime.now().isoformat(),
                "title": info.get("title", ""),
                "video_id": video_id,
                "method": "subtitles",
                "chars": len(subs),
            })
        else:
            result += "No subtitles found. Try `action=transcribe` for audio transcription."
        return result

    elif action == "transcribe":
        result = "**Transcribing audio with Whisper...**\n\n"
        result += "(This may take a while for long videos)\n\n"
        info = _get_video_info(full_url)
        transcript = _transcribe_audio(full_url, video_id)
        if transcript.startswith("Error"):
            return transcript
        result += f"**Transcript:** ({len(transcript)} chars)\n\n"
        result += transcript[:5000]
        if len(transcript) > 5000:
            result += f"\n\n... ({len(transcript) - 5000} more chars)"
        _save_history({
            "time": datetime.now().isoformat(),
            "title": info.get("title", ""),
            "video_id": video_id,
            "method": "whisper",
            "chars": len(transcript),
        })
        return result

    elif action == "summarize":
        result = "**Generating summary...**\n\n"
        info = _get_video_info(full_url)
        if "error" in info:
            return f"Error getting info: {info['error']}"

        # Try subtitles first
        _log("Trying subtitles...")
        transcript = _download_subtitles(full_url, video_id)
        method = "subtitles"

        if not transcript or len(transcript) < 100:
            _log("No subtitles, falling back to Whisper transcription...")
            transcript = _transcribe_audio(full_url, video_id)
            method = "whisper"

        if transcript.startswith("Error"):
            return f"Could not get transcript: {transcript}\n\nTry `action=research` for web-based analysis."

        summary = _generate_summary(transcript, info)
        _save_history({
            "time": datetime.now().isoformat(),
            "title": info.get("title", ""),
            "video_id": video_id,
            "method": method,
            "chars": len(transcript),
        })
        return summary

    elif action == "research":
        result = "**Web Research about this video**\n\n"
        info = _get_video_info(full_url)
        if "error" in info:
            return f"Error: {info['error']}"

        title = info.get("title", "")
        desc = info.get("description", "")[:300]
        result += f"**Title:** {title}\n"
        result += f"**Channel:** {info.get('uploader', '?')}\n"
        result += f"**Duration:** {info.get('duration', 0) // 60}:{info.get('duration', 0) % 60:02d}\n\n"

        result += "**Description:**\n"
        result += f"{desc}\n\n"

        # Try subtitles as context
        subs = _download_subtitles(full_url, video_id)
        if subs and len(subs) > 100:
            result += "**Subtitles/Transcript:**\n"
            result += subs[:3000]
            if len(subs) > 3000:
                result += f"\n... ({len(subs) - 3000} more chars)"
        else:
            result += "**Note:** No subtitles available. "
            result += "Use `action=summarize` or `action=transcribe` for full audio analysis.\n"

        _save_history({
            "time": datetime.now().isoformat(),
            "title": title,
            "video_id": video_id,
            "method": "research",
        })
        return result

    elif action == "full":
        result = "**Full Video Analysis**\n\n"
        info = _get_video_info(full_url)
        if "error" in info:
            return f"Error: {info['error']}"

        # Video info
        result += "## Video Info\n"
        result += f"**Title:** {info.get('title', '?')}\n"
        result += f"**Channel:** {info.get('uploader', '?')}\n"
        duration = info.get('duration', 0)
        result += f"**Duration:** {duration // 60}:{duration % 60:02d}\n"
        result += f"**Views:** {info.get('view_count', 0):,}\n\n"

        # Try to get transcript
        _log("Trying subtitles...")
        transcript = _download_subtitles(full_url, video_id)
        method = "subtitles"

        if not transcript or len(transcript) < 100:
            _log("No subtitles, trying Whisper...")
            transcript = _transcribe_audio(full_url, video_id)
            method = "whisper"

        if not transcript.startswith("Error") and len(transcript) > 100:
            # Generate summary
            summary = _generate_summary(transcript, info)
            result += summary
        else:
            result += "## No transcript available\n"
            result += "Could not get subtitles or transcribe audio.\n"
            result += "The video may be too long or have no audio.\n"

        _save_history({
            "time": datetime.now().isoformat(),
            "title": info.get("title", ""),
            "video_id": video_id,
            "method": method,
            "chars": len(transcript) if not transcript.startswith("Error") else 0,
        })
        return result

    available = "info | subtitles | transcribe | summarize | research | full | local | local_audio | history"
    return f"Action '{action}' not found. Available: {available}"
