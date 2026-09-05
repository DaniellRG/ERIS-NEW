# ERIS en LINUX (CachyOS/Arch) — Guía de despliegue dual

ERIS es **multiplataforma**: el mismo código corre en Windows y Linux. Este
documento explica cómo levantar ERIS en tu laptop con **CachyOS** y cómo
trabajar en paralelo entre tus dos máquinas.

> El código ya está blindado para importar completo en Linux sin los paquetes
> Windows-only (pycaw, comtypes, win10toast, pywinauto, pygetwindow). Esas
> acciones se desactivan automáticamente (quedan como `None`) y las 400+ tools
> multiplataforma siguen funcionando.

---

## Requisitos de sistema (una vez)

```bash
sudo pacman -S python python-pip python-virtualenv portaudio pipewire-pulse git
```

## Despliegue

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

- `"os_system": "linux"`
- `"mic_device"` / `"speaker_device"` → índices de tu audio en Linux (PipeWire)
- `"chrome_exe_path"` → normalmente vacío funciona (busca en PATH)

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

**Fase 1 (MVP, ya hecha):** arrancar y chatear por texto en Linux con memoria
+ evolución + Obsidian.
**Fase 2 (ya hecha):** voz, control de sistema, notificaciones, ventanas y
brillo — mismos tools que Windows, backend nativo Linux. Requiere paquetes de
sistema: `wireplumber`, `hyprland`, `libnotify`, `brightnessctl`,
`networkmanager` (nmcli), `rfkill`, `grim`.
**Detalle Hyprland ≥0.55:** `hyprctl dispatch` ya no acepta la sintaxis
legacy (`focuswindow address:...` → rc 7); los tools de ERIS usan la forma
Lua (`hl.dsp.focus({ window = "address:0x..." })`).
**Estado del venv (.venv-linux, creado por run_linux.sh):** `test_all.py` da
**52 PASS / 2 FAIL** (eris.bat y api_keys.json, ambientales de Windows — se
resuelven copiando la config). El 448/448 de tools carga completo: los 17
deps pip (requests/psutil/flask/numpy/vosk/PIL…) quedan funcionales. **GUI
automation (browser_control/computer_control/native_ui/desktop_control/screen_vision)
queda degradada en Wayland** (pyautogui/pygetwindow requieren X11): no
crashean, devuelven mensaje de error. Equivalente futuro: ydotool + grim/OCR.

## Resolver el popup de CFFI (solo Windows)

En Windows puede aparecer un diálogo "Python-CFFI error" por el callback de
`sounddevice`. Es cosmético y no fatal; no ocurre en Linux con PipeWire.
