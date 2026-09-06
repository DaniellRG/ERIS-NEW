# AGENTS.md — ERIS AI

Windows desktop assistant (Python 3.14, PyQt6). 457 tools, NeuroSpheres brain, dual Ollama/Gemini chat, Fish Audio TTS.

## Quick start

```powershell
# GUI
D:\Eris_Source\.venv\Scripts\pythonw.exe main.py

# CLI (from anywhere after PATH setup)
eris

# Tests (must pass: 56 PASS, 0 FAIL)
D:\Eris_Source\.venv\Scripts\python.exe test_all.py

# Run a single tool
$env:PYTHONIOENCODING="utf-8"
& .venv\Scripts\python.exe -c "from core.tool_registry import get_tool; print(get_tool('NOMBRE')({'action':'get'}))"
```

## Non-obvious constraints

- **Console is cp1252**: emojis → `UnicodeEncodeError`. Use `$env:PYTHONIOENCODING="utf-8"` or write to file.
- **config/api_keys.json**: must be UTF-8 **without BOM**. BOM → crash on load. Write with `Path.write_text(json, encoding="utf-8")` or PowerShell: `[System.IO.File]::WriteAllText($p, $json, (New-Object System.Text.UTF8Encoding($false)))`.
- **Tool sync is sacred**: after adding/removing tools, edit BOTH `core/tool_registry.py` AND `core/tool_declarations.py`, then verify `len(registry) == len(declarations)` and 0 duplicates. Restart Eris.
- **Gemini limita a 128 function_declarations**: con las 457 tools directas, el chat Gemini crashea con `400 INVALID_ARGUMENT` (`tools[0].function_de...`). `core/gemini_text_chat.py` ya envía un subconjunto priorizado <=120 vía `_gemini_tools()` (ver `_GEMINI_PRIORITY_TOOLS`: imprescindibles garantizadas + resto en orden de dominio). No revertir a `TOOL_DECLARATIONS` completo en el payload de Gemini.
- **ARRAY type rejected by Gemini**: use `STRING` with JSON-encoded content in declarations (see `actions/office_tools.py` for pattern).
- **Ollama tool_calls**: `arguments` arrives as `dict` (not string) — check `isinstance(raw_args, dict)` before `json.loads`.
- **edge-tts `synthesize()` is async**: call with `asyncio.run(...)`.
- **Vosk**: `KaldiRecognizer` takes a `Model` object, not a string path.
- **pycaw**: use `AudioUtilities.GetSpeakers()` → `.EndpointVolume`. No `Activate()` or `MMDeviceEnumerator`.
- **weather_report**: requires User-Agent `curl/8.0` (Mozilla returns HTML from wttr.in).
- **Rutas portables, nunca hardcodeadas**: `D:\Eris_*`, `C:\Users\...` y `ctypes.windll` rompen Linux. Usar `BASE = Path(__file__).resolve().parent.parent`, env vars `ERIS_WORKSPACE` / `ERIS_OBSIDIAN_VAULT` con fallback, y guardar `ctypes` tras `if os.name == "nt"`. (`core/logging_setup.get_obsidian_vault()` ya resuelve el vault portable.)
- **Deps opcionales = guard TODO**: si un action module importa algo opcional (openpyxl, PyQt6, google…) en un `try/except ImportError`, **ninguna referencia a nivel de módulo** puede usar esos nombres fuera del guard (ni en constantes de estilo, ni en `class X(QtBase)`, ni en defaults). Si lo hacés, el módulo crashea con `NameError`/`TypeError` al importar y se cae **todo** `core/action_imports.py`. Patrón válido: guard + `if _OK:` para definir lo dependiente; caso real: `actions/spreadsheet_generator.py`, `actions/accessibility_overlay.py`.
- **pyautogui/pygetwindow = guard `except Exception`, NO `except ImportError`**: en Wayland sin display X11, `import pyautogui` levanta `Xlib.error.XauthError` (no ImportError) y `import pygetwindow` levanta `NotImplementedError("...does not support Linux")`. Cualquiera de los dos a nivel de módulo sin guard **tumba todo `core/action_imports`** al arrancar (aunque estén instalados en el venv). Todos los `import pyautogui`/`pygetwindow` de `actions/` deben quedar dentro de `try/except Exception: X = None`. `core/action_imports.py` usa `except Exception:` (NO `except ImportError:`) en los 233 bloques para que cualquier fallo de dep-plataforma degrade a `None` en vez de crashear el import — no revertir a ImportError.
- **GUI-automation (browser_control/computer_control/native_ui/desktop_control/screen_vision) NO funciona en Wayland**: pyautogui/pygetwindow dependen de X11. En Linux quedan degradados (tools → mensaje de error o None), NO crashean. Equivalente en Wayland: ydotool (input) + grim/OCR (visión), sin portar aún.
- **`test_all.py` usa `BASE = Path(__file__).resolve().parent`** (no `D:\Eris_Source`); en Windows resuelve igual. No lo re-hardcodees.
- **Controles de sistema Linux** (mismos tools que Windows, mismo nombre de tool, backend distinto — sync de tools intocada): `system_volume` → pactl (fallback wpctl); `window_manager` → hyprctl (en Hyprland ≥0.55 `dispatch` es Lua con formato `hyprctl dispatch 'hl.dsp.focus({ window = \"address:0x...\" })'` — la sintaxis legacy `focuswindow address:...` CRASHEA con rc 7); `desktop_notifications` → notify-send; `pc_control` monitor → `hl.dsp.dpms`, wifi → nmcli, bluetooth → rfkill, screenshot → grim (Wayland); `screen_control`/brillo → brightnessctl (`-m info`: porcentaje en campo 4). Dependencias: paquetes de sistema (wireplumber, hyprland, libnotify, brightnessctl, nmcli, rfkill, grim), no pip.
- **Terminal Linux bash persistente + sudo on-demand**: `core/shell_session.py` lanza `/bin/bash --norc --noprofile` persistente (el `cd` se mantiene entre llamadas; `cd` con operadores `&& ; |` va normal por bash). En la sesión se exporta `SUDO_ASKPASS=tools/eris_askpass.py` → cualquier `sudo <cmd>` abre un diálogo gráfico (tkinter, fallback zenity) pidiendo la contraseña **en el momento**; la password NUNCA se loguea ni se guarda, vive solo en el flujo askpass→sudo y sudo cachea su timestamp (~15 min por defecto; no persiste la password). El tool `elevated` de `terminal_agent` antepone `sudo`. Nunca usar `echo "...password..." | sudo -S` (fuga en historial).
- **`network_monitor` es multipataforma** (rama Linux usa `ip`/`ss`/`ping`/`socket.gethostbyname`; Windows usa netsh/ipconfig/netstat/nslookup/tracert/taskkill). Si falta una sub-herramienta o dep opcional (PyPDF2, vosk, deep-translator), devuelve mensaje de error elegante, NO crash: usa guard `try/except ImportError` para deps opcionales (patrón de `pdf_editor`/`meeting_transcriber`/`translator`).
- **`_handle_*` legacy del dispatcher**: las tools `translator`, `meeting_transcriber`, `network_monitor`, `quick_actions`, `pdf_editor` eran `_SPECIAL_TOOLS` que despachaban a sub-funciones legacy inexistentes → `TypeError` en runtime. CORREGIDO: ahora delegan a `_generic_dispatch` (el módulo resuelve sus acciones). No reintroducir imports de `translate_text`/`start_monitoring`/`network_status`/etc. desde `core/action_imports`.
- **`core/action_imports.py` purgado**: los `translate_text`/`start_transcription`/`connections`/`bandwidth`/`monitor_*`/`network_status`/`scan_network`/`wifi_info`/`ping_host`/`summarize_transcription`/`transcription_status`/`translator_status`/`stop_*`/`start_monitoring`/`file_organizer` legacy fueron eliminados (el dispatcher ya no los usa). `eye_tracking`/`micro_movement`/`task_simplify`/`routine_gamify` SE MANTIENEN como `None` (main.py los usa con `if X:`). `emo_tick`/`emo_task_done`/`emo_task_failed`/`emo_core`/`accessibility`/`obsidian_note`/`translator`/`meeting_transcriber`/`network_monitor` son REALES tras guardar deps opcionales (psutil/yaml). Quedan 23 `None` en Linux bare: 17 deps pip (requests/psutil/flask/numpy — se resuelven en el venv con `requirements-linux.txt`) + pyautogui/pygetwindow/mss (GUI de escritorio, no Wayland) + `desktop_control` (Windows-only, pygetwindow) + 4 guards de main.py.

