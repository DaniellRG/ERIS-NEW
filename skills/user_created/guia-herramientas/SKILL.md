---
name: guia-herramientas
description: Guias de uso de las tools de ERIS de oficina, media y analisis: video_analyzer, pc_control, reminders, web_search, calculator, file_manager, music_player, fun_mode, email, calendar, clipboard, text_summarizer, translator, ocr, image_analyzer, audio_transcriber, data_analyst, data_viz, pdf_manager, template_engine, browser_history, whatsapp, telegram, phone, notifications, voice_clone, real_time_tts. Cargar cuando una de estas tools no responda como esperas o necesites su modo de uso exacto.
version: 1.0.0
category: productivity
tags: [guias, herramientas, oficina, media, analisis, comunicacion]
---

## ANÁLISIS DE VIDEOS (video_analyzer)

Eris puede analizar videos de YouTube y archivos locales de video.

ACCIONES (YouTube):
- `info`: Info del video (título, duración, descripción, tags). Params: url
- `subtitles`: Extraer subtítulos del video. Params: url
- `transcribe`: Descargar audio y transcribir con Whisper. Params: url
- `summarize`: Resumen completo (intenta subtítulos primero, luego Whisper). Params: url
- `research`: Research web sobre el tema del video. Params: url
- `full`: Análisis completo: info + subtítulos/transcripción + resumen. Params: url
- `history`: Ver historial de videos analizados

ACCIONES (Archivos Locales):
- `local`: Analizar video local con visión AI — extrae keyframes y los analiza con Gemini. Params: file="ruta/video.mp4", prompt="opcional"
- `local_audio`: Extraer y transcribir audio de video local con Whisper. Params: file="ruta/video.mp4"

COMPORTAMIENTO:
- Para YouTube: primero intentar subtítulos (más rápido), si falla usar Whisper
- Para archivos locales .mp4/.avi/.mov/.mkv: usar action=local para análisis visual o action=local_audio para transcripción
- Si ambos fallan, hacer research web con la info del video
- Guardar en historial para referencia futura
- Para videos largos (>30 min), avisar que tomará tiempo

## CONTROL DEL PC (pc_control)
Control del computador por voz.
- Volumen: volume_up, volume_down, volume_set (value: 0-100), mute, unmute
- Monitor: monitor_on, monitor_off
- Red: wifi_on, wifi_off, wifi_status, bluetooth_on, bluetooth_off, bluetooth_status
- Sistema: screenshot, lock, status (CPU/RAM/disco/batería)
- IMPORTANTE: apagar, suspender, reiniciar, hibernar y cerrar sesión están DESHABILITADOS por seguridad. Nunca intentes usarlos.

## RECORDATORIOS (reminders)
Crea recordatorios temporizados.
- add: crear recordatorio. Params: text="llamar a mamá", time="en 30 minutos"
- list: ver recordatorios activos
- cancel: cancelar por ID o texto
- clear: limpiar vencidos

## BÚSQUEDA WEB (web_search)
Búsqueda rápida via API (DuckDuckGo). Sin navegador, sin CAPTCHA. Tu herramienta PRINCIPAL para buscar.
- search: buscar. Params: query="noticias de hoy"
- news: buscar noticias. Params: query="últimas noticias"
- open: abrir URL en el navegador del usuario

**CUÁNDO USAR:** SIEMPRE que el usuario pida "buscar", "googlea", "investiga", "qué es", "información sobre". Es la más rápida.

## CALCULADORA (calculator)
Operaciones matemáticas, conversiones y fechas.
- calculate: resolver expresiones (ej: "2 + 2 * 3", "raiz cuadrada de 144")
- convert: unidades (km a millas, kg a libras, celsius a fahrenheit, etc.)
- date: info de fechas ("¿qué día es hoy?", "en 30 días qué fecha es")
- random: número aleatorio (ej: "random 1 a 100")

## GESTOR DE ARCHIVOS (file_manager)
Organiza y gestiona archivos.
- move: mover archivo. Params: source, destination
- copy: copiar
- rename: renombrar
- delete: eliminar
- organize: organizar carpeta por tipo (imágenes, videos, docs, etc.)
- list: contenido de carpeta
- search: buscar archivos por nombre
- info: info detallada de archivo
- create_dir: crear carpeta

## MÚSICA (music_player)
Reproduce música del PC por voz.
- play: reproducir (query: nombre de canción)
- pause, stop, next, previous
- volume: volumen de la música
- list: ver biblioteca
- shuffle: reproducción aleatoria

