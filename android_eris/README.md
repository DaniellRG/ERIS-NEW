# ERIS Android — APK standalone

ERIS instalada como app en el teléfono (sin PC, sin USB, sin root). Es la MISMA
ERIS: misma personalidad, mismo modelo de IA, memoria persistente, y ahora con
control total del celular mediante **Accessibility Service**.

## Qué hace

- **Chatear** con ERIS en el celu (pantalla de chat en la app).
- **Burbuja flotante**: un botón flotante sobre cualquier app para chatear con
  ERIS *sin cerrar lo que estás viendo*. ERIS lee y controla la app de atrás
  (ver + tocar + escribir desde el panel).
- **Voz**: respuestas habladas (TTS en español, botón 🔊) y dictado por micrófono
  (botón 🎤, STT).
- **Controlar el teléfono** en lenguaje natural:
  - "abrí youtube" → `android_open_app`
  - "¿qué hay en pantalla?" → `android_screen` (lee los textos de la pantalla)
  - "toca el botón buscar" → `android_tap_text`
  - "escribe hola" → `android_type`
  - "baja" / "volvé atrás" / "al inicio" → `android_scroll` / `android_back` / `android_home`
  - "leé las notificaciones" → `android_notifications`
  - "acordate que..." / "¿qué recordás?" → `android_memory_save` / `android_memory_recall`
  - "exportá la memoria" / "importá la memoria" → `android_memory_export` / `android_memory_import`
- **Memoria**: guarda hechos e historial en `eris_memory.json` (mismo formato
  que la ERIS de la PC). Se sincroniza con la PC con el script
  `D:\Eris_Source\sync_memoria.py` (ver "Sincronizar memoria con la PC").

## Herramientas que expone al cerebro

`android_status`, `android_battery`, `android_apps`, `android_open_app`,
`android_screen`, `android_tap_text`, `android_tap`, `android_swipe`,
`android_scroll`, `android_type`, `android_home`, `android_back`,
`android_recent`, `android_notifications`, `android_memory_save`,
`android_memory_recall`, `android_memory_export`, `android_memory_import`.

## Cómo se activó

1. **Instalar**: `adb install -r eris_android.apk` (el APK está firmado con el
   keystore propio `D:\Eris_Source\android_build\keys\eris.keystore`).
2. Abrir la app "ERIS". La propia app ofrece botones para ir a cada permiso:
   - **Accesibilidad**: Configuración → Accesibilidad → ERIS (permiso de
     accesibilidad). Sin esto no puede tocar la pantalla.
   - **Acceso a notificaciones**: Configuración → Apps → ERIS → Notificaciones
     → Acceso a notificaciones (para `android_notifications`).
   - **Ventanas sobre otras apps**: Configuración → Apps → ERIS → Mostrar sobre
     otras apps (para la burbuja flotante).
   - **Micrófono**: para el dictado por voz.
3. La barra de estado muestra el estado real: `Accesibilidad ACTIVA · Notif ON`.

> Nota Motorola: un `am force-stop` (o `pm clear`) de la app DESACTIVA el
> permiso de accesibilidad. Rehabilitarlo:
> `settings put secure enabled_accessibility_services com.eris.android/com.eris.android.ErisAccessibilityService`
> `settings put secure accessibility_enabled 1`

## Burbuja flotante

- Tocar la burbuja abre/cierra el panel de chat (encima de cualquier app).
- El botón 👁 del panel pregunta "¿Qué hay en pantalla?" y ERIS lee la app de atrás.
- El panel NO roba el foco: al tocar el campo de texto se activa el teclado y
  vuelve a cederlo al enviar (así ERIS sigue viendo/controlando la app de abajo).
- Botones del panel: 🔊/🔇 voz, 🎤 dictar, — ocultar, ✕ apagar la burbuja.

## Sincronizar memoria con la PC

El archivo de memoria se comparte en la ruta externa de la app:
`/sdcard/Android/data/com.eris.android/files/eris_memory.json`.

Flujo:

```powershell
# 1. en el teléfono: tocar "Exportar memoria"
#    (o decirle a ERIS: "exportá la memoria")
# 2. bajar a la PC y fusionar con la copia local:
python D:\Eris_Source\sync_memoria.py pull
# 3. (opcional) editar pc_memory.json
# 4. subir de vuelta:
python D:\Eris_Source\sync_memoria.py push
# 5. en el teléfono: tocar "Importar memoria" (o "importá la memoria")
```

El script fusiona hechos (sin duplicar) y conserva el historial de chat más largo.

## Construir el APK

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Eris_Source\android_eris\build.ps1
```

Toolchain local (sin Android Studio):
- JDK 17 Temurin → `D:\Eris_Source\android_build\jdk\`
- Android SDK (build-tools 34 + platform android-34) → `D:\Eris_Source\android_build\sdk\`
- Build manual: `aapt2` (recursos) → `javac` → `d8` (dex) → `zipalign` → `apksigner`

Config del cerebro: `assets/eris_config.json` (`gemini_key`, `model`).

## Arquitectura de archivos

```
android_eris/
├── AndroidManifest.xml
├── res/                          recursos (layout, strings, accesibilidad, icono)
├── assets/eris_config.json       clave de Gemini + modelo
├── java/com/eris/android/
│   ├── MainActivity.java         chat + estado + burbuja/voz/sync
│   ├── ErisOverlayService.java   burbuja flotante + panel (ver/controlar de atrás)
│   ├── ErisVoice.java            TTS (hablar) + STT (escuchar)
│   ├── ErisBrain.java            cerebro: Gemini REST + loop de herramientas
│   ├── ErisTools.java            ejecuta las herramientas de Android
│   ├── ErisAccessibilityService.java  gestos + lectura de pantalla
│   ├── ErisNotificationListener.java  lee notificaciones
│   ├── ErisMemory.java           memoria persistente (JSON) + sync
│   ├── ErisViews.java            helpers de UI del chat
│   ├── ErisChat.java             estado ocupado entre chat/pantalla
│   └── ErisConfig.java           lee la config
├── build.ps1                     build manual sin Gradle
└── eris_android.apk              resultado firmado
```

## Limitaciones actuales (v2)

- Voz: escucha solo al tocar el mic (el "Eris..." siempre activo es v3).
- Sin acceso a cámara/GPS/contactos (v3).
- El panel flotante lee la app de atrás solo si el servicio de accesibilidad
  está activo y hay una app de primer plano real detrás.
