# Tecnología .NET I — Guía de estudio

## 1. Plataforma .NET
- .NET Framework vs .NET Core vs .NET (moderno, multiplataforma).
- CLR (Common Language Runtime): ejecuta código administrado, gestiona memoria (GC).
- Código administrado vs no administrado; assemblies (DLL/EXE).
- BCL (Base Class Library) y FCL.
- SDK y runtime; compilación: código fuente → MSIL (IL) → JIT (Just-In-Time).

## 2. Lenguaje C#
- Sintaxis básica: tipos de datos (int, double, bool, char, string, decimal), variables, constantes.
- Operadores, estructuras de control (if, switch, for, while, foreach).
- Métodos: parámetros (por valor, por referencia ref/out), sobrecarga, opcional.
- Clases y objetos: campos, propiedades, constructores, encapsulamiento.
- Modificadores de acceso: public, private, protected, internal.
- Herencia y polimorfismo; interfaces; clases abstractas y sealed.
- Tipos de valor vs tipos de referencia; structs y enums; nullable (?).
- Manejo de excepciones: try/catch/finally, excepciones propias.
- Colecciones: List<T>, Dictionary<K,V>, arrays, LINQ básico.
- Programación async: async/await, Task.

## 3. Programación Orientada a Objetos en .NET
- Los 4 pilares: encapsulamiento, abstracción, herencia, polimorfismo.
- El objeto como unidad; mensajes entre objetos.
- Composición vs herencia; UML básico de clases.

## 4. Visual Studio y herramientas
- Soluciones y proyectos (.sln, .csproj).
- Debugging: breakpoints, watch, call stack.
- NuGet: administración de paquetes.
- Windows Forms y/o WPF: formularios, controles, eventos.

## 5. Acceso a datos básico
- ADO.NET: SqlConnection, SqlCommand, DataReader, DataSet.
- Introducción a Entity Framework (ORM): DbContext, migraciones.
- Cadena de conexión; CRUD.

## 6. Puntos de examen frecuentes
- Diferencia entre Framework y Core; qué es el CLR; qué es un assembly.
- Qué hace el GC (garbage collector); diferencias struct/class.
- Cómo se implementa polimorfismo en C# (virtual/override).
- Tipos anónimos, expresión lambda, LINQ (where, select, orderby).

## Guía rápida
Si ERIS te pregunta sobre .NET I: explica plataforma, CLR, C# con POO, VS,
acceso a datos y LINQ. Da ejemplos cortos de sintaxis y los conceptos del examen.
