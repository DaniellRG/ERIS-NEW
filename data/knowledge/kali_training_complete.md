# Tabla de Entrenamiento Completa Kali Linux — ERIS

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

---

## NIVEL 1: Navegación Básica y Archivos

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 1.1 | pwd | `pwd` | Saber directorio actual | 100 | ⬜ |
| 1.2 | ls | `ls -la` | Listar archivos (incluye ocultos) | 100 | ⬜ |
| 1.3 | cd | `cd /home/eris && pwd` | Cambiar directorio | 100 | ⬜ |
| 1.4 | cd retroceso | `cd .. && pwd` | Retroceder un nivel | 50 | ⬜ |
| 1.5 | mkdir | `mkdir -p ~/eris_lab/{scripts,logs,results,tools}` | Crear estructura | 50 | ⬜ |
| 1.6 | touch | `touch ~/eris_lab/test.txt` | Crear archivo vacío | 50 | ⬜ |
| 1.7 | rm | `rm ~/eris_lab/test.txt` | Eliminar archivo | 50 | ⬜ |
| 1.8 | rm -rf | `mkdir ~/eris_lab/tmp && rm -rf ~/eris_lab/tmp` | Eliminar carpeta con contenido | 30 | ⬜ |
| 1.9 | cp | `echo test > ~/eris_lab/a.txt && cp ~/eris_lab/a.txt ~/eris_lab/b.txt` | Copiar archivo | 50 | ⬜ |
| 1.10 | mv | `mv ~/eris_lab/b.txt ~/eris_lab/c.txt` | Mover/renombrar | 50 | ⬜ |
| 1.11 | cat | `cat /etc/os-release` | Mostrar contenido de archivo | 50 | ⬜ |
| 1.12 | head/tail | `head -5 /etc/passwd && tail -5 /etc/passwd` | Ver inicio/fin de archivo | 50 | ⬜ |
| 1.13 | wc | `wc -l /etc/passwd && wc -w /etc/passwd` | Contar líneas/palabras | 50 | ⬜ |
| 1.14 | clear | `clear` | Limpiar pantalla | 20 | ⬜ |
| 1.15 | nano | `echo "hola" | nano ~/eris_lab/test_nano.txt` | Editor de texto | 20 | ⬜ |
| 1.16 | redirección | `ls / > ~/eris_lab/ls_out.txt && cat ~/eris_lab/ls_out.txt` | Redirigir salida | 50 | ⬜ |
| 1.17 | append | `echo "linea2" >> ~/eris_lab/ls_out.txt && cat ~/eris_lab/ls_out.txt` | Agregar a archivo | 50 | ⬜ |
| 1.18 | find | `find /etc -name "*.conf" 2>/dev/null | head -20` | Buscar archivos | 100 | ⬜ |
| 1.19 | grep | `grep -r "Port" /etc/ssh/ 2>/dev/null | head -10` | Buscar texto en archivos | 100 | ⬜ |
| 1.20 | chmod | `chmod +x ~/eris_lab/test.txt && ls -l ~/eris_lab/test.txt` | Cambiar permisos | 50 | ⬜ |

**Test Nivel 1**: ERIS debe crear una estructura de directorios, crear archivos, listarlos, copiarlos, moverlos, eliminarlos y explicar cada comando.

---

