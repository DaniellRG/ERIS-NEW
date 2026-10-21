# -*- coding: utf-8 -*-
"""
code_helper.py — Write, edit, explain, run, and build code files.
Actions: write, edit, explain, run, build, auto
"""
import os
import subprocess
import tempfile
import traceback
from pathlib import Path


def code_helper(parameters: dict, player=None) -> str:
    action = parameters.get("action", "auto").lower().strip()
    description = parameters.get("description", "")
    language = parameters.get("language", "python").lower().strip()
    output_path = parameters.get("output_path", "")
    file_path = parameters.get("file_path", "")
    code = parameters.get("code", "")
    args = parameters.get("args", "")
    timeout = int(parameters.get("timeout", 30))

    if action == "auto":
        if code:
            return _explain_code(code, language)
        elif file_path and os.path.exists(file_path):
            return _explain_file(file_path)
        elif description:
            return _generate_and_save(description, language, output_path)
        return "Usá action=write/edit/explain/run/build para más control."

    elif action == "write":
        if not description:
            return "Error: Se requiere 'description' para generar código."
        return _generate_and_save(description, language, output_path)

    elif action == "edit":
        if not file_path or not os.path.exists(file_path):
            return f"Error: '{file_path}' no existe o no se especificó."
        if not description:
            return "Error: Se requiere 'description' describiendo el cambio."
        return _edit_file_with_ai(file_path, description, language)

    elif action == "explain":
        if code:
            return _explain_code(code, language)
        elif file_path and os.path.exists(file_path):
            return _explain_file(file_path)
        return "Error: Se requiere 'code' o 'file_path'."

    elif action == "run":
        if not file_path or not os.path.exists(file_path):
            return f"Error: '{file_path}' no existe."
        return _run_file(file_path, language, args, timeout)

    elif action == "build":
        if not file_path or not os.path.exists(file_path):
            return f"Error: '{file_path}' no existe."
        return _build_file(file_path, language, args, timeout)

    elif action in ("verify", "verify_project"):
        # (c) Gate end-to-end: import + pytest + servidor real. PASS 3/3 para
        # poder declarar la tarea terminada. Ver _verify_project.
        project_dir = (parameters.get("project_dir", "") or file_path
                       or output_path or "").strip()
        return _verify_project(
            project_dir=project_dir,
            app_module=str(parameters.get("app_module", "") or "main").strip(),
            endpoint=str(parameters.get("endpoint", "") or "/").strip() or "/",
            port=parameters.get("port", 0),
            test_path=str(parameters.get("test_path", "") or "").strip(),
            python=str(parameters.get("python", "") or "").strip(),
        )

    elif action == "help":
        return (
            "Puedo ayudarte con programación:\n"
            "- write: generar código desde descripción\n"
            "- edit: modificar archivos existentes\n"
            "- explain: explicar código existente\n"
            "- run: ejecutar scripts\n"
            "- build: compilar proyectos\n"
            "- verify_project: verificar un proyecto REAL (import + tests + servidor) — SIEMPRE antes de darlo por terminado\n"
            "- auto: decidir automáticamente\n\n"
            "Lenguajes soportados: Python, JavaScript, TypeScript, C#, Java, C, C++, Go, Rust, HTML, CSS, SQL.\n"
            "Pedime directamente lo que necesites."
        )

    return f"Acción '{action}' no reconocida. Usa: write, edit, explain, run, build, verify_project, auto, help"


