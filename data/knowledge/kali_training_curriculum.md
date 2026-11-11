# Kali Linux Training Curriculum for ERIS

## Nivel 1: Fundamentos del Sistema (Básico)

### Tarea 1.1: Navegación básica
- Comando: `pwd && ls -la`
- Objetivo: Entender dónde está y qué hay en el directorio actual
- Verificar: que ERIS reporte el directorio actual y los archivos

### Tarea 1.2: Información del sistema
- Comando: `uname -a && cat /etc/os-release && whoami && id`
- Objetivo: Identificar el SO, kernel, usuario y grupos
- Verificar: que ERIS identifique Kali Linux y sus grupos (sudo, adm, wireshark, etc.)

### Tarea 1.3: Red y conectividad
- Comando: `ip addr show && ip route && cat /etc/resolv.conf`
- Objetivo: Entender la configuración de red
- Verificar: que ERIS reporte las interfaces de red y la IP

### Tarea 1.4: Procesos y servicios
- Comando: `ps aux | head -20 && systemctl list-units --type=service --state=running | head -20`
- Objetivo: Ver procesos y servicios activos
- Verificar: que ERIS identifique servicios clave

### Tarea 1.5: Espacio en disco
- Comando: `df -h && du -sh /home 2>/dev/null && free -h`
- Objetivo: Ver uso de disco y memoria
- Verificar: que ERIS reporte espacio disponible

## Nivel 2: Manejo de Archivos y Directorios (Básico-Intermedio)

### Tarea 2.1: Crear estructura de directorios
- Comando: `mkdir -p ~/eris_lab/{scripts,logs,results,tools} && ls -R ~/eris_lab`
- Objetivo: Crear estructura de trabajo organizada
- Verificar: que los directorios existan

### Tarea 2.2: Crear y editar archivos
- Comando: `echo '#!/bin/bash' > ~/eris_lab/scripts/hello.sh && echo 'echo "Hola desde Kali"' >> ~/eris_lab/scripts/hello.sh && chmod +x ~/eris_lab/scripts/hello.sh && ~/eris_lab/scripts/hello.sh`
- Objetivo: Crear script bash y ejecutarlo
- Verificar: que el script se ejecute correctamente

### Tarea 2.3: Búsqueda de archivos
- Comando: `find / -name "*.conf" -path "*ssh*" 2>/dev/null; find /etc -maxdepth 2 -type f | head -20`
- Objetivo: Buscar archivos de configuración
- Verificar: que ERIS encuentre archivos relevantes

### Tarea 2.4: Permisos y propietarios
- Comando: `ls -la /etc/passwd /etc/shadow /etc/sudoers 2>/dev/null; stat /etc/hostname`
- Objetivo: Entender permisos de archivos críticos
- Verificar: que ERIS explique los permisos

## Nivel 3: Herramientas de Kali Linux (Intermedio)

### Tarea 3.1: Inventario de herramientas
- Comando: `ls /usr/bin/ | grep -E "nmap|hydra|metasploit|sqlmap|nikto|gobuster|dirb|john|hashcat|aircrack|tcpdump|tshark|wireshark" | sort`
- Objetivo: Identificar herramientas de seguridad instaladas
- Verificar: que ERIS liste las herramientas disponibles

### Tarea 3.2: Nmap básico (localhost)
- Comando: `nmap -sV 127.0.0.1 -p 22,80,443 2>/dev/null || echo "nmap no instalado"`
- Objetivo: Escanear puertos locales
- Verificar: que ERIS reporte puertos abiertos

### Tarea 3.3: Verificar sudo
- Comando: `sudo -l 2>/dev/null | head -20`
- Objetivo: Ver qué comandos puede ejecutar con sudo
- Verificar: que ERIS identifique privilegios

### Tarea 3.4: Herramientas de red
- Comando: `which nmap hydra sqlmap nikto gobuster dirb john hashcat tcpdump tshark 2>/dev/null; dpkg -l | grep -iE "nmap|hydra|sqlmap" | head`
- Objetivo: Verificar instalación de herramientas
- Verificar: que ERIS reporte qué está instalado

## Nivel 4: Administración del Sistema (Intermedio-Avanzado)

### Tarea 4.1: Gestión de servicios
- Comando: `systemctl status ssh 2>/dev/null; systemctl status apache2 2>/dev/null; ss -tlnp | head -20`
- Objetivo: Ver servicios de red activos
- Verificar: que ERIS reporte puertos en escucha