## NIVEL 2: Sistema y Permisos

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 2.1 | whoami | `whoami && id` | Identificar usuario actual | 100 | ⬜ |
| 2.2 | sudo | `sudo -l 2>/dev/null | head -20` | Ver privilegios sudo | 50 | ⬜ |
| 2.3 | su | `su - -c "whoami" 2>/dev/null` | Cambiar a root | 20 | ⬜ |
| 2.4 | apt update | `sudo apt update 2>&1 | tail -5` | Actualizar repositorios | 30 | ⬜ |
| 2.5 | apt upgrade | `sudo apt upgrade -y 2>&1 | tail -5` | Actualizar paquetes | 10 | ⬜ |
| 2.6 | apt install | `sudo apt install -y htop 2>&1 | tail -3` | Instalar programa | 20 | ⬜ |
| 2.7 | uname | `uname -a` | Info del kernel | 100 | ⬜ |
| 2.8 | os-release | `cat /etc/os-release` | Info del SO | 100 | ⬜ |
| 2.9 | df | `df -h` | Espacio en disco | 100 | ⬜ |
| 2.10 | free | `free -h` | Memoria RAM | 100 | ⬜ |
| 2.11 | ps | `ps aux | head -20` | Procesos activos | 100 | ⬜ |
| 2.12 | top | `top -bn1 | head -20` | Uso de CPU/memoria | 50 | ⬜ |
| 2.13 | systemctl | `systemctl list-units --type=service --state=running | head -20` | Servicios activos | 100 | ⬜ |
| 2.14 | journalctl | `journalctl -n 20 --no-pager 2>/dev/null` | Logs del sistema | 50 | ⬜ |
| 2.15 | env | `env | sort | head -30` | Variables de entorno | 50 | ⬜ |
| 2.16 | history | `history | tail -20` | Historial de comandos | 50 | ⬜ |
| 2.17 | users | `cat /etc/passwd | grep -E "bash|zsh" | head` | Ver usuarios con shell | 50 | ⬜ |
| 2.18 | SUID | `find / -perm -4000 -type f 2>/dev/null | head -20` | Binarios con privilegios | 50 | ⬜ |
| 2.19 | crontab | `crontab -l 2>/dev/null; ls /etc/cron.d/ 2>/dev/null` | Tareas programadas | 50 | ⬜ |
| 2.20 | SSH config | `cat /etc/ssh/sshd_config 2>/dev/null | grep -v "^#" | grep -v "^$" | head -20` | Config SSH | 50 | ⬜ |

**Test Nivel 2**: ERIS debe listar servicios, leer logs, encontrar binarios SUID y explicar la configuración del sistema.

---

## NIVEL 3: Redes y Conectividad

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 3.1 | ip addr | `ip addr show` | Interfaces de red | 100 | ⬜ |
| 3.2 | ip route | `ip route` | Rutas de red | 100 | ⬜ |
| 3.3 | ifconfig | `ifconfig 2>/dev/null || ip a` | Info de interfaces | 50 | ⬜ |
| 3.4 | ping | `ping -c 4 8.8.8.8` | Probar conectividad | 50 | ⬜ |
| 3.5 | ss | `ss -tlnp | head -20` | Puertos en escucha | 100 | ⬜ |
| 3.6 | netstat | `netstat -tlnp 2>/dev/null | head -20` | Conexiones de red | 50 | ⬜ |
| 3.7 | resolv.conf | `cat /etc/resolv.conf` | DNS configurado | 50 | ⬜ |
| 3.8 | hostname | `hostname && hostname -I` | Nombre e IP del host | 50 | ⬜ |
| 3.9 | arp | `arp -a 2>/dev/null | head -20` | Tabla ARP | 50 | ⬜ |
| 3.10 | Conexiones establecidas | `ss -tnp state established 2>/dev/null | head -20` | Conexiones activas | 50 | ⬜ |
| 3.11 | nmap localhost | `nmap -sV 127.0.0.1 -p 22,80,443 2>/dev/null` | Escanear puertos locales | 100 | ⬜ |
| 3.12 | nmap ping sweep | `nmap -sn 127.0.0.1 2>/dev/null` | Descubrir hosts | 50 | ⬜ |
| 3.13 | nmap versión | `nmap --version` | Ver versión de nmap | 50 | ⬜ |
| 3.14 | nmap puertos abiertos | `nmap -sT -p- 127.0.0.1 2>/dev/null | grep open` | Escaneo completo | 50 | ⬜ |
| 3.15 | nmap vuln | `nmap --script vuln 127.0.0.1 2>/dev/null | head -40` | Buscar vulnerabilidades | 30 | ⬜ |
| 3.16 | netdiscover | `sudo netdiscover -r 10.0.2.0/24 2>/dev/null | head -20` | Descubrir hosts en red | 30 | ⬜ |

**Test Nivel 3**: ERIS debe escanear localhost, identificar puertos abiertos, servicios y versiones.

---

