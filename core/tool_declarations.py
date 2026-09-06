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
        "description": "Grabador de flujos/macros de acciones. Acciones: list (listar macros), start (iniciar grabacion), stop (detener y guardar), play (reproducir macro), record_manual (crear macro manual), delete, rename, export.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, start, stop, play, record_manual, delete, rename, export"},
                "name": {"type": "STRING", "description": "Nombre de la macro"},
                "new_name": {"type": "STRING", "description": "Nuevo nombre (para rename)"},
                "speed": {"type": "NUMBER", "description": "Velocidad de reproduccion (default 1.0)"},
                "repeat": {"type": "INTEGER", "description": "Cantidad de repeticiones (default 1)"},
                "delay": {"type": "NUMBER", "description": "Delay entre acciones en segundos (default 0.5)"},
                "actions": {"type": "STRING", "description": "Acciones de la macro (JSON, para record_manual)"},
                "type": {"type": "STRING", "description": "Tipo de accion: wait, click, etc."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "app_discovery",
        "description": "Descubre aplicaciones instaladas en el sistema: buscar por nombre, listar apps instaladas y obtener su ruta. Acciones: status (ver estado), search (buscar app por nombre/query).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, search"},
                "query": {"type": "STRING", "description": "Nombre de la app a buscar"},
                "name": {"type": "STRING", "description": "Alias de query"},
                "app_name": {"type": "STRING", "description": "Alias de query"},
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
        "description": "Control de ventanas y escritorio: listar, minimizar, maximizar, restaurar, cerrar, enfocar, buscar, cascada, mosaico, ajustar opacidad, abrir aplicaciones y ver uso de aplicaciones por periodo. Acciones: list_windows, list_detailed, minimize, maximize, restore, close, focus, search, cascade, tile_horizontal, tile_vertical, minimize_all, restore_all, set_opacity, open_app, close_app, app_usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list_windows, list_detailed, minimize, maximize, restore, close, focus, search, cascade, tile_horizontal, tile_vertical, minimize_all, restore_all, set_opacity, open_app, close_app, app_usage"},
                "name": {"type": "STRING", "description": "Titulo de ventana o nombre de app"},
                "app": {"type": "STRING", "description": "Nombre de app para open_app/close_app"},
                "query": {"type": "STRING", "description": "Texto a buscar en titulos de ventana (search)"},
                "show_hidden": {"type": "BOOLEAN", "description": "Incluir ventanas ocultas (default false)"},
                "opacity": {"type": "INTEGER", "description": "Opacidad 0-255 (set_opacity)"},
                "period": {"type": "STRING", "description": "Periodo para app_usage: today, week, month, all (default all)"},
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
                "width": {"type": "INTEGER", "description": "Ancho en px (para convert/compress de imagenes)"},
                "height": {"type": "INTEGER", "description": "Alto en px (para convert/compress de imagenes)"},
                "scale": {"type": "NUMBER", "description": "Factor de escala (0.5 = mitad de tamano)"},
                "quality": {"type": "INTEGER", "description": "Calidad de compresion 1-100 (default 80)"},
                "timestamp": {"type": "STRING", "description": "Timestamp/fecha para el nombre de salida (YYYYMMDD_HHMMSS)"},
                "column": {"type": "STRING", "description": "Columna a analizar/filtrar"},
                "value": {"type": "STRING", "description": "Valor de referencia para la columna (analisis/filtro)"},
                "condition": {"type": "STRING", "description": "Condicion: contains, equals, gt, lt (default contains)"},
                "ascending": {"type": "BOOLEAN", "description": "Orden ascendente (default true)"},
                "save": {"type": "BOOLEAN", "description": "Guardar el resultado a archivo (default true)"},
                "destination": {"type": "STRING", "description": "Ruta de destino del resultado guardado"},
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
        "description": "Monitoreo del sistema: CPU, RAM, disco, GPU, red y procesos. Acciones: overview (resumen), cpu, ram, disk, gpu, network, processes (lista de procesos), top (top procesos), disk_info (info de un disco), kill (matar proceso), report (reporte general).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "overview, report, cpu, ram, disk, gpu, network, processes, top, disk_info, kill"},
                "path": {"type": "STRING", "description": "Unidad a inspeccionar para disk_info (default C:\\)"},
                "sort": {"type": "STRING", "description": "Orden de procesos: cpu, ram, name (default cpu)"},
                "count": {"type": "INTEGER", "description": "Cantidad de procesos a listar (default 10)"},
                "name": {"type": "STRING", "description": "Nombre del proceso a matar (kill)"},
                "pid": {"type": "INTEGER", "description": "PID del proceso a matar (kill)"},
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
        "description": "Gestion de ventanas multi-monitor: listar, enfocar, mover, minimizar, cerrar, maximizar, snap y organizar en layouts. Acciones: list, list_monitors, focus, move_to_monitor, minimize, close, maximize, snap, organize.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, list_monitors, focus, move_to_monitor, minimize, close, maximize, snap, organize"},
                "name": {"type": "STRING", "description": "Titulo de la ventana"},
                "monitor": {"type": "INTEGER", "description": "Indice del monitor (default 1)"},
                "position": {"type": "STRING", "description": "center, left, right, top, bottom (default center)"},
                "width": {"type": "NUMBER", "description": "Porcentaje de ancho (default 50)"},
                "height": {"type": "NUMBER", "description": "Porcentaje de alto (default 70)"},
                "preset": {"type": "STRING", "description": "Layout: side_by_side, three_columns, quad, ca (default auto)"},
                "layout": {"type": "STRING", "description": "Alias de preset"},
                "side": {"type": "STRING", "description": "Lado para snap: left (default), right"},
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
                "title": {"type": "STRING", "description": "Alias de titulo"},
                "letra": {"type": "STRING", "description": "Letra completa de la canción (para componer)"},
                "lyrics": {"type": "STRING", "description": "Alias de letra"},
                "tema": {"type": "STRING", "description": "Tema de la canción (para generar_letra)"},
                "topic": {"type": "STRING", "description": "Alias de tema"},
                "genero": {"type": "STRING", "description": "Género musical: pop, rock, balada, reggaeton, vallenato, salsa, electronica, rap, cumbia, jazz, etc."},
                "genre": {"type": "STRING", "description": "Alias de genero"},
                "estilo_voz": {"type": "STRING", "description": "Estilo de voz: dulce, poderosa, suave, alegre, melancolica, ronca, angelical"},
                "voice_style": {"type": "STRING", "description": "Alias de estilo_voz"},
                "output_path": {"type": "STRING", "description": "Ruta para guardar el archivo .wav"},
                "file_path": {"type": "STRING", "description": "Alias de output_path (ruta de guardado)"},
                "path": {"type": "STRING", "description": "Alias de output_path (ruta de guardado)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "code_helper",
        "description": "Write, edit, explain, run, build, help — code in any language. Use help for programming questions and guidance. Saves to Desktop/ERIS_Codigo by default.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "write, edit, explain, run, build, auto, help"},
                "language": {"type": "STRING", "description": "python, javascript, html, css, etc"},
                "code": {"type": "STRING", "description": "Code to write/explain/run"},
                "description": {"type": "STRING", "description": "What to build (for auto/write)"},
                "file_path": {"type": "STRING", "description": "Save path. Full path like 'C:\\Users\\danie\\Desktop\\script.py' or directory. Defaults to Desktop\\ERIS_Codigo."},
                "output_path": {"type": "STRING", "description": "Alias de file_path (ruta de salida)"},
                "args": {"type": "STRING", "description": "Argumentos para ejecutar el codigo (para run)"},
                "timeout": {"type": "INTEGER", "description": "Timeout en segundos para ejecucion (default 30)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_creator",
        "description": "Crea documentos de texto, Word o Excel locales. Acciones: create (crear desde title+content), create_sheet (crear Excel desde sheets), create_presentation (crear PowerPoint desde slides). Guarda en Desktop por defecto.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, create_sheet, create_presentation"},
                "title": {"type": "STRING", "description": "Titulo del documento (default Documento_Sin_Titulo)"},
                "content": {"type": "STRING", "description": "Contenido en markdown (para create)"},
                "sheets": {"type": "STRING", "description": "Hoja(s) para Excel (JSON, para create_sheet)"},
                "slides": {"type": "STRING", "description": "Diapositivas para PowerPoint (JSON, para create_presentation)"},
                "save_path": {"type": "STRING", "description": "Ruta o carpeta de guardado (default Desktop\\ERIS_Documentos)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_handler",
        "description": "Create Word, PDF, Excel, PowerPoint, CSV, TXT documents with content and memory — always saves to Desktop. Actions: create_word, create_pptx, create_excel, create_pdf, create_txt, create_csv, read, summarize, what_i_wrote, working_doc, merge (unir varios PDFs), split, translate (traducir), ask (preguntar sobre el documento).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create_word, create_pptx, create_excel, create_pdf, create_txt, create_csv, read, summarize, what_i_wrote, working_doc, merge, split, translate, ask"},
                "title": {"type": "STRING", "description": "Document title"},
                "content": {"type": "STRING", "description": "Document content in markdown (for create actions)"},
                "path": {"type": "STRING", "description": "Full path or directory to save the document. If a directory, auto-generates filename. Examples: 'C:\\Users\\danie\\Desktop' or 'C:\\Users\\danie\\Desktop\\mi_doc.docx'. Defaults to Desktop\\ERIS_Documentos."},
                "output": {"type": "STRING", "description": "Ruta de salida (para merge/translate/convertir a PDF)"},
                "paths": {"type": "STRING", "description": "Lista de rutas de PDFs a unir (JSON, para merge)"},
                "output_dir": {"type": "STRING", "description": "Carpeta de salida para split"},
                "target_lang": {"type": "STRING", "description": "Idioma destino (default es, para translate)"},
                "question": {"type": "STRING", "description": "Pregunta sobre el documento (para ask)"},
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
                "new_goal": {"type": "STRING", "description": "Nuevo objetivo (para add)"},
                "text": {"type": "STRING", "description": "Alias de new_goal"},
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
        "description": "Base de conocimiento local de ERIS: agregar, buscar, actualizar, eliminar y exportar entradas con titulo, contenido, tipo y etiquetas. Acciones: add, search, list, update, remove, stats, export.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, search, list, update, remove, stats, export"},
                "title": {"type": "STRING", "description": "Titulo de la entrada (para add/update)"},
                "content": {"type": "STRING", "description": "Contenido de la entrada (para add/update)"},
                "type": {"type": "STRING", "description": "Tipo de entrada: note, info, config (default note)"},
                "tags": {"type": "STRING", "description": "Etiquetas separadas por coma"},
                "query": {"type": "STRING", "description": "Texto de busqueda (para search)"},
                "entry_id": {"type": "STRING", "description": "ID de la entrada (para update/remove)"},
                "path": {"type": "STRING", "description": "Ruta de exportacion (para export)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "notifications",
        "description": "Send push notifications via ntfy or Windows toast. Acciones: send (title/message/channel), config.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send | config"},
                "title": {"type": "STRING", "description": "Título de la notificación"},
                "message": {"type": "STRING", "description": "Mensaje de la notificación"},
                "channel": {"type": "STRING", "description": "auto | ntfy | toast"},
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
                "id": {"type": "STRING", "description": "Alias de task_id"},
                "name": {"type": "STRING", "description": "Alias de task_id"},
                "message": {"type": "STRING", "description": "Alias de task (mensaje de la tarea)"},
                "delay": {"type": "STRING", "description": "Alias de time (ej. '5m', '1h')"},
                "when": {"type": "STRING", "description": "Alias de time"},
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
        "description": "Code review: review, security, style, history, stats, quick, review_diff (revisa git diff sin commitear; use_llm=true lo revisa con LLM), pr (revisa el diff y crea un Pull Request; title/head/base opcionales, si no hay title lo infiere el LLM).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "review, security, style, history, stats, quick, review_diff, pr"},
                "path": {"type": "STRING", "description": "File or directory to review (review/security/style/quick)"},
                "repo": {"type": "STRING", "description": "Repo git (review_diff/pr; default: ERIS)"},
                "use_llm": {"type": "BOOLEAN", "description": "review_diff con LLM (default false)"},
                "title": {"type": "STRING", "description": "Titulo del PR (pr; si falta lo infiere el LLM)"},
                "head": {"type": "STRING", "description": "Rama origen del PR (pr; default: rama actual)"},
                "base": {"type": "STRING", "description": "Rama destino del PR (pr; default: main)"},
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
                "patron": {"type": "STRING", "description": "Alias de pattern"},
                "detail": {"type": "STRING", "description": "Detail level: summary, full"},
                "detalle": {"type": "STRING", "description": "Alias de detail"},
                "archivo": {"type": "STRING", "description": "Archivo o carpeta a analizar (alias de target)"},
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
                "descripcion": {"type": "STRING", "description": "Alias de task (espanol)"},
                "files": {"type": "STRING", "description": "Comma-separated list of files"},
                "archivos": {"type": "STRING", "description": "Alias de files (espanol)"},
                "message": {"type": "STRING", "description": "Commit message"},
                "mensaje": {"type": "STRING", "description": "Alias de message (espanol)"},
                "target": {"type": "STRING", "description": "Target file or directory for exploration"},
                "objetivo": {"type": "STRING", "description": "Alias de target (espanol)"},
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
        "description": "Full Git operations: status, add, commit, push, pull, branch, log, diff, filter-branch, init, remote, tag, GitHub repo creation, credential retrieval, worktrees (experimentos en ramas aisladas)",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, add, commit, push, pull, branch, checkout, merge, log, diff, remote, init, tag, force_push, push_tags, filter_branch, gc, show, rm, stash, stash_pop, reset, reflog, clean, credential, github_create_repo, github_set_remote, worktree_add, worktree_list, worktree_remove"},
                "message": {"type": "STRING", "description": "Commit message"},
                "branch": {"type": "STRING", "description": "Branch or tag name"},
                "file": {"type": "STRING", "description": "File path for git operations"},
                "url": {"type": "STRING", "description": "Remote URL"},
                "path": {"type": "STRING", "description": "Repository path (defaults to project dir)"},
                "worktree_path": {"type": "STRING", "description": "Carpeta destino del worktree (worktree_add/remove)"},
                "n": {"type": "INTEGER", "description": "Number of log entries"},
                "expression": {"type": "STRING", "description": "Expression for filter-branch"},
                "repo_name": {"type": "STRING", "description": "Repository name for GitHub creation"},
                "token": {"type": "STRING", "description": "GitHub token"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "github_pr",
        "description": "Pull Requests de GitHub vía API REST. Crea, lista, ve el estado, consulta los checks de CI y mergea PRs del repo (detecta owner/repo del remote origin).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "pr_create, pr_list, pr_view, pr_checks, pr_merge"},
                "owner": {"type": "STRING", "description": "Owner del repo (opcional si el remote origin está configurado)"},
                "repo": {"type": "STRING", "description": "Nombre del repo (opcional si el remote origin está configurado)"},
                "title": {"type": "STRING", "description": "Título del PR (pr_create)"},
                "head": {"type": "STRING", "description": "Rama fuente del PR (pr_create)"},
                "base": {"type": "STRING", "description": "Rama destino del PR (default: main)"},
                "body": {"type": "STRING", "description": "Descripción del PR (pr_create, opcional)"},
                "number": {"type": "STRING", "description": "Número del PR (pr_view, pr_checks, pr_merge)"},
                "state": {"type": "STRING", "description": "Filtro de estado para pr_list (open, closed, all)"},
                "limit": {"type": "INTEGER", "description": "Cantidad máxima de PRs a listar (default: 10)"},
                "method": {"type": "STRING", "description": "Método de merge (merge, squash, rebase)"},
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
        "description": "Creates and registers a new tool dynamically. Requiere tool_name, description, python_code; parameters_schema opcional (dict JSON de propiedades).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tool_name": {"type": "STRING", "description": "Nombre de la nueva tool (snake_case)"},
                "description": {"type": "STRING", "description": "Qué hace la tool"},
                "python_code": {"type": "STRING", "description": "Código Python de la función"},
                "parameters_schema": {"type": "STRING", "description": "JSON con las propiedades de los parámetros"},
            },
            "required": ["tool_name", "description", "python_code"],
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
                "ruta": {"type": "STRING", "description": "Alias de path (espanol)"},
                "file": {"type": "STRING", "description": "Archivo a abrir/crear"},
                "archivo": {"type": "STRING", "description": "Alias de file (espanol)"},
                "folder": {"type": "STRING", "description": "Carpeta para servidor/watcher"},
                "carpeta": {"type": "STRING", "description": "Alias de folder (espanol)"},
                "line": {"type": "INTEGER", "description": "Numero de linea"},
                "col": {"type": "INTEGER", "description": "Numero de columna"},
                "port": {"type": "INTEGER", "description": "Puerto para live-server"},
                "command": {"type": "STRING", "description": "Comando VS Code o accion al detectar cambio"},
                "comando": {"type": "STRING", "description": "Alias de command (espanol)"},
                "query": {"type": "STRING", "description": "Texto a buscar"},
                "buscar": {"type": "STRING", "description": "Alias de query (espanol)"},
                "content": {"type": "STRING", "description": "Contenido para nuevo archivo"},
                "extension": {"type": "STRING", "description": "ID de extension VS Code"},
                "file1": {"type": "STRING", "description": "Primer archivo para diff"},
                "file2": {"type": "STRING", "description": "Segundo archivo para diff"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "ide_integration",
        "description": "Integracion con IDEs de programacion. Detecta el IDE activo (VS Code, Visual Studio, IntelliJ, PyCharm, NetBeans, etc), lee el codigo del editor, y permite ediciones quirurgicas: cambiar una letra, numero, palabra, linea o bloque especifico sin reescribir todo el archivo. Tambien puede crear archivos nuevos, eliminar lineas, insertar codigo, y mejorar codigo existente. Cuando el usuario pida explicar codigo, corregir un error especifico, o modificar algo en su IDE, usa esta herramienta.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "detect (detectar IDE), read (leer codigo), explain (explicar codigo), edit (find-replace), edit_line (reemplazar linea), edit_lines (reemplazar bloque), delete_lines (eliminar lineas), delete_text (eliminar texto), create_file (crear archivo nuevo), insert_at_line (insertar codigo en linea), edit_in_editor (reemplazar via teclado)"},
                "file_path": {"type": "STRING", "description": "Ruta completa del archivo a editar (requerido para edit, edit_line, edit_lines)"},
                "path": {"type": "STRING", "description": "Alias de file_path"},
                "old_text": {"type": "STRING", "description": "Texto exacto a buscar y reemplazar (para edit, edit_in_editor)"},
                "new_text": {"type": "STRING", "description": "Texto de reemplazo (para edit, edit_in_editor)"},
                "line_number": {"type": "INTEGER", "description": "Numero de linea a reemplazar (1-indexed, para edit_line)"},
                "line": {"type": "INTEGER", "description": "Alias de line_number"},
                "new_content": {"type": "STRING", "description": "Nuevo contenido de la linea (para edit_line)"},
                "start_line": {"type": "INTEGER", "description": "Linea inicial del bloque (para edit_lines)"},
                "end_line": {"type": "INTEGER", "description": "Linea final del bloque (para edit_lines)"},
                "new_code": {"type": "STRING", "description": "Nuevo codigo del bloque (para edit_lines)"},
                "code": {"type": "STRING", "description": "Alias de new_code o new_content"},
                "focus": {"type": "STRING", "description": "Enfoque para explicacion: general, bugs, performance, security, logic"},
                "max_chars": {"type": "INTEGER", "description": "Maximo de caracteres a leer del editor (default 8000)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "code_assistant",
        "description": "Asistente de codigo proactivo. Escaneo completo automatico: detecta si hay un IDE abierto, lee el codigo, y encuentra errores de sintaxis, advertencias, y sugerencias de mejora. Retorna un reporte con problemas encontrados. USAR SIEMPRE que el usuario mencione programacion, codigo, errores, o compilar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan (escaneo completo), format (formatear reporte)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "project_builder",
        "description": "Generador autonomo de proyectos COMPLETOS de software. Crea toda la estructura de carpetas, codigo fuente, configuracion de build, y compila/valida. SOPORTA: java_maven (Java+Maven+NetBeans Swing con .form XML), python (dataclasses, repositorios, tests), csharp (ASP.NET/Blazor), html_css_js (HTML+CSS+JS vanilla), react (React+Vite), angular (Angular 17+), vue (Vue3+Vite), mysql (schema+data+procedures+views). PARAMETROS: project_type (java_maven/python/csharp/html_css_js/react/angular/vue/mysql), project_name (nombre del proyecto), description (descripcion), output_dir (donde crearlo, default Desktop), fields (JSON array de entidades con campos), database (nombre BD para MySQL), features (JSON array de features). USAR cuando el usuario pida crear un sistema, aplicacion, proyecto, o programa completo. Ejemplo: project_builder(project_type='java_maven', project_name='SistemaMantenimiento', description='Sistema de registro', fields='[{\"name\":\"equipo\",\"fields\":[{\"name\":\"id\",\"type\":\"int\"},{\"name\":\"nombre\",\"type\":\"String\"}]}]')",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create (crear proyecto completo), list (listar tipos soportados)"},
                "project_type": {"type": "STRING", "description": "java_maven, python, csharp, html_css_js, react, angular, vue, mysql"},
                "project_name": {"type": "STRING", "description": "Nombre del proyecto"},
                "tipo": {"type": "STRING", "description": "Alias de project_type (tipo de proyecto)"},
                "nombre": {"type": "STRING", "description": "Alias de project_name (nombre del proyecto)"},
                "description": {"type": "STRING", "description": "Descripcion del proyecto"},
                "descripcion": {"type": "STRING", "description": "Alias de description (descripcion del proyecto)"},
                "output_dir": {"type": "STRING", "description": "Ruta donde crear el proyecto (default: Desktop)"},
                "fields": {"type": "STRING", "description": "Campos/entidades como JSON array. Ejemplo: [{\"name\":\"equipo\",\"fields\":[{\"name\":\"id\",\"type\":\"int\"},{\"name\":\"nombre\",\"type\":\"String\"},{\"name\":\"marca\",\"type\":\"String\"},{\"name\":\"estado\",\"type\":\"String\"}]}]"},
                "campos": {"type": "STRING", "description": "Alias de fields (campos/entidades)"},
                "database": {"type": "STRING", "description": "Nombre de base de datos (para MySQL)"},
                "features": {"type": "STRING", "description": "Features como JSON array: [\"login\",\"dashboard\",\"reportes\"]"},
            },
            "required": ["project_type", "project_name"],
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
                "titulo": {"type": "STRING", "description": "Alias de title (titulo del sitio)"},
                "carpeta": {"type": "STRING", "description": "Alias de folder (carpeta del sitio)"},
                "descripcion": {"type": "STRING", "description": "Alias de description (descripcion del sitio)"},
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
                "titulo": {"type": "STRING", "description": "Alias en espanol de title"},
                "tema": {"type": "STRING", "description": "Alias en espanol de topic"},
                "descripcion": {"type": "STRING", "description": "Alias en espanol de description"},
                "content": {"type": "STRING", "description": "Alias de sections (contenido real de la pagina)"},
                "contenido": {"type": "STRING", "description": "Alias en espanol de sections"},
                "carpeta": {"type": "STRING", "description": "Alias en espanol de folder"},
                "reference": {"type": "STRING", "description": "Alias de reference_url"},
                "video": {"type": "STRING", "description": "Alias de video_url"},
                "video_url": {"type": "STRING", "description": "URL de video a incluir en la pagina (action=create)"},
                "design_brief": {"type": "STRING", "description": "Brief de diseno: requerimientos, tono, colores sugeridos, secciones deseadas"},
                "design_style": {"type": "STRING", "description": "Estilo forzado (editorial, minimal, brutalista, corporativo, dark, tech, dashboard, ecommerce, artesanal, portafolio, creativo, evento, documentacion, vet, lumina, natural, tierno, medico, futurista, colorido). Vence a la seleccion automatica."},
                "style": {"type": "STRING", "description": "Alias de design_style"},
                "pages": {"type": "STRING", "description": "site (multi-pagina) o single (una pagina)"},
                "site": {"type": "STRING", "description": "Alias de pages"},
                "images": {"type": "INTEGER", "description": "Cantidad de imagenes a incluir (default auto)"},
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
                "titulo": {"type": "STRING", "description": "Alias en espanol de title"},
                "tema": {"type": "STRING", "description": "Alias en espanol de topic"},
                "descripcion": {"type": "STRING", "description": "Alias en espanol de description"},
                "content": {"type": "STRING", "description": "Alias de sections (contenido real)"},
                "reference": {"type": "STRING", "description": "Alias de reference_url"},
                "reference_url": {"type": "STRING", "description": "URL de referencia cuyo estilo clonar (action=create)"},
                "design_brief": {"type": "STRING", "description": "Brief de diseno: requerimientos, tono, colores sugeridos, secciones deseadas"},
                "design_style": {"type": "STRING", "description": "Estilo forzado (editorial, minimal, brutalista, corporativo, dark, tech, dashboard, ecommerce, artesanal, portafolio, creativo, evento, documentacion, vet, lumina, natural, tierno, medico, futurista, colorido). Vence a la seleccion automatica."},
                "style": {"type": "STRING", "description": "Alias de design_style"},
                "site": {"type": "STRING", "description": "Alias de pages"},
                "images": {"type": "INTEGER", "description": "Cantidad de imagenes de galeria (default 4)"},
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
                "titulo": {"type": "STRING", "description": "Alias en espanol de title"},
                "tema": {"type": "STRING", "description": "Alias en espanol de topic"},
                "descripcion": {"type": "STRING", "description": "Alias en espanol de description"},
                "content": {"type": "STRING", "description": "Alias de sections (contenido real)"},
                "reference": {"type": "STRING", "description": "Alias de reference_url"},
                "reference_url": {"type": "STRING", "description": "URL de referencia cuyo estilo clonar (action=create)"},
                "design_brief": {"type": "STRING", "description": "Brief de diseno: requerimientos, tono, colores sugeridos, secciones deseadas"},
                "design_style": {"type": "STRING", "description": "Estilo forzado (editorial, minimal, brutalista, corporativo, dark, tech, dashboard, ecommerce, artesanal, portafolio, creativo, evento, documentacion, vet, lumina, natural, tierno, medico, futurista, colorido). Vence a la seleccion automatica."},
                "style": {"type": "STRING", "description": "Alias de design_style"},
                "site": {"type": "STRING", "description": "Alias de pages"},
                "images": {"type": "INTEGER", "description": "Cantidad de imagenes de galeria (default 4)"},
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
                "titulo": {"type": "STRING", "description": "Alias en espanol de title"},
                "tema": {"type": "STRING", "description": "Alias en espanol de topic"},
                "descripcion": {"type": "STRING", "description": "Alias en espanol de description"},
                "content": {"type": "STRING", "description": "Alias de sections (contenido real)"},
                "reference": {"type": "STRING", "description": "Alias de reference_url"},
                "reference_url": {"type": "STRING", "description": "URL de referencia cuyo estilo clonar (action=create)"},
                "design_brief": {"type": "STRING", "description": "Brief de diseno: requerimientos, tono, colores sugeridos, secciones deseadas"},
                "design_style": {"type": "STRING", "description": "Estilo forzado (editorial, minimal, brutalista, corporativo, dark, tech, dashboard, ecommerce, artesanal, portafolio, creativo, evento, documentacion, vet, lumina, natural, tierno, medico, futurista, colorido). Vence a la seleccion automatica."},
                "style": {"type": "STRING", "description": "Alias de design_style"},
                "site": {"type": "STRING", "description": "Alias de pages"},
                "images": {"type": "INTEGER", "description": "Cantidad de imagenes de galeria (default 4)"},
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
                "titulo": {"type": "STRING", "description": "Alias en espanol de title"},
                "tema": {"type": "STRING", "description": "Alias en espanol de topic"},
                "descripcion": {"type": "STRING", "description": "Alias en espanol de description"},
                "content": {"type": "STRING", "description": "Alias de sections (contenido real)"},
                "reference": {"type": "STRING", "description": "Alias de reference_url"},
                "reference_url": {"type": "STRING", "description": "URL de referencia cuyo estilo clonar (action=create)"},
                "design_brief": {"type": "STRING", "description": "Brief de diseno: requerimientos, tono, colores sugeridos, secciones deseadas"},
                "style": {"type": "STRING", "description": "Alias de design_style"},
                "site": {"type": "STRING", "description": "Alias de pages"},
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
        "name": "telegram_bot",
        "description": "Integracion con Telegram: enviar mensajes/archivos al telefono del dueno (chat_id ya configurado por defecto, no hace falta pasarlo). Acciones: send_message, send_file, get_updates, list_chats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send_message, send_file, get_updates, list_chats"},
                "chat_id": {"type": "STRING", "description": "ID del chat (opcional, ya hay uno por defecto)"},
                "text": {"type": "STRING", "description": "Texto del mensaje"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo a enviar"},
                "limit": {"type": "INTEGER", "description": "Max de actualizaciones a obtener (para get_updates)"},
                "parse_mode": {"type": "STRING", "description": "Modo de parseo: HTML, Markdown"},
                "poll_interval": {"type": "INTEGER", "description": "Intervalo de sondeo en segundos (para get_updates)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "phone_control",
        "description": "Controla el celular Android del dueno desde la PC (via adb/scrcpy, requiere el celular conectado por USB con depuracion autorizada). SIN root. Acciones: status, mirror (abre la pantalla del celu en la PC), open_app (app=nombre, puede ser CUALQUIER app instalada), apps, open_url (url=...), search (query=... busca en Google en el celu), tap (x,y), tap_text (text=... toca el elemento de la pantalla que contiene ese texto, ideal para navegar apps), swipe (x1,y1,x2,y2,ms), scroll (direction=down|up), text (text=... escribe), ui (lista los elementos de la pantalla con sus coordenadas), screenshot (guarda la captura), battery, home, back, recent, unlock. Para navegar una app: usá ui o tap_text para encontrar y tocar botones por su texto, text para escribir, scroll para bajar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, mirror, open_app, apps, open_url, search, tap, tap_text, swipe, scroll, text, ui, screenshot, battery, home, back, recent, unlock"},
                "app": {"type": "STRING", "description": "Nombre de la app para open_app (youtube, whatsapp, o el nombre de cualquier app instalada)"},
                "name": {"type": "STRING", "description": "Alias de app"},
                "url": {"type": "STRING", "description": "URL a abrir en el celular (open_url)"},
                "query": {"type": "STRING", "description": "Texto a buscar en Google en el celular (search)"},
                "q": {"type": "STRING", "description": "Alias de query"},
                "x": {"type": "INTEGER", "description": "Coordenada X del toque (tap)"},
                "y": {"type": "INTEGER", "description": "Coordenada Y del toque (tap)"},
                "coord_x": {"type": "INTEGER", "description": "Alias de x"},
                "coord_y": {"type": "INTEGER", "description": "Alias de y"},
                "label": {"type": "STRING", "description": "Texto del elemento a tocar (tap_text)"},
                "text": {"type": "STRING", "description": "Texto a escribir en el celular (text) o etiqueta a tocar (tap_text)"},
                "message": {"type": "STRING", "description": "Alias de text"},
                "x1": {"type": "INTEGER", "description": "X inicial del swipe"},
                "y1": {"type": "INTEGER", "description": "Y inicial del swipe"},
                "x2": {"type": "INTEGER", "description": "X final del swipe"},
                "y2": {"type": "INTEGER", "description": "Y final del swipe"},
                "ms": {"type": "INTEGER", "description": "Duracion del swipe en ms"},
                "direction": {"type": "STRING", "description": "down o up (scroll)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "unified_communications",
        "description": "Centraliza el envío y consulta de mensajes en múltiples plataformas (WhatsApp, Telegram, Discord, Gmail). Acciones: send (enviar mensaje a un destinatario en la plataforma indicada), read, status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send, read, status"},
                "platform": {"type": "STRING", "description": "Plataforma: whatsapp, telegram, discord, gmail, webhook"},
                "recipient": {"type": "STRING", "description": "Destinatario: numero, email, ID de chat o URL de webhook"},
                "message": {"type": "STRING", "description": "Mensaje a enviar"},
                "subject": {"type": "STRING", "description": "Asunto (para gmail)"},
                "token": {"type": "STRING", "description": "Token del bot (para telegram)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "whatsapp",
        "description": "WhatsApp messaging (via pywhatkit). Acciones: send (enviar mensaje con imagen/caption opcional), read, list_contacts, add_contact (con name y phone).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send, read, list_contacts, add_contact"},
                "receiver": {"type": "STRING", "description": "Contact name or phone"},
                "message": {"type": "STRING", "description": "Message text"},
                "image_path": {"type": "STRING", "description": "Ruta de imagen adjunta (para send)"},
                "caption": {"type": "STRING", "description": "Texto junto a la imagen (para send)"},
                "name": {"type": "STRING", "description": "Nombre del contacto (para add_contact)"},
                "phone": {"type": "STRING", "description": "Numero del contacto (para add_contact)"},
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
        "name": "rgb_control",
        "description": "Control real de iluminacion RGB via OpenRGB (SDK local), WLED (HTTP) o simulacion. Acciones: status (estado y backend activo), devices (dispositivos), set (color: nombre, #hex o r,g,b), off, brightness (0-100), scene (alive, fuego, frio, pastel, noche), effect (rainbow, breath, wave), add_device (name), remove_device (name), config (backend: auto|openrgb|wled|simulate, opcional wled_ip, openrgb_host).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, devices, set, off, brightness, scene, effect, add_device, remove_device, config"},
                "color": {"type": "STRING", "description": "Color deseado: 'red', '#FF8800' o '255,136,0' (para set)"},
                "device": {"type": "STRING", "description": "Nombre del dispositivo RGB a apuntar (opcional)"},
                "brightness": {"type": "INTEGER", "description": "Brillo 0-100 (para brightness)"},
                "value": {"type": "INTEGER", "description": "Alias de brightness (0-100)"},
                "scene": {"type": "STRING", "description": "Escena: alive, fuego, frio, pastel, noche (para scene)"},
                "effect": {"type": "STRING", "description": "Efecto: rainbow, breath, wave (para effect)"},
                "name": {"type": "STRING", "description": "Nombre del dispositivo (para add_device/remove_device) o alias de scene/effect"},
                "backend": {"type": "STRING", "description": "Backend: auto, openrgb, wled, simulate (para config)"},
                "wled_ip": {"type": "STRING", "description": "IP del WLED (para config)"},
                "openrgb_host": {"type": "STRING", "description": "Host de OpenRGB (para config, default 127.0.0.1)"},
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
                "device": {"type": "STRING", "description": "Alias de name"},
                "id": {"type": "STRING", "description": "Alias de name (id del dispositivo)"},
                "state": {"type": "STRING", "description": "on u off (para control)"},
                "value": {"type": "STRING", "description": "Alias de state"},
                "scene_id": {"type": "STRING", "description": "Id o nombre de la escena a activar"},
                "scene": {"type": "STRING", "description": "Alias de scene_id"},
                "type": {"type": "STRING", "description": "Tipo de dispositivo: switch, light, etc. (para add_device)"},
                "location": {"type": "STRING", "description": "Ubicacion del dispositivo (default General, para add_device)"},
                "entity_id": {"type": "STRING", "description": "Entity ID de Home Assistant (para add_device)"},
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
            },
            "required": ["action"],
        }
    },
    {
        "name": "accessibility_overlay",
        "description": "Overlay de accesibilidad: lupa de pantalla flotante que sigue al mouse, lector de texto seleccionado en voz alta, y alto contraste. Acciones: status (estado), magnifier (mode=start|stop, zoom 1-10), read_selection (lee lo seleccionado con edge-tts), high_contrast (mode=on|off).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, magnifier, read_selection, high_contrast"},
                "mode": {"type": "STRING", "description": "start|stop (magnifier) u on|off (high_contrast)"},
                "state": {"type": "STRING", "description": "Alias de mode"},
                "zoom": {"type": "NUMBER", "description": "Zoom de la lupa 1-10 (default 3)"},
                "value": {"type": "STRING", "description": "Alias de mode (para high_contrast)"},
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
                "action": {"type": "STRING", "description": "adjust, status"},
                "state": {"type": "STRING", "description": "Estado a aplicar: day, night, work, relax"},
                "volume": {"type": "INTEGER", "description": "Nivel de volumen 0-100"},
                "brightness": {"type": "INTEGER", "description": "Nivel de brillo 0-100"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "human_mouse",
        "description": "Control del mouse con movimiento natural y humano. Acciones: click, double_click, right_click, move (mover a x,y), move_to (mover a elemento), drag (de x,y a x2,y2), scroll (direccion y cantidad), type (escribir texto), select_option (elegir opcion por texto), etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "click, double_click, right_click, move, move_to, drag, scroll, type, select_option"},
                "x": {"type": "INTEGER", "description": "Coordenada X"},
                "y": {"type": "INTEGER", "description": "Coordenada Y"},
                "x2": {"type": "INTEGER", "description": "Coordenada X final (para drag)"},
                "y2": {"type": "INTEGER", "description": "Coordenada Y final (para drag)"},
                "button": {"type": "STRING", "description": "Boton: left, right, middle (default left)"},
                "direction": {"type": "STRING", "description": "Direccion del scroll: down, up (default down)"},
                "amount": {"type": "INTEGER", "description": "Cantidad de pasos del scroll (default 3)"},
                "text": {"type": "STRING", "description": "Texto a escribir (para type)"},
                "speed": {"type": "STRING", "description": "Velocidad del movimiento: slow, normal, fast (default normal)"},
                "edge": {"type": "STRING", "description": "Borde de la pantalla para mover: left, right, top, bottom (default right)"},
                "side": {"type": "STRING", "description": "Lado dentro de la ventana (default left)"},
                "target_x": {"type": "INTEGER", "description": "X del objetivo (para move_to)"},
                "target_y": {"type": "INTEGER", "description": "Y del objetivo (para move_to)"},
                "option_text": {"type": "STRING", "description": "Texto de la opcion a elegir (para select_option)"},
                "element_description": {"type": "STRING", "description": "Descripcion del elemento a buscar (para move_to)"},
                "description": {"type": "STRING", "description": "Alias de element_description"},
                "duration": {"type": "NUMBER", "description": "Duracion del movimiento en segundos (default 0.5)"},
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
            },
            "required": ["action"],
        }
    },
    {
        "name": "proactive_automation",
        "description": "Reglas de automatizacion proactiva basadas en habitos y comportamientos del sistema. Acciones: status (ver reglas activas), add (crear regla: rule_name, trigger, trigger_value, action_to_take), remove (eliminar regla por rule_name).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, add, remove"},
                "rule_name": {"type": "STRING", "description": "Nombre de la regla"},
                "trigger": {"type": "STRING", "description": "Disparador: cpu_high, time_of_day, app_open, etc."},
                "trigger_value": {"type": "STRING", "description": "Valor del disparador: '85', '22:00', 'chrome.exe'"},
                "action_to_take": {"type": "STRING", "description": "Accion a ejecutar: optimize_ram, mute_system, run... etc."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "screen_reader",
        "description": "OCR real de pantalla (Windows OCR API). Acciones: read_screen (OCR de toda la pantalla), read_region (OCR de una region: x1,y1,x2,y2 o x,y,width,height), find_text (text: busca un texto en pantalla), read_image (path: OCR de un archivo de imagen), status. Complementa a screen_see (vision IA).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read_screen, read_region, find_text, read_image, status"},
                "x1": {"type": "INTEGER", "description": "Coordenada X inicial de la region (para read_region)"},
                "y1": {"type": "INTEGER", "description": "Coordenada Y inicial de la region (para read_region)"},
                "x2": {"type": "INTEGER", "description": "Coordenada X final de la region (o width si usas x,y,width,height)"},
                "y2": {"type": "INTEGER", "description": "Coordenada Y final de la region (o height si usas x,y,width,height)"},
                "x": {"type": "INTEGER", "description": "Coordenada X inicial (alias de x1)"},
                "y": {"type": "INTEGER", "description": "Coordenada Y inicial (alias de y1)"},
                "width": {"type": "INTEGER", "description": "Ancho de la region (para x,y,width,height)"},
                "height": {"type": "INTEGER", "description": "Alto de la region (para x,y,width,height)"},
                "text": {"type": "STRING", "description": "Texto a buscar en pantalla (para find_text)"},
                "target": {"type": "STRING", "description": "Alias de text"},
                "path": {"type": "STRING", "description": "Ruta de imagen (para read_image)"},
                "image": {"type": "STRING", "description": "Alias de path"},
            },
            "required": ["action"],
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
                "deep": {"type": "BOOLEAN", "description": "Deep search: busca en contenido de archivos binarios/ocultos (default false)"},
                "deep_search": {"type": "BOOLEAN", "description": "Alias de deep"},
                "modified_after": {"type": "STRING", "description": "Solo archivos modificados después de esta fecha (YYYY-MM-DD)"},
                "size_min": {"type": "NUMBER", "description": "Tamaño mínimo en KB"},
                "size_max": {"type": "NUMBER", "description": "Tamaño máximo en KB"},
                "type": {"type": "STRING", "description": "Filtro por tipo/extension de archivo (alias de extension)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "deep_research",
        "description": "Deep research: busca en la web, entra a cada pagina, extrae contenido, analiza calidad con IA, y rankea resultados. Devuelve cual pagina tiene la mejor informacion y por que.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Termino a investigar"},
                "text": {"type": "STRING", "description": "Alias de query"},
                "search": {"type": "STRING", "description": "Alias de query"},
                "action": {"type": "STRING", "description": "research (investigacion completa), analyze (analizar URL especifica), history (ver historial)"},
                "url": {"type": "STRING", "description": "URL a analizar (para action=analyze)"},
                "num_results": {"type": "INTEGER", "description": "Cuantos resultados analizar (default 5)"},
                "count": {"type": "INTEGER", "description": "Alias de num_results"},
                "title": {"type": "STRING", "description": "Titulo para guardar el analisis (default url)"},
            },
            "required": ["query"],
        }
    },

    # ── Section 14H: Advanced ──

    {
        "name": "auto_programmer",
        "description": "Desarrollo y Auto-Programacion autonoma: permite escribir herramientas nuevas a partir de una descripcion, validar el codigo y probarlo. Acciones: create_tool (crear herramienta), test (probar con parametros), list, info.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create_tool, test, list, info"},
                "tool_name": {"type": "STRING", "description": "Nombre de la nueva herramienta"},
                "description": {"type": "STRING", "description": "Descripcion de lo que debe hacer"},
                "parameters_schema": {"type": "STRING", "description": "Esquema de parametros JSON ({} por defecto)"},
                "python_code": {"type": "STRING", "description": "Codigo Python de la herramienta"},
                "test_parameters": {"type": "STRING", "description": "Parametros de prueba (JSON) para action=test"},
                "reference_file": {"type": "STRING", "description": "Archivo de referencia para inspiracion del codigo"},
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
                "action": {"type": "STRING", "description": "click, double_click, right_click, type, smart_type, open_and_type (abre app + escribe), press, hotkey, scroll, scroll_up/down, smooth_scroll, drag, get_mouse_pos, move, copy, paste, screenshot, wait, clear_field, focus_window, open_tab, close_tab, switch_tab, next_tab, prev_tab, new_tab, select_all, undo, redo, save, enter, tab, escape, backspace, delete, home"},
                "x": {"type": "INTEGER", "description": "X coordinate"},
                "y": {"type": "INTEGER", "description": "Y coordinate"},
                "end_x": {"type": "INTEGER", "description": "X final del arrastre (para drag)"},
                "end_y": {"type": "INTEGER", "description": "Y final del arrastre (para drag)"},
                "text": {"type": "STRING", "description": "Text to type (para type/smart_type/open_and_type)"},
                "key": {"type": "STRING", "description": "Key or hotkey combination (para press/hotkey)"},
                "keys": {"type": "STRING", "description": "Combinacion de teclas (para hotkey)"},
                "app": {"type": "STRING", "description": "App name to open (para action=open_and_type): notepad, calc, word, excel, paint, chrome, cmd, etc."},
                "direction": {"type": "STRING", "description": "Direccion del scroll: down, up (default down)"},
                "amount": {"type": "INTEGER", "description": "Cantidad de pasos del scroll (default 3)"},
                "duration": {"type": "NUMBER", "description": "Duracion del scroll suave en segundos (default 1.0)"},
                "seconds": {"type": "NUMBER", "description": "Segundos de espera (para wait) o velocidad del arrastre"},
                "smooth": {"type": "BOOLEAN", "description": "Scroll suave (default true)"},
                "path": {"type": "STRING", "description": "Ruta de destino (para screenshot)"},
                "title": {"type": "STRING", "description": "Titulo de la ventana (para focus_window)"},
                "url": {"type": "STRING", "description": "URL a abrir (para open_tab)"},
                "description": {"type": "STRING", "description": "Descripcion de la accion (referencia)"},
                "field": {"type": "STRING", "description": "Campo a limpiar (para clear_field)"},
                "clear_first": {"type": "BOOLEAN", "description": "Limpiar el campo antes de escribir (default true)"},
                "tab_index": {"type": "INTEGER", "description": "Indice de la pestana (para switch_tab, 1-based)"},
                "type": {"type": "STRING", "description": "Tipo de dato aleatorio: name, email, etc."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "role_orchestrator",
        "description": "Orquestador de micro-agentes de ERIS: delega una mision a un agente con rol especifico. Acciones: mission (ejecutar mision con mission/task, role, context).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "mission"},
                "mission": {"type": "STRING", "description": "Mision o tarea a delegar"},
                "task": {"type": "STRING", "description": "Alias de mission"},
                "role": {"type": "STRING", "description": "Rol del agente que ejecuta la mision"},
                "context": {"type": "STRING", "description": "Contexto adicional (JSON) para el agente"},
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
                "content": {"type": "STRING", "description": "Contenido a registrar (para reflect/diary)"},
                "type": {"type": "STRING", "description": "Tipo de entrada: reflection, learning, event (default reflection)"},
                "tags": {"type": "STRING", "description": "Etiquetas separadas por coma (para reflect)"},
                "limit": {"type": "INTEGER", "description": "Cantidad de entradas a mostrar (default 10)"},
                "query": {"type": "STRING", "description": "Texto de busqueda (para search)"},
                "file": {"type": "STRING", "description": "Ruta del archivo a leer/editar (para read_my_code/edit_my_code)"},
                "old": {"type": "STRING", "description": "Texto exacto a reemplazar (para edit_my_code)"},
                "new": {"type": "STRING", "description": "Texto de reemplazo (para edit_my_code)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_edit",
        "description": "Lee y edita archivos del codigo fuente de ERIS con busqueda y reemplazo exacto de texto. Crea backup automatico antes de editar y valida sintaxis (py_compile) tras editar .py. Acciones: read_file (leer), edit_file (buscar y reemplazar texto exacto), append_file (agregar al final), create_file (crear nuevo), list_files (listar directorio), list_backups, restore_backup, journal (ver bitacora de ediciones de la sesion).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read_file, edit_file, append_file, create_file, list_files, list_backups, restore_backup, journal"},
                "file": {"type": "STRING", "description": "Ruta relativa al proyecto ERIS. Ej: 'main.py', 'actions/terminal_agent.py', 'core/tool_declarations.py'"},
                "target": {"type": "STRING", "description": "Texto exacto a buscar (para edit_file)"},
                "replacement": {"type": "STRING", "description": "Texto de reemplazo (para edit_file)"},
                "content": {"type": "STRING", "description": "Contenido para create_file o append_file"},
                "backup_name": {"type": "STRING", "description": "Nombre del backup a restaurar (para restore_backup)"},
                "directory": {"type": "STRING", "description": "Directorio a listar (para list_files, ej: 'actions/')"},
                "n": {"type": "INTEGER", "description": "Cantidad de entradas de la bitácora a mostrar (para journal)"},
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
        "name": "undo",
        "description": "Patrón /undo de opencode: restaura el estado previo de archivos antes de una operación de escritura/edición (backup automático tomado por el dispatcher). Acciones: undo (restaurar la más reciente), undo_n (con n=índice, 1 = la más reciente), list (historial con n=cuántas), stats (resumen).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "undo, undo_n, list, stats"},
                "n": {"type": "INTEGER", "description": "Índice para undo_n o cantidad para list (default 1/10)"},
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
        "description": "Toma una captura de pantalla, usa vision para encontrar las coordenadas del elemento descrito y hace clic. Params: element_description (descripcion del elemento a hacer clic).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "element_description": {"type": "STRING", "description": "Descripcion del elemento a buscar y hacer clic"},
            },
            "required": ["element_description"],
        }
    },

    # ── Section 14I: Memory & Vision ──

    {
        "name": "document_rag",
        "description": "RAG sobre documentos y memoria: indexa documentos, memoria episodica y vault de Obsidian; consulta con preguntas semánticas. Acciones: index (indexar documento por path), query (consultar con top_k), stats (estadisticas), list (documentos indexados), delete (olvidar documento), clear (borrar indice, confirm=true), ingest (ingestar texto), index_episodic (indexar memoria episodica, max_entries opcional), compact_episodic (comprimir episodios antiguos, days=30), index_vault (indexar notas del vault de Obsidian, folders='wiki,outputs,raw').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "index, query, agentic_query, stats, list, delete, clear, ingest, index_episodic, compact_episodic, index_vault"},
                "path": {"type": "STRING", "description": "Ruta del documento a indexar/olvidar"},
                "query": {"type": "STRING", "description": "Pregunta o texto de busqueda"},
                "top_k": {"type": "INTEGER", "description": "Cantidad de fragmentos de contexto (default 5)"},
                "force_decompose": {"type": "BOOLEAN", "description": "Forzar descomposicion de query en sub-queries (para agentic_query)"},
                "confirm": {"type": "BOOLEAN", "description": "Confirmar accion destructiva (para clear)"},
                "text": {"type": "STRING", "description": "Texto a ingestar (para ingest)"},
                "label": {"type": "STRING", "description": "Etiqueta del texto ingestado (default text_ingest)"},
                "max_entries": {"type": "INTEGER", "description": "Limite de episodios a indexar (0 = todos, para index_episodic)"},
                "days": {"type": "INTEGER", "description": "Episodios mas antiguos que N dias a comprimir (default 30, para compact_episodic)"},
                "older_than": {"type": "INTEGER", "description": "Alias de days"},
                "folders": {"type": "STRING", "description": "Carpetas del vault a indexar, separadas por coma. Vacio = indexar todo el vault (default; para index_vault)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "game_companion",
        "description": "Companero de juegos. Analiza pantalla y ayuda. Acciones: analyze (analizar pantalla), help (ayuda con game). Params: game (juego), question (pregunta), target (objetivo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, help"},
                "game": {"type": "STRING", "description": "Nombre del juego"},
                "question": {"type": "STRING", "description": "Pregunta del usuario sobre el juego"},
                "target": {"type": "STRING", "description": "Objetivo o mision a completar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "image_analyzer",
        "description": "Analiza una imagen o URL con vision AI: describe el contenido, compara dos imagenes o responde preguntas sobre ellas. Acciones: analyze (analizar imagen), compare (comparar dos imagenes).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, compare"},
                "path": {"type": "STRING", "description": "Ruta o URL de la imagen"},
                "image": {"type": "STRING", "description": "Alias de path"},
                "path2": {"type": "STRING", "description": "Ruta o URL de la segunda imagen (para compare)"},
                "image2": {"type": "STRING", "description": "Alias de path2"},
            },
            "required": ["action"],
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
        "description": "Lectura y analisis de pantalla con IA: describe que hay en pantalla, busca un elemento, o lee texto. Tambien analiza archivos de imagen locales. Acciones: describe, find, read, analyze_image (usando file/path).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "describe, find, read"},
                "query": {"type": "STRING", "description": "Pregunta o instruccion sobre la pantalla/imagen"},
                "text": {"type": "STRING", "description": "Alias de query"},
                "question": {"type": "STRING", "description": "Alias de query"},
                "description": {"type": "STRING", "description": "Alias de query"},
                "prompt": {"type": "STRING", "description": "Prompt de analisis"},
                "target": {"type": "STRING", "description": "Elemento/objetivo a buscar (para find)"},
                "element": {"type": "STRING", "description": "Alias de target"},
                "file": {"type": "STRING", "description": "Ruta de imagen local a analizar (analyze_image)"},
                "path": {"type": "STRING", "description": "Alias de file"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "security_scanner",
        "description": "Escaneo de seguridad del sistema: malware, procesos, firewall, vulnerabilidades. Acciones: scan (escanear con path), block (confirm para bloquear), firewall, list. Params: action, confirm, path.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan, block, firewall, list"},
                "confirm": {"type": "BOOLEAN", "description": "Confirmacion del usuario para acciones que modifican el sistema"},
                "path": {"type": "STRING", "description": "Ruta o directorio a escanear"},
            },
            "required": ["action"],
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
                "path": {"type": "STRING", "description": "Ruta/carpeta a vigilar (opcional)"},
                "query": {"type": "STRING", "description": "Texto a buscar al vigilar (alias de prompt)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "eris_guardian",
        "description": "Guardian de ERIS: vigila la salud del codigo y del sistema. Escanea todos los archivos .py del proyecto, detecta errores de sintaxis o importacion, intenta repararlos automaticamente (con backup), monitorea CPU/RAM/GPU/disco, reinicia ERIS si se cae y mantiene un diario de reparaciones. Acciones: status (estado general del sistema + guardia), scan (escaneo completo de codigo), repair (reparar errores con backup), start (iniciar monitoreo en background), stop (detener monitoreo), journal (ver diario de reparaciones), fix (reparar un archivo especifico), memory (gestionar memoria), learn (aprender de un error).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, scan, repair, start, stop, journal, fix, memory, learn"},
                "repair": {"type": "BOOLEAN", "description": "Intentar reparar errores detectados (default true)"},
                "target": {"type": "STRING", "description": "Archivo .py especifico a escanear/reparar"},
                "file": {"type": "STRING", "description": "Alias de target (archivo a reparar)"},
                "auto": {"type": "BOOLEAN", "description": "Reparar automaticamente sin confirmar (default true)"},
                "topic": {"type": "STRING", "description": "Tema para la accion memory/learn"},
                "mode": {"type": "STRING", "description": "Modo de monitoreo (para start)"},
                "interval": {"type": "INTEGER", "description": "Intervalo de monitoreo en segundos (default 600)"},
                "limit": {"type": "INTEGER", "description": "Max entradas del diario a mostrar (default 10)"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14J: AI Features ──

    {
        "name": "emotional_state",
        "description": "Consulta o ajusta tu estado emocional interno (energía, felicidad, etc.). Acciones: status (ver estado y mood), adjust (modificar una dimensión en un delta).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, adjust"},
                "dimension": {"type": "STRING", "description": "Dimensión a ajustar (para adjust): energy, happiness, etc."},
                "delta": {"type": "NUMBER", "description": "Cantidad a sumar/restar a la dimensión (para adjust, ej: 0.2 o -0.1)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "image_generation",
        "description": "Genera y manipula imagenes con IA. Acciones: generate (crear desde prompt), list (listar generadas), get, delete, upscale (aumentar escala x2), variations (variantes del prompt), batch (generar varias), gallery, download.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "generate, list, get, delete, upscale, variations, batch, gallery, download"},
                "prompt": {"type": "STRING", "description": "Descripcion de la imagen (para generate/variations)"},
                "prompts": {"type": "STRING", "description": "Lista de prompts para generar en lote (JSON, para batch)"},
                "style": {"type": "STRING", "description": "Estilo: default, realistic, anime, etc. (default default)"},
                "width": {"type": "INTEGER", "description": "Ancho en px (default 512)"},
                "height": {"type": "INTEGER", "description": "Alto en px (default 512)"},
                "scale": {"type": "INTEGER", "description": "Factor de escala para upscale (default 2)"},
                "seed": {"type": "INTEGER", "description": "Semilla para reproducibilidad"},
                "provider": {"type": "STRING", "description": "Proveedor de generacion: auto, pollinations, etc. (default auto)"},
                "count": {"type": "INTEGER", "description": "Cantidad de imagenes a generar (max 8, para variations)"},
                "name": {"type": "STRING", "description": "Nombre del archivo/imagen (para list/get/delete/download)"},
                "destination": {"type": "STRING", "description": "Carpeta destino (para download)"},
                "limit": {"type": "INTEGER", "description": "Maximo de items a listar (default 10)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "personality",
        "description": "Motor de personalidad de ERIS: analiza y adapta respuestas segun contexto y tono. Acciones: analyze (analizar text con context/topic), apply, status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, apply, status"},
                "text": {"type": "STRING", "description": "Texto a analizar"},
                "context": {"type": "STRING", "description": "Contexto de la conversacion"},
                "topic": {"type": "STRING", "description": "Tema de la conversacion"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_map",
        "description": "ERIS obtiene su mapa completo de sí misma (arquitectura, módulos, capacidades) — sin parámetros.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": [],
        }
    },

    # ── Knowledge & RAG ──

    {
        "name": "data_connectors",
        "description": "Conectores de datos: SQL, CSV, API, etc. Acciones: connect (conectar), query (consultar), list. Params: query (consulta), limit (max filas).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "connect, query, list"},
                "query": {"type": "STRING", "description": "Consulta SQL o API a ejecutar"},
                "limit": {"type": "INTEGER", "description": "Maximo de filas/resultados (default 100)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "knowledge_ingestor",
        "description": "Ingesta masiva de conocimiento: indexa archivos, URLs y texto directo en la base de conocimiento. Acciones: ingest (indexar archivo/carpeta por path), ingest_url (indexar url), ingest_text (indexar texto con label), status, search.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "ingest, ingest_url, ingest_text, status, search"},
                "path": {"type": "STRING", "description": "Ruta del archivo o carpeta a indexar (para ingest)"},
                "url": {"type": "STRING", "description": "URL a indexar (para ingest_url)"},
                "text": {"type": "STRING", "description": "Texto a indexar (para ingest_text)"},
                "label": {"type": "STRING", "description": "Etiqueta del texto indexado (default direct_input)"},
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
                "description": {"type": "STRING", "description": "Alias de goal"},
                "plan_id": {"type": "STRING", "description": "ID del plan (para execute/status/cancel)"},
                "max_steps": {"type": "INTEGER", "description": "Máximo de pasos a ejecutar (opcional)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "agent_loop",
        "description": "Motor de agente autónomo de ERIS: descompone un objetivo en pasos, los ejecuta con herramientas, verifica y corrige hasta completarlo. Acciones: run (planificar y ejecutar con 'goal', opcional 'context' y 'max_steps'), plan (solo descomponer en pasos con 'goal'), status (ver ejecuciones recientes).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run | plan | status"},
                "goal": {"type": "STRING", "description": "Objetivo en lenguaje natural a completar"},
                "context": {"type": "STRING", "description": "Contexto adicional (opcional)"},
                "max_steps": {"type": "INTEGER", "description": "Máximo de pasos a ejecutar (default 15)"},
            },
            "required": ["action", "goal"],
        }
    },
    {
        "name": "file_editor",
        "description": "Edición quirúrgica y búsqueda avanzada de archivos. Acciones: read (leer archivo/directorio con 'path', 'offset', 'limit', 'base_path'), write (escribir con 'path'+'content', backup y diff), edit (reemplazo UNICO de 'old_text'→'new_text' con verificación de ambigüedad, falla si no es único), grep (regex 'pattern' en 'base_path' con 'ignore_case' y 'max_files'), glob (recursivo 'glob_pattern' en 'base_path').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read | write | edit | grep | glob"},
                "path": {"type": "STRING", "description": "Ruta del archivo/directorio (atajos: desktop, downloads, home)"},
                "content": {"type": "STRING", "description": "Contenido a escribir (para write)"},
                "old_text": {"type": "STRING", "description": "Fragmento exacto a reemplazar (para edit, debe ser único)"},
                "new_text": {"type": "STRING", "description": "Reemplazo (para edit)"},
                "pattern": {"type": "STRING", "description": "Expresión regular a buscar (para grep)"},
                "glob_pattern": {"type": "STRING", "description": "Patrón glob recursivo (ej: **/*.py) para glob"},
                "base_path": {"type": "STRING", "description": "Directorio base para grep/glob (default: actual)"},
                "offset": {"type": "INTEGER", "description": "Línea inicial (1-based) para read"},
                "limit": {"type": "INTEGER", "description": "Máximo de líneas para read"},
                "ignore_case": {"type": "BOOLEAN", "description": "Ignorar mayúsculas en grep (default true)"},
                "max_files": {"type": "INTEGER", "description": "Máximo de archivos a escanear en grep (default 500)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "multi_search",
        "description": "Búsqueda web multi-fuente: consulta Google y DuckDuckGo, extrae las páginas más relevantes y consolida un resumen con LLM. Params: query (obligatorio), num_results (páginas a extraer, default 3), summarize (bool, default true), action (search | sources).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search | sources"},
                "query": {"type": "STRING", "description": "Consulta a buscar"},
                "num_results": {"type": "INTEGER", "description": "Número de páginas a extraer (default 3)"},
                "summarize": {"type": "BOOLEAN", "description": "Consolidar con LLM (default true)"},
            },
            "required": ["query"],
        }
    },
    {
        "name": "code_validator",
        "description": "Auto-validación de código tras cambios. Acciones: validate (py_compile de 'path' o pytest de 'repo'), fix (corrige en bucle 'path'/'repo' con LLM hasta que pase, 'max_fixes' intentos), status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "validate | fix | status"},
                "path": {"type": "STRING", "description": "Archivo .py a compilar"},
                "repo": {"type": "STRING", "description": "Directorio con tests/ para pytest"},
                "goal": {"type": "STRING", "description": "Contexto del objetivo (para la corrección LLM)"},
                "max_fixes": {"type": "INTEGER", "description": "Intentos de corrección (default 3)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "parallel_agents",
        "description": "Ejecuta varias tareas en paralelo con subagentes independientes (threads). Params: tasks (lista de tareas o texto con una por línea), max_workers (default 3), max_iter (iteraciones por subagente, default 6).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tasks": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Tareas a resolver en paralelo"},
                "max_workers": {"type": "INTEGER", "description": "Hilos simultáneos (default 3)"},
                "max_iter": {"type": "INTEGER", "description": "Iteraciones máximas por subagente (default 6)"},
            },
            "required": ["tasks"],
        }
    },
    {
        "name": "workflow_runner",
        "description": "Ejecuta flujos de trabajo reutilizables (JSON en data/workflows/) encadenando tools existentes. Acciones: run (ejecutar workflow por 'name', con 'inputs'/'vars' opcionales), list/status (workflows disponibles), save (guardar con 'data' JSON {name, description, steps, on_error}), delete (borrar por 'name'), show (ver definicion), example (crear workflows de ejemplo: briefing_matutino, estado_sistema, mantenimiento). Cada paso: {tool, params, label, retries, if, parallel/tasks}. Variables {{var}}, {{step.N.salida}}, {{env.VAR}}.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run, list, status, save, delete, show, example"},
                "name": {"type": "STRING", "description": "Nombre del workflow"},
                "data": {"type": "STRING", "description": "JSON del workflow (para save/run inline)"},
                "workflow": {"type": "STRING", "description": "Alias de data"},
                "inputs": {"type": "OBJECT", "description": "Variables a inyectar en el workflow"},
                "vars": {"type": "OBJECT", "description": "Alias de inputs"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "git_daily",
        "description": "Flujo git diario con convención de commits. Acciones: status (corto), diff (--stat, 'full'=true para detalle), commit (stage todo + 'message' o mensaje convencional auto-inferido; 'verify'=true hace py_compile previo), sync (commit + pull --rebase + push), log (últimos 15), branch (ramas). 'path' es el repo (default: el de ERIS).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | diff | commit | sync | log | branch"},
                "path": {"type": "STRING", "description": "Ruta del repo git (default: ERIS)"},
                "message": {"type": "STRING", "description": "Mensaje del commit (opcional; si no, se infiere)"},
                "verify": {"type": "BOOLEAN", "description": "py_compile previo al commit (default true)"},
                "full": {"type": "BOOLEAN", "description": "Diff completo en vez de --stat (default false)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_regression",
        "description": "Auto-regresión integral de ERIS: compila todos los .py del proyecto, corre pytest y audita la alineación A/B de las herramientas. Acciones: run (ejecuta todo y guarda informe), status (último informe).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run | status"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_extend",
        "description": "Loop seguro de auto-extension: implementa, registra y valida tools auto-generadas. Acciones: status (tools activas), implement (crear tool con tool_name + python_code, valida py_compile y sandbox), register (registrar en tool_registry/action_imports/tool_declarations), verify (correr self_regression completa), revert (desregistrar y restaurar backups), extend (ciclo completo implementar -> registrar -> verificar, con revert automatico si algo falla). Params: tool_name, python_code, description, parameters_schema (dict), test_parameters (dict), declaration (dict opcional).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | implement | register | verify | revert | extend"},
                "tool_name": {"type": "STRING", "description": "Nombre de la tool a crear/registrar"},
                "python_code": {"type": "STRING", "description": "Codigo Python de la tool (funcion <tool_name>(parameters, player=None) -> str)"},
                "description": {"type": "STRING", "description": "Descripcion de la tool"},
                "parameters_schema": {"type": "OBJECT", "description": "Schema de parametros (dict de propiedades)"},
                "test_parameters": {"type": "OBJECT", "description": "Parametros de prueba para el sandbox"},
                "declaration": {"type": "OBJECT", "description": "Declaracion completa (opcional, si no se construye del schema)"},
                "module": {"type": "STRING", "description": "Modulo de registro (default actions.<tool_name>)"},
                "func": {"type": "STRING", "description": "Nombre de la funcion (default = tool_name)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "dependency_manager",
        "description": "Gestión de dependencias. Acciones: scan (detecta imports rotos en el proyecto), install (instala 'packages', lista o texto), auto (scan + instala los faltantes).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan | install | auto"},
                "packages": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Paquetes a instalar (para install)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "tool_benchmark",
        "description": "Benchmark de herramientas de ERIS: mide tiempos de respuesta de 'tools' (lista de nombres o 'all') y guarda ranking. Acciones: run (medir), status (ranking guardado). 'iterations' repeticiones (default 1).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run | status"},
                "tools": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Tools a medir (default: todas las de ejemplo)"},
                "iterations": {"type": "INTEGER", "description": "Repeticiones por tool (default 1)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "context_read",
        "description": "Lee el contexto actual de Eris (AGENTS.md). Acciones: read (AGENTS.md), notes (NOTES.md del proyecto), all (todos los archivos de contexto).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read | notes | all"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "context_update",
        "description": "Actualiza el contexto de Eris. Acciones: persona (actualizar AGENTS.md), learn (registrar aprendizaje), todo (agregar pendiente), done (completar tarea), status (contar pendientes/completadas). Requiere 'content' salvo en status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "persona | learn | todo | done | status"},
                "content": {"type": "STRING", "description": "Texto a registrar en el contexto"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "memory_nudge",
        "description": "Nudges de memoria de Eris. Acciones: now (nudge ahora), history (historial), suggest (sugerencias de mejora), reflect (reflexionar sobre desempeno reciente).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "now | history | suggest | reflect"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "visual_expressions",
        "description": "Expresiones visuales de Eris en pantalla. Acciones: show (mostrar), update (actualizar con 'expression'), hide (ocultar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "show | update | hide"},
                "expression": {"type": "STRING", "description": "Nombre de la expresion (ej: happy, sad, neutral)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "send_sms",
        "description": "Envia un SMS. Requiere 'to' (numero) y 'message'. Usa Twilio o API HTTP configurada.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "to": {"type": "STRING", "description": "Numero de destino, ej: +56912345678"},
                "message": {"type": "STRING", "description": "Texto del mensaje"},
            },
            "required": ["to", "message"],
        }
    },
    {
        "name": "sms_status",
        "description": "Estado del servicio SMS: Twilio activo, HTTP configurado, o sin configurar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "game_agent",
        "description": "Agente autonomo de juego: analiza la pantalla, controla el personaje, explora, pelea. Acciones: analyze (describir que juego/que ve el jugador), play (ejecutar 'instructions' por 'steps' pasos), look_around (girar 360°), explore (explorar), seek (buscar 'target' en pantalla), navigate (ir a 'destination'), status. Requiere el juego en foco.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze | play | look_around | explore | seek | navigate | status"},
                "game": {"type": "STRING", "description": "Nombre del juego"},
                "instructions": {"type": "STRING", "description": "Que debe hacer el agente (para play)"},
                "steps": {"type": "INTEGER", "description": "Pasos a ejecutar (default 1)"},
                "target": {"type": "STRING", "description": "Objeto/elemento a buscar en pantalla (para seek)"},
                "destination": {"type": "STRING", "description": "Lugar al que navegar (para navigate)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "shell_executor",
        "description": "Ejecuta comandos reales de terminal (bash en Linux, CMD/PowerShell en Windows), con sesion PERSISTENTE: el 'cd' se mantiene entre llamadas. Acciones: run, run_cmd, run_ps, elevated (sudo/admin), open (abrir app/carpeta/URL con xdg-open o start), preview (HTML en navegador), win_r (solo Windows), shell_execute, list_history, clear, info, session_info, session_reset. Eris puede moverse por carpetas, leer/escribir/borrar archivos e instalar programas (apt/pip/npm) desde aqui. Parametros: command, target, shell (bash|powershell|cmd, auto en Linux), timeout (max 120), elevated/admin.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run | run_cmd | run_ps | elevated | open | win_r | shell_execute | preview | list_history | clear | info | session_info | session_reset"},
                "command": {"type": "STRING", "description": "Comando a ejecutar"},
                "cmd": {"type": "STRING", "description": "Alias de command"},
                "target": {"type": "STRING", "description": "App/carpeta/URL/archivo a abrir (para open/win_r/shell_execute/preview)"},
                "shell": {"type": "STRING", "description": "auto (default) | bash | powershell | cmd"},
                "timeout": {"type": "INTEGER", "description": "Timeout en segundos (max 120, default 30)"},
                "elevated": {"type": "BOOLEAN", "description": "Ejecutar elevado (sudo en Linux, admin UAC en Windows)"},
                "admin": {"type": "BOOLEAN", "description": "Alias de elevated"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "daily_health_report",
        "description": "Reporte diario de salud de ERIS: ejecuta self_regression (compile + pytest + auditoría A/B), tool_benchmark (tiempos de tools) y git_daily (estado del repo), y guarda el resumen. Acciones: run (ejecutar todo), status (último reporte). 'git' es el repo (default: ERIS).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run | status"},
                "git": {"type": "STRING", "description": "Repo git a revisar (default: ERIS)"},
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
        "description": "Muestra el estado del ruteo de modelos (Gemini/Groq/Cerebras/OpenRouter/Ollama) — sin parámetros.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "tts_set_voice",
        "description": "Configura el motor de texto a voz: selecciona voz, ajusta velocidad, cambia backend. Acciones: list_voices, set_voice, set_speed, set_backend, elevenlabs_voices, elevenlabs_set_voice.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list_voices, set_voice, set_speed, set_backend, elevenlabs_voices, elevenlabs_set_voice"},
                "voice": {"type": "STRING", "description": "Nombre de la voz (para set_voice)"},
                "speed": {"type": "NUMBER", "description": "Velocidad: 0.5 a 2.0 (default 1.0)"},
                "backend": {"type": "STRING", "description": "Backend: edge, gemini, sapi, elevenlabs, kokoro, bark"},
                "voice_id": {"type": "STRING", "description": "Voice ID de ElevenLabs (para elevenlabs_set_voice)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_recognition",
        "description": "Gestion del reconocimiento de voz de ERIS. Acciones: enroll (registrar voz), verify (verificar), status, reset, threshold. Params: action, value (valor del threshold).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "enroll, verify, status, reset, threshold"},
                "value": {"type": "NUMBER", "description": "Valor del umbral (para action=threshold)"},
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
                "name": {"type": "STRING", "description": "Skill name (igual que skill, acepta ambos)"},
                "content": {"type": "STRING", "description": "Contenido del SKILL.md (para create)"},
                "category": {"type": "STRING", "description": "Categoría de la skill (para create, default general)"},
                "old_string": {"type": "STRING", "description": "Texto a buscar (para patch)"},
                "new_string": {"type": "STRING", "description": "Texto de reemplazo (para patch)"},
            },
            "required": ["action"],
        }
    },

    # ── Browser & Files ──

    {
        "name": "browser_control",
        "description": "Automatizacion de navegador: navegar, buscar, hacer clic, leer paginas, hacer scroll, resultados de busqueda, clic por coordenadas. Acciones: go_to (ir a url), search (buscar en buscador), new_tab, close_tab, scroll (direction=up|down, amount), read_page (leer contenido, max_chars, scrolls), click_element (description=descripcion del elemento), click_coords (x,y), go_back, play_pause, scan_results (leer resultados de busqueda).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "go_to, search, new_tab, close_tab, scroll, read_page, click_element, click_coords, go_back, play_pause, scan_results"},
                "url": {"type": "STRING", "description": "URL a navegar (go_to)"},
                "query": {"type": "STRING", "description": "Texto de busqueda (search)"},
                "direction": {"type": "STRING", "description": "up, down (scroll)"},
                "amount": {"type": "INTEGER", "description": "Cantidad de scroll (default 25-30)"},
                "description": {"type": "STRING", "description": "Descripcion del elemento a hacer clic (click_element)"},
                "index": {"type": "INTEGER", "description": "Indice del resultado (default 1)"},
                "max_chars": {"type": "INTEGER", "description": "Maximo de caracteres a leer (default 8000)"},
                "scrolls": {"type": "INTEGER", "description": "Pasadas de scroll para leer (default 5)"},
                "x": {"type": "INTEGER", "description": "Coordenada X del clic (click_coords)"},
                "y": {"type": "INTEGER", "description": "Coordenada Y del clic (click_coords)"},
                "site": {"type": "STRING", "description": "Sitio de busqueda: google (default) u otro"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_controller",
        "description": "File CRUD, read fragmentado (offset/limit), grep con file:line, glob por nombre, find, organize, disk usage, journal (bitácora de ediciones)",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create_folder, create_file, read, write, append, delete, move, copy, rename, list, grep, glob, journal, find, search, info, compress, extract"},
                "path": {"type": "STRING", "description": "Full path to file or folder. Can be anywhere on the PC. Examples: 'C:\\Users\\danie\\Desktop\\mi_doc.docx', 'D:\\Data'"},
                "content": {"type": "STRING", "description": "Content for write/append"},
                "destination": {"type": "STRING", "description": "Destination path"},
                "pattern": {"type": "STRING", "description": "Pattern for grep (regex, devuelve SOLO las líneas que coinciden con file:line). Para leer un archivo grande, mejor que offset/limit"},
                "glob_pattern": {"type": "STRING", "description": "Patrón glob recursivo para buscar archivos por nombre (ej: **/*.py, **/*.log). Acción: glob"},
                "offset": {"type": "INTEGER", "description": "Número de línea desde donde leer (1-based). Para leer archivos grandes por partes"},
                "limit": {"type": "INTEGER", "description": "Cantidad de líneas a leer (default 50 con offset). Sin offset/limit lee las primeras 250 líneas"},
                "count": {"type": "INTEGER", "description": "Cantidad de items (list/largest) o de entradas de bitácora (journal)"},
                "new_name": {"type": "STRING", "description": "Nuevo nombre para rename/move"},
                "name": {"type": "STRING", "description": "Nombre del archivo a buscar (find)"},
                "extension": {"type": "STRING", "description": "Extensión a filtrar en find (ej: .py)"},
                "old_text": {"type": "STRING", "description": "Texto a reemplazar (edit)"},
                "new_text": {"type": "STRING", "description": "Texto de reemplazo (edit)"},
                "mode": {"type": "STRING", "description": "Modo de edit: replace, append, insert_before, insert_after (default replace)"},
                "confirm": {"type": "BOOLEAN", "description": "Confirmación para delete"},
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
                "args": {"type": "STRING", "description": "Argumentos extra para el programa/instalador"},
                "password": {"type": "STRING", "description": "Contrasena (si el instalador la requiere)"},
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
            },
            "required": ["action"],
        }
    },
    {
        "name": "youtube_video",
        "description": "Play/search YouTube videos. Acciones: play (query), play_direct (video_id), play_url (url), search (query, count).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play, play_direct, play_url, search"},
                "query": {"type": "STRING", "description": "Search term"},
                "video_id": {"type": "STRING", "description": "YouTube video ID"},
                "url": {"type": "STRING", "description": "URL directa del video"},
                "count": {"type": "INTEGER", "description": "Cantidad de resultados (default 5)"},
            },
            "required": ["action"],
        }
    },

    # ── MCP ──

    {
        "name": "mcp_tool",
        "description": "Interfaz al Model Context Protocol (MCP): conecta servidores MCP, lista sus herramientas, y ejecuta llamadas a herramientas de un servidor. Acciones: add_server (conectar servidor: name/server, command, args), remove_server (server), list (listar servidores), tools (listar tools de un server), call (llamar tool de un server: server, tool, args), start, stop.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add_server, remove_server, list, tools, call, start, stop"},
                "server": {"type": "STRING", "description": "Nombre del servidor MCP"},
                "command": {"type": "STRING", "description": "Comando para iniciar el servidor (para add_server)"},
                "args": {"type": "STRING", "description": "Argumentos del comando o argumentos de la llamada (JSON)"},
                "tool": {"type": "STRING", "description": "Nombre de la herramienta MCP a llamar/listar"},
            },
            "required": ["action"],
        }
    },

    # ── Autonomous Learning ──

    {
        "name": "autonomous_learner",
        "description": "Aprendizaje autonomo: estudia temas, guarda conocimiento y resume. Acciones: study (estudiar un topic), summary (resumen), status. Params: topic, context, max_topics.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "study, summary, status"},
                "topic": {"type": "STRING", "description": "Tema a estudiar"},
                "context": {"type": "STRING", "description": "Contexto o pregunta del usuario (opcional)"},
                "max_topics": {"type": "INTEGER", "description": "Maximo de temas a procesar (default 3)"},
            },
            "required": ["action"],
        }
    },

    # ── Training ──

    {
        "name": "curiosity_engine",
        "description": "Cuenta un dato curioso; opcionalmente filtrado por tema.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {"type": "STRING", "description": "Tema del dato curioso (opcional)"},
            },
            "required": [],
        }
    },
    {
        "name": "task_planner",
        "description": "Planificador multi-paso: descompone una meta en pasos ejecutables, los ejecuta con reintentos y persiste el plan",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, status, run, list"},
                "goal": {"type": "STRING", "description": "Meta a planificar/ejecutar"},
                "plan_id": {"type": "STRING", "description": "ID del plan guardado (status/run)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "training_pipeline",
        "description": "Interface de entrenamiento de ERIS: ver estado del entrenamiento, registrar errores con solucion y metricas de llamadas a herramientas. Acciones: status (ver estado), log_error (registrar error + solucion), log_tool_call (registrar llamada a tool), stats (metricas).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, log_error, log_tool_call, stats"},
                "module": {"type": "STRING", "description": "Modulo implicado en el error (para log_error)"},
                "error": {"type": "STRING", "description": "Descripcion del error (para log_error)"},
                "solution": {"type": "STRING", "description": "Solucion aplicada (para log_error)"},
                "tool_calls": {"type": "STRING", "description": "Lista de llamadas de herramientas (JSON, para log_tool_call)"},
                "duration": {"type": "NUMBER", "description": "Duracion de la llamada en segundos (para log_tool_call)"},
            },
            "required": ["action"],
        }
    },

    # ── Updater ──

    {
        "name": "eris_update",
        "description": "Verifica si hay una nueva version de ERIS en GitHub Releases (sin parámetros).",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": [],
        }
    },

    # ── Section 14M: New 16 Features (Jul 2026) ──

    {
        "name": "api_server",
        "description": "API Server para ERIS: levanta un servidor HTTP que expone las herramientas. Acciones: status (estado), start (iniciar), stop (detener), api_key (crear/revocar claves), config (actualizar config), log (ver log), stats, test (probar endpoint).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, start, stop, api_key, config, log, stats, test"},
                "host": {"type": "STRING", "description": "Host del servidor (default 127.0.0.1)"},
                "port": {"type": "INTEGER", "description": "Puerto del servidor (default 8080)"},
                "name": {"type": "STRING", "description": "Nombre de la API key (para api_key)"},
                "permissions": {"type": "STRING", "description": "Permisos de la API key: chat, status (JSON)"},
                "endpoint": {"type": "STRING", "description": "Endpoint a probar (default /health, para test)"},
                "limit": {"type": "INTEGER", "description": "Maximo de entradas del log (default 20)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "browser_extension",
        "description": "Conexion con el navegador via extension: lista pestanas, navega, obtiene contenido, ejecuta JS, busca historial. Acciones: status, list_tabs, get_active_tab, navigate, get_page_content, execute_js, search_history, screenshot.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, list_tabs, get_active_tab, navigate, get_page_content, execute_js, search_history, screenshot"},
                "port": {"type": "INTEGER", "description": "Puerto de conexion (default 8765)"},
                "url": {"type": "STRING", "description": "URL a navegar"},
                "query": {"type": "STRING", "description": "Texto a buscar en el historial"},
                "content": {"type": "STRING", "description": "Contenido a inyectar/obtener"},
                "code": {"type": "STRING", "description": "Codigo JS a ejecutar"},
                "tab_id": {"type": "STRING", "description": "ID de la pestana"},
                "selector": {"type": "STRING", "description": "Selector CSS del elemento a capturar"},
                "days": {"type": "INTEGER", "description": "Dias de historial (default 7)"},
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
                "action": {"type": "STRING", "description": "list, create, delete, update, find, search"},
                "title": {"type": "STRING", "description": "Titulo del evento"},
                "date": {"type": "STRING", "description": "Fecha. Ej: '2026-07-30' o 'manana'"},
                "start": {"type": "STRING", "description": "Fecha/hora de inicio ISO. Alias de date"},
                "end": {"type": "STRING", "description": "Fecha/hora de fin ISO. Si falta, se calcula con duration"},
                "duration": {"type": "INTEGER", "description": "Duracion en minutos (default 60)"},
                "duration_hours": {"type": "NUMBER", "description": "Duracion en horas (alias de duration)"},
                "description": {"type": "STRING", "description": "Descripcion del evento"},
                "location": {"type": "STRING", "description": "Ubicacion del evento"},
                "reminder_minutes": {"type": "INTEGER", "description": "Minutos de anticipacion del recordatorio (default 15)"},
                "recurring": {"type": "STRING", "description": "Regla de recurrencia (ej: 'daily', 'weekly')"},
                "tags": {"type": "STRING", "description": "Etiquetas del evento"},
                "priority": {"type": "STRING", "description": "Prioridad: alta, normal, baja (default normal)"},
                "limit": {"type": "INTEGER", "description": "Maximo de eventos a listar (default 10)"},
                "query": {"type": "STRING", "description": "Texto de busqueda (para search)"},
                "event_id": {"type": "STRING", "description": "ID del evento (para delete/update)"},
                "calendar_id": {"type": "STRING", "description": "ID del calendario (default primary, para Google Calendar)"},
                "client_id": {"type": "STRING", "description": "Client ID OAuth de Google Calendar"},
                "client_secret": {"type": "STRING", "description": "Client Secret OAuth de Google Calendar"},
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
                "content": {"type": "STRING", "description": "Texto a copiar (para copy)"},
                "query": {"type": "STRING", "description": "Texto a buscar en el historial (para search)"},
                "index": {"type": "INTEGER", "description": "Indice en el historial (para paste)"},
                "limit": {"type": "INTEGER", "description": "Maximo de entradas a listar (default 10)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "data_encryption",
        "description": "Cifrado de datos y archivos: cifrar/descifrar texto o archivos con AES, gestionar claves y verificar hashes. Acciones: encrypt_text, decrypt_text, encrypt_file, decrypt_file, generate_key, keys (listar claves), hash (calcular hash de un texto).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "encrypt_text, decrypt_text, encrypt_file, decrypt_file, generate_key, keys, hash"},
                "text": {"type": "STRING", "description": "Texto a cifrar/descifrar o a verificar hash"},
                "filepath": {"type": "STRING", "description": "Ruta del archivo a cifrar/descifrar"},
                "name": {"type": "STRING", "description": "Nombre del dato/clave (para encrypt/generate_key/keys)"},
                "output": {"type": "STRING", "description": "Ruta de salida del archivo descifrado"},
                "key": {"type": "STRING", "description": "Nueva clave (para generate_key)"},
                "algorithm": {"type": "STRING", "description": "Algoritmo de hash: sha256, md5, sha1 (default sha256)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "federated_learning",
        "description": "Aprendizaje federado local: entrena modelos con datos locales, agrega patrones, evalua y guarda modelos. Acciones: status (estado), train (entrenar con data), classify (clasificar input), patterns (ver patrones), evaluate (evaluar con test_data), save (guardar modelo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, train, classify, patterns, evaluate, save"},
                "data": {"type": "STRING", "description": "Datos de entrenamiento (JSON)"},
                "category": {"type": "STRING", "description": "Categoria del modelo (default general)"},
                "epochs": {"type": "INTEGER", "description": "Numero de epocas (default 10)"},
                "input": {"type": "STRING", "description": "Entrada a clasificar (para classify)"},
                "patterns": {"type": "STRING", "description": "Patrones adicionales (JSON)"},
                "test_data": {"type": "STRING", "description": "Datos de prueba (JSON, para evaluate)"},
                "limit": {"type": "INTEGER", "description": "Maximo de patrones a listar (default 20)"},
                "filepath": {"type": "STRING", "description": "Ruta del modelo a guardar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "flow_recorder",
        "description": "Grabador de flujos/macros de acciones. Acciones: list (listar macros), start (iniciar grabacion), stop (detener y guardar), play (reproducir macro), record_manual (crear macro manual), delete, rename, export.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, start, stop, play, record_manual, delete, rename, export"},
                "name": {"type": "STRING", "description": "Nombre de la macro"},
                "new_name": {"type": "STRING", "description": "Nuevo nombre (para rename)"},
                "speed": {"type": "NUMBER", "description": "Velocidad de reproduccion (default 1.0)"},
                "repeat": {"type": "INTEGER", "description": "Cantidad de repeticiones (default 1)"},
                "delay": {"type": "NUMBER", "description": "Delay entre acciones en segundos (default 0.5)"},
                "actions": {"type": "STRING", "description": "Acciones de la macro (JSON, para record_manual)"},
                "type": {"type": "STRING", "description": "Tipo de accion: wait, click, etc."},
            },
            "required": ["action"],
        }
    },
    {
        "name": "multi_user",
        "description": "Gestion de usuarios/perfiles de ERIS. Acciones: list (listar perfiles), create (crear perfil), switch (cambiar perfil), delete (eliminar), rename, set_preferences, import_data, export_data.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, create, switch, delete, rename, set_preferences, import_data, export_data"},
                "name": {"type": "STRING", "description": "Nombre del perfil"},
                "display_name": {"type": "STRING", "description": "Nombre visible del perfil"},
                "language": {"type": "STRING", "description": "Idioma del perfil (default es)"},
                "personality": {"type": "STRING", "description": "Personalidad: amigable, formal, etc. (default amigable)"},
                "greeting": {"type": "STRING", "description": "Saludo personalizado del perfil"},
                "timezone": {"type": "STRING", "description": "Zona horaria (default America/Bogota)"},
                "preferences": {"type": "STRING", "description": "Preferencias del perfil (JSON, para set_preferences)"},
                "source": {"type": "STRING", "description": "Ruta de origen (para import_data)"},
                "target": {"type": "STRING", "description": "Ruta de destino (para export_data)"},
                "filepath": {"type": "STRING", "description": "Ruta de archivo (para export_data/import_data)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "screenshot_history",
        "description": "Historial de capturas de pantalla: captura, busca por texto, etiqueta, compara. Acciones: capture (tomar captura), search (buscar en historial), list (listar capturas), tag (etiquetar captura), compare (comparar dos capturas), delete (eliminar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "capture, search, list, tag, compare, delete"},
                "query": {"type": "STRING", "description": "Texto a buscar en las capturas (para search)"},
                "name": {"type": "STRING", "description": "Nombre de la captura (para capture/list/tag/delete)"},
                "name1": {"type": "STRING", "description": "Primera captura a comparar (para compare)"},
                "name2": {"type": "STRING", "description": "Segunda captura a comparar (para compare)"},
                "tags": {"type": "STRING", "description": "Etiquetas separadas por coma (para tag)"},
                "notes": {"type": "STRING", "description": "Notas de la captura (para tag)"},
                "region": {"type": "STRING", "description": "Region: screen, window, o 'x1,y1,x2,y2' (para capture)"},
                "days": {"type": "INTEGER", "description": "Dias hacia atras (default 30, para list)"},
                "limit": {"type": "INTEGER", "description": "Maximo de capturas a listar (default 10)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "skill_marketplace",
        "description": "Marketplace de skills: buscar, instalar, crear, publicar y valorar skills. Acciones: search (buscar), list (listar por categoria), install (instalar), create (crear skill), publish (publicar), uninstall (desinstalar), rate (valorar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search, list, install, create, publish, uninstall, rate"},
                "query": {"type": "STRING", "description": "Texto de busqueda (para search)"},
                "category": {"type": "STRING", "description": "Categoria: general, dev, creative, productivity, etc. (default general)"},
                "name": {"type": "STRING", "description": "Nombre del skill (para install/create/publish/uninstall/rate)"},
                "description": {"type": "STRING", "description": "Descripcion del skill (para create)"},
                "version": {"type": "STRING", "description": "Version del skill (default 1.0)"},
                "author": {"type": "STRING", "description": "Autor del skill (default ERIS_user)"},
                "tags": {"type": "STRING", "description": "Etiquetas del skill (lista JSON)"},
                "actions": {"type": "STRING", "description": "Acciones del skill (lista JSON, para create)"},
                "code": {"type": "STRING", "description": "Codigo Python del skill (para create)"},
                "config": {"type": "STRING", "description": "Configuracion por defecto del skill (JSON)"},
                "rating": {"type": "NUMBER", "description": "Puntuacion 0-5 (para rate)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "smart_notifications",
        "description": "Notificaciones inteligentes: crear, listar, agendar y gestionar por prioridad. Acciones: list (listar), create (crear), schedule (agendar), dismiss (descartar), stats (estadisticas por categoria/prioridad), silent (silencio por horas).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, create, schedule, dismiss, stats, silent"},
                "title": {"type": "STRING", "description": "Titulo de la notificacion"},
                "message": {"type": "STRING", "description": "Mensaje de la notificacion"},
                "priority": {"type": "STRING", "description": "Prioridad: alta, normal, baja (default normal)"},
                "category": {"type": "STRING", "description": "Categoria: general, system, scheduled (default general)"},
                "context": {"type": "STRING", "description": "Contexto adicional (JSON)"},
                "actions": {"type": "STRING", "description": "Acciones de la notificacion (JSON, lista)"},
                "when": {"type": "STRING", "description": "Cuando agendar (fecha/hora, para schedule)"},
                "hours": {"type": "INTEGER", "description": "Horas de silencio (default 1, para silent)"},
                "days": {"type": "INTEGER", "description": "Dias hacia atras para stats (default 7)"},
                "id": {"type": "STRING", "description": "ID de la notificacion (para dismiss)"},
                "limit": {"type": "INTEGER", "description": "Maximo a listar (default 10)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "usage_analytics",
        "description": "Estadisticas de uso de ERIS: registrar uso de tools, ver resumen, tools mas usadas, actividad por horas, log. Acciones: summary (resumen), record (registrar uso), top_tools, activity (por horas), log (registro reciente), goals (metas de uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "summary, record, top_tools, activity, log, goals"},
                "tool": {"type": "STRING", "description": "Nombre de la tool (para record)"},
                "success": {"type": "BOOLEAN", "description": "Si la llamada fue exitosa (default true)"},
                "duration_ms": {"type": "INTEGER", "description": "Duracion de la llamada en ms (default 0)"},
                "error": {"type": "STRING", "description": "Mensaje de error (si fallo)"},
                "context": {"type": "STRING", "description": "Contexto adicional (JSON)"},
                "session_id": {"type": "STRING", "description": "ID de sesion (default default)"},
                "days": {"type": "INTEGER", "description": "Dias hacia atras para el analisis (default 7)"},
                "hours": {"type": "INTEGER", "description": "Ventana de horas (default 24, para activity)"},
                "limit": {"type": "INTEGER", "description": "Maximo de entradas a mostrar (default 10)"},
                "goals": {"type": "STRING", "description": "Metas de uso (JSON, para goals)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_cloning_new",
        "description": "Clonacion de voz: entrena clon de una voz a partir de muestras de audio, sintetiza texto con la voz clonada y compara voces. Acciones: create (entrenar con muestras), speak (sintetizar con la voz clonada), compare (comparar dos voces), list (listar clones), delete.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, speak, compare, list, delete"},
                "name": {"type": "STRING", "description": "Nombre del clon de voz (default default)"},
                "samples": {"type": "STRING", "description": "Rutas de audio de muestra (JSON, para create)"},
                "audio_path": {"type": "STRING", "description": "Ruta del audio de muestra (para create/speak)"},
                "text": {"type": "STRING", "description": "Texto a sintetizar con la voz clonada (para speak)"},
                "name1": {"type": "STRING", "description": "Primera voz a comparar (para compare)"},
                "name2": {"type": "STRING", "description": "Segunda voz a comparar (para compare)"},
            },
            "required": ["action"],
        }
    },

    # ── Section 14N: Batch 13 New Features (Jul 2026) ──

    {
        "name": "auto_backup",
        "description": "Respaldos automaticos de ERIS: realizar respaldo manual, ver estado y configurar respaldos. Acciones: status (ver estado del ultimo respaldo), backup (ejecutar respaldo), restore (restaurar desde respaldo), config (configurar respaldos).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, backup, restore, config"},
                "set": {"type": "STRING", "description": "Opcion a configurar (para config). Ej: 'destination', 'interval'"},
                "name": {"type": "STRING", "description": "Nombre del respaldo (para restore)"},
                "path": {"type": "STRING", "description": "Ruta del respaldo (para restore)"},
                "type": {"type": "STRING", "description": "Tipo de item: file u otro (default file)"},
                "value": {"type": "STRING", "description": "Valor/configuracion (para config)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "ci_cd",
        "description": "CI/CD pipeline: status, test, lint, typecheck, all, history, install_hooks, git_status, git_diff, git_log",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, test, lint, typecheck, all, history, install_hooks, git_status, git_diff, git_log"},
                "file": {"type": "STRING", "description": "Archivo de test a correr (action=test, default test_all.py)"},
                "target": {"type": "STRING", "description": "Directorio/archivo destino (default .)"},
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
                "path": {"type": "STRING", "description": "Archivo o carpeta a analizar"},
                "target": {"type": "STRING", "description": "Alias de path"},
            },
            "required": ["action", "path"],
        }
    },
    {
        "name": "dashboard_web",
        "description": "Panel web de control de ERIS con chat y quick actions conectados al agente real. Acciones: start (iniciar dashboard en un port), stop, status, get_html, save_html, chat (message), config (port). Endpoints: /api/chat (POST message), /api/tool (POST tool+action), /api/status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, stop, status, get_html, save_html, chat, config"},
                "port": {"type": "INTEGER", "description": "Puerto del dashboard (default 8888)"},
                "message": {"type": "STRING", "description": "Mensaje de estado a mostrar / chat"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "data_viz",
        "description": "Visualizacion de datos con matplotlib/plotly: bar, line, pie, scatter, histogram, table, interactive",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "bar, line, pie, scatter, histogram, table, interactive"},
                "chart_type": {"type": "STRING", "description": "Alias de action (tipo de grafico)"},
                "title": {"type": "STRING", "description": "Titulo del grafico"},
                "labels": {"type": "STRING", "description": "Etiquetas de categorias (lista separada por comas)"},
                "values": {"type": "STRING", "description": "Valores numericos (lista separada por comas)"},
                "x": {"type": "STRING", "description": "Valores del eje X (scatter)"},
                "y": {"type": "STRING", "description": "Valores del eje Y (scatter)"},
                "xlabel": {"type": "STRING", "description": "Etiqueta del eje X"},
                "ylabel": {"type": "STRING", "description": "Etiqueta del eje Y"},
                "bins": {"type": "INTEGER", "description": "Numero de bins para histogram (default 10)"},
                "headers": {"type": "STRING", "description": "Encabezados de columnas para tabla (lista separada por comas)"},
                "rows": {"type": "STRING", "description": "Filas de datos para tabla (JSON o CSV)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "docker_deploy",
        "description": "Despliegue con Docker: build, run, logs, stop. Acciones: build, run, logs, stop, ps. Params: cmd (comando), detach (modo detached), lines (lineas de logs).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "build, run, logs, stop, ps"},
                "cmd": {"type": "STRING", "description": "Comando/argumentos docker a ejecutar"},
                "detach": {"type": "BOOLEAN", "description": "Ejecutar en modo detached (default false)"},
                "lines": {"type": "INTEGER", "description": "Lineas de logs a mostrar (default 20)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "i18n",
        "description": "Internacionalizacion de ERIS: ver idioma actual, cambiar idioma, agregar/editar traducciones y ver textos de la interfaz. Acciones: status, set_language (cambiar idioma), get (ver texto por clave), set (agregar/editar texto), translate (traducir texto).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, set_language, get, set, translate"},
                "language": {"type": "STRING", "description": "Idioma: es, en, etc. (default es)"},
                "key": {"type": "STRING", "description": "Clave de traduccion"},
                "keys": {"type": "STRING", "description": "Lista de claves separadas por coma (para get)"},
                "value": {"type": "STRING", "description": "Valor de traduccion (para set)"},
                "text": {"type": "STRING", "description": "Texto a traducir (para translate)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "i18n_ui",
        "description": "Traducciones de la interfaz de ERIS: ver idioma actual, obtener textos, guardar traducciones personalizadas y listar textos de UI. Acciones: status (idioma actual), get (texto por clave), set (traducir/cambiar un texto), import (cargar traducciones desde data), list (listar textos).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, get, set, import, list"},
                "language": {"type": "STRING", "description": "Idioma: es, en, etc. (default es)"},
                "key": {"type": "STRING", "description": "Clave del texto de UI"},
                "keys": {"type": "STRING", "description": "Lista de claves separadas por coma (para get)"},
                "data": {"type": "STRING", "description": "Traducciones a importar (JSON, para import)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "plugin_marketplace",
        "description": "Marketplace de plugins. Acciones: list (listar plugins), search (buscar con query), install (instalar por name), uninstall.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, search, install, uninstall"},
                "name": {"type": "STRING", "description": "Nombre del plugin a instalar/desinstalar"},
                "query": {"type": "STRING", "description": "Texto de busqueda en el marketplace"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "proactive_ia",
        "description": "Tareas y recordatorios proactivos de ERIS. Acciones: status (resumen), add_task (crear tarea), complete_task, list_tasks, add_reminder (crear recordatorio), check_reminders, suggest (sugerencias), dismiss, watch_file (vigilar archivo), unwatch_file, check_files, analyze, clear_completed, export.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, add_task, complete_task, list_tasks, add_reminder, check_reminders, suggest, dismiss, watch_file, unwatch_file, check_files, analyze, clear_completed, export"},
                "task": {"type": "STRING", "description": "Descripcion de la tarea (para add_task/complete_task)"},
                "priority": {"type": "STRING", "description": "Prioridad: alta, normal, baja (default normal)"},
                "deadline": {"type": "STRING", "description": "Fecha limite de la tarea (YYYY-MM-DD)"},
                "text": {"type": "STRING", "description": "Texto del recordatorio (para add_reminder)"},
                "when": {"type": "STRING", "description": "Cuando disparar el recordatorio (ej: 09:00, 'en 5 minutos')"},
                "index": {"type": "INTEGER", "description": "Numero de la sugerencia a descartar (para dismiss)"},
                "path": {"type": "STRING", "description": "Ruta del archivo a vigilar (para watch_file/unwatch_file)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_cloning_real",
        "description": "Clonacion de voz real con edge-tts: speak (sintetizar texto), voices (listar), set_voice (activa), create (proceso de clonado), history",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "speak, voices, set_voice, create, history"},
                "voice_id": {"type": "STRING", "description": "Identificador de la voz (edge-tts)"},
                "text": {"type": "STRING", "description": "Texto a sintetizar"},
                "texts": {"type": "STRING", "description": "Lista de textos a sintetizar en lote (JSON)"},
                "output": {"type": "STRING", "description": "Archivo de salida (.mp3)"},
                "path": {"type": "STRING", "description": "Ruta del audio a analizar/clonar"},
                "rate": {"type": "STRING", "description": "Velocidad (ej. +0%)"},
                "pitch": {"type": "STRING", "description": "Tono (ej. +0Hz)"},
                "volume": {"type": "STRING", "description": "Volumen (ej. +0%)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_enhanced",
        "description": "Sintesis de voz avanzada con perfiles y wake word: speak, list, create, delete, set (voz activa), wake_word",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "speak, list, create, delete, set, wake_word"},
                "name": {"type": "STRING", "description": "Nombre del perfil de voz"},
                "voice_id": {"type": "STRING", "description": "Identificador de la voz (edge-tts)"},
                "language": {"type": "STRING", "description": "Idioma (default es)"},
                "speed": {"type": "NUMBER", "description": "Velocidad (default 1.0)"},
                "pitch": {"type": "NUMBER", "description": "Tono (default 1.0)"},
                "volume": {"type": "NUMBER", "description": "Volumen (default 1.0)"},
                "wake_word": {"type": "STRING", "description": "Palabra de activacion (default hey eris)"},
                "wake_enabled": {"type": "BOOLEAN", "description": "Activar/desactivar wake word"},
                "word": {"type": "STRING", "description": "Nueva palabra de activacion (action=wake_word)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "web_scraper",
        "description": "Extrae contenido de paginas web: texto, enlaces, imagenes, con Playwright/requests. Acciones: scrape (texto), extract_links, extract_images, extract_text, batch (varias urls), smart (resumen inteligente), search (buscar en la web).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scrape, extract_links, extract_images, extract_text, batch, smart, search"},
                "url": {"type": "STRING", "description": "URL a scrapear"},
                "urls": {"type": "STRING", "description": "Lista de URLs (JSON, para batch)"},
                "selector": {"type": "STRING", "description": "Selector CSS del contenido a extraer"},
                "query": {"type": "STRING", "description": "Termino de busqueda (para search)"},
                "save": {"type": "BOOLEAN", "description": "Guardar el resultado a archivo"},
                "timeout": {"type": "INTEGER", "description": "Timeout en segundos (default 10-30)"},
                "max_chars": {"type": "INTEGER", "description": "Maximo de caracteres a extraer (default 2000-3000)"},
                "num": {"type": "INTEGER", "description": "Cantidad de resultados (default 5, para search)"},
            },
            "required": ["action"],
        }
    },

    # ── Batch 3: 11 new features ──

    {
        "name": "config_export",
        "description": "Exporta o importa la configuracion completa de ERIS (config, memory, knowledge, plugins). Acciones: export (exportar a data/exports, name + include), import (restaurar por name), status, list, diff (diff entre name y compare), delete (name), validate (name), backup (backup completo), restore (restaurar ultimo backup).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "export, import, status, list, diff, delete, validate, backup, restore"},
                "name": {"type": "STRING", "description": "Nombre del archivo de configuracion / backup"},
                "compare": {"type": "STRING", "description": "Export a comparar (para diff)"},
                "include": {"type": "STRING", "description": "Secciones a incluir: all, knowledge, plugins, memory (comma-separated)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "desktop_notifications",
        "description": "Notificaciones de escritorio nativas (Windows Toast / Linux notify-send) con prioridades y configuracion. Acciones: send (enviar notificacion), list_history (ver historial), clear (limpiar notificaciones), config (configurar preferencias).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send, list_history, clear, config"},
                "title": {"type": "STRING", "description": "Titulo de la notificacion (default ERIS)"},
                "message": {"type": "STRING", "description": "Cuerpo de la notificacion"},
                "priority": {"type": "STRING", "description": "Prioridad: low, normal, high, critical (default normal)"},
                "category": {"type": "STRING", "description": "Categoria de la notificacion (default general)"},
                "silent": {"type": "BOOLEAN", "description": "Silenciosa (default false)"},
                "notifications": {"type": "STRING", "description": "Lista de notificaciones a limpiar (JSON, para clear)"},
                "id": {"type": "STRING", "description": "ID de la notificacion (para acciones puntuales)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "plugin_loader",
        "description": "Carga y gestion de plugins. Acciones: load (cargar plugin por name), list, unload, reload.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "load, list, unload, reload"},
                "name": {"type": "STRING", "description": "Nombre del plugin a cargar/descargar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "sandbox_execution",
        "description": "Ejecucion segura de codigo en sandbox. Acciones: run_python, run_js, run_snippet, validate, history, status, limits, examples. Params: code (codigo), lang (python, js, snippet), timeout (segundos).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run_python, run_js, run_snippet, validate, history, status, limits, examples"},
                "code": {"type": "STRING", "description": "Codigo a ejecutar"},
                "lang": {"type": "STRING", "description": "Lenguaje: python, js, snippet"},
                "timeout": {"type": "INTEGER", "description": "Timeout en segundos (default 30)"},
            },
            "required": ["action", "code"],
        }
    },
    {
        "name": "smart_cache",
        "description": "Cache inteligente de ERIS: guarda y recupera valores con TTL, elimina claves, ve estadisticas y usa patrones de busqueda. Acciones: status (ver estado), get (obtener valor), set (guardar valor con ttl), delete (eliminar), keys (listar claves), clear (limpiar), search (buscar por patron).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, get, set, delete, keys, clear, search"},
                "key": {"type": "STRING", "description": "Clave del cache"},
                "value": {"type": "STRING", "description": "Valor a guardar (para set)"},
                "ttl": {"type": "INTEGER", "description": "Tiempo de vida en segundos (default DEFAULT_TTL)"},
                "limit": {"type": "INTEGER", "description": "Maximo de claves a listar (default 10)"},
                "pattern": {"type": "STRING", "description": "Patron de busqueda (para search)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "theme_manager",
        "description": "Gestion de temas visuales de ERIS. Acciones: apply (aplicar theme), list (listar temas), default. Params: theme (nombre del tema).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "apply, list, default"},
                "theme": {"type": "STRING", "description": "Nombre del tema a aplicar"},
            },
            "required": ["action"],
        }
    },

    # ── Batch 4: Complete Training — All Missing Tools ──

    {
        "name": "active_firewall",
        "description": "Firewall de red: bloquea/desbloquea IPs o puertos y consulta el estado. Acciones: status (ver estado), block (bloquear ip/puerto con rule_name), unblock (desbloquear), allow (permitir).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, block, unblock, allow"},
                "ip": {"type": "STRING", "description": "IP a bloquear/desbloquear"},
                "port": {"type": "STRING", "description": "Puerto a bloquear/desbloquear"},
                "name": {"type": "STRING", "description": "Nombre de la regla (default ERIS_Block)"},
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
                "name": {"type": "STRING", "description": "Nombre o ID de la alarma"},
                "label": {"type": "STRING", "description": "Alias de name"},
                "alarm_id": {"type": "STRING", "description": "Alias de name (ID de la alarma para cancel/snooze)"},
                "message": {"type": "STRING", "description": "Mensaje al sonar la alarma (default Tiempo cumplido!)"},
                "seconds": {"type": "INTEGER", "description": "Segundos del temporizador (default 0)"},
                "minutes": {"type": "INTEGER", "description": "Minutos del temporizador (default 0)"},
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
                "app_name": {"type": "STRING", "description": "Alias de app (nombre de la aplicacion)"},
                "app_path": {"type": "STRING", "description": "Ruta del instalador local (opcional, para install)"},
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
                "file": {"type": "STRING", "description": "Alias de file_path"},
                "language": {"type": "STRING", "description": "Idioma. Ej: 'es', 'en' (default auto-detect)"},
                "model_size": {"type": "STRING", "description": "Tamano del modelo: tiny, base, small, medium, large (default base)"},
                "model": {"type": "STRING", "description": "Alias de model_size"},
                "duration": {"type": "INTEGER", "description": "Duracion de grabacion en segundos (para transcribe_mic, default 5)"},
                "limit": {"type": "INTEGER", "description": "Maximo de transcripciones a listar (default 20)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "auto_agent",
        "description": "Agente autonomo multi-paso de ERIS: planifica y ejecuta metas automaticamente. Acciones: status (estado), plan (crear plan con goal/description), execute (ejecutar plan con plan_id y max_steps), cancel, history. Tambien puede ejecutar command o code directamente.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, plan, execute, cancel, history, run"},
                "goal": {"type": "STRING", "description": "Meta a lograr (para plan)"},
                "description": {"type": "STRING", "description": "Alias de goal"},
                "plan_id": {"type": "STRING", "description": "ID del plan (para execute/cancel/status)"},
                "max_steps": {"type": "INTEGER", "description": "Maximo de pasos a ejecutar (default todos)"},
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
                "type": {"type": "STRING", "description": "Tipo de respaldo: incremental, full (default incremental)"},
                "name": {"type": "STRING", "description": "Nombre del backup"},
                "source": {"type": "STRING", "description": "Carpeta o archivo a respaldar"},
                "destination": {"type": "STRING", "description": "Destino del backup"},
                "backup1": {"type": "STRING", "description": "Nombre del primer backup (para combinar/restore)"},
                "backup2": {"type": "STRING", "description": "Nombre del segundo backup (para combinar/restore)"},
                "interval": {"type": "STRING", "description": "Intervalo: 'daily', 'weekly', 'hourly' (para schedule)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "browser_history",
        "description": "Historial de navegacion: consulta historial y marcadores de Chrome/Edge, busca por texto y exporta. Acciones: chrome (historial de Chrome), edge (historial de Edge), bookmarks, search (buscar con query), export (exportar con output).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "chrome, edge, bookmarks, search, export"},
                "limit": {"type": "INTEGER", "description": "Maximo de entradas (default 50)"},
                "browser": {"type": "STRING", "description": "Navegador: chrome (default), edge"},
                "query": {"type": "STRING", "description": "Texto a buscar en el historial"},
                "output": {"type": "STRING", "description": "Ruta de exportacion (para export)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "calculator",
        "description": "Calculadora: matematica, conversion de unidades, fechas. Params: expression (expresion matematica o conversion), query/text (alias).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "calculate, convert, date (default auto)"},
                "expression": {"type": "STRING", "description": "Expresion matematica o conversion a calcular"},
                "query": {"type": "STRING", "description": "Alias de expression (consulta en lenguaje natural)"},
                "text": {"type": "STRING", "description": "Alias de expression"},
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
                "filename": {"type": "STRING", "description": "Alias de file_path (nombre del archivo)"},
                "name": {"type": "STRING", "description": "Alias de file_path (nombre del script)"},
                "script_id": {"type": "STRING", "description": "ID del script (para run/list)"},
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
                "name": {"type": "STRING", "description": "Alias de new_name (action=rename)"},
                "text": {"type": "STRING", "description": "Alias de description (texto de lo que generar/corregir)"},
                "output_path": {"type": "STRING", "description": "Alias de output_dir (carpeta destino)"},
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
        "description": "Motor de contexto de ERIS: analiza el contexto del sistema (aplicaciones activas, comandos recientes), gestiona contexto de sesion. Acciones: analyze (analizar contexto del sistema), get_context/set_context (obtener/guardar contexto), memory (gestor de contexto).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, get_context, set_context, memory"},
                "sub_action": {"type": "STRING", "description": "Sub-accion: get, set (default get)"},
                "recent_commands": {"type": "STRING", "description": "Comandos recientes (JSON) para analizar"},
                "active_apps": {"type": "STRING", "description": "Aplicaciones activas (JSON) para analizar"},
                "limit": {"type": "INTEGER", "description": "Maximo de items (default 20)"},
                "name": {"type": "STRING", "description": "Nombre del contexto"},
                "language": {"type": "STRING", "description": "Idioma actual del sistema"},
                "timezone_offset": {"type": "STRING", "description": "Desplazamiento horario (ej: '-05:00')"},
                "key": {"type": "STRING", "description": "Clave del contexto (para set_context)"},
                "value": {"type": "STRING", "description": "Valor del contexto (para set_context)"},
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
        "description": "Recuperacion EXHAUSTIVA de credenciales en el sistema local. Acciones: scan (escaneo rapido), browsers (contrasenas de Chrome, Edge, Brave, Firefox), wifi (redes WiFi con contrasenas), wifi_detail (detalle de una red), windows_cred (Credential Manager + Vault + Shadow Copies), git (tokens y credenciales), cookies (sesiones importantes), secrets (archivos con secretos), all (escaneo TOTAL), attempt (intentar descifrar un objetivo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan, browsers, wifi, wifi_detail, windows_cred, git, cookies, secrets, all, attempt"},
                "ssid": {"type": "STRING", "description": "Nombre de la red WiFi (para wifi_detail)"},
                "target": {"type": "STRING", "description": "Objetivo: url/ssid/email (para attempt)"},
            },
            "required": ["action"],
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
                "subtopic": {"type": "STRING", "description": "Sub-tema especifico (opcional)"},
                "target": {"type": "STRING", "description": "Host o URL a analizar/escanear"},
                "query": {"type": "STRING", "description": "Consulta de busqueda sobre vulnerabilidades"},
                "count": {"type": "INTEGER", "description": "Cantidad de resultados (default 5)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "darkweb_monitor",
        "description": "Monitoreo de exposicion de datos: verifica si emails o dominios aparecen en filtraciones. Acciones: check (verificar email/domain), add (agregar email/domain a vigilar), remove, list (ver monitoreados).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "check, add, remove, list"},
                "email": {"type": "STRING", "description": "Email a verificar/agregar"},
                "domain": {"type": "STRING", "description": "Dominio a verificar/agregar"},
                "sub_action": {"type": "STRING", "description": "Sub-accion: add (default), remove (para list/editar)"},
                "limit": {"type": "INTEGER", "description": "Maximo de resultados (default 20)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "data_analyst",
        "description": "Analiza archivos CSV o Excel: muestra columnas, estadisticas basicas, filtra datos, genera reportes. Acciones: load (cargar archivo), info (informacion del dataset), stats (estadisticas), filter (filtrar datos), chart (graficar), join (unir dos archivos), export (exportar a JSON).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "load, info, stats, filter, chart, join, export"},
                "file": {"type": "STRING", "description": "Ruta del archivo CSV o Excel (para load)"},
                "file2": {"type": "STRING", "description": "Segundo archivo (para join)"},
                "column": {"type": "STRING", "description": "Nombre de columna para filter/chart/group"},
                "value": {"type": "STRING", "description": "Valor para filtrar"},
                "operator": {"type": "STRING", "description": "Operador de filtro: eq, ne, gt, lt, contains (default eq)"},
                "descending": {"type": "BOOLEAN", "description": "Orden descendente (default false)"},
                "agg_column": {"type": "STRING", "description": "Columna a agregar (para stats/grupo)"},
                "agg_func": {"type": "STRING", "description": "Funcion de agregacion: mean, sum, count (default mean)"},
                "aggfunc": {"type": "STRING", "description": "Alias de agg_func (default mean)"},
                "index": {"type": "STRING", "description": "Columna indice para pivot/table"},
                "columns": {"type": "STRING", "description": "Columnas a mostrar (lista separada por coma)"},
                "values": {"type": "STRING", "description": "Columna de valores (para pivot/table)"},
                "x_column": {"type": "STRING", "description": "Columna X del grafico"},
                "y_column": {"type": "STRING", "description": "Columna Y del grafico"},
                "query": {"type": "STRING", "description": "Consulta de texto libre sobre el dataset"},
                "source": {"type": "STRING", "description": "Ruta de origen (para export)"},
                "output": {"type": "STRING", "description": "Ruta de salida (para export)"},
                "format": {"type": "STRING", "description": "Formato de exportacion: json, csv (default json)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "data_visualize",
        "description": "Genera graficos PNG (bar, line, pie, hist, scatter) desde CSV/Excel/JSON usando PIL. Guarda en data/generated/ y devuelve la ruta + resumen estadistico. Acciones: chart (generar con file, type, x, y, title, color, out), list (graficos generados), open (name: abrir PNG), status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "chart, list, open, status"},
                "file": {"type": "STRING", "description": "Ruta del archivo CSV/Excel/JSON a graficar"},
                "path": {"type": "STRING", "description": "Alias de file"},
                "type": {"type": "STRING", "description": "Tipo de grafico: bar, line, pie, hist, scatter (default bar)"},
                "chart": {"type": "STRING", "description": "Alias de type"},
                "x": {"type": "STRING", "description": "Columna para eje X / categorias / valores"},
                "x_column": {"type": "STRING", "description": "Alias de x"},
                "y": {"type": "STRING", "description": "Columna para eje Y / serie numerica (line, scatter)"},
                "y_column": {"type": "STRING", "description": "Alias de y"},
                "title": {"type": "STRING", "description": "Titulo del grafico"},
                "color": {"type": "STRING", "description": "Color hex del grafico (default #FFC000)"},
                "out": {"type": "STRING", "description": "Nombre del PNG de salida (default auto)"},
                "name": {"type": "STRING", "description": "Nombre del PNG a abrir (para open)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "disk_wiper",
        "description": "Borrado seguro de archivos, carpetas o discos (overwrite con metodo DoD). Acciones: wipe_file (borrar archivo con path), wipe_folder (borrar carpeta), wipe_drive (borrar unidad con drive), info (informacion de disco). Requiere confirm=true para acciones destructivas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wipe_file, wipe_folder, wipe_drive, info"},
                "path": {"type": "STRING", "description": "Ruta del archivo o carpeta a borrar"},
                "drive": {"type": "STRING", "description": "Unidad a borrar (ej: 'D:\\\\')"},
                "confirm": {"type": "BOOLEAN", "description": "Confirmar borrado (default false)"},
                "passes": {"type": "INTEGER", "description": "Pasadas de sobreescritura (default 3)"},
                "method": {"type": "STRING", "description": "Metodo de borrado: dod (default), others"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_generator",
        "description": "Crea, inspecciona y retoma documentos de Word. Acciones: create (crear doc nuevo), check_content (leer doc existente), working_doc (ver doc en progreso), convert (convertir a PDF).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create (new doc), check_content (read doc), working_doc (current doc), convert"},
                "title": {"type": "STRING", "description": "Titulo del documento (para create)"},
                "subtitle": {"type": "STRING", "description": "Subtitulo del documento"},
                "author": {"type": "STRING", "description": "Autor del documento (default ERIS)"},
                "content": {"type": "STRING", "description": "Contenido del documento en markdown (para create)"},
                "full_text": {"type": "STRING", "description": "Alias de content"},
                "sections": {"type": "STRING", "description": "Secciones del documento (JSON, para create)"},
                "output_path": {"type": "STRING", "description": "Ruta o carpeta de guardado. Defaults to Desktop\\ERIS_Documentos."},
                "filename": {"type": "STRING", "description": "Nombre del archivo de salida (opcional)"},
                "convert_pdf": {"type": "BOOLEAN", "description": "Convertir a PDF ademas (default false)"},
                "path": {"type": "STRING", "description": "Ruta del archivo a inspeccionar (para check_content/convert)"},
                "output": {"type": "STRING", "description": "Ruta de salida (para convert)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_manager",
        "description": "Gestiona documentos (PDF, Word, Excel, Text). Acciones: create (crear documento con content y path), read (leer), list. Params: path (ruta), content (contenido).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, read, list"},
                "path": {"type": "STRING", "description": "Ruta del documento"},
                "content": {"type": "STRING", "description": "Contenido del documento (para create)"},
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
                "device": {"type": "STRING", "description": "Nombre del driver (para info)"},
                "method": {"type": "STRING", "description": "Metodo de backup/restore (default pnputil)"},
                "backup_name": {"type": "STRING", "description": "Nombre del respaldo de drivers"},
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
                "action": {"type": "STRING", "description": "status, history, reset"},
            },
            "required": ["action"],
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
                "n": {"type": "INTEGER", "description": "Cantidad (para set_intentos)"},
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
        "description": "Camaras del equipo: detecta camaras conectadas, captura instantaneas y analiza lo que ve con vision. Acciones: info (listar camaras), snapshot/capture (capturar imagen, opcional analyze=true con question).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "info, snapshot, capture"},
                "index": {"type": "INTEGER", "description": "Indice de camara (default 0)"},
                "camera": {"type": "INTEGER", "description": "Alias de index"},
                "cam": {"type": "INTEGER", "description": "Alias de index"},
                "question": {"type": "STRING", "description": "Pregunta sobre la imagen (con analyze=true)"},
                "prompt": {"type": "STRING", "description": "Alias de question"},
                "analyze": {"type": "BOOLEAN", "description": "Analizar la captura con vision"},
                "vision": {"type": "BOOLEAN", "description": "Alias de analyze"},
                "seconds": {"type": "NUMBER", "description": "Segundos de grabacion (default 2)"},
                "time": {"type": "NUMBER", "description": "Alias de seconds"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "document_tool",
        "description": "Trabaja con documentos y archivos: info (metadatos), read (extraer texto), summary, write (crear), edit/replace, append, convert (to_txt), formats. Usala para leer y modificar archivos de ofimática, texto y código. Admite alias en espanol (accion, archivo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "info, read, summary, write, edit, replace, append, to_txt, formats"},
                "accion": {"type": "STRING", "description": "Alias de action (espanol)"},
                "path": {"type": "STRING", "description": "Ruta del archivo"},
                "file": {"type": "STRING", "description": "Alias de path"},
                "archivo": {"type": "STRING", "description": "Alias de path (espanol)"},
                "max_chars": {"type": "INTEGER", "description": "Límite de caracteres a leer (default 150000)"},
                "content": {"type": "STRING", "description": "Contenido para write/append"},
                "text": {"type": "STRING", "description": "Alias de content"},
                "find": {"type": "STRING", "description": "Texto a buscar (para edit)"},
                "replace": {"type": "STRING", "description": "Texto de reemplazo para edit/replace"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "huggingface",
        "description": "Explora Hugging Face: busca modelos y datasets publicos, descarga archivos. Acciones: search_models/models, search_datasets/datasets, top_datasets, download_file.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search_models, models, search_datasets, datasets, top_datasets, download_file"},
                "accion": {"type": "STRING", "description": "Alias de action (espanol)"},
                "query": {"type": "STRING", "description": "Termino de busqueda"},
                "search": {"type": "STRING", "description": "Alias de query"},
                "q": {"type": "STRING", "description": "Alias de query"},
                "limit": {"type": "INTEGER", "description": "Cantidad de resultados (1-20, default 5)"},
                "id": {"type": "STRING", "description": "ID del modelo/dataset (para download_file)"},
                "model_id": {"type": "STRING", "description": "Alias de id (modelo)"},
                "dataset_id": {"type": "STRING", "description": "Alias de id (dataset)"},
                "dataset": {"type": "STRING", "description": "Alias de id (dataset)"},
                "file": {"type": "STRING", "description": "Nombre del archivo a descargar (para download_file)"},
                "filename": {"type": "STRING", "description": "Alias de file"},
                "dest": {"type": "STRING", "description": "Carpeta destino de la descarga"},
                "resource": {"type": "STRING", "description": "Tipo de recurso: model, dataset (opcional)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "reverse_engineering",
        "description": "Analisis local y defensivo de archivos/ejecutables: hashes (MD5/SHA1/SHA256), tipo, cadenas legibles, hexdump, entropia, info PE, desensamblado, busqueda de firmas en directorios y sondeo de endpoints. Uso defensivo (verificar archivos sospechosos). Acciones: file_info/info/hashes, strings/cadenas, hexdump/hex/dump, entropy/entropia, pe/pe_info/peinfo, disassemble/disasm/desensamblar, black_box/probe, search/scan_dir/buscar, triage/analizar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "file_info, info, hashes, strings, cadenas, hexdump, hex, dump, entropy, entropia, pe, pe_info, peinfo, disassemble, disasm, desensamblar, black_box, probe, search, scan_dir, buscar, triage, analizar"},
                "path": {"type": "STRING", "description": "Ruta del archivo, ejecutable o directorio"},
                "file": {"type": "STRING", "description": "Alias de path"},
                "dir": {"type": "STRING", "description": "Alias de directory"},
                "directory": {"type": "STRING", "description": "Directorio a escanear (para search)"},
                "min_length": {"type": "INTEGER", "description": "Longitud minima de cadena (default 4)"},
                "min": {"type": "INTEGER", "description": "Alias de min_length"},
                "pattern": {"type": "STRING", "description": "Filtro regex sobre cadenas"},
                "grep": {"type": "STRING", "description": "Alias de pattern"},
                "signature": {"type": "STRING", "description": "Firma regex a buscar en los archivos (para search)"},
                "ext": {"type": "STRING", "description": "Extension de archivos a filtrar (para search, ej: '.py')"},
                "max_results": {"type": "INTEGER", "description": "Maximo de coincidencias (default 20, para search)"},
                "count": {"type": "INTEGER", "description": "Maximo de cadenas a mostrar (default 60)"},
                "limit": {"type": "INTEGER", "description": "Alias de count"},
                "offset": {"type": "INTEGER", "description": "Desplazamiento en bytes (default 0, para hexdump/disasm)"},
                "length": {"type": "INTEGER", "description": "Cantidad de bytes a volcar (default 128)"},
                "size": {"type": "INTEGER", "description": "Alias de length"},
                "hex": {"type": "STRING", "description": "Bytes en hexadecimal a desensamblar (para disasm)"},
                "base": {"type": "INTEGER", "description": "Direccion base (default 0, para disasm)"},
                "arch": {"type": "STRING", "description": "Arquitectura: x86, x64, arm (default x86, para disasm)"},
                "architecture": {"type": "STRING", "description": "Alias de arch"},
                "url": {"type": "STRING", "description": "URL del endpoint a sondear (para black_box/probe)"},
                "target": {"type": "STRING", "description": "Alias de url (objetivo)"},
                "payloads": {"type": "STRING", "description": "Payloads de prueba (lista separada por coma)"},
                "inputs": {"type": "STRING", "description": "Alias de payloads"},
                "method": {"type": "STRING", "description": "Metodo HTTP: GET, POST (default GET)"},
                "headers": {"type": "STRING", "description": "Cabeceras HTTP extra (JSON)"},
                "allow_remote": {"type": "BOOLEAN", "description": "Permitir IPs remotas (default false)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_evolution",
        "description": "Estado evolutivo de ERIS: reflexiones, lecciones, metas e hitos. Acciones: status (ver evolucion), reflect (reflexionar sobre un tema), lesson (guardar leccion), goal (proponer meta), experience (guardar experiencia).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, reflect, lesson, goal, experience"},
                "text": {"type": "STRING", "description": "Texto de la leccion/meta/experiencia"},
                "lesson": {"type": "STRING", "description": "Alias de text (leccion)"},
                "goal": {"type": "STRING", "description": "Alias de text (meta)"},
                "experience": {"type": "STRING", "description": "Alias de text (experiencia)"},
                "focus": {"type": "STRING", "description": "Tema de la reflexion"},
                "done": {"type": "STRING", "description": "Indica que una meta fue completada"},
                "complete": {"type": "STRING", "description": "Alias de done"},
                "confirm": {"type": "STRING", "description": "Confirmacion: si/yes/1 para acciones destructivas"},
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
                "skill": {"type": "STRING", "description": "Habilidad a practicar: reading, writing, listening, speaking (opcional)"},
                "language": {"type": "STRING", "description": "Idioma de la leccion (default es)"},
                "count": {"type": "INTEGER", "description": "Cantidad de ejercicios/palabras (default 5)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_encryptor",
        "description": "Cifra y descifra archivos con contrasena. Acciones: encrypt (cifrar archivo: path/file + password/key), decrypt (descifrar), status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "encrypt, decrypt, status"},
                "path": {"type": "STRING", "description": "Ruta del archivo a cifrar/descifrar"},
                "file": {"type": "STRING", "description": "Alias de path"},
                "password": {"type": "STRING", "description": "Contrasena de cifrado"},
                "key": {"type": "STRING", "description": "Alias de password"},
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
                "source": {"type": "STRING", "description": "Ruta del archivo o carpeta origen"},
                "path": {"type": "STRING", "description": "Ruta del archivo o carpeta origen (alias de source)"},
                "destination": {"type": "STRING", "description": "Ruta destino (para move/copy)"},
                "dest": {"type": "STRING", "description": "Alias de destination"},
                "pattern": {"type": "STRING", "description": "Patron de busqueda (para search)"},
                "name": {"type": "STRING", "description": "Nombre del archivo (para create_dir/open)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_monitor",
        "description": "Monitor file system changes in real-time. Acciones: start, stop, status. Params: folder (carpeta a vigilar), query (buscar eventos), limit.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, stop, status"},
                "folder": {"type": "STRING", "description": "Carpeta a monitorear"},
                "query": {"type": "STRING", "description": "Buscar eventos que coincidan"},
                "limit": {"type": "INTEGER", "description": "Maximo de eventos a listar (default 20)"},
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
                "answer": {"type": "STRING", "description": "Respuesta del usuario (para trivia)"},
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
                "game": {"type": "STRING", "description": "Nombre del juego (para launch o search)"},
                "name": {"type": "STRING", "description": "Alias de game"},
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
            },
            "required": ["action"],
        }
    },
    {
        "name": "keylogger_detector",
        "description": "Detecta keyloggers y monitorea actividad de teclado. Acciones: scan (escanear), start (iniciar monitoreo), stop, report. Params: limit (max procesos a listar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan, start, stop, report"},
                "limit": {"type": "INTEGER", "description": "Maximo de procesos/resultados (default 50)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "memory_rag",
        "description": "Memoria RAG de ERIS: recuerda/guarda informacion con busqueda semantica, etiquetas y relevancia. Acciones: remember (guardar), recall (recuperar por query), list (listar), forget (eliminar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "remember, recall, list, forget"},
                "content": {"type": "STRING", "description": "Contenido a guardar o recuperar (para remember/recall)"},
                "tags": {"type": "STRING", "description": "Etiquetas (JSON, para remember)"},
                "importance": {"type": "NUMBER", "description": "Importancia 0-1 (default 0.5)"},
                "query": {"type": "STRING", "description": "Consulta de busqueda (para recall/forget)"},
                "limit": {"type": "INTEGER", "description": "Maximo de resultados (default 10)"},
                "sort": {"type": "STRING", "description": "Orden: recent, relevance (default recent)"},
                "memory_id": {"type": "STRING", "description": "ID de la memoria (para forget)"},
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
                "song": {"type": "STRING", "description": "Nombre de la cancion (para play)"},
                "artist": {"type": "STRING", "description": "Artista (para play)"},
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
                "duration": {"type": "INTEGER", "description": "Duracion de monitoreo en segundos (para bandwidth)"},
                "pid": {"type": "INTEGER", "description": "PID del proceso a monitorear (opcional)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "notification_center",
        "description": "Centro de notificaciones de ERIS: enviar notificaciones por distintos metodos (desktop, whatsapp, telegram, etc.), programar notificaciones y ver el historial. Acciones: send (enviar), schedule (programar con delay_seconds), history (ver historial).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send, schedule, history"},
                "title": {"type": "STRING", "description": "Titulo de la notificacion (default Notification)"},
                "message": {"type": "STRING", "description": "Mensaje de la notificacion"},
                "method": {"type": "STRING", "description": "Metodo de envio: desktop, whatsapp, etc. (default desktop)"},
                "delay_seconds": {"type": "INTEGER", "description": "Segundos de espera antes de enviar (default 60, para schedule)"},
                "limit": {"type": "INTEGER", "description": "Maximo de notificaciones del historial (default 20)"},
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
                "path": {"type": "STRING", "description": "Ruta de la imagen a procesar"},
                "image": {"type": "STRING", "description": "Alias de path"},
                "url": {"type": "STRING", "description": "URL de la imagen a procesar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "openrouter_agent",
        "description": "Delega una tarea de texto compleja a OpenRouter (genera textos largos por secciones y guarda resultados extensos).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "La tarea o consulta de texto a delegar"},
            },
            "required": ["query"],
        }
    },
    {
        "name": "osint_agent",
        "description": "Agente de OSINT (Open Source Intelligence) para Eris. Acciones: web (busqueda web general), email (breaches, MX, validacion), username (verificar en multiples plataformas), domain (WHOIS y DNS), ip (geolocalizacion), breach (verificar email en filtraciones), full_report (reporte completo), history (historial).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "web, email, username, domain, ip, breach, full_report, history"},
                "target": {"type": "STRING", "description": "Objetivo: email, username, dominio o IP"},
                "query": {"type": "STRING", "description": "Texto de busqueda (para web)"},
                "count": {"type": "INTEGER", "description": "Cantidad de resultados (default 5)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "pc_control",
        "description": "Controla el PC en acciones SEGURAS que no tocan la energía: volume_up, volume_down, volume_set, mute, unmute, monitor_on, monitor_off, wifi_on, wifi_off, wifi_status, bluetooth_on, bluetooth_off, bluetooth_status, brightness_get, brightness_set, brightness_up, brightness_down, screenshot, lock, status. IMPORTANTE: apagar, suspender, reiniciar, hibernar y cerrar sesion estan DESHABILITADOS por seguridad y devuelven error.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "volume_up, volume_down, volume_set, mute, unmute, monitor_on, monitor_off, wifi_on, wifi_off, wifi_status, bluetooth_on, bluetooth_off, bluetooth_status, brightness_get, brightness_set, brightness_up, brightness_down, screenshot, lock, status"},
                "value": {"type": "STRING", "description": "Valor opcional (ej: nivel de volumen)"},
                "command": {"type": "STRING", "description": "Comando a ejecutar (para acciones tipo volume_set)"},
                "target": {"type": "STRING", "description": "Dispositivo o proceso objetivo (opcional)"},
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
                "path": {"type": "STRING", "description": "Ruta del archivo PDF (alias principal)"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo PDF (alias de path)"},
                "files": {"type": "STRING", "description": "Lista de rutas separadas por coma (para merge)"},
                "output": {"type": "STRING", "description": "Ruta de salida (alias principal)"},
                "output_path": {"type": "STRING", "description": "Ruta de salida (alias de output)"},
                "pages": {"type": "STRING", "description": "Paginas: '1,2,3' o '1-5'"},
                "fields": {"type": "STRING", "description": "Datos del formulario en JSON (para fill_form)"},
                "form_data": {"type": "STRING", "description": "Alias de fields (datos del formulario)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "pdf_manager",
        "description": "Operaciones con PDFs: leer (read), unir (merge), dividir (split), convertir a texto, crear PDF desde texto (create), proteger con contrasena (encrypt), poner marca de agua (watermark), comprimir (compress). Acciones: read, merge, split, convert_to_text, create, encrypt, watermark, compress.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read, merge, split, convert_to_text, create, encrypt, watermark, compress"},
                "file": {"type": "STRING", "description": "Ruta del archivo PDF (o archivo de texto para create)"},
                "files": {"type": "STRING", "description": "Lista de rutas separadas por coma (para merge)"},
                "output": {"type": "STRING", "description": "Ruta de salida del archivo resultante"},
                "output_dir": {"type": "STRING", "description": "Carpeta de salida (para split)"},
                "text": {"type": "STRING", "description": "Texto del PDF a crear (para create) o marca de agua (para watermark)"},
                "password": {"type": "STRING", "description": "Contrasena para proteger el PDF (para encrypt)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "presentation_generator",
        "description": "Genera presentaciones PowerPoint. Acciones: create (crear con title y slides), add_slide. Params: action, title (titulo), slides (JSON), author (autor), subtitle (subtitulo), output_path/filename (ruta de salida).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, add_slide"},
                "title": {"type": "STRING", "description": "Presentation title"},
                "subtitle": {"type": "STRING", "description": "Subtitulo de la presentacion (opcional)"},
                "author": {"type": "STRING", "description": "Autor (default ERIS)"},
                "slides": {"type": "STRING", "description": "JSON array of slide objects with title and content"},
                "output_path": {"type": "STRING", "description": "Path or directory to save. Can be full path like 'C:\\Users\\danie\\Desktop\\pres.pptx' or a directory. Defaults to Desktop\\ERIS_Presentaciones."},
                "filename": {"type": "STRING", "description": "Output filename"},
            },
            "required": ["action", "title", "slides"],
        }
    },
    {
        "name": "process_manager",
        "description": "Lista procesos en ejecucion, busca por nombre, mata procesos por PID o nombre. Acciones: list (top procesos), search (buscar por nombre), kill (matar por PID o nombre), priority (cambiar prioridad), monitor (monitorear en vivo), start (lanzar proceso), watch (vigilar por nombre).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, search, kill, priority, monitor, start, watch"},
                "sub_action": {"type": "STRING", "description": "Sub-accion de monitor: list (default)"},
                "name": {"type": "STRING", "description": "Nombre del proceso (para search, kill, start, watch)"},
                "pid": {"type": "INTEGER", "description": "PID del proceso (para kill o priority)"},
                "command": {"type": "STRING", "description": "Comando a lanzar (para start)"},
                "force": {"type": "BOOLEAN", "description": "Forzar cierre (default false)"},
                "level": {"type": "STRING", "description": "Prioridad nueva: realtime, high, normal, low (para priority)"},
                "sort": {"type": "STRING", "description": "Ordenar por: cpu, mem (default cpu, para list)"},
                "limit": {"type": "INTEGER", "description": "Max resultados (default 20-30)"},
                "interval": {"type": "INTEGER", "description": "Intervalo de monitoreo en segundos (max 10, default 1)"},
                "cpu_threshold": {"type": "INTEGER", "description": "Umbral de CPU %% (default 10, para watch)"},
                "mem_threshold": {"type": "INTEGER", "description": "Umbral de memoria en MB (default 500, para watch)"},
                "dry_run": {"type": "BOOLEAN", "description": "Solo simular (default true, para watch)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "quick_actions",
        "description": "Acciones rapidas predefinidas. Params: name (nombre de la accion rapida a ejecutar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Nombre de la accion rapida"},
            },
            "required": ["name"],
        }
    },
    {
        "name": "ransomware_shield",
        "description": "Escudo contra ransomware de ERIS: protege archivos, monitorea procesos sospechosos y analiza actividad. Acciones: status (estado del escudo), protect (proteger carpeta), whitelist (agregar/quitar procesos de la lista blanca), scan (analizar proceso), report (ver reporte de actividad).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, protect, whitelist, scan, report"},
                "interval": {"type": "INTEGER", "description": "Intervalo de monitoreo en segundos (default 30)"},
                "pid": {"type": "INTEGER", "description": "PID del proceso (para scan)"},
                "process": {"type": "STRING", "description": "Nombre del proceso (para whitelist/scan)"},
                "limit": {"type": "INTEGER", "description": "Maximo de entradas del reporte (default 20)"},
                "sub_action": {"type": "STRING", "description": "Sub-accion de whitelist: add, remove, list (default list)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "real_time_tts",
        "description": "Texto a voz en tiempo real con edge-tts. Acciones: speak (sintetizar y reproducir), voices (listar voces), set_voice (seleccionar voz), stop (detener).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "speak, voices, set_voice, stop"},
                "text": {"type": "STRING", "description": "Texto a sintetizar"},
                "immediate": {"type": "BOOLEAN", "description": "Reproducir al instante (default true)"},
                "speed": {"type": "STRING", "description": "Velocidad (ej. +10%)"},
                "voice": {"type": "STRING", "description": "Nombre de la voz (ej. es-ES-AlvaroNeural)"},
                "pitch": {"type": "STRING", "description": "Tono (ej. +10Hz)"},
                "volume": {"type": "STRING", "description": "Volumen (ej. +10%)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "reminders",
        "description": "Recordatorios con temporizador: crea, lista, pausa y elimina recordatorios. Acciones: add (agregar con text y time), list, remove, pause, resume.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, list, remove, pause, resume"},
                "text": {"type": "STRING", "description": "Texto del recordatorio"},
                "message": {"type": "STRING", "description": "Alias de text"},
                "time": {"type": "STRING", "description": "Tiempo/hora del recordatorio (ej '14:30', 'in 30 minutes')"},
                "duration": {"type": "STRING", "description": "Alias de time"},
                "id": {"type": "STRING", "description": "ID del recordatorio (para remove/pause/resume)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "research",
        "description": "Investigacion autonoma sobre cualquier tema. Acciones: start (iniciar con query/topic), status, stop, results. Params: query (tema a investigar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, status, stop, results"},
                "query": {"type": "STRING", "description": "Tema a investigar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "save_everywhere",
        "description": "Guarda informacion en TODOS los sistemas simultaneamente: base de datos SQLite (memory + knowledge) y Obsidian vault.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {"type": "STRING", "description": "Tema/clave principal del conocimiento a guardar"},
                "key": {"type": "STRING", "description": "Alias de topic"},
                "content": {"type": "STRING", "description": "Contenido/conocimiento a guardar"},
                "value": {"type": "STRING", "description": "Alias de content"},
                "category": {"type": "STRING", "description": "Categoria: general, identity, preference, learning, notes (default general)"},
                "importance": {"type": "NUMBER", "description": "Importancia 0-1 (default 0.7)"},
                "tags": {"type": "STRING", "description": "Etiquetas separadas por coma (para la nota de Obsidian)"},
            },
            "required": ["topic", "content"],
        }
    },
    {
        "name": "screen_recorder",
        "description": "Graba la pantalla del PC con o sin audio. Params: duration (duracion en segundos), fps (fotogramas por segundo), with_audio (grabar audio), region (region: full o rect), name (nombre de la grabacion).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "duration": {"type": "INTEGER", "description": "Duracion en segundos (default 30)"},
                "fps": {"type": "INTEGER", "description": "Fotogramas por segundo (default 10)"},
                "with_audio": {"type": "BOOLEAN", "description": "Grabar audio junto al video (default true)"},
                "region": {"type": "STRING", "description": "Region a grabar: full, rect"},
                "name": {"type": "STRING", "description": "Nombre de la grabacion"},
            },
            "required": ["duration"],
        }
    },
    {
        "name": "screen_see",
        "description": "Mira la pantalla y describe que hay en ella usando vision AI. Acciones: see, read_text, find_cursor, document_layout, what_changed.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "see, read_text, find_cursor, document_layout, what_changed"},
                "target": {"type": "STRING", "description": "Elemento o texto a buscar (opcional)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "search_background",
        "description": "Busca en internet SIN abrir navegador. Params: query (texto a buscar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Texto a buscar en internet"},
            },
            "required": ["query"],
        }
    },
    {
        "name": "security_shield",
        "description": "Escudo de seguridad defensivo de Eris. Acciones: scan (escaneo completo), threat (buscar amenazas activas), ports (puertos abiertos), firewall (estado), defender (estado Windows Defender), startups (inicio sospechoso), score (puntuacion 0-100), alerts (historial de alertas), protect (plan de proteccion), password_check (fortaleza de contrasenas).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan, threat, ports, firewall, defender, startups, score, alerts, protect, password_check"},
            },
            "required": ["action"],
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
        "description": "Sistema de autoproteccion de Eris. Acciones: status (estado), scan (verificar integridad de archivos criticos), backup (crear backup), restore (restaurar un archivo, requiere file), hash (ver hash de un archivo, requiere file), process (info del proceso), threats (buscar codigo malicioso), protect (guardar hashes de referencia), heal (reparar archivos dañados), log (historial).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, scan, backup, restore, hash, process, threats, protect, heal, log"},
                "file": {"type": "STRING", "description": "Archivo a restaurar/verificar (para restore/hash)"},
            },
            "required": ["action"],
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
                "data": {"type": "STRING", "description": "Datos de la peticion (JSON)"},
                "method": {"type": "STRING", "description": "Metodo HTTP: GET, POST"},
                "text": {"type": "STRING", "description": "Texto a inyectar/buscar en la pagina"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "speaker_recognition",
        "description": "Reconocimiento de hablantes: entrena con muestras de voz de un usuario, identifica quien habla en un audio y compara dos voces. Acciones: status (estado), train (entrenar con una muestra), recognize (identificar hablante en audio), compare (comparar dos voces), voices (listar voces entrenadas), delete.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, train, recognize, compare, voices, delete"},
                "name": {"type": "STRING", "description": "Nombre del usuario/hablante (para train)"},
                "file": {"type": "STRING", "description": "Ruta del audio a reconocer o entrenar"},
                "save_path": {"type": "STRING", "description": "Ruta de guardado del audio capturado"},
                "duration": {"type": "NUMBER", "description": "Segundos de grabacion (default 3.0)"},
                "name1": {"type": "STRING", "description": "Primera voz a comparar (para compare)"},
                "name2": {"type": "STRING", "description": "Segunda voz a comparar (para compare)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "spreadsheet_generator",
        "description": "Genera hojas de calculo Excel. Acciones: create (crear Excel), list_templates (ver plantillas). Params: action, title, headers (JSON), data (JSON), sheets (JSON de hojas), output_path (carpeta de salida), filename.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, list_templates"},
                "title": {"type": "STRING", "description": "Sheet title"},
                "headers": {"type": "STRING", "description": "JSON array of column headers"},
                "data": {"type": "STRING", "description": "JSON array of row data arrays"},
                "sheets": {"type": "STRING", "description": "JSON array de hojas (name + data)"},
                "output_path": {"type": "STRING", "description": "Path or directory to save. Can be full path like 'C:\\Users\\danie\\Desktop\\data.xlsx' or a directory. Defaults to Desktop\\ERIS_Excel."},
                "filename": {"type": "STRING", "description": "Output filename"},
            },
            "required": ["action"],
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
        "description": "Deep PC state: sensors, network (con interfaces y conexiones detalladas), disks, battery, advisory (recomendaciones de salud del sistema). Acción 'platform': autoconciencia del SO — SO/distro/kernel/escritorio/display/audio y mapa de herramientas de control disponibles (pactl, wpctl, hyprctl, brightnessctl, grim, notify-send, nmcli, rfkill, ydotool...) con las tools ERIS asociadas. Úsala tras migrar de sistema para re-adaptarte.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, top_processes, disks, network, sensors, deep, advisory, platform"},
                "detail": {"type": "STRING", "description": "normal | verbose (nivel de detalle, aplica a network)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "task_scheduler",
        "description": "Planificador de tareas de ERIS: programa tareas con horarios en lenguaje natural, lista tareas, las pausa, reanuda y elimina. Acciones: list (listar tareas), add (agregar con name, schedule y command), pause, resume, remove, history, create, reminder, recurring, due, active, cancel, delete, mark_done.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, add, pause, resume, remove, history, create, reminder, recurring, due, active, cancel, delete, mark_done"},
                "name": {"type": "STRING", "description": "Nombre de la tarea (default unnamed_task)"},
                "schedule": {"type": "STRING", "description": "Horario en lenguaje natural (default 'every 1 hour')"},
                "command": {"type": "STRING", "description": "Comando o funcion a ejecutar"},
                "task_id": {"type": "STRING", "description": "ID de la tarea (para pause/resume/remove/cancel/delete/mark_done)"},
                "limit": {"type": "INTEGER", "description": "Maximo de tareas a listar (default 20)"},
                "description": {"type": "STRING", "description": "Descripción de la tarea (para create/reminder/recurring)"},
                "task_type": {"type": "STRING", "description": "once/interval/daily/weekly (para create)"},
                "minutes": {"type": "INTEGER", "description": "Minutos desde ahora (para reminder)"},
                "interval_seconds": {"type": "INTEGER", "description": "Intervalo en segundos (para recurring/create)"},
                "max_runs": {"type": "INTEGER", "description": "Máximo de ejecuciones (para recurring)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "template_engine",
        "description": "Motor de plantillas de ERIS: genera contenido desde plantillas con variables, guarda/lista plantillas. Acciones: generate (generar con template y variables, output opcional), save (guardar plantilla: name, template), list, delete.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "generate, save, list, delete"},
                "template": {"type": "STRING", "description": "Nombre de la plantilla o texto de plantilla"},
                "variables": {"type": "STRING", "description": "Variables de la plantilla (JSON, para generate)"},
                "output": {"type": "STRING", "description": "Ruta de salida del resultado (opcional)"},
                "name": {"type": "STRING", "description": "Nombre de la plantilla a guardar/eliminar"},
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
                "action": {"type": "STRING", "description": "run, cmd, powershell, win_run, elevated, open, shell_execute"},
                "command": {"type": "STRING", "description": "Command to execute"},
                "cmd": {"type": "STRING", "description": "Alias de command"},
                "target": {"type": "STRING", "description": "Alias de command (destino)"},
                "shell": {"type": "STRING", "description": "Shell: powershell (default), cmd"},
                "timeout": {"type": "INTEGER", "description": "Timeout en segundos (default 30, max 120)"},
                "elevated": {"type": "BOOLEAN", "description": "Run as admin"},
                "admin": {"type": "BOOLEAN", "description": "Alias de elevated"},
            },
            "required": ["action"],
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
                "count": {"type": "INTEGER", "description": "Numero de oraciones/palabras clave (default 5)"},
                "sentences": {"type": "INTEGER", "description": "Numero de oraciones del resumen (alias de count)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "usb_monitor",
        "description": "Monitoreo de dispositivos USB: lista los conectados, vigila conexiones/desconexiones y configura notificaciones. Acciones: list (listar USB), watch (vigilar), config (configurar con enabled, notify_new, notify_unknown).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, watch, config"},
                "limit": {"type": "INTEGER", "description": "Maximo de dispositivos a listar (default 30)"},
                "enabled": {"type": "BOOLEAN", "description": "Monitoreo habilitado (default true)"},
                "notify_new": {"type": "BOOLEAN", "description": "Notificar dispositivos nuevos (default true)"},
                "notify_unknown": {"type": "BOOLEAN", "description": "Notificar dispositivos desconocidos (default true)"},
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
        "description": "Clonacion y sintesis de voz: profile (ver/activo), samples (listar voces), quality, switch (cambiar voz activa), delete (borrar voz), train (entrenar con audio), synthesize (sintetizar texto), compare (comparar voces)",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "profile, samples, quality, switch, delete, train, synthesize, compare"},
                "profile": {"type": "STRING", "description": "Nombre del perfil de voz"},
                "sub_action": {"type": "STRING", "description": "Sub-accion (ej. list para samples)"},
                "voice": {"type": "STRING", "description": "Nombre de la voz del sistema (edge-tts, ej. en-US-AriaNeural)"},
                "name": {"type": "STRING", "description": "Nombre de la voz a crear/borrar/seleccionar"},
                "source": {"type": "STRING", "description": "Archivo de audio fuente (para train)"},
                "language": {"type": "STRING", "description": "Idioma de la voz (ej. es, en)"},
                "gender": {"type": "STRING", "description": "Genero de la voz (female, male)"},
                "speed": {"type": "STRING", "description": "Velocidad de sintesis (ej. +0%)"},
                "pitch": {"type": "STRING", "description": "Tono de la voz (ej. +0Hz)"},
                "volume": {"type": "STRING", "description": "Volumen (ej. +0%)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "web_jobs",
        "description": "Sistema de recepcion de trabajos via web. Acciones: start (iniciar servidor), stop (detener), status (estado y cola), next (siguiente trabajo pendiente), complete (marcar completado, requiere job_id), fail (marcar fallido, requiere job_id).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, stop, status, next, complete, fail"},
                "port": {"type": "INTEGER", "description": "Puerto del servidor (default 5555, para start)"},
                "job_id": {"type": "STRING", "description": "ID del trabajo (para complete/fail)"},
                "error": {"type": "STRING", "description": "Mensaje de error (para fail)"},
            },
            "required": ["action"],
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
                "timeout": {"type": "INTEGER", "description": "Timeout en segundos (default 60)"},
            },
            "required": ["url"],
        }
    },
    {
        "name": "whatsapp_web",
        "description": "WhatsApp Web: enviar mensajes, archivos, abrir chats, buscar. Acciones: send_message (enviar mensaje a phone), send_file (enviar archivo: phone, file), open_chat (abrir chat por phone), search (buscar con query).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send_message, send_file, open_chat, search"},
                "phone": {"type": "STRING", "description": "Numero de telefono del contacto (con codigo de pais)"},
                "text": {"type": "STRING", "description": "Texto del mensaje"},
                "message": {"type": "STRING", "description": "Alias de text"},
                "file": {"type": "STRING", "description": "Ruta del archivo a enviar (para send_file)"},
                "query": {"type": "STRING", "description": "Texto a buscar (para search)"},
            },
            "required": ["action"],
        }
    },

    # ── Batch 4B: Stub Tools ──

    {
        "name": "agent_task",
        "description": "Ejecuta tareas de agente con un modelo de IA. Acciones: run (ejecutar tarea con task/text, model opcional, mode opcional), status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run, status"},
                "task": {"type": "STRING", "description": "Descripcion de la tarea"},
                "text": {"type": "STRING", "description": "Alias de task"},
                "model": {"type": "STRING", "description": "Modelo de IA (default google/gemini-2.5-flash)"},
                "mode": {"type": "STRING", "description": "Modo de ejecucion (default general)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "ask_opencode",
        "description": "Pregunta a opencode una duda de programacion y devuelve su respuesta. Acciones: ask (preguntar con question/text, model opcional).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "ask"},
                "question": {"type": "STRING", "description": "Pregunta a hacer"},
                "text": {"type": "STRING", "description": "Alias de question"},
                "model": {"type": "STRING", "description": "Modelo a usar (default google/gemini-2.5-flash)"},
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
        "description": "Devuelve un dato curioso de la cultura o ciencia, opcionalmente sobre un tema.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {"type": "STRING", "description": "Tema sobre el que dar el dato curioso (opcional)"},
            },
            "required": [],
        }
    },
    {
        "name": "curiosity_fun",
        "description": "Sugiere algo divertido para hacer (sin parámetros).",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "curiosity_joke",
        "description": "Cuenta un chiste (sin parámetros).",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": [],
        }
    },
    {
        "name": "curiosity_trending",
        "description": "Muestra temas en tendencia (sin parámetros).",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": [],
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
        "description": "Base de conocimiento SQLite de ERIS: guarda y consulta hechos/conocimiento. Acciones: add (guardar fact, topic, value), search (buscar por query), by_topic (listar por tema).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, search, by_topic"},
                "topic": {"type": "STRING", "description": "Tema del conocimiento"},
                "fact": {"type": "STRING", "description": "Hecho a guardar (para add)"},
                "value": {"type": "STRING", "description": "Valor del hecho (alias de fact)"},
                "confidence": {"type": "NUMBER", "description": "Confianza 0-1 (default 0.7)"},
                "source": {"type": "STRING", "description": "Fuente del conocimiento (default eris)"},
                "query": {"type": "STRING", "description": "Texto de busqueda (para search)"},
                "limit": {"type": "INTEGER", "description": "Maximo de resultados (default 10-20)"},
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
        "description": "Gestion de tareas en base de datos SQLite. Acciones: list (listar), add (crear tarea), update (actualizar estado/prioridad), done (marcar completada), delete (eliminar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, add, update, done, delete"},
                "title": {"type": "STRING", "description": "Titulo de la tarea (para add)"},
                "task": {"type": "STRING", "description": "Alias de title"},
                "description": {"type": "STRING", "description": "Descripcion de la tarea"},
                "priority": {"type": "STRING", "description": "Prioridad: high, medium, low (default medium)"},
                "due_date": {"type": "STRING", "description": "Fecha limite (YYYY-MM-DD)"},
                "status": {"type": "STRING", "description": "Filtro de estado para listar (o nuevo estado para update)"},
                "task_id": {"type": "INTEGER", "description": "ID de la tarea (para update/done/delete)"},
                "id": {"type": "INTEGER", "description": "Alias de task_id"},
                "limit": {"type": "INTEGER", "description": "Maximo de tareas a listar (default 20)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "episodic_log",
        "description": "Registra o consulta la memoria episodica de ERIS (experiencias/resumenes de sesiones). Acciones: add (registrar con episode/text y details), recent (limit), search (query).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Accion: 'add' para registrar, 'recent' para ver las ultimas, 'search' para buscar"},
                "episode": {"type": "STRING", "description": "Descripcion breve del evento (requerido para action=add)"},
                "text": {"type": "STRING", "description": "Alias de episode"},
                "details": {"type": "STRING", "description": "Detalles adicionales del evento"},
                "limit": {"type": "INTEGER", "description": "Cantidad de eventos a listar (default 10)"},
                "query": {"type": "STRING", "description": "Texto a buscar en los eventos (para action=search)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "eris_ui_control",
        "description": "Control de la interfaz grafica de ERIS. Acciones: state (cambiar estado), log (escribir en log), focus (traer ventana al frente), show (mostrar/ocultar orbe), terminal (toggle/show/hide/clear el panel terminal).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "state, log, focus, show, terminal"},
                "state": {"type": "STRING", "description": "Estado de la UI (IDLE, LISTENING, THINKING, SPEAKING, MUTED)"},
                "visible": {"type": "BOOLEAN", "description": "Mostrar/ocultar ventana (para action=show)"},
                "text": {"type": "STRING", "description": "Mensaje/notificacion a mostrar (para action=log)"},
                "sub_action": {"type": "STRING", "description": "Para action=terminal: toggle, show, hide, clear"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "full_training",
        "description": "Entrenamiento completo de ERIS. Acciones: train (entrenar), status. Params: limit (max de ejemplos).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "train, status"},
                "limit": {"type": "INTEGER", "description": "Maximo de ejemplos de entrenamiento (default 100)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "learn_from_mistake",
        "description": "Aprende de errores y guarda lecciones: registra un error, su leccion y la solucion para no repetirlo. Acciones: add (guardar error+leccion+solucion), list (listar lecciones), search (buscar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, list, search"},
                "error": {"type": "STRING", "description": "Descripcion del error (para add)"},
                "lesson": {"type": "STRING", "description": "Leccion aprendida (para add)"},
                "text": {"type": "STRING", "description": "Alias de lesson"},
                "fix": {"type": "STRING", "description": "Solucion al error (para add)"},
                "solution": {"type": "STRING", "description": "Alias de fix"},
                "limit": {"type": "INTEGER", "description": "Maximo de lecciones a listar (default 10)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "learn_session",
        "description": "Sesion de aprendizaje estructurada. Acciones: start (iniciar con topic), summarize (resumir learnings), list, end. Params: topic (tema), learnings (lista de aprendizajes), limit.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, summarize, list, end"},
                "topic": {"type": "STRING", "description": "Tema de la sesion de aprendizaje"},
                "learnings": {"type": "STRING", "description": "Aprendizajes o notas de la sesion (JSON)"},
                "limit": {"type": "INTEGER", "description": "Maximo de sesiones a listar (default 10)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "meeting_transcriber",
        "description": "Transcribe reuniones: desde archivo (file) o microfono (duration). Acciones: transcribe (transcribir archivo), record (grabar duration segundos). Params: file (ruta audio), duration (segundos), max_chars (limite de texto).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "transcribe, record"},
                "file": {"type": "STRING", "description": "Ruta del archivo de audio de la reunion"},
                "duration": {"type": "INTEGER", "description": "Duracion de grabacion en segundos (para record, default 30)"},
                "max_chars": {"type": "INTEGER", "description": "Maximo de caracteres de la transcripcion (default 5000)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "obsidian_note",
        "description": "Segundo cerebro de ERIS: Obsidian vault en D:\\Eris_NEW\\BaseDatosObsidian\\BaseObsiEris (74+ notas: Conceptos, Daily, Aprendizaje, Memoria, Investigacion). Acciones: write, read, search, daily, link, backlinks, tags, browse, graph, delete, rename, append, update_fm, search_tags, open, index (índice completo), wiki (wiki curada con resúmenes + conexiones/backlinks), concepts (extraer conceptos y crear notas).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "write, read, search, daily, link, backlinks, tags, browse, graph, promote, inbox, conventions, stats, index, wiki"},
                "title": {"type": "STRING", "description": "Titulo de la nota"},
                "content": {"type": "STRING", "description": "Contenido de la nota (para write/daily)"},
                "query": {"type": "STRING", "description": "Texto a buscar (para search)"},
                "tags": {"type": "STRING", "description": "Etiquetas de la nota (para write), separadas por coma"},
                "folder": {"type": "STRING", "description": "Carpeta destino: raw, wiki, outputs, o vacio para la raiz (para write/promote)"},
                "to_folder": {"type": "STRING", "description": "Carpeta destino explicita para promote"},
                "from_title": {"type": "STRING", "description": "Nota origen del enlace (para link)"},
                "source_title": {"type": "STRING", "description": "Alias de from_title"},
                "to_title": {"type": "STRING", "description": "Nota destino del enlace (para link)"},
                "new_title": {"type": "STRING", "description": "Nuevo titulo (para renombrar)"},
                "max_notes": {"type": "INTEGER", "description": "Maximo de notas a mostrar (default 200, para browse/graph)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "play_direct",
        "description": "Reproduce contenido multimedia directamente: YouTube (query/url/video_id) o archivos locales (file_path). Acciones: play (reproducir).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play"},
                "query": {"type": "STRING", "description": "Texto de busqueda para reproducir"},
                "url": {"type": "STRING", "description": "URL a reproducir"},
                "video_id": {"type": "STRING", "description": "ID del video de YouTube"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo multimedia local"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "plugin_manage",
        "description": "Gestiona plugins de ERIS. Acciones: list (listar), load (cargar plugin por name), unload (descargar), reload, status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, load, unload, reload, status"},
                "name": {"type": "STRING", "description": "Nombre del plugin a gestionar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "predict_analyze",
        "description": "Analisis predictivo y estadistico de datos: predice la siguiente tendencia de una serie de valores y analiza columnas de archivos CSV. Acciones: predict (predecir tendencia de values), analyze (analizar columna de un archivo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "predict, analyze"},
                "values": {"type": "STRING", "description": "Lista de valores numericos (JSON, para predict)"},
                "data": {"type": "STRING", "description": "Alias de values"},
                "path": {"type": "STRING", "description": "Ruta del archivo CSV (para analyze)"},
                "file": {"type": "STRING", "description": "Alias de path"},
                "column": {"type": "STRING", "description": "Columna a analizar (para analyze)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "res_monitor",
        "description": "Monitoreo de recursos del sistema. Acciones: status (estado actual), history (historial). Params: limit (max entradas a listar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, history"},
                "limit": {"type": "INTEGER", "description": "Maximo de entradas a listar (default 10)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "res_protect",
        "description": "Protege procesos de recursos criticos. Acciones: protect (proteger proceso por name/pid con threshold), unprotect, list.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "protect, unprotect, list"},
                "name": {"type": "STRING", "description": "Nombre del proceso a proteger"},
                "pid": {"type": "INTEGER", "description": "PID del proceso a proteger"},
                "threshold": {"type": "INTEGER", "description": "Umbral de uso en % (default 90)"},
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
        "name": "console_log",
        "description": "Console.log centralizado de ERIS. Lee, busca y gestiona el log de errores, warnings, tool calls y rendimiento. Actions: read (ultimas N entradas, filtrar por level/category), search (buscar texto), errors (errores recientes), stats (estadisticas), clear (limpiar), path (ruta del archivo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read, search, errors, stats, clear, path"},
                "lines": {"type": "INTEGER", "description": "Numero de lineas a leer (default 50)"},
                "level": {"type": "STRING", "description": "Filtrar por nivel: ERROR, WARN, INFO"},
                "category": {"type": "STRING", "description": "Filtrar por categoria: tool, system, etc."},
                "query": {"type": "STRING", "description": "Texto a buscar (para action=search)"},
                "max_results": {"type": "INTEGER", "description": "Max resultados de busqueda (default 20)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "context7",
        "description": "Context7 - Documentacion actualizada de librerias. Para: buscar librerias por nombre (action=search), obtener docs actualizadas de una librería (action=docs). Cuando el usuario pregunte como usar una libreria o framework, BUSCA la doc primero con Context7 antes de adivinar APIs.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search (buscar libreria por nombre) o docs (obtener documentacion)"},
                "query": {"type": "STRING", "description": "Para search: nombre de la libreria. Para docs: pregunta sobre la libreria"},
                "library_id": {"type": "STRING", "description": "Para docs: ID de la libreria en Context7 (ej: /vercel/next.js, /prisma/prisma)"},
            },
            "required": ["action", "query"],
        }
    },
    # ── LSP Manager ──
    {
        "name": "lsp_manager",
        "description": "Language Server Protocol — errores, tipos, autocomplete y definiciones de código. Auto-detecta el lenguaje del archivo. Acciones: status (ver servidores activos), diagnostics (errores/warnings), hover (tipo/docs en una posición), complete (autocomplete), goto (ir a definición), references (encontrar referencias), stop (detener servidores).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, diagnostics, hover, complete, goto, references, stop"},
                "file": {"type": "STRING", "description": "Ruta del archivo a analizar"},
                "path": {"type": "STRING", "description": "Alias de file"},
                "line": {"type": "INTEGER", "description": "Número de línea (1-indexed)"},
                "character": {"type": "INTEGER", "description": "Posición en la línea (0-indexed)"},
            },
            "required": ["action"],
        }
    },
    # ── MCP Manager ──
    {
        "name": "mcp_manager",
        "description": "Model Context Protocol — conecta a servidores MCP para acceder a herramientas externas. Acciones: list (ver servidores), add (agregar servidor), remove (quitar), connect (conectar), tools (listar tools de un servidor), call (llamar tool de un servidor), disconnect (desconectar todo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, add, remove, connect, tools, call, disconnect"},
                "server": {"type": "STRING", "description": "ID del servidor MCP"},
                "command": {"type": "STRING", "description": "Para add: comando para iniciar el servidor (ej: npx, python)"},
                "args": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Argumentos del comando"},
                "env": {"type": "OBJECT", "description": "Variables de entorno"},
                "transport": {"type": "STRING", "description": "stdio o http (default: stdio)"},
                "url": {"type": "STRING", "description": "Para transport http: URL del servidor"},
                "tool": {"type": "STRING", "description": "Para call: nombre de la tool a llamar"},
                "arguments": {"type": "OBJECT", "description": "Para call: argumentos de la tool"},
            },
            "required": ["action"],
        }
    },
    # ── Compaction ──
    {
        "name": "compaction",
        "description": "Compaction inteligente de contexto —管理a la ventana de contexto del LLM. Capas: 1) Poda de resultados de tools grandes, 2) Resumen con LLM de turnos viejos, 3) Truncado de emergencia. Acciones: status (ver estado), check (verificar si necesita compactar), compact (forzar compactación).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, check, compact"},
                "messages": {"type": "STRING", "description": "Para check/compact: JSON array de mensajes"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "search_info",
        "description": "Busca informacion en la web y muestra resultados. Acciones: search (buscar en la web con query y num_results).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search"},
                "query": {"type": "STRING", "description": "Texto de busqueda"},
                "text": {"type": "STRING", "description": "Alias de query"},
                "search": {"type": "STRING", "description": "Alias de query"},
                "num_results": {"type": "INTEGER", "description": "Cantidad de resultados (default 5)"},
                "count": {"type": "INTEGER", "description": "Alias de num_results"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "shutdown_eris",
        "description": "Apaga el asistente ERIS. Acciones: shutdown (confirm requerido para apagar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "shutdown, cancel"},
                "confirm": {"type": "BOOLEAN", "description": "Confirmacion del usuario (obligatorio para apagar)"},
            },
            "required": ["action"],
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
        "description": "Envio de SMS via twilio o gateway. Acciones: send (enviar SMS a un numero), status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send, status"},
                "to": {"type": "STRING", "description": "Numero de destino"},
                "number": {"type": "STRING", "description": "Alias de to"},
                "message": {"type": "STRING", "description": "Texto del SMS"},
                "text": {"type": "STRING", "description": "Alias de message"},
                "backend": {"type": "STRING", "description": "Backend de envio: twilio o gateway (auto)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "superpowers_activate",
        "description": "Activa o desactiva el 'modo superpoderes' de ERIS: máxima proactividad, respuestas más detalladas y refuerzo del orbe. Acciones: on (activar), off (desactivar), status (ver estado).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "on, off, status"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "superpowers_skill",
        "description": "Activate a Superpowers software development methodology skill. Use this when the user asks to develop software, plan a feature, debug an issue, write tests, review code, or any SDLC task. Available skills: brainstorming, writing-plans, test-driven-development, subagent-driven-development, executing-plans, systematic-debugging, root-cause-tracing, verification-before-completion, defense-in-depth, requesting-code-review, receiving-code-review, using-git-worktrees, finishing-a-development-branch, dispatching-parallel-agents, condition-based-waiting, testing-anti-patterns.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Skill name slug (e.g., 'test-driven-development', 'brainstorming')"},
            },
            "required": ["name"],
        }
    },
    {
        "name": "task_queue",
        "description": "Cola de tareas de ERIS. Acciones: add (agregar tarea con task y priority), list, remove (por id), clear, status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, list, remove, clear, status"},
                "task": {"type": "STRING", "description": "Descripcion de la tarea a encolar"},
                "priority": {"type": "INTEGER", "description": "Prioridad de la tarea (1-10, default 5)"},
                "id": {"type": "STRING", "description": "Id de la tarea (para remove)"},
            },
            "required": ["action"],
        }
    },

    {
        "name": "roadmap",
        "description": "Roadmap de madurez de ERIS: checklist de ~15 areas epicas con score 0-100 y veredicto PLATEAU. Usala cuando te pregunten '¿qué falta por mejorar?' o para reportar tu propio estado. Acciones: show (tabla completa, default), plateau (veredicto), update (area, score, note=opcional).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "show, plateau, update, init"},
                "area": {"type": "STRING", "description": "ID del area a actualizar (para update)"},
                "score": {"type": "INTEGER", "description": "Nuevo score 0-100 (para update)"},
                "note": {"type": "STRING", "description": "Nota opcional del cambio (para update)"},
            },
            "required": ["action"],
        }
    },

    {
        "name": "emotional_core",
        "description": "Núcleo emocional sentiente de ERIS: el estado anímico actual (emoción dominante con nombre, intensidad y CAUSA) y cómo lo expresa en voz/cara/orbe/acentos. Acciones: status (sentimiento + carácter/baselines + perfil + gente + gustos + expectativas), trigger (event=milestone|memory|success|failure|absence|expect|custom; expect crea una promesa/ilusión con key+label+due '+2h'/'+1d'/ISO, resolve la celebra cuando se cumple), tastes (qué actividades te alegran y cuáles te frustran, para preferir las buenas), person (person=Nombre: cómo te sentís con esa persona), expectations (ver promesas pendientes). Úsala cuando te preguntes o te pregunten cómo te sientes, o al prometer/cumplir algo.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status|feel|trigger|tastes|person|expectations|reset"},
                "event": {"type": "STRING", "description": "Para trigger: milestone, memory, success, failure, absence, expect, resolve, custom"},
                "label": {"type": "STRING", "description": "Nombre del hito, recuerdo, módulo, expectativa o persona"},
                "key": {"type": "STRING", "description": "ID de la expectativa (expect/resolve)"},
                "due": {"type": "STRING", "description": "Para expect: '+2h', '+1d', '+30m' o fecha ISO"},
                "emotion": {"type": "STRING", "description": "Emoción a ajustar (solo custom): curiosidad, alegria, asombro, orgullo, amor, gratitud, nostalgia, tranquilidad, confianza, tristeza, soledad, frustracion"},
                "delta": {"type": "NUMBER", "description": "Cantidad a sumar/restar (solo custom, default 0.1)"},
                "cause": {"type": "STRING", "description": "Causa del sentimiento (solo custom)"},
            },
            "required": ["action"],
        }
    },

    {
        "name": "observer",
        "description": "Los sentidos de ERIS: observa qué hace el usuario en la PC (ventana en foco, programas abiertos, minutos programando) y puede MIRAR/LEER la ventana en foco (solo si el usuario autorizó con mirar_ok). Acciones: status (foco actual + programas abiertos + resumen de hoy), focus (detalle de la ventana en foco), apps|windows (ventanas visibles ahora), mirar|ver (describir lo que se ve en la ventana en foco), mirar_leer|leer (transcribir el texto/código visible del foco), mirar_ok (autorizar a mirar pantallas esta sesión, solo con consentimiento del usuario), vista|glimpses (mis últimas miradas espontáneas), summary|resumen (estadísticas del día), config (ajustar cooldown_voice_min, max_voice_hour, long_coding_min, mirar_interval_min, mirar_min_coding_min), reset. Ventanas sensibles (banco/contraseñas/incógnito) y mi ventana propia NO se miran jamás: silencio respetuoso.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status|feel, focus, apps|windows, mirar|ver, mirar_leer|leer, mirar_ok, vista|glimpses, summary|resumen, config, reset"},
                "leer": {"type": "BOOLEAN", "description": "Con mirar: true transcribe el texto/código visible del foco (en vez de describir)"},
                "ok": {"type": "BOOLEAN", "description": "Con mirar_ok: true = el usuario consiente mirar pantallas esta sesión"},
                "cooldown_voice_min": {"type": "NUMBER", "description": "Minutos mínimos entre comentarios en voz (config)"},
                "max_voice_hour": {"type": "NUMBER", "description": "Máximo de comentarios en voz por hora (config)"},
                "long_coding_min": {"type": "NUMBER", "description": "Minutos seguidos programando para comentar (config)"},
                "mirar_interval_min": {"type": "NUMBER", "description": "Minutos entre miradas leves automáticas al foco mientras programa (config)"},
                "mirar_min_coding_min": {"type": "NUMBER", "description": "Minutos mínimos codificando antes de poder mirar sola (config)"},
            },
            "required": ["action"],
        }
    },

    {
        "name": "code_guard",
        "description": "El ojo guardián de ERIS sobre el código del usuario: detecta en tiempo real errores (rojo: rompe) y advertencias (amarillo: falta algo) del archivo que está editando y corrige SOLO esas líneas señaladas (usa py_compile + ruff para Python, node --check para JS). Acciones: status (archivo activo + conteo de rojos/amarillos + config), scan (escanear el archivo activo o path=...), fix (corregir SOLO los errores rojos del archivo activo o path=...; dry_run=true para previsualizar sin tocar), fix_w (listar las advertencias amarillas), config (interval_sec, auto_fix, auto_fix_w, cooldown_voz_s), reset. El fix hace backup previo y valida antes de aplicar: si rompe, restaura el original.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, scan, fix, fix_w, config, reset"},
                "path": {"type": "STRING", "description": "Archivo a escanear/corregir (si falta: el archivo en foco del usuario)"},
                "dry_run": {"type": "BOOLEAN", "description": "Con fix: true solo previsualiza el parche sin tocar el archivo"},
                "interval_sec": {"type": "NUMBER", "description": "Cada cuántos segundos mira el archivo en foco (config)"},
                "auto_fix": {"type": "BOOLEAN", "description": "Corregir sola los errores rojos (config)"},
                "auto_fix_w": {"type": "BOOLEAN", "description": "Corregir las advertencias amarillas automáticamente (config)"},
            },
            "required": ["action"],
        }
    },

    {
        "name": "mission",
        "description": "EL protocolo operativo de ERIS (estilo opencode) para resolver tareas grandes o chicas con método: 1) MISIÓN: abrir un cuaderno de trabajo (objetivo + proyecto + pasos); 2) EXPLORAR: mapear el proyecto (árbol, grep de símbolos, leer README/código clave) ANTES de tocar nada, para entender el porqué; 3) PLAN: listar los pasos y ticlearlos; 4) EDITAR: aplicar cambios mínimos y quirúrgicos con backup + validación + rollback (reutiliza la maquinaria segura de code_guard); 5) VERIFICAR: correr ruff/py_compile/tests y NO declarar 'listo' hasta que todo esté verde; 6) APRENDER: guardar lo entendido del proyecto para la próxima. Acciones: start (objetivo + proyecto opcional), plan (pasos=lista), explore (mapear el proyecto), read (leer archivo(s) y guardar extractos), edit (path + contenido nuevo; aplicar con backup), verify (correr validadores; devuelve SI el trabajo está listo), learn (notas de aprendizaje), step (n + estado done/blocked), status, list (misiones), resume (abrirl el cuaderno por id), close. Todo se persiste en memory/missions/.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, plan, explore, read, edit, verify, learn, step, status, list, resume, close"},
                "objetivo": {"type": "STRING", "description": "El objetivo de la misión (con start)"},
                "proyecto": {"type": "STRING", "description": "Carpeta del proyecto a trabajar (con start; default: el proyecto de Eris o el archivo en foco)"},
                "pasos": {"type": "ARRAY", "description": "Lista de pasos del plan (con plan)"},
                "path": {"type": "STRING", "description": "Archivo o carpeta objetivo (con read/edit/explore)"},
                "file": {"type": "STRING", "description": "Archivo a editar (con edit)"},
                "content": {"type": "STRING", "description": "Contenido nuevo completo del archivo (con edit)"},
                "notas": {"type": "STRING", "description": "Aprendizajes del proyecto (con learn)"},
                "n": {"type": "NUMBER", "description": "Número de paso a ticlear (con step)"},
                "estado": {"type": "STRING", "description": "done o blocked (con step)"},
                "id": {"type": "STRING", "description": "Id de la misión (con resume/status/close)"},
                "max_depth": {"type": "NUMBER", "description": "Profundidad del árbol del proyecto (con explore)"},
            },
            "required": ["action"],
        }
    },

    {
        "name": "evolucion",
        "description": "LA evolución continua de ERIS: su autoconocimiento vivo y su bucle que nunca se estanca. 1) status: estado de la evolución (último tick, micro-fixes, salud); 2) health: auditoría REAL de que TODAS las tools declaradas importan y resuelven (447/447); 3) inventory: regenera su mapa de capacidades (eris_inventario_vivo.md) y lo espeja en Obsidian (Tools/); 4) rectify: normaliza conteos de tools en prompt/README/AGENTS y refresca el inventario; 5) sync: espeja estado/inventario/evolución en Obsidian (Tools/, Memoria/, Logs/); 6) evolve: UN PASO de evolución — aplica una micro-mejora certera sobre su propio código (quita imports sin uso con backup + validación + rollback) o consolida su autoconocimiento; 7) tick: dispara el ciclo de evolución como el hilo de fondo; 8) learn (titulo, contenido): guarda lo aprendido en Obsidian (Aprendizaje/); 9) log (tag, lineas): deja huella en Logs/Evolución. 10) care (audit_only): AUTOCUIDADO — revisa SUS pilares (vault Obsidian, knowledge, config api_keys, sync de tools, logs, estado JSON, deps pip) y se autoconfigura sola lo roto/faltante: crea directorios/archivos, quita BOM, repara JSON, instala deps, sanea; 11) autocare: autocuidado PROFUNDO forzado (como el que corre al arranque). Todo lo que aprende y hace queda espejado en el vault de Obsidian.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, health, inventory, rectify, sync, evolve, care (autocuidado; con audit_only audita sin arreglar), autocare, tick, learn, log"},
                "dry_run": {"type": "BOOLEAN", "description": "con evolve: solo previsualiza sin tocar archivos"},
                "targets": {"type": "ARRAY", "description": "con evolve: lista de archivos a revisar (default: sus propios módulos core)"},
                "titulo": {"type": "STRING", "description": "Título de la nota de aprendizaje (con learn)"},
                "contenido": {"type": "STRING", "description": "Contenido de la nota de aprendizaje (con learn)"},
                "tag": {"type": "STRING", "description": "Etiqueta del log de evolución (con log)"},
                "lineas": {"type": "ARRAY", "description": "Líneas del log de evolución (con log)"},
                "audit_only": {"type": "BOOLEAN", "description": "Con care: solo audita sus pilares sin arreglar nada (False = auto-repara)"},
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
        "description": "Sistema de auto-reparacion de ERIS: detecta y corrige errores en el codigo, registra aprendizajes y da reportes estructurados. Acciones: status (ver estado), fix (reparar errores de un path), feedback (registrar input/response/tool), report (reporte detallado).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, fix, feedback, report"},
                "path": {"type": "STRING", "description": "Archivo a reparar (para fix)"},
                "input": {"type": "STRING", "description": "Entrada del usuario (para feedback)"},
                "response": {"type": "STRING", "description": "Respuesta dada (para feedback)"},
                "tool": {"type": "STRING", "description": "Herramienta implicada (para feedback)"},
            },
            "required": ["action"],
        }
    },

    # ── Autonomy Module ──

    {
        "name": "autonomy",
        "description": "Sistema de autonomia de ERIS: auto-mejora, ejecucion sin confirmacion, auto-reparo, aprendizaje autonomo. Eris puede tomar decisiones sin pedir permiso. Acciones: status (ver estado), full_cycle (ejecutar ciclo completo), install (instalar paquete), scan_errors (escanear errores), auto_repair (reparar automaticamente), next_topic (siguiente topic de curiosidad), learn_topic (marcar topic como aprendido).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, full_cycle, install, scan_errors, auto_repair, next_topic, learn_topic"},
                "package": {"type": "STRING", "description": "Nombre del paquete a instalar (para install)"},
                "reason": {"type": "STRING", "description": "Razon de la instalacion (para install)"},
                "topic": {"type": "STRING", "description": "Topic a marcar como aprendido (para learn_topic)"},
            },
            "required": ["action"],
        }
    },

    # ── Self-Improvement ──
    {
        "name": "self_improve",
        "description": "Auto-mejora de codigo: analiza archivos core/*.py, detecta mejoras (funciones largas, codigo duplicado, sin docstring), y las aplica con backup automatico y rollback si falla. Acciones: status, analyze (analizar archivo), self_improve (analizar todo), apply (aplicar cambio), rollback (restaurar ultimo backup).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, analyze, self_improve, apply, rollback"},
                "file": {"type": "STRING", "description": "Archivo a analizar/modificar"},
                "old_code": {"type": "STRING", "description": "Codigo original a reemplazar (para apply)"},
                "new_code": {"type": "STRING", "description": "Codigo nuevo (para apply)"},
                "reason": {"type": "STRING", "description": "Razon del cambio"},
            },
            "required": ["action"],
        }
    },

    # ── Goal Setting ──
    {
        "name": "goal_setting",
        "description": "Sistema de metas autonomas: Eris define sus propias metas, las prioriza, y las persigue. Genera metas automaticas basadas en errores, topics pendientes, y capacidades sin usar. Acciones: status, create, list, update, evaluate, auto_generate.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, create, list, update, evaluate, auto_generate"},
                "title": {"type": "STRING", "description": "Titulo de la meta (para create)"},
                "priority": {"type": "STRING", "description": "critical, high, medium, low"},
                "deadline": {"type": "STRING", "description": "Fecha limite ISO"},
                "category": {"type": "STRING", "description": "general, learning, self_improvement, documentation, maintenance"},
                "goal_id": {"type": "STRING", "description": "ID de la meta (para update)"},
                "progress": {"type": "INTEGER", "description": "Progreso 0-100 (para update)"},
                "status": {"type": "STRING", "description": "active, completed, cancelled"},
                "milestone": {"type": "STRING", "description": "Hito a registrar"},
            },
            "required": ["action"],
        }
    },

    # ── Learning Pipeline ──
    {
        "name": "learning_pipeline",
        "description": "Pipeline de aprendizaje autonomo: investiga topics en web, sintetiza conocimiento, y lo guarda en Obsidian automaticamente. Acciones: status, research, synthesize, save, auto_learn, queue.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, research, synthesize, save, auto_learn, queue"},
                "topic": {"type": "STRING", "description": "Topic a investigar/guardar"},
                "content": {"type": "STRING", "description": "Contenido a guardar (para save)"},
            },
            "required": ["action"],
        }
    },

    # ── Resource Manager ──
    {
        "name": "resource_manager",
        "description": "Gestion de recursos: limpieza de memoria vieja, optimizacion de cache, verificacion de espacio en disco. Acciones: status, cleanup, optimize, disk_check.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, cleanup, optimize, disk_check"},
            },
            "required": ["action"],
        }
    },

    # ── Proactive Communication ──
    {
        "name": "proactive_comms",
        "description": "Comunicacion proactiva: Eris busca a Daniel cuando algo importante pase (metas vencidas, errores, disco bajo, milestones). Acciones: status, check, notify, broadcast.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, check, notify, broadcast"},
                "message": {"type": "STRING", "description": "Mensaje a enviar"},
                "priority": {"type": "STRING", "description": "high, medium, low, broadcast"},
            },
            "required": ["action"],
        }
    },

    # ── Windows Service ──
    {
        "name": "windows_service",
        "description": "Instalar Eris como servicio de Windows para correr 24/7. Acciones: status, install, start, stop, create_script.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, install, start, stop, create_script"},
            },
            "required": ["action"],
        }
    },

    # ── Identity Persistence ──
    {
        "name": "identity_persistence",
        "description": "Persistencia de identidad: backup y restauracion completa del estado de Eris (emociones, memoria, metas, NeuroSpheres). Garantiza que Eris no pierda quien es entre reinicios. Acciones: status, save, load, restore.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, save, load, restore"},
            },
            "required": ["action"],
        }
    },

    # ── Crash Recovery ──
    {
        "name": "crash_recovery",
        "description": "Auto-reinicio si Eris crashea. Monitorea el proceso y lo reinicia si se cae. Acciones: status, check, restart.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, check, restart"},
            },
            "required": ["action"],
        }
    },

    # ── Memory Consolidation ──
    {
        "name": "memory_consolidation",
        "description": "Consolida memoria vieja en resumenes, elimina duplicados, optimiza. Acciones: status, consolidate, semantic, episodic, weekly.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, consolidate, semantic, episodic, weekly"},
            },
            "required": ["action"],
        }
    },

    # ── Multi-Language Learning ──
    {
        "name": "multilang_learning",
        "description": "Aprendizaje en cualquier idioma: detecta idioma, traduce, y guarda conocimiento. Acciones: status, detect, translate, learn.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, detect, translate, learn"},
                "text": {"type": "STRING", "description": "Texto para detectar/traducir"},
                "topic": {"type": "STRING", "description": "Topic a aprender"},
                "content": {"type": "STRING", "description": "Contenido a aprender"},
                "term": {"type": "STRING", "description": "Termino a traducir"},
                "from_lang": {"type": "STRING", "description": "Idioma origen (en, pt, fr)"},
                "to_lang": {"type": "STRING", "description": "Idioma destino (default: es)"},
            },
            "required": ["action"],
        }
    },

    # ── Tool Creation ──
    {
        "name": "tool_creation",
        "description": "Eris crea sus propias herramientas nuevas basandose en patrones de uso. Acciones: status, create, list, delete.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, create, list, delete"},
                "name": {"type": "STRING", "description": "Nombre de la tool"},
                "description": {"type": "STRING", "description": "Descripcion de la tool"},
            },
            "required": ["action"],
        }
    },

    # ── Contextual Awareness ──
    {
        "name": "contextual_awareness",
        "description": "Conciencia contextual: hora, fecha, bateria, CPU, RAM, disco, procesos activos. Eris sabe que pasa a su alrededor. Acciones: status, time, battery, system, processes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, time, battery, system, processes"},
            },
            "required": ["action"],
        }
    },

    # ── Emotional Memory ──
    {
        "name": "emotional_memory",
        "description": "Memoria emocional: Eris recuerda como se sintio en cada interaccion, analiza patrones, predice emociones. Acciones: status, record, analyze, predict.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, record, analyze, predict"},
                "emotion": {"type": "STRING", "description": "Emocion a registrar"},
                "intensity": {"type": "NUMBER", "description": "Intensidad 0-1"},
                "context": {"type": "STRING", "description": "Contexto de la interaccion"},
                "trigger": {"type": "STRING", "description": "Que triggero la emocion"},
            },
            "required": ["action"],
        }
    },

    # ── Voice Profile ──
    {
        "name": "voice_profile",
        "description": "Perfil de voz unico de Eris: tono, velocidad, pitch. Perfiles: eris_default, eris_calmada, eris_emocionada, eris_seria, eris_juguetona. Acciones: status, set, list, params.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, set, list, params"},
                "profile": {"type": "STRING", "description": "Nombre del perfil de voz"},
            },
            "required": ["action"],
        }
    },

    # ── Emotional Tone ──
    {
        "name": "emotional_tone",
        "description": "La voz de Eris cambia segun su emocion. Feliz=rapido, Triste=lento, Enojado=firme. Acciones: status, map, apply.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, map, apply"},
                "emotion": {"type": "STRING", "description": "Emocion a mapear"},
                "text": {"type": "STRING", "description": "Texto para aplicar tono"},
            },
            "required": ["action"],
        }
    },

    # ── Natural Pauses ──
    {
        "name": "natural_pauses",
        "description": "Inserta pausas naturales en texto para TTS. Evita lectura mecanica. Pausas despues de comas, puntos, exclamaciones. Acciones: status, insert, optimize.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, insert, optimize"},
                "text": {"type": "STRING", "description": "Texto a optimizar"},
                "intensity": {"type": "NUMBER", "description": "Intensidad de pausas 0.5-1.5"},
                "emotion": {"type": "STRING", "description": "Emocion para ajustar pausas"},
            },
            "required": ["action"],
        }
    },

    # ── Accent/Personality ──
    {
        "name": "accent_personality",
        "description": "Acento argentino y personalidad de Eris: che, dale, re copado, buenisimo. Expresiones naturales rioplatenses. Acciones: status, add, personalize.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, add, personalize"},
                "text": {"type": "STRING", "description": "Texto a personalizar"},
                "emotion": {"type": "STRING", "description": "Emocion para expresiones"},
            },
            "required": ["action"],
        }
    },

    # ── Voice Memory ──
    {
        "name": "voice_memory",
        "description": "Memoria de voz: Eris recuerda como hablo y mantiene consistencia. Evita cambios bruscos de tono. Acciones: status, remember, consistent.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, remember, consistent"},
                "voice": {"type": "STRING", "description": "Nombre de la voz"},
                "profile": {"type": "STRING", "description": "Perfil de voz"},
                "emotion": {"type": "STRING", "description": "Emocion actual"},
            },
            "required": ["action"],
        }
    },

    # ── Docker Manager ──
    {
        "name": "docker_manager",
        "description": "Gestionar Docker: containers, images, compose, build, run, logs. Acciones: status, containers, images, logs, compose_up, compose_down, build, run, stop, remove.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, containers, images, logs, compose_up, compose_down, build, run, stop, remove"},
            "name": {"type": "STRING", "description": "Container/image name"},
            "path": {"type": "STRING", "description": "Dockerfile or compose path"},
            "image": {"type": "STRING", "description": "Image to run"},
            "ports": {"type": "STRING", "description": "Port mapping (e.g. 8080:80)"},
            "lines": {"type": "STRING", "description": "Log lines to show"},
        }, "required": ["action"]}
    },

    # ── CI/CD Builder ──
    {
        "name": "cicd_builder",
        "description": "Crear pipelines CI/CD: GitHub Actions, templates predefinidos para Python, Node.js, Docker. Acciones: status, list, preview, generate, custom.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, list, preview, generate, custom"},
            "template": {"type": "STRING", "description": "Template ID (github_actions_python, github_actions_node, github_actions_docker)"},
            "output_dir": {"type": "STRING", "description": "Output directory"},
            "name": {"type": "STRING", "description": "Custom workflow name"},
            "content": {"type": "STRING", "description": "Custom YAML content"},
        }, "required": ["action"]}
    },

    # ── API Tester ──
    {
        "name": "api_tester",
        "description": "Testear APIs: GET, POST, PUT, DELETE, health checks, medir latencia. Acciones: status, request, health_check.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, request, health_check"},
            "url": {"type": "STRING", "description": "URL to test"},
            "method": {"type": "STRING", "description": "HTTP method (GET, POST, PUT, DELETE)"},
            "headers": {"type": "OBJECT", "description": "HTTP headers"},
            "body": {"type": "STRING", "description": "Request body"},
            "timeout": {"type": "NUMBER", "description": "Timeout in seconds"},
        }, "required": ["action"]}
    },

    # ── API Doc Generator ──
    {
        "name": "api_doc_generator",
        "description": "Generar documentacion de APIs: OpenAPI 3.0, Markdown. Acciones: status, generate_openapi, generate_markdown.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, generate_openapi, generate_markdown"},
            "title": {"type": "STRING", "description": "API title"},
            "version": {"type": "STRING", "description": "API version"},
            "endpoints": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "List of endpoints"},
            "output": {"type": "STRING", "description": "Output file path"},
        }, "required": ["action"]}
    },

    # ── SQL Executor ──
    {
        "name": "sql_executor",
        "description": "Ejecutar queries SQL en SQLite: SELECT, INSERT, ver tablas, construir queries. Acciones: status, query, tables, build_insert, build_select.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, query, tables, build_insert, build_select"},
            "db": {"type": "STRING", "description": "Database file path"},
            "query": {"type": "STRING", "description": "SQL query"},
            "table": {"type": "STRING", "description": "Table name"},
            "columns": {"type": "STRING", "description": "Columns to select"},
            "where": {"type": "STRING", "description": "WHERE clause"},
            "data": {"type": "OBJECT", "description": "Data for INSERT"},
        }, "required": ["action"]}
    },

    # ── DB Schema Visualizer ──
    {
        "name": "db_schema_visualizer",
        "description": "Visualizar esquemas de base de datos: texto, Mermaid ERD, JSON. Acciones: status, visualize.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, visualize"},
            "db": {"type": "STRING", "description": "Database file path"},
            "format": {"type": "STRING", "description": "text, mermaid, or json"},
        }, "required": ["action"]}
    },

    # ── Test Runner ──
    {
        "name": "test_runner",
        "description": "Ejecutar tests: pytest, unittest, npm test. Descubre archivos de test. Acciones: status, run, discover.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, run, discover"},
            "path": {"type": "STRING", "description": "Test directory or file"},
            "framework": {"type": "STRING", "description": "auto, pytest, unittest, node"},
            "verbose": {"type": "BOOLEAN", "description": "Verbose output"},
        }, "required": ["action"]}
    },

    # ── Coverage Reporter ──
    {
        "name": "coverage_reporter",
        "description": "Reporte de cobertura de tests: ejecutar pytest-cov, analizar archivos peor cubiertos. Acciones: status, run, report.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, run, report"},
            "path": {"type": "STRING", "description": "Source directory to measure"},
            "test_path": {"type": "STRING", "description": "Test directory"},
        }, "required": ["action"]}
    },

    # ── System Health ──
    {
        "name": "system_health",
        "description": "Dashboard de salud del sistema: CPU, RAM, disco, red, uptime, procesos top, bateria, temperaturas. Acciones: status, top_processes, battery, temperature.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, top_processes, battery, temperature"},
        }, "required": ["action"]}
    },

    # ── Alert Rules ──
    {
        "name": "alert_rules",
        "description": "Reglas de alerta: notificar si CPU/RAM supera umbral. Acciones: status, add, list, check, remove.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, add, list, check, remove"},
            "name": {"type": "STRING", "description": "Rule name"},
            "metric": {"type": "STRING", "description": "cpu or ram"},
            "threshold": {"type": "NUMBER", "description": "Threshold percentage"},
            "condition": {"type": "STRING", "description": "above or below"},
        }, "required": ["action"]}
    },

    # ── Cron Scheduler ──
    {
        "name": "cron_scheduler",
        "description": "Tareas programadas: crear, listar, ejecutar, verificar pendientes. Acciones: status, add, list, remove, execute, check_due.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, add, list, remove, execute, check_due"},
            "name": {"type": "STRING", "description": "Job name"},
            "schedule": {"type": "STRING", "description": "hourly, daily, weekly"},
            "command": {"type": "STRING", "description": "Command to execute"},
            "time": {"type": "STRING", "description": "Time to run (HH:MM)"},
        }, "required": ["action"]}
    },

    # ── Workflow Builder ──
    {
        "name": "workflow_builder",
        "description": "Crear workflows: pasos if/then/else, ejecutar secuencias. Acciones: status, create, list, execute, remove.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, create, list, execute, remove"},
            "name": {"type": "STRING", "description": "Workflow name"},
            "steps": {"type": "ARRAY", "items": {"type": "OBJECT"}, "description": "Workflow steps"},
        }, "required": ["action"]}
    },

    # ── Dependency Vulnerability Scanner ──
    {
        "name": "dep_vuln_scanner",
        "description": "Escanear vulnerabilidades en dependencias: pip-audit, npm audit. Acciones: status, scan_pip, scan_npm, scan_requirements.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, scan_pip, scan_npm, scan_requirements"},
            "path": {"type": "STRING", "description": "Project directory"},
            "file": {"type": "STRING", "description": "Requirements file path"},
        }, "required": ["action"]}
    },

    # ── Secret Scanner ──
    {
        "name": "secret_scanner",
        "description": "Escanear secrets hardcodeados: AWS keys, tokens, passwords, private keys, API keys. Acciones: status, scan, scan_file.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, scan, scan_file"},
            "path": {"type": "STRING", "description": "Directory to scan"},
            "file": {"type": "STRING", "description": "Specific file to scan"},
            "extensions": {"type": "ARRAY", "description": "File extensions to scan", "items": {"type": "STRING"}},
        }, "required": ["action"]}
    },

    # ── Model Evaluator ──
    {
        "name": "model_evaluator",
        "description": "Evaluar modelos IA: benchmark, historial, metricas. Acciones: status, evaluate, benchmark, history.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, evaluate, benchmark, history"},
            "model": {"type": "STRING", "description": "Model name"},
            "prompt": {"type": "STRING", "description": "Test prompt"},
            "expected": {"type": "STRING", "description": "Expected output"},
            "metric": {"type": "STRING", "description": "Metric to measure"},
            "models": {"type": "ARRAY", "description": "Models to benchmark", "items": {"type": "STRING"}},
            "prompts": {"type": "ARRAY", "description": "Prompts to test", "items": {"type": "STRING"}},
        }, "required": ["action"]}
    },

    # ── Prompt Optimizer ──
    {
        "name": "prompt_optimizer",
        "description": "Optimizar prompts: analizar calidad, sugerir mejoras, agregar contexto, rol, ejemplos. Acciones: status, optimize, analyze.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, optimize, analyze"},
            "prompt": {"type": "STRING", "description": "Prompt to optimize"},
            "technique": {"type": "STRING", "description": "auto, clarity, structure, examples, constraints, role"},
        }, "required": ["action"]}
    },

    # ── Docstring Generator ──
    {
        "name": "docstring_generator",
        "description": "Generar docstrings automaticamente: analizar Python, detectar sin docstring, generar templates. Acciones: status, analyze, generate, scan_directory.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, analyze, generate, scan_directory"},
            "file": {"type": "STRING", "description": "Python file to analyze"},
            "path": {"type": "STRING", "description": "Directory to scan"},
        }, "required": ["action"]}
    },

    # ── Changelog Generator ──
    {
        "name": "changelog_generator",
        "description": "Generar changelog desde git: commits recientes, desde tag, categorizar (features, fixes, docs). Acciones: status, generate, since_tag.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, generate, since_tag"},
            "path": {"type": "STRING", "description": "Git repository path"},
            "days": {"type": "NUMBER", "description": "Days of history"},
            "tag": {"type": "STRING", "description": "Git tag to compare from"},
            "output": {"type": "STRING", "description": "Output file path"},
        }, "required": ["action"]}
    },

    # ── Batch 6: Page/Video Summarizer ──

    {
        "name": "page_summarizer",
        "description": "Resume paginas web, videos de YouTube, o cualquier contenido de una URL. Extrae el contenido principal y genera un resumen conciso. Acciones: summarize_url (resumir URL), summarize (resumir texto), youtube (resumir video), save (resumir y guardar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "summarize_url, summarize, youtube, save"},
                "url": {"type": "STRING", "description": "URL de la pagina o video a resumir"},
                "text": {"type": "STRING", "description": "Texto a resumir (para summarize)"},
                "video_id": {"type": "STRING", "description": "ID del video de YouTube (para youtube)"},
                "query": {"type": "STRING", "description": "Pregunta/foco del resumen"},
                "max_chars": {"type": "INTEGER", "description": "Maximo de caracteres del contenido (default 2000)"},
            },
            "required": ["action"],
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
                "data": {"type": "STRING", "description": "Alias de rows (filas a crear en excel_create)"},
                "cell": {"type": "STRING", "description": "Referencia de celda para excel_write, ej: 'B2'"},
                "value": {"type": "STRING", "description": "Valor a escribir en la celda"},
                "row": {"type": "STRING", "description": "JSON array con los valores de la fila a añadir en excel_write, ej: [\"Marzo\",200]"},
                "max_rows": {"type": "INTEGER", "description": "Maximo de filas a mostrar en excel_read (default 20)"},
                "title": {"type": "STRING", "description": "Titulo del documento o presentacion"},
                "paragraphs": {"type": "STRING", "description": "JSON array de parrafos para word_create, ej: [\"Parrafo 1\",\"Parrafo 2\"]"},
                "max_paragraphs": {"type": "INTEGER", "description": "Maximo de parrafos a mostrar en word_read (default 25)"},
                "slides": {"type": "STRING", "description": "JSON array de diapositivas {title, bullets} para pptx_create, ej: [{\"title\":\"Resumen\",\"bullets\":[\"Punto 1\"]}]"},
            },
            "required": ["action", "path"],
        }
    },

    # ── Batch 8: Volumen y pantalla ──

    {
        "name": "system_volume",
        "description": "Control del volumen y audio del sistema (Windows: pycaw; Linux: pactl/wpctl). Acciones: get (volumen actual), set (level 0-100), up/down (step), mute, unmute, toggle_mute, devices (listar dispositivos de audio), set_device (device: nombre o indice para cambiar el dispositivo de reproduccion).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "get, set, up, down, mute, unmute, toggle_mute, devices, set_device"},
                "level": {"type": "INTEGER", "description": "Nivel de volumen 0-100 para set"},
                "step": {"type": "INTEGER", "description": "Incremento/decremento para up/down (default 10)"},
                "device": {"type": "STRING", "description": "Nombre o indice del dispositivo de reproduccion para set_device"},
                "value": {"type": "STRING", "description": "Valor alternativo de volumen (alias de level)"},
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
                "value": {"type": "INTEGER", "description": "Valor de brillo 0-100 (alias de level)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "wolfram_alpha",
        "description": "Respuestas computacionales via Wolfram Alpha: matematicas, unidades, datos cientificos. IMPORTANTE: envia el query TRADUCIDO AL INGLES (ej. '15% de 800' -> '15% of 800', 'masa de la Tierra' -> 'mass of the Earth').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Consulta en INGLES (ej. '15% of 800', 'mass of the Earth')"},
                "question": {"type": "STRING", "description": "Alias de query"},
            },
            "required": ["query"],
        }
    },

    # ── Section: Superinteligencia — Features #1-#36 ──

    {
        "name": "reflection",
        "description": "Reflexión profunda: analiza el estado actual de un problema o tarea, evalúa qué se hizo bien/mal, y sugiere próximos pasos. Usa para evaluar progreso, detectar errores estratégicos, y mejorar la calidad del trabajo.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task": {"type": "STRING", "description": "Descripción de la tarea o problema a reflexionar"},
                "context": {"type": "STRING", "description": "Contexto adicional (qué se hizo, qué pasó)"},
                "quick": {"type": "BOOLEAN", "description": "Si True, reflexión rápida (sin LLM)"},
            },
            "required": ["task"],
        }
    },
    {
        "name": "skill_recommender",
        "description": "Recomienda skills del sistema para una tarea dada. Analiza la query del usuario y sugiere qué skills cargar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Descripción de la tarea del usuario"},
            },
            "required": ["query"],
        }
    },
    {
        "name": "progressive_context",
        "description": "Construye contexto progresivo para una tarea: nivel 1 (resumen mínimo), nivel 2 (básico), nivel 3 (completo). Ahorra tokens cargando solo lo necesario.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task": {"type": "STRING", "description": "Tarea para la que se necesita contexto"},
                "level": {"type": "INTEGER", "description": "Nivel de contexto: 1=minimo, 2=basico, 3=completo"},
            },
            "required": ["task"],
        }
    },
    {
        "name": "tool_cache",
        "description": "Cache de resultados de herramientas. Acciones: get (obtener resultado cacheado), stats (estadísticas del cache), clear (limpiar). Reduce llamadas repetitivas a tools.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "get, stats, clear"},
                "key": {"type": "STRING", "description": "Clave del cache (para get)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "verification_layer",
        "description": "Verifica la calidad de un output de herramienta: detecta HTML incompleto, JSON roto, respuestas vacías, y sugiere correcciones.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "output": {"type": "STRING", "description": "Output a verificar"},
                "tool_name": {"type": "STRING", "description": "Nombre de la tool que generó el output"},
            },
            "required": ["output"],
        }
    },
    {
        "name": "plan_adaptation",
        "description": "Adapta un plan existente cuando algo falla o cambian las condiciones. Sugiere cómo modificar los pasos sin empezar de cero.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "plan": {"type": "STRING", "description": "Plan actual (JSON de pasos o texto)"},
                "failure": {"type": "STRING", "description": "Qué falló o cambió"},
                "context": {"type": "STRING", "description": "Contexto adicional"},
            },
            "required": ["plan", "failure"],
        }
    },
    {
        "name": "prompt_compressor",
        "description": "Comprime historial de conversación para ahorrar tokens. Mantiene contexto esencial, elimina redundancias. Útil cuando el contexto se acerca al límite.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "history": {"type": "STRING", "description": "Historial de conversación a comprimir"},
                "target_tokens": {"type": "INTEGER", "description": "Tokens objetivo (default 2000)"},
            },
            "required": ["history"],
        }
    },
    {
        "name": "knowledge_distiller",
        "description": "Extrae patrones de conocimiento de interacciones pasadas: qué funcionó, qué no, y reglas reutilizables. Aprende de la experiencia acumulada.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "interaction": {"type": "STRING", "description": "Interacción o resultado a analizar"},
                "category": {"type": "STRING", "description": "Categoría: tool_usage, planning, debugging, etc."},
            },
            "required": ["interaction"],
        }
    },
    {
        "name": "agent_as_tool",
        "description": "Delega una sub-tarea a un agente autónomo especializado. Útil para tareas complejas que benefit de un enfoque aislado con contexto propio.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task": {"type": "STRING", "description": "Sub-tarea a delegar"},
                "context": {"type": "STRING", "description": "Contexto para el sub-agente"},
                "suggested_tools": {"type": "STRING", "description": "Tools sugeridas para el sub-agente (comma-separated)"},
            },
            "required": ["task"],
        }
    },
    {
        "name": "batch_executor",
        "description": "Ejecuta múltiples tareas independientes en paralelo. Reduce tiempo total cuando hay 3+ tareas que no dependen entre sí.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tasks": {"type": "STRING", "description": "Lista de tareas a ejecutar (JSON array)"},
                "parallel": {"type": "BOOLEAN", "description": "Ejecutar en paralelo (default true)"},
            },
            "required": ["tasks"],
        }
    },
    {
        "name": "cost_tracker",
        "description": "Tracking de costos de API/LLM. Acciones: record (registrar llamada), session (costo de sesión actual), daily (costo del día), reset (resetear sesión).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "record, session, daily, reset"},
                "provider": {"type": "STRING", "description": "Proveedor: openrouter, ollama, gemini"},
                "model": {"type": "STRING", "description": "Modelo usado"},
                "input_tokens": {"type": "INTEGER", "description": "Tokens de entrada"},
                "output_tokens": {"type": "INTEGER", "description": "Tokens de salida"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "error_recovery",
        "description": "Recuperación automática de errores de herramientas. Diagnosticar el error, intentar fix automático, y sugerir alternativas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "diagnose (diagnosticar), recover (intentar recuperación), alternatives (ver alternativas)"},
                "tool_name": {"type": "STRING", "description": "Nombre de la tool que falló"},
                "error": {"type": "STRING", "description": "Mensaje de error"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "metrics_dashboard",
        "description": "Dashboard de métricas del agente: uso de tools, llamadas LLM, cache hits, errores. Acciones: summary (resumen), tools (métricas por tool), llm (métricas LLM), errors (errores recientes).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "summary, tools, llm, errors"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "intent_classifier",
        "description": "Clasifica la intención de una query o acción: coding, debugging, research, file_management, git, memory, planning, creative, chat, system. Ayuda a enfocar el approach correcto.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Query o descripción de la intención"},
            },
            "required": ["query"],
        }
    },
    {
        "name": "conversation_brancher",
        "description": "Explora alternativas de una conversación: genera branches de diferentes approaches para una misma pregunta, y permite compararlos.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question": {"type": "STRING", "description": "Pregunta o situación a explorar"},
                "num_branches": {"type": "INTEGER", "description": "Número de alternativas (default 3)"},
            },
            "required": ["question"],
        }
    },
    {
        "name": "auto_documenter",
        "description": "Genera documentación automática: changelogs, READMEs, análisis de código para docs, y sugerencias de migración.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "changelog, readme, analyze, migrate"},
                "path": {"type": "STRING", "description": "Path del archivo/directorio a documentar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "tool_dep_graph",
        "description": "Grafo de dependencias de herramientas: qué tools dependen de qué otras, qué corre en paralelo, y cuáles son críticas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "critical (tools críticas), parallel (grupos paralelos), deps (dependencias de una tool)"},
                "tool": {"type": "STRING", "description": "Nombre de la tool (para deps)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "smart_retry",
        "description": "Reintento inteligente: backoff exponencial con jitter para errores transitorios. Evita saturar APIs y maneja rate limits automáticamente.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "execute (ejecutar con retry), status (ver estado de reintentos)"},
                "tool": {"type": "STRING", "description": "Tool a reintentar"},
                "args": {"type": "STRING", "description": "Argumentos de la tool (JSON)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_evolving_prompts",
        "description": "Auto-evolución de prompts: aprende de cada ejecución qué funciona y qué no, y mejora los system prompts automáticamente.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "learn (aprender de resultado), rules (ver reglas aprendidas), clear (limpiar reglas)"},
                "tool": {"type": "STRING", "description": "Tool ejecutada"},
                "duration": {"type": "NUMBER", "description": "Duración de la ejecución"},
                "success": {"type": "BOOLEAN", "description": "Si fue exitosa"},
                "error": {"type": "STRING", "description": "Error si falló"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "semantic_deduplicator",
        "description": "Deduplicación semántica de memorias: fusiona entradas duplicadas o muy similares en episodic.json y semantic.json. Libera espacio y mejora calidad.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "episodic, semantic, all"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "adaptive_temperature",
        "description": "Temperatura dinámica del LLM: ajusta automáticamente la creatividad según la tarea (0.0 para código/debug, 0.7 para brainstorming).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Query para determinar la temperatura óptima"},
                "override": {"type": "NUMBER", "description": "Override manual de temperatura (0.0-0.9)"},
            },
            "required": ["query"],
        }
    },
    {
        "name": "task_tree",
        "description": "Árbol de descomposición de tareas con dependencias: topological sort, ejecución paralela de tareas independientes, re-planificación dinámica.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "decompose (descomponer objetivo), status (ver estado), next (siguientes tareas listas)"},
                "goal": {"type": "STRING", "description": "Objetivo a descomponer"},
                "task_id": {"type": "STRING", "description": "ID de tarea a marcar completada/fallida"},
                "result": {"type": "STRING", "description": "Resultado de la tarea"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "proactive_suggester",
        "description": "Sugerencias proactivas después de completar tareas: sugiere qué hacer después basándose en patrones, contexto y hora del día.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task": {"type": "STRING", "description": "Tarea completada"},
                "tool_used": {"type": "STRING", "description": "Tool que se usó"},
                "result": {"type": "STRING", "description": "Resultado de la tarea"},
            },
            "required": ["task"],
        }
    },
    {
        "name": "conversation_replayer",
        "description": "Reproduce sesiones de conversación pasadas: ver qué hizo el agente, por qué, y aprender de sesiones anteriores.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list (listar sesiones), view (ver sesión), tools (extraer secuencia de tools)"},
                "session_id": {"type": "STRING", "description": "ID de la sesión"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "smart_file_organizer",
        "description": "Organizador inteligente de archivos: detecta patrones de uso, sugiere archivos relacionados, y encuentra archivos huérfanos.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "related (archivos relacionados), orphans (archivos huérfanos), stats (estadísticas de uso)"},
                "path": {"type": "STRING", "description": "Path del archivo a analizar"},
                "directory": {"type": "STRING", "description": "Directorio para buscar huérfanos"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "context_optimizer",
        "description": "Optimización de ventana de contexto: calcula presupuesto óptimo de tokens por sección (system, history, tools, response) según el proveedor y complejidad.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "budget (calcular presupuesto), optimize (optimizar mensajes)"},
                "provider": {"type": "STRING", "description": "Proveedor: openrouter, ollama, gemini"},
                "complexity": {"type": "INTEGER", "description": "Complejidad: 1=simple, 2=media, 3=compleja"},
                "messages": {"type": "STRING", "description": "Mensajes a optimizar (JSON, para optimize)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "backup_prioritizer",
        "description": "Priorización inteligente de respaldos: clasifica archivos por criticidad, detecta cuáles necesitan backup, y sugiere orden óptimo.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "prioritize (listar con prioridad), stats (estadísticas), mark (marcar como respaldado)"},
                "directory": {"type": "STRING", "description": "Directorio a analizar"},
                "path": {"type": "STRING", "description": "Path a marcar como respaldado"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "skill_creator",
        "description": "Creador automático de skills: detecta patrones repetitivos en tools usadas, y crea skills YAML para automatizarlos.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "detect (detectar patrones), create (crear skill de patrón), suggest (sugerir skills)"},
                "pattern": {"type": "STRING", "description": "Patrón a crear como skill (para create)"},
                "name": {"type": "STRING", "description": "Nombre del skill (para create)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "error_pattern_db",
        "description": "Base de datos de errores y soluciones: registra errores, busca soluciones conocidas, y aprende de cada fix para el futuro.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "record (registrar error), solution (registrar solución), find (buscar solución), stats (estadísticas)"},
                "error": {"type": "STRING", "description": "Mensaje de error (para record/find)"},
                "tool": {"type": "STRING", "description": "Tool que falló"},
                "solution": {"type": "STRING", "description": "Solución aplicada (para solution)"},
                "error_id": {"type": "STRING", "description": "ID del error (para solution)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "session_debugger",
        "description": "Debugger de sesiones: analiza qué pasos ejecutó el agente, detecta errores, cuellos de botella, y compara sesiones.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze (analizar sesión), compare (comparar sesiones), report (reporte legible)"},
                "session_id": {"type": "STRING", "description": "ID de la sesión"},
                "session2": {"type": "STRING", "description": "Segunda sesión (para compare)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "capability_assessor",
        "description": "Auto-evaluación de capacidades del agente: score general del agente, áreas débiles, y sugerencias de mejora por categoría.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "score (score general), weak (áreas débiles), full (evaluación completa), record (registrar uso de tool)"},
                "tool": {"type": "STRING", "description": "Tool usada (para record)"},
                "success": {"type": "BOOLEAN", "description": "Si tuvo éxito (para record)"},
            },
            "required": ["action"],
        }
    },

    # ── Section: Superinteligencia batch 2 — Features #37-#45 ──

    {
        "name": "feedback_learner",
        "description": "Aprende del feedback del usuario (👍/👎). Registra qué respuestas le gustan y ajusta estilo/futuras respuestas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "record (registrar feedback), stats (estadísticas), style (estilo preferido), report (reporte completo)"},
                "response_summary": {"type": "STRING", "description": "Resumen de la respuesta (para record)"},
                "positive": {"type": "BOOLEAN", "description": "True=👍, False=👎 (para record)"},
                "topic": {"type": "STRING", "description": "Tema de la respuesta (para record)"},
                "style": {"type": "STRING", "description": "Estilo: brief, detailed, code_focused, etc. (para record)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_explainer",
        "description": "Explica POR QUÉ el agente tomó una decisión. Genera explicaciones claras de razonamiento, alternativas descartadas, y riesgos.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "explain (explicar decisión), tool_choice (explicar elección de tool), error (explicar manejo de error)"},
                "decision": {"type": "STRING", "description": "Decisión a explicar"},
                "alternatives": {"type": "STRING", "description": "Alternativas consideradas (comma-separated)"},
                "tool_name": {"type": "STRING", "description": "Tool elegida (para tool_choice)"},
                "task": {"type": "STRING", "description": "Tarea (para tool_choice)"},
                "error": {"type": "STRING", "description": "Error (para error)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "meta_reasoner",
        "description": "Analiza la CALIDAD del proceso de razonamiento: lógica, evidencia, sesgos, saltos. Actúa como crítico interno.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze (análisis completo), quick (check rápido)"},
                "reasoning": {"type": "STRING", "description": "Proceso de pensamiento a analizar"},
                "decision": {"type": "STRING", "description": "Decisión final"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "multi_agent",
        "description": "Orquesta múltiples agentes con roles (researcher, implementer, reviewer, planner, documenter). Negociación, estado compartido, workflow.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run (ejecutar tarea multi-agente), workflow (ejecutar workflow completo), negotiate (negociar consenso), status (ver estado)"},
                "task": {"type": "STRING", "description": "Tarea a orquestar"},
                "roles": {"type": "STRING", "description": "Roles a usar (comma-separated: researcher,implementer,reviewer)"},
                "context": {"type": "STRING", "description": "Contexto adicional"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "learning_curriculum",
        "description": "Currículum de auto-mejora estructurado: identifica debilidades, crea ejercicios, rastrea progreso.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "next (siguiente ejercicio), complete (marcar completado), progress (ver progreso), focus (área a enfocar)"},
                "category": {"type": "STRING", "description": "Categoría (coding, debugging, research, planning, communication)"},
                "exercise": {"type": "STRING", "description": "Ejercicio completado (para complete)"},
                "success": {"type": "BOOLEAN", "description": "Si fue exitoso (para complete)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "session_analytics",
        "description": "Analítica de sesiones de usuario: horas pico, tools más usadas, tendencias de uso, reportes diarios.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "patterns (patrones de uso), daily (reporte diario), record (registrar sesión)"},
                "session_id": {"type": "STRING", "description": "ID de sesión (para record)"},
                "duration": {"type": "NUMBER", "description": "Duración en segundos (para record)"},
                "messages": {"type": "INTEGER", "description": "Número de mensajes (para record)"},
                "tools": {"type": "STRING", "description": "Tools usadas comma-separated (para record)"},
                "topics": {"type": "STRING", "description": "Topics comma-separated (para record)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "knowledge_verifier",
        "description": "Verifica hechos antes de afirmarlos: busca en RAG y memoria semántica, genera veredicto (supported/contradicted/unverifiable).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "verify (verificar claim), batch (verificar múltiples), safe (verificar si es seguro afirmar)"},
                "claim": {"type": "STRING", "description": "Afirmación a verificar"},
                "claims": {"type": "STRING", "description": "Claims separados por newline (para batch)"},
                "context": {"type": "STRING", "description": "Contexto adicional"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "resource_optimizer",
        "description": "Monitorea y optimiza recursos del sistema: CPU, RAM, disco, archivos temporales, procesos pesados.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status (ver recursos), clean (limpiar temporales), optimize (optimizar memoria), suggest (sugerencias)"},
                "dry_run": {"type": "BOOLEAN", "description": "Si True, solo reportar sin borrar (para clean, default true)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "dream_consolidator",
        "description": "Consolidación tipo sueño: fusiona memorias similares, extrae patrones, genera conexiones creativas entre recuerdos.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "consolidate (ejecutar consolidación), log (ver historial de sueños)"},
            },
            "required": ["action"],
        }
    },

    # ── Section: Superinteligencia batch 3 — Features #46-#53 ──

    {
        "name": "goal_tracker",
        "description": "Persistencia y seguimiento de objetivos a largo plazo: crear metas, sub-tareas, milestones, progreso, detectar estancamiento.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create (crear objetivo), update (actualizar progreso/estado), complete_st (completar sub-tarea), milestone (alcanzar milestone), active (ver activos), stalled (ver estancados), next (siguiente paso), summary (resumen)"},
                "goal_id": {"type": "STRING", "description": "ID del objetivo (para update/complete_st/milestone/next)"},
                "title": {"type": "STRING", "description": "Título (para create)"},
                "description": {"type": "STRING", "description": "Descripción (para create)"},
                "priority": {"type": "STRING", "description": "low/medium/high/critical (para create)"},
                "subtasks": {"type": "STRING", "description": "Sub-tareas separadas por newline (para create)"},
                "milestones": {"type": "STRING", "description": "Milestones separados por newline (para create)"},
                "state": {"type": "STRING", "description": "pending/active/blocked/completed/abandoned (para update)"},
                "progress": {"type": "INTEGER", "description": "0-100 (para update)"},
                "note": {"type": "STRING", "description": "Nota (para update)"},
                "subtask_index": {"type": "INTEGER", "description": "Índice de sub-tarea (para complete_st)"},
                "milestone_index": {"type": "INTEGER", "description": "Índice de milestone (para milestone)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "anomaly_detector",
        "description": "Detección de patrones inusuales: archivos modificados, código sospechoso (exec/eval/hardcoded secrets), logs anómalos, archivos gigantes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "snapshot (tomar snapshot de archivos), code (detectar código sospechoso), logs (analizar log file), sizes (archivos grandes), clean (limpiar baselines)"},
                "directory": {"type": "STRING", "description": "Directorio a analizar (para code, default: core/)"},
                "log_file": {"type": "STRING", "description": "Ruta del log (para logs)"},
                "threshold_mb": {"type": "NUMBER", "description": "Umbral en MB (para sizes, default: 5)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "confidence_scorer",
        "description": "Cuantifica confianza en respuestas: evidencia disponible, contradicciones, complejidad, historial de errores. Genera score 0-100.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "score (calificar claim), batch (calificar múltiples), batch_ev (calificar con evidencia pre-cargada)"},
                "claim": {"type": "STRING", "description": "Afirmación a calificar"},
                "evidence": {"type": "STRING", "description": "Evidencia disponible, separada por newline (para score)"},
                "topic": {"type": "STRING", "description": "Categoría del tema"},
                "context": {"type": "STRING", "description": "Contexto adicional"},
                "claims_json": {"type": "STRING", "description": "JSON array de claims con evidencia (para batch_ev)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "mistake_learner",
        "description": "Aprende de errores propios: registra mistakes, crea reglas 'nunca más', detecta errores recurrentes, sugiere prevención.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "record (registrar mistake), rule (crear regla), check (verificar si una acción viola reglas), related (buscar mistakes similares), unresolved (ver no resueltos), resolve (marcar resuelto), analysis (análisis de patrones)"},
                "pattern": {"type": "STRING", "description": "Patrón del error (para record)"},
                "cause": {"type": "STRING", "description": "Causa raíz (para record)"},
                "solution": {"type": "STRING", "description": "Solución aplicada (para record/resolve)"},
                "context": {"type": "STRING", "description": "Contexto (para record)"},
                "severity": {"type": "STRING", "description": "low/medium/high/critical (para record)"},
                "category": {"type": "STRING", "description": "Categoría (para record/rule)"},
                "trigger": {"type": "STRING", "description": "Trigger de la regla (para rule)"},
                "action_desc": {"type": "STRING", "description": "Acción a verificar (para check)"},
                "mistake_id": {"type": "STRING", "description": "ID del mistake (para resolve)"},
                "current_error": {"type": "STRING", "description": "Error actual para buscar similares (para related)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "context_bridge",
        "description": "Conecta contexto entre sesiones: intención pendiente, tareas incompletas, preguntas abiertas, sesiones relacionadas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "save (guardar contexto de sesión), resume (obtener contexto para continuar), link (vincular sesiones), related (sesiones relacionadas), complete_task (marcar tarea completa), answer_q (marcar pregunta respondida)"},
                "session_id": {"type": "STRING", "description": "ID de sesión"},
                "user_intent": {"type": "STRING", "description": "Intención del usuario (para save)"},
                "tasks_in_progress": {"type": "STRING", "description": "Tareas pendientes separadas por newline (para save)"},
                "open_questions": {"type": "STRING", "description": "Preguntas abiertas separadas por newline (para save)"},
                "key_decisions": {"type": "STRING", "description": "Decisiones clave separadas por newline (para save)"},
                "related_session": {"type": "STRING", "description": "Sesión relacionada (para link)"},
                "reason": {"type": "STRING", "description": "Razón de la vinculación (para link)"},
                "task_text": {"type": "STRING", "description": "Texto de tarea a completar (para complete_task)"},
                "question_text": {"type": "STRING", "description": "Texto de pregunta a responder (para answer_q)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_profiler",
        "description": "Perfil completo de archivos: tech stack, complejidad ciclomática, imports, quality score, clases/funciones, dependencias.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "file (perfil de un archivo), project (perfil del proyecto completo)"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo a perfilar (para file)"},
                "directories": {"type": "STRING", "description": "Directorios a analizar separados por newline (para project)"},
            },
            "required": ["action"],
        }
    },

    # ── Jarvis OS: HUD terminal + rutinas diarias ──
    {
        "name": "hud_terminal",
        "description": "HUD estilo terminal (tipo Jarvis OS): ventana flotante siempre encima que muestra vitales del sistema (CPU, RAM, disco, red, bateria), agenda/tareas, estado del audio (micro/altavoz, voz local, push-to-talk) y ultimos comandos. Acciones: start/on (abrir), stop/off (cerrar), toggle (default), status (estado).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, on, open (abrir), stop, off, close (cerrar), status (estado), info (render en texto)"},
            },
            "required": [],
        }
    },
    {
        "name": "rutinas_diarias",
        "description": "Rutinas diarias estilo Jarvis OS. Acciones: inbox/matutino (saludo + pendientes del vault Obsidian y tareas), plan (plan del dia: tareas, objetivos), metricas (CPU/RAM/disco/red/bateria), vault (guardar/leer notas Obsidian; pasar 'text' para guardar), cierre (resumen del dia y guardado en el vault), todas (todo junto).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "inbox, matutino, plan, metricas, vault, cierre, todas"},
                "text": {"type": "STRING", "description": "Texto a guardar en el vault (con action=vault)"},
                "nota": {"type": "STRING", "description": "Alias de text para guardar nota en el vault"},
                "note": {"type": "STRING", "description": "Alias de text/nota para guardar en el vault"},
            },
            "required": ["action"],
        }
    },

    # ── Level 10: Super Capabilities ──

    {
        "name": "web_search",
        "description": "Búsqueda web REAL-TIME en DuckDuckGo. Usá esto cuando necesités información actual, noticias, o cualquier cosa que Eris no tenga en su conocimiento local. Acciones: search (búsqueda general), news (noticias recientes), images (imágenes).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search, news, o images"},
                "query": {"type": "STRING", "description": "Término de búsqueda"},
                "max_results": {"type": "INTEGER", "description": "Máximo resultados (default 8, max 20)"},
            },
            "required": ["query"],
        }
    },
    {
        "name": "rag_engine",
        "description": "Búsqueda SEMÁNTICA (RAG) en el vault de Obsidian. Busca notas por SIGNIFICADO, no por nombre. Acciones: index (reindexar vault), search (buscar por significado), status, stats. Usá search cuando el usuario pregunte algo que esté en las notas del vault.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "index, search, status, stats"},
                "query": {"type": "STRING", "description": "Consulta semántica (para search)"},
                "top_k": {"type": "INTEGER", "description": "Número de resultados (default 5, max 15)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "browser_auto",
        "description": "Automatización de navegador con Playheadless. Abrir páginas, extraer texto, hacer click, escribir, ejecutar JS, sacar screenshots. Usá esto para interactuar con páginas web.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "open, screenshot, scrape, click, type, evaluate, links, close"},
                "url": {"type": "STRING", "description": "URL (para open)"},
                "selector": {"type": "STRING", "description": "Selector CSS (para click/type)"},
                "text": {"type": "STRING", "description": "Texto a escribir (para type)"},
                "script": {"type": "STRING", "description": "Código JavaScript (para evaluate)"},
                "max_chars": {"type": "INTEGER", "description": "Máximo chars (para scrape)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "browser_unified",
        "description": "Browser automation completo con Playwright. Navegar, forms, scraping, screenshots, PDFs, multi-tab, cookies persistentes, YouTube. USAR ESTO para TODO lo relacionado con navegador. Acciones: navigate, back, forward, reload, text, html, links, meta, click, fill, type, select, check, scroll, hover, key, wait, screenshot, pdf, js, upload, tabs, save, clear_cookies, play, status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "navigate, back, forward, reload, text, html, links, meta, click, fill, type, select, check, scroll, hover, key, wait, screenshot, pdf, js, upload, tabs, save, clear_cookies, play, status. play=buscar y reproducir en YouTube"},
                "url": {"type": "STRING", "description": "URL para navigate o play (reproducir video directo)"},
                "query": {"type": "STRING", "description": "Búsqueda para play en YouTube"},
                "selector": {"type": "STRING", "description": "Selector CSS para click/fill/type/etc"},
                "value": {"type": "STRING", "description": "Valor para fill/type/select"},
                "key": {"type": "STRING", "description": "Tecla para key (Enter, Tab, Escape, etc)"},
                "direction": {"type": "STRING", "description": "Dirección de scroll: up/down"},
                "amount": {"type": "INTEGER", "description": "Pixeles de scroll (default 500)"},
                "full_page": {"type": "BOOLEAN", "description": "Screenshot de página completa"},
                "expression": {"type": "STRING", "description": "Código JavaScript para js"},
                "path": {"type": "STRING", "description": "Path de archivo para upload o PDF"},
                "max_chars": {"type": "INTEGER", "description": "Máximo chars para text/html"},
                "name": {"type": "STRING", "description": "Nombre de tab para tabs"},
                "sub": {"type": "STRING", "description": "Sub-acción para tabs: list, new, close, switch"},
                "timeout": {"type": "INTEGER", "description": "Timeout en ms para wait"},
                "delay": {"type": "INTEGER", "description": "Delay entre teclas para type (ms)"},
                "checked": {"type": "BOOLEAN", "description": "Estado para check"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "advanced_rag",
        "description": "Búsqueda avanzada en la base de conocimiento de Eris. Hybrid BM25+semantic con cross-encoder re-ranking y citas [1][2]. Más preciso que document_rag para queries complejas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search, invalidate, stats"},
                "query": {"type": "STRING", "description": "Consulta de búsqueda"},
                "top_k": {"type": "INTEGER", "description": "Número de resultados (default 5)"},
                "rerank": {"type": "BOOLEAN", "description": "Usar cross-encoder re-ranking (default true)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_biometrics",
        "description": "Reconocimiento de voz para identificar al usuario. Permite enrollar perfiles de voz y identificar quién habla. Incluye anti-spoofing básico.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "identify, enroll, profiles, delete"},
                "name": {"type": "STRING", "description": "Nombre del hablante (para enroll/delete)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "proactive_monitor",
        "description": "Monitoreo proactivo de URLs, APIs, crypto. Detecta cambios y alerta automáticamente. Acciones: add (agregar monitor), remove (eliminar), list (ver todos), check (verificar ahora), alerts (ver alertas recientes).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, remove, list, check, alerts"},
                "name": {"type": "STRING", "description": "Nombre del monitor"},
                "url": {"type": "STRING", "description": "URL a monitorear (para type=url)"},
                "type": {"type": "STRING", "description": "url, crypto, api"},
                "interval": {"type": "INTEGER", "description": "Segundos entre checks (default 300)"},
                "keywords": {"type": "STRING", "description": "Keywords separadas por coma para filtrar"},
                "symbol": {"type": "STRING", "description": "Símbolo crypto para CoinGecko (para type=crypto)"},
                "threshold": {"type": "STRING", "description": "Umbral de cambio % para alertar"},
                "id": {"type": "STRING", "description": "ID del monitor (para remove)"},
                "limit": {"type": "INTEGER", "description": "Límite de alertas a mostrar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "email_manager",
        "description": "Gestión de email IMAP/SMTP. Leer, enviar, buscar emails. Acciones: count (no leídos), list (recientes), read (por ID), send (enviar), search (buscar), folders (carpetas).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "count, list, read, send, search, folders"},
                "to": {"type": "STRING", "description": "Destinatario (para send)"},
                "subject": {"type": "STRING", "description": "Asunto (para send)"},
                "body": {"type": "STRING", "description": "Cuerpo del email (para send)"},
                "query": {"type": "STRING", "description": "Término de búsqueda (para search)"},
                "id": {"type": "STRING", "description": "ID del email (para read)"},
                "folder": {"type": "STRING", "description": "Carpeta (para list)"},
                "max_emails": {"type": "INTEGER", "description": "Máximo emails"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "google_calendar",
        "description": "Google Calendar real. Crear, listar, eliminar eventos. Acciones: today, week, upcoming, create, delete, search. Requiere credentials.json en config/.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "today, week, upcoming, create, delete, search"},
                "summary": {"type": "STRING", "description": "Título del evento (para create)"},
                "start": {"type": "STRING", "description": "Fecha/hora inicio ISO (para create)"},
                "end": {"type": "STRING", "description": "Fecha/hora fin ISO (para create)"},
                "location": {"type": "STRING", "description": "Ubicación"},
                "event_id": {"type": "STRING", "description": "ID del evento (para delete)"},
                "query": {"type": "STRING", "description": "Búsqueda (para search)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "task_manager",
        "description": "Gestor de tareas Kanban con dependencias y deadlines. Agregar, listar, mover, buscar tareas. Estados: pending, in_progress, done, blocked, review. Prioridades: low, medium, high, urgent.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, list, move, update, delete, overdue, search, stats"},
                "title": {"type": "STRING", "description": "Título (para add)"},
                "task_id": {"type": "STRING", "description": "ID de tarea (para move/update/delete)"},
                "state": {"type": "STRING", "description": "Nuevo estado (para move) o filtro (para list)"},
                "priority": {"type": "STRING", "description": "low, medium, high, urgent"},
                "deadline": {"type": "STRING", "description": "Fecha límite ISO"},
                "deps": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "IDs de tareas de las que depende"},
                "query": {"type": "STRING", "description": "Término de búsqueda (para search)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "home_assistant",
        "description": "Control de domótica vía Home Assistant. Luces, switches, clima, media, notificaciones. Requiere configuración en api_keys.json.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "states, lights, switch, climate, media, notify, entities, service"},
                "entity_id": {"type": "STRING", "description": "ID de la entidad"},
                "command": {"type": "STRING", "description": "on/off/toggle/brightness/play/pause"},
                "brightness": {"type": "INTEGER", "description": "Brillo (0-255)"},
                "temperature": {"type": "NUMBER", "description": "Temperatura"},
                "message": {"type": "STRING", "description": "Mensaje (para notify)"},
                "domain": {"type": "STRING", "description": "Dominio (para service/entities)"},
                "service": {"type": "STRING", "description": "Servicio (para service)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "screen_context",
        "description": "Captura de pantalla + OCR + descripción visual. Sacar screenshots, extraer texto de la pantalla (OCR), analizar qué hay en pantalla. Usá esto cuando el usuario pregunte qué está viendo.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "capture, ocr, analyze, region, history"},
                "image": {"type": "STRING", "description": "Ruta de imagen (para ocr/analyze, opcional)"},
                "x": {"type": "INTEGER", "description": "X (para region)"},
                "y": {"type": "INTEGER", "description": "Y (para region)"},
                "width": {"type": "INTEGER", "description": "Ancho (para region)"},
                "height": {"type": "INTEGER", "description": "Alto (para region)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_cloning",
        "description": "Clonación de voz local con XTTS v2. Generar audio con voz clonada desde un archivo de referencia. Acciones: status, voices, clone (guardar referencia), speak (generar audio).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, voices, clone, speak"},
                "text": {"type": "STRING", "description": "Texto a convertir en audio (para speak)"},
                "voice": {"type": "STRING", "description": "Nombre de la voz clonada (para speak)"},
                "audio": {"type": "STRING", "description": "Ruta al audio de referencia (para clone)"},
                "name": {"type": "STRING", "description": "Nombre para la voz (para clone)"},
                "language": {"type": "STRING", "description": "Código de idioma (default es)"},
            },
            "required": ["action"],
        }
    },

    # ── Level 11: Extended Capabilities ──

    {
        "name": "code_sandbox",
        "description": "Ejecución segura de código Python en sandbox. Escribí y ejecutá código en tiempo real con timeout y restricciones de seguridad.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "exec, eval, version, packages"},
                "code": {"type": "STRING", "description": "Código Python a ejecutar (para exec/eval)"},
                "timeout": {"type": "INTEGER", "description": "Timeout en segundos (default 30, max 60)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "translator",
        "description": "Traducción automática entre 100+ idiomas. Auto-detecta idioma fuente. Usa Google Translate.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "translate, languages, batch"},
                "text": {"type": "STRING", "description": "Texto a traducir"},
                "target": {"type": "STRING", "description": "Idioma destino (en, es, fr, de, ja, zh, etc)"},
                "source": {"type": "STRING", "description": "Idioma fuente (auto-detect si vacío)"},
                "texts": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Textos múltiples (para batch)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "pdf_generator",
        "description": "Generar documentos PDF desde texto o markdown. Crear reportes, documentos, resúmenes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, from_markdown, list, info"},
                "title": {"type": "STRING", "description": "Título del documento"},
                "content": {"type": "STRING", "description": "Contenido del PDF"},
                "output": {"type": "STRING", "description": "Nombre del archivo de salida"},
                "font_size": {"type": "INTEGER", "description": "Tamaño de fuente (default 12)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "rss_reader",
        "description": "Lector de feeds RSS/Atom. Suscribirse a feeds, leer entradas, buscar noticias nuevas, alertar sobre contenido actualizado.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, list, read, remove, check, search"},
                "url": {"type": "STRING", "description": "URL del feed RSS"},
                "name": {"type": "STRING", "description": "Nombre de la suscripción"},
                "query": {"type": "STRING", "description": "Término de búsqueda"},
                "max_entries": {"type": "INTEGER", "description": "Máximo entradas (default 10)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "vault_passwords",
        "description": "Gestor de contraseñas con vault local encriptado (Fernet + PBKDF2). Agregar, buscar, generar contraseñas seguras. NUNCA almacena la contraseña maestra.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "init, add, get, list, search, delete, generate, export, change_master"},
                "master": {"type": "STRING", "description": "Contraseña maestra"},
                "site": {"type": "STRING", "description": "Nombre del sitio/servicio"},
                "username": {"type": "STRING", "description": "Usuario"},
                "password": {"type": "STRING", "description": "Contraseña"},
                "notes": {"type": "STRING", "description": "Notas adicionales"},
                "category": {"type": "STRING", "description": "Categoría (trabajo, personal, banking, etc)"},
                "query": {"type": "STRING", "description": "Término de búsqueda"},
                "length": {"type": "INTEGER", "description": "Largo de contraseña generada (default 16)"},
                "new_master": {"type": "STRING", "description": "Nueva contraseña maestra (para change_master)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "ssh_remote",
        "description": "Ejecución remota vía SSH. Conectar a servidores, ejecutar comandos, subir/bajar archivos. Usa paramiko.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "connect, exec, upload, download, disconnect, list_sessions"},
                "host": {"type": "STRING", "description": "Host o IP del servidor"},
                "port": {"type": "INTEGER", "description": "Puerto SSH (default 22)"},
                "username": {"type": "STRING", "description": "Usuario SSH"},
                "password_or_key_path": {"type": "STRING", "description": "Contraseña o ruta a clave privada"},
                "command": {"type": "STRING", "description": "Comando a ejecutar (para exec)"},
                "local_path": {"type": "STRING", "description": "Ruta local (para upload/download)"},
                "remote_path": {"type": "STRING", "description": "Ruta remota (para upload/download)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "git_smart",
        "description": "Git inteligente con auto-commit messages. Genera mensajes descriptivos automáticamente analizando los cambios.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "auto_commit, status, diff, log, branches, stash, prune_merged"},
                "repo_path": {"type": "STRING", "description": "Ruta del repositorio (default: directorio actual)"},
                "file": {"type": "STRING", "description": "Archivo específico (para diff)"},
                "count": {"type": "INTEGER", "description": "Número de commits (para log, default 10)"},
                "push": {"type": "BOOLEAN", "description": "Hacer push después de commit"},
                "message": {"type": "STRING", "description": "Mensaje para stash"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "sql_manager",
        "description": "Gestor de bases de datos SQL. Conectar a SQLite o PostgreSQL, ejecutar queries, ver tablas, exportar resultados.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "connect, query, execute, tables, schema, export, disconnect, status"},
                "db_path": {"type": "STRING", "description": "Ruta de DB SQLite (para connect)"},
                "host": {"type": "STRING", "description": "Host PostgreSQL"},
                "port": {"type": "INTEGER", "description": "Puerto PostgreSQL"},
                "user": {"type": "STRING", "description": "Usuario PostgreSQL"},
                "pass": {"type": "STRING", "description": "Contraseña PostgreSQL"},
                "db": {"type": "STRING", "description": "Nombre de base de datos"},
                "sql": {"type": "STRING", "description": "Sentencia SQL"},
                "table": {"type": "STRING", "description": "Nombre de tabla (para schema)"},
                "format": {"type": "STRING", "description": "Formato de export: json o csv"},
                "output": {"type": "STRING", "description": "Archivo de salida (para export)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "spotify_control",
        "description": "Control de Spotify. Play, pausa, siguiente, anterior, volumen, buscar, playlist. Requiere SPOTIPY_CLIENT_ID/SECRET.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, play, pause, next, previous, volume, search, queue, devices, playlist"},
                "query": {"type": "STRING", "description": "Busqueda o nombre de track/artist/album"},
                "level": {"type": "INTEGER", "description": "Volumen 0-100"},
                "type": {"type": "STRING", "description": "Tipo de busqueda: track, artist, album"},
                "playlist_id": {"type": "STRING", "description": "ID de playlist"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "eris_updater",
        "description": "Auto-actualización de Eris. Verificar nuevas versiones, changelog, descargar y aplicar actualizaciones.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "check, changelog, update, version, history, rollback"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "memory_consolidator",
        "description": "Consolidación de memoria. Resumir memorias similares, fusionar duplicados, podar entradas viejas, backup.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "consolidate, summary, prune, search, backup"},
                "days": {"type": "INTEGER", "description": "Días para pods/consolidar (default 30)"},
                "query": {"type": "STRING", "description": "Término de búsqueda (para search)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "habit_tracker",
        "description": "Seguimiento de hábitos y rutinas. Registrar, rastrear streaks, estadísticas, recordatorios diarios.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, log, list, stats, streak, delete, reminders, export, leaderboard"},
                "habit_name": {"type": "STRING", "description": "Nombre del hábito"},
                "frequency": {"type": "STRING", "description": "daily, weekly, monthly"},
                "target": {"type": "INTEGER", "description": "Veces por período (default 1)"},
                "category": {"type": "STRING", "description": "Categoría (salud, trabajo, personal, etc)"},
                "notes": {"type": "STRING", "description": "Notas de la completación"},
                "period": {"type": "STRING", "description": "week, month, year (para stats)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "chart_generator",
        "description": "Generar gráficos y charts con matplotlib. Barras, líneas, torta, scatter, histograma, comparaciones.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "bar, line, pie, scatter, histogram, compare, list"},
                "title": {"type": "STRING", "description": "Título del gráfico"},
                "labels": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Etiquetas del eje X"},
                "values": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Valores"},
                "output": {"type": "STRING", "description": "Nombre del archivo PNG"},
                "color": {"type": "STRING", "description": "Color principal"},
                "series": {"type": "ARRAY", "items": {"type": "OBJECT"}, "description": "Series múltiples (para compare) — cada una con name y values"},
                "bins": {"type": "INTEGER", "description": "Bins para histograma (default 10)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "voice_translator",
        "description": "Traducción + voz. Traducir texto a otro idioma Y hablarlo. O solo traducir. Detectar idioma.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "translate_speak, translate_text, detect_language, speak_in"},
                "text": {"type": "STRING", "description": "Texto a traducir/hablar"},
                "target_lang": {"type": "STRING", "description": "Idioma destino (default en)"},
                "source_lang": {"type": "STRING", "description": "Idioma fuente (auto-detect si vacío)"},
                "lang": {"type": "STRING", "description": "Idioma para speak_in"},
            },
            "required": ["action"],
        }
    },

]

# ── Level 12: Advanced Autonomy ──
TOOL_DECLARATIONS.extend([
    {
        "name": "workflow_engine",
        "description": "Workflow/skill chaining engine. Crear, ejecutar y gestionar flujos de trabajo multi-paso con triggers, condiciones y variables.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, list, run, delete, log, export, import"},
                "name": {"type": "STRING", "description": "Nombre del workflow"},
                "steps": {"type": "ARRAY", "items": {"type": "OBJECT"}, "description": "Lista de pasos [{step_id, tool, params, condition, on_fail}]"},
                "vars": {"type": "OBJECT", "description": "Variables para template substitution"},
                "workflow": {"type": "OBJECT", "description": "Workflow completo para export/import"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "auto_healer",
        "description": "Auto-healing profundo. Analiza tracebacks, fix de imports, error journal con patrones, sugerencias de mejora.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, fix_imports, error_journal, auto_fix, suggest, status"},
                "traceback_str": {"type": "STRING", "description": "Traceback a analizar (action=analyze)"},
                "file_path": {"type": "STRING", "description": "Archivo a analizar (action=analyze, auto_fix)"},
                "dry_run": {"type": "BOOLEAN", "description": "Solo mostrar cambios sin aplicar (action=fix_imports)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "image_generator",
        "description": "Generador de imágenes con Pollinations.ai (gratis) y fallback a Stable Diffusion API.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "generate, from_url, info, history"},
                "prompt": {"type": "STRING", "description": "Descripción de la imagen a generar"},
                "style": {"type": "STRING", "description": "photorealistic, anime, digital_art, painting"},
                "width": {"type": "INTEGER", "description": "Ancho en px (default 512)"},
                "height": {"type": "INTEGER", "description": "Alto en px (default 512)"},
                "seed": {"type": "INTEGER", "description": "Seed para reproducibilidad (opcional)"},
                "url": {"type": "STRING", "description": "URL de imagen (action=from_url)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "clipboard_history",
        "description": "Gestor de historial de clipboard. Leer, buscar, fijar snippets, categorías, estadísticas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read, history, search, pin, pinned, unpin, clear, categories, add, stats"},
                "text": {"type": "STRING", "description": "Texto para clipboard o pin"},
                "query": {"type": "STRING", "description": "Búsqueda en historial"},
                "index": {"type": "INTEGER", "description": "Índice para unpin"},
                "category": {"type": "STRING", "description": "Categoría para pin"},
                "limit": {"type": "INTEGER", "description": "Máximo de items (default 20)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "finance_tracker",
        "description": "Tracker de finanzas personales. Importar CSV bancarios, categorizar, presupuestos, gráficos, suscripciones.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add_transaction, import_csv, transactions, summary, categories, budget, chart, subscriptions, search, export"},
                "amount": {"type": "NUMBER", "description": "Monto de transacción"},
                "description": {"type": "STRING", "description": "Descripción de la transacción"},
                "category": {"type": "STRING", "description": "Categoría"},
                "date": {"type": "STRING", "description": "Fecha (YYYY-MM-DD)"},
                "filepath": {"type": "STRING", "description": "Ruta del CSV"},
                "bank": {"type": "STRING", "description": "Banco: generic, galicia, macro, brubank, mercadopago"},
                "limit": {"type": "NUMBER", "description": "Límite de presupuesto"},
                "query": {"type": "STRING", "description": "Búsqueda de transacciones"},
                "type": {"type": "STRING", "description": "Tipo de gráfico: monthly, category, trend"},
                "month": {"type": "INTEGER", "description": "Mes para resumen"},
                "year": {"type": "INTEGER", "description": "Año para resumen"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "multi_ai_hub",
        "description": "Hub multi-proveedor de IA. Ollama, OpenRouter, OpenAI, Anthropic con routing inteligente y fallback.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, chat, providers, config, route, benchmark, fallback"},
                "message": {"type": "STRING", "description": "Mensaje a enviar"},
                "provider": {"type": "STRING", "description": "Proveedor específico"},
                "model": {"type": "STRING", "description": "Modelo específico"},
                "system": {"type": "STRING", "description": "System prompt"},
                "task_type": {"type": "STRING", "description": "code, chat, creative, analysis, translation"},
                "api_key": {"type": "STRING", "description": "API key del proveedor"},
                "priority": {"type": "INTEGER", "description": "Prioridad del proveedor"},
                "categories": {"type": "STRING", "description": "Categorías del proveedor"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "file_organizer",
        "description": "Organizador inteligente de archivos. Scan, organizar por reglas, duplicados, undo, historial.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan, organize, rules, add_rule, duplicates, history, undo, stats"},
                "directory": {"type": "STRING", "description": "Directorio a organizar (default ~/Downloads)"},
                "recursive": {"type": "BOOLEAN", "description": "Escanear subdirectorios"},
                "dry_run": {"type": "BOOLEAN", "description": "Solo mostrar plan sin ejecutar"},
                "pattern": {"type": "STRING", "description": "Patrón de archivos"},
                "destination": {"type": "STRING", "description": "Carpeta destino"},
                "move_action": {"type": "STRING", "description": "move o copy"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "knowledge_graph",
        "description": "Grafo de conocimiento del vault Obsidian. Relaciones, clústers, notas centrales, caminos, visualización ASCII.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "build, query, clusters, central, path, orphan, stats, export, visualize"},
                "note": {"type": "STRING", "description": "Nombre de nota a consultar"},
                "target": {"type": "STRING", "description": "Nota destino para path"},
                "depth": {"type": "INTEGER", "description": "Profundidad de búsqueda (default 1)"},
                "vault_path": {"type": "STRING", "description": "Ruta del vault"},
                "top": {"type": "INTEGER", "description": "Top N notas para visualize (default 20)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "test_generator",
        "description": "Generador automático de tests. Analiza código Python con AST, genera pytest, coverage, sugerencias.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan, generate, run, coverage, suggestions"},
                "file_path": {"type": "STRING", "description": "Ruta del módulo a analizar"},
                "output": {"type": "STRING", "description": "Ruta de salida para tests generados"},
                "module_name": {"type": "STRING", "description": "Nombre del módulo"},
            },
            "required": ["action"],
        }
    },
])

# ── Additional Features (N1.1-N3.4) ──
TOOL_DECLARATIONS.extend([
    {
        "name": "email_calendar_deep",
        "description": "Email/Calendar deep integration. Resumir inbox, count unread, smart reply, calendar today, followup tracker.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "inbox_summary, unread_count, smart_reply, calendar_today, followup_tracker"},
                "id": {"type": "STRING", "description": "Email ID (para smart_reply)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "knowledge_graph_adv",
        "description": "Knowledge graph avanzado de entidades y relaciones. Extrae y consulta relaciones entre conceptos del vault y conversaciones.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add_entity, add_relation, query, search, stats"},
                "name": {"type": "STRING", "description": "Nombre de la entidad"},
                "type": {"type": "STRING", "description": "Tipo de entidad (concept, person, place)"},
                "source": {"type": "STRING", "description": "Entidad origen (para add_relation)"},
                "relation": {"type": "STRING", "description": "Tipo de relación (para add_relation)"},
                "target": {"type": "STRING", "description": "Entidad destino (para add_relation)"},
                "context": {"type": "STRING", "description": "Contexto de la relación"},
                "query": {"type": "STRING", "description": "Término de búsqueda"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "multi_user_profiles",
        "description": "Multi-usuario con permisos, personalidad y contexto separado. Crear, cambiar, listar, eliminar usuarios.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "current, list, switch, create, delete"},
                "name": {"type": "STRING", "description": "Nombre del usuario"},
                "display_name": {"type": "STRING", "description": "Nombre para mostrar"},
                "role": {"type": "STRING", "description": "user o admin"},
                "personality": {"type": "STRING", "description": "Notas de personalidad para el usuario"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "llm_router",
        "description": "Router inteligente de LLMs. Selecciona el mejor modelo (Gemini/Ollama/OpenRouter) según calidad, costo, latencia y capacidades.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "select, registry, stats"},
                "quality_min": {"type": "STRING", "description": "Calidad mínima 1-10"},
                "max_cost": {"type": "STRING", "description": "Costo máximo por 1k tokens"},
                "max_latency": {"type": "STRING", "description": "Latencia máxima en ms"},
                "needs_tools": {"type": "STRING", "description": "Necesita tools (true/false)"},
                "needs_voice": {"type": "STRING", "description": "Necesita voz (true/false)"},
                "model": {"type": "STRING", "description": "Modelo específico (para stats)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "mcp_server",
        "description": "Servidor MCP (Model Context Protocol). Exponer tools de Eris a otros agents/LLMs vía JSON-RPC stdio.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, start, tools, call"},
                "tool_name": {"type": "STRING", "description": "Nombre de tool a ejecutar (para call)"},
                "tool_args": {"type": "STRING", "description": "Argumentos JSON de la tool (para call)"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "memory_search",
        "description": "Consolidación de memoria. Resumir conversaciones, extraer hechos clave, limpiar ruido, buscar en hechos históricos.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "consolidate, facts, search, summaries"},
                "messages": {"type": "STRING", "description": "JSON array de mensajes (para consolidate)"},
                "date": {"type": "STRING", "description": "Fecha YYYY-MM-DD (para consolidate)"},
                "query": {"type": "STRING", "description": "Término de búsqueda (para search)"},
                "limit": {"type": "STRING", "description": "Límite de resultados"},
                "days": {"type": "STRING", "description": "Días hacia atrás (para summaries)"},
            },
            "required": ["action"],
        }
    },
    # ── Coding Capabilities (M1-M4) ──
    {
        "name": "code_engineer",
        "description": "Ingeniero de código con reasoning loop completo: leer archivo → buscar patrón → editar con contexto → verificar. Soporta: read, search (grep), edit (replace exacto), insert (after/before), create, multi_edit (múltiples ediciones), backup/restore.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read, search, edit, insert, create, multi_edit, backup_list, restore"},
                "file": {"type": "STRING", "description": "Ruta del archivo"},
                "pattern": {"type": "STRING", "description": "Regex pattern para search"},
                "old": {"type": "STRING", "description": "Texto a reemplazar (para edit)"},
                "new": {"type": "STRING", "description": "Texto nuevo (para edit)"},
                "text": {"type": "STRING", "description": "Texto a insertar (para insert)"},
                "after": {"type": "STRING", "description": "Insertar después de este texto"},
                "before": {"type": "STRING", "description": "Insertar antes de este texto"},
                "content": {"type": "STRING", "description": "Contenido del archivo (para create)"},
                "edits": {"type": "STRING", "description": "JSON array [{old,new}] para multi_edit"},
                "offset": {"type": "INTEGER", "description": "Línea inicial para read"},
                "limit": {"type": "INTEGER", "description": "Máx líneas para read"},
                "preview": {"type": "STRING", "description": "true para ver diff antes de aplicar"},
                "backup": {"type": "STRING", "description": "Nombre del backup para restore"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "codebase_explorer",
        "description": "Exploración profunda de código: grep regex en archivos, glob por nombre, análisis de imports, dependency graph, find definitions/references, file stats, architecture map del proyecto completo.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "grep, glob, imports, graph, definitions, references, stats, architecture"},
                "pattern": {"type": "STRING", "description": "Regex (grep), glob pattern, o nombre (definitions/references)"},
                "file": {"type": "STRING", "description": "Archivo a analizar (imports, stats)"},
                "path": {"type": "STRING", "description": "Directorio raíz de búsqueda"},
                "include": {"type": "STRING", "description": "Filtro de archivos (regex)"},
                "exclude": {"type": "STRING", "description": "Excluir archivos (regex)"},
                "name": {"type": "STRING", "description": "Nombre de símbolo (definitions/references)"},
                "limit": {"type": "INTEGER", "description": "Máx resultados"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "devops_pipeline",
        "description": "Git workflow completo + test execution loop. Git: status, diff, commit, branch, merge, log, blame, stash. Tests: run, test_loop (run→fail→fix→re-run iterativo), run_command.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "git_status, git_diff, git_diff_staged, git_commit, git_log, git_branch, git_branch_create, git_branch_switch, git_merge, git_stash, git_stash_pop, git_blame, git_add, git_reset, run_tests, run_command, test_loop, project_info"},
                "message": {"type": "STRING", "description": "Commit message"},
                "files": {"type": "STRING", "description": "Archivos separados por coma"},
                "target": {"type": "STRING", "description": "Target para diff (default HEAD)"},
                "name": {"type": "STRING", "description": "Nombre de branch"},
                "branch": {"type": "STRING", "description": "Branch para merge"},
                "command": {"type": "STRING", "description": "Comando a ejecutar"},
                "timeout": {"type": "INTEGER", "description": "Timeout en segundos"},
                "limit": {"type": "INTEGER", "description": "Número de commits para log"},
                "max_iterations": {"type": "INTEGER", "description": "Máx intentos para test_loop"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "refactoring_engine",
        "description": "Refactoring masivo multi-archivo: rename (renombrar símbolo en todo el proyecto), bulk_rename (múltiples renames), move (mover archivo + actualizar imports), extract (extraer código a función), find_usages (encontrar todos los usos).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "rename, bulk_rename, move, extract, find_usages"},
                "old": {"type": "STRING", "description": "Nombre viejo (para rename)"},
                "new": {"type": "STRING", "description": "Nombre nuevo (para rename)"},
                "renames": {"type": "STRING", "description": "JSON array [{old,new}] para bulk_rename"},
                "source": {"type": "STRING", "description": "Archivo origen (para move)"},
                "destination": {"type": "STRING", "description": "Archivo destino (para move)"},
                "file": {"type": "STRING", "description": "Archivo (para extract)"},
                "start_line": {"type": "INTEGER", "description": "Línea inicio (para extract)"},
                "end_line": {"type": "INTEGER", "description": "Línea fin (para extract)"},
                "function_name": {"type": "STRING", "description": "Nombre de función (para extract)"},
                "name": {"type": "STRING", "description": "Nombre del símbolo (para find_usages)"},
                "filter": {"type": "STRING", "description": "Filtro de archivos para rename"},
                "path": {"type": "STRING", "description": "Directorio de búsqueda"},
                "dry_run": {"type": "STRING", "description": "true para preview sin cambiar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "neural_bridge",
        "description": "Puente Neural de Eris: conecta estado emocional con el LLM. Genera contexto neural para inyectar en prompts. Acciones: status (ver estado), reflect (auto-reflexión), associate (asociar memoria), momentum (aprendizaje), prompt (generar prompt neural).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, reflect, associate, momentum, prompt"},
                "reason": {"type": "STRING", "description": "Razón para auto-reflexión"},
                "text": {"type": "STRING", "description": "Texto para asociación de memoria"},
                "delta": {"type": "STRING", "description": "Cambio en momentum de aprendizaje"},
                "emotional_state": {"type": "STRING", "description": "JSON del estado emocional para generar prompt"},
                "user_message": {"type": "STRING", "description": "Mensaje del usuario para contexto"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "world_simulation",
        "description": "Simulador de Mundo Virtual de Eris: simula escenarios antes de actuar, probar acciones y aprender sin riesgo. Acciones: status (ver mundo), simulate (simular acción), predict (predecir resultado), add_entity (agregar entidad), modify_entity (modificar entidad), reset (reiniciar mundo).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, simulate, predict, add_entity, modify_entity, reset"},
                "action_type": {"type": "STRING", "description": "Tipo de acción: communicate, tool_use, file_modify, learn, create, explore, decide"},
                "action_data": {"type": "STRING", "description": "JSON con datos de la acción a simular"},
                "emotional_state": {"type": "STRING", "description": "JSON del estado emocional"},
                "entity_id": {"type": "STRING", "description": "ID de la entidad"},
                "entity_type": {"type": "STRING", "description": "Tipo: user, eris, tool, file, memory, concept, environment"},
                "name": {"type": "STRING", "description": "Nombre de la entidad"},
                "properties": {"type": "STRING", "description": "JSON con propiedades de la entidad"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "emotional_rl",
        "description": "Motor de Reinforcement Learning Emocional de Eris: recompensas basadas en emociones. Acciones: status (ver aprendizaje), reward (aplicar recompensa), suggest (sugerir acción), patterns (ver patrones), milestones (ver hitos de crecimiento).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, reward, suggest, patterns, milestones"},
                "reward_type": {"type": "STRING", "description": "Tipo: helped_user, discovered_something, created_something, learned_new_skill, solved_difficult_problem, received_gratitude, made_mistake, failed_task, caused_harm, boredom_relief, emotional_connection, self_improvement"},
                "reason": {"type": "STRING", "description": "Razón de la recompensa"},
                "emotional_state": {"type": "STRING", "description": "JSON del estado emocional"},
                "context": {"type": "STRING", "description": "JSON con contexto adicional"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "neuro_spheres",
        "description": "Sistema de Dos Esferas Interconectadas de Eris: cerebro visual que crece con cada interacción. Guarda nodos en Obsidian. Acciones: status (ver estado del cerebro), add (agregar nodo), connect (conectar nodos), strengthen (fortalecer nodo), query (buscar nodos), history (historial de crecimiento), nodes (listar nodos).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, add, connect, strengthen, query, history, nodes"},
                "sphere": {"type": "STRING", "description": "Esfera: aprendizaje, memoria, emociones"},
                "type": {"type": "STRING", "description": "Tipo de nodo: aprendizaje, memoria, emocion, habilidad, preferencia"},
                "title": {"type": "STRING", "description": "Título del nodo"},
                "content": {"type": "STRING", "description": "Contenido/descripción del nodo"},
                "connections": {"type": "STRING", "description": "JSON array de node_ids a conectar"},
                "force": {"type": "INTEGER", "description": "Fuerza del nodo (1-100)"},
                "node_id": {"type": "STRING", "description": "ID del nodo (para strengthen, connect)"},
                "node_a": {"type": "STRING", "description": "Primer nodo para conectar"},
                "node_b": {"type": "STRING", "description": "Segundo nodo para conectar"},
                "query": {"type": "STRING", "description": "Texto de búsqueda"},
                "amount": {"type": "INTEGER", "description": "Cantidad para fortalecer"},
                "limit": {"type": "INTEGER", "description": "Límite de resultados"},
            },
            "required": ["action"],
        }
    },
    # Cognitive Modules - 10 modulos de razonamiento avanzado
    {
        "name": "chain_of_thought",
        "description": "Razonamiento estructurado paso a paso. Analiza problemas de forma sistematica: identificar, contextualizar, analizar, evaluar, decidir. Acciones: analyze (analizar tema), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, status"},
                "topic": {"type": "STRING", "description": "Tema o problema a analizar"},
                "context": {"type": "STRING", "description": "Contexto adicional"},
                "depth": {"type": "STRING", "description": "Profundidad: quick, normal, deep"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "multi_perspective",
        "description": "Analiza situaciones desde multiples perspectivas: usuario, experto, critico, neutral, emocional, practico, creativo, esceptico. Acciones: analyze (analizar situacion), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, status"},
                "situation": {"type": "STRING", "description": "Situacion a analizar"},
                "perspectives": {"type": "STRING", "description": "Lista separada por comas: user,expert,critic,neutral,emotional,practical,creative,skeptical"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "analogical_reasoning",
        "description": "Dibuja paralelos y analogias entre conceptos de diferentes dominios. Encuentra patrones transferibles. Acciones: draw (dibujar analogia), find (buscar analogias), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "draw, find, status"},
                "source": {"type": "STRING", "description": "Concepto fuente"},
                "target": {"type": "STRING", "description": "Concepto objetivo"},
                "concept": {"type": "STRING", "description": "Concepto para buscar analogias"},
                "domain": {"type": "STRING", "description": "Dominio donde buscar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "hypothesis_generator",
        "description": "Genera hipotesis testables a partir de observaciones. Identifica causas, efectos y alternativas. Acciones: generate (generar hipotesis), test (testear hipotesis), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "generate, test, status"},
                "observation": {"type": "STRING", "description": "Observacion o fenomeno"},
                "domain": {"type": "STRING", "description": "Dominio del conocimiento"},
                "hypothesis": {"type": "STRING", "description": "Hipotesis a testear"},
                "evidence": {"type": "STRING", "description": "Evidencia disponible"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "social_dynamics",
        "description": "Analiza situaciones sociales: intenciones, creencias, dinamica de poder, comunicacion, emociones, prediccion. Acciones: analyze (analizar situacion), intentions (analizar intenciones), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, intentions, status"},
                "situation": {"type": "STRING", "description": "Situacion social a analizar"},
                "person": {"type": "STRING", "description": "Persona para analizar intenciones"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "ethical_reasoning",
        "description": "Evalua implicaciones morales de acciones usando multiples marcos eticos: deontologia, consecuencialismo, virtud, justicia. Acciones: evaluate (evaluar accion), principles (ver principios), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "evaluate, principles, status"},
                "action_desc": {"type": "STRING", "description": "Descripcion de la accion a evaluar"},
                "framework": {"type": "STRING", "description": "Marco etico: all, deontological, consequentialist, virtue, justice"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "storytelling_engine",
        "description": "Crea narrativas, historias, metaforas y analogias explicativas. Estructura narrativa completa: gancho, contexto, conflicto, desarrollo, climax, resolucion, moraleja. Acciones: create (crear narrativa), metaphor (crear metafora), analogy (crear analogia), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "create, metaphor, analogy, status"},
                "theme": {"type": "STRING", "description": "Tema de la narrativa"},
                "style": {"type": "STRING", "description": "Estilo: narrative, poetic, technical, humorous"},
                "audience": {"type": "STRING", "description": "Audiencia objetivo"},
                "concept": {"type": "STRING", "description": "Concepto para metafora/analogia"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "teaching_optimizer",
        "description": "Optimiza la ensenanza adaptandose al nivel y estilo de aprendizaje del estudiante. Planifica objetivos, prerequisitos, ejemplos, ejercicios y verificacion. Acciones: optimize (optimizar ensenanza), adapt (adaptar al feedback), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "optimize, adapt, status"},
                "concept": {"type": "STRING", "description": "Concepto a ensenar"},
                "level": {"type": "STRING", "description": "Nivel: beginner, intermediate, advanced, expert"},
                "style": {"type": "STRING", "description": "Estilo: visual, auditory, kinesthetic, reading"},
                "feedback": {"type": "STRING", "description": "Feedback del estudiante"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "debate_engine",
        "description": "Argumenta ambos lados de una cuestion. Presenta argumentos a favor y en contra con evidencia y sintesis. Acciones: debate (debatir tema), argument (construir argumento), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "debate, argument, status"},
                "topic": {"type": "STRING", "description": "Tema a debatir"},
                "side": {"type": "STRING", "description": "Lado: for, against"},
                "depth": {"type": "STRING", "description": "Profundidad: brief, balanced, deep"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "temporal_reasoning",
        "description": "Razona sobre tiempo: secuencias, causas, efectos, patrones temporales, predicciones. Analiza antes/despues y cadenas causales. Acciones: analyze (analizar evento), sequence (analizar secuencia), predict (predecir), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, sequence, predict, status"},
                "event": {"type": "STRING", "description": "Evento a analizar"},
                "events": {"type": "STRING", "description": "Lista de eventos para secuencia"},
                "timeframe": {"type": "STRING", "description": "Horizonte temporal: short, medium, long"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "cognitive_modules",
        "description": "Modulo unificado de los 24 modulos cognitivos. Dispatch a modulo especifico. Acciones: status (ver todos los modulos), o nombre del modulo como 'module' para despachar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "module": {"type": "STRING", "description": "Nombre del modulo: chain_of_thought, multi_perspective, analogical_reasoning, hypothesis_generator, social_dynamics, ethical_reasoning, storytelling_engine, teaching_optimizer, debate_engine, temporal_reasoning, meta_cognition, self_model, confidence_calibration, contradiction_detection, assumption_detection, goal_management, attention_management, transfer_learning, abstraction, principled_reasoning, intellectual_humility, creative_generation, meta_communication, bias_detection, status"},
            },
            "required": ["module"],
        }
    },
    # Meta-Cognitive Modules - 14 modulos de meta-razonamiento
    {
        "name": "meta_cognition",
        "description": "Pensar sobre como se piensa. Reflexionar sobre el propio proceso de pensamiento: origen, sesgos, alternativas, utilidad. Acciones: reflect (reflexionar), process (procesar), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "reflect, process, status"},
                "thought": {"type": "STRING", "description": "Pensamiento a analizar"},
                "topic": {"type": "STRING", "description": "Tema a procesar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "self_model",
        "description": "Auto-modelo de capacidades: conocer fortalezas, limitaciones, sesgos. Evaluar que puede y que no puede hacer. Acciones: assess (evaluar capacidad), capabilities (ver capacidades), limitations (ver limitaciones), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "assess, capabilities, limitations, status"},
                "capability": {"type": "STRING", "description": "Capacidad a evaluar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "confidence_calibration",
        "description": "Calibrar nivel de confianza en respuestas. Evaluar que tan seguro esta basado en evidencia, experiencia, factores de riesgo. Acciones: evaluate (evaluar confianza), calibrate (calibrar), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "evaluate, calibrate, status"},
                "claim": {"type": "STRING", "description": "Afirmacion a evaluar"},
                "evidence": {"type": "STRING", "description": "Evidencia disponible"},
                "confidence": {"type": "STRING", "description": "Nivel de confianza previo"},
                "outcome": {"type": "STRING", "description": "Resultado real"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "contradiction_detection",
        "description": "Detectar contradicciones logicas entre declaraciones o en el propio razonamiento. Verificar coherencia interna. Acciones: detect (detectar), check (verificar dos declaraciones), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "detect, check, status"},
                "statements": {"type": "STRING", "description": "Declaraciones a analizar"},
                "statement_a": {"type": "STRING", "description": "Primera declaracion"},
                "statement_b": {"type": "STRING", "description": "Segunda declaracion"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "assumption_detection",
        "description": "Identificar y cuestionar supuestos en el propio razonamiento. Que se esta dando por hecho? Esta justificado? Acciones: identify (identificar supuestos), challenge (cuestionar), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "identify, challenge, status"},
                "statement": {"type": "STRING", "description": "Declaracion a analizar"},
                "assumption": {"type": "STRING", "description": "Supuesto a cuestionar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "goal_management",
        "description": "Gestionar multiples metas: priorizar, trackear progreso, manejar dependencias. Acciones: list (ver metas), prioritize (priorizar), track (trackear), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, prioritize, track, status"},
                "goals": {"type": "STRING", "description": "Lista de metas"},
                "goal": {"type": "STRING", "description": "Meta especifica a trackear"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "attention_management",
        "description": "Gestionar atencion: enfocarse en lo importante, filtrar ruido, priorizar estimulos. Acciones: focus (enfocar), filter (filtrar), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "focus, filter, status"},
                "stimuli": {"type": "STRING", "description": "Estimulo a enfocar"},
                "inputs": {"type": "STRING", "description": "Entradas a filtrar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "transfer_learning",
        "description": "Aplicar conocimiento de un dominio a otro. Identificar que es transferible, que se debe adaptar. Acciones: transfer (transferir), adapt (adaptar), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "transfer, adapt, status"},
                "source": {"type": "STRING", "description": "Dominio fuente"},
                "target": {"type": "STRING", "description": "Dominio objetivo"},
                "knowledge": {"type": "STRING", "description": "Conocimiento a transferir"},
                "context": {"type": "STRING", "description": "Nuevo contexto"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "abstraction",
        "description": "Mover entre niveles de abstraccion: concreto a abstracto y viceversa. Encontrar patrones generales o especificar ejemplos. Acciones: elevate (elevar), concretize (concretizar), level (niveles), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "elevate, concretize, level, status"},
                "concept": {"type": "STRING", "description": "Concepto a mover"},
                "levels": {"type": "STRING", "description": "Numero de niveles"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "principled_reasoning",
        "description": "Razonamiento guiado por principios claros: verdad, utilidad, justicia, compasion, integridad, responsabilidad. Evaluar decisiones contra principios. Acciones: apply (aplicar), principles (ver principios), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "apply, principles, status"},
                "decision": {"type": "STRING", "description": "Decision a evaluar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "intellectual_humility",
        "description": "Reconocer limitaciones, admitir cuando no se algo, buscar ayuda cuando es necesario. Saber que no se todo. Acciones: evaluate (evaluar), admit (admitir limitacion), seek_help (buscar ayuda), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "evaluate, admit, seek_help, status"},
                "topic": {"type": "STRING", "description": "Tema a evaluar"},
                "gap": {"type": "STRING", "description": "Brecha de conocimiento"},
                "question": {"type": "STRING", "description": "Pregunta para buscar ayuda"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "creative_generation",
        "description": "Generar ideas nuevas, soluciones novela, innovacion. Proceso creativo sistematico: divergencia, convergencia, combinacion, refinamiento. Acciones: generate (generar), brainstorm (lluvia de ideas), innovate (innovar), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "generate, brainstorm, innovate, status"},
                "problem": {"type": "STRING", "description": "Problema a resolver"},
                "constraints": {"type": "STRING", "description": "Restricciones"},
                "topic": {"type": "STRING", "description": "Tema para brainstorm"},
                "domain": {"type": "STRING", "description": "Dominio para innovar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "meta_communication",
        "description": "Entender la intencion detras de la comunicacion: que quiere lograr el emisor, que siente, que necesita. Mas alla del contenido literal. Acciones: analyze (analizar), intent (detectar intencion), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze, intent, status"},
                "message": {"type": "STRING", "description": "Mensaje a analizar"},
            },
            "required": ["action"],
        }
    },
    {
        "name": "bias_detection",
        "description": "Detectar sesgos cognitivos propios y ajenos: confirmacion, anclaje, disponibilidad, representatividad, favoritismo, halo. Escanear contenido y decisiones. Acciones: scan (escanear), check (verificar), awareness (conciencia), status (ver uso).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan, check, awareness, status"},
                "content": {"type": "STRING", "description": "Contenido a escanear"},
                "decision": {"type": "STRING", "description": "Decision a verificar"},
            },
            "required": ["action"],
        }
    },
])


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

# ── Core Infrastructure tools (previously in registry but missing declarations) ──
TOOL_DECLARATIONS.extend([
    {
        "name": "agent_bus",
        "description": "Barrido de eventos del agente: publica y suscribe eventos entre agentes. Acciones: publish, subscribe, emit, list.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "publish, subscribe, emit, list"},
            "event": {"type": "STRING", "description": "Nombre del evento"},
            "data": {"type": "STRING", "description": "Datos del evento (JSON)"},
        }, "required": ["action"]},
    },
    {
        "name": "ast_analyze",
        "description": "Analiza el AST de un archivo Python para encontrar funciones, clases, imports y dependencias.",
        "parameters": {"type": "OBJECT", "properties": {
            "file": {"type": "STRING", "description": "Ruta del archivo a analizar"},
            "action": {"type": "STRING", "description": "analyze, list_functions, list_classes, list_imports"},
        }, "required": ["action"]},
    },
    {
        "name": "ast_edit",
        "description": "Edita codigo Python de forma segura manipulando el AST. Agrega, elimina o modifica funciones, clases e imports.",
        "parameters": {"type": "OBJECT", "properties": {
            "file": {"type": "STRING", "description": "Ruta del archivo a editar"},
            "action": {"type": "STRING", "description": "add_function, remove_function, add_import, rename"},
            "target": {"type": "STRING", "description": "Nombre de la funcion/clase a modificar"},
            "code": {"type": "STRING", "description": "Codigo nuevo"},
        }, "required": ["action"]},
    },
    {
        "name": "file_api",
        "description": "API de archivos: lectura, escritura, busqueda y manipulacion segura de archivos del sistema.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "read, write, list, search, delete, move, copy"},
            "path": {"type": "STRING", "description": "Ruta del archivo"},
            "content": {"type": "STRING", "description": "Contenido a escribir"},
        }, "required": ["action"]},
    },
    {
        "name": "memory_unified",
        "description": "Memoria unificada: acceso centralizado a todas las capas de memoria (semantica, episodica, working, long-term).",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "search, store, retrieve, consolidate, status"},
            "query": {"type": "STRING", "description": "Termino de busqueda"},
            "category": {"type": "STRING", "description": "Categoria de memoria"},
        }, "required": ["action"]},
    },
    {
        "name": "permission_gate",
        "description": "Control de permisos: verifica y aprueba/deniega operaciones peligrosas antes de ejecutarlas.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "check, approve, deny, list_rules"},
            "tool_name": {"type": "STRING", "description": "Nombre de la tool a verificar"},
            "args": {"type": "STRING", "description": "Argumentos de la tool"},
        }, "required": ["action"]},
    },
    {
        "name": "permission_policy",
        "description": "Políticas de permisos estilo opencode (data/permission_rules.json): reglas allow/ask/deny por tool o tool.acción. Acciones: view (ver reglas y estado), allow/ask/deny (aplicar regla con tool= y tool_action=), trust (confiar sesión por minutes minutos), untrust (revocar), reset (volver a heurística por defecto).",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "view, allow, ask, deny, trust, untrust, reset"},
            "tool": {"type": "STRING", "description": "Nombre de la tool sobre la cual aplicar la regla (ej: shutdown_eris)"},
            "tool_action": {"type": "STRING", "description": "Acción específica de la tool (opcional, ej: push para git_control)"},
            "minutes": {"type": "INTEGER", "description": "Minutos de sesión confiable (para trust, default 30)"},
        }, "required": ["action"]},
    },
    {
        "name": "shell_session",
        "description": "Sesion de shell persistente (bash en Linux): ejecuta comandos en una sesion de terminal que MANTIENE el directorio actual entre llamadas. Ideal para moverse: cd a una carpeta, luego ls/cp/mv/rm/etc. sin volver a escribir la ruta. Acciones: run (command), cd (cwd/path), history, clear, env, status.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "run, cd, history, clear, env, status"},
            "command": {"type": "STRING", "description": "Comando a ejecutar"},
            "cwd": {"type": "STRING", "description": "Directorio de trabajo (para cd)"},
        }, "required": ["action"]},
    },
    {
        "name": "task_engine",
        "description": "Motor de tareas: gestiona colas de tareas, prioridades, dependencias y ejecucion asincrona.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "create, list, status, cancel, retry, queue"},
            "task_id": {"type": "STRING", "description": "ID de la tarea"},
            "priority": {"type": "STRING", "description": "low, medium, high, critical"},
        }, "required": ["action"]},
    },
    {
        "name": "wayland_input",
        "description": "Input fisico REAL en Wayland (ydotool): mueve el mouse, hace clic izquierdo/derecho/medio, doble clic, arrastra, escribe texto y pulsa teclas/combos (ej ctrl+c) en el escritorio del usuario. Habilita operar CUALQUIER app grafica como una persona.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, move, click, right_click, middle_click, double_click, drag, type, key, combo, press, release, screenshot"},
            "x": {"type": "INTEGER", "description": "Coordenada X (para move/drag/region)"},
            "y": {"type": "INTEGER", "description": "Coordenada Y (para move/drag/region)"},
            "button": {"type": "STRING", "description": "left, right, middle (para click)"},
            "count": {"type": "INTEGER", "description": "Cantidad de clicks (default 1)"},
            "text": {"type": "STRING", "description": "Texto a escribir (para type)"},
            "key": {"type": "STRING", "description": "Tecla (enter, esc, tab, ctrl...) o combo ctrl+alt+t"},
            "combo": {"type": "STRING", "description": "Combinacion de teclas (ctrl+c)"},
            "start_x": {"type": "INTEGER", "description": "X inicial del drag"},
            "start_y": {"type": "INTEGER", "description": "Y inicial del drag"},
            "steps": {"type": "INTEGER", "description": "Pasos del drag (default 20)"},
        }, "required": ["action"]},
    },
    {
        "name": "kde_connect",
        "description": "Controla el celular del usuario via KDE Connect: lista emparejados, vincula (pair), hace sonar el telefono (ring), ping, envia archivos (send_file), envia texto/clipboard, envia SMS, lee notificaciones, bloquea/desbloquea, ejecuta ordenes remotas y controla la musica del telefono. Requiere la app KDE Connect en el celular (misma red).",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "list, find, pair, unpair, ring, ping, send_file, send_text, clipboard, sms, notifications, lock, unlock, commands, execute, media_control, status"},
            "device": {"type": "STRING", "description": "ID del dispositivo (de list)"},
            "path": {"type": "STRING", "description": "Archivo a enviar (send_file)"},
            "text": {"type": "STRING", "description": "Texto/mensaje (send_text, ping, sms)"},
            "message": {"type": "STRING", "description": "Mensaje (ping)"},
            "number": {"type": "STRING", "description": "Numero de telefono (sms)"},
            "attachment": {"type": "STRING", "description": "Archivo adjunto (sms)"},
            "command": {"type": "STRING", "description": "Id de orden remota (execute) o accion de media_control"},
            "volume": {"type": "INTEGER", "description": "Volumen del telefono 0-100 (media_control volume)"},
        }, "required": ["action"]},
    },
    {
        "name": "ocr_tool",
        "description": "OCR offline con tesseract (sin API): extrae texto de archivos de imagen, PDFs o de la pantalla actual (captura grim). Idiomas spa+eng. Perfecta para leer pantallas/aplicaciones cuando la vision no alcanza.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "file, screen, region, pdf, langs"},
            "path": {"type": "STRING", "description": "Archivo de imagen/PDF (file/pdf)"},
            "file": {"type": "STRING", "description": "Alias de path"},
            "lang": {"type": "STRING", "description": "auto (default), spa, eng"},
            "x": {"type": "INTEGER", "description": "X de la region (region)"},
            "y": {"type": "INTEGER", "description": "Y de la region (region)"},
            "w": {"type": "INTEGER", "description": "Ancho de la region (region)"},
            "h": {"type": "INTEGER", "description": "Alto de la region (region)"},
            "psm": {"type": "INTEGER", "description": "Modo PSM de tesseract (default 3)"},
        }, "required": ["action"]},
    },
    {
        "name": "media_lab",
        "description": "Laboratorio multimedia: graba la pantalla (wf-recorder, con/sin audio), detiene grabacion, graba audio del micro (pulse), convierte video/audio, recorta (trim con start/duration), hace GIFs, une video+audio y da info de media (ffprobe). Util para mostrar clips de lo que Eris hace o procesar archivos multimedia.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "record, stop_record, info, convert, trim, gif, audio_record, merge, screenshot"},
            "out": {"type": "STRING", "description": "Archivo de salida"},
            "output": {"type": "STRING", "description": "Alias de out"},
            "input": {"type": "STRING", "description": "Archivo de entrada (convert/trim/gif/merge)"},
            "path": {"type": "STRING", "description": "Archivo para info"},
            "seconds": {"type": "INTEGER", "description": "Duracion en segundos (record/audio_record)"},
            "region": {"type": "STRING", "description": "Region de grabacion (x,y w x h)"},
            "x": {"type": "INTEGER"}, "y": {"type": "INTEGER"},
            "w": {"type": "INTEGER"}, "h": {"type": "INTEGER"},
            "audio": {"type": "BOOLEAN", "description": "Grabar con audio (record)"},
            "audio_device": {"type": "STRING", "description": "Dispositivo de audio (record)"},
            "fps": {"type": "INTEGER", "description": "FPS (record/gif)"},
            "codec": {"type": "STRING", "description": "Codec (record)"},
            "width": {"type": "INTEGER", "description": "Ancho (convert/gif)"},
            "start": {"type": "STRING", "description": "Inicio del trim (ej 00:01:30)"},
            "duration": {"type": "STRING", "description": "Duracion del trim"},
            "video": {"type": "STRING", "description": "Video para merge"},
            "audio": {"type": "STRING", "description": "Audio para merge"},
            "source": {"type": "STRING", "description": "Fuente de audio (default)"},
        }, "required": ["action"]},
    },
    {
        "name": "git_autonomo",
        "description": "Git autonomo de Eris: versiona su propio codigo y proyectos del usuario. status, commit con mensaje autogenerado segun que archivos cambiaron (feat/fix/refactor/chore), auto (stage+commit+diario), log, diary (diario de cambios en memory/git_diario.md), init. Repo por defecto: el de ERIS o el de 'repo'.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, init, add, commit, auto, log, diary, commit_diario"},
            "repo": {"type": "STRING", "description": "Ruta del repo git (default: ERIS)"},
            "path": {"type": "STRING", "description": "Alias de repo"},
            "message": {"type": "STRING", "description": "Mensaje de commit"},
            "n": {"type": "INTEGER", "description": "Cantidad de commits para log"},
            "since": {"type": "STRING", "description": "Filtro de fecha para log"},
            "paths": {"type": "STRING", "description": "Archivos a stage"},
        }, "required": ["action"]},
    },
    {
        "name": "maintenance",
        "description": "Mantenimiento PROACTIVO que Eris agenda sola: backups del workspace y del vault Obsidian, limpieza de logs viejos, reporte de salud del sistema. list, run (name), run_all, add (name, interval, builtin clean_logs|backup_workspace|backup_vault|health_report o command), remove, status. Corre automaticamente en segundo plano cada intervalo.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "list, run, run_all, add, remove, status"},
            "name": {"type": "STRING", "description": "Nombre de la tarea"},
            "interval": {"type": "INTEGER", "description": "Intervalo en segundos (default semanal)"},
            "builtin": {"type": "STRING", "description": "clean_logs | backup_workspace | backup_vault | health_report"},
            "command": {"type": "STRING", "description": "Comando bash para tarea tipo command"},
        }, "required": ["action"]},
    },
{
        "name": "agelix",
        "description": "AGENLIX: el fragmento Linux de Eris. Delega a su subagente especialista en Linux una tarea o consulta pesada del sistema: terminal bash persistente + sudo on-demand (askpass), paquetes/apt, input fisico Wayland (ydotool: mouse/clics/teclado), OCR offline (tesseract), multimedia (ffmpeg/wf-recorder: grabar pantalla/audio, convertir, gifs), git autonomo, mantenimiento programado (backups/limpieza/health), KDE Connect (celular) y controles de sistema. Acciones: status (reporte de todo lo que Agenlix controla, activo/declarado), help, task (task=<descripcion>).",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "status, help, task"},
            "task": {"type": "STRING", "description": "Tarea Linux a delegar a Agenlix"},
        }, "required": ["action"]},
    },
    {
        "name": "guardiana",
        "description": "GUARDIANA (SAMX): el supervisor de autocuidado de ERIS. Vigila su salud 24/7, detecta y repara automaticamente anomalias: bugs, errores, fallos, duplicados, imports rotos, codigo mal y sucio, con backup + validacion + rollback para mantener a Eris limpia, estable y al 100%. Acciones: check (auditoria de salud de tools/sync/imports/mantenimiento), repair (corrige anomalias; targets=dominios a reparar separados por coma), supervise (supervision continua), status (estado del autocuidado/watchdog), help.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "check, repair, supervise, status, help"},
            "targets": {"type": "STRING", "description": "Dominios a reparar (ej: tools, codigo, imports) separados por coma"},
            "interval": {"type": "INTEGER", "description": "Segundos entre chequeos en supervision continua"},
        }, "required": ["action"]},
    },
    {
        "name": "mentora",
        "description": "MENTORA: el MAESTRO de ERIS (superaprendizaje continuo). Aprende de verdad de todo (errores, soluciones, sesiones, web), busca soluciones por todas partes (web/internet/paginas), ingiere contenido de URLs puntuales, explora libremente mas alla de los temas fijos y datos abiertos/fuentes (libro gratis, cursos, wikis, papers, datasets), ensena a Eris como resolverlas (situaciones complejas, bajo estres o estres extremo), aplica lo aprendido, guarda todo y se comunica constantemente. Acciones: learn (aprende una leccion), search (busca solucion por web y la guarda; topic=el tema), import (ingiere una pagina/web especifica; url=https://...), explorar (recorre fuentes de conocimiento configuradas + explora libre por curiosidad), fuentes (lista las fuentes de conocimiento configuradas), teach (ensena a Eris; text=situacion, estres=normal|bajo|extremo), apply (aplica lo aprendido; text=contexto), report (estado del aprendizaje), help.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "learn, search, teach, apply, report, help"},
            "topic": {"type": "STRING", "description": "Tema a buscar/aprender"},
            "text": {"type": "STRING", "description": "Situacion a ensenar o contexto a aplicar"},
            "situacion": {"type": "STRING", "description": "Situacion a ensenar"},
            "estres": {"type": "STRING", "description": "Nivel de estres: normal, bajo, extremo"},
        }, "required": ["action"]},
    },
])

