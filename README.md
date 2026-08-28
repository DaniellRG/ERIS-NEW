# ERIS AI — Asistente Autónomo

Asistente virtual de escritorio con autonomía total, integración profunda en Windows, inteligencia emocional, NeuroSpheres y 448 tools.

## Arquitectura

```
Eris_Source/
├── main.py              # Entry point GUI (PyQt6)
├── eris_cli.py          # CLI terminal (estilo opencode)
├── ui.py                # UI principal (2908 líneas)
├── config/
│   └── api_keys.json    # API keys, modelos, configuración
├── core/
│   ├── tool_registry.py         # 448 tools registradas
│   ├── tool_declarations.py     # 442 declarations para LLM
│   ├── tool_dispatcher.py       # Ejecutor de tools
│   ├── action_imports.py        # Imports de 295 action modules
│   ├── gemini_text_chat.py      # Chat dual Ollama/Gemini
│   ├── neuro_spheres.py         # Cerebro visual (91+ nodos)
│   ├── emotional_state.py       # Sistema emocional
│   ├── neural_bridge.py         # Puente neural
│   ├── world_simulation.py      # Simulación del mundo
│   ├── semantic_memory.py       # Memoria semántica
│   ├── rag_pipeline.py          # RAG (Retrieval Augmented Generation)
│   ├── compaction.py            # Compresión de contexto
│   ├── context_window_optimizer.py
│   ├── autonomous_learner.py    # Auto-aprendizaje
│   ├── idle_learning_loop.py    # Aprendizaje en idle
│   ├── prompt.txt               # System prompt de Eris
│   └── ...
├── actions/             # 295 módulos de acciones
├── agents/              # 9 agentes especializados
├── skills/              # 39 skills instaladas (21 builtin + 18 user_created)
├── memory/              # Estado de memoria y NeuroSpheres
├── data/
│   ├── knowledge/       # 62 archivos .md de conocimiento
│   ├── session_analytics.json
│   ├── search_history.json
│   └── ...
└── test_all.py          # 56 tests (0 fallos)
```

## Lanzamiento

### GUI (recomendado)
```cmd
cd D:\Eris_Source
.\.venv\Scripts\pythonw.exe main.py
```

### CLI (desde CMD)
```cmd
eris
```

### Tests
```cmd
cd D:\Eris_Source
.\.venv\Scripts\python.exe test_all.py
```

## Tools (442)

Las 448 tools están perfectamente sincronizadas entre `tool_declarations.py` y `tool_registry.py`. Categorías principales:

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
| **IDE** | ide_integration (detecta VS Code, PyCharm, etc.) |

## NeuroSpheres (91+ nodos)

Cerebro visual que crece con cada interacción. 11 esferas:

- **aprendizaje** — Lo que Eris aprende de cada sesión
- **memoria** — Conexiones entre aprendizajes
- **emociones** — Registros emocionales
- **habilidad** — Nuevas capacidades
- **investigacion** — Temas investigados
- **codigo** — Código analizado/revisado
- **error/bug/solucion** — Errores encontrados y solucionados
- **diagnostico** — Análisis completos

### Auto-aprendizaje
```python
from core.neuro_spheres import learn_from_sessions
result = learn_from_sessions()  # Analiza sesiones reales, crea nodos automáticamente
```

## Agentes (9)

| Agente | Función |
|--------|---------|
| `dev_agent` | Desarrollo de software |
| `media_agent` | Procesamiento multimedia |
| `productivity_agent` | Productividad y organización |
| `search_agent` | Búsqueda e investigación |
| `security_agent` | Seguridad del sistema |
| `system_agent` | Control del sistema |
| `vision_agent` | Análisis de imágenes/pantalla |
| `studies_agent` | Estudios/aprendizaje: explica, resume, planes, quizzes |
| `opencode_bridge` | Bridge a opencode |

## Skills (33)

Módulos especializados: code_review, deep_research, dev_flow, file_forensics, network_intel, obsidian_vault, self_evolution, voice_assistant, y más.

## Modelo de IA

- **Default**: Ollama (local, sin rate limits) — `qwen3:8b`
- **Fallback**: Gemini API (cloud)
- **Fish Audio TTS**: Voz personalizada
- **Config**: `config/api_keys.json`

## Requisitos

- Python 3.14
- PyQt6
- Ollama (opcional, para modo local)
- API key de Gemini (para modo cloud)
- API key de Fish Audio (para voz)

## Estado Actual

- **56/56 tests pass** ✓
- **448 tools** sincronizadas ✓
- **0 duplicados** en declarations/registry ✓
- **0 imports rotos** ✓
- **0 archivos .pyi huérfanos** ✓
- **0 stubs muertos** ✓
- **0 BOMs** ✓
- **95+ nodos NeuroSpheres** con contenido real ✓
- **62 knowledge files** ✓
- **9/9 agents** en uso ✓
