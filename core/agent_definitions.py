"""
core/agent_definitions.py — 8 Agent Architecture for ERIS
Each agent owns a clear domain with only WORKING tools.
No overlap, no stubs, no confusion.
"""

AGENT_DEFINITIONS = {
    # ──────────────────────────────────────────────
    # 1. CORE — System basics, apps, desktop, settings
    # ──────────────────────────────────────────────
    "core": {
        "name": "CoreAgent",
        "description": "Operaciones básicas del sistema: abrir apps, escritorio, ventanas, volumen, clipboard, monitor de sistema",
        "keywords": [
            "abrir", "abre", "abri", "iniciar", "lanzar", "ejecutar", "app", "aplicacion",
            "escritorio", "desktop", "ventana", "window", "minimizar", "maximizar", "cerrar",
            "volumen", "sonido", "audio", "mute", "silenciar",
            "clipboard", "copiar", "pegar", "portapapeles",
            "monitor", "sistema", "cpu", "ram", "disco", "procesos",
            "configuracion", "settings", "windows", "config",
            "calculadora", "calc", "notepad", "bloc de notas",
            "captura", "screenshot", "pantalla",
            "control", "pc", "computadora", "equipo",
        ],
        "tools": [
            "open_app", "app_discovery", "desktop_control", "window_manager",
            "system_monitor", "system_volume", "computer_settings", "computer_control",
            "clipboard_manager", "screen_control", "screen_see", "shell_executor",
            "process_manager", "action_history", "windows_settings", "driver_manager",
            "pc_control", "quick_actions", "context_menu", "desktop_notifications",
        ],
        "handler": "agents.system_agent.handle_system",
    },

    # ──────────────────────────────────────────────
    # 2. WEB — Search, browse, fetch, research
    # ──────────────────────────────────────────────
    "web": {
        "name": "WebAgent",
        "description": "Búsqueda web, navegación, scraping, investigación profunda, fetch de páginas",
        "keywords": [
            "buscar", "busca", "busca", "search", "google", "encontrar",
            "navegador", "browser", "abrir pagina", "web", "sitio", "website",
            "scraping", "scrapear", "extraer", "extrae", "raspar",
            "investigar", "investiga", "research", "profundo", "deep",
            "url", "enlace", "link", "pagina", "page",
            "resumir pagina", "resumen web", "summarize",
            "fetch", "descargar pagina", "contenido web",
            "duckduckgo", "ddg", "bing",
        ],
        "tools": [
            "web_search", "super_search", "deep_research", "webfetch",
            "web_navigation", "browser_control", "browser_auto", "browser_unified",
            "page_summarizer", "smart_browser", "web_scraper", "multi_search",
            "search_info", "research", "rss_reader", "browser_history",
        ],
        "handler": "agents.search_agent.handle_search",
    },

    # ──────────────────────────────────────────────
    # 3. FILE — File operations, editing, AST, organization
    # ──────────────────────────────────────────────
    "file": {
        "name": "FileAgent",
        "description": "Operaciones con archivos: leer, escribir, editar, organizar, buscar, copiar, mover",
        "keywords": [
            "archivo", "carpeta", "directorio", "folder", "file",
            "leer archivo", "escribir", "editar", "modificar", "crear archivo",
            "copiar", "mover", "renombrar", "eliminar", "borrar",
            "buscar archivo", "encontrar archivo", "listar",
            "organizar", "organiza", "organizar archivos",
            "backup", "respaldo", "copia de seguridad",
            "txt", "py", "json", "csv", "xml",
        ],
        "tools": [
            "file_api", "file_manager", "file_editor", "file_processor",
            "file_controller", "ast_analyze", "ast_edit",
            "smart_file_organizer", "file_organizer", "file_monitor",
            "file_profiler", "backup_system", "auto_backup",
            "save_everywhere", "clipboard_history",
        ],
        "handler": "agents.system_agent.handle_file",
    },

    # ──────────────────────────────────────────────
    # 4. DEV — Code, git, programming, DevOps
    # ──────────────────────────────────────────────
    "dev": {
        "name": "DevAgent",
        "description": "Programación, código, git, codebase, DevOps, refactoring, testing",
        "keywords": [
            "codigo", "code", "programar", "programa", "script",
            "funcion", "function", "clase", "class", "metodo",
            "git", "commit", "push", "pull", "branch", "repositorio", "repo",
            "python", "javascript", "html", "css", "react", "node",
            "compilar", "compile", "build", "npm", "pip",
            "debug", "error", "bug", "fix", "arreglar",
            "refactor", "refactorizar", "optimizar codigo",
            "test", "testing", "prueba", "unittest",
            "docker", "deploy", "desplegar", "ci/cd",
            "downloader", "scraper", "bot", "proyecto",
            "dependencias", "instalar paquete", "requirements",
        ],
        "tools": [
            "code_helper", "code_generator", "code_analyzer", "code_review",
            "code_engineer", "codebase_explorer", "code_validator",
            "git_control", "git_smart", "git_daily", "github_pr",
            "devops_pipeline", "refactoring_engine", "test_generator",
            "dependency_manager", "vscode_controller", "dev_agent",
            "web_generator", "web_designer", "react_designer",
            "angular_designer", "vue_designer", "next_designer",
            "tool_creator", "code_sandbox", "shell_session",
        ],
        "handler": "agents.dev_agent.handle_dev",
    },

    # ──────────────────────────────────────────────
    # 5. MEDIA — Music, YouTube, images, entertainment
    # ──────────────────────────────────────────────
    "media": {
        "name": "MediaAgent",
        "description": "Música, YouTube, generación de imágenes, entretenimiento, games",
        "keywords": [
            "musica", "music", "spotify", "cancion", "song", "playlist",
            "youtube", "video", "yt", "descargar video",
            "imagen", "image", "foto", "photo", "dibujar", "generar imagen",
            "juego", "game", "gaming", "jugar",
            "tiktok", "reel", "short",
            "radio", "podcast", "audio",
            "pelicula", "movie", "serie", "anime",
        ],
        "tools": [
            "music_player", "play_direct", "spotify_control",
            "youtube_video", "image_generation", "image_generator",
            "image_analyzer", "video_analyzer", "game_companion",
            "game_agent", "game_launcher", "game_updater",
            "audio_transcriber", "voice_recognition", "tts_set_voice",
        ],
        "handler": "agents.media_agent.handle_media",
    },

    # ──────────────────────────────────────────────
    # 6. COMM — Email, calendar, messaging, documents
    # ──────────────────────────────────────────────
    "comm": {
        "name": "CommAgent",
        "description": "Email, calendario, mensajería, documentos, notificaciones, productividad",
        "keywords": [
            "email", "correo", "gmail", "mail", "enviar mensaje",
            "calendario", "calendar", "evento", "reunion", "meeting",
            "whatsapp", "telegram", "sms", "mensaje",
            "documento", "document", "pdf", "word", "excel", "powerpoint",
            "notificacion", "notification", "alerta",
            "recordatorio", "reminder", "alarma",
            "tarea", "task", "todo", "pendiente",
            "agenda", "schedule", "planificar",
            "hoja de calculo", "spreadsheet", "presentacion",
        ],
        "tools": [
            "email_manager", "gmail_control", "send_message", "send_sms",
            "whatsapp", "whatsapp_web", "telegram_bot",
            "google_calendar", "calendar_manager", "reminder", "reminders",
            "document_creator", "document_handler", "document_manager", "document_tool",
            "document_generator", "document_rag",
            "presentation_generator", "spreadsheet_generator",
            "pdf_editor", "pdf_manager", "pdf_generator",
            "office_docs", "notification_center", "notifications",
            "task_manager", "task_scheduler", "goals",
            "scheduler", "alarm_manager", "meeting_transcriber",
            "obsidian_note", "i18n",
        ],
        "handler": "agents.productivity_agent.handle_productivity",
    },

    # ──────────────────────────────────────────────
    # 7. VISION — Screen analysis, OCR, images, perception
    # ──────────────────────────────────────────────
    "vision": {
        "name": "VisionAgent",
        "description": "Análisis de pantalla, OCR, visión por computadora, análisis de imágenes",
        "keywords": [
            "ver pantalla", "que se ve", "que hay en pantalla",
            "capturar", "screenshot", "pantalla",
            "ocr", "leer texto imagen", "texto en imagen",
            "analizar imagen", "analizar foto", "que hay en la foto",
            "vision", "ver", "mirar", "observar",
            "reconocer", "detectar", "identificar",
            "cámara", "camera", "webcam",
        ],
        "tools": [
            "screen_vision", "image_analyzer", "ocr_reader",
            "screen_see", "camera_bus", "vision_guardian",
            "screen_context", "screen_recorder",
        ],
        "handler": "agents.vision_agent.handle_vision",
    },

    # ──────────────────────────────────────────────
    # 8. SECURITY — Scanning, firewall, protection
    # ──────────────────────────────────────────────
    "security": {
        "name": "SecurityAgent",
        "description": "Seguridad del sistema, escaneo, firewall, protección, criptografía",
        "keywords": [
            "seguridad", "security", "escanear", "scan", "virus", "malware",
            "firewall", "proteccion", "protect", "amenaza", "threat",
            "encriptar", "encrypt", "cifrar", "descifrar",
            "contraseña", "password", "credential", "clave",
            "hack", "vulnerabilidad", "vulnerability",
            "osint", "investigar persona", "whois",
            "usb", "dispositivo", "periferico",
            "rama", "ransomware", "spyware",
        ],
        "tools": [
            "security_scanner", "security_shield", "eris_guardian",
            "active_firewall", "ransomware_shield", "self_protection",
            "osint_agent", "cybersecurity", "credential_recovery",
            "keylogger_detector", "usb_monitor", "darkweb_monitor",
            "disk_wiper", "file_encryptor",
        ],
        "handler": "agents.security_agent.handle_security",
    },

    # ──────────────────────────────────────────────
    # 9. LINUX — Agenlix: el fragmento Linux de ERIS
    # Todo lo Linux: terminal, paquetes, input, OCR,
    # multimedia, git, mantenimiento, celular.
    # ──────────────────────────────────────────────
    "linux": {
        "name": "AgenlixAgent",
        "description": "Fragmento Linux de ERIS: terminal bash persistente + sudo on-demand, paquetes (apt), input físico Wayland (ydotool), OCR (tesseract), multimedia (ffmpeg/wf-recorder), git autónomo, mantenimiento programado, KDE Connect (celular) y controles de sistema. ERIS delega acá todo lo pesado de Linux.",
        "keywords": [
            "agelix", "agenlix", "fragmento linux",
            "terminal", "bash", "consola", "comando", "shell",
            "sudo", "permiso administrador", "con permisos",
            "paquete", "apt", "pacman", "instalar paquete",
            "actualizá el sistema", "actualiza el sistema",
            "wayland", "hyprland", "hyprctl", "ydotool",
            "mové el mouse", "mueve el mouse", "doble clic", "clic en", "escribí con el teclado",
            "kde connect", "celular", "vincular celular", "hacé sonar",
            "ocr", "tesseract", "leé el texto de la pantalla",
            "grabá la pantalla", "grabar la pantalla", "convertí video", "hacé un gif",
            "subí todo al repo", "git autónomo",
            "mantenimiento programado", "hacé el mantenimiento",
            "servicio systemd", "systemctl",
        ],
        "tools": [
            "agelix", "shell_session", "terminal_agent", "wayland_input",
            "ocr_tool", "media_lab", "git_autonomo", "maintenance",
            "kde_connect", "system_volume", "window_manager", "pc_control",
            "desktop_notifications", "screen_control", "screen_see",
        ],
        "handler": "agents.agenlix_agent.handle_linux",
    },

    # ──────────────────────────────────────────────
    # 10. GUARDIANA — autocuidado continuo de ERIS
    # Supervisor que vigila, detecta y repara cualquier
    # anomalía (bugs, errores, duplicados, imports rotos)
    # para mantener a Eris limpia, estable y al 100%.
    # ──────────────────────────────────────────────
    "guardian": {
        "name": "GuardianaAgent",
        "description": "SAMX: el supervisor de autocuidado de ERIS. Vigila su salud 24/7 y repara automaticamente bugs, errores, fallos, duplicados, imports rotos y codigo mal, con backup + validacion + rollback, para mantenerla limpia, estable y al 100%.",
        "keywords": [
            "guardiana", "samx", "autocuidado", "cuidame", "cuida a eris",
            "repará", "repara", "reparar", "arreglá", "arregla", "corrigí", "corregí",
            "arregla los errores", "corrige los errores", "revisá mi salud", "revisa mi salud",
            "estoy rota", "hay problemas", "revisá todo", "auditoría de salud",
            "salud de eris", "revisá si hay errores", "detección de bugs",
            "reducir duplicados", "mantené a eris", "mantenla estable", "mantenla limpia",
            "supervisión continua", "vigila siempre", "siempre pendiente",
            "code review de eris", "mantenimiento de eris", "revisá mi código",
        ],
        "penalty_keywords": [
            "spotify", "musica", "youtube", "email", "calendario", "navegador",
            "web", "juego", "pelicula", "imagen", "video youtube",
        ],
        "tools": [
            "guardiana", "evolucion", "self_healing", "code_guard", "codebase_explorer",
            "auto_healer", "maintenance", "system_health", "self_evolution",
        ],
        "handler": "agents.guardiana_agent.handle_guardian",
    },
}


def get_agent_for_text(text: str) -> str | None:
    """Classify text intent and return agent key, or None."""
    import unicodedata
    text_lower = text.lower()
    text_norm = ''.join(
        unicodedata.normalize('NFKD', c)
        for c in text_lower
        if not unicodedata.combining(c)
    )

    scores = {}
    for key, agent in AGENT_DEFINITIONS.items():
        score = 0
        for kw in agent["keywords"]:
            kw_norm = ''.join(
                unicodedata.normalize('NFKD', c)
                for c in kw
                if not unicodedata.combining(c)
            )
            if kw_norm in text_norm:
                # Multi-word phrases get bonus
                weight = 2 if " " in kw else 1
                # Exact word boundary match bonus
                import re
                if re.search(r'\b' + re.escape(kw_norm) + r'\b', text_norm):
                    weight *= 1.5
                score += weight
        if score > 0:
            scores[key] = score

    if not scores:
        return None

    best = max(scores, key=scores.get)
    if scores[best] >= 3:
        return best
    return None
