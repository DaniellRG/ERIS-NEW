# -*- coding: utf-8 -*-
"""
voice_cloning.py — Voz multi-engine: Coqui XTTS v2 (local) + Edge TTS (Microsoft cloud).
Acciones:
  speak   — Generar audio con voz local o clonada
  voices  — Listar voces disponibles (Edge TTS)
  clone   — Guardar audio de referencia para clonación (requiere XTTS)
  status  — Estado de motores TTS
"""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any

_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "voice_clones"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_coqui_model = None
_coqui_model_name = "tts_models/multilingual/multi-dataset/xtts_v2"


def _get_coqui():
    global _coqui_model
    if _coqui_model is not None:
        return _coqui_model
    try:
        from TTS.api import TTS
        _coqui_model = TTS(_coqui_model_name)
        return _coqui_model
    except Exception:
        return None


_EDGE_VOICE_MAP = {
    "es": "es-AR-TomasNeural",
    "es-ar": "es-AR-TomasNeural",
    "es-mx": "es-MX-DaliaNeural",
    "es-es": "es-ES-ElviraNeural",
    "es-co": "es-CO-GonzaloNeural",
    "en": "en-US-GuyNeural",
    "en-us": "en-US-GuyNeural",
    "en-gb": "en-GB-RyanNeural",
    "pt": "pt-BR-AntonioNeural",
    "fr": "fr-FR-HenriNeural",
    "de": "de-DE-ConradNeural",
    "it": "it-IT-DiegoNeural",
    "ja": "ja-JP-KeitaNeural",
    "ko": "ko-KR-InJoonNeural",
    "zh": "zh-CN-YunxiNeural",
    "ru": "ru-RU-DmitryNeural",
    "ar": "ar-SA-HamedNeural",
    "hi": "hi-IN-MadhurNeural",
}


def _resolve_edge_voice(voice_name: str, lang: str) -> str:
    if voice_name and (voice_name.startswith("es-") or voice_name.startswith("en-")
                       or voice_name.startswith("pt-") or voice_name.startswith("fr-")
                       or voice_name.startswith("de-") or voice_name.startswith("it-")):
        return voice_name
    if voice_name and not voice_name.startswith("es") and not voice_name.startswith("en"):
        return voice_name
    lang_key = lang.lower().strip()
    if lang_key in _EDGE_VOICE_MAP:
        return _EDGE_VOICE_MAP[lang_key]
    return _EDGE_VOICE_MAP.get("es")


def _edge_speak(text: str, voice: str, output_path: Path) -> bool:
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        asyncio.run(communicate.save(str(output_path)))
        return output_path.exists() and output_path.stat().st_size > 100
    except Exception:
        return False


def voice_cloning(parameters: dict = None, player=None) -> str:
    """Tool: Voz multi-engine (XTTS v2 + Edge TTS)."""
    params = parameters or {}
    action = str(params.get("action", "status")).lower().strip()

    if action == "status":
        coqui = _get_coqui()
        edge_ok = False
        try:
            import edge_tts
            edge_ok = True
        except ImportError:
            pass
        lines = ["**Estado TTS:**\n"]
        if coqui:
            lines.append(f"  XTTS v2: activo (device: {coqui.device})")
        else:
            try:
                from TTS.api import TTS
                lines.append("  XTTS v2: instalado, modelo no cargado")
            except ImportError:
                lines.append("  XTTS v2: no disponible (requiere Python <3.12)")
        lines.append(f"  Edge TTS: {'activo' if edge_ok else 'no instalado'}")
        if edge_ok:
            lines.append(f"  Voces Edge: 300+ en 70+ idiomas")
        return "\n".join(lines)

    if action == "voices":
        try:
            import edge_tts
            loop = asyncio.new_event_loop()
            voices_raw = loop.run_until_complete(edge_tts.list_voices())
            loop.close()
            es_voices = [v for v in voices_raw if v.get("Locale", "").startswith("es")]
            lines = [f"**Voces Edge disponibles:** {len(voices_raw)} total, {len(es_voices)} español\n"]
            lines.append("**Español:**")
            for v in es_voices[:12]:
                lines.append(f"  • {v['ShortName']} — {v.get('Gender', '?')} ({v.get('Locale', '')})")
            lines.append(f"\n**Otros idiomas destacados:**")
            other = [v for v in voices_raw if not v.get("Locale", "").startswith("es")]
            seen = set()
            for v in other:
                loc = v.get("Locale", "")[:2]
                if loc not in seen and len(seen) < 8:
                    seen.add(loc)
                    lines.append(f"  • {v['ShortName']} — {v.get('Gender', '?')}")
            if coqui := _get_coqui():
                ref_dir = _OUTPUT_DIR / "references"
                refs = list(ref_dir.glob("*.wav")) + list(ref_dir.glob("*.mp3")) if ref_dir.exists() else []
                if refs:
                    lines.append(f"\n**Voces locales (XTTS):**")
                    for r in refs:
                        lines.append(f"  • {r.stem} ({r.stat().st_size // 1024}KB)")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listando voces: {str(e)[:100]}"

    if action == "clone":
        ref_audio = str(params.get("audio", "")).strip()
        if not ref_audio:
            return "Necesitás 'audio': ruta a un archivo .wav/.mp3 de referencia."
        if not os.path.exists(ref_audio):
            return f"Audio no encontrado: {ref_audio}"
        ref_dir = _OUTPUT_DIR / "references"
        ref_dir.mkdir(exist_ok=True)
        import shutil
        name = str(params.get("name", f"voice_{int(time.time())}")).strip()
        dest = ref_dir / f"{name}.wav"
        shutil.copy2(ref_audio, str(dest))
        coqui = _get_coqui()
        engine = "XTTS v2" if coqui else "Edge TTS"
        return f"✅ Voz '{name}' guardada como referencia: {dest.name}\nMotor: {engine}\nUsá 'speak' con voice='{name}' para generar audio."

    if action == "speak":
        text = str(params.get("text", "")).strip()
        voice_name = str(params.get("voice", "")).strip()
        if not text:
            return "Necesitás 'text' para generar audio."
        lang = str(params.get("language", "es")).strip()
        output_name = f"tts_{int(time.time())}.wav"
        output_path = _OUTPUT_DIR / output_name
        coqui = _get_coqui()
        if coqui:
            ref_dir = _OUTPUT_DIR / "references"
            ref_audio = None
            if voice_name:
                ref_audio = ref_dir / f"{voice_name}.wav"
                if not ref_audio.exists():
                    ref_audio = None
            try:
                if ref_audio:
                    coqui.tts_to_file(text, speaker_wav=str(ref_audio), language=lang, file_path=str(output_path))
                else:
                    coqui.tts_to_file(text, file_path=str(output_path))
                size_kb = output_path.stat().st_size // 1024
                return f"✅ Audio generado (XTTS v2): {output_path.name} ({size_kb}KB)"
            except Exception as e:
                return f"Error XTTS: {str(e)[:150]}"
        edge_voice = _resolve_edge_voice(voice_name, lang)
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, edge_voice)
            asyncio.run(communicate.save(str(output_path)))
            if output_path.exists() and output_path.stat().st_size > 100:
                size_kb = output_path.stat().st_size // 1024
                return f"✅ Audio generado (Edge TTS): {output_path.name} ({size_kb}KB) voz={edge_voice}"
            return "Edge TTS: error generando audio."
        except ImportError:
            return "Ni XTTS ni Edge TTS disponibles. Instalá: pip install edge-tts"
        except Exception as e:
            return f"Error Edge TTS: {str(e)[:150]}"

    return "Acciones: status, voices, clone, speak"
