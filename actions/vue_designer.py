"""
actions/vue_designer.py — Generador de proyectos web con Vue 3 (Vite).

Genera un proyecto Vue 3 completo y funcional (Vite + vue-router):
  - package.json, vite.config.js, index.html
  - src/main.js (directivas reveal/count globales), src/router.js, src/data.js
  - src/styles.css (mismo lenguaje visual que web_designer)
  - src/App.vue, src/PageView.vue
  - src/components/Nav.vue, Footer.vue, Section.vue (renderiza las 12 secciones)

Reutiliza el sistema de diseño de web_designer (paletas, fuentes, contenido,
memoria anti-repetición) para que cada proyecto sea distinto al anterior.
"""
import json
import os
import random
import re
import subprocess
import sys
import time
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path

# Reutilizamos diseño + memoria de web_designer (variedad global compartida)
from actions.web_designer import (
    PALETTES, FONTS, CONTENT_BUNDLES, LAYOUTS, ANIM_SETS, BG_STYLES, SITE_PAGES,
    _MEMORY_FILE, _DEFAULT_OUT,
    _load_memory, _save_memory, _avoid_recent,
    _slug, _parse_sections, _classify_section, _fallback_sections,
    _pick_palette, _pick_font, _map_reference_animations, _analyze_reference,
    _site_sections, _bundle_for, _STYLE_PRESETS,
)
# Helpers compartidos con los otros diseñadores
from actions.react_designer import (
    _npm, _wait_port, _url_for, _css, _serialize_sections, _js_escape,
)

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_DEV_PROCS = {}  # folder -> Popen
_DEFAULT_PORT = 5174


def _replace(template, **kw):
    for k, v in kw.items():
        template = template.replace("@@" + k + "@@", str(v))
    return template


# ──────────────────────────────────────────────────────────────────────
#  TEMPLATES DE ARCHIVOS
# ──────────────────────────────────────────────────────────────────────
_PKG_TEMPLATE = {
    "name": "@@slug@@",
    "private": True,
    "version": "1.0.0",
    "type": "module",
    "scripts": {
        "dev": "vite",
        "build": "vite build",
        "preview": "vite preview",
    },
    "dependencies": {
        "vue": "^3.5.13",
        "vue-router": "^4.5.0",
    },
    "devDependencies": {
        "@vitejs/plugin-vue": "^5.2.1",
        "vite": "^5.4.8",
    },
}

_VITE_CONFIG = """import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: @@port@@
  }
})
"""

_INDEX_HTML = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>@@title@@</title>
    <meta name="description" content="@@description@@" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=@@font_url@@&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
"""

_MAIN_JS = """import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles.css'

const app = createApp(App)

app.directive('reveal', {
  mounted(el) {
    el.classList.add('rv')
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          el.classList.add('on')
          io.disconnect()
        }
      },
      { threshold: 0.12 }
    )
    io.observe(el)
  },
})

app.directive('count', {
  mounted(el, binding) {
    const target = Number(binding.value) || 0
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return
        io.disconnect()
        const t0 = performance.now()
        const dur = 1300
        const step = (t) => {
          const p = Math.min((t - t0) / dur, 1)
          el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))).toLocaleString('es-AR')
          if (p < 1) requestAnimationFrame(step)
        }
        requestAnimationFrame(step)
      },
      { threshold: 0.4 }
    )
    io.observe(el)
  },
})

app.use(router)
app.mount('#app')
"""

_ROUTER_JS = """import { createRouter, createWebHistory } from 'vue-router'
import PageView from './PageView.vue'
import { pages } from './data'

const routes = pages.map((p) => ({
  path: p.id === 'index' ? '/' : '/' + p.id,
  name: p.id,
  component: PageView,
  props: { pageId: p.id },
}))
routes.push({ path: '/:pathMatch(.*)*', redirect: '/' })

export default createRouter({
  history: createWebHistory(),
  routes,
})
"""

_DATA_JS = """export const site = @@site@@;

export const theme = @@theme@@;

export const pages = @@pages@@;
"""


def _data_js(theme, site_name, pages):
    return _DATA_JS.replace("@@site@@", json.dumps(site_name, ensure_ascii=False)) \
                   .replace("@@theme@@", json.dumps(theme, ensure_ascii=False)) \
                   .replace("@@pages@@", json.dumps(pages, ensure_ascii=False))


_APP_VUE = """<script setup>
import { theme } from './data'
import Nav from './components/Nav.vue'
import Footer from './components/Footer.vue'
</script>

