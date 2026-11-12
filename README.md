# ERIS — Asistente de Escritorio Agéntico

**ERIS 4.0.1 "Constellation Prime"** — Asistente de escritorio agéntico avanzado
en Python 3.14 + PyQt6, con cerebro NeuroSpheres, chat dual Ollama/Gemini, TTS
local (Kokoro-82M), memoria semántica/episódica + RAG, auto-evolución, laboratorios
de pentest y simulación de mundo. Corriendo en Windows y Linux.

## Qué hace ERIS

ERIS es un asistente de escritorio **agéntico**: no solo responde, ejecuta. Tiene
**525 herramientas** (acciones), **14 agentes especializados + 15 sub-agentes**,
y puede escribir código, gestionar archivos, controlar audio, leer la agenda,
hablar por voz y automejorarse. Todo con permisos (fail-closed) y un gate de
seguridad para acciones de alto riesgo.

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python 3.14 |
| GUI | PyQt6 |
| LLM local | Ollama (`qwen3:8b` por defecto) |
| LLM nube | Gemini (`gemini-3.1-flash-lite` como fallback) |
| TTS | Kokoro-82M local (`ef_dora`, español) / Edge TTS |
| Cerebro | NeuroSpheres (auto-creciente) + memoria semántica/episódica/working |
| RAG | sentence-transformers (con fallback TF-IDF) |
| Acciones | 309 módulos en `actions/` (una herramienta por archivo) |
| Config | `config/api_keys.json` (UTF-8 sin BOM, gitignored) |
| Métricas | `scripts/metrics_ssot.py` (fuente única de verdad) |

## Instalación segura

### Requisitos

- Python 3.12+ (3.14 recomendado)
- Git
- Ollama instalado y ejecutando (`ollama serve`, modelo `qwen3:8b`)

### Pasos

```bash
# 1. Clonar (o usar tu checkout existente)
git clone <tu-repo-eris>
cd eris

# 2. Entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux

# 3. Dependencias (usa requirements-linux.txt en Linux)
pip install --upgrade pip
pip install -r requirements.txt   # Windows
# pip install -r requirements-linux.txt  # Linux

# 4. Crear config (se te pedirá al arrancar la primera vez)
python main.py

# 5. Arrancar
python main.py
```

> ⚠️ **Seguridad:** El API REST (`main_server.py`, puerto 8081) y el WebSocket
> (puerto 8766) se vinculan a `127.0.0.1` por defecto y exigen token Bearer.
> El endpoint móvil `POST /chat` (puerto 8765) también exige token. No expongas
> estos puertos a la red sin revisar el firewall. Ver Fase 1 y `docs/security/`.

## Cómo correr los tests

```bash
# Suite completa
python test_all.py

# Un solo test con pytest
python -m pytest tests/test_neurospheres.py -x

# Compile check de un archivo
python -m py_compile core/app.py
```

En clon fresco, algunas pruebas fallan por archivos de datos ausentes
(`memory/*.json`, `config/api_keys.json` están en `.gitignore`). Se recrean con:

```bash
python scripts/ci_seed.py
```

## Validación de herramientas (CI)

```bash
python scripts/validate_tools.py
```

Falla si `tool_registry.py` y `tool_declarations.py` no están sincronizados o
hay duplicados.

## Métricas (fuente única de verdad)

```bash
python scripts/metrics_ssot.py
```

Genera el JSON con el conteo real de tools, acciones, agentes, skills y el
baseline de tests. `AGENTS.md` y `CHANGELOG.md` se actualizan a partir de este
archivo, no de números hardcodeados.

## Estructura del repositorio

```
ERIS/
├── main.py              # Punto de entrada GUI (delgado tras refactor Fase 3)
├── eris_cli.py          # Entrada CLI (terminal, chat Ollama/Gemini)
├── core/                # Núcleo: app, controller, events, shared_context, …
├── actions/             # 309 módulos de herramientas (una por archivo)
├── agents/              # 14 sub-agentes especializados + 15 sub-agentes
├── skills/              # Skills (formato SKILL.md)
├── gui/                 # Interfaz (estilos, widgets, settings, transcript…)
├── docs/                # Documentación (incluye docs/superpowers/ con specs)
├── scripts/             # validate_tools.py, metrics_ssot.py, ci_seed.py
├── tests/               # Suite pytest + test_all.py
├── config/              # api_keys.json (gitignored)
├── memory/              # Memoria semántica/episódica/working (gitignored)
├── data/                # Datos de usuario (gitignored)
└── docs/superpowers/    # Specs y planes de desarrollo
```

## Licencia

Uso personal/proyecto propio. Las claves de API y los datos de memoria no se
comitean (`config/api_keys.json`, `memory/`, `data/` están en `.gitignore`).

---

## Flujo de trabajo para checkouts divergentes (Windows ↔ Linux)

ERIS se desarrolla en dos entornos (Windows y Linux) que comparten el mismo
repositorio. Esta guía evita pisar trabajo entre checkouts.

### Antes de cambiar de SO

```bash
# En el SO actual, revisa estado
git status

# Si hay cambios sin commitear que quieres conservar:
git add -A
git commit -m "WIP: <descripción>"   # o usa git stash -u si no quieres commitear
# O, si prefieres no commitear:
git stash -u
```

### Al cambiar al otro SO

```bash
# Traer cambios del otro SO
git fetch origin
git pull --rebase

# Si usaste stash, recuperarlo:
git stash pop
```

### Si hubo conflictos

```bash
git status           # ver archivos en conflicto
# Editar los archivos para resolver, luego:
git add <archivo-resuelto>
git rebase --continue   # o git merge --continue
```

### Reglas de oro

1. **Nunca** trabajes en ambos SO a la vez sobre la misma rama sin commitear/stashear.
2. Los entornos virtuales son locales y separados: `.venv` (Windows) y
   `.venv-linux` (Linux). Ambos están en `.gitignore`.
3. Los datos de usuario (`config/api_keys.json`, `memory/`, `data/`) son locales y
   no viajan en git. Usa `scripts/ci_seed.py` para crear placeholders en un clone fresco.
4. Antes de cerrar una sesión de trabajo, siempre `git status` para confirmar que
   no dejaste cambios sin commitear.

---

Mantén `AGENTS.md` y `CHANGELOG.md` sincronizados con `scripts/metrics_ssot.py`.