def _generate_and_save(description: str, language: str, output_path: str) -> str:
    ext_map = {
        "python": ".py", "py": ".py", "javascript": ".js", "js": ".js",
        "typescript": ".ts", "ts": ".ts", "html": ".html", "css": ".css",
        "java": ".java", "c": ".c", "cpp": ".cpp", "go": ".go",
        "rust": ".rs", "bash": ".sh", "shell": ".sh", "sql": ".sql",
        "json": ".json", "yaml": ".yaml", "yml": ".yaml", "xml": ".xml",
        "markdown": ".md", "md": ".md",
    }
    ext = ext_map.get(language, ".py")
    if output_path:
        p = Path(output_path)
        # If directory (no recognized extension), auto-generate filename
        if p.suffix not in set(ext_map.values()) | {".sh", ".bat", ".ps1", ".rb", ".php", ".pl", ".r", ".swift", ".kt"}:
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(p / f"code_{ts}{ext}")
    else:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            from actions.path_helper import get_desktop_path
            desk = Path(get_desktop_path())
        except Exception:
            desk = Path.home() / "Desktop"
        output_path = str(desk / "ERIS_Codigo" / f"code_{ts}{ext}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # (b) Generación REAL con el router de modelos (Gemini/Groq/Ollama), no una
    #     plantilla estática. (Antes devolvía un stub "TODO: Implementar".)
    code = _generate_code_llm(description, language)
    if code is None:
        return (
            "❌ No pude generar código real: el modelo de código no respondió "
            "(cuota agotada o sin conexión). NO guardé ningún archivo para no "
            "dejarte un placeholder. Probá de nuevo en unos segundos o pedime "
            "que escriba el código directamente."
        )

    # (c) Gate de verificación: no declarar "listo" con un placeholder o código
    #     que no compila.
    problem = _verificar_codigo(code, language)
    if problem:
        return (
            f"❌ El código generado NO pasó la verificación ({problem}). No lo "
            "guardé como listo. Revisá la descripción o pedime que reintente."
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code if code.endswith("\n") else code + "\n")

    return (
        f"✅ Código real generado y guardado en: {output_path}\n"
        f"Lenguaje: {language} · {len(code.splitlines())} líneas.\n"
        f"Verificación: {_verificacion_ok(language)}\n"
        f"Descripción: {description}"
    )


def _generate_code_llm(description: str, language: str) -> str | None:
    """Genera código real vía el router de modelos. Devuelve el código (ya sin
    fences markdown) o None si el modelo no respondió."""
    system = (
        f"Eres un programador experto en {language}. Escribes código REAL, "
        "completo y funcional, listo para ejecutarse. NUNCA uses placeholders, "
        "'TODO: Implementar', 'Your code here' ni 'pass' como cuerpo vacío. "
        "Devuelve SOLO el código puro, sin explicaciones y sin fences de "
        "markdown (sin ```)."
    )
    prompt = (
        f"Escribe el código {language} completo y funcional que cumpla esto:\n\n"
        f"{description}\n\n"
        "Requisitos: implementación real y corriente (no un esqueleto), lista "
        "para correr. Sin 'TODO'. Devuelve únicamente el código."
    )
    try:
        from core.model_router import quick_chat
        raw = quick_chat(prompt, system=system, task="agent")
    except Exception:
        return None
    return _strip_fences(raw or "")


def _strip_fences(raw: str) -> str:
    """Quita fences de markdown (```python ... ```) si el modelo los añadió."""
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _verificar_codigo(code: str, language: str) -> str:
    """Devuelve '' si el código es real y válido; si no, el motivo del rechazo."""
    if not code or not code.strip():
        return "código vacío"
    low = code.lower()
    if "todo: implementar" in low or "your code here" in low:
        return "sigue siendo un placeholder (TODO)"
    meaningful = [l for l in code.split("\n")
                  if l.strip() and not l.strip().startswith(("#", "//"))]
    if len(meaningful) < 3:
        return "demasiado corto para ser una implementación real"
    if language in ("python", "py"):
        try:
            import py_compile
            import tempfile
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                             encoding="utf-8") as tf:
                tf.write(code)
                tmp = tf.name
            try:
                py_compile.compile(tmp, doraise=True)
            finally:
                os.unlink(tmp)
        except py_compile.PyCompileError as e:
            return f"no compila: {str(e)[:140]}"
        except Exception as e:
            return f"error de verificación: {str(e)[:140]}"
    return ""


def _verificacion_ok(language: str) -> str:
    if language in ("python", "py"):
        return "compila (py_compile OK), sin placeholders"
    return "sin placeholders"


