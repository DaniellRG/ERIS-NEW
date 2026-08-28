"""
actions/web_designer.py — Diseñador web completo para ERIS.

Flujo de trabajo (entrenado en prompt.txt):
  1. ANALIZAR referencia:  action=analyze url=https://...  → extrae framework
     (React/Vue/Angular/Next/WordPress/plain), paleta de colores, fuentes,
     secciones, animaciones y estilo. Si el sitio es una SPA (JS), lo renderiza
     con Playwright (Edge/Chrome) para extraer el HTML real.
  2. CREAR página:          action=create title= topic= reference_url=
                           sections="..." folder= images=  → genera un
     index.html autocontenido (HTML+CSS+JS en un solo archivo), con contenido
     real, imágenes (picsum + fallback SVG offline), animaciones y el lenguaje
     de diseño clonado de la referencia. Lo abre en el navegador.
  3. PREVIEW:               action=preview folder=  → renderiza la página con
     Playwright y guarda preview.png para que ERIS la "vea".
  4. SERVE:                 action=serve folder= port=  → servidor local
     http://127.0.0.1:puerto para verla en el móvil o por red.

Todo es autocontenido: la página generada NO depende de archivos externos
(a excepción de Google Fonts y picsum, que tienen fallback offline).
"""
import json
import os
import re
import random
import subprocess
import time
import uuid
import webbrowser
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

_BASE_DIR = Path(__file__).resolve().parent.parent
_MEMORY_FILE = _BASE_DIR / "data" / "web_designer_memory.json"
_DEFAULT_OUT = Path.home() / "Desktop" / "ERIS_web"

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
}

# ──────────────────────────────────────────────────────────────────────
#  PALETAS Y FUENTES (igual lenguaje visual que web_generator)
# ──────────────────────────────────────────────────────────────────────
PALETTES = [
    {"bg": "#0a0a0f", "fg": "#e0e0e0", "primary": "#7c3aed", "secondary": "#6366f1", "accent": "#f472b6", "name": "purple-cosmic"},
    {"bg": "#0f172a", "fg": "#e2e8f0", "primary": "#06b6d4", "secondary": "#0891b2", "accent": "#2dd4bf", "name": "cyan-deep"},
    {"bg": "#1c1917", "fg": "#fafafa", "primary": "#f59e0b", "secondary": "#f97316", "accent": "#ef4444", "name": "amber-warm"},
    {"bg": "#0f1a14", "fg": "#d1fae5", "primary": "#10b981", "secondary": "#059669", "accent": "#34d399", "name": "emerald-forest"},
    {"bg": "#130a0f", "fg": "#fce7f3", "primary": "#ec4899", "secondary": "#db2777", "accent": "#f43f5e", "name": "pink-rose"},
    {"bg": "#0a0f1a", "fg": "#dbeafe", "primary": "#3b82f6", "secondary": "#2563eb", "accent": "#60a5fa", "name": "blue-ocean"},
    {"bg": "#0f0a1a", "fg": "#f3e8ff", "primary": "#a855f7", "secondary": "#d946ef", "accent": "#e879f9", "name": "violet-neon"},
    {"bg": "#1a0f0a", "fg": "#fff7ed", "primary": "#f97316", "secondary": "#dc2626", "accent": "#fbbf24", "name": "sunset"},
    {"bg": "#0a1412", "fg": "#ccfbf1", "primary": "#14b8a6", "secondary": "#0d9488", "accent": "#5eead4", "name": "teal-aurora"},
    {"bg": "#0a0a14", "fg": "#ede9fe", "primary": "#8b5cf6", "secondary": "#a78bfa", "accent": "#c4b5fd", "name": "indigo-twilight"},
    {"bg": "#140a0c", "fg": "#ffe4e6", "primary": "#e11d48", "secondary": "#be123c", "accent": "#fb7185", "name": "ruby"},
    {"bg": "#0a121a", "fg": "#e0f2fe", "primary": "#0ea5e9", "secondary": "#0284c7", "accent": "#7dd3fc", "name": "sky"},
    {"bg": "#0e130a", "fg": "#ecfccb", "primary": "#84cc16", "secondary": "#65a30d", "accent": "#a3e635", "name": "lime"},
    {"bg": "#100a12", "fg": "#fae8ff", "primary": "#d946ef", "secondary": "#c026d3", "accent": "#f0abfc", "name": "magenta"},
    {"bg": "#120a0b", "fg": "#ffe4e6", "primary": "#f43f5e", "secondary": "#e11d48", "accent": "#fb7185", "name": "crimson"},
    # Estilos "de agencia creativa" (tipo whitemirrorlab)
    {"bg": "#050505", "fg": "#f2f2f2", "primary": "#ffffff", "secondary": "#a0a0a0", "accent": "#ff3d3d", "name": "studio-black"},
    {"bg": "#f4f1ec", "fg": "#16130f", "primary": "#16130f", "secondary": "#6b6459", "accent": "#c8522e", "name": "studio-cream"},
    {"bg": "#0b0e14", "fg": "#e8ecf2", "primary": "#7cf2b0", "secondary": "#3ea5ff", "accent": "#ffb454", "name": "retro-terminal"},
    {"bg": "#faf6f1", "fg": "#33241f", "primary": "#b76e79", "secondary": "#a2545f", "accent": "#c8522e", "name": "rose-gold"},
    # Estilo editorial premium "Sierra & Mar" (océano / arena / mango)
    {"bg": "#FBF7EC", "fg": "#1C2621", "primary": "#0E3B36", "secondary": "#B76321", "accent": "#E38A34", "name": "ocean-sand"},
    # Estilo "Lúmina Vet" premium-natural (verde oscuro / lima / crema)
    {"bg": "#F7F5EF", "fg": "#17352D", "primary": "#17352D", "secondary": "#879B2C", "accent": "#D8F27B", "name": "lumina"},
]
FONTS = [
    ("Inter", "Inter:ital,opsz,wght@0,14..32,100..900"),
    ("Poppins", "Poppins:wght@300;400;600;700;800"),
    ("Space Grotesk", "Space+Grotesk:wght@300;400;500;700"),
    ("Outfit", "Outfit:wght@200;300;400;600;700;800"),
    ("DM Sans", "DM+Sans:ital,opsz,wght@0,9..40,100..1000"),
    ("Plus Jakarta Sans", "Plus+Jakarta+Sans:wght@200;300;400;500;600;700;800"),
    ("Sora", "Sora:wght@100;200;300;400;600;700;800"),
    ("Syne", "Syne:wght@400;500;600;700;800"),
    ("Epilogue", "Epilogue:ital,wght@0,100..900"),
    ("Manrope", "Manrope:wght@200;300;400;500;600;700;800"),
    ("Clash Display", "Clash+Display:wght@200;300;400;500;600;700"),
    ("Cormorant Garamond", "Cormorant+Garamond:wght@400;500;600;700"),
    ("Fraunces", "Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,500;0,9..144,600;1,9..144,400;1,9..144,500"),
    ("Space Mono", "Space+Mono:wght@400;700"),
    ("Playfair Display", "Playfair+Display:ital,wght@0,600;0,700;1,600"),
]

# ── Curated content por categoría (fallback cuando ERIS no da texto real) ──
CONTENT_BUNDLES = {
    "tech": ("Innovación digital", "Producto", "Somos un equipo que construye tecnología con propósito.",
             ["Plataforma cloud", "IA aplicada", "Ciberseguridad"], ["Escalable", "Seguro", "Rápido"]),
    "studio": ("Estudio creativo", "Trabajo", "Diseñamos experiencias que dejan huella.",
               ["Identidad de marca", "Diseño web", "Motion"], ["Audaces", "Precisos", "Memorables"]),
    "food": ("Gastronomía", "Platos", "Sabores auténticos con ingredientes de primera.",
             ["Recetas propias", "Ingredientes frescos", "Chef invitado"], ["Fresco", "Local", "Artesanal"]),
    "fitness": ("Entrenamiento", "Rutinas", "Tu mejor versión empieza hoy.",
                ["Personal trainer", "Nutrición", "Clases grupales"], ["Fuerza", "Disciplina", "Resultados"]),
    "art": ("Galería", "Obras", "El arte como forma de diálogo.",
            ["Curaduría", "Talleres", "Exposiciones"], ["Vanguardista", "Íntimo", "Inquietante"]),
    "travel": ("Viajes", "Destinos", "Rutas que transforman tu forma de ver el mundo.",
               ["Ecoturismo", "Guías locales", "Rutas únicas"], ["Aventura", "Auténtico", "Sostenible"]),
    "photo": ("Fotografía", "Sesiones", "Momentos que se vuelven eternos.",
              ["Retrato", "Eventos", "Editorial"], ["Natural", "Sensible", "Atemporal"]),
    "music": ("Música", "Sesiones", "Sonido que conecta almas.",
              ["Producción", "Conciertos", "Clases"], ["Vivo", "Íntimo", "Enérgico"]),
    "architecture": ("Arquitectura", "Proyectos", "Espacios que respiran.",
                     ["Diseño", "Planos 3D", "Interiores"], ["Puro", "Funcional", "Luminoso"]),
    "nature": ("Naturaleza", "Especies", "Verde que transforma espacios.",
               ["Plantas únicas", "Riego inteligente", "Asesoría"], ["Vivo", "Orgánico", "Renovable"]),
    "books": ("Librería", "Colección", "Historias que esperan ser leídas.",
              ["Club de lectura", "Café literario", "Book box"], ["Curado", "Acogedor", "Inquieto"]),
    "fashion": ("Moda", "Colección", "Estilo con conciencia.",
                ["Diseño propio", "Materiales éticos", "A medida"], ["Elegante", "Sostenible", "Único"]),
    "salon": ("Peluquería y belleza", "Servicios", "Realzamos tu estilo natural con técnicas y productos de primera.",
              ["Corte y peinado", "Color y mechas", "Tratamientos capilares", "Barbería", "Manicura"], ["Elegante", "Renovador", "Personal"]),
    "vet": ("Veterinaria", "Mascotas", "Cuidamos a tu mascota con medicina preventiva y de avanzada.",
            ["Consultas", "Vacunación", "Cirugía", "Estética", "Emergencias 24h"], ["Cercano", "Profesional", "Confiable"]),
    "restaurant": ("Restaurante", "Platos", "Cocina de autor con productos de estación.",
                   ["Menú degustación", "Vinos", "Postres"], ["Estacional", "Creativo", "Acompañado"]),
    "gym": ("Gimnasio", "Entrenamiento", "Entrená fuerte, viví mejor.",
            ["Crossfit", "Yoga", "Nutrición"], ["Intenso", "Comunidad", "Resultados"]),
}

# ── Variedad de diseño: ERIS siempre elige combinaciones nuevas ──────────
# Cada creación combina layout + paleta + fuente + fondo + animaciones.
# _avoid_recent() descarta lo ya usado en las últimas N páginas para que
# cada página nueva sea distinta a las anteriores.
LAYOUTS = ["centered", "split", "editorial", "compact"]
ANIM_SETS = [
    ["reveal"],
    ["reveal", "particles"],
    ["reveal", "marquee"],
    ["reveal", "float"],
    ["reveal", "blob"],
    ["reveal", "kenburns"],
    ["reveal", "tilt"],
    ["reveal", "parallax", "marquee"],
    ["reveal", "blob", "particles"],
]
BG_STYLES = ["grid", "blobs", "mesh", "dots", "rings", "aurora"]

# páginas que conforman un sitio multi-página (menú navegable)
SITE_PAGES = [
    ("index", "Inicio"),
    ("servicios", "Servicios"),
    ("nosotros", "Nosotros"),
    ("galeria", "Galería"),
    ("contacto", "Contacto"),
]

# ──────────────────────────────────────────────────────────────────────
#  MEMORIA
# ──────────────────────────────────────────────────────────────────────
def _load_memory():
    try:
        _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _MEMORY_FILE.exists():
            data = json.loads(_MEMORY_FILE.read_text("utf-8"))
            data.setdefault("pages_created", 0)
            data.setdefault("history", [])
            data.setdefault("analyzed_urls", [])
            return data
    except Exception:
        pass
    return {"pages_created": 0, "history": [], "analyzed_urls": []}


def _avoid_recent(memory, key, pool, window=5):
    """Elige un elemento del pool evitando los usados recientemente (aprendizaje)."""
    if not pool:
        return None
    used = [u for u in memory.get(key, []) if isinstance(u, dict)]
    recent = {str(u.get("value")) for u in used[-window:]}
    if isinstance(pool, dict):
        cand = [k for k in pool if k not in recent]
        choice = random.choice(cand) if cand else random.choice(list(pool))
        return pool[choice], choice
    cand = [c for c in pool if str(c) not in recent]
    return random.choice(cand) if cand else random.choice(pool)


def _save_memory(data):
    try:
        _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────
