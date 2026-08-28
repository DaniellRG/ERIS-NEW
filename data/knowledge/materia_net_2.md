# Tecnología .NET II — Guía de estudio (avanzado)

## 1. C# avanzado
- **Generics**: tipos genéricos, restricciones (where T : class, struct, new()), ventajas de tipado seguro y reutilización.
- **Delegados y eventos**: delegate, Action, Func, multicast; event y patrón publicador-suscriptor.
- **Expresiones lambda y LINQ**: LINQ to Objects, IEnumerable/IQueryable, operadores (Where, Select, OrderBy, GroupBy, Join, Any, All, First/FirstOrDefault, Aggregate).
- **async/await profundo**: Task, Task<T>, cancellation (CancellationToken), ConfigureAwait, flujo del SynchronizationContext.
- **Colecciones avanzadas**: Queue<T>, Stack<T>, LinkedList<T>, SortedSet<T>, ConcurrentDictionary.
- **Nullable reference types** (NRT), records, pattern matching avanzado (switch expressions, property patterns).
- **Tuplas, deconstructores, interpolación avanzada, atributos personalizados.**

## 2. Entity Framework (ORM)
- DbContext, DbSet, migraciones (Add-Migration/Update-Database).
- Code First vs Database First; modelos y fluencias (Fluent API) y anotaciones de datos.
- Consultas LINQ contra la BD; carga diferida vs anticipada (Lazy/Eager Loading).
- Tracking de entidades; transacciones; SQL crudo (FromSqlRaw, ExecuteSqlRaw).

## 3. ASP.NET Core
- **MVC**: controladores, vistas (Razor), modelos, validación, Action Results.
- **Web API / REST**: atributos de enrutamiento, modelos, JSON (System.Text.Json), códigos de estado, versionado.
- **Dependency Injection (DI)**: contenedor, ciclo de vida (Singleton, Scoped, Transient).
- Middleware y pipeline de request; autenticación y autorización (JWT, Identity, cookies).
- Configuración (appsettings.json), logging (ILogger), environments.

## 4. Arquitectura y buenas prácticas
- Principios SOLID aplicados a .NET.
- Arquitectura en capas y Clean Architecture (núcleo, infraestructura, presentación).
- Patrón repositorio y Unit of Work; MediatR/CQRS (introducción).
- Pruebas: xUnit/NUnit, mocking (Moq), tests de integración con WebApplicationFactory.
- Microservicios: comunicación HTTP/gRPC, mensajería (RabbitMQ), contenedores (Docker).

## 5. Otros
- WPF/MAUI avanzado: MVVM, data binding, INotifyPropertyChanged, comandos.
- Serialización: JSON/XML; caching (MemoryCache, Redis); background jobs (BackgroundService, Hangfire).

## 6. Puntos de examen frecuentes
- Implementar un evento y su manejador; explicar delegados.
- Escribir consultas LINQ y traducirlas a SQL mentalmente.
- Diferencia entre IEnumerable e IQueryable; async vs sincrónico (deadlock en UI).
- Configurar DI y sus ciclos de vida; explicar middleware.
- Migraciones con EF Core; relaciones entre entidades.
- Diferencias entre MVC y Web API; cómo autenticar con JWT.

## Guía rápida
Si ERIS te pregunta sobre .NET II: cubre generics, delegados/eventos, LINQ, async,
EF Core, ASP.NET Core MVC/API, DI, SOLID, pruebas y arquitectura, con código.