def _get_template(language: str, description: str) -> str:
    desc_camel = description.replace("'", "\\'")
    desc_lower = description.lower()
    has_form = any(kw in desc_lower for kw in ["contacto", "form", "registro", "login"])
    has_gallery = any(kw in desc_lower for kw in ["galeria", "gallery", "portfolio", "portafolio", "imagen"])
    has_dark = any(kw in desc_lower for kw in ["dark", "oscuro", "noche", "nocturno"])
    theme_bg = "#0a0a0f" if has_dark else "#ffffff"
    theme_text = "#e0e0e0" if has_dark else "#1a1a2e"
    theme_card = "rgba(255,255,255,0.05)" if has_dark else "#f8f9fa"

    templates = {
        "python": f'''#!/usr/bin/env python3
"""
{description}
"""
import sys
import os


def main():
    """Main function."""
    print("TODO: Implementar — {description}")
    # Your code here


if __name__ == "__main__":
    main()
''',
        "javascript": f'''/**
 * {description}
 */

function main() {{
    console.log("TODO: Implementar — {description}");
}}

main();
''',
        "html": f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{description}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: {theme_bg};
            color: {theme_text};
            overflow-x: hidden;
        }}
        .hero {{
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            background: linear-gradient(135deg, {theme_bg} 0%, #1a1a2e 50%, {theme_bg} 100%);
            position: relative;
        }}
        .hero h1 {{
            font-size: 4rem;
            font-weight: 800;
            background: linear-gradient(135deg, #a78bfa, #60a5fa, #f472b6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
        }}
        .hero p {{ font-size: 1.3rem; opacity: 0.8; margin-bottom: 2rem; }}
        .btn-gradient {{
            background: linear-gradient(135deg, #7c3aed, #6366f1);
            border: none; color: white; padding: 12px 40px; border-radius: 50px;
            font-weight: 600; transition: all 0.3s ease;
        }}
        .btn-gradient:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 40px rgba(124, 58, 237, 0.4);
        }}
        .feature-card {{
            background: {theme_card};
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 20px; padding: 2rem;
            transition: all 0.4s ease; text-align: center;
        }}
        .feature-card:hover {{
            transform: translateY(-10px);
            border-color: rgba(167, 139, 250, 0.3);
            box-shadow: 0 20px 60px rgba(124, 58, 237, 0.15);
        }}
        .feature-icon {{
            width: 60px; height: 60px; margin: 0 auto 1rem;
            display: flex; align-items: center; justify-content: center;
            border-radius: 50%; font-size: 1.8rem; color: #a78bfa;
            background: linear-gradient(135deg, rgba(167,139,250,0.2), rgba(96,165,250,0.2));
        }}
        section {{ padding: 5rem 0; }}
        .section-title {{ font-size: 2.8rem; font-weight: 700; margin-bottom: 3rem; text-align: center; }}
        .particle {{
            position: fixed; width: 3px; height: 3px; border-radius: 50%;
            pointer-events: none; z-index: 0;
        }}
        @keyframes float {{
            0% {{ transform: translateY(0) rotate(0deg); opacity: 0; }}
            10% {{ opacity: 0.6; }}
            90% {{ opacity: 0.6; }}
            100% {{ transform: translateY(-100vh) rotate(720deg); opacity: 0; }}
        }}
        footer {{
            text-align: center; padding: 2rem; border-top: 1px solid rgba(255,255,255,0.05);
            color: rgba(255,255,255,0.4);
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark fixed-top" style="background:rgba(10,10,15,0.9);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,0.05);">
        <div class="container">
            <a class="navbar-brand fw-bold" href="#"><i class="bi bi-stars me-2"></i>{description}</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="nav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item"><a class="nav-link active" href="#inicio">Inicio</a></li>
                    <li class="nav-item"><a class="nav-link" href="#caracteristicas">Caracteristicas</a></li>
                    <li class="nav-item"><a class="nav-link" href="#galeria">Galeria</a></li>
                    <li class="nav-item"><a class="nav-link" href="#contacto">Contacto</a></li>
                </ul>
            </div>
        </div>
    </nav>

    <section id="inicio" class="hero">
        <div class="container">
            <div style="font-size:5rem;margin-bottom:1rem;">✨</div>
            <h1 data-aos="fade-up">{description}</h1>
            <p data-aos="fade-up" data-aos-delay="100">Una experiencia unica creada por ERIS AI</p>
            <div data-aos="fade-up" data-aos-delay="200">
                <a href="#caracteristicas" class="btn btn-gradient btn-lg me-3">Comenzar</a>
                <a href="#contacto" class="btn btn-outline-light btn-lg">Contacto</a>
            </div>
        </div>
    </section>

    <section id="caracteristicas">
        <div class="container">
            <h2 class="section-title" data-aos="fade-up">Caracteristicas</h2>
            <div class="row g-4">
                <div class="col-md-4" data-aos="fade-up" data-aos-delay="0">
                    <div class="feature-card">
                        <div class="feature-icon"><i class="bi bi-lightning-fill"></i></div>
                        <h3>Rapido</h3>
                        <p style="opacity:0.7;">Rendimiento optimizado para una experiencia fluida.</p>
                    </div>
                </div>
                <div class="col-md-4" data-aos="fade-up" data-aos-delay="100">
                    <div class="feature-card">
                        <div class="feature-icon"><i class="bi bi-shield-fill"></i></div>
                        <h3>Seguro</h3>
                        <p style="opacity:0.7;">Tus datos protegidos con los mas altos estandares.</p>
                    </div>
                </div>
                <div class="col-md-4" data-aos="fade-up" data-aos-delay="200">
                    <div class="feature-card">
                        <div class="feature-icon"><i class="bi bi-moon-stars-fill"></i></div>
                        <h3>Moderno</h3>
                        <p style="opacity:0.7;">Diseno vanguardista con las mejores tecnologias.</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section id="galeria" style="background:rgba(255,255,255,0.02);">
        <div class="container">
            <h2 class="section-title" data-aos="fade-up">Galeria</h2>
            <div class="row g-4">
                <div class="col-md-4" data-aos="zoom-in"><img src="https://picsum.photos/seed/a/600/400" class="img-fluid rounded-3" style="width:100%;height:250px;object-fit:cover;"></div>
                <div class="col-md-4" data-aos="zoom-in" data-aos-delay="100"><img src="https://picsum.photos/seed/b/600/400" class="img-fluid rounded-3" style="width:100%;height:250px;object-fit:cover;"></div>
                <div class="col-md-4" data-aos="zoom-in" data-aos-delay="200"><img src="https://picsum.photos/seed/c/600/400" class="img-fluid rounded-3" style="width:100%;height:250px;object-fit:cover;"></div>
            </div>
        </div>
    </section>

    <section id="contacto">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-lg-6">
                    <h2 class="section-title" data-aos="fade-up">Contacto</h2>
                    <form data-aos="fade-up" onsubmit="event.preventDefault();alert('Mensaje enviado!');">
                        <div class="mb-3">
                            <input class="form-control form-control-lg" placeholder="Nombre" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:inherit;border-radius:15px;">
                        </div>
                        <div class="mb-3">
                            <input type="email" class="form-control form-control-lg" placeholder="Email" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:inherit;border-radius:15px;">
                        </div>
                        <div class="mb-3">
                            <textarea class="form-control form-control-lg" rows="4" placeholder="Mensaje" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:inherit;border-radius:15px;"></textarea>
                        </div>
                        <button type="submit" class="btn btn-gradient w-100 btn-lg">Enviar</button>
                    </form>
                </div>
            </div>
        </div>
    </section>

    <footer>
        <p class="mb-0">&copy; 2026 {description} — Creado por ERIS AI <i class="bi bi-heart-fill text-danger"></i></p>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>
    <script>
        AOS.init({{ duration: 800, once: true }});
        (function() {{
            const colors = ['#a78bfa','#60a5fa','#f472b6','#34d399','#fbbf24'];
            for (let i = 0; i < 30; i++) {{
                const p = document.createElement('div');
                p.className = 'particle';
                p.style.left = Math.random() * 100 + '%';
                p.style.top = '100%';
                p.style.background = colors[Math.floor(Math.random() * colors.length)];
                p.style.animation = `float ${{10 + Math.random() * 20}}s linear infinite`;
                p.style.animationDelay = Math.random() * 15 + 's';
                document.body.appendChild(p);
            }}
        }})();
        document.querySelectorAll('a[href^="#"]').forEach(a => {{
            a.addEventListener('click', e => {{
                e.preventDefault();
                const t = document.querySelector(a.getAttribute('href'));
                if (t) t.scrollIntoView({{ behavior: 'smooth' }});
            }});
        }});
    </script>
</body>
</html>
''',
        "html_landing": f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Landing — {description}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a0f; color: #e0e0e0; }}
        .hero {{ min-height: 100vh; display: flex; align-items: center; background: radial-gradient(ellipse at center, #1a1a2e, #0a0a0f); }}
        .hero h1 {{ font-size: 4.5rem; font-weight: 800; }}
        .gradient-text {{ background: linear-gradient(135deg, #a78bfa, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .btn-cta {{ background: linear-gradient(135deg, #7c3aed, #6366f1); border: none; border-radius: 50px; padding: 15px 50px; font-weight: 700; color: white; transition: all 0.3s; }}
        .btn-cta:hover {{ transform: translateY(-3px); box-shadow: 0 15px 45px rgba(124,58,237,0.4); }}
    </style>
</head>
<body>
    <section class="hero">
        <div class="container text-center">
            <p class="text-uppercase small tracking-wider mb-3" style="letter-spacing:5px;opacity:0.5;">Bienvenido a</p>
            <h1 class="gradient-text">{description}</h1>
            <p class="lead fs-4 mb-4" style="opacity:0.7;">La mejor solucion para tus necesidades</p>
            <a href="#" class="btn btn-cta btn-lg me-3">Comenzar <i class="bi bi-arrow-right ms-2"></i></a>
            <a href="#" class="btn btn-outline-light btn-lg">Saber mas</a>
        </div>
    </section>
</body>
</html>
''',
        "html_dashboard": f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard — {description}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a0f; color: #e0e0e0; }}
        .sidebar {{ width: 260px; height: 100vh; position: fixed; background: rgba(255,255,255,0.03); border-right: 1px solid rgba(255,255,255,0.06); padding: 2rem 1rem; }}
        .sidebar a {{ display: block; padding: 12px 16px; border-radius: 12px; color: rgba(255,255,255,0.6); text-decoration: none; margin-bottom: 4px; transition: all 0.3s; }}
        .sidebar a:hover, .sidebar a.active {{ background: rgba(124,58,237,0.2); color: #a78bfa; }}
        .main {{ margin-left: 260px; padding: 2rem; }}
        .stat-card {{ background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 20px; padding: 1.5rem; }}
        .stat-value {{ font-size: 2.5rem; font-weight: 700; }}
    </style>
</head>
<body>
    <div class="sidebar">
        <h4 class="fw-bold mb-4"><i class="bi bi-grid-fill me-2" style="color:#a78bfa;"></i>{description}</h4>
        <a href="#" class="active"><i class="bi bi-house-fill me-2"></i>Inicio</a>
        <a href="#"><i class="bi bi-bar-chart-fill me-2"></i>Estadisticas</a>
        <a href="#"><i class="bi bi-people-fill me-2"></i>Usuarios</a>
        <a href="#"><i class="bi bi-gear-fill me-2"></i>Configuracion</a>
    </div>
    <div class="main">
        <h2>Dashboard</h2>
        <div class="row g-4 mt-3">
            <div class="col-md-3"><div class="stat-card"><p style="opacity:0.5;">Usuarios</p><p class="stat-value" style="color:#a78bfa;">1,234</p></div></div>
            <div class="col-md-3"><div class="stat-card"><p style="opacity:0.5;">Ventas</p><p class="stat-value" style="color:#60a5fa;">$45.2K</p></div></div>
            <div class="col-md-3"><div class="stat-card"><p style="opacity:0.5;">Visitas</p><p class="stat-value" style="color:#34d399;">89.1K</p></div></div>
            <div class="col-md-3"><div class="stat-card"><p style="opacity:0.5;">Tasa</p><p class="stat-value" style="color:#fbbf24;">12.5%</p></div></div>
        </div>
        <div class="row g-4 mt-3">
            <div class="col-md-8"><div class="stat-card"><canvas id="chart"></canvas></div></div>
            <div class="col-md-4"><div class="stat-card"><h5>Actividad Reciente</h5><p style="opacity:0.5;">Sin actividad reciente.</p></div></div>
        </div>
    </div>
    <script>
        new Chart(document.getElementById('chart'), {{
            type: 'line',
            data: {{ labels: ['Ene','Feb','Mar','Abr','May','Jun'], datasets: [{{ label: 'Ventas', data: [12,19,15,22,28,35], borderColor: '#a78bfa', tension: 0.4 }}] }},
            options: {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#e0e0e0' }} }} }} }}
        }});
    </script>
</body>
</html>
''',
    }
    if language == "html" and not has_form and not has_gallery:
        return templates["html"]
    if language == "html_landing":
        return templates["html_landing"]
    if language == "html_dashboard":
        return templates["html_dashboard"]
    return templates.get(language, f'# {description}\n# TODO: Implementar\n')


def _explain_code(code: str, language: str) -> str:
    lines = code.strip().split("\n")
    explanation = [
        f"Código ({language}, {len(lines)} líneas):",
        ""
    ]

    functions = []
    classes = []
    imports = []
    variables = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            imports.append(f"  L{i}: {stripped}")
        elif stripped.startswith("def "):
            name = stripped.split("(")[0].replace("def ", "")
            functions.append(f"  L{i}: {name}()")
        elif stripped.startswith("class "):
            name = stripped.split(":")[0].replace("class ", "")
            classes.append(f"  L{i}: {name}")
        elif "=" in stripped and not stripped.startswith("#"):
            var = stripped.split("=")[0].strip()
            if var and len(var) < 50:
                variables.append(f"  L{i}: {var}")

    if imports:
        explanation.append(f"Imports ({len(imports)}):")
        explanation.extend(imports[:10])
    if classes:
        explanation.append(f"\nClases ({len(classes)}):")
        explanation.extend(classes)
    if functions:
        explanation.append(f"\nFunciones ({len(functions)}):")
        explanation.extend(functions)
    if variables:
        explanation.append(f"\nVariables ({len(variables)}):")
        explanation.extend(variables[:10])

    if not any([imports, classes, functions, variables]):
        explanation.append("Código simple sin estructura detectable.")

    return "\n".join(explanation)


def _explain_file(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read(50000)
        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {".py": "python", ".js": "javascript", ".ts": "typescript",
                    ".html": "html", ".css": "css", ".java": "java",
                    ".go": "go", ".rs": "rust", ".sh": "bash"}
        lang = lang_map.get(ext, ext.replace(".", "") or "unknown")
        result = _explain_code(code, lang)
        return f"Archivo: {os.path.basename(file_path)}\n{result}"
    except Exception as e:
        return f"Error leyendo archivo: {e}"


def _edit_file_with_ai(file_path: str, description: str, language: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return f"Error leyendo archivo: {e}"

    # (b) Edición REAL con el modelo: devuelve el archivo COMPLETO ya editado.
    #     (Antes hacía matcheo por palabras clave y agregaba stubs TODO.)
    system = (
        f"Eres un programador experto en {language}. Aplicás un cambio a un "
        "archivo devolviendo el archivo COMPLETO ya modificado. NUNCA insertes "
        "'TODO: Implementar'. Devuelve SOLO el código completo, sin explicaciones "
        "y sin fences markdown (sin ```)."
    )
    prompt = (
        f"Archivo actual ({language}):\n\n{content}\n\n"
        f"Aplicá este cambio y devolvé el archivo COMPLETO ya editado:\n{description}"
    )
    try:
        from core.model_router import quick_chat
        new_content = _strip_fences(quick_chat(prompt, system=system, task="agent"))
    except Exception:
        new_content = ""

    if not new_content or "todo: implementar" in new_content.lower():
        return (
            "❌ No pude aplicar el cambio con el modelo (no respondió o generó "
            "un placeholder). NO modifiqué el archivo. Probá de nuevo."
        )

    # (c) Verificación: si es Python, debe compilar antes de sobreescribir.
    if language in ("python", "py"):
        problem = _verificar_codigo(new_content, language)
        if problem:
            return f"❌ El archivo editado NO compila ({problem}). NO lo sobreescribí."

    # Backup + rollback si algo falla al escribir.
    backup_path = file_path + ".bak"
    try:
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(content)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content if new_content.endswith("\n") else new_content + "\n")
    except Exception as e:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass
        return f"Error escribiendo archivo (rollback hecho): {e}"

    verif = "compila (py_compile OK)" if language in ("python", "py") else "sin placeholders"
    return (
        f"Archivo editado: {file_path}\n"
        f"Backup guardado en: {backup_path}\n"
        f"Cambio aplicado: {description}\n"
        f"Verificación: {verif}"
    )


def _find_python(project_dir: str) -> str:
    """Busca el intérprete del proyecto: .venv o venv (uno solo), si no, el sistema."""
    import shutil as _shutil
    for venv_name in (".venv", "venv"):
        for sub in (("bin", "python"), ("Scripts", "python.exe")):
            cand = os.path.join(project_dir, venv_name, *sub)
            if os.path.isfile(cand):
                return cand
    return _shutil.which("python3") or _shutil.which("python") or "python3"


def _verify_project(project_dir: str, app_module: str = "main",
                    endpoint: str = "/", port=0, test_path: str = "",
                    python: str = "", timeout: int = 60) -> str:
    """(c) Verificación end-to-end de un proyecto: import + pytest + servidor.

    Tres checks, todos obligatorios:
      1. import  — el módulo de la app importa sin excepción.
      2. tests   — pytest termina con returncode 0 (si no hay tests: FAIL).
      3. endpoint — uvicorn levanta y el endpoint RESPONDE HTTP de verdad.

    Veredicto: PASS 3/3 (se puede declarar listo) o FAIL x/3 (NO declarar).
    Correr SIEMPRE antes de decir que la tarea está terminada.
    """
    import re as _re
    import shutil as _shutil
    import signal as _signal
    import socket as _socket
    import time as _time
    import urllib.request as _urlreq
    import urllib.error as _urlerr

    if not project_dir:
        return ("Error: verify_project requiere 'project_dir' (la carpeta del "
                "proyecto a verificar).")
    project_dir = os.path.expanduser(str(project_dir))
    if not os.path.isdir(project_dir):
        return f"Error: no existe el directorio '{project_dir}'."

    py = python or _find_python(project_dir)
    if not os.path.isfile(py):
        py = _shutil.which(py) or py
    # Módulo: aceptar "main", "main.py" o "paquete.main"
    app_module = str(app_module).strip().strip("'\"")
    if app_module.endswith(".py"):
        app_module = app_module[:-3]

    checks: list[tuple[str, bool, str]] = []  # (nombre, ok, detalle)

    # ── 1) IMPORT: el módulo de la app debe importar sin excepción ──
    #    Se corre EXACTAMENTE como lo pide la consigna: desde la raíz del
    #    proyecto (uvicorn main:app). Si main.py está escondido en src/ y eso
    #    rompe el import, el check FALLA y se explica el motivo.
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = project_dir + os.pathsep + env.get("PYTHONPATH", "")
        r = subprocess.run(
            [py, "-c", f"import {app_module}; print('IMPORT_OK')"],
            capture_output=True, text=True, timeout=timeout,
            cwd=project_dir, env=env,
        )
        if r.returncode == 0 and "IMPORT_OK" in (r.stdout or ""):
            checks.append(("import", True, f"'{app_module}' importa OK con {py}"))
        else:
            err = (r.stderr or r.stdout or "").strip().splitlines()
            tail = " | ".join(err[-3:]) if err else "sin salida"
            hint = ""
            if not os.path.isfile(os.path.join(project_dir, app_module + ".py")):
                for sub in ("src", "app"):
                    if os.path.isfile(os.path.join(project_dir, sub, app_module + ".py")):
                        hint = (f" — NOTA: {app_module}.py está en {sub}/; la consigna "
                                f"pide servir con 'uvicorn {app_module}:app' desde la raíz. "
                                f"Elegí UN layout coherente y que raíz, tests y servidor "
                                f"matcheen.")
                        break
            checks.append(("import", False,
                           f"'{app_module}' NO importa (rc={r.returncode}): {tail[:400]}{hint}"))
    except subprocess.TimeoutExpired:
        checks.append(("import", False, f"import de '{app_module}' tardó >{timeout}s (posible loop/crash)"))
    except Exception as e:
        checks.append(("import", False, f"no se pudo ejecutar el import: {e}"))

    # ── 2) TESTS: pytest debe terminar en 0. Sin tests = FAIL (no se puede
    #       declarar 'listo sin verificar' si nadie corrió las pruebas) ──
    if not test_path:
        for cand in ("tests", "test"):
            if os.path.isdir(os.path.join(project_dir, cand)):
                test_path = cand
                break
        else:
            if os.path.isfile(os.path.join(project_dir, "test_main.py")):
                test_path = "test_main.py"
    if not test_path:
        checks.append(("tests", False,
                       "no hay carpeta tests/ ni archivos de test — no se puede verificar nada"))
    else:
        try:
            r = subprocess.run(
                [py, "-m", "pytest", test_path, "-q", "--no-header", "-x"],
                capture_output=True, text=True, timeout=max(timeout, 120),
                cwd=project_dir,
            )
            out = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
            if r.returncode == 0:
                m = _re.search(r"\d+ passed", out)
                resumen = m.group(0) if m else "todos pasaron"
                checks.append(("tests", True, f"pytest OK ({resumen})"))
            else:
                tail = [ln for ln in out.splitlines() if ln.strip()][-4:]
                checks.append(("tests", False,
                               f"pytest FALLA (rc={r.returncode}): {' | '.join(tail)[:400]}"))
        except subprocess.TimeoutExpired:
            checks.append(("tests", False, "pytest tardó demasiado (>120s)"))
        except Exception as e:
            checks.append(("tests", False, f"no se pudo correr pytest: {e}"))

    # ── 3) ENDPOINT: uvicorn real y golpe HTTP real al endpoint ──
    try:
        port = int(port or 0)
    except (TypeError, ValueError):
        port = 0
    if not port:
        with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
    url = f"http://127.0.0.1:{port}{endpoint if endpoint.startswith('/') else '/' + endpoint}"

    proc = None
    try:
        proc = subprocess.Popen(
            [py, "-m", "uvicorn", f"{app_module}:app",
             "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=project_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,  # grupo propio: killpg no mata a mi proceso
        )
        status = None
        last_err = ""
        deadline = _time.time() + 25
        while _time.time() < deadline:
            if proc.poll() is not None:
                last_err = f"uvicorn murió solo (rc={proc.poll()})"
                break
            try:
                with _urlreq.urlopen(url, timeout=3) as resp:
                    status = resp.status
                    break
            except _urlerr.HTTPError as he:
                status = he.code  # responder 4xx/5xx igualmente es RESPONDER
                break
            except Exception as e:
                last_err = str(e)[:120]
                _time.sleep(0.7)
        if status is not None and 200 <= status < 400:
            checks.append(("endpoint", True,
                           f"{url} RESPONDE (HTTP {status})"))
        elif status is not None:
            checks.append(("endpoint", False,
                           f"{url} contesta pero con HTTP {status} — el servidor "
                           f"levanta, pero ese endpoint no funciona (revisá la ruta)"))
        else:
            checks.append(("endpoint", False,
                           f"{url} SIN RESPUESTA en 25s ({last_err or 'nadie contesta'})"))
    except Exception as e:
        checks.append(("endpoint", False, f"no pude levantar uvicorn: {e}"))
    finally:
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), _signal.SIGTERM)
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass
            try:
                proc.wait(timeout=8)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    # ── Veredicto ──
    n_ok = sum(1 for _, ok, _ in checks if ok)
    total = 3
    veredicto = f"VERIFICACIÓN DE PROYECTO — {os.path.basename(project_dir.rstrip('/'))}: "
    lines = [veredicto + (f"PASS {n_ok}/{total} ✅" if n_ok == total else f"FAIL {n_ok}/{total} ❌")]
    for name, ok, detalle in checks:
        lines.append(f"  {'✅' if ok else '❌'} {name}: {detalle}")
    if n_ok == total:
        lines.append("  → Todo verde. Puedes declarar la tarea COMPLETA.")
    else:
        lines.append("  → NO declares la tarea lista. Arreglá los puntos ❌ y volvé a "
                     "correr verify_project hasta PASS 3/3.")
    return "\n".join(lines)


def _run_file(file_path: str, language: str, args: str, timeout: int) -> str:
    cmd_map = {
        "python": ["python", file_path],
        "py": ["python", file_path],
        "javascript": ["node", file_path],
        "js": ["node", file_path],
        "bash": ["bash", file_path],
        "shell": ["bash", file_path],
        "go": ["go", "run", file_path],
    }
    cmd = cmd_map.get(language)
    if not cmd:
        return f"Extensión '{language}' no soportada para ejecutar."

    if args:
        cmd.extend(args.split())

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=os.path.dirname(file_path) or "."
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[Código de salida: {result.returncode}]"
        return output or "Ejecutado sin salida."
    except subprocess.TimeoutExpired:
        return f"Timeout después de {timeout}s."
    except Exception as e:
        return f"Error ejecutando: {e}"


def _build_file(file_path: str, language: str, args: str, timeout: int) -> str:
    if language in ("c", "cpp"):
        out = os.path.splitext(file_path)[0] + ".exe"
        cmd = ["gcc" if language == "c" else "g++", file_path, "-o", out]
        if args:
            cmd.extend(args.split())
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return f"Compilado exitosamente: {out}"
            return f"Error de compilación:\n{result.stderr}"
        except Exception as e:
            return f"Error compilando: {e}"
    elif language == "go":
        try:
            result = subprocess.run(["go", "build", file_path], capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return f"Build exitoso: {os.path.splitext(file_path)[0]}.exe"
            return f"Error de build:\n{result.stderr}"
        except Exception as e:
            return f"Error compilando: {e}"

    return f"Build no soportado para '{language}'. Usa run en su lugar."