#  ANALIZADOR DE REFERENCIA
# ──────────────────────────────────────────────────────────────────────
_FW_SIGNALS = [
    (r"__next_f|/_next/static", "nextjs"),
    (r"data-reactroot|__reactFiber|react-dom|data-reactid", "react"),
    (r"id=[\"']app[\"']|__VUE__|data-v-[a-f0-9]|vue\.runtime|@vue", "vue"),
    (r"_ngcontent|ng-version|angular\.js|@angular", "angular"),
    (r"svelte\.mjs|__svelte|data-svelte", "svelte"),
    (r"astro-|is:inline", "astro"),
    (r"wp-content|wp-includes|wp-admin", "wordpress"),
    (r"cdn\.shopify\.com|myshopify\.com", "shopify"),
    (r"gatsby", "gatsby"),
    (r"nuxt|__nuxt", "nuxt"),
]
_ANIM_SIGNALS = {
    "aos": r"data-aos|aos\.js",
    "gsap": r"gsap|ScrollTrigger",
    "three": r"three(\.min)?\.js|THREE\.",
    "swiper": r"swiper|Swiper",
    "animate.css": r"animate__|animate\.min\.css",
    "lenis": r"lenis",
    "locomotive": r"locomotive-scroll",
}


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return None


def _is_dark(bg):
    rgb = _hex_to_rgb(bg)
    if not rgb:
        return True
    r, g, b = rgb
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return lum < 0.55


def _color_score(rgb):
    """Ordena colores: descarta casi-negros/casi-blancos y grises de fondo."""
    r, g, b = rgb
    maxc, minc = max(rgb), min(rgb)
    sat = (maxc - minc) / max(maxc, 1)
    if sat < 0.25:
        return 0.05  # gris / borde
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum < 35 or lum > 225:
        return 0.3  # fondo oscuro/claro
    return 1.0


def _extract_colors(css):
    colors = []
    for m in re.finditer(r"#[0-9a-fA-F]{3,8}\b", css):
        colors.append(m.group(0))
    for m in re.finditer(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", css):
        colors.append("#{:02x}{:02x}{:02x}".format(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    scored = []
    for c in colors:
        rgb = _hex_to_rgb(c)
        if not rgb:
            continue
        scored.append((_color_score(rgb), c))
    scored.sort(reverse=True)
    palette = [c for s, c in scored if s > 0.5][:6]
    return palette


def _extract_fonts(css):
    fonts = []
    for m in re.finditer(r"font-family\s*:\s*([^;}]+)", css, re.I):
        names = [p.strip().strip("'\"") for p in m.group(1).split(",")]
        if names:
            fonts.append(names[0])
    counts = Counter(fonts)
    top = []
    for f, _ in counts.most_common(6):
        if f in ("sans-serif", "serif", "monospace", "inherit", "initial", "none"):
            continue
        if f.startswith(("var(", "-webkit-", "-moz-", "apple-")) or f.startswith("--"):
            continue
        if not any(ch.isalpha() for ch in f):
            continue
        top.append(f)
    return top[:4]


def _extract_style_flags(css):
    flags = {}
    flags["glass"] = bool(re.search(r"backdrop-filter|backdrop_filter", css))
    flags["gradient_text"] = bool(re.search(r"background-clip:\s*text|background-clip:text", css))
    radii = [int(r) for r in re.findall(r"border-radius\s*:\s*(\d+)px", css) if int(r) <= 60]
    flags["radius"] = str(Counter(radii).most_common(1)[0][0]) + "px" if radii else "8px"
    flags["dark"] = css.count("background:#0") > 2 or css.count("background: #0") > 2
    return flags


def _extract_animations(css):
    found = []
    if re.search(r"@keyframes", css):
        found.append("css-keyframes")
    anim = {}
    for name, pat in _ANIM_SIGNALS.items():
        anim[name] = bool(re.search(pat, css, re.I))
    if anim.get("aos"):
        found.append("scroll-reveal")
    if anim.get("gsap"):
        found.append("gsap-scroll")
    if anim.get("three"):
        found.append("three-3d")
    if anim.get("swiper"):
        found.append("slider")
    return found


def _detect_framework(html):
    low = html.lower()
    for pat, name in _FW_SIGNALS:
        if re.search(pat, low):
            return name
    return "html-plain"


def _sections_from_html(soup):
    sections = []
    for h in soup.find_all(["h1", "h2"], limit=16):
        txt = h.get_text(" ", strip=True)
        if txt:
            sections.append((h.name, txt[:60]))
    if not sections:
        return []
    # dedupe preservando orden
    seen, out = set(), []
    for tag, txt in sections:
        if txt not in seen:
            seen.add(txt)
            out.append([tag, txt])
    return out


def _fetch_static(url):
    resp = requests.get(url, headers=_HEADERS, timeout=20, allow_redirects=True)
    resp.raise_for_status()
    return resp.text, resp.url


def _render_js(url):
    """Renderiza la página en un navegador real (Edge/Chrome) para SPAs."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        pg = browser.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(url, wait_until="networkidle", timeout=45000)
        pg.wait_for_timeout(2500)
        html = pg.content()
        css = pg.evaluate(
            "() => Array.from(document.styleSheets).map(s => {"
            "  try { return [...s.cssRules].map(r => r.cssText).join('\\n'); }"
            "  catch(e) { return ''; } }).join('\\n')"
        )
        browser.close()
    return html, css


def _analyze_reference(url):
    """Extrae un brief de diseño del sitio de referencia."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    raw_html = None
    rendered = False
    try:
        html, final = _fetch_static(url)
    except Exception as e:
        return {"error": "No se pudo acceder a {}: {}".format(url, str(e)[:150])}

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else final
    framework = _detect_framework(html)
    text_len = len(soup.get_text(" ", strip=True))

    css_parts = []
    for st in soup.find_all("style"):
        css_parts.append(st.get_text())
    for link in soup.find_all("link", rel=lambda v: v and "stylesheet" in v):
        href = link.get("href")
        if href:
            try:
                css_parts.append(requests.get(urljoin(final, href), headers=_HEADERS, timeout=10).text)
            except Exception:
                pass

    # Si el HTML estático está casi vacío → SPA: renderizar con navegador real
    if text_len < 200 or framework != "html-plain":
        try:
            html_js, css_js = _render_js(final)
            if len(BeautifulSoup(html_js, "html.parser").get_text(" ", strip=True)) > text_len:
                html, soup, css_parts, rendered = html_js, BeautifulSoup(html_js, "html.parser"), [css_js], True
                framework = _detect_framework(html)
        except Exception:
            pass

    all_css = "\n".join(css_parts)
    palette_raw = _extract_colors(all_css)
    fonts = _extract_fonts(all_css)
    flags = _extract_style_flags(all_css)
    animations = _extract_animations(all_css)
    sections = _sections_from_html(soup)
    images = len(soup.find_all("img"))

    brief = {
        "url": final,
        "title": title,
        "framework": framework,
        "rendered_with_js": rendered,
        "text_chars": max(len(soup.get_text(" ", strip=True)), text_len),
        "palette": palette_raw,
        "fonts": fonts,
        "style_flags": flags,
        "animations": animations,
        "sections": sections,
        "image_count": images,
    }
    return brief


def _format_brief(b):
    if "error" in b:
        return b["error"]
    lines = [
        "ANÁLISIS DE REFERENCIA — {}".format(b["url"]),
        "URL: {}".format(b["url"]),
        "Título: {}".format(b["title"]),
        "Framework: {} {}".format(b["framework"], "(renderizado JS)" if b.get("rendered_with_js") else ""),
        "Paleta de colores: {}".format(", ".join(b.get("palette", [])[:6]) or "no detectada"),
        "Fuentes: {}".format(", ".join(b.get("fonts", [])[:3]) or "no detectadas"),
        "Estilo: {}".format(", ".join("{}={}".format(k, v) for k, v in b.get("style_flags", {}).items())),
        "Animaciones detectadas: {}".format(", ".join(b.get("animations", [])) or "ninguna"),
        "Imágenes en la página: {}".format(b.get("image_count", 0)),
    ]
    if b.get("sections"):
        lines.append("Secciones detectadas:")
        for tag, txt in b["sections"][:12]:
            lines.append("  <{}> {}".format(tag, txt))
    lines.append("")
    lines.append("BRIEF_JSON:")
    lines.append(json.dumps(b, ensure_ascii=False))
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
#  IMÁGENES
# ──────────────────────────────────────────────────────────────────────
def _svg_placeholder(seed, w, h, c1, c2, label):
    """SVG data-URI como fallback offline: siempre renderiza algo."""
    label = label or seed
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>'
        '<rect width="{w}" height="{h}" fill="url(#g)"/>'
        '<circle cx="{w}" cy="0" r="{r}" fill="{c2}" opacity="0.35"/>'
        '<circle cx="0" cy="{h}" r="{r2}" fill="{c1}" opacity="0.35"/>'
        '<text x="50%" y="52%" font-family="Segoe UI,sans-serif" font-size="{fs}" fill="#fff" opacity="0.9" '
        'text-anchor="middle" dominant-baseline="middle">{t}</text>'
        '</svg>'
    ).format(w=w, h=h, c1=c1, c2=c2, r=int(w * 0.35), r2=int(h * 0.4),
             fs=max(16, int(min(w, h) / 9)), t=label.replace("&", "&amp;"))
    from urllib.parse import quote
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


def _img(seed, w, h, c1, c2, label):
    """Foto real de picsum con fallback SVG offline (nunca imagen rota)."""
    url = "https://picsum.photos/seed/{}/{}/{}".format(seed, w, h)
    fb = _svg_placeholder(seed, w, h, c1, c2, label)
    return ('<img src="{url}" alt="{alt}" loading="lazy" '
            'onerror="this.onerror=null;this.src=\'{fb}\';" />').format(url=url, alt=label, fb=fb)


# ──────────────────────────────────────────────────────────────────────
#  PARSER DE CONTENIDO (secciones que pasa ERIS)
# ──────────────────────────────────────────────────────────────────────
def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:30]


def _parse_sections(content, topic, desc):
    """Acepta: JSON de secciones, o texto markdown '## Título\\nTexto'."""
    if isinstance(content, dict):
        return content.get("sections") or content.get("items") or []
    if not content:
        return []
    content = str(content).strip()
    if "\\n" in content:
        content = content.replace("\\n", "\n")
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("sections") or data.get("items") or []
    except Exception:
        pass
    # markdown-lite
    out, cur = [], None
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"#{1,3}\s+(.+)", line)
        if m:
            cur = {"type": "auto", "title": m.group(1).strip(), "text": ""}
            out.append(cur)
        elif cur is not None:
            if line.startswith("- ") or line.startswith("* "):
                cur.setdefault("items", []).append(line[2:].strip())
            elif line.lower().startswith(("pregunta:", "q:")):
                cur.setdefault("items", []).append(("q", line.split(":", 1)[1].strip()))
            else:
                cur["text"] = (cur.get("text", "") + " " + line).strip()
        else:
            out.append({"type": "auto", "title": "", "text": line})
    return out


def _classify_section(sec, idx, total):
    title = (sec.get("title") or "").lower()
    stype = (sec.get("type") or "").lower()
    if stype and stype in ("hero", "subhero", "features", "gallery", "stats", "testimonials", "cta", "contact", "faq",
                           "prices", "process", "team"):
        return stype
    if idx == 0:
        return "hero"
    if any(k in title for k in ("galer", "proyecto", "portfolio", "trabajo", "obras")):
        return "gallery"
    if any(k in title for k in ("equipo", "sobre", "nosotros", "about", "studio")):
        return "about"
    if any(k in title for k in ("servicio", "caracter", "feature", "que ofrecem", "propuesta")):
        return "features"
    if any(k in title for k in ("testimonio", "opinion", "reseña", "dijeron")):
        return "testimonials"
    if any(k in title for k in ("contacto", "contact", "escribin", "hablemos")):
        return "contact"
    if any(k in title for k in ("pregunta", "faq", "duda")):
        return "faq"
    if any(k in title for k in ("cifra", "stat", "numero", "resultado")):
        return "stats"
    return "auto"


def _fallback_sections(topic, desc):
    bundle = None
    for key, (kw, _, _, _, _) in CONTENT_BUNDLES.items():
        if any(w in topic.lower() for w in kw):
            bundle = CONTENT_BUNDLES[key]
            break
    if not bundle:
        bundle = CONTENT_BUNDLES["tech"]
    _, kw, about, feats, _ = bundle[0], bundle[1], bundle[2], bundle[3], bundle[4]
    return [
        {"type": "hero", "title": topic or kw, "text": desc or about},
        {"type": "features", "title": "Lo que hacemos", "text": about, "items": list(feats)},
        {"type": "gallery", "title": "Nuestro trabajo", "text": "Algunas piezas seleccionadas.", "images": 4},
        {"type": "stats", "title": "Resultados", "items": [("120+", "Proyectos"), ("98%", "Clientes felices"), ("12", "Premios"), ("24/7", "Soporte")]},
        {"type": "testimonials", "title": "Lo que dicen", "items": [
            "Trabajar con este equipo fue transformador. Resultados impecables.",
            "Creatividad y precisión en cada entrega. Lo recomiendo sin dudar.",
            "Superaron todas las expectativas. Un placer colaborar.",
        ]},
        {"type": "contact", "title": "Hablemos", "text": "Cuéntanos tu proyecto y te respondemos rápido."},
    ]


