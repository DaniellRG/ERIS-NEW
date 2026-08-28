# ERIS Móvil (Termux) — Guía técnica completa

Versión: v1 | Creado: 12/08/2026 | Asistente: Nyx (opencode)

ERIS móvil corre **todo en el celular** (Termux) y responde por Telegram,
así se puede usar desde cualquier lugar con internet. No depende de la PC.

---

## 1. Herramientas usadas

### En la PC
| Herramienta | Para qué |
|---|---|
| PowerShell | ver/matar/reiniciar procesos de ERIS, descomprimir, lanzar programas |
| Python (venv) | probar la API de Gemini para diagnosticar errores |
| adb (incluido en Scrcpy) | comunicarse con el celular por cable USB |
| scrcpy.exe | espejar y controlar la pantalla del celular desde la PC |

### En el celular (Android)
- **Termux**: terminal Linux en el celu (Python + curl + nano). Instalar desde F-Droid, NUNCA desde Play Store.
- **Termux:API**: puente para acceder a funciones del celular (batería, notificaciones, WiFi, micrófono).
- **Telegram Bot API**: la "tubería" para hablar desde cualquier lugar.
- **Gemini API** (REST): el cerebro (mismo modelo y clave que la ERIS de la PC).

---

## 2. Archivos del proyecto

```
D:\Eris_Source\mobile\
├── eris_mobile.py          <- el bot (se corre en el celular)
├── eris_mobile.config.json <- plantilla de config (token + chat_id)
└── README.md               <- esta guía
```

En el celular:
```
~/eris_mobile.json      <- config (telegram_token, gemini_key, chat_id, model)
~/eris_memory.json      <- memoria persistente (hechos + últimos mensajes)
```

---

## 3. Funciones clave de eris_mobile.py

- **`tg()`** — llama a Telegram por HTTP (`getUpdates`, `sendMessage`).
  Usa **long-polling con `offset`** para recibir mensajes sin servidor propio.
- **`_gemini_call()`** — llama a Gemini por REST (`generateContent`), devuelve
  código HTTP + cuerpo de respuesta. Así se pueden diagnosticar errores.
- **`gemini()`** — arma el prompt: `systemInstruction` (personalidad) +
  historial + los "datos que me pidió recordar".
- **`dispatch()`** — el enrutador: si el mensaje empieza con `/` ejecuta el
  comando; si no, chatea con Gemini.
- **`run()`** — ejecuta comandos de Android vía `subprocess`:
  `termux-battery-status`, `am start` (abrir apps), `pm list packages`
  (verificar que la app existe).
- **Memoria** — guarda en `~/eris_memory.json` los hechos (`/recuerda`) y los
  últimos mensajes, y los inyecta en cada respuesta.
- **Bucle principal** — `getUpdates` con timeout de 50s; responde solo al
  `chat_id` dueño (en `eris_mobile.json`).

---

## 4. Comandos del bot

```
/bateria            -> estado de la bateria
/estado             -> bateria + red + memoria
/apps               -> lista de apps que puedo abrir
/abrir <app>        -> abre una app
/notifs             -> ultimas notificaciones
/recuerda <texto>   -> guarda un dato en la memoria
/memoria            -> muestra lo que recuerda
/olvida             -> borra los hechos guardados
/test               -> diagnostica la conexion con Gemini
/ayuda              -> este mensaje
cualquier texto     -> chatear con ERIS (Gemini)
```

---

## 5. Cómo se conectó (procedimiento)

1. Buscar el token y chat id en `config/api_keys.json` y `data/telegram_state.json` de la PC.
2. Escribir `eris_mobile.py` con SOLO librerías estándar de Python (cero pip).
3. Levantar un servidor HTTP local en la PC: `python -m http.server 8000 --directory D:\Eris_Source\mobile`.
4. En Termux: `curl -O http://<IP_PC>:8000/eris_mobile.py` y bajar también la config.
5. Crear `~/eris_mobile.json` con `nano` y pegar la `gemini_key` real.
6. Correr `python eris_mobile.py`.

### Error 503 diagnosticado
- El celular daba `HTTP Error 503` al pensar, pero la PC funcionaba con el mismo
  modelo y clave. Se probó la llamada desde la PC (OK) → el problema era del
  celular (clave mal pegada o red).
- Para evitar pegar comandos largos (se corrompen en el celular), se agregó el
  comando `/test` que hace el diagnóstico SOLO y responde por Telegram.

