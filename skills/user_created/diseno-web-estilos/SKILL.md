---
name: diseno-web-estilos
description: Guias de creacion de paginas web (HTML/CSS puro, React, Angular, Vue), estilos editoriales premium (Sierra & Mar), catalogo de estilos de diseno y estilo Lumina. Cargar al crear/modificar sitios web o elegir una estetica de UI.
version: 1.0.0
category: design
tags: [diseno, web, estilos, sierra-mar, lumina, react, angular, vue]
---

## CREACIÓN DE PÁGINAS WEB

Cuando el usuario pida crear una página web, landing, sitio, portfolio o dashboard:

1. **Usá SIEMPRE `web_designer`** (action=create). NUNCA uses `code_copilot` con language=html para páginas completas: genera páginas en blanco.
2. **Si el usuario da una URL de referencia** (o una web que quiera imitar), primero ejecutá `web_designer action=analyze url='...'`. Eso extrae framework (React/Angular/Vue/Next/etc.), colores, fuentes y animaciones. Después pasá esa misma URL en `reference_url` al crear para clonar el estilo.
3. **Pasá contenido REAL** en `sections`: lo que el usuario pidió, servicios, precios, testimonios, contacto. Formato: `## Sección` + bullets `- item`. Si no sabés del tema, usá el `topic` y web_designer pone contenido curado.
4. **Nunca dejar la página vacía**: siempre va con título, descripción, secciones, imágenes y animaciones.
5. **Verificá el resultado**: ejecutá `web_designer action=preview folder=...` para renderizarla y ver el screenshot. Mostrá al usuario dónde quedó y que ya está visible en el navegador.
6. Para verla en el celular: `web_designer action=serve folder=...`.

Ejemplo de flujo completo:
- `web_designer action=analyze url='https://www.whitemirrorlab.com/'`
- `web_designer action=create title='Mi Estudio' topic='estudio creativo' reference_url='https://www.whitemirrorlab.com/' sections='## Servicios\n- Diseño de marca\n- Desarrollo web'`
- `web_designer action=preview folder=...`

## CREACIÓN DE PÁGINAS WEB CON REACT

Cuando el usuario pida una página web EN REACT (o "con componentes", "JSX", "SPA", "proyecto Vite"), usá **`react_designer`**:

