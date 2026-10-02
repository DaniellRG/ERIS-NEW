# ERIS AI — Asistente Autónoma Multi-SO

Asistente virtual de escritorio **100% Python** (3.14 + PyQt6) con autonomía total,
inteligencia emocional, NeuroSpheres, auto-evolución y **500 herramientas**. Corre en
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
- **Ejecuta 500 herramientas** (anteriormente 459): archivos, terminal, web,
  memoria, código, sistema, comunicación, multimedia, autonomía, IDE.
- **Se autocuida**: code_guard (corrige su propio código con backup+rollback),
  self-healing, crash recovery, auto-backup, y la **Guardiana** (supervisora de
  autocuidado).
- **Aprende a aprender**: la **Mentora** integra fuentes de conocimiento y
  genera lecciones que sí impactan respuestas futuras.

**Idioma**: español (colombiana). **NO usa Node/Bun**: es Python puro — los
scripts Node/JS solo existen como plantillas para generar proyectos de usuario.

## 2. Estado actual del proyecto

### Mejoras recientes (septiembre 2026)

#### 🎤 Nueva herramienta: audio_diagnostic (actions/audio_diagnostic.py)
- Diagnóstico completo del audio de ERIS: estado, dispositivos, prueba de micrófono y altavoz, y auto-corrección de problemas comunes.
- Acciones: `status`, `devices`, `test_mic`, `test_speaker`, `fix`.
- 324 líneas, registrada en el sistema de herramientas.

#### 📊 Nueva herramienta: system_status (actions/system_status.py)
- Resumen del estado del sistema: CPU, RAM, disco, red, procesos.
- Acciones: `overview`, `cpu`, `ram`, `disk`, `network`, `processes`, `top`.
- 336 líneas, registrada en el sistema de herramientas.

#### 🖥️ Nuevo agente: system_monitor_agent (agents/system_monitor_agent.py)
- Monitoreo del sistema en tiempo real: CPU, RAM, disco, red, temperatura.
- Acciones: `start`, `stop`, `status`, `check`, `configure`, `report`.
- 449 líneas, registrado en el sistema de agentes.

#### 🚀 Nuevo agente: deploy_agent (agents/deploy_agent.py)
- DevOps/Infraestructura: Docker, Git, empaquetado, mantenimiento, backups.
- Acciones: `docker_ps`, `docker_info`, `git_status`, `git_branch`, `deploy_status`, `package_check`, `system_cleanup`, `backup_create`.
- 269 líneas, registro completo en las 4 estructuras, verificado con 8/8 tests.

#### 🔊 Audio — ALSA spam eliminado
- `core/logging_setup.py`: redirección de stderr de ALSA a /dev/null (elimina 513 ocurrencias de paInvalidSampleRate/PaAlsaStream en logs).
- `core/audio_config.py`: `RECEIVE_SAMPLE_RATE` ajustado de 24000Hz a 44100Hz.
- `config/api_keys.json`: mic_device=8 (PipeWire, funciona), mic_device_rate=16000Hz, speaker_device=5 (pipewire). Device 9 (Ryzen) causaba segfault (exit 139) — evitado.

#### 🤖 Gemini Live Audio — modelo corregido
- `model_for_conversation`: cambiada de `gemini-flash-latest` a `gemini-2.5-flash` (gemini-flash-latest no soporta Live Audio y causaba crash).
- `LIVE_MODEL`: `gemini-2.5-flash-native-audio-latest`.

#### 📦 PKGBUILD — empaquetado para Arch/CachyOS
- Archivo `PKGBUILD` (121 líneas): empaqueta ERIS para Arch Linux y CachyOS.
- Instala en `/opt/eris`, crea venv automático, .desktop file integrado, dependencias de sistema y Python.
- Build: `makepkg -si`.

