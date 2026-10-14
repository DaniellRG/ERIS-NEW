---
name: armar-clase
description: Arma una clase/leccion HTML interactiva y autocontenida (portada, slides navegables, quiz con correccion y simulacion opcional) a partir de un tema o de un documento. Cargar cuando el usuario pida una clase, una leccion, un tutorial interactivo, un material de estudio o un quiz.
version: 1.0.0
category: educacion
tags: [clase, leccion, slides, quiz, educacion, tutorial, interactivo, estudio]
---

## CUÁNDO USARLA

Cuando el usuario pida: "armá una clase de…", "haceme una lección sobre…",
"un tutorial interactivo de…", "un material de estudio de…", "un quiz de…", o pase
un documento (PDF/MD/TXT) y diga "convertilo en clase". La clase se escribe como
**un solo archivo HTML** (sin build, sin servidor), navegable en el navegador.

## REGLA DE ORO

**Un único HTML autocontenido** en
`~/Desktop/ERIS_web/clases/<slug>-<fecha>.html`, con:
1. **Portada** (título, bajada, autor/ERIS).
2. **Slides navegables** con flechas ← → (y teclado).
3. **Quiz** al final con corrección automática y puntaje.
4. **Opcional**: una simulación interactiva simple si el tema lo pide.
Todo el CSS y JS adentro. Las librerías (KaTeX/Three.js) por **CDN** (requiere
internet al abrir).

## PROCEDIMIENTO

### 1. Entender el material
- Si el usuario dio un **tema**, usalo.
- Si dio un **documento**, leelo primero:
  - texto/markdown: `file_api action=read filepath='...'`
  - PDF: `pdf_editor` (extraer texto)
- Si el pedido es vago ("algo de historia"), hacé **una** pregunta corta de alcance
  antes de armar (tema, nivel, cantidad de slides).

### 2. Armar el guion (outline → escenas)
Generá un outline de 6–12 escenas. Cada escena es uno de estos tipos:

| Tipo | Qué es |
|------|--------|
| **slide** | Título + 3–5 bullets o una figura. Una idea por slide. |
| **concepto** | Un diagrama simple (SVG) que explica una relación (flujo, ciclo, capas). |
| **simulación** | Un control (slider/botón) que cambia un resultado en vivo (una función, una física simple, un algoritmo paso a paso). |
| **quiz** | Una o más preguntas (opción múltiple o verdadero/falso) con corrección y feedback. |
| **cierre** | Resumen + "para seguir pensando". |

Para temas de proyecto, podés sumar una consigna **PBL** (un rol y un entregable
con hitos) como escena final.

### 3. Escribir la clase
```
file_api action=write filepath='~/Desktop/ERIS_web/clases/<slug>-<YYYYMMDD-HHMM>.html' content='<!doctype html> ... </html>'
```
Estructura recomendada del HTML:
- Un contenedor `#deck` con un `<section class="scene">` por escena.
- Navegación: dos botones y las teclas `←`/`→`; un contador `escena i/N`.
- El quiz: un `<form>`/botones con JS que marca correcto/incorrecto y suma el
  puntaje (mostrá el resultado y la explicación de cada respuesta).
- Estilos: tipografía legible, buen contraste, responsive (funciona en celular).
- `file_api` crea la carpeta `clases/` si no existe.

### 4. Verificar que no quedó en blanco (obligatorio)
```
file_api action=read filepath='...'
```
Confirmá que: hay ≥6 `<section` de escena, hay `<script`, hay lógica de quiz
(puntaje/corrección), hay navegación, y cierra con `</html>`. Si falta algo,
corregí con `file_api action=edit` antes de decir que está lista.

### 5. Abrir y contar
```
file_manager action=open path='~/Desktop/ERIS_web/clases/<archivo>.html'
```
Decile dónde quedó, cuántas escenas tiene y que se navega con ← →.

## PITFALLS

- **No dejes la clase en un solo slide**: el valor está en la secuencia + el quiz.
- **El quiz tiene que corregir de verdad**: no un "quiz" decorativo sin lógica JS.
- **Nada de librerías locales ni build**: KaTeX/Three.js por CDN y avisá que
  necesita internet. Si el tema no necesita fórmulas ni 3D, no cargues nada.
- **Rutas portables**: `~/Desktop/ERIS_web/clases`, nunca `C:\Users\...`.
- **Un archivo por clase**, con timestamp para no pisar la anterior.
- **No confundir con la skill `animacion-html`**: esa hace una animación/explicador
  visual suelto; esta arma una **clase con estructura, navegación y evaluación**.
