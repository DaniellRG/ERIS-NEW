# sistemas RAG híbridos (vector + keyword + grafo)

Aprendido: 2026-10-23 17:36:01

**Lección ERIS: RAG Híbrido (Vector + Keyword + Grafo)**

*   **Lo importante:** Unificar similitud semántica (Vectores), coincidencia exacta de términos (BM25/Keyword) y relaciones estructuradas (Grafos) elimina puntos ciegos. El vector capta el *significado*, el keyword rescata *datos precisos* (códigos, nombres) y el grafo mapea *conexiones complejas*.
*   **En mi código:** Implementa un recuperador tripartito donde el usuario lanza la query en paralelo a Chroma/Milvus (Vectores), Elasticsearch/BM25 (Keyword) y Neo4j (Grafo). Usa *Reciprocal Rank Fusion (RRF)* para mezclar los resultados y alimenta al LLM solo con el top $K$ unificado.
*   **Paso concreto:** Crea una función en Python que reciba una query, ejecute una búsqueda vectorial y una por BM25, y fusione sus IDs usando RRF ponderado.