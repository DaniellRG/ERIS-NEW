import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": [
        "os", "sys", "json", "pathlib", "asyncio", "ctypes",
        "websockets", "numpy", "sounddevice", "vosk", "spotipy",
        "psutil", "pyautogui", "pygetwindow", "pyrect",
        "comtypes", "pycaw", "docx", "openpyxl", "qtawesome",
        "win10toast", "PyQt6", "actions", "agent", "memory",
        "core", "google", "flask", "PyPDF2", "pptx", "tzdata",
        "chromadb", "_sounddevice_data",
    ],

    "include_files": [
        "assets/",
        "memory/",
        "config/",
        "bios/",
        "context/",
        "core/",
        "skills/",
        "plugins/",
        # Nuevos modulos de Eris
        "actions/emo_core.py",
        "actions/task_automation.py",
        "actions/res_manager.py",
        "actions/self_learning.py",
        "actions/predict_engine.py",
        "actions/web_jobs.py",
        "actions/sandbox.py",
        "actions/eris_db.py",
        "actions/curiosity_engine.py",
        "actions/context_files.py",
        "actions/memory_nudge.py",
        "actions/notifications.py",
        "actions/send_message.py",
        "actions/app_installer.py",
        "actions/training_full.py",
        "actions/autonomous_agent.py",
        "actions/game_companion.py",
        "actions/game_launcher.py",
        "actions/search_background.py",
        "actions/backup_system.py",
        "actions/alarm_manager.py",
        "actions/habit_predictor.py",
        "actions/window_manager.py",
        "actions/contextual_control.py",
        "actions/proactive_automation.py",
        "actions/smart_file_organizer.py",
        "actions/tool_creator.py",
        "actions/unified_communications.py",
        "actions/file_monitor.py",
        "actions/task_manager.py",
        "actions/spotify_control.py",
        "actions/webfetch.py",
        "actions/ask_user.py",
        "actions/subagent_task.py",
        "actions/self_heal.py",
        "actions/emotional_growth.py",
        "actions/mobile_server.py",
        "actions/ollama_provider.py",
        "actions/screen_recorder.py",
        "actions/translator.py",
        "actions/meeting_transcriber.py",
        "actions/network_monitor.py",
        "actions/quick_actions.py",
        "actions/pdf_editor.py",
        "actions/context_menu.py",
        "actions/context_menu_handler.py",
        "actions/sms_manager.py",
        "actions/dashboard_server.py",
        # Sounddevice data from system Python 3.14
        (
            r"C:\Users\danie\AppData\Roaming\Python\Python314\site-packages\_sounddevice_data",
            "lib/_sounddevice_data"
        ),
    ],

    "include_msvcr": True,
    "optimize": 2,

    "zip_exclude_packages": ["_sounddevice_data"],

    "excludes": [
        "PySide6"
    ]
}

base = "gui" if sys.platform == "win32" else None

setup(
    name="ERIS AI",
    version="2.0",
    description="ERIS AI Assistant",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "run.py",
            base=base,
            icon="assets/eris_icono.ico",
            target_name="ERIS.exe"
        )
    ]
)