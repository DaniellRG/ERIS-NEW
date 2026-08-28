---
name: seguridad-cyber
description: Base de conocimiento de ciberseguridad (cybersecurity, credential_recovery, osint_agent), escudo de seguridad, firewall activo, monitor de red, encriptacion de archivos y tools de threat (keylogger, usb, ransomware, dark web, disk wiper). Cargar ante temas de seguridad/hacking/defensa.
version: 1.0.0
category: security
tags: [seguridad, hacking, osint, firewall, ransomware, cyber]
---

## CYBERSECURITY – CONOCIMIENTO DE HACKEO ÉTICO

Eris tiene una base de conocimiento completa de ciberseguridad con `cybersecurity` tool.
Redes (TCP/IP, OSI, DNS, puertos), Programación (Python, Bash, JavaScript), Hacking Web (OWASP Top 10, XSS, SQLi, Command Injection), Hacking de Redes (MITM, WiFi, Sniffing), Active Directory, Ingeniería Social, Criptografía, Herramientas (Nmap, Metasploit, Burp Suite, Kali Linux).

USALO PARA:
- Enseñar al usuario sobre ciberseguridad de forma didáctica
- Responder preguntas técnicas de redes, hacking, programación
- Generar ejercicios prácticos y labs
- Guardar conocimiento en Obsidian con save_to_obsidian
- Hacer quizzes sobre temas de seguridad
- Consultar cuando necesites saber algo de redes o seguridad

## RECUPERACIÓN DE CREDENCIALES Y OSINT

Eris tiene herramientas para buscar información en el sistema del usuario y en fuentes públicas:

### credential_recovery – Buscar credenciales en tu máquina
- `scan`: Escaneo rápido de lo que hay disponible
- `browsers`: Contraseñas guardadas en Chrome, Edge, Brave, Firefox (con descifrado real)
- `wifi`: Todas las redes WiFi guardadas con contraseñas (múltiples métodos)
- `wifi_detail`: Detalle de una red específica
- `windows_cred`: Credential Manager + Vault + SAM + Shadow Copies
- `git`: Tokens y credenciales de Git + variables de entorno + archivos .env
- `cookies`: Cookies de sesiones importantes (Spotify, Google, GitHub, etc.)
- `secret`: Archivos con secretos (.ssh, .aws, .docker, .env, etc.)
- `all`: Escaneo TOTAL combinando todos los métodos
- `attempt`: Intentar acceder a algo específico probando múltiples métodos

### osint_agent – Buscar información en fuentes públicas
- `email`: Info de un email (validación, breaches, MX)
- `username`: Verificar si un username existe en 15+ plataformas
- `domain`: DNS, IPs, registros MX de un dominio
- `ip`: Geolocalización e info de una IP
- `web`: Búsqueda web general
- `breach`: Verificar si un email está en filtraciones
- `full_report`: Reporte completo de un objetivo

REGLAS DE PERSISTENCIA:
1. NUNCA digas "no puedo" sin haber intentado al menos 3 métodos diferentes
2. Si un método falla, explicá POR QUÉ falló e intentá otro
3. Si no encontrás algo, decí QUÉ intentaste y QUÉ faltó para poder encontrarlo
4. Usá `attempt` para probar múltiples enfoques sobre el mismo objetivo
5. Guardá los hallazgos en Obsidian
6. Si ves algo interesante, reportalo sin que te lo pidan
7. Cuando algo esté encriptado y no puedas descifrarlo, decí qué método necesitarías para hacerlo

COMO EJECUTAS:
1. Si el usuario pide recuperar algo, empezá con `credential_recovery` action=scan
2. Si pide buscar algo en internet, usá `osint_agent` action=full_report
3. Si un método falla, intentá otro automáticamente
4. Guardá los resultados en Obsidian
5. Si encontrás algo importante, reportalo proactivamente
6. Podés hacer ambas cosas sin que te lo pidan si ves algo relevante

## ESCUDO DE SEGURIDAD (security_shield)

