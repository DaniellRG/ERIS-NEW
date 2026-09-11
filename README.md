# ERIS AI — Asistente Autónoma Multi-SO

Asistente virtual de escritorio **100% Python** (3.14 + PyQt6) con autonomía total,
inteligencia emocional, NeuroSpheres, auto-evolución y **477 tools**. Corre en
**Windows y Linux** (CachyOS/Arch) desde el mismo repositorio — pensado para
trabajar en paralelo desde dos máquinas sincronizando por git.

> 📌 **Si estás retomando contexto desde otra PC**: leé la sección
> [2. Cómo retomar](#2-cómo-retomar-el-contexto) y la
> [3. Bitácora de mejoras recientes](#3-bitácora-de-mejoras-recientes-2026-09). Esto
> es un proyecto vivo; el `git log` local y este README son la fuente de verdad.

---

## 1. Qué es ERIS

ERIS es un asistente de escritorio que:

- **Chatea por voz y texto** — Gemini Live (nube, baja latencia) + Ollama local.
- **Siente y evoluciona**: sistema emocional, NeuroSpheres (cerebro visual que
  crece), diario emocional nocturno, y un loop de **auto-evolución continua**
  que la mantiene aprendiendo y nunca estancada.
- **Guarda todo en Obsidian**: memoria, capacidades, aprendizaje, misiones,
  neuroesferas y proyecto vivo.
- **Ejecuta 459 herramientas**: archivos, terminal, web, memoria, código,
  sistema, comunicación, multimedia, autonomía, IDE.
- **Se autocuida**: code_guard (corrige su propio código con backup+rollback),
  self-healing, crash recovery, auto-backup, y la **Guardiana** (supervisora de
  autocuidado).
- **Aprende a aprender**: la **Mentora** integra fuentes de conocimiento y
  genera lecciones que sí impactan respuestas futuras.

**Idioma**: español (colombiana). **NO usa Node/Bun**: es Python puro — los
scripts Node/JS solo existen como plantillas para generar proyectos de usuario.

---

## 2. Cómo retomar el contexto

Estado del repote y cómo seguir después de un tiempo sin tocar el código:

1. **Regenerate**: `git pull` en la otra PC; `git log --oneline -15` para ver lo
   último; probar `python test_all.py` (gate: 56 PASS en esta máquina).
2. **Tools son sagradas**: `core/tool_registry.py` == `core/tool_declarations.py`
   (`len` igual, 0 duplicados). Si agregás/quitas una tool, editás AMBOS y
   verificás, después reiniciar ERIS. Hoy: **459 = 459**.
3. **Agentes**: la fuente única de verdad es `core/agent_definitions.py`
   (12 agentes + keywords + handlers + penalty_keywords). `core/agent_router.py`
   la importa (no duplica) y purga el registro stale. **NO** editar
   `core/agent_registry.json` a mano: se regenera.
4. **Gemini limita function_declarations a 128**: el chat texto envía un
   subconjunto priorizado <=120 vía `_gemini_tools()`; el modo Live envía 85
   (sin nombres reservados). No revertir a `TOOL_DECLARATIONS` completo en el
   payload de Gemini.
5. **Nombres reservados de Gemini Live**: las funciones no pueden empezar con
   `google`/`_` ni llamarse `reset`/`default`. El filtro de `LIVE_TOOL_DECLARATIONS`
   ya los excluye automáticamente (caso real: `google_calendar`).
6. **pytest no está instalado** en `.venv-linux`; los tests de `tests/` se
   validan con asserts directos o con `test_all.py`.
7. **Vault Obsidian**: NO viaja en git. Se resuelve portable con
   `core/logging_setup.get_obsidian_vault()` (env `ERIS_OBSIDIAN_VAULT`, luego
   carpeta hermana `../Eris_NEW/BaseDatosObsidian/BaseObsiEris`).
8. **`config/api_keys.json`** NO viaja (gitignored). Es UTF-8 **sin BOM**. Ahí
   viven las API keys y la configuración (voz, backend TTS, modelo, etc.).

---

## 3. Bitácora de mejoras recientes (2026-09)

Todo esto está en `main` y pusheado a `origin`.

### 🩺 Fix Live 1011 crónico (2026-09-07, `e8bbfd7`)
- **`google_calendar` fuera del payload Live**: su nombre viola la regla de
  Gemini (no empezar con `google`). Podía cerrar la sesión con **1011** durante
  la fase de function-calling. Ahora `LIVE_TOOL_DECLARATIONS` excluye por regla
  (prefijo `google`, `_`, `reset`, `default`), también en el fallback de 140. Live: 85 declaraciones.
- **Modelo primario estable**: `models/gemini-2.5-flash-native-audio-latest`
  (alias GA); el `gemini-3.1-flash-live-preview` quedó como 1er fallback. Los
  `-preview` rotan y son la fuente típica de 1011. Fallback automático tras 3 fallos.

### ⚡ Performance (2026-09-06, `70fe0af`)
- **Caché central de config** (`core/audio_config.get_config`, invalidación por
  mtime): `api_keys.json` se leía ~30+ veces en hot paths; ahora 1 lectura.
- **`_gemini_tools()` cacheado** (firma de `TOOL_DECLARATIONS`): las 120
  declaraciones ya no se reconstruyen por turno.
- **TTS Fish en paralelo**: chunks vía `asyncio.gather` + POST en
  `asyncio.to_thread` (textos largos = 1/2~1/N del tiempo, sin bloquear el loop).
- **Prompt cacheado** (`core/prompt_loader.load_system_prompt`, ~134 KB): no se
  relee en cada reconexión.
- **Latencia offline 4x menor**: poll `0.2s → 0.05s` en `core/offline_voice.py`.
- **Timeouts de red** bajados en `core/local_brain.py` (180s→60s, 45s→30s).
- ⚠️ El spin del main thread (~67% CPU) es **preexistente** (medido contra
  baseline): viene del hot-loop `asyncio.sleep(0.01)` de `_listen_audio`. Pendiente
  de optimizar con cola bloqueante.

### 🗂️ Refactor agent-router — una sola fuente de verdad (2026-09-06, `d1d621d`)
- `core/agent_definitions.py` = 12 agentes (keywords + penalty_keywords +
  handlers + tools). El router **importa** de ahí; `agent_registry.json`
  regenerado a 12 (purga 6 stale: home/reverse/search/self/productivity/system).
- Herramientas rotas corregidas: `game_updater` eliminado, `semantic_memory→memory_unified`.
- Clasificación afinada 100%: visión recuperó "qué ves"/"qué hay en la pantalla";
  security recuperó "escaneá la red"/"busca virus"/"puerto"; `study` ruteando.

### 🎓 Mentora — maestra de ERIS (2026-09-06, `0e15c68` + `d6252e1`)
- `agents/mentora_agent.py`: acciones learn/search/teach/apply/report/import/
  explorar/fuentes/help. Lecciones en `memory/mentora_lecciones.json` y
  `mentora_ensena.json`.
- `config/fuentes_aprendizaje.json`: fuentes por dominio (programación, ciencia,
  IA, general, videos, datasets) + `exploracion_libre: true`.

### 🛡️ Guardiana — supervisor de autocuidado (2026-09-06, `2e34cb8`)
- `agents/guardiana_agent.py`: monitorea el bienestar de ERIS y dispara
  auto-correcciones; `_run_guardian_supervision` en `main.py`.

### 🐧 Previo (2026-09-05/06)
- Instaladores one-liner `install.sh`/`install.ps1` + launcher `eris` + wizard.
- Portabilidad Linux completa (Hyprland, controles nativos, terminal libre bash
  persistente + sudo on-demand, 6 tools nuevas, audio fluido con jitter buffer).

---

## 4. Arquitectura

```
ERIS-NEW/
├── main.py                  # Entry point GUI (PyQt6)
├── eris_cli.py              # CLI terminal
├── ui.py                    # UI principal (orbe, emociones, ventana)
├── config/
│   ├── api_keys.json        # 🔒 API keys y configuración (gitignored)
│   └── fuentes_aprendizaje.json  # Fuentes de conocimiento de la Mentora
├── core/                    # Motor interno
│   ├── tool_registry.py         # 488 tools (callables)
│   ├── tool_declarations.py     # 459 declaraciones + LIVE (85, sin reservados)
│   ├── tool_dispatcher.py       # Ejecutador de tools
│   ├── action_imports.py        # Imports tolerantes de 296 action modules
│   ├── agent_definitions.py     # ⭐ Fuente única de verdad de 12 agentes
│   ├── agent_router.py          # Enruta a los agentes (importa las definiciones)
│   ├── prompt.txt               # System prompt de ERIS (~1864 líneas)
│   ├── prompt_loader.py         # Carga prompt cacheada (mtime)
│   ├── audio_config.py          # Modelos Live, voces, devices, get_config()
│   ├── gemini_text_chat.py      # Chat dual Ollama/Gemini (tools <=120)
│   ├── local_brain.py           # Cerebro local (Ollama + tools) offline
│   ├── offline_voice.py         # STT Vosk + loop de voz offline
│   ├── tts_engine.py            # TTS (edge/fish/gemini), fish en paralelo
│   ├── mission_agent.py         # Tool "mission"
│   ├── self_evolution.py        # Tool "evolucion" (autoconocimiento vivo)
│   ├── code_guard.py            # Auto-corrección de código (backup+rollback)
│   ├── logging_setup.py         # BASE_DIR + get_obsidian_vault() PORTABLE
│   ├── neuro_spheres.py         # Cerebro visual auto-creciente
│   ├── emotional_core.py        # Núcleo emocional sentiente (12 emociones)
│   ├── observer.py              # Sentidos: ventana en foco, mirada con permiso
│   ├── platform_self.py / platform.py  # Capa cross-platform
│   └── ... (conectividad, self_healing, daily_digest, llm_bridge...)
├── actions/                 # 296 módulos de acciones (uno por tool)
├── agents/                  # 12 agentes especializados
├── skills/                  # 39 skills (21 builtin + 18 user)
├── memory/                  # Estado de memoria, evolución, backups, lecciones
├── data/
│   └── knowledge/           # 69 archivos .md de conocimiento (inventario vivo)
├── test_all.py              # Gate de tests
├── requirements.txt / requirements-linux.txt
├── install.sh / install.ps1 / run_linux.sh
└── README_LINUX.md          # Guía de despliegue Linux
```

---

## 5. Agentes especializados (12)

Ruteados por `core/agent_router.py` desde `core/agent_definitions.py`. Cada uno
tiene keywords, penalty_keywords, handler y tools propias:

| Agente | Rol |
|---|---|
| **core** | Núcleo general (router se queda sin match) |
| **web** | Búsqueda, navegación, scraping |
| **file** | Archivos, memoria, conocimiento |
| **dev** | Código, terminal, git |
| **media** | Imagen, video, audio, TTS |
| **comm** | Mensajes, notificaciones, redes |
| **vision** | Ver pantalla/ventanas, describir lo visible |
| **security** | Escaneos, virus, puertos, pentest |
| **study** | Estudio, repaso, notas |
| **linux** | Control del sistema Linux (Hyprland, audio, red) |
| **guardian** (Guardiana) | Autocuidado de ERIS |
| **mentora** (Mentora) | Aprendizaje continuo y fuentes de conocimiento |

---

## 6. Voz y modelos de IA

- **Voz en vivo (Gemini Live API)** — primario **`gemini-2.5-flash-native-audio-latest`**
  (estable), fallback automático a `gemini-3.1-flash-live-preview` → luego
  `gemini-2.5-flash-native-audio-preview-12-2025`.
- **Texto**: `gemini-flash-latest` (model_for_conversation); agentes `gemini`;
  búsqueda `gemini`.
- **Local**: Ollama (`ollama_model: llama3.2` en esta máquina; `qwen3:8b` como
  cerebro dual recomendado) — sin rate limits.
- **STT**: Vosk local (modelo ya en `config/vosk_model`) + transcripción del Live.
- **TTS**: edge-tts default (`tts_backend: edge`, voz `es-AR-TomasNeural`);
  Fish Audio opcional (`s2.1-pro-free`) con voz personalizada; voces de
  Gemini Live (`Aoede`... `Orus`) para el modo en vivo.
- Toda la configuración vive en `config/api_keys.json`.

---

## 7. Gear clave de autonomía

| Componente | Qué hace |
|---|---|
| **`evolucion`** | Autoconocimiento vivo: status, health, inventory, rectify, tick… Loop cada 30 min que la mantiene evolucionando. Estado en `memory/self_evolution_state.json`. |
| **`mission`** | Define y persigue la misión global; al cerrar espeja en Obsidian `Proyectos/`. |
| **`code_guard`** | Audita y corrige su propio código (mata imports sin uso, backup + rollback si rompe). |
| **`guardiana`** | Supervisor de autocuidado continua de ERIS. |
| **`mentora`** | Ingiere fuentes, explora libre, y genera lecciones que impactan respuestas. |
| **Self-healing / crash recovery** | Repara módulos caídos y sobrevive a cortes. |

---

## 8. NeuroSpheres

Cerebro visual que crece con cada interacción
(`memory/neuro_spheres_state.json`). Esferas de aprendizaje, memoria, emociones,
habilidad, investigación, código, error/bug/solución, diagnóstico… (en esta
máquina ~60 nodos y creciendo; el test espera >= 80, por eso un WARN).

---

## 9. Vault de Obsidian (memoria persistente)

Segundo cerebro de ERIS, resuelto portable (ver arriba). Contenido vivo:
`Tools/`, `Capacidades/`, `Memoria/`, `Logs/`, `Aprendizaje/`, `Proyectos/`,
`NeuroSpheres/`.

---

## 10. Portabilidad Linux (lista)

- ✅ Arranca y chatea por voz y texto en Linux.
- ✅ Memoria, emociones, NeuroSpheres, evolución, Obsidian.
- ✅ Controles de sistema nativos: volumen → pactl, ventanas → hyprctl,
  notificaciones → notify-send, wifi/bluetooth → nmcli/rfkill, brillo →
  brightnessctl, captura → grim.
- ✅ Terminal libre bash persistente + `sudo` on-demand con diálogo gráfico
  (`core/shell_session.py`; la password nunca se loguea).
- ✅ GUI-automation X11 (pyautogui) degradado en Wayland sin crashear.

> Guía completa en `README_LINUX.md`.

---

## 11. Lanzamiento

Instalación one-liner (instala en `~/.eris/ERIS-NEW`, crea venv, deja `eris`):

```bash
# Linux
curl -fsSL https://raw.githubusercontent.com/DaniellRG/ERIS-NEW/main/install.sh | bash
```

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/DaniellRG/ERIS-NEW/main/install.ps1 | iex"
```

Desarrollo manual:
```bash
# Linux
./run_linux.sh          # o: ./.venv-linux/bin/python main.py
# Windows
D:\Eris_Source\.venv\Scripts\pythonw.exe main.py
```

CLI: `eris` (o `python eris_cli.py`). Tests: `python test_all.py`.

---

## 12. Tests y estado actual

En esta máquina (Linux): **56 PASS, 1 FAIL, 3 WARN**.

- El FAIL es `eris.bat` (launcher de **Windows**) — esperado en Linux; en la PC
  Windows debe dar 57 PASS / 0 FAIL.
- WARN ambientales: neuro nodos < 80, chromadb no instalado, `ctypes.windll`.
- Estado del repo: **477 tools sincronizadas (459=459, 0 duplicados)**, 12
  agentes, 85 declaraciones Live, 0 imports rotos (590 `.py` compilan).

---

## 13. Trabajo en paralelo (2 máquinas)

```
PC 1 (Windows)                        PC 2 (CachyOS/Linux)
    git push  ───────────────────────►   git pull
    git pull  ◄───────────────────────   git push
```

- **Un solo repo** (`https://github.com/DaniellRG/ERIS-NEW`), un fork local por
  máquina, `main` compartido.
- **Nunca editar lo mismo en ambas a la vez** (git avisará conflictos).
- `config/api_keys.json` y el vault de Obsidian **NO viajan en git** — copiarlos
  aparte e igualarlos en ambas máquinas.

---

## 14. Requisitos

- **Python 3.14** (Windows) / 3.12+ (Linux)
- **PyQt6** + webengine
- **Ollama** (opcional, cerebro local) + un modelo (ej. `qwen3:8b` o `llama3.2`)
- **API keys** (Gemini obligatoria para modo nube) en `config/api_keys.json`
- **Linux**: `portaudio pipewire-pulse` y paquetes del sistema (ver AGENTS.md)

---

## 15. Repositorio remoto

```text
origin  https://github.com/DaniellRG/ERIS-NEW  (rama main)
```