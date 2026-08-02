import asyncio
import json
import math
import os
import random
import subprocess
import struct
import tempfile
import time
from datetime import datetime
from pathlib import Path

try:
    import imageio_ffmpeg
    _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _FFMPEG = "ffmpeg"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_FILE = DATA_DIR / "canciones_history.json"

_GENEROS = [
    "pop", "rock", "balada", "reggaeton", "vallenato", "salsa",
    "electronica", "rap", "cumbia", "bolero", "jazz", "clasica",
    "folk", "indie", "r&b", "soul",
]

_ESTILOS_VOZ = [
    "dulce", "poderosa", "suave", "alegre", "melancolica",
    "ronca", "angelical", "fuerte", "susurrada", "vibrante",
]

# Melody patterns per genre: list of (semitones_from_base, duration_multiplier)
_MELODIAS = {
    "pop":        [(0,1),(2,1),(4,1),(5,1),(7,2),(5,1),(4,1),(2,2)],
    "rock":       [(0,2),(3,1),(5,1),(7,2),(5,1),(3,1),(0,2)],
    "balada":     [(0,2),(2,2),(4,2),(5,2),(7,4),(5,2),(4,2),(2,2),(0,4)],
    "reggaeton":  [(0,1),(1,1),(2,1),(3,1),(4,2),(3,1),(2,1),(1,2)],
    "vallenato":  [(0,1),(2,1),(4,1),(5,2),(7,2),(5,1),(4,1),(2,1),(0,2)],
    "salsa":      [(0,1),(2,1),(4,2),(5,1),(7,2),(5,1),(4,2),(2,1),(0,1)],
    "electronica":[(0,1),(4,1),(7,1),(12,2),(7,1),(4,1),(0,2)],
    "rap":        [(0,1),(0,1),(1,1),(1,1),(2,1),(2,1),(0,2)],
    "cumbia":     [(0,1),(2,1),(3,1),(5,2),(3,1),(2,1),(0,2)],
    "bolero":     [(0,2),(3,2),(5,2),(7,2),(5,2),(3,2),(0,4)],
    "jazz":       [(0,2),(2,1),(5,1),(7,2),(9,2),(7,2),(5,1),(2,1),(0,2)],
    "clasica":    [(0,3),(2,2),(4,2),(5,3),(7,3),(5,2),(4,2),(2,2),(0,4)],
    "folk":       [(0,2),(2,1),(4,1),(5,2),(7,2),(5,1),(4,1),(2,2),(0,2)],
    "indie":      [(0,2),(2,2),(3,2),(5,2),(7,2),(5,2),(3,2),(0,2)],
    "r&b":        [(0,2),(2,1),(4,2),(5,2),(7,2),(5,2),(4,1),(2,1),(0,2)],
    "soul":       [(0,2),(4,2),(5,2),(7,2),(9,2),(7,2),(5,2),(4,2),(0,2)],
}

_ESTILO_PARAMS = {
    "dulce":      {"voice": "es-AR-ElenaNeural", "rate": "+5%", "volume": "+20%", "base_pitch": "+2st"},
    "poderosa":   {"voice": "es-MX-DaliaNeural", "rate": "+10%", "volume": "+30%", "base_pitch": "-2st"},
    "suave":      {"voice": "es-AR-ElenaNeural", "rate": "-10%", "volume": "-10%", "base_pitch": "+1st"},
    "alegre":     {"voice": "es-MX-DaliaNeural", "rate": "+15%", "volume": "+20%", "base_pitch": "+3st"},
    "melancolica":{"voice": "es-AR-ElenaNeural", "rate": "-15%", "volume": "-10%", "base_pitch": "-1st"},
    "ronca":      {"voice": "es-ES-AlvaroNeural", "rate": "+5%", "volume": "+10%", "base_pitch": "-5st"},
    "angelical":  {"voice": "es-AR-ElenaNeural", "rate": "-5%", "volume": "+10%", "base_pitch": "+5st"},
    "fuerte":     {"voice": "es-MX-DaliaNeural", "rate": "+10%", "volume": "+40%", "base_pitch": "-3st"},
    "susurrada":  {"voice": "es-AR-ElenaNeural", "rate": "-20%", "volume": "-20%", "base_pitch": "0st"},
    "vibrante":   {"voice": "es-MX-DaliaNeural", "rate": "+5%", "volume": "+25%", "base_pitch": "+4st"},
}


