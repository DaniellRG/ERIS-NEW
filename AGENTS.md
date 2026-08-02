# AGENTS.md — ERIS (D:\Eris_Source)

Asistente de voz de escritorio (Windows) en Python. Conversación en vivo con Google
Gemini (modelo live `gemini-3.1-flash-live-preview`), voz TTS offline (edge-tts), y
herramientas declaradas al modelo mediante la API de Gemini Live.

## Comandos clave

```powershell
# Arrancar ERIS
Start-Process -FilePath "D:\Eris_Source\.venv\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory "D:\Eris_Source" -WindowStyle Hidden

# Reinicio completo (OJO: mata TODOS los procesos python)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item -LiteralPath "D:\Eris_Source\data\.eris_lock" -Force
Start-Process -FilePath "D:\Eris_Source\.venv\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory "D:\Eris_Source" -WindowStyle Hidden

# Tests
D:\Eris_Source\.venv\Scripts\python.exe test_all.py        # esperar: PASS>=99, FAIL=0

# Probar una tool del registro
$env:PYTHONIOENCODING="utf-8"; & .venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'.'); from core.tool_registry import get_tool; print(get_tool('NOMBRE')({'action':'get'}))"
```

## Reglas críticas (lecciones aprendidas — NO repetir errores)

1. **Consola cp1252**: imprimir emojis lanza `UnicodeEncodeError`. Si un script imprime
   texto no ASCII, ejecutarlo con `$env:PYTHONIOENCODING="utf-8"` o escribir a archivo.
2. **`config/api_keys.json` debe escribirse SIN BOM** (UTF-8 sin firma). Con BOM,
   `main.py` muere con "Unexpected UTF-8 BOM". Al editar desde PowerShell usar:
   `[System.IO.File]::WriteAllText($p, $json, (New-Object System.Text.UTF8Encoding($false)))`.
   En Python usar `Path.write_text(json, encoding="utf-8")` (sin BOM).
3. **Error 1008 = CUOTA AGOTADA** (confirmado 2026-08-01): el websocket LIVE cierra con
   `1008 policy violation. The operation was aborted` y ERIS entra en bucle de reconexión
   ("Reconectando en 1.0s..."). Es la MISMA causa que el `429 RESOURCE_EXHAUSTED` de
   `generateContent` con `gemini-2.0-flash`: la key `gemini_api_key` no tiene cuota.
   NO es bug de código. Diagnóstico definitivo:
   ```powershell
   $env:PYTHONIOENCODING="utf-8"; & .venv\Scripts\python.exe -c "import json;from pathlib import Path;from google import genai;k=json.loads(Path('config/api_keys.json').read_text(encoding='utf-8-sig'))['gemini_api_key'];genai.Client(api_key=k).models.generate_content(model='gemini-2.0-flash',contents='hola')"
   ```
   Si da `429`, hay que: revisar plan/billing en https://aistudio.google.com/apikey,
   crear key nueva, o esperar reset de cuota. El bucle se auto-recupera al volver la cuota.
4. **Convención de declaraciones** (`core/tool_declarations.py`): el tipo `ARRAY` es
   rechazado por la API de Gemini (error 1007 "items: missing field"). Usar `STRING`
   con JSON codificado (patrón de `spreadsheet_generator` y `office_docs`). Helper
   `_as_list()` en `actions/office_tools.py` convierte JSON string / listas / texto.
5. **pycaw (volumen)** usa la API nueva: `AudioUtilities.GetSpeakers()` devuelve un
   `pycaw.utils.AudioDevice` con atributos `EndpointVolume`, `FriendlyName`, `id`.
   NO existe `Activate()` ni `MMDeviceEnumerator`. Usar
   `AudioUtilities.GetAllDevices()` (lista) y `AudioUtilities.SetDefaultDevice(id)`.
6. **Tras agregar/quitar tools**: editar SIEMPRE en paralelo `core/tool_registry.py`
   (registro en memoria) y `core/tool_declarations.py` (declaraciones para la API),
   luego verificar: `len(registradas)==len(declaradas)` y 0 duplicados, y REINICIAR ERIS.
7. **Ollama**: exe en `C:\Users\danie\AppData\Local\Programs\Ollama\ollama.exe`
   (serve v0.30.8). Modelos: `phi`, `tinyllama`, `nomic-embed-text`, `minicpm-v`,
   `qwen3:14b` (9.3GB, ~10 tok/s — MUY lento) y **`qwen3:8b`** (37-63 tok/s, el bueno).
   No usar modelos no instalados (p.ej. `llama3.2`). Si el serve no corre:
   `Start-Process "C:\Users\danie\AppData\Local\Programs\Ollama\ollama.exe" serve`.
