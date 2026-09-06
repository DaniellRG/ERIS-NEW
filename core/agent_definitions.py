"""core/agent_definitions.py — SINGLE SOURCE OF TRUTH de los agentes de ERIS.

12 agentes especializados. Cada agente domina un dominio con tools que
EXISTEN de verdad (registry==declarations). Claves: core, web, file, dev,
media, comm, vision, security, study, linux, guardian, mentora.
core/agent_router.py importa ESTA definición (no la duplica).
"""

__all__ = ["AGENT_DEFINITIONS"]

AGENT_DEFINITIONS = {
    # ── 1. CoreAgent (core) ──
    "core": {
        "name": 'CoreAgent',
        "description": 'Operaciones básicas del sistema: abrir apps, escritorio, ventanas, volumen, clipboard, monitor de sistema',
        "keywords": ['abrir', 'abre', 'abri', 'iniciar', 'lanzar', 'ejecutar app', 'escritorio', 'desktop', 'ventana', 'window', 'minimizar', 'maximizar', 'volumen', 'sonido', 'audio', 'mute', 'silenciar', 'clipboard', 'copiar', 'pegar', 'portapapeles', 'monitor', 'sistema', 'cpu', 'ram', 'disco', 'procesos', 'configuracion', 'settings', 'config', 'calculadora', 'calc', 'notepad', 'bloc de notas', 'captura', 'screenshot', 'pantalla', 'control', 'pc', 'computadora'],
        "penalty_keywords": ['spotify', 'musica', 'codigo', 'git', 'virus', 'email', 'calendario', 'documento', 'buscar', 'browser', 'malware', 'amenaza'],
        "tools": ['open_app', 'app_discovery', 'desktop_control', 'window_manager', 'system_monitor', 'system_volume', 'computer_settings', 'computer_control', 'clipboard_manager', 'screen_control', 'screen_see', 'shell_executor', 'process_manager', 'action_history', 'windows_settings', 'driver_manager', 'pc_control', 'quick_actions', 'context_menu', 'desktop_notifications'],
        "handler": 'agents.system_agent.handle_system',
    },
    # ── 2. WebAgent (web) ──
    "web": {
        "name": 'WebAgent',
        "description": 'Búsqueda web, navegación, scraping, investigación profunda, fetch de páginas',
        "keywords": ['buscar', 'busca', 'buscá', 'search', 'google', 'encontrar', 'navegador', 'browser', 'abrir pagina', 'web', 'sitio', 'scraping', 'scrapear', 'extraer', 'raspar', 'investigar', 'investiga', 'research', 'profundo', 'deep', 'url', 'enlace', 'link', 'pagina', 'page', 'resumir pagina', 'resumen web', 'summarize', 'fetch', 'contenido web', 'duckduckgo', 'ddg', 'bing'],
        "penalty_keywords": ['spotify', 'musica', 'codigo', 'git', 'virus', 'calendario', 'email', 'documento', 'abrir app', 'malware', 'amenaza', 'escaneá', 'escanear', 'puerto', 'exploit', 'hack', 'pentest'],
        "tools": ['web_search', 'super_search', 'deep_research', 'webfetch', 'web_navigation', 'browser_control', 'browser_auto', 'browser_unified', 'page_summarizer', 'smart_browser', 'web_scraper', 'multi_search', 'search_info', 'research', 'rss_reader', 'browser_history'],
        "handler": 'agents.search_agent.handle_search',
    },
    # ── 3. FileAgent (file) ──
    "file": {
        "name": 'FileAgent',
        "description": 'Operaciones con archivos: leer, escribir, editar, organizar, buscar, copiar, mover',
        "keywords": ['archivo', 'carpeta', 'directorio', 'folder', 'file', 'leer archivo', 'escribir archivo', 'editar archivo', 'copiar archivo', 'mover archivo', 'renombrar', 'eliminar archivo', 'buscar archivo', 'encontrar archivo', 'listar archivos', 'organizar archivos', 'organiza', 'backup', 'respaldo', 'copia de seguridad'],
        "penalty_keywords": ['spotify', 'musica', 'virus', 'email', 'calendario', 'codigo', 'git', 'navegador', 'browser'],
        "tools": ['file_api', 'file_manager', 'file_editor', 'file_processor', 'file_controller', 'ast_analyze', 'ast_edit', 'smart_file_organizer', 'file_organizer', 'file_monitor', 'file_profiler', 'backup_system', 'auto_backup', 'save_everywhere', 'clipboard_history'],
        "handler": 'agents.system_agent.handle_file',
    },
    # ── 4. DevAgent (dev) ──
    "dev": {
        "name": 'DevAgent',
        "description": 'Programación, código, git, codebase, DevOps, refactoring, testing',
        "keywords": ['codigo', 'code', 'programar', 'programa', 'script', 'funcion', 'function', 'clase', 'class', 'metodo', 'git', 'commit', 'push', 'pull', 'branch', 'repositorio', 'repo', 'python', 'javascript', 'html', 'css', 'react', 'node', 'compilar', 'compile', 'build', 'npm', 'pip', 'debug', 'error', 'bug', 'fix', 'arreglar codigo', 'refactor', 'refactorizar', 'optimizar codigo', 'test', 'testing', 'prueba', 'unittest', 'docker', 'deploy', 'desplegar', 'ci/cd', 'downloader', 'scraper', 'bot', 'proyecto', 'dependencias', 'instalar paquete', 'requirements', 'crear archivo', 'creá archivo', 'escribir archivo', 'hacer un programa', 'hacé un programa', 'make a'],
        "penalty_keywords": ['spotify', 'virus', 'calendario', 'email', 'pantalla', 'screenshot', 'volumen', 'brillo', 'reproducir', 'cancion', 'playlist'],
        "tools": ['code_helper', 'code_generator', 'code_analyzer', 'code_review', 'code_engineer', 'codebase_explorer', 'code_validator', 'git_control', 'git_smart', 'git_daily', 'github_pr', 'devops_pipeline', 'refactoring_engine', 'test_generator', 'dependency_manager', 'vscode_controller', 'dev_agent', 'web_generator', 'web_designer', 'react_designer', 'angular_designer', 'vue_designer', 'next_designer', 'tool_creator', 'code_sandbox', 'shell_session'],
        "handler": 'agents.dev_agent.handle_dev',
    },
    # ── 5. MediaAgent (media) ──
    "media": {
        "name": 'MediaAgent',
        "description": 'Música, YouTube, generación de imágenes, entretenimiento, games',
        "keywords": ['musica', 'music', 'spotify', 'cancion', 'song', 'playlist', 'youtube', 'video', 'yt', 'descargar video', 'imagen', 'image', 'foto', 'dibujar', 'generar imagen', 'juego', 'game', 'gaming', 'jugar', 'tiktok', 'reel', 'short', 'radio', 'podcast', 'audio', 'pelicula', 'movie', 'serie', 'anime'],
        "penalty_keywords": ['calendario', 'email', 'codigo', 'git', 'virus', 'instalar', 'archivo', 'carpeta', 'buscar'],
        "tools": ['music_player', 'play_direct', 'spotify_control', 'youtube_video', 'image_generation', 'image_generator', 'image_analyzer', 'video_analyzer', 'game_companion', 'game_agent', 'game_launcher', 'audio_transcriber', 'voice_recognition', 'tts_set_voice'],
        "handler": 'agents.media_agent.handle_media',
    },
    # ── 6. CommAgent (comm) ──
    "comm": {
        "name": 'CommAgent',
        "description": 'Email, calendario, mensajería, documentos, notificaciones, productividad',
        "keywords": ['email', 'correo', 'gmail', 'mail', 'enviar mensaje', 'calendario', 'calendar', 'evento', 'reunion', 'meeting', 'whatsapp', 'telegram', 'sms', 'mensaje', 'documento', 'document', 'pdf', 'word', 'excel', 'powerpoint', 'notificacion', 'notification', 'alerta', 'recordatorio', 'reminder', 'alarma', 'tarea', 'task', 'todo', 'pendiente', 'agenda', 'schedule', 'planificar', 'hoja de calculo', 'spreadsheet', 'presentacion'],
        "penalty_keywords": ['spotify', 'youtube', 'virus', 'codigo', 'git', 'pantalla', 'screenshot', 'volumen', 'abrir app'],
        "tools": ['email_manager', 'gmail_control', 'send_message', 'send_sms', 'whatsapp', 'whatsapp_web', 'telegram_bot', 'google_calendar', 'calendar_manager', 'reminder', 'reminders', 'document_creator', 'document_handler', 'document_manager', 'document_tool', 'document_generator', 'document_rag', 'presentation_generator', 'spreadsheet_generator', 'pdf_editor', 'pdf_manager', 'pdf_generator', 'office_docs', 'notification_center', 'notifications', 'task_manager', 'task_scheduler', 'goals', 'scheduler', 'alarm_manager', 'meeting_transcriber', 'obsidian_note', 'i18n'],
        "handler": 'agents.productivity_agent.handle_productivity',
    },
    # ── 7. VisionAgent (vision) ──
    "vision": {
        "name": 'VisionAgent',
        "description": 'Análisis de pantalla, OCR, visión por computadora, análisis de imágenes',
        "keywords": ['ver pantalla', 'que se ve', 'que hay en pantalla', 'qué hay en la pantalla', 'que hay en la pantalla', 'capturar pantalla', 'screenshot para analizar', 'ocr', 'leer texto imagen', 'texto en imagen', 'analizar imagen', 'analizar foto', 'que hay en la foto', 'vision', 'ver imagen', 'mirar imagen', 'reconocer texto', 'detectar', 'identificar imagen', 'cámara', 'camera', 'webcam', 'vigilancia', 'qué ves', 'que ves', 'ves en la pantalla', 'describe la pantalla', 'describí la pantalla'],
        "penalty_keywords": ['spotify', 'musica', 'virus', 'email', 'calendario', 'codigo', 'git', 'navegador', 'abrir app'],
        "tools": ['screen_vision', 'image_analyzer', 'ocr_reader', 'screen_see', 'camera_bus', 'vision_guardian', 'screen_context', 'screen_recorder'],
        "handler": 'agents.vision_agent.handle_vision',
    },
    # ── 8. SecurityAgent (security) ──
    "security": {
        "name": 'SecurityAgent',
        "description": 'Seguridad del sistema, escaneo, firewall, protección, criptografía',
        "keywords": ['seguridad', 'security', 'escanear', 'scan', 'virus', 'malware', 'firewall', 'proteccion', 'protect', 'amenaza', 'threat', 'encriptar', 'encrypt', 'cifrar', 'descifrar', 'contraseña', 'password', 'credential', 'clave', 'hack', 'vulnerabilidad', 'vulnerability', 'osint', 'investigar persona', 'whois', 'usb', 'dispositivo', 'periferico', 'ransomware', 'spyware', 'instalar programa', 'desinstalar programa', 'puerto abierto', 'puertos', 'escaneá la red', 'escanear la red', 'busca virus', 'buscá virus', 'exploit', 'pentest'],
        "penalty_keywords": ['spotify', 'youtube', 'calendario', 'email', 'pantalla', 'screenshot', 'volumen', 'brillo'],
        "tools": ['security_scanner', 'security_shield', 'eris_guardian', 'active_firewall', 'ransomware_shield', 'self_protection', 'osint_agent', 'cybersecurity', 'credential_recovery', 'keylogger_detector', 'usb_monitor', 'darkweb_monitor', 'disk_wiper', 'file_encryptor'],
        "handler": 'agents.security_agent.handle_security',
    },
    # ── 9. StudiesAgent (study) ──
    "study": {
        "name": 'StudiesAgent',
        "description": 'Estudios y aprendizaje: explica conceptos, resume material, arma planes de estudio, genera quizzes y flashcards, guarda notas de estudio.',
        "keywords": ['explica', 'explicame', 'explicá', 'qué es', 'que es', 'que son', 'explicar', 'define', 'sobre', 'acerca de', 'contame', 'estudiar', 'estudio', 'aprender', 'aprendizaje', 'plan de estudio', 'plan de estudios', 'cronograma', 'resume', 'resumi', 'resumen', 'sintetiza', 'quiz', 'flashcard', 'repaso', 'examen', 'evaluame', 'autoevaluaci', 'anota', 'anotá', 'apunte', 'nota de estudio', 'material de estudio', 'tesis', 'materia', 'facultad', 'universidad', 'clase', 'carrera'],
        "penalty_keywords": ['spotify', 'youtube', 'virus', 'email', 'calendario', 'pantalla', 'screenshot', 'volumen', 'abrir app', 'musica', 'video', 'instalá', 'instala', 'apagá', 'apaga', 'mail', 'archivo', 'carpeta', 'compilá', 'compila', 'script'],
        "tools": ['web_search', 'super_search', 'deep_research', 'webfetch', 'file_api', 'file_manager', 'save_memory', 'db_tasks', 'task_scheduler', 'reminders', 'document_creator', 'document_generator', 'pdf_generator'],
        "handler": 'agents.studies_agent.handle_studies',
    },
    # ── 10. AgenlixAgent (linux) ──
    "linux": {
        "name": 'AgenlixAgent',
        "description": 'Fragmento Linux de ERIS: terminal bash persistente + sudo on-demand, paquetes (apt), input físico Wayland (ydotool), OCR (tesseract), multimedia (ffmpeg/wf-recorder), git autónomo, mantenimiento programado, KDE Connect (celular) y controles de sistema. ERIS delega acá todo lo pesado de Linux.',
        "keywords": ['agelix', 'agenlix', 'fragmento linux', 'terminal', 'bash', 'consola', 'comando', 'shell', 'shell session', 'permiso administrador', 'con permisos', 'sudo', 'paquete', 'paquetes', 'apt', 'pacman', 'dnf', 'instalar paquete', 'instalá el paquete', 'instala el paquete', 'actualizá el sistema', 'actualiza el sistema', 'update system', 'wayland', 'hyprland', 'hyprctl', 'ydotool', 'mové el mouse', 'mueve el mouse', 'escribí con el teclado', 'doble clic', 'clic en', 'kde connect', 'celular', 'teléfono', 'telefono', 'vincular celular', 'hacé sonar', 'ocr', 'tesseract', 'leé el texto de la pantalla', 'lee el texto', 'grabá la pantalla', 'grabar la pantalla', 'wf-recorder', 'convertí video', 'convertir video', 'hacé un gif', 'git autónomo', 'git_autonomo', 'subí todo al repo', 'sube todo al repo', 'mantenimiento programado', 'hacé el mantenimiento', 'hace el mantenimiento', 'background services', 'file_undo', 'respaldar', 'respaldo', 'servicio systemd', 'systemctl', 'habilita el servicio'],
        "penalty_keywords": ['spotify', 'musica', 'youtube', 'email', 'calendario', 'virus', 'hack', 'codigo fuente explicame', 'web', 'navegador'],
        "tools": ['agelix', 'shell_session', 'terminal_agent', 'wayland_input', 'ocr_tool', 'media_lab', 'git_autonomo', 'maintenance', 'kde_connect', 'system_volume', 'window_manager', 'pc_control', 'desktop_notifications', 'screen_control', 'screen_see'],
        "handler": 'agents.agenlix_agent.handle_linux',
    },
    # ── 11. GuardianaAgent (guardian) ──
    "guardian": {
        "name": 'GuardianaAgent',
        "description": 'SAMX: el supervisor de autocuidado de ERIS. Vigila su salud 24/7 y repara automaticamente bugs, errores, fallos, duplicados, imports rotos y codigo mal, con backup + validacion + rollback, para mantenerla limpia, estable y al 100%.',
        "keywords": ['guardiana', 'samx', 'autocuidado', 'cuidame', 'cuida a eris', 'repará', 'repara', 'reparar', 'arreglá', 'arregla', 'corrigí', 'corregí', 'arregla los errores', 'corrige los errores', 'revisá mi salud', 'revisa mi salud', 'estoy rota', 'hay problemas', 'revisá todo', 'auditoría de salud', 'salud de eris', 'revisá si hay errores', 'detección de bugs', 'reducir duplicados', 'mantené a eris', 'mantenla estable', 'mantenla limpia', 'supervisión continua', 'vigila siempre', 'siempre pendiente', 'code review de eris', 'mantenimiento de eris', 'revisá mi código'],
        "penalty_keywords": ['spotify', 'musica', 'youtube', 'email', 'calendario', 'navegador', 'web', 'juego', 'pelicula', 'imagen', 'video youtube'],
        "tools": ['guardiana', 'evolucion', 'self_healing', 'code_guard', 'codebase_explorer', 'auto_healer', 'maintenance', 'system_health', 'self_evolution'],
        "handler": 'agents.guardiana_agent.handle_guardian',
    },
    # ── 12. MentoraAgent (mentora) ──
    "mentora": {
        "name": 'MentoraAgent',
        "description": 'MENTORA: el maestro de ERIS (superaprendizaje continuo). Aprende de verdad de todo (errores, soluciones, sesiones, web), busca soluciones por todas partes, enseña a Eris a resolver situaciones complejas/bajo estres/extremo, aplica lo aprendido, guarda todo y se comunica constantemente.',
        "keywords": ['mentora', 'maestro', 'maestra', 'aprendé', 'aprende', 'aprenda', 'la lección', 'lección', 'lesson', 'enseñame', 'ensename', 'cómo resolver', 'como resolver', 'busca la solución', 'buscá la solución', 'por web', 'estrés extremo', 'bajo estrés', 'situación compleja', 'situaciones complejas', 'aplicá lo aprendido', 'aplica lo aprendido', 'enseñame a resolver', 'dame clases', 'aprendé sobre', 'aprende sobre', 'explorá libre', 'explora libre', 'explorá', 'explora', 'aprendé algo nuevo', 'aprende algo nuevo', 'explorá en internet', 'importá esta página', 'importa esta página', 'importá la página', 'tu fuente', 'tus fuentes', 'mis fuentes', 'las fuentes', 'muestrame las fuentes', 'mostrame las fuentes', 'de dónde aprendés', 'aprendé de esta web', 'aprende de esta web', 'aprendé de esta página', 'aprende de esta página', 'ingestá', 'ingesta', 'aprendé de la web', 'aprende de la web', 'aprendé de las fuentes', 'aprende de las fuentes', 'navegá libre', 'navega libre'],
        "penalty_keywords": ['spotify', 'musica', 'youtube', 'email', 'calendario', 'navegador', 'web', 'juego', 'pelicula', 'imagen', 'video youtube', 'instalá'],
        "tools": ['mentora', 'learning_pipeline', 'save_memory', 'memory_rag', 'mistake_learner', 'feedback_learner', 'learning_curriculum', 'web_search', 'deep_research', 'webfetch', 'super_search', 'memory_unified', 'neuro_spheres', 'learn_from_mistake'],
        "handler": 'agents.mentora_agent.handle_mentora',
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