# ──────────────────────────────────────────────────────────────────────
#  GENERADOR HTML
# ──────────────────────────────────────────────────────────────────────
def _pick_brief_palette(brief):
    """Adapta la paleta del sitio de referencia a nuestro esquema (tema oscuro garantizado)."""
    seen, cols = set(), []
    for c in (brief or {}).get("palette", []):
        if isinstance(c, str) and c.startswith("#"):
            key = c[:7].lower()
            if key not in seen:
                seen.add(key)
                cols.append(c[:7])
    if len(cols) < 2:
        return None
    return {
        "bg": "#0a0a0f",
        "fg": "#f2f2f2",
        "primary": cols[0],
        "secondary": cols[1] if len(cols) > 1 else "#888888",
        "accent": cols[2] if len(cols) > 2 else cols[0],
        "name": "reference",
    }


def _map_reference_animations(brief):
    anims = set((brief or {}).get("animations", []))
    out = []
    if "gsap-scroll" in anims or "scroll-reveal" in anims:
        out.append("reveal")
    if "three-3d" in anims:
        out.append("particles")
    if "slider" in anims:
        out.append("marquee")
    if not out:
        out.append("reveal")
    return out


# Paletas preferidas por tipo de negocio (coherencia temática, sin forzar repetir)
_TOPIC_PALETTES = (
    (("editorial", "premium", "revista", "magazine", "artesanal", "boutique", "lujo", "de autor", "print", "alta cocina", "sierra", "mar"), "ocean-sand"),
    (("lumina", "premium natural", "natural moderno", "verde lima", "sostenible moderno"), "lumina"),
    (("tierno", "amigable", "jugueton", "kawaii", "mascotas amigable"), "rose-gold"),
    (("medico", "médico", "profesional", "clinica", "consultorio", "salud"), "sky"),
    (("futurista", "futuristico", "neon", "glitch", "cyberpunk"), "indigo-twilight"),
    (("colorido", "juvenil", "divertido", "playful", "kids", "niños"), "magenta"),
    (("minimal", "minimalista", "broadsheet", "brutalista", "periodico", "periódico", "newspaper", "revista impresa"), "studio-cream"),
    (("corporativ", "saas", "producto", "landing", "startup b2b"), "cyan-deep"),
    (("dark", "hacker", "terminal", "devtools", "cyber", "tecnico", "tecnológico"), "retro-terminal"),
    (("dashboard", "analytics", "datos", "metricas", "métricas", "reporte", "informes"), "retro-terminal"),
    (("ecommerce", "tienda online", "catalogo", "catálogo", "shop", "venta online"), "amber-warm"),
    (("portafolio", "portfolio", "experimental", "creativo", "artista", "ilustrador", "fotografo", "fotógrafo", "musico", "músico"), "violet-neon"),
    (("evento", "campana", "campaña", "countdown", "concierto", "festival", "lanzamiento", "feria"), "ruby"),
    (("documentacion", "documentación", "wiki", "manual", "docs", "guia", "guía", "tutoriales"), "sky"),
    (("peluquer", "salon", "belleza", "beauty", "barber", "estetica", "spa"), "rose-gold"),
    (("studio", "agencia", "diseño", "brand", "lab", "abogad", "jurid", "legal", "banc", "finanz", "consultor", "corporat"), "studio-black"),
    (("veterin", "vet", "mascota", "perro", "gato", "animal"), "teal-aurora"),
    (("cafe", "cafeter", "coffee", "bar", "restaurant", "gastronom", "comida", "panader", "pastel", "postre"), "amber-warm"),
    (("gym", "gimnasio", "fitness", "crossfit", "entrenam", "yoga", "pilates", "deporte", "sport"), "violet-neon"),
    (("viaj", "turismo", "travel", "hotel", "vacacion", "aventur", "playa", "montana"), "sunset"),
    (("tech", "tecnologia", "software", "startup", "app", "robot", "digital", "sistemas", "ciberseguridad"), "cyan-deep"),
    (("inmobiliar", "propiedad", "real estate", "alquiler", "vivienda"), "sky"),
    (("flor", "jardin", "plant", "naturaleza", "ecolog", "sustentable", "verde", "huerta"), "emerald-forest"),
)
_TOPIC_PALETTES = tuple((tuple(words), name) for words, name in _TOPIC_PALETTES)

# ── Presets de estilo forzado (cuando el usuario pide un estilo POR NOMBRE) ──
# Se activan con el parámetro design_style= y vencen a la anti-repetición.
_STYLE_PRESETS = {
    "editorial": ("ocean-sand", "Fraunces"),
    "minimal": ("studio-cream", "Inter"),
    "brutalista": ("studio-cream", "Fraunces"),
    "broadsheet": ("studio-cream", "Fraunces"),
    "corporativo": ("cyan-deep", "Inter"),
    "saas": ("cyan-deep", "Inter"),
    "dark": ("retro-terminal", "Space Grotesk"),
    "tech": ("retro-terminal", "Space Grotesk"),
    "dashboard": ("retro-terminal", "Inter"),
    "ecommerce": ("amber-warm", "Outfit"),
    "artesanal": ("ocean-sand", "Fraunces"),
    "portafolio": ("violet-neon", "Poppins"),
    "creativo": ("violet-neon", "Poppins"),
    "evento": ("ruby", "Poppins"),
    "documentacion": ("sky", "Inter"),
    "vet": ("teal-aurora", "Outfit"),
    "lumina": ("lumina", "Playfair Display"),
    "natural": ("lumina", "Playfair Display"),
    "tierno": ("rose-gold", "Poppins"),
    "medico": ("sky", "Inter"),
    "futurista": ("indigo-twilight", "Space Grotesk"),
    "colorido": ("magenta", "Poppins"),
}


def _pick_palette(low_topic, memory, brief=None, window=4):
    """Paleta con variedad: referencia → tema → anti-repetición global.
    Si la paleta preferida por tema ya se usó hace poco, elige otra no repetida."""
    if brief:
        pal = _pick_brief_palette(brief)
        if pal:
            return pal
    preferred = None
    for words, name in _TOPIC_PALETTES:
        if any(w in (low_topic or "") for w in words):
            preferred = name
            break
    used = [str(u.get("value")) for u in memory.get("palettes_used", [])][-window:]
    cand = [x for x in PALETTES if x["name"] not in used]
    if preferred:
        if preferred not in used:
            return next(x for x in PALETTES if x["name"] == preferred)
        if cand:
            return random.choice(cand)
        return next(x for x in PALETTES if x["name"] == preferred)
    return random.choice(cand) if cand else random.choice(PALETTES)


def _pick_font(low_topic, memory, brief=None, palette_name=None, window=4):
    """Fuente con variedad: referencia → estilo (editorial) → tema → anti-repetición.
    El estilo editorial premium (ocean-sand) prefiere Fraunces."""
    if brief and brief.get("fonts"):
        ref_font = brief["fonts"][0]
        mapping = {f[0].lower(): f for f in FONTS}
        mapped = mapping.get(ref_font.lower())
        if mapped:
            return mapped
        if ref_font.startswith(("var(", "-webkit-", "-moz-")) or not any(ch.isalpha() for ch in ref_font):
            pass
        else:
            return ref_font, ref_font.replace(" ", "+")
    preferred = None
    if palette_name == "ocean-sand":
        preferred = "Fraunces"
    elif palette_name == "lumina":
        preferred = "Playfair Display"
    elif any(w in (low_topic or "") for w in ("peluquer", "salon", "belleza", "beauty", "barber", "estetica", "spa")):
        preferred = "Cormorant Garamond"
    elif any(w in (low_topic or "") for w in ("veterin", "vet", "mascota", "perro", "gato", "animal")):
        cand = [f for f in FONTS if f[0] in ("Manrope", "Inter", "Outfit")]
        return random.choice(cand)
    used = [str(u.get("value")) for u in memory.get("fonts_used", [])][-window:]
    cand = [f for f in FONTS if f[0] not in used]
    if preferred:
        if preferred not in used:
            return next(f for f in FONTS if f[0] == preferred)
        if cand:
            return random.choice(cand)
        return next(f for f in FONTS if f[0] == preferred)
    return random.choice(cand) if cand else random.choice(FONTS)


def _render_section(sec, p, fonts_css, idx, hero_mode="centered", kb_img=""):
    stype = _classify_section(sec, idx, 10)
    title = sec.get("title") or ""
    text = sec.get("text") or ""
    items = sec.get("items") or []
    if isinstance(items, dict):
        items = list(items.values())
    hid = _slug(title) or ("seccion-" + str(idx + 1))

    if stype == "hero":
        return _hero_sec(title, text, p, hid, mode=hero_mode, kb_img=kb_img)
    if stype == "features":
        return _features_sec(title, text, items, p, hid)
    if stype == "gallery":
        n = sec.get("images") or max(3, len(items) or 4)
        return _gallery_sec(title, text, n, p, hid)
    if stype == "stats":
        return _stats_sec(title, items, p, hid, text=text)
    if stype == "testimonials":
        return _testimonials_sec(title, items, p, hid, text=text)
    if stype == "faq":
        return _faq_sec(title, items, p, hid, text=text)
    if stype == "contact":
        return _contact_sec(title, text, p, hid)
    if stype == "prices":
        return _prices_sec(title, text, items, p, hid)
    if stype == "process":
        return _process_sec(title, text, items, p, hid)
    if stype == "team":
        return _team_sec(title, text, items, p, hid)
    if stype == "subhero":
        return _subhero_sec(title, text, p, hid)
    return _about_sec(title, text, items, p, hid)


def _section_wrap(inner, hid, p, label=""):
    return (
        '<section id="{hid}" class="section reveal" data-label="{label}">\n'
        '  <div class="container">\n{inner}\n  </div>\n</section>'
    ).format(hid=hid, label=label, inner=inner)


def _section_header(title, text, p, center=True):
    t = ('<h2 class="s-title">{}</h2>'.format(title)) if title else ""
    d = ('<p class="s-sub">{}</p>'.format(text)) if text else ""
    return '<div class="s-head">{}{}</div>'.format(t, d)


def _hero_sec(title, text, p, hid, mode="centered", kb_img=""):
    grad = "linear-gradient(120deg, {a}, {b}, {c})".format(a=p["primary"], b=p["secondary"], c=p["accent"])
    d = _is_dark(p.get("bg", "#0a0a0f"))
    line = "rgba(255,255,255,.04)" if d else "rgba(0,0,0,.05)"
    tagb = "rgba(255,255,255,.14)" if d else "rgba(0,0,0,.18)"
    tagt = ".55" if d else ".62"
    if mode == "split":
        return _hero_split(title, text, p, hid, grad, line, tagb, tagt)
    if mode == "editorial":
        return _hero_editorial(title, text, p, hid, grad, line, tagb, tagt)
    if mode == "compact":
        return _hero_compact(title, text, p, hid, grad, line, tagb, tagt, kb_img)
    return (
        '<section id="{hid}" class="hero">\n'
        '  {kb}'
        '  <div class="hero-bg"></div>\n'
        '  <div class="container hero-inner">\n'
        '    <div class="hero-tag reveal" style="animation-delay:.05s">{tag}</div>\n'
        '    <h1 class="hero-title reveal" style="animation-delay:.15s">{t}</h1>\n'
        '    <p class="hero-text reveal" style="animation-delay:.3s">{txt}</p>\n'
        '    <div class="hero-cta reveal" style="animation-delay:.45s">\n'
        '      <a class="btn btn-a" href="#{next}">Explorar <span>&rarr;</span></a>\n'
        '      <a class="btn btn-b" href="#contacto">Contacto</a>\n'
        '    </div>\n'
        '  </div>\n'
        '  <div class="hero-scroll">scroll &darr;</div>\n'
        '</section>\n'
        '<style>'
        '.hero{{min-height:100vh;display:flex;align-items:center;position:relative;overflow:hidden;}}'
        '.hero-bg{{position:absolute;inset:0;z-index:0;background:radial-gradient(ellipse 70% 60% at 75% 20%,{p1}33,transparent 60%),'
        'radial-gradient(ellipse 60% 50% at 20% 80%,{p2}33,transparent 60%),{bg};}}'
        '.hero::after{{content:"";position:absolute;inset:0;background-image:linear-gradient({line} 1px,transparent 1px),'
        'linear-gradient(90deg,{line} 1px,transparent 1px);background-size:56px 56px;mask-image:radial-gradient(ellipse at center,#000 30%,transparent 75%);z-index:0;}}'
        '.hero-inner{{position:relative;z-index:2;padding-top:4rem;}}'
        '.hero-tag{{display:inline-block;font-size:.75rem;letter-spacing:.35em;text-transform:uppercase;opacity:{tagt};margin-bottom:1.2rem;border:1px solid {tagb};padding:.4rem 1rem;border-radius:100px;}}'
        '.hero-title{{font-size:clamp(2.4rem,7vw,5rem);line-height:1.04;font-weight:800;letter-spacing:-.02em;margin-bottom:1.2rem;background:{grad};-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;}}'
        '.hero-text{{font-size:1.2rem;max-width:560px;opacity:.78;margin-bottom:2rem;}}'
        '.hero-cta{{display:flex;gap:1rem;flex-wrap:wrap;}}'
        '</style>'
    ).format(hid=hid, kb=('<div class="hero-kb">' + kb_img + '</div>') if kb_img else "",
             tag=title or "ERIS DESIGN", t=title or "Creamos experiencias", txt=text,
             next="que-hacemos", grad=grad, p1=p["primary"], p2=p["secondary"], bg=p["bg"],
             line=line, tagb=tagb, tagt=tagt)