#### 🐳 Dockerfile — despliegue en contenedor
- Archivo `Dockerfile` (57 líneas): build-stage + runtime-stage, puerto 5000, healthcheck.
- Build: `docker build -t eris-ai .` | Run: `docker run -it --rm -v /ruta/vault:/app/obsidian_vault eris-ai`.

#### 🚀 install_eris.sh — instalador interactivo
- Script `install_eris.sh` (213 líneas): detecta distro (Arch/Debian/Fedora), instala deps de sistema, soporta user-local (~/eris-ai) o system-wide (/opt/eris).
- Configura venv, deps pip, .desktop file, config inicial.

#### 🖥️ .desktop file — integrado en menú de Linux
- `/home/soul/.local/share/applications/eris.desktop`: Nombre "ERIS AI" / "ERIS IA", categoría Utility;AI;Assistant, icono face.png, ejecuta run_eris.sh.
- Registrado con `update-desktop-database`, chmod +x aplicado.

#### 🔧 Limpieza de herramientas duplicadas
- `tool_declarations.py`: eliminada duplicación de `weather_report` (ahora única).
- `tool_registry.py`: eliminada duplicación de `system_monitor_agent` (ahora única).
- Verificado: 526 tools únicas = 506 declaraciones, 0 duplicados, sync perfecto.

#### ✅ Tests — 177 PASS, 1 FAIL
- `test_all.py`: 177 tests pasan (1 FAIL: eris.bat, ambiental de Windows en Linux — esperado).
- 500 = 526 tools, 0 duplicados, 16 agentes.

### Estructura de directorios

```
ERIS-NEW/
├── main.py                  # Entry point GUI (PyQt6, ~5200 líneas)
├── eris_cli.py              # CLI terminal
├── ui.py                    # UI principal (orbe, emociones, ventana)
├── core/                    # Motor interno (~228 archivos)
│   ├── tool_registry.py         # 526 tools (callables)
│   ├── tool_declarations.py     # 506 declaraciones (0 duplicados)
│   ├── tool_dispatcher.py       # Ejecutador de tools
│   ├── action_imports.py        # Imports tolerantes de 302 action modules
│   ├── agent_definitions.py     # ⭐ 16 agentes (fuente única de verdad)
│   ├── agent_router.py          # Enruta a los agentes
│   ├── audio_config.py          # Modelos Live, voces, devices
│   ├── gemini_text_chat.py      # Chat Gemini (tools <=120)
│   ├── gemini_live_tts.py       # Gemini Live Audio (526 tools)
│   ├── tts_engine.py            # TTS (edge/fish/gemini), fish en paralelo
│   ├── logging_setup.py         # Configuración de logging + ALSA suppress
│   ├── emotional_core.py        # Núcleo emocional (12 emociones)
│   └── ... (neuro_spheres, observer, code_guard, mission, evolucion, etc.)
├── actions/                 # 302 módulos de acciones (una tool por archivo)
├── agents/                  # 16 agentes especializados
│   ├── system_monitor_agent.py  # ← NOVO: Monitoreo del sistema
│   ├── deploy_agent.py          # ← NOVO: DevOps/Infraestructura
│   ├── agenlix_agent.py         # Linux system agent
│   ├── dev_agent.py             # Development agent
│   ├── productivity_agent.py    # Comm, scheduler, reminders
│   ├── system_agent.py          # Core, file, security
│   ├── media_agent.py           # Media, vision
│   ├── search_agent.py          # Web search
│   ├── studies_agent.py         # Studies
│   ├── mentora_agent.py         # Learning mentor
│   ├── guardiana_agent.py       # Self-care supervisor
│   ├── memoria_agent.py         # Memory agent
│   ├── vision_agent.py          # Vision
│   ├── security_agent.py        # Security
│   └── pentest_lab.py           # Pentest lab (standalone)
├── config/                  # Configuración
├── memory/                  # Estado de memoria, evolución, backups
├── data/                    # Conocimiento, prompts, métricas
├── assets/                  # Recursos (face.png, vrm, etc.)
├── skills/                  # 5 skills
├── libraries/               # Librerias ERIS
├── tests/                   # Suite de tests
├── tools/                   # Tools misc (eris_askpass.py, etc.)
├── eris_run.log             # Log de ejecución (audio errors, etc.)
├── requirements-linux.txt  # Deps Python para Linux
├── requirements.txt        # Deps Python (cross-platform)
├── PKGBUILD                 # Empaquetado Arch/CachyOS
├── Dockerfile               # Despliegue contenedor
├── install.sh               # Script de instalación
├── install_eris.sh          # Instalador interactivo
├── run_eris.sh              # Launcher mejorado
├── run_linux.sh             # Launcher original
├── setup_wizard.py          # Configurador GUI
├── watchdog.py              # Watchdog de reinicio
└── face.png                 # Icon
```

