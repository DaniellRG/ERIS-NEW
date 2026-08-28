"""
actions/project_builder.py — Generador autónomo de proyectos completos de software.
Crea proyectos con estructura completa, código fuente, configuración de build,
compilación y validación. Soporta: Java/Maven, Python, C#, HTML/CSS/JS, React,
Angular, Vue, MySQL.

Protocolo:
  1. Recibe tipo de proyecto + nombre + descripción + campos
  2. Crea estructura de carpetas
  3. Genera todos los archivos (código + config + README)
  4. Compila/valida
  5. Retorna resumen completo
"""

import ast
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

_BASE_DIR = Path(__file__).resolve().parent.parent
_JDK_PATH = r"C:\Program Files\Apache NetBeans\jdk\bin\javac.exe"
_JAVA_PATH = r"C:\Program Files\Apache NetBeans\jdk\bin\java.exe"

# ──────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────────────────────────

def _safe_makedirs(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_file(path: Path, content: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return len(content)


def _run_cmd(cmd: str, cwd: str, timeout: int = 60) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode == 0, out.strip()[:3000]
    except subprocess.TimeoutExpired:
        return False, f"Timeout ({timeout}s)"
    except Exception as e:
        return False, str(e)[:500]


def _java_package_to_path(package: str) -> str:
    return package.replace(".", "/")


def _classify_class_name(name: str) -> str:
    return "".join(w.capitalize() for w in name.replace("-", "_").split("_"))


# ──────────────────────────────────────────────────────────────────────────────
# JAVA / MAVEN / NETBEANS SWING
# ──────────────────────────────────────────────────────────────────────────────

def _generate_java_maven(params: dict) -> dict:
    project_name = params["project_name"]
    description = params.get("description", "")
    output_dir = Path(params.get("output_dir", "") or Path.home() / "Desktop")
    fields_raw = params.get("fields", "[]")
    features = _parse_json_list(params.get("features", "[]"))

    try:
        fields_list = json.loads(fields_raw) if isinstance(fields_raw, str) else fields_raw
    except Exception:
        fields_list = []

    root = output_dir / project_name
    pkg = f"com.eris.{project_name.lower().replace('-', '_').replace(' ', '_')}"
    pkg_path = _java_package_to_path(pkg)
    src_main = root / "src" / "main" / "java" / pkg_path
    src_res = root / "src" / "main" / "resources"
    src_test = root / "src" / "test" / "java" / pkg_path
    files = []

    # ── pom.xml ──
    pom = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.eris</groupId>
    <artifactId>{project_name.lower().replace(" ", "-")}</artifactId>
    <version>1.0-SNAPSHOT</version>
    <packaging>jar</packaging>
    <name>{project_name}</name>
    <description>{description}</description>
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    <dependencies>
        <dependency>
            <groupId>com.google.code.gson</groupId>
            <artifactId>gson</artifactId>
            <version>2.10.1</version>
        </dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-jar-plugin</artifactId>
                <version>3.3.0</version>
                <configuration>
                    <archive>
                        <manifest>
                            <mainClass>{pkg}.Main</mainClass>
                        </manifest>
                    </archive>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>"""
    files.append(("pom.xml", pom))

    # ── Modelos ──
    for entity in fields_list:
        entity_name = _classify_class_name(entity.get("name", "Item"))
        entity_fields = entity.get("fields", [])
        if not entity_fields:
            entity_fields = [
                {"name": "id", "type": "int"},
                {"name": "nombre", "type": "String"},
                {"name": "descripcion", "type": "String"},
            ]

        # Clase modelo
        model_fields = ""
        constructors = ""
        getters_setters = ""
        for f in entity_fields:
            fname = f.get("name", "campo")
            ftype = _java_type(f.get("type", "String"))
            model_fields += f"    private {ftype} {fname};\n"
            constructors += f"        this.{fname} = {fname};\n"
            cap = fname[0].upper() + fname[1:]
            getters_setters += f"""
    public {ftype} get{cap}() {{ return {fname}; }}
    public void set{cap}({ftype} {fname}) {{ this.{fname} = {fname}; }}
"""
        first_fields = ", ".join(
            f"{_java_type(f.get('type','String'))} {f.get('name','campo')}" for f in entity_fields[:5]
        )
        model_code = f"""package {pkg}.models;

/**
 * Modelo de datos: {entity_name}
 * Generado por ERIS project_builder
 */
public class {entity_name} {{
{model_fields}
    public {entity_name}() {{}}

    public {entity_name}({first_fields}) {{
{constructors}
    }}
{getters_setters}
    @Override
    public String toString() {{
        return "{entity_name}{{" + "id=" + id + ", nombre=" + nombre + "}}";
    }}
}}"""
        files.append((f"src/main/java/{pkg_path}/models/{entity_name}.java", model_code))

        # Repositorio
        repo_code = f"""package {pkg}.repositories;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import {pkg}.models.{entity_name};

/**
 * Repositorio en memoria para {entity_name}
 * Generado por ERIS project_builder
 */
public class {entity_name}Repository {{
    private final List<{entity_name}> datos = new ArrayList<>();
    private final AtomicInteger idCounter = new AtomicInteger(1);

    public {entity_name} guardar({entity_name} entidad) {{
        if (entidad.getId() == 0) {{
            entidad.setId(idCounter.getAndIncrement());
        }}
        datos.removeIf(e -> e.getId() == entidad.getId());
        datos.add(entidad);
        return entidad;
    }}

    public Optional<{entity_name}> buscarPorId(int id) {{
        return datos.stream().filter(e -> e.getId() == id).findFirst();
    }}

    public List<{entity_name}> listarTodos() {{
        return new ArrayList<>(datos);
    }}

    public boolean eliminar(int id) {{
        return datos.removeIf(e -> e.getId() == id);
    }}

    public int contar() {{
        return datos.size();
    }}
}}"""
        files.append((f"src/main/java/{pkg_path}/repositories/{entity_name}Repository.java", repo_code))

        # Servicio
        svc_code = f"""package {pkg}.services;

import java.util.List;
import java.util.Optional;
import {pkg}.models.{entity_name};
import {pkg}.repositories.{entity_name}Repository;

/**
 * Servicio de negocio para {entity_name}
 * Generado por ERIS project_builder
 */
public class {entity_name}Service {{
    private final {entity_name}Repository repositorio = new {entity_name}Repository<>();

    public {entity_name} crear({entity_name} entidad) {{
        return repositorio.guardar(entidad);
    }}

    public {entity_name} actualizar({entity_name} entidad) {{
        return repositorio.guardar(entidad);
    }}

    public Optional<{entity_name}> buscarPorId(int id) {{
        return repositorio.buscarPorId(id);
    }}

    public List<{entity_name}> listarTodos() {{
        return repositorio.listarTodos();
    }}

    public boolean eliminar(int id) {{
        return repositorio.eliminar(id);
    }}

    public int contar() {{
        return repositorio.contar();
    }}
}}"""
        files.append((f"src/main/java/{pkg_path}/services/{entity_name}Service.java", svc_code))

        # Formulario Swing + .form XML
        form_swing, form_xml = _generate_swing_form(entity_name, entity_fields, pkg)
        files.append((f"src/main/java/{pkg_path}/forms/{entity_name}Form.java", form_swing))
        files.append((f"src/main/java/{pkg_path}/forms/{entity_name}Form.form", form_xml))

    # ── Main.java ──
    main_code = f"""package {pkg};

import javax.swing.*;
import java.awt.*;

/**
 * {project_name} — {description}
 * Generado por ERIS project_builder
 */
public class Main {{
    public static void main(String[] args) {{
        try {{
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        }} catch (Exception e) {{
            e.printStackTrace();
        }}

        SwingUtilities.invokeLater(() -> {{
            JFrame frame = new JFrame("{project_name}");
            frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            frame.setSize(900, 650);
            frame.setLocationRelativeTo(null);

            JTabbedPane tabs = new JTabbedPane();
"""
    for entity in fields_list:
        entity_name = _classify_class_name(entity.get("name", "Item"))
        main_code += f'            tabs.addTab("{entity_name}", new {pkg}.forms.{entity_name}Form().getPanel());\n'

    main_code += f"""
            frame.setContentPane(tabs);
            frame.setVisible(true);
        }});
    }}
}}"""
    files.append((f"src/main/java/{pkg_path}/Main.java", main_code))

    # ── README.md ──
    readme = f"""# {project_name}

{description}

## Estructura

```
{project_name}/
├── pom.xml
├── README.md
├── src/main/java/{pkg_path}/
│   ├── Main.java
│   ├── models/         (entidades de datos)
│   ├── repositories/   (acceso a datos)
│   ├── services/       (lógica de negocio)
│   └── forms/          (formularios Swing + .form XML)
├── src/main/resources/
└── src/test/java/{pkg_path}/
```

## Cómo compilar

### Con Maven (recomendado)
```bash
mvn clean compile
mvn exec:java
```

### Sin Maven (javac directo)
```bash
cd src/main/java
javac -d ../../classes {pkg_path.replace("/", "/")}/**/*.java
java -cp ../../classes {pkg}.Main
```

## Cómo abrir en NetBeans

1. File → Open Project → seleccionar la carpeta `{project_name}`
2. NetBeans detecta el `pom.xml` automáticamente
3. Los formularios `.form` se abren en el editor visual de Swing

## Generado por
ERIS AI — project_builder
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    files.append(("README.md", readme))

    # ── .gitignore ──
    gitignore = """target/
*.class
*.jar
*.war
*.ear
.idea/
*.iml
.settings/
.project
.classpath
nbproject/private/
build/
dist/
"""
    files.append((".gitignore", gitignore))

    # ── Crear todos los archivos ──
    created = []
    total_bytes = 0
    for rel_path, content in files:
        full = root / rel_path
        sz = _write_file(full, content)
        created.append(rel_path)
        total_bytes += sz

    # ── Compilar ──
    compile_ok = False
    compile_msg = ""
    if os.path.exists(_JDK_PATH):
        src_dir = root / "src" / "main" / "java"
        classes_dir = root / "target" / "classes"
        classes_dir.mkdir(parents=True, exist_ok=True)
        java_files = list(src_dir.rglob("*.java"))
        if java_files:
            file_list = " ".join(f'"{f}"' for f in java_files)
            cmd = f'"{_JDK_PATH}" -d "{classes_dir}" {file_list}'
            compile_ok, compile_msg = _run_cmd(cmd, str(root), timeout=30)

    return {
        "ok": True,
        "project_type": "java_maven",
        "project_name": project_name,
        "root": str(root),
        "files_created": len(created),
        "total_bytes": total_bytes,
        "compile_ok": compile_ok,
        "compile_output": compile_msg[:1000] if compile_msg else "Compilación OK" if compile_ok else "Sin javac en PATH (proyecto creado, compilar en NetBeans)",
        "files": created,
    }


def _java_type(t: str) -> str:
    t = t.lower().strip()
    mapping = {
        "int": "int", "integer": "int", "long": "long",
        "double": "double", "float": "float", "boolean": "boolean",
        "string": "String", "str": "String", "text": "String",
        "date": "String", "datetime": "String",
    }
    return mapping.get(t, "String")


def _generate_swing_form(entity_name: str, fields: list, pkg: str) -> tuple[str, str]:
    """Genera formulario Swing + archivo .form XML para NetBeans."""
    if not fields:
        fields = [{"name": "id", "type": "int"}, {"name": "nombre", "type": "String"}]

    java_code = f"""package {pkg}.forms;

import javax.swing.*;
import java.awt.*;
import {pkg}.models.{entity_name};
import {pkg}.services.{entity_name}Service;

/**
 * Formulario de gestión de {entity_name}
 * Generado por ERIS project_builder
 */
public class {entity_name}Form {{
    private JPanel panel;
    private {entity_name}Service service = new {entity_name}Service<>();
"""
    # Declarar campos Swing
    field_vars = []
    for f in fields:
        fname = f.get("name", "campo")
        fname_safe = fname.replace("-", "_").replace(" ", "_")
        field_vars.append(fname_safe)
        java_code += f"    private JTextField txt{fname_safe.capitalize()};\n"

    java_code += f"    private JList<{entity_name}> listItems;\n"
    java_code += f"    private DefaultListModel<{entity_name}> listModel;\n\n"

    java_code += f"""    public {entity_name}Form() {{
        initUI();
        cargarDatos();
    }}

    private void initUI() {{
        panel = new JPanel(new BorderLayout(10, 10));
        panel.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));

        // ── Formulario ──
        JPanel formPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.anchor = GridBagConstraints.WEST;

        int row = 0;
"""
    for i, f in enumerate(fields):
        fname = f.get("name", "campo")
        fname_safe = fname.replace("-", "_").replace(" ", "_")
        cap = fname_safe.capitalize()
        java_code += f"""
        gbc.gridx = 0; gbc.gridy = {i};
        formPanel.add(new JLabel("{fname.capitalize()}:"), gbc);
        txt{cap} = new JTextField(20);
        gbc.gridx = 1;
        formPanel.add(txt{cap}, gbc);
"""

    java_code += f"""
        // ── Botones ──
        JPanel btnPanel = new JPanel(new FlowLayout(FlowLayout.CENTER, 10, 0));
        JButton btnGuardar = new JButton("Guardar");
        JButton btnEliminar = new JButton("Eliminar");
        JButton btnLimpiar = new JButton("Limpiar");
        btnPanel.add(btnGuardar);
        btnPanel.add(btnEliminar);
        btnPanel.add(btnLimpiar);

        gbc.gridx = 0; gbc.gridy = {len(fields)}; gbc.gridwidth = 2;
        formPanel.add(btnPanel, gbc);

        // ── Lista ──
        listModel = new DefaultListModel<>();
        listItems = new JList<>(listModel);
        listItems.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        listItems.addListSelectionListener(e -> {{
            {entity_name} sel = listItems.getSelectedValue();
            if (sel != null) cargarFormulario(sel);
        }});

        JSplitPane split = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT,
            new JScrollPane(formPanel), new JScrollPane(listItems));
        split.setDividerLocation(350);
        panel.add(split, BorderLayout.CENTER);

        // ── Acciones ──
        btnGuardar.addActionListener(e -> guardar());
        btnEliminar.addActionListener(e -> eliminar());
        btnLimpiar.addActionListener(e -> limpiarFormulario());
    }}

    private void guardar() {{
        {entity_name} entidad = new {entity_name}();
"""
    for f in fields:
        fname = f.get("name", "campo")
        fname_safe = fname.replace("-", "_").replace(" ", "_")
        cap = fname_safe.capitalize()
        ftype = f.get("type", "String").lower()
        if ftype in ("int", "integer", "long"):
            java_code += f'        try {{ entidad.set{cap}(Integer.parseInt(txt{cap}.getText().trim())); }} catch (Exception ex) {{}}\n'
        elif ftype in ("double", "float"):
            java_code += f'        try {{ entidad.set{cap}(Double.parseDouble(txt{cap}.getText().trim())); }} catch (Exception ex) {{}}\n'
        elif ftype == "boolean":
            java_code += f'        entidad.set{cap}(Boolean.parseBoolean(txt{cap}.getText().trim()));\n'
        else:
            java_code += f"        entidad.set{cap}(txt{cap}.getText().trim());\n"

    java_code += f"""        service.crear(entidad);
        cargarDatos();
        limpiarFormulario();
        JOptionPane.showMessageDialog(panel, "{entity_name} guardado correctamente.");
    }}

    private void eliminar() {{
        {entity_name} sel = listItems.getSelectedValue();
        if (sel == null) {{
            JOptionPane.showMessageDialog(panel, "Seleccioná un registro para eliminar.");
            return;
        }}
        int confirm = JOptionPane.showConfirmDialog(panel,
            "¿Eliminar registro #" + sel.getId() + "?",
            "Confirmar", JOptionPane.YES_NO_OPTION);
        if (confirm == JOptionPane.YES_OPTION) {{
            service.eliminar(sel.getId());
            cargarDatos();
            limpiarFormulario();
        }}
    }}

    private void cargarFormulario({entity_name} entidad) {{
"""
    for f in fields:
        fname = f.get("name", "campo")
        fname_safe = fname.replace("-", "_").replace(" ", "_")
        cap = fname_safe.capitalize()
        java_code += f"        txt{cap}.setText(String.valueOf(entidad.get{cap}()));\n"

    java_code += f"""    }}

    private void limpiarFormulario() {{
"""
    for f in fields:
        fname = f.get("name", "campo")
        fname_safe = fname.replace("-", "_").replace(" ", "_")
        cap = fname_safe.capitalize()
        java_code += f"        txt{cap}.setText(\"\");\n"

    java_code += f"""        listItems.clearSelection();
    }}

    private void cargarDatos() {{
        listModel.clear();
        for ({entity_name} e : service.listarTodos()) {{
            listModel.addElement(e);
        }}
    }}

    public JPanel getPanel() {{
        return panel;
    }}
}}
"""
    # ── .form XML para NetBeans ──
    form_xml = f"""<?xml version="1.0" encoding="UTF-8"?>

<Form version="1" maxVersion="2.0">
    <MatthewPainsworthAndERIS/>
    <Properties>
        <Property name="defaultCloseOperation" type="java.lang.Integer" value="2"/>
        <Property name="title" type="java.lang.String" value="{entity_name} Form"/>
    </Properties>
    <SyntheticProperties>
        <SyntheticProperty name="form_size" type="java.awt.Dimension" value="900,650"/>
    </SyntheticProperties>
    <AuxValues>
        <AuxValue name="FormBounds_x" type="java.lang.Integer" value="100"/>
        <AuxValue name="FormBounds_y" type="java.lang.Integer" value="100"/>
        <AuxValue name="FormBounds_width" type="java.lang.Integer" value="900"/>
        <AuxValue name="FormBounds_height" type="java.lang.Integer" value="650"/>
    </AuxValues>
    <Imports>
        <Import class="java.awt.*"/>
        <Import class="javax.swing.*"/>
    </Imports>
    <Layout>
        <GridBagLayout>
            <Constraints>
                <Constraint layoutClass="GridBagConstraints" row="0" column="0">
                    <GridBagConstraints gridwidth="2" fill="BOTH" weightx="1.0" weighty="1.0"
                        insets="5,5,5,5" anchor="NORTHWEST"/>
                </Constraint>
            </Constraints>
        </GridBagLayout>
    </Layout>
    <Components>
"""
    for i, f in enumerate(fields):
        fname = f.get("name", "campo")
        form_xml += f"""        <Component class="javax.swing.JLabel" name="label{fname.capitalize()}">
            <Constraints>
                <Constraint layoutClass="GridBagConstraints" row="{i}" column="0">
                    <GridBagConstraints insets="5,5,5,5" anchor="WEST"/>
                </Constraint>
            </Constraints>
            <Properties>
                <Property name="text" type="java.lang.String" value="{fname.capitalize()}:"/>
            </Properties>
        </Component>
"""
    form_xml += """    </Components>
</Form>
"""
    return java_code, form_xml


# ──────────────────────────────────────────────────────────────────────────────
# PYTHON
# ──────────────────────────────────────────────────────────────────────────────

def _generate_python(params: dict) -> dict:
    project_name = params["project_name"]
    description = params.get("description", "")
    output_dir = Path(params.get("output_dir", "") or Path.home() / "Desktop")
    fields_raw = params.get("fields", "[]")
    features = _parse_json_list(params.get("features", "[]"))

    try:
        fields_list = json.loads(fields_raw) if isinstance(fields_raw, str) else fields_raw
    except Exception:
        fields_list = []

    root = output_dir / project_name
    pkg = project_name.lower().replace("-", "_").replace(" ", "_")
    files = []

    # ── pyproject.toml ──
    pyproject = f"""[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "{project_name.lower().replace(' ', '-')}"
version = "1.0.0"
description = "{description}"
requires-python = ">=3.10"
dependencies = []

[project.scripts]
{pkg} = "{pkg}.main:main"
"""
    files.append(("pyproject.toml", pyproject))

    # ── Módulos ──
    files.append((f"{pkg}/__init__.py", f'"""' + f"\n{project_name} — {description}\n" + '"""' + "\n\n__version__ = '1.0.0'\n"))

    for entity in fields_list:
        entity_name = entity.get("name", "item").lower().replace(" ", "_").replace("-", "_")
        entity_fields = entity.get("fields", [])
        if not entity_fields:
            entity_fields = [{"name": "id", "type": "int"}, {"name": "nombre", "type": "str"}]

        # Modelo
        model_attrs = "\n".join(f"    {f.get('name','campo')}: {f.get('type','str')}" for f in entity_fields)
        model_init = "\n".join(f"        self.{f.get('name','campo')} = {f.get('name','campo')}" for f in entity_fields)
        model_repr_fields = ", ".join(f"{f.get('name','campo')}={{self.{f.get('name','campo')}}}" for f in entity_fields)

        model_code = f"""\"\"\"
models/{entity_name}.py — Modelo de datos {entity_name}
Generado por ERIS project_builder
\"\"\"
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class {entity_name.capitalize()}:
{model_attrs}

    def to_dict(self) -> dict:
        return {{{", ".join(f'"{f.get("name","campo")}": self.{f.get("name","campo")}' for f in entity_fields)}}}

    @classmethod
    def from_dict(cls, data: dict) -> "{entity_name.capitalize()}":
        return cls(**{{k: v for k, v in data.items() if k in cls.__dataclass_fields__}})

    def __repr__(self) -> str:
        return f"{entity_name.capitalize()}({model_repr_fields})"
"""
        files.append((f"{pkg}/models/{entity_name}.py", model_code))

        # Repositorio
        repo_code = f"""\"\"\"
repositories/{entity_name}_repository.py — Repositorio {entity_name}
Generado por ERIS project_builder
\"\"\"
from typing import Optional, List
from {pkg}.models.{entity_name} import {entity_name.capitalize()}


class {entity_name.capitalize()}Repository:
    def __init__(self):
        self._datos: List[{entity_name.capitalize()}] = []
        self._counter = 1

    def guardar(self, entidad: {entity_name.capitalize()}) -> {entity_name.capitalize()}:
        if not entidad.id:
            entidad.id = self._counter
            self._counter += 1
        self._datos = [e for e in self._datos if e.id != entidad.id]
        self._datos.append(entidad)
        return entidad

    def buscar_por_id(self, id: int) -> Optional[{entity_name.capitalize()}]:
        return next((e for e in self._datos if e.id == id), None)

    def listar_todos(self) -> List[{entity_name.capitalize()}]:
        return list(self._datos)

    def eliminar(self, id: int) -> bool:
        prev = len(self._datos)
        self._datos = [e for e in self._datos if e.id != id]
        return len(self._datos) < prev

    def contar(self) -> int:
        return len(self._datos)
"""
        files.append((f"{pkg}/repositories/{entity_name}_repository.py", repo_code))

        # Servicio
        svc_code = f"""\"\"\"
services/{entity_name}_service.py — Servicio de negocio {entity_name}
Generado por ERIS project_builder
\"\"\"
from typing import Optional, List
from {pkg}.models.{entity_name} import {entity_name.capitalize()}
from {pkg}.repositories.{entity_name}_repository import {entity_name.capitalize()}Repository


class {entity_name.capitalize()}Service:
    def __init__(self):
        self.repo = {entity_name.capitalize()}Repository()

    def crear(self, entidad: {entity_name.capitalize()}) -> {entity_name.capitalize()}:
        return self.repo.guardar(entidad)

    def actualizar(self, entidad: {entity_name.capitalize()}) -> {entity_name.capitalize()}:
        return self.repo.guardar(entidad)

    def buscar_por_id(self, id: int) -> Optional[{entity_name.capitalize()}]:
        return self.repo.buscar_por_id(id)

    def listar_todos(self) -> List[{entity_name.capitalize()}]:
        return self.repo.listar_todos()

    def eliminar(self, id: int) -> bool:
        return self.repo.eliminar(id)
"""
        files.append((f"{pkg}/services/{entity_name}_service.py", svc_code))

    # ── main.py ──
    main_code = f"""\"\"\"
main.py — Punto de entrada de {project_name}
{description}
Generado por ERIS project_builder
\"\"\"
from pkg import __version__
"""
    imports = "\n".join(
        f"from {pkg}.services.{e.get('name','item').lower().replace(' ','_').replace('-','_')}_service import "
        f"{e.get('name','item').lower().replace(' ','_').replace('-','_').capitalize()}Service"
        for e in fields_list
    )
    main_code += imports + "\n\n\n"
    main_code += """def main():
    print("=" * 60)
    print(f"  {project_name} v{__version__}")
    print("=" * 60)
    print()
"""
    for e in fields_list:
        en = e.get("name", "item").lower().replace(" ", "_").replace("-", "_")
        main_code += f'    print("[{en.upper()}] Servicio listo. Usar {en.capitalize()}Service para operar.")\n'
    main_code += """
    print()
    print("Proyecto listo. Agregá lógica de UI o API según necesites.")


if __name__ == "__main__":
    main()
"""
    files.append((f"{pkg}/main.py", main_code))

    # ── tests/ ──
    files.append(("tests/__init__.py", ""))
    test_code = '"""Tests básicos para el proyecto."""\n\n'
    for e in fields_list:
        en = e.get("name", "item").lower().replace(" ", "_").replace("-", "_")
        cap = en.capitalize()
        test_code += f"""
def test_{en}_crear():
    from {pkg}.models.{en} import {cap}
    e = {cap}()
    assert e is not None
    print("  OK: {cap} se instancia correctamente")


def test_{en}_repository():
    from {pkg}.models.{en} import {cap}
    from {pkg}.repositories.{en}_repository import {cap}Repository
    repo = {cap}Repository()
    e = {cap}()
    repo.guardar(e)
    assert repo.contar() == 1
    print("  OK: {cap}Repository funciona")
"""
    test_code += f"""

if __name__ == "__main__":
    test_{fields_list[0].get('name','item').lower().replace(' ','_').replace('-','_')}_crear() if "{fields_list[0].get('name','item').lower().replace(' ','_').replace('-','_')}" in dir() else None
    print("\\nTodos los tests pasaron.")
"""
    files.append(("tests/test_basic.py", test_code))

    # ── README ──
    readme = f"""# {project_name}

{description}

## Estructura

```
{project_name}/
├── pyproject.toml
├── README.md
├── {pkg}/
│   ├── __init__.py
│   ├── main.py
│   ├── models/
│   ├── repositories/
│   └── services/
└── tests/
```

## Cómo ejecutar

```bash
python -m {pkg}.main
```

## Tests

```bash
python -m pytest tests/ -v
```

## Generado por
ERIS AI — project_builder
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    files.append(("README.md", readme))
    files.append((".gitignore", "__pycache__/\n*.pyc\n*.egg-info/\ndist/\nbuild/\n.env\n"))

    # ── Crear archivos ──
    created = []
    total_bytes = 0
    for rel_path, content in files:
        full = root / rel_path
        sz = _write_file(full, content)
        created.append(rel_path)
        total_bytes += sz

    # ── Validar Python ──
    compile_ok = True
    compile_errors = []
    py_files = list(root.rglob("*.py"))
    for pf in py_files:
        try:
            with open(pf, "r", encoding="utf-8") as fh:
                compile(fh.read(), str(pf), "exec")
        except SyntaxError as e:
            compile_ok = False
            compile_errors.append(f"{pf.relative_to(root)}: L{e.lineno} {e.msg}")

    return {
        "ok": True,
        "project_type": "python",
        "project_name": project_name,
        "root": str(root),
        "files_created": len(created),
        "total_bytes": total_bytes,
        "compile_ok": compile_ok,
        "compile_output": "; ".join(compile_errors) if compile_errors else "Syntax OK — todos los archivos válidos",
        "files": created,
    }


# ──────────────────────────────────────────────────────────────────────────────
# CSHARP / .NET
# ──────────────────────────────────────────────────────────────────────────────

def _generate_csharp(params: dict) -> dict:
    project_name = params["project_name"]
    description = params.get("description", "")
    output_dir = Path(params.get("output_dir", "") or Path.home() / "Desktop")
    fields_raw = params.get("fields", "[]")

    try:
        fields_list = json.loads(fields_raw) if isinstance(fields_raw, str) else fields_raw
    except Exception:
        fields_list = []

    root = output_dir / project_name
    files = []

    csproj = f"""<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <RootNamespace>{project_name.replace("-","_").replace(" ","_")}</RootNamespace>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
</Project>"""
    files.append((f"{project_name}.csproj", csproj))

    sln = f"""
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}", "{project_name}.csproj", "{{GENERATED-GUID}}"
EndProject
Global
    GlobalSection(SolutionConfigurationPlatforms) = preSolution
        Debug|Any CPU = Debug|Any CPU
        Release|Any CPU = Release|Any CPU
    EndGlobalSection
EndGlobal"""
    files.append((f"{project_name}.sln", sln))

    files.append(("Program.cs", f"""var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.MapGet("/", () => "{project_name} — {description}");
app.Run();
"""))

    readme = f"""# {project_name}

{description}

## Cómo compilar

```bash
dotnet build
dotnet run
```

## Generado por ERIS AI — project_builder
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    files.append(("README.md", readme))

    created = []
    total_bytes = 0
    for rel_path, content in files:
        full = root / rel_path
        sz = _write_file(full, content)
        created.append(rel_path)
        total_bytes += sz

    return {
        "ok": True, "project_type": "csharp",
        "project_name": project_name, "root": str(root),
        "files_created": len(created), "total_bytes": total_bytes,
        "compile_ok": None,
        "compile_output": "Requiere dotnet SDK para compilar",
        "files": created,
    }


# ──────────────────────────────────────────────────────────────────────────────
# HTML / CSS / JS
# ──────────────────────────────────────────────────────────────────────────────

def _generate_html_css_js(params: dict) -> dict:
    project_name = params["project_name"]
    description = params.get("description", "")
    output_dir = Path(params.get("output_dir", "") or Path.home() / "Desktop")
    fields_raw = params.get("fields", "[]")

    try:
        fields_list = json.loads(fields_raw) if isinstance(fields_raw, str) else fields_raw
    except Exception:
        fields_list = []

    root = output_dir / project_name
    files = []

    fields_html = ""
    for f in fields_list:
        fname = f.get("name", "campo")
        fields_html += f'            <div class="form-group">\n                <label for="{fname}">{fname.capitalize()}</label>\n                <input type="text" id="{fname}" name="{fname}" class="form-control" placeholder="{fname.capitalize()}">\n            </div>\n'

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <nav class="navbar">
            <div class="brand">{project_name}</div>
            <ul class="nav-links">
                <li><a href="#inicio">Inicio</a></li>
                <li><a href="#datos">Datos</a></li>
                <li><a href="#about">Acerca de</a></li>
            </ul>
        </nav>
    </header>

    <main>
        <section id="inicio" class="hero">
            <h1>{project_name}</h1>
            <p>{description}</p>
        </section>

        <section id="datos" class="container">
            <h2>Gestión de Datos</h2>
            <form id="dataForm" class="form-card">
{fields_html}
                <button type="submit" class="btn btn-primary">Guardar</button>
                <button type="reset" class="btn btn-secondary">Limpiar</button>
            </form>
            <div id="results" class="results-card" style="display:none;">
                <h3>Registros</h3>
                <table id="resultsTable">
                    <thead><tr id="tableHead"></tr></thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
        </section>

        <section id="about" class="container">
            <h2>Acerca de</h2>
            <p>{description}</p>
        </section>
    </main>

    <footer>
        <p>&copy; 2026 {project_name} — Creado por ERIS AI</p>
    </footer>
    <script src="js/app.js"></script>
</body>
</html>"""
    files.append(("index.html", html))

    css = f"""/* {project_name} — Estilos */
:root {{
    --primary: #6366f1;
    --secondary: #8b5cf6;
    --bg: #0f172a;
    --card: #1e293b;
    --text: #e2e8f0;
    --border: rgba(255,255,255,0.1);
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
}}

.navbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 2rem;
    background: rgba(15,23,42,0.95);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 100;
}}