8. **Ollama tool_calls**: `tool_calls[].function.arguments` llega como **dict** (no
   string) → no hacer `json.loads` directo; parsear con `isinstance(raw_args, dict)`.
9. **edge-tts** (`core/tts_engine.py`): `synthesize()` es **asíncrono** — llamarlo con
   `asyncio.run(...)`. Requiere `imageio-ffmpeg` instalado (ffmpeg estático; no hay
   ffmpeg en el sistema). `get_voice()` devuelve la voz de otro backend (p.ej.
   "Zephyr") que edge rechaza → `_synthesize_edge` valida contra `_EDGE_VOICES.values()`
   y cae a `es-AR-ElenaNeural`. PCM resultante: s16le 24000 Hz mono.
10. **Vosk** (`core/offline_voice.py`): `vosk.KaldiRecognizer` recibe un objeto
    `vosk.Model(...)`, NO la ruta string (si no: `'str' object has no attribute '_handle'`).
    Modelo es: `data/vosk-model-es`.

## Arquitectura

- `main.py` — bucle principal: sesión live Gemini, audio, wake word, `_announce()`
  (avisos por voz offline con edge-tts en hilo daemon).
- `actions/` — UNA tool por archivo, función `nombre(parameters: dict, player=None) -> str`.
  Firmas sin depender de scipy (no instalado). Ejemplos a copiar: `system_volume.py`,
  `office_tools.py`, `curiosity_engine.py`.
- `core/tool_registry.py` — registro central (245 tools). `get_tool(nombre)` devuelve el callable.
- `core/tool_declarations.py` — `TOOL_DECLARATIONS` (245) para la API.
- `core/rag_pipeline.py` — `RAGPipeline` + singleton `rag` (27 docs / 103 chunks).
- `core/training_pipeline.py` — `full_training` (56 módulos con puntajes).
- `config/` — `api_keys.json` (claves), `email_credentials.json` (IMAP/SMTP), estados.
- `data/` — logs de runtime, transcripts, `eris_tasks.json`, `.eris_lock`.
- `tests/` + `test_all.py` — suite de integración (99 PASS).

## Estado de integraciones (2026-08-01)

| Integración | Estado | Key/archivo requerido |
|---|---|---|
| OpenAI / Gemini | OK | `api_keys.json` (`gemini_api_key`, `openrouter_api_key`) |
| Cerebro dual (fallback) | OK | `local_brain_enabled=true`, `local_brain_model=qwen3:8b`, `cloud_brain_model=google/gemini-2.5-pro`, `local_tools_enabled=true` |
| Voz local (fallback) | OK | `core/offline_voice.py`: Vosk→cerebro dual→edge-tts; se activa al entrar fallback (≥5 fails de cuota) |
| Spotify | OK | `spotify_token.json` |
| Ollama (respaldo LLM) | OK | `ollama_enabled=true`, `ollama_model=phi` |
| RAG (memoria) | OK | 27 docs indexados |
| Telegram | PENDIENTE | `telegram_bot_token` (vía @BotFather) |
| Gmail (email_manager) | PENDIENTE | `config/email_credentials.json` (app password) |
| Gmail/Calendar/Drive | PENDIENTE | OAuth client |
| SMS | PENDIENTE | Twilio (`twilio_account_sid`, `twilio_auth_token`, `twilio_from`) o `sms_gateway_url` |
| TMDB / OpenWeather | OPCIONAL | `tmdb_api_key`, `openweather_api_key` (clima ya funciona con wttr.in) |

Cerebro dual: `core/local_brain.py` enruta por heurística (largo>260 o regex
`_CLOUD_HINTS` → OpenRouter nube; sino → Ollama local `qwen3:8b` con tool-calling de
14 tools del registry). Fallback de chat en `main.py` → `get_brain().respond(text)` +
`_announce()`. Requiere `quick_check()` (verifica que Ollama esté arriba).
`weather_report` necesita User-Agent `curl/8.0` (Mozilla devuelve HTML de wttr.in).

Asistente interactivo para integrar: `.venv\Scripts\python.exe config\setup_integrations.py`

## Notas del entorno

- Windows 11, consola cp1252, PC desktop (SIN batería y SIN sensor WMI de brillo →
  `screen_control` brillo reporta limitación correctamente).
- Python: `.venv` en `D:\Eris_Source\.venv`. También existe `C:\Python314`.
- El sandbox (`actions/sandbox.py`) ejecuta código; usar `PYTHONIOENCODING=utf-8`.
- `test_all.py` consulta `eris.log` para errores 1008 — trazas antiguas generan WARN
  (no bloquean; confirmar que no haya 1008 nuevos tras reinicio).
