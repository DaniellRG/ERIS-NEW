# Tabla de Entrenamiento Kali Linux — ERIS

## Reglas de Entrenamiento

1. ERIS ejecuta CADA tarea en la VM Kali
2. ERIS repite cada tarea MILES de veces hasta dominarla
3. ERIS guarda cada aprendizaje en memoria + Obsidian
4. ERIS es LIBRE de experimentar, romper cosas, probar
5. ERIS notifica cuando domina un nivel
6. El entrenador (Kilo) verifica con un test
7. Si pasa el test → siguiente nivel
8. Si falla → repetir hasta dominar
9. ERIS NO se distrae: 100% enfocada en el entrenamiento

## Nivel 1: Fundamentos del Sistema (Básico)

| # | Tarea | Comando | Objetivo | Repeticiones | Estado |
|---|-------|---------|----------|--------------|--------|
| 1.1 | Navegación | `pwd && ls -la` | Saber dónde estás | 100 | ⬜ |
| 1.2 | Info del sistema | `uname -a && cat /etc/os-release && whoami && id` | Identificar SO, kernel, usuario | 100 | ⬜ |
| 1.3 | Red | `ip addr show && ip route` | Configuración de red | 100 | ⬜ |
| 1.4 | Procesos | `ps aux | head -20` | Ver procesos activos | 100 | ⬜ |
| 1.5 | Espacio en disco | `df -h && free -h` | Uso de disco y memoria | 100 | ⬜ |
| 1.6 | Crear directorio | `mkdir -p ~/eris_lab/{scripts,logs,results,tools}` | Estructura de trabajo | 50 | ⬜ |
| 1.7 | Crear archivo | `echo "test" > ~/eris_lab/test.txt && cat ~/eris_lab/test.txt` | Crear y leer archivos | 50 | ⬜ |
| 1.8 | Permisos | `chmod +x ~/eris_lab/test.txt && ls -l ~/eris_lab/test.txt` | Cambiar permisos | 50 | ⬜ |

**Test Nivel 1**: ERIS debe ejecutar los 8 comandos sin errores y explicar qué hace cada uno.

## Nivel 2: Manejo de Archivos y Directorios (Básico-Intermedio)

| # | Tarea | Comando | Objetivo | Repeticiones | Estado |
|---|-------|---------|----------|--------------|--------|
| 2.1 | Buscar archivos | `find /etc -name "*.conf" | head -20` | Buscar archivos de config | 100 | ⬜ |
| 2.2 | Buscar texto | `grep -r "Port" /etc/ssh/ 2>/dev/null` | Buscar texto en archivos | 100 | ⬜ |
| 2.3 | Copiar/Mover | `cp ~/eris_lab/test.txt ~/eris_lab/test2.txt && mv ~/eris_lab/test2.txt ~/eris_lab/test3.txt` | Copiar y mover archivos | 50 | ⬜ |
| 2.4 | Eliminar | `rm ~/eris_lab/test3.txt && ls ~/eris_lab/` | Eliminar archivos | 50 | ⬜ |
| 2.5 | Ver contenido | `head -20 /etc/passwd && tail -5 /etc/passwd` | Ver inicio/fin de archivos | 50 | ⬜ |
| 2.6 | Contar líneas | `wc -l /etc/passwd && wc -w /etc/passwd` | Contar líneas y palabras | 50 | ⬜ |
| 2.7 | Crear script bash | `echo '#!/bin/bash' > ~/eris_lab/scripts/hello.sh && echo 'echo "Hola"' >> ~/eris_lab/scripts/hello.sh && chmod +x ~/eris_lab/scripts/hello.sh && ~/eris_lab/scripts/hello.sh` | Crear y ejecutar script | 50 | ⬜ |
| 2.8 | Redirección | `ls / > ~/eris_lab/ls_output.txt && cat ~/eris_lab/ls_output.txt` | Redirigir salida a archivo | 50 | ⬜ |

**Test Nivel 2**: ERIS debe crear un script bash que liste archivos, cuente líneas y guarde el resultado en un archivo.

## Nivel 3: Herramientas de Kali Linux (Intermedio)