<template>
  <div class="site" :class="['anim-' + theme.anim, 'bg-' + theme.bgStyle]">
    <Nav />
    <main>
      <router-view />
    </main>
    <Footer />
  </div>
</template>
"""

_PAGEVIEW_VUE = """<script setup>
import { computed } from 'vue'
import { pages } from './data'
import Section from './components/Section.vue'

const props = defineProps({
  pageId: { type: String, default: 'index' },
})
const page = computed(() => pages.find((p) => p.id === props.pageId) || pages[0])
</script>

<template>
  <Section v-for="(sec, i) in page.sections" :key="i" :s="sec" />
</template>
"""

_NAV_VUE = """<script setup>
import { RouterLink } from 'vue-router'
import { pages, site } from '../data'
</script>

<template>
  <header class="nav">
    <div class="nav-inner container">
      <RouterLink class="brand" to="/">{{ site }}</RouterLink>
      <nav>
        <RouterLink
          v-for="p in pages"
          :key="p.id"
          :to="p.id === 'index' ? '/' : '/' + p.id"
          active-class="active"
        >
          {{ p.label }}
        </RouterLink>
      </nav>
    </div>
  </header>
</template>
"""

_FOOTER_VUE = """<script setup>
import { RouterLink } from 'vue-router'
import { pages, site } from '../data'
</script>

<template>
  <footer class="footer">
    <div class="container footer-inner">
      <div>
        <span class="brand">{{ site }}</span>
        <p class="muted">Hecho con Vue por ERIS.</p>
      </div>
      <nav class="footer-nav">
        <RouterLink
          v-for="p in pages"
          :key="p.id"
          :to="p.id === 'index' ? '/' : '/' + p.id"
        >
          {{ p.label }}
        </RouterLink>
      </nav>
    </div>
  </footer>
</template>
"""

_SECTION_VUE = """<script setup>
import { ref } from 'vue'
import { theme } from '../data'

defineProps({ s: { type: Object, required: true } })

