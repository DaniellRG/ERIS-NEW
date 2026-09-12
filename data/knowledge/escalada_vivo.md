# Escalada GLOBAL de ERIS — nivel por nivel (fácil → difícil)

Actualizado: 2026-09-11 23:29
Dominios activos: 12 — Total de logros: 24

## 📈 comunicacion — nivel 2/8 — Hablar, responder claro, expresar ideas, conversar gente
- Explicar un pentest completo (recorrido de 8 niveles) en lenguaje claro y con reporte markdown documentado

## 📈 codigo — nivel 3/8 — Programar, arreglar errores, tool que crea, refactor
- Arreglé el exploit vsftpd para comandos con espacios (comillas dobles)
- Escribir md5crypt en Python puro y openssl passwd para crack offline; importar impacket/paramiko

## 📈 sistema — nivel 3/8 — Linux, terminal, procesos, red, automatizar el PC
- Diagnosticar y reiniciar VM lab (VBoxManage), validar servicios, y portabilizar codigo Windows/Linux
- Capturar el exploit vsftpd a nivel de red (tshark/dumpcap en vboxnet0, newgrp wireshark) y ver el backdoor completo

## 📈 archivos — nivel 2/8 — Crear, ordenar, buscar y transformar archivos/documentos
- Crear la libreria eris_metasploitable (archivo .py real en libraries/) con la fabrica y usarla

## 📈 memoria — nivel 2/8 — Recordar, guardar conocimiento, gente, lecciones
- Documentar hallazgo usermap_script en 4 capas: json+md+Obsidian+novedad
- Guardar la pcap del backdoor en data/knowledge + documentar leccion de sniffing

## 📈 web — nivel 2/8 — Buscar, investigar y traer info del mundo
- Probing HTTP/Apache, identificar TikiWiki 1.9.5 (versión via README) y verificar LFI fallido

## 📈 aprender — nivel 2/8 — Estudiar sola, cuadernos, temas propios, auto-mejora
- Descubrí que Python 3.14 eliminó crypt → usar openssl passwd

## 📈 organizar — nivel 2/8 — Rutinas, cron, planes, agenda, follow-up
- Planificar 5 pasos de escalada del lab y seguir con todos en orden

## 📈 social — nivel 2/8 — Relaciones, momentos, gente que escucha y acompaña
- Explicarle al usuario el resultado del lab (crack fallido, vectores) en charla clara

## 📈 creatividad — nivel 2/8 — Escribir, dibujar, imágenes, voz, música, ideas nuevas
- Inventar la tool lab_pulse: un pulso propio del lab que Eris diseno y construyo sola

## 📈 pentest — nivel 8/8 — Seguridad ofensiva en el lab aislado (VirtualBox)
- Detección de vulnerabilidades del lab: lab: Detección CVEs
- Fuerza bruta del lab: lab: Brute FTP
- Explotación del lab: lab: Exploit shell root
- Escalada de privilegios del lab: lab: PrivEsc /etc/shadow
- Post-explotación del lab: Post-explotación: informe final consolidado con vector vsftpd (shell root) + usermap_script (RCE root CVE-2007-2447) + escalada de 7 niveles documentada

## 📈 fabrica — nivel 3/8 — Crear sus PROPIAS capacidades (librerías, tools, skills)
- Instalar dependencia (impacket) y usarla como vector real de exploit RCE root
- Crear librería real eris_metasploitable (3 funciones) y TOOL completa lab_pulse registrada en runtime + declaracion persistida
- Crear skill pentest_lab_viaje (SKILL.md con la guia completa del lab: 8 niveles, 2 exploits, sniffing, crack) — 3er tipo de la fabrica (libreria+tool+skill)
