# -*- coding: utf-8 -*-
"""
code_copilot.py — Asistente de código IA de ERIS.

Usa core.model_router.quick_chat (gemini -> groq -> openrouter -> ollama) y
edición QUIRÚRGICA: corrige/agrega SOLO lo necesario, con backup.

Acciones:
  new        Generar código/proyecto en cualquier lenguaje (java, html, css,
             javascript, python, c#, c++, react, angular, vue, bootstrap,
             mysql, php, typescript, go, rust, ...).
  fix        Corregir un error tocando SOLO las líneas necesarias.
  add        Agregar código a un archivo existente en el punto correcto.
  locate     Encontrar dónde están los problemas/errores.
  analyze    Análisis completo de un archivo o proyecto.
  structure  Organizar/estructurar un proyecto en carpetas (dry-run default).
  organize   Mover archivos a carpetas según su tipo.
  rename     Renombrar archivos (opcional: actualizar referencias).
  languages  Listar lenguajes soportados.
  knowledge  Mostrar convenciones/patrones de un lenguaje.
"""
import json
import os
import re
import shutil
import time
import traceback
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"

LANGUAGES = {
    "python":     {"ext": ".py",   "aliases": ["py"]},
    "javascript": {"ext": ".js",   "aliases": ["js", "node", "nodejs"]},
    "typescript": {"ext": ".ts",   "aliases": ["ts"]},
    "html":       {"ext": ".html", "aliases": ["html5"]},
    "css":        {"ext": ".css",  "aliases": ["scss", "sass"]},
    "java":       {"ext": ".java", "aliases": []},
    "csharp":     {"ext": ".cs",   "aliases": ["c#", "csharp", ".net", "dotnet"]},
    "cpp":        {"ext": ".cpp",  "aliases": ["c++", "cplusplus"]},
    "react":      {"ext": ".jsx",  "aliases": ["react.js", "reactjs", "jsx", "reactjsx"]},
    "reactts":    {"ext": ".tsx",  "aliases": ["react ts", "reactts", "tsx"]},
    "angular":    {"ext": ".ts",   "aliases": []},
    "vue":        {"ext": ".vue",  "aliases": ["vuejs"]},
    "php":        {"ext": ".php",  "aliases": []},
    "mysql":      {"ext": ".sql",  "aliases": ["sql", "mariadb", "database", "db"]},
    "go":         {"ext": ".go",   "aliases": ["golang"]},
    "rust":       {"ext": ".rs",   "aliases": []},
    "bash":       {"ext": ".sh",   "aliases": ["shell", "zsh"]},
    "json":       {"ext": ".json", "aliases": []},
    "yaml":       {"ext": ".yaml", "aliases": ["yml"]},
    "markdown":   {"ext": ".md",   "aliases": ["md", "readme"]},
}

