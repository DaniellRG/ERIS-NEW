# Java Avanzado — Guía de estudio

## 1. Lenguaje avanzado
- **Generics**: clases/métodos genéricos, comodines (wildcards) ? extends / ? super, borrado de tipos (erasure).
- **Programación funcional**: lambdas, interfaces funcionales (Predicate, Function, Consumer, Supplier), method references.
- **Streams**: stream pipeline, operaciones intermedias y terminales (map, filter, flatMap, reduce, collect, sorted, distinct, limit), Collectors (toList, groupingBy, joining).
- **Optional**: manejo seguro de valores nulos; orElse, orElseGet, map, flatMap, ifPresent.
- **Date/Time API** (java.time): LocalDate, LocalTime, LocalDateTime, ZonedDateTime, Duration, Period.
- **Strings**: StringBuilder, StringJoiner, text blocks, String.format, regex (Pattern/Matcher).

## 2. Colecciones avanzadas
- Jerarquía: Collection → List/Set/Queue; Map.
- Implementaciones: ArrayList, LinkedList, HashSet, LinkedHashSet, TreeSet, HashMap, LinkedHashMap, TreeMap, PriorityQueue.
- Reglas de equals/hashCode para usarlas correctamente en Set/Map.
- Iterator/Iterable, for-each, fail-fast; Collections (sort, reverse, unmodifiable).

## 3. Concurrencia y threads
- Creación: extends Thread, implements Runnable, Callable, ExecutorService/Executors, Future, CompletableFuture.
- Sincronización: synchronized (métodos/bloques), locks (ReentrantLock), volatile, semáforos.
- wait/notify/notifyAll; problemas clásicos (productor-consumidor).
- Thread-safe collections: ConcurrentHashMap, CopyOnWriteArrayList, BlockingQueue.
- Virtual threads (Project Loom) en Java moderno.

## 4. Entrada/Salida y persistencia
- java.io: InputStream/OutputStream, Reader/Writer, buffering, File.
- java.nio.file: Path, Files (copy, move, read/write), Files.walk.
- Serialización (Serializable) y Object streams.
- **JDBC**: DriverManager, Connection, Statement, PreparedStatement (inyección SQL), ResultSet, transacciones (commit/rollback), pooling básico.

## 5. Anotaciones, reflexión y empaquetado
- Anotaciones built-in (@Override, @Deprecated, @SuppressWarnings) y personalizadas (@interface).
- Reflexión: Class.forName, getMethods, getDeclaredFields, acceso a privados.
- Maven/Gradle: estructura del proyecto, dependencias, ciclo de build.

## 6. Buenas prácticas
- Programación defensiva; evitar null; interfaces sobre clases concretas.
- Patrones comunes: Singleton, Factory, Builder, Strategy.
- Manejo de recursos con try-with-resources; excepciones multicatch.

## 7. Puntos de examen frecuentes
- Escribir una lambda y su interfaz funcional equivalente.
- Pipeline de streams: transformar una lista (map/filter/reduce).
- Diferencia entre ? extends y ? super; borrado de tipos.
- Diferencias entre Runnable y Callable; cómo lanzar hilos con ExecutorService.
- Implementar equals/hashCode correctamente.
- PreparedStatement vs Statement (inyección SQL).

## Guía rápida
Si ERIS te pregunta sobre Java Avanzado: cubre generics, lambdas/streams, Optional,
colecciones, concurrencia (Executor, synchronized), JDBC, anotaciones/reflexión,
y Maven, con ejemplos de código.
