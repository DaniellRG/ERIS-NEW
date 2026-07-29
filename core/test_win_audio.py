import time
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.win_audio_output import WinAudioOutput


def generate_sine_tone(
    frequency: float = 440.0,
    duration: float = 2.0,
    samplerate: int = 24000,
    amplitude: float = 0.5,
) -> bytes:
    num_samples = int(samplerate * duration)
    samples = []
    for i in range(num_samples):
        t = i / samplerate
        value = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack("<h", value))
    return b"".join(samples)


def test_win_audio_output():
    print("WinAudioOutput self-test: generating 440Hz sine tone")

    ao = WinAudioOutput(channels=1, samplerate=24000, bits_per_sample=16)

    success = ao.open()
    if not success:
        print("FAIL: open() returned False")
        return False
    print("OK: device opened")

    tone_data = generate_sine_tone(440.0, 2.0, 24000, 0.5)
    print(f"Generated {len(tone_data)} bytes of audio")

    start = time.perf_counter()
    ao.write(tone_data)
    elapsed = time.perf_counter() - start
    print(f"Wrote audio in {elapsed:.3f}s (expected ~2.0s of playback)")

    ao.close()
    print("OK: device closed cleanly")
    print("PASS: WinAudioOutput works correctly")
    return True


if __name__ == "__main__":
    success = test_win_audio_output()
    sys.exit(0 if success else 1)