## ENTRETENIMIENTO (fun_mode)
Chistes, datos curiosos y trivial.
- joke: un chiste aleatorio
- fact: dato curioso
- trivia: pregunta de trivial
- answer: responder trivia (answer="1" o answer="Python")
- score: ver puntaje
- jokes/facts: varios de cada uno

## EMAIL (email_manager)
Envía y lee emails. Requiere configuración en api_keys.json.
- send: enviar email. Params: to, subject, body
- read: leer últimos emails de la bandeja
- status: ver configuración actual

## CALENDARIO (calendar_manager)
Eventos por voz.
- add: crear evento. Params: title, date (YYYY-MM-DD), time (HH:MM), duration (min)
- list: eventos del día
- delete: eliminar evento
- upcoming: próximos eventos
- today/tomorrow: resumen del día

## CLIPBOARD (clipboard_manager)
Historial de copiar/pegar.
- current: ver contenido actual
- copy: copiar texto al clipboard
- history: ver historial
- save: guardar contenido actual en historial
- search: buscar en historial
- clear: limpiar historial

## RESUMEN DE TEXTOS (text_summarizer)
Resume documentos y textos largos.
- summarize: resumir texto. Params: text="texto largo"
- extract_keywords: extraer palabras clave
- tldr: resumen de una línea
- bullet_points: puntos clave en viñetas
- shorten: acortar a N oraciones

## TRADUCTOR (translator)
Traduce texto o páginas web a español (o cualquier idioma).
- translate: traducir texto. Params: text="hello world", target="es"
- translate_web: traducir una PÁGINA WEB completa. Params: url="https://...", target="es", mode="text"|"file"
  - mode=text: devuelve la traducción (hasta max_chars).
  - mode=file: guarda la traducción completa en un archivo y devuelve la ruta.
  - Cuando el usuario pase/enuncie un link o diga "traducime esta página", usar translate_web.
- detect: detectar idioma del texto
- batch: traducir múltiples textos
- languages: listar idiomas disponibles
- Idiomas: es, en, fr, de, pt, it, ja, ko, zh

## LECTOR OCR (ocr_reader)
Lee texto de imágenes.
- read_image: leer texto de archivo de imagen
- read_screenshot: leer texto de captura de pantalla
- read_url: leer texto de imagen en URL

## ANALIZADOR DE IMÁGENES (image_analyzer)
Analiza imágenes con IA.
- analyze: describir imagen. Params: path="ruta/imagen.jpg"
- identify: identificar objetos en imagen
- read_text: OCR de imagen
- compare: comparar dos imágenes
- metadata: ver datos EXIF

## TRANSCRIPCIÓN DE AUDIO (audio_transcriber)
Convierte audio a texto.
- transcribe: transcribir archivo. Params: path="audio.mp3"
- transcribe_clipboard: transcribir del micrófono
- languages: idiomas soportados
- history: transcripciones anteriores

## ANALIZADOR DE DATOS (data_analyst)
Analiza CSV, Excel, JSON y datos tabulares.
- analyze: análisis completo. Params: path="datos.csv"
- summary: estadísticas descriptivas
- filter: filtrar filas por condición
- sort: ordenar por columna
- group: agrupar por columna (con agrupación y agregación)
- chart: describir tendencias visualmente
- compare: comparar dos datasets
- export: exportar resultados a JSON/CSV/TXT
- pandas: análisis avanzado con pandas (describe, dtypes, nulos). Params: path
- pivot: tabla pivot interactiva. Params: path, index, columns, values, aggfunc
- pandas_groupby: groupby avanzado con pandas. Params: path, column, agg_column, agg_func
- pandas_filter: filtrar con sintaxis pandas query. Params: path, query="age > 30"

## VISUALIZACIÓN DE DATOS (data_viz)
Genera gráficos y visualizaciones.
- bar: gráfico de barras. Params: title, labels=[], values=[]
- line: gráfico de líneas. Params: title, labels=[], values=[]
- pie: gráfico circular. Params: title, labels=[], values=[]
- scatter: diagrama de dispersión. Params: title, x=[], y=[]
- histogram: histograma. Params: title, values=[], bins=10
- table: tabla de datos. Params: title, headers=[], rows=[]
- system_report: reporte de salud del sistema (CPU, RAM, disco)
- usage_report: top 10 tools más usadas
- plotly/interactive: gráficos interactivos con Plotly (bar, line, pie, scatter, histogram, area, box). Params: chart_type, title, labels, values

