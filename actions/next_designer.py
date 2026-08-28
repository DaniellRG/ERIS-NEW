"""
actions/next_designer.py — Generador de proyectos web con Next.js + Tailwind CSS.

Genera un proyecto Next.js (App Router) completo y funcional:
  - package.json, postcss.config.mjs, next.config.mjs
  - src/app/layout.jsx (html, head, metadatos, fuentes)
  - src/app/globals.css (Tailwind + variables del tema ERIS)
  - src/app/page.jsx (home) y src/app/[pid]/page.jsx (resto de páginas)
  - src/lib/data.js (site, theme, pages)
  - src/components/sections.jsx (componentes por sección, "use client")

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
# Helpers compartidos con React (npm, url, serialización)
from actions.react_designer import (
    _npm, _wait_port, _url_for, _serialize_sections, _js_escape,
)

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_DEV_PROCS = {}  # folder -> Popen


# ──────────────────────────────────────────────────────────────────────
#  TEMPLATES DE ARCHIVOS
# ──────────────────────────────────────────────────────────────────────
_PKG_TEMPLATE = """{{
  "name": "{slug}",
  "private": true,
  "version": "1.0.0",
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  }},
  "dependencies": {{
    "next": "^15.3.1",
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  }},
  "devDependencies": {{
    "tailwindcss": "^4.1.0",
    "@tailwindcss/postcss": "^4.1.0"
  }}
}}
"""

_POSTCSS = """export default { plugins: { "@tailwindcss/postcss": {} } }
"""

_NEXT_CONFIG = """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
}
export default nextConfig
"""

_JSCONFIG = """{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  }
}
"""

_GLOBALS_CSS = """@import "tailwindcss";

:root {{
  --bg: {bg};
  --fg: {fg};
  --primary: {p};
  --secondary: {sec};
  --accent: {accent};
  --font: '{font}', system-ui, sans-serif;
  --card: {card};
  --line: {line};
  --line-soft: {line_soft};
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
kbd, .mono {{ font-family: 'Space Mono', monospace; }}

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
.anim-float img {{ animation: floaty 7s ease-in-out infinite; }}
@keyframes floaty {{
  0%,100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-14px); }}
}}
"""

_LAYOUT_JSX = """import { Nav, Footer } from '@/components/sections.jsx'
import './globals.css'

export const metadata = {
  title: '@@TITLE@@',
  description: '@@DESCRIPTION@@',
}

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=@@FONT_URL@@&display=swap" rel="stylesheet" />
      </head>
      <body className={'bg-[@@BG@@] text-[@@FG@@] anim-@@ANIM@@ bg-@@BGSTYLE@@'}>
        <Nav />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  )
}
"""

_PAGE_HOME = """import { pages } from '@/lib/data.js'
import { PageSections } from '@/components/sections.jsx'

export default function Home() {
  const page = pages.find((p) => p.id === 'index') || pages[0]
  return <PageSections sections={page.sections} />
}
"""

_PAGE_SLUG = """import { pages } from '@/lib/data.js'
import { PageSections } from '@/components/sections.jsx'

export async function generateStaticParams() {
  return pages.filter((p) => p.id !== 'index').map((p) => ({ pid: p.id }))
}

export default async function SlugPage({ params }) {
  const { pid } = await params
  const page = pages.find((p) => p.id === pid) || pages[0]
  return <PageSections sections={page.sections} />
}
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