# ── Base de conocimiento por lenguaje (convenciones + esqueleto base) ──
KNOWLEDGE = {
    "java": {
        "conv": ("Paquete en minúsculas (com.example). Clases PascalCase, métodos "
                 "camelCase, constantes UPPER_SNAKE. Un archivo público por clase. "
                 "Extensión .java. Build con javac/maven/gradle."),
        "skeleton": "public class Main {\n    public static void main(String[] args) {\n        // código\n    }\n}\n",
    },
    "csharp": {
        "conv": ("Namespaces PascalCase. Clases/métodos PascalCase, campos privados "
                 "_camelCase. Framework .NET. Extensión .cs. Build con dotnet build."),
        "skeleton": "using System;\n\nclass Program\n{\n    static void Main(string[] args)\n    {\n        Console.WriteLine(\"Hola\");\n    }\n}\n",
    },
    "cpp": {
        "conv": ("Headers .h/.hpp, fuentes .cpp. std:: por convención. Clases "
                 "PascalCase, métodos camelCase, includes al inicio. Compilar con g++."),
        "skeleton": "#include <iostream>\n\nint main() {\n    std::cout << \"Hola\" << std::endl;\n    return 0;\n}\n",
    },
    "javascript": {
        "conv": ("camelCase para variables/funciones, PascalCase para clases. "
                 "const/let (no var). ; al final de sentencia. ESM o CommonJS consistente."),
        "skeleton": "function main() {\n    console.log('Hola');\n}\n\nmain();\n",
    },
    "typescript": {
        "conv": ("Tipado estricto. Interfaces PascalCase (prefijo I opcional). "
                 "Enum PascalCase. Evitar any. Compilar con tsc/tsx."),
        "skeleton": "interface Usuario {\n  nombre: string;\n  edad: number;\n}\n\nfunction main(): void {\n  console.log('Hola');\n}\n\nmain();\n",
    },
    "react": {
        "conv": ("Componentes funcionales con hooks. Componente PascalCase. "
                 "JSX en .jsx/.tsx. Estado con useState, efectos con useEffect. "
                 "Estilos con CSS modules o Tailwind/Bootstrap."),
        "skeleton": "import React, { useState } from 'react';\n\nexport default function App() {\n  const [count, setCount] = useState(0);\n  return (\n    <div>\n      <h1>Hola</h1>\n      <button onClick={() => setCount(count + 1)}>{count}</button>\n    </div>\n  );\n}\n",
    },
    "angular": {
        "conv": ("Proyecto con Angular CLI (ng new). Componentes con decorador "
                 "@Component, módulos, servicios inyectables, RxJS. archivo .ts."),
        "skeleton": "import { Component } from '@angular/core';\n\n@Component({\n  selector: 'app-root',\n  templateUrl: './app.component.html',\n  styleUrls: ['./app.component.css']\n})\nexport class AppComponent {\n  title = 'Hola';\n}\n",
    },
    "vue": {
        "conv": ("SFC: <template>, <script setup>, <style scoped>. Opciones o "
                 "Composition API. Props definidos, eventos con emit."),
        "skeleton": "<template>\n  <div>\n    <h1>Hola</h1>\n    <button @click=\"count++\">{{ count }}</button>\n  </div>\n</template>\n\n<script setup>\nimport { ref } from 'vue';\nconst count = ref(0);\n</script>\n",
    },
    "html": {
        "conv": ("DOCTYPE + lang. Meta charset/viewport. Semántica: header, nav, "
                 "main, section, footer. Bootstrap 5 vía CDN si se usa. Accesibilidad."),
        "skeleton": "<!DOCTYPE html>\n<html lang=\"es\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n  <title>Título</title>\n  <style>\n    * { margin: 0; padding: 0; box-sizing: border-box; }\n    body { font-family: 'Segoe UI', sans-serif; line-height: 1.6; color: #222; }\n    header { background: linear-gradient(135deg, #7c3aed, #2563eb); color: #fff; padding: 80px 20px; text-align: center; }\n    header h1 { font-size: 2.8em; margin-bottom: 10px; }\n    nav { position: sticky; top: 0; background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,.1); display: flex; gap: 20px; padding: 14px 24px; justify-content: center; }\n    nav a { color: #7c3aed; text-decoration: none; font-weight: 600; }\n    section { max-width: 900px; margin: 40px auto; padding: 0 20px; }\n    h2 { color: #7c3aed; margin-bottom: 12px; }\n    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-top: 20px; }\n    .card { border: 1px solid #eee; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.06); }\n    footer { text-align: center; padding: 30px; color: #888; }\n  </style>\n</head>\n<body>\n  <header>\n    <h1>Título</h1>\n    <p>Subtítulo o propuesta de valor</p>\n  </header>\n  <nav>\n    <a href=\"#inicio\">Inicio</a>\n    <a href=\"#servicios\">Servicios</a>\n    <a href=\"#contacto\">Contacto</a>\n  </nav>\n  <main>\n    <section id=\"inicio\">\n      <h2>Bienvenido</h2>\n      <p>Descripción breve del sitio o negocio.</p>\n    </section>\n    <section id=\"servicios\">\n      <h2>Servicios</h2>\n      <div class=\"cards\">\n        <div class=\"card\"><h3>Servicio 1</h3><p>Detalle del servicio.</p></div>\n        <div class=\"card\"><h3>Servicio 2</h3><p>Detalle del servicio.</p></div>\n        <div class=\"card\"><h3>Servicio 3</h3><p>Detalle del servicio.</p></div>\n      </div>\n    </section>\n    <section id=\"contacto\">\n      <h2>Contacto</h2>\n      <p>Email: contacto@ejemplo.com</p>\n    </section>\n  </main>\n  <footer>&copy; 2026 Título. Todos los derechos reservados.</footer>\n</body>\n</html>\n",
    },
    "css": {
        "conv": ("Selectores de clase .kebab-case. Variables con :root { --color }."
                 "Responsive con media queries. Mobile-first."),
        "skeleton": ":root {\n  --primario: #7c3aed;\n}\n\n* { margin: 0; padding: 0; box-sizing: border-box; }\n",
    },
    "php": {
        "conv": ("PHP moderno (>=8): tipos, match, named args. Clases PSR-4. "
                 "Conexión MySQL con PDO y prepared statements (nunca mysqli sin escapar)."),
        "skeleton": "<?php\ndeclare(strict_types=1);\n\necho \"Hola\\n\";\n",
    },
    "mysql": {
        "conv": ("Tablas snake_case, PK id INT UNSIGNED AUTO_INCREMENT, FK con "
                 "ON DELETE. InnoDB + utf8mb4. Índices para columnas de filtro."),
        "skeleton": "CREATE TABLE usuarios (\n  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,\n  nombre VARCHAR(100) NOT NULL,\n  email VARCHAR(255) UNIQUE NOT NULL\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n",
    },
    "go": {
        "conv": ("gofmt. Exportado = Mayúscula. Errores explícitos (if err != nil)."
                 " Módulos con go.mod. paquetes en minúscula."),
        "skeleton": "package main\n\nimport \"fmt\"\n\nfunc main() {\n\tfmt.Println(\"Hola\")\n}\n",
    },
    "rust": {
        "conv": ("snake_case funciones/vars, PascalCase tipos. cargo new. "
                 "Errores con Result. Sin punteros nulos."),
        "skeleton": "fn main() {\n    println!(\"Hola\");\n}\n",
    },
    "python": {
        "conv": ("PEP 8: snake_case, 4 espacios, clases PascalCase. Type hints. "
                 "docstrings. main() guardado por __name__."),
        "skeleton": "def main():\n    print('Hola')\n\n\nif __name__ == '__main__':\n    main()\n",
    },
}


