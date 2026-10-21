---
name: estructura-proyecto-python
description: Reglas CONCRETAS de organización para proyectos Python (FastAPI u otros): UN solo venv, UN layout coherente con los tests, dependencias mínimas, y verify_project PASS 3/3 antes de declarar listo. Usar SIEMPRE al crear o terminar un proyecto Python.
version: 1.0.0
category: development
tags: [python, estructura, organizacion, venv, dependencias, verify, proyecto]
---
# Estructura de Proyecto Python — Reglas que NO se rompen

## When to Use

Al CREAR un proyecto Python nuevo (API, script, app) y ANTES de declarar
cualquier proyecto como terminado. Si el pedido implica carpeta, estructura,
dependencias o tests, estas reglas aplican.

## Procedure

### 1. UN solo venv (nunca dos)
- Crear UN entorno virtual: `.venv` en la raíz del proyecto. Nada de `venv/`
  además de `.venv/`, ni `env/`, ni venvs del sistema.
- Instalar SOLO ahí: `.venv/bin/pip install -r requirements.txt`.
- Si encontrás dos venvs en un proyecto, borrá el extra (pedir OK antes de
  borrar) y deja uno solo.

### 2. UN layout coherente — elegir y respetar
- **Opción plana (default para consignas que dicen `uvicorn main:app`):**
  `main.py` en la RAÍZ del proyecto. La raíz es la que importa, la que corre
  pytest y la que sirve uvicorn.
- **Opción src/:** solo si el pedido la pide explícitamente. Entonces TODO
  se configura para src/ (PYTHONPATH, pytest, uvicorn con cwd=src).
- La trampa clásica: `main.py` en `src/` pero tests con `from main import`
  y `uvicorn main:app` desde la raíz → NO IMPORTA NADA. Raíz, tests y
  servidor deben matchear UN layout.

### 3. Estructura mínima correcta (FastAPI de consigna)
```
mi_proyecto/
├── main.py            # app FastAPI en la raíz (o src/ si se pidió)
├── requirements.txt   # SOLO lo necesario (p.ej. fastapi, uvicorn)
├── .venv/             # UN solo venv
└── tests/
    └── test_main.py   # importan igual que la raíz: from main import app
```

### 4. Dependencias mínimas (nada de más)
- Instalar SOLO lo que la consigna/pedido pide. No agregar librerías "por si
  acaso", ni duplicar lo que ya trae el framework.
- `requirements.txt` escrito a mano con lo instalado de verdad, no volcado
  ciego de `pip freeze` (eso trae cientos de paquetes innecesarios).
- Regla YAGNI: si no lo usás en el código, no se instala.

### 5. Verificación OBLIGATORIA antes de declarar listo
- Correr SIEMPRE: `code_helper(action='verify_project', project_dir='<raíz>')`.
- Solo PASS 3/3 (import + tests + endpoint respondiendo) autoriza a decir
  "tarea completa".
- Si es FAIL: arreglar los puntos ❌ y volver a correr hasta PASS 3/3.
- NUNCA declarar "listo/verificado" sin el output de verify_project.

## Pitfalls

- Decir "está listo, verifiqué los tests" sin haberlos corrido = mentira
  detectable; el gate de verify_project te lo va a mostrar en rojo.
- `pip freeze` completo al requirements.txt = instalaciones de más.
- Dos venvs = mitad de las dependencias se instala donde nadie las ve.
- Tests que importan por una vía y la app corre por otra = import roto en
  producción aunque "los tests pasen en mi terminal".
