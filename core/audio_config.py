import json
import time

from core.logging_setup import API_CONFIG_PATH

LIVE_MODEL          = "models/gemini-3.1-flash-live-preview"

# Modelos alternativos para fallback cuando el primario falla (error 1008)
LIVE_MODEL_FALLBACKS = [
    "models/gemini-2.5-flash-native-audio-preview-12-2025",
    "models/gemini-2.5-flash-native-audio-latest",
]
_live_model_index = 0  # índice del modelo actual en uso
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 128      # 8ms chunks — mic input (keep small for low latency)
PLAY_CHUNK_SIZE     = 240      # 10ms chunks — playback (smaller = lower latency)

_cached_api_key: str | None = None

_device_cache: dict = {"ts": 0.0, "devs": None}
_DEVICE_CACHE_TTL = 5.0


def _cached_devices() -> list[dict]:
    """Lista de dispositivos de audio con cache TTL (enumerar es costoso)."""
    import sounddevice as sd
    now = time.monotonic()
    c = _device_cache
    if c["devs"] is None or now - c["ts"] > _DEVICE_CACHE_TTL:
        c["devs"] = sd.query_devices()
        c["ts"] = now
    return c["devs"]


def resolve_device(name_sub: str, kind: str = "input") -> int | None:
    """Find a device index by name substring (e.g. 'HAYLOU'). Returns None if not found."""
    for i, d in enumerate(_cached_devices()):
        if name_sub.lower() in d["name"].lower():
            if kind == "input" and d["max_input_channels"] > 0:
                return i
            if kind == "output" and d["max_output_channels"] > 0:
                return i
    return None


def _find_input_by_name(name_sub: str) -> int | None:
    if not name_sub:
        return None
    try:
        for i, d in enumerate(_cached_devices()):
            if name_sub.lower() in d["name"].lower() and d["max_input_channels"] > 0:
                return i
    except Exception:
        pass
    return None