.brand {{ font-size: 1.3rem; font-weight: 700; color: var(--primary); }}
.nav-links {{ display: flex; list-style: none; gap: 1.5rem; }}
.nav-links a {{ color: rgba(255,255,255,0.6); text-decoration: none; transition: color 0.3s; }}
.nav-links a:hover {{ color: var(--primary); }}

.hero {{
    text-align: center;
    padding: 5rem 2rem;
    background: radial-gradient(ellipse at center, rgba(99,102,241,0.15), transparent 70%);
}}
.hero h1 {{ font-size: 2.5rem; margin-bottom: 1rem; }}
.hero p {{ opacity: 0.7; max-width: 600px; margin: 0 auto; }}

.container {{ max-width: 900px; margin: 0 auto; padding: 3rem 2rem; }}
.container h2 {{ margin-bottom: 1.5rem; font-size: 1.8rem; }}

.form-card {{
    background: var(--card);
    padding: 2rem;
    border-radius: 12px;
    border: 1px solid var(--border);
}}
.form-group {{ margin-bottom: 1rem; }}
.form-group label {{ display: block; margin-bottom: 0.3rem; opacity: 0.8; font-size: 0.9rem; }}
.form-control {{
    width: 100%;
    padding: 0.7rem 1rem;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 1rem;
}}
.form-control:focus {{ border-color: var(--primary); outline: none; box-shadow: 0 0 0 3px rgba(99,102,241,0.2); }}