def code_copilot(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "languages").lower().strip()
    try:
        if action == "new":
            return _new(parameters, player)
        if action == "fix":
            return _fix(parameters, player)
        if action == "add":
            return _add(parameters, player)
        if action == "locate":
            return _locate(parameters, player)
        if action == "analyze":
            return _analyze(parameters, player)
        if action == "structure":
            return _structure(parameters, player)
        if action == "organize":
            return _organize(parameters, player)
        if action == "rename":
            return _rename(parameters, player)
        if action == "languages":
            return _languages()
        if action == "knowledge":
            return _knowledge(parameters)
    except Exception as e:
        return "Error en code_copilot: {}\n{}".format(e, traceback.format_exc(limit=2))
    return ("Acción '{}' desconocida. Usá: new, fix, add, locate, analyze, "
            "structure, organize, rename, languages, knowledge").format(action)


# ─────────────────────────── helpers ───────────────────────────

def _norm_lang(lang):
    lang = (lang or "python").lower().strip()
    if lang in LANGUAGES:
        return lang
    for k, v in LANGUAGES.items():
        if lang in v["aliases"]:
            return k
    for k, v in LANGUAGES.items():
        if "." + lang == v["ext"] or v["ext"] == lang:
            return k
    return "python"


def _log(player, msg):
    try:
        if player:
            player.write_log(msg)
    except Exception:
        pass


def _ai(prompt, system, retries=2, timeout=120):
    from core.model_router import quick_chat
    last = None
    for _ in range(retries):
        try:
            out = quick_chat(prompt, system=system, task="agent")
            if out and out.strip():
                return out.strip()
        except Exception as e:
            last = e
            time.sleep(0.5)
    if last is not None:
        return None
    return None


def _extract_json(text):
    """Extrae el primer bloque JSON balanceado de la respuesta del LLM."""
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = text.find("{")
    if start == -1:
        start = text.find("[")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
            if depth == 0:
                cand = text[start:i + 1]
                try:
                    return json.loads(cand)
                except Exception:
                    break
    return None


def _read_file(path: Path, cap=60000):
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None, "No se pudo leer el archivo: {}".format(path)
    if len(content) > cap:
        return content[:cap], "Archivo mayor a {} caracteres: se usó un fragmento inicial.".format(cap)
    return content, None


def _backup(path: Path):
    try:
        bak = str(path) + ".copilot.bak"
        shutil.copy2(str(path), bak)
        return bak
    except Exception:
        return None


def _strip_numbers(text):
    """Si el LLM copió los prefijos 'N| ' (de los números de línea de referencia),
    los elimina para quedarse con el texto real del archivo."""
    lines = text.split("\n")
    stripped = []
    any_stripped = False
    for ln in lines:
        m = re.match(r"^\s*\d+\|\s?", ln)
        if m:
            any_stripped = True
            stripped.append(ln[m.end():])
        else:
            stripped.append(ln)
    if any_stripped:
        return "\n".join(stripped)
    return text