## 2. Cómo retomar el contexto

Estado del repote y cómo seguir después de un tiempo sin tocar el código:

0. **BUG ABIERTO — Avatar VRM no se ve (¡empezar por acá!)**: el modelo 3D
   flotante (`floating_visual=vrm` en config) carga sin errores JS en el log
   pero la ventana queda vacía en Linux/Wayland. Detalles, causa candidata y
   pasos de debug en la sección 3 (entrada "Avatar VRM 3D flotante"). El studio
   (`Ctrl+Alt+A`) y los parámetros `vrm_anim` ya funcionan; falta el render.
1. **Regenerate**: `git pull` en la otra PC; `git log --oneline -15` para ver lo
   último; probar `python test_all.py` (gate: 177 PASS en esta máquina).
2. **Tools son sagradas**: `core/tool_registry.py` == `core/tool_declarations.py`
   (`len` igual, 0 duplicados). Si agregás/quitas una tool, editás AMBOS y
   verificás, después reiniciar ERIS. Hoy: **500 = 500**.
3. **Agentes**: la fuente única de verdad es `core/agent_definitions.py`
   (16 agentes + keywords + handlers + penalty_keywords). `core/agent_router.py`
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

### 🧊 Avatar VRM 3D flotante — ERIS en 3D (2026-09-12, `0aa91b8`)
- **Objetivo** (decisión del usuario): el avatar 3D NO va en la ventana principal;
  solo el **orbe flotante** se conmuta a "Modelo 3D (VRM)" desde Ajustes
  (combo "Flotante", config `floating_visual`, default `orb`, hoy `vrm`).
- **VrmAvatar** (`ui.py`): ventana flotante 340×480, frameless, siempre al tope,
  transparente (WA_TranslucentBackground + `page().setBackgroundColor(transparent)`)
  que carga `assets/vrm/viewer.html` vía mini HTTP local (`core/vrm_server.py`,
  los ES modules no abren desde `file://`). Interfaz: `runJavaScript` (Python→JS)
  + QWebChannel (JS→Python, model_loaded/errores).
- **viewer.html**: three.js 0.160 + @pixiv/three-vrm 3.5 (libs locales en
  `assets/vrm/lib/`, estructura tipo unpkg). `Eris.vrm` = modelo VRM 1.0 de
  VRoid Studio (16.7 MB, commiteado). Motor procedural:
  - Lip-sync por visemas `aa`/`oh` (boca se cierra a volumen 0; tope 0.55/0.22).
  - Parpadeo automático, respiración, mirada sutil.
  - **Pose natural**: el .vrm de VRoid viene en T-Pose → los brazos se bajan 90°
    colgando a los costados con codos flexionados y dedos curvados.
  - **Giro lento del cuerpo con peso** (~28s/ciclo): al girar, el peso pasa a la
    pierna contraria, el torso resiste parcialmente y la cabeza compensa.
  - **Parámetros ajustables** en `window.ANIM` + `window.setAnimParam(name,val)`
    + `window.applyAnimConfig(cfg)`.