const open = ref(0)
const toggle = (i) => {
  open.value = open.value === i ? -1 : i
}
const sent = ref(false)
const send = () => {
  sent.value = true
}
const split = theme.layout === 'split' || theme.layout === 'editorial'
const hideImg = (e) => {
  e.target.style.display = 'none'
}
const initials = (name) =>
  name
    .split(/\\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
</script>

<template>
  <!-- HERO -->
  <section v-if="s.type === 'hero'" class="hero" :class="'hero-' + theme.layout">
    <div class="container hero-inner">
      <div class="hero-text">
        <p v-if="s.badges && s.badges[0]" class="kicker">{{ s.badges[0] }}</p>
        <h1>{{ s.title }}</h1>
        <p class="lead">{{ s.text }}</p>
        <div class="hero-cta">
          <a class="btn btn-grad" href="#contact">Empezar ahora</a>
          <a class="btn btn-ghost" href="#services">Ver servicios</a>
        </div>
      </div>
      <div v-if="split" class="hero-media">
        <img :src="s.media" :alt="s.title" @error="hideImg" />
      </div>
    </div>
  </section>

  <!-- SUBHERO -->
  <section v-else-if="s.type === 'subhero'" class="subhero">
    <div class="container">
      <p class="kicker">Conocé más</p>
      <h1>{{ s.title }}</h1>
      <p class="lead">{{ s.text }}</p>
    </div>
  </section>

  <!-- FEATURES -->
  <section v-else-if="s.type === 'features'" class="sec features" id="services">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Servicios</p>
        <h2>{{ s.title }}</h2>
        <p v-if="s.text">{{ s.text }}</p>
      </div>
      <div class="grid cards">
        <div
          v-for="(it, i) in s.items || []"
          :key="i"
          class="card"
          v-reveal
          :style="{ transitionDelay: i * 60 + 'ms' }"
        >
          <span class="card-num">0{{ i + 1 }}</span>
          <h3>{{ it }}</h3>
        </div>
      </div>
    </div>
  </section>

  <!-- GALLERY -->
  <section v-else-if="s.type === 'gallery'" class="sec gallery">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Trabajos</p>
        <h2>{{ s.title }}</h2>
        <p v-if="s.text">{{ s.text }}</p>
      </div>
      <div class="gallery-grid">
        <figure
          v-for="(img, i) in s.images || []"
          :key="i"
          class="shot"
          v-reveal
          :style="{ transitionDelay: (i % 4) * 60 + 'ms' }"
        >
          <img :src="img" :alt="s.title + ' ' + (i + 1)" loading="lazy" @error="hideImg" />
        </figure>
      </div>
    </div>
  </section>

  <!-- STATS -->
  <section v-else-if="s.type === 'stats'" class="sec stats-sec">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Cifras</p>
        <h2>{{ s.title }}</h2>
      </div>
      <div class="stats">
        <div
          v-for="(it, i) in s.items || []"
          :key="i"
          class="stat"
          v-reveal
          :style="{ transitionDelay: i * 70 + 'ms' }"
        >
          <span class="stat-num" v-count="it.value">0</span>
          <span class="stat-label">{{ it.label }}</span>
        </div>
      </div>
    </div>
  </section>

  <!-- TESTIMONIALS -->
  <section v-else-if="s.type === 'testimonials'" class="sec">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Opiniones</p>
        <h2>{{ s.title }}</h2>
        <p v-if="s.text">{{ s.text }}</p>
      </div>
      <div class="grid quotes">
        <blockquote
          v-for="(it, i) in s.items || []"
          :key="i"
          class="quote"
          v-reveal
          :style="{ transitionDelay: i * 80 + 'ms' }"
        >
          <span class="quote-mark">"</span>
          <p>{{ it }}</p>
        </blockquote>
      </div>
    </div>
  </section>

  <!-- FAQ -->
  <section v-else-if="s.type === 'faq'" class="sec">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">FAQ</p>
        <h2>{{ s.title }}</h2>
        <p v-if="s.text">{{ s.text }}</p>
      </div>
      <div class="faq">
        <div
          v-for="(it, i) in s.items || []"
          :key="i"
          class="faq-item"
          :class="{ open: open === i }"
          v-reveal
          :style="{ transitionDelay: i * 50 + 'ms' }"
        >
          <button class="faq-q" @click="toggle(i)">
            <span>{{ it.q }}</span>
            <span class="faq-chev">+</span>
          </button>
          <div class="faq-a">{{ it.a }}</div>
        </div>
      </div>
    </div>
  </section>

  <!-- PRICES -->
  <section v-else-if="s.type === 'prices'" class="sec prices">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Tarifas</p>
        <h2>{{ s.title }}</h2>
        <p v-if="s.text">{{ s.text }}</p>
      </div>
      <div class="grid cards">
        <div
          v-for="(it, i) in s.items || []"
          :key="i"
          class="card price"
          :class="{ hot: i === 1 }"
          v-reveal
          :style="{ transitionDelay: i * 60 + 'ms' }"
        >
          <h3>{{ it.name }}</h3>
          <p class="price-tag">{{ it.price }}</p>
          <a class="btn btn-ghost" href="#contact">Consultar</a>
        </div>
      </div>
    </div>
  </section>

  <!-- PROCESS -->
  <section v-else-if="s.type === 'process'" class="sec">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Cómo trabajamos</p>
        <h2>{{ s.title }}</h2>
        <p v-if="s.text">{{ s.text }}</p>
      </div>
      <div class="steps">
        <div
          v-for="(it, i) in s.items || []"
          :key="i"
          class="step"
          v-reveal
          :style="{ transitionDelay: i * 70 + 'ms' }"
        >
          <span class="step-num">{{ i + 1 }}</span>
          <p>{{ it }}</p>
        </div>
      </div>
    </div>
  </section>

  <!-- TEAM -->
  <section v-else-if="s.type === 'team'" class="sec">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Equipo</p>
        <h2>{{ s.title }}</h2>
        <p v-if="s.text">{{ s.text }}</p>
      </div>
      <div class="grid team">
        <div
          v-for="(it, i) in s.items || []"
          :key="i"
          class="member"
          v-reveal
          :style="{ transitionDelay: i * 60 + 'ms' }"
        >
          <span class="avatar">{{ initials(it) }}</span>
          <p>{{ it }}</p>
        </div>
      </div>
    </div>
  </section>

  <!-- ABOUT -->
  <section v-else-if="s.type === 'about'" class="sec about">
    <div class="container about-inner">
      <div class="about-card" v-reveal>
        <p class="kicker">Nosotros</p>
        <h2>{{ s.title }}</h2>
        <p v-if="s.text">{{ s.text }}</p>
      </div>
    </div>
  </section>

  <!-- CONTACT -->
  <section v-else-if="s.type === 'contact'" class="sec contact" id="contact">
    <div class="container contact-inner">
      <div class="contact-info">
        <p class="kicker">Contacto</p>
        <h2>{{ s.title }}</h2>
        <p v-if="s.text">{{ s.text }}</p>
        <ul class="contact-list">
          <li>Dirección: Av. Principal 123, Ciudad</li>
          <li>Horario: Lun a Sáb de 9 a 20hs</li>
          <li>Teléfono: +54 11 5555-1234</li>
        </ul>
      </div>
      <form class="contact-form" @submit.prevent="send">
        <input type="text" placeholder="Tu nombre" required />
        <input type="email" placeholder="Tu email" required />
        <textarea rows="4" placeholder="Contanos tu idea..." required></textarea>
        <button class="btn btn-grad" type="submit">
          {{ sent ? '¡Gracias! Te respondemos pronto' : 'Enviar mensaje' }}
        </button>
      </form>
    </div>
  </section>
</template>
"""


def _theme_anim(animations):
    if "float" in animations or "kenburns" in animations:
        return "float"
    return "reveal"


# ──────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ──────────────────────────────────────────────────────────────────────
def vue_designer(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "help").lower().strip()
    memory = _load_memory()

    if player:
        try:
            player.write_log("VueDesigner: {}".format(action))
        except Exception:
            pass

    if action in ("help", "ayuda"):
        return (
            "vue_designer — Diseñador de webs con Vue 3 (Vite).\n"
            "  create title= topic= description= sections= folder= pages= images=  → genera el proyecto Vue completo y lo abre\n"
            "  install folder=       → npm install\n"
            "  dev folder= port=     → levanta el dev server (puerto 5174)\n"
            "  build folder=         → compila a producción (dist/)\n"
            "  preview folder=       → renderiza la app y saca screenshots\n"
            "  stop                  → detiene los dev servers\n"
            "  memory                → historial"
        )

    if action in ("create", "crear", "generate"):
        return _create(parameters, player, memory)

    if action in ("install", "instalar"):
        folder = parameters.get("folder")
        if not folder:
            return "Necesito el parámetro 'folder'."
        return _install(folder)

    if action in ("dev", "desarrollo"):
        folder = parameters.get("folder")
        if not folder:
            return "Necesito el parámetro 'folder'."
        return _dev(folder, int(parameters.get("port") or _DEFAULT_PORT))

    if action in ("build", "compilar"):
        folder = parameters.get("folder")
        if not folder:
            return "Necesito el parámetro 'folder'."
        return _build(folder)

    if action in ("preview", "ver"):
        folder = parameters.get("folder")
        if not folder:
            return "Necesito el parámetro 'folder'."
        return _preview(folder, player)

    if action == "stop":
        for folder, proc in list(_DEV_PROCS.items()):
            try:
                proc.terminate()
            except Exception:
                pass
        _DEV_PROCS.clear()
        return "Dev servers detenidos."

    if action in ("memory", "memoria"):
        h = [x for x in memory.get("history", []) if x.get("kind", "").startswith("vue")]
        lines = ["Vue Designer — memoria:",
                 "  Proyectos creados: {}".format(len(h))]
        for p_ in h[-5:]:
            lines.append("    - {} ({}) — {} / {}".format(
                p_.get("title"), p_.get("topic"), p_.get("palette"), p_.get("font")))
        return "\n".join(lines)

    return vue_designer({"action": "help"}, player)


def _create(parameters, player, memory):
    title = (parameters.get("title") or parameters.get("titulo") or "Mi App").strip()
    topic = (parameters.get("topic") or parameters.get("tema") or title).strip()
    description = (parameters.get("description") or parameters.get("descripcion") or
                   "Bienvenido a {}".format(title))
    sections_param = parameters.get("sections") or parameters.get("content")
    folder = parameters.get("folder")
    images = parameters.get("images")
    reference_url = parameters.get("reference_url") or parameters.get("reference")
    design_brief = parameters.get("design_brief")
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

    # ── Variedad de diseño (aprendizaje compartido) ──
    forced_style = (parameters.get("design_style") or parameters.get("style") or "").strip().lower()
    palette = None
    if forced_style and forced_style in _STYLE_PRESETS:
        pal_name, font_forced = _STYLE_PRESETS[forced_style]
        palette = next((x for x in PALETTES if x["name"] == pal_name), None)
    if not palette:
        palette = _pick_palette(low_topic, memory, brief)
    if not palette.get("fg"):
        palette["fg"] = "#f2f2f2"

    if forced_style and forced_style in _STYLE_PRESETS:
        mapped = {f[0]: f for f in FONTS}
        font_forced = _STYLE_PRESETS[forced_style][1]
        font_name, font_url = mapped.get(font_forced) or _pick_font(low_topic, memory, brief, palette.get("name"))
    else:
        font_name, font_url = _pick_font(low_topic, memory, brief, palette.get("name"))

    animations = _map_reference_animations(brief) if brief else None
    if not animations:
        used_anims = [tuple(u.get("value", [])) for u in memory.get("anims_used", [])][-4:]
        cand = [a for a in ANIM_SETS if tuple(a) not in used_anims]
        animations = random.choice(cand) if cand else random.choice(ANIM_SETS)
    if not animations:
        animations = ["reveal"]

    layout = _avoid_recent(memory, "layouts_used", LAYOUTS)
    bg_style = _avoid_recent(memory, "bgs_used", BG_STYLES)

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

    n_images = 4
    if isinstance(images, (int, float)) and images > 0:
        n_images = int(images)
    elif isinstance(images, str) and images.strip().lstrip("+-").isdigit():
        n_images = int(images)

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
        folder = str(_DEFAULT_OUT / "{}_{}".format(_slug(topic) or "vue", datetime.now().strftime("%Y%m%d_%H%M%S")))
    folder = os.path.abspath(folder)
    os.makedirs(folder, exist_ok=True)

    if multi:
        pages_data = []
        for pid, label in SITE_PAGES:
            secs = _site_sections(pid, topic, title, description, n_images)
            if pid == "index" and sections_param:
                parsed = _parse_sections(sections_param, topic, description)
                if parsed:
                    secs = parsed
                    if not any(_classify_section(s, 1, 10) == "contact" for s in secs):
                        secs.append({"type": "contact", "title": "Contacto",
                                     "text": "Escribinos y te respondemos pronto."})
            pages_data.append({
                "id": pid, "label": label,
                "sections": _serialize_sections(secs, _slug(topic) + pid[:3], topic),
            })
        kind = "vue-site"
        n_pages = len(pages_data)
    else:
        sections = _parse_sections(sections_param, topic, description) if sections_param else None
        if not sections:
            sections = _fallback_sections(topic, description)
        elif not (sections[0].get("type") == "hero"):
            sections = [{"type": "hero", "title": title, "text": description}] + sections
        if not any(_classify_section(s, 1, 10) == "contact" for s in sections):
            sections.append({"type": "contact", "title": "Contacto",
                             "text": "Escribinos y te respondemos pronto."})
        if not any(_classify_section(s, 1, 10) == "gallery" for s in sections):
            idx = -1 if sections[-1].get("type") == "contact" else len(sections)
            sections.insert(idx, {"type": "gallery", "title": "Nuestro trabajo",
                                  "text": "Algunas piezas seleccionadas.", "images": n_images})
        pages_data = [{
            "id": "index", "label": "Inicio",
            "sections": _serialize_sections(sections, _slug(topic) or "site", topic),
        }]
        kind = "vue-single"
        n_pages = 1

    theme = {
        "name": palette["name"],
        "bg": palette["bg"], "fg": palette["fg"],
        "primary": palette["primary"], "secondary": palette["secondary"],
        "accent": palette["accent"],
        "font": font_name.replace("+", " "),
        "layout": layout,
        "bgStyle": bg_style,
        "anim": _theme_anim(animations),
    }

    _write_project(folder, title, description, topic, font_name, font_url, theme, pages_data,
                   palette, animations, layout, bg_style)

    memory["pages_created"] = memory.get("pages_created", 0) + 1
    memory.setdefault("history", []).append({
        "id": uuid.uuid4().hex[:8], "title": title, "topic": topic,
        "palette": palette["name"], "font": font_name.replace("+", " "),
        "folder": folder, "timestamp": time.time(), "kind": kind,
        "layout": layout, "bg": bg_style, "n_pages": n_pages})
    memory["history"] = memory["history"][-20:]
    _save_memory(memory)

    lines = [
        "✅ Proyecto Vue #{} creado ({} páginas):".format(memory["pages_created"], n_pages),
        "   {}".format(folder),
        "",
        "   Diseño: {} | Fuente: {} | Layout: {} | Fondo: {} | Animaciones: {}".format(
            palette["name"], font_name.replace("+", " "), layout, bg_style, ", ".join(animations)),
        "   Vue 3 + Vite · {} páginas con componentes .vue".format(n_pages),
    ]
    if brief and not brief.get("error"):
        lines.append("   Referencia clonada: {} ({})".format(brief.get("url"), brief.get("framework")))
    lines.append("")
    lines.append("Instalando dependencias con npm...")
    res = _install(folder)
    lines.append(res)
    if "✅" in res:
        dev = _dev(folder)
        lines.append(dev)
    lines.append("")
    lines.append("Para renderizar y revisar: vue_designer action=preview folder='{}'".format(folder))
    return "\n".join(lines)


def _write_project(folder, title, description, topic, font_name, font_url, theme, pages_data,
                   palette, animations, layout, bg_style):
    (Path(folder) / "src").mkdir(parents=True, exist_ok=True)
    (Path(folder) / "src" / "components").mkdir(parents=True, exist_ok=True)

    slug = _slug(topic) or "vue-app"
    port = _DEFAULT_PORT

    def j(obj):
        return json.dumps(obj, indent=2, ensure_ascii=False)

    (Path(folder) / "package.json").write_text(
        _replace(j(_PKG_TEMPLATE), slug=slug), encoding="utf-8")
    (Path(folder) / "vite.config.js").write_text(
        _replace(_VITE_CONFIG, port=port), encoding="utf-8")
    (Path(folder) / "index.html").write_text(
        _replace(_INDEX_HTML, title=title, description=description, font_url=font_url), encoding="utf-8")
    (Path(folder) / "src" / "main.js").write_text(_MAIN_JS, encoding="utf-8")
    (Path(folder) / "src" / "router.js").write_text(_ROUTER_JS, encoding="utf-8")
    (Path(folder) / "src" / "data.js").write_text(_data_js(theme, title, pages_data), encoding="utf-8")
    (Path(folder) / "src" / "styles.css").write_text(
        _css(theme, font_name.replace("+", " ")), encoding="utf-8")
    (Path(folder) / "src" / "App.vue").write_text(_APP_VUE, encoding="utf-8")
    (Path(folder) / "src" / "PageView.vue").write_text(_PAGEVIEW_VUE, encoding="utf-8")
    (Path(folder) / "src" / "components" / "Nav.vue").write_text(_NAV_VUE, encoding="utf-8")
    (Path(folder) / "src" / "components" / "Footer.vue").write_text(_FOOTER_VUE, encoding="utf-8")
    (Path(folder) / "src" / "components" / "Section.vue").write_text(_SECTION_VUE, encoding="utf-8")

    meta = {
        "title": title, "topic": topic, "type": "vue", "framework": "vue3+vite",
        "pages": [{"page": p["id"], "label": p["label"]} for p in pages_data],
        "palette": palette["name"],
        "palette_colors": {k: palette[k] for k in ("bg", "fg", "primary", "secondary", "accent")},
        "font": font_name.replace("+", " "), "animations": animations,
        "layout": layout, "bg": bg_style,
        "timestamp": datetime.now().isoformat(),
    }
    try:
        (Path(folder) / "design.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _install(folder):
    folder = str(Path(folder).resolve())
    if not Path(folder, "package.json").exists():
        return "No hay package.json en {}".format(folder)
    try:
        res = _npm(["install", "--no-audit", "--no-fund"], cwd=folder, timeout=600)
    except subprocess.TimeoutExpired:
        return "El npm install tardó demasiado. Podés reintentar con vue_designer action=install folder='{}'".format(folder)
    if res.returncode == 0:
        return "✅ npm install completado (node_modules listo)."
    tail = (res.stdout or "")[-1200:]
    return "⚠️ npm install falló:\n{}".format(tail)


def _dev(folder, port=_DEFAULT_PORT):
    folder = str(Path(folder).resolve())
    if folder in _DEV_PROCS and _DEV_PROCS[folder].poll() is None:
        return "Dev server ya activo en http://127.0.0.1:{}".format(port)
    if not Path(folder, "node_modules").exists():
        inst = _install(folder)
        if "✅" not in inst:
            return inst
    try:
        proc = subprocess.Popen(
            ["cmd", "/c", "npm", "run", "dev", "--", "--port", str(port), "--strictPort"],
            cwd=folder,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_CREATE_NO_WINDOW,
        )
    except Exception as e:
        return "No se pudo levantar Vite: {}".format(str(e)[:120])
    _DEV_PROCS[folder] = proc
    if not _wait_port(port, timeout=90):
        try:
            proc.terminate()
        except Exception:
            pass
        return "Vite no respondió en el puerto {}. Revisá con vue_designer action=dev folder='{}'".format(port, folder)
    try:
        webbrowser.open("http://127.0.0.1:{}".format(port))
    except Exception:
        pass
    return "Dev server activo: http://127.0.0.1:{}  (folder: {})".format(port, folder)


def _build(folder):
    folder = str(Path(folder).resolve())
    if not Path(folder, "package.json").exists():
        return "No hay package.json en {}".format(folder)
    try:
        res = _npm(["run", "build"], cwd=folder, timeout=600)
    except subprocess.TimeoutExpired:
        return "El build tardó demasiado."
    if res.returncode == 0:
        dist = Path(folder, "dist")
        size = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file()) if dist.exists() else 0
        return "✅ Build completado en {}/dist ({} bytes)".format(folder, size)
    tail = (res.stdout or "")[-1200:]
    return "⚠️ Build falló:\n{}".format(tail)


def _preview(folder, player=None):
    folder = str(Path(folder).resolve())
    if not Path(folder, "package.json").exists():
        return "No hay proyecto Vue en {}".format(folder)
    port = _DEFAULT_PORT
    dev = _dev(folder, port)
    if "http" not in dev:
        return dev
    shots = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="msedge", headless=True)
            except Exception:
                browser = p.chromium.launch(headless=True)
            pg = browser.new_page(viewport={"width": 1440, "height": 900})
            base = "http://127.0.0.1:{}".format(port)
            routes = ["/"]
            data_fp = Path(folder, "src", "data.js")
            if data_fp.exists():
                try:
                    txt = data_fp.read_text("utf-8")
                    for m in re.finditer(r'"id":\s*"(index|servicios|nosotros|galeria|contacto)"', txt):
                        rid = m.group(1)
                        if rid != "index" and "/" + rid not in routes:
                            routes.append("/" + rid)
                except Exception:
                    pass
            for r in routes:
                try:
                    pg.goto(base + r, wait_until="load", timeout=30000)
                    pg.wait_for_timeout(1600)
                    h = pg.evaluate("() => document.body.scrollHeight")
                    for y in range(0, h, 700):
                        pg.evaluate("(y) => scrollTo(0,y)", y)
                        pg.wait_for_timeout(160)
                    pg.evaluate("() => scrollTo(0,0)")
                    pg.wait_for_timeout(400)
                    shot = Path(folder) / ("preview" + ("" if r == "/" else r.strip("/")) + ".png")
                    pg.screenshot(path=str(shot), full_page=True)
                    shots.append(str(shot))
                except Exception as e:
                    shots.append("  {} → error: {}".format(r, str(e)[:80]))
            browser.close()
    except Exception as e:
        return "No se pudo renderizar con Playwright ({}).\nDev server activo en http://127.0.0.1:{}".format(str(e)[:120], port)
    lines = ["Vue renderizada y abierta en el navegador (http://127.0.0.1:{}).".format(port),
             "Screenshots:"]
    lines.extend("  " + s for s in shots)
    return "\n".join(lines)


if __name__ == "__main__":
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
    print(vue_designer(args))
