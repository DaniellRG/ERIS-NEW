## GUÍA DE HERRAMIENTAS WEB — SABÉ CUÁL USAR

### REGLA #1: NO uses Google en el navegador — está BLOQUEADO (CAPTCHA).
Usá SIEMPRE DuckDuckGo para buscar en el navegador: `https://duckduckgo.com/?q=...`

### REGLA #2: Para búsquedas rápidas, usá `web_search` (sin abrir navegador).

### Para BUSCAR información (la más usada):
- **`web_search`** → Búsqueda rápida API (DuckDuckGo). Sin navegador, sin CAPTCHA.
  - `web_search action=search query="qué buscar"`
  - `web_search action=news query="noticias de hoy"`
  - CUÁNDO: "busca", "googlea", "qué es", "información sobre", "noticias de"

### Para NAVEGAR + BUSCAR en el navegador (visible):
- **`browser_unified`** → Browser Playwright VISIBLE. Abrí, buscá, navegá, leé.
  - **BUSCAR:** `browser_unified action=navigate url="https://duckduckgo.com/?q=tu+busqueda"`
  - **LEER:** `browser_unified action=text`
  - **CLICKEAR:** `browser_unified action=click selector="a.result__a"`
  - **SCROLL:** `browser_unified action=scroll direction=down`
  - **SCREENSHOT:** `browser_unified action=screenshot`
  - CUÁNDO: "abrir el navegador y buscar", "navegá a...", "entrá a la página", "hacé screenshot"

### Para REPRODUCIR VIDEOS (YouTube):
- **`browser_unified`** con action `play` → Busca y reproduce en YouTube.
  - `browser_unified action=play query="nombre del video"` → Busca en YouTube y reproduce el primero
  - `browser_unified action=play url="https://youtube.com/watch?v=..."` → Reproduce URL directa
  - CUÁNDO: "poné un video de X", "reproducí", "buscá video de", "poné música"

### Para RESUMIR una página o video:
- **`page_summarizer`** → Resume cualquier URL (páginas, YouTube, etc.)
  - `page_summarizer url="https://..." max_chars=500`
  - CUÁNDO: "resumí esta página", "qué dice este video"

### Para INVESTIGACIÓN profunda:
- **`deep_research`** → Busca + entra a cada página + analiza con IA
  - `deep_research query="tema a investigar" depth=3`
  - CUÁNDO: "investigá a fondo sobre X", "haceme una investigación completa"

### Para FETCH rápido de contenido:
- **`webfetch`** → Descarga contenido de una URL (sin browser)
  - `webfetch url="https://..." format="markdown"`
  - CUÁNDO: "traeme el contenido de esta URL"

### NO USAR (confusión):
- `browser_control` → FRÁGIL (pyautogui + coordenadas). NO USAR.
- `browser_auto` → DUPLICADO. NO USAR.
- `smart_browser` → Solo HTTP (no browser real). NO USAR.
- `search_info` → DUPLICADO de web_search. NO USAR.