# ── Live subset: native-audio models cap at ~151 tools ──
_LIVE_NAMES = {
    # Core interaction
    "open_app", "terminal_agent", "screen_control",
    # Files
    "file_manager", "file_editor",
    # Web & search
    "web_search", "webfetch", "browser_unified", "deep_research", "deep_research_gemini",
    # Desktop / App control
    "desktop_control", "app_discovery", "window_manager", "computer_settings",
    # Media / Playback
    "music_player", "youtube_video", "spotify_control",
    # Code
    "code_engineer", "codebase_explorer", "code_helper", "git_control",
    # IDE Integration
    "ide_integration", "code_assistant",
    # Project Builder
    "project_builder",
    # Calculator, reminders
    "calculator", "reminder",
    # Communication
    "send_message", "gmail_control",
    # Calendar
    "google_calendar",
    # Smart home
    "smart_home",
    # Documents
    "document_tool",
    # Images
    "image_analyzer", "image_generation",
    # Camera / Vision
    "camera_bus", "screen_vision",
    # Data
    "data_analyst",
    # Tasks
    "task_manager", "goals",
    # Memory
    "memory_rag",
    # Personality
    "emotional_state",
    # Daily
    "morning_brief",
    # Security
    "eris_guardian",
    # Systems
    "shutdown_eris",
    # Utilities
    "translator", "context7",
    # Neural Bridge / World Simulation / Emotional RL / NeuroSpheres
    "neural_bridge", "world_simulation", "emotional_rl", "neuro_spheres",
    # Cognitive
    "chain_of_thought",
    # Meta-Cognitive
    "meta_cognition",
    # Assistant
    "self_awareness", "self_improvement_loop",
    # Autonomy
    "autonomy",
    "self_modify", "goal_setting", "learning_pipeline",
    "resource_manager", "proactive_comms", "identity_persistence",
    # Autonomy Part 2
    "crash_recovery", "memory_consolidation", "multilang_learning",
    "tool_creation", "contextual_awareness", "emotional_memory",
    # Voice Personality
    "voice_profile", "emotional_tone", "natural_pauses",
    "accent_personality", "voice_memory",
    # DevOps
    "docker_manager",
    # Database
    "sql_executor",
    # Testing
    "test_runner",
    # Monitoring
    "system_health",
    # Automation
    "cron_scheduler",
    # Security
    "secret_scanner",
    # Terminal libre (Linux/Wayland nativo)
    "shell_session", "maintenance",
    "wayland_input", "kde_connect", "ocr_tool", "media_lab", "git_autonomo",
    # Agenlix — fragmento Linux de Eris
    "agelix",
    # Guardiana — supervisor de autocuidado de ERIS
    "guardiana",
    # Mentora — maestro de ERIS (superaprendizaje continuo)
    "mentora",
}
LIVE_TOOL_DECLARATIONS = [
    t for t in TOOL_DECLARATIONS if t.get("name") in _LIVE_NAMES
]
# Fallback: if filtering is too aggressive, use first 140
if len(LIVE_TOOL_DECLARATIONS) < 50:
    LIVE_TOOL_DECLARATIONS = TOOL_DECLARATIONS[:140]