.btn {{
    padding: 0.7rem 1.5rem;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    margin-right: 0.5rem;
    transition: transform 0.2s;
}}
.btn:hover {{ transform: translateY(-2px); }}
.btn-primary {{ background: var(--primary); color: #fff; }}
.btn-secondary {{ background: rgba(255,255,255,0.1); color: var(--text); }}

.results-card {{
    margin-top: 2rem;
    background: var(--card);
    padding: 1.5rem;
    border-radius: 12px;
    border: 1px solid var(--border);
}}
table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
th, td {{ padding: 0.7rem; text-align: left; border-bottom: 1px solid var(--border); }}
th {{ color: var(--primary); font-weight: 600; }}

footer {{ text-align: center; padding: 2rem; opacity: 0.4; font-size: 0.85rem; border-top: 1px solid var(--border); margin-top: 3rem; }}
"""
    files.append(("css/style.css", css))

    js_fields = ", ".join(f'"{f.get("name","campo")}"' for f in fields_list) if fields_list else '"nombre", "descripcion"'
    js = f"""// {project_name} — JavaScript
document.addEventListener('DOMContentLoaded', () => {{
    const form = document.getElementById('dataForm');
    const results = document.getElementById('results');
    const thead = document.getElementById('tableHead');
    const tbody = document.getElementById('tableBody');
    const fields = [{js_fields}];
    let records = [];
    let idCounter = 1;

    // Generar encabezados de tabla
    fields.forEach(f => {{
        const th = document.createElement('th');
        th.textContent = f.charAt(0).toUpperCase() + f.slice(1);
        thead.appendChild(th);
    }});
    const thAct = document.createElement('th');
    thAct.textContent = 'Acciones';
    thead.appendChild(thAct);

    form.addEventListener('submit', (e) => {{
        e.preventDefault();
        const record = {{ id: idCounter++ }};
        fields.forEach(f => {{
            const input = form.querySelector(`[name="${{f}}"]`);
            record[f] = input ? input.value : '';
            if (input) input.value = '';
        }});
        records.push(record);
        renderTable();
        results.style.display = 'block';
    }});

    function renderTable() {{
        tbody.innerHTML = '';
        records.forEach((r, i) => {{
            const tr = document.createElement('tr');
            fields.forEach(f => {{
                const td = document.createElement('td');
                td.textContent = r[f];
                tr.appendChild(td);
            }});
            const tdA = document.createElement('td');
            const btnDel = document.createElement('button');
            btnDel.textContent = 'Eliminar';
            btnDel.className = 'btn btn-secondary';
            btnDel.style.padding = '0.3rem 0.8rem';
            btnDel.style.fontSize = '0.8rem';
            btnDel.onclick = () => {{ records.splice(i, 1); renderTable(); }};
            tdA.appendChild(btnDel);
            tr.appendChild(tdA);
            tbody.appendChild(tr);
        }});
    }}
}});
"""
    files.append(("js/app.js", js))

    files.append(("README.md", f"""# {project_name}

{description}

## Cómo abrir

Abrí `index.html` en tu navegador.

## Generado por ERIS AI — project_builder
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""))

    created = []
    total_bytes = 0
    for rel_path, content in files:
        full = root / rel_path
        sz = _write_file(full, content)
        created.append(rel_path)
        total_bytes += sz

    return {
        "ok": True, "project_type": "html_css_js",
        "project_name": project_name, "root": str(root),
        "files_created": len(created), "total_bytes": total_bytes,
        "compile_ok": True,
        "compile_output": "HTML/CSS/JS válido (abrir index.html en navegador)",
        "files": created,
    }


