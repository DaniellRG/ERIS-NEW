"""face_sounds.py — SFX sintetizados para las reacciones de la cara.

Genera WAVs con Python puro (sin numpy) en face_sounds/ y los reproduce
con winsound (Windows). Si falla, hace silencio.
"""
import math
import random
import struct
import threading
import wave
from pathlib import Path

_RATE = 22050
_DIR = Path(__file__).resolve().parent / "face_sounds"
_DIR.mkdir(exist_ok=True)
_LOCK = threading.Lock()
_CACHE = {}

_WHITENOISE = random.Random(20260804)


def _tone(dur, f0, f1, amp, wobble=0.0):
    n = int(_RATE * dur)
    out = []
    for i in range(n):
        t = i / _RATE
        f = f0 + (f1 - f0) * (i / max(1, n))
        out.append(math.sin(math.tau * f * t + wobble * math.sin(math.tau * 3.1 * t)) * amp)
    return out


def _noise(dur, amp, lpf=0.1):
    n = int(_RATE * dur)
    out = []
    last = 0.0
    for _ in range(n):
        last += (_WHITENOISE.uniform(-1, 1) - last) * lpf
        out.append(last * amp)
    return out


def _burst(dur, f, amp, decay):
    n = int(_RATE * dur)
    out = []
    for i in range(n):
        t = i / _RATE
        e = math.exp(-t * decay)
        out.append((math.sin(math.tau * f * t) + _WHITENOISE.uniform(-0.4, 0.4)) * amp * e)
    return out


def _env(samples, a=0.05, r=None):
    n = len(samples)
    if r is None:
        r = n * 0.6
    at = int(a * _RATE)
    rt = int(r)
    out = []
    for i, s in enumerate(samples):
        e = 1.0
        if i < at and at > 0:
            e = i / at
        if n - i < rt and rt > 0:
            e = min(e, (n - i) / rt)
        out.append(s * e)
    return out


def _pad(samples, secs):
    return samples + [0.0] * int(secs * _RATE)


def _build(name):
    if name == "sigh":
        s = _env(_noise(1.0, 0.5, lpf=0.05))
    elif name == "deep_sigh":
        s = _env(_noise(1.7, 0.45, lpf=0.04), a=0.12, r=0.9)
    elif name == "yawn":
        s = _env(_tone(1.3, 170, 85, 0.42, wobble=0.8))
    elif name == "flinch":
        s = _env(_noise(0.24, 0.7, lpf=0.2), a=0.01, r=0.18)
    elif name == "laugh":
        s = []
        for k in range(6):
            s += _burst(0.09, 330 + k * 35, 0.5, 42)
            s += _pad([], 0.05)
        s = _env(s, a=0.01)
    elif name == "sneeze":
        s = _burst(0.12, 320, 0.5, 22)
        s += _tone(0.32, 820, 150, 0.6) + _noise(0.32, 0.4, lpf=0.3)
        s = _env(s, a=0.01, r=0.3)
    elif name == "hiccup":
        s = _burst(0.09, 520, 0.45, 30) + _pad([], 0.22)
        s += _burst(0.08, 500, 0.4, 30) + _pad([], 0.12)
        s = _env(s, a=0.005)
    elif name == "cough":
        s = _env(_noise(0.4, 0.6, lpf=0.25), a=0.01, r=0.3)
    elif name == "cry":
        s = _env(_tone(1.4, 300, 210, 0.22, wobble=2.2), a=0.1, r=0.9)
    else:
        return None
    return s


def ensure(name):
    p = _DIR / f"{name}.wav"
    if p.exists():
        return p
    with _LOCK:
        if p.exists():
            return p
        s = _build(name)
        if not s:
            return None
        data = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32000)) for v in s)
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(_RATE)
            w.writeframes(data)
    return p


def play(name):
    try:
        import winsound
        p = ensure(name)
        if p:
            winsound.PlaySound(str(p), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass


def stop():
    try:
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass
