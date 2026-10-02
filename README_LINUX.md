# ERIS en LINUX (CachyOS/Arch) — Guía de despliegue dual

ERIS es **multiplataforma**: el mismo código corre en Windows y Linux. Este
documento explica cómo levantar ERIS en tu laptop con **CachyOS** y cómo
trabajar en paralelo entre tus dos máquinas.

> El código ya está blindado para importar completo en Linux sin los paquetes
> Windows-only (pycaw, comtypes, win10toast, pywinauto, pygetwindow). Esas
> acciones se desactivan automáticamente (quedan como `None`) y las 500 tools
> multiplataforma siguen funcionando.

---

## Estado actual del proyecto (septiembre 2026)

### Lo que funciona

| Componente | Estado |
|---|---|
| Chat por texto (Gemini/Ollama) | ✅ Funciona |
| Voz en vivo (Gemini Live Audio) | ✅ Configurado — gemini-2.5-flash-native-audio-latest |
| TTS local (Kokoro-82M) | ✅ Disponible en venv |
| Reconocimiento de voz (Vosk) | ✅ Funciona (portaudio) |
| UI PyQt6 (orbe, emociones, ventana) | ✅ Funciona |
| Memoria, emociones, NeuroSpheres, evolución | ✅ Funciona |
| Vault Obsidian (evolución, neurospheres) | ✅ Funciona |
| 500 herramientas registradas | ✅ 500 = 500, 0 duplicados |
| 16 agentes especializados | ✅ Registrados y ruteables |
| `.desktop` file (menú Linux) | ✅ Creado y registrado |
| Audio (micrófono + altavoz PipeWire) | ✅ Device 8 (default/PipeWire), 16000Hz entrada / 44100Hz salida |
| ALSA stderr spam | ✅ Suprimido (logging_setup.py) |

### Mejoras recientes (septiembre 2026)

#### Audio — ALSA spam eliminado (sesión 2026-09-18/19)
- **`core/logging_setup.py`**: redirección de stderr de ALSA a /dev/null para eliminar el spam de `paInvalidSampleRate`/`PaAlsaStream` (513 ocurrencias en logs anteriores)
- **`core/audio_config.py`**: `RECEIVE_SAMPLE_RATE` ajustado de 24000Hz a 44100Hz (compatible universal)
- **`config/api_keys.json`**: micrófono configurado en device 8 (PipeWire default, funciona), mic_device_rate=16000Hz, speaker=device 5 (pipewire)
- **Device 9 (Ryzen HD Audio Controller)**: segfault comprobado (exit 139 al leer) — evitado usando device 8

#### Gemini Live Audio — modelo corregido
- Modelo cambiado de `gemini-flash-latest` (sin soporte Live Audio) a `gemini-2.5-flash`
- `model_for_conversation`: `gemini-2.5-flash`
- `LIVE_MODEL`: `gemini-2.5-flash-native-audio-latest`

#### Nueva herramienta: `audio_diagnostic` (actions/audio_diagnostic.py, 324 líneas)
- Acciones: `status`, `devices`, `test_mic`, `test_speaker`, `fix`
- Diagnostica estado de audio, lista dispositivos, prueba mic/altavoz, auto-corregir problemas comunes

#### Nueva herramienta: `system_status` (actions/system_status.py, 336 líneas)
- Acciones: `overview`, `cpu`, `ram`, `disk`, `network`, `processes`, `top`
- Resumen del estado del sistema con métricas detalladas

#### Nuevo agente: `system_monitor_agent` (agents/system_monitor_agent.py, 449 líneas)
- Monitoreo continuo del sistema: CPU, RAM, disco, red, temperatura
- Acciones: `start`, `stop`, `status`, `check`, `configure`, `report`
- Registrado como agente ruteable en el sistema

#### Nuevo agente: `deploy_agent` (agents/deploy_agent.py, 269 líneas)
- DevOps/Infraestructura: docker (ps, images, logs, build, stop), git (status, log, commit, push, pull, branch), empaquetado (pacman, pip, requirements), limpieza, backups
- Acciones: `docker_ps`, `docker_info`, `git_status`, `git_branch`, `deploy_status`, `package_check`, `system_cleanup`, `backup_create`
- Verificado: 8/8 tests pasan

#### Empaquetado y despliegue
- **`PKGBUILD`** (121 líneas): empaquetado para Arch/CachyOS — instala en `/opt/eris`, crea venv automático, integra `.desktop`, maneja dependencias tanto de sistema como de Python
- **`Dockerfile`** (57 líneas): despliegue en contenedor con build-stage + runtime-stage, exposición de puerto 5000, healthcheck
- **`install.sh`** (36 líneas): script de instalación del paquete (post_install, post_remove, post_upgrade)
- **`install_eris.sh`** (213 líneas): instalador interactivo que detecta distro (Arch/Debian/Fedora), soporta instalación user-local (~/eris-ai) o system-wide (/opt/eris), configura .desktop, crea venv e instala deps
- **`.desktop` file**: `/home/soul/.local/share/applications/eris.desktop` — registrado con `update-desktop-database`

### Estructura de directorios

El proyecto tiene **una sola carpeta de código fuente activa**: `ERIS-NEW/`. El resto son artefactos secundarios:

```
/home/soul/Eris/
├── ERIS-NEW/              ← CÓDIGO FUENTE PRINCIPAL (aquí trabaja ERIS)
│   ├── main.py            # Entry point GUI (PyQt6, ~5200 líneas)
│   ├── eris_cli.py        # CLI terminal
│   ├── ui.py              # UI principal PyQt6 (~3895 líneas)
│   ├── core/              # Motor interno (228 archivos)
│   │   ├── tool_registry.py        # 500 tools (callables)
│   │   ├── tool_declarations.py    # 500 declaraciones (0 duplicados)
│   │   ├── tool_dispatcher.py      # Ejecutador de tools
│   │   ├── action_imports.py       # Imports de 302 action modules
│   │   ├── agent_definitions.py    # ⭐ 16 agentes (fuente única de verdad)
│   │   ├── agent_router.py         # Enruta intents a agentes
│   │   ├── audio_config.py         # Devices, sample rates, modelos Live
│   │   ├── gemini_text_chat.py     # Chat Gemini (tools <=120)
│   │   ├── gemini_live_tts.py      # Gemini Live Audio (85 tools)
│   │   ├── tts_engine.py           # TTS (edge/fish/gemini/kokoro)
│   │   ├── logging_setup.py        # Configuración de logging + ALSA suppress
│   │   ├── emotional_core.py       # Núcleo emocional (12 emociones)
│   │   └── ... (228 archivos total)
│   ├── actions/           # 306 módulos de acciones (una tool por archivo)
│   ├── agents/            # 16 agentes especializados
│   │   ├── deploy_agent.py         # ← NOVO: DevOps/Infraestructura
│   │   ├── system_monitor_agent.py # ← NOVO: Monitoreo del sistema
│   │   ├── agenlix_agent.py        # Linux system agent
│   │   ├── dev_agent.py            # Development agent
│   │   ├── productivity_agent.py   # Comm, scheduler, reminders
│   │   ├── system_agent.py         # Core, file, security
│   │   ├── media_agent.py          # Media, vision
│   │   ├── search_agent.py         # Web search
│   │   ├── studies_agent.py        # Studies
│   │   ├── mentora_agent.py        # Learning mentor
│   │   ├── guardiana_agent.py      # Self-care supervisor
│   │   ├── memoria_agent.py        # Memory agent
│   │   ├── vision_agent.py         # Vision
│   │   └── security_agent.py       # Security
│   ├── config/            # Configuración (api_keys.json, etc.)
│   ├── memory/            # Estado de memoria, evolución, backups
│   ├── data/              # Conocimiento, prompts, métricas
│   ├── assets/            # Recursos (face.png, vrm, etc.)
│   ├── skills/            # 5 skills
│   ├── libraries/         # Librerias ERIS (eris_evolution, eris_tools)
│   ├── tests/             # Suite de tests (177 PASS)
│   ├── tools/             # Tools misc (eris_askpass.py, etc.)
│   ├── eris_run.log       # Log de ejecución (audio errors, etc.)
│   ├── eris.log           # Log actual
│   ├── requirements-linux.txt  # Deps Python para Linux
│   ├── requirements.txt        # Deps Python (cross-platform)
│   ├── PKGBUILD           # ← NOVO: Empaquetado Arch/CachyOS
│   ├── Dockerfile         # ← NOVO: Despliegue contenedor
│   ├── install.sh         # ← NOVO: Script de instalación del paquete
│   ├── install_eris.sh    # ← NOVO: Instalador interactivo
│   ├── run_eris.sh        # Launcher mejorado (venv + env)
│   ├── run_linux.sh       # Launcher original Linux
│   ├── eris               # Bash launcher (legacy)
│   ├── setup_wizard.py    # Configurador GUI de primera ejecución
│   ├── watchdog.py        # Watchdog de reinicio
│   └── face.png           # Icon del .desktop
│
├── Eris_NEW/              ← VAULT DE OBSIDIAN (memoria persistente, NO viaja en git)
│   └── BaseDatosObsidian/ # Segundo cerebro de ERIS
│
├── BACKUPS/               ← Backups automáticos de ERIS
│   └── eris_20260909_101504/
│
├── Desktop/               ← Archivos generados por ERIS (documentos, canciones, etc.)
├── Documents/             ← Documentos del usuario
├── ERIS/                  ← ?? (carpeta vacía, revisar uso)
├── eris_workspace/        ← Contexto del IDE assistant (NO es código de ERIS)
├── src_clean/             ← Copia limpia experimental (revisar si se usa)
├── vault/                 ← ?? (1 archivo, revisar uso)
├── android_eris/          ← Proyecto Android (en depuración)
├── mobile/                ← Móvil (3 archivos, revisar)
├── plugins/               ← Plugins (3 archivos)
├── web_project/           ← Proyecto web (1 archivo)
├── face_designs/          ← Diseños de cara (6 archivos)
├── face_sounds/           ← Sons de cara (9 archivos)
├── bios/                  ← BIOS (5 archivos)
├── snapshots/             ← Snapshots (1 archivo)
├── skills/                ← Skills adicionales (5 archivos)
├── agents/                ← ?? (carpeta en raíz, NO ES la misma que ERIS-NEW/agents/)
├── action/                ← ?? (carpeta en raíz, revisar)
├── actions/               ← ?? (carpeta en raíz, revisar — NO ES la misma que ERIS-NEW/actions/)
├── core/                  ← ?? (carpeta en raíz, revisar — NO ES la misma que ERIS-NEW/core/)
├── data/                  ← ?? (carpeta en raíz, revisar)
├── memory/                ← ?? (carpeta en raíz, revisar)
├── tools/                 ← ?? (carpeta en raíz, revisar)
├── config/                ← ?? (carpeta en raíz, revisar)
├── libraries/             ← ?? (carpeta en raíz, revisar)
├── tests/                 ← ?? (carpeta en raíz, revisar)
├── voices/                ← Voz (carpeta vacía)
├── context/               ← Contexto (2 archivos)
├── backups/               ← Backups (4 archivos)
├── face_sounds/           ← Sons (carpeta vacía)
├── D:\Eris_Source\data\screenshots/  ← RUTA WINDOWS (gitignored, no usar en Linux)
├── Desktop/
├── Documents/
└── ...
```

