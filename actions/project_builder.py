import os
import sys
import subprocess

def _generate_python(params):
    project_name = params.get('project_name', 'my_python_project')
    fields_list = params.get('fields', [])
    
    try:
        os.makedirs(project_name, exist_ok=True)
        main_content = f"def main():\n    print(f'Hola desde {project_name}')\n\nif __name__ == '__main__':\n    main()"
        with open(os.path.join(project_name, 'main.py'), 'w') as f:
            f.write(main_content)
        
        # FIX: Check if fields_list is not empty before accessing index 0
        test_entity_name = fields_list[0].get('name', 'item').lower().replace(' ', '_').replace('-', '_') if fields_list and fields_list[0] else 'item'

        test_content = f"import unittest\nimport main\nimport os\n\nclass TestProject(unittest.TestCase):\n    def test_main_file_exists(self):\n        self.assertTrue(os.path.exists(f'{project_name}/main.py'))\n\nif __name__ == '__main__':\n    unittest.main()"
        
        tests_path = os.path.join(project_name, 'tests')
        os.makedirs(tests_path, exist_ok=True)
        with open(os.path.join(tests_path, 'test_main.py'), 'w') as f:
            f.write(test_content)
        
        return f'Proyecto {project_name} creado con éxito y tests generados.'
    except Exception as e:
        return f'Error al crear el proyecto {project_name}: {e}'

# Simulación de la función generator que llama a _generate_python
def project_builder(params):
    if params.get('project_type') == 'python':
        return _generate_python(params)
    return "Tipo de proyecto no soportado para esta prueba."
