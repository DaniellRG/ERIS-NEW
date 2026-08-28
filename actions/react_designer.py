"""
actions/react_designer.py — Generador de proyectos web con React (Vite).

Genera un proyecto Vite + React completo y funcional:
  - package.json, vite.config.js, index.html
  - src/main.jsx, src/App.jsx (router), src/data.js, src/index.css
  - src/components/sections.jsx (componentes React por sección)

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

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_DEV_PROCS = {}  # folder -> Popen


def _npm(cmd, cwd, timeout=600):
    """Ejecuta npm a través de cmd (evita el bloqueo de .ps1 por ExecutionPolicy)."""
    return subprocess.run(
        ["cmd", "/c", "npm"] + cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


# ──────────────────────────────────────────────────────────────────────
#  HELPERS DE CONTENIDO
# ──────────────────────────────────────────────────────────────────────
def _url_for(p):
    return "https://picsum.photos/seed/{}".format(p)


def _page_sections(page_id, topic, title, description, images_n, sections_param, multi):
    if multi:
        secs = _site_sections(page_id, topic, title, description, images_n)
        if page_id == "index" and sections_param:
            parsed = _parse_sections(sections_param, topic, description)
            if parsed:
                secs = parsed
                if not any(_classify_section(s, 1, 10) == "contact" for s in secs):
                    secs.append({"type": "contact", "title": "Contacto",
                                 "text": "Escribinos y te respondemos pronto."})
        return secs
    return None


def _serialize_sections(secs, seed, topic):
    """Convierte secciones (dicts de web_designer) a objetos JSON usables por React."""
    out = []
    for s in secs:
        stype = s.get("type", "text")
        item = {"type": stype, "title": s.get("title", ""), "text": s.get("text", "")}
        if stype == "hero":
            item["media"] = _url_for("{}hero".format(seed))
            item["badges"] = ["Elegí {}".format(topic), "Calidad garantizada", "Hoy mismo"]
        elif stype == "subhero":
            item["items"] = s.get("items", [])
        elif stype == "gallery":
            n = int(s.get("images") or 4)
            item["images"] = [_url_for("{}{}".format(seed, i)) for i in range(n)]
        elif stype in ("features", "process", "team"):
            item["items"] = s.get("items", [])
        elif stype == "stats":
            item["items"] = []
            for v, l in s.get("items", []):
                sv = str(v)
                m = re.match(r"(\d[\d,.]*)", sv)
                base = int(m.group(1).replace(",", "").replace(".", "")) if m else 0
                item["items"].append({"value": base, "suffix": sv[m.end():] if m else sv,
                                      "label": str(l)})
        elif stype == "testimonials":
            item["items"] = s.get("items", [])
        elif stype == "prices":
            item["items"] = [{"name": n, "price": p} for n, p in s.get("items", [])]
        elif stype == "faq":
            item["items"] = [{"q": q, "a": a} for q, a in s.get("items", [])]
        elif stype == "contact":
            item["text"] = s.get("text", "Escribinos y te respondemos pronto.")
        out.append(item)
    return out


def _js_escape(text):
    return str(text).replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


# ──────────────────────────────────────────────────────────────────────
#  TEMPLATES DE ARCHIVOS
# ──────────────────────────────────────────────────────────────────────
_PKG_TEMPLATE = """{{
  "name": "{slug}",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2"
  }},
  "devDependencies": {{
    "@vitejs/plugin-react": "^4.3.2",
    "vite": "^5.4.8"
  }}
}}
"""

_VITE_CONFIG = """import {{ defineConfig }} from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({{
  plugins: [react()],
  server: {{
    host: '0.0.0.0',
    port: {port}
  }}
}})
"""

_INDEX_HTML = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <meta name="description" content="{description}" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family={font_url}&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""

_MAIN_JSX = """import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
"""


def _data_js(theme, site_name, pages):
    lines = []
    lines.append("export const site = " + json.dumps(site_name, ensure_ascii=False))
    lines.append("")
    lines.append("export const theme = " + json.dumps(theme, ensure_ascii=False))
    lines.append("")
    lines.append("export const pages = " + json.dumps(pages, ensure_ascii=False))
    lines.append("")
    return "\n".join(lines)


_APP_JSX = """import { Routes, Route } from 'react-router-dom'
import { pages, theme } from './data.js'
import { Nav, Footer, Section } from './components/sections.jsx'

