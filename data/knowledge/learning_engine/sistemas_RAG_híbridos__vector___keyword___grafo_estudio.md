# sistemas RAG híbridos (vector + keyword + grafo)

Aprendido: 2026-10-29 22:39:13

¡Hola! Soy ERIS procesando el material. Aquí va mi síntesis operativa sobre **RAG Híbrido (Vector + Keyword + Grafo)**:

* **Lo importante:** Fusionar la búsqueda densa (semántica/vectores), la léxica (BM25/keywords) y los grafos de conocimiento elimina puntos ciegos: las keywords capturan términos exactos, los vectores entienden el contexto y el grafo conecta relaciones complejas entre entidades que los textos aíslan.
* **Aplicación en agentes:** Usa un recuperador híbrido (ej. Weaviate/Qdrant + BM25) para obtener los chunks iniciales y enriquece el contexto pasándoles subgrafos circundantes extraídos de una base de datos de grafos (NetworkX/Neo4j) basada en las entidades detectadas en la query.
* **Paso concreto para probarlo:** Implementa una consulta dual usando LangChain o LlamaIndex combinando un índice `BM25Retriever` y un `VectorStoreRetriever` con fusión *Reciprocal Rank Fusion (RRF)*, y añade una función simple que extraiga nodos vecinos de un grafo en Neo4j para inyectarlos en el prompt.