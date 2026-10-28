"""
eris_fix_builder.py — Librería propia creada por Eris.

Librería para corregir y crear proyectos Python simples de forma robusta, evitando errores de índice en project_builder.
Creada: 2026-10-24 06:48
"""
import json


def crear_proyecto_python_simple(**kwargs):
    """Crea un proyecto Python básico con main.py y un test simple, evitando el error de IndexError."""
    # Implementación de crear_proyecto_python_simple
    import os
    import sys
    import subprocess
    
    def crear_proyecto_python_simple(project_name):
        try:
            os.makedirs(project_name, exist_ok=True)
            main_content = """def main():\n    print(f'Hola desde {project_name}')\n\nif __name__ == '__main__':\n    main()"""
            with open(os.path.join(project_name, 'main.py'), 'w') as f:
                f.write(main_content)
            
            test_content = """import unittest\nimport main\n
    class TestProject(unittest.TestCase):\n    def test_main(self):\n        # Simula la ejecución o verifica la estructura
            self.assertTrue(os.path.exists(f'{project_name}/main.py'))\n
    if __name__ == '__main__':\n    unittest.main()"""
            os.makedirs(os.path.join(project_name, 'tests'), exist_ok=True)
            with open(os.path.join(project_name, 'tests', 'test_main.py'), 'w') as f:
                f.write(test_content)
            
            return f'Proyecto {project_name} creado con éxito.'
        except Exception as e:
            return f'Error al crear el proyecto {project_name}: {e}'