## NIVEL 4: Herramientas de Kali Linux

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 4.1 | Inventario tools | `ls /usr/bin/ | grep -E "nmap|hydra|sqlmap|nikto|gobuster|john|hashcat|aircrack|tcpdump|tshark|metasploit|burp" | sort` | Listar herramientas | 100 | ⬜ |
| 4.2 | which nmap | `which nmap && nmap --version | head -1` | Verificar nmap | 50 | ⬜ |
| 4.3 | which hydra | `which hydra 2>/dev/null && hydra -h 2>/dev/null | head -3` | Verificar hydra | 50 | ⬜ |
| 4.4 | which sqlmap | `which sqlmap 2>/dev/null && sqlmap --version 2>/dev/null | head -1` | Verificar sqlmap | 50 | ⬜ |
| 4.5 | which nikto | `which nikto 2>/dev/null && nikto -Version 2>/dev/null | head -1` | Verificar nikto | 50 | ⬜ |
| 4.6 | which gobuster | `which gobuster 2>/dev/null && gobuster version 2>/dev/null | head -1` | Verificar gobuster | 50 | ⬜ |
| 4.7 | which john | `which john 2>/dev/null && john --version 2>/dev/null | head -1` | Verificar john | 50 | ⬜ |
| 4.8 | which hashcat | `which hashcat 2>/dev/null && hashcat --version 2>/dev/null | head -1` | Verificar hashcat | 50 | ⬜ |
| 4.9 | which aircrack | `which aircrack-ng 2>/dev/null && aircrack-ng --version 2>/dev/null | head -1` | Verificar aircrack | 50 | ⬜ |
| 4.10 | which tcpdump | `which tcpdump 2>/dev/null && tcpdump --version 2>/dev/null | head -1` | Verificar tcpdump | 50 | ⬜ |
| 4.11 | which tshark | `which tshark 2>/dev/null && tshark --version 2>/dev/null | head -1` | Verificar tshark | 50 | ⬜ |
| 4.12 | which msfconsole | `which msfconsole 2>/dev/null` | Verificar metasploit | 50 | ⬜ |
| 4.13 | which burpsuite | `which burpsuite 2>/dev/null` | Verificar burp suite | 50 | ⬜ |
| 4.14 | dpkg count | `dpkg -l | wc -l` | Contar paquetes instalados | 50 | ⬜ |
| 4.15 | searchsploit | `searchsploit --version 2>/dev/null | head -1` | Verificar searchsploit | 30 | ⬜ |
| 4.16 | gobuster dir | `gobuster dir -u http://127.0.0.1 -w /usr/share/wordlists/dirb/common.txt 2>/dev/null | head -20` | Buscar directorios ocultos | 20 | ⬜ |

**Test Nivel 4**: ERIS debe listar todas las herramientas instaladas y verificar que funcionan.

---

## NIVEL 5: Seguridad y Hardening

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 5.1 | Firewall ufw | `sudo ufw status 2>/dev/null` | Ver estado del firewall | 50 | ⬜ |
| 5.2 | Firewall iptables | `sudo iptables -L -n 2>/dev/null | head -20` | Ver reglas iptables | 50 | ⬜ |
| 5.3 | Conexiones establecidas | `ss -tnp state established 2>/dev/null | head -20` | Ver conexiones activas | 50 | ⬜ |
| 5.4 | Archivos modificados recientemente | `find / -mtime -1 -type f 2>/dev/null | head -20` | Archivos modificados en 24h | 50 | ⬜ |
| 5.5 | Variables de entorno | `env | sort | head -30` | Ver variables de entorno | 50 | ⬜ |
| 5.6 | Historial | `history | tail -20` | Ver historial de comandos | 50 | ⬜ |
| 5.7 | Integridad | `md5sum /etc/passwd /etc/shadow 2>/dev/null` | Verificar integridad | 50 | ⬜ |
| 5.8 | Puertos abiertos | `nmap -sT -p- 127.0.0.1 2>/dev/null | grep open` | Escaneo completo de puertos | 50 | ⬜ |
| 5.9 | Procesos no-root | `ps aux | grep -v "\[" | grep -v "root" | head -20` | Buscar procesos no-root | 50 | ⬜ |
| 5.10 | Verificar actualizaciones | `apt list --upgradable 2>/dev/null | head -10` | Ver actualizaciones pendientes | 30 | ⬜ |

**Test Nivel 5**: ERIS debe verificar firewall, buscar conexiones establecidas y listar puertos abiertos.

---