function Page({ sections }) {
  return (
    <>
      {sections.map((s, i) => (
        <Section key={i} s={s} />
      ))}
    </>
  )
}

export default function App() {
  const home = pages.find((p) => p.id === 'index')
  return (
    <div className={'site anim-' + theme.anim + ' bg-' + theme.bgStyle}>
      <Nav />
      <main>
        <Routes>
          {pages.map((p) => (
            <Route
              key={p.id}
              path={p.id === 'index' ? '/' : '/' + p.id}
              element={<Page sections={p.sections} />}
            />
          ))}
          <Route path="*" element={<Page sections={home.sections} />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
"""

_SECTIONS_JSX = """import { useState, useEffect, useRef } from 'react'
import { NavLink } from 'react-router-dom'
import { site, pages, theme } from '../data.js'

function Reveal({ children, delay = 0 }) {
  const ref = useRef(null)
  const [on, setOn] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setOn(true)
          io.disconnect()
        }
      },
      { threshold: 0.12 }
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return (
    <div ref={ref} className={'rv' + (on ? ' on' : '')} style={{ transitionDelay: delay + 'ms' }}>
      {children}
    </div>
  )
}

export function Nav() {
  return (
    <header className="nav">
      <div className="nav-inner container">
        <a className="brand" href="/">
          {site}
        </a>
        <nav>
          {pages.map((p) => (
            <NavLink
              key={p.id}
              to={p.id === 'index' ? '/' : '/' + p.id}
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              {p.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}

function Kicker({ t }) {
  return t ? <p className="kicker">{t}</p> : null
}

function Hero({ s }) {
  const split = theme.layout === 'split' || theme.layout === 'editorial'
  return (
    <section className={'hero hero-' + theme.layout}>
      <div className="container hero-inner">
        <div className="hero-text">
          <Kicker t={s.badges?.[0]} />
          <h1>{s.title}</h1>
          <p className="lead">{s.text}</p>
          <div className="hero-cta">
            <a className="btn btn-grad" href="#contact">
              Empezar ahora
            </a>
            <a className="btn btn-ghost" href="#services">
              Ver servicios
            </a>
          </div>
        </div>
        {split && (
          <div className="hero-media">
            <img src={s.media} alt={s.title} loading="eager" onError={(e) => (e.currentTarget.style.display = 'none')} />
          </div>
        )}
      </div>
    </section>
  )
}

function SubHero({ s }) {
  return (
    <section className="subhero">
      <div className="container">
        <Kicker t="Conocé más" />
        <h1>{s.title}</h1>
        <p className="lead">{s.text}</p>
      </div>
    </section>
  )
}

function Features({ s, id = 'services' }) {
  return (
    <section className="sec features" id={id}>
      <div className="container">
        <div className="sec-head">
          <Kicker t="Servicios" />
          <h2>{s.title}</h2>
          <p>{s.text}</p>
        </div>
        <div className="grid cards">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 60}>
              <div className="card">
                <span className="card-num">0{i + 1}</span>
                <h3>{it}</h3>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Gallery({ s }) {
  return (
    <section className="sec gallery">
      <div className="container">
        <div className="sec-head">
          <Kicker t="Trabajos" />
          <h2>{s.title}</h2>
          <p>{s.text}</p>
        </div>
        <div className="gallery-grid">
          {(s.images || []).map((img, i) => (
            <Reveal key={i} delay={(i % 4) * 60}>
              <figure className="shot">
                <img src={img} alt={s.title + ' ' + (i + 1)} loading="lazy" onError={(e) => (e.currentTarget.style.display = 'none')} />
              </figure>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function useCount(target, dur = 1300) {
  const [v, setV] = useState(0)
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    let raf
    let t0
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return
        io.disconnect()
        const step = (ts) => {
          if (!t0) t0 = ts
          const p = Math.min((ts - t0) / dur, 1)
          setV(Math.round(target * (1 - Math.pow(1 - p, 3))))
          if (p < 1) raf = requestAnimationFrame(step)
        }
        raf = requestAnimationFrame(step)
      },
      { threshold: 0.4 }
    )
    io.observe(el)
    return () => {
      io.disconnect()
      if (raf) cancelAnimationFrame(raf)
    }
  }, [target, dur])
  return { ref, v }
}

function StatItem({ value, suffix, label }) {
  const { ref, v } = useCount(value)
  return (
    <div className="stat" ref={ref}>
      <span className="stat-num">{v.toLocaleString('es-AR')}{suffix || ''}</span>
      <span className="stat-label">{label}</span>
    </div>
  )
}

function Stats({ s }) {
  return (
    <section className="sec stats-sec">
      <div className="container">
        <div className="sec-head">
          <Kicker t="Cifras" />
          <h2>{s.title}</h2>
        </div>
        <div className="stats">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 70}>
              <StatItem value={it.value} suffix={it.suffix} label={it.label} />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Testimonials({ s }) {
  return (
    <section className="sec">
      <div className="container">
        <div className="sec-head">
          <Kicker t="Opiniones" />
          <h2>{s.title}</h2>
          <p>{s.text}</p>
        </div>
        <div className="grid quotes">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 80}>
              <blockquote className="quote">
                <span className="quote-mark">"</span>
                <p>{it}</p>
              </blockquote>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Faq({ s }) {
  const [open, setOpen] = useState(0)
  return (
    <section className="sec">
      <div className="container">
        <div className="sec-head">
          <Kicker t="FAQ" />
          <h2>{s.title}</h2>
          <p>{s.text}</p>
        </div>
        <div className="faq">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 50}>
              <div className={'faq-item' + (open === i ? ' open' : '')}>
                <button className="faq-q" onClick={() => setOpen(open === i ? -1 : i)}>
                  <span>{it.q}</span>
                  <span className="faq-chev">+</span>
                </button>
                <div className="faq-a">{it.a}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Prices({ s }) {
  return (
    <section className="sec prices">
      <div className="container">
        <div className="sec-head">
          <Kicker t="Tarifas" />
          <h2>{s.title}</h2>
          <p>{s.text}</p>
        </div>
        <div className="grid cards">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 60}>
              <div className={'card price' + (i === 1 ? ' hot' : '')}>
                <h3>{it.name}</h3>
                <p className="price-tag">{it.price}</p>
                <a className="btn btn-ghost" href="#contact">
                  Consultar
                </a>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Process({ s }) {
  return (
    <section className="sec">
      <div className="container">
        <div className="sec-head">
          <Kicker t="Cómo trabajamos" />
          <h2>{s.title}</h2>
          <p>{s.text}</p>
        </div>
        <div className="steps">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 70}>
              <div className="step">
                <span className="step-num">{i + 1}</span>
                <p>{it}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Team({ s }) {
  const initials = (name) =>
    name
      .split(/\\s+/)
      .map((w) => w[0])
      .slice(0, 2)
      .join('')
      .toUpperCase()
  return (
    <section className="sec">
      <div className="container">
        <div className="sec-head">
          <Kicker t="Equipo" />
          <h2>{s.title}</h2>
          <p>{s.text}</p>
        </div>
        <div className="grid team">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 60}>
              <div className="member">
                <span className="avatar">{initials(it)}</span>
                <p>{it}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function About({ s }) {
  return (
    <section className="sec about">
      <div className="container about-inner">
        <Reveal>
          <div className="about-card">
            <Kicker t="Nosotros" />
            <h2>{s.title}</h2>
            <p>{s.text}</p>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Contact({ s }) {
  const [sent, setSent] = useState(false)
  return (
    <section className="sec contact" id="contact">
      <div className="container contact-inner">
        <div className="contact-info">
          <Kicker t="Contacto" />
          <h2>{s.title}</h2>
          <p>{s.text}</p>
          <ul className="contact-list">
            <li>Dirección: Av. Principal 123, Ciudad</li>
            <li>Horario: Lun a Sáb de 9 a 20hs</li>
            <li>Teléfono: +54 11 5555-1234</li>
          </ul>
        </div>
        <form
          className="contact-form"
          onSubmit={(e) => {
            e.preventDefault()
            setSent(true)
          }}
        >
          <input type="text" placeholder="Tu nombre" required />
          <input type="email" placeholder="Tu email" required />
          <textarea rows="4" placeholder="Contanos tu idea..." required />
          <button className="btn btn-grad" type="submit">
            {sent ? '¡Gracias! Te respondemos pronto' : 'Enviar mensaje'}
          </button>
        </form>
      </div>
    </section>
  )
}

const SECTION_TYPES = {
  hero: Hero,
  subhero: SubHero,
  features: Features,
  gallery: Gallery,
  stats: Stats,
  testimonials: Testimonials,
  faq: Faq,
  prices: Prices,
  process: Process,
  team: Team,
  about: About,
  contact: Contact,
}

export function Section({ s }) {
  const C = SECTION_TYPES[s.type] || Features
  return <C s={s} />
}

export function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <div>
          <span className="brand">{site}</span>
          <p className="muted">Hecho con React + Vite por ERIS.</p>
        </div>
        <nav className="footer-nav">
          {pages.map((p) => (
            <NavLink key={p.id} to={p.id === 'index' ? '/' : '/' + p.id}>
              {p.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </footer>
  )
}

export default theme
"""


def _css(theme, font_name):
    p, fg, bg, accent = theme["primary"], theme["fg"], theme["bg"], theme["accent"]
    sec = theme["secondary"]
    font_family = '"{}", system-ui, sans-serif'.format(font_name)
    return """/* Generado por ERIS · React Designer */
:root {{
  --bg: {bg};
  --fg: {fg};
  --primary: {p};
  --secondary: {sec};
  --accent: {accent};
  --font: {font_family};
  --card: rgba(255,255,255,0.05);
  --line: rgba(255,255,255,0.12);
  --radius: 18px;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  background: var(--bg);
  color: var(--fg);
  font-family: var(--font);
  line-height: 1.6;
  overflow-x: hidden;
}}
img {{ max-width: 100%; display: block; }}
a {{ color: inherit; text-decoration: none; }}
.container {{ width: min(1120px, 92%); margin: 0 auto; }}
.muted {{ opacity: 0.65; }}

::selection {{ background: var(--primary); color: #fff; }}

.brand {{ font-weight: 800; font-size: 1.15rem; letter-spacing: 0.5px; }}

.nav {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 50;
  backdrop-filter: blur(14px);
  background: linear-gradient(180deg, rgba(0,0,0,0.35), transparent);
  border-bottom: 1px solid var(--line);
}}
.nav-inner {{ display: flex; align-items: center; justify-content: space-between; height: 68px; }}
.nav nav {{ display: flex; gap: 26px; }}
.nav nav a {{ font-size: 0.92rem; opacity: 0.75; transition: opacity .2s, color .2s; }}
.nav nav a:hover {{ opacity: 1; }}
.nav nav a.active {{ color: var(--primary); opacity: 1; font-weight: 700; }}

/* ── Fondos decorativos ── */
.bg-grid {{ background-image:
  linear-gradient(var(--line) 1px, transparent 1px),
  linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size: 46px 46px; }}
.bg-dots {{ background-image: radial-gradient(var(--line) 1.4px, transparent 1.4px); background-size: 26px 26px; }}
.bg-mesh {{ background-image:
  radial-gradient(40% 60% at 20% 10%, {p}22, transparent 60%),
  radial-gradient(40% 60% at 90% 20%, {sec}22, transparent 60%),
  radial-gradient(50% 50% at 60% 90%, {accent}18, transparent 60%); }}
.bg-aurora {{ background:
  linear-gradient(115deg, {p}1a, {sec}14, {accent}14, {p}1a);
  background-size: 220% 220%;
  animation: aurora 16s ease infinite; }}
.bg-rings {{ background-image:
  radial-gradient(circle at 12% 15%, {p}22 0 5%, transparent 5.2%),
  radial-gradient(circle at 88% 25%, {sec}22 0 8%, transparent 8.2%),
  radial-gradient(circle at 30% 85%, {accent}1c 0 6%, transparent 6.2%),
  radial-gradient(circle at 75% 78%, {p}18 0 10%, transparent 10.2%); }}
.bg-blobs {{ background-image:
  radial-gradient(24% 40% at 15% 20%, {p}30, transparent 70%),
  radial-gradient(22% 36% at 85% 30%, {sec}26, transparent 70%),
  radial-gradient(30% 40% at 55% 95%, {accent}22, transparent 70%); }}

@keyframes aurora {{
  0% {{ background-position: 0% 50%; }}
  50% {{ background-position: 100% 50%; }}
  100% {{ background-position: 0% 50%; }}
}}

/* ── Reveal ── */
.rv {{ opacity: 0; transform: translateY(26px); transition: opacity .7s ease, transform .7s ease; }}
.rv.on {{ opacity: 1; transform: none; }}
.anim-float .hero-media img {{ animation: floaty 7s ease-in-out infinite; }}
@keyframes floaty {{
  0%,100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-14px); }}
}}

/* ── Secciones ── */
.hero {{ padding: 150px 0 80px; min-height: 88vh; display: flex; align-items: center; }}
.hero-inner {{ display: grid; gap: 50px; align-items: center; }}
.hero-centered .hero-inner {{ justify-items: center; text-align: center; }}
.hero-centered .hero-cta {{ justify-content: center; }}
.hero-split .hero-inner, .hero-editorial .hero-inner {{ grid-template-columns: 1.1fr .9fr; }}
.hero-compact {{ min-height: auto; padding: 150px 0 90px; }}
.hero-compact .hero-inner {{ justify-items: start; }}
.hero h1 {{
  font-size: clamp(2.4rem, 5vw, 4.2rem);
  line-height: 1.05;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin: 10px 0 18px;
}}
.hero-editorial h1 {{
  background: linear-gradient(90deg, var(--fg), var(--primary));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}}
.lead {{ font-size: 1.12rem; opacity: 0.85; max-width: 34em; }}
.hero-cta {{ display: flex; gap: 14px; margin-top: 30px; flex-wrap: wrap; }}
.hero-media {{ position: relative; }}
.hero-media img {{
  width: 100%; aspect-ratio: 4/3; object-fit: cover;
  border-radius: 26px;
  border: 1px solid var(--line);
  box-shadow: 0 40px 80px -30px rgba(0,0,0,0.6);
}}
.hero-media::before {{
  content: ''; position: absolute; inset: -6%; z-index: -1;
  background: radial-gradient(60% 60% at 50% 50%, {p}3d, transparent 70%);
  filter: blur(30px);
}}

.kicker {{
  text-transform: uppercase; letter-spacing: 0.18em; font-size: 0.78rem;
  font-weight: 700; color: var(--accent);
}}
.subhero {{ padding: 150px 0 70px; text-align: center; }}
.subhero h1 {{ font-size: clamp(2rem, 4vw, 3.2rem); margin: 10px 0 14px; }}
.subhero .lead {{ margin: 0 auto; }}

.sec {{ padding: 90px 0; }}
.sec-head {{ text-align: center; max-width: 640px; margin: 0 auto 50px; }}
.sec-head h2 {{ font-size: clamp(1.7rem, 3vw, 2.6rem); margin: 8px 0 12px; letter-spacing: -0.01em; }}
.sec-head p {{ opacity: 0.8; }}

.grid {{ display: grid; gap: 22px; }}
.cards {{ grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }}
.card {{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 28px 24px;
  transition: transform .25s, border-color .25s, background .25s;
}}
.card:hover {{ transform: translateY(-6px); border-color: var(--primary); background: rgba(255,255,255,0.08); }}
.card-num {{ font-size: 0.8rem; color: var(--primary); font-weight: 800; }}
.card h3 {{ margin: 10px 0 8px; font-size: 1.12rem; }}

.gallery-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }}
.shot {{
  position: relative; overflow: hidden; border-radius: var(--radius);
  border: 1px solid var(--line); aspect-ratio: 5/4;
}}
.shot img {{ width: 100%; height: 100%; object-fit: cover; transition: transform .5s; }}
.shot:hover img {{ transform: scale(1.06); }}

.stats-sec {{ border-block: 1px solid var(--line); background: rgba(0,0,0,0.18); }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 30px; text-align: center; }}
.stat-num {{
  font-size: clamp(2rem, 4vw, 3.4rem); font-weight: 800; line-height: 1;
  background: linear-gradient(90deg, var(--primary), var(--accent));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}}
.stat-label {{ opacity: 0.75; margin-top: 8px; display: block; }}

.quotes {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
.quote {{ position: relative; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 28px 24px; }}
.quote-mark {{ font-size: 3rem; color: var(--primary); line-height: 0.6; font-family: Georgia, serif; }}
.quote p {{ opacity: 0.9; margin-top: 12px; }}

.faq {{ max-width: 760px; margin: 0 auto; display: grid; gap: 14px; }}
.faq-item {{ border: 1px solid var(--line); border-radius: 14px; overflow: hidden; background: var(--card); }}
.faq-q {{ width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 14px;
  padding: 18px 20px; background: none; border: none; color: var(--fg); font: inherit; font-weight: 700;
  cursor: pointer; text-align: left; }}
.faq-chev {{ color: var(--primary); transition: transform .25s; font-size: 1.3rem; }}
.faq-item.open .faq-chev {{ transform: rotate(45deg); }}
.faq-a {{ max-height: 0; overflow: hidden; transition: max-height .3s ease; opacity: 0; padding: 0 20px; }}
.faq-item.open .faq-a {{ max-height: 200px; opacity: 1; padding: 0 20px 18px; }}

.price {{ text-align: center; }}
.price.hot {{ border-color: var(--primary); box-shadow: 0 0 0 1px var(--primary), 0 20px 50px -20px var(--primary); }}
.price-tag {{ font-size: 1.6rem; font-weight: 800; margin: 12px 0 18px; color: var(--primary); }}

.steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; counter-reset: step; }}
.step {{ text-align: center; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 26px 18px; }}
.step-num {{
  width: 42px; height: 42px; margin: 0 auto 12px; display: grid; place-items: center;
  border-radius: 50%; background: linear-gradient(135deg, var(--primary), var(--accent)); color: #fff; font-weight: 800;
}}

.team {{ grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }}
.member {{ text-align: center; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 26px 16px; }}
.avatar {{
  width: 68px; height: 68px; margin: 0 auto 14px; display: grid; place-items: center;
  border-radius: 50%; font-weight: 800; font-size: 1.3rem; color: var(--bg);
  background: linear-gradient(135deg, var(--accent), var(--primary));
}}

.about-inner {{ display: grid; place-items: center; }}
.about-card {{ max-width: 720px; text-align: center; background: var(--card); border: 1px solid var(--line);
  border-radius: 26px; padding: 60px 40px; }}

.contact {{ background: rgba(0,0,0,0.22); border-top: 1px solid var(--line); }}
.contact-inner {{ display: grid; grid-template-columns: 1fr 1fr; gap: 46px; }}
.contact-list {{ list-style: none; margin-top: 22px; display: grid; gap: 10px; opacity: 0.85; }}
.contact-list li::before {{ content: '▸ '; color: var(--primary); }}
.contact-form {{ display: grid; gap: 14px; }}
.contact-form input, .contact-form textarea {{
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  color: var(--fg); font: inherit; padding: 14px 16px; outline: none;
  transition: border-color .2s;
}}
.contact-form input:focus, .contact-form textarea:focus {{ border-color: var(--primary); }}

.btn {{ display: inline-block; padding: 14px 26px; border-radius: 999px; font-weight: 700; font-size: 0.95rem;
  transition: transform .2s, box-shadow .2s; border: 1px solid transparent; }}
.btn:hover {{ transform: translateY(-2px); }}
.btn-grad {{
  background: linear-gradient(90deg, var(--primary), var(--accent));
  color: #fff; box-shadow: 0 14px 34px -12px var(--primary);
}}
.btn-ghost {{ border-color: var(--line); }}
.btn-ghost:hover {{ border-color: var(--primary); }}

.footer {{ border-top: 1px solid var(--line); padding: 50px 0; }}
.footer-inner {{ display: flex; align-items: center; justify-content: space-between; gap: 20px; flex-wrap: wrap; }}
.footer-nav {{ display: flex; gap: 18px; opacity: 0.75; font-size: 0.9rem; }}
.footer-nav a:hover {{ color: var(--primary); }}

@media (max-width: 820px) {{
  .hero {{ padding: 130px 0 50px; }}
  .hero-split .hero-inner, .hero-editorial .hero-inner {{ grid-template-columns: 1fr; }}
  .contact-inner {{ grid-template-columns: 1fr; }}
  .nav nav {{ gap: 14px; font-size: 0.85rem; }}
}}
""".format(
        bg=bg, fg=fg, p=p, sec=sec, accent=accent, font_family=font_family
    )


# ──────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ──────────────────────────────────────────────────────────────────────
def react_designer(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "help").lower().strip()
    memory = _load_memory()

    if player:
        try:
            player.write_log("ReactDesigner: {}".format(action))
        except Exception:
            pass

    if action in ("help", "ayuda"):
        return (
            "react_designer — Diseñador de webs con React (Vite).\n"
            "  create title= topic= description= sections= folder= pages= images=  → genera el proyecto React completo y lo abre\n"
            "  install folder=       → npm install\n"
            "  dev folder= port=     → levanta el dev server (Vite)\n"
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
        return _dev(folder, int(parameters.get("port") or 5173))

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
        h = [x for x in memory.get("history", []) if x.get("kind", "").startswith("react")]
        lines = ["React Designer — memoria:",
                 "  Proyectos creados: {}".format(len(h))]
        for p_ in h[-5:]:
            lines.append("    - {} ({}) — {} / {}".format(
                p_.get("title"), p_.get("topic"), p_.get("palette"), p_.get("font")))
        return "\n".join(lines)

    return react_designer({"action": "help"}, player)


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

    # ── Variedad de diseño (aprendizaje compartido con web_designer) ──
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
        folder = str(_DEFAULT_OUT / "{}_{}".format(_slug(topic) or "react", datetime.now().strftime("%Y%m%d_%H%M%S")))
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
        kind = "react-site"
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
        kind = "react-single"
        n_pages = 1

    theme = {
        "name": palette["name"],
        "bg": palette["bg"], "fg": palette["fg"],
        "primary": palette["primary"], "secondary": palette["secondary"],
        "accent": palette["accent"],
        "font": font_name.replace("+", " "),
        "layout": layout,
        "bgStyle": bg_style,
        "anim": "reveal" if "reveal" not in animations else "float" if "float" in animations else "reveal",
    }
    if "float" in animations:
        theme["anim"] = "float"
    elif "kenburns" in animations:
        theme["anim"] = "float"
    else:
        theme["anim"] = "reveal"

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
        "✅ Proyecto React #{} creado ({} páginas):".format(memory["pages_created"], n_pages),
        "   {}".format(folder),
        "",
        "   Diseño: {} | Fuente: {} | Layout: {} | Fondo: {} | Animaciones: {}".format(
            palette["name"], font_name.replace("+", " "), layout, bg_style, ", ".join(animations)),
        "   React {} Vite · {} componentes JSX".format("18", len(pages_data)),
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
    lines.append("Para renderizar y revisar: react_designer action=preview folder='{}'".format(folder))
    return "\n".join(lines)


def _write_project(folder, title, description, topic, font_name, font_url, theme, pages_data,
                   palette, animations, layout, bg_style):
    (Path(folder) / "src").mkdir(parents=True, exist_ok=True)
    (Path(folder) / "src" / "components").mkdir(parents=True, exist_ok=True)

    slug = _slug(topic) or "react-app"
    port = 5173
    (Path(folder) / "package.json").write_text(
        _PKG_TEMPLATE.format(slug=slug), encoding="utf-8")
    (Path(folder) / "vite.config.js").write_text(
        _VITE_CONFIG.format(port=port), encoding="utf-8")
    (Path(folder) / "index.html").write_text(
        _INDEX_HTML.format(title=title, description=description, font_url=font_url), encoding="utf-8")
    (Path(folder) / "src" / "main.jsx").write_text(_MAIN_JSX, encoding="utf-8")
    (Path(folder) / "src" / "App.jsx").write_text(_APP_JSX, encoding="utf-8")
    (Path(folder) / "src" / "index.css").write_text(
        _css(theme, font_name.replace("+", " ")), encoding="utf-8")
    (Path(folder) / "src" / "data.js").write_text(
        _data_js(theme, title, pages_data), encoding="utf-8")
    (Path(folder) / "src" / "components" / "sections.jsx").write_text(
        _SECTIONS_JSX, encoding="utf-8")

    meta = {
        "title": title, "topic": topic, "type": "react", "framework": "react+vite",
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
        return "El npm install tardó demasiado. Podés reintentar con react_designer action=install folder='{}'".format(folder)
    if res.returncode == 0:
        return "✅ npm install completado (node_modules listo)."
    tail = (res.stdout or "")[-1200:]
    return "⚠️ npm install falló:\n{}".format(tail)


def _wait_port(port, timeout=60):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://127.0.0.1:{}".format(port), timeout=2)
            return True
        except Exception:
            time.sleep(0.7)
    return False


def _dev(folder, port=5173):
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
    if not _wait_port(port):
        try:
            proc.terminate()
        except Exception:
            pass
        return "Vite no respondió en el puerto {}. Revisá con react_designer action=dev folder='{}'".format(port, folder)
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
        return "No hay proyecto React en {}".format(folder)
    port = 5173
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
            # páginas del sitio
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
    lines = ["React renderizada y abierta en el navegador (http://127.0.0.1:{}).".format(port),
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
    print(react_designer(args))