def _apply_patches(content, patches):
    """Aplica parches quirúrgicos (old exacto -> new). Devuelve (content, report)."""
    report = []
    if not patches:
        return content, ["No se aplicó ningún cambio (sin parches)."]
    for i, p in enumerate(patches, 1):
        old = _strip_numbers((p.get("old") or "").rstrip("\n"))
        new = _strip_numbers((p.get("new") or "").rstrip("\n"))
        if not old:
            report.append("  ✗ patch {}: 'old' vacío".format(i))
            continue
        if old not in content:
            report.append("  ✗ patch {}: no se encontró el texto exacto ({!r})".format(i, old[:60]))
            continue
        count = content.count(old)
        if count > 1:
            report.append("  ✗ patch {}: 'old' aparece {} veces; agregá más contexto".format(i, count))
            continue
        content = content.replace(old, new, 1)
        report.append("  ✓ patch {}: {} línea(s) → {} línea(s)".format(
            i, old.count("\n") + 1, new.count("\n") + 1))
    return content, report


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ─────────────────────────── acciones ───────────────────────────

def _languages():
    lines = ["Lenguajes soportados por code_copilot ({})".format(len(LANGUAGES)), ""]
    for k, v in LANGUAGES.items():
        lines.append("  {:<12} ext: {}".format(k, v["ext"]))
    lines.append("")
    lines.append("Acciones: new, fix, add, locate, analyze, structure, organize, "
                 "rename, languages, knowledge")
    return "\n".join(lines)


def _knowledge(parameters):
    lang = _norm_lang(parameters.get("language", ""))
    if lang in KNOWLEDGE:
        e = KNOWLEDGE[lang]
        return "Lenguaje: {}\n\nConvenciones:\n{}\n\nEsqueleto base:\n{}".format(
            lang, e["conv"], e["skeleton"])
    return "No hay conocimiento específico para '{}'. Usá action=languages para ver los soportados.".format(lang)


SYSTEM_NEW = """Eres ERIS, una programadora senior experta en TODOS los lenguajes. Generás código de alta calidad, bien estructurado y con buenas prácticas.

REGLAS:
1. Código completo, funcional, con comentarios mínimos y claros.
2. Seguí las convenciones del lenguaje (naming, estructura, imports).
3. Para proyectos: separá en archivos lógicos (componentes, estilos, servicios, base de datos, etc.).
4. No inventes librerías: usá las estándar o las que se indiquen.
5. Respondé ÚNICAMENTE JSON válido sin markdown:
{"files":[{"path":"relativo/carpeta/archivo.ext","code":"..."}],"summary":"breve descripción"}
"""


def _new(parameters, player):
    lang = _norm_lang(parameters.get("language", "python"))
    description = parameters.get("description") or parameters.get("text") or ""
    filename = (parameters.get("filename") or "").strip()
    output_dir = (parameters.get("output_dir") or parameters.get("output_path") or "").strip()
    if not description:
        return "Error: se requiere 'description' con lo que querés generar."
    conv = KNOWLEDGE.get(lang, {}).get("conv", "")
    prompt = "Lenguaje: {}\nConvenciones: {}\nDescripción: {}\n".format(lang, conv, description)
    if filename:
        prompt += "Archivo único: {}\n".format(filename)
    prompt += "\nGenerá el código/proyecto."
    _log(player, "🛠️ code_copilot: generando {} ({})...".format(lang, description[:40]))
    out = _ai(prompt, SYSTEM_NEW)
    if not out:
        return "Error: la IA no respondió (¿API sin crédito?)."
    data = _extract_json(out)
    if not data or not data.get("files"):
        return "La IA no devolvió un JSON de archivos válido."
    files = data.get("files", [])
    if not files:
        return "La IA no devolvió archivos."
    base = Path(output_dir) if output_dir else BASE / "data" / "generated_projects"
    if not output_dir:
        base = base / (filename and Path(filename).stem or re.sub(r"[^a-z0-9]+", "_", description.lower())[:40])
    created = []
    for f in files:
        rel = str(f.get("path", "")).strip() or "archivo" + LANGUAGES[lang]["ext"]
        code = f.get("code", "")
        if not rel.endswith(tuple(LANGUAGES[lang]["ext"])) and "/" not in rel and "." not in Path(rel).name:
            rel += LANGUAGES[lang]["ext"]
        p = (base / rel)
        _write(p, code)
        created.append(str(p.relative_to(BASE) if str(base).startswith(str(BASE)) else p))
    summary = data.get("summary", "")
    head = "Proyecto '{}' generado ({} archivos):\n".format(summary or description[:40], len(created))
    return head + "\n".join("  " + c for c in created) + "\n\nBase: {}".format(base)