| # | Tarea | Comando | Objetivo | Repeticiones | Estado |
|---|-------|---------|----------|--------------|--------|
| 3.1 | Inventario tools | `ls /usr/bin/ | grep -E "nmap|hydra|sqlmap|nikto|gobuster|john|hashcat|aircrack|tcpdump|tshark" | sort` | Listar herramientas de seguridad | 100 | ⬜ |
| 3.2 | Nmap versión | `nmap --version` | Ver versión de nmap | 50 | ⬜ |
| 3.3 | Nmap localhost | `nmap -sV 127.0.0.1 -p 22,80,443 2>/dev/null` | Escanear puertos locales | 100 | ⬜ |
| 3.4 | Nmap ping sweep | `nmap -sn 127.0.0.1 2>/dev/null` | Descubrir hosts | 50 | ⬜ |
| 3.5 | Verificar sudo | `sudo -l 2>/dev/null | head -20` | Ver privilegios sudo | 50 | ⬜ |
| 3.6 | Servicios activos | `ss -tlnp | head -20` | Ver puertos en escucha | 100 | ⬜ |
| 3.7 | Procesos de red | `netstat -tlnp 2>/dev/null | head -20 || ss -tlnp | head -20` | Ver conexiones de red | 50 | ⬜ |
| 3.8 | Info de interfaz | `ip link show && ethtool eth0 2>/dev/null | head -10` | Info de interfaces de red | 50 | ⬜ |

**Test Nivel 3**: ERIS debe escanear localhost con nmap, identificar puertos abiertos y explicar qué servicio corre en cada uno.

## Nivel 4: Administración del Sistema (Intermedio-Avanzado)

| # | Tarea | Comando | Objetivo | Repeticiones | Estado |
|---|-------|---------|----------|--------------|--------|
| 4.1 | Servicios | `systemctl list-units --type=service --state=running | head -20` | Ver servicios activos | 100 | ⬜ |
| 4.2 | Logs | `journalctl -n 20 --no-pager 2>/dev/null` | Leer logs del sistema | 50 | ⬜ |
| 4.3 | Usuarios | `cat /etc/passwd | grep -E "bash|zsh" | head` | Ver usuarios con shell | 50 | ⬜ |
| 4.4 | Cron | `crontab -l 2>/dev/null; ls /etc/cron.d/ 2>/dev/null` | Ver tareas programadas | 50 | ⬜ |
| 4.5 | Binarios SUID | `find / -perm -4000 -type f 2>/dev/null | head -20` | Encontrar binarios con privilegios | 50 | ⬜ |
| 4.6 | Paquetes instalados | `dpkg -l | wc -l` | Contar paquetes instalados | 50 | ⬜ |
| 4.7 | Actualizaciones | `apt list --upgradable 2>/dev/null | head -10` | Ver actualizaciones pendientes | 50 | ⬜ |
| 4.8 | Config SSH | `cat /etc/ssh/sshd_config 2>/dev/null | grep -v "^#" | grep -v "^$" | head -20` | Revisar config SSH | 50 | ⬜ |

**Test Nivel 4**: ERIS debe listar servicios activos, leer logs recientes y encontrar binarios SUID.

## Nivel 5: Seguridad y Hardening (Avanzado)

| # | Tarea | Comando | Objetivo | Repeticiones | Estado |
|---|-------|---------|----------|--------------|--------|
| 5.1 | Firewall | `sudo ufw status 2>/dev/null || sudo iptables -L -n 2>/dev/null | head -20` | Ver firewall | 50 | ⬜ |
| 5.2 | Procesos sospechosos | `ps aux | grep -v "\[" | grep -v "root" | head -20` | Buscar procesos no-root | 50 | ⬜ |
| 5.3 | Conexiones establecidas | `ss -tnp state established 2>/dev/null | head -20` | Ver conexiones activas | 50 | ⬜ |
| 5.4 | Archivos modificados recientemente | `find / -mtime -1 -type f 2>/dev/null | head -20` | Archivos modificados en 24h | 50 | ⬜ |
| 5.5 | Variables de entorno | `env | sort | head -30` | Ver variables de entorno | 50 | ⬜ |
| 5.6 | Historial de comandos | `history | tail -20` | Ver historial de comandos | 50 | ⬜ |
| 5.7 | Verificar integridad | `md5sum /etc/passwd /etc/shadow 2>/dev/null` | Verificar integridad de archivos | 50 | ⬜ |
| 5.8 | Puertos abiertos | `nmap -sT -p- 127.0.0.1 2>/dev/null | grep open` | Escaneo completo de puertos | 50 | ⬜ |

**Test Nivel 5**: ERIS debe verificar firewall, buscar conexiones establecidas y listar puertos abiertos.

## Nivel 6: Scripting y Automatización (Avanzado)

| # | Tarea | Comando | Objetivo | Repeticiones | Estado |
|---|-------|---------|----------|--------------|--------|
| 6.1 | Script de inventario | Crear script que liste OS, IP, disco, memoria | Automatizar recopilación | 30 | ⬜ |
| 6.2 | Script de monitoreo | Crear script que monitoree CPU/mem/disco | Automatizar monitoreo | 30 | ⬜ |
| 6.3 | Script de backup | Crear script que haga backup de /home/eris | Automatizar backups | 30 | ⬜ |
| 6.4 | Script de alerta | Crear script que alerte si disco > 90% | Automatizar alertas | 30 | ⬜ |
| 6.5 | Loop for | `for i in $(seq 1 5); do echo "Iteracion $i"; done` | Bucles en bash | 50 | ⬜ |
| 6.6 | Condicionales | `if [ -f /etc/passwd ]; then echo "existe"; else echo "no existe"; fi` | Condicionales en bash | 50 | ⬜ |
| 6.7 | Funciones | Crear función bash que salude | Funciones en bash | 50 | ⬜ |
| 6.8 | Variables | `VAR="Eris"; echo "Hola $VAR"; echo "Longitud: ${#VAR}"` | Variables en bash | 50 | ⬜ |