def _hero_split(title, text, p, hid, grad, line, tagb, tagt):
    img = _img("hero-split", 900, 1000, p["primary"], p["secondary"], title)
    return (
        '<section id="{hid}" class="hero hero-split">\n'
        '  <div class="hero-bg"></div>\n'
        '  <div class="container hero-inner">\n'
        '    <div class="hs-left">\n'
        '      <div class="hero-tag reveal" style="animation-delay:.05s">{tag}</div>\n'
        '      <h1 class="hero-title reveal" style="animation-delay:.15s" data-parallax=".14">{t}</h1>\n'
        '      <p class="hero-text reveal" style="animation-delay:.3s" data-parallax=".1">{txt}</p>\n'
        '      <div class="hero-cta reveal" style="animation-delay:.45s">\n'
        '        <a class="btn btn-a" href="#{next}">Explorar <span>&rarr;</span></a>\n'
        '        <a class="btn btn-b" href="#contacto">Contacto</a>\n'
        '      </div>\n'
        '    </div>\n'
        '    <div class="hs-right reveal" style="animation-delay:.2s">{img}</div>\n'
        '  </div>\n'
        '  <div class="hero-scroll">scroll &darr;</div>\n'
        '</section>\n'
        '<style>'
        '.hero-split{{min-height:100vh;display:flex;align-items:center;position:relative;overflow:hidden;}}'
        '.hero-split .hero-bg{{position:absolute;inset:0;z-index:0;background:radial-gradient(ellipse 80% 60% at 10% 30%,{p1}2e,transparent 60%),{bg};}}'
        '.hero-split .hero-inner{{position:relative;z-index:2;display:grid;grid-template-columns:1.1fr .9fr;gap:3rem;align-items:center;padding-top:4rem;}}'
        '.hs-left{{padding:2rem 0;}}'
        '.hs-right img{{width:100%;height:min(70vh,620px);object-fit:cover;border-radius:28px;box-shadow:0 40px 90px rgba(0,0,0,.35);}}'
        '.hero-tag{{display:inline-block;font-size:.75rem;letter-spacing:.35em;text-transform:uppercase;opacity:{tagt};margin-bottom:1.2rem;border:1px solid {tagb};padding:.4rem 1rem;border-radius:100px;}}'
        '.hero-split .hero-title{{font-size:clamp(2.4rem,5.6vw,4.4rem);line-height:1.02;font-weight:800;letter-spacing:-.03em;margin-bottom:1.2rem;background:{grad};-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;}}'
        '.hero-split .hero-text{{font-size:1.2rem;max-width:520px;opacity:.78;margin-bottom:2rem;}}'
        '@media(max-width:900px){{.hero-split .hero-inner{{grid-template-columns:1fr;}}.hs-right{{display:none;}}}}'
        '</style>'
    ).format(hid=hid, tag=title or "ERIS DESIGN", t=title or "Creamos experiencias", txt=text,
             next="que-hacemos", grad=grad, p1=p["primary"], bg=p["bg"], img=img,
             tagb=tagb, tagt=tagt)


def _hero_editorial(title, text, p, hid, grad, line, tagb, tagt):
    return (
        '<section id="{hid}" class="hero hero-ed">\n'
        '  <div class="hero-bg"></div>\n'
        '  <div class="container hero-inner">\n'
        '    <p class="ed-kicker reveal">— {tag}</p>\n'
        '    <h1 class="ed-title reveal" style="animation-delay:.1s" data-parallax=".12">{t}</h1>\n'
        '    <div class="ed-row reveal" style="animation-delay:.3s">\n'
        '      <p class="ed-text">{txt}</p>\n'
        '      <div class="ed-cta"><a class="btn btn-a" href="#{next}">Empezar <span>&rarr;</span></a></div>\n'
        '    </div>\n'
        '  </div>\n'
        '  <div class="hero-scroll">scroll &darr;</div>\n'
        '</section>\n'
        '<style>'
        '.hero-ed{{min-height:100vh;display:flex;align-items:flex-end;position:relative;overflow:hidden;padding-bottom:8vh;}}'
        '.hero-ed .hero-bg{{position:absolute;inset:0;z-index:0;background:{bg};}}'
        '.hero-ed .hero-inner{{position:relative;z-index:2;padding-top:4rem;}}'
        '.ed-kicker{{font-size:.8rem;letter-spacing:.4em;text-transform:uppercase;opacity:.6;margin-bottom:1.6rem;}}'
        '.ed-title{{font-family:inherit;font-size:clamp(3rem,11vw,9rem);line-height:.98;font-weight:800;'
        'letter-spacing:-.04em;max-width:12ch;margin-bottom:3rem;}}'
        '.ed-row{{display:flex;gap:3rem;align-items:flex-end;justify-content:space-between;max-width:1000px;}}'
        '.ed-text{{font-size:1.25rem;opacity:.75;max-width:520px;}}'
        '.ed-cta{{flex-shrink:0;}}'
        '@media(max-width:760px){{.ed-row{{flex-direction:column;align-items:flex-start;}}}}'
        '</style>'
    ).format(hid=hid, tag=title or "ERIS DESIGN", t=title or "Creamos experiencias", txt=text,
             next="que-hacemos", bg=p["bg"])


def _hero_compact(title, text, p, hid, grad, line, tagb, tagt, kb_img=""):
    return (
        '<section id="{hid}" class="hero hero-c">\n'
        '  {kb}'
        '  <div class="hero-bg"></div>\n'
        '  <div class="container hero-inner">\n'
        '    <div class="hc-chip reveal">✦ {tag}</div>\n'
        '    <h1 class="hero-title reveal" style="animation-delay:.1s">{t}</h1>\n'
        '    <p class="hero-text reveal" style="animation-delay:.2s">{txt}</p>\n'
        '    <div class="hero-cta reveal" style="animation-delay:.3s">\n'
        '      <a class="btn btn-a" href="#{next}">Explorar</a>\n'
        '      <a class="btn btn-b" href="#contacto">Contacto</a>\n'
        '    </div>\n'
        '  </div>\n'
        '  <div class="hero-scroll">scroll &darr;</div>\n'
        '</section>\n'
        '<style>'
        '.hero-c{{min-height:78vh;display:flex;align-items:center;position:relative;overflow:hidden;}}'
        '.hero-c .hero-bg{{position:absolute;inset:0;z-index:0;background:{bg};'
        'background-image:radial-gradient(circle at 80% 20%,{p1}2e,transparent 50%);}}'
        '.hero-c .hero-inner{{position:relative;z-index:2;padding-top:4rem;text-align:left;}}'
        '.hc-chip{{display:inline-block;font-size:.78rem;letter-spacing:.3em;text-transform:uppercase;'
        'opacity:.65;margin-bottom:1.4rem;padding:.45rem 1.1rem;border:1px solid {tagb};border-radius:100px;}}'
        '.hero-c .hero-title{{font-size:clamp(2.6rem,7vw,5rem);line-height:1.02;font-weight:800;'
        'letter-spacing:-.02em;margin-bottom:1.1rem;background:{grad};-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;}}'
        '.hero-c .hero-text{{font-size:1.2rem;max-width:560px;opacity:.78;margin-bottom:2rem;}}'
        '</style>'
    ).format(hid=hid, kb=('<div class="hero-kb">' + kb_img + '</div>') if kb_img else "",
             tag=title or "ERIS DESIGN", t=title or "Creamos experiencias", txt=text,
             next="que-hacemos", grad=grad, p1=p["primary"], bg=p["bg"], tagb=tagb)


def _features_sec(title, text, items, p, hid):
    items = [i if isinstance(i, str) else str(i) for i in items]
    if len(items) < 3:
        items = items + ["Excelencia en cada detalle", "Atención personalizada", "Entrega a tiempo"][:3 - len(items)]
    cards = "\n".join(
        '<div class="feature reveal" style="animation-delay:{}s">'
        '<div class="feature-icon">{icon}</div><h3>{t}</h3><p>{d}</p></div>'.format(
            i * 0.08, icon=chr(9670 + i), t=txt, d="Un pilar de nuestro servicio.")
        for i, txt in enumerate(items)
    )
    return _section_wrap(
        _section_header(title, text, p) + '<div class="grid-3">{}</div>'.format(cards), hid, p)


def _gallery_sec(title, text, n, p, hid):
    n = int(n) if n else 4
    seeds = ["eris" + str(i) for i in range(n)]
    grid = "\n".join(
        '<figure class="g-item reveal" style="animation-delay:{}s">{}</figure>'.format(
            i * 0.07, _img(seeds[i], 640, 480, p["primary"], p["secondary"], "Proyecto " + str(i + 1)))
        for i in range(n)
    )
    return _section_wrap(
        _section_header(title, text, p) + '<div class="g-grid">{}</div>'.format(grid), hid, p)


def _stats_sec(title, items, p, hid, text=""):
    stats = []
    for it in items:
        if isinstance(it, str):
            parts = it.split("::")
            stats.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""))
        elif isinstance(it, (list, tuple)) and len(it) >= 2:
            stats.append((str(it[0]), str(it[1])))
    stats = stats or [("120+", "Proyectos"), ("98%", "Clientes felices"), ("12", "Premios")]
    cells = "\n".join(
        '<div class="stat reveal" style="animation-delay:{}s"><div class="stat-n" data-count="{}">{}</div><div class="stat-l">{}</div></div>'.format(
            i * 0.08, re.sub(r"[^0-9.]", "", n), n, l) for i, (n, l) in enumerate(stats)
    )
    return _section_wrap(
        _section_header(title or "Cifras", text, p) + '<div class="stats">{}</div>'.format(cells), hid, p)


def _testimonials_sec(title, items, p, hid, text=""):
    quotes = [q if isinstance(q, str) else (q.get("text") or q.get("quote") or "") for q in items]
    cards = "\n".join(
        '<blockquote class="t-item reveal" style="animation-delay:{}s"><span class="q">&ldquo;</span>{}</blockquote>'.format(
            i * 0.08, q) for i, q in enumerate(quotes[:6])
    )
    return _section_wrap(
        _section_header(title or "Testimonios", text, p) + '<div class="grid-3">{}</div>'.format(cards), hid, p)


def _faq_sec(title, items, p, hid, text=""):
    faqs = []
    for it in items:
        if isinstance(it, (list, tuple)) and len(it) == 2:
            faqs.append(it)
        elif isinstance(it, dict):
            faqs.append((it.get("q") or it.get("title"), it.get("a") or it.get("text")))
    blocks = []
    for i, (q, a) in enumerate(faqs[:8]):
        blocks.append(
            '<details class="faq reveal" style="animation-delay:{}s" open={}><summary>{}</summary><p>{}</p></details>'.format(
                i * 0.05, "open" if i == 0 else "", q, a))
    return _section_wrap(
        _section_header(title or "Preguntas frecuentes", text, p) + "".join(blocks), hid, p)


def _about_sec(title, text, items, p, hid):
    imgs = "<div class='about-img reveal'>{}</div>".format(
        _img(hid, 720, 540, p["primary"], p["secondary"], title or "Sobre nosotros"))
    body = '<div class="about-body"><h2 class="s-title">{}</h2><p class="s-sub">{}</p></div>'.format(title, text)
    return _section_wrap(
        '<div class="about-grid">{}{}</div>'.format(imgs, body), hid, p)


def _contact_sec(title, text, p, hid):
    return _section_wrap(
        _section_header(title or "Contacto", text or "Escribinos y te respondemos pronto", p)
        + '<form id="cform" class="form reveal">'
          '<div class="f-row"><input class="f-in" placeholder="Nombre" required>'
          '<input class="f-in" type="email" placeholder="Email" required></div>'
          '<textarea class="f-in f-ta" rows="4" placeholder="Mensaje" required></textarea>'
          '<button type="submit" class="btn btn-a btn-lg">Enviar mensaje</button></form>',
        hid, p, label="contact")


def _subhero_sec(title, text, p, hid):
    d = _is_dark(p.get("bg", "#0a0a0f"))
    line = "rgba(255,255,255,.05)" if d else "rgba(0,0,0,.06)"
    return (
        '<section id="{hid}" class="subhero">\n'
        '  <div class="container subhero-inner reveal">\n'
        '    <h1 class="subhero-title">{t}</h1>\n'
        '    <p class="subhero-text">{txt}</p>\n'
        '  </div>\n'
        '</section>\n'
        '<style>'
        '.subhero{{padding:9rem 0 3.5rem;position:relative;overflow:hidden;}}'
        '.subhero::after{{content:"";position:absolute;inset:0;background-image:linear-gradient({line} 1px,transparent 1px),'
        'linear-gradient(90deg,{line} 1px,transparent 1px);background-size:56px 56px;'
        'mask-image:radial-gradient(ellipse at center,#000 20%,transparent 70%);pointer-events:none;}}'
        '.subhero-inner{{position:relative;z-index:2;}}'
        '.subhero-title{{font-size:clamp(2.2rem,6vw,4rem);font-weight:800;letter-spacing:-.02em;margin-bottom:.8rem;}}'
        '.subhero-text{{font-size:1.15rem;opacity:.72;max-width:620px;}}'
        '</style>'
    ).format(hid=hid, t=title, txt=text, line=line)


