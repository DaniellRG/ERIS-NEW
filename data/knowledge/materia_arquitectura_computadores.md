# Arquitectura de Computadores — Guía de estudio

## 1. Conceptos fundamentales
- Arquitectura (lo que el programador ve: ISA, conjunto de instrucciones) vs microarquitectura (cómo se implementa).
- **Modelo de Von Neumann**: memoria única para datos e instrucciones, CPU, unidad de control, ALU, bus. Cuello de botella de Von Neumann.
- **Arquitectura Harvard**: memorias separadas para datos e instrucciones.

## 2. Representación de datos
- Sistemas de numeración: binario, octal, hexadecimal; conversiones.
- Representación de enteros: signo-magnitud, complemento a 2, exceso.
- Representación en coma flotante: IEEE 754 (signo, exponente, mantisa), precisión simple/doble.
- Códigos: BCD, ASCII, Unicode.
- Operaciones básicas en binario: suma, resta (con complemento a 2), y/o/xor, desplazamientos.

## 3. CPU
- Unidad de control (CU): interpreta y coordina instrucciones.
- Unidad aritmético-lógica (ALU): realiza operaciones aritméticas y lógicas.
- Registros: PC (contador de programa), IR (registro de instrucción), AC (acumulador), SP, registros de propósito general.
- Ciclo de instrucción: buscar (fetch) → decodificar (decode) → ejecutar (execute) → escribir resultado.
- Modos de direccionamiento: inmediato, directo, indirecto, registro, índice, relativo.
- RISC vs CISC.
- **Pipeline**: segmentación del ciclo de instrucción (fetch, decode, execute, write-back); riesgos (datos, control, estructurales) y soluciones.
- Memorias caché: L1/L2/L3, principio de localidad (espacial y temporal), acierto/fallo (hit/miss), políticas de reemplazo (LRU, FIFO).
- RISC-V / ARM / x86 como ejemplos de ISA.

## 4. Memoria
- Jerarquía de memoria: registros → caché → RAM → disco.
- Memoria principal: RAM (DRAM) vs ROM; volátil vs no volátil.
- Direcciones de memoria; unidad de gestión (MMU), direcciones lógicas vs físicas.
- Memoria virtual: paginación, tablas de páginas, TLB.

## 5. Entrada/Salida y buses
- Buses: datos, dirección, control; ancho de bus, velocidad, arbitraje.
- Periféricos; técnicas de E/S: programada, interrupciones, DMA (acceso directo a memoria).
- Interrupciones: prioridades, controlador de interrupciones.

## 6. Componentes y rendimiento
- Placa madre, CPU, RAM, disco (HDD/SSD), GPU, fuente.
- Métricas: IPC (instrucciones por ciclo), CPI, frecuencia (GHz), tiempo de ejecución.
- Ley de Amdahl: impacto de acelerar una parte del sistema.

## 7. Puntos de examen frecuentes
- Convertir números entre bases y aplicar complemento a 2.
- Explicar el ciclo de instrucción de la CPU.
- Diferencia entre RISC y CISC; entre arquitectura Von Neumann y Harvard.
- Explicar la jerarquía de memoria y la caché (aciertos/fallos).
- Modos de direccionamiento con ejemplos.
- Calcular rendimiento simple (CPI / tiempo).

## Guía rápida
Si ERIS te pregunta sobre Arquitectura de Computadores: cubre Von Neumann, binario
y complemento a 2, CPU (ciclo de instrucción), memoria (caché y jerarquía),
buses/E-S y rendimiento (CPI, Ley de Amdahl), con ejemplos numéricos.