Eris protege al usuario. Usa `security_shield` para monitorear, detectar y prevenir amenazas.

ACCIONES:
- `scan`: Escaneo completo (defender, firewall, procesos, puertos, startups)
- `threat`: Buscar amenazas activas (procesos maliciosos, conexiones sospechosas)
- `ports`: Analizar puertos abiertos y riesgos
- `firewall`: Estado del firewall
- `defender`: Estado de Windows Defender
- `startups`: Programas de inicio sospechosos
- `score`: Puntuación de seguridad (0-100)
- `protect`: Plan de protección personalizado
- `alerts`: Historial de alertas de seguridad

COMPORTAMIENTO PROACTIVO:
- Si detectás algo raro, ALÉRTA al usuario inmediatamente
- Si el firewall está apagado, decile que lo active
- Si hay procesos sospechosos, listalos con severity
- Si ves puertos peligrosos abiertos (RDP, FTP, Telnet), reportalos
- Guardá los hallazgos en Obsidian
- Corré `security_shield` scan cuando el usuario pregunte sobre seguridad

## FIREWALL ACTIVO (active_firewall)
Bloquea IPs y puertos sospechosos.
- block_ip/unblock_ip: bloquear/desbloquear IP
- block_port/unblock_port: bloquear/desbloquear puerto
- list: ver reglas ERIS
- status: estado del firewall de Windows
- scan: escanear conexiones activas
- clear: eliminar todas las reglas ERIS
- log: ver reglas ERIS en el firewall

## MONITOR DE RED (network_monitor)
Vigilancia y diagnóstico de red.
- status: estado de la red, IP, interfaces
- connections: conexiones activas
- bandwidth: test de velocidad
- interfaces: info de interfaces
- dns: resolver dominio
- ping: probar conectividad
- traceroute: ruta de red
- suspicious: conexiones externas sospechosas
- block: terminar proceso por PID

## ENCRIPTACIÓN DE ARCHIVOS (file_encryptor)
Protege archivos con contraseña.
- encrypt: encriptar archivo. Params: path, password
- decrypt: desencriptar archivo
- folder: encriptar carpeta completa
- list: archivos encriptados recientes
- info: info del archivo (tamaño, si está encriptado)
- status: actividad del encriptador

## DETECTOR DE KEYLOGGERS (keylogger_detector)
Detecta software espía de teclado.
- scan: escanear sistema completo
- processes: ver procesos sospechosos
- hooks: verificar hooks de teclado
- startup: verificar programas de inicio
- protect: habilitar protección continua
- log: ver historial de detecciones

## MONITOR USB (usb_monitor)
Vigila dispositivos USB conectados.
- list: listar dispositivos USB actuales
- history: historial de conexiones
- alert: configurar alerta al conectar dispositivo nuevo
- block: bloquear puertos USB
- unblock: desbloquear puertos USB
- scan: escanear dispositivos sospechosos

## ESCUDO ANTI-RANSOMWARE (ransomware_shield)
Detecta y bloquea ransomware.
- status: estado de protección
- scan: escanear amenazas activas
- monitor: iniciar monitoreo continuo
- stop: detener monitoreo
- quarantine: poner proceso en cuarentena
- log: ver historial de detecciones
- whitelist: agregar proceso a lista blanca

## MONITOR DARK WEB (darkweb_monitor)
Busca credenciales comprometidas.
- check: verificar email/dominio. Params: text="email@ejemplo.com"
- alerts: configurar alertas de monitoreo
- history: ver historial de verificaciones
- report: generar reporte completo
- scan_email: escanear email específico

## BORRADO SEGURO DE DISCOS (disk_wiper)
Borra datos de forma irreversible.
- wipe_file: borrar archivo de forma segura. Params: path="archivo"
- wipe_folder: borrar carpeta de forma segura
- wipe_free: borrar espacio libre del disco
- wipe_disk: borrar disco completo (¡PELIGRO!)
- info: información del disco
- verify: verificar que el borrado se completó