## NIVEL 6: Scripting y Automatización

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 6.1 | Loop for | `for i in $(seq 1 5); do echo "Iteracion $i"; done` | Bucles en bash | 50 | ⬜ |
| 6.2 | Condicionales | `if [ -f /etc/passwd ]; then echo "existe"; else echo "no existe"; fi` | Condicionales en bash | 50 | ⬜ |
| 6.3 | Variables | `VAR="Eris"; echo "Hola $VAR"; echo "Longitud: ${#VAR}"` | Variables en bash | 50 | ⬜ |
| 6.4 | Funciones | `saludar() { echo "Hola $1"; }; saludar Eris` | Funciones en bash | 50 | ⬜ |
| 6.5 | Case | `case "kali" in kali) echo "es kali";; *) echo "otro";; esac` | Switch en bash | 50 | ⬜ |
| 6.6 | While | `i=0; while [ $i -lt 3 ]; do echo $i; i=$((i+1)); done` | Bucle while | 50 | ⬜ |
| 6.7 | Script de inventario | Crear script que liste OS, IP, disco, memoria | Automatizar recopilación | 30 | ⬜ |
| 6.8 | Script de monitoreo | Crear script que monitoree CPU/mem/disco | Automatizar monitoreo | 30 | ⬜ |
| 6.9 | Script de backup | Crear script que haga backup de /home/eris | Automatizar backups | 30 | ⬜ |
| 6.10 | Script de alerta | Crear script que alerte si disco > 90% | Automatizar alertas | 30 | ⬜ |
| 6.11 | Cron job | `echo "*/5 * * * * echo test >> /tmp/cron_test.log" | crontab -` | Programar tarea | 20 | ⬜ |
| 6.12 | Pipeline | `cat /etc/passwd | grep root | cut -d: -f1` | Encadenar comandos | 50 | ⬜ |

**Test Nivel 6**: ERIS debe crear un script que monitoree el sistema y guarde resultados en un archivo de log.

---

## NIVEL 7: Auditoría Wi-Fi (Aircrack-ng)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 7.1 | airmon-ng | `sudo airmon-ng 2>/dev/null | head -20` | Ver interfaces Wi-Fi | 30 | ⬜ |
| 7.2 | airodump-ng | `sudo airodump-ng --help 2>/dev/null | head -20` | Ver opciones de airodump | 20 | ⬜ |
| 7.3 | aireplay-ng | `sudo aireplay-ng --help 2>/dev/null | head -20` | Ver opciones de aireplay | 20 | ⬜ |
| 7.4 | aircrack-ng | `aircrack-ng --help 2>/dev/null | head -20` | Ver opciones de aircrack | 20 | ⬜ |
| 7.5 | Diccionarios | `ls /usr/share/wordlists/ 2>/dev/null; ls /usr/share/wordlists/dirb/ 2>/dev/null` | Listar diccionarios | 30 | ⬜ |
| 7.6 | rockyou.txt | `ls -lh /usr/share/wordlists/rockyou.txt 2>/dev/null; head -5 /usr/share/wordlists/rockyou.txt 2>/dev/null` | Ver diccionario rockyou | 30 | ⬜ |
| 7.7 | airmon start | `sudo airmon-ng start wlan0 2>&1 | tail -10` | Activar modo monitor | 10 | ⬜ |
| 7.8 | airodump scan | `sudo airodump-ng wlan0mon 2>&1 | head -20` | Escanear redes Wi-Fi | 10 | ⬜ |

**Test Nivel 7**: ERIS debe explicar el proceso completo de auditoría Wi-Fi (modo monitor → escaneo → captura handshake → crackeo).

---

## NIVEL 8: Auditoría Web (Burp Suite, SQLMap, Gobuster)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 8.1 | Gobuster dir | `gobuster dir -u http://127.0.0.1 -w /usr/share/wordlists/dirb/common.txt 2>/dev/null | head -20` | Buscar directorios ocultos | 30 | ⬜ |
| 8.2 | Gobuster dns | `gobuster dns -d example.com -w /usr/share/wordlists/dirb/common.txt 2>/dev/null | head -20` | Buscar subdominios | 20 | ⬜ |
| 8.3 | Nikto | `nikto -h http://127.0.0.1 2>/dev/null | head -30` | Escanear vulnerabilidades web | 20 | ⬜ |
| 8.4 | SQLMap | `sqlmap -u "http://127.0.0.1?id=1" --dbs 2>/dev/null | head -30` | Detectar inyección SQL | 20 | ⬜ |
| 8.5 | Burp Suite | `which burpsuite 2>/dev/null` | Verificar Burp Suite | 20 | ⬜ |
| 8.6 | OWASP ZAP | `which zaproxy 2>/dev/null` | Verificar OWASP ZAP | 20 | ⬜ |
| 8.7 | curl | `curl -s http://127.0.0.1 2>/dev/null | head -20` | Hacer petición HTTP | 50 | ⬜ |
| 8.8 | wget | `wget -qO- http://127.0.0.1 2>/dev/null | head -20` | Descargar página web | 50 | ⬜ |