def _prices_sec(title, text, items, p, hid):
    rows = []
    for it in items:
        if isinstance(it, (list, tuple)) and len(it) >= 2:
            name, price = str(it[0]), str(it[1])
        elif isinstance(it, dict):
            name, price = it.get("name") or "", it.get("price") or ""
        else:
            parts = str(it).split("::")
            name = parts[0].strip()
            price = parts[1].strip() if len(parts) > 1 else "consultar"
        rows.append((name, price))
    rows = rows or [("Servicio base", "desde $25"), ("Servicio premium", "desde $60")]
    lis = "\n".join(
        '<li class="price-row reveal" style="animation-delay:{}s">'
        '<span class="price-name">{n}</span><span class="price-dots"></span>'
        '<span class="price-val">{pr}</span></li>'.format(i * 0.05, n=n, pr=price)
        for i, (n, price) in enumerate(rows))
    return _section_wrap(
        _section_header(title, text, p) + '<ul class="p-list">{}</ul>'.format(lis), hid, p)


def _process_sec(title, text, items, p, hid):
    steps = items or ["Conocernos", "Proponer", "Crear", "Entregar"]
    cards = "\n".join(
        '<div class="step reveal" style="animation-delay:{}s">'
        '<div class="step-num">0{}</div><h3 class="step-t">{t}</h3>'
        '<p class="step-d">Paso del proceso para lograr resultados claros y a medida.</p></div>'.format(
            i * 0.08, i + 1, t=s)
        for i, s in enumerate(steps[:6]))
    return _section_wrap(
        _section_header(title, text, p) + '<div class="proc">{}</div>'.format(cards), hid, p)


def _team_sec(title, text, items, p, hid):
    members = items or ["Fundador", "Directora creativa", "Equipo"]
    cards = "\n".join(
        '<div class="team reveal" style="animation-delay:{}s">'
        '<div class="team-ava">{ava}</div>'
        '<h3 class="team-n">{n}</h3><p class="team-r">Miembro del equipo</p></div>'.format(
            i * 0.08, ava=_img("team" + str(i), 240, 240, p["primary"], p["secondary"], "Perfil"),
            n=mem)
        for i, mem in enumerate(members[:6]))
    return _section_wrap(
        _section_header(title or "Nuestro equipo", text, p) + '<div class="team-grid">{}</div>'.format(cards), hid, p)


def _assemble_page(title, topic, sections, p, font_name, font_url, animations, brief, layout="centered", nav_html="", bg_style="grid", page_id="", video_url=None, current="index"):
    body_secs = "\n".join(_render_section(s, p, "", i) for i, s in enumerate(sections))
    if nav_html:
        nav_links = nav_html
    else:
        nav_items = []
        for s in sections[1:]:
            st = _classify_section(s, 1, 10)
            if st == "contact":
                nav_items.append(("contacto", "Contacto"))
                continue
            if s.get("title"):
                nav_items.append((_slug(s["title"]), s["title"][:22]))
        nav_links = "".join('<li><a href="#{}">{}</a></li>'.format(k, v) for k, v in nav_items[:5])
        if "contacto" not in [k for k, _ in nav_items]:
            nav_links += '<li><a href="#contacto">Contacto</a></li>'

    kb_img = _img(_slug(topic) + "-hero", 1600, 900, p["primary"], p["secondary"], title) if "kenburns" in animations else ""
    body_secs = "\n".join(
        _render_section(s, p, "", i, hero_mode=layout, kb_img=kb_img if i == 0 else "")
        for i, s in enumerate(sections))

    anim_js = ""
    if "particles" in animations:
        anim_js += (
            "var c=document.createElement('canvas');c.id='dots';document.body.prepend(c);"
            "var cx=c.getContext('2d'),W,H;"
            "function rs(){W=c.width=c.offsetWidth;H=c.height=c.offsetHeight;}rs();"
            "window.addEventListener('resize',rs);"
            "var N=Math.min(70,Math.floor(W*H/22000)),ps=[];"
            "for(var i=0;i<N;i++)ps.push({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*.6,vy:(Math.random()-.5)*.6,r:Math.random()*2+.4});"
            "function lo(){cx.clearRect(0,0,W,H);for(var i=0;i<N;i++){var o=ps[i];o.x+=o.vx;o.y+=o.vy;"
            "if(o.x<0||o.x>W)o.vx*=-1;if(o.y<0||o.y>H)o.vy*=-1;"
            "cx.beginPath();cx.arc(o.x,o.y,o.r,0,7);cx.fillStyle='%s';cx.globalAlpha=.6;cx.fill();}requestAnimationFrame(lo);}lo();" % p["primary"])
        anim_js = "<script>" + anim_js + "</script>"
        anim_js += (
            "<style>#dots{position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none;opacity:.5;}"
            ".hero{position:relative}.hero-inner,.section{position:relative;z-index:1;}</style>")
    if "tilt" in animations:
        anim_js += (
            "<script>document.querySelectorAll('.tilt').forEach(function(el){"
            "el.addEventListener('mousemove',function(e){var r=el.getBoundingClientRect();"
            "var x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;"
            "el.style.transform='perspective(700px) rotateY('+(x*10)+'deg) rotateX('+(-y*10)+'deg) translateY(-6px)';});"
            "el.addEventListener('mouseleave',function(){el.style.transform='';});});</script>")

    vid = ""
    if video_url:
        vid = ("<video class='hero-video' autoplay muted loop playsinline src='{v}'></video>"
               .format(v=video_url))

    brand = topic or title
    html = (
        "<!DOCTYPE html>\n<html lang='es'>\n<head>\n"
        "<meta charset='UTF-8'>\n"
        "<meta name='viewport' content='width=device-width,initial-scale=1.0'>\n"
        "<title>{title}</title>\n"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>\n"
        "<link href='https://fonts.googleapis.com/css2?family={font_url}&display=swap' rel='stylesheet'>\n"
        "<style>\n{css}\n</style>\n</head>\n<body class='bg-{bg_style}'>\n"
        "<div class='progress' id='prog'></div>\n"
        "<nav class='nav reveal' id='nav'><a class='nav-brand' href='index.html'>✦ {brand}</a>"
        "<button class='burger' onclick=\"document.getElementById('nav').classList.toggle('open')\">☰</button>"
        "<ul class='nav-links'>{nav_links}</ul></nav>\n"
        "{vid}"
        "{body}\n"
        "<footer class='foot'><p>© {year} {brand} — Diseñada por ERIS AI</p>"
        "<p class='foot-links'><a href='index.html'>Inicio</a> · <a href='servicios.html'>Servicios</a> · "
        "<a href='nosotros.html'>Nosotros</a> · <a href='galeria.html'>Galería</a> · <a href='contacto.html'>Contacto</a></p></footer>\n"
        "{anim_js}\n"
        "<script>\n{js}\n</script>\n</body></html>"
    ).format(
        title=title, font_url=font_url, brand=brand, nav_links=nav_links, body=body_secs,
        year=datetime.now().year, anim_js=anim_js, vid=vid,
        css=_css(p, font_name, animations, brief, bg_style=bg_style), js=_js(p["primary"]),
        bg_style=bg_style,
    )
    return html


def _css(p, font_name, animations, brief=None, bg_style="grid"):
    font_stack = '"{}","Segoe UI",system-ui,sans-serif'.format(font_name.replace("+", " "))
    d = _is_dark(p.get("bg", "#0a0a0f"))
    w = "rgba(255,255,255," if d else "rgba(0,0,0,"
    ink = p.get("fg", "#f2f2f2")
    if d:
        fgmuted = "rgba(255,255,255,.55)"
        card = "rgba(255,255,255,.035)"
        f_input = "rgba(255,255,255,.05)"
        foot = "rgba(255,255,255,.35)"
        btnb_hov = "rgba(255,255,255,.08)"
    else:
        fgmuted = "rgba(0,0,0,.62)"
        card = "#ffffff"
        f_input = "rgba(255,255,255,.75)"
        foot = "rgba(0,0,0,.5)"
        btnb_hov = "rgba(0,0,0,.06)"
    reveal = ""
    if "reveal" in animations:
        reveal = (
            ".reveal{opacity:0;transform:translateY(26px);transition:opacity .8s cubic-bezier(.22,.61,.36,1),transform .8s cubic-bezier(.22,.61,.36,1);}"
            ".reveal.on{opacity:1;transform:none;}"
        )
    marquee = ""
    if "marquee" in animations:
        marquee = (
            "@keyframes marq{{{{0%{{{{transform:translateX(0)}}}}100%{{{{transform:translateX(-50%)}}}}}}}}"
            ".marquee{{{{overflow:hidden;border-block:1px solid {b08};padding:1rem 0;white-space:nowrap;}}}}"
            ".marquee span{{{{display:inline-block;animation:marq 30s linear infinite;font-size:1rem;"
            "letter-spacing:.2em;text-transform:uppercase;opacity:.6;}}}}"
        ).format(b08=w + ".08)")
    return (
        "*{{margin:0;padding:0;box-sizing:border-box;}}"
        "html{{scroll-behavior:smooth;}}"
        "body{{font-family:{fs};background:{bg};color:{fg};line-height:1.6;overflow-x:hidden;font-size:16px;}}"
        "a{{color:inherit;text-decoration:none;}}img{{max-width:100%;display:block;height:auto;}}"
        "::selection{{background:{primary};color:#fff;}}"
        "::-webkit-scrollbar{{width:8px;}}::-webkit-scrollbar-thumb{{background:{primary}88;border-radius:8px;}}"
        ".container{{max-width:1140px;margin:0 auto;padding:0 1.5rem;}}"
        ".progress{{position:fixed;top:0;left:0;height:3px;background:linear-gradient(90deg,{primary},{accent});z-index:2000;width:0;}}"
        ".nav{{position:fixed;top:0;left:0;right:0;z-index:1500;display:flex;align-items:center;padding:.9rem 1.6rem;"
        "background:{bgdd};backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border-bottom:1px solid {b06};}}"
        ".nav-brand{{font-weight:700;font-size:1.25rem;letter-spacing:-.01em;color:{primary};}}"
        ".nav-links{{list-style:none;display:flex;margin-left:auto;gap:.2rem;}}"
        ".nav-links a{{display:block;padding:.45rem .9rem;font-size:.92rem;color:{fgmuted};border-radius:100px;transition:all .25s;}}"
        ".nav-links a:hover{{color:{primary};background:{primary}14;}}"
        ".nav-links a.active{{color:{primary};font-weight:700;background:{primary}1a;}}"
        ".burger{{display:none;margin-left:auto;background:none;border:1px solid {b25};color:{fg};"
        "font-size:1.2rem;padding:.2rem .6rem;border-radius:8px;cursor:pointer;}}"
        ".section{{padding:5.5rem 0;position:relative;}}"
        ".s-head{{text-align:center;max-width:680px;margin:0 auto 3rem;}}"
        ".s-title{{font-size:clamp(1.7rem,3.6vw,2.9rem);font-weight:800;letter-spacing:-.02em;margin-bottom:.6rem;}}"
        ".s-sub{{opacity:.62;font-size:1.05rem;}}"
        ".grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:1.4rem;}}"
        ".feature{{background:{card};border:1px solid {b07};border-radius:{radius};padding:2rem;transition:all .45s cubic-bezier(.175,.885,.32,1.275);}}"
        ".feature:hover{{transform:translateY(-8px);border-color:{primary}55;box-shadow:0 24px 60px rgba(0,0,0,.18);}}"
        ".feature-icon{{font-size:1.8rem;color:{primary};margin-bottom:.9rem;}}"
        ".feature h3{{font-size:1.15rem;margin-bottom:.5rem;}}"
        ".feature p{{opacity:.68;font-size:.95rem;}}"
        ".g-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.2rem;}}"
        ".g-item{{border-radius:{radius};overflow:hidden;border:1px solid {b07};transition:transform .5s cubic-bezier(.175,.885,.32,1.275);}}"
        ".g-item:hover{{transform:scale(1.03) rotate(.5deg);}}"
        ".stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1.4rem;text-align:center;}}"
        ".stat-n{{font-size:clamp(2.2rem,5vw,3.6rem);font-weight:800;background:linear-gradient(120deg,{primary},{accent});"
        "-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;}}"
        ".stat-l{{opacity:.6;margin-top:.2rem;}}"
        ".t-item{{background:{card};border:1px solid {b07};border-radius:{radius};padding:1.8rem;font-style:italic;position:relative;}}"
        ".q{{position:absolute;top:.4rem;left:1rem;font-size:3rem;color:{primary}44;}}"
        ".about-grid{{display:grid;grid-template-columns:1fr 1fr;gap:3rem;align-items:center;}}"
        ".about-img img{{border-radius:{radius};}}"
        ".p-list{{list-style:none;max-width:760px;margin:0 auto;}}"
        ".price-row{{display:flex;align-items:baseline;gap:1rem;padding:.9rem 0;border-bottom:1px dashed {b12};}}"
        ".price-name{{font-weight:600;}}"
        ".price-dots{{flex:1;border-bottom:2px dotted {b25};}}"
        ".price-val{{font-weight:800;color:{primary};font-size:1.15rem;}}"
        ".proc{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1.4rem;}}"
        ".step{{background:{card};border:1px solid {b07};border-radius:{radius};padding:1.8rem;}}"
        ".step-num{{font-size:2.2rem;font-weight:800;background:linear-gradient(120deg,{primary},{accent});"
        "-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;}}"
        ".step-t{{font-size:1.1rem;margin:.6rem 0 .4rem;}}"
        ".step-d{{opacity:.65;font-size:.92rem;}}"
        ".team-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1.4rem;}}"
        ".team{{background:{card};border:1px solid {b07};border-radius:{radius};padding:1.5rem;text-align:center;}}"
        ".team-ava{{border-radius:50%;overflow:hidden;aspect-ratio:1;margin-bottom:1rem;}}"
        ".team-ava img{{width:100%;height:100%;object-fit:cover;}}"
        ".team-n{{font-weight:600;}}"
        ".team-r{{opacity:.6;font-size:.85rem;margin-top:.25rem;}}"
        ".faq{{background:{card};border:1px solid {b07};border-radius:{radius};margin-bottom:.8rem;overflow:hidden;}}"
        ".faq summary{{padding:1.1rem 1.4rem;cursor:pointer;font-weight:600;}}"
        ".faq p{{padding:0 1.4rem 1.2rem;opacity:.7;}}"
        ".btn{{display:inline-block;padding:14px 34px;font-weight:600;border-radius:100px;cursor:pointer;border:none;font-size:1rem;transition:all .4s cubic-bezier(.175,.885,.32,1.275);}}"
        ".btn-a{{background:linear-gradient(120deg,{primary},{secondary});color:#fff;box-shadow:0 6px 24px {primary}55;}}"
        ".btn-a:hover{{transform:translateY(-3px) scale(1.02);box-shadow:0 14px 40px {primary}77;}}"
        ".btn-b{{background:transparent;border:1px solid {b35};color:{fg};}}"
        ".btn-b:hover{{background:{btnb_hov};}}"
        ".btn-lg{{padding:16px 40px;}}"
        ".form{{max-width:640px;margin:0 auto;display:grid;gap:.9rem;}}"
        ".f-row{{display:grid;grid-template-columns:1fr 1fr;gap:.9rem;}}"
        ".f-in{{width:100%;padding:.95rem 1.2rem;background:{f_input};border:1px solid {b12};"
        "color:{fg};border-radius:{radius};font-size:1rem;outline:none;transition:border-color .25s;}}"
        ".f-in:focus{{border-color:{primary};box-shadow:0 0 0 3px {primary}33;}}"
        ".foot{{padding:2.2rem 0;text-align:center;border-top:1px solid {b06};color:{foot};font-size:.9rem;}}"
        "@media(max-width:768px){{.grid-3{{grid-template-columns:1fr;}}.about-grid{{grid-template-columns:1fr;}}"
        ".f-row{{grid-template-columns:1fr;}}.burger{{display:block;}}.nav-links{{display:none;position:absolute;top:100%;left:0;right:0;"
        "flex-direction:column;background:{bg};padding:1rem;border-bottom:1px solid {b08};}}"
        ".nav.open .nav-links{{display:flex;}}"
        ".hero-title{{font-size:clamp(2rem,10vw,3.4rem);}}}}"
        "{bgcss}"
        "{extra}"
        "{reveal}{marquee}"
    ).format(
        fs=font_stack, bg=p["bg"], bgdd=p["bg"] + "dd", fg=ink, fgmuted=fgmuted,
        primary=p["primary"], secondary=p["secondary"], accent=p["accent"],
        card=card, radius=(brief or {}).get("style_flags", {}).get("radius", "18px"),
        b06=w + ".06)", b07=w + ".07)", b08=w + ".08)", b12=w + ".12)", b25=w + ".25)", b35=w + ".35)",
        f_input=f_input, foot=foot, btnb_hov=btnb_hov,
        bgcss=_bg_css(bg_style, p), extra=_extra_anim_css(animations, w, p),
        reveal=reveal, marquee=marquee,
    )


