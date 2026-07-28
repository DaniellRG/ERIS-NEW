"""
TOOL_DECLARATIONS — extracted from main.py
Contains the full list of tool declarations for ERIS
and the load_custom_tools function for dynamic tool loading.
"""

import json
from pathlib import Path

TOOL_DECLARATIONS = [
    {
        "name": "eris_ui_control",
        "description": "ERIS window. Actions: minimize, show, hide, toggle",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "minimize, restore, show, hide, hide_all, toggle"
                },
                "widget": {
                    "type": "STRING",
                    "description": "Widget name for show/hide/toggle: weather, spotify, system, notes, todo, maps"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "open_app",
        "description": "Opens any application on the computer. Actions: launch app by name",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Web search. Actions: search, news, images, videos, definition, open",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":      {"type": "STRING", "description": "Termino de busqueda"},
                "action":     {"type": "STRING", "description": "search, news, images, videos, definition, open"},
                "engine":     {"type": "STRING", "description": "auto (default, fallback automatico) | google | duckduckgo"},
                "num_results": {"type": "INTEGER", "description": "Numero de resultados (default: 5)"},
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user. Actions: report by city",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "whatsapp",
        "description": "WhatsApp. Actions: send, read, contacts, history",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "send | send_image | read | unread | add_contact | list_contacts | delete_contact"},
                "receiver":  {"type": "STRING",  "description": "Nombre del contacto o número de teléfono con código de país (ej: 5491155551234)"},
                "message":   {"type": "STRING",  "description": "Texto del mensaje a enviar"},
                "image_path":{"type": "STRING",  "description": "Ruta de la imagen para send_image"},
                "caption":   {"type": "STRING",  "description": "Descripción de la imagen (opcional)"},
                "count":     {"type": "INTEGER", "description": "Cantidad de mensajes a leer (default: 10)"},
                "name":      {"type": "STRING",  "description": "Nombre del contacto para add_contact/delete_contact"},
                "phone":     {"type": "STRING",  "description": "Número de teléfono con código de país (ej: 5491155551234) para add_contact"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends text via Telegram, Discord, Signal or other platforms. Actions: send by platform",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: Telegram, Discord, Signal, Messenger (NOT WhatsApp — use whatsapp tool)"}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Task Scheduler. Actions: set by date/time",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": "YouTube. Actions: play, search, playlist, pause, resume",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING", "description": "play, search, playlist, pause, resume, info, trending, stop, fullscreen"},
                "query":    {"type": "STRING", "description": "Nombre/URL/ID del video a reproducir o buscar"},
                "url":      {"type": "STRING", "description": "URL del video"},
                "video_id": {"type": "STRING", "description": "ID del video de 11 caracteres"},
                "count":    {"type": "NUMBER", "description": "Numero de resultados (default 5)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "computer_settings",
        "description": "System control. Actions: volume, brightness, WiFi, shortcuts, screenshots",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": "Browser control. Actions: go_to, search, scroll, click_element, read_page",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to, search, scroll, click_element, read_page, play_pause, new_tab, close_tab, select_result"},
                "url":         {"type": "STRING", "description": "URL para go_to o new_tab"},
                "query":       {"type": "STRING", "description": "Busqueda para search, search_info, o play_direct"},
                "direction":   {"type": "STRING", "description": "up | down (para scroll)"},
                "index":       {"type": "INTEGER", "description": "Numero de resultado (1=primero)"},
                "tabs":        {"type": "INTEGER", "description": "Cantidad de tabs para select_keyboard"},
                "description": {"type": "STRING", "description": "Descripcion del elemento para click_element"},
                "site":        {"type": "STRING", "description": "youtube | google (para select_result)"},
                "x":           {"type": "INTEGER", "description": "Coordenada X del mouse"},
                "y":           {"type": "INTEGER", "description": "Coordenada Y del mouse"},
                "amount":      {"type": "INTEGER", "description": "Cantidad de scroll (default 3-5)"},
                "duration":    {"type": "NUMBER", "description": "Duracion del movimiento del mouse en segundos"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "sleep_mode",
        "description": "Enters sleep mode. Disables mic until user says wake word locally.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "file_controller",
        "description": "File manager. Actions: list, create, delete, move, copy, read, write",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list, create, delete, move, copy, rename, read, write, find, organize, info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
                "old_text":    {"type": "STRING",  "description": "Texto a reemplazar (para edit)"},
                "new_text":    {"type": "STRING",  "description": "Nuevo texto o contenido (para edit)"},
                "mode":        {"type": "STRING",  "description": "replace | append | prepend | overwrite (para edit)"},
                "confirm":     {"type": "BOOLEAN", "description": "true para confirmar eliminaciones"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Desktop control. Actions: list, minimize, close, focus, open_app, get_state",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list, minimize, maximize, restore, close, focus, search, open_app, close_app, get_state, status"},
                "name":        {"type": "STRING", "description": "Window name for minimize, close, focus, get_info"},
                "query":       {"type": "STRING", "description": "Texto de busqueda para search"},
                "app":         {"type": "STRING", "description": "Nombre de app para open_app/close_app/is_open (ej: notepad.exe)"},
                "opacity":     {"type": "INTEGER", "description": "Nivel de opacidad 0-255 (para set_opacity)"},
                "period":      {"type": "STRING", "description": "Periodo para what_did_i_do: all, last_hour, last_5min"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files. Actions: write, edit, explain, run, build, auto",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch. Actions: plan, write, install, run, fix",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": "Executes complex multi-step tasks using multiple tools. Actions: multi-tool orchestration",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Mouse/keyboard control. Actions: type, click, scroll, hotkey, screenshot",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type, click, scroll, hotkey, screenshot, drag, move, paste, wait, focus_window"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait or mouse duration"},
                "title":       {"type": "STRING",  "description": "Window/tab title"},
                "url":         {"type": "STRING",  "description": "URL for open_tab"},
                "description": {"type": "STRING",  "description": "Element description for screen_find"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
                "smooth":      {"type": "BOOLEAN", "description": "Use smooth Bezier movement (default: true)"},
                "duration":    {"type": "NUMBER",  "description": "Duration for smooth_scroll in seconds"},
                "tab_index":   {"type": "INTEGER", "description": "Tab index for switch_tab"},
                "end_x":       {"type": "INTEGER", "description": "End X for drag"},
                "end_y":       {"type": "INTEGER", "description": "End Y for drag"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": "Steam/Epic games. Actions: update, install, list, schedule",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update, install, list, schedule, cancel"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options. Actions: search flights",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "shutdown_eris",
        "description": "Shuts down the assistant completely. Actions: shutdown on goodbye",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "file_processor",
        "description": "Process files. Actions: describe, ocr, summarize, convert, trim",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
                },
                "action": {
                    "type": "STRING",
                    "description": (
                        "What to do with the file. Examples by type:\n"
                        "image: describe | ocr | resize | compress | convert | info\n"
                        "pdf: summarize | extract_text | to_word | info\n"
                        "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                        "csv/excel: analyze | stats | filter | sort | convert | info\n"
                        "json: validate | format | analyze | to_csv\n"
                        "code: explain | review | fix | optimize | run | document | test\n"
                        "audio: transcribe | trim | convert | info\n"
                        "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                        "archive: list | extract\n"
                        "pptx: summarize | extract_text | analyze"
                    )
                },
                "instruction": {
                    "type": "STRING",
                    "description": "Free-form instruction not covered by other actions"
                },
                "format": {
                    "type": "STRING",
                    "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
                },
                "width":     {"type": "INTEGER", "description": "Target width for image resize"},
                "height":    {"type": "INTEGER", "description": "Target height for image resize"},
                "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
                "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
                "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
                "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
                "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
                "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
                "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
                "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
                "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
                "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
                "destination": {"type": "STRING", "description": "Output folder for archive extract"},
            },
            "required": []
        }
    },
    {
        "name": "google_calendar",
        "description": "Google Calendar manager. Actions: list, create, edit, delete events",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING",  "description": "list | create | edit | delete"},
                "summary":     {"type": "STRING",  "description": "Event title/name"},
                "start":       {"type": "STRING",  "description": "Start date/time: ISO, YYYY-MM-DD HH:MM, or DD/MM/YYYY HH:MM"},
                "end":         {"type": "STRING",  "description": "End date/time (optional — defaults to start + 1 hour)"},
                "description": {"type": "STRING",  "description": "Event notes or description"},
                "location":    {"type": "STRING",  "description": "Event location"},
                "event_id":    {"type": "STRING",  "description": "Event ID (first 8 chars from list) for edit/delete"},
                "days_ahead":  {"type": "INTEGER", "description": "Days to look ahead for list (default: 7)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "spotify_control",
        "description": "Spotify. Actions: play, pause, next, volume, search, shuffle",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play, pause, next, volume, shuffle, search, current, playlist"},
                "query":  {"type": "STRING", "description": "Búsqueda para play/search/search_desktop: canción, artista, álbum o playlist"},
                "type":   {"type": "STRING", "description": "track | album | playlist | artist (default: track)"},
                "value":  {"type": "STRING", "description": "Valor para volume (0-100), shuffle (true/false), repeat (off/track/context)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "rgb_control",
        "description": "Control RGB peripherals via OpenRGB. Actions: set_color, off, brightness, effect, rainbow, list",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":     {"type": "STRING", "description": "set_color | off | brightness | effect | rainbow | list"},
                "color":      {"type": "STRING", "description": "Color: nombre (rojo, azul, verde, blanco…) o hex #RRGGBB"},
                "brightness": {"type": "INTEGER", "description": "Brillo 0-100 (default: 100)"},
                "device":     {"type": "STRING", "description": "Filtro por nombre de dispositivo (opcional, aplica a todos si se omite)"},
                "effect":     {"type": "STRING", "description": "Nombre del efecto para la acción effect"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "scheduler",
        "description": "Creates/manages scheduled automations. Actions: list, create, delete, enable, disable, run_now",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":           {"type": "STRING",  "description": "list | create | delete | enable | disable | run_now"},
                "name":             {"type": "STRING",  "description": "Nombre descriptivo de la tarea"},
                "frequency":        {"type": "STRING",  "description": "daily | weekly | interval | once"},
                "hour":             {"type": "INTEGER", "description": "Hora de ejecución (0-23)"},
                "minute":           {"type": "INTEGER", "description": "Minuto de ejecución (0-59)"},
                "weekday":          {"type": "STRING",  "description": "Día de la semana para frequency=weekly"},
                "interval_minutes": {"type": "INTEGER", "description": "Intervalo en minutos para frequency=interval"},
                "task_action":      {"type": "STRING",  "description": "backup | file_controller | notify | custom_script | browser_control"},
                "task_parameters":  {"type": "OBJECT",  "description": "Parámetros de la tarea (source, destination para backup, etc.)"},
                "task_id":          {"type": "STRING",  "description": "ID de la tarea (primeros 6 chars) para delete/enable/disable/run_now"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "google_drive",
        "description": "Google Drive manager. Actions: list, search, upload, download, create_folder, delete, share, info",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | search | upload | download | create_folder | delete | share | info"},
                "folder_id":   {"type": "STRING", "description": "ID de la carpeta (default: root)"},
                "file_id":     {"type": "STRING", "description": "ID del archivo para download/delete/share/info"},
                "path":        {"type": "STRING", "description": "Ruta local para upload"},
                "name":        {"type": "STRING", "description": "Nombre de la nueva carpeta"},
                "query":       {"type": "STRING", "description": "Término de búsqueda"},
                "destination": {"type": "STRING", "description": "Carpeta local de destino para download"},
                "email":       {"type": "STRING", "description": "Email para compartir"},
                "role":        {"type": "STRING", "description": "reader | writer | commenter"},
                "confirm":     {"type": "BOOLEAN", "description": "true para confirmar eliminación"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "gmail_control",
        "description": "Gmail manager. Actions: inbox, read, send, reply, search, archive, delete, mark_read, labels",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":     {"type": "STRING",  "description": "inbox | read | send | reply | search | archive | delete | mark_read | labels"},
                "count":      {"type": "INTEGER", "description": "Cantidad de correos a listar/buscar (default: 5)"},
                "message_id": {"type": "STRING",  "description": "ID del mensaje para read/reply/archive/delete/mark_read"},
                "to":         {"type": "STRING",  "description": "Destinatario para send"},
                "subject":    {"type": "STRING",  "description": "Asunto para send"},
                "body":       {"type": "STRING",  "description": "Cuerpo del correo para send/reply"},
                "query":      {"type": "STRING",  "description": "Búsqueda Gmail para search (ej: 'from:juan', 'subject:factura')"},
                "confirm":    {"type": "BOOLEAN", "description": "true para confirmar eliminación"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "google_maps",
        "description": "Navigation routes and interactive maps. Actions: directions, search",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "directions | search"},
                "origin":      {"type": "STRING", "description": "Punto de partida (dirección, ciudad, lugar)"},
                "destination": {"type": "STRING", "description": "Destino (dirección, ciudad, lugar)"},
                "mode":        {"type": "STRING", "description": "car (auto) | walk (caminando) | bike (bicicleta). Default: car"},
                "query":       {"type": "STRING", "description": "Lugar a buscar en el mapa (para action=search)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "rules_engine",
        "description": "Automation and alert engine. Actions: list, create, delete, enable, disable, trigger, alert",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":     {"type": "STRING", "description": "list | list_phrases | create | delete | enable | disable | trigger | alert"},
                "name":       {"type": "STRING", "description": "Nombre de la automatización"},
                "rule_id":    {"type": "STRING", "description": "ID de la regla para delete/enable/disable/trigger"},
                "condition":  {
                    "type": "OBJECT",
                    "description": (
                        "Condición. phrase: {type:phrase, trigger:'texto exacto', match:contains|exact|startswith}. "
                        "time: {type:time, hour:8, minute:0, days:[monday,...]}. "
                        "file_exists: {type:file_exists, path:'...'}. always: {type:always}"
                    )
                },
                "action_def": {
                    "type": "OBJECT",
                    "description": (
                        "Acción a ejecutar. "
                        "open_app: {type:open_app, app_name:'Spotify'}. "
                        "spotify_play: {type:spotify_play, query:'Back in Black AC/DC'}. "
                        "browser: {type:browser, url:'https://...'}. "
                        "smart_home: {type:smart_home, device:'living', action:'on'}. "
                        "composite: {type:composite, actions:[{...},{...}]}. "
                        "notify: {type:notify, message:'...'}. speak: {type:speak, message:'...'}. "
                        "run_script: {type:run_script, command:'...'}."
                    )
                },
                "message":    {"type": "STRING", "description": "Mensaje para action=alert"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "user_profile",
        "description": "User profile. Actions: view, set_preference, notes, habits",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "view | set_preference | set_name | add_note | notes | habits | reset"},
                "key":    {"type": "STRING", "description": "Clave de preferencia (ej: idioma, tema, ciudad)"},
                "value":  {"type": "STRING", "description": "Valor de la preferencia"},
                "name":   {"type": "STRING", "description": "Nombre del usuario"},
                "note":   {"type": "STRING", "description": "Nota personal a guardar"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "goals",
        "description": "Long-term goals. Actions: list, create, update, complete, detail",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING",  "description": "list | create | update_progress | complete | complete_step | add_step | delete | detail"},
                "goal_id":     {"type": "STRING",  "description": "ID del objetivo para update/complete/delete/detail"},
                "title":       {"type": "STRING",  "description": "Título del objetivo"},
                "description": {"type": "STRING",  "description": "Descripción detallada"},
                "deadline":    {"type": "STRING",  "description": "Fecha límite ISO (YYYY-MM-DD)"},
                "progress":    {"type": "INTEGER", "description": "Progreso 0-100"},
                "steps":       {"type": "ARRAY",   "items": {"type": "STRING"}, "description": "Lista de pasos del objetivo"},
                "step":        {"type": "STRING",  "description": "Texto del nuevo paso (add_step)"},
                "step_index":  {"type": "INTEGER", "description": "Índice del paso a completar (0-based)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "git_control",
        "description": "Full Git integration. Actions: status, log, diff, commit, add, branches, pull, push, stash, analyze",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING",  "description": "status, log, diff, commit, add, branches"},
                "repo_path":   {"type": "STRING",  "description": "Ruta al repositorio Git"},
                "message":     {"type": "STRING",  "description": "Mensaje del commit"},
                "branch_name": {"type": "STRING",  "description": "Nombre de la rama"},
                "remote":      {"type": "STRING",  "description": "Remote (default: origin)"},
                "n":           {"type": "INTEGER", "description": "Número de commits para log"},
                "file":        {"type": "STRING",  "description": "Archivo específico para diff"},
                "staged":      {"type": "BOOLEAN", "description": "Mostrar diff staged"},
                "add_all":     {"type": "BOOLEAN", "description": "Agregar todos los archivos antes del commit (default: true)"},
                "files":       {"type": "ARRAY",   "items": {"type": "STRING"}, "description": "Archivos para add"},
                "sub":         {"type": "STRING",  "description": "Subcomando para stash: push|pop|list"},
            },
            "required": ["action", "repo_path"]
        }
    },
    {
        "name": "codebase",
        "description": "Code index. Actions: index, search, find_symbol, generate_docs",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING", "description": "index | list | info | search | find_symbol | generate_docs | remove"},
                "path":      {"type": "STRING", "description": "Ruta del proyecto a indexar"},
                "name":      {"type": "STRING", "description": "Nombre del proyecto (default: nombre de carpeta)"},
                "project":   {"type": "STRING", "description": "Nombre del proyecto para info/search/find_symbol"},
                "query":     {"type": "STRING", "description": "Texto a buscar en el código"},
                "symbol":    {"type": "STRING", "description": "Nombre de función/clase a buscar"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo para generate_docs"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "knowledge_base",
        "description": "Knowledge base. Actions: add, search, list, get, delete",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING", "description": "add/save/store | search/find | list | get/read/view | update | delete | stats | export"},
                "title":    {"type": "STRING", "description": "Título de la entrada"},
                "content":  {"type": "STRING", "description": "Contenido o texto a guardar"},
                "type":     {"type": "STRING", "description": "note | idea | snippet | reference | fact | task | question"},
                "tags":     {"type": "STRING", "description": "Tags separados por coma (ej: python, eris, idea)"},
                "query":    {"type": "STRING", "description": "Búsqueda en la base de conocimiento"},
                "entry_id": {"type": "STRING", "description": "ID de la entrada para get/update/delete"},
                "path":     {"type": "STRING", "description": "Ruta para exportar (action=export)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "screen_recorder",
        "description": "Records PC screen with or without audio. Actions: start, stop, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING", "description": "start | stop | status"},
                "duration": {"type": "NUMBER", "description": "Duración en segundos (default: 30)"},
                "fps":      {"type": "NUMBER", "description": "Frames por segundo (default: 15)"},
                "with_audio": {"type": "STRING", "description": "true/false — grabar audio del micrófono"},
                "region":   {"type": "STRING", "description": "Región: left,top,width,height (ej: 0,0,800,600)"},
                "name":     {"type": "STRING", "description": "Nombre del archivo de salida"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "translator",
        "description": "Real-time translation. Actions: translate_text, start_monitoring, stop_monitoring, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "translate_text | start_monitoring | stop_monitoring | status"},
                "text":        {"type": "STRING", "description": "Texto a traducir (solo para translate_text)"},
                "target_lang": {"type": "STRING", "description": "Idioma destino (ej: es, en, fr, de, pt, it)"},
                "source_lang": {"type": "STRING", "description": "Idioma origen (opcional, auto-detect si se omite)"},
                "interval":    {"type": "NUMBER", "description": "Intervalo de monitoreo en segundos (default: 1.0)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "meeting_transcriber",
        "description": "Automatic meeting transcription. Actions: start, stop, status, summarize",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING", "description": "start | stop | status | summarize"},
                "duration": {"type": "NUMBER", "description": "Duracion en segundos (default: 300)"},
                "backend":  {"type": "STRING", "description": "auto | google (default: auto = vosk local)"},
                "name":     {"type": "STRING", "description": "Nombre del archivo de salida"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "network_monitor",
        "description": "Network monitor. Actions: connections, wifi, ping, scan, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING", "description": "connections | bandwidth | wifi | ping | scan | monitor_start | monitor_stop | status"},
                "host":     {"type": "STRING", "description": "Host para ping (ej: 8.8.8.8, google.com)"},
                "count":    {"type": "NUMBER", "description": "Numero de pings (default: 4)"},
                "type":     {"type": "STRING", "description": "Tipo de conexiones: all, tcp, udp (default: all)"},
                "subnet":   {"type": "STRING", "description": "Subred para escaneo (ej: 192.168.1)"},
                "interval": {"type": "NUMBER", "description": "Intervalo en segundos (default: 1)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "quick_actions",
        "description": "Custom shortcuts. Actions: add, update, remove, list, run",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":  {"type": "STRING", "description": "add | update | remove | list | run"},
                "name":    {"type": "STRING", "description": "Nombre del atajo"},
                "command": {"type": "STRING", "description": "Comando a ejecutar (solo para add/update)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "pdf_editor",
        "description": "PDF editor. Actions: read, merge, split, info, fill_form, add_signature",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING", "description": "read | merge | split | info | fill_form | add_signature"},
                "path":      {"type": "STRING", "description": "Ruta del PDF"},
                "pages":     {"type": "STRING", "description": "Paginas a leer/dividir (ej: 1-3,5,7 o numero de paginas)"},
                "output":    {"type": "STRING", "description": "Nombre del archivo de salida"},
                "files":     {"type": "STRING", "description": "Lista de PDFs separados por coma para fusionar"},
                "fields":    {"type": "STRING", "description": "Campos del formulario: campo1=valor1, campo2=valor2"},
                "signature": {"type": "STRING", "description": "Ruta de la imagen de firma"},
                "x":         {"type": "NUMBER", "description": "Posicion X de la firma"},
                "y":         {"type": "NUMBER", "description": "Posicion Y de la firma"},
                "width":     {"type": "NUMBER", "description": "Ancho de la firma en px"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "context_menu",
        "description": "Windows context menu for ERIS. Actions: install, uninstall, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "install | uninstall | status"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "sms",
        "description": "SMS from PC via Twilio. Actions: send, history, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":  {"type": "STRING", "description": "send | history | status"},
                "to":      {"type": "STRING", "description": "Numero destino con codigo pais (ej: +56912345678)"},
                "message": {"type": "STRING", "description": "Texto del mensaje"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dashboard",
        "description": "Web dashboard with system stats. Actions: start, stop, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | status"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "social_media",
        "description": "Social media control: Twitter/X, Instagram, TikTok, LinkedIn. Actions: post, like, timeline, search",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "platform": {"type": "STRING", "description": "twitter | instagram | tiktok | linkedin | setup"},
                "action":   {"type": "STRING", "description": (
                    "Twitter: tweet, delete_tweet, like, retweet, timeline, search_tweets, my_tweets, profile | "
                    "Instagram: post/upload_photo, story, send_dm, feed, profile, like, comment | "
                    "TikTok: upload/publicar, profile/perfil, trending | "
                    "LinkedIn: post/publicar, profile/perfil, send_message/mensaje, feed"
                )},
                "text":       {"type": "STRING", "description": "Texto del tweet/post/comentario/mensaje"},
                "content":    {"type": "STRING", "description": "Contenido del post (LinkedIn/TikTok)"},
                "tweet_id":   {"type": "STRING", "description": "ID del tweet para like/retweet/delete"},
                "media_id":   {"type": "STRING", "description": "ID del post de Instagram para like/comment"},
                "username":   {"type": "STRING", "description": "Usuario para DM/perfil (Instagram, TikTok, LinkedIn)"},
                "receiver":   {"type": "STRING", "description": "Destinatario del DM de Instagram"},
                "image_path": {"type": "STRING", "description": "Ruta imagen para Instagram/LinkedIn"},
                "video_path": {"type": "STRING", "description": "Ruta del video para TikTok"},
                "caption":    {"type": "STRING", "description": "Descripción/caption de la foto o video"},
                "query":      {"type": "STRING", "description": "Búsqueda de tweets"},
                "count":      {"type": "INTEGER", "description": "Cantidad de resultados (default: 5)"},
            },
            "required": ["platform", "action"]
        }
    },
    {
        "name": "windows_settings",
        "description": "Full Windows settings control. Actions: display, audio, network, power, system, apps, security, etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "La acción a realizar. Ejemplos por categoría:\n"
                        "display: get_brightness | set_brightness | get_resolution | set_resolution | "
                        "set_refresh_rate | get_scaling | set_scaling | night_light_on | night_light_off | "
                        "hdr_on | hdr_off | set_orientation | list_monitors | open\n"
                        "audio: get_volume | set_volume | mute | unmute | toggle_mute | list_devices | "
                        "set_device | get_mic_volume | set_mic_volume | open\n"
                        "network: list_wifi | connect_wifi | disconnect_wifi | wifi_on | wifi_off | "
                        "get_ip | set_dns | flush_dns | airplane_on | airplane_off | "
                        "bluetooth_on | bluetooth_off | set_proxy | disable_proxy | open\n"
                        "power: get_plan | set_plan | list_plans | sleep | hibernate | battery_status | "
                        "set_sleep_timeout | set_screen_timeout | fast_startup_on | fast_startup_off | open\n"
                        "system: info | get_hostname | set_hostname | get_datetime | set_datetime | "
                        "set_timezone | restart | shutdown | lock | get_env | set_env | delete_env | open\n"
                        "personalization: set_wallpaper | get_wallpaper | dark_mode | light_mode | "
                        "transparency_on | transparency_off | taskbar_position | screensaver | open\n"
                        "apps: list | uninstall | startup_apps | set_default | open\n"
                        "security: defender_scan | defender_status | firewall_on | firewall_off | "
                        "firewall_status | uac_level | bitlocker_status | list_users | add_user | open\n"
                        "input: get_mouse_speed | set_mouse_speed | swap_buttons | get_keyboard_speed | "
                        "set_keyboard_speed | list_languages | add_language | open\n"
                        "storage: list_drives | disk_usage | cleanup | empty_trash | clean_temp | "
                        "defrag | chkdsk | open\n"
                        "services: list | start | stop | restart | status | list_processes | kill_process | open\n"
                        "privacy: camera_on | camera_off | mic_on | mic_off | location_on | location_off | "
                        "telemetry_level | notifications_on | notifications_off | clipboard_history_on | "
                        "clipboard_history_off | open\n"
                        "registry: read | write | delete | export\n"
                        "accessibility: magnifier_on | magnifier_off | narrator_on | narrator_off | "
                        "high_contrast_on | high_contrast_off | osk_on | open\n"
                        "open_settings: <nombre del panel, ej: display, sound, wifi, bluetooth, apps>"
                    )
                },
                "value":    {"type": "STRING",  "description": "Valor para la acción (ej: 80 para brillo, 'Dark' para tema, SSID para wifi, etc.)"},
                "value2":   {"type": "STRING",  "description": "Segundo valor cuando se necesitan dos parámetros (ej: contraseña de WiFi, valor de registro)"},
                "name":     {"type": "STRING",  "description": "Nombre del servicio, proceso, usuario, app, o variable de entorno"},
                "hive":     {"type": "STRING",  "description": "Para registry: HKLM | HKCU | HKCR | HKU | HKCC"},
                "key":      {"type": "STRING",  "description": "Para registry: ruta de la clave del registro"},
                "reg_name": {"type": "STRING",  "description": "Para registry: nombre del valor del registro"},
                "reg_type": {"type": "STRING",  "description": "Para registry: REG_SZ | REG_DWORD | REG_BINARY | REG_EXPAND_SZ"},
                "path":     {"type": "STRING",  "description": "Ruta de archivo (para wallpaper, export registry, etc.)"},
                "monitor":  {"type": "INTEGER", "description": "Índice del monitor (0, 1, 2…)"},
                "width":    {"type": "INTEGER", "description": "Ancho de resolución"},
                "height":   {"type": "INTEGER", "description": "Alto de resolución"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "save_memory",
        "description": "Saves important user facts to long-term memory. Actions: save by category",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "image_generation",
        "description": "AI image generation from text prompts. Actions: generate via Pollinations/Gemini",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt":       {"type": "STRING",  "description": "Descripción detallada de la imagen a generar"},
                "count":        {"type": "INTEGER", "description": "Cantidad de imágenes (1-4, default: 1)"},
                "aspect_ratio": {"type": "STRING",  "description": "Relación de aspecto: 1:1 | 4:3 | 3:4 | 16:9 | 9:16 (default: 1:1)"},
                "save_path":    {"type": "STRING",  "description": "Carpeta de guardado (default: ~/Pictures/ERIS_Generadas)"},
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "smart_home",
        "description": "Smart home device control. Actions: on, off, toggle, color, brightness, temperature, scene, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING",  "description": "on | off | toggle | color | brightness | temperature | scene | status | list | setup"},
                "device":      {"type": "STRING",  "description": "Nombre o sala del dispositivo (ej: 'sala', 'cuarto', 'lampara principal'). Omitir = todos."},
                "color":       {"type": "STRING",  "description": "Color: nombre (rojo, azul, blanco, cálido…) o hex #RRGGBB"},
                "value":       {"type": "INTEGER", "description": "Valor numérico para brightness (1-100) o temperatura Kelvin (1700-9000)"},
                "brightness":  {"type": "INTEGER", "description": "Brillo 1-100 (alternativa a value)"},
                "scene":       {"type": "STRING",  "description": "Nombre de la escena: relajar, leer, trabajar, noche, fiesta"},
                "protocol":    {"type": "STRING",  "description": "tuya | hue | lifx | yeelight. Omitir = usa el configurado por defecto."},
                "group":       {"type": "STRING",  "description": "Nombre del grupo/sala en Philips Hue"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "system_monitor",
        "description": "System monitor. Actions: cpu, ram, disk, gpu, processes, kill",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING",  "description": "cpu | ram | disk | network | gpu | temperature | battery | uptime | processes | kill | report"},
                "sort_by":  {"type": "STRING",  "description": "Para processes: cpu (default) | ram"},
                "count":    {"type": "INTEGER", "description": "Para processes: cantidad a mostrar (default: 10)"},
                "name":     {"type": "STRING",  "description": "Para kill: nombre o PID del proceso"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "document_handler",
        "description": "Docs. Actions: create, read, convert, merge, summarize",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":     {"type": "STRING", "description": "create_word, create_excel, create_pdf, read, convert_to_pdf, merge_pdfs, summarize, translate"},
                "title":      {"type": "STRING", "description": "Titulo del documento (para crear)"},
                "content":    {"type": "STRING", "description": "Contenido del documento. # heading, ## subheading, - bullets, --- separador de slides"},
                "path":       {"type": "STRING", "description": "Ruta del archivo (para leer/convertir/info/open)"},
                "paths":      {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Lista de rutas (para merge_pdfs)"},
                "output":     {"type": "STRING", "description": "Ruta de salida (para convert_to_pdf/merge_pdfs)"},
                "output_dir": {"type": "STRING", "description": "Directorio de salida (para split_pdf)"},
                "target_lang":{"type": "STRING", "description": "Idioma destino: es, en, fr, de, pt, it, ja, zh, ko, ru, ar (para translate)"},
                "question":   {"type": "STRING", "description": "Pregunta sobre el documento (para interpret)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "tiktok_analyzer",
        "description": "Analyzes public TikTok profiles. Actions: extract stats, videos, followers",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "profile_url": {"type": "STRING", "description": "URL completa del perfil de TikTok (ej: https://www.tiktok.com/@usuario)"},
                "max_videos":  {"type": "INTEGER", "description": "Cantidad máxima de videos a analizar (default: 8)"},
            },
            "required": ["profile_url"]
        }
    },
    {
        "name": "arca_invoice",
        "description": "Argentina ARCA/AFIP digital invoices. Actions: generar, listar, historial",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":         {"type": "STRING", "description": "generar | listar | historial"},
                "tipo":           {"type": "INTEGER", "description": "1=A, 5=C, 6=B, 3=NC_A, 8=NC_B. Use action=listar"},
                "razon_social":   {"type": "STRING", "description": "Razón social del receptor (obligatorio para Factura A/B)"},
                "cuit_receptor":  {"type": "STRING", "description": "CUIT del receptor (obligatorio para Factura A/B)"},
                "domicilio":      {"type": "STRING", "description": "Domicilio del receptor (opcional)"},
                "detalle":        {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"descripcion": {"type": "STRING"}, "precio": {"type": "NUMBER"}, "cantidad": {"type": "INTEGER"}}}, "description": "Lista de productos/servicios: [{'descripcion':'...', 'precio':0.0, 'cantidad':1}]"},
                "importe_neto":   {"type": "NUMBER", "description": "Importe neto gravado (se calcula del detalle si no se especifica)"},
                "importe_iva":    {"type": "NUMBER", "description": "Importe de IVA (se calcula al 21% si no se especifica)"},
                "iva_pct":        {"type": "NUMBER", "description": "Porcentaje de IVA (default: 21.0). 0 para exento."},
                "fecha":          {"type": "STRING", "description": "Fecha del comprobante YYYY-MM-DD (default: hoy)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "accessibility",
        "description": "Accessibility. Actions: task_simplify, routine, speech_config",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "task_simplify — descomponer texto en pasos simples | "
                        "emotional — intervencion emocional | "
                        "routine — gestion de rutinas gamificadas | "
                        "eye_tracking — control ocular | "
                        "micro_movement — micromovimientos | "
                        "speech_config — tolerancia de voz | "
                        "feedback — feedback visual/haptico | "
                        "config — ver o cambiar configuracion"
                    )
                },
                "text":     {"type": "STRING", "description": "Texto a simplificar (para task_simplify)"},
                "format":   {"type": "STRING", "description": "Formato: steps (default) | summary | explain"},
                "name":     {"type": "STRING", "description": "Nombre de rutina (para routine add/complete)"},
                "setting":  {"type": "STRING", "description": "Clave de configuracion a ver o cambiar"},
                "value":    {"type": "STRING", "description": "Valor para la configuracion"},
                "level":    {"type": "NUMBER", "description": "Nivel de tolerancia (0.1-1.0) o sensibilidad"},
                "stress_level": {"type": "NUMBER", "description": "Nivel de estres estimado (0.0-1.0)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "screen_vision",
        "description": "ERIS sees user screen via AI vision. Actions: describe, question, help, read",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "describe, question, help, read"
                },
                "question": {
                    "type": "STRING",
                    "description": "Pregunta o tarea específica sobre lo que se ve en pantalla (para action=question/help)"
                },
                "monitor": {
                    "type": "INTEGER",
                    "description": "0=toda la pantalla (default), 1=monitor principal, 2=segundo monitor"
                },
            },
            "required": ["action"]
        }
    },
    {
        "name": "morning_brief",
        "description": "Generates intelligent morning report. Actions: generate with optional force",
        "parameters": {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "Si True, genera el informe aunque ya se haya dado hoy."
                }
            },
            "required": []
        }
    },
    {
        "name": "vision_guardian",
        "description": "Proactive screen monitoring guardian. Actions: status, enable, disable, check_now, set_interval",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "enable", "disable", "check_now", "set_interval"],
                    "description": "Acción: status | enable | disable | check_now | set_interval"
                },
                "seconds": {
                    "type": "integer",
                    "description": "Para set_interval: segundos entre análisis (30-600)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "accessibility_overlay",
        "description": "Toggle the floating accessibility toolbar. Actions: show, hide, toggle, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "show — mostrar | hide — cerrar | toggle — alternar | status — estado actual"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "openrouter_agent",
        "description": "Delegates complex text tasks to OpenRouter models. Actions: query with optional model",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "El prompt o instrucción completa para el agente de OpenRouter"
                },
                "model": {
                    "type": "STRING",
                    "description": "Opcional. Modelo a usar, por defecto google/gemini-2.5-flash"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "terminal_agent",
        "description": "CMD/PowerShell + Win+R. Actions: run_cmd, run_ps, open, win_r, elevated, info",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "run_cmd, run_ps, run, elevated, open, win_r, shell_execute, list_history, info"
                },
                "command": {
                    "type": "STRING",
                    "description": "Command to execute or app/folder/URL to open"
                },
                "target": {
                    "type": "STRING",
                    "description": "Target for open/win_r: app name, folder path, or URL"
                },
                "shell": {
                    "type": "STRING",
                    "description": "cmd or powershell (auto-detected)"
                },
                "elevated": {
                    "type": "BOOLEAN",
                    "description": "Run as administrator (UAC prompt)"
                },
                "timeout": {
                    "type": "INTEGER",
                    "description": "Max seconds (default 30)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "native_ui",
        "description": "UI Automation. Actions: list_windows, focus_window, type_in_window",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Acción a realizar: list_windows | focus_window | type_in_window | click_center"
                },
                "window_title": {
                    "type": "STRING",
                    "description": "El nombre (o parte del nombre) de la ventana destino. (Ej: 'WhatsApp', 'Chrome')"
                },
                "text": {
                    "type": "STRING",
                    "description": "El texto a escribir (solo si action es type_in_window)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "tool_creator",
        "description": "Program and install new ERIS tools. Actions: create tool with code and schema",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tool_name": {
                    "type": "STRING",
                    "description": "Nombre de la herramienta en snake_case"
                },
                "description": {
                    "type": "STRING",
                    "description": "Descripción clara de la herramienta y para qué sirve"
                },
                "parameters_schema": {
                    "type": "STRING",
                    "description": "El bloque de 'properties' del JSON schema en formato string válido. Ej: '{\"accion\": {\"type\": \"STRING\"}}'"
                },
                "python_code": {
                    "type": "STRING",
                    "description": "Código Python con la función def <tool_name>(parameters: dict, player=None, speak=None) -> str:"
                }
            },
            "required": ["tool_name", "description", "parameters_schema", "python_code"]
        }
    },
    {
        "name": "proactive_automation",
        "description": "Proactive rules. Actions: add_rule, list_rules, trigger_check",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "add_rule, list_rules, delete_rule, trigger_check"
                },
                "rule_name": {
                    "type": "STRING",
                    "description": "Nombre identificativo de la regla de automatización"
                },
                "trigger": {
                    "type": "STRING",
                    "description": "Disparador: cpu_high | ram_high | time_of_day | app_open"
                },
                "trigger_value": {
                    "type": "STRING",
                    "description": "Valor del disparador (ej. '85' para 85% cpu, '22:00' para hora, 'chrome.exe' para app)"
                },
                "action_to_take": {
                    "type": "STRING",
                    "description": "Acción a ejecutar (ej. 'optimize_ram', 'mute_system', 'run_script')"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "auto_programmer",
        "description": "Autonomous coding suite. Actions: create_tool, fix_tool, test_tool, list_tools, plan_code",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "create_tool, fix_tool, test_tool, list_tools, plan_code"
                },
                "tool_name": {
                    "type": "STRING",
                    "description": "Nombre de la herramienta en snake_case"
                },
                "description": {
                    "type": "STRING",
                    "description": "Descripción clara de la herramienta y su uso"
                },
                "parameters_schema": {
                    "type": "STRING",
                    "description": "JSON de propiedades de parámetros. Ej: '{\"param\": {\"type\": \"STRING\"}}'"
                },
                "python_code": {
                    "type": "STRING",
                    "description": "Código Python con la función def <tool_name>(parameters: dict, player=None) -> str:"
                },
                "test_parameters": {
                    "type": "OBJECT",
                    "description": "Parámetros mock de prueba para evaluar la ejecución de la función en el sandbox"
                },
                "reference_file": {
                    "type": "STRING",
                    "description": "Para plan_code: nombre de archivo .py existente a usar como referencia de estilo"
                }
            },
            "required": ["action", "tool_name"]
        }
    },
    {
        "name": "self_awareness",
        "description": "ERIS self-awareness. Actions: full_map, capabilities, reflect",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "full_map — mapa completo de TODOS los archivos de ERIS | "
                        "file_tree — árbol de archivos con tamaños | "
                        "recent_changes — cambios recientes en el código | "
                        "capabilities — todas las capacidades organizadas | "
                        "search_code query='...' — buscar en código fuente | "
                        "read_my_code file='...' — leer un archivo propio | "
                        "edit_my_code file='...' old='...' new='...' — editar código propio | "
                        "identity — quién es ERIS | "
                        "reflect — reflexión interna profunda | "
                        "discover — auto-descubrimiento | "
                        "log content='...' — escribir en diario | "
                        "diary — leer diario interno | "
                        "metacognition — estado meta-cognitivo | "
                        "search query='...' — buscar en diario | "
                        "status — estado completo de auto-conciencia"
                    )
                },
                "query": {"type": "STRING", "description": "Para search_code: texto a buscar en el código fuente"},
                "file": {"type": "STRING", "description": "Para read_my_code/edit_my_code: ruta del archivo"},
                "old": {"type": "STRING", "description": "Para edit_my_code: texto viejo a reemplazar"},
                "new": {"type": "STRING", "description": "Para edit_my_code: texto nuevo"},
                "content": {"type": "STRING", "description": "Para log: contenido de la entrada del diario"},
                "limit": {"type": "STRING", "description": "Para diary: número de entradas a mostrar"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "task_queue",
        "description": "Autonomous task queue with priority. Actions: add, list, stats, run_next, clear",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add, list, stats, run_next, clear"},
                "task_name": {"type": "STRING", "description": "Nombre de la tarea (para add)"},
                "task_type": {"type": "STRING", "description": "Tipo: file_op, system, analysis, custom"},
                "priority": {"type": "INTEGER", "description": "Prioridad 1-5 (5=máxima)"},
                "details": {"type": "STRING", "description": "Detalles de la tarea (para add)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "learn_session",
        "description": "Progressive learning system. Actions: status, start, achievements, mistakes, skill, pattern",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, start, achievements, mistakes, skill, pattern"},
                "skill_name": {"type": "STRING", "description": "Nombre de la habilidad (para skill)"},
                "pattern_name": {"type": "STRING", "description": "Nombre del patrón (para pattern)"},
                "increase": {"type": "INTEGER", "description": "Puntos a aumentar (para skill)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "predict_analyze",
        "description": "Predictive engine based on usage patterns. Actions: predict, record, stats, routine, feedback",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "predict, record, stats, routine, feedback"},
                "action_name": {"type": "STRING", "description": "Nombre de la acción a registrar (para record)"},
                "correct": {"type": "STRING", "description": "true/false (para feedback)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "web_jobs",
        "description": "Web job reception panel. Actions: start, status, next, complete, fail",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, status, next, complete, fail"},
                "port": {"type": "INTEGER", "description": "Puerto del servidor (default: 5555)"},
                "job_id": {"type": "STRING", "description": "ID del trabajo (para complete/fail)"},
                "error": {"type": "STRING", "description": "Mensaje de error (para fail)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "super_search",
        "description": "File search. Actions: find_file, find_content, find_app, find_recent",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "find_file, find_content, find_app, find_recent, find_by_type, find_by_date"},
                "name": {"type": "STRING", "description": "Nombre o texto a buscar"},
                "extension": {"type": "STRING", "description": "Extension de archivo (ej: .py, .txt, .pdf)"},
                "path": {"type": "STRING", "description": "Directorio donde buscar (default: todo el sistema)"},
                "max_results": {"type": "INTEGER", "description": "Maximo de resultados (default: 20)"},
                "date_from": {"type": "STRING", "description": "Fecha inicio (YYYY-MM-DD)"},
                "date_to": {"type": "STRING", "description": "Fecha fin (YYYY-MM-DD)"},
                "min_size": {"type": "STRING", "description": "Tamano minimo (ej: 1MB, 500KB)"},
                "max_size": {"type": "STRING", "description": "Tamano maximo"}
            },
            "required": ["action", "name"]
        }
    },
    {
        "name": "sandbox_run",
        "description": "Isolated code execution sandbox. Actions: run_python, run_cmd, history, clear, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run_python, run_cmd, history, clear"},
                "code": {"type": "STRING", "description": "Código Python a ejecutar (para run_python)"},
                "command": {"type": "STRING", "description": "Comando del sistema (para run_cmd)"},
                "timeout": {"type": "INTEGER", "description": "Timeout en segundos (default: 10 para Python, 15 para comandos)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "obsidian_note",
        "description": "Obsidian vault. Actions: write, read, search, daily, link",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "write, read, search, daily, link, backlinks, graph, tags"},
                "title": {"type": "STRING", "description": "Titulo de la nota (para write/read/delete/rename/backlinks/append/update_fm/open)"},
                "new_title": {"type": "STRING", "description": "Nuevo titulo (para rename)"},
                "content": {"type": "STRING", "description": "Contenido Markdown de la nota (para write/daily/append)"},
                "tags": {"type": "STRING", "description": "Etiquetas separadas por coma (para write)"},
                "folder": {"type": "STRING", "description": "Carpeta dentro del vault (para write/browse)"},
                "query": {"type": "STRING", "description": "Texto a buscar (para search/search_tags)"},
                "field": {"type": "STRING", "description": "Campo de frontmatter a actualizar (para update_fm)"},
                "value": {"type": "STRING", "description": "Valor a asignar al campo (para update_fm)"},
                "source_title": {"type": "STRING", "description": "Nota fuente (para concepts)"},
                "text": {"type": "STRING", "description": "Texto para extraer conceptos (para concepts)"},
                "from_title": {"type": "STRING", "description": "Nota origen (para link)"},
                "to_title": {"type": "STRING", "description": "Nota destino (para link)"},
                "max_notes": {"type": "NUMBER", "description": "Maximo de notas en el grafo (para graph, default 200)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "db_memory",
        "description": "Database memory storage. Actions: save, recall, recent, delete",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "save | recall | recent | delete"},
                "key":    {"type": "STRING", "description": "Clave para save/recall/delete"},
                "value":  {"type": "STRING", "description": "Valor a guardar"},
                "query":  {"type": "STRING", "description": "Texto a buscar (para recall)"},
                "category": {"type": "STRING", "description": "identity | preference | fact | context | general"},
                "importance": {"type": "NUMBER", "description": "0 a 1"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "db_knowledge",
        "description": "Knowledge base for facts. Actions: add, search, topic",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add | search | topic"},
                "topic":  {"type": "STRING", "description": "Tema"},
                "fact":   {"type": "STRING", "description": "Hecho a guardar"},
                "query":  {"type": "STRING", "description": "Texto a buscar"},
                "source": {"type": "STRING", "description": "Fuente (default 'eris')"},
                "confidence": {"type": "NUMBER", "description": "0 a 1"},
                "tags":   {"type": "STRING", "description": "Tags separados por coma"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "db_tasks",
        "description": "Task list manager. Actions: add, list, done, delete",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add | list | done | delete"},
                "title": {"type": "STRING", "description": "Titulo"},
                "description": {"type": "STRING", "description": "Descripcion"},
                "priority": {"type": "STRING", "description": "low | medium | high | critical"},
                "task_id": {"type": "INTEGER", "description": "ID de tarea"},
                "status": {"type": "STRING", "description": "pending | in_progress | done"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "skill_manage",
        "description": "ERIS skill manager. Actions: list, view, create, edit, patch, delete, sync",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list | view | create | edit | patch | delete | sync"},
                "name": {"type": "STRING", "description": "Nombre de la skill"},
                "content": {"type": "STRING", "description": "Contenido SKILL.md (para create/edit)"},
                "category": {"type": "STRING", "description": "Categoria"},
                "old_string": {"type": "STRING", "description": "Texto a reemplazar (patch)"},
                "new_string": {"type": "STRING", "description": "Reemplazo (patch)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "superpowers_activate",
        "description": "Activates Superpowers methodology skills. Actions: activate by skill name",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Nombre del skill (ej: 'test-driven-development')"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "plugin_manage",
        "description": "Plugin manager. Actions: list, reload, run",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list | reload | run"},
                "plugin_name": {"type": "STRING", "description": "Nombre del plugin (para run)"},
                "plugin_action": {"type": "STRING", "description": "Accion del plugin (para run)"},
                "params": {"type": "STRING", "description": "Parametros JSON (para run)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "app_installer",
        "description": "Install/uninstall apps via winget. Actions: install, uninstall, list, run",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "install | uninstall | list | run"},
                "app_name": {"type": "STRING", "description": "Nombre de la app"},
                "app_path": {"type": "STRING", "description": "Ruta del ejecutable"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "full_training",
        "description": "Runs complete ERIS training. Actions: test all tools and save knowledge",
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "save_everywhere",
        "description": "Saves info to ALL systems (SQLite + Obsidian). Actions: save to DB and vault",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {"type": "STRING", "description": "Tema o clave"},
                "content": {"type": "STRING", "description": "Contenido detallado"},
                "category": {"type": "STRING", "description": "Categoria: identity, preference, fact, research, general"},
                "importance": {"type": "NUMBER", "description": "0 a 1"},
                "tags": {"type": "STRING", "description": "Tags separados por coma"}
            },
            "required": ["topic", "content"]
        }
    },
    {
        "name": "episodic_log",
        "description": "Logs events to episodic memory. Actions: record event",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "event": {"type": "STRING", "description": "Descripcion"},
                "category": {"type": "STRING", "description": "Categoria"},
                "context": {"type": "STRING", "description": "Contexto"},
                "importance": {"type": "NUMBER", "description": "0 a 1"}
            },
            "required": ["event"]
        }
    },
    {
        "name": "conversation_search",
        "description": "Searches conversation history. Actions: search, recent",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search | recent"},
                "query": {"type": "STRING", "description": "Texto a buscar en conversaciones pasadas"},
                "limit": {"type": "INTEGER", "description": "Max resultados (default 10)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "emotional_state",
        "description": "Shows/adjusts ERIS emotional state. Actions: status, tone, adjust",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | tone | adjust"},
                "dimension": {"type": "STRING", "description": "Dimension (happiness, energy, etc) - para adjust"},
                "delta": {"type": "NUMBER", "description": "Cuanto ajustar (-1 a 1) - para adjust"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "ask_opencode",
        "description": "Asks opencode for help when ERIS is stuck. Actions: ask question",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question": {"type": "STRING", "description": "La pregunta o problema"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "game_companion",
        "description": "Game companion. Actions: analyze, spot, help, loot, danger",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "analyze | spot | help | loot | danger | map | guide"},
                "game": {"type": "STRING", "description": "Nombre del juego (para guide)"},
                "target": {"type": "STRING", "description": "Que buscar (para spot)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "window_manager",
        "description": "Multi-monitor window manager. Actions: list, focus, move_to_monitor, snap, organize",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list | list_monitors | focus | move_to_monitor | minimize | close | maximize | snap | organize"},
                "name": {"type": "STRING", "description": "Nombre de la ventana"},
                "monitor": {"type": "INTEGER", "description": "Monitor destino (1, 2...)"},
                "position": {"type": "STRING", "description": "center | left | right | top | bottom"},
                "width": {"type": "NUMBER", "description": "Ancho en % de la pantalla"},
                "height": {"type": "NUMBER", "description": "Alto en % de la pantalla"},
                "side": {"type": "STRING", "description": "left | right (para snap)"},
                "preset": {"type": "STRING", "description": "Layout: auto | side_by_side | three_columns | quad | cascade | focus | save | restore"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_monitor",
        "description": "File change monitor. Actions: recent, snapshot, changes, search",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "recent | snapshot | changes | search"},
                "folder": {"type": "STRING", "description": "Carpeta a monitorear (default: Documents)"},
                "query": {"type": "STRING", "description": "Buscar archivo por nombre (para search)"},
                "limit": {"type": "INTEGER", "description": "Max resultados"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "task_manager",
        "description": "Task manager for processes. Actions: list, search, kill, count, details",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list | search | kill | count | details"},
                "process": {"type": "STRING", "description": "Nombre del proceso"},
                "pid": {"type": "INTEGER", "description": "ID del proceso"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "system_reader",
        "description": "Deep PC state reader. Actions: status, top_processes, disks, network, sensors, deep",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | top_processes | disks | network | sensors | deep"},
                "detail": {"type": "STRING", "description": "normal (default)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "webfetch",
        "description": "Fetches a specific URL and returns content. Actions: fetch URL as text/json",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url":     {"type": "STRING", "description": "URL completa a descargar"},
                "format":  {"type": "STRING", "description": "text (default) | json"},
                "timeout": {"type": "INTEGER", "description": "Timeout en segundos (default 15, max 30)"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "research",
        "description": "Autonomous research agent. Actions: auto, topic, status, suggest",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "auto (default) | topic | status | suggest"},
                "query":  {"type": "STRING", "description": "Tema a investigar (si action=topic)"}
            }
        }
    },
    {
        "name": "ask_user",
        "description": "Asks user a direct question with options. Actions: prompt with optional choices",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question":   {"type": "STRING", "description": "La pregunta clara y directa"},
                "options":    {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Lista de opciones (max 6)"},
                "allow_custom": {"type": "BOOLEAN", "description": "Permitir respuesta libre (default false)"},
                "default":    {"type": "STRING", "description": "Valor por defecto si no responde"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "subagent_task",
        "description": "Launches autonomous subagent via OpenRouter. Actions: task with wait/background mode",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task":    {"type": "STRING", "description": "Descripcion de la tarea. Si solo pides task_id, dejalo vacio"},
                "mode":    {"type": "STRING", "description": "general | research | analyze | code | write (default: general)"},
                "model":   {"type": "STRING", "description": "Modelo (default: google/gemini-2.5-flash)"},
                "wait":    {"type": "BOOLEAN", "description": "Esperar resultado (default true)"},
                "task_id": {"type": "STRING", "description": "[OPCIONAL] task_id previo para recuperar resultado"}
            },
            "required": []
        }
    },
    {
        "name": "self_heal",
        "description": "Code scanner. Actions: scan_all, scan_file, auto_fix, rollback",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan_all | scan_file | deep_scan | health_report | auto_fix | auto_fix_all | rollback | history"},
                "file":   {"type": "STRING", "description": "File path for scan, fix operations"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "english_teacher",
        "description": "English teacher A1-C2. Actions: curriculum, lesson, exercise, progress, assess, mistakes, advance",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "curriculum | lesson | exercise | progress | assess | mistakes | advance | save_lesson"},
                "level": {"type": "STRING", "description": "Nivel: A1, A2, B1, B2, C1, C2 (default: tu nivel actual)"},
                "topic": {"type": "STRING", "description": "Tema: grammar | vocabulary | conversation | all (default: all, para lesson)"},
                "count": {"type": "NUMBER", "description": "Cantidad de ejercicios (default 3, para exercise)"},
                "skill": {"type": "STRING", "description": "Habilidad a evaluar: grammar | vocabulary | pronunciation | all (para assess)"},
                "language": {"type": "STRING", "description": "Idioma nativo: spanish | general (para mistakes)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "cybersecurity",
        "description": "Cybersecurity knowledge base and labs. Actions: topics, learn, search, lab, progress, tools, quiz",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "topics | learn | search | lab | progress | tools | quiz | save_to_obsidian"},
                "topic": {"type": "STRING", "description": "Topic: networking, programming, databases, hacking, crypto, tools"},
                "subtopic": {"type": "STRING", "description": "Subtema específico dentro del tema"},
                "query": {"type": "STRING", "description": "Texto a buscar en la base de conocimiento"},
                "count": {"type": "NUMBER", "description": "Cantidad de preguntas para quiz (default 5)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "credential_recovery",
        "description": "Recovers saved local credentials. Actions: scan, browsers, wifi, windows_cred, git, all",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan | browsers | wifi | wifi_detail | windows_cred | git | all"},
                "ssid": {"type": "STRING", "description": "Nombre de red WiFi (para wifi_detail)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "osint_agent",
        "description": "OSINT intelligence agent. Actions: email, username, domain, ip, web, breach, full_report, history",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "email | username | domain | ip | web | breach | full_report | history"},
                "target": {"type": "STRING", "description": "Email, username, dominio o IP a investigar"},
                "query": {"type": "STRING", "description": "Texto para búsqueda web (action=web)"},
                "count": {"type": "NUMBER", "description": "Número de resultados (para web, default 5)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "security_shield",
        "description": "Security shield. Actions: scan, threat, firewall, score, protect",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan | threat | ports | firewall | defender | startups | score | alerts | protect | password_check"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "self_protection",
        "description": "ERIS self-protection and integrity. Actions: status, scan, backup, restore, hash, threats, heal, log",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | scan | backup | restore | hash | process | threats | protect | heal | log"},
                "file":  {"type": "STRING", "description": "Archivo a restaurar o hashear (main.py, core/prompt.txt, etc.)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "video_analyzer",
        "description": "YouTube video analyzer. Actions: info, subtitles, transcribe, summarize, research, full, history",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING", "description": "info | subtitles | transcribe | summarize | research | full | history"},
                "url":       {"type": "STRING", "description": "URL del video de YouTube"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "calculator",
        "description": "Advanced calculator. Actions: calculate, convert, date, random",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":     {"type": "STRING", "description": "calculate | convert | date | random"},
                "expression": {"type": "STRING", "description": "Expresión, conversión o consulta"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "music_player",
        "description": "Local music player. Actions: play, pause, stop, next, previous, volume, list, shuffle",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | pause | stop | next | previous | volume | list | shuffle"},
                "query":  {"type": "STRING", "description": "Nombre de canción o artista"},
                "volume": {"type": "STRING", "description": "Nivel de volumen 0-100"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "fun_mode",
        "description": "Entertainment mode: jokes, trivia, fun facts. Actions: joke, fact, trivia, answer, score",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING", "description": "joke | fact | trivia | answer | score | jokes | facts"},
                "answer":   {"type": "STRING", "description": "Respuesta a la trivia"},
                "category": {"type": "STRING", "description": "Categoría específica"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "active_firewall",
        "description": "Active firewall manager. Actions: block_ip, unblock_ip, block_port, unblock_port, list, status, scan",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "block_ip | unblock_ip | block_port | unblock_port | list | status | scan | clear | log"},
                "ip":     {"type": "STRING", "description": "IP a bloquear/desbloquear"},
                "port":   {"type": "STRING", "description": "Puerto a bloquear/desbloquear"},
                "name":   {"type": "STRING", "description": "Nombre de la regla"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_encryptor",
        "description": "File encryption with XOR cipher. Actions: encrypt, decrypt, folder, list, info, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING", "description": "encrypt | decrypt | folder | list | info | status"},
                "path":     {"type": "STRING", "description": "Ruta del archivo o carpeta"},
                "password": {"type": "STRING", "description": "Contraseña para encriptar/desencriptar"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "audio_transcriber",
        "description": "Audio transcription. Actions: transcribe, transcribe_clipboard, languages, history",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "transcribe | transcribe_clipboard | languages | history"},
                "text":   {"type": "STRING", "description": "Input text or parameter"},
                "path":   {"type": "STRING", "description": "File path"},
                "query":  {"type": "STRING", "description": "Search query"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "browser_history",
        "description": "Browser history viewer. Actions: chrome, edge, bookmarks, search, stats, export",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "chrome | edge | bookmarks | search | stats | export"},
                "text":   {"type": "STRING", "description": "Input text or parameter"},
                "path":   {"type": "STRING", "description": "File path"},
                "query":  {"type": "STRING", "description": "Search query"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "telegram_bot",
        "description": "Telegram bot manager. Actions: send_message, list_chats, read_messages, start_bot, stop_bot, status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send_message | list_chats | read_messages | start_bot | stop_bot | status"},
                "text":   {"type": "STRING", "description": "Input text or parameter"},
                "path":   {"type": "STRING", "description": "File path"},
                "query":  {"type": "STRING", "description": "Search query"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "keylogger_detector",
        "description": "Keylogger detector. Actions: scan, processes, hooks, startup, protect, log",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan | processes | hooks | startup | protect | log"},
                "text":   {"type": "STRING", "description": "Input text or parameter"},
                "path":   {"type": "STRING", "description": "File path"},
                "query":  {"type": "STRING", "description": "Search query"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "usb_monitor",
        "description": "USB device monitor. Actions: list, history, alert, block, unblock, scan",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list | history | alert | block | unblock | scan"},
                "text":   {"type": "STRING", "description": "Input text or parameter"},
                "path":   {"type": "STRING", "description": "File path"},
                "query":  {"type": "STRING", "description": "Search query"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "ransomware_shield",
        "description": "Anti-ransomware shield. Actions: status, scan, monitor, stop, quarantine, log, whitelist",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | scan | monitor | stop | quarantine | log | whitelist"},
                "text":   {"type": "STRING", "description": "Input text or parameter"},
                "path":   {"type": "STRING", "description": "File path"},
                "query":  {"type": "STRING", "description": "Search query"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "darkweb_monitor",
        "description": "Dark web monitor. Actions: check, alerts, history, report, scan_email",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "check | alerts | history | report | scan_email"},
                "text":   {"type": "STRING", "description": "Input text or parameter"},
                "path":   {"type": "STRING", "description": "File path"},
                "query":  {"type": "STRING", "description": "Search query"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "disk_wiper",
        "description": "Secure disk wiper. Actions: wipe_file, wipe_folder, wipe_free, wipe_disk, info, verify",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wipe_file | wipe_folder | wipe_free | wipe_disk | info | verify"},
                "text":   {"type": "STRING", "description": "Input text or parameter"},
                "path":   {"type": "STRING", "description": "File path"},
                "query":  {"type": "STRING", "description": "Search query"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "memory_consolidation",
        "description": "Memory cleanup and consolidation. Actions: full, episodic, semantic, long_term, status, auto",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "full | episodic | semantic | long_term | status | auto"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "flow_recorder",
        "description": "Macro/flow recorder. Actions: start, stop, list, play, save, delete, add_step, edit, duplicate",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | list | play | save | delete | info | status | add_step | edit | duplicate"},
                "name": {"type": "STRING", "description": "Nombre de la macro"},
                "speed": {"type": "STRING", "description": "Velocidad de reproducción (1.0 = normal)"},
                "repeat": {"type": "STRING", "description": "Número de repeticiones"},
                "type": {"type": "STRING", "description": "Tipo de paso: click, type, hotkey, key, move, scroll, drag, wait"},
                "text": {"type": "STRING", "description": "Texto a escribir"},
                "keys": {"type": "STRING", "description": "Teclas (para hotkey)"},
                "delay": {"type": "STRING", "description": "Delay entre pasos"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "screenshot_history",
        "description": "Screenshot history manager. Actions: capture, list, search, get, delete, compare, tag, stats",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "capture | list | search | get | delete | clean | compare | open | stats | tag | folder"},
                "name": {"type": "STRING", "description": "Nombre del screenshot"},
                "query": {"type": "STRING", "description": "Búsqueda"},
                "tags": {"type": "STRING", "description": "Tags (lista)"},
                "notes": {"type": "STRING", "description": "Notas"},
                "limit": {"type": "STRING", "description": "Límite de resultados"},
                "days": {"type": "STRING", "description": "Días para limpiar"},
                "name1": {"type": "STRING", "description": "Screenshot 1 para comparar"},
                "name2": {"type": "STRING", "description": "Screenshot 2 para comparar"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "clipboard_manager",
        "description": "Clipboard. Actions: list, search, clear, copy, paste",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, search, clear, copy, paste, export"},
                "content": {"type": "STRING", "description": "Texto a copiar"},
                "query": {"type": "STRING", "description": "Búsqueda"},
                "index": {"type": "STRING", "description": "Índice en historial"},
                "limit": {"type": "STRING", "description": "Límite de resultados"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "multi_user",
        "description": "Profiles. Actions: list, create, switch, delete, export",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list, create, switch, delete, export"},
                "name": {"type": "STRING", "description": "Nombre del usuario"},
                "display_name": {"type": "STRING", "description": "Nombre para mostrar"},
                "language": {"type": "STRING", "description": "Idioma"},
                "personality": {"type": "STRING", "description": "Personalidad de ERIS"},
                "preferences": {"type": "STRING", "description": "Preferencias (JSON dict)"},
                "source": {"type": "STRING", "description": "Perfil origen (merge)"},
                "target": {"type": "STRING", "description": "Perfil destino (merge)"},
                "filepath": {"type": "STRING", "description": "Ruta para importar"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "voice_cloning_new",
        "description": "Voice cloning system. Actions: train, list, delete, synthesize, analyze, compare, status, export",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "train | list | delete | synthesize | analyze | compare | status | export | upload_sample | preview"},
                "name": {"type": "STRING", "description": "Nombre del perfil de voz"},
                "text": {"type": "STRING", "description": "Texto a sintetizar"},
                "audio_path": {"type": "STRING", "description": "Ruta del audio de muestra"},
                "samples": {"type": "STRING", "description": "Lista de rutas de audio"},
                "name1": {"type": "STRING", "description": "Voz 1 para comparar"},
                "name2": {"type": "STRING", "description": "Voz 2 para comparar"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "browser_extension",
        "description": "Browser extension WebSocket server. Actions: start, stop, tabs, navigate, get_page, search_history",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start, stop, tabs, navigate, get_page, bookmarks, execute_js"},
                "url": {"type": "STRING", "description": "URL a navegar"},
                "code": {"type": "STRING", "description": "JavaScript a ejecutar"},
                "query": {"type": "STRING", "description": "Búsqueda en historial"},
                "content": {"type": "STRING", "description": "Contenido a enviar"},
                "port": {"type": "STRING", "description": "Puerto del servidor"},
                "days": {"type": "STRING", "description": "Días de historial"},
                "tab_id": {"type": "STRING", "description": "ID de pestaña"},
                "selector": {"type": "STRING", "description": "Selector CSS para highlight"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "smart_notifications",
        "description": "Notifications. Actions: send, list, schedule, mute, priority",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send, list, schedule, mute, stats, priority"},
                "title": {"type": "STRING", "description": "Título de notificación"},
                "message": {"type": "STRING", "description": "Mensaje"},
                "priority": {"type": "STRING", "description": "Prioridad: low, normal, high"},
                "category": {"type": "STRING", "description": "Categoría"},
                "hours": {"type": "STRING", "description": "Horas para mute"},
                "days": {"type": "STRING", "description": "Días de historial"},
                "when": {"type": "STRING", "description": "Fecha/hora programada (ISO)"},
                "id": {"type": "STRING", "description": "ID de notificación"},
                "limit": {"type": "STRING", "description": "Límite de resultados"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "usage_analytics",
        "description": "Analytics. Actions: log, report, errors, export",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "log | report | top_tools | errors | timeline | summary | export | clear | session | goals | health"},
                "tool": {"type": "STRING", "description": "Nombre de tool a loguear"},
                "success": {"type": "STRING", "description": "Si fue exitoso (true/false)"},
                "duration_ms": {"type": "STRING", "description": "Duración en ms"},
                "error": {"type": "STRING", "description": "Mensaje de error"},
                "days": {"type": "STRING", "description": "Días para reporte"},
                "hours": {"type": "STRING", "description": "Horas para timeline"},
                "session_id": {"type": "STRING", "description": "ID de sesión"},
                "limit": {"type": "STRING", "description": "Límite de resultados"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "skill_marketplace",
        "description": "Skill marketplace. Actions: search, install, list, publish, update, remove, info, rate, featured",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "search | install | list | publish | update | remove | info | rate | featured | my_skills | status"},
                "name": {"type": "STRING", "description": "Nombre del skill"},
                "query": {"type": "STRING", "description": "Búsqueda"},
                "category": {"type": "STRING", "description": "Categoría"},
                "description": {"type": "STRING", "description": "Descripción (publish)"},
                "version": {"type": "STRING", "description": "Versión"},
                "author": {"type": "STRING", "description": "Autor"},
                "tags": {"type": "STRING", "description": "Tags (lista)"},
                "actions": {"type": "STRING", "description": "Acciones del skill"},
                "code": {"type": "STRING", "description": "Código del skill"},
                "rating": {"type": "STRING", "description": "Rating (0-5)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "api_server",
        "description": "ERIS REST API server. Actions: start, stop, status, create_key, revoke_key, list_keys, config, docs",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | status | create_key | revoke_key | list_keys | config | docs | log | stats | test"},
                "host": {"type": "STRING", "description": "Host (default: 127.0.0.1)"},
                "port": {"type": "STRING", "description": "Puerto (default: 8080)"},
                "name": {"type": "STRING", "description": "Nombre de API key"},
                "permissions": {"type": "STRING", "description": "Permisos (lista)"},
                "limit": {"type": "STRING", "description": "Límite de logs"},
                "endpoint": {"type": "STRING", "description": "Endpoint a testear"},
                "rate_limit": {"type": "STRING", "description": "Rate limit por minuto"},
                "cors_origins": {"type": "STRING", "description": "CORS origins"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "federated_learning",
        "description": "Federated learning. Actions: train, predict, status, evaluate",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "train, predict, patterns, status, export, evaluate"},
                "data": {"type": "STRING", "description": "Datos de entrenamiento (lista)"},
                "input": {"type": "STRING", "description": "Input para predicción"},
                "category": {"type": "STRING", "description": "Categoría"},
                "epochs": {"type": "STRING", "description": "Épocas de entrenamiento"},
                "limit": {"type": "STRING", "description": "Límite de patrones"},
                "filepath": {"type": "STRING", "description": "Ruta de modelo a importar"},
                "patterns": {"type": "STRING", "description": "Patrones para merge"},
                "test_data": {"type": "STRING", "description": "Datos de test (lista {input, expected})"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "data_encryption",
        "description": "AES-256 data encryption. Actions: encrypt, decrypt, encrypt_file, hash_data, verify, generate_key",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "encrypt, decrypt, secure_delete, hash_data, status"},
                "text": {"type": "STRING", "description": "Texto a cifrar/descifrar"},
                "name": {"type": "STRING", "description": "Nombre del dato cifrado"},
                "filepath": {"type": "STRING", "description": "Ruta de archivo a cifrar"},
                "key": {"type": "STRING", "description": "Clave de cifrado"},
                "algorithm": {"type": "STRING", "description": "Algoritmo: sha256, sha512, md5, sha1"},
                "output": {"type": "STRING", "description": "Ruta de salida"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "auto_backup",
        "description": "Backup. Actions: backup, status, history, config, start",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "backup | status | history | config | list | start | stop | add_item | remove_item"},
                "name": {"type": "STRING", "description": "Item name for add/remove"},
                "path": {"type": "STRING", "description": "File/dir path for add_item"},
                "set": {"type": "STRING", "description": "Config key to set"},
                "value": {"type": "STRING", "description": "Config value"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "voice_enhanced",
        "description": "Voice control. Actions: status, profiles, set_profile, set_wake_word",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, profiles, set_profile, create_profile, delete_profile, set_wake_word, set_speed, set_pitch"},
                "name": {"type": "STRING", "description": "Profile name"},
                "word": {"type": "STRING", "description": "Wake word"},
                "speed": {"type": "STRING", "description": "Speech speed (0.5-3.0)"},
                "pitch": {"type": "STRING", "description": "Speech pitch (0.5-2.0)"},
                "language": {"type": "STRING", "description": "Language code (es, en, pt, fr, de, it)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "data_viz",
        "description": "Charts. Actions: bar, line, pie, scatter, histogram, table",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | bar | line | pie | scatter | histogram | table | system_report | usage_report | list_charts"},
                "title": {"type": "STRING", "description": "Chart title"},
                "labels": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Labels for chart"},
                "values": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Values for chart"},
                "x": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "X values for scatter"},
                "y": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "Y values for scatter"},
                "ylabel": {"type": "STRING", "description": "Y axis label"},
                "xlabel": {"type": "STRING", "description": "X axis label"},
                "bins": {"type": "STRING", "description": "Number of bins for histogram"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "i18n",
        "description": "i18n. Actions: status, set_language, get_string, languages",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | set_language | get_string | translate_batch | languages | add_string | auto_detect | help"},
                "language": {"type": "STRING", "description": "Language code (es, en, pt, fr, de, it, ja, ko, zh, ar)"},
                "key": {"type": "STRING", "description": "String key to translate"},
                "value": {"type": "STRING", "description": "String value to add"},
                "keys": {"type": "STRING", "description": "Comma-separated keys"},
                "text": {"type": "STRING", "description": "Text to detect language"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_review",
        "description": "Automated code review. Actions: review, security, style, history, stats, quick",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "review | security | style | history | stats | quick"},
                "path": {"type": "STRING", "description": "File or directory path"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_analyzer",
        "description": "Static code analysis. Actions: full_scan, quick_scan, ruff, radon, mypy, bandit, fix, info",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "full_scan, quick_scan, ruff, radon, mypy, jscpd, bandit, pylint, pip_audit, fix, install_tools, info"
                },
                "path": {
                    "type": "STRING",
                    "description": "Path to analyze (default: entire project)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "web_scraper",
        "description": "Web scraper. Actions: fetch, extract, links, metadata",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | fetch | extract | links | images | text | metadata | search | batch | history | js_render"},
                "url": {"type": "STRING", "description": "URL to scrape"},
                "selector": {"type": "STRING", "description": "CSS selector for extract"},
                "query": {"type": "STRING", "description": "Search query"},
                "urls": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "URLs for batch"},
                "max_chars": {"type": "STRING", "description": "Max characters for text"},
                "timeout": {"type": "STRING", "description": "Request timeout"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "docker_deploy",
        "description": "Docker deployment manager. Actions: status, init, build, run, stop, restart, logs, compose_up, shell",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status, init, build, run, stop, logs, shell"},
                "cmd": {"type": "STRING", "description": "Command for exec"},
                "lines": {"type": "STRING", "description": "Number of log lines"},
                "detach": {"type": "STRING", "description": "Run in background (true/false)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "ci_cd",
        "description": "CI/CD. Actions: test, lint, typecheck, all, git_status",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "test, lint, typecheck, all, git_status, clean"},
                "file": {"type": "STRING", "description": "Test file name"},
                "target": {"type": "STRING", "description": "Lint target"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "connectivity",
        "description": "Internet connectivity monitor. Actions: status, set_offline, set_online, check, config",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | set_offline | set_online | check | config"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "page_summarizer",
        "description": "Summarizer. Actions: summarize_url, summarize_video, summarize_text, fetch_page",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "summarize_url, summarize_video, summarize_text, fetch_page, history"},
                "url": {"type": "STRING", "description": "URL to fetch/summarize (page or video)"},
                "video_id": {"type": "STRING", "description": "YouTube video ID"},
                "text": {"type": "STRING", "description": "Text to summarize or list of URLs (newline separated)"},
                "query": {"type": "STRING", "description": "Search query for search_and_summarize"},
                "max_chars": {"type": "NUMBER", "description": "Max characters in summary (default 2000)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "self_healing_loop",
        "description": "Self-healing orchestrator. Actions: detect, fix_file, test, validate, scan_all, status, rollback, restart",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "detect | fix_file | test | validate | scan_all | status | rollback | restart"},
                "file":   {"type": "STRING", "description": "Target file (e.g. actions/self_heal.py)"},
                "code":   {"type": "STRING", "description": "Candidate fix code for fix_file/validate"}
            },
            "required": ["action"]
        }
    },
]

def load_custom_tools(BASE_DIR):
    """Load custom tools from custom_tools.json and append to TOOL_DECLARATIONS."""
    try:
        _custom_tools_path = BASE_DIR / "actions" / "custom_tools.json"
        if _custom_tools_path.exists():
            _custom_tools = json.loads(_custom_tools_path.read_text(encoding="utf-8"))
            if isinstance(_custom_tools, list):
                for _t in _custom_tools:
                    if _t.get("name") not in [td["name"] for td in TOOL_DECLARATIONS]:
                        TOOL_DECLARATIONS.append(_t)
    except Exception:
        pass