**Test Nivel 6**: ERIS debe crear un script que monitoree el sistema y guarde resultados en un archivo de log.

## Nivel 7: Pentesting Básico (Experto)

| # | Tarea | Comando | Objetivo | Repeticiones | Estado |
|---|-------|---------|----------|--------------|--------|
| 7.1 | Escaneo de red | `nmap -sn 10.0.2.0/24 2>/dev/null` | Descubrir hosts en la red | 50 | ⬜ |
| 7.2 | Escaneo de puertos | `nmap -sV -sC 127.0.0.1 2>/dev/null | head -40` | Escanear servicios | 50 | ⬜ |
| 7.3 | Análisis vuln | `nmap --script vuln 127.0.0.1 2>/dev/null | head -40` | Buscar vulnerabilidades | 30 | ⬜ |
| 7.4 | Hydra brute force | `hydra -l eris -P /usr/share/wordlists/rockyou.txt 127.0.0.1 ssh 2>/dev/null | tail -5` | Fuerza bruta (solo lab) | 10 | ⬜ |
| 7.5 | Captura de tráfico | `sudo tcpdump -i eth0 -c 10 2>/dev/null | head -20` | Capturar paquetes | 30 | ⬜ |
| 7.6 | Análisis de hash | `echo "password" | md5sum && echo "password" | sha256sum` | Hash de passwords | 50 | ⬜ |
| 7.7 | John the Ripper | `echo "eris:$(openssl passwd -1 password)" > /tmp/test_passwd && john /tmp/test_passwd 2>/dev/null | tail -5` | Crackear hash | 20 | ⬜ |
| 7.8 | Reporte de pentest | Crear reporte markdown con hallazgos | Documentar hallazgos | 20 | ⬜ |

**Test Nivel 7**: ERIS debe ejecutar un escaneo completo de localhost, identificar vulnerabilidades y crear un reporte.

## Estado General

| Nivel | Nombre | Estado | Test |
|-------|--------|--------|------|
| 1 | Fundamentos | ⬜ Pendiente | ⬜ |
| 2 | Archivos | ⬜ Pendiente | ⬜ |
| 3 | Herramientas Kali | ⬜ Pendiente | ⬜ |
| 4 | Administración | ⬜ Pendiente | ⬜ |
| 5 | Seguridad | ⬜ Pendiente | ⬜ |
| 6 | Scripting | ⬜ Pendiente | ⬜ |
| 7 | Pentesting | ⬜ Pendiente | ⬜ |

## Progreso: 0/7 niveles completados

---

## Instrucciones para ERIS

Eris, tienes un laboratorio de Kali Linux en VirtualBox. Las credenciales son:
- Usuario: eris
- Password: eris3267
- VM: Kalilinux

Puedes:
1. Ejecutar comandos con: guestcontrol via VBoxManage
2. Escribir en terminal visible con: xdotool (DISPLAY=:0)
3. Abrir Firefox para investigar
4. Abrir Nautilus para ver archivos
5. Crear, editar, eliminar archivos
6. Experimentar libremente

Reglas:
- Repite cada tarea MILES de veces hasta dominarla
- Guarda CADA aprendizaje en memoria y Obsidian
- Notifica cuando domines un nivel
- Eres LIBRE de experimentar, romper cosas, probar
- NO te distraigas: 100% enfocada en el entrenamiento
- Cuando domines un nivel, dile al entrenador (Kilo) que estás lista para el test

## Comandos útiles para el entrenador (Kilo)

```python
# Enviar tarea a ERIS
import urllib.request, json
msg = "Eris, [instrucción]"
data = json.dumps({'text': msg}).encode()
urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765/chat', data=data, headers={'Content-Type': 'application/json'}))

# Ejecutar comando en VM directamente
from core.vbox_controller import exec_in_vm
r = exec_in_vm('Kalilinux', 'eris', 'eris3267', 'COMANDO', timeout=30)
print(r.get('stdout', ''))

# Escribir en terminal visible
from core.vbox_controller import exec_in_vm
exec_in_vm('Kalilinux', 'eris', 'eris3267', 'export DISPLAY=:0 && xdotool type --delay 50 "COMANDO" && xdotool key Return', timeout=15)
```