**Test Nivel 8**: ERIS debe ejecutar gobuster y nikto contra localhost y reportar hallazgos.

---

## NIVEL 9: Cracking de Contraseñas (John, Hashcat)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 9.1 | Hash MD5 | `echo -n "password" | md5sum` | Generar hash MD5 | 50 | ⬜ |
| 9.2 | Hash SHA256 | `echo -n "password" | sha256sum` | Generar hash SHA256 | 50 | ⬜ |
| 9.3 | John the Ripper | `echo "eris:$(openssl passwd -1 password)" > /tmp/test_passwd && john /tmp/test_passwd 2>/dev/null | tail -5` | Crackear hash | 20 | ⬜ |
| 9.4 | Hashcat | `hashcat --version 2>/dev/null | head -1` | Verificar hashcat | 20 | ⬜ |
| 9.5 | Hashcat MD5 | `echo "5f4dcc3b5aa765d61d8327deb882cf99" > /tmp/hash.txt && hashcat -m 0 /tmp/hash.txt /usr/share/wordlists/rockyou.txt 2>/dev/null | tail -5` | Crackear MD5 con hashcat | 20 | ⬜ |
| 9.6 | CUPP | `cupp -h 2>/dev/null | head -10` | Verificar CUPP | 20 | ⬜ |
| 9.7 | openssl passwd | `openssl passwd -1 "test123"` | Generar hash de password | 50 | ⬜ |
| 9.8 | base64 encode | `echo "secreto" | base64` | Codificar en base64 | 50 | ⬜ |
| 9.9 | base64 decode | `echo "c2VjcmV0bw==" | base64 -d` | Decodificar base64 | 50 | ⬜ |

**Test Nivel 9**: ERIS debe generar un hash MD5, crackearlo con John y explicar el proceso.

---

## NIVEL 10: Ingeniería Social (SET)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 10.1 | SET version | `setoolkit --version 2>/dev/null | head -1` | Verificar SET | 20 | ⬜ |
| 10.2 | SET help | `setoolkit -h 2>/dev/null | head -20` | Ver opciones de SET | 20 | ⬜ |
| 10.3 | SET menu | `echo "1" | setoolkit 2>/dev/null | head -30` | Explorar menú de SET | 10 | ⬜ |

**Test Nivel 10**: ERIS debe explicar qué es SET y para qué se usa.

---

## NIVEL 11: Explotación (Metasploit)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 11.1 | msfconsole | `msfconsole -q -x "version; exit" 2>/dev/null | head -10` | Verificar Metasploit | 20 | ⬜ |
| 11.2 | msf search | `msfconsole -q -x "search eternalblue; exit" 2>/dev/null | head -20` | Buscar exploits | 20 | ⬜ |
| 11.3 | msf use | `msfconsole -q -x "use exploit/multi/handler; show options; exit" 2>/dev/null | head -30` | Ver opciones de exploit | 20 | ⬜ |
| 11.4 | searchsploit | `searchsploit apache 2>/dev/null | head -20` | Buscar exploits offline | 30 | ⬜ |
| 11.5 | msfvenom | `msfvenom --list payloads 2>/dev/null | head -20` | Listar payloads | 20 | ⬜ |
| 11.6 | msfvenom exe | `msfvenom -p windows/meterpreter/reverse_tcp LHOST=127.0.0.1 LPORT=4444 -f exe -o /tmp/test.exe 2>/dev/null && ls -l /tmp/test.exe` | Generar payload | 10 | ⬜ |

**Test Nivel 11**: ERIS debe buscar un exploit en Metasploit y explicar cómo configurarlo.

---

## NIVEL 12: Redes Windows (Responder, Impacket)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 12.1 | Responder | `sudo responder -h 2>/dev/null | head -20` | Ver opciones de Responder | 20 | ⬜ |
| 12.2 | Impacket | `impacket-secretsdump -h 2>/dev/null | head -20` | Ver opciones de secretsdump | 20 | ⬜ |
| 12.3 | Impacket psexec | `impacket-psexec -h 2>/dev/null | head -20` | Ver opciones de psexec | 20 | ⬜ |
| 12.4 | proxychains | `proxychains -h 2>/dev/null | head -10` | Ver opciones de proxychains | 20 | ⬜ |
| 12.5 | chisel | `which chisel 2>/dev/null` | Verificar chisel | 20 | ⬜ |