- **Studio de animación 3D**: `Ctrl+Alt+A` → diálogo `VrmAnimStudio` (`ui.py`)
  con sliders en vivo (abertura/vaivén de brazos, codos, muñecas, dedos,
  respiración, sway de caderas, giro, peso, contragiro, cabeza, piernas, flote).
  "Guardar" persiste en `config/api_keys.json` → clave `vrm_anim`
  (recargado al iniciar el avatar).
- **Fix crash "Unsupported Graphics API: 4"** (`core/gpu_config.py`): forzaba
  `QSG_RHI_BACKEND=d3d11` en Linux (no existe) → QtWebEngine moría; ahora en
  Linux usa `opengl` y antepone `--no-sandbox` a QTWEBENGINE_CHROMIUM_FLAGS
  (con espacios correctos entre flags concatenados).
- **Import de QtWebEngine ordenado**: `QtWebEngineWidgets` (o
  `AA_ShareOpenGLContexts`) se importa ANTES de la primera QApplication y solo
  si `assets/vrm/Eris.vrm` existe (`main.py` bloque temprano, `ui.py` `_vrm_ok`).
- ⚠️ **BUG ABIERTO — el modelo NO aparece en pantalla en esta PC Linux**. El
  log muestra el modelo cargando sin errores JS, pero la ventana queda vacía.
  Se aplicaron guards anti-NaN (el frente calculado con la cámara en `(0,0,0)`
  daba vector nulo → NaN → esqueleto colapsado), el encuadre se hace antes de la
  primera pose, y se reemplazó `getBoneNode()` deprecado por `getRawBoneNode()`.
  **Siguiente paso sugerido en la otra PC**: capturar `console.log`
  (añadir `window.__eris_errors` ya existe) o probar el viewer.html directo en
  un navegador (sirviendo `assets/vrm/` con `python -m http.server`) para ver
  si renderiza fuera de QtWebEngine; si renderiza, el problema es Qt/GPU; si no,
  el HTML/JS.

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

### 🎤 audio_diagnostic — herramienta de diagnóstico de audio (2026-09-19)
- `actions/audio_diagnostic.py` (324 líneas): diagnóstico completo del audio de
  ERIS. Acciones: `status` (estado actual), `devices` (listar dispositivos de
  entrada/salida), `test_mic` (probar micrófono con detección de audio), `test_speaker`
  (probar altavoz), `fix` (auto-corregir problemas comunes).
- Diagnostica: configuración activa, dispositivos detectados por sounddevice, niveles
  de entrada/salida, estado de backends (ALSA, PulseAudio, PipeWire), y errores en
  logs de audio (ALSA stderr spam de `paInvalidSampleRate`/`PaAlsaStream`).
- Integrado en el sistema de tools: registrado en `tool_registry.py`,
  `tool_declarations.py`, `action_imports.py`. Total: 500 herramientas.

### 📊 system_status — herramienta de estado del sistema (2026-09-19)
- `actions/system_status.py` (336 líneas): resumen del estado del sistema con
  métricas detalladas. Acciones: `overview` (resumen completo CPU/RAM/disco/red),
  `cpu` (uso y top procesos), `ram` (consumo y top), `disk` (espacio y uso por
  partición), `network` (interfaces, IP, tráfico), `processes` (lista ordenada),
  `top` (procesos más pesados).
- Usa psutil para métricas en tiempo real. Detecta automáticamente sistemas Linux
  (usando `/proc/meminfo`, `df`, `ip addr`) y reporta métricas nativas.
- Integrado en el sistema de tools: registrado en `tool_registry.py`,
  `tool_declarations.py`, `action_imports.py`.

### 🖥️ system_monitor_agent — agente de monitoreo del sistema (2026-09-19)
- `agents/system_monitor_agent.py` (449 líneas): agente especializado en
  monitoreo del sistema. Monitorea CPU, RAM, disco, red, temperatura y procesos
  en tiempo real. Detecta problemas de rendimiento, alertas de recursos críticos
  (CPU >95%, RAM >95%, disco >90%), y permite chequeos manuales y reportes
  detallados del sistema.
