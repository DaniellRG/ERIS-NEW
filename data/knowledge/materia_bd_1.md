# Base de Datos I — Guía de estudio

## 1. Conceptos fundamentales
- Dato e información; sistema gestor de base de datos (SGBD / DBMS).
- Base de datos relacional: tablas, filas (registros), columnas (campos/atributos).
- Ventajas de las BD: integridad, consistencia, concurrencia, seguridad.
- Modelo entidad-relación (E/R): entidades, atributos, relaciones, cardinalidad (1:1, 1:N, N:M).
- Modelo relacional: tablas, claves.

## 2. Claves e integridad
- Clave primaria (PK): identifica de forma única una fila.
- Clave foránea (FK): referencia una PK de otra tabla.
- Claves candidatas, alternas y compuestas.
- Reglas de integridad: entidad, referencial, dominio, usuario.
- Normalización: 1FN, 2FN, 3FN (y breve FNBC/4FN).
  - 1FN: valores atómicos (sin grupos repetidos).
  - 2FN: 1FN + dependencia total (sin dependencia parcial de la clave).
  - 3FN: 2FN + sin dependencias transitivas.

## 3. SQL (Lenguaje de consulta estructurada)
- **DDL** (definición): CREATE, ALTER, DROP, TRUNCATE.
- **DML** (manipulación): SELECT, INSERT, UPDATE, DELETE.
- **DCL** (control): GRANT, REVOKE.
- SELECT básico: columnas, WHERE, ORDER BY, DISTINCT.
- Filtros: =, <>, <, >, LIKE, IN, BETWEEN, AND, OR, NOT, IS NULL.
- Funciones agregadas: COUNT, SUM, AVG, MIN, MAX; GROUP BY y HAVING.
- Uniones: INNER JOIN, LEFT JOIN, RIGHT JOIN, FULL JOIN; producto cartesiano.
- Subconsultas; vistas (VIEW); índices (índice primario/secundario).

## 4. Modelado y diseño
- Pasos: análisis de requisitos → modelo conceptual (E/R) → modelo lógico → físico.
- Diccionario de datos; diagramas.
- Claves compuestas y relaciones N:M → tablas de intersección.

## 5. SGBD comunes
- MySQL/MariaDB, SQL Server, PostgreSQL, Oracle, SQLite.

## 6. Puntos de examen frecuentes
- Diferencia entre clave primaria y foránea; ejemplo con dos tablas.
- Normalizar un ejemplo hasta 3FN.
- Escribir consultas SQL con JOIN, GROUP BY y HAVING.
- Diferencia entre DDL, DML y DCL.
- Cardinalidad de una relación E/R.

## Guía rápida
Si ERIS te pregunta sobre Base de Datos I: cubre el modelo E/R, claves, normalización
(1FN-3FN), SQL (DDL/DML, SELECT, JOIN, GROUP BY) y diseño de tablas, con ejemplos.
