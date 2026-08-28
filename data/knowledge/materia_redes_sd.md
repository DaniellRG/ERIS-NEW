# Redes y Sistemas Distribuidos — Guía de estudio

## 1. Modelos de referencia
- **Modelo OSI (7 capas)**: física, enlace de datos, red, transporte, sesión, presentación, aplicación. Función de cada una y ejemplos de protocolos.
- **Modelo TCP/IP (4 capas)**: acceso a red, internet, transporte, aplicación; correspondencia con OSI.
- Ventajas de los modelos en capas: modularidad, interoperabilidad.

## 2. Capa de red e IP
- Direccionamiento IPv4: clases, máscaras de subred, **CIDR** (notación /n), subredes y cálculo de host.
- NAT (traducción de direcciones), DHCP (asignación automática).
- IPv6: formato de dirección, diferencias con IPv4.
- Enrutamiento: tablas de enrutamiento, protocolos (RIP, OSPF, BGP) intro; routers vs switches.
- ARP (resolución IP→MAC); ICMP (ping, traceroute).

## 3. Capa de transporte
- **TCP**: orientado a conexión, 3-way handshake, ACKs, control de flujo y congestión, puertos.
- **UDP**: no orientado a conexión, sin garantías, menor sobrecarga; cuándo se usa.
- Comparación TCP vs UDP; socket (dirección IP + puerto).

## 4. Protocolos de aplicación
- HTTP/HTTPS (métodos, códigos, cabeceras), DNS (jerarquía, resolución), FTP, SMTP/POP/IMAP (correo), SSH, WebSocket.
- Cómo funciona una petición web completa (DNS → TCP → HTTP → respuesta).

## 5. Redes físicas y dispositivos
- Topologías (bus, estrella, anillo, malla); cableado (par trenzado, fibra); Wi-Fi (estándares 802.11).
- Dispositivos: NIC, switch, router, access point, hub, firewall.
- LAN/MAN/WAN; VLAN.

## 6. Seguridad de red
- Firewalls (filtrado, stateful), VPN (tunelado, IPSec), cifrado en tránsito (TLS).
- Ataques comunes: sniffing, spoofing, DoS/DDoS, man-in-the-middle, phishing.
- Autenticación y autorización; PKI y certificados.

## 7. Sistemas distribuidos
- Definición: múltiples nodos que cooperan y comparten recursos; transparencia.
- **Modelos**: cliente-servidor, peer-to-peer (P2P), multi-capa.
- **Comunicación**: RPC/RMI, sockets, REST, mensajería asíncrona (cola, pub/sub).
- **Consistencia**: fuerte, eventual; teorema CAP.
- **Tolerancia a fallos**: replicación, redundancia, checkpoints, reintentos, timeouts.
- **Escalabilidad**: horizontal vs vertical; balanceo de carga (load balancing).
- Concurrencia distribuida: elección de líder, relojes lógicos (vector clocks).
- Coordinación: ZooKeeper/etcd (concepto); estado vs sin estado (stateless).

## 8. Puntos de examen frecuentes
- Calcular subredes con CIDR (número de hosts, broadcast).
- Explicar el handshake TCP de 3 pasos.
- Comparar TCP vs UDP con ejemplos.
- Recorrer una petición web: DNS, TCP, HTTP.
- Explicar el teorema CAP con un ejemplo.
- Diferenciar RPC de REST; consistencia fuerte vs eventual.

## Guía rápida
Si ERIS te pregunta sobre Redes y Sistemas Distribuidos: cubre OSI/TCP-IP, IP y
subredes (CIDR), TCP/UDP, protocolos (HTTP, DNS), seguridad de red y sistemas
distribuidos (CAP, tolerancia a fallos, RPC/REST), con ejercicios numéricos.
