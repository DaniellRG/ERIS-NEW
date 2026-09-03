# ERIS AI — Asistente Autónomo Multi-SO

Asistente virtual de escritorio con autonomía total, integración profunda,
inteligencia emocional, NeuroSpheres y **448 tools**. Funciona en **Windows y
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
- **Ejecuta 448 herramientas** (archivos, terminal, web, memoria, código,
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
│   ├── tool_registry.py         # 448 tools registradas
│   ├── tool_declarations.py     # Declaraciones para el LLM
│   ├── tool_dispatcher.py       # Ejecutor de tools
│   ├── action_imports.py        # Imports tolerantes de 295+ action modules
│   ├── prompt.txt               # System prompt de ERIS
│   ├── mission_agent.py         # Tool #447 "mission"
│   ├── self_evolution.py        # Tool #448 "evolucion" (autoconocimiento vivo)
│   ├── code_guard.py            # Auto-corrección de código (F401, backups, rollback)
│   ├── logging_setup.py         # BASE_DIR + get_obsidian_vault() PORTABLE
│   ├── platform.py              # Capa de abstracción cross-platform
│   ├── neuro_spheres.py         # Cerebro visual (95+ nodos)
│   ├── emotional_state/emotional_core.py
│   ├── gemini_text_chat.py      # Chat dual Ollama/Gemini
│   ├── knowledge_graph.py       # Grafo de conocimiento (vault portable)
│   ├── learning_pipeline.py     # Aprendizaje autónomo → Obsidian
│   ├── goal_setting.py          # Metas autónomas
│   └── ... (conectividad, self_healing, offline_voice, tts_engine...)
├── actions/                 # 295+ módulos de acciones (volumen, apps, web...)
├── agents/                  # 9 agentes especializados
├── skills/                  # 39 skills instaladas
├── eris_workspace/          # Workspace 3D (ursina/panda3d)
├── android_eris/            # Build APK Android (config con key → gitignored)
├── memory/                  # Estado de memoria, evolución, backups
├── data/                    # Conocimiento, sesiones, caches (parcial gitignored)
│   └── knowledge/           # 62+ archivos .md de conocimiento
├── test_all.py              # 57 tests (0 fallos)
├── requirements.txt         # Dependencias Windows
├── requirements-linux.txt   # Dependencias Linux (sin paquetes win-only)
├── run_linux.sh             # 🐧 Arranque en Linux (crea venv, instala, lanza)
└── README_LINUX.md          # 🐧 Guía de despliegue Linux
```

---

## 3. Lanzamiento

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
python test_all.py        # 57/57 PASS
```

---

## 4. Tools (448)

Las 448 tools están sincronizadas entre `tool_declarations.py`,
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
| **Evolución** | evolucion (#448) — autoconocimiento vivo, salud, Obsidian |

---

## 5. Gear clave de autonomía

| Componente | Qué hace |
|---|---|
| **`evolucion` (#448)** | Autoconocimiento vivo: status, health, inventory, rectify, sync, evolve, tick, learn, log. Loop cada 30 min que la mantiene evolucionando (nunca se estanca). Registra en Obsidian `Tools/`, `Aprendizaje/`. |
| **`mission` (#447)** | Define y persigue la misión global; al cerrar espeja la misión en Obsidian `Proyectos/`. |
| **`code_guard`** | Audita y corrige su propio código (mata imports sin uso, backup + rollback si rompe). Ya se corrigió sola 2 veces. |
| **Self-healing** | Monitorea y repara módulos caídos. |
| **Auto-evolución loop** | Tick inmediato al arrancar + cada 30 min; estado en `memory/self_evolution_state.json`. |

---

## 6. NeuroSpheres (95+ nodos)

Cerebro visual que crece con cada interacción. 11 esferas: **aprendizaje,
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
- ⚠️ **Pendiente (Fase 2)**: control de volumen (→ pulsectl), control de
  ventanas (→ xdotool/ydotool), notificaciones (→ notify-send), brillo/energía
  (→ systemctl/xrandr).

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

- ✅ **57/57 tests** pass (`test_all.py`)
- ✅ **448 tools** sincronizadas
- ✅ **0 imports rotos** (verificado también en Linux-simulado: 26/26 + 72/72)
- ✅ **0 duplicados** / 0 stubs muertos / 0 BOMs
- ✅ **95+ nodos NeuroSpheres** con contenido real
- ✅ **62+ knowledge files**
- ✅ **9/9 agents** en uso
- ✅ **Árbol importa sin paquetes Windows** → listo para Linux

---

## 12. Requisitos

- **Python 3.14** (Windows) / 3.12+ (Linux)
- **PyQt6** + webengine
- **Ollama** (opcional, cerebro local) + modelo `qwen3:8b`
- **API keys** (Gemini, Fish Audio, etc.) en `config/api_keys.json`
- **Linux**: `portaudio pipewire-pulse` (sistema)
