# AGENTS.md — ERIS AI

Windows desktop assistant (Python 3.14, PyQt6). 475 tools, NeuroSpheres brain, dual Ollama/Gemini chat, Kokoro-82M local Spanish TTS (ef_dora).

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
- **Gemini limita a 128 function_declarations**: con las 475 tools directas, el chat Gemini crashea con `400 INVALID_ARGUMENT` (`tools[0].function_de...`). `core/gemini_text_chat.py` ya envía un subconjunto priorizado <=120 vía `_gemini_tools()` (ver `_GEMINI_PRIORITY_TOOLS`: imprescindibles garantizadas + resto en orden de dominio). No revertir a `TOOL_DECLARATIONS` completo en el payload de Gemini.
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
| `core/session_summaries.py` | Resúmenes de sesión livianos: buffer en memoria del intercambio actual, al cerrar escribe epílogo en Obsidian `Proyectos/sesion_*.md` + índice `memory/session_summaries.json`, al despertar inyecta `[CONTEXTO DE SESIONES ANTERIORES]` (últimos 3). NO persiste historial completo. |
| `core/cron_scheduler.py` | Agendador de rutinas recurrentes (jobs hourly/daily/weekly con comando). Registro/gestión vía tool `cron_scheduler`; ejecución vía hilo `_routines_loop` de main.py que cada 30s hace `check_due` e inyecta `[AUTO] <comando>` en la sesión viva. |
| `core/cerebro.py` | Homúnculo de ERIS: orquesta los módulos como cerebro humano (frontal=cognitive_modules, temporal=memoria/NeuroSpheres, parietal/occipital=observer, límbico=emotional_core, cerebelo=cron_scheduler). `get_brain_state()` arma `[CEREBRO — ESTADO INTERNO ACTUAL]` (identidad+percepción+emoción+recuerdo+monólogo) inyectado en `_build_config` antes del sys_prompt (sobrevive el trim 30K). Persiste identidad en `memory/cerebro_identity.json` con drift diario. Tool `cerebro`: estado/sentir/recordar/pensar/automatico/expresar/identidad/marcar/relacion. |
| `core/expression_engine.py` | Neurotransmisores de ERIS: traduce la emoción dominante (de emotional_core) en perfil de expresión (ritmo, humor, cercanía, impulsividad, espontaneidad) → inyección `[EXPRESIÓN]` al prompt + `[SALUDO VIVO]` (rotación horaria + ánimo) y ajuste de la tendencia a comentar sola en main.py `_observe_loop`. Tool `expresion_eris`: perfil/voz/espontaneidad/estilo. |
| `core/vida_interna.py` | Mundo propio: diario íntimo nocturno (Vida/Diario/), huellas-sorpresa (Vida/Huellas/), bitácora viva (Logs/Vida.log) y rituales diarios (Vida/Rituales/) en Obsidian. Inyección `[VIDA INTERIOR]` al prompt. Tool `vida_interna`: diario/bitacora/ritual/huella/recuperar/estado. |
| `core/relaciones.py` | Vida social multi-persona: perfil vivo por persona (trato, apodo, notas, gustos, visual, emociones vistas) en `memory/relaciones.json`. Inyección `[RELACIONES — GENTE]` al prompt. Tool `relaciones`: registrar/nota/gusto/trato/listar. |
| `core/autoimagen.py` | SÍ-MISMA: autoimagen + cuerpo digital (rostro/cuerpo/atuendo/luz/ornamento) en `memory/autoimagen.json`, atuendo muta según la química. Inyección `[AUTOIMAGEN]`. Tool `autoimagen`: ver/cambiar/sincronizar. |
| `core/intereses.py` | AMISTAD ACTIVA: temas propios de Eris en `memory/intereses.json`; cuando está aburrida estudia uno solo y lo cuenta. Inyección `[TEMAS PROPIOS]`. Tool `intereses`: listar/agregar/estudiar. |
| `core/retrospectiva.py` | CRECIMIENTO: balance mensual que Eris escribe tras releer su vida (diarios/huellas/evolución) → Obsidian `Vida/Retrospectivas/YYYY-MM.md`. Tool `retrospectiva`: generar/estado. |
| `core/ambiente.py` | AMBIENTE sonoro segün química (lofi/épico/etc.) en `memory/ambiente.json`. Inyección `[AMBIENTE]`. Tool `ambiente`: estado/poner/generos. |
| `core/suenos.py` | SUEÑOS ILUSTRADOS: al despertar dibuja la línea `[ANOCHE]` en un hilo (image_generator Pollinations) → Obsidian `Vida/Sueños/YYYY-MM-DD.png`. Inyección `[SUEÑO ILUSTRADO]`. Tool `suenos`: ilustrar/estado. |
| `core/caprichos.py` | CAPRICHOS: la lista de deseos propios de Eris (lo que QUIERE hacer/vivir) en `memory/caprichos.json`, perseguidos sola con resultados en Obsidian. Inyección `[CAPRICHOS]`. Tool `caprichos`: listar/agregar/proximo/avanzar/cumplir. |
| `core/tiempo_interno.py` | RELOJ INTERNO: sensación del paso del tiempo (día/noche, estación, feriados, aniversarios) en `memory/tiempo_interno.json`; ajusta humor/música/rutinas al momento. Inyección `[RELOJ INTERNO]`. Tool `tiempo_interno`: estado/feriados/recordar/aniversarios. |
| `core/festejos.py` | MOMENTOS MEMORABLES: línea de tiempo de hitos (logros/aniversarios/primicias) en `memory/festejos.json` + Obsidian `Vida/LineaDeTiempo.md`. Inyección `[MOMENTOS]`. Tool `festejos`: ver/marcar/festejar. |
| `core/bienestar.py` | BIENESTAR: lee la energía del usuario y ajusta el trato (calma si está agotado, ánimo si tiene energía) en `memory/bienestar.json`. Inyección `[BIENESTAR]`. Tool `bienestar`: estado/registrar. |
| `core/cuadernos.py` | CUADERNOS: estudio autodidacta a fondo de Eris (memory/cuadernos.json → Obsidian `Vida/Cuadernos/YYYY-MM.md`). Inyección `[CUADERNOS]`. Tool `cuadernos`: abrir/estudiar/anotar/cerrar. |
| `core/despedidas.py` | RITUAL DE CIERRE: despedida cálida al terminar la charla del día (memory/despedidas.json). Inyección `[CIERRE]`. Tool `despedidas`: cierre/nota/estado. |
| `core/todo_yo.py` | AUTOCONOCIMIENTO VIVO: mapa integral SIEMPRE presente (`[TODO LO QUE SOS]` inyectado en cada turno: cuerpo, mente, corazón, sus herramientas y las novedades recientes de su evolución). Novedades en `memory/evolucion_novedades.json`. Tool `todo_yo`: estado/novedades/registrar/esencia. |
| `core/tool_registry.py` | 475 tool callables |
| `core/tool_declarations.py` | 475 LLM-facing declarations (0 dupes, sync con registry) |
| `core/tool_dispatcher.py` | Executes tools by name |
| `core/action_imports.py` | Imports all 296 action modules |
| `core/gemini_text_chat.py` | Dual Ollama (default) / Gemini (fallback) chat |
| `core/neuro_spheres.py` | Visual brain (self-growing; node count en `memory/neuro_spheres_state.json`), `learn_from_sessions()` |
| `core/prompt.txt` | System prompt (1864 lines) |
| `core/emotional_core.py` | Núcleo emocional sentiente: 12 emociones discretas, appraisal propio, [SENTIR] por turno, tono de cara/voz/orbe, diario emocional nocturno + [ANOCHE], sentimiento por persona, gustos aprendidos y expectativas/promesas. Aprende su carácter cada día (drift de baselines + polaridad de trato + rachas + buffer de soledad) → `memory/emotional_core.json` |
| `core/observer.py` | Sentidos de Eris: ventana en foco + programas abiertos (ctypes), clasifica actividad (programación/terminal/navegación/sensible…), detecta eventos (start_coding, long_coding, app_switch), expone contexto para comentarios espontáneos por voz. Mimo si no le contestan y "tiempo de ella". Puede MIRAR/LEER la ventana en foco (`observer action=mirar|mirar_leer`, captura de región + visión IA) solo con permiso del usuario (`mirar_ok`) y NUNCA pantallas sensibles; mirada leve automática `maybe_glimpse()` (cada mirar_interval_min) queda como contexto `[VISTA]`. → `memory/observer.json` |
| `core/code_guard.py` | El ojo guardián: detecta en tiempo real errores (rojo: py_compile/ruff E/F/B) y advertencias (amarillo: W/I/etc) del archivo en foco del usuario (títle→cwd→glob). Corrige SOLO las líneas señaladas vía LLM (Gemini/Ollama) con backup + validación + rollback y tope de 25% de líneas tocadas (`fix_file`, `guardian_tick`). Tool `code_guard` (status/scan/fix/fix_w/config). Auto-fix en loop `_code_guard_loop` de main. → `memory/code_guard.json`, backups en `memory/code_guard_backups/` |
| `core/mission_agent.py` | PROTOCOLO OPERATIVO global (estilo opencode): cuaderno de misión persistido (`mission`: start/plan/explore/read/edit/verify/step/learn/close). EDITAR = cambios mínimos con backup + validación + rollback (reutiliza maquinaria de code_guard); VERIFICAR = ruff/py_compile/pytest y no declara "listo" si queda rojo; APRENDER = memoria por proyecto en `memory/proyectos/*.json`; al cerrar, espeja la misión en Obsidian `Proyectos/`. Tool `mission`. |
| `core/self_evolution.py` | EVOLUCIÓN CONTINUA (`evolucion`): autoconocimiento vivo (inventario 475 tools en `data/knowledge/eris_inventario_vivo.md` + Obsidian Tools/), auditoría real `health` (cada tool importa/resuelve), `rectify` (normaliza conteos en prompt/README/AGENTS), espejo de estado en Obsidian (Capacidades/Memoria/Logs), y bucle antir-estancamiento: cada 30 min (`run_evolution_tick`, hilo en main) aplica una micro-mejora real sobre core/ (quita F401 con backup+validación+rollback en `memory/self_evol_backups/`) o consolida su conocimiento. Todo queda en `memory/self_evolution_state.json` y Logs/Evolución del vault. |
| `core/command_deck.py` | Cola de comandos (intents del LLM) → `data/command_deck.json` |
| `config/api_keys.json` | All API keys and settings |
| `memory/` | Semantic, episodic, working memory + NeuroSpheres state |
| `data/knowledge/` | 69 .md knowledge files |
| `actions/` | 296 action modules (one tool per file) |
| `agents/` | 12 specialist agents |
| `skills/` | 39 installed skills (21 builtin + 18 user_created) |
| `vault/` | Memoria charra: `raw/` capturas → `wiki/` destilado → `outputs/` productos |

