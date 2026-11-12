# AGENTS.md — ERIS AI

**Versión: 4.0.1 "Constellation Prime"** (2026-10-16) · fuente de verdad: `core/version.py`.

Windows desktop assistant (Python 3.14, PyQt6). **525 tools**,
NeuroSpheres brain, dual Ollama/Gemini chat, Kokoro-82M local Spanish TTS
(ef_dora). También corre en Linux (.venv-linux) con scripts adaptados.
**14 agentes** especializados, con empaquetado nativo
(PKGBUILD), despliegue Docker y .desktop file para menú Linux.

## Commands

- **Run full test suite**: `python test_all.py` (baseline: ejecutar `python scripts/metrics_ssot.py` para métricas SSOT; en clon fresco fallan pruebas por archivos de datos ausentes — usar `python scripts/ci_seed.py` primero)
- **Run single test**: `python -m pytest tests/test_neurospheres.py -x` (pytest-compatible)
- **Compile check single file**: `python -m py_compile <file>.py`
- **Linux setup**: `./run_linux.sh` (crea .venv-linux, instala deps, arranca)
- **Windows**: `.venv\Scripts\python.exe main.py`

## Architecture

| File | Role |
|------|------|
| `main.py` | GUI entry point (PyQt6, ~5380 lines) |
| `eris_cli.py` | CLI entry point (terminal, Ollama/Gemini chat, ~872 lines) |
| `ui.py` | PyQt6 UI (~1186 lines, ErisUI class; widgets en gui/widgets/) |
| `core/tool_registry.py` | 525 tool callables |
| `core/tool_declarations.py` | 525 LLM-facing declarations (0 dupes, sync verificado) |
| `core/tool_dispatcher.py` | Executes tools by name |
| `core/action_imports.py` | Lazy registry of action modules (`_LAZY` + `__getattr__`, PEP 562) |
| `core/gemini_text_chat.py` | Dual Ollama (default) / Gemini (fallback) chat |
| `core/neuro_spheres.py` | Visual brain (self-growing), `learn_from_sessions()` |
| `core/prompt.txt` | System prompt (~2142 lines) |
| `core/emotional_core.py` | 12-emotion nucleus, learns daily |
| `core/agent_definitions.py` | 14 specialist agents |
| `core/agent_router.py` | Intent classification (`classify_intent()`, threshold ≥3) |
| `actions/` | 309 action modules (one tool per file) |
| `agents/` | 14 specialist agents + 15 sub-agents |
| `skills/` | Builtin + user_created skills (52 SKILL.md) |
| `config/api_keys.json` | All API keys and settings (UTF-8 without BOM) |
| `data/knowledge/` | 78 knowledge .md files |
| `memory/` | Semantic, episodic, working memory + NeuroSpheres state |

## Non-obvious constraints

- **Console is cp1252**: emojis → `UnicodeEncodeError`. Use `$env:PYTHONIOENCODING="utf-8"` or write to file.
- **config/api_keys.json**: must be UTF-8 **without BOM**. BOM → crash on load. Write with `Path.write_text(json, encoding="utf-8")`.
- **Tool sync is sacred**: after adding/removing tools, edit BOTH `core/tool_registry.py` AND `core/tool_declarations.py`, then verify `len(registry) == len(declarations)` and 0 duplicates. Restart Eris.
- **Gemini limita a 128 function_declarations**: envía subconjunto priorizado ≤120 vía `_gemini_tools()` en `core/gemini_text_chat.py`. No revertir a `TOOL_DECLARATIONS` completo.
- **ARRAY type rejected by Gemini**: use `STRING` with JSON-encoded content in declarations.
- **Ollama tool_calls**: `arguments` arrives as `dict` (not string) — check `isinstance(raw_args, dict)` before `json.loads`.
- **edge-tts `synthesize()` is async**: call with `asyncio.run(...)`.
- **Vosk**: `KaldiRecognizer` takes a `Model` object, not a string path.
- **pycaw**: use `AudioUtilities.GetSpeakers()` → `.EndpointVolume`.
- **weather_report**: requires User-Agent `curl/8.0`.
- **Rutas portables, nunca hardcodeadas**: usar `BASE = Path(__file__).resolve().parent.parent`, env vars `ERIS_WORKSPACE` / `ERIS_OBSIDIAN_VAULT`. Guard `ctypes` tras `if os.name == "nt"`.
- **Deps opcionales = guard TODO**: si un action module importa algo opcional en `try/except ImportError`, ninguna referencia a nivel de módulo puede usar esos nombres fuera del guard. Patrón: guard + `if _OK:`. Ver `actions/spreadsheet_generator.py`.
- **pyautogui/pygetwindow = guard `except Exception`, NO `except ImportError`**: en Wayland sin X11, `import pyautogui` levanta `Xlib.error.XauthError` (no ImportError). Todos los imports de pyautogui/pygetwindow deben quedar en `try/except Exception: X = None`. `core/action_imports.py` es lazy (`_LAZY` + `__getattr__`, PEP 562) con `except Exception:` — no revertir a ImportError.
- **GUI-automation NO funciona en Wayland**: pyautogui/pygetwindow dependen de X11. En Linux quedan degradados, NO crashean.
- **Linux system controls**: `system_volume` → pactl, `window_manager` → hyprctl (Hyprland ≥0.55 `dispatch` es Lua: `hyprctl dispatch 'hl.dsp.focus({ window = "address:0x..." })'` — legacy CRASHEA rc 7), `desktop_notifications` → notify-send, `screen_control` → brightnessctl.
- **Terminal Linux**: `core/shell_session.py` lanza `/bin/bash --norc --noprofile` persistente. `SUDO_ASKPASS=tools/eris_askpass.py` → `sudo` abre diálogo gráfico. Nunca usar `echo "password" | sudo -S`.
- **`_handle_*` legacy eliminados**: tools `translator`, `meeting_transcriber`, `network_monitor`, `quick_actions`, `pdf_editor` ahora delegan a `_generic_dispatch`. No reintroducir imports legacy.
- **7 `None` en venv Linux**: `aprendizaje_videos`, `audio_diagnostic`, `system_status`, `eye_tracking`, `micro_movement`, `task_simplify`, `routine_gamify`. `screen_vision` ya resuelve (usa grim en Wayland).

