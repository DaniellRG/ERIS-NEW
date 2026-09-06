# ERIS AI — Asistente Autónomo Multi-SO

Asistente virtual de escritorio con autonomía total, integración profunda,
inteligencia emocional, NeuroSpheres y **456 tools**. Funciona en **Windows y
Linux** (CachyOS/Arch) con el mismo repositorio — podés trabajar en tus dos
máquinas en paralelo sincronizando por git.

> 📌 **Si estás leyendo esto desde la laptop Linux**: tenés todo lo que ERIS
> es y hace. Este README + `README_LINUX.md` te guían para arrancar y saber
> qué tiene.

---

## 1. Qué es ERIS

ERIS es un asistente de escritorio que:

- **Chatea por voz y texto** (Gemini Live en la nube + Ollama local).
- **Siente y evoluciona**: sistema emocional, NeuroSpheres (cerebro visual que
  crece), y un loop de **auto-evolución continua** que la mantiene aprendiendo
  y nunca estancada.
- **Guarda todo en Obsidian**: memoria, capacidades, aprendizaje, misiones,
  neuroesferas y proyecto vivo.
- **Ejecuta 456 herramientas** (archivos, terminal, web, memoria, código,
  sistema, comunicación, multimedia, autonomía).
- **Se autocuida**: self-healing, code_guard (corrige su propio código),
  crash recovery, auto-backup.

---

## 2. Arquitectura

```
Eris_Source/
├── main.py                  # Entry point GUI (PyQt6) — arranca Eris
├── eris_cli.py              # CLI terminal (estilo opencode)
├── ui.py                    # UI principal (orbe, emociones, ventana)
├── config/
│   └── api_keys.json        # 🔒 API keys, modelos, configuración (gitignored)
├── core/                    # Motor interno
│   ├── tool_registry.py         # 456 tools registradas
│   ├── tool_declarations.py     # Declaraciones para el LLM
│   ├── tool_dispatcher.py       # Ejecutor de tools
│   ├── action_imports.py        # Imports tolerantes de 296 action modules
│   ├── prompt.txt               # System prompt de ERIS
│   ├── mission_agent.py         # Tool #447 "mission"
│   ├── self_evolution.py        # Tool #456 "evolucion" (autoconocimiento vivo)
│   ├── code_guard.py            # Auto-corrección de código (F401, backups, rollback)
│   ├── logging_setup.py         # BASE_DIR + get_obsidian_vault() PORTABLE
│   ├── platform.py              # Capa de abstracción cross-platform
│   ├── neuro_spheres.py         # Cerebro visual auto-creciente
│   ├── emotional_state/emotional_core.py
│   ├── gemini_text_chat.py      # Chat dual Ollama/Gemini
│   ├── knowledge_graph.py       # Grafo de conocimiento (vault portable)
│   ├── learning_pipeline.py     # Aprendizaje autónomo → Obsidian
│   ├── goal_setting.py          # Metas autónomas
│   └── ... (conectividad, self_healing, offline_voice, tts_engine...)
├── actions/                 # 296 módulos de acciones (volumen, apps, web...)
├── agents/                  # 9 agentes especializados
├── skills/                  # 39 skills instaladas
├── eris_workspace/          # Workspace 3D (ursina/panda3d)
├── android_eris/            # Build APK Android (config con key → gitignored)
├── memory/                  # Estado de memoria, evolución, backups
├── data/                    # Conocimiento, sesiones, caches (parcial gitignored)
│   └── knowledge/           # 69 archivos .md de conocimiento
├── test_all.py              # 57 tests (0 fallos)
├── requirements.txt         # Dependencias Windows
├── requirements-linux.txt   # Dependencias Linux (sin paquetes win-only)
├── run_linux.sh             # 🐧 Arranque en Linux (crea venv, instala, lanza)
└── README_LINUX.md          # 🐧 Guía de despliegue Linux
```

---

## 3. Lanzamiento

### Instalacion one-liner (recomendada para cualquier PC)

**Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/DaniellRG/ERIS-NEW/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/DaniellRG/ERIS-NEW/main/install.ps1 | iex"
```

Instalan en `~/.eris/ERIS-NEW` (no tocan el workspace de desarrollo), crean
el venv, instalan deps, dejan el comando `eris` y abren el **wizard de
bienvenida** (API keys: REQUERIDA la de Gemini para chatear por internet;
las OPCIONALES pueden quedarse vacias). Nada descarga modelos de IA — el
uso local con Ollama es aparte y opcional. Actualizar: `eris --update`.

### Windows (PC de escritorio)
```cmd
cd D:\Eris_Source
.\.venv\Scripts\pythonw.exe main.py
```

### Linux (laptop CachyOS)
```bash
cd Eris_Source
./run_linux.sh
```

### CLI (ambos)
```cmd
eris
```

### Tests (ambos)
```cmd
python test_all.py        # gate: 56 PASS, 0 FAIL
```

---

## 4. Tools (456)

Las 456 tools están sincronizadas entre `tool_declarations.py`,
`tool_registry.py` y `action_imports.py`. Categorías principales:

| Categoría | Ejemplos |
|-----------|----------|
| **Archivos** | read, write, edit, glob, grep, file_organizer |
| **Terminal** | shell, shell_elevated, shell_session |
| **Web** | web_search, web_fetch, web_scrape, browser_control |
| **Memoria** | memory_read, memory_write, memory_search, memory_consolidation |
| **NeuroSpheres** | neuro_spheres (add, connect, strengthen, query, learn) |
| **Código** | ast_analyze, ast_edit, code_review, project_builder |
| **Sistema** | system_monitor, computer_control, process_manager |
| **Comunicación** | gmail_control, telegram, whatsapp, discord |
| **Multimedia** | image_generation, tts, speech_to_text, screen_vision |
| **Autonomía** | self_evolution, self_edit, autonomous_learner |
| **Emociones** | emotional_state, neural_bridge, world_simulation |
| **IDE** | ide_integration |
| **Misión** | mission (#447) — plantea y persigue tu misión |
| **Evolución** | evolucion (#456) — autoconocimiento vivo, salud, Obsidian |

---

## 5. Gear clave de autonomía

| Componente | Qué hace |
|---|---|
| **`evolucion` (#456)** | Autoconocimiento vivo: status, health, inventory, rectify, sync, evolve, tick, learn, log. Loop cada 30 min que la mantiene evolucionando (nunca se estanca). Registra en Obsidian `Tools/`, `Aprendizaje/`. |
| **`mission` (#447)** | Define y persigue la misión global; al cerrar espeja la misión en Obsidian `Proyectos/`. |
| **`code_guard`** | Audita y corrige su propio código (mata imports sin uso, backup + rollback si rompe). Ya se corrigió sola 2 veces. |
| **Self-healing** | Monitorea y repara módulos caídos. |
| **Auto-evolución loop** | Tick inmediato al arrancar + cada 30 min; estado en `memory/self_evolution_state.json`. |

---

## 6. NeuroSpheres

Cerebro visual que crece con cada interacción (estado en
`memory/neuro_spheres_state.json`). 11 esferas: **aprendizaje,
memoria, emociones, habilidad, investigacion, codigo, error/bug/solucion,
diagnostico**, y más. Cada sesión genera nodos automáticamente.

---

## 7. Modelo de IA

- **Nube (default)**: Gemini — `gemini-3.1-flash-lite` (conversación) y
  `gemini`/`gemini-search` para agentes y búsqueda.
- **Local**: Ollama — `qwen3:8b` (cerebro dual, sin rate limits).
- **Otros**: OpenRouter, Groq, Cerebras (fallbacks secundarios).
- **Voz**: Fish Audio (voz personalizada) + edge-tts/gtts (local cloud).
- **Voz local offline**: Vosk (STT) + edge-tts + Ollama.
- **Config**: `config/api_keys.json` (todas las claves ahí).

---

## 8. Vault de Obsidian (memoria persistente)

ERIS guarda su segundo cerebro en Obsidian. Ruta resuelta de forma **portable**
por `core/logging_setup.get_obsidian_vault()`, en este orden:

1. Variable de entorno `ERIS_OBSIDIAN_VAULT`
2. Carpeta hermana `../Eris_NEW/BaseDatosObsidian/BaseObsiEris`
3. `D:/Eris_NEW/BaseDatosObsidian/BaseObsiEris` (Windows)
4. `obsidian_vault/` local (fallback)

Contenido vivo: `Tools/`, `Capacidades/`, `Memoria/`, `Logs/`, `Aprendizaje/`,
`Proyectos/`, `NeuroSpheres/` (687 notas).

---

## 9. Portabilidad Linux (Fase 1 — lista)

- ✅ Arranca y **chatea por texto** en Linux (Gemini/Ollama).
- ✅ Memoria, emociones, NeuroSpheres, evolución, Obsidian.
- ✅ UI PyQt6, TTS nube, Vosk.
- ✅ **Controles de sistema Linux** (mismos tools que Windows): volumen →
  pactl/wpctl, ventanas → hyprctl (Hyprland, sintaxis Lua), notificaciones →
  notify-send, monitor/wifi/bluetooth → hyprctl/nmcli/rfkill, brillo →
  brightnessctl, captura → grim. Cero deps pip (solo paquetes de sistema).

> Ver `README_LINUX.md` para la guía completa de despliegue en la laptop.

---

## 10. Trabajo en paralelo (2 máquinas)

Flujo recomendado: **un solo repo**, commit por máquina.

```
PC escritorio (Windows)         Laptop (CachyOS / Linux)
      |  git push                    |  git pull
      +---------------------------->+
      |  git pull                    |  git push
      +<----------------------------+
```

Reglas:
- Nunca editar lo mismo en ambas máquinas a la vez (git avisará conflictos).
- `api_keys.json` y el vault Obsidian **NO viajan en git** — copialos aparte.
  Conservalos igual en ambas (la laptop apunta a `$HOME/Eris_NEW/...`).

---

## 11. Estado actual (validado)

- ✅ **56 PASS / 0 FAIL** en Windows (`test_all.py`)
- ✅ **456 tools sincronizadas** (456 registry = 456 declarations, 0 duplicados)
- ✅ **0 imports rotos** — `590 .py` compilan; `action_imports` importa limpio
  incluso sin PyQt6/openpyxl (deps opcionales degradan con gracia)
- ✅ **0 duplicados** / 0 stubs muertos / 0 BOMs
- ✅ **NeuroSpheres** creciendo por sesión (46 nodos al último sync)
- ✅ **69 knowledge files**
- ✅ **9/9 agents** en uso
- ✅ **Árbol importa sin paquetes Windows** → listo para Linux

---

## 12. Requisitos

- **Python 3.14** (Windows) / 3.12+ (Linux)
- **PyQt6** + webengine
- **Ollama** (opcional, cerebro local) + modelo `qwen3:8b`
- **API keys** (Gemini, Fish Audio, etc.) en `config/api_keys.json`
- **Linux**: `portaudio pipewire-pulse` (sistema)