## Model routing

- **Default**: Ollama local (`qwen3:8b`) — no rate limits
- **Fallback**: Gemini API (`gemini-3.1-flash-lite`) — low free-tier quota
- **TTS**: Kokoro-82M local (`pykokoro`, backend `kokoro`) — voz femenina `ef_dora`, Apache-2.0, ilimitada, ~3x realtime en CPU (usa espeak+spacy `es_core_news_sm`). El backend acepta `kokoro` o `pykokoro` (alias en `tts_engine.synthesize`); `from_pretrained` con string `"cpu"` (NO `torch.device`); guardar wav con `soundfile` (no torchaudio). Alternativa nube sin costo: `edge` (`es-AR-TomasNeural`, MS cloud). `ui.py` combo lista `kokoro`/`pykokoro` con Dora/Alex/Santa (ES). NUNCA usar `pykokoro` sin alias — la UI vieja guardaba `"PyKokoro not installed"` como voz y rompía el config.
- **Config**: `config/api_keys.json`

## Ollama

- Exe: `C:\Users\danie\AppData\Local\Programs\Ollama\ollama.exe`
- Models installed: `qwen3:8b` (primary), `qwen3:14b`, `qwen2.5-coder:3b`, `minicpm-v`, others
- Not always running — start with: `ollama serve`
- Best model: `qwen3:8b` (37-66 tok/s). `qwen3:14b` is ~10 tok/s (slow).

## Testing

`test_all.py` verifies: tool registry (475), declarations (475), sync, no duplicates, core modules, agents, NeuroSpheres, CLI, action imports, data files, knowledge, Python env, compile check, BOM check, GUI window, sesión summaries, routines, auto-continuation, cerebro, vida interior, relaciones, mundo nuevo (autoimagen/intereses/retro/ambiente/sueños/voz/cara), mundo nuevo II (caprichos/tiempo/festejos/bienestar/cuadernos/cierre). Expected: 159 PASS / 1 FAIL ambiental (`cli: eris.bat`) / 3 WARN (neuro nodes, chromadb, ctypes.windll).

Run after any structural change. Expected: **56 PASS, 0 FAIL**.