SYSTEM_FIX = """Eres ERIS, programadora senior. Tu tarea es EDICIÓN QUIRÚRGICA: corregir SOLO el problema indicado sin tocar nada más del archivo.

REGLAS OBLIGATORIAS:
1. Cambiá ÚNICAMENTE las líneas mínimas necesarias. NO reformatees, NO renombres, NO reescribas código que funciona, NO "mejores" el estilo.
2. "old" debe ser COPIA EXACTA del archivo actual (misma indentación, mismas comillas, mismo espaciado). LOS NÚMEROS DE LÍNEA (formato "N| ") son SOLO referencia para vos: NUNCA los copies dentro de "old" ni "new".
3. "old" debe aparecer EXACTAMENTE UNA vez; si hay ambigüedad, incluí más líneas de contexto.
4. Preservá la indentación original. Si cambiás una línea, "new" lleva el MISMO nivel de indentación que "old".
5. Si el error indica una línea (ej. "line 42"), apuntá a esa línea o a la lógica adyacente, no a otra.
6. Respondé ÚNICAMENTE JSON sin markdown:
{"patches":[{"old":"...","new":"..."}]}
Si el archivo ya está correcto: {"patches":[]}."""


def _fix(parameters, player):
    fp = (parameters.get("file_path") or parameters.get("path") or "").strip()
    error = (parameters.get("error") or parameters.get("description") or parameters.get("issue") or "").strip()
    if not fp:
        return "Error: se requiere 'file_path' del archivo a corregir."
    path = Path(fp)
    if not path.exists():
        return "Error: no existe el archivo '{}'.".format(fp)
    content, warn = _read_file(path)
    if content is None:
        return warn
    if not error:
        return ("Error: se requiere 'error' (mensaje de error o descripción de lo que "
                "falla). Para encontrar el error automáticamente usá action=locate.")
    line_hint = parameters.get("line")
    m = re.search(r"\bline\s+(\d+)", error, re.IGNORECASE)
    if m and not line_hint:
        line_hint = m.group(1)
    _log(player, "🛠️ code_copilot: corrigiendo {}...".format(path.name))
    numbered = []
    for i, l in enumerate(content.split("\n"), 1):
        numbered.append("{:5d}| {}".format(i, l))
    numbered_src = "\n".join(numbered)
    prompt = (
        "ARCHIVO (con números de línea):\n```\n{}\n```\n\n"
        "ERROR/ISSUE A CORREGIR: {}\n".format(numbered_src, error)
    )
    if line_hint:
        prompt += "Pista: el problema está cerca de la línea {}.\n".format(line_hint)
    prompt += "\nProducí los parches quirúrgicos."
    out = _ai(prompt, SYSTEM_FIX)
    if not out:
        return "Error: la IA no respondió."
    data = _extract_json(out)
    if data is None:
        return "La IA no devolvió JSON válido. Respuesta:\n" + out[:500]
    patches = data.get("patches", [])
    if not patches:
        return "La IA determinó que el archivo ya está correcto (sin parches)."
    bak = _backup(path)
    new_content, report = _apply_patches(content, patches)
    if not any(r.startswith("  ✓") for r in report):
        return "No se pudo aplicar ningún cambio.\n" + "\n".join(report)
    _write(path, new_content)
    lines_before = content.count("\n") + 1
    lines_after = new_content.count("\n") + 1
    head = ("✅ Corregido '{}' ({} → {} líneas; {} parche(s) aplicado(s)). "
            "Backup: {}").format(path.name, lines_before, lines_after, sum(1 for r in report if r.startswith("  ✓")), bak)
    return head + "\n" + "\n".join(report) + (("\nNota: " + warn) if warn else "")


SYSTEM_ADD = """Eres ERIS, programadora senior. Agregás código a un archivo EXISTENTE en el punto correcto, sin tocar el resto.

REGLAS:
1. El código nuevo va donde corresponde estructuralmente: imports arriba, funciones después de las dependencias que usan, métodos dentro de su clase, lógica donde se usa.
2. "anchor" debe ser COPIA EXACTA de una o más líneas existentes del archivo (para ubicar el punto). LOS NÚMEROS DE LÍNEA (formato "N| ") son SOLO referencia: NUNCA los copies dentro de "anchor" ni "new_code".
3. "position": "after" (insertar después del anchor) o "before".
4. "new_code" con la MISMA indentación que el contexto.
5. Respondé ÚNICAMENTE JSON sin markdown:
{"anchor":"...","position":"after","new_code":"..."}"""


