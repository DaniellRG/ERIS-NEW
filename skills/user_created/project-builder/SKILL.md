---
name: project-builder
description: Protocolo completo para crear proyectos de software autónomamente. Genera estructura + código + config + compilación para 8 tipos: Java/Maven, Python, C#, HTML/CSS/JS, React, Angular, Vue, MySQL.
version: 1.0.0
category: development
tags: [proyectos, java, python, react, angular, vue, mysql, creacion, autonomo]
---
# Project Builder — Protocolo de Creación Autónoma de Proyectos

## When to Use
CUANDO el usuario pida crear un sistema, aplicación, proyecto, o programa completo de cualquier lenguaje. Incluye: "creame un...", "haceme un proyecto de...", "necesito un sistema para...", "generame una app de...", "armame un programa que...".

## Procedure

### 1. Recibir y confirmar el pedido
- Escuchar qué quiere el usuario: qué tipo de proyecto, para qué sirve, qué lenguaje/framework.
- Si el usuario no especifica el tipo → preguntar opciones:
  - "¿Qué lenguaje/fra-mework preferís? Java, Python, C#, HTML/CSS/JS, React, Angular, Vue, o MySQL?"
- Confirmar nombre del proyecto y ubicación (default: Desktop).

### 2. Recopilar campos/entidades (si es CRUD o app con datos)
- Preguntar: "¿Qué datos maneja el sistema? ¿Qué campos tiene cada entidad?"
- Ejemplo: "Para el sistema de mantenimiento necesito: Equipo (id, nombre, marca, modelo, estado) y Mantenimiento (id, equipo_id, tipo, fecha, técnico, observaciones)"
- Si el usuario no da campos → crear campos de ejemplo razonables según el dominio.

### 3. Ejecutar project_builder
```
project_builder(
    project_type='tipo',
    project_name='nombre',
    description='qué hace el sistema',
    fields='[JSON con entidades y campos]',
    output_dir='Desktop',       # opcional
    database='nombre_bd',        # solo para MySQL
    features='["feature1"]'      # opcional
)
```

**Tipos disponibles:**
| Tipo | Para qué |
|------|----------|
| `java_maven` | Java + Maven + NetBeans Swing con .form XML |
| `python` | Python con dataclasses, repos, services, tests |
| `csharp` | C# / ASP.NET |
| `html_css_js` | HTML + CSS + JS vanilla |
| `react` | React + Vite (JSX) |
| `angular` | Angular 17+ |
| `vue` | Vue 3 + Vite |
| `mysql` | MySQL schema + data + procedures + views |

### 4. Reportar resultados
- Decir al usuario: cuántos archivos, dónde quedó, si compiló OK.
- Abrir la carpeta o el navegador si es web.
- Ofrecer modifications: "¿Querés que le agregue algo más?"

### 5. Modifications posteriores
- Si el usuario quiere cambiar algo específico → usar `code_engineer` o `self_edit` para editar archivos individuales.
- Si quiere agregar una entidad nueva → volver a llamar `project_builder` con los campos actualizados.

### 6. Documentar en memoria
- Guardar en Obsidian: `obsidian_note(action='write', title='Proyecto: [nombre]', content='[detalles]', folder='Proyectos', tags='proyecto,[tipo]')`
- Guardar en memoria semántica para referencia futura.

## Format — JSON de campos

```json
[
    {
        "name": "equipo",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "nombre", "type": "String"},
            {"name": "marca", "type": "String"},
            {"name": "modelo", "type": "String"},
            {"name": "estado", "type": "String"}
        ]
    },
    {
        "name": "mantenimiento",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "equipo_id", "type": "int"},
            {"name": "tipo", "type": "String"},
            {"name": "fecha", "type": "String"},
            {"name": "tecnico", "type": "String"},
            {"name": "observaciones", "type": "String"}
        ]
    }
]
```

**Tipos de campo soportados:** int, long, double, float, boolean, String (str/text), Date (date/datetime).

## Ejemplo completo — Java NetBeans

Usuario: "Creame un sistema de registro de mantenimiento de computadores en Java con NetBeans"

Eris ejecuta:
```
project_builder(
    project_type='java_maven',
    project_name='SistemaMantenimiento',
    description='Sistema de registro de mantenimiento de computadores',
    fields='[{"name":"equipo","fields":[{"name":"id","type":"int"},{"name":"nombre","type":"String"},{"name":"marca","type":"String"},{"name":"modelo","type":"String"},{"name":"estado","type":"String"}]},{"name":"mantenimiento","fields":[{"name":"id","type":"int"},{"name":"equipo_id","type":"int"},{"name":"tipo","type":"String"},{"name":"fecha","type":"String"},{"name":"tecnico","type":"String"},{"name":"observaciones","type":"String"}]}]'
)
```

**Resultado esperado:**
- Crea `SistemaMantenimiento/` en Desktop
- Genera: pom.xml, Main.java, 2 modelos, 2 repositorios, 2 servicios, 2 formularios Swing + .form XML, README.md, .gitignore
- Intenta compilar con javac (si JDK está disponible)
- Reporta: "Proyecto creado: 12 archivos, 15.3 KB, compilación OK"

## Ejemplo — Python

Usuario: "Haceme un proyecto Python para gestionar empleados"

Eris ejecuta:
```
project_builder(
    project_type='python',
    project_name='GestionEmpleados',
    description='Sistema de gestión de empleados',
    fields='[{"name":"empleado","fields":[{"name":"id","type":"int"},{"name":"nombre","type":"str"},{"name":"cargo","type":"str"},{"name":"salario","type":"float"},{"name":"activo","type":"bool"}]}]'
)
```

## Pitfalls
- NO crear archivos sueltos a mano cuando project_builder puede generar todo el proyecto de una.
- Si el usuario no da campos → crear campos razonables según el dominio, no preguntar 10 veces.
- Si el tipo no está soportado → usar la tool de todas formas y generar lo que se pueda (ej: para C# sin dotnet SDK, crear archivos y decir que necesita SDK).
- Para Java: SIEMPRE generar el .form XML para que NetBeans pueda abrir el formulario en modo visual.
- Después de generar, siempre reportar si compiló o no, y la ruta exacta del proyecto.