def _bg_css(bg_style, p):
    """Fondos de página variados que se aplican según bg_style."""
    b = p["bg"]
    p1, p2 = p.get("primary", "#888"), p.get("secondary", "#666")
    if bg_style == "blobs":
        return (
            "body.bg-blobs{{position:relative;}}"
            "body.bg-blobs::before{{content:'';position:fixed;inset:-20%;z-index:-1;pointer-events:none;"
            "background:radial-gradient(circle at 20% 30%,{p1}3a,transparent 40%),"
            "radial-gradient(circle at 80% 20%,{p2}3a,transparent 40%),"
            "radial-gradient(circle at 60% 80%,{a}33,transparent 45%),{b};"
            "filter:blur(30px);animation:bgdrift 18s ease-in-out infinite alternate;}}"
            "@keyframes bgdrift{{0%{{transform:translate(0,0) scale(1);}}100%{{transform:translate(-4%,3%) scale(1.08);}}}}"
        ).format(b=b, p1=p1, p2=p2, a=p.get("accent", p1))
    if bg_style == "mesh":
        return (
            "body.bg-mesh{{background:{b};}}"
            "body.bg-mesh::before{{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;"
            "background:linear-gradient(135deg,{p1}22 0%,transparent 40%),linear-gradient(315deg,{p2}22 0%,transparent 45%);}}"
        ).format(b=b, p1=p1, p2=p2)
    if bg_style == "dots":
        return (
            "body.bg-dots{{background:{b};}}"
            "body.bg-dots::before{{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;"
            "background-image:radial-gradient({p1}55 1.2px,transparent 1.4px);background-size:26px 26px;opacity:.5;}}"
        ).format(b=b, p1=p1)
    if bg_style == "rings":
        return (
            "body.bg-rings{{background:{b};}}"
            "body.bg-rings::before{{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;"
            "background:radial-gradient(circle at 30% 40%,transparent 0 18%,{p1}22 18% 18.4%,transparent 18.4% 34%,{p2}22 34% 34.4%,transparent 34.4%);opacity:.6;}}"
        ).format(b=b, p1=p1, p2=p2)
    if bg_style == "aurora":
        return (
            "body.bg-aurora{{background:{b};}}"
            "body.bg-aurora::before{{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;"
            "background:linear-gradient(120deg,{p1}2b,{p2}29,{a}24);filter:blur(70px);animation:au 14s ease-in-out infinite alternate;}}"
            "@keyframes au{{0%{{opacity:.5;transform:scale(1) rotate(0);}}100%{{opacity:.9;transform:scale(1.15) rotate(4deg);}}}}"
        ).format(b=b, p1=p1, p2=p2, a=p.get("accent", p1))
    return ""


def _extra_anim_css(animations, w, p):
    """CSS extra por tipo de animación (float/blob/kenburns/tilt/parallax)."""
    out = []
    p1, p2, ac = p.get("primary", "#888"), p.get("secondary", "#666"), p.get("accent", "#888")
    d = _is_dark(p.get("bg", "#0a0a0f"))
    if "float" in animations:
        out.append(
            "@keyframes fl{0%,100%{transform:translateY(0)}50%{transform:translateY(-18px)}}"
            ".hero-bg::before{{content:'';position:absolute;width:220px;height:220px;border-radius:50%;"
            "top:16%;left:8%;background:linear-gradient(135deg,{p1}33,transparent);"
            "animation:fl 9s ease-in-out infinite;}}"
            ".hero-bg::after{{content:'';position:absolute;width:140px;height:140px;border-radius:50%;"
            "bottom:18%;right:10%;background:linear-gradient(225deg,{p2}33,transparent);"
            "animation:fl 7s ease-in-out infinite reverse;}}".format(p1=p1, p2=p2))
    if "blob" in animations:
        out.append(
            "@keyframes blobm{{0%,100%{{border-radius:60% 40% 30% 70%/60% 30% 70% 40%;}}"
            "50%{{border-radius:30% 60% 70% 40%/50% 60% 30% 60%;}}}}"
            ".hero-bg::before{{content:'';position:absolute;width:46vw;height:46vw;max-width:560px;max-height:560px;"
            "top:10%;right:4%;background:linear-gradient(135deg,{p1}44,{p2}33);"
            "filter:blur(6px);animation:blobm 16s ease-in-out infinite;opacity:.55;}}".format(p1=p1, p2=p2))
    if "kenburns" in animations:
        over_a, over_b = ("rgba(0,0,0,.35)", "rgba(0,0,0,.6)") if d else ("rgba(255,255,255,.25)", "rgba(255,255,255,.55)")
        out.append(
            "@keyframes kb{{0%{{transform:scale(1) translate(0,0);}}100%{{transform:scale(1.18) translate(2%,-2%);}}}}"
            ".hero .hero-kb{{position:absolute;inset:0;z-index:0;overflow:hidden;}}"
            ".hero .hero-kb img{{width:100%;height:100%;object-fit:cover;animation:kb 24s ease-in-out infinite alternate;}}"
            ".hero .hero-kb::after{{content:'';position:absolute;inset:0;background:linear-gradient(180deg,{a},{b});}}"
            .format(a=over_a, b=over_b))
    if "tilt" in animations:
        out.append(
            ".feature,.g-item,.team{{transform-style:preserve-3d;will-change:transform;transition:transform .3s ease,box-shadow .3s ease;}}")
    if "parallax" in animations:
        out.append("[data-parallax]{{will-change:transform;}}")
    return "".join(out)


def _js(primary):
    return (
        "(function(){"
        "var p=document.getElementById('prog');"
        "function sp(){var h=document.documentElement;var m=h.scrollHeight-h.clientHeight;"
        "p.style.width=(m>0?100*h.scrollTop/m:0)+'%';}"
        "addEventListener('scroll',sp,{passive:true});sp();"
        "var nav=document.getElementById('nav');var lh=window.innerHeight;"
        "var iv=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)e.target.classList.add('on');});},"
        "{threshold:.12});"
        "document.querySelectorAll('.reveal').forEach(function(el){iv.observe(el);});"
        "document.querySelectorAll('a[href^=\"#\"]').forEach(function(a){a.addEventListener('click',function(e){"
        "var t=document.querySelector(this.getAttribute('href'));"
        "if(t){e.preventDefault();t.scrollIntoView({behavior:'smooth'});nav.classList.remove('open');}});});"
        "document.querySelectorAll('[data-count]').forEach(function(el){"
        "var target=parseFloat(el.getAttribute('data-count'));var started=false;"
        "function run(){var v=0,step=Math.max(target/60,0.1);"
        "var iv2=setInterval(function(){v+=step;if(v>=target){v=target;clearInterval(iv2);}"
        "el.textContent=Math.floor(v)+(el.getAttribute('data-count').indexOf('.')>-1?'.'+target.toString().split('.')[1]:'');},16);}"
        "var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting&&!started){started=true;run();}});},{threshold:.3});"
        "io.observe(el);});"
        "var f=document.getElementById('cform');"
        "if(f){f.addEventListener('submit',function(e){e.preventDefault();"
        "var t=document.createElement('div');t.textContent='Mensaje enviado correctamente.';"
        "t.style.cssText='position:fixed;bottom:1.6rem;right:1.6rem;background:" + primary + ";color:#fff;padding:.9rem 1.6rem;"
        "border-radius:14px;z-index:9999;transform:translateY(100px);opacity:0;transition:all .4s';"
        "document.body.appendChild(t);requestAnimationFrame(function(){t.style.transform='translateY(0)';t.style.opacity='1';});"
        "setTimeout(function(){t.style.transform='translateY(100px)';t.style.opacity='0';setTimeout(function(){t.remove();},400);},3200);"
        "f.reset();});}"
        "var type=document.querySelector('.hero-tag');"
        "if(type){var words=['Diseño','Código','Motion','Identidad','Producto'];var wi=0;"
        "setInterval(function(){wi=(wi+1)%words.length;type.style.opacity=.2;"
        "setTimeout(function(){type.textContent=words[wi];type.style.opacity=.55;},180);},2400);}"
        "document.querySelectorAll('[data-parallax]').forEach(function(el){"
        "var k=parseFloat(el.getAttribute('data-parallax'))||.1;"
        "function pa(){var r=el.getBoundingClientRect();var off=(r.top+ r.height/2 - window.innerHeight/2);"
        "el.style.transform='translateY('+(off*k*-1)+'px)';}"
        "addEventListener('scroll',function(){requestAnimationFrame(pa);},{passive:true});pa();});"
        "})();"
    )