def _add(parameters, player):
    fp = (parameters.get("file_path") or parameters.get("path") or "").strip()
    description = (parameters.get("description") or parameters.get("text") or "").strip()
    lang = _norm_lang(parameters.get("language", ""))
    if not fp:
        return "Error: se requiere 'file_path'."
    if not description:
        return "Error: se requiere 'description' (qué código agregar)."
    path = Path(fp)
    if not path.exists():
        return "Error: no existe '{}'.".format(fp)
    content, warn = _read_file(path)
    if content is None:
        return warn
    conv = KNOWLEDGE.get(lang, {}).get("conv", "")
    _log(player, "🛠️ code_copilot: agregando a {}...".format(path.name))
    numbered = "\n".join("{:5d}| {}".format(i, l) for i, l in enumerate(content.split("\n"), 1))
    prompt = ("ARCHIVO ACTUAL (con números):\n```\n{}\n```\n\n"
              "AGREGAR: {}\nLenguaje: {}\nConvenciones: {}\n"
              "Determiná el punto correcto y producí el JSON.").format(
                  numbered, description, lang, conv)
    out = _ai(prompt, SYSTEM_ADD)
    if not out:
        return "Error: la IA no respondió."
    data = _extract_json(out)
    if not data or "anchor" not in data:
        return "La IA no devolvió JSON válido: " + (out[:400])
    anchor = _strip_numbers((data.get("anchor") or "").rstrip("\n"))
    new_code = (data.get("new_code") or "").rstrip("\n")
    position = (data.get("position") or "after").lower()
    if not anchor:
        return "Error: la IA no devolvió 'anchor'."
    if not new_code:
        return "Error: la IA no devolvió 'new_code'."
    idx = content.find(anchor)
    if idx == -1:
        return "No se encontró el anchor exacto ({!r}). Reintentá con más contexto.".format(anchor[:60])
    if content.count(anchor) > 1:
        return "El anchor aparece varias veces; la IA debe incluir más contexto."
    end = idx + len(anchor)
    if position == "before":
        new_content = content[:idx] + new_code + "\n" + content[idx:]
    else:
        new_content = content[:end] + "\n" + new_code + "\n" + content[end:].lstrip("\n")
    bak = _backup(path)
    _write(path, new_content)
    lines_before = content.count("\n") + 1
    lines_after = new_content.count("\n") + 1
    return ("✅ Código agregado a '{}' ({} → {} líneas). Backup: {}\n"
            "Anchor: {!r}\nPosición: {}").format(path.name, lines_before, lines_after, bak, anchor[:60], position)


SYSTEM_LOCATE = """Eres ERIS, debugger senior. Analizás el código y localizás los problemas exactos.

REGLAS:
1. Indicá ARCHIVO y LÍNEA de cada problema (los números de línea ya están en el código provisto).
2. Solo diagnóstico y sugerencias, NO modifiques código.
3. Respondé ÚNICAMENTE JSON sin markdown:
{"findings":[{"file":"...","line":N,"issue":"...","suggestion":"..."}]}
Si no hay problemas: {"findings":[]}."""


def _locate(parameters, player):
    path = Path(parameters.get("path") or parameters.get("file_path") or ".")
    issue = (parameters.get("issue") or parameters.get("description") or "").strip()
    if path.is_file():
        contents = [path]
    elif path.is_dir():
        exts = set(v["ext"] for v in LANGUAGES.values()) | {".css"}
        skip = {".venv", "node_modules", ".git", "__pycache__", "build", "dist", ".idea", "data"}
        contents = sorted(
            p for p in path.rglob("*")
            if p.is_file() and p.suffix in exts
            and not any(part in skip for part in p.parts))
        if not contents:
            return "No se encontraron archivos de código en '{}'.".format(path)
    else:
        return "No existe '{}'.".format(path)
    _log(player, "🛠️ code_copilot: localizando problemas en {}...".format(path))
    files_text = []
    for p in contents[:12]:
        c, _ = _read_file(p, cap=25000)
        if c is None:
            continue
        files_text.append("=== {} ===\n{}".format(p, c))
    prompt = "PROYECTO:\n\n" + "\n\n".join(files_text) + "\n"
    if issue:
        prompt += "\nBuscar específicamente: {}\n".format(issue)
    prompt += "\nLocalizá los problemas."
    out = _ai(prompt, SYSTEM_LOCATE)
    if not out:
        return "Error: la IA no respondió."
    data = _extract_json(out)
    if data is None:
        return "La IA no devolvió JSON válido: " + (out[:400])
    findings = data.get("findings", [])
    if not findings:
        return "✅ No se encontraron problemas en '{}'.".format(path)
    lines = ["🔍 {} hallazgo(s) en '{}':".format(len(findings), path), ""]
    for f in findings:
        lines.append("• {}:{} — {}".format(f.get("file", "?"), f.get("line", "?"), f.get("issue", "")))
        if f.get("suggestion"):
            lines.append("    → {}".format(f["suggestion"]))
    return "\n".join(lines)