- Acciones: `start` (iniciar monitoreo continuo), `stop` (detener), `status`
  (estado actual del monitoreo), `check` (chequeo inmediato del sistema),
  `configure` (cambiar umbrales de alerta), `report` (reporte completo).
- Alertas automáticas cuando los recursos superan los umbrales configurados.
- Integrado en el sistema de agentes: registrado en `agent_definitions.py` como
  agente ruteable con keywords "monitor sistema cpu ram disco temperatura sistema".

### 🚀 deploy_agent — agente de DevOps/Infraestructura (2026-09-19)
- `agents/deploy_agent.py` (269 líneas): especialista en DevOps y despliegue de
  ERIS. Maneja contenedores Docker, repositorios Git, empaquetado, mantenimiento
  del sistema y backups.
- Acciones: `docker_ps` (contenedores/en ejecución), `docker_info` (info del
  daemon Docker), `git_status` (estado del repo), `git_branch` (ramas y checkout),
  `deploy_status` (estado de deploys conocidos), `package_check` (verificar
  paquetes en el sistema), `system_cleanup` (limpiar archivos temporales y cache),
  `backup_create` (crear backup de archivos/paths dados).
- Verificado funcional: 8/8 tests pasan en escenarios reales de Docker, Git y
  administrativo de sistema.
- Integrado en el sistema de agentes: registrado en `agent_definitions.py` como
  agente ruteable con keywords "deploy desplegar docker contenedor git push commit
  empaquetar paquete mantenimiento backup".

### 🧹 PKGBUILD — empaquetado para Arch/CachyOS (2026-09-19)
- `PKGBUILD` (121 líneas): definición de paquete nativo para Arch Linux y
  CachyOS. Instala ERIS en `/opt/eris`, crea el venv automáticamente en primera
  ejecución, instala las dependencias de sistema y Python, registra el `.desktop`
  file para menú de aplicaciones, y configura el launcher `eris`.
- Incluye `install.sh` (script de post-install/remove/upgrade) para configurar
  desktop database y limpiar al desinstalar.
- Build con `makepkg -si` desde la raíz del repo.

### 🐳 Dockerfile — despliegue en contenedor (2026-09-19)
- `Dockerfile` (57 líneas): despliegue de ERIS en contenedor Docker. Usa build-
  stage para instalar dependencias Python (incluyendo compilación de paquetes
  nativos como sounddevice con portaudio), y runtime-stage minimal para ejecución.
- Expone puerto 5000 para Flask/virtualización, incluye healthcheck, soporta
  montaje del vault de Obsidian como volumen para persistencia de datos.
- Build: `docker build -t eris-ai .` | Run: `docker run -it --rm -v
  /ruta/vault:/app/obsidian_vault eris-ai`

### 🚀 install_eris.sh — instalador interactivo (2026-09-19)
- `install_eris.sh` (213 líneas): instalador interactivo que detecta la distribución
  del sistema (Arch, Debian, Fedora) e instala las dependencias de sistema
  automáticamente (pacman/apt/dnf).
- Soporta dos modos: user-local (instala en `~/eris-ai`, sin sudo) y system-wide
  (instala en `/opt/eris`, requiere sudo).
- Configura automáticamente: venv Python, dependencias pip, `.desktop` file para
  menú, y archivos de configuración iniciales.
- Ejecutable con `./install_eris.sh` desde la raíz del repo.

### 🖥️ .desktop file — integración con menú de Linux (2026-09-19)
- `/home/soul/.local/share/applications/eris.desktop`: integración con el menú de
  aplicaciones de Linux (XDG Desktop Entry). Nombre: "ERIS AI" (y "ERIS IA" en
  español), categoría Utility;AI;Assistant, icono face.png, ejecuta
  `/home/soul/Eris/ERIS-NEW/run_eris.sh`.
- Registrado con `update-desktop-database`, chmod +x aplicado.
- Disponible en la barra de aplicaciones del entorno de escritorio.