**Advertencia**: Hay MÚLTIPLES carpetas con los mismos nombres en la raíz de `/home/soul/Eris/` además de las que están dentro de `ERIS-NEW/`. Ejemplos: `agents/`, `actions/`, `core/`, `config/`, `memory/`, `data/`, `tools/`, `config/`, `libraries/`, `tests/`. Estas carpetas en la raíz **no son el código fuente de ERIS** — el código fuente está exclusivamente en `ERIS-NEW/`. La presencia de estas carpetas duplicadas puede causar confusión; si no se usan, deberían eliminarse o renombrarse para evitar errores de ruta.

### Scripts de ejecución

| Script | Propósito | Estado |
|---|---|---|
| `run_linux.sh` | Launcher original: crea venv, instala deps, ejecuta main.py | ✅ Funciona |
| `run_eris.sh` | Launcher mejorado: venv + env + pip install fallback | ✅ Funciona (chmod +x) |
| `eris` | Bash launcher legacy | ⚠️ Revisar (puede estar roto) |
| `eris_cli.py` | CLI de terminal | ✅ Funciona |
| `setup_wizard.py` | Configurador GUI de primera ejecución | ✅ Funciona |
| `watchdog.py` | Reiniciador automático | ✅ Funciona |
| `install_eris.sh` | Instalador interactivo (detecta distro, user/system install) | ✅ Nuevo |
| `install.sh` | Script de post-install del paquete | ✅ Nuevo |
| `PKGBUILD` | Definición de paquete Arch/CachyOS | ✅ Nuevo |
| `Dockerfile` | Despliegue en contenedor | ✅ Nuevo |

---

## Instalación one-liner (recomendada)

```bash
curl -fsSL https://raw.githubusercontent.com/DaniellRG/ERIS-NEW/main/install.sh | bash
```