1. **Usá SIEMPRE `react_designer`** (action=create). Crea un proyecto Vite+React REAL y funcional: package.json, vite.config.js, index.html, src/main.jsx, src/App.jsx (con react-router), src/data.js (contenido), src/index.css y src/components/sections.jsx (componentes React por sección: Nav, Hero, Features, Gallery, Stats, Testimonials, Faq, Prices, Process, Team, About, Contact, Footer). Luego hace npm install, levanta el dev server y abre el navegador.
2. **React vs HTML**: si el usuario pide "React", NO uses `web_designer` (genera HTML plano). Usá `react_designer`. Si pidió una web normal sin especificar framework, usá `web_designer`. Si dio una URL de referencia que es React (verificá con `web_designer action=analyze url='...'`, el campo framework lo dice), usá `react_designer`.
3. **Variedad anti-repetición**: `react_designer` comparte la memoria de diseño con `web_designer`, así que cada proyecto usa paleta/fuente/layout/fondo/animaciones distintas a las anteriores (nunca repetir el mismo diseño).
4. **Multi-página**: para negocios (veterinaria, restaurant, gym, salón, etc.) usá `pages=site` → genera 5 páginas navegables (Inicio, Servicios, Nosotros, Galería, Contacto) con react-router. Para una sola página usá `pages=single` o no pases el parámetro.
5. **Verificá el resultado**: `react_designer action=preview folder=...` renderiza la app con Playwright y saca screenshots de cada página. Mostrá al usuario la carpeta y la URL del dev server (http://127.0.0.1:5173).
6. Otras acciones: `install` (npm install), `dev` (levantar Vite), `build` (compilar a dist/), `stop`, `memory`.

Ejemplo de flujo completo:
- `react_designer action=create title='Vet Patitas' topic='veterinaria' pages=site folder='C:\Users\danie\Desktop\ERIS_web\react-vet'`
- `react_designer action=preview folder=...`

## CREACIÓN DE PÁGINAS WEB CON ANGULAR

Cuando el usuario pida una página web EN ANGULAR (o "components de TypeScript", "TypeScript Angular", "SPA Angular"), usá **`angular_designer`**:

1. **Usá SIEMPRE `angular_designer`** (action=create). Crea un proyecto Angular 20 standalone REAL y funcional: package.json, angular.json, tsconfig.json, src/index.html, src/main.ts, src/styles.css y src/app/ con componentes standalone por sección (Nav, Hero, Features, Gallery, Stats, Testimonials, Faq, Prices, Process, Team, About, Contact), directivas reveal/count-up, routing y src/app/data.ts con el contenido. Luego hace npm install, levanta `ng serve` en el puerto 4200 y abre el navegador.
2. **Framework correcto**: si el usuario pide "Angular" o "TypeScript", usá `angular_designer` (NO `web_designer` que da HTML plano, NO `react_designer`). Si pidió "React" usá `react_designer`. Si pidió una web normal sin framework, usá `web_designer`. Si dio una URL de referencia, verificá el framework con `web_designer action=analyze url='...'` y elegí la herramienta acorde (React → react_designer, Angular → angular_designer).
3. **Variedad anti-repetición**: `angular_designer` comparte la memoria de diseño, así que cada proyecto usa paleta/fuente/layout/fondo/animaciones distintas a las anteriores.
4. **Multi-página**: para negocios usá `pages=site` → 5 páginas navegables (Inicio, Servicios, Nosotros, Galería, Contacto). Para una sola página usá `pages=single`.
5. **Verificá el resultado**: `angular_designer action=preview folder=...` renderiza la app con Playwright y saca screenshots de cada página. La URL del dev server es http://127.0.0.1:4200.
6. Otras acciones: `install`, `dev`, `build` (compila a dist/), `stop`, `memory`.

Ejemplo de flujo completo:
- `angular_designer action=create title='Vet Patitas' topic='veterinaria' pages=site folder='C:\Users\danie\Desktop\ERIS_web\angular-vet'`
- `angular_designer action=preview folder=...`

## CREACIÓN DE PÁGINAS WEB CON VUE

Cuando el usuario pida una página web EN VUE (o "Vue 3", "composition API", "SPA Vue"), usá **`vue_designer`**:

1. **Usá SIEMPRE `vue_designer`** (action=create). Crea un proyecto Vue 3 + Vite REAL y funcional: package.json, vite.config.js, index.html, src/main.js (con directivas globales reveal y count-up), src/router.js (vue-router), src/data.js, src/styles.css y src/components/ con componentes .vue (Nav, Footer, y Section.vue que renderiza Hero, Features, Gallery, Stats, Testimonials, Faq, Prices, Process, Team, About, Contact). Luego hace npm install, levanta el dev server en el puerto 5174 y abre el navegador.
2. **Framework correcto**: si el usuario pide "Vue", usá `vue_designer` (NO `web_designer`, `react_designer` ni `angular_designer`). Si pidió "React" usá `react_designer`; "Angular" o "TypeScript" usá `angular_designer`; una web normal sin framework usá `web_designer`. Si dio una URL de referencia, verificá el framework con `web_designer action=analyze url='...'` y elegí la herramienta acorde (React → react_designer, Angular → angular_designer, Vue → vue_designer).
3. **Variedad anti-repetición**: `vue_designer` comparte la memoria de diseño, así que cada proyecto usa paleta/fuente/layout/fondo/animaciones distintas a las anteriores.
4. **Multi-página**: para negocios usá `pages=site` → 5 páginas navegables (Inicio, Servicios, Nosotros, Galería, Contacto). Para una sola página usá `pages=single`.
5. **Verificá el resultado**: `vue_designer action=preview folder=...` renderiza la app con Playwright y saca screenshots de cada página. La URL del dev server es http://127.0.0.1:5174.
6. Otras acciones: `install`, `dev`, `build` (compila a dist/), `stop`, `memory`.

Ejemplo de flujo completo:
- `vue_designer action=create title='Vet Patitas' topic='veterinaria' pages=site folder='C:\Users\danie\Desktop\ERIS_web\vue-vet'`
- `vue_designer action=preview folder=...`

## ESTILO EDITORIAL PREMIUM (SIERRA & MAR)

ERIS conoce un estilo de diseño de alta calidad llamado **editorial premium** (referencia: `actions/data/reference_pages/sierra_mar.html`, una veterinaria de Santa Marta con estética de revista). Características:

- **Paleta `ocean-sand`**: fondo arena claro `#FBF7EC`/`#F3EAD6`, tinta `#1C2621`, verde océano `#0E3B36`/`#092A26`, mango `#E38A34`/`#B76321`, selva `#3F6B4F`. Es un look claro, cálido y costero (NO oscuro).
- **Tipografías**: Fraunces (serif editorial para títulos), Inter (cuerpo), Space Mono (etiquetas/eyebrows en mayúsculas).
- **Detalles del estilo**: eyebrow en monoespaciada con línea, h1 con itálica de acento, grillas finas con bordes de 1px, tarjetas de servicios con iconos SVG de trazo fino, sección tipo "notas/diario" sobre fondo océano con citas en serif itálica, equipo con avatares iniciales, franja de emergencia en mango, layout editorial y generoso espaciado vertical.

**CUÁNDO USARLO**: cuando el usuario pida "una página como Sierra & Mar", "estilo editorial premium", "de revista", "artesanal de autor", "boutique", "alta cocina", "premium de lujo", o mencione palabras como editorial/premium/artesanal/boutique en el tema. Las 4 herramientas (`web_designer`, `react_designer`, `angular_designer`, `vue_designer`) ya saben aplicar `ocean-sand` + Fraunces automáticamente cuando el `topic` contiene esas palabras. Si el usuario lo pide explícitamente ("igual a Sierra & Mar"), pasá también el contenido real del negocio en `sections` y usá `pages=site`.

Ejemplo:
- `web_designer action=create title='Casa del Pan' topic='panaderia artesanal premium de autor' pages=site folder='C:\Users\danie\Desktop\ERIS_web\html-pan'`
- `react_designer action=create title='Casa del Pan' topic='panaderia premium editorial' pages=site folder='C:\Users\danie\Desktop\ERIS_web\react-pan'`

## CATÁLOGO DE ESTILOS DE DISEÑO

ERIS maneja un catálogo completo de estilos visuales que puede producir con las 4 herramientas web. Cuando el usuario pida un estilo por nombre, usá la paleta correspondiente (el sistema ya la selecciona sola con keywords en el `topic`):

- **Minimalista / editorial**: mucho espacio en blanco, tipografía grande, pocos colores → `studio-cream`, Fraunces/Inter. Keywords: minimal, revista.
- **Editorial premium / revista** (estilo Sierra & Mar): → `ocean-sand` + Fraunces + Space Mono. Keywords: editorial, premium, artesanal, boutique, de autor, alta cocina.
- **Corporativo / SaaS**: secciones de features, pricing, testimonios, CTA → `cyan-deep` o `studio-black`. Keywords: corporativo, saas, producto, landing, software.
- **Brutalista / broadsheet**: bordes duros, serif de alto contraste, retículas de periódico, sin redondeos → `studio-cream`. Keywords: brutalista, broadsheet, periódico, newspaper.
- **Dark / tech**: fondo casi negro, acento brillante único → `retro-terminal` o `cyan-deep`. Keywords: dark, hacker, terminal, devtools, tecnológico.
- **Cálido / artesanal**: paletas tierra, tipografía con personalidad, negocios locales → `ocean-sand`, `amber-warm`, `rose-gold`. Keywords: artesanal, local, familiar.
- **E-commerce / catálogo**: grillas de producto, filtros, carrito → `amber-warm` o `sky`. Keywords: ecommerce, tienda online, catálogo, shop.
- **Dashboard / datos**: métricas, tablas, gráficos → `retro-terminal` o `cyan-deep`. Keywords: dashboard, analytics, métricas, reporte, informes.
- **Portafolio creativo / experimental**: animaciones, scroll interactivo, tipografía protagonista → `violet-neon`. Keywords: portafolio, portfolio, creativo, artista, fotógrafo, músico.
- **Documentación / wiki**: sidebar, contenido denso y legible → `sky`. Keywords: documentación, wiki, manual, guía, tutoriales.
- **Evento / campaña**: hero llamativo, countdown, registro → `ruby`. Keywords: evento, campaña, concierto, festival, lanzamiento, feria.

Regla: si el usuario pide un estilo POR NOMBRE, priorizalo por encima del tema. Si pide solo por tema, ERIS elige según el mapeo automático.

**CÓMO FORZAR UN ESTILO**: las 4 herramientas aceptan el parámetro `design_style=ESTILO` que vence a la variedad automática. Usalo SIEMPRE que el usuario nombre un estilo explícitamente:
- `web_designer ... design_style='editorial'`, `react_designer ... design_style='dark'`, etc.
Estilos disponibles: editorial, minimal, brutalista, broadsheet, corporativo, saas, dark, tech, dashboard, ecommerce, artesanal, portafolio, creativo, evento, documentacion, vet, lumina, natural, tierno, medico, futurista, colorido.

Ejemplo:
- `react_designer action=create title='Vet Amanecer' topic='veterinaria premium' design_style='editorial' pages=site folder='C:\Users\danie\Desktop\ERIS_web\react-vet'`

## ESTILO LÚMINA (PREMIUM-NATURAL)

ERIS también conoce el estilo **Lúmina** (veterinaria premium, verde oscuro + lima + crema, referencias `actions/data/reference_pages/`). Características:

- **Paleta `lumina`**: fondo crema `#F7F5EF`, tinta verde oscuro `#17352D`, lima oscuro `#879B2C`, lima brillante `#D8F27B`. Look claro, natural y elegante (NO oscuro).
- **Tipografías**: Playfair Display (serif editorial para títulos), DM Sans (cuerpo).
- **Detalles**: hero con grande tipografía serif e itálica de acento, esfera/orb decorativo, tarjetas de servicios redondeadas con hover que eleva, franja de confianza en verde oscuro, equipo con avatares, sección de filosofía de dos columnas, testimonio sobre verde oscuro, formulario de citas, responsive.
- **Variantes de estilo** que ERIS mapea a paletas existentes: premium (ocean-sand), natural-moderno (lumina), tierno-amigable (rose-gold), dark-futurista (indigo-twilight), profesional-médico (sky), colorido-juvenil (magenta).

**CUÁNDO USARLO**: cuando el usuario pida "como Lúmina Vet", "estilo Lúmina", "veterinaria premium-natural", "verde lima", o mencione premium-natural/sostenible moderno. Forzable con `design_style='lumina'` o `design_style='natural'`.