_SECTIONS_JSX = """'use client'
import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { site, pages, theme } from '@/lib/data.js'

const P = {
  bg: '@@BG@@', fg: '@@FG@@', primary: '@@P@@', secondary: '@@SEC@@', accent: '@@ACCENT@@',
  card: '@@CARD@@', line: '@@LINE@@', lineSoft: '@@LINE_SOFT@@',
}

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
    <header className="fixed inset-x-0 top-0 z-50 border-b backdrop-blur-md" style={{ borderColor: P.line, background: 'rgba(0,0,0,0.18)' }}>
      <div className="container flex h-16 items-center justify-between">
        <Link href="/" className="font-extrabold">{site}</Link>
        <nav className="flex gap-6">
          {pages.map((p) => (
            <Link
              key={p.id}
              href={p.id === 'index' ? '/' : '/' + p.id}
              className="text-sm opacity-75 transition-opacity hover:opacity-100"
            >
              {p.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  )
}

function Hero({ s }) {
  return (
    <section className="flex min-h-[88vh] items-center px-[4%] pt-24 pb-16">
      <div className={'container ' + (theme.layout === 'centered' ? 'text-center' : '')}>
        {s.badges?.[0] && <p className="text-xs font-bold uppercase tracking-[0.18em] mb-3" style={{ color: P.accent }}>{s.badges[0]}</p>}
        <h1 className="max-w-4xl text-5xl font-extrabold leading-[1.05] tracking-tight md:text-7xl">
          {s.title}
        </h1>
        <p className="mt-4 max-w-2xl text-lg opacity-85">{s.text}</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <a href="#contact" className="rounded-full px-6 py-3 font-bold text-white transition-transform hover:-translate-y-0.5" style={{ background: 'linear-gradient(90deg, ' + P.primary + ', ' + P.accent + ')' }}>
            Empezar ahora
          </a>
          <a href="#services" className="rounded-full border px-6 py-3 font-bold" style={{ borderColor: P.line }}>
            Ver servicios
          </a>
        </div>
      </div>
    </section>
  )
}

function SubHero({ s }) {
  return (
    <section className="px-[4%] pt-36 pb-16 text-center">
      <div className="container">
        <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>Conocé más</p>
        <h1 className="mt-2 text-4xl font-extrabold md:text-5xl">{s.title}</h1>
        <p className="mx-auto mt-3 max-w-2xl opacity-85">{s.text}</p>
      </div>
    </section>
  )
}

function Features({ s }) {
  return (
    <section className="px-[4%] py-20" id="services">
      <div className="container">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>Servicios</p>
          <h2 className="mt-2 text-3xl font-extrabold md:text-4xl">{s.title}</h2>
          <p className="mt-2 opacity-80">{s.text}</p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 60}>
              <div className="h-full rounded-2xl border p-6 transition-transform hover:-translate-y-1.5" style={{ background: P.card, borderColor: P.line }}>
                <span className="text-xs font-extrabold" style={{ color: P.primary }}>0{i + 1}</span>
                <h3 className="mt-2 text-lg font-bold">{it}</h3>
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
    <section className="px-[4%] py-20">
      <div className="container">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>Trabajos</p>
          <h2 className="mt-2 text-3xl font-extrabold md:text-4xl">{s.title}</h2>
          <p className="mt-2 opacity-80">{s.text}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {(s.images || []).map((img, i) => (
            <Reveal key={i} delay={(i % 4) * 60}>
              <figure className="aspect-[5/4] overflow-hidden rounded-2xl border" style={{ borderColor: P.line }}>
                <img src={img} alt={s.title + ' ' + (i + 1)} loading="lazy" className="h-full w-full object-cover transition-transform duration-500 hover:scale-105" onError={(e) => (e.currentTarget.style.display = 'none')} />
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
    let raf, t0
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

function Stats({ s }) {
  return (
    <section className="px-[4%] py-16" style={{ borderTop: '1px solid ' + P.line, borderBottom: '1px solid ' + P.line, background: 'rgba(0,0,0,0.18)' }}>
      <div className="container">
        <div className="mx-auto mb-10 max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>Cifras</p>
          <h2 className="mt-2 text-3xl font-extrabold md:text-4xl">{s.title}</h2>
        </div>
        <div className="grid gap-8 text-center sm:grid-cols-2 lg:grid-cols-4">
          {(s.items || []).map((it, i) => {
            const { ref, v } = useCount(it.value)
            return (
              <Reveal key={i} delay={i * 70}>
                <div ref={ref}>
                  <div className="text-4xl font-extrabold md:text-5xl" style={{ background: 'linear-gradient(90deg, ' + P.primary + ', ' + P.accent + ')', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    {v.toLocaleString('es-AR')}{it.suffix || ''}
                  </div>
                  <div className="mt-2 opacity-75">{it.label}</div>
                </div>
              </Reveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}

function Testimonials({ s }) {
  return (
    <section className="px-[4%] py-20">
      <div className="container">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>Opiniones</p>
          <h2 className="mt-2 text-3xl font-extrabold md:text-4xl">{s.title}</h2>
          <p className="mt-2 opacity-80">{s.text}</p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 80}>
              <blockquote className="h-full rounded-2xl border p-6" style={{ background: P.card, borderColor: P.line }}>
                <span className="text-4xl leading-none" style={{ color: P.primary, fontFamily: 'Georgia, serif' }}>"</span>
                <p className="mt-2 opacity-90">{it}</p>
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
    <section className="px-[4%] py-20">
      <div className="container max-w-3xl">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>FAQ</p>
          <h2 className="mt-2 text-3xl font-extrabold md:text-4xl">{s.title}</h2>
          <p className="mt-2 opacity-80">{s.text}</p>
        </div>
        <div className="grid gap-3">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 50}>
              <div className="overflow-hidden rounded-xl border" style={{ background: P.card, borderColor: P.line }}>
                <button
                  className="flex w-full items-center justify-between gap-3 p-4 text-left font-bold"
                  onClick={() => setOpen(open === i ? -1 : i)}
                >
                  <span>{it.q}</span>
                  <span className="text-xl transition-transform" style={{ color: P.primary }}>{open === i ? '−' : '+'}</span>
                </button>
                {open === i && <div className="px-4 pb-4 opacity-85">{it.a}</div>}
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
    <section className="px-[4%] py-20">
      <div className="container">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>Tarifas</p>
          <h2 className="mt-2 text-3xl font-extrabold md:text-4xl">{s.title}</h2>
          <p className="mt-2 opacity-80">{s.text}</p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 60}>
              <div className={'rounded-2xl border p-6 text-center ' + (i === 1 ? 'shadow-lg' : '')}
                style={{ background: P.card, borderColor: i === 1 ? P.primary : P.line }}>
                <h3 className="text-lg font-bold">{it.name}</h3>
                <p className="my-3 text-2xl font-extrabold" style={{ color: P.primary }}>{it.price}</p>
                <a href="#contact" className="rounded-full border px-5 py-2 text-sm font-bold" style={{ borderColor: P.line }}>Consultar</a>
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
    <section className="px-[4%] py-20">
      <div className="container">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>Cómo trabajamos</p>
          <h2 className="mt-2 text-3xl font-extrabold md:text-4xl">{s.title}</h2>
          <p className="mt-2 opacity-80">{s.text}</p>
        </div>
        <div className="grid gap-5 text-center sm:grid-cols-2 lg:grid-cols-4">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 70}>
              <div className="rounded-2xl border p-6" style={{ background: P.card, borderColor: P.line }}>
                <div className="mx-auto mb-3 grid h-11 w-11 place-items-center rounded-full font-extrabold text-white" style={{ background: 'linear-gradient(135deg, ' + P.primary + ', ' + P.accent + ')' }}>
                  {i + 1}
                </div>
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
    name.split(/\\s+/).map((w) => w[0]).slice(0, 2).join('').toUpperCase()
  return (
    <section className="px-[4%] py-20">
      <div className="container">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>Equipo</p>
          <h2 className="mt-2 text-3xl font-extrabold md:text-4xl">{s.title}</h2>
          <p className="mt-2 opacity-80">{s.text}</p>
        </div>
        <div className="grid gap-5 text-center sm:grid-cols-2 lg:grid-cols-4">
          {(s.items || []).map((it, i) => (
            <Reveal key={i} delay={i * 60}>
              <div className="rounded-2xl border p-6" style={{ background: P.card, borderColor: P.line }}>
                <div className="mx-auto mb-3 grid h-16 w-16 place-items-center rounded-full text-lg font-extrabold"
                  style={{ background: 'linear-gradient(135deg, ' + P.accent + ', ' + P.primary + ')', color: '@@BG@@' }}>
                  {initials(it)}
                </div>
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
    <section className="px-[4%] py-20">
      <div className="container grid place-items-center">
        <Reveal>
          <div className="max-w-2xl rounded-3xl border p-12 text-center" style={{ background: P.card, borderColor: P.line }}>
            <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>Nosotros</p>
            <h2 className="mt-2 text-3xl font-extrabold md:text-4xl">{s.title}</h2>
            <p className="mt-3 opacity-85">{s.text}</p>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Contact({ s }) {
  const [sent, setSent] = useState(false)
  return (
    <section className="px-[4%] py-20" id="contact" style={{ borderTop: '1px solid ' + P.line, background: 'rgba(0,0,0,0.22)' }}>
      <div className="container grid gap-10 lg:grid-cols-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em]" style={{ color: P.accent }}>Contacto</p>
          <h2 className="mt-2 text-3xl font-extrabold md:text-4xl">{s.title}</h2>
          <p className="mt-2 opacity-85">{s.text}</p>
          <ul className="mt-6 grid gap-2 opacity-85">
            <li>Dirección: Av. Principal 123, Ciudad</li>
            <li>Horario: Lun a Sáb de 9 a 20hs</li>
            <li>Teléfono: +54 11 5555-1234</li>
          </ul>
        </div>
        <form
          className="grid gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            setSent(true)
          }}
        >
          <input type="text" placeholder="Tu nombre" required className="rounded-xl border p-3 outline-none focus:border-transparent" style={{ background: P.card, borderColor: P.line, color: P.fg }} />
          <input type="email" placeholder="Tu email" required className="rounded-xl border p-3 outline-none" style={{ background: P.card, borderColor: P.line, color: P.fg }} />
          <textarea rows="4" placeholder="Contanos tu idea..." required className="rounded-xl border p-3 outline-none" style={{ background: P.card, borderColor: P.line, color: P.fg }} />
          <button type="submit" className="rounded-full px-6 py-3 font-bold text-white transition-transform hover:-translate-y-0.5" style={{ background: 'linear-gradient(90deg, ' + P.primary + ', ' + P.accent + ')' }}>
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

export function PageSections({ sections }) {
  return (
    <>
      {(sections || []).map((s, i) => {
        const C = SECTION_TYPES[s.type] || Features
        return <C key={i} s={s} />
      })}
    </>
  )
}

export function Footer() {
  return (
    <footer className="px-[4%] py-12" style={{ borderTop: '1px solid ' + P.line }}>
      <div className="container flex flex-wrap items-center justify-between gap-5">
        <div>
          <span className="brand">{site}</span>
          <p className="mt-1 text-sm opacity-60">Hecho con Next.js + Tailwind por ERIS.</p>
        </div>
        <nav className="flex gap-4 text-sm opacity-75">
          {pages.map((p) => (
            <Link key={p.id} href={p.id === 'index' ? '/' : '/' + p.id} className="hover:opacity-100">
              {p.label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  )
}"""


