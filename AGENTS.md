# AGENTS.md — ERIS AI

Windows desktop assistant (Python 3.14, PyQt6). 448 tools, NeuroSpheres brain, dual Ollama/Gemini chat, Fish Audio TTS.

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
- **ARRAY type rejected by Gemini**: use `STRING` with JSON-encoded content in declarations (see `actions/office_tools.py` for pattern).
- **Ollama tool_calls**: `arguments` arrives as `dict` (not string) — check `isinstance(raw_args, dict)` before `json.loads`.
- **edge-tts `synthesize()` is async**: call with `asyncio.run(...)`.
- **Vosk**: `KaldiRecognizer` takes a `Model` object, not a string path.
- **pycaw**: use `AudioUtilities.GetSpeakers()` → `.EndpointVolume`. No `Activate()` or `MMDeviceEnumerator`.
- **weather_report**: requires User-Agent `curl/8.0` (Mozilla returns HTML from wttr.in).

## Architecture

| File | Role |
|------|------|
| `main.py` | GUI entry point (PyQt6, 3572 lines) |
| `eris_cli.py` | CLI entry point (terminal, Ollama/Gemini chat) |
| `ui.py` | PyQt6 UI (2908 lines, ErisUI class) |
| `core/tool_registry.py` | 442 tool callables |
| `core/tool_declarations.py` | 444 LLM-facing declarations |
| `core/tool_dispatcher.py` | Executes tools by name |
| `core/action_imports.py` | Imports all 295 action modules |
| `core/gemini_text_chat.py` | Dual Ollama (default) / Gemini (fallback) chat |
| `core/neuro_spheres.py` | Visual brain: 91+ nodes, `learn_from_sessions()` |
| `core/prompt.txt` | System prompt (~1790 lines) |
| `core/emotional_core.py` | Núcleo emocional sentiente: 12 emociones discretas, appraisal propio, [SENTIR] por turno, tono de cara/voz/orbe, diario emocional nocturno + [ANOCHE], sentimiento por persona, gustos aprendidos y expectativas/promesas. Aprende su carácter cada día (drift de baselines + polaridad de trato + rachas + buffer de soledad) → `memory/emotional_core.json` |
| `core/observer.py` | Sentidos de Eris: ventana en foco + programas abiertos (ctypes), clasifica actividad (programación/terminal/navegación/sensible…), detecta eventos (start_coding, long_coding, app_switch), expone contexto para comentarios espontáneos por voz. Mimo si no le contestan y "tiempo de ella". Puede MIRAR/LEER la ventana en foco (`observer action=mirar|mirar_leer`, captura de región + visión IA) solo con permiso del usuario (`mirar_ok`) y NUNCA pantallas sensibles; mirada leve automática `maybe_glimpse()` (cada mirar_interval_min) queda como contexto `[VISTA]`. → `memory/observer.json` |
| `core/code_guard.py` | El ojo guardián: detecta en tiempo real errores (rojo: py_compile/ruff E/F/B) y advertencias (amarillo: W/I/etc) del archivo en foco del usuario (títle→cwd→glob). Corrige SOLO las líneas señaladas vía LLM (Gemini/Ollama) con backup + validación + rollback y tope de 25% de líneas tocadas (`fix_file`, `guardian_tick`). Tool `code_guard` (status/scan/fix/fix_w/config). Auto-fix en loop `_code_guard_loop` de main. → `memory/code_guard.json`, backups en `memory/code_guard_backups/` |
| `core/mission_agent.py` | PROTOCOLO OPERATIVO global (estilo opencode): cuaderno de misión persistido (`mission`: start/plan/explore/read/edit/verify/step/learn/close). EDITAR = cambios mínimos con backup + validación + rollback (reutiliza maquinaria de code_guard); VERIFICAR = ruff/py_compile/pytest y no declara "listo" si queda rojo; APRENDER = memoria por proyecto en `memory/proyectos/*.json`; al cerrar, espeja la misión en Obsidian `Proyectos/`. Tool `mission`. |
| `core/self_evolution.py` | EVOLUCIÓN CONTINUA (`evolucion`): autoconocimiento vivo (inventario 448 tools en `data/knowledge/eris_inventario_vivo.md` + Obsidian Tools/), auditoría real `health` (cada tool importa/resuelve), `rectify` (normaliza conteos en prompt/README/AGENTS), espejo de estado en Obsidian (Capacidades/Memoria/Logs), y bucle antir-estancamiento: cada 30 min (`run_evolution_tick`, hilo en main) aplica una micro-mejora real sobre core/ (quita F401 con backup+validación+rollback en `memory/self_evol_backups/`) o consolida su conocimiento. Todo queda en `memory/self_evolution_state.json` y Logs/Evolución del vault. |
| `core/command_deck.py` | Cola de comandos (intents del LLM) → `data/command_deck.json` |
| `config/api_keys.json` | All API keys and settings |
| `memory/` | Semantic, episodic, working memory + NeuroSpheres state |
| `data/knowledge/` | 62 .md knowledge files |
| `actions/` | 295 action modules (one tool per file) |
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

`test_all.py` verifies: tool registry (442), declarations (442), sync, no duplicates, core modules, agents, NeuroSpheres, CLI, action imports, data files, knowledge, Python env, compile check, BOM check, GUI window.

Run after any structural change. Expected: **56 PASS, 0 FAIL**.
