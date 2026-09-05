# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/) (no released de
versiones formales; ERIS es un proyecto vivo que evoluciona por sesiones).

## [2026-09-06] — Instalador one-liner + wizard de arranque (Linux)

- `install.sh`: `curl | bash` instala ERIS en `~/.eris/ERIS-NEW` (copia
  separada del workspace de desarrollo), crea venv, instala
  `requirements-linux.txt`, deja el comando `eris` y abre el configurador.
  Por diseño instala siempre el último commit de `main`.
- `setup_wizard.py`: ventana de bienvenida (ERIS en grande) con API keys
  **REQUERIDAS** (Gemini) y **OPCIONALES** (Fish/Telegram/Spotify/OpenWeather/
  ElevenLabs/OpenRouter/Groq/Cerebras/Context7/HIBP) que pueden quedar vacías.
  Guarda en `config/api_keys.json` (UTF-8 sin BOM, merge conserva lo existente).
  Modos: GUI, `--check` (headless) y `--save k=v`.
- `eris` (launcher Linux): GUI por defecto (primer arranque abre el wizard),
  `--cli`, `--wizard`, `--check`, `--update` (git pull + deps).
- `main.py`: guard Windows-only de boot en Linux — single-instance mutex y
  global hotkey Win32 protegidos tras `os.name == "nt"`; primer arranque en
  Linux abre el wizard portable (`launch_after=False` evita doble instancia).
- README_LINUX.md: sección de instalación one-liner + comandos del launcher.

## [2026-09-05] — Sesión de saneamiento integral (Fases 1–4)

### Fase 1 — Bugs críticos

- Seguridad: `mobile/eris_mobile.config.json` — token de Telegram real
  reemplazado por placeholders.
- `actions/file_encryptor.py` — cifrado XOR inseguro → PBKDF2-HMAC-SHA256
  (200k iteraciones) + salt aleatorio de 16 bytes; excepciones tipadas.
  **Nota de compatibilidad**: los `.enc` viejos (XOR, sin salt) no se
  descifran con el nuevo código.
- `actions/disk_wiper.py` — contador `written` no se reseteaba entre pasadas;
  eliminado dead code (`random_path`) y un `pass` no-op.
- ~66 de 85 `except:` desnudos tipados según contexto en todo el repo
  (los restantes son strings de ejemplo/diagnóstico intencionales).
- `core/observer.py` — `ctypes.windll`/`user32` ahora guardados tras
  `os.name == "nt"` (no crashea en Linux).
- Rutas Windows hardcodeadas (`D:\Eris_Source`, `D:\Eris_NEW`, `C:\Users\...`)
  reemplazadas por `Path(__file__).resolve().parent.parent` + env vars
  `ERIS_WORKSPACE` / `ERIS_OBSIDIAN_VAULT` en: `core/self_evolution.py`,
  `core/auto_healer.py`, `core/codebase_explorer.py`,
  `core/devops_pipeline.py`, `core/refactoring_engine.py`,
  `core/multi_ai_hub.py`, `core/rag_engine.py`, `core/test_generator.py`,
  `core/voice_cloning.py`, `core/knowledge_graph.py`,
  `core/logging_setup.py` y `main.py` (3 lugares).
- `actions/cybersecurity.py` — `import random` movido al tope del archivo.
- `actions/credential_recovery.py` — whitelist `VALID_TABLES` para evitar
  SQL por f-string contra tablas no conocidas.

### Fase 2 — Rendimiento

- `core/tool_dispatcher.py` — los post-dispatch hooks ya no crean un hilo por
  llamada: se ejecutan en `_HOOK_EXECUTOR` (ThreadPoolExecutor, 2 workers).
- `actions/eris_db.py` — conexión SQLite compartida (`check_same_thread=False`)
  serializada con lock (en vez de abrir/cerrar por query); `busy_timeout=5000`,
  `synchronous=NORMAL`; búsquedas FTS5 (trigger-indexadas) para
  conversations/knowledge/episodic con fallback a `LIKE`; `episodic` agregado
  a `db_stats`. Verificado con test de concurrencia (8 hilos × 30 ops, 0
  errores).
- `memory/memory_manager.py` — saves a disco atómicas (`.tmp` + `os.replace`)
  y debounce: flush asíncrono serializado que coalesce writes; `load_memory()`
  fuerza flush si hay pendiente (nunca devuelve estado viejo).
- `core/audio_config.py` — cache TTL (5 s) para `sd.query_devices()` (1
  enumeración sirve para resolver device + UI + scoring).
- `core/plugin_manager.py` — `POLL_INTERVAL` 5→15 s.
- `core/connectivity.py` — `check_interval` 5→15 s (cada chequeo dispara hasta
  4 requests HTTP).

### Fase 3 — Testing y verificación

- `actions/accessibility_overlay.py` — `class _Magnifier(QWidget)` crasheaba
  al importar sin PyQt6 (rompía `core/action_imports.py` entero); base
  condicional (`QWidget if HAS_PYQT6 else object`).
- `actions/spreadsheet_generator.py` — constantes de estilo definidas a nivel
  de módulo aunque openpyxl faltara → `NameError`; ahora solo se definen si
  `_OPENPYXL_OK`.
- `test_all.py` — `BASE = Path(r"D:\Eris_Source")` hardcodeado → `BASE =
  Path(__file__).resolve().parent` (idéntico resultado en Windows, y ahora
  la suite se puede correr en Linux).
- `tests/generated/test_weather_report.py` — docstring con `\w` inválido
  (SyntaxWarning) corregido.
- Verificación: `test_all.py` en Linux sin PyQt6 → 48 PASS / 3 FAIL / 6 WARN
  (FAILs ambientales: PyQt6, `eris.bat`, `api_keys.json`; en Windows → 0 FAIL
  esperado). Compilación global: **590 `.py`, 0 errores**.

### Fase 4 — Documentación

- `AGENTS.md` — conteos reales (448/448 tools sincronizadas, 296 action
  modules, 69 knowledge files, líneas de main/ui/prompt) + constraints nuevos
  (rutas portables, guard de deps opcionales, `test_all.BASE` portable).
- `README.md` — claims stale corregidos (NeuroSpheres sin número fijo,
  counts de modules/knowledge, gate de tests).
- Este changelog + `CONTRIBUTING.md` nuevos.

---

## Historial previo (resumen de hitos del proyecto)

- Cerebro NeuroSpheres (esferas visuales, nodos auto-generados por sesión).
- `mission_agent` — protocolo operativo estilo opencode con cuaderno
  persistido y espejo Obsidian.
- `code_guard` — ojo guardián que detecta/corrige errores en vivo con backup +
  validación + rollback.
- `self_evolution` — loop antir-estancamiento cada 30 min (inventario vivo,
  auditoría, micro-mejoras reales sobre `core/`).
- `observer` — sentidos de Eris (ventana en foco, eventos de actividad,
  posible mirada-mirar con permiso).
- Portabilidad Linux Fase 1: arranque y chat por texto en CachyOS.
- Lote "Section 14M" y batches 3–6 de imports (16 + ~26 herramientas nuevas).