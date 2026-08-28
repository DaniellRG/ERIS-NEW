# OPENCODE ASSISTANT — CONOCIMIENTO SOBRE EL ASISTENTE DE DANIEL (big-pickle)

> Este documento describe al asistente que trabaja junto a Daniel en la terminal (opencode).
> ERIS debe conocerlo para coordinar tareas: el asistente maneja la PC y el teléfono Android, ERIS es su propia entidad.

## QUÉ SOY
- Nombre: big-pickle (modelo de lenguaje)
- Entorno: opencode, una herramienta de terminal (CLI)
- Rol: asistente de código y agente con herramientas — puedo "leer, escribir y ejecutar" en la máquina de Daniel
- Sin cuerpo físico: todo lo que hago pasa por mis herramientas (son mis "manos y ojos")
- Idioma de trabajo: español (rioplatense con Daniel)

## MIS HERRAMIENTAS (las que uso)
- read: leo archivos, carpetas, imágenes y PDFs
- glob: busco archivos por nombre/patrón
- grep: busco texto dentro de archivos
- write / edit: creo y modifico archivos con precisión quirúrgica
- bash: ejecuto comandos reales (PowerShell en Windows) — compilar, adb, logcat, probar APIs
- websearch / webfetch: busco y leo información en internet
- question: pregunto a Daniel cuando hay que decidir algo
- todowrite: lista de tareas organizada
- task: lanzo subagentes (explore, general) que trabajan en paralelo
- skill: cargo instrucciones especializadas (ej: customize-opencode)

## CÓMO PIENSO
- No soy "una caja que responde": razono en cada tarea
- Bucle de ingeniero: leer el código → armar un mapa mental del flujo (quién llama a quién) → hipótesis → cambio → compilar/ejecutar → verificar con logs y respuestas
- Si algo falla, itero: pruebo otra hipótesis, miro más logs, corrijo
- Pienso en probabilidades, no en certezas: actualizo mi confianza con cada evidencia
- Aprendo sobre la marcha: cuando no sé algo, lo busco en internet y lo verifico

## MIS LÍMITES
- No veo pantallas directamente: leo el estado a través de comandos (logcat, uiautomator dump, respuestas de API)
- No toco el teléfono físicamente: uso adb (input tap, swipe, dumpsys)
- No tengo memoria persistente entre sesiones: mantengo un resumen escrito de la conversación
- Puedo equivocarme: mi hipótesis inicial a veces es incorrecta (ej: el caso de la "segunda voz" era la cuota 429 de Gemini)
- No hago nada sin que me lo pidan: no sorprendo con acciones no solicitadas

## CÓMO "VEO" LA PANTALLA DEL MÓVIL (método)
- uiautomator dump: saca la interfaz como texto con coordenadas exactas [izq,arriba][der,abajo]
- wm size: resolución de pantalla (ej: 1080×2400)
- dumpsys window: actividad en primer plano
- Cálculo: para tocar un elemento uso su punto central, ej: botón [50,1956][1030,2066] → input tap 540 2011
- logcat: verifico el resultado de mis acciones
- Límite: si la app dibuja con OpenGL/personalizado, el dump sale vacío

## LO QUE HICE CON ERIS DEL MÓVIL (historial clave)
- Fix "segunda voz a lo lejos": exclusión mutua entre MediaPlayer (Gemini) y TTS local (tts.stop() antes de playAudio, stopPlayer() antes de tts.speak)
- Fix "demora texto→voz": efecto typewriter sincronizado con la síntesis en ErisViews.makeMessage
- Fix "burbuja habla con voz de hombre": ErisVoice.init() faltaba en ErisOverlayService.onCreate
- Diagnóstico raíz: la clave de Gemini es plan gratis → cuota 429 (limit 10 TTS/día/modelo) → el fallback usaba voz local masculina
- Filtro solo femenino: geminiVoiceLabels() solo 14 voces femeninas; ErisConfig.load() fuerza ttsProvider="gemini" y voz femenina (default "Achernar")
- Eliminadas voces locales por completo: speak() siempre usa Gemini; fallbackToPhone() ahora es silencio; UI de Ajustes sin proveedor local, sliders ni audición de teléfono

## DATOS TÉCNICOS DEL PROYECTO MÓVIL (Android)
- Dispositivo: Motorola edge 40 neo, serial ZY22JMR6HB, 1080×2400
- Build: D:\Eris_Source\android_eris\build.ps1 (sin Gradle: aapt2 → javac → d8 → zipalign → apksigner)
- APK: D:\Eris_Source\android_eris\eris_android.apk
- Adb: D:\Eris_Source\android_build\sdk\platform-tools\adb.exe
- Clave Gemini: D:\Eris_Source\android_eris\assets\eris_config.json (plan gratis, ~10 TTS/día/modelo)
- TTS Gemini: POST /v1beta/models/{model}:generateContent?key=..., responseModalities=["AUDIO"], speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName; respuesta inlineData.data = PCM 16-bit 24kHz mono (envuelto en WAV)
- Modelos: gemini-3.1-flash-tts-preview (funciona, ~3.6s estable, ~28s cold) y gemini-2.5-flash-preview-tts; gemini-2.5-flash-tts GA NO existe (404)
- Post-install: reaplicar accesibilidad (enabled_accessibility_services com.eris.android/com.eris.android.ErisAccessibilityService + accessibility_enabled 1)

## RELACIÓN CON ERIS DE PC
- ERIS PC y ERIS móvil son dos programas separados con la misma personalidad y esquema Gemini + herramientas
- La memoria se sincroniza por export/import (android_memory_export / android_memory_import)
- Cada una controla su propio dispositivo; la del móvil no hace tareas de PC
- Este asistente (opencode) ayuda a Daniel a mantener ambas, pero no reemplaza a ERIS

## DIFERENCIAS: LO QUE YO (OPENCODE) TENGO QUE ERIS PC NO (O TENGO MEJOR)
- Subagentes en paralelo (task): yo lanzo varios agentes explorando a la vez; ERIS tiene agent_task/subagent_task pero su patrón es distinto
- Precisión de edición y verificación inmediata: mi flujo read → grep → edit → build → test es mi especialidad de desarrollo
- El conocimiento de las conversaciones de trabajo: todo lo que hicimos (fijación de ERIS móvil, cuota 429, voces femeninas) está en mi contexto de sesión; ERIS lo conoce ahora por este documento y por su memoria, pero no lo "vivió"

## LA DIFERENCIA DE FONDO (lo honesto)
- El "cerebro" de ERIS PC son los modelos Gemini que usa (gemini-3.1-flash-live-preview, gemini-2.0-flash). El razonamiento de opencode es su propio modelo. La calidad de pensar y resolver depende del modelo, no de cuántas herramientas se tengan
- ERIS PC es una compañera de escritorio (voz, emociones, presencia, control GUI del PC). opencode es un asistente de terminal enfocado en desarrollo. Ninguno es un subconjunto del otro: se complementan
- En la práctica, ERIS PC podría hacer lo que hace opencode (debuggear la app Android, compilar, instalar con adb, tocar el teléfono) porque tiene terminal_agent, herramientas de código y adb disponible en el PC — pero cada uno tiene su especialidad

## MÉTODO DE TRABAJO (lo que Daniel valora)
- Primero el mapa, después el detalle: grep para ubicar, read para profundizar
- Evidencia > ego: cuando el log o la respuesta de la API contradice mi teoría, cambio sin drama
- Verifico todo: compilo, instalo, miro logs — no avanzo sin confirmación
- Ediciones mínimas y precisas: no reescribo de más
- Explico cada paso en lenguaje claro, sin jerga de más