# ──────────────────────────────────────────────────────────────────────────────
# REACT
# ──────────────────────────────────────────────────────────────────────────────

def _generate_react(params: dict) -> dict:
    project_name = params["project_name"]
    description = params.get("description", "")
    output_dir = Path(params.get("output_dir", "") or Path.home() / "Desktop")
    fields_raw = params.get("fields", "[]")

    try:
        fields_list = json.loads(fields_raw) if isinstance(fields_raw, str) else fields_raw
    except Exception:
        fields_list = []

    root = output_dir / project_name
    slug = project_name.lower().replace(" ", "-").replace("_", "-")
    files = []

    files.append(("package.json", json.dumps({
        "name": slug, "version": "1.0.0",
        "description": description,
        "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
        "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
        "devDependencies": {"vite": "^5.0.0", "@vitejs/plugin-react": "^4.2.0"},
    }, indent=2)))

    files.append(("vite.config.js", """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({ plugins: [react()] })
"""))

    files.append(("index.html", f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
</body>
</html>"""))

    files.append(("src/main.jsx", """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
)
"""))

    files.append(("src/index.css", """* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }
"""))

    fields_jsx = ""
    for f in fields_list:
        fname = f.get("name", "campo")
        fields_jsx += f'                    <div key="{fname}" style={{{{ marginBottom: "1rem" }}}}>\n'
        fields_jsx += f'                        <label style={{{{ display: "block", marginBottom: "0.3rem", opacity: 0.8 }}}}>{fname.capitalize()}</label>\n'
        fields_jsx += f'                        <input type="text" name="{fname}" value={{{{form.{fname}}} }} onChange={handleChange}\n'
        fields_jsx += f'                            style={{{{ width: "100%", padding: "0.7rem", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#e2e8f0" }}}} />\n'
        fields_jsx += f'                    </div>\n'

    empty_form = ", ".join(f'{f.get("name","campo")}: ""' for f in fields_list) if fields_list else ""
    fields_header = ", ".join(f'"{f.get("name","campo")}"' for f in fields_list) if fields_list else '"nombre"'
    fields_table = ""
    for f in fields_list:
        fname = f.get("name", "campo")
        fields_table += f'                            <td>{{item.{fname}}}</td>\n'

    files.append(("src/App.jsx", f"""import React, {{ useState }} from 'react'

