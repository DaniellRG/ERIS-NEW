# Base de Datos II — Guía de estudio (avanzado)

## 1. SQL avanzado
- Subconsultas: escalares, de fila, de tabla; correlacionadas; IN/EXISTS/ANY/ALL.
- **CTE** (Common Table Expressions): WITH ... AS, recursivas.
- **Window functions**: ROW_NUMBER, RANK, DENSE_RANK, NTILE, LAG/LEAD, SUM/AVG OVER (PARTITION BY ... ORDER BY ...).
- CASE, CAST/CONVERT, funciones de texto y fecha.
- **Stored procedures** y **funciones**: parámetros, control de flujo, manejo de errores (TRY/CATCH o EXCEPTION).
- **Triggers**: AFTER/BEFORE, INSTEAD OF; tablas insertadas/borradas.
- **Vistas**: simples y materializadas (indexadas).

## 2. Índices y optimización
- Tipos de índice: clustered vs non-clustered, compuestos, únicos; índices en texto (full-text).
- Cuándo usarlos; trade-offs en escritura.
- Plan de ejecución (EXPLAIN / Show Execution Plan); lecturas lógicas, operadores (seek/scan, joins, sort).
- Estadísticas; comando de recompilación.
- Anti-patrones: SELECT *, funciones en WHERE, índices sin uso, no usar SARGability.

## 3. Transacciones y concurrencia
- **ACID**: atomicidad, consistencia, aislamiento, durabilidad.
- Estados de una transacción; COMMIT/ROLLBACK.
- Niveles de aislamiento: READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE; snapshot.
- Fenómenos: lectura sucia, no repetible, fantasma.
- Control de concurrencia: bloqueos (shared/exclusive), granularidad de locks, deadlocks (detección y prevención), tiempos de espera.

## 4. Seguridad y administración
- Usuarios, roles, permisos (GRANT/REVOKE, DENY).
- Encriptación de datos (TDE, columnas); máscara de datos.
- Respaldo y recuperación: full/differential/log backups, restauración, punto de restauración.
- Mantenimiento: reindexar, actualizar estadísticas, particionado de tablas.
- Monitoreo de rendimiento y registro de errores.

## 5. Modelado avanzado
- Normalización superior: BCNF, 4FN (dependencias multivaluadas), 5FN (join).
- Desnormalización controlada (para lectura/rendimiento).
- Modelo dimensional: hechos (facts) y dimensiones, esquema estrella y copo de nieve (intro a data warehouse).
- Diagramas avanzados y documentación (diccionario de datos).

## 6. NoSQL (introducción)
- Tipos: clave-valor (Redis), documentos (MongoDB), columnas (Cassandra), grafos (Neo4j).
- Cuándo elegir SQL vs NoSQL; CAP (consistencia, disponibilidad, particionamiento).
- Integración: SQL Server + JSON; Mongo CRUD básico.

## 7. Puntos de examen frecuentes
- Escribir una query con window function (rank por grupo).
- Crear un stored procedure con validación y errores.
- Explicar niveles de aislamiento y qué problema evita cada uno.
- Leer un plan de ejecución y detectar un scan innecesario.
- Explicar ACID con ejemplo; cómo evitar deadlocks.
- Diseñar un esquema estrella sencillo.

## Guía rápida
Si ERIS te pregunta sobre Base de Datos II: cubre SQL avanzado (CTE, window functions,
procedimientos, triggers), índices y planes, transacciones/aislamiento, seguridad,
backups, normalización avanzada y NoSQL básico, con ejemplos.
