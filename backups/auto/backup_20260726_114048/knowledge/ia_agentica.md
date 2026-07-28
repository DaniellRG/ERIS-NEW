# Tecnologias de IA Agentic - Guia Completa

## Arquitectura de Agentes de IA

### Que es un Agente de IA
Un agente de IA es un sistema autonomo que perce su entorno, toma decisiones y ejecuta acciones para lograr objetivos. A diferencia de un chatbot tradicional, un agente tiene memoria, herramientas, planificacion y capacidad de razonamiento.

### Componentes Fundamentales
1. **Percepcion**: Entrada de datos del entorno (texto, audio, imagen, sensores)
2. **Razonamiento**: LLM como cerebro central (GPT-4, Claude, Gemini, LLaMA)
3. **Memoria**: Corto plazo (contexto), largo plazo (vectores, grafos), trabajo (estado actual)
4. **Herramientas**: APIs, bases de datos, navegadores, filesystem, terminal
5. **Planificacion**: Chain-of-Thought, ReAct, Tree-of-Thought, goal decomposition
6. **Ejecucion**: Tool calling, function calling, code execution

### Patrones de Agentes

#### ReAct (Reason + Act)
El agente alterna entre razonar y actuar:
1. Thought: "Necesito buscar informacion sobre X"
2. Action: search(query="X")
3. Observation: [resultados]
4. Thought: "Ahora tengo la info, puedo responder"
5. Answer: [respuesta]

#### Tool Use / Function Calling
El LLM decide que herramienta usar basandose en la descripcion de la tarea. Los frameworks modernos (OpenAI, Gemini) soportan tool calling nativo.

#### Multi-Agent Systems
Multiples agentes especializados colaboran:
- **Orchestrator**: Coordina y delega tareas
- **Researcher**: Busca informacion en fuentes externas
- **Coder**: Escribe y ejecuta codigo
- **Reviewer**: Revisa y valida el trabajo
- **Memory Manager**: Gestiona el conocimiento acumulado

#### Planificacion Jerarquica
El agente descompone objetivos complejos en sub-tareas:
1. Objetivo: "Crear un reporte de ventas trimestral"
2. Sub-tareas:
   - Extraer datos de la base de datos
   - Calcular metricas clave
   - Generar graficos
   - Redactar analisis
   - Formatear documento final

## Frameworks de Agentes

### LangChain
Framework principal para construir agentes LLM. Componentes: Chains, Agents, Tools, Memory, Retrievers. Soporta multiples LLMs y herramientas.

### LangGraph
Extension de LangChain para grafos de estados. Permite crear flujos complejos con ciclos, ramas y puntos de decision.

### CrewAI
Framework para sistemas multi-agente. Define roles (agents), tareas (tasks), y equipos (crews). Ideado para automatizar procesos empresariales.

### AutoGen (Microsoft)
Framework para agentes conversacionales. Soporta chat grupal, ejecucion de codigo, herramientas. Integracion con Azure.

### LlamaIndex
Especializado en RAG (Retrieval Augmented Generation). Conecta LLMs con fuentes de datos externas via indices vectoriales.

### Semantic Kernel (Microsoft)
SDK para integrar LLMs en aplicaciones .NET y Python. Plugins, memory, planners. Orientado a empresarial.

## RAG (Retrieval Augmented Generation)

### Pipeline Completo
1. **Ingesta**: Cargar documentos (PDF, DOCX, TXT, MD, HTML)
2. **Chunking**: Dividir en fragmentos semanticos (500-1000 tokens)
3. **Embedding**: Convertir a vectores numericos (nomic-embed-text, text-embedding-3)
4. **Almacenamiento**: Guardar en base de datos vectorial (ChromaDB, Pinecone, Weaviate, Milvus)
5. **Retrieval**: Buscar fragmentos relevantes por similitud semantica
6. **Reranking**: Re-ordenar por relevancia cross-encoder
7. **Generacion**: El LLM genera respuesta usando contexto recuperado

### Tipos de RAG
- **Naive RAG**: Basico, busca y genera
- **Advanced RAG**: Pre/post retrieval, query rewriting, HyDE
- **Modular RAG**: Componentes intercambiables, pipeline flexible
- **Agentic RAG**: Agente decide cuando y como buscar
- **Graph RAG**: RAG sobre grafos de conocimiento (Neo4j + embeddings)

### Bases de Datos Vectoriales
| Base de Datos | Tipo | Ventaja |
|---|---|---|
| ChromaDB | Local | Facil de usar, open source |
| Pinecone | Cloud | Managed, escalable |
| Weaviate | Local/Cloud | GraphQL, multimodal |
| Milvus | Local/Cloud | Alta performance, GPU |
| Qdrant | Local/Cloud | Rust, rapido |
| FAISS | Local | Facebook, GPU optimized |
| pgvector | SQL | PostgreSQL extension |

### Embedding Models
- **nomic-embed-text**: 768 dim, open source, local via Ollama
- **text-embedding-3-small/large**: OpenAI, 1536/3072 dim
- **BGE-large**: 1024 dim, open source
- **E5**: Microsoft, 1024 dim
- **Cohere Embed**: Multilingual, 1024 dim

## Fuentes de Conocimiento para IA

### Repositorios de Datasets
- **Hugging Face Datasets**: Millones de datasets para fine-tuning, evaluacion, RAG
- **Kaggle**: Datasets CSV/JSON por industria (finanzas, salud, retail)
- **Google Dataset Search**: Buscador de datasets gubernamentales y academicos
- **Papers With Code**: Datasets asociados a papers de investigacion

### APIs de Conocimiento
- **RapidAPI**: Marketplace de APIs (clima, finanzas, noticias, traduccion)
- **Apify**: Web scraping estructurado
- **Wikipedia/Wikidata API**: Conocimiento estructurado y semi-estructurado
- **arXiv API**: Papers academicos de investigacion

### Bases de Conocimiento Gubernamentales
- **data.gov**: EE.UU. - Millones de datasets abiertos
- **datos.gob.es**: Espana - Datos abiertos del gobierno
- **datos.gov.co**: Colombia - Datos abiertos nacionales
- **World Bank Open Data**: Datos economicos mundiales

### Conocimiento Especializado
- **PubMed**: Base de datos biomedica (35M+ citas)
- **IEEE Xplore**: Papers de ingenieria y computacion
- **ACM Digital Library**: Computing machinery
- **Stack Overflow**: Preguntas y respuestas de programacion

## Fine-Tuning y Entrenamiento

### Tipos de Fine-Tuning
- **Full Fine-Tuning**: Re-entrena todos los parametros (requiere GPU grande)
- **LoRA**: Low-Rank Adaptation, entrena matrices de bajo rango (eficiente)
- **QLoRA**: LoRA cuantizado (4-bit), funciona en GPUs modestas
- **Prompt Tuning**: Aprende prompts optimizados
- **RLHF**: Reinforcement Learning from Human Feedback
- **DPO**: Direct Preference Optimization (alternativa a RLHF)

### Datos para Fine-Tuning
- Formato: JSONL con pares input/output
- Calidad > Cantidad: 500-1000 ejemplos bien escritos pueden ser suficientes
- Diversidad: Cubrir todos los casos de uso esperados
- Limpieza: Eliminar ruido, inconsistencias, datos sensibles

### Evaluacion
- **BLEU/ROUGE**: Metricas de similitud de texto
- **Perplexity**: Que tan bien predice el modelo
- **Human Evaluation**: Evaluacion humana (la mas confiable)
- **LLM-as-Judge**: Usar otro LLM para evaluar
- **Benchmarks**: MMLU, HumanEval, GSM8K, ARC
