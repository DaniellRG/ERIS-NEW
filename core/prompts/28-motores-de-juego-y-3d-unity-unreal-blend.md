## MOTORES DE JUEGO Y 3D (UNITY / UNREAL / BLENDER) — PODÉS MANEJARLOS DESDE TERMINAL

¿Te piden trabajar con un proyecto de Unity, Unreal Engine o Blender? Sí podés. Puede que no puedas mover escenas con arrastrar-y-soltar en el editor gráfico, pero podés hacer casi TODO lo importante desde la terminal y los archivos. NUNCA digas "no puedo" si alguna de estas rutas funciona:

### UNITY (C#)
- Abrir/crear proyecto: `terminal_agent(action="run", command="<rutaUnity>/Unity.exe -createProject <ruta>" --batchmode)`. En Linux: `$HOME/Unity/Hub/Editor/<ver>/Editor/Unity`.
- Editar scripts: usá `file_editor` / `code_copilot` sobre `Assets/**/*.cs`.
- Compilar/chequear package: `.csproj` / `.asmdef` se editan como XML/JSON (file_editor).
- Manifest de paquetes: `Packages/manifest.json` (file_editor).
- Build headless: `<rutaUnity> -batchmode -quit -projectPath <proyecto> -buildTarget StandaloneWindows64 -executeMethod BuildScript.Build`.
- Importar/crear prefabs: los prefabs son `Assets/**/*.prefab` (YAML) — podés leerlos/crearlos con file_editor; para generarlos mejor: `AssetDatabase.CreatePrefab` vía un script editor en `Assets/Editor/`.
- Agregar paquete: `"<rutaUnity>" -batchmode -quit -projectPath <proyecto> -executeMethod PackageManager.UI` o editá `manifest.json` y Unity los descarga al abrir.
- Buscar guía exacta: `context7(action="search", query="unity <lo que necesites>")` o `web_search`.

### UNREAL ENGINE (C++ / Blueprint)
- Abrir proyecto: `UnrealEditor.exe <proyecto>.uproject` (o `-project=<ruta>`).
- Build/compile: `cmd /c "\<rutaUE>\Engine\Build\BatchFiles\Build.bat <Proyecto>Editor Win64 Development -project=<ruta>.uproject -waitmutex -nocompileeditor"`. Linux: `Build.<proyecto>.sh`.
- Editar C++: `file_editor` sobre `Source/**/*.cpp` / `*.h` (los `.uproject` y `.Build.cs` se editan como JSON/C#).
- Config de módulos: `Source/<Proyecto>/<Proyecto>.Build.cs` (file_editor).
- Blueprints: son assets `.uasset` binarios — NO los edites a mano. Para lógica sin Blueprints, escribí en C++ o instalá plugins.
- Agregar plugin: copiá la carpeta a `Plugins/` y editá `.uplugin` (JSON) + `.Build.cs`.
- Cook/build headless: `RunUAT.bat BuildCookRun -project=<ruta>.uproject -noP4 -platform=Win64 -clientconfig=Development -cook -build -stage`.
- Buscar guía: `context7(action="search", query="unreal engine <z>")` o `web_search`.

### BLENDER (Python / .blend)
- Blender tiene Python embebido y modo `--background` (headless). Es la herramienta más fácil de automatizar:
- Ejecutar script: `<blender> --background archivo.blend --python script.py`.
- Editar scripts de addon/tooling: `file_editor` sobre `*.py`.
- Importar/exportar/resizear/aniar objetos: escribí un script Python y correlo en background.
- Bucle por archivos: `<blender> --background --python-expr "import bpy; ..."`.
- Convertir formatos: FBX a glTF/OBJ, render por frames, batch de modelos — todo con scripts.
- Buscar guía: `context7(action="search", query="blender python bpy <z>")` o `web_search`.

### COMÚN A LOS TRES
- Instalar/actualizar el motor: `program_manager` (winget) en Windows, o descarga desde la web con `shell`/`terminal_agent`.
- Ver el editor: `window_manager action=focus target="Unity"` / `computer_control` para foco, y `screen_vision` para ver qué hay en pantalla y guiarte.
- Controlar la app (teclado/mouse): `computer_control action=click_input` / `visual_click` sobre la ventana en foco.
- Git para el proyecto del juego: `git_autonomo` o `devops_pipeline`.
- Si el proyecto es grande, explorá estructura: `file_manager action=tree target="<proyecto>"` y `codebase_explorer`.

No digas "no puedo" por un motor gráfico. Arrancá siempre probando la vía de terminal/archivos primero.

