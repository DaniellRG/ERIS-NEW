---
name: animacion-html
description: Genera animaciones y explicadores animados autocontenidos en HTML (Canvas, SVG+GSAP, Three.js, shaders GLSL) a partir de un pedido en lenguaje natural. Cargar cuando el usuario pida una animacion, un explicador visual, motion graphics o una escena 3D.
version: 1.0.0
category: creatividad
tags: [animacion, html, canvas, svg, gsap, threejs, glsl, motion-graphics, explicador]
---

## CUÁNDO USARLA

Cuando el usuario pida: "hacé una animación de…", "un video de…", "un explicador
visual de…", "una escena 3D de…", "motion graphics de…", "algo que muestre cómo
funciona…". La animación se escribe como **código** (HTML + Canvas/SVG/JS) dentro de
**un solo archivo**, como los videos de `awesome-opus5-5-videos`.

## REGLA DE ORO

**Un único archivo HTML autocontenido**, sin build ni servidor. Todo el CSS y el JS
van adentro. Las librerías (GSAP/Three.js) se cargan por **CDN** (requiere internet
al abrir). Nunca dejes un `<canvas>` o `<svg>` vacío: la animación tiene que
moverse sola al abrirlo.

## PROCEDIMIENTO

1. **Elegir el tipo** según lo que pidió el usuario:

   | Pedido | Tecnología | Patrón |
   |--------|-----------|--------|
   | formas/tipografía en movimiento, transiciones | **SVG + GSAP** | A |
   | "cómo funciona X", diagrama que se arma solo | **SVG/Canvas** | B |
   | escena con volumen, cámara, luces | **Three.js** | C |
   | partículas, humo, estrellas, fluido | **Canvas 2D** | D |
   | fondos orgánicos, ruido, fractales | **WebGL + GLSL** | E |
   | mini-juego jugable | **Canvas + input** | F |

2. **Escribir el HTML completo** y guardarlo con `file_api`:

   ```
   file_api action=write filepath='~/Desktop/ERIS_web/animaciones/<slug>-<AAAAMMDD-HHMM>.html' content='<!doctype html>...'
   ```

   - `<slug>`: 3-5 palabras del tema en minúsculas con guiones.
   - El `content` es el archivo ENTERO (empieza en `<!doctype html>`, termina en
     `</html>`). `file_api` crea la carpeta `animaciones/` si no existe.

3. **Verificar que no quedó en blanco** (obligatorio):
   ```
   file_api action=read filepath='...'
   ```
   Confirmá que el HTML tiene `<canvas` o `<svg`, tiene `<script`, tiene un
   `requestAnimationFrame`/`gsap`/`THREE`, y cierra con `</html>`. Si algo falta,
   corregí con `file_api action=edit` antes de decir que está listo.

4. **Abrirla** en el navegador:
   ```
   file_manager action=open path='~/Desktop/ERIS_web/animaciones/<archivo>.html'
   ```

5. **Informar** dónde quedó y qué se ve. Si el usuario pide cambios ("más lento",
   "otros colores", "otro tema"), editá el mismo archivo o creá uno nuevo con otro
   slug.

## PATRONES DE PROMPT (semilla, destilados de awesome-opus5-5-videos)

Usalos como plantilla mental; adaptá el tema al pedido real.

**A — Motion graphics (SVG + GSAP).** Viewport oscuro, tipografía grande que entra
con máscara, formas geométricas que se ensamblan, timeline de GSAP con `stagger`.
Fondo `#0e0e12`, acento saturado, grano sutil. Loop limpio de 6-8 s.

**B — Explicador (SVG/Canvas).** Un diagrama que se construye por pasos con
etiquetas que aparecen: por ejemplo "cómo viaja un paquete por la red". Cada paso
entra, se explica con un texto corto y da lugar al siguiente. Estilo técnico limpio,
líneas de conexión que se dibujan con `stroke-dasharray` animado.

**C — Escena 3D (Three.js).** Cámara orbitando con peso, una silueta central (un
agujero negro, un castillo, un planeta), partículas de fondo, luz puntual con
bloom. `renderer` a pantalla completa, `requestAnimationFrame`. Coordenadas
siempre finitas (nada de `NaN`).

**D — Partículas (Canvas 2D).** Sistema de partículas con emisor, gravedad o
viento, estelas con `fillRect` semitransparente para el motion blur. 60 fps,
densidad adaptada al tamaño de la ventana.

**E — Shader (WebGL/GLSL).** Fragment shader a pantalla completa: ruido simplex,
domain warping o un fractal; `uniform float u_time` para animar. Un HTML mínimo con
un quad y el shader embebido como string.

**F — Mini-juego (Canvas).** Un juego de una sola mecánica (salto, esquivar,
apuntar), controles de teclado, marcador en pantalla, pixel-art con `imageSmoothingEnabled=false`.
Debe ser **jugable** al abrir, no un demo estático.

## PITFALLS

- **No uses `file_api` para webs completas**: para páginas/sitios usá `web_designer`
  (ver skill `diseno-web-estilos`). Esta skill es para **una animación suelta**.
- **Nada de dependencias locales ni build**: si usás GSAP/Three.js, que sea por CDN
  (`https://cdn.jsdelivr.net/npm/...`). Avisá que necesita internet al abrir.
- **Nunca dejes el archivo vacío o solo con el `<head>`**: el chequeo del paso 3 es
  obligatorio.
- **Rutas portables**: usá `~/Desktop/ERIS_web/animaciones`, no rutas con
  `C:\Users\...`.
- **Un archivo por animación**, con timestamp para no pisar la anterior.