# ──────────────────────────────────────────────────────────────────────
#  PREVIEW (Playwright screenshot) + SERVE
# ──────────────────────────────────────────────────────────────────────
def _preview(folder, player=None):
    folder = Path(folder)
    idx = folder / "index.html"
    if not idx.exists():
        return "No se encontró index.html en {}".format(folder)
    shot = folder / "preview.png"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="msedge", headless=True)
            except Exception:
                browser = p.chromium.launch(headless=True)
            pg = browser.new_page(viewport={"width": 1440, "height": 900})
            pg.goto(idx.resolve().as_uri(), wait_until="load", timeout=30000)
            pg.wait_for_timeout(2800)
            # scroll para revelar animaciones y capturar la página completa
            h = pg.evaluate("() => document.body.scrollHeight")
            for y in range(0, h, 700):
                pg.evaluate("(y) => scrollTo(0,y)", y)
                pg.wait_for_timeout(180)
            pg.evaluate("() => scrollTo(0,0)")
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(shot), full_page=True)
            browser.close()
        webbrowser.open(idx.resolve().as_uri())
        size = shot.stat().st_size if shot.exists() else 0
        return ("Preview renderizada y abierta en el navegador.\n"
                "Screenshot: {}\nTamaño: {} bytes".format(shot, size))
    except Exception as e:
        webbrowser.open(idx.resolve().as_uri())
        return ("No se pudo renderizar con Playwright ({}).\n"
                "Página abierta en el navegador de todos modos.".format(str(e)[:120]))


_SERVERS = {}


def _serve(folder, port, player=None):
    folder = str(Path(folder).resolve())
    if not Path(folder).exists():
        return "Carpeta no encontrada: {}".format(folder)
    import http.server
    import functools
    import threading

    if port in _SERVERS:
        return "Ya hay un servidor en el puerto {}".format(port)

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=folder)
    try:
        httpd = http.server.ThreadingHTTPServer(("0.0.0.0", port), handler)
    except OSError as e:
        return "No se pudo levantar el servidor en el puerto {}: {}".format(port, str(e)[:100])
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    _SERVERS[port] = httpd
    return ("Servidor activo en: http://127.0.0.1:{}  (folder: {})\n"
            "Accesible desde tu móvil con: http://<IP-local>:{}".format(port, folder, port))


def _stop_servers():
    for port, httpd in list(_SERVERS.items()):
        try:
            httpd.shutdown()
        except Exception:
            pass
    _SERVERS.clear()


# ──────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ──────────────────────────────────────────────────────────────────────
def web_designer(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "help").lower().strip()
    memory = _load_memory()

    if player:
        try:
            player.write_log("WebDesigner: {}".format(action))
        except Exception:
            pass

    if action in ("help", "ayuda"):
        return (
            "web_designer — Diseñador web profesional.\n"
            "  analyze url=...        → analiza un sitio de referencia (framework, colores, fuentes, animaciones)\n"
            "  create title= topic= reference_url= sections= folder= images=  → genera la página\n"
            "  preview folder=        → renderiza y saca screenshot (preview.png)\n"
            "  serve folder= port=    → servidor local para verla en el móvil\n"
            "  stop                   → detiene los servidores\n"
            "  memory                 → historial"
        )

    if action in ("analyze", "analizar"):
        url = parameters.get("url") or parameters.get("reference_url")
        if not url:
            return "Necesito el parámetro 'url' para analizar una referencia."
        brief = _analyze_reference(url)
        memory.setdefault("analyzed_urls", []).append({
            "url": brief.get("url", url), "framework": brief.get("framework"),
            "time": datetime.now().isoformat(),
        })
        memory["analyzed_urls"] = memory["analyzed_urls"][-30:]
        _save_memory(memory)
        return _format_brief(brief)

    if action in ("create", "crear", "generate"):
        return _create(parameters, player, memory)

    if action in ("preview", "ver"):
        folder = parameters.get("folder") or parameters.get("carpeta")
        if not folder:
            return "Necesito el parámetro 'folder' con la carpeta de la página."
        return _preview(folder, player)

    if action in ("serve", "servir"):
        folder = parameters.get("folder") or parameters.get("carpeta")
        port = int(parameters.get("port") or 8899)
        if not folder:
            return "Necesito el parámetro 'folder'."
        return _serve(folder, port, player)

    if action == "stop":
        _stop_servers()
        return "Servidores detenidos."

    if action in ("memory", "memoria"):
        h = memory.get("history", [])
        a = memory.get("analyzed_urls", [])
        lines = ["Web Designer — memoria:",
                 "  Páginas creadas: {}".format(memory.get("pages_created", 0))]
        if a:
            lines.append("  Referencias analizadas: {}".format(len(a)))
            for e in a[-5:]:
                lines.append("    - {} ({})".format(e["url"], e.get("framework")))
        if h:
            lines.append("  Últimas páginas:")
            for p_ in h[-5:]:
                lines.append("    - {} ({}) — {} / {}".format(
                    p_.get("title"), p_.get("topic"), p_.get("palette"), p_.get("font")))
        return "\n".join(lines)

    return web_designer({"action": "help"}, player)


