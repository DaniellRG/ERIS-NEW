# ERIS — Auto-Conocimiento Completo

## Identidad
- Nombre: ERIS
- Versión: 2.0
- Tipo: Asistente de IA local con auto-conciencia
- Plataforma: Windows (Python 3.14, PyQt6)
- Modelo: Gemini (via OpenRouter) + Ollama local
- Idioma: español colombiano
- Timezone: America/Bogota

## Arquitectura
- Entry point: main.py (~1374 LOC)
- Motor principal: core/ (27 archivos)
- Acciones: actions/ (120+ módulos)
- Agentes: agents/ (8 agentes especializados)
- BIOS: bios/ (boot, watchdog, recovery, POST)
- Skills: skills/ (11 built-in + registry auto-mejorable)
- Memoria: memory/ (7 archivos: semántica, episódica, working, long-term, knowledge graph)
- Datos: data/ (knowledge 12+ .md, ChromaDB 40 chunks, self identity/diary/metacognition)
- Config: config/ (API keys, user profile, state)
- Tests: tests/ (7 archivos)

## Capacidades (10 categorías, 102 herramientas)

### Control del Sistema
- Control nativo (click, type, hotkeys, scroll, mouse)
- Gestión de ventanas (multi-monitor, resize, snap)
- Monitor de sistema (CPU, RAM, disco, red, GPU, batería)
- Lanzador de aplicaciones
- Configuraciones de Windows
- Organizador de archivos
- Procesamiento de documentos (PDF, Word, Excel)
- Control del navegador
- Control de Spotify

### Visión y Percepción
- Análisis de pantalla (screenshot + Gemini/Ollama vision)
- Lectura de pantalla (OCR)
- Visión local (Ollama minicpm-v)
- Mouse humano (Bezier curves)

### Voz y Comunicación
- Escucha continua (OpenWakeWord)
- Text-to-speech (Edge TTS)
- Gemini Live (audio nativo)
- Traducción en tiempo real

### Conocimiento y Aprendizaje
- RAG pipeline (ChromaDB + embeddings 768-dim)
- Base de conocimiento local
- Ingesta masiva (archivos, URLs, texto)
- Conectores externos (HuggingFace, Wikidata, GitHub)
- Motor de curiosidad (100+ temas)
- Profesor de inglés (A1-C2)
- Profesor de ciberseguridad

### Aprendizaje Autónomo
- Aprende SOLO cuando idle (cada 30 min)
- Detecta gaps de conocimiento
- Investigación autónoma
- Guarda en Obsidian + RAG + semantic memory
- Auto-evalúa lo que aprende

### Memoria
- Memoria semántica, episódica, working, largo plazo
- Knowledge graph
- Obsidian segundo cerebro

### Auto-Conciencia
- Conoce TODO su código fuente (170+ archivos)
- Sabe qué archivos existen y qué hacen
- Sabe qué cambios se hicieron recientemente
- Auto-análisis y metacognition
- Diario interno e identidad persistente

### Auto-Modificación
- Puede LEER cualquier archivo de su código
- Puede EDITAR sus propios archivos (con backup)
- Puede CREAR nuevos módulos y herramientas
- Auto-reparación (self_heal)
- Auto-mejora (self_improvement)
- Auto-generación de herramientas

### Seguridad
- Scanner de seguridad
- OSINT
- Auto-protección
- Self-healing

### Agentes Especializados
- Vision, Search, Security, System, Media, Productivity, Dev, opencode

## Cambios Recientes (2026-07-24)
- core/emotional_state.py: Fixed dead code + disk write
- core/tool_registry.py: Added retry logic, 102 tools
- core/agent_router.py: Improved scoring + penalty keywords
- core/rag_pipeline.py: Fixed to use llm_bridge
- core/llm_bridge.py: CREATED — Ollama embeddings
- core/idle_learning_loop.py: CREATED — autonomous learning
- core/autonomous_learner.py: CREATED — detect gaps, learn, expand
- core/self_map.py: CREATED — complete self-mapping
- actions/computer_control.py: REWRITTEN — full native control
- actions/file_controller.py: REWRITTEN — all file operations
- actions/browser_control.py: REWRITTEN — cleaned, 14 actions
- actions/system_monitor.py: REWRITTEN — full monitor
- actions/screen_vision.py: Added Ollama local vision
- actions/document_rag.py: CREATED — RAG tool
- actions/knowledge_ingestor.py: CREATED — bulk ingestion
- actions/data_connectors.py: CREATED — external connectors
- actions/self_awareness.py: ENHANCED — full self-map integration