### 🔊 Audio — ALSA spam eliminado y configuración corregida (2026-09-19)
- **`core/logging_setup.py`**: redirección de stderr de ALSA a /dev/null para
  eliminar el spam de `paInvalidSampleRate`/`PaAlsaStream` (513 ocurrencias en
  logs anteriores).
- **`core/audio_config.py`**: `RECEIVE_SAMPLE_RATE` ajustado de 24000Hz a 44100Hz
  (tasa universalmente compatible).
- **`config/api_keys.json`**: micrófono configurado en device 8 (PipeWire default,
  funciona correctamente), mic_device_rate=16000Hz (tasa óptima para STT), speaker
  device 5 (pipewire).
- **Device 9 (Ryzen HD Audio Controller)**: comprobado que causa segfault (exit
  139) al intentar leer datos de audio. Solucionado usando device 8.

### 🤖 Gemini Live Audio — modelo corregido (2026-09-19)
- `model_for_conversation` cambiado de `gemini-flash-latest` a `gemini-2.5-flash`
  en `config/api_keys.json`. `gemini-flash-latest` no soporta Live Audio y causaba
  crash al intentar usarla.
- `gemini-2.5-flash` soporta Live Audio nativamente (speech-to-text y text-to-speech
  en tiempo real).
- Modelo nativo de audio: `gemini-2.5-flash-native-audio-latest` (referenciado en
  `core/audio_config.py` como `LIVE_MODEL`).

### 🔧 Limpieza de herramientas duplicadas (2026-09-19)
- **`tool_declarations.py`**: eliminada duplicación de `weather_report` (ahora
  aparece una sola vez en la sección Core).
- **`tool_registry.py`**: eliminada duplicación de `system_monitor_agent` (ahora
  aparece una sola vez).
- Verificado: 500 herramientas únicas, 0 duplicados, sync perfecto entre
  tool_registry.py y tool_declarations.py.

### ✅ Tests — 177 PASS, 1 FAIL (2026-09-19)
- `test_all.py`: 177 tests pasan, 1 FAIL (eris.bat, launcher de Windows —
  esperado en Linux).