def _load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"canciones": []}
    return {"canciones": []}


def _save_history(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_desktop() -> Path:
    try:
        from actions.path_helper import get_desktop_path
        return Path(get_desktop_path())
    except Exception:
        return Path.home() / "Desktop"


def _generate_melody_ssml(lyrics: str, genero: str, estilo_voz: str) -> str:
    lines = [l.strip() for l in lyrics.strip().split("\n") if l.strip()]
    if not lines:
        return ""

    params = _ESTILO_PARAMS.get(estilo_voz, _ESTILO_PARAMS["dulce"])
    melody = _MELODIAS.get(genero, _MELODIAS["pop"])
    base_pitch = params["base_pitch"]
    rate = params["rate"]
    volume = params["volume"]

    ssml = ['<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis">']
    ssml.append(f'<prosody rate="{rate}" volume="{volume}">')

    note_idx = 0
    for line in lines:
        words = line.split()
        if not words:
            ssml.append(f'<break time="400ms"/>')
            continue

        # Distribute melody notes across words in this line
        notes_per_word = max(1, len(melody) // max(1, len(words)))
        for i, word in enumerate(words):
            note_offset, duration = melody[(note_idx + i) % len(melody)]
            semitones = _parse_semitones(base_pitch) + note_offset
            pitch_str = f"{semitones:+d}st"
            dur_ms = int(150 * duration)
            ssml.append(
                f'<prosody pitch="{pitch_str}" duration="{dur_ms}ms">{word}</prosody>'
            )
            if i < len(words) - 1:
                ssml.append(f'<break time="{int(80 * duration)}ms"/>')

        note_idx = (note_idx + len(words)) % len(melody)
        ssml.append(f'<break time="500ms"/>')

    ssml.append("</prosody>")
    ssml.append("</speak>")
    return "\n".join(ssml)


def _parse_semitones(pitch_str: str) -> int:
    s = pitch_str.replace("st", "").strip()
    try:
        return int(s)
    except ValueError:
        return 0


def _generate_instrumental(duration_sec: float, genero: str, sample_rate: int = 24000) -> bytes:
    """Generate a simple instrumental backing track (chords + rhythm)."""
    num_samples = int(sample_rate * duration_sec)
    import numpy as np
    t = np.arange(num_samples) / sample_rate

    # Chord progressions per genre (frequencies)
    chords_map = {
        "pop":        [261.63, 329.63, 392.00, 349.23],  # C, E, G, F
        "rock":       [261.63, 293.66, 349.23, 392.00],  # C, D, F, G
        "balada":     [261.63, 329.63, 392.00, 440.00],  # C, E, G, A
        "reggaeton":  [220.00, 261.63, 329.63, 293.66],  # A, C, E, D
        "vallenato":  [261.63, 293.66, 329.63, 392.00],  # C, D, E, G
        "salsa":      [261.63, 329.63, 349.23, 392.00],  # C, E, F, G
        "electronica":[220.00, 277.18, 329.63, 440.00],  # A, C#, E, A
        "cumbia":     [261.63, 329.63, 392.00, 440.00],  # C, E, G, A
        "bolero":     [261.63, 293.66, 329.63, 392.00],  # C, D, E, G
        "jazz":       [261.63, 329.63, 392.00, 466.16],  # C, E, G, Bb
        "clasica":    [261.63, 329.63, 392.00, 523.25],  # C, E, G, C5
        "folk":       [261.63, 293.66, 329.63, 349.23],  # C, D, E, F
        "indie":      [261.63, 329.63, 349.23, 440.00],  # C, E, F, A
        "r&b":        [220.00, 261.63, 329.63, 392.00],  # A, C, E, G
        "soul":       [220.00, 261.63, 329.63, 349.23],  # A, C, E, F
        "rap":        [220.00, 246.94, 261.63, 293.66],  # A, B, C, D
    }
    chords = chords_map.get(genero, chords_map["pop"])
    chord_duration = 2.0  # seconds per chord
    total = np.zeros(num_samples, dtype=np.float64)

    for ci, freq in enumerate(chords):
        start = int(ci * chord_duration * sample_rate) % num_samples
        end = min(start + int(chord_duration * sample_rate), num_samples)
        seg = t[start:end]
        seg_t = seg - seg[0]
        # Soft attack/release
        env = np.sin(np.pi * seg_t / (chord_duration * 0.1))
        env = np.clip(env, 0, 1)
        # Sine + triangle wave for warmth
        chord_wave = 0.3 * np.sin(2 * np.pi * freq * seg_t)
        chord_wave += 0.15 * np.sin(2 * np.pi * freq * 2 * seg_t)
        chord_wave += 0.1 * np.sin(2 * np.pi * freq * 3 * seg_t)
        # Add octave
        chord_wave += 0.15 * np.sin(2 * np.pi * (freq / 2) * seg_t)
        total[start:end] += chord_wave * env * 0.5

    # Rhythm pulse
    bpm = {"pop":120, "rock":130, "balada":70, "reggaeton":95, "vallenato":110, "salsa":100,
           "electronica":128, "rap":90, "cumbia":100, "bolero":75, "jazz":80, "clasica":90,
           "folk":105, "indie":115, "r&b":85, "soul":75}
    tempo = bpm.get(genero, 100)
    beat_interval = 60.0 / tempo
    kick_t = np.arange(0, duration_sec, beat_interval)
    for bt in kick_t:
        idx = int(bt * sample_rate)
        if idx < num_samples:
            env_len = int(0.05 * sample_rate)
            end_idx = min(idx + env_len, num_samples)
            env_len = end_idx - idx
            env = np.linspace(1.0, 0.0, env_len)
            total[idx:end_idx] += env * 0.3 * np.sin(2 * np.pi * 60 * t[idx:end_idx])

    total = np.clip(total, -1, 1)
    pcm = (total * 32767 * 0.3).astype(np.int16).tobytes()
    return pcm


def _pcm_to_wav(pcm: bytes, sr: int = 24000) -> bytes:
    nchan, bps = 1, 16
    br = sr * nchan * bps // 8
    ba = nchan * bps // 8
    ds = len(pcm)
    hdr = struct.pack(
        "<4sI4s4sIHHIIHH",
        b"RIFF", 36 + ds, b"WAVE",
        b"fmt ", 16, 1, nchan, sr, br, ba, bps,
    )
    return hdr + struct.pack("<4sI", b"data", ds) + pcm


async def _generate_song_audio(lyrics: str, genero: str, estilo_voz: str) -> tuple[bytes, float]:
    import edge_tts
    ssml = _generate_melody_ssml(lyrics, genero, estilo_voz)
    params = _ESTILO_PARAMS.get(estilo_voz, _ESTILO_PARAMS["dulce"])
    voice = params["voice"]

    communicate = edge_tts.Communicate(ssml, voice)
    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])

    if not audio_chunks:
        return b"", 0.0

    raw = b"".join(audio_chunks)
    proc = await asyncio.create_subprocess_exec(
        _FFMPEG, "-y", "-i", "pipe:0",
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "24000", "-ac", "1",
        "pipe:1",
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    vocal_pcm, _ = await proc.communicate(input=raw)
    vocal_dur = len(vocal_pcm) / (24000 * 2)

    instrumental_pcm = _generate_instrumental(vocal_dur, genero)

    # Mix vocal + instrumental
    import numpy as np
    vocal = np.frombuffer(vocal_pcm, dtype=np.int16).astype(np.float64)
    inst = np.frombuffer(instrumental_pcm, dtype=np.int16).astype(np.float64)
    min_len = min(len(vocal), len(inst))
    vocal = vocal[:min_len]
    inst = inst[:min_len]
    mixed = vocal * 1.0 + inst * 0.35
    mixed = np.clip(mixed, -32767, 32767).astype(np.int16)
    return mixed.tobytes(), vocal_dur


def _play_file(filepath: str) -> str:
    """Play any media file using the default OS player."""
    path = Path(filepath)
    if not path.exists():
        return f"No encontré el archivo: {path}"
    try:
        os.startfile(str(path))
        return f"Reproduciendo: {path.name}"
    except Exception:
        pass
    try:
        import subprocess
        subprocess.Popen(["cmd", "/c", "start", "", str(path)])
        return f"Reproduciendo: {path.name}"
    except Exception as e:
        return f"No pude reproducir {path.name}: {str(e)[:80]}"


def cancion_generator(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "help").lower().strip()
    titulo = params.get("titulo", params.get("title", "mi cancion")).strip()
    letra = params.get("letra", params.get("lyrics", "")).strip()
    genero = params.get("genero", params.get("genre", "pop")).lower().strip()
    estilo_voz = params.get("estilo_voz", params.get("voice_style", "dulce")).lower().strip()
    output_path = params.get("output_path", "")

    if action in ("generos", "genres"):
        return "Géneros: " + ", ".join(_GENEROS)

    if action in ("estilos", "voice_styles"):
        return "Estilos de voz: " + ", ".join(_ESTILOS_VOZ)

    if action == "generar_letra":
        tema = params.get("tema", params.get("topic", ""))
        if not tema:
            return "Necesito un tema. Usá 'tema'."
        return (
            f"Voy a crear la letra sobre '{tema}' en estilo {genero}...\n\n"
            f"[TEMA: {tema} | GÉNERO: {genero} | VOZ: {estilo_voz}]\n"
            f"Para generar el audio usá action=componer con la letra."
        )

    if action in ("componer", "generar", "create"):
        start = time.time()
        if not letra:
            return "Necesito la letra. Usá 'letra' con el texto."

        if output_path:
            out = Path(output_path)
            if out.suffix.lower() not in (".wav", ".mp3"):
                out = out / f"{titulo.replace(' ', '_')}.wav"
        else:
            desk = _get_desktop() / "ERIS_Canciones"
            desk.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = desk / f"{titulo.replace(' ', '_')}_{ts}.wav"
        out.parent.mkdir(parents=True, exist_ok=True)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            pcm, duracion = loop.run_until_complete(
                _generate_song_audio(letra, genero, estilo_voz)
            )
            loop.close()
        except Exception as e:
            return f"Error generando canción: {str(e)[:120]}"

        if not pcm:
            return "No se pudo generar audio. Revisá la letra e intentá de nuevo."

        wav_bytes = _pcm_to_wav(pcm)
        out.write_bytes(wav_bytes)
        elapsed = time.time() - start

        history = _load_history()
        history["canciones"].append({
            "titulo": titulo, "genero": genero,
            "estilo_voz": estilo_voz, "archivo": str(out),
            "created_at": datetime.now().isoformat(),
            "tiempo_generacion": round(elapsed, 1),
            "duracion": round(duracion, 1),
        })
        _save_history(history)

        return (
            f"Canción creada: {out}\n"
            f"Título: {titulo} | Género: {genero} | Voz: {estilo_voz}\n"
            f"Duración: {duracion:.1f}s | Generado en {elapsed:.1f}s\n\n"
            f"Para escucharla decime: reproducí {out.name}"
        )

    if action in ("play", "reproducir", "reproducir_ultima"):
        if action == "reproducir_ultima":
            history = _load_history()
            if not history["canciones"]:
                return "No hay canciones generadas aún."
            fp = history["canciones"][-1]["archivo"]
        else:
            fp = params.get("file_path", params.get("path", ""))
            if not fp:
                history = _load_history()
                if history["canciones"]:
                    fp = history["canciones"][-1]["archivo"]
        if not fp:
            return "No hay canción para reproducir. Usá el reproductor de música con action=play y path=..."
        return _play_file(fp)

    if action == "history":
        history = _load_history()
        if not history["canciones"]:
            return "No hay canciones generadas."
        lines = []
        for i, c in enumerate(history["canciones"][-10:], 1):
            t = c.get("titulo", "sin título")
            g = c.get("genero", "?")
            d = c.get("duracion", "?")
            lines.append(f"{i}. {t} ({g}) — {d}s — {Path(c['archivo']).name}")
        return "Últimas canciones:\n" + "\n".join(lines)

    return (
        "Acciones:\n"
        "  generar_letra — Crear letra (tema, genero, estilo_voz)\n"
        "  componer — Generar audio cantado (letra, titulo, genero, estilo_voz)\n"
        "  reprodicir_ultima / play — Reproducir última canción\n"
        "  history — Ver historial\n"
        "  generos / estilos — Ver opciones disponibles\n"
        "Parámetros: letra, titulo, genero, estilo_voz, output_path"
    )
