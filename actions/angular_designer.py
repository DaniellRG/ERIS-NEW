"""
actions/angular_designer.py — Generador de proyectos web con Angular (standalone).

Genera un proyecto Angular completo y funcional (Angular 20, standalone components):
  - package.json, angular.json, tsconfig.json, tsconfig.app.json
  - src/index.html, src/main.ts, src/styles.css
  - src/app/*: app.config, app.routes, app.component, data.ts
  - src/app/components: nav, footer, reveal.directive, sections.component, page.component

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
# Helpers compartidos con el generador React (npm, css, serialización)
from actions.react_designer import (
    _npm, _wait_port, _url_for, _css, _serialize_sections, _js_escape,
)

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_DEV_PROCS = {}  # folder -> Popen
_DEFAULT_PORT = 4200


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
    "scripts": {
        "ng": "ng",
        "start": "ng serve --host 0.0.0.0",
        "build": "ng build",
        "watch": "ng build --watch --configuration development",
    },
    "dependencies": {
        "@angular/animations": "^20.3.27",
        "@angular/common": "^20.3.27",
        "@angular/compiler": "^20.3.27",
        "@angular/core": "^20.3.27",
        "@angular/forms": "^20.3.27",
        "@angular/platform-browser": "^20.3.27",
        "@angular/platform-browser-dynamic": "^20.3.27",
        "@angular/router": "^20.3.27",
        "rxjs": "~7.8.1",
        "tslib": "^2.3.0",
        "zone.js": "~0.15.0",
    },
    "devDependencies": {
        "@angular-devkit/build-angular": "^20.3.27",
        "@angular/cli": "^20.3.27",
        "@angular/compiler-cli": "^20.3.27",
        "typescript": "~5.8.0",
    },
}

_ANGULAR_JSON = {
    "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
    "version": 1,
    "newProjectRoot": "projects",
    "projects": {
        "@@slug@@": {
            "projectType": "application",
            "schematics": {},
            "root": "",
            "sourceRoot": "src",
            "prefix": "app",
            "architect": {
                "build": {
                    "builder": "@angular-devkit/build-angular:application",
                    "options": {
                        "outputPath": "dist",
                        "index": "src/index.html",
                        "browser": "src/main.ts",
                        "polyfills": ["zone.js"],
                        "tsConfig": "tsconfig.app.json",
                        "assets": [{"glob": "**/*", "input": "public"}],
                        "styles": ["src/styles.css"],
                        "scripts": [],
                    },
                    "configurations": {
                        "production": {
                            "budgets": [
                                {"type": "initial", "maximumWarning": "1mb", "maximumError": "3mb"},
                                {"type": "anyComponentStyle", "maximumWarning": "6kb", "maximumError": "20kb"},
                            ],
                            "outputHashing": "all",
                        },
                        "development": {
                            "optimization": False,
                            "extractLicenses": False,
                            "sourceMap": True,
                        },
                    },
                    "defaultConfiguration": "production",
                },
                "serve": {
                    "builder": "@angular-devkit/build-angular:dev-server",
                    "configurations": {
                        "production": {"buildTarget": "@@slug@@:build:production"},
                        "development": {"buildTarget": "@@slug@@:build:development"},
                    },
                    "defaultConfiguration": "development",
                },
            },
        }
    },
}

_TSCONFIG = {
    "compileOnSave": False,
    "compilerOptions": {
        "outDir": "./dist/out-tsc",
        "strict": False,
        "noImplicitOverride": True,
        "noPropertyAccessFromIndexSignature": True,
        "noImplicitReturns": True,
        "noFallthroughCasesInSwitch": True,
        "skipLibCheck": True,
        "isolatedModules": True,
        "esModuleInterop": True,
        "experimentalDecorators": True,
        "moduleResolution": "bundler",
        "importHelpers": True,
        "target": "ES2022",
        "module": "ES2022",
        "useDefineForClassFields": False,
        "lib": ["ES2022", "dom"],
    },
    "angularCompilerOptions": {
        "enableI18nLegacyMessageIdFormat": False,
        "strictInjectionParameters": False,
        "strictInputAccessModifiers": False,
        "strictTemplates": False,
    },
}

_TSCONFIG_APP = {
    "extends": "./tsconfig.json",
    "compilerOptions": {"outDir": "./out-tsc/app", "types": []},
    "files": ["src/main.ts"],
    "include": ["src/**/*.d.ts"],
}

_INDEX_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>@@title@@</title>
  <meta name="description" content="@@description@@">
  <base href="/">
  <link rel="icon" type="image/svg+xml" href="favicon.svg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=@@font_url@@&display=swap" rel="stylesheet">
</head>
<body>
  <app-root></app-root>
</body>
</html>
"""

_FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#@@accent@@"/><circle cx="32" cy="32" r="14" fill="none" stroke="#fff" stroke-width="4"/></svg>
"""

_MAIN_TS = """import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';

bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error(err));
"""

_APP_CONFIG_TS = """import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
  ],
};
"""

_APP_ROUTES_TS = """import { Routes } from '@angular/router';
import { PageComponent } from './page.component';
import { pages } from './data';

export const routes: Routes = [
@@routes@@
  { path: '**', redirectTo: '' },
];
"""

_APP_COMPONENT_TS = """import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavComponent } from './components/nav.component';
import { FooterComponent } from './components/footer.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavComponent, FooterComponent],
  template: `
  <app-nav />
  <main>
    <router-outlet />
  </main>
  <app-footer />
  `,
})
export class AppComponent {}
"""

_NAV_COMPONENT_TS = """import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { pages, site } from '../data';

@Component({
  selector: 'app-nav',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
  <header class="nav">
    <div class="nav-inner container">
      <a class="brand" routerLink="/">{{ site }}</a>
      <nav>
        @for (p of pages; track p.id) {
          <a [routerLink]="p.id === 'index' ? '/' : '/' + p.id"
             routerLinkActive="active"
             [routerLinkActiveOptions]="{ exact: p.id === 'index' }">
            {{ p.label }}
          </a>
        }
      </nav>
    </div>
  </header>
  `,
})
export class NavComponent {
  site = site;
  pages = pages;
}
"""

_FOOTER_COMPONENT_TS = """import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { pages, site } from '../data';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [RouterLink],
  template: `
  <footer class="footer">
    <div class="container footer-inner">
      <div>
        <span class="brand">{{ site }}</span>
        <p class="muted">Hecho con Angular por ERIS.</p>
      </div>
      <nav class="footer-nav">
        @for (p of pages; track p.id) {
          <a [routerLink]="p.id === 'index' ? '/' : '/' + p.id">{{ p.label }}</a>
        }
      </nav>
    </div>
  </footer>
  `,
})
export class FooterComponent {
  site = site;
  pages = pages;
}
"""

_REVEAL_DIRECTIVE_TS = """import { Directive, ElementRef, Input, OnInit, OnDestroy } from '@angular/core';

@Directive({ selector: '[appReveal]', standalone: true })
export class RevealDirective implements OnInit, OnDestroy {
  private io!: IntersectionObserver;

  constructor(private el: ElementRef) {}

  ngOnInit() {
    this.io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          this.el.nativeElement.classList.add('on');
          this.io.disconnect();
        }
      },
      { threshold: 0.12 }
    );
    this.io.observe(this.el.nativeElement);
  }

  ngOnDestroy() {
    if (this.io) this.io.disconnect();
  }
}

@Directive({ selector: '[appCount]', standalone: true })
export class CountDirective implements OnInit, OnDestroy {
  @Input() appCount = 0;
  private io?: IntersectionObserver;

  constructor(private el: ElementRef) {}

  ngOnInit() {
    this.io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        this.io!.disconnect();
        const t0 = performance.now();
        const dur = 1300;
        const step = (t: number) => {
          const p = Math.min((t - t0) / dur, 1);
          const v = Math.round(this.appCount * (1 - Math.pow(1 - p, 3)));
          this.el.nativeElement.textContent = v.toLocaleString('es-AR');
          if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      },
      { threshold: 0.4 }
    );
    this.io.observe(this.el.nativeElement);
  }

  ngOnDestroy() {
    if (this.io) this.io.disconnect();
  }
}
"""

_DATA_TS = """export const site = @@site@@;

export const theme = @@theme@@;

export type Section = any;
export type Page = { id: string; label: string; sections: Section[] };

export const pages: Page[] = @@pages@@;
"""


def _data_ts(theme, site_name, pages):
    return _DATA_TS.replace("@@site@@", json.dumps(site_name, ensure_ascii=False)) \
                   .replace("@@theme@@", json.dumps(theme, ensure_ascii=False)) \
                   .replace("@@pages@@", json.dumps(pages, ensure_ascii=False))


_PAGE_COMPONENT_TS = """import { Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { pages } from './data';
import { SectionComponent } from './components/sections.component';

@Component({
  selector: 'app-page',
  standalone: true,
  imports: [SectionComponent],
  template: `
  @for (sec of page.sections; track $index) {
    <app-section [s]="sec" />
  }
  `,
})
export class PageComponent {
  page: any = pages[0];
  private route = inject(ActivatedRoute);

  constructor() {
    this.route.data.subscribe((d) => {
      this.page = pages.find((p) => p.id === d['id']) || pages[0];
    });
  }
}
"""


def _routes_ts(ids):
    lines = []
    for pid in ids:
        path = "''" if pid == "index" else "'" + pid + "'"
        lines.append("  {{ path: {path}, component: PageComponent, data: {{ id: '{pid}' }} }},".format(
            path=path, pid=pid))
    return _APP_ROUTES_TS.replace("@@routes@@", "\n".join(lines))


_SECTIONS_COMPONENT_TS = """import { Component, Input } from '@angular/core';
import { theme } from '../data';
import { RevealDirective, CountDirective } from './reveal.directive';

@Component({
  selector: 'app-hero-section',
  standalone: true,
  template: `
  <section class="hero hero-{{ theme.layout }}">
    <div class="container hero-inner">
      <div class="hero-text">
        @if (s.badges && s.badges[0]) { <p class="kicker">{{ s.badges[0] }}</p> }
        <h1>{{ s.title }}</h1>
        <p class="lead">{{ s.text }}</p>
        <div class="hero-cta">
          <a class="btn btn-grad" href="#contact">Empezar ahora</a>
          <a class="btn btn-ghost" href="#services">Ver servicios</a>
        </div>
      </div>
      @if (split) {
        <div class="hero-media">
          <img [src]="s.media" [alt]="s.title" (error)="hideImg($event)" />
        </div>
      }
    </div>
  </section>
  `,
})
export class HeroSectionComponent {
  @Input() s: any = {};
  theme = theme;
  get split(): boolean {
    return theme.layout === 'split' || theme.layout === 'editorial';
  }
  hideImg(e: any) { e.target.style.display = 'none'; }
}

@Component({
  selector: 'app-subhero-section',
  standalone: true,
  template: `
  <section class="subhero">
    <div class="container">
      <p class="kicker">Conocé más</p>
      <h1>{{ s.title }}</h1>
      <p class="lead">{{ s.text }}</p>
    </div>
  </section>
  `,
})
export class SubHeroSectionComponent {
  @Input() s: any = {};
}

@Component({
  selector: 'app-features-section',
  standalone: true,
  imports: [RevealDirective],
  template: `
  <section class="sec features" id="services">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Servicios</p>
        <h2>{{ s.title }}</h2>
        @if (s.text) { <p>{{ s.text }}</p> }
      </div>
      <div class="grid cards">
        @for (it of s.items || []; track $index) {
          <div class="card rv" appReveal [style.transitionDelay]="($index * 60) + 'ms'">
            <span class="card-num">0{{ $index + 1 }}</span>
            <h3>{{ it }}</h3>
          </div>
        }
      </div>
    </div>
  </section>
  `,
})
export class FeaturesSectionComponent {
  @Input() s: any = {};
}

@Component({
  selector: 'app-gallery-section',
  standalone: true,
  imports: [RevealDirective],
  template: `
  <section class="sec gallery">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Trabajos</p>
        <h2>{{ s.title }}</h2>
        @if (s.text) { <p>{{ s.text }}</p> }
      </div>
      <div class="gallery-grid">
        @for (img of s.images || []; track $index) {
          <figure class="shot rv" appReveal [style.transitionDelay]="(($index % 4) * 60) + 'ms'">
            <img [src]="img" [alt]="s.title + ' ' + ($index + 1)" loading="lazy" (error)="hideImg($event)" />
          </figure>
        }
      </div>
    </div>
  </section>
  `,
})
export class GallerySectionComponent {
  @Input() s: any = {};
  hideImg(e: any) { e.target.style.display = 'none'; }
}

@Component({
  selector: 'app-stats-section',
  standalone: true,
  imports: [RevealDirective, CountDirective],
  template: `
  <section class="sec stats-sec">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Cifras</p>
        <h2>{{ s.title }}</h2>
      </div>
      <div class="stats">
        @for (it of s.items || []; track $index) {
          <div class="stat rv" appReveal [style.transitionDelay]="($index * 70) + 'ms'">
            <span class="stat-num" appCount [appCount]="it.value">0</span>
            <span class="stat-label">{{ it.label }}</span>
          </div>
        }
      </div>
    </div>
  </section>
  `,
})
export class StatsSectionComponent {
  @Input() s: any = {};
}

@Component({
  selector: 'app-testimonials-section',
  standalone: true,
  imports: [RevealDirective],
  template: `
  <section class="sec">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Opiniones</p>
        <h2>{{ s.title }}</h2>
        @if (s.text) { <p>{{ s.text }}</p> }
      </div>
      <div class="grid quotes">
        @for (it of s.items || []; track $index) {
          <blockquote class="quote rv" appReveal [style.transitionDelay]="($index * 80) + 'ms'">
            <span class="quote-mark">"</span>
            <p>{{ it }}</p>
          </blockquote>
        }
      </div>
    </div>
  </section>
  `,
})
export class TestimonialsSectionComponent {
  @Input() s: any = {};
}

@Component({
  selector: 'app-faq-section',
  standalone: true,
  imports: [RevealDirective],
  template: `
  <section class="sec">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">FAQ</p>
        <h2>{{ s.title }}</h2>
        @if (s.text) { <p>{{ s.text }}</p> }
      </div>
      <div class="faq">
        @for (it of s.items || []; track $index) {
          <div class="faq-item rv" appReveal [class.open]="open === $index" [style.transitionDelay]="($index * 50) + 'ms'">
            <button class="faq-q" (click)="toggle($index)">
              <span>{{ it.q }}</span>
              <span class="faq-chev">+</span>
            </button>
            <div class="faq-a">{{ it.a }}</div>
          </div>
        }
      </div>
    </div>
  </section>
  `,
})
export class FaqSectionComponent {
  @Input() s: any = {};
  open = 0;
  toggle(i: number) { this.open = this.open === i ? -1 : i; }
}

@Component({
  selector: 'app-prices-section',
  standalone: true,
  imports: [RevealDirective],
  template: `
  <section class="sec prices">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Tarifas</p>
        <h2>{{ s.title }}</h2>
        @if (s.text) { <p>{{ s.text }}</p> }
      </div>
      <div class="grid cards">
        @for (it of s.items || []; track $index) {
          <div class="card price rv" appReveal [class.hot]="$index === 1" [style.transitionDelay]="($index * 60) + 'ms'">
            <h3>{{ it.name }}</h3>
            <p class="price-tag">{{ it.price }}</p>
            <a class="btn btn-ghost" href="#contact">Consultar</a>
          </div>
        }
      </div>
    </div>
  </section>
  `,
})
export class PricesSectionComponent {
  @Input() s: any = {};
}

@Component({
  selector: 'app-process-section',
  standalone: true,
  imports: [RevealDirective],
  template: `
  <section class="sec">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Cómo trabajamos</p>
        <h2>{{ s.title }}</h2>
        @if (s.text) { <p>{{ s.text }}</p> }
      </div>
      <div class="steps">
        @for (it of s.items || []; track $index) {
          <div class="step rv" appReveal [style.transitionDelay]="($index * 70) + 'ms'">
            <span class="step-num">{{ $index + 1 }}</span>
            <p>{{ it }}</p>
          </div>
        }
      </div>
    </div>
  </section>
  `,
})
export class ProcessSectionComponent {
  @Input() s: any = {};
}

@Component({
  selector: 'app-team-section',
  standalone: true,
  imports: [RevealDirective],
  template: `
  <section class="sec">
    <div class="container">
      <div class="sec-head">
        <p class="kicker">Equipo</p>
        <h2>{{ s.title }}</h2>
        @if (s.text) { <p>{{ s.text }}</p> }
      </div>
      <div class="grid team">
        @for (it of s.items || []; track $index) {
          <div class="member rv" appReveal [style.transitionDelay]="($index * 60) + 'ms'">
            <span class="avatar">{{ initials(it) }}</span>
            <p>{{ it }}</p>
          </div>
        }
      </div>
    </div>
  </section>
  `,
})
export class TeamSectionComponent {
  @Input() s: any = {};
  initials(name: string): string {
    return name.split(/\\s+/).map((w) => w[0]).slice(0, 2).join('').toUpperCase();
  }
}

@Component({
  selector: 'app-about-section',
  standalone: true,
  imports: [RevealDirective],
  template: `
  <section class="sec about">
    <div class="container about-inner">
      <div class="about-card rv" appReveal>
        <p class="kicker">Nosotros</p>
        <h2>{{ s.title }}</h2>
        @if (s.text) { <p>{{ s.text }}</p> }
      </div>
    </div>
  </section>
  `,
})
export class AboutSectionComponent {
  @Input() s: any = {};
}

@Component({
  selector: 'app-contact-section',
  standalone: true,
  template: `
  <section class="sec contact" id="contact">
    <div class="container contact-inner">
      <div class="contact-info">
        <p class="kicker">Contacto</p>
        <h2>{{ s.title }}</h2>
        @if (s.text) { <p>{{ s.text }}</p> }
        <ul class="contact-list">
          <li>Dirección: Av. Principal 123, Ciudad</li>
          <li>Horario: Lun a Sáb de 9 a 20hs</li>
          <li>Teléfono: +54 11 5555-1234</li>
        </ul>
      </div>
      <form class="contact-form" (ngSubmit)="send()">
        <input type="text" placeholder="Tu nombre" required />
        <input type="email" placeholder="Tu email" required />
        <textarea rows="4" placeholder="Contanos tu idea..." required></textarea>
        <button class="btn btn-grad" type="submit">{{ sent ? '¡Gracias! Te respondemos pronto' : 'Enviar mensaje' }}</button>
      </form>
    </div>
  </section>
  `,
})
export class ContactSectionComponent {
  @Input() s: any = {};
  sent = false;
  send() { this.sent = true; }
}

@Component({
  selector: 'app-section',
  standalone: true,
  imports: [
    HeroSectionComponent,
    SubHeroSectionComponent,
    FeaturesSectionComponent,
    GallerySectionComponent,
    StatsSectionComponent,
    TestimonialsSectionComponent,
    FaqSectionComponent,
    PricesSectionComponent,
    ProcessSectionComponent,
    TeamSectionComponent,
    AboutSectionComponent,
    ContactSectionComponent,
  ],
  template: `
  @switch (s.type) {
    @case ('hero') { <app-hero-section [s]="s" /> }
    @case ('subhero') { <app-subhero-section [s]="s" /> }
    @case ('features') { <app-features-section [s]="s" /> }
    @case ('gallery') { <app-gallery-section [s]="s" /> }
    @case ('stats') { <app-stats-section [s]="s" /> }
    @case ('testimonials') { <app-testimonials-section [s]="s" /> }
    @case ('faq') { <app-faq-section [s]="s" /> }
    @case ('prices') { <app-prices-section [s]="s" /> }
    @case ('process') { <app-process-section [s]="s" /> }
    @case ('team') { <app-team-section [s]="s" /> }
    @case ('about') { <app-about-section [s]="s" /> }
    @case ('contact') { <app-contact-section [s]="s" /> }
  }
  `,
})
export class SectionComponent {
  @Input() s: any = {};
}
"""


def _theme_anim(animations):
    if "float" in animations or "kenburns" in animations:
        return "float"
    return "reveal"


# ──────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ──────────────────────────────────────────────────────────────────────
def angular_designer(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "help").lower().strip()
    memory = _load_memory()

    if player:
        try:
            player.write_log("AngularDesigner: {}".format(action))
        except Exception:
            pass

    if action in ("help", "ayuda"):
        return (
            "angular_designer — Diseñador de webs con Angular (standalone).\n"
            "  create title= topic= description= sections= folder= pages= images=  → genera el proyecto Angular completo y lo abre\n"
            "  install folder=       → npm install\n"
            "  dev folder= port=     → levanta el dev server (ng serve, puerto 4200)\n"
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
        h = [x for x in memory.get("history", []) if x.get("kind", "").startswith("angular")]
        lines = ["Angular Designer — memoria:",
                 "  Proyectos creados: {}".format(len(h))]
        for p_ in h[-5:]:
            lines.append("    - {} ({}) — {} / {}".format(
                p_.get("title"), p_.get("topic"), p_.get("palette"), p_.get("font")))
        return "\n".join(lines)

    return angular_designer({"action": "help"}, player)


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
        folder = str(_DEFAULT_OUT / "{}_{}".format(_slug(topic) or "angular", datetime.now().strftime("%Y%m%d_%H%M%S")))
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
        kind = "angular-site"
        n_pages = len(pages_data)
        page_ids = [p["id"] for p in pages_data]
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
        kind = "angular-single"
        n_pages = 1
        page_ids = ["index"]

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
                   page_ids, palette, animations, layout, bg_style)

    memory["pages_created"] = memory.get("pages_created", 0) + 1
    memory.setdefault("history", []).append({
        "id": uuid.uuid4().hex[:8], "title": title, "topic": topic,
        "palette": palette["name"], "font": font_name.replace("+", " "),
        "folder": folder, "timestamp": time.time(), "kind": kind,
        "layout": layout, "bg": bg_style, "n_pages": n_pages})
    memory["history"] = memory["history"][-20:]
    _save_memory(memory)

    lines = [
        "✅ Proyecto Angular #{} creado ({} páginas):".format(memory["pages_created"], n_pages),
        "   {}".format(folder),
        "",
        "   Diseño: {} | Fuente: {} | Layout: {} | Fondo: {} | Animaciones: {}".format(
            palette["name"], font_name.replace("+", " "), layout, bg_style, ", ".join(animations)),
        "   Angular 20 standalone · {} páginas con componentes".format(n_pages),
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
    lines.append("Para renderizar y revisar: angular_designer action=preview folder='{}'".format(folder))
    return "\n".join(lines)


def _write_project(folder, title, description, topic, font_name, font_url, theme, pages_data,
                   page_ids, palette, animations, layout, bg_style):
    (Path(folder) / "src").mkdir(parents=True, exist_ok=True)
    (Path(folder) / "src" / "app").mkdir(parents=True, exist_ok=True)
    (Path(folder) / "src" / "app" / "components").mkdir(parents=True, exist_ok=True)
    (Path(folder) / "public").mkdir(parents=True, exist_ok=True)

    slug = _slug(topic) or "angular-app"

    def j(obj):
        return json.dumps(obj, indent=2, ensure_ascii=False)

    (Path(folder) / "package.json").write_text(
        _replace(j(_PKG_TEMPLATE), slug=slug), encoding="utf-8")
    (Path(folder) / "angular.json").write_text(
        _replace(j(_ANGULAR_JSON), slug=slug), encoding="utf-8")
    (Path(folder) / "tsconfig.json").write_text(j(_TSCONFIG), encoding="utf-8")
    (Path(folder) / "tsconfig.app.json").write_text(j(_TSCONFIG_APP), encoding="utf-8")
    (Path(folder) / "src" / "index.html").write_text(
        _replace(_INDEX_HTML, title=title, description=description, font_url=font_url), encoding="utf-8")
    (Path(folder) / "src" / "main.ts").write_text(_MAIN_TS, encoding="utf-8")
    (Path(folder) / "src" / "styles.css").write_text(
        _css(theme, font_name.replace("+", " ")), encoding="utf-8")
    (Path(folder) / "src" / "app" / "app.config.ts").write_text(_APP_CONFIG_TS, encoding="utf-8")
    (Path(folder) / "src" / "app" / "app.routes.ts").write_text(_routes_ts(page_ids), encoding="utf-8")
    (Path(folder) / "src" / "app" / "app.component.ts").write_text(_APP_COMPONENT_TS, encoding="utf-8")
    (Path(folder) / "src" / "app" / "data.ts").write_text(_data_ts(theme, title, pages_data), encoding="utf-8")
    (Path(folder) / "src" / "app" / "page.component.ts").write_text(_PAGE_COMPONENT_TS, encoding="utf-8")
    (Path(folder) / "src" / "app" / "components" / "nav.component.ts").write_text(_NAV_COMPONENT_TS, encoding="utf-8")
    (Path(folder) / "src" / "app" / "components" / "footer.component.ts").write_text(_FOOTER_COMPONENT_TS, encoding="utf-8")
    (Path(folder) / "src" / "app" / "components" / "reveal.directive.ts").write_text(_REVEAL_DIRECTIVE_TS, encoding="utf-8")
    (Path(folder) / "src" / "app" / "components" / "sections.component.ts").write_text(_SECTIONS_COMPONENT_TS, encoding="utf-8")
    (Path(folder) / "public" / "favicon.svg").write_text(
        _FAVICON.format(accent=palette["accent"].lstrip("#")), encoding="utf-8")

    meta = {
        "title": title, "topic": topic, "type": "angular", "framework": "angular20",
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
        res = _npm(["install", "--no-audit", "--no-fund"], cwd=folder, timeout=900)
    except subprocess.TimeoutExpired:
        return "El npm install tardó demasiado. Podés reintentar con angular_designer action=install folder='{}'".format(folder)
    if res.returncode == 0:
        return "✅ npm install completado (node_modules listo)."
    tail = (res.stdout or "")[-1500:]
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
            ["cmd", "/c", "npm", "run", "start", "--", "--port", str(port)],
            cwd=folder,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_CREATE_NO_WINDOW,
        )
    except Exception as e:
        return "No se pudo levantar ng serve: {}".format(str(e)[:120])
    _DEV_PROCS[folder] = proc
    if not _wait_port(port, timeout=120):
        try:
            proc.terminate()
        except Exception:
            pass
        return "ng serve no respondió en el puerto {}. Revisá con angular_designer action=dev folder='{}'".format(port, folder)
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
        dist = Path(folder, "dist")
        size = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file()) if dist.exists() else 0
        return "✅ Build completado en {}/dist ({} bytes)".format(folder, size)
    tail = (res.stdout or "")[-1500:]
    return "⚠️ Build falló:\n{}".format(tail)


def _preview(folder, player=None):
    folder = str(Path(folder).resolve())
    if not Path(folder, "package.json").exists():
        return "No hay proyecto Angular en {}".format(folder)
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
            data_fp = Path(folder, "src", "app", "data.ts")
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
                    pg.wait_for_timeout(2200)
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
    lines = ["Angular renderizada y abierta en el navegador (http://127.0.0.1:{}).".format(port),
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
    print(angular_designer(args))