# ──────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ──────────────────────────────────────────────────────────────────────
def next_designer(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "help").lower().strip()
    memory = _load_memory()

    if player:
        try:
            player.write_log("NextDesigner: {}".format(action))
        except Exception:
            pass

    if action in ("help", "ayuda"):
        return (
            "next_designer — Diseñador de webs con Next.js + Tailwind CSS.\n"
            "  create title= topic= description= sections= folder= pages= images=  → genera el proyecto Next.js completo y lo abre\n"
            "  install folder=       → npm install\n"
            "  dev folder= port=     → levanta el dev server (next dev)\n"
            "  build folder=         → compila a producción (.next/)\n"
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
        return _dev(folder, int(parameters.get("port") or 3000))

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
        h = [x for x in memory.get("history", []) if x.get("kind", "").startswith("next")]
        lines = ["Next Designer — memoria:",
                 "  Proyectos creados: {}".format(len(h))]
        for p_ in h[-5:]:
            lines.append("    - {} ({}) — {} / {}".format(
                p_.get("title"), p_.get("topic"), p_.get("palette"), p_.get("font")))
        return "\n".join(lines)

    return next_designer({"action": "help"}, player)


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
        folder = str(_DEFAULT_OUT / "{}_{}".format(_slug(topic) or "next", datetime.now().strftime("%Y%m%d_%H%M%S")))
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
        kind = "next-site"
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
        kind = "next-single"
        n_pages = 1

    theme = {
        "name": palette["name"],
        "bg": palette["bg"], "fg": palette["fg"],
        "primary": palette["primary"], "secondary": palette["secondary"],
        "accent": palette["accent"],
        "font": font_name.replace("+", " "),
        "layout": layout,
        "bgStyle": bg_style,
        "anim": "reveal",
    }
    if "float" in animations:
        theme["anim"] = "float"

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
        "✅ Proyecto Next.js #{} creado ({} páginas):".format(memory["pages_created"], n_pages),
        "   {}".format(folder),
        "",
        "   Diseño: {} | Fuente: {} | Layout: {} | Fondo: {} | Animaciones: {}".format(
            palette["name"], font_name.replace("+", " "), layout, bg_style, ", ".join(animations)),
        "   Next.js 15 App Router · Tailwind CSS · {} rutas".format(len(pages_data)),
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
    lines.append("Para renderizar y revisar: next_designer action=preview folder='{}'".format(folder))
    return "\n".join(lines)


def _write_project(folder, title, description, topic, font_name, font_url, theme, pages_data,
                   palette, animations, layout, bg_style):
    (Path(folder) / "src" / "app").mkdir(parents=True, exist_ok=True)
    (Path(folder) / "src" / "lib").mkdir(parents=True, exist_ok=True)
    (Path(folder) / "src" / "components").mkdir(parents=True, exist_ok=True)

    slug = _slug(topic) or "next-app"

    # colores derivados para CSS / JSX
    bg = palette["bg"]
    fg = palette["fg"]
    p = palette["primary"]
    sec = palette["secondary"]
    accent = palette["accent"]
    dark = _is_dark(bg)
    line = "rgba(255,255,255,0.12)" if dark else "rgba(0,0,0,0.10)"
    card = "rgba(255,255,255,0.05)" if dark else "rgba(0,0,0,0.04)"
    line_soft = "rgba(255,255,255,0.06)" if dark else "rgba(0,0,0,0.05)"

    (Path(folder) / "package.json").write_text(
        _PKG_TEMPLATE.format(slug=slug), encoding="utf-8")
    (Path(folder) / "postcss.config.mjs").write_text(_POSTCSS, encoding="utf-8")
    (Path(folder) / "next.config.mjs").write_text(_NEXT_CONFIG, encoding="utf-8")
    (Path(folder) / "jsconfig.json").write_text(_JSCONFIG, encoding="utf-8")
    (Path(folder) / "src" / "app" / "globals.css").write_text(
        _GLOBALS_CSS.format(bg=bg, fg=fg, p=p, sec=sec, accent=accent,
                            font=font_name.replace("+", " "),
                            card=card, line=line, line_soft=line_soft),
        encoding="utf-8")
    (Path(folder) / "src" / "app" / "layout.jsx").write_text(
        _LAYOUT_JSX
        .replace("@@TITLE@@", title).replace("@@DESCRIPTION@@", description)
        .replace("@@FONT_URL@@", font_url).replace("@@BG@@", bg)
        .replace("@@FG@@", fg).replace("@@ANIM@@", theme["anim"])
        .replace("@@BGSTYLE@@", bg_style),
        encoding="utf-8")
    (Path(folder) / "src" / "app" / "page.jsx").write_text(_PAGE_HOME, encoding="utf-8")
    slug_dir = Path(folder) / "src" / "app" / "[pid]"
    slug_dir.mkdir(parents=True, exist_ok=True)
    (slug_dir / "page.jsx").write_text(_PAGE_SLUG, encoding="utf-8")
    (Path(folder) / "src" / "lib" / "data.js").write_text(
        _data_js(theme, title, pages_data), encoding="utf-8")
    (Path(folder) / "src" / "components" / "sections.jsx").write_text(
        _SECTIONS_JSX
        .replace("@@BG@@", bg).replace("@@FG@@", fg).replace("@@P@@", p)
        .replace("@@SEC@@", sec).replace("@@ACCENT@@", accent)
        .replace("@@CARD@@", card).replace("@@LINE@@", line)
        .replace("@@LINE_SOFT@@", line_soft),
        encoding="utf-8")

    meta = {
        "title": title, "topic": topic, "type": "next", "framework": "next+tailwind",
        "pages": [{"page": p_["id"], "label": p_["label"]} for p_ in pages_data],
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


def _is_dark(bg):
    try:
        h = bg.lstrip("#")
        if len(h) != 6:
            return False
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return (0.299 * r + 0.587 * g + 0.114 * b) < 140
    except Exception:
        return False


def _install(folder):
    folder = str(Path(folder).resolve())
    if not Path(folder, "package.json").exists():
        return "No hay package.json en {}".format(folder)
    try:
        res = _npm(["install", "--no-audit", "--no-fund"], cwd=folder, timeout=900)
    except subprocess.TimeoutExpired:
        return "El npm install tardó demasiado. Podés reintentar con next_designer action=install folder='{}'".format(folder)
    if res.returncode == 0:
        return "✅ npm install completado (node_modules listo)."
    tail = (res.stdout or "")[-1200:]
    return "⚠️ npm install falló:\n{}".format(tail)


def _dev(folder, port=3000):
    folder = str(Path(folder).resolve())
    if folder in _DEV_PROCS and _DEV_PROCS[folder].poll() is None:
        return "Dev server ya activo en http://127.0.0.1:{}".format(port)
    if not Path(folder, "node_modules").exists():
        inst = _install(folder)
        if "✅" not in inst:
            return inst
    try:
        proc = subprocess.Popen(
            ["cmd", "/c", "set NEXT_TELEMETRY_DISABLED=1&&npx next dev -p {} -H 0.0.0.0".format(port)],
            cwd=folder,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_CREATE_NO_WINDOW,
        )
    except Exception as e:
        return "No se pudo levantar Next.js: {}".format(str(e)[:120])
    _DEV_PROCS[folder] = proc
    if not _wait_port(port, timeout=120):
        try:
            proc.terminate()
        except Exception:
            pass
        return "Next.js no respondió en el puerto {}. Revisá con next_designer action=dev folder='{}'".format(port, folder)
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
        res = _npm(["run", "build"], cwd=folder, timeout=900)
    except subprocess.TimeoutExpired:
        return "El build tardó demasiado."
    if res.returncode == 0:
        return "✅ Build completado en {} (.next/)".format(folder)
    tail = (res.stdout or "")[-2000:]
    return "⚠️ Build falló:\n{}".format(tail)


def _preview(folder, player=None):
    folder = str(Path(folder).resolve())
    if not Path(folder, "package.json").exists():
        return "No hay proyecto Next.js en {}".format(folder)
    port = 3000
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
            data_fp = Path(folder, "src", "lib", "data.js")
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
                    pg.goto(base + r, wait_until="load", timeout=45000)
                    pg.wait_for_timeout(2000)
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
    lines = ["Next.js renderizada y abierta en el navegador (http://127.0.0.1:{}).".format(port),
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
    print(next_designer(args))