Instala ERIS en `~/.eris/ERIS-NEW` (NO toca tu workspace de desarrollo),
crea el venv, instala dependencias, deja el comando `eris` y abre la
**ventana de bienvenida** (ERIS en grande + formulario de API keys:

**REQUERIDAS** para poder chatear — la key de Gemini —, todo lo demás es
**OPCIONAL** y puede quedar vacío: ERIS igual arranca en pleno.

Comandos del launcher:

```bash
eris               # GUI (el primer uso abre el configurador)
eris --cli         # chat por terminal
eris --update      # trae la ultima version de GitHub (git pull + deps)
eris --check       # estado de las API keys
eris --wizard      # reabrir el configurador
```

> Por diseño, el one-liner **siempre instala el ultimo commit** de `main`, y
> `eris --update` te mantiene al dia. La config (`api_keys.json`), `data/`,
> `memory/` y el vault quedan **fuera de git**: nunca se pisan al actualizar.

---

## Requisitos de sistema (una vez)

```bash
sudo pacman -S python python-pip python-virtualenv portaudio pipewire-pulse git
```

Para el empaquetado nativo (opcional):

```bash
# Construir paquete Arch/CachyOS
makepkg -si

# O usar el instalador interactivo
./install_eris.sh
```

Para despliegue en contenedor (opcional):

```bash
docker build -t eris-ai .
docker run -it --rm -v /home/tu_usuario/Eris_NEW/BaseDatosObsidian/BaseObsiEris:/app/obsidian_vault eris-ai
```

---

## Despliegue (desarrollo)

```bash
cd Eris_Source          # clonado del repo (ver seccion git abajo)
./run_linux.sh          # crea .venv-linux, instala deps y lanza Eris
```

Para solo actualizar dependencias:

```bash
./run_linux.sh --update
```

> Si el repo está en otra ruta que no sea la misma de Windows, **no importa**:
> el código resuelve las rutas relativas desde `__file__` (portable). La única
> ruta externa configurable es el vault de Obsidian (variable de entorno).

## Vault de Obsidian (memoria persistente)

ERIS espera encontrar su segundo cerebro (Obsidian) en cualquiera de estas
ubicaciones, en ese orden:

1. Variable de entorno `ERIS_OBSIDIAN_VAULT` → `/home/USUARIO/Eris_NEW/BaseDatosObsidian/BaseObsiEris`
2. Carpeta hermana junto al repo: `../Eris_NEW/BaseDatosObsidian/BaseObsiEris`
3. `D:/Eris_NEW/BaseDatosObsidian/BaseObsiEris` (solo si existe en Windows)
4. Carpeta local `obsidian_vault/` dentro del repo (fallback)

Para la laptop Linux, lo más limpio es copiar tu vault actual a
`$HOME/Eris_NEW/...` y setear la variable (el script `run_linux.sh` ya lo hace
por defecto a `$HOME`). Con eso ERIS conserva toda su memoria y evolución.

## Claves de API

`config/api_keys.json` está **gitignored** (protegido por seguridad). Al clonar
en la laptop deberás copiarlo desde tu PC de escritorio (o desde el backup) a
`config/api_keys.json`, y ajustar:

- `\"os_system\": \"linux\"`
- `\"mic_device\"` / `\"speaker_device\"` → índices de tu audio en Linux (PipeWire)
- `\"chrome_exe_path\"` → normalmente vacío funciona (busca en PATH)

> ⚠️ Nunca subir `api_keys.json` al repo (ya está ignorado).

## Trabajo en paralelo (git)

El flujo recomendado es **un solo repo** (`DaniellRG/ERIS-NEW`), commit por
máquina:

- Cuando terminás en la PC de escritorio → `git add -A`, `git commit`, `git push`.
- Al cambiar a la laptop → `git pull`, trabajás, `git commit`, `git push`.
- Al volver al escritorio → `git pull`.

Así ambas máquinas quedan sincronizadas y nunca editás lo mismo a la vez
(si lo hacés, git avisará el conflicto y lo resolvés igual que siempre).

```
PC escritorio (Windows)         Laptop (CachyOS / Linux)
      |  git push                    |  git pull
      +---------------------------->+
      |  git pull                    |  git push
      +<----------------------------+
```

## Estado de portabilidad

| Componente | Estado en Linux |
|---|---|
| Chat por texto (Gemini/Ollama) | ✅ Funciona |
| Memoria, emociones, NeuroSpheres, evolución | ✅ Funciona |
| Vault Obsidian (`evolucion`, neurospheres) | ✅ Funciona |
| UI PyQt6 (orbe, ventana) | ✅ Funciona |
| TTS nube (edge-tts, gtts, Fish/Eleven) | ✅ Funciona |
| Reconocimiento de voz (Vosk) | ✅ Funciona (portaudio) |
| Control de volumen (pycaw → pactl/wpctl) | ✅ Funciona (PipeWire) |
| Control de ventanas (win32 → hyprctl, Hyprland/0.55+ Lua) | ✅ Funciona |
| Notificaciones (win10toast → notify-send) | ✅ Funciona (libnotify) |
| Monitor/wifi/bluetooth (→ hyprctl dpms, nmcli, rfkill) | ✅ Funciona |
| Brillo (`screen_control` → brightnessctl) | ✅ Funciona |
| Captura de pantalla (→ grim en Wayland) | ✅ Funciona |
| Monitor de red (`network_monitor`, → ip/ss/ping) | ✅ Funciona |
| Editor PDF / transcriptor (PyPDF2, vosk) | ✅ Fallback elegante sin la dep (error claro, no crash) |
| Audio mic/speaker (ALSA/PipeWire) | ✅ Device 8 (PipeWire), 16000Hz entrada / 44100Hz salida |
| Spam ALSA | ✅ Suprimido |
| Gemini Live Audio | ✅ gemini-2.5-flash-native-audio-latest |

**Fase 1 (MVP, ya hecha):** arrancar y chatear por texto en Linux con memoria
+ evolución + Obsidian.
**Fase 2 (ya hecha):** voz, control de sistema, notificaciones, ventanas y
brillo — mismos tools que Windows, backend nativo Linux. Requiere paquetes de
sistema: `wireplumber`, `hyprland`, `libnotify`, `brightnessctl`,
`networkmanager` (nmcli), `rfkill`, `grim`.
**Detalle Hyprland ≥0.55:** `hyprctl dispatch` ya no acepta la sintaxis
legacy (`focuswindow address:...` → rc 7); los tools de ERIS usan la forma
Lua (`hl.dsp.focus({ window = \"address:0x...\" })`).
**Estado del venv (.venv-linux, creado por run_linux.sh):** `test_all.py` da
**177 PASS / 1 FAIL** (eris.bat ambiental de Windows — se resuelve copiando la config). El 500/500 de tools carga completo: los 17
deps pip (requests/psutil/flask/numpy/vosk/PIL…) quedan funcionales. **GUI
automation (browser_control/computer_control/native_ui/desktop_control/screen_vision)
queda degradada en Wayland** (pyautogui/pygetwindow requieren X11): no
crashean, devuelven mensaje de error. Equivalente futuro: ydotool + grim/OCR.

## Resolver el popup de CFFI (solo Windows)

En Windows puede aparecer un diálogo \"Python-CFFI error\" por el callback de
`sounddevice`. Es cosmético y no fatal; no ocurre en Linux con PipeWire.

## Empaquetado e instalación nativa

### PKGBUILD (Arch/CachyOS)

El archivo `PKGBUILD` en la raíz de `ERIS-NEW/` permite empaquetar ERIS como
un paquete nativo de Arch. Instala en `/opt/eris`, crea el venv automáticamente
en primera ejecución, y registra el `.desktop` file para que aparezca en el
menú de aplicaciones.

```bash
cd /ruta/a/ERIS-NEW
makepkg -si    # construye e instala el paquete
```

### Docker (despliegue en contenedor)

El `Dockerfile` permite ejecutar ERIS en un contenedor:

```bash
docker build -t eris-ai /ruta/a/ERIS-NEW
docker run -it --rm \
  -v /home/tu_usuario/Eris_NEW/BaseDatosObsidian/BaseObsiEris:/app/obsidian_vault \
  -p 5000:5000 \
  eris-ai
```

### Instalador interactivo (`install_eris.sh`)

Para una instalación sin tener que compilar el paquete ni usar Pip:

```bash
cd /ruta/a/ERIS-NEW
./install_eris.sh
```

El instalador detecta tu distribución (Arch, Debian, Fedora) e instala las
dependencias de sistema automáticamente. Pide confirmación para:
- Instalación user-local en `~/eris-ai` (sin sudo)
- Instalación system-wide en `/opt/eris` (requiere sudo)
- Solo configurar (si ERIS ya está instalado)

## Errores conocidos

### ALSA paInvalidSampleRate
- **Solucionado**: `core/logging_setup.py` redirige stderr de ALSA a /dev/null
- **Causa original**: mic_device=9 (Ryzen HD Audio) causaba segfault + rate mismatch
- **Config actual**: mic_device=8 (PipeWire default), mic_device_rate=16000Hz, RECEIVE_SAMPLE_RATE=44100Hz

### Segfault al leer micrófono (device 9)
- **Solucionado**: se usa device 8 (PipeWire default) en lugar de device 9 (Ryzen)
- device 9 abre pero crasha al leer datos (exit 139)
- device 8 funciona correctamente con audio detectado

### Qt software rendering en Linux
- ERIS corre con software rendering en Qt (Ubuntu/Wayland por defecto)
- AMD Radeon 660M tiene soporte Vulkan pero Qt no lo usa automáticamente
- No es bloqueante para el funcionamiento básico

### Gemini model_for_conversation incompleto
- **Solucionado**: cambiado de `gemini-flash-latest` a `gemini-2.5-flash`
- `gemini-flash-latest` no soporta Live Audio → causaba crash
- `gemini-2.5-flash` tiene soporte Live Audio completo