SYSTEM_ANALYZE = """Eres ERIS, arquitecta de software. Analizás un archivo o proyecto y das un informe claro y accionable. Respondé en español, conciso pero completo."""


def _analyze(parameters, player):
    path = Path(parameters.get("path") or parameters.get("file_path") or ".")
    if path.is_file():
        c, warn = _read_file(path)
        if c is None:
            return warn
        src = "=== {} ===\n{}".format(path, c)
    elif path.is_dir():
        exts = set(v["ext"] for v in LANGUAGES.values()) | {".css"}
        skip = {".venv", "node_modules", ".git", "__pycache__", "build", "dist", ".idea", "data"}
        files = sorted(p for p in path.rglob("*") if p.is_file() and p.suffix in exts and not any(part in skip for part in p.parts))[:15]
        if not files:
            return "No se encontraron archivos de código en '{}'.".format(path)
        parts = []
        for p in files:
            c, _ = _read_file(p, cap=20000)
            if c is not None:
                parts.append("=== {} ===\n{}".format(p, c))
        src = "\n\n".join(parts)
    else:
        return "No existe '{}'.".format(path)
    _log(player, "🛠️ code_copilot: analizando {}...".format(path))
    prompt = ("Analizá en profundidad:\n\n" + src + "\n\n"
              "Informe: arquitectura, problemas, riesgos, mejoras concretas (con "
              "archivo:línea cuando aplique). No modifiques nada.")
    out = _ai(prompt, SYSTEM_ANALYZE)
    if not out:
        return "Error: la IA no respondió."
    return "📊 Análisis de {}:\n\n{}".format(path, out)


SYSTEM_STRUCTURE = """Eres ERIS, arquitecta de proyectos. Proponés una estructura de carpetas estándar y organizada para un proyecto de software.

REGLAS:
1. Proponé rutas 'from' → 'to' (mover), renames, y carpetas a crear.
2. No muevas archivos de configuración sensibles (.env, keys) ni .git.
3. Usá estructura estándar según el lenguaje (src/, components/, styles/, services/, templates/, public/, etc.).
4. Respondé ÚNICAMENTE JSON sin markdown:
{"moves":[{"from":"...","to":"..."}],"renames":[{"from":"...","to":"..."}],"creates":["src","components"]}"""


def _structure(parameters, player):
    path = Path(parameters.get("path") or parameters.get("file_path") or ".")
    if not path.is_dir():
        return "Error: 'structure' requiere una carpeta de proyecto (path)."
    apply = str(parameters.get("apply", "false")).lower() in ("1", "true", "yes", "si", "aplicar")
    skip = {".venv", "node_modules", ".git", "__pycache__", "build", "dist", ".idea", "data", "backups"}
    entries = sorted(
        p for p in path.rglob("*")
        if p.is_file()
        and not any(part in skip for part in p.parts)
        and not str(p).endswith(".copilot.bak"))
    if not entries:
        return "No hay archivos para estructurar en '{}'.".format(path)
    tree = []
    for p in entries[:120]:
        tree.append(str(p.relative_to(path)))
    _log(player, "🛠️ code_copilot: estructurando {}...".format(path))
    prompt = ("PROYECTO ACTUAL (rutas relativas):\n" + "\n".join(tree) +
              "\n\nProponé la reorganización.")
    out = _ai(prompt, SYSTEM_STRUCTURE)
    if not out:
        return "Error: la IA no respondió."
    data = _extract_json(out)
    if data is None:
        return "La IA no devolvió JSON válido: " + (out[:400])
    report = ["📁 Estructura propuesta para '{}':".format(path)]
    moves = data.get("moves", []) or []
    renames = data.get("renames", []) or []
    creates = data.get("creates", []) or []
    for c in creates:
        report.append("  + crear carpeta: {}".format(c))
        if apply:
            (path / c).mkdir(parents=True, exist_ok=True)
    for m in moves:
        frm, to = m.get("from"), m.get("to")
        if not frm or not to:
            continue
        report.append("  → mover: {} → {}".format(frm, to))
        if apply:
            _safe_move(path / frm, path / to)
    for r in renames:
        frm, to = r.get("from"), r.get("to")
        if not frm or not to:
            continue
        report.append("  ⇄ renombrar: {} → {}".format(frm, to))
        if apply:
            _safe_move(path / frm, path / to)
    report.append("")
    report.append("Modo: {}APLICADO{}".format("✅ " if apply else "🔍 ", " (solo propuesta)" if not apply else ""))
    report.append("Para aplicar: action=structure path=... apply=true")
    return "\n".join(report)


