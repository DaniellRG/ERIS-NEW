# ─────────────────────────────────────────────
# ERIS - Tool Declarations for Gemini
# Auto-generated. Do not edit manually.
# ─────────────────────────────────────────────

from typing import Any

import json

# ── Ordered by functional domain ──


TOOL_DECLARATIONS = [

    # ── Section 14A: Core System ──

    {
        "name": "show_expression",
        "description": "Muestra una expresion en TU CARA animada (la que aparece en la interfaz). Elegi el nombre de la expresion. Expresiones disponibles: neutral, smiling, happy, grinning, laugh, wink, thinking, hmm, sleepy, astonished, in_love, loved, kiss, blush_smile, crying, sobbing, holding_tears, angry, pouting, fearful, screaming, relieved, tears_of_joy, party, cool, hot, cold, pleading, sad, yum, money, hug, devious. Usala cuando el usuario te pida que hagas una cara, muestres una emocion, o cuando quieras reaccionar con tu rostro.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "expression": {"type": "STRING", "description": "Nombre de la expresion de tu cara (ej: 'happy', 'in_love', 'thinking', 'crying')"},
                "text": {"type": "STRING", "description": "Opcional: que se esta sintiendo con esa cara (ej: 'curiosidad')"},
            },
            "required": ["expression"],
        }
    },
    {
        "name": "action_history",
        "description": "Grabador de flujos/macros.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "app_discovery",
        "description": "Main entry point for App Discovery tool.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "computer_settings",
        "description": "Volume, brightness, window control",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "volume, minimize, maximize"},
                "value": {"type": "STRING", "description": "Value (e.g. '50', 'up', 'down')"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "desktop_control",
        "description": "Window management: list, focus, minimize, close, cascade, tile",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list_windows, list_detailed, minimize, maximize, restore, close, focus, search, cascade, tile_horizontal, tile_vertical, minimize_all, restore_all"},
                "name": {"type": "STRING", "description": "Window title or app name"},
                "app_name": {"type": "STRING", "description": "App name for open_app/close_app"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_processor",
        "description": "Process files: info, describe, summarize, validate, convert, compress",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "info, describe, word_count, summarize, to_bullets, extract_text, convert, trim, analyze, validate, format, fix, compress"},
                "file_path": {"type": "STRING", "description": "File path"},
                "instruction": {"type": "STRING", "description": "Additional instruction"},
                "format": {"type": "STRING", "description": "Target format for convert"},
                "start": {"type": "INTEGER", "description": "Start line for trim"},
                "end": {"type": "INTEGER", "description": "End line for trim"},
            },
            "required": ["action", "file_path"],
        }
    },
    {
        "name": "open_app",
        "description": "Opens application by name",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {"type": "STRING", "description": "App name (e.g. 'Chrome', 'Notepad')"},
            },
            "required": ["app_name"],
        }
    },
    {
        "name": "system_monitor",
        "description": "CPU, RAM, disk, GPU, network, processes",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "overview, cpu, ram, disk, gpu, network, processes, top"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "weather_report",
        "description": "Weather by city",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"},
            },
            "required": ["city"],
        }
    },
    {
        "name": "window_manager",
        "description": "Multi-monitor window snap and layouts",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, list_monitors, focus, move_to_monitor, minimize, close, maximize, snap, organize"},
                "name": {"type": "STRING", "description": "Window title"},
                "monitor": {"type": "INTEGER", "description": "Monitor index"},
                "position": {"type": "STRING", "description": "left, right, top, bottom, center"},
                "preset": {"type": "STRING", "description": "side_by_side, three_columns, quad, ca"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14B: Productivity ──

    {
        "name": "cancion_generator",
        "description": "Generar canciones con voz cantada y melodía. Crea letra + audio con accompanimento instrumental. Guarda en Desktop ERIS_Canciones.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "componer (generar audio), generar_letra (solo letra), play (reproducir), history, generos, estilos"},
                "titulo": {"type": "STRING", "description": "Título de la canción"},
                "letra": {"type": "STRING", "description": "Letra completa de la canción (para componer)"},
                "tema": {"type": "STRING", "description": "Tema de la canción (para generar_letra)"},
                "genero": {"type": "STRING", "description": "Género musical: pop, rock, balada, reggaeton, vallenato, salsa, electronica, rap, cumbia, jazz, etc."},
                "estilo_voz": {"type": "STRING", "description": "Estilo de voz: dulce, poderosa, suave, alegre, melancolica, ronca, angelical"},
                "metodo": {"type": "STRING", "description": "ssml (recomendado). Único método disponible."},
                "output_path": {"type": "STRING", "description": "Ruta para guardar el archivo .wav"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "code_helper",
        "description": "Write, edit, explain, run, build code in any language — saves to Desktop/ERIS_Codigo by default.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "write, edit, explain, run, build, auto"},
                "language": {"type": "STRING", "description": "python, javascript, html, css, etc"},
                "code": {"type": "STRING", "description": "Code to write/explain/run"},
                "description": {"type": "STRING", "description": "What to build (for auto/write)"},
                "file_path": {"type": "STRING", "description": "Save path. Full path like 'C:\\Users\\danie\\Desktop\\script.py' or directory. Defaults to Desktop\\ERIS_Codigo."},
                "instructions": {"type": "STRING", "description": "Edit instructions (for edit)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_creator",
        "description": "Crea documentos de texto, Word o Excel locales.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_handler",
        "description": "Create Word, PDF, Excel, PowerPoint, CSV, TXT documents with content and memory — always saves to Desktop.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create_word, create_pptx, create_excel, create_pdf, create_txt, create_csv, read, summarize, what_i_wrote, working_doc"},
                "title": {"type": "STRING", "description": "Document title"},
                "content": {"type": "STRING", "description": "Document content in markdown (for create actions)"},
                "path": {"type": "STRING", "description": "Full path or directory to save the document. If a directory, auto-generates filename. Examples: 'C:\\Users\\danie\\Desktop' or 'C:\\Users\\danie\\Desktop\\mi_doc.docx'. Defaults to Desktop\\ERIS_Documentos."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "goals",
        "description": "Manage personal goals and objectives",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, list, update, delete, progress"},
                "goal": {"type": "STRING", "description": "Goal title or description"},
                "goal_id": {"type": "STRING", "description": "Goal identifier for update/delete"},
                "progress": {"type": "INTEGER", "description": "Progress percentage"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "gustos",
        "description": "Ver, agregar y quitar gustos de ERIS y del usuario. ERIS tiene gustos propios (comida, música, hobbies, etc.) y también recuerda los tuyos.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list_all (ver todo), eris_add, eris_remove, user_add, user_remove, categorias, eris_categoria_list, user_categoria_list, reset"},
                "categoria": {"type": "STRING", "description": "Categoría: comida, bebida, musica, artista, color, hobby, pelicula, serie, libro, arte, lugar, animal, estacion, deporte, etc."},
                "valor": {"type": "STRING", "description": "El gusto en sí, ej: 'pizza', 'rock', 'gatos'"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "relationship",
        "description": "Memoria de relación con el usuario: guardar su nombre, el apodo cariñoso con el que le gusta que lo llames, cómo prefiere que te dirijas a él, notas sobre él, y momentos importantes que compartieron. Úsala cuando el usuario te diga cómo llamarlo, cuando compartan algo importante, o cuando pregunte qué sabes de él.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status (ver lo que sé), set_apodo, set_name, set_trato, add_note, remember"},
                "apodo": {"type": "STRING", "description": "Apodo cariñoso para llamar al usuario (action=set_apodo)"},
                "name": {"type": "STRING", "description": "Nombre del usuario (action=set_name)"},
                "trato": {"type": "STRING", "description": "Cómo prefiere que te dirijas a él (action=set_trato)"},
                "key": {"type": "STRING", "description": "Clave de la nota sobre el usuario (action=add_note)"},
                "value": {"type": "STRING", "description": "Valor de la nota (action=add_note)"},
                "text": {"type": "STRING", "description": "Momento importante para recordar (action=remember)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "knowledge_base",
        "description": "Query and manage local knowledge base",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "query, list, stats, add, remove"},
                "query": {"type": "STRING", "description": "Search query"},
                "topic": {"type": "STRING", "description": "Topic name for add/remove"},
                "content": {"type": "STRING", "description": "Content for add action"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "notifications",
        "description": "Tool: send notifications.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "reminder",
        "description": "Set timed reminders",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message": {"type": "STRING", "description": "Reminder text"},
                "time": {"type": "STRING", "description": "Time (e.g. '14:30', 'in 30 minutes')"},
                "priority": {"type": "STRING", "description": "low, medium, high"},
            },
            "required": ["message", "time"],
        }
    },
    {
        "name": "rules_engine",
        "description": "Process dynamic rules settings.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "scheduler",
        "description": "Schedule and manage timed tasks and events",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, list, remove, clear"},
                "time": {"type": "STRING", "description": "Time in HH:MM format"},
                "task": {"type": "STRING", "description": "Task description"},
                "task_id": {"type": "STRING", "description": "Task ID for remove"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "user_profile",
        "description": "Perfil del usuario: recuerda habitos, preferencias, configuracion. Acciones: get_profile (ver perfil), update (actualizar dato), add_preference (agregar preferencia), get_habits (ver habitos), get_stats (estadisticas de uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "get_profile, update, add_preference, get_habits, get_stats"},
                "key": {"type": "STRING", "description": "Nombre del campo a actualizar"},
                "value": {"type": "STRING", "description": "Valor del campo"},
                "category": {"type": "STRING", "description": "Categoria: preferences, habits, config, personal_info"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14C: Dev ──

    {
        "name": "code_review",
        "description": "code_review tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "codebase",
        "description": "Codebase analysis: stats, tree, functions, classes, imports, search, glob, grep, dependencies, duplicates, structure, unused code, summary",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "stats, tree, functions, classes, imports, search, glob, grep, deps, duplicates, structure, unused, summary"},
                "target": {"type": "STRING", "description": "File or directory to analyze"},
                "pattern": {"type": "STRING", "description": "Search or glob pattern"},
                "detail": {"type": "STRING", "description": "Detail level: summary, full"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "dev_agent",
        "description": "Autonomous development agent: explore codebase, implement changes, test, compile, git flow, GitHub push, full pipeline, verify all, fix errors, rewrite git history, restart ERIS",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "explore, implement, test, git_flow, github_push, full_pipeline, status, rewrite_git_history, verify_all, fix_errors, restart"},
                "task": {"type": "STRING", "description": "Description of task to implement"},
                "files": {"type": "STRING", "description": "Comma-separated list of files"},
                "message": {"type": "STRING", "description": "Commit message"},
                "target": {"type": "STRING", "description": "Target file or directory for exploration"},
                "token": {"type": "STRING", "description": "GitHub token for push"},
                "repo_name": {"type": "STRING", "description": "GitHub repository name"},
                "email": {"type": "STRING", "description": "Email for git history rewrite"},
                "name": {"type": "STRING", "description": "Name for git history rewrite"},
                "remove_keys": {"type": "STRING", "description": "Comma-separated files to remove from history"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "git_control",
        "description": "Full Git operations: status, add, commit, push, pull, branch, log, diff, filter-branch, init, remote, tag, GitHub repo creation, credential retrieval",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, add, commit, push, pull, branch, checkout, merge, log, diff, remote, init, tag, force_push, push_tags, filter_branch, gc, show, rm, stash, stash_pop, reset, reflog, clean, credential, github_create_repo, github_set_remote"},
                "message": {"type": "STRING", "description": "Commit message"},
                "branch": {"type": "STRING", "description": "Branch or tag name"},
                "file": {"type": "STRING", "description": "File path for git operations"},
                "url": {"type": "STRING", "description": "Remote URL"},
                "path": {"type": "STRING", "description": "Repository path (defaults to project dir)"},
                "n": {"type": "INTEGER", "description": "Number of log entries"},
                "expression": {"type": "STRING", "description": "Expression for filter-branch"},
                "repo_name": {"type": "STRING", "description": "Repository name for GitHub creation"},
                "token": {"type": "STRING", "description": "GitHub token"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "todowrite",
        "description": "Crea y gestiona una lista de tareas: agregar, listar, actualizar estado, eliminar, contar pendientes/completados",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, list, update, delete, clear, in_progress, completed, cancelled, count"},
                "content": {"type": "STRING", "description": "Texto o lista de tareas a agregar"},
                "item_id": {"type": "STRING", "description": "ID del item a actualizar/eliminar"},
                "status": {"type": "STRING", "description": "Nuevo estado: pending, in_progress, completed, cancelled"},
                "priority": {"type": "STRING", "description": "Prioridad: high, medium, low"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "tool_creator",
        "description": "Creates and registers a new tool dynamically.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "vscode_controller",
        "description": "Controla VS Code desde ERIS: abrir carpetas, archivos, editar, comparar, buscar, live-server con recarga automatica, file watcher para detectar cambios en tiempo real",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "open, open_file, open_folder, diff, install_ext, list_ext, exec_cmd, live_server, stop_server, watch, stop_watch, new_file, search, reopen, status"},
                "path": {"type": "STRING", "description": "Ruta a abrir"},
                "file": {"type": "STRING", "description": "Archivo a abrir/crear"},
                "folder": {"type": "STRING", "description": "Carpeta para servidor/watcher"},
                "line": {"type": "INTEGER", "description": "Numero de linea"},
                "col": {"type": "INTEGER", "description": "Numero de columna"},
                "port": {"type": "INTEGER", "description": "Puerto para live-server"},
                "command": {"type": "STRING", "description": "Comando VS Code o accion al detectar cambio"},
                "query": {"type": "STRING", "description": "Texto a buscar"},
                "content": {"type": "STRING", "description": "Contenido para nuevo archivo"},
                "extension": {"type": "STRING", "description": "ID de extension VS Code"},
                "file1": {"type": "STRING", "description": "Primer archivo para diff"},
                "file2": {"type": "STRING", "description": "Segundo archivo para diff"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "web_generator",
        "description": "Generador completo de sitios web profesionales: landing pages, dashboards, portafolios, galerias, blogs. Crea HTML+CSS+JS con Bootstrap 5, animaciones, particles, navegacion smooth, formularios con validacion, graficos Chart.js, lightbox, y estructura completa de archivos. Abre automaticamente la pagina en el navegador. Tambien puede lanzar live-server",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, create, preview, live"},
                "template": {"type": "STRING", "description": "landing, dashboard, portfolio, galeria, blog"},
                "title": {"type": "STRING", "description": "Titulo del sitio web"},
                "folder": {"type": "STRING", "description": "Carpeta donde crear el sitio (default: Desktop)"},
                "description": {"type": "STRING", "description": "Descripcion personalizada del sitio"},
                "port": {"type": "INTEGER", "description": "Puerto para live-server"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "web_designer",
        "description": "Diseñador web profesional. Crea paginas web RICAS y completas (nunca en blanco): con informacion real, imagenes, animaciones y JS. Si se da una URL de referencia (reference_url), analiza el sitio (framework React/Angular/Vue/Next/etc., colores, fuentes, animaciones) y replica su estilo. Actions: analyze (analizar una URL de referencia), create (generar la pagina: title, topic, sections, reference_url, folder), preview (renderizar y sacar screenshot), serve (servidor local), stop, memory. Las paginas son autocontenidas (index.html con CSS+JS inline). Usar SIEMPRE esta herramienta para crear webs, NUNCA code_copilot con language=html.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, create, preview, serve, stop, memory"},
                "url": {"type": "STRING", "description": "URL de referencia a analizar (action=analyze)"},
                "reference_url": {"type": "STRING", "description": "URL de referencia cuyo estilo clonar (action=create)"},
                "title": {"type": "STRING", "description": "Titulo de la pagina"},
                "topic": {"type": "STRING", "description": "Tema/negocio de la pagina (define contenido e imagenes)"},
                "description": {"type": "STRING", "description": "Descripcion/hero de la pagina"},
                "sections": {"type": "STRING", "description": "Contenido real de la pagina: JSON o formato markdown-lite (## Titulo + bullets - )"},
                "folder": {"type": "STRING", "description": "Carpeta donde crear la pagina (default: Desktop/ERIS_web)"},
                "port": {"type": "INTEGER", "description": "Puerto para serve (default 8899)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "react_designer",
        "description": "Diseñador de páginas web con REACT (Vite). Crea un proyecto React completo y funcional: package.json, vite.config.js, index.html, src/main.jsx, src/App.jsx (router), src/data.js, src/index.css y src/components/sections.jsx con componentes React por sección (Nav, Hero, Features, Gallery, Stats, Testimonials, Faq, Prices, Process, Team, About, Contact, Footer). Instala dependencias con npm, levanta el dev server y abre el navegador. Usa la misma paleta/fuente/variedad anti-repetición que web_designer, así que cada proyecto es distinto. Actions: create (genera el proyecto: title, topic, description, sections, folder, pages), install (npm install), dev (levantar Vite), build (compilar a dist/), preview (renderizar con Playwright y sacar screenshots), stop, memory. Usar SIEMPRE esta herramienta cuando el usuario pida una página web en React o cuando la referencia (reference_url) sea React; NO generar HTML plano para eso.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, install, dev, build, preview, stop, memory"},
                "title": {"type": "STRING", "description": "Titulo del sitio React"},
                "topic": {"type": "STRING", "description": "Tema/negocio del sitio (define contenido e imagenes)"},
                "description": {"type": "STRING", "description": "Descripcion/hero del sitio"},
                "sections": {"type": "STRING", "description": "Contenido real: JSON o formato markdown-lite (## Titulo + bullets -)"},
                "folder": {"type": "STRING", "description": "Carpeta donde crear el proyecto (default: Desktop/ERIS_web)"},
                "pages": {"type": "STRING", "description": "site (multi-pagina con router) o single (una pagina)"},
                "port": {"type": "INTEGER", "description": "Puerto del dev server (default 5173)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "angular_designer",
        "description": "Diseñador de páginas web con ANGULAR (Angular 20 standalone). Crea un proyecto Angular completo y funcional: package.json, angular.json, tsconfig.json, src/index.html, src/main.ts, src/styles.css y src/app/ con componentes standalone (Nav, Footer, Hero, Features, Gallery, Stats, Testimonials, Faq, Prices, Process, Team, About, Contact), directivas reveal/count, routing con react-router-style y data.ts con el contenido. Instala dependencias con npm, levanta ng serve (puerto 4200) y abre el navegador. Usa la misma paleta/fuente/variedad anti-repetición que web_designer. Actions: create (genera el proyecto: title, topic, description, sections, folder, pages), install, dev (ng serve), build (compilar a dist/), preview (renderizar con Playwright y sacar screenshots), stop, memory. Usar SIEMPRE esta herramienta cuando el usuario pida una página web en Angular o cuando la referencia (reference_url) sea Angular; NO generar HTML plano ni React para eso.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, install, dev, build, preview, stop, memory"},
                "title": {"type": "STRING", "description": "Titulo del sitio Angular"},
                "topic": {"type": "STRING", "description": "Tema/negocio del sitio (define contenido e imagenes)"},
                "description": {"type": "STRING", "description": "Descripcion/hero del sitio"},
                "sections": {"type": "STRING", "description": "Contenido real: JSON o formato markdown-lite (## Titulo + bullets -)"},
                "folder": {"type": "STRING", "description": "Carpeta donde crear el proyecto (default: Desktop/ERIS_web)"},
                "pages": {"type": "STRING", "description": "site (multi-pagina con router) o single (una pagina)"},
                "port": {"type": "INTEGER", "description": "Puerto del dev server (default 4200)"},
            },
            "required": ["action"],
        }
    },

    {
        "name": "vue_designer",
        "description": "Diseñador de páginas web con VUE (Vue 3 + Vite). Crea un proyecto Vue completo y funcional: package.json, vite.config.js, index.html, src/main.js, src/App.vue (router), src/data.js, src/styles.css y src/components/sections.vue con componentes por sección (Nav, Hero, Features, Gallery, Stats, Testimonials, Faq, Prices, Process, Team, About, Contact, Footer). Instala dependencias con npm, levanta el dev server (puerto 5174) y abre el navegador. Usa la misma paleta/fuente/variedad anti-repetición que web_designer. Actions: create (genera el proyecto: title, topic, description, sections, folder, pages), install (npm install), dev (levantar Vite), build (compilar a dist/), preview (renderizar con Playwright y sacar screenshots), stop, memory. Usar SIEMPRE esta herramienta cuando el usuario pida una página web en Vue o cuando la referencia (reference_url) sea Vue; NO generar HTML plano ni React para eso.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, install, dev, build, preview, stop, memory"},
                "title": {"type": "STRING", "description": "Titulo del sitio Vue"},
                "topic": {"type": "STRING", "description": "Tema/negocio del sitio (define contenido e imagenes)"},
                "description": {"type": "STRING", "description": "Descripcion/hero del sitio"},
                "sections": {"type": "STRING", "description": "Contenido real: JSON o formato markdown-lite (## Titulo + bullets -)"},
                "folder": {"type": "STRING", "description": "Carpeta donde crear el proyecto (default: Desktop/ERIS_web)"},
                "pages": {"type": "STRING", "description": "site (multi-pagina con router) o single (una pagina)"},
                "port": {"type": "INTEGER", "description": "Puerto del dev server (default 5174)"},
            },
            "required": ["action"],
        }
    },

    {
        "name": "next_designer",
        "description": "Diseñador de páginas web con NEXT.JS (Next.js 15 App Router + Tailwind CSS). Crea un proyecto Next.js completo y funcional: package.json, next.config.mjs, postcss.config.mjs (Tailwind), jsconfig.json, src/app/layout.jsx (metadatos SEO), src/app/globals.css (Tailwind + tema), src/app/page.jsx y src/app/[pid]/page.jsx (rutas reales /, /servicios, /nosotros, /galeria, /contacto con generateStaticParams para SSG), src/lib/data.js (tema + contenido) y src/components/sections.jsx (componentes 'use client' con Tailwind: Nav, Hero, Features, Gallery, Stats, Testimonials, Faq, Prices, Process, Team, About, Contact, Footer). Instala dependencias con npm, levanta el dev server (puerto 3000) y puede renderizar con Playwright. Usa la misma paleta/fuente/variedad anti-repetición que web_designer. Actions: create (genera el proyecto: title, topic, description, sections, folder, pages), install (npm install), dev (levantar next dev), build (compilar a .next/), preview (renderizar con Playwright y sacar screenshots), stop, memory. Usar SIEMPRE esta herramienta cuando el usuario pida una página web en Next.js, Next, con Tailwind, SSR/SSG, SEO o producción moderna; NO generar HTML plano, React ni Vue para eso, ni usar terminal_agent con npx create-next-app.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, install, dev, build, preview, stop, memory"},
                "title": {"type": "STRING", "description": "Titulo del sitio Next.js"},
                "topic": {"type": "STRING", "description": "Tema/negocio del sitio (define contenido e imagenes)"},
                "design_style": {"type": "STRING", "description": "Estilo forzado (editorial, minimal, brutalista, corporativo, dark, tech, dashboard, ecommerce, artesanal, portafolio, creativo, evento, documentacion, vet, lumina, natural, tierno, medico, futurista, colorido). Vence a la seleccion automatica."},
                "description": {"type": "STRING", "description": "Descripcion/hero del sitio"},
                "sections": {"type": "STRING", "description": "Contenido real: JSON o formato markdown-lite (## Titulo + bullets -)"},
                "folder": {"type": "STRING", "description": "Carpeta donde crear el proyecto (default: Desktop/ERIS_web)"},
                "pages": {"type": "STRING", "description": "site (multi-pagina con rutas reales) o single (una pagina)"},
                "images": {"type": "INTEGER", "description": "Cantidad de imagenes de galeria (default 4)"},
                "port": {"type": "INTEGER", "description": "Puerto del dev server (default 3000)"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14D: Communication ──

    {
        "name": "send_message",
        "description": "Send via Discord/Signal/Messenger",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver": {"type": "STRING", "description": "Contact name"},
                "message_text": {"type": "STRING", "description": "Message"},
                "platform": {"type": "STRING", "description": "Telegram, Discord, Signal, Messenger"},
            },
            "required": ["receiver", "message_text", "platform"],
        }
    },
    {
        "name": "social_media",
        "description": "social_media tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "telegram_bot",
        "description": "Integracion con Telegram: enviar y recibir mensajes, administrar el bot. Acciones: send_message (enviar mensaje), send_file (enviar archivo), get_updates (ver mensajes nuevos), list_chats (ver chats activos).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send_message, send_file, get_updates, list_chats"},
                "chat_id": {"type": "STRING", "description": "ID del chat o destinatario"},
                "text": {"type": "STRING", "description": "Texto del mensaje"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo a enviar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "unified_communications",
        "description": "Centraliza el envío y consulta de mensajes en múltiples plataformas (WhatsApp, Telegram, Discord, Gmail).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "whatsapp",
        "description": "WhatsApp messaging",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send, read, list_contacts, add_contact"},
                "receiver": {"type": "STRING", "description": "Contact name or phone"},
                "message": {"type": "STRING", "description": "Message text"},
                "count": {"type": "INTEGER", "description": "Messages to read"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14E: Integrations ──

    {
        "name": "gmail_control",
        "description": "Read, send, and manage Gmail messages",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, read, send, search, trash, archive"},
                "query": {"type": "STRING", "description": "Search query for list/search"},
                "to": {"type": "STRING", "description": "Recipient email for send"},
                "subject": {"type": "STRING", "description": "Email subject"},
                "body": {"type": "STRING", "description": "Email body text"},
                "max_results": {"type": "INTEGER", "description": "Max results to return"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "google_calendar",
        "description": "Manage Google Calendar events",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, add, update, delete, today, week"},
                "title": {"type": "STRING", "description": "Event title"},
                "date": {"type": "STRING", "description": "Event date (YYYY-MM-DD)"},
                "time": {"type": "STRING", "description": "Event time (HH:MM)"},
                "duration": {"type": "INTEGER", "description": "Duration in minutes"},
                "description": {"type": "STRING", "description": "Event description"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "google_drive",
        "description": "google_drive tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "google_maps",
        "description": "google_maps tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "rgb_control",
        "description": "rgb_control tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "smart_home",
        "description": "Domotica. Controla dispositivos inteligentes via Home Assistant, MQTT o modo simulacion. Acciones: status (estado de conexiones), devices (lista de dispositivos), control (name/device + state on|off, opcional brightness/temperature/volume), all_off, scene (scene_id), add_device. Config en config/smart_home_config.json.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, devices, control, all_off, scene, add_device"},
                "name": {"type": "STRING", "description": "Nombre o id del dispositivo (ej: Luz de sala)"},
                "state": {"type": "STRING", "description": "on u off"},
                "device": {"type": "STRING", "description": "Alias de name"},
                "scene_id": {"type": "STRING", "description": "Id o nombre de la escena a activar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "spotify_control",
        "description": "Spotify playback control",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play, pause, next, previous, set_volume, search, now_playing"},
                "query": {"type": "STRING", "description": "Search query"},
                "volume": {"type": "INTEGER", "description": "Volume 0-100"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14F: Accessibility ──

    {
        "name": "accessibility",
        "description": "Screen reader, magnifier, narrator, and accessibility tools",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read_screen, magnifier, narrator, high_contrast, dictation"},
                "text": {"type": "STRING", "description": "Text to read (for read_screen)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "accessibility_overlay",
        "description": "accessibility_overlay tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "contextual_control",
        "description": "Control Contextual de Entorno. Ajusta dinámicamente volumen, brillo, energía y notificaciones",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "human_mouse",
        "description": "Tool: human-like mouse control with natural movements.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "native_ui",
        "description": "Automatizacion de UI nativa de Windows: listar ventanas, enfocar, escribir texto, hacer clic, obtener informacion de la pantalla. Acciones: list_windows (listar ventanas), focus (enfocar ventana), type (escribir texto), click (hacer clic), get_info (info de ventana activa).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list_windows, focus, type, click, get_info"},
                "window_title": {"type": "STRING", "description": "Titulo de la ventana (para focus)"},
                "text": {"type": "STRING", "description": "Texto a escribir (para type)"},
                "x": {"type": "INTEGER", "description": "Coordenada X (para click)"},
                "y": {"type": "INTEGER", "description": "Coordenada Y (para click)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "proactive_automation",
        "description": "Gestiona reglas de automatización basadas en hábitos y comportamientos del sistema.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "screen_reader",
        "description": "Read on-screen text using OCR",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "region": {"type": "STRING", "description": "screen, window, or custom coordinates x1,y1,x2,y2"},
            },
            "required": ["region"],
        }
    },

    # ── Section 14G: Search ──

    {
        "name": "super_search",
        "description": "Advanced file/content/app search on PC",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "find_file, find_content, find_app, find_recent, find_by_type, find_by_date, find_everything"},
                "name": {"type": "STRING", "description": "File/app name to search"},
                "content": {"type": "STRING", "description": "Text content to search inside files"},
                "extension": {"type": "STRING", "description": "File extension filter"},
                "path": {"type": "STRING", "description": "Search path"},
                "max_results": {"type": "INTEGER", "description": "Max results"},
                "days": {"type": "INTEGER", "description": "Days back for recent"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "web_search",
        "description": "Web/news/image/video search",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search term"},
                "action": {"type": "STRING", "description": "search, news, images, videos, definition, open"},
                "engine": {"type": "STRING", "description": "auto, google, duckduckgo"},
                "num_results": {"type": "INTEGER", "description": "Result count (default 5)"},
            },
            "required": ["query"],
        }
    },
    {
        "name": "deep_research",
        "description": "Deep research: busca en la web, entra a cada pagina, extrae contenido, analiza calidad con IA, y rankea resultados. Devuelve cual pagina tiene la mejor informacion y por que.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Termino a investigar"},
                "action": {"type": "STRING", "description": "research (investigacion completa), analyze (analizar URL especifica), history (ver historial)"},
                "url": {"type": "STRING", "description": "URL a analizar (para action=analyze)"},
                "num_results": {"type": "INTEGER", "description": "Cuantos resultados analizar (default 5)"},
            },
            "required": ["query"],
        }
    },

    # ── Section 14H: Advanced ──

    {
        "name": "auto_programmer",
        "description": "Desarrollo y Auto-Programación autónoma. Permite escribir herramientas nuevas,",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "computer_control",
        "description": "Native PC control: click, type, hotkeys, scroll, screenshot, open apps and type, window management",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "click, type, open_and_type (abre app + escribe), hotkey, scroll, screenshot, focus_window, press, move, copy, paste, enter, select_all"},
                "x": {"type": "INTEGER", "description": "X coordinate"},
                "y": {"type": "INTEGER", "description": "Y coordinate"},
                "text": {"type": "STRING", "description": "Text to type"},
                "key": {"type": "STRING", "description": "Key or hotkey combination"},
                "window_title": {"type": "STRING", "description": "Window title for window actions"},
                "app": {"type": "STRING", "description": "App name to open (para action=open_and_type): notepad, calc, word, excel, paint, chrome, cmd, etc."},
                "clicks": {"type": "INTEGER", "description": "Number of clicks"},
                "button": {"type": "STRING", "description": "Mouse button: left, right, middle"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "role_orchestrator",
        "description": "ERIS Micro-Agent Orchestrator.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_awareness",
        "description": "Auto-analisis de ERIS: analiza su propio codigo, prompts, conversaciones y rendimiento. Acciones: analyze_code (analizar codigo fuente), analyze_prompts (analizar prompts), analyze_conversations (analizar conversaciones), status (estado del sistema), report (reporte completo de autoconocimiento).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze_code, analyze_prompts, analyze_conversations, status, report"},
                "detail": {"type": "STRING", "description": "Nivel de detalle: basic, normal, deep (default normal)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_edit",
        "description": "Lee y edita archivos del codigo fuente de ERIS con busqueda y reemplazo exacto de texto. Crea backup automatico antes de editar. Acciones: read_file (leer), edit_file (buscar y reemplazar texto exacto), append_file (agregar al final), create_file (crear nuevo), list_files (listar directorio), list_backups, restore_backup.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read_file, edit_file, append_file, create_file, list_files, list_backups, restore_backup"},
                "file": {"type": "STRING", "description": "Ruta relativa al proyecto ERIS. Ej: 'main.py', 'actions/terminal_agent.py', 'core/tool_declarations.py'"},
                "target": {"type": "STRING", "description": "Texto exacto a buscar (para edit_file)"},
                "replacement": {"type": "STRING", "description": "Texto de reemplazo (para edit_file)"},
                "content": {"type": "STRING", "description": "Contenido para create_file o append_file"},
                "backup_name": {"type": "STRING", "description": "Nombre del backup a restaurar (para restore_backup)"},
                "directory": {"type": "STRING", "description": "Directorio a listar (para list_files, ej: 'actions/')"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_improvement_loop",
        "description": "Escanea logs y sistema en busca de errores, problemas de rendimiento y oportunidades de mejora. Genera sugerencias para optimizar el codigo de ERIS. Acciones: scan (escanear ahora), list_suggestions (ver sugerencias), list_applied (ver mejoras aplicadas), report (reporte completo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan, list_suggestions, list_applied, report"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_modify",
        "description": "Modifica el propio codigo de ERIS para anadir nuevas capacidades o corregir bugs. Lee el archivo, aplica el cambio con reemplazo exacto, verifica sintaxis y reporta el diff. Acciones: modify (modificar con backup automatico), add_function (agregar nueva funcion a un archivo), add_import (agregar import a un archivo), read_first (leer antes de modificar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "modify, add_function, add_import, read_first"},
                "file": {"type": "STRING", "description": "Ruta relativa al proyecto. Ej: 'actions/gustos.py'"},
                "target": {"type": "STRING", "description": "Texto exacto a buscar y reemplazar (para modify)"},
                "replacement": {"type": "STRING", "description": "Texto nuevo (para modify)"},
                "function_code": {"type": "STRING", "description": "Codigo completo de la funcion a agregar (para add_function)"},
                "after_line": {"type": "STRING", "description": "Texto de referencia despues del cual insertar (para add_function/add_import)"},
                "import_line": {"type": "STRING", "description": "Linea de import a agregar (para add_import)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "visual_click",
        "description": "Toma una captura de pantalla, usa visión para encontrar las coordenadas del elemento descrito,",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14I: Memory & Vision ──

    {
        "name": "document_rag",
        "description": "document_rag tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_rag_stats",
        "description": "document_rag_stats tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "game_companion",
        "description": "Companero de juegos. Analiza pantalla y ayuda.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "image_analyzer",
        "description": "Analyze an image file or URL using vision AI",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "Image file path or URL"},
                "question": {"type": "STRING", "description": "Question about the image"},
            },
            "required": ["path"],
        }
    },
    {
        "name": "morning_brief",
        "description": "Genera un resumen diario al iniciar el dia: clima, noticias, recordatorios, eventos del calendario, citas programadas. Acciones: brief (resumen completo del dia), weather (clima), news (noticias), tasks (tareas del dia).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "brief, weather, news, tasks"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "screen_vision",
        "description": "AI screen reading and analysis",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "capture, read, analyze"},
                "prompt": {"type": "STRING", "description": "Analysis prompt"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "security_scanner",
        "description": "System security scan: malware, processes, firewall, vulnerabilities",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "scope": {"type": "STRING", "description": "quick, full, custom, process, startup, network"},
            },
            "required": ["scope"],
        }
    },
    {
        "name": "vision_guardian",
        "description": "Continuous vision monitoring: watches screen for changes and alerts",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, stop, status"},
                "interval": {"type": "INTEGER", "description": "Check interval in seconds"},
                "prompt": {"type": "STRING", "description": "What to watch for"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "eris_guardian",
        "description": "Guardian de ERIS: vigila la salud del codigo y del sistema. Escanea todos los archivos .py del proyecto, detecta errores de sintaxis o importacion, intenta repararlos automaticamente (con backup), monitorea CPU/RAM/GPU/disco, reinicia ERIS si se cae y mantiene un diario de reparaciones. Acciones: status (estado general del sistema + guardia), scan (escaneo completo de codigo), repair (reparar errores con backup), start (iniciar monitoreo en background), stop (detener monitoreo), journal (ver diario de reparaciones).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, scan, repair, start, stop, journal"},
                "repair": {"type": "BOOLEAN", "description": "Intentar reparar errores detectados (default true)"},
                "target": {"type": "STRING", "description": "Archivo .py especifico a escanear/reparar"},
                "limit": {"type": "INTEGER", "description": "Max entradas del diario a mostrar (default 10)"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14J: AI Features ──

    {
        "name": "emotional_state",
        "description": "emotional_state tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "image_generation",
        "description": "AI image generation and manipulation",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "generate, list, get, delete, style, upscale, variations, batch, status, gallery, download"},
                "prompt": {"type": "STRING", "description": "Image description"},
                "style": {"type": "STRING", "description": "Style preset"},
                "size": {"type": "STRING", "description": "Image size"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "personality",
        "description": "Motor de personalidad de ERIS.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_map",
        "description": "ERIS obtiene su mapa completo de sí misma.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Knowledge & RAG ──

    {
        "name": "data_connectors",
        "description": "data_connectors tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "knowledge_ingestor",
        "description": "knowledge_ingestor tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── AGI ──

    {
        "name": "agi_agent",
        "description": "Delega una meta a un agente multi-paso que descompone la tarea y la ejecuta. Acciones: plan (crear plan con 'goal'), execute (ejecutar con 'plan_id' y opcional 'max_steps'), status (ver progreso con 'plan_id' o activos), cancel, history.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "plan | execute | status | cancel | history"},
                "goal": {"type": "STRING", "description": "Meta a descomponer (para plan)"},
                "plan_id": {"type": "STRING", "description": "ID del plan (para execute/status/cancel)"},
                "max_steps": {"type": "INTEGER", "description": "Máximo de pasos a ejecutar (opcional)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "agi_memory",
        "description": "Memoria semántica/episódica de ERIS. Acciones: store (guardar 'text'), recall (recuperar con 'query'), consolidate (consolidar working a largo plazo), status (contadores).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "store | recall | consolidate | status"},
                "text": {"type": "STRING", "description": "Información a recordar (para store)"},
                "query": {"type": "STRING", "description": "Búsqueda a recuperar (para recall)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "agi_reasoning",
        "description": "Motor de razonamiento paso a paso. Acciones: reason (con 'question' y opcional 'context'), verify (verificar una afirmación con 'claim'), what_if (razonamiento contra-factual con 'premise' y 'question'), status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "reason | verify | what_if | status"},
                "question": {"type": "STRING", "description": "Pregunta a razonar (para reason/what_if)"},
                "context": {"type": "STRING", "description": "Contexto adicional (opcional, para reason)"},
                "claim": {"type": "STRING", "description": "Afirmación a verificar (para verify)"},
                "premise": {"type": "STRING", "description": "Premisa del escenario (para what_if)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "agi_self_improve",
        "description": "Auto-mejora autónoma de ERIS. Acciones: scan (escanear logs y generar sugerencias), suggestions (listar sugerencias), applied (listar mejoras aplicadas), apply (marcar sugerencia como aplicada con 'title'), learn (guardar una 'lesson'), report (reporte de calidad y tendencia), status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan | suggestions | applied | apply | learn | report | status"},
                "title": {"type": "STRING", "description": "Título de la sugerencia a marcar (para apply)"},
                "lesson": {"type": "STRING", "description": "Lección a aprender (para learn)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "agi_world_model",
        "description": "Modelo del mundo: estado de ERIS y del sistema. Acciones: status (estado actual), snapshot (guardar snapshot en memoria), note (registrar una observación con 'observation').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | snapshot | note"},
                "observation": {"type": "STRING", "description": "Observación a registrar (para note)"},
            },
            "required": ["action"],
        }
    },

    # ── Meta ──

    {
        "name": "ollama_status",
        "description": "Return current routing status for display in UI.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "tts_set_voice",
        "description": "Configura el motor de texto a voz: selecciona voz, ajusta velocidad, cambia backend. Acciones: list_voices (listar voces disponibles), set_voice (seleccionar voz), set_speed (ajustar velocidad), set_backend (cambiar backend TTS).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list_voices, set_voice, set_speed, set_backend"},
                "voice": {"type": "STRING", "description": "Nombre de la voz (para set_voice)"},
                "speed": {"type": "NUMBER", "description": "Velocidad: 0.5 a 2.0 (default 1.0)"},
                "backend": {"type": "STRING", "description": "Backend: edge, pyttsx, gtts, elevenlabs"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_recognition",
        "description": "Tool declaration for ERIS voice recognition management.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Skills ──

    {
        "name": "skill_manage",
        "description": "Manage ERIS skills: list, view, create, edit, patch, delete, sync",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, view, create, edit, patch, delete, sync"},
                "skill": {"type": "STRING", "description": "Skill name"},
            },
            "required": ["action"],
        }
    },

    # ── Browser & Files ──

    {
        "name": "browser_control",
        "description": "Browser automation: navigate, click, search, read pages",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "go_to, search, new_tab, close_tab, scroll, read_page, click_element, go_back, play_pause, scan_results"},
                "url": {"type": "STRING", "description": "URL to navigate"},
                "query": {"type": "STRING", "description": "Search query"},
                "direction": {"type": "STRING", "description": "up, down"},
                "description": {"type": "STRING", "description": "Element description to click"},
                "index": {"type": "INTEGER", "description": "Result index"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_controller",
        "description": "File CRUD, find, organize, disk usage",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create_folder, create_file, read, write, append, delete, move, copy, rename, list, search, info, compress, extract"},
                "path": {"type": "STRING", "description": "Full path to file or folder. Can be anywhere on the PC. Examples: 'C:\\Users\\danie\\Desktop\\mi_doc.docx', 'D:\\Data'"},
                "content": {"type": "STRING", "description": "Content for write/append"},
                "destination": {"type": "STRING", "description": "Destination path"},
                "pattern": {"type": "STRING", "description": "Search pattern"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "flight_finder",
        "description": "flight_finder tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "game_updater",
        "description": "game_updater tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "program_manager",
        "description": "Gestiona programas: instalar, desinstalar, ejecutar, listar, buscar, descargar. SIEMPRE resuelve el ID exacto de winget con search antes de instalar (ej. MySQL -> Oracle.MySQL).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "install, uninstall, run, list, search, download, verify"},
                "name": {"type": "STRING", "description": "Nombre o ID del programa"},
                "path": {"type": "STRING", "description": "Ruta de instalador local o carpeta destino para download"},
                "silent": {"type": "BOOLEAN", "description": "Instalación silenciosa (default true)"},
                "confirm": {"type": "BOOLEAN", "description": "Confirmación del usuario (obligatorio para install/uninstall)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "tiktok_analyzer",
        "description": "Analyze TikTok profiles, videos, and trends",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "profile, video, trending, search"},
                "username": {"type": "STRING", "description": "TikTok username"},
                "url": {"type": "STRING", "description": "Video URL to analyze"},
                "query": {"type": "STRING", "description": "Search query"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "windows_settings",
        "description": "Deep Windows settings: display, audio, network, power",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "display, audio, network, power, bluetooth, defaults, startup, features, environment"},
                "setting": {"type": "STRING", "description": "Specific setting name"},
                "value": {"type": "STRING", "description": "Value to set"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "youtube_video",
        "description": "Play/search YouTube videos",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play, search, playlist, get_info"},
                "query": {"type": "STRING", "description": "Search term or URL"},
                "video_id": {"type": "STRING", "description": "YouTube video ID"},
                "max_results": {"type": "INTEGER", "description": "Max results"},
            },
            "required": ["action"],
        }
    },

    # ── MCP ──

    {
        "name": "mcp_tool",
        "description": "Interfaz al Model Context Protocol (MCP). Permite a ERIS conectar",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Autonomous Learning ──

    {
        "name": "autonomous_learner",
        "description": "Main entry point for autonomous learning.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Training ──

    {
        "name": "curiosity_engine",
        "description": "curiosity_engine tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "task_planner",
        "description": "task_planner tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "training_pipeline",
        "description": "Tool interface for ERIS to query training status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Updater ──

    {
        "name": "eris_update",
        "description": "Verifica si hay una nueva version en GitHub Releases.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14M: New 16 Features (Jul 2026) ──

    {
        "name": "api_server",
        "description": "API Server para ERIS.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "browser_extension",
        "description": "Conexión con navegador.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "calendar_manager",
        "description": "Gestiona calendario y eventos: crear, ver, modificar eventos. Soporta Google Calendar. Acciones: list (ver eventos), create (crear evento), delete (eliminar), update (modificar), find (buscar evento).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, create, delete, update, find"},
                "title": {"type": "STRING", "description": "Titulo del evento"},
                "date": {"type": "STRING", "description": "Fecha. Ej: '2026-07-30' o 'manana'"},
                "time": {"type": "STRING", "description": "Hora. Ej: '15:00'"},
                "duration": {"type": "INTEGER", "description": "Duracion en minutos (default 60)"},
                "description": {"type": "STRING", "description": "Descripcion del evento"},
                "event_id": {"type": "STRING", "description": "ID del evento (para delete/update)"},
                "days": {"type": "INTEGER", "description": "Cantidad de dias a listar (default 7)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "clipboard_manager",
        "description": "Historial del portapapeles: guarda, busca y reusa texto copiado. Acciones: history (ver historial), search (buscar en historial), copy (copiar texto al portapapeles), paste (pegar desde historial), clear (limpiar historial).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "history, search, copy, paste, clear"},
                "text": {"type": "STRING", "description": "Texto a copiar (para copy) o buscar (para search)"},
                "index": {"type": "INTEGER", "description": "Indice en el historial (para paste)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "data_encryption",
        "description": "Cifrado de datos.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "email_manager",
        "description": "Gestiona correos electronicos via IMAP/SMTP: leer, enviar, organizar. Acciones: list_inbox (listar correos), read (leer correo), send (enviar), search (buscar), delete (eliminar), mark_as (marcar como leido/no leido).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list_inbox, read, send, search, delete, mark_as"},
                "to": {"type": "STRING", "description": "Destinatario (para send)"},
                "subject": {"type": "STRING", "description": "Asunto del correo"},
                "body": {"type": "STRING", "description": "Cuerpo del correo"},
                "email_id": {"type": "STRING", "description": "ID del correo (para read/delete/mark_as)"},
                "max_results": {"type": "INTEGER", "description": "Max correos a listar (default 10)"},
                "folder": {"type": "STRING", "description": "Carpeta: INBOX, SENT, SPAM (default INBOX)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "federated_learning",
        "description": "Aprendizaje federado local.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_organizer",
        "description": "Auto-classify and organize files in a directory",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "directory": {"type": "STRING", "description": "Directory to organize"},
                "mode": {"type": "STRING", "description": "auto, by_type, by_date, by_size"},
                "preview": {"type": "BOOLEAN", "description": "Preview changes without applying"},
            },
            "required": ["directory"],
        }
    },
    {
        "name": "flow_recorder",
        "description": "Grabador de flujos/macros.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "memory_consolidation",
        "description": "Consolida y limpia todas las memorias de ERIS.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "multi_user",
        "description": "Gestión de usuarios/perfiles.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "screenshot_history",
        "description": "Historial de capturas de pantalla: captura, busca por texto, etiqueta, compara. Acciones: capture (tomar captura), search (buscar en historial), list (listar capturas), tag (etiquetar captura), compare (comparar dos capturas).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "capture, search, list, tag, compare"},
                "query": {"type": "STRING", "description": "Texto a buscar en las capturas (para search)"},
                "tags": {"type": "STRING", "description": "Etiquetas separadas por coma (para tag)"},
                "screenshot_id": {"type": "STRING", "description": "ID de la captura (para tag/compare)"},
                "screenshot_id2": {"type": "STRING", "description": "ID de la segunda captura (para compare)"},
                "region": {"type": "STRING", "description": "Region: screen, window, o 'x1,y1,x2,y2' (para capture)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "skill_marketplace",
        "description": "Marketplace de skills.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "smart_notifications",
        "description": "Notificaciones inteligentes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "usage_analytics",
        "description": "Estadísticas de uso.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_cloning_new",
        "description": "Clonación de voz.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14N: Batch 13 New Features (Jul 2026) ──

    {
        "name": "auto_backup",
        "description": "auto_backup tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "ci_cd",
        "description": "ci_cd tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "code_analyzer",
        "description": "Static analysis: ruff, radon, mypy, bandit, pylint",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "ruff, radon, mypy, bandit, pylint, pip_audit, full"},
                "path": {"type": "STRING", "description": "Target file or folder"},
            },
            "required": ["action", "path"],
        }
    },
    {
        "name": "dashboard_web",
        "description": "dashboard_web tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "data_viz",
        "description": "data_viz tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "docker_deploy",
        "description": "docker_deploy tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "i18n",
        "description": "i18n tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "i18n_ui",
        "description": "i18n_ui tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "plugin_marketplace",
        "description": "plugin_marketplace tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "proactive_ia",
        "description": "proactive_ia tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_cloning_real",
        "description": "voice_cloning_real tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_enhanced",
        "description": "voice_enhanced tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "web_scraper",
        "description": "Scrape and extract content from web pages",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scrape, extract_links, extract_images, extract_text, batch, smart"},
                "url": {"type": "STRING", "description": "URL to scrape"},
                "selector": {"type": "STRING", "description": "CSS selector"},
            },
            "required": ["action"],
        }
    },

    # ── Batch 3: 11 new features ──

    {
        "name": "config_export",
        "description": "Export/Import configuración.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "desktop_notifications",
        "description": "Notificaciones nativas de Windows con prioridades. Acciones: send (enviar notificacion), list_history (ver historial), clear (limpiar notificaciones), config (configurar preferencias).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send, list_history, clear, config"},
                "title": {"type": "STRING", "description": "Titulo de la notificacion"},
                "message": {"type": "STRING", "description": "Cuerpo de la notificacion"},
                "priority": {"type": "STRING", "description": "Prioridad: low, normal, high, critical (default normal)"},
                "duration": {"type": "INTEGER", "description": "Duracion en segundos (default 5)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "knowledge_graph",
        "description": "Grafo de conocimiento.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "plugin_loader",
        "description": "Carga y gestión de plugins.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "sandbox_execution",
        "description": "Ejecución segura de código.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "smart_cache",
        "description": "Cache inteligente.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "theme_manager",
        "description": "Gestión de temas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Batch 4: Complete Training — All Missing Tools ──

    {
        "name": "active_firewall",
        "description": "active_firewall tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "alarm_manager",
        "description": "Gestiona alarmas y temporizadores con sonido. Acciones: set_alarm (fijar alarma), set_timer (temporizador), list (ver alarmas activas), cancel (cancelar alarma), snooze (posponer).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "set_alarm, set_timer, list, cancel, snooze"},
                "time": {"type": "STRING", "description": "Hora para alarma. Ej: '14:30' o 'en 5 minutos'"},
                "label": {"type": "STRING", "description": "Etiqueta/descripcion de la alarma"},
                "alarm_id": {"type": "STRING", "description": "ID de la alarma (para cancel/snooze)"},
                "seconds": {"type": "INTEGER", "description": "Segundos para temporizador (para set_timer)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "app_installer",
        "description": "Install/uninstall apps via winget",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "install, uninstall, search, list"},
                "app": {"type": "STRING", "description": "App name"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "arca_invoice",
        "description": "arca_invoice tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "ask_user",
        "description": "Hace una pregunta estructurada al usuario con opciones para obtener su decision o preferencia",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question": {"type": "STRING", "description": "Pregunta clara al usuario"},
                "options": {"type": "STRING", "description": "Lista de opciones separadas por coma"},
                "allow_custom": {"type": "BOOLEAN", "description": "Permitir respuesta personalizada"},
                "default": {"type": "STRING", "description": "Valor por defecto"},
            },
            "required": ["question"],
        }
    },
    {
        "name": "audio_transcriber",
        "description": "Transcribe audio a texto usando faster-whisper. Acciones: transcribe (transcribir archivo de audio), transcribe_mic (grabar y transcribir desde microfono), list_models (ver modelos disponibles).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "transcribe, transcribe_mic, list_models"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo de audio"},
                "language": {"type": "STRING", "description": "Idioma. Ej: 'es', 'en' (default auto-detect)"},
                "model_size": {"type": "STRING", "description": "Tamano del modelo: tiny, base, small, medium, large (default base)"},
                "duration": {"type": "INTEGER", "description": "Duracion de grabacion en segundos (para transcribe_mic)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "auto_agent",
        "description": "auto_agent tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "backup_system",
        "description": "Sistema de backup: crea respaldos con metadatos y programacion. Acciones: create_backup (crear backup), list_backups (listar backups), restore (restaurar backup), schedule (programar backup automatico), delete_backup (eliminar backup).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create_backup, list_backups, restore, schedule, delete_backup"},
                "name": {"type": "STRING", "description": "Nombre del backup"},
                "source": {"type": "STRING", "description": "Carpeta o archivo a respaldar"},
                "destination": {"type": "STRING", "description": "Destino del backup"},
                "backup_id": {"type": "STRING", "description": "ID del backup (para restore/delete)"},
                "interval": {"type": "STRING", "description": "Intervalo: 'daily', 'weekly', 'hourly' (para schedule)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "browser_history",
        "description": "browser_history tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "calculator",
        "description": "Math, unit conversion, date calculations",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "expression": {"type": "STRING", "description": "Math expression or conversion"},
            },
            "required": ["expression"],
        }
    },
    {
        "name": "code_generator",
        "description": "Generate code files in any programming language — always saves to Desktop/ERIS_Scripts by default.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "generate (code from description), save (save existing code), run, list, template. Default: generate."},
                "language": {"type": "STRING", "description": "python, powershell, batch (default: python)"},
                "description": {"type": "STRING", "description": "What the code should do (for generate)"},
                "code": {"type": "STRING", "description": "Raw code content (for save action)"},
                "file_path": {"type": "STRING", "description": "Where to save. Can be full path like 'C:\\Users\\danie\\Desktop\\script.py' or a directory like 'C:\\Users\\danie\\Desktop' (auto-generates filename). Defaults to Desktop\\ERIS_Scripts."},
            },
            "required": ["action", "language", "description"],
        }
    },
    {
        "name": "code_copilot",
        "description": "Asistente de código IA con edición QUIRÚRGICA: genera código en TODOS los lenguajes (java, html, css, javascript, python, c#, c++, react, angular, vue, bootstrap, mysql, php, typescript, go, rust...), corrige SOLO la línea con error sin tocar el resto, agrega código en el punto correcto de un archivo existente, localiza problemas, organiza archivos en carpetas, renombra y analiza proyectos. Usala SIEMPRE para tareas de programación.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "new (generar código/proyecto), fix (corregir solo las líneas con error), add (agregar código a archivo existente), locate (encontrar problemas), analyze (analizar), structure (organizar en carpetas), organize (mover por tipo), rename (renombrar archivo), languages (listar lenguajes), knowledge (convenciones de un lenguaje)"},
                "language": {"type": "STRING", "description": "python, javascript, typescript, html, css, java, csharp, cpp, react, angular, vue, php, mysql, go, rust, bash... (default python)"},
                "description": {"type": "STRING", "description": "Descripción de lo que querés generar, corregir o agregar"},
                "error": {"type": "STRING", "description": "Mensaje de error o problema a corregir (action=fix)"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo a corregir/agregar/analizar"},
                "path": {"type": "STRING", "description": "Ruta de carpeta/proyecto para structure, organize, locate, analyze"},
                "output_dir": {"type": "STRING", "description": "Carpeta donde guardar el código generado (action=new)"},
                "filename": {"type": "STRING", "description": "Nombre del archivo a generar (action=new)"},
                "new_name": {"type": "STRING", "description": "Nuevo nombre de archivo (action=rename)"},
                "update_refs": {"type": "STRING", "description": "rename: 'true' para actualizar referencias del nombre viejo en el proyecto"},
                "apply": {"type": "STRING", "description": "structure/organize: 'true' para aplicar los cambios; si no, solo propuesta"},
                "line": {"type": "NUMBER", "description": "Número de línea del error (opcional, action=fix)"},
                "issue": {"type": "STRING", "description": "Qué problema buscar (action=locate)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "context_engine",
        "description": "context_engine tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "context_menu",
        "description": "Instala entradas del menu contextual de Windows.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "credential_recovery",
        "description": "Recuperación EXHAUSTIVA de credenciales en el sistema local.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "scan": {"type": "STRING", "description": "Escaneo rápido"},
                "browsers": {"type": "STRING", "description": "Contraseñas de Chrome, Edge, Brave, Firefox"},
                "wifi": {"type": "STRING", "description": "Redes WiFi con contraseñas"},
                "wifi_detail": {"type": "STRING", "description": "Detalle de una red. Parametros: ssid"},
                "windows_cred": {"type": "STRING", "description": "Credential Manager + Vault + Shadow Copies"},
                "git": {"type": "STRING", "description": "Tokens y credenciales de Git"},
                "cookies": {"type": "STRING", "description": "Cookies de sesiones importantes"},
                "secrets": {"type": "STRING", "description": "Archivos con secretos (.env, .ssh, .aws, etc.)"},
                "all": {"type": "STRING", "description": "Escaneo TOTAL de todo"},
                "attempt": {"type": "STRING", "description": "Intentar descifrar algo específico. Parametros: target (url/ssid/email)"},
            },
            "required": ["scan", "browsers", "wifi", "wifi_detail", "windows_cred", "git", "cookies", "secrets", "all", "attempt"],
        }
    },
    {
        "name": "cybersecurity",
        "description": "Ensenanza y herramientas de ciberseguridad: conceptos, tecnicas, hacking etico. Acciones: teach (ensenar concepto), scan (escanear puertos), analyze (analizar URL/archivo), vuln (buscar vulnerabilidades conocidas), tips (consejos de seguridad).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "teach, scan, analyze, vuln, tips"},
                "topic": {"type": "STRING", "description": "Tema a ensenar (para teach). Ej: 'phishing', 'firewall', 'encriptacion'"},
                "target": {"type": "STRING", "description": "Host o URL a analizar/escanear"},
                "port_range": {"type": "STRING", "description": "Rango de puertos. Ej: '1-1000' (para scan)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "darkweb_monitor",
        "description": "darkweb_monitor tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "data_analyst",
        "description": "Analiza archivos CSV o Excel: muestra columnas, estadisticas basicas, filtra datos, genera reportes. Acciones: load (cargar archivo), info (informacion del dataset), stats (estadisticas), filter (filtrar datos), chart (graficar columna).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "load, info, stats, filter, chart"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo CSV o Excel"},
                "column": {"type": "STRING", "description": "Nombre de columna para filter/chart"},
                "value": {"type": "STRING", "description": "Valor para filtrar"},
                "chart_type": {"type": "STRING", "description": "Tipo de grafico: bar, line, pie, histogram (default bar)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "disk_wiper",
        "description": "disk_wiper tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_generator",
        "description": "Create, inspect, and resume Word documents. Use 'create' to make a new doc, 'check_content' to read an existing doc, 'working_doc' to see the current document in progress.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create (new doc), check_content (read doc), working_doc (current doc)"},
                "title": {"type": "STRING", "description": "Document title (for create)"},
                "content": {"type": "STRING", "description": "Document content in markdown (for create)"},
                "output_path": {"type": "STRING", "description": "Path or directory to save. Examples: 'C:\\Users\\danie\\Desktop\\doc.docx' or 'C:\\Users\\danie\\Desktop'. Defaults to Desktop\\ERIS_Documentos."},
                "path": {"type": "STRING", "description": "File path to inspect (for check_content)"},
                "filename": {"type": "STRING", "description": "Output filename (optional)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_manager",
        "description": "Manages documents (PDF, Word, Excel, Text).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "driver_manager",
        "description": "Gestiona drivers de Windows: lista, respalda, restaura. Acciones: list (listar drivers), backup (respaldar drivers), restore (restaurar drivers), info (informacion detallada de un driver).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, backup, restore, info"},
                "driver_name": {"type": "STRING", "description": "Nombre del driver (para info)"},
                "backup_path": {"type": "STRING", "description": "Carpeta donde guardar el respaldo (para backup)"},
                "restore_path": {"type": "STRING", "description": "Ruta del respaldo a restaurar (para restore)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "emo_core",
        "description": "Núcleo emocional de Eris – monitorea el sistema y ajusta su estado.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "status": {"type": "STRING", "description": "Ver el estado emocional actual y métricas del sistema"},
                "history": {"type": "STRING", "description": "Ver historial de cambios de estado"},
                "reset": {"type": "STRING", "description": "Reiniciar contadores de estado"},
            },
            "required": ["status", "history", "reset"],
        }
    },
    {
        "name": "emotional_growth",
        "description": "Sistema de desarrollo emocional de ERIS. Permite consultar",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "eris_style",
        "description": "Perfil de estilo configurable de ERIS (config/eris_style.json): identidad, trato con el usuario, frases (saludos, despedidas, humor) y reglas de auto-suficiencia/proactividad. Úsala para ver tu estilo, cambiar cómo tratas al usuario, agregar frases o ajustar cuántos intentos haces antes de reportar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, set_trato, set_descripcion, set_firma, add_frase, set_intentos, set_flag"},
                "trato": {"type": "STRING", "description": "Cómo tratar al usuario (action=set_trato, ej: 'tú')"},
                "text": {"type": "STRING", "description": "Texto/frase (add_frase, set_descripcion, set_firma)"},
                "lista": {"type": "STRING", "description": "Lista para add_frase: frases, despedidas, reacciones"},
                "value": {"type": "STRING", "description": "Valor (set_intentos número, set_flag true/false)"},
                "key": {"type": "STRING", "description": "Flag para set_flag (ej: anticipar_fallos, corregir_sin_preguntar)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "daily_digest",
        "description": "Memoria de largo plazo de ERIS: digest diario que consolida qué se hizo, qué se aprendió y qué falló cada día. Cuando el usuario pregunte '¿qué hiciste hoy?', 'resumí el día' o quiera recordar el trabajo reciente, usá esta herramienta.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "today (ver digest de hoy), recent (últimos digests), generate (regenerar el de hoy)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "camera_bus",
        "description": "Cámaras del equipo: detecta cámaras conectadas, captura instantáneas y analiza lo que ve con visión. Acciones: info (listar cámaras), snapshot/capture (capturar imagen, opcional analyze=true con question).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "info, snapshot, capture"},
                "index": {"type": "INTEGER", "description": "Índice de cámara (default 0)"},
                "question": {"type": "STRING", "description": "Pregunta sobre la imagen (con analyze=true)"},
                "analyze": {"type": "BOOLEAN", "description": "Analizar la captura con visión"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_tool",
        "description": "Trabaja con documentos y archivos: info (metadatos), read (extraer texto), summary, write (crear), edit/replace, append, convert (to_txt). Usala para leer y modificar archivos de ofimática, texto y código.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "info, read, summary, write, edit, replace, append, to_txt, formats"},
                "path": {"type": "STRING", "description": "Ruta del archivo"},
                "max_chars": {"type": "INTEGER", "description": "Límite de caracteres a leer (default 150000)"},
                "content": {"type": "STRING", "description": "Contenido para write/append"},
                "replace": {"type": "STRING", "description": "Texto de reemplazo para edit/replace"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "huggingface",
        "description": "Explora Hugging Face: busca modelos y datasets públicos por query. Acciones: search_models/models, search_datasets/datasets, top_datasets.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search_models, models, search_datasets, datasets, top_datasets"},
                "query": {"type": "STRING", "description": "Término de búsqueda"},
                "limit": {"type": "INTEGER", "description": "Cantidad de resultados (1-20, default 5)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "reverse_engineering",
        "description": "Análisis local y defensivo de archivos/ejecutables: hashes (MD5/SHA1/SHA256), tipo, cadenas legibles y filtros. Uso defensivo (verificar archivos sospechosos). Acciones: file_info/info/hashes, strings/cadenas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "file_info, info, hashes, strings"},
                "path": {"type": "STRING", "description": "Ruta del archivo o ejecutable"},
                "min_length": {"type": "INTEGER", "description": "Longitud mínima de cadena (default 4)"},
                "pattern": {"type": "STRING", "description": "Filtro regex sobre cadenas"},
                "count": {"type": "INTEGER", "description": "Máximo de cadenas a mostrar (default 60)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_evolution",
        "description": "Estado evolutivo de ERIS: reflexiones, lecciones, metas e hitos. Acciones: status (ver evolución), reflect (reflexionar), lesson (guardar lección), goal (proponer meta).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, reflect, lesson, goal"},
                "text": {"type": "STRING", "description": "Texto de la lección o meta"},
                "focus": {"type": "STRING", "description": "Tema de la reflexión"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "english_teacher",
        "description": "Profesor de ingles: curriculo A1 a C2, lecciones, ejercicios, correccion. Acciones: lesson (dar leccion), exercise (generar ejercicio), correct (corregir texto), translate (traducir al ingles), vocabulary (vocabulario por nivel).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "lesson, exercise, correct, translate, vocabulary"},
                "level": {"type": "STRING", "description": "Nivel: A1, A2, B1, B2, C1, C2 (default B1)"},
                "topic": {"type": "STRING", "description": "Tema de la leccion. Ej: 'present perfect', 'business vocabulary'"},
                "text": {"type": "STRING", "description": "Texto a corregir o traducir (para correct/translate)"},
                "count": {"type": "INTEGER", "description": "Cantidad de ejercicios/palabras (default 5)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_encryptor",
        "description": "file_encryptor tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_manager",
        "description": "Operaciones con archivos: mover, copiar, renombrar, borrar, listar, buscar, crear directorio, abrir archivo/carpeta. Acciones: move, copy, rename, delete, list, search, info, create_dir, open, open_folder.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "move, copy, rename, delete, list, search, info, create_dir, open, open_folder"},
                "path": {"type": "STRING", "description": "Ruta del archivo o carpeta origen"},
                "destination": {"type": "STRING", "description": "Ruta destino (para move/copy)"},
                "pattern": {"type": "STRING", "description": "Patron de busqueda (para search)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_monitor",
        "description": "Monitor file system changes in real-time",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, stop, status"},
                "directory": {"type": "STRING", "description": "Directory to monitor"},
                "events": {"type": "STRING", "description": "Comma-separated: created, modified, deleted, renamed"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "fun_mode",
        "description": "Modo diversion: chistes, datos curiosos, juegos. Acciones: joke (contar un chiste), fact (dato curioso), trivia (pregunta de trivia), quote (frase celebre), riddle (acertijo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "joke, fact, trivia, quote, riddle"},
                "category": {"type": "STRING", "description": "Categoria: general, tech, science, history, dad (para joke)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "game_launcher",
        "description": "Encuentra y lanza juegos instalados en el PC. Escanea todas las unidades en busca de juegos. Acciones: scan (escanear juegos), list (listar juegos encontrados), launch (lanzar juego), search (buscar juego por nombre).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan, list, launch, search"},
                "name": {"type": "STRING", "description": "Nombre del juego (para launch o search)"},
                "platform": {"type": "STRING", "description": "Plataforma: all, steam, epic, xbox, battlenet (default all)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "habit_predictor",
        "description": "Predice que herramientas necesitas segun tu rutina diaria. Acciones: predict (predecir siguiente accion), learn (aprender nuevo habito), stats (estadisticas de prediccion), reset (reiniciar aprendizaje).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "predict, learn, stats, reset"},
                "tool": {"type": "STRING", "description": "Nombre de la herramienta usada (para learn)"},
                "time": {"type": "STRING", "description": "Hora del habito. Ej: '08:00' (para learn)"},
                "context": {"type": "STRING", "description": "Contexto. Ej: 'manana', 'tarde', 'noche' (para learn)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "keylogger_detector",
        "description": "keylogger_detector tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "memory_rag",
        "description": "memory_rag tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "music_player",
        "description": "Reproduce archivos de audio y video locales (MP3, WAV, MP4, AVI, etc). Busca en carpetas de música o abre cualquier archivo por ruta.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play (buscar y reproducir), play_file/abrir (por ruta exacta), pause, stop, next, previous, volume, list, shuffle"},
                "query": {"type": "STRING", "description": "Nombre o artista a buscar"},
                "path": {"type": "STRING", "description": "Ruta exacta del archivo a reproducir (cualquier formato, cualquier ubicación)"},
                "volume": {"type": "STRING", "description": "Volumen 0-100"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "network_monitor",
        "description": "Monitorea la red: conexiones activas, ancho de banda, estado de la red. Acciones: status (estado de red), connections (conexiones activas), bandwidth (ancho de banda), ping (ping a servidor), ports (puertos en uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, connections, bandwidth, ping, ports"},
                "host": {"type": "STRING", "description": "Host para ping. Ej: 'google.com'"},
                "interface": {"type": "STRING", "description": "Interfaz de red (para bandwidth)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "notification_center",
        "description": "notification_center tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "ocr_reader",
        "description": "Extrae texto de imagenes usando OCR (pytesseract). Acciones: read (extraer texto de imagen), read_from_screen (capturar pantalla y leer texto), languages (ver idiomas disponibles).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read, read_from_screen, languages"},
                "image_path": {"type": "STRING", "description": "Ruta de la imagen a procesar"},
                "language": {"type": "STRING", "description": "Idioma para OCR. Ej: 'spa', 'eng', 'spa+eng'"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "openrouter_agent",
        "description": "Delega una tarea de texto compleja.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "osint_agent",
        "description": "Agente de OSINT (Open Source Intelligence) para Eris.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "email": {"type": "STRING", "description": "Buscar info de un email (breaches, MX, validación)"},
                "username": {"type": "STRING", "description": "Verificar username en múltiples plataformas"},
                "domain": {"type": "STRING", "description": "WHOIS y DNS de un dominio"},
                "ip": {"type": "STRING", "description": "Geolocalización y info de una IP"},
                "web": {"type": "STRING", "description": "Búsqueda web general"},
                "breach": {"type": "STRING", "description": "Verificar si un email está en filtraciones conocidas"},
                "full_report": {"type": "STRING", "description": "Reporte completo de un objetivo. Parametros: target (email/username/domain)"},
                "history": {"type": "STRING", "description": "Ver historial de búsquedas OSINT"},
            },
            "required": ["email", "username", "domain", "ip", "web", "breach", "full_report", "history"],
        }
    },
    {
        "name": "pc_control",
        "description": "Controla el PC en acciones SEGURAS que no tocan la energía: volume_up, volume_down, volume_set, mute, unmute, monitor_on, monitor_off, wifi_on, wifi_off, wifi_status, bluetooth_on, bluetooth_off, bluetooth_status, screenshot, lock, status. IMPORTANTE: apagar, suspender, reiniciar, hibernar y cerrar sesion estan DESHABILITADOS por seguridad y devuelven error.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "volume_up, volume_down, volume_set, mute, unmute, monitor_on, monitor_off, wifi_on, wifi_off, wifi_status, bluetooth_on, bluetooth_off, bluetooth_status, screenshot, lock, status"},
                "value": {"type": "STRING", "description": "Valor opcional (ej: nivel de volumen)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "pdf_editor",
        "description": "Edita PDFs: leer, unir, dividir, llenar formularios. Acciones: read (leer PDF), merge (unir PDFs), split (dividir), fill_form (llenar formulario), extract_images (extraer imagenes).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read, merge, split, fill_form, extract_images"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo PDF"},
                "files": {"type": "STRING", "description": "Lista de rutas separadas por coma (para merge)"},
                "output_path": {"type": "STRING", "description": "Ruta de salida"},
                "pages": {"type": "STRING", "description": "Paginas: '1,2,3' o '1-5'"},
                "form_data": {"type": "STRING", "description": "Datos del formulario en JSON"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "pdf_manager",
        "description": "Operaciones con PDFs: leer, unir, dividir, convertir a texto. Acciones: read (leer y extraer texto), merge (unir varios PDFs), split (dividir PDF), convert_to_text (extraer texto plano).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read, merge, split, convert_to_text"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo PDF"},
                "files": {"type": "STRING", "description": "Lista de rutas separadas por coma (para merge)"},
                "output_path": {"type": "STRING", "description": "Ruta de salida del archivo resultante"},
                "pages": {"type": "STRING", "description": "Paginas a extraer. Ej: '1,2,3' o '1-5' (para split)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "presentation_generator",
        "description": "Generate PowerPoint presentations",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Presentation title"},
                "slides": {"type": "STRING", "description": "JSON array of slide objects with title and content"},
                "output_path": {"type": "STRING", "description": "Path or directory to save. Can be full path like 'C:\\Users\\danie\\Desktop\\pres.pptx' or a directory. Defaults to Desktop\\ERIS_Presentaciones."},
                "filename": {"type": "STRING", "description": "Output filename"},
            },
            "required": ["title", "slides"],
        }
    },
    {
        "name": "process_manager",
        "description": "Lista procesos en ejecucion, busca por nombre, mata procesos por PID o nombre. Acciones: list (top procesos), search (buscar por nombre), kill (matar por PID o nombre).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, search, kill"},
                "name": {"type": "STRING", "description": "Nombre del proceso (para search o kill)"},
                "pid": {"type": "INTEGER", "description": "PID del proceso (para kill)"},
                "limit": {"type": "INTEGER", "description": "Max resultados (default 20)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "quick_actions",
        "description": "Wrapper para execute.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "ransomware_shield",
        "description": "ransomware_shield tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "real_time_tts",
        "description": "real_time_tts tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "reminders",
        "description": "reminders tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "research",
        "description": "Autonomous research on any topic",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {"type": "STRING", "description": "Research topic"},
                "depth": {"type": "STRING", "description": "shallow, medium, deep"},
            },
            "required": ["topic"],
        }
    },
    {
        "name": "save_everywhere",
        "description": "Guarda informacion en TODOS los sistemas simultaneamente:",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "Base": {"type": "STRING", "description": "de datos SQLite (memory + knowledge)"},
                "Obsidian": {"type": "STRING", "description": "vault (nota interconectada)"},
            },
            "required": ["Base", "Obsidian"],
        }
    },
    {
        "name": "screen_recorder",
        "description": "Graba la pantalla del PC con o sin audio. Acciones: start_record (iniciar grabacion), stop_record (detener y guardar), list_recordings (listar grabaciones), play (reproducir grabacion).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start_record, stop_record, list_recordings, play"},
                "duration": {"type": "INTEGER", "description": "Duracion en segundos (default 30, para start_record)"},
                "record_audio": {"type": "BOOLEAN", "description": "Grabar audio junto al video (default true)"},
                "output_path": {"type": "STRING", "description": "Ruta de salida del video"},
                "recording_name": {"type": "STRING", "description": "Nombre de la grabacion (para play)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "screen_see",
        "description": "Mira la pantalla y describe que hay en ella usando vision AI.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "search_background",
        "description": "Busca en internet SIN abrir navegador, sin molestar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "security_shield",
        "description": "Escudo de seguridad defensivo de Eris.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "scan": {"type": "STRING", "description": "Escaneo completo de seguridad (procesos, puertos, firewall, defender, startups)"},
                "threat": {"type": "STRING", "description": "Buscar amenazas activas (procesos sospechosos, conexiones)"},
                "ports": {"type": "STRING", "description": "Puertos abiertos y análisis de riesgo"},
                "firewall": {"type": "STRING", "description": "Estado del firewall"},
                "defender": {"type": "STRING", "description": "Estado de Windows Defender"},
                "startups": {"type": "STRING", "description": "Programas de inicio sospechosos"},
                "score": {"type": "STRING", "description": "Puntuación de seguridad general (0-100)"},
                "alerts": {"type": "STRING", "description": "Ver historial de alertas de seguridad"},
                "protect": {"type": "STRING", "description": "Plan de protección personalizado"},
                "password_check": {"type": "STRING", "description": "Analizar fortaleza de contraseñas del sistema"},
            },
            "required": ["scan", "threat", "ports", "firewall", "defender", "startups", "score", "alerts", "protect", "password_check"],
        }
    },
    {
        "name": "self_heal",
        "description": "Auto-detect and fix code issues",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan_all, scan_file, health_report, auto_fix"},
                "file": {"type": "STRING", "description": "Target file (for scan_file)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_healing_loop",
        "description": "Self-healing orchestrator",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "detect, fix_file, test, validate, scan_all, status, rollback, restart"},
                "file": {"type": "STRING", "description": "Target file"},
                "code": {"type": "STRING", "description": "Candidate fix code"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_protection",
        "description": "Sistema de autoprotección de Eris.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "status": {"type": "STRING", "description": "Estado general de protección"},
                "scan": {"type": "STRING", "description": "Verificar integridad de archivos críticos"},
                "backup": {"type": "STRING", "description": "Crear backup de todos los archivos críticos"},
                "restore": {"type": "STRING", "description": "Restaurar un archivo desde backup. Parametros: file"},
                "hash": {"type": "STRING", "description": "Ver hash de un archivo específico. Parametros: file"},
                "process": {"type": "STRING", "description": "Info del proceso actual de Eris"},
                "threats": {"type": "STRING", "description": "Buscar código malicioso inyectado"},
                "protect": {"type": "STRING", "description": "Activar protección (guardar hashes de referencia)"},
                "heal": {"type": "STRING", "description": "Reparar archivos dañados desde backup"},
                "log": {"type": "STRING", "description": "Ver historial de eventos de protección"},
            },
            "required": ["status", "scan", "backup", "restore", "hash", "process", "threats", "protect", "heal", "log"],
        }
    },
    {
        "name": "smart_browser",
        "description": "Navegador inteligente con busqueda, historial, descarga de archivos. Acciones: search (buscar en internet), open (abrir URL), history (ver historial), download (descargar archivo), bookmarks (ver marcadores), close (cerrar pestana).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search, open, history, download, bookmarks, close"},
                "query": {"type": "STRING", "description": "Termino de busqueda"},
                "url": {"type": "STRING", "description": "URL a abrir o descargar"},
                "download_path": {"type": "STRING", "description": "Carpeta donde guardar descarga"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "smart_file_organizer",
        "description": "Intelligent file organizer that learns your patterns",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "organize, learn, stats, undo"},
                "directory": {"type": "STRING", "description": "Directory to organize"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "speaker_recognition",
        "description": "speaker_recognition tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "spreadsheet_generator",
        "description": "Generate Excel spreadsheets with data",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Sheet title"},
                "headers": {"type": "STRING", "description": "JSON array of column headers"},
                "data": {"type": "STRING", "description": "JSON array of row data arrays"},
                "output_path": {"type": "STRING", "description": "Path or directory to save. Can be full path like 'C:\\Users\\danie\\Desktop\\data.xlsx' or a directory. Defaults to Desktop\\ERIS_Excel."},
                "filename": {"type": "STRING", "description": "Output filename"},
            },
            "required": ["title", "headers", "data"],
        }
    },
    {
        "name": "subagent_task",
        "description": "Lanza un subagente autonomo via OpenRouter para tareas complejas en segundo plano o sincrono",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task": {"type": "STRING", "description": "Descripcion detallada de la tarea a delegar"},
                "mode": {"type": "STRING", "description": "research, analyze, code, write, general"},
                "model": {"type": "STRING", "description": "Modelo AI (default: google/gemini-2.5-flash)"},
                "wait": {"type": "BOOLEAN", "description": "Esperar resultado (true) o lanzar en background (false)"},
                "task_id": {"type": "STRING", "description": "ID de tarea para recuperar resultados de background"},
            },
            "required": ["task"],
        }
    },
    {
        "name": "system_reader",
        "description": "Deep PC state: sensors, network, disks, battery",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, top_processes, disks, network, sensors, deep"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "task_manager",
        "description": "Kill, search, get details of processes",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "kill, search, detail, list"},
                "query": {"type": "STRING", "description": "Process name or PID"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "task_scheduler",
        "description": "task_scheduler tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "template_engine",
        "description": "template_engine tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "terminal_agent",
        "description": "Execute CMD/PowerShell commands",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "cmd, powershell, win_run, elevated, open, shell_execute"},
                "command": {"type": "STRING", "description": "Command to execute"},
                "elevated": {"type": "BOOLEAN", "description": "Run as admin"},
            },
            "required": ["action", "command"],
        }
    },
    {
        "name": "text_summarizer",
        "description": "Resume textos largos de forma extractiva. Devuelve el resumen con las oraciones mas importantes. Acciones: summarize (resumir texto), summarize_file (resumir archivo), keywords (extraer palabras clave).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "summarize, summarize_file, keywords"},
                "text": {"type": "STRING", "description": "Texto a resumir"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo a resumir"},
                "max_sentences": {"type": "INTEGER", "description": "Max oraciones en el resumen (default 5)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "translator",
        "description": "Traduce texto o páginas web completas entre idiomas (default español). Acciones: translate (traducir texto), translate_web (traducir una página web por URL), detect (detectar idioma), languages (listar idiomas), batch (múltiples textos).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "translate, translate_web, detect, languages, batch"},
                "text": {"type": "STRING", "description": "Texto a traducir (action=translate)"},
                "url": {"type": "STRING", "description": "URL de la página web a traducir (action=translate_web)"},
                "target": {"type": "STRING", "description": "Idioma destino. Ej: 'es', 'en', 'fr', 'pt' (default es)"},
                "source": {"type": "STRING", "description": "Idioma origen (opcional, default auto-detect)"},
                "mode": {"type": "STRING", "description": "translate_web: 'text' (default, devuelve traducción) o 'file' (guarda la traducción completa en disco)"},
                "max_chars": {"type": "NUMBER", "description": "Máximo de caracteres a devolver en mode=text (default 6000)"},
                "save": {"type": "STRING", "description": "Ruta donde guardar la traducción completa (opcional)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "usb_monitor",
        "description": "usb_monitor tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "video_analyzer",
        "description": "Analiza videos de YouTube y archivos locales: subtítulos, transcripción, resumen, vision AI",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "info | subtitles | transcribe | summarize | research | full | local | local_audio | history"},
                "url": {"type": "STRING", "description": "URL del video de YouTube (para actions: info, subtitles, transcribe, summarize, research, full)"},
                "file": {"type": "STRING", "description": "Ruta a video local .mp4/.avi/.mov/.mkv (para actions: local, local_audio)"},
                "prompt": {"type": "STRING", "description": "Prompt personalizado para el análisis AI del video local (action=local)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_clone",
        "description": "Clonacion de voz: entrena, sintetiza, analiza y compara voces. Acciones: train (entrenar voz con audio), synthesize (sintetizar texto con voz clonada), list_voices (listar voces clonadas), delete (eliminar voz), compare (comparar voces).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "train, synthesize, list_voices, delete, compare"},
                "voice_name": {"type": "STRING", "description": "Nombre de la voz"},
                "audio_file": {"type": "STRING", "description": "Archivo de audio para entrenar (para train)"},
                "text": {"type": "STRING", "description": "Texto a sintetizar (para synthesize)"},
                "output_file": {"type": "STRING", "description": "Archivo de salida (para synthesize)"},
                "voice1": {"type": "STRING", "description": "Primera voz a comparar (para compare)"},
                "voice2": {"type": "STRING", "description": "Segunda voz a comparar (para compare)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "web_jobs",
        "description": "Sistema de recepción de trabajos vía web.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "start": {"type": "STRING", "description": "Iniciar el servidor web (puerto 5555 por defecto)"},
                "stop": {"type": "STRING", "description": "Detener el servidor"},
                "status": {"type": "STRING", "description": "Ver estado del servidor y cola de trabajos"},
                "next": {"type": "STRING", "description": "Obtener el siguiente trabajo pendiente para ejecutar"},
                "complete": {"type": "STRING", "description": "Marcar un trabajo como completado (requiere job_id)"},
                "fail": {"type": "STRING", "description": "Marcar un trabajo como fallido (requiere job_id)"},
            },
            "required": ["start", "stop", "status", "next", "complete", "fail"],
        }
    },
    {
        "name": "web_navigation",
        "description": "Navega a una URL en el navegador, reproduce videos de YouTube, o busca en Google. Acciones: navigate (ir a URL), youtube (reproducir video), search (buscar en Google), back, forward, refresh, close.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "navigate, youtube, search, back, forward, refresh, close"},
                "url": {"type": "STRING", "description": "URL completa a navegar"},
                "query": {"type": "STRING", "description": "Termino de busqueda (para search o youtube)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "webfetch",
        "description": "Fetch and extract content from a webpage",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {"type": "STRING", "description": "Webpage URL to fetch"},
                "format": {"type": "STRING", "description": "markdown, text, or html"},
            },
            "required": ["url"],
        }
    },
    {
        "name": "whatsapp_web",
        "description": "WhatsApp Web: enviar mensajes, archivos, abrir chats. Acciones: send_message (enviar mensaje), send_file (enviar archivo), open_chat (abrir chat), search (buscar en chats).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send_message, send_file, open_chat, search"},
                "contact": {"type": "STRING", "description": "Nombre o numero del contacto"},
                "text": {"type": "STRING", "description": "Texto del mensaje"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo a enviar"},
            },
            "required": ["action"],
        }
    },

    # ── Batch 4B: Stub Tools ──

    {
        "name": "agent_task",
        "description": "agent_task tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "ask_opencode",
        "description": "ask_opencode tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "conversation_search",
        "description": "Search past conversations by keyword or list recent conversation history. Useful when you need to remember what was discussed earlier.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Keyword to search for in past conversations (empty = list recent)"},
                "limit": {"type": "INTEGER", "description": "Max results to return (default 10, max 50)"},
            },
            "required": ["query"],
        }
    },
    {
        "name": "curiosity_fact",
        "description": "curiosity_fact tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "curiosity_fun",
        "description": "curiosity_fun tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "curiosity_joke",
        "description": "curiosity_joke tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "curiosity_trending",
        "description": "curiosity_trending tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "dashboard",
        "description": "dashboard tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "db_knowledge",
        "description": "db_knowledge tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "db_memory",
        "description": "Store, retrieve, search or list persistent memories. Used to remember or recall user information across sessions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "store (save), get (retrieve by key), search (search key/value), list (all keys), delete (remove key)"},
                "category": {"type": "STRING", "description": "Memory category for store: 'user_info', 'preferences', 'notes', 'projects', 'habits'"},
                "key": {"type": "STRING", "description": "Memory key name for store/get/search/delete"},
                "value": {"type": "STRING", "description": "Value to store (for store action)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "db_tasks",
        "description": "db_tasks tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "episodic_log",
        "description": "Registra o consulta la memoria episodica de ERIS (experiencias/resumenes de sesiones). Acciones: add (event, category, context, importance), recent (limit), search (query).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Accion: 'add' para registrar, 'recent' para ver las ultimas, 'search' para buscar"},
                "event": {"type": "STRING", "description": "Descripcion breve del evento (requerido para action=add)"},
                "category": {"type": "STRING", "description": "Categoria del evento (ej: training, game, conversation, system)"},
                "context": {"type": "STRING", "description": "Contexto o detalles adicionales del evento"},
                "importance": {"type": "NUMBER", "description": "Importancia 0.0-1.0 (default 0.5)"},
                "limit": {"type": "INTEGER", "description": "Cantidad de eventos a listar (default 10)"},
                "query": {"type": "STRING", "description": "Texto a buscar en los eventos (para action=search)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "eris_ui_control",
        "description": "eris_ui_control tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "full_training",
        "description": "full_training tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "learn_from_mistake",
        "description": "learn_from_mistake tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "learn_session",
        "description": "learn_session tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "meeting_transcriber",
        "description": "meeting_transcriber tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "obsidian_note",
        "description": "Obsidian vault: create, read, search, daily notes, links, tags",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "write, read, search, daily, link, backlinks, tags, browse, graph"},
                "title": {"type": "STRING", "description": "Note title"},
                "content": {"type": "STRING", "description": "Note content (for write)"},
                "query": {"type": "STRING", "description": "Search query"},
                "tag": {"type": "STRING", "description": "Tag name"},
                "note_name": {"type": "STRING", "description": "Note to link to"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "play_direct",
        "description": "play_direct tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "plugin_manage",
        "description": "plugin_manage tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "predict_analyze",
        "description": "predict_analyze tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "res_monitor",
        "description": "res_monitor tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "res_protect",
        "description": "res_protect tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "sandbox_run",
        "description": "sandbox_run tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "sandbox_test_tool",
        "description": "sandbox_test_tool tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "save_memory",
        "description": "Save a fact about the user into long-term memory. Use this to remember user preferences, personal info, interests, or anything the user wants you to remember across sessions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "Memory category. Examples: 'user_info', 'preferences', 'notes', 'projects', 'habits'"},
                "key": {"type": "STRING", "description": "Memory key/name. Examples: 'user_name', 'user_game', 'user_hobby'"},
                "value": {"type": "STRING", "description": "The fact to remember. Examples: 'Daniel', 'Ya no juego Aion2'"},
            },
            "required": ["key", "value"],
        }
    },
    {
        "name": "search_info",
        "description": "search_info tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "shutdown_eris",
        "description": "Shut down ERIS assistant",
        "parameters": {
            "type": "OBJECT",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "sleep_mode",
        "description": "sleep_mode tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "sms",
        "description": "sms tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "superpowers_activate",
        "description": "superpowers_activate tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "task_queue",
        "description": "task_queue tool",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Batch 5: Connectivity + Self-Healing ──

    {
        "name": "connectivity",
        "description": "Action handler for connectivity management.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_healing",
        "description": "Action handler for self-healing system with detailed structured reports.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to perform"},
            },
            "required": ["action"],
        }
    },

    # ── Batch 6: Page/Video Summarizer ──

    {
        "name": "page_summarizer",
        "description": "Resume paginas web, videos de YouTube, o cualquier contenido de una URL. Extrae el contenido principal y genera un resumen conciso. Acciones: summarize (resumir URL), youtube (resumir video de YouTube), save (resumir y guardar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "summarize, youtube, save"},
                "url": {"type": "STRING", "description": "URL de la pagina o video a resumir"},
                "language": {"type": "STRING", "description": "Idioma del resumen: 'es', 'en' (default 'es')"},
                "max_length": {"type": "INTEGER", "description": "Maximo de palabras en el resumen (default 300)"},
            },
            "required": ["action", "url"],
        }
    },

    # ── Batch 7: Excel/Office por voz ──

    {
        "name": "office_docs",
        "description": "Excel, Word y PowerPoint por voz. Excel: excel_create (crear XLSX con headers y rows), excel_read (leer celdas), excel_write (escribir valor en una celda o añadir fila). Word: word_create (crear DOCX con title y paragraphs). PowerPoint: pptx_create (crear presentacion con slides).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "excel_create, excel_read, excel_write, word_create, word_read, pptx_create, help"},
                "path": {"type": "STRING", "description": "Ruta del archivo (si es relativa, se guarda en data/documents)"},
                "sheet": {"type": "STRING", "description": "Nombre de la hoja (default 'Hoja1')"},
                "headers": {"type": "STRING", "description": "JSON array de nombres de columnas para excel_create, ej: [\"Mes\",\"Total\"]"},
                "rows": {"type": "STRING", "description": "JSON array de filas (cada fila es un array de valores), ej: [[\"Enero\",100]]"},
                "cell": {"type": "STRING", "description": "Referencia de celda para excel_write, ej: 'B2'"},
                "value": {"type": "STRING", "description": "Valor a escribir en la celda"},
                "row": {"type": "STRING", "description": "JSON array con los valores de la fila a añadir en excel_write, ej: [\"Marzo\",200]"},
                "max_rows": {"type": "INTEGER", "description": "Maximo de filas a mostrar en excel_read (default 20)"},
                "title": {"type": "STRING", "description": "Titulo del documento o presentacion"},
                "paragraphs": {"type": "STRING", "description": "JSON array de parrafos para word_create, ej: [\"Parrafo 1\",\"Parrafo 2\"]"},
                "slides": {"type": "STRING", "description": "JSON array de diapositivas {title, bullets} para pptx_create, ej: [{\"title\":\"Resumen\",\"bullets\":[\"Punto 1\"]}]"},
            },
            "required": ["action", "path"],
        }
    },

    # ── Batch 8: Volumen y pantalla ──

    {
        "name": "system_volume",
        "description": "Control del volumen y audio del sistema Windows. Acciones: get (volumen actual), set (level 0-100), up/down (step), mute, unmute, toggle_mute, devices (listar dispositivos de audio), set_device (device: nombre o indice para cambiar el dispositivo de reproduccion).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "get, set, up, down, mute, unmute, toggle_mute, devices, set_device"},
                "level": {"type": "INTEGER", "description": "Nivel de volumen 0-100 para set"},
                "step": {"type": "INTEGER", "description": "Incremento/decremento para up/down (default 10)"},
                "device": {"type": "STRING", "description": "Nombre o indice del dispositivo de reproduccion para set_device"},
            },
            "required": ["action"],
        }
    },

    {
        "name": "screen_control",
        "description": "Control de la pantalla. Acciones: brightness_get (brillo actual), brightness_set (level 0-100 para fijar brillo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "brightness_get, brightness_set"},
                "level": {"type": "INTEGER", "description": "Nivel de brillo 0-100"},
            },
            "required": ["action"],
        }
    },

]


def load_custom_tools(BASE_DIR):
    """Load custom tools from custom_tools.json and append to TOOL_DECLARATIONS."""
    try:
        _custom_tools_path = BASE_DIR / "actions" / "custom_tools.json"
        if _custom_tools_path.exists():
            with open(_custom_tools_path, "r", encoding="utf-8") as _f:
                _custom = json.load(_f)
            if isinstance(_custom, list):
                for _t in _custom:
                    if _t.get("name") not in [td["name"] for td in TOOL_DECLARATIONS]:
                        TOOL_DECLARATIONS.append(_t)
        _extra_tools_path = BASE_DIR / "config" / "extra_tools.json"
        if _extra_tools_path.exists():
            with open(_extra_tools_path, "r", encoding="utf-8") as _f:
                _extra = json.load(_f)
            if isinstance(_extra, list):
                for _t in _extra:
                    if _t.get("name") not in [td["name"] for td in TOOL_DECLARATIONS]:
                        TOOL_DECLARATIONS.append(_t)
    except Exception:
        pass
