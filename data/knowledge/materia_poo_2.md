# Programación Orientada a Objetos II — Guía de estudio (avanzado)

## 1. Principios de diseño
- **SOLID**:
  - S: Single Responsibility (una razón para cambiar).
  - O: Open/Closed (abierto a extensión, cerrado a modificación).
  - L: Liskov Substitution (subtipos intercambiables).
  - I: Interface Segregation (interfaces específicas).
  - D: Dependency Inversion (depender de abstracciones).
- **GRASP**: información expert, creator, controller, low coupling, high cohesion, protected variations, indirection, pure fabrication, polymorphism.
- Cohesión alta y acoplamiento bajo; diseño por contrato (precondiciones, postcondiciones, invariantes).

## 2. Patrones de diseño (GoF)
- **Creacionales**: Singleton, Factory Method, Abstract Factory, Builder, Prototype.
- **Estructurales**: Adapter, Decorator, Facade, Composite, Proxy, Bridge, Flyweight.
- **De comportamiento**: Observer, Strategy, Command, State, Template Method, Iterator, Mediator, Memento.
- Cómo elegir un patrón; ventajas, desventajas y cuándo NO usarlo.

## 3. UML avanzado
- **Diagrama de clases**: asociaciones, agregación, composición, herencia, implementación, multiplicidad, roles, navegabilidad.
- **Diagrama de secuencia**: lifelines, mensajes (síncronos/asíncronos), fragmentos combinados (alt, opt, loop).
- **Diagrama de estados**: estados, transiciones, eventos, subestados.
- **Diagrama de actividades**: acciones, decisiones, bifurcaciones, swimlanes.
- **Diagrama de componentes y de despliegue**: estructura física del sistema.
- Relación entre diagramas: de casos de uso → clases → secuencia → despliegue.

## 4. Arquitectura de software
- Arquitectura en capas (presentación, lógica, datos); MVC, MVP, MVVM.
- Arquitectura hexagonal / puertos y adaptadores; Clean Architecture.
- Patrones de arquitectura: cliente-servidor, peer-to-peer, pipelines.
- Estilos de integración: REST, mensajería asíncrona, eventos de dominio.

## 5. Diseño de interfaces y APIs
- Diseño por contrato; DTOs; versionado de API.
- Manejo de errores y excepciones como diseño (jerarquías de excepción).

## 6. Calidad de código
- **Refactoring**: extraer método, renombrar, reemplazar condicional por polimorfismo, etc.
- **TDD**: red-green-refactor; ciclo de desarrollo orientado a pruebas.
- Pruebas unitarias (asserts, mocks, stubs, fakes), pruebas de integración.
- Code smells y deuda técnica; revisión de código.

## 7. Puntos de examen frecuentes
- Identificar un patrón GoF a partir de una descripción y diagramarlo.
- Aplicar SOLID: refactorizar una clase que viola SRP/OCP.
- Dibujar un diagrama de secuencia de un caso de uso.
- Diferenciar agregación de composición con ejemplos.
- Explicar TDD y refactoring con un ejemplo práctico.

## Guía rápida
Si ERIS te pregunta sobre POO II: cubre SOLID y GRASP, patrones GoF con ejemplos,
UML avanzado (clases, secuencia, estados), arquitectura en capas/MVC, TDD y
refactoring, con ejercicios prácticos.