def _safe_move(frm: Path, to: Path):
    if not frm.exists():
        return False
    to.parent.mkdir(parents=True, exist_ok=True)
    if to.exists():
        to = to.with_name(to.name + " (movido)")
    try:
        shutil.move(str(frm), str(to))
        return True
    except Exception:
        return False


def _organize(parameters, player):
    path = Path(parameters.get("path") or parameters.get("file_path") or ".")
    if not path.is_dir():
        return "Error: 'organize' requiere una carpeta."
    apply = str(parameters.get("apply", "false")).lower() in ("1", "true", "yes", "si")
    cat_map = {
        "code": {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cs", ".cpp", ".c", ".h", ".hpp", ".go", ".rs", ".php", ".rb", ".kt", ".swift"},
        "web": {".html", ".css", ".scss", ".vue"},
        "assets": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".mp4", ".mp3", ".wav", ".ogg"},
        "datos": {".json", ".csv", ".sql", ".xml", ".yaml", ".yml", ".db", ".sqlite"},
        "docs": {".md", ".txt", ".pdf", ".docx", ".rtf"},
        "scripts": {".sh", ".bat", ".ps1", ".cmd"},
    }
    skip = {".venv", "node_modules", ".git", "__pycache__", "build", "dist", ".idea", "data"}
    files = sorted(p for p in path.rglob("*") if p.is_file() and not any(part in skip for part in p.parts))
    report = ["🗂️ Organización de '{}' ({} archivos):".format(path, len(files))]
    moved = 0
    for p in files:
        if p.parent.name in cat_map:
            continue  # ya está en una carpeta de categoría
        cat = next((c for c, exts in cat_map.items() if p.suffix.lower() in exts), None)
        if not cat:
            continue
        dest = path / cat / p.name
        if p.parent == path / cat:
            continue
        report.append("  → {} → {}/{}".format(p.relative_to(path), cat, p.name))
        if apply:
            if _safe_move(p, dest):
                moved += 1
    if not apply:
        report.append("")
        report.append("🔍 Solo propuesta. Para mover: action=organize path=... apply=true")
    else:
        report.append("")
        report.append("✅ {} archivo(s) movido(s).".format(moved))
    return "\n".join(report)


def _rename(parameters, player):
    fp = (parameters.get("file_path") or parameters.get("path") or "").strip()
    new_name = (parameters.get("new_name") or parameters.get("name") or "").strip()
    if not fp or not new_name:
        return "Error: se requiere 'file_path' y 'new_name'."
    path = Path(fp)
    if not path.exists():
        return "Error: no existe '{}'.".format(fp)
    new_path = path.with_name(new_name)
    if new_path.exists() and new_path != path:
        return "Error: ya existe '{}'.".format(new_path)
    _safe_move(path, new_path)
    update_refs = str(parameters.get("update_refs", "false")).lower() in ("1", "true", "yes")
    ref_report = []
    if update_refs and path.suffix and new_path.name != path.name:
        old_name = path.name
        for sibling in path.parent.rglob("*"):
            if sibling.is_file() and sibling != new_path and sibling.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".php", ".java", ".cs", ".cpp"):
                try:
                    txt = sibling.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                if old_name in txt:
                    cnt = txt.count(old_name)
                    txt = txt.replace(old_name, new_path.name)
                    _write(sibling, txt)
                    ref_report.append("  ↻ {}: {} referencia(s) actualizada(s)".format(sibling.name, cnt))
    head = "✅ Renombrado: {} → {}".format(path.name, new_path.name)
    if ref_report:
        head += "\n" + "\n".join(ref_report)
    if not ref_report and update_refs:
        head += "\n(Sin referencias encontradas)"
    return head