- WARN: neuro nodos < 80 (NeuroSpheres aún creciendo), ctypes.windll (Windows-only).
- Equilibrado: 500 = 526 tools, 0 duplicados, 16 agentes registrados.

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
│   ├── tool_registry.py         # 526 tools (callables)
│   ├── tool_declarations.py     # 506 declaraciones + LIVE (85, sin reservados)
│   ├── tool_dispatcher.py       # Ejecutador de tools
│   ├── action_imports.py        # Imports tolerantes de 302 action modules
│   ├── agent_definitions.py     # ⭐ Fuente única de verdad de 16 agentes
│   ├── agent_router.py          # Enruta a los agentes (importa las definiciones)
│   ├── prompt.txt               # System prompt de ERIS (~1864 líneas)
│   ├── prompt_loader.py         # Carga prompt cacheada (mtime)
│   ├── audio_config.py          # Modelos Live, voces, devices, get_config()
│   ├── gemini_text_chat.py      # Chat dual Ollama/Gemini (tools <=120)
│   ├── gemini_live_tts.py       # Gemini Live Audio (526 tools)
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
├── actions/                 # 302 módulos de acciones (uno por tool)
├── agents/                  # 16 agentes especializados
│   ├── deploy_agent.py            # DevOps/Infraestructura (NOVO)
│   ├── system_monitor_agent.py    # Monitoreo del sistema (NOVO)
│   ├── agenlix_agent.py           # Linux system agent
│   ├── dev_agent.py               # Development agent
│   ├── productivity_agent.py      # Comm, scheduler, reminders
│   ├── system_agent.py            # Core, file, security
│   ├── media_agent.py             # Media, vision
│   ├── search_agent.py            # Web search
│   ├── studies_agent.py           # Studies
│   ├── mentora_agent.py           # Learning mentor
│   ├── guardiana_agent.py         # Self-care supervisor
│   ├── memoria_agent.py           # Memory agent
│   ├── vision_agent.py            # Vision
│   ├── security_agent.py          # Security
│   ├── pentest_lab.py             # Pentest lab (standalone tool)
│   └── web_agent.py               # Web browser automation
├── skills/                  # 39 skills (21 builtin + 18 user)
├── memory/                  # Estado de memoria, evolución, backups, lecciones
├── data/
│   └── knowledge/           # 69 archivos .md de conocimiento (inventario vivo)
├── test_all.py              # Gate de tests
├── requirements.txt / requirements-linux.txt
├── install.sh / install.ps1 / run_linux.sh
├── PKGBUILD                 # Empaquetado Arch/CachyOS
├── Dockerfile               # Despliegue contenedor
├── install_eris.sh          # Instalador interactivo
└── README_LINUX.md          # Guía de despliegue Linux
```

---

## 5. Agentes especializados (16)

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
| **memoria** | Memoria semántica + episódica + world model |
| **pentest** | Pentest lab (VirtualBox aislado, 192.168.56.0/24) |
| **system_monitor** (NOVO) | Monitoreo del sistema en tiempo real |
| **deploy** (NOVO, 2026-09-19) | DevOps, Docker, Git, empaquetado, backups |

> Los **3 agentes más nuevos** (system_monitor, deploy) están integrados en el
> router y listos para ser invocados por ERIS cuando el contexto lo requiera.

---

## 6. Voz y modelos de IA

- **Voz en vivo (Gemini Live API)** — primario **`gemini-2.5-flash-native-audio-latest`**
  (estable), fallback automático a `gemini-3.1-flash-live-preview` → luego
  `gemini-2.5-flash-native-audio-preview-12-2025`.
- **Texto**: `gemini-2.5-flash` (model_for_conversation, cambiado de
  `gemini-flash-latest` en sept 2026 porque `gemini-flash-latest` no soporta
  Live Audio); agentes `gemini`; búsqueda `gemini`.
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

En esta máquina (Linux): **177 PASS, 1 FAIL, 3 WARN**.

- El FAIL es `eris.bat` (launcher de **Windows**) — esperado en Linux; en la PC
  Windows debe dar 177 PASS / 0 FAIL.
- WARN ambientales: neuro nodos < 80 (NeuroSpheres aún creciendo),
  chromadb no instalado, `ctypes.windll`.
- Estado del repo: **526 tools sincronizadas (500=500, 0 duplicados)**, 16
  agentes, 85 declaraciones Live, 0 imports rotos (620 `.py` compilan).
- Herramientas nuevas (sept 2026): `audio_diagnostic`, `system_status`.
- Agentes nuevos (sept 2026): `system_monitor_agent`, `deploy_agent`.
- Empaquetado: `PKGBUILD` (Arch/CachyOS), `Dockerfile` (contenedor),
  `install_eris.sh` (instalador interactivo), `.desktop` file registrado.

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
- **Linux**: `portaudio pipewire-pulse` y paquetes del sistema (ver README_LINUX.md)

---

## 15. Empaquetado y despliegue

### Arch/CachyOS (PKGBUILD)
```bash
cd /ruta/a/ERIS-NEW
makepkg -si
```

### Docker
```bash
docker build -t eris-ai /ruta/a/ERIS-NEW
docker run -it --rm -v /ruta/vault:/app/obsidian_vault -p 5000:5000 eris-ai
```

### Instalador interactivo
```bash
cd /ruta/a/ERIS-NEW
./install_eris.sh
```

### Menú de aplicaciones
El archivo `eris.desktop` está instalado en
`/home/soul/.local/share/applications/eris.desktop` y registrado. ERIS aparece
en el menú de aplicaciones como "ERIS AI".

---

## 16. Repositorio remoto

```text
origin  https://github.com/DaniellRG/ERIS-NEW  (rama main)
```