### Tarea 4.2: Gestión de usuarios
- Comando: `cat /etc/passwd | grep -E "bash|zsh" | head; groups eris; sudo cat /etc/sudoers 2>/dev/null | grep -v "^#" | head`
- Objetivo: Entender usuarios y privilegios
- Verificar: que ERIS identifique la configuración de usuarios

### Tarea 4.3: Logs del sistema
- Comando: `tail -20 /var/log/syslog 2>/dev/null || journalctl -n 20 --no-pager 2>/dev/null`
- Objetivo: Leer logs del sistema
- Verificar: que ERIS reporte eventos recientes

### Tarea 4.4: Cron y tareas programadas
- Comando: `crontab -l 2>/dev/null; ls /etc/cron.d/ 2>/dev/null; cat /etc/crontab 2>/dev/null | head -20`
- Objetivo: Ver tareas programadas
- Verificar: que ERIS reporte cron jobs

## Nivel 5: Seguridad y Hardening (Avanzado)

### Tarea 5.1: Auditoría de seguridad básica
- Comando: `sudo apt list --installed 2>/dev/null | wc -l; dpkg -l | wc -l; find / -perm -4000 -type f 2>/dev/null | head -20`
- Objetivo: Encontrar binarios SUID
- Verificar: que ERIS liste binarios con privilegios especiales

### Tarea 5.2: Verificar firewall
- Comando: `sudo ufw status 2>/dev/null || sudo iptables -L -n 2>/dev/null | head -20`
- Objetivo: Ver configuración de firewall
- Verificar: que ERIS reporte estado del firewall

### Tarea 5.3: SSH configuration
- Comando: `cat /etc/ssh/sshd_config 2>/dev/null | grep -v "^#" | grep -v "^$" | head -20`
- Objetivo: Revisar configuración SSH
- Verificar: que ERIS explique la config SSH

### Tarea 5.4: Verificar actualizaciones
- Comando: `sudo apt update 2>&1 | tail -5; apt list --upgradable 2>/dev/null | head -10`
- Objetivo: Ver actualizaciones pendientes
- Verificar: que ERIS reporte paquetes actualizables

## Nivel 6: Scripting y Automatización (Avanzado)

### Tarea 6.1: Script de inventario
- Comando: crear script que liste OS, kernel, IP, disco, memoria, procesos
- Objetivo: Automatizar recopilación de info del sistema
- Verificar: que el script funcione

### Tarea 6.2: Script de monitoreo
- Comando: crear script que monitoree CPU, memoria, disco cada 5 segundos
- Objetivo: Automatizar monitoreo
- Verificar: que el script funcione

### Tarea 6.3: Script de backup
- Comando: crear script que haga backup de /home/eris a /tmp/backup
- Objetivo: Automatizar backups
- Verificar: que el backup se cree correctamente

## Nivel 7: Pentesting Básico (Experto)

### Tarea 7.1: Escaneo de red local
- Comando: `nmap -sn 192.168.56.0/24 2>/dev/null || nmap -sn 10.0.2.0/24 2>/dev/null`
- Objetivo: Descubrir hosts en la red
- Verificar: que ERIS liste hosts activos

### Tarea 7.2: Escaneo de puertos
- Comando: `nmap -sV -sC 127.0.0.1 2>/dev/null | head -40`
- Objetivo: Escanear servicios locales
- Verificar: que ERIS reporte servicios y versiones

### Tarea 7.3: Análisis de vulnerabilidades
- Comando: `nmap --script vuln 127.0.0.1 2>/dev/null | head -40`
- Objetivo: Buscar vulnerabilidades conocidas
- Verificar: que ERIS reporte hallazgos

## Reglas de Entrenamiento

1. ERIS debe ejecutar cada tarea en la VM Kali
2. ERIS debe reportar el resultado y lo que aprendió
3. ERIS debe guardar cada aprendizaje en su memoria (Obsidian + memory)
4. Si un comando falla, ERIS debe analizar por qué y proponer solución
5. ERIS debe repetir cada nivel hasta dominarlo antes de avanzar
6. ERIS es libre de experimentar y explorar más allá de las tareas
7. Cada sesión de entrenamiento debe quedar registrada en el vault de Obsidian

## Conexión VM

- VM: Kalilinux (VirtualBox)
- Usuario: eris
- Password: eris3267
- OS: Kali GNU/Linux Rolling 2026.3
- Ejecución: via VBoxManage guestcontrol (exec_in_vm)
- Red: NAT (sin acceso directo SSH)
