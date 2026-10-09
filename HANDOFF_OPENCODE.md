# HANDOFF — ERIS lote 2 → opencode

Repo: `/home/soul/ERIS/ERIS-NEW` · branch `main` · HEAD `2beb417`
Python: `.venv-linux/bin/python` (3.14.7) · Correr TODO desde la raíz del repo.
Autor git configurado local: `DaniellRG <126819635+DaniellRG@users.noreply.github.com>`.
**No push a origin** — los commits son locales.

---

## 1. Qué se hizo en el lote 2 (5 commits, ya commiteados)

| Commit | Fix |
|---|---|
| `21a8a1c` | **P1** — 5 tools devolvían basura al LLM |
| `9a6a14a` | **P1 rewrite + P2** — wrappers con `parameters` + `close_orphan()` |
| `fd0584b` | **P3** — permission gate fail-closed + dangerous commands |
| `26744f9` | **P3 event loop + P4** — gate no bloquea + RAG TF-IDF fallback |
| `2beb417` | **P5** — game_agent degrada graceful en Wayland |

### P1 — 5 tools devolvían basura (object at 0x / missing args)
`agent_bus`, `memory_unified`, `permission_gate` → el registry apuntaba a **getters**
(`get_agent_bus()`, `get_memory()`, `get_permission_gate()`) que devuelven singletons →
el LLM recibía `"<object at 0x...>"`. `ast_edit` apuntaba a `safe_edit()` → `missing
required positional`. `eris_update` apuntaba a `check_for_update()` → `None`.

**Fix:** `core/tool_wrappers.py` (NUEVO) — wrappers con firma `(parameters=None, player=None)`
que reciben el dict completo vía `parameters` y hacen action-dispatch. `core/tool_registry.py`
redirige las 5 tools a `core.tool_wrappers`. La clave del dispatch: `_build_kwargs()` en
`core/tool_dispatcher.py` detecta que el primer parámetro se llama `parameters` y pasa el dict entero.

### P2 — pending_tasks huérfanos
Si un post-hook del dispatcher levantaba una excepción, nunca se llegaba a
`resilient.task_completed(task_id, ...)` → el task_id quedaba en `data/pending_tasks.json`
**para siempre**. Acumulación infinita.

**Fix:** `core/resilient.py` +`is_pending()` +`close_orphan()` (marca la task como failed si
sigue pending). `core/tool_dispatcher.py` envuelve el post-hook en `try/finally`; el `finally`
llama `close_orphan` si la task sigue pending. Verificado: 0 huérfanas tras forzar excepción.

### P3 — permission gate fail-open (huecos)
`sudo reboot` y `pc_control shutdown` pasaban como **"safe"**. Sin UI callback → `allow by
default` (fail open). `shell_session` no evaluaba comandos peligrosos.

**Fix en `core/permission_gate.py`:**
- `DANGEROUS_COMMANDS` ampliado: `sudo reboot`, `reboot`, `halt`, `poweroff`, formateo de FS,
  `dd if=`, escritura a `/dev/sd` (antes solo `shutdown`).
- `ALWAYS_CONFIRM` + `DANGEROUS_TOOLS` ahora incluyen `shell_session`, `terminal_agent`,
  `pc_control`, `shutdown_eris`, `process_manager`, `git_control`.
- `assess_risk`: `shell_session` también evalúa `DANGEROUS_COMMANDS`.
- **Fail-closed sin UI**: riesgo `high`/`critical` sin callback → `DENY`. Tools safe siguen allow.
- `gate.check()` corre en `run_in_executor` para no bloquear el event loop con `ui.ask`
  (`input()` síncrono en CLI).

### P4 — RAG inerte
`sentence-transformers` no está instalado → el índice quedaba vacío y `search` devolvía
"sentence-transformers no disponible".

**Fix en `core/rag_engine.py`:** clase `_TfidfModel` (numpy puro, sin torch ni sklearn) como
fallback en `_get_model()`. Construye vocabulario + TF-IDF desde `_collect_notes()`.
`encode()` acepta `**kwargs` (`show_progress_bar`, `batch_size`) para compatibilidad con la
interfaz de sentence-transformers. Verificado: **215 notas indexadas, dim=3183**.

### P5 — game_agent AttributeError en Wayland
`pygetwindow` devuelve `None` tras `except` en Wayland, pero `_focus_game()` llamaba
`gw.getAllWindows()` sin verificar → `AttributeError: 'NoneType'`.

