# Escalada — sistema

Nivel: 4/8

- Diagnosticar y reiniciar VM lab (VBoxManage), validar servicios, y portabilizar codigo Windows/Linux
- Capturar el exploit vsftpd a nivel de red (tshark/dumpcap en vboxnet0, newgrp wireshark) y ver el backdoor completo
- Explotar el segundo vector (usermap_script CVE-2007-2447) y capturarlo en vivo a nivel de red: dumpcap en vboxnet0 puerto 445, payload en Session Setup AndX NTLMSSP_AUTH smb.uname, LOGON_FAILURE tras ejecutar