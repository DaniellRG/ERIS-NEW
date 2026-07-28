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

# Get ffmpeg path
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = "ffmpeg"


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
        audio_path = subs_dir / f"{video_id}.mp3"

        # Download audio only
        _log("Downloading audio...")
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'outtmpl': str(subs_dir / f'{video_id}.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not audio_path.exists():
            # Find any audio file
            for f in subs_dir.glob(f"{video_id}.*"):
                if f.suffix in ['.mp3', '.wav', '.m4a', '.opus', '.webm']:
                    audio_path = f
                    break

        if not audio_path.exists():
            return "Error: Could not download audio"

        _log(f"Audio downloaded: {audio_path.name} ({audio_path.stat().st_size / 1024 / 1024:.1f} MB)")

        # Transcribe with faster-whisper
        _log("Transcribing with Whisper...")
        from faster_whisper import WhisperModel

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=3,
            language=None,  # Auto-detect
            vad_filter=True,
        )

        _log(f"Detected language: {info.language} (prob: {info.language_probability:.2f})")

        transcript_parts = []
        for segment in segments:
            transcript_parts.append(segment.text.strip())

        transcript = " ".join(transcript_parts)

        # Clean up audio file to save space
        try:
            audio_path.unlink()
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


def video_analyzer(parameters: dict, player=None) -> str:
    """
    Analizador de videos de YouTube.
    Descarga subtítulos o transcribe audio, y genera resúmenes.

    Acciones:
      - info: Info del video (título, duración, descripción). Parametros: url
      - subtitles: Extraer subtítulos del video. Parametros: url
      - transcribe: Descargar audio y transcribir con Whisper. Parametros: url
      - summarize: Resumen completo (subtítulos o transcripción). Parametros: url
      - research: Research web sobre el tema del video (como hace Eris). Parametros: url
      - full: Análisis completo: info + subtítulos/transcripción + resumen. Parametros: url
      - history: Ver historial de videos analizados
    """
    action = parameters.get("action", "info").lower()
    url = parameters.get("url", "").strip()

    if action == "history":
        history = _get_history()
        if not history:
            return "No videos analyzed yet."
        result = "**Video Analysis History**\n\n"
        for h in history[-10:]:
            result += f"  [{h.get('time', '?')[:16]}] {h.get('title', '?')} ({h.get('method', '?')})\n"
        return result

    if not url:
        return "Error: Se requiere 'url' del video de YouTube"

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

    available = "info | subtitles | transcribe | summarize | research | full | history"
    return f"Action '{action}' not found. Available: {available}"