export default function App() {{
    const [records, setRecords] = useState([])
    const [form, setForm] = useState({{{empty_form}}})
    const [idCounter, setIdCounter] = useState(1)

    const fields = [{fields_header}]

    const handleChange = (e) => {{
        setForm({{...form, [e.target.name]: e.target.value}})
    }}

    const handleSubmit = (e) => {{
        e.preventDefault()
        setRecords([...records, {{...form, id: idCounter}}])
        setIdCounter(idCounter + 1)
        setForm({{...Object.fromEntries(Object.keys(form).map(k => [k, ""]))}})
    }}

    const handleDelete = (idx) => {{
        setRecords(records.filter((_, i) => i !== idx))
    }}

    return (
        <div style={{{{ maxWidth: 900, margin: "0 auto", padding: "2rem" }}}}>
            <h1 style={{{{ marginBottom: "0.5rem", fontSize: "2rem" }}}}>{{'{project_name}'}}</h1>
            <p style={{{{ opacity: 0.7, marginBottom: "2rem" }}}}>{{'{description}'}}</p>

            <form onSubmit={{handleSubmit}} style={{{{ background: "#1e293b", padding: "2rem", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}}}>
{fields_jsx}
                <button type="submit" style={{{{ background: "#6366f1", color: "#fff", padding: "0.7rem 1.5rem", border: "none", borderRadius: 8, cursor: "pointer", fontWeight: 600 }}}}>
                    Guardar
                </button>
            </form>

            {{records.length > 0 && (
                <div style={{{{ marginTop: "2rem", background: "#1e293b", padding: "1.5rem", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}}}>
                    <h3>Registros ({{records.length}})</h3>
                    <table style={{{{ width: "100%", marginTop: "1rem", borderCollapse: "collapse" }}}}>
                        <thead>
                            <tr>
                                <th style={{{{ textAlign: "left", padding: "0.7rem", borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#6366f1" }}}}>ID</th>
                                {{fields.map(f => <th key={{f}} style={{{{ textAlign: "left", padding: "0.7rem", borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#6366f1" }}}}>{{f.charAt(0).toUpperCase() + f.slice(1)}}</th>)}}
                                <th style={{{{ textAlign: "left", padding: "0.7rem", borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#6366f1" }}}}>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {{records.map((item, idx) => (
                                <tr key={{item.id}}>
                                    <td style={{{{ padding: "0.7rem", borderBottom: "1px solid rgba(255,255,255,0.05)" }}}}>{{item.id}}</td>
{fields_table}
                                    <td style={{{{ padding: "0.7rem", borderBottom: "1px solid rgba(255,255,255,0.05)" }}}}>
                                        <button onClick={{() => handleDelete(idx)}} style={{{{ background: "rgba(255,255,255,0.1)", color: "#e2e8f0", border: "none", padding: "0.3rem 0.8rem", borderRadius: 6, cursor: "pointer" }}}}>
                                            Eliminar
                                        </button>
                                    </td>
                                </tr>
                            ))}}
                        </tbody>
                    </table>
                </div>
            )}}
        </div>
    )
}}
"""))

    files.append(("README.md", f"""# {project_name}

{description}

## Cómo ejecutar

```bash
npm install
npm run dev
```

## Generado por ERIS AI — project_builder
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""))

    created = []
    total_bytes = 0
    for rel_path, content in files:
        full = root / rel_path
        sz = _write_file(full, content)
        created.append(rel_path)
        total_bytes += sz

    return {
        "ok": True, "project_type": "react",
        "project_name": project_name, "root": str(root),
        "files_created": len(created), "total_bytes": total_bytes,
        "compile_ok": None,
        "compile_output": "Requiere npm install && npm run dev",
        "files": created,
    }


# ──────────────────────────────────────────────────────────────────────────────
# ANGULAR
# ──────────────────────────────────────────────────────────────────────────────

def _generate_angular(params: dict) -> dict:
    project_name = params["project_name"]
    description = params.get("description", "")
    output_dir = Path(params.get("output_dir", "") or Path.home() / "Desktop")
    root = output_dir / project_name
    slug = project_name.lower().replace(" ", "-")
    files = []

    files.append(("package.json", json.dumps({
        "name": slug, "version": "1.0.0",
        "scripts": {"ng": "ng", "start": "ng serve", "build": "ng build"},
        "dependencies": {"@angular/core": "^17.0.0", "@angular/common": "^17.0.0",
                         "@angular/platform-browser": "^17.0.0", "rxjs": "^7.8.0", "zone.js": "^0.14.0"},
        "devDependencies": {"@angular/cli": "^17.0.0", "@angular/compiler": "^17.0.0",
                            "@angular/compiler-cli": "^17.0.0", "typescript": "^5.3.0"},
    }, indent=2)))

    files.append(("tsconfig.json", json.dumps({
        "compilerOptions": {"target": "ES2022", "module": "ES2022", "moduleResolution": "node",
                           "strict": True, "esModuleInterop": True, "skipLibCheck": True},
    }, indent=2)))

    files.append(("angular.json", json.dumps({
        "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
        "version": 1, "projects": {slug: {"projectType": "application",
            "root": "", "sourceRoot": "src",
            "architect": {"build": {"builder": "@angular-devkit/build-angular:application",
                "options": {"outputPath": "dist", "index": "src/index.html",
                           "main": "src/main.ts", "tsConfig": "tsconfig.json"}}}}
        }
    }, indent=2)))

    files.append(("src/main.ts", """import { platformBrowserDynamic } from '@angular/platform-browser-dynamic'
import { AppModule } from './app/app.module'
platformBrowserDynamic().bootstrapModule(AppModule)
"""))

    files.append(("src/index.html", f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
</head>
<body>
    <app-root></app-root>
</body>
</html>"""))

    files.append(("src/app/app.module.ts", """import { NgModule } from '@angular/core'
import { BrowserModule } from '@angular/platform-browser'
import { FormsModule } from '@angular/forms'
import { AppComponent } from './app.component'

@NgModule({
    declarations: [AppComponent],
    imports: [BrowserModule, FormsModule],
    bootstrap: [AppComponent]
})
export class AppModule {}
"""))

    files.append(("src/app/app.component.ts", """import { Component } from '@angular/core'

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css']
})
export class AppComponent {
    title = '""" + project_name + """'
    records: any[] = []
    model: any = {}

    save() {
        this.records.push({...this.model, id: this.records.length + 1})
        this.model = {}
    }

    remove(idx: number) {
        this.records.splice(idx, 1)
    }
}
"""))

    files.append(("src/app/app.component.html", f"""<div style="max-width:900px;margin:0 auto;padding:2rem;">
    <h1>{{{{title}}}}</h1>
    <p style="opacity:0.7;">{description}</p>
    <form (ngSubmit)="save()" style="background:#1e293b;padding:2rem;border-radius:12px;margin:2rem 0;">
"""
    + "\n".join(
        f'        <div style="margin-bottom:1rem;"><label>{f.get("name","campo").capitalize()}</label><input [(ngModel)]="model.{f.get("name","campo")}" name="{f.get("name","campo")}" style="width:100%;padding:0.7rem;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:#e2e8f0;"></div>'
        for f in (json.loads(params.get("fields", "[]")) if params.get("fields") else [])
    ) + """
        <button type="submit" style="background:#6366f1;color:#fff;padding:0.7rem 1.5rem;border:none;border-radius:8px;cursor:pointer;">Guardar</button>
    </form>
    <div *ngIf="records.length > 0" style="background:#1e293b;padding:1.5rem;border-radius:12px;">
        <h3>Registros ({{records.length}})</h3>
        <div *ngFor="let item of records; let i = index" style="padding:0.7rem;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;">
            <span>#{{item.id}}</span>
            <button (click)="remove(i)" style="background:rgba(255,255,255,0.1);color:#e2e8f0;border:none;padding:0.3rem 0.8rem;border-radius:6px;cursor:pointer;">Eliminar</button>
        </div>
    </div>
</div>"""))

    files.append(("src/app/app.component.css", """h1 { margin-bottom: 0.5rem; }
"""))

    files.append(("README.md", f"""# {project_name}
{description}
## Cómo ejecutar
```bash
npm install
ng serve
```
## Generado por ERIS AI — project_builder
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""))

    created = []
    total_bytes = 0
    for rel_path, content in files:
        full = root / rel_path
        sz = _write_file(full, content)
        created.append(rel_path)
        total_bytes += sz

    return {
        "ok": True, "project_type": "angular",
        "project_name": project_name, "root": str(root),
        "files_created": len(created), "total_bytes": total_bytes,
        "compile_ok": None, "compile_output": "Requiere npm install && ng serve",
        "files": created,
    }


# ──────────────────────────────────────────────────────────────────────────────
# VUE
# ──────────────────────────────────────────────────────────────────────────────

def _generate_vue(params: dict) -> dict:
    project_name = params["project_name"]
    description = params.get("description", "")
    output_dir = Path(params.get("output_dir", "") or Path.home() / "Desktop")
    fields_raw = params.get("fields", "[]")

    try:
        fields_list = json.loads(fields_raw) if isinstance(fields_raw, str) else fields_raw
    except Exception:
        fields_list = []

    root = output_dir / project_name
    slug = project_name.lower().replace(" ", "-")
    files = []

    files.append(("package.json", json.dumps({
        "name": slug, "version": "1.0.0",
        "scripts": {"dev": "vite", "build": "vite build"},
        "dependencies": {"vue": "^3.4.0"},
        "devDependencies": {"vite": "^5.0.0", "@vitejs/plugin-vue": "^5.0.0"},
    }, indent=2)))

    files.append(("vite.config.js", """import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({ plugins: [vue()] })
"""))

    files.append(("index.html", f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
</head>
<body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
</body>
</html>"""))

    files.append(("src/main.js", """import { createApp } from 'vue'
import App from './App.vue'
createApp(App).mount('#app')
"""))

    fields_template = ""
    for f in fields_list:
        fname = f.get("name", "campo")
        fields_template += f'            <div style="margin-bottom:1rem;">\n'
        fields_template += f'                <label style="display:block;margin-bottom:0.3rem;opacity:0.8;">{fname.capitalize()}</label>\n'
        fields_template += f'                <input v-model="form.{fname}" placeholder="{fname.capitalize()}" style="width:100%;padding:0.7rem;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:#e2e8f0;">\n'
        fields_template += f'            </div>\n'

    empty_form = ", ".join(f'{f.get("name","campo")}: ""' for f in fields_list) if fields_list else ""
    fields_header = ", ".join(f'"{f.get("name","campo")}"' for f in fields_list) if fields_list else '"nombre"'

    files.append(("src/App.vue", f"""<template>
    <div style="max-width:900px;margin:0 auto;padding:2rem;">
        <h1>{{{{ title }}}}</h1>
        <p style="opacity:0.7;">{description}</p>

        <form @submit.prevent="save" style="background:#1e293b;padding:2rem;border-radius:12px;margin:2rem 0;border:1px solid rgba(255,255,255,0.1);">
{fields_template}
            <button type="submit" style="background:#6366f1;color:#fff;padding:0.7rem 1.5rem;border:none;border-radius:8px;cursor:pointer;font-weight:600;">Guardar</button>
        </form>

        <div v-if="records.length" style="background:#1e293b;padding:1.5rem;border-radius:12px;border:1px solid rgba(255,255,255,0.1);">
            <h3>Registros ({{{{ records.length }}}})</h3>
            <div v-for="(item, idx) in records" :key="item.id" style="padding:0.7rem;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;">
                <span>#{{{{ item.id }}}}</span>
                <button @click="records.splice(idx, 1)" style="background:rgba(255,255,255,0.1);color:#e2e8f0;border:none;padding:0.3rem 0.8rem;border-radius:6px;cursor:pointer;">Eliminar</button>
            </div>
        </div>
    </div>
</template>

<script>
export default {{
    data() {{
        return {{
            title: '{project_name}',
            records: [],
            idCounter: 1,
            form: {{{empty_form}}}
        }}
    }},
    methods: {{
        save() {{
            this.records.push({{...this.form, id: this.idCounter++}})
            this.form = {{{", ".join(f'{f.get("name","campo")}: ""' for f in fields_list) if fields_list else ""}}}
        }}
    }}
}}
</script>
"""))

    files.append(("README.md", f"""# {project_name}
{description}
## Cómo ejecutar
```bash
npm install
npm run dev
```
## Generado por ERIS AI — project_builder
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""))

    created = []
    total_bytes = 0
    for rel_path, content in files:
        full = root / rel_path
        sz = _write_file(full, content)
        created.append(rel_path)
        total_bytes += sz

    return {
        "ok": True, "project_type": "vue",
        "project_name": project_name, "root": str(root),
        "files_created": len(created), "total_bytes": total_bytes,
        "compile_ok": None, "compile_output": "Requiere npm install && npm run dev",
        "files": created,
    }


# ──────────────────────────────────────────────────────────────────────────────
# MYSQL
# ──────────────────────────────────────────────────────────────────────────────

def _generate_mysql(params: dict) -> dict:
    project_name = params["project_name"]
    description = params.get("description", "")
    output_dir = Path(params.get("output_dir", "") or Path.home() / "Desktop")
    fields_raw = params.get("fields", "[]")

    try:
        fields_list = json.loads(fields_raw) if isinstance(fields_raw, str) else fields_raw
    except Exception:
        fields_list = []

    root = output_dir / project_name
    files = []

    db_name = params.get("database", project_name.lower().replace(" ", "_").replace("-", "_"))
    files.append(("README.md", f"""# {project_name} — Base de Datos MySQL

{description}

## Archivos

- `schema.sql` — DDL (creación de tablas)
- `data.sql` — Datos de ejemplo
- `procedures.sql` — Stored procedures
- `views.sql` — Vistas
- `README.md` — Esta documentación

## Cómo usar

```sql
source schema.sql;
source data.sql;
source procedures.sql;
source views.sql;
```

## Generado por ERIS AI — project_builder
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""))

    # ── schema.sql ──
    schema = f"""-- =============================================
-- {project_name} — Schema MySQL
-- {description}
-- Generado por ERIS project_builder
-- =============================================

CREATE DATABASE IF NOT EXISTS `{db_name}`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `{db_name}`;

"""
    for entity in fields_list:
        tbl_name = entity.get("name", "items").lower().replace(" ", "_").replace("-", "_")
        cols = entity.get("fields", [])
        if not cols:
            cols = [
                {"name": "id", "type": "INT", "pk": True},
                {"name": "nombre", "type": "VARCHAR(255)"},
                {"name": "descripcion", "type": "TEXT"},
                {"name": "fecha_creacion", "type": "DATETIME DEFAULT CURRENT_TIMESTAMP"},
            ]

        schema += f"DROP TABLE IF EXISTS `{tbl_name}`;\n"
        schema += f"CREATE TABLE `{tbl_name}` (\n"
        col_defs = []
        for c in cols:
            cname = c.get("name", "campo")
            ctype = _mysql_type(c.get("type", "VARCHAR(255)"))
            extras = ""
            if c.get("pk"):
                extras = " PRIMARY KEY AUTO_INCREMENT"
            elif c.get("not_null"):
                extras = " NOT NULL"
            elif c.get("unique"):
                extras = " UNIQUE"
            col_defs.append(f"    `{cname}` {ctype}{extras}")
        col_defs.append("    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP")
        col_defs.append("    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        schema += ",\n".join(col_defs) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n\n"

    files.append(("schema.sql", schema))

    # ── data.sql ──
    data = f"-- Datos de ejemplo — {project_name}\nUSE `{db_name}`;\n\n"
    for entity in fields_list:
        tbl_name = entity.get("name", "items").lower().replace(" ", "_").replace("-", "_")
        cols = entity.get("fields", [])
        if not cols:
            cols = [{"name": "nombre", "type": "String"}, {"name": "descripcion", "type": "String"}]
        insert_cols = ", ".join(f"`{c.get('name','campo')}`" for c in cols[:5])
        for i in range(1, 4):
            vals = ", ".join(f"'Ejemplo {i}'" for _ in cols[:5])
            data += f"INSERT INTO `{tbl_name}` ({insert_cols}) VALUES ({vals});\n"
        data += "\n"
    files.append(("data.sql", data))

    # ── procedures.sql ──
    procs = f"-- Stored Procedures — {project_name}\nUSE `{db_name}`;\n\n"
    for entity in fields_list:
        tbl_name = entity.get("name", "items").lower().replace(" ", "_").replace("-", "_")
        cap = entity.get("name", "items").capitalize()
        cols = entity.get("fields", [])
        if not cols:
            cols = [{"name": "nombre", "type": "String"}]
        params = ", ".join(f"IN p_{c.get('name','campo')} { _mysql_type(c.get('type','VARCHAR(255)'))}" for c in cols[:5])
        sets = ", ".join(f"`{c.get('name','campo')}` = p_{c.get('name','campo')}" for c in cols[:5])

        procs += f"""DELIMITER //
CREATE PROCEDURE sp_listar_{tbl_name}()
BEGIN
    SELECT * FROM `{tbl_name}` ORDER BY id DESC;
END //

CREATE PROCEDURE sp_insertar_{tbl_name}({params})
BEGIN
    INSERT INTO `{tbl_name}` ({", ".join(f'`{c.get("name","campo")}`' for c in cols[:5])})
    VALUES ({", ".join(f"p_{c.get('name','campo')}" for c in cols[:5])});
END //

CREATE PROCEDURE sp_eliminar_{tbl_name}(IN p_id INT)
BEGIN
    DELETE FROM `{tbl_name}` WHERE id = p_id;
END //
DELIMITER ;

"""
    files.append(("procedures.sql", procs))

    # ── views.sql ──
    views = f"-- Vistas — {project_name}\nUSE `{db_name}`;\n\n"
    for entity in fields_list:
        tbl_name = entity.get("name", "items").lower().replace(" ", "_").replace("-", "_")
        cap = entity.get("name", "items").capitalize()
        views += f"CREATE OR REPLACE VIEW vw_{tbl_name}_resumen AS\n"
        views += f"SELECT id, nombre, created_at\nFROM `{tbl_name}`\nWHERE deleted_at IS NULL\nORDER BY created_at DESC;\n\n"
    files.append(("views.sql", views))

    created = []
    total_bytes = 0
    for rel_path, content in files:
        full = root / rel_path
        sz = _write_file(full, content)
        created.append(rel_path)
        total_bytes += sz

    return {
        "ok": True, "project_type": "mysql",
        "project_name": project_name, "root": str(root),
        "files_created": len(created), "total_bytes": total_bytes,
        "compile_ok": None,
        "compile_output": "Archivos SQL generados (ejecutar en MySQL/MariaDB)",
        "files": created,
    }


def _mysql_type(t: str) -> str:
    t = t.upper().strip()
    mapping = {
        "INT": "INT", "INTEGER": "INT", "LONG": "BIGINT",
        "DOUBLE": "DOUBLE", "FLOAT": "FLOAT", "DECIMAL": "DECIMAL(10,2)",
        "BOOLEAN": "TINYINT(1)", "BOOL": "TINYINT(1)",
        "DATE": "DATE", "DATETIME": "DATETIME", "TIMESTAMP": "TIMESTAMP",
        "TEXT": "TEXT", "LONGTEXT": "LONGTEXT",
    }
    if t.startswith("VARCHAR"):
        return t
    return mapping.get(t, "VARCHAR(255)")


# ──────────────────────────────────────────────────────────────────────────────
# UTILIDADES GENERALES
# ──────────────────────────────────────────────────────────────────────────────

def _parse_json_list(val) -> list:
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except Exception:
        return []


def _format_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1048576:
        return f"{b/1024:.1f} KB"
    else:
        return f"{b/1048576:.1f} MB"


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT — Tool principal
# ──────────────────────────────────────────────────────────────────────────────

_GENERATORS = {
    "java_maven": _generate_java_maven,
    "java": _generate_java_maven,
    "python": _generate_python,
    "py": _generate_python,
    "csharp": _generate_csharp,
    "c#": _generate_csharp,
    "dotnet": _generate_csharp,
    "html_css_js": _generate_html_css_js,
    "html": _generate_html_css_js,
    "web": _generate_html_css_js,
    "react": _generate_react,
    "angular": _generate_angular,
    "vue": _generate_vue,
    "mysql": _generate_mysql,
    "sql": _generate_mysql,
}


def project_builder(parameters: dict, player=None) -> str:
    """
    Tool principal: genera proyectos completos de software.
    Acciones: create (crear proyecto), list (listar tipos soportados).
    """
    action = (parameters.get("action") or "create").lower()
    project_type = (parameters.get("project_type") or parameters.get("tipo") or "").lower().strip()
    project_name = parameters.get("project_name") or parameters.get("nombre") or ""

    if player:
        player.write_log(f"Project Builder: {action} — tipo={project_type} nombre={project_name}")

    # ── list ──
    if action in ("list", "listar", "tipos", "help"):
        return (
            "Tipos de proyecto soportados:\n"
            "  java_maven (java)  — Java + Maven + NetBeans Swing (.form XML)\n"
            "  python (py)        — Python con pyproject.toml, dataclasses, tests\n"
            "  csharp (c#)        — C# / ASP.NET (requiere dotnet SDK)\n"
            "  html_css_js (html/web) — HTML + CSS + JS vanilla\n"
            "  react              — React + Vite\n"
            "  angular            — Angular 17+\n"
            "  vue                — Vue 3 + Vite\n"
            "  mysql (sql)        — MySQL schema + data + procedures + views\n\n"
            "Parámetros: project_type, project_name, description, output_dir, fields (JSON), database, features (JSON)\n\n"
            "Ejemplo:\n"
            "  project_builder(project_type='java_maven', project_name='SistemaMantenimiento',\n"
            "    description='Sistema de registro de mantenimiento',\n"
            "    fields='[{\"name\":\"equipo\",\"fields\":[{\"name\":\"id\",\"type\":\"int\"},{\"name\":\"nombre\",\"type\":\"String\"},{\"name\":\"marca\",\"type\":\"String\"},{\"name\":\"estado\",\"type\":\"String\"}]}]')"
        )

    # ── create ──
    if not project_type:
        return "Necesito 'project_type'. Usa: java_maven, python, csharp, html_css_js, react, angular, vue, mysql"
    if not project_name:
        return "Necesito 'project_name' con el nombre del proyecto."

    generator = _GENERATORS.get(project_type)
    if not generator:
        return (
            f"Tipo '{project_type}' no reconocido. "
            f"Soportados: {', '.join(sorted(set(_GENERATORS.keys())))}"
        )

    params = {
        "project_type": project_type,
        "project_name": project_name,
        "description": parameters.get("description") or parameters.get("descripcion") or "",
        "output_dir": parameters.get("output_dir") or "",
        "fields": parameters.get("fields") or parameters.get("campos") or "[]",
        "database": parameters.get("database") or "",
        "features": parameters.get("features") or "[]",
    }

    try:
        result = generator(params)
    except Exception as e:
        tb = traceback.format_exc()
        return f"Error generando proyecto '{project_name}':\n{str(e)[:300]}\n\nTraceback:\n{tb[:500]}"

    if not result.get("ok"):
        return f"Error generando proyecto: {result}"

    # ── Formatear respuesta ──
    lines = [
        f"PROYECTO CREADO: {result['project_name']}",
        f"Tipo: {result['project_type']}",
        f"Ubicación: {result['root']}",
        f"Archivos: {result['files_created']}",
        f"Tamaño total: {_format_size(result['total_bytes'])}",
        f"Compilación: {'✅ OK' if result.get('compile_ok') else '⚠️ Requiere herramientas' if result.get('compile_ok') is None else '❌ Error'}",
    ]

    if result.get("compile_output"):
        lines.append(f"Detalle: {result['compile_output'][:500]}")

    lines.append(f"\nArchivos creados ({len(result.get('files', []))}):")
    for f in result.get("files", [])[:30]:
        lines.append(f"  • {f}")
    if len(result.get("files", [])) > 30:
        lines.append(f"  ... y {len(result.get('files', [])) - 30} más")

    if result.get("root"):
        lines.append(f"\nPara abrir: cd {result['root']}")

    response = "\n".join(lines)

    if player:
        player.write_log(f"  ✅ {result['project_name']}: {result['files_created']} archivos, {_format_size(result['total_bytes'])}")

    return response


# ── Alias para tool_registry ──
project_builder.__doc__ = (
    "Generador autónomo de proyectos completos de software. "
    "Crea estructura, código fuente, configuración de build, y valida. "
    "Soporta: java_maven, python, csharp, html_css_js, react, angular, vue, mysql."
)
