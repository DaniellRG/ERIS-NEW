import ctypes
import ctypes.wintypes
import time
import threading
from typing import Optional

winmm = ctypes.WinDLL("winmm")

WAVE_MAPPER = ctypes.c_uint(-1).value
WAVE_FORMAT_PCM = 1
CALLBACK_NULL = 0
WHDR_DONE = 0x00000001
WHDR_PREPARED = 0x00000002
MMSYSERR_NOERROR = 0
WAVERR_STILLPLAYING = 0x21


class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [
        ("wFormatTag", ctypes.wintypes.WORD),
        ("nChannels", ctypes.wintypes.WORD),
        ("nSamplesPerSec", ctypes.wintypes.DWORD),
        ("nAvgBytesPerSec", ctypes.wintypes.DWORD),
        ("nBlockAlign", ctypes.wintypes.WORD),
        ("wBitsPerSample", ctypes.wintypes.WORD),
        ("cbSize", ctypes.wintypes.WORD),
    ]


class WAVEHDR(ctypes.Structure):
    _fields_ = [
        ("lpData", ctypes.wintypes.LPSTR),
        ("dwBufferLength", ctypes.wintypes.DWORD),
        ("dwBytesRecorded", ctypes.wintypes.DWORD),
        ("dwUser", ctypes.c_size_t),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("dwLoops", ctypes.wintypes.DWORD),
        ("lpNext", ctypes.c_void_p),
        ("reserved", ctypes.c_size_t),
    ]


MMRESULT = ctypes.wintypes.UINT

_wave_out_open = winmm.waveOutOpen
_wave_out_open.restype = MMRESULT
_wave_out_open.argtypes = [
    ctypes.POINTER(ctypes.wintypes.HANDLE),
    ctypes.wintypes.UINT,
    ctypes.POINTER(WAVEFORMATEX),
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.wintypes.DWORD,
]

_wave_out_close = winmm.waveOutClose
_wave_out_close.restype = MMRESULT
_wave_out_close.argtypes = [ctypes.wintypes.HANDLE]

_wave_out_prepare_header = winmm.waveOutPrepareHeader
_wave_out_prepare_header.restype = MMRESULT
_wave_out_prepare_header.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.POINTER(WAVEHDR),
    ctypes.wintypes.UINT,
]

_wave_out_unprepare_header = winmm.waveOutUnprepareHeader
_wave_out_unprepare_header.restype = MMRESULT
_wave_out_unprepare_header.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.POINTER(WAVEHDR),
    ctypes.wintypes.UINT,
]

_wave_out_write = winmm.waveOutWrite
_wave_out_write.restype = MMRESULT
_wave_out_write.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.POINTER(WAVEHDR),
    ctypes.wintypes.UINT,
]

_wave_out_reset = winmm.waveOutReset
_wave_out_reset.restype = MMRESULT
_wave_out_reset.argtypes = [ctypes.wintypes.HANDLE]


class WinAudioOutput:
    def __init__(
        self,
        channels: int = 1,
        samplerate: int = 24000,
        bits_per_sample: int = 16,
    ):
        self.channels = channels
        self.samplerate = samplerate
        self.bits_per_sample = bits_per_sample
        self._block_align = channels * bits_per_sample // 8
        self._avg_bytes_per_sec = samplerate * self._block_align

        self._hwave: Optional[int] = None
        self._wave_format: Optional[WAVEFORMATEX] = None
        self._buffers: list[tuple[ctypes.Array[ctypes.c_char], WAVEHDR]] = []
        self._lock = threading.Lock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._closed = False

    def open(self) -> bool:
        if self._hwave is not None:
            return True

        self._wave_format = WAVEFORMATEX(
            wFormatTag=WAVE_FORMAT_PCM,
            nChannels=self.channels,
            nSamplesPerSec=self.samplerate,
            nAvgBytesPerSec=self._avg_bytes_per_sec,
            nBlockAlign=self._block_align,
            wBitsPerSample=self.bits_per_sample,
            cbSize=0,
        )

        hwave = ctypes.wintypes.HANDLE()
        err = _wave_out_open(
            ctypes.byref(hwave),
            WAVE_MAPPER,
            ctypes.byref(self._wave_format),
            0,
            0,
            0,
        )
        if err != MMSYSERR_NOERROR:
            self._wave_format = None
            return False

        self._hwave = hwave.value

        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        return True

    def write(self, data: bytes) -> None:
        if self._hwave is None:
            raise RuntimeError("WinAudioOutput not opened")

        buf = ctypes.create_string_buffer(data)
        hdr = WAVEHDR(
            lpData=ctypes.cast(buf, ctypes.wintypes.LPSTR),
            dwBufferLength=len(data),
            dwBytesRecorded=0,
            dwUser=0,
            dwFlags=0,
            dwLoops=0,
            lpNext=0,
            reserved=0,
        )

        err = _wave_out_prepare_header(
            self._hwave, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR)
        )
        if err != MMSYSERR_NOERROR:
            raise RuntimeError(f"waveOutPrepareHeader failed: {err}")

        err = _wave_out_write(
            self._hwave, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR)
        )
        if err != MMSYSERR_NOERROR:
            _wave_out_unprepare_header(
                self._hwave, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR)
            )
            raise RuntimeError(f"waveOutWrite failed: {err}")

        with self._lock:
            self._buffers.append((buf, hdr))

    def _cleanup_loop(self) -> None:
        while not self._closed:
            time.sleep(0.01)
            with self._lock:
                still_pending: list[tuple[ctypes.Array[ctypes.c_char], WAVEHDR]] = []
                for buf, hdr in self._buffers:
                    if hdr.dwFlags & WHDR_DONE:
                        _wave_out_unprepare_header(
                            self._hwave, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR)
                        )
                    else:
                        still_pending.append((buf, hdr))
                self._buffers = still_pending

    def flush(self) -> None:
        if self._hwave is None:
            return
        for _ in range(500):
            with self._lock:
                if not self._buffers:
                    break
            time.sleep(0.01)
        with self._lock:
            for buf, hdr in self._buffers:
                _wave_out_unprepare_header(
                    self._hwave, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR)
                )
            self._buffers.clear()

    def close(self) -> None:
        if self._hwave is None:
            return
        self._closed = True
        _wave_out_reset(self._hwave)
        with self._lock:
            for buf, hdr in self._buffers:
                try:
                    _wave_out_unprepare_header(
                        self._hwave, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR)
                    )
                except Exception:
                    pass
            self._buffers.clear()
        _wave_out_close(self._hwave)
        self._hwave = None
        self._wave_format = None