**Fix en `actions/game_agent.py`:** `if gw is None: return False` + `try/except` alrededor del loop.

---

## 2. Baseline de tests (NO bajar de acá)

```
test_all.py  →  PASS: 176 | FAIL: 1 | WARN: 3 | TOTAL: 180
```
El único FAIL es ambiental: `cli: eris.bat not found` (script Windows, no existe en Linux).
Los 3 WARN: `neuro: Only 27 nodes (expected >= 80)`, `chromadb not installed`,
`gui: module 'ctypes' has no attribute 'windll'`.

Tool sync: **504/504, 0 duplicados**.

Comando:
```bash
cd /home/soul/ERIS/ERIS-NEW && timeout 300 .venv-linux/bin/python test_all.py 2>&1 | grep -E "PASS:|FAIL:|WARN:|TOTAL:"
```

---

## 3. ⚠️ REGLA DE ORO — WIP del usuario NO SE TOCA

Estos 6 archivos están modificados en el working tree **por el dueño (Daniel)** y **NO están
commiteados**. NO los edites, NO los commitees, NO les hagas `git checkout`:

```
 M core/gemini_text_chat.py                       (+30)   print→pass
 M data/cli_sessions/default.json                 (+226)  sesión CLI
 M data/knowledge/eris_inventario_vivo.md         (+2)
 M eris_cli.py                                    (+339)  banner ERIS-AGENT
 M memory/self_care_apuntes.md                    (+27)
 M vault/Capacidades/Estado de Evolución.md       (+2)
```

**Trampa real que ya pasó en el lote 2:** hacer `git checkout HEAD -- core/tool_dispatcher.py`
borra el WIP del dueño en ese archivo (`print → pass`). Si necesitás editarlo, usá
`git apply --cached` con un patch que contenga SOLO tus hunks:

```bash
# 1. backup
cp core/tool_dispatcher.py /tmp/backup_dispatcher.py
# 2. version HEAD + aplicar SOLO tus ediciones con str.replace exacto (script Python)
# 3. git diff --cached --stat   ← verificar que NO aparezcan los 6 archivos de arriba
# 4. git commit SOLO tus archivos (nunca git add -A)
```

Los 27 archivos untracked (`data/agent_traces/*.json`, `memory/sub_agent_plans/*.json`,
`data/cli_history.txt`, etc.) son artefactos de runtime, no tocar.

---

## 4. Backend / configuración

`config/api_keys.json` (UTF-8 **sin BOM** — con BOM crashea al cargar):
- `openrouter_api_key` = token de Nous Portal (sincronizado con `~/.hermes/auth.json`)
- `openrouter_base_url` = endpoint de inferencia de Nous Portal
- `openrouter_model` = `meituan/longcat-2.5-preview:free`
- `gemini_api_key` = `""` (vacío a propósito: las declarations de Eris rompen el schema de Gemini)
- `xkairo_admin_key` = validada (130 modelos, HTTP 200), `xkairo_base_url` = `https://api.xkiro.com/v1`,
  `xkairo_model` = `deepseek/deepseek-chat`
- `os_system` = `"windows"` ← **desactualizado en este Linux box**. Solo lo lee
  `actions/send_message.py:60`. Candidato a fix (usar `os.name` o actualizarlo a `"linux"`).

**Failover chain** en `core/gemini_text_chat.py`: openrouter (Nous) → groq → ollama.
Sin Gemini key y sin Ollama instalado → **Nous es punto único de falla**.

**Token desync:** Hermes rota `agent_key` en `~/.hermes/auth.json` cada ~1h. `core/token_sync.py`
resincroniza automáticamente al arrancar. Si Eris da 401, correr el sync.

**Arranque:**
```bash
eris                          # wrapper → .venv-linux/bin/python eris_cli.py
# o GUI:
cd /home/soul/ERIS/ERIS-NEW && PYTHONUNBUFFERED=1 .venv-linux/bin/python main.py
```
La GUI expone `POST http://127.0.0.1:8765/chat {"text":"..."}` (canal programático confiable
en Wayland — `wtype` no llega al campo de texto).

---

## 5. Pendientes reales (verificados, no inventados)

1. **`os_system: "windows"`** en config → solo afecta `send_message.py`. Fix chico.
2. **`visual_expressions`** requiere `libtk8.6.so` del paquete de sistema `tk`
   (`sudo pacman -S tk`). Sin eso, tkinter no importa.
