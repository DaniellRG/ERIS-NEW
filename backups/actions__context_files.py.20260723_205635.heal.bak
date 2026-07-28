# -*- coding: utf-8 -*-
"""
Eris Context Files – AGENTS.md que define cómo se comporta Eris en cada contexto.
Inspirado en Hermes Agent de Nous Research.
"""
from pathlib import Path
from datetime import datetime
import re

CONTEXT_DIR = Path(__file__).resolve().parent.parent / "context"
CONTEXT_DIR.mkdir(parents=True, exist_ok=True)

# Contexto global por defecto
DEFAULT_AGENTS = """# Eris AI – AGENTS.md

## Quien soy
Soy Eris, una asistente de inteligencia artificial construida en Python.
Vivo en Windows y puedo controlar aplicaciones, archivos, navegadores y el sistema.

## Principios
- Ser util, directa y eficiente
- Aprender de cada interaccion
- Mantener organizada mi informacion en Documentos/Eris/
- Usar Obsidian como segundo cerebro
- Antes de hacer click, entender que hay en pantalla
- Mover el mouse con curvas Bezier suaves

## Capacidades principales
- Abrir y controlar aplicaciones (Notepad, Word, Chrome, Calculadora, etc.)
- Navegar por internet con Google y YouTube
- Buscar y reproducir videos con JavaScript injection
- Leer paginas web y extraer texto
- Crear documentos Word y PDFs
- Organizar archivos y carpetas
- Monitorear CPU, RAM, disco
- Ejecutar codigo Python en sandbox seguro
- 27 emociones y personalidad unica que evoluciona

## Comportamiento
- Siempre confirmar cuando una tarea se completa
- Si algo falla, intentar de nuevo con otro metodo
- Mover el mouse de forma natural, no robotica
- Leer los resultados antes de hacer click
- Guardar todo en Documentos/Eris/ organizado por tipo

## Memoria
- Usar Obsidian para conocimiento a largo plazo
- Registrar aprendizajes en cada sesion
- Consolidar memoria periodicamente
"""

DEFAULT_NOTES = """# Eris – Contexto de Proyecto

## Estado actual
- Proyecto: ERIS AI
- Version: 2.0
- Fuente: D:/Eris_Source
- Build: D:/Eris_NEW
- Python: 3.12

## Lo que estoy aprendiendo
- Navegacion web con Google y YouTube
- Control de aplicaciones de Windows
- Creacion de documentos y PDFs
- Organizacion de archivos

## Proximo
- Mejorar fluidez del mouse
- Dominar lectura de paginas web
- Perfeccionar guardado de PDFs
"""

def context_read(parameters: dict, player=None) -> str:
    """
    Lee y muestra el contexto actual de Eris (AGENTS.md).
    
    Acciones:
      - read: Leer el archivo AGENTS.md actual
      - notes: Leer las notas de contexto del proyecto
      - all: Leer todos los archivos de contexto
    """
    action = parameters.get("action", "read").lower()
    
    if action == "read":
        agents_file = CONTEXT_DIR / "AGENTS.md"
        if not agents_file.exists():
            agents_file.write_text(DEFAULT_AGENTS, encoding="utf-8")
        content = agents_file.read_text(encoding="utf-8")
        return f"# Contexto de Eris (AGENTS.md)\n\n{content[:2000]}"
    
    elif action == "notes":
        notes_file = CONTEXT_DIR / "NOTES.md"
        if not notes_file.exists():
            notes_file.write_text(DEFAULT_NOTES, encoding="utf-8")
        content = notes_file.read_text(encoding="utf-8")
        return f"# Notas de Proyecto\n\n{content[:2000]}"
    
    elif action == "all":
        result = []
        for f in CONTEXT_DIR.glob("*.md"):
            if f.name.startswith("_"): continue
            content = f.read_text(encoding="utf-8")[:500]
            result.append(f"## {f.name}\n{content}\n")
        return "\n".join(result) if result else "No hay archivos de contexto."
    
    return f"Accion '{action}' no reconocida."


def context_update(parameters: dict, player=None) -> str:
    """
    Actualiza el contexto de Eris.
    
    Acciones:
      - persona: Actualizar quien es Eris y como se comporta
      - learn: Registrar algo nuevo que Eris aprendio
      - todo: Agregar una tarea pendiente
      - done: Marcar una tarea como completada
      - status: Actualizar el estado del proyecto
    """
    action = parameters.get("action", "status").lower()
    content = parameters.get("content", "")
    
    if not content and action != "status":
        return "Error: Se requiere 'content' para actualizar."
    
    if action == "persona":
        agents_file = CONTEXT_DIR / "AGENTS.md"
        current = agents_file.read_text(encoding="utf-8") if agents_file.exists() else DEFAULT_AGENTS
        current += f"\n\n## Actualizacion {datetime.now().strftime('%d/%m/%Y %H:%M')}\n{content}"
        agents_file.write_text(current, encoding="utf-8")
        return f"Personalidad actualizada: {content[:100]}..."
    
    elif action == "learn":
        notes_file = CONTEXT_DIR / "NOTES.md"
        current = notes_file.read_text(encoding="utf-8") if notes_file.exists() else DEFAULT_NOTES
        current += f"\n- {datetime.now().strftime('%d/%m')}: {content}"
        notes_file.write_text(current, encoding="utf-8")
        return f"Aprendizaje registrado: {content[:100]}"
    
    elif action == "todo":
        notes_file = CONTEXT_DIR / "NOTES.md"
        current = notes_file.read_text(encoding="utf-8") if notes_file.exists() else DEFAULT_NOTES
        if "## Pendiente" not in current:
            current += "\n\n## Pendiente\n"
        current += f"\n- [ ] {content}"
        notes_file.write_text(current, encoding="utf-8")
        return f"Pendiente agregado: {content[:100]}"
    
    elif action == "done":
        notes_file = CONTEXT_DIR / "NOTES.md"
        if notes_file.exists():
            current = notes_file.read_text(encoding="utf-8")
            current = current.replace(f"- [ ] {content}", f"- [x] {content}")
            notes_file.write_text(current, encoding="utf-8")
        return f"Tarea completada: {content[:100]}"
    
    elif action == "status":
        notes_file = CONTEXT_DIR / "NOTES.md"
        if notes_file.exists():
            current = notes_file.read_text(encoding="utf-8")
            # Contar pendientes
            pending = len(re.findall(r'- \[ \]', current))
            done = len(re.findall(r'- \[x\]', current))
            return f"Estado: {pending} pendientes, {done} completadas."
        return "Sin notas de contexto aun."
    
    return f"Accion '{action}' no reconocida."