## Architecture

| File | Role |
|------|------|
| `main.py` | GUI entry point (PyQt6, 3884 lines) |
| `eris_cli.py` | CLI entry point (terminal, Ollama/Gemini chat) |
| `ui.py` | PyQt6 UI (3061 lines, ErisUI class) |
| `core/tool_registry.py` | 457 tool callables |
| `core/tool_declarations.py` | 457 LLM-facing declarations (0 dupes, sync con registry) |
| `core/tool_dispatcher.py` | Executes tools by name |
| `core/action_imports.py` | Imports all 296 action modules |
| `core/gemini_text_chat.py` | Dual Ollama (default) / Gemini (fallback) chat |
| `core/neuro_spheres.py` | Visual brain (self-growing; node count en `memory/neuro_spheres_state.json`), `learn_from_sessions()` |
| `core/prompt.txt` | System prompt (1864 lines) |
| `core/emotional_core.py` | Núcleo emocional sentiente: 12 emociones discretas, appraisal propio, [SENTIR] por turno, tono de cara/voz/orbe, diario emocional nocturno + [ANOCHE], sentimiento por persona, gustos aprendidos y expectativas/promesas. Aprende su carácter cada día (drift de baselines + polaridad de trato + rachas + buffer de soledad) → `memory/emotional_core.json` |
| `core/observer.py` | Sentidos de Eris: ventana en foco + programas abiertos (ctypes), clasifica actividad (programación/terminal/navegación/sensible…), detecta eventos (start_coding, long_coding, app_switch), expone contexto para comentarios espontáneos por voz. Mimo si no le contestan y "tiempo de ella". Puede MIRAR/LEER la ventana en foco (`observer action=mirar|mirar_leer`, captura de región + visión IA) solo con permiso del usuario (`mirar_ok`) y NUNCA pantallas sensibles; mirada leve automática `maybe_glimpse()` (cada mirar_interval_min) queda como contexto `[VISTA]`. → `memory/observer.json` |
| `core/code_guard.py` | El ojo guardián: detecta en tiempo real errores (rojo: py_compile/ruff E/F/B) y advertencias (amarillo: W/I/etc) del archivo en foco del usuario (títle→cwd→glob). Corrige SOLO las líneas señaladas vía LLM (Gemini/Ollama) con backup + validación + rollback y tope de 25% de líneas tocadas (`fix_file`, `guardian_tick`). Tool `code_guard` (status/scan/fix/fix_w/config). Auto-fix en loop `_code_guard_loop` de main. → `memory/code_guard.json`, backups en `memory/code_guard_backups/` |
| `core/mission_agent.py` | PROTOCOLO OPERATIVO global (estilo opencode): cuaderno de misión persistido (`mission`: start/plan/explore/read/edit/verify/step/learn/close). EDITAR = cambios mínimos con backup + validación + rollback (reutiliza maquinaria de code_guard); VERIFICAR = ruff/py_compile/pytest y no declara "listo" si queda rojo; APRENDER = memoria por proyecto en `memory/proyectos/*.json`; al cerrar, espeja la misión en Obsidian `Proyectos/`. Tool `mission`. |
| `core/self_evolution.py` | EVOLUCIÓN CONTINUA (`evolucion`): autoconocimiento vivo (inventario 457 tools en `data/knowledge/eris_inventario_vivo.md` + Obsidian Tools/), auditoría real `health` (cada tool importa/resuelve), `rectify` (normaliza conteos en prompt/README/AGENTS), espejo de estado en Obsidian (Capacidades/Memoria/Logs), y bucle antir-estancamiento: cada 30 min (`run_evolution_tick`, hilo en main) aplica una micro-mejora real sobre core/ (quita F401 con backup+validación+rollback en `memory/self_evol_backups/`) o consolida su conocimiento. Todo queda en `memory/self_evolution_state.json` y Logs/Evolución del vault. |
| `core/command_deck.py` | Cola de comandos (intents del LLM) → `data/command_deck.json` |
| `config/api_keys.json` | All API keys and settings |
| `memory/` | Semantic, episodic, working memory + NeuroSpheres state |
| `data/knowledge/` | 69 .md knowledge files |
| `actions/` | 296 action modules (one tool per file) |
| `agents/` | 9 specialist agents |
| `skills/` | 39 installed skills (21 builtin + 18 user_created) |
| `vault/` | Memoria charra: `raw/` capturas → `wiki/` destilado → `outputs/` productos |

## Model routing

- **Default**: Ollama local (`qwen3:8b`) — no rate limits
- **Fallback**: Gemini API (`gemini-3.1-flash-lite`) — low free-tier quota
- **TTS**: Fish Audio (`s2.1-pro-free`) with custom voice
- **Config**: `config/api_keys.json`

## Ollama

- Exe: `C:\Users\danie\AppData\Local\Programs\Ollama\ollama.exe`
- Models installed: `qwen3:8b` (primary), `qwen3:14b`, `qwen2.5-coder:3b`, `minicpm-v`, others
- Not always running — start with: `ollama serve`
- Best model: `qwen3:8b` (37-66 tok/s). `qwen3:14b` is ~10 tok/s (slow).

## Testing

`test_all.py` verifies: tool registry (457), declarations (457), sync, no duplicates, core modules, agents, NeuroSpheres, CLI, action imports, data files, knowledge, Python env, compile check, BOM check, GUI window.

Run after any structural change. Expected: **56 PASS, 0 FAIL**.