## Model routing

- **Default**: Ollama local (`qwen3:8b`) — no rate limits
- **Fallback**: Gemini API (`gemini-3.1-flash-lite`) — low free-tier quota
- **TTS**: Kokoro-82M local (`pykokoro`, backend `kokoro`) — voz `ef_dora`, Apache-2.0. Alternativa nube: `edge` (`es-AR-TomasNeural`). En Linux: `tts_backend: "gemini"` reproduce audio nativo via `response.data → pacat`.
- **Config**: `config/api_keys.json`

## Ollama

- Exe: `C:\Users\danie\AppData\Local\Programs\Ollama\ollama.exe`
- Models: `qwen3:8b` (primary, 37-66 tok/s), `qwen3:14b` (slow, ~10 tok/s)
- Start: `ollama serve`

## Testing

`test_all.py` verifica: tool registry (525), declarations (525), sync, sin duplicados, core modules, agents, NeuroSpheres, CLI, action imports, data files, knowledge, Python env, compile check, BOM check, GUI window, sesión summaries, rutinas, cerebro, vida interior, relaciones, mundo nuevo I/II.

### Commands

- **Run full test suite**: `python test_all.py`
- **Run single test**: `python -m pytest tests/test_neurospheres.py -x`
- **Compile check single file**: `python -m py_compile <file>.py`

### Linux dev setup

- **Venv**: `.venv-linux` (NOT `.venv`) — activate with `source .venv-linux/bin/activate`
- **Entrypoint**: `python main.py` (GUI) or `./run_linux.sh`
- **System packages**: `portaudio`, `pipewire-pulse`, `espeak-ng`, `brightnessctl`, `grim`, `nmcli`, `rfkill`, `libnotify`, `wireplumber`, `hyprland` (install via `pacman -S`)
- **API server ports**: 8080 (REST API + web dashboard), 8765 (health + mobile_server `/chat`), 8888 (web dashboard)

### Verificación de voz/audio (Linux)

- `sounddevice` + `numpy` deben estar en `.venv-linux`. Instalar: `.venv-linux/bin/pip install sounddevice numpy`
- Reproduce audio vía `pacat`: `ps aux | grep pacat` → debe ver `pacat --rate=24000 --format=S16LE --channels=1`
- Test voz sin GUI: `curl -X POST http://127.0.0.1:8765/chat -H "Content-Type: application/json" -d '{"text":"Hola Eris, habla algo"}'`
- Probar TTS local: `.venv-linux/bin/python -c "from core.tts_engine import synthesize; import asyncio; pcm=asyncio.run(synthesize('Hola', backend='kokoro')); print(len(pcm) if pcm else 'empty')"`

## Avatar VRM 3D (flotante, Eris.vrm)

- El modelo 3D NO va en la ventana principal. Solo el orbe flotante se conmuta a "Modelo 3D (VRM)" desde Ajustes → combo "Flotante" (`floating_visual`, default `orb`).
- **VrmAvatar** (`ui.py:2441`): ventana 340×480 frameless, transparente, carga `assets/vrm/viewer.html` servido por `core/vrm_server.py`.
- **BUG ABIERTO**: el avatar carga pero NO se ve en Linux/Wayland. Debug: servir `assets/vrm/` con `python -m http.server`.
- **GPU**: `core/gpu_config.py` debe correr ANTES de crear QApplication. En Linux fuerza `QSG_RHI_BACKEND=software` + flags Chromium. NO usar `opengl`/d3d11 en Linux.