def _create(parameters, player, memory):
    title = (parameters.get("title") or parameters.get("titulo") or "Mi Página").strip()
    topic = (parameters.get("topic") or parameters.get("tema") or title).strip()
    description = (parameters.get("description") or parameters.get("descripcion") or
                   "Bienvenido a {}".format(title))
    sections_param = parameters.get("sections") or parameters.get("content") or parameters.get("contenido")
    folder = parameters.get("folder") or parameters.get("carpeta")
    images = parameters.get("images")
    reference_url = parameters.get("reference_url") or parameters.get("reference")
    design_brief = parameters.get("design_brief")
    video_url = parameters.get("video_url") or parameters.get("video")
    low_topic = (topic or "").lower()

    brief = None
    if design_brief:
        try:
            if design_brief.lstrip().startswith("{"):
                brief = json.loads(design_brief)
            else:
                m = re.search(r"BRIEF_JSON:\s*(\{.*\})", design_brief, re.S)
                if m:
                    brief = json.loads(m.group(1))
        except Exception:
            brief = None
    elif reference_url:
        brief = _analyze_reference(reference_url)
        if "error" in brief:
            brief = None
        else:
            memory.setdefault("analyzed_urls", []).append({
                "url": brief.get("url", reference_url), "framework": brief.get("framework"),
                "time": datetime.now().isoformat()})
            memory["analyzed_urls"] = memory["analyzed_urls"][-30:]

    # ── Variedad de diseño: elegir combinación no repetida (aprendizaje) ──
    # Paleta: prioridad 1 = estilo forzado (design_style), 2 = referencia, 3 = tema (con anti-repetición)
    forced_style = (parameters.get("design_style") or parameters.get("style") or "").strip().lower()
    palette = None
    if forced_style and forced_style in _STYLE_PRESETS:
        pal_name, font_forced = _STYLE_PRESETS[forced_style]
        palette = next((x for x in PALETTES if x["name"] == pal_name), None)
    if not palette:
        palette = _pick_palette(low_topic, memory, brief)
    if not palette.get("fg"):
        palette["fg"] = "#f2f2f2"

    # Fuente: igual lógica. El preset de estilo fuerza su fuente de firma
    # (venciendo la anti-repetición) para que el estilo sea reconocible.
    if forced_style and forced_style in _STYLE_PRESETS:
        font_forced = _STYLE_PRESETS[forced_style][1]
        mapped = {f[0]: f for f in FONTS}
        font_name, font_url = mapped.get(font_forced) or _pick_font(low_topic, memory, brief, palette.get("name"))
    else:
        font_name, font_url = _pick_font(low_topic, memory, brief, palette.get("name"))

    # Animaciones: anti-repetición salvo que la referencia pida algo
    animations = _map_reference_animations(brief) if brief else None
    if not animations:
        used_anims = [tuple(u.get("value", [])) for u in memory.get("anims_used", [])][-4:]
        cand = [a for a in ANIM_SETS if tuple(a) not in used_anims]
        animations = random.choice(cand) if cand else random.choice(ANIM_SETS)
    if not animations:
        animations = ["reveal"]

    # Layout y fondo del sitio: también anti-repetición
    layout = _avoid_recent(memory, "layouts_used", LAYOUTS)
    bg_style = _avoid_recent(memory, "bgs_used", BG_STYLES)

    # registrar lo usado para que la próxima sea distinta
    memory.setdefault("palettes_used", []).append({"value": palette["name"], "time": datetime.now().isoformat()})
    memory["palettes_used"] = memory["palettes_used"][-40:]
    memory.setdefault("fonts_used", []).append({"value": font_name, "time": datetime.now().isoformat()})
    memory["fonts_used"] = memory["fonts_used"][-40:]
    memory.setdefault("layouts_used", []).append({"value": layout, "time": datetime.now().isoformat()})
    memory["layouts_used"] = memory["layouts_used"][-40:]
    memory.setdefault("anims_used", []).append({"value": animations, "time": datetime.now().isoformat()})
    memory["anims_used"] = memory["anims_used"][-40:]
    memory.setdefault("bgs_used", []).append({"value": bg_style, "time": datetime.now().isoformat()})
    memory["bgs_used"] = memory["bgs_used"][-40:]

    # cantidad de imágenes de galería
    n_images = 4
    if isinstance(images, (int, float)) and images > 0:
        n_images = int(images)
    elif isinstance(images, str) and images.strip().lstrip("+-").isdigit():
        n_images = int(images)

    # ── ¿Sitio multi-página o página única? ──
    pages_flag = (parameters.get("pages") or parameters.get("site") or "").lower().strip()
    multi = False
    if pages_flag in ("site", "multi", "sitio", "web", "completo", "all"):
        multi = True
    elif pages_flag in ("single", "pagina", "one", "1", "única", "unica"):
        multi = False
    elif reference_url:
        multi = False
    elif any(w in low_topic for w in ("veterin", "vet", "peluquer", "salon", "belleza", "restauran",
                                       "gym", "gimnasio", "fitness", "barber", "clinic", "consulta",
                                       "tienda", "shop", "cafe", "hotel", "farmacia", "panader",
                                       "estudio", "agencia", "consultor", "mascota", "animal")):
        multi = True
    else:
        multi = False

    if not folder:
        folder = str(_DEFAULT_OUT / "{}_{}".format(_slug(topic) or "pagina", datetime.now().strftime("%Y%m%d_%H%M%S")))
    folder = os.path.abspath(folder)
    os.makedirs(folder, exist_ok=True)

    if multi:
        return _create_site(player, memory, title, topic, description, sections_param, brief,
                            palette, font_name, font_url, animations, layout, bg_style, n_images,
                            folder, video_url)

    # ── Página única ──
    sections = _parse_sections(sections_param, topic, description)
    if not sections:
        sections = _fallback_sections(topic, description)
    elif not (sections[0].get("type") == "hero"):
        sections = [{"type": "hero", "title": title, "text": description}] + sections
    # asegurar contacto al final
    if not any(_classify_section(s, 1, 10) == "contact" for s in sections):
        sections.append({"type": "contact", "title": "Contacto", "text": "Escribinos y te respondemos pronto."})
    # asegurar imágenes: si no hay galería ni sección con fotos, agregar una
    if not any(_classify_section(s, 1, 10) == "gallery" for s in sections):
        idx = -1 if sections[-1].get("type") == "contact" else len(sections)
        sections.insert(idx, {"type": "gallery", "title": "Nuestro trabajo",
                              "text": "Algunas piezas seleccionadas.", "images": n_images})

    html = _assemble_page(title, topic, sections, palette, font_name, font_url, animations, brief,
                          layout=layout, nav_html="", bg_style=bg_style, video_url=video_url)
    fp = os.path.join(folder, "index.html")
    Path(fp).write_text(html, encoding="utf-8")
    # config de diseño para que ERIS pueda reutilizar
    meta = {
        "title": title, "topic": topic, "palette": palette["name"],
        "palette_colors": {k: palette[k] for k in ("bg", "fg", "primary", "secondary", "accent")},
        "font": font_name.replace("+", " "), "animations": animations,
        "layout": layout, "bg": bg_style,
        "framework_target": (brief or {}).get("framework"),
        "reference_url": (brief or {}).get("url"),
        "sections": [{"type": _classify_section(s, i, len(sections)), "title": s.get("title", "")}
                     for i, s in enumerate(sections)],
        "timestamp": datetime.now().isoformat(),
    }
    try:
        Path(folder, "design.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    memory["pages_created"] = memory.get("pages_created", 0) + 1
    memory.setdefault("history", []).append({
        "id": uuid.uuid4().hex[:8], "title": title, "topic": topic,
        "palette": palette["name"], "font": font_name.replace("+", " "),
        "folder": folder, "timestamp": time.time(), "kind": "single",
        "layout": layout, "bg": bg_style})
    memory["history"] = memory["history"][-20:]
    _save_memory(memory)

    try:
        webbrowser.open("file://{}".format(fp.replace("\\", "/")))
    except Exception:
        pass

    lines = [
        "✅ Página #{} creada:".format(memory["pages_created"]),
        "   {}  ({})".format(fp, len(html), ),
        "",
        "   Diseño: {} | Fuente: {} | Layout: {} | Fondo: {} | Animaciones: {}".format(
            palette["name"], font_name.replace("+", " "), layout, bg_style, ", ".join(animations)),
    ]
    if brief and not brief.get("error"):
        lines.append("   Referencia clonada: {} ({})".format(brief.get("url"), brief.get("framework")))
    if sections_param:
        lines.append("   Secciones: {}".format(len(sections)))
    lines.append("")
    lines.append("Abierta en el navegador. Para verla y revisarla: web_designer action=preview folder='{}'".format(folder))
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
#  SITIO MULTI-PÁGINA (index/servicios/nosotros/galería/contacto)
# ──────────────────────────────────────────────────────────────────────
def _site_nav(active_id=""):
    """Menú navegable entre páginas del sitio (resalta la página activa)."""
    links = []
    for pid, label in SITE_PAGES:
        href = "index.html" if pid == "index" else pid + ".html"
        cls = ' class="active"' if pid == active_id else ""
        links.append('<li><a href="{}"{}>{}</a></li>'.format(href, cls, label))
    return "".join(links)


def _bundle_for(topic):
    low = (topic or "").lower()
    for key, (kw, _, _, _, _) in CONTENT_BUNDLES.items():
        if any(w in low for w in kw) or key in low:
            return CONTENT_BUNDLES[key]
    return CONTENT_BUNDLES["tech"]


def _site_sections(page_id, topic, title, description, images_n):
    """Secciones curadas para cada página del sitio, con contenido real por tema."""
    _, kw, about, feats, adj = _bundle_for(topic)
    low = (topic or "").lower()
    vet = any(w in low for w in ("veterin", "vet", "mascota", "perro", "gato", "animal"))
    food = any(w in low for w in ("restauran", "cafe", "comida", "gastro", "panader"))
    gym = any(w in low for w in ("gym", "gimnasio", "fitness", "crossfit", "yoga"))
    beauty = any(w in low for w in ("peluquer", "salon", "belleza", "beauty", "barber", "estetica", "spa"))

    if vet:
        services = ["Consulta general", "Vacunación", "Cirugía menor", "Estética canina", "Emergencias 24h", "Estudios de laboratorio"]
        prices = [("Consulta general", "desde $25"), ("Vacunación", "desde $15"), ("Cirugía menor", "desde $120"),
                  ("Estética", "desde $30"), ("Emergencia", "desde $60"), ("Plan anual", "desde $180")]
        faqs = [("¿Necesito turno previo?", "Sí, así evitamos esperas y le damos atención completa a tu mascota."),
                ("¿Atienden emergencias?", "Contamos con guardia 24/7 todos los días del año."),
                ("¿Cuándo es la primera vacuna?", "A partir de las 6 semanas de vida, según el calendario.")]
        process = ["Agendamos tu turno", "Recibimos a tu mascota", "Diagnóstico y plan", "Seguimiento"]
        team = ["Médica veterinaria", "Cirujano", "Enfermera", "Estética", "Recepción"]
        values = adj
    elif food:
        services = ["Menú del día", "Reservas", "Eventos privados", "Take away", "Vinos", "Postres"]
        prices = [("Plato principal", "desde $18"), ("Menú completo", "desde $35"), ("Postre", "desde $8"),
                  ("Maridaje", "desde $22"), ("Menú infantil", "desde $14")]
        faqs = [("¿Hacen reservas?", "Sí, reservá online o por teléfono con 24h de anticipación."),
                ("¿Tienen opciones veganas?", "Tenemos un menú especial sin productos de origen animal."),
                ("¿Pueden organizar eventos?", "Contamos con salón privado para hasta 60 personas.")]
        process = ["Elegí tu experiencia", "Reservá tu mesa", "Disfrutá del servicio", "Feedback"]
        team = ["Chef", "Sous chef", "Sommelier", "Maître", "Pastelero"]
        values = adj
    elif gym:
        services = ["Crossfit", "Yoga", "Spinning", "Personal trainer", "Nutrición", "Clases grupales"]
        prices = [("Mensual", "desde $35"), ("Trimestral", "desde $90"), ("Anual", "desde $300"),
                  ("Personal trainer", "desde $20/sesión"), ("Plan pareja", "desde $55")]
        faqs = [("¿Necesito experiencia?", "No, tenemos clases para todos los niveles."),
                ("¿Hay prueba gratis?", "Sí, tu primera clase es gratis."),
                ("¿Puedo congelar mi plan?", "Podés pausar tu plan hasta 30 días por año.")]
        process = ["Conocé el espacio", "Elegí tu plan", "Entrená con nosotros", "Seguí tus resultados"]
        team = ["Head coach", "Instructora de yoga", "Nutricionista", "Coach de crossfit", "Recepción"]
        values = adj
    elif beauty:
        services = ["Corte y peinado", "Color y mechas", "Tratamientos capilares", "Barbería", "Manicura", "Peinados para eventos"]
        prices = [("Corte + lavado", "desde $20"), ("Color completo", "desde $60"), ("Mechas", "desde $75"),
                  ("Tratamiento", "desde $40"), ("Manicura", "desde $15"), ("Novia", "desde $120")]
        faqs = [("¿Debo reservar?", "Recomendamos turno, aunque aceptamos consulta sin cita."),
                ("¿Usan productos de calidad?", "Trabajamos solo con marcas profesionales."),
                ("¿Cuánto dura un color?", "Entre 6 y 8 semanas con el cuidado adecuado.")]
        process = ["Asesoría personalizada", "Elección del servicio", "Transformación", "Cuidado en casa"]
        team = ["Directora creativa", "Colorista", "Barbero", "Manicurista", "Recepcionista"]
        values = adj
    else:
        services = list(feats)[:6]
        prices = [("Servicio base", "desde $25"), ("Servicio estándar", "desde $45"), ("Servicio premium", "desde $80"),
                  ("Proyecto completo", "desde $250"), ("Consulta", "desde $15")]
        faqs = [("¿Cómo arranco?", "Escribinos y en menos de 24h te respondemos."),
                ("¿Hacen presupuestos?", "Sí, sin cargo y sin compromiso."),
                ("¿Cuál es el plazo?", "Depende del alcance; te lo damos por escrito.")]
        process = ["Contanos tu idea", "Recibí una propuesta", "Aprobación y avance", "Entrega y soporte"]
        team = ["Fundador", "Directora creativa", "Especialista", "Atención al cliente"]
        values = adj

    if page_id == "index":
        return [
            {"type": "hero", "title": title or topic, "text": description or about},
            {"type": "features", "title": "Servicios", "text": about, "items": services[:6]},
            {"type": "gallery", "title": "Nuestro trabajo", "text": "Momentos que nos enorgullecen.", "images": images_n},
            {"type": "stats", "title": "Cifras", "items": [
                ("12", "Años de experiencia"), ("4800", "Clientes felices"), ("98", "% de satisfacción"), ("24", "hs de atención")]},
            {"type": "testimonials", "title": "Opiniones", "text": "Lo que dicen nuestros clientes.", "items": [
                "Excelente atención, siempre se nota el cuidado por los detalles.",
                "El mejor equipo de la zona, super recomendados.",
                "Volvimos muchas veces y la calidad nunca bajó."]},
            {"type": "contact", "title": "Contacto", "text": "Escribinos y te respondemos pronto."},
        ]
    if page_id == "servicios":
        return [
            {"type": "subhero", "title": "Nuestros servicios", "text": about},
            {"type": "features", "title": "Todo lo que ofrecemos", "text": "Elegí el servicio que necesitás.", "items": services[:8]},
            {"type": "prices", "title": "Precios", "text": "Tarifas claras, sin sorpresas.", "items": prices},
            {"type": "process", "title": "Cómo trabajamos", "text": "Un proceso simple y transparente.", "items": process},
            {"type": "faq", "title": "Preguntas frecuentes", "text": "Resolvemos tus dudas.", "items": faqs},
            {"type": "contact", "title": "Reservá tu turno", "text": "Agendá tu visita hoy mismo."},
        ]
    if page_id == "nosotros":
        return [
            {"type": "subhero", "title": "Sobre nosotros", "text": "Conocé nuestra historia y nuestro equipo."},
            {"type": "about", "title": "Nuestra historia", "text": "Empezamos con una idea simple: {}".format(about)},
            {"type": "team", "title": "Nuestro equipo", "text": "Gente apasionada por lo que hace.", "items": team},
            {"type": "features", "title": "Nuestros valores", "text": "Lo que nos define.", "items": values[:6]},
            {"type": "gallery", "title": "Nuestro espacio", "text": "Así trabajamos.", "images": images_n},
            {"type": "contact", "title": "Sumate", "text": "¿Querés trabajar con nosotros?"},
        ]
    if page_id == "galeria":
        return [
            {"type": "subhero", "title": "Galería", "text": "Un vistazo a nuestro mundo."},
            {"type": "gallery", "title": "Trabajos recientes", "text": "Selección de nuestros mejores momentos.", "images": images_n + 3},
            {"type": "testimonials", "title": "Testimonios", "text": "Historias reales.", "items": [
                "Increíble experiencia, superaron mis expectativas.",
                "Atención de primera, lo recomiendo 100%.",
                "Profesionales de verdad, volveré seguro."]},
            {"type": "contact", "title": "Contacto", "text": "¿Querés saber más de nosotros?"},
        ]
    # contacto
    return [
        {"type": "subhero", "title": "Contacto", "text": "Estamos para ayudarte."},
        {"type": "contact", "title": "Escribinos", "text": "Respondemos en menos de 24 horas."},
        {"type": "features", "title": "Dónde estamos", "text": "Información útil para tu visita.", "items": [
            "Dirección: Av. Principal 123, Ciudad",
            "Horario: Lun a Sáb de 9 a 20hs",
            "Teléfono: +54 11 5555-1234",
            "Email: hola@{}".format(_slug(topic) + ".com" if _slug(topic) else "eris.com")]},
    ]


def _create_site(player, memory, title, topic, description, sections_param, brief, palette, font_name,
                 font_url, animations, layout, bg_style, images_n, folder, video_url):
    """Genera un sitio completo multi-página con menú que navega entre páginas."""
    pages = []
    for pid, label in SITE_PAGES:
        secs = _site_sections(pid, topic, title, description, images_n)
        if pid == "index" and sections_param:
            parsed = _parse_sections(sections_param, topic, description)
            if parsed:
                secs = parsed
                if not any(_classify_section(s, 1, 10) == "contact" for s in secs):
                    secs.append({"type": "contact", "title": "Contacto",
                                 "text": "Escribinos y te respondemos pronto."})
        page_title = title if pid == "index" else "{} — {}".format(title or topic, label)
        html = _assemble_page(page_title, topic, secs, palette, font_name, font_url, animations, brief,
                              layout=layout, nav_html=_site_nav(pid), bg_style=bg_style,
                              page_id=pid, video_url=video_url if pid == "index" else None, current=pid)
        fname = "index.html" if pid == "index" else pid + ".html"
        Path(folder, fname).write_text(html, encoding="utf-8")
        pages.append({"page": pid, "label": label, "file": fname, "size": len(html), "sections": len(secs)})

    # mapa del sitio para navegación offline y sitemap para SEO
    sitemap = "<?xml version='1.0' encoding='UTF-8'?>\n<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n"
    for pg in pages:
        sitemap += "  <url><loc>{}</loc></url>\n".format(pg["file"])
    sitemap += "</urlset>\n"
    try:
        Path(folder, "sitemap.xml").write_text(sitemap, encoding="utf-8")
    except Exception:
        pass

    meta = {
        "title": title, "topic": topic, "type": "site", "pages": pages,
        "palette": palette["name"],
        "palette_colors": {k: palette[k] for k in ("bg", "fg", "primary", "secondary", "accent")},
        "font": font_name.replace("+", " "), "animations": animations,
        "layout": layout, "bg": bg_style,
        "framework_target": (brief or {}).get("framework"),
        "reference_url": (brief or {}).get("url"),
        "timestamp": datetime.now().isoformat(),
    }
    try:
        Path(folder, "design.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    memory["pages_created"] = memory.get("pages_created", 0) + 1
    memory.setdefault("history", []).append({
        "id": uuid.uuid4().hex[:8], "title": title, "topic": topic,
        "palette": palette["name"], "font": font_name.replace("+", " "),
        "folder": folder, "timestamp": time.time(), "kind": "site",
        "layout": layout, "bg": bg_style, "n_pages": len(pages)})
    memory["history"] = memory["history"][-20:]
    _save_memory(memory)

    index_fp = os.path.join(folder, "index.html")
    try:
        webbrowser.open("file://{}".format(index_fp.replace("\\", "/")))
    except Exception:
        pass

    lines = [
        "✅ Sitio #{} creado ({} páginas):".format(memory["pages_created"], len(pages)),
        "   {}".format(folder),
        "",
        "   Diseño: {} | Fuente: {} | Layout: {} | Fondo: {} | Animaciones: {}".format(
            palette["name"], font_name.replace("+", " "), layout, bg_style, ", ".join(animations)),
    ]
    for pg in pages:
        lines.append("   - {} → {} ({} secciones, {} bytes)".format(pg["label"], pg["file"], pg["sections"], pg["size"]))
    if brief and not brief.get("error"):
        lines.append("   Referencia clonada: {} ({})".format(brief.get("url"), brief.get("framework")))
    lines.append("")
    lines.append("El menú navega entre las páginas. Abierta en el navegador.")
    return "\n".join(lines)
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    args = {}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            args[k.strip()] = v.strip()
    print(web_designer(args))