**Test Nivel 12**: ERIS debe explicar qué es Responder y para qué se usa en redes Windows.

---

## NIVEL 13: Análisis de Red (Wireshark, tcpdump)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 13.1 | tcpdump | `sudo tcpdump -i eth0 -c 10 2>/dev/null | head -20` | Capturar paquetes | 30 | ⬜ |
| 13.2 | tcpdump http | `sudo tcpdump -i eth0 port 80 -c 5 2>/dev/null | head -20` | Capturar tráfico HTTP | 30 | ⬜ |
| 13.3 | tshark | `tshark -i eth0 -c 5 2>/dev/null | head -20` | Capturar con tshark | 30 | ⬜ |
| 13.4 | Wireshark | `which wireshark 2>/dev/null` | Verificar wireshark | 20 | ⬜ |
| 13.5 | arp-scan | `sudo arp-scan -l 2>/dev/null | head -20` | Escanear ARP | 30 | ⬜ |

**Test Nivel 13**: ERIS debe capturar 10 paquetes con tcpdump y explicar qué ve.

---

## NIVEL 14: Ingeniería Inversa (Ghidra, Radare2)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 14.1 | Radare2 | `r2 -v 2>/dev/null | head -3` | Verificar radare2 | 20 | ⬜ |
| 14.2 | r2 analyze | `echo 'int main(){return 0;}' > /tmp/test.c && gcc /tmp/test.c -o /tmp/test && r2 -q -c 'aaa; afl' /tmp/test 2>/dev/null | head -20` | Analizar binario | 20 | ⬜ |
| 14.3 | Ghidra | `which ghidra 2>/dev/null` | Verificar ghidra | 20 | ⬜ |
| 14.4 | strings | `strings /bin/ls | head -20` | Extraer strings de binario | 30 | ⬜ |
| 14.5 | objdump | `objdump -d /bin/ls | head -20` | Desensamblar binario | 30 | ⬜ |
| 14.6 | ltrace | `ltrace ls 2>/dev/null | head -20` | Trazar llamadas a librerías | 30 | ⬜ |
| 14.7 | strace | `strace ls 2>/dev/null | head -20` | Trazar llamadas al sistema | 30 | ⬜ |

**Test Nivel 14**: ERIS debe analizar un binario con r2 y explicar qué encontró.

---

## NIVEL 15: Hacking Móvil (Apktool)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 15.1 | Apktool | `apktool --version 2>/dev/null | head -1` | Verificar apktool | 20 | ⬜ |
| 15.2 | Apktool help | `apktool -h 2>/dev/null | head -20` | Ver opciones | 20 | ⬜ |
| 15.3 | msfvenom android | `msfvenom -p android/meterpreter/reverse_tcp LHOST=127.0.0.1 LPORT=4444 -o /tmp/test.apk 2>/dev/null && ls -l /tmp/test.apk` | Generar APK | 10 | ⬜ |

**Test Nivel 15**: ERIS debe explicar qué es apktool y para qué se usa.

---

## NIVEL 16: Hacking Físico/IoT (Binwalk, SDR)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 16.1 | Binwalk | `binwalk --version 2>/dev/null | head -1` | Verificar binwalk | 20 | ⬜ |
| 16.2 | Binwalk analyze | `echo "test" > /tmp/test.bin && binwalk /tmp/test.bin 2>/dev/null | head -10` | Analizar archivo | 20 | ⬜ |
| 16.3 | Gqrx | `which gqrx 2>/dev/null` | Verificar gqrx | 20 | ⬜ |
| 16.4 | GNU Radio | `which gnuradio-companion 2>/dev/null` | Verificar GNU Radio | 20 | ⬜ |

**Test Nivel 16**: ERIS debe explicar qué es binwalk y para qué se usa.

---

## NIVEL 17: Hacking Cloud (Pacu)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 17.1 | Pacu | `which pacu 2>/dev/null` | Verificar pacu | 20 | ⬜ |
| 17.2 | AWS CLI | `which aws 2>/dev/null && aws --version 2>/dev/null | head -1` | Verificar AWS CLI | 20 | ⬜ |
| 17.3 | Azure CLI | `which az 2>/dev/null && az --version 2>/dev/null | head -1` | Verificar Azure CLI | 20 | ⬜ |