def _can_open_mic(idx: int | None) -> bool:
    """True si el dispositivo abre de verdad como micro a SEND_SAMPLE_RATE."""
    import sounddevice as sd
    try:
        s = sd.InputStream(
            device=idx,
            samplerate=SEND_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        s.start()
        s.stop()
        s.close()
        return True
    except Exception:
        return False


def _can_open_out(idx: int | None) -> bool:
    """True si el dispositivo abre de verdad como salida a RECEIVE_SAMPLE_RATE."""
    import sounddevice as sd
    try:
        s = sd.RawOutputStream(
            device=idx,
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=PLAY_CHUNK_SIZE,
        )
        s.start()
        s.stop()
        s.close()
        return True
    except Exception:
        return False


def _device_name(idx: int | None) -> str:
    if idx is None:
        return ""
    try:
        devs = _cached_devices()
        if 0 <= idx < len(devs):
            return str(devs[idx]["name"])
    except Exception:
        pass
    import sounddevice as sd
    try:
        return str(sd.query_devices(idx)["name"])
    except Exception:
        return ""


_VIRTUAL_HINT = ("virtual", "sonar", "monitor", "stereo mix", "what u hear",
                 "loopback", "mapper", "primario", "primary", "asignador",
                 "wave out", "wave in")
_OUTPUT_BAD = _VIRTUAL_HINT + ("spdif", "digital", "hdmi", "nvidia", "microphone")
_INPUT_HINT = ("mic", "micro", "micrófono", "headset", "headphone", "auricular",
               "handsfree", "hands-free", "earbud", "buds", "capture", "entrada")
_OUTPUT_HINT = ("speaker", "altavoz", "parlante", "headset", "headphone",
                "auricular", "handsfree", "hands-free", "earbud", "output", "salida")


def _score_device(idx: int, kind: str) -> int:
    """Puntúa un dispositivo: físicos y nombres que suenan a mic/salida suman."""
    name = _device_name(idx).lower()
    s = 0
    bad = _OUTPUT_BAD if kind == "output" else _VIRTUAL_HINT
    if any(v in name for v in bad):
        s -= 5
    else:
        s += 3
    hints = _INPUT_HINT if kind == "input" else _OUTPUT_HINT
    if any(h in name for h in hints):
        s += 2
    return s


def _default_index(kind: str) -> int | None:
    import sounddevice as sd
    try:
        d = sd.default.device
        if isinstance(d, (tuple, list)):
            idx = d[0] if kind == "input" else d[1]
        else:
            idx = d
        if idx is not None and idx != -1:
            return int(idx)
    except Exception:
        pass
    return None


def _ordered_candidates(kind: str, cfg: dict) -> list[int]:
    """Candidatos en orden de prioridad: config -> default de Windows -> resto.

    El resto se puntúa (físicos y con nombre sugestivo primero); no depende de
    marcas concretas, así que funciona en cualquier máquina/micro conectado.
    """
    idx_key = "mic_device" if kind == "input" else "speaker_device"
    name_key = "mic_device_name" if kind == "input" else "speaker_device_name"

    cands: list[int] = []
    if cfg.get(idx_key):
        try:
            idx = int(cfg[idx_key])
            name = cfg.get(name_key)
            full = _device_name(idx)
            if not name or name.lower() in full.lower():
                cands.append(idx)
        except Exception:
            pass

    dflt = _default_index(kind)
    if dflt is not None:
        cands.append(dflt)

    scored = []
    try:
        for i, d in enumerate(_cached_devices()):
            if kind == "input" and d["max_input_channels"] <= 0:
                continue
            if kind == "output" and d["max_output_channels"] <= 0:
                continue
            scored.append((_score_device(i, kind), i))
    except Exception:
        pass
    scored.sort(key=lambda t: t[0], reverse=True)
    cands.extend(i for _, i in scored)

    seen: set[int] = set()
    ordered = []
    for i in cands:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered


def resolve_mic() -> int | None:
    """Detecta automáticamente cualquier micro conectado, sin marcas fijas.

    Orden: mic_device de config (si sigue válido) -> default de Windows ->
    mics físicos (los que suenan a mic/auricular primero) -> cualquier entrada
    que abra a 16 kHz. El que funcione se persiste en config/api_keys.json.
    """
    cfg = {}
    try:
        from memory.config_manager import load_api_keys, save_api_keys
        cfg = load_api_keys() or {}
    except Exception:
        pass
    for idx in _ordered_candidates("input", cfg):
        if _can_open_mic(idx):
            try:
                if cfg.get("mic_device") != idx:
                    cfg["mic_device"] = idx
                    cfg["mic_device_name"] = _device_name(idx)
                    save_api_keys(cfg)
            except Exception:
                pass
            return idx
    return None


def resolve_speaker() -> int | None:
    """Detecta automáticamente cualquier salida conectada, sin marcas fijas.

    Orden: speaker_device de config (si sigue válido) -> default de Windows ->
    salidas físicas -> cualquier salida que abra a 24 kHz. Se persiste en config.
    """
    cfg = {}
    try:
        from memory.config_manager import load_api_keys, save_api_keys
        cfg = load_api_keys() or {}
    except Exception:
        pass
    for idx in _ordered_candidates("output", cfg):
        if _can_open_out(idx):
            try:
                if cfg.get("speaker_device") != idx:
                    cfg["speaker_device"] = idx
                    cfg["speaker_device_name"] = _device_name(idx)
                    save_api_keys(cfg)
            except Exception:
                pass
            return idx
    return None


def describe_audio_devices() -> list[str]:
    """Resumen legible de todos los dispositivos de audio conectados."""
    out = []
    try:
        devs = _cached_devices()
        for i, d in enumerate(devs):
            inn = d["max_input_channels"] > 0
            outn = d["max_output_channels"] > 0
            if not (inn or outn):
                continue
            kind = ("ENT " if inn else "    ") + ("SAL " if outn else "    ")
            out.append(f"[{i}] {d['name']}  {kind}  in={d['max_input_channels']} "
                       f"out={d['max_output_channels']}  {int(d['default_samplerate'])}Hz")
    except Exception as e:
        out.append(f"(error enumerando audio: {e})")
    return out


def audio_device_options(kind: str) -> list[tuple[str, str]]:
    """Dispositivos como (index_str, etiqueta) para un combo box.

    kind: "input" (micros) o "output" (altavoces/audífonos). Devuelve todas
    las opciones detectadas; el elemento "Auto" se agrega aparte en la UI.
    """
    opts: list[tuple[str, str]] = []
    seen: set[str] = set()
    try:
        devs = _cached_devices()
        for i, d in enumerate(devs):
            inn = d["max_input_channels"] > 0
            outn = d["max_output_channels"] > 0
            if kind == "input" and not inn:
                continue
            if kind == "output" and not outn:
                continue
            name = str(d["name"])
            if name in seen:
                continue
            seen.add(name)
            rate = int(d["default_samplerate"] or 0)
            icon = ("🎤" if inn and not outn else "🔊" if outn and not inn else "🔄")
            opts.append((str(i), f"{icon}  [{i}]  {name}  ({rate}Hz)"))
    except Exception:
        pass
    return opts


def get_device_name(idx: int | None) -> str:
    """Nombre legible de un dispositivo por índice ("" si no existe)."""
    return _device_name(idx)


_WAVEOUT_BAD = ("sonar", "microphone", "chat", "gaming", " media", "aux",
                "stream", "virtual", "spdif", "digital", "hdmi", "primario",
                "asignador", "mapper", "monitor", "wave")
_WAVEOUT_GOOD = ("altavoces", "altavoz", "speakers", "speaker", "headphones",
                 "headphone", "auricular", "earbud", "line out", "output")


def resolve_waveout() -> int | None:
    """Elige una salida física (winmm) que SÍ abra a 24 kHz, sin depender del
    default de Windows (que puede ser un loopback virtual tipo Sonar).

    Prioriza el dispositivo elegido en config (por nombre) y luego las salidas
    físicas (altavoces/auriculares). Descarta virtuales, SPDIF, HDMI y loops.
    """
    try:
        from core.win_audio_output import winmm_output_devices, winmm_probe
    except Exception:
        return None

    cfg = {}
    try:
        from memory.config_manager import load_api_keys
        cfg = load_api_keys() or {}
    except Exception:
        pass
    preferred = (cfg.get("speaker_device_name") or "").lower()

    try:
        devs = winmm_output_devices()
    except Exception:
        return None

    scored = []
    for d in devs:
        name = d["name"].lower()
        # Skip bad devices UNLESS the user explicitly selected them in config
        if any(b in name for b in _WAVEOUT_BAD):
            if not (preferred and preferred in name):
                continue
        s = 4
        if any(g in name for g in _WAVEOUT_GOOD):
            s += 3
        if preferred and preferred in name:
            s += 12
        scored.append((s, d["index"], d["name"]))

    scored.sort(key=lambda t: t[0], reverse=True)
    for _s, idx, _name in scored:
        if winmm_probe(idx):
            return idx
    return None


def get_api_key() -> str:
    global _cached_api_key
    if _cached_api_key:
        return _cached_api_key
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        _cached_api_key = json.load(f)["gemini_api_key"]
    return _cached_api_key


ERIS_VOICES = {
    "Aoede":  ("Femenina", "Cálida y sofisticada — ideal para asistente IA — RECOMENDADA PARA ERIS"),
    "Kore":   ("Femenina", "Suave y precisa"),
    "Leda":   ("Femenina", "Natural y fluida"),
    "Zephyr": ("Femenina", "Dinámica y expresiva"),
    "Charon": ("Masculina", "Profunda y seria — voz original de ERIS"),
    "Puck":   ("Masculina", "Ágil y versátil"),
    "Fenrir": ("Masculina", "Grave y autoritaria"),
    "Orus":   ("Masculina", "Clásica y equilibrada"),
}


def get_eris_voice() -> str:
    try:
        cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        voice = cfg.get("eris_voice", cfg.get("jarvis_voice", "Aoede"))
        # Strip suffixes like " (Warm)" or " (Femenina)" in case UI saved display text
        if " (" in voice:
            voice = voice.split(" (")[0]
        return voice
    except Exception:
        return "Aoede"