3. **xKiro como backend**: key válida, 130 modelos, pero **no soporta creación programática de
   keys** (los endpoints `/api-keys`, `/api-keys/create` dan 404). Config ya presente; falta
   integrarlo al failover chain y mapear nombres de modelo (`deepseek-chat` → `deepseek/deepseek-chat`).
4. **ORBE GUI**: verificar que escuche en el puerto `6790` cuando arranca `eris_cli.py`
   (ahora no escucha porque Eris no está corriendo).
5. **AGENTS.md**: el docstring dice "16 agentes" y es correcto
   (`AGENT_DEFINITIONS` tiene 16: comm, core, deploy, dev, file, guardian, linux, media,
   memoria, mentora, pentest, security, study, system_monitor, vision, web). Verificar si el
   conteo de tools (dice 504) sigue alineado.
6. **GUI-automation en Wayland** (browser_control, computer_control, native_ui, desktop_control,
   screen_vision): degradadas a mensaje de error / None. Equivalente Wayland = ydotool (input)
   + grim/OCR (visión), sin portar.

---

## 6. Trampas del repo (de AGENTS.md — leerlo completo antes de tocar nada)

- **Tool sync es sagrado**: si agregás/quitás tools, editá BOTH `core/tool_registry.py` AND
  `core/tool_declarations.py`, y verificá `len(registry) == len(declarations)` y 0 duplicados.
- **`pyautogui`/`pygetwindow` = guard `except Exception`, NUNCA `except ImportError`**:
  en Wayland sin X11, `import pyautogui` levanta `Xlib.error.XauthError` (no ImportError) y
  `import pygetwindow` levanta `NotImplementedError`. Sin guard, se cae **todo**
  `core/action_imports.py` al arrancar.
- **Deps opcionales = guard + `if _OK:`**: ninguna referencia a nivel de módulo puede usar un
  nombre importado dentro de un `try/except ImportError` (ni constantes, ni bases de clase, ni
  defaults) — `NameError`/`TypeError` al importar tumba todo el árbol.
- **Rutas portables, nunca hardcodeadas**: nada de `D:\Eris_*`, `C:\Users\...`, `ctypes.windll`
  fuera de `if os.name == "nt"`. Usar `BASE = Path(__file__).resolve().parent.parent`.
- **Gemini limita a 128 function_declarations**: `core/gemini_text_chat.py` envía un subconjunto
  priorizado ≤120 vía `_gemini_tools()`. No revertir a `TOOL_DECLARATIONS` completo.
- **`custom_tools.json`/`extra_tools.json`**: toda entrada SIEMPRE con `"name"`; una entrada a
  medias rompe `decl["name"]` en TODOS los constructores y tumba el chat.
- **Terminal Linux**: `core/shell_session.py` lanza bash persistente; `sudo` abre diálogo gráfico
  vía `SUDO_ASKPASS=tools/eris_askpass.py`. Nunca `echo "...password..." | sudo -S`.
- **`core/action_imports.py` usa `except Exception:`** (NO `ImportError`) en los 233 bloques — no
  revertir.
- **Hyprland ≥0.55**: `hyprctl dispatch` es Lua (`hl.dsp.focus({...})`); la sintaxis legacy
  `focuswindow address:...` crashea con rc 7.

---

## 7. Cómo verificar antes de decir "listo"

```bash
cd /home/soul/ERIS/ERIS-NEW

# 1. compile
find core actions agents -name "*.py" -exec python3 -m py_compile {} + ; echo "compile=$?"

# 2. sync de tools
.venv-linux/bin/python -c "
from core.tool_registry import get_all_tool_names
from core.tool_declarations import TOOL_DECLARATIONS
r=list(get_all_tool_names()); d=[x['name'] for x in TOOL_DECLARATIONS]
print(f'reg={len(r)} dec={len(d)} dups={len(d)-len(set(d))} sync={len(r)==len(d) and len(d)==len(set(d))}')"

# 3. suite (baseline 176/1/3 — no bajar)
timeout 300 .venv-linux/bin/python test_all.py 2>&1 | grep -E "PASS:|FAIL:|WARN:|TOTAL:"

# 4. git — confirmar que el WIP del dueño sigue intacto
git status --short | grep -v '^??'
```