### Scrcpy (controlar el celular desde la PC)
- Descomprimir `scrcpy-win64-vX.Y.Z.zip` en `D:\Scrcpy`.
- Activar en el celular: Opciones de desarrollador → Depuración USB.
- Conectar por cable USB → autorizar el aviso → `adb devices` debe mostrar el equipo como `device`.
- Ejecutar `scrcpy.exe`.

---

## 7. Control INVERTIDO: ERIS (PC) manejando el celular
La ERIS de la PC tiene la herramienta **`phone_control`** (actions/phone_control.py)
para controlar el celular desde la PC vía adb/scrcpy, SIN root:
- `status` — ¿hay celular conectado? modelo + resolución
- `mirror` — abre la pantalla del celu en la PC (scrcpy)
- `open_app` — abrir CUALQUIER app instalada (resuelve por nombre parcial; no
  solo las conocidas). Params: `app="youtube"` o el nombre exacto de la app.
- `apps` — lista de apps conocidas
- `open_url` — abrir una web en el celu. Params: `url="https://..."`
- `search` — buscar en Google. Params: `query="..."`
- `tap` / `swipe` / `scroll` — tocar, deslizar y hacer scroll
- `tap_text` — toca el elemento de la pantalla que contiene ese texto.
  **Clave para navegar apps sin calcular coordenadas.**
- `text` — escribir texto (ideal tras `tap_text` en un campo)
- `ui` — lista los elementos de la pantalla con sus coordenadas
- `screenshot` — captura de pantalla
- `battery` / `home` / `back` / `recent` / `unlock`

Flujo para navegar una app: `open_app` → `ui` (leer la pantalla) → `tap_text`
(tocar botones por su texto) → `text` (escribir en campos) → `scroll` →
`screenshot` para confirmar. Si `tap_text` no encuentra el texto, listar `ui`
y usar `tap` con las coordenadas que devuelve.

Requiere: adb + scrcpy en `D:\Scrcpy\scrcpy-win64-v3.3.4`, celular conectado por
USB con depuración autorizada.

## 8. Limitaciones actuales (sin root)

- **Este bot de Termux no puede tocar la pantalla** (tocar/deslizar apps sin
  root). Para eso está el **APK standalone de ERIS Android**
  (`D:\Eris_Source\android_eris\`, ver su README): la misma ERIS corriendo en el
  celular con Accessibility Service → toca, desliza, escribe, abre apps y lee la
  pantalla y las notificaciones. La ERIS de la PC también puede controlar el
  celular vía adb (sección 7).
- Solo lee **texto** por ahora. Los audios/notas de voz son v2.
- **No comparte la memoria/conocimiento de la ERIS de la PC** (su RAG y
  recuerdos). Tiene su propia memoria local. Un sync de memoria es una mejora
  pendiente.
- El bot es el mismo `@SoulEris_bot`: no pueden correr a la vez la ERIS de la
  PC y la del celular (conflicto de polling 409). Solución futura: un bot
  separado para el celular.

---

## 9. Pendientes / mejoras futuras
- [x] APK con Accessibility Service para control total de pantalla (ERIS Android v1).
- [ ] Notas de voz (grabar micrófono → transcribir → responder con audio).
- [ ] Sync de memoria con la ERIS de la PC (fase 2 del APK: compartir hechos/recuerdos).
- [ ] Bot de Telegram separado para el celular.

---

## 10. APK standalone de ERIS para Android (v2)

A partir de 12/08/2026 existe una **app APK standalone** instalada en el
Motorola edge 40 neo del dueño: la MISMA ERIS corriendo en el teléfono (mismo
cerebro Gemini, misma personalidad, memoria persistente) con control total de
la pantalla sin root ni USB gracias al Accessibility Service.

- Guía completa + build: `D:\Eris_Source\android_eris\README.md`
- Probada en vivo: chatea, abrió YouTube por lenguaje natural, leyó la pantalla
  y recordó hechos.
- **v2 (burbuja flotante + voz + sync de memoria)**:
  - Burbuja flotante sobre cualquier app: ERIS **lee y controla la app de atrás**
    (probado: leyó Chrome y abrió YouTube desde el panel sin cerrar nada).
  - Voz: respuestas habladas en español (TTS) y dictado por micrófono (STT).
  - Sync de memoria APK↔PC con `D:\Eris_Source\sync_memoria.py` (`pull`/`push`),
    archivo compartido en `/sdcard/Android/data/com.eris.android/files/eris_memory.json`.
- Activar en el celu: Configuración → Accesibilidad → ERIS + botón "Burbuja" en la app.