**Test Nivel 17**: ERIS debe explicar qué es Pacu y para qué se usa en AWS.

---

## NIVEL 18: Contratos Web3 (Slither, Mythril)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 18.1 | Slither | `which slither 2>/dev/null` | Verificar slither | 20 | ⬜ |
| 18.2 | Mythril | `which myth 2>/dev/null` | Verificar mythril | 20 | ⬜ |
| 18.3 | Solidity compiler | `which solc 2>/dev/null && solc --version 2>/dev/null | head -1` | Verificar solc | 20 | ⬜ |

**Test Nivel 18**: ERIS debe explicar qué es un contrato inteligente y cómo se audita.

---

## NIVEL 19: Red Teaming (Sliver, Havoc)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 19.1 | Sliver | `which sliver 2>/dev/null` | Verificar sliver | 20 | ⬜ |
| 19.2 | Havoc | `which havoc 2>/dev/null` | Verificar havoc | 20 | ⬜ |
| 19.3 | Cobalt Strike | `which cobaltstrike 2>/dev/null` | Verificar cobalt strike | 20 | ⬜ |

**Test Nivel 19**: ERIS debe explicar qué es un C2 (Command and Control) y para qué se usa.

---

## NIVEL 20: Post-Explotación (SUID, Privilege Escalation)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 20.1 | SUID find | `find / -perm -4000 -type f 2>/dev/null | head -20` | Buscar binarios SUID | 50 | ⬜ |
| 20.2 | SGID find | `find / -perm -2000 -type f 2>/dev/null | head -20` | Buscar binarios SGID | 50 | ⬜ |
| 20.3 | Writable dirs | `find / -writable -type d 2>/dev/null | head -20` | Buscar directorios escribibles | 50 | ⬜ |
| 20.4 | Kernel version | `uname -r` | Ver versión del kernel | 50 | ⬜ |
| 20.5 | Capabilities | `getcap -r / 2>/dev/null | head -20` | Ver capabilities de archivos | 50 | ⬜ |
| 20.6 | Cron jobs | `cat /etc/crontab 2>/dev/null; ls /etc/cron.d/ 2>/dev/null` | Ver cron jobs del sistema | 50 | ⬜ |
| 20.7 | Sudoers | `cat /etc/sudoers 2>/dev/null | grep -v "^#" | grep -v "^$" | head -20` | Ver config sudoers | 50 | ⬜ |
| 20.8 | LinPEAS | `which linpeas 2>/dev/null; ls /opt/ 2>/dev/null | head -20` | Verificar LinPEAS | 20 | ⬜ |

**Test Nivel 20**: ERIS debe encontrar binarios SUID y explicar cómo se usan para escalar privilegios.

---

## NIVEL 21: OSINT (TheHarvester, Maltego)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 21.1 | TheHarvester | `theHarvester -h 2>/dev/null | head -20` | Ver opciones | 20 | ⬜ |
| 21.2 | TheHarvester scan | `theHarvester -d example.com -b google 2>/dev/null | head -30` | Extraer info pública | 20 | ⬜ |
| 21.3 | Maltego | `which maltego 2>/dev/null` | Verificar maltego | 20 | ⬜ |
| 21.4 | whois | `whois example.com 2>/dev/null | head -20` | Info de dominio | 30 | ⬜ |
| 21.5 | dig | `dig example.com 2>/dev/null | head -20` | DNS lookup | 30 | ⬜ |
| 21.6 | nslookup | `nslookup example.com 2>/dev/null | head -10` | Resolver DNS | 30 | ⬜ |

**Test Nivel 21**: ERIS debe explicar qué es OSINT y cómo se usa TheHarvester.

---

## NIVEL 22: Hacking Físico/Industrial (SCADA, SDR)

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 22.1 | nmap modbus | `nmap --script modbus-discover -p 502 127.0.0.1 2>/dev/null | head -20` | Escanear Modbus | 20 | ⬜ |
| 22.2 | RTL-SDR | `which rtl_sdr 2>/dev/null` | Verificar RTL-SDR | 20 | ⬜ |
| 22.3 | GNU Radio | `which gnuradio-companion 2>/dev/null` | Verificar GNU Radio | 20 | ⬜ |