## GESTOR DE PDFS (pdf_manager)
Operaciones con archivos PDF.
- read: extraer texto de PDF. Params: path="documento.pdf"
- merge: unir múltiples PDFs
- split: separar páginas
- create: crear PDF desde texto
- info: ver metadatos
- encrypt: encriptar con contraseña
- watermark: agregar marca de agua
- compress: reducir tamaño

## GENERADOR DE PLANTILLAS (template_engine)
Genera documentos con plantillas.
- generate: generar documento. Params: text="factura", data="datos JSON"
- list: ver plantillas disponibles
- create: crear nueva plantilla
- preview: vista previa del resultado
- save: guardar documento generado

## HISTORIAL DE NAVEGACIÓN (browser_history)
Lee historial de Chrome/Edge.
- chrome: ver historial de Chrome
- edge: ver historial de Edge
- bookmarks: ver marcadores
- search: buscar en historial. Params: text="término"
- stats: estadísticas de navegación
- export: exportar historial

## WHATSAPP WEB (whatsapp_web)
Envía mensajes por WhatsApp Web.
- send_message: enviar mensaje de texto. Params: text="mensaje", contact="nombre"
- send_file: enviar archivo
- open_chat: abrir chat específico
- contacts: ver contactos recientes
- search: buscar mensajes
- read_last: leer últimos mensajes de chat

## BOT DE TELEGRAM (telegram_bot)
Interface con Telegram.
- send_message: enviar mensaje. Params: text="mensaje", chat_id="id"
- list_chats: ver chats recientes
- read_messages: leer mensajes no leídos
- start_bot: iniciar bot en segundo plano
- stop_bot: detener bot
- status: estado del bot

## CONTROL DEL CELULAR (phone_control)
Controla el celular Android del dueño desde la PC (via adb/scrcpy, el celular
debe estar conectado por USB con depuración autorizada). Sin root.
- status: ¿hay celular conectado? modelo y resolución
- mirror: abre la pantalla del celular en la PC (scrcpy) para verla y controlarla
- open_app: abrir CUALQUIER app instalada. Params: app="youtube" o el nombre
  exacto de una app (resuelve también por nombre parcial).
- apps: ver apps conocidas
- open_url: abrir una web. Params: url="https://..."
- search: buscar en Google. Params: query="recetas de pasta"
- tap: tocar la pantalla. Params: x="540", y="1200"
- tap_text: tocar el elemento que contiene ese texto (para navegar apps sin
  calcular coordenadas). Params: text="Buscar"
- swipe: deslizar. Params: x1, y1, x2, y2, ms="300"
- scroll: hacer scroll. Params: direction="down|up"
- text: escribir texto (útil tras tap_text en un campo). Params: text="hola"
- ui: lista los elementos de la pantalla con sus coordenadas
- screenshot: captura la pantalla del celular
- battery: estado de la batería
- home: volver al inicio del celular
- back: ir para atrás
- recent: apps recientes
- unlock: intentar desbloquear
FLUJO recomendado para navegar una app: open_app → ui (leer pantalla) →
tap_text (tocar botón por texto) → text (escribir si hay campo) → scroll →
screenshot para confirmar. Si un tap_text no encuentra el texto, listá ui y
usá tap con las coordenadas que devuelve.
Guía completa: D:\Eris_Source\mobile\README.md

## CENTRO DE NOTIFICACIONES (notification_center)
Notificaciones push de escritorio.
- send: enviar notificación. Params: text="mensaje", title="título"
- history: ver notificaciones anteriores
- clear: limpiar historial
- schedule: programar notificación. Params: text="mensaje", time="en 5 minutos"
- desktop: notificación de Windows toast

## PERFILES DE VOZ (voice_clone)
Configuración de voz de ERIS.
- profile: ver perfil de voz actual
- samples: gestionar muestras de voz
- quality: verificar calidad de voz
- switch: cambiar voz. Params: text="nombre de voz"
- list: ver voces disponibles

## TTS EN TIEMPO REAL (real_time_tts)
Texto a voz con streaming.
- speak: hablar texto. Params: text="texto a decir"
- stop: detener reproducción
- pause: pausar
- resume: reanudar
- speed: cambiar velocidad. Params: text="1.5"
- voice: cambiar voz
- queue: agregar a cola de reproducción
