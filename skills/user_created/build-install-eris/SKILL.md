---
name: build-install-eris
description: Pipeline completo de build + instalación + verificación del APK de ERIS Android (sin Gradle). Usar cuando Daniel pida compilar, actualizar o reinstalar la app del celular, o después de editar código Java/recursos de android_eris.
version: 1.0.0
category: development
tags: [android, apk, build, adb, instalacion, verificacion]
---
# Build + Instalación + Verificación del APK de ERIS Android

## When to Use
Compilar el APK de ERIS móvil, instalarlo en el celular o verificar que la app instalada corresponde al código actual. Pipeline REAL verificado: build.ps1 (7 pasos, sin Gradle) + adb install + dumpsys.

## COMANDOS CLAVE (copia exacta, sin inventar)
- Compilar: `powershell -ExecutionPolicy Bypass -File D:\Eris_Source\android_eris\build.ps1`
- APK final SIEMPRE en: `D:\Eris_Source\android_eris\eris_android.apk` (la carpeta build\ solo tiene intermedios; NUNCA instalar desde ahí)
- Verificar dispositivo: `D:\Eris_Source\android_build\sdk\platform-tools\adb.exe devices`
- Instalar: `D:\Eris_Source\android_build\sdk\platform-tools\adb.exe install -r D:\Eris_Source\android_eris\eris_android.apk`
- Verificar versión: `D:\Eris_Source\android_build\sdk\platform-tools\adb.exe shell dumpsys package com.eris.android | findstr versionName`
- Lanzar app: `D:\Eris_Source\android_build\sdk\platform-tools\adb.exe shell am start -n com.eris.android/.MainActivity`
- ADB también en PATH como `adb` (D:\Eris_Source\android_build\sdk\platform-tools)

## Rutas y Toolchain (verificados)
- Proyecto: `D:\Eris_Source\android_eris`
- Script de build: `D:\Eris_Source\android_eris\build.ps1`
- ADB: `D:\Eris_Source\android_build\sdk\platform-tools\adb.exe`
- SDK build-tools 34.0.0 + platform android-34 + JDK 17 (los usa build.ps1 internamente)
- Keystore: `D:\Eris_Source\android_build\keys\eris.keystore` (alias eris, pass: eris2026) — generado automáticamente si no existe
- Config de la app en el APK: `android_eris\assets\eris_config.json` (clave Gemini, voz, etc.)
- Paquete instalado: `com.eris.android`

## Procedure

### 1. Pre-flight (verificar antes de empezar)
- Celular conectado: `adb devices` → el serial debe aparecer como `device` (no `unauthorized` ni vacío). Serial típico: `ZY22JMR6HB`.
- Si no aparece: revisar cable USB, `adb kill-server` + `adb start-server`, autorizar el diálogo en el celular.
- Confirmar que el código a compilar está completo: `android_eris\java\*.java` y `android_eris\res\*`.

### 2. Compilar el APK
- Ejecutar: `powershell -ExecutionPolicy Bypass -File D:\Eris_Source\android_eris\build.ps1`
- El script corre 7 pasos: aapt2 compile → aapt2 link → javac → d8 (dex) → agregar classes.dex → zipalign → apksigner.
- RUTA DEL APK FINAL (IMPORTANTE, no confundir): el APK firmado se genera SIEMPRE en
  `D:\Eris_Source\android_eris\eris_android.apk`. La carpeta `android_eris\build\` solo contiene
  archivos intermedios (unsigned.apk, aligned.apk, classes, dex, res) — NUNCA se instala desde ahí.
- ÉXITO: último mensaje `OK! APK generado: D:\Eris_Source\android_eris\eris_android.apk (0.08 MB)`.
- Si un paso falla, el script tira `throw` y corta: leer QUÉ paso falló (el número [x/7] en pantalla) y resolver ese paso. Ver Pitfalls.

### 3. Instalar en el celular
- `adb install -r D:\Eris_Source\android_eris\eris_android.apk`
- ÉXITO: mensaje `Success`.
- Si da `INSTALL_FAILED_UPDATE_INCOMPATIBLE` u otro error, ver Pitfalls.

### 4. Verificación (obligatoria — nunca dar por terminado sin esto)
- `adb shell dumpsys package com.eris.android | findstr versionName` → debe decir `versionName=1.0`.
- Lanzar la app: `adb shell am start -n com.eris.android/.MainActivity` (ajustar activity si falla: `adb shell monkey -p com.eris.android -c android.intent.category.LAUNCHER 1`).
- Revisar logs de arranque: `adb logcat -d -s AndroidRuntime:E` (errores de crash) y `adb logcat -d | findstr /i eris`.
- Si la app abre y no crashea, la tarea está completa.

### 5. Regresión de voz/config (si se tocó TTS o config)
- El APK lleva `eris_config.json` embebido. Si se cambió la voz o clave, verificar que el JSON en `assets` es el correcto ANTES de compilar (aapt2 link lo incluye).
- Recordar: el TTS de voz usa la API de Gemini (cuota gratuita 10/día/modelo → 429 posible). No confundir un 429 con un bug del APK.

## Pitfalls
- javac puede avisar `deprecated API` — es un WARNING, no falla. Ignorar.
- Si `adb install` falla por "not debuggable": la app no se puede inspeccionar con run-as; verificar por dumpsys/logcat, no por archivos internos.
- `run-as` y `cat /data/data/com.eris.android/...` NO funcionan en esta app (no debuggable). No perder tiempo ahí.
- Nunca instalar sin compilar antes: el APK viejo queda en el celular y Daniel creerá que el cambio no funcionó.
- Guardar un backup del APK funcionando antes de experimentos: copiar `eris_android.apk` a `backups\eris_android_<fecha>.apk`.
- El mensaje `Success` de adb es la única señal de instalación correcta; no asumir.