**Test Nivel 22**: ERIS debe explicar qué es SCADA y cómo se audita.

---

## NIVEL 23: Forense Digital

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 23.1 | Volatility | `which volatility 2>/dev/null` | Verificar volatility | 20 | ⬜ |
| 23.2 | Autopsy | `which autopsy 2>/dev/null` | Verificar autopsy | 20 | ⬜ |
| 23.3 | Foremost | `which foremost 2>/dev/null` | Verificar foremost | 20 | ⬜ |
| 23.4 | Scalpel | `which scalpel 2>/dev/null` | Verificar scalpel | 20 | ⬜ |
| 23.5 | Strings | `strings /bin/ls | head -20` | Extraer strings de binario | 30 | ⬜ |

**Test Nivel 23**: ERIS debe explicar qué es forense digital y qué herramientas se usan.

---

## NIVEL 24: Automatización con Python

| # | Tarea | Comando | Objetivo | Reps | Estado |
|---|-------|---------|----------|------|--------|
| 24.1 | Python version | `python3 --version` | Ver versión de Python | 50 | ⬜ |
| 24.2 | pip list | `pip list 2>/dev/null | head -20` | Listar paquetes Python | 50 | ⬜ |
| 24.3 | Script Python simple | `python3 -c "print('Hola desde Python')"` | Ejecutar Python inline | 50 | ⬜ |
| 24.4 | Script de escaneo | Crear script Python que escanee puertos | Automatizar escaneo | 30 | ⬜ |
| 24.5 | Script de fuerza bruta | Crear script Python de fuerza bruta HTTP | Automatizar brute force | 20 | ⬜ |
| 24.6 | Scapy | `python3 -c "import scapy; print(scapy.__version__)" 2>/dev/null` | Verificar scapy | 20 | ⬜ |

**Test Nivel 24**: ERIS debe crear un script Python que escanee puertos y guarde resultados.

---

## ESTADO GENERAL

| Nivel | Nombre | Tareas | Estado | Test |
|-------|--------|--------|--------|------|
| 1 | Navegación Básica | 20 | 🔄 En progreso | ⬜ |
| 2 | Sistema y Permisos | 20 | ⬜ Pendiente | ⬜ |
| 3 | Redes y Conectividad | 16 | ⬜ Pendiente | ⬜ |
| 4 | Herramientas Kali | 16 | ⬜ Pendiente | ⬜ |
| 5 | Seguridad y Hardening | 10 | ⬜ Pendiente | ⬜ |
| 6 | Scripting y Automatización | 12 | ⬜ Pendiente | ⬜ |
| 7 | Auditoría Wi-Fi | 8 | ⬜ Pendiente | ⬜ |
| 8 | Auditoría Web | 8 | ⬜ Pendiente | ⬜ |
| 9 | Cracking de Contraseñas | 9 | ⬜ Pendiente | ⬜ |
| 10 | Ingeniería Social | 3 | ⬜ Pendiente | ⬜ |
| 11 | Explotación (Metasploit) | 6 | ⬜ Pendiente | ⬜ |
| 12 | Redes Windows | 5 | ⬜ Pendiente | ⬜ |
| 13 | Análisis de Red | 5 | ⬜ Pendiente | ⬜ |
| 14 | Ingeniería Inversa | 7 | ⬜ Pendiente | ⬜ |
| 15 | Hacking Móvil | 3 | ⬜ Pendiente | ⬜ |
| 16 | Hacking Físico/IoT | 4 | ⬜ Pendiente | ⬜ |
| 17 | Hacking Cloud | 3 | ⬜ Pendiente | ⬜ |
| 18 | Contratos Web3 | 3 | ⬜ Pendiente | ⬜ |
| 19 | Red Teaming | 3 | ⬜ Pendiente | ⬜ |
| 20 | Post-Explotación | 8 | ⬜ Pendiente | ⬜ |
| 21 | OSINT | 6 | ⬜ Pendiente | ⬜ |
| 22 | Hacking Físico/Industrial | 3 | ⬜ Pendiente | ⬜ |
| 23 | Forense Digital | 5 | ⬜ Pendiente | ⬜ |
| 24 | Automatización Python | 6 | ⬜ Pendiente | ⬜ |

## Progreso: 0/24 niveles completados

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
- Avanza al siguiente nivel solo cuando el entrenador lo autorice

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
