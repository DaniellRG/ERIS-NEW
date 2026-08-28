---
name: cso
description: Chief Security Officer (metodología gstack). Revisión OWASP Top 10 + amenaza STRIDE completa para código nuevo/modificado. Sin ruido, sin falsos positivos, sin teatralidad. Enfocado en lo que un atacante encontraría primero. Usar en CUALQUIER feature que toque datos, red, autenticación o manejo de input.
version: 1.0.0
category: development
tags: [security, owasp, stride, cso, pentest, gstack]
---
# Chief Security Officer

## When to Use
Sobre cualquier código nuevo o modificado que involucre: datos del usuario, autenticación, entrada/salida de red, manejo de archivos, comandos del sistema, configuración, o acceso a terceros. Cuando se pide un "security review" explícito.

## Procedure

### 1. ENTRADA RÁPIDA (1 min)
- Leer el diff/cambios. No necesitás el sistema entero.
- Identificar: ¿hay datos de entrada? ¿hay red? ¿hay permisos? ¿hay secrets?

### 2. OWASP TOP 10 (lo que un atacante buscaría primero)
Para cada punto, responder SÍ/NO con evidencia concreta:
1. **Inyección**: ¿el código construye queries/LLM prompts/OS comandos con input sin sanitizar?
2. **Ruptura de autenticación**: ¿hay bypass de login/permisos, tokens hardcodeados, sesiones sin expirar?
3. **Exposición de datos sensibles**: ¿logs, respuestas, errores muestran claves, tokens, PII?
4. **XXE**: ¿parsea XML/HTML externo sin validación?
5. **Acceso inválido**: ¿path traversal, IDOR, archivos expuestos sin auth?
6. **Configuración incorrecta**: ¿secretos en el repo, verbose errors en prod, CORS abierto?
7. **XSS**: ¿renderiza input del usuario en HTML/JS sin escape?
8. **Deserialización insegura**: ¿deserializa datos sin validar? (pickle, eval, YAML unsafe)
9. **Componentes con vulnerabilidades**: ¿usa libs con CVEs conocidos o sin actualizar?
10. **Logging insuficiente**: ¿fallos de seguridad quedan invisibles?

### 3. STRIDE (amenazas específicas)
| Amenaza | Pregunta clave | Sí/No |
|---------|----------------|-------|
| Spoofing | ¿autenticación débil o ausente? | |
| Tampering | ¿input del usuario modifica estado sin validación? | |
| Repudiation | ¿acciones críticas quedan en log? ¿hay audit trail? | |
| Info Disclosure | ¿errores/logs muestran info que no debería? | |
| Denial of Service | ¿hay límites, timeouts, rate limiting? | |
| Elevation of Privilege | ¿se puede escalar permisos por input malicioso? | |

### 4. ARREGLAR O CLASIFICAR
- **CRÍTICO/ALTO**: inyección, exposición de secretos, auth bypass → arreglar AHORA.
- **MEDIO**: XSS, path traversal sin protección → arreglar antes del merge.
- **BAJO**: logging incompleto, headers faltantes → backlog.
- Auto-fix para lo obvio (escaping, validación de rutas). Flag lo que requiera diseño.

### 5. VEREDICTO
Formato limpio: sin falsos positivos, sin teatralidad.
- **PASS / FAIL** (con severidad y ubicación exacta: archivo:línea).
- Por cada hallazgo: severidad, reproducción (1 línea), fix sugerido.
- No inventar: si no hay problema, no lo reportes.

## Pitfalls
- Confundir estilo de código con vulnerabilidad (no es el rol CSO).
- Falsos positivos: reportar `json.dumps()` como "inseguro" sin contexto.
- Ignorar Windows: rutas, permisos, `os.path.join` vs concatenación.
- No verificar logs: ¿se filtra algo en mensajes de error?
- Saltar la verificación post-fix: el fix también puede tener vulnerabilidades.
