"""
TOOL_DECLARATIONS - final clean version
Only tools with REAL implementations and CORRECT params.
Stub tools removed. All removed tools still callable via registry.
"""

import json
from pathlib import Path

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Opens application by name",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "App name (e.g. 'Chrome', 'Notepad')"
                }
            },
            "required": [
                "app_name"
            ]
        }
    },
    {
        "name": "web_search",
        "description": "Web/news/image/video search",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Search term"
                },
                "action": {
                    "type": "STRING",
                    "description": "search, news, images, videos, definition, open"
                },
                "engine": {
                    "type": "STRING",
                    "description": "auto, google, duckduckgo"
                },
                "num_results": {
                    "type": "INTEGER",
                    "description": "Result count (default 5)"
                }
            },
            "required": [
                "query"
            ]
        }
    },
    {
        "name": "weather_report",
        "description": "Weather by city",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {
                    "type": "STRING",
                    "description": "City name"
                }
            },
            "required": [
                "city"
            ]
        }
    },
    {
        "name": "whatsapp",
        "description": "WhatsApp messaging",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "send, read, list_contacts, add_contact"
                },
                "receiver": {
                    "type": "STRING",
                    "description": "Contact name or phone"
                },
                "message": {
                    "type": "STRING",
                    "description": "Message text"
                },
                "count": {
                    "type": "INTEGER",
                    "description": "Messages to read"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "reminder",
        "description": "Set timed reminders",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message": {
                    "type": "STRING",
                    "description": "Reminder text"
                },
                "time": {
                    "type": "STRING",
                    "description": "Time (e.g. '14:30', 'in 30 minutes')"
                },
                "priority": {
                    "type": "STRING",
                    "description": "low, medium, high"
                }
            },
            "required": [
                "message",
                "time"
            ]
        }
    },
    {
        "name": "youtube_video",
        "description": "Play/search YouTube videos",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "play, search, playlist, get_info"
                },
                "query": {
                    "type": "STRING",
                    "description": "Search term or URL"
                },
                "video_id": {
                    "type": "STRING",
                    "description": "YouTube video ID"
                },
                "max_results": {
                    "type": "INTEGER",
                    "description": "Max results"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "computer_settings",
        "description": "Volume, brightness, window control",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "volume, minimize, maximize"
                },
                "value": {
                    "type": "STRING",
                    "description": "Value (e.g. '50', 'up', 'down')"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "browser_control",
        "description": "Browser automation: navigate, click, search, read pages",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "go_to, search, new_tab, close_tab, scroll, read_page, click_element, go_back, play_pause, scan_results"
                },
                "url": {
                    "type": "STRING",
                    "description": "URL to navigate"
                },
                "query": {
                    "type": "STRING",
                    "description": "Search query"
                },
                "direction": {
                    "type": "STRING",
                    "description": "up, down"
                },
                "description": {
                    "type": "STRING",
                    "description": "Element description to click"
                },
                "index": {
                    "type": "INTEGER",
                    "description": "Result index"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "file_controller",
        "description": "File CRUD, find, organize, disk usage",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "read, write, append, delete, move, copy, rename, list, search, info, compress, extract"
                },
                "path": {
                    "type": "STRING",
                    "description": "File/folder path"
                },
                "content": {
                    "type": "STRING",
                    "description": "Content for write/append"
                },
                "destination": {
                    "type": "STRING",
                    "description": "Destination path"
                },
                "pattern": {
                    "type": "STRING",
                    "description": "Search pattern"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "desktop_control",
        "description": "Window management: list, focus, minimize, close, cascade, tile",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "list_windows, list_detailed, minimize, maximize, restore, close, focus, search, cascade, tile_horizontal, tile_vertical, minimize_all, restore_all"
                },
                "name": {
                    "type": "STRING",
                    "description": "Window title or app name"
                },
                "app_name": {
                    "type": "STRING",
                    "description": "App name for open_app/close_app"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "code_helper",
        "description": "Write, edit, explain, run, build code in any language",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "write, edit, explain, run, build, auto"
                },
                "language": {
                    "type": "STRING",
                    "description": "python, javascript, html, css, etc"
                },
                "code": {
                    "type": "STRING",
                    "description": "Code to write/explain/run"
                },
                "description": {
                    "type": "STRING",
                    "description": "What to build (for auto/write)"
                },
                "file_path": {
                    "type": "STRING",
                    "description": "Target file path"
                },
                "instructions": {
                    "type": "STRING",
                    "description": "Edit instructions (for edit)"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "shutdown_eris",
        "description": "Shut down ERIS assistant",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "file_processor",
        "description": "Process files: info, describe, summarize, validate, convert, compress",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "info, describe, word_count, summarize, to_bullets, extract_text, convert, trim, analyze, validate, format, fix, compress"
                },
                "file_path": {
                    "type": "STRING",
                    "description": "File path"
                },
                "instruction": {
                    "type": "STRING",
                    "description": "Additional instruction"
                },
                "format": {
                    "type": "STRING",
                    "description": "Target format for convert"
                },
                "start": {
                    "type": "INTEGER",
                    "description": "Start line for trim"
                },
                "end": {
                    "type": "INTEGER",
                    "description": "End line for trim"
                }
            },
            "required": [
                "action",
                "file_path"
            ]
        }
    },
    {
        "name": "spotify_control",
        "description": "Spotify playback control",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "play, pause, next, previous, set_volume, search, now_playing"
                },
                "query": {
                    "type": "STRING",
                    "description": "Search query"
                },
                "volume": {
                    "type": "INTEGER",
                    "description": "Volume 0-100"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "system_monitor",
        "description": "CPU, RAM, disk, GPU, network, processes",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "overview, cpu, ram, disk, gpu, network, processes, top"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "screen_vision",
        "description": "AI screen reading and analysis",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "capture, read, analyze"
                },
                "prompt": {
                    "type": "STRING",
                    "description": "Analysis prompt"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "terminal_agent",
        "description": "Execute CMD/PowerShell commands",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "cmd, powershell, win_run, elevated, open, shell_execute"
                },
                "command": {
                    "type": "STRING",
                    "description": "Command to execute"
                },
                "elevated": {
                    "type": "BOOLEAN",
                    "description": "Run as admin"
                }
            },
            "required": [
                "action",
                "command"
            ]
        }
    },
    {
        "name": "super_search",
        "description": "Advanced file/content/app search on PC",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "find_file, find_content, find_app, find_recent, find_by_type, find_by_date, find_everything"
                },
                "name": {
                    "type": "STRING",
                    "description": "File/app name to search"
                },
                "content": {
                    "type": "STRING",
                    "description": "Text content to search inside files"
                },
                "extension": {
                    "type": "STRING",
                    "description": "File extension filter"
                },
                "path": {
                    "type": "STRING",
                    "description": "Search path"
                },
                "max_results": {
                    "type": "INTEGER",
                    "description": "Max results"
                },
                "days": {
                    "type": "INTEGER",
                    "description": "Days back for recent"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "obsidian_note",
        "description": "Obsidian vault: create, read, search, daily notes, links, tags",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "write, read, search, daily, link, backlinks, tags, browse, graph"
                },
                "title": {
                    "type": "STRING",
                    "description": "Note title"
                },
                "content": {
                    "type": "STRING",
                    "description": "Note content (for write)"
                },
                "query": {
                    "type": "STRING",
                    "description": "Search query"
                },
                "tag": {
                    "type": "STRING",
                    "description": "Tag name"
                },
                "note_name": {
                    "type": "STRING",
                    "description": "Note to link to"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "app_installer",
        "description": "Install/uninstall apps via winget",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "install, uninstall, search, list"
                },
                "app": {
                    "type": "STRING",
                    "description": "App name"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "task_manager",
        "description": "Kill, search, get details of processes",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "kill, search, detail, list"
                },
                "query": {
                    "type": "STRING",
                    "description": "Process name or PID"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "system_reader",
        "description": "Deep PC state: sensors, network, disks, battery",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "status, top_processes, disks, network, sensors, deep"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "calculator",
        "description": "Math, unit conversion, date calculations",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "expression": {
                    "type": "STRING",
                    "description": "Math expression or conversion"
                }
            },
            "required": [
                "expression"
            ]
        }
    },
    {
        "name": "music_player",
        "description": "Local music playback",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "play, pause, stop, list, now_playing"
                },
                "path": {
                    "type": "STRING",
                    "description": "Music file/folder path"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "code_analyzer",
        "description": "Static analysis: ruff, radon, mypy, bandit, pylint",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "ruff, radon, mypy, bandit, pylint, pip_audit, full"
                },
                "path": {
                    "type": "STRING",
                    "description": "Target file or folder"
                }
            },
            "required": [
                "action",
                "path"
            ]
        }
    },
    {
        "name": "self_heal",
        "description": "Auto-detect and fix code issues",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "scan_all, scan_file, health_report, auto_fix"
                },
                "file": {
                    "type": "STRING",
                    "description": "Target file (for scan_file)"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "self_healing_loop",
        "description": "Self-healing orchestrator",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "detect, fix_file, test, validate, scan_all, status, rollback, restart"
                },
                "file": {
                    "type": "STRING",
                    "description": "Target file"
                },
                "code": {
                    "type": "STRING",
                    "description": "Candidate fix code"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "image_generation",
        "description": "AI image generation and manipulation",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "generate, list, get, delete, style, upscale, variations, batch, status, gallery, download"
                },
                "prompt": {
                    "type": "STRING",
                    "description": "Image description"
                },
                "style": {
                    "type": "STRING",
                    "description": "Style preset"
                },
                "size": {
                    "type": "STRING",
                    "description": "Image size"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "window_manager",
        "description": "Multi-monitor window snap and layouts",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "list, list_monitors, focus, move_to_monitor, minimize, close, maximize, snap, organize"
                },
                "name": {
                    "type": "STRING",
                    "description": "Window title"
                },
                "monitor": {
                    "type": "INTEGER",
                    "description": "Monitor index"
                },
                "position": {
                    "type": "STRING",
                    "description": "left, right, top, bottom, center"
                },
                "preset": {
                    "type": "STRING",
                    "description": "side_by_side, three_columns, quad, ca"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "windows_settings",
        "description": "Deep Windows settings: display, audio, network, power",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "display, audio, network, power, bluetooth, defaults, startup, features, environment"
                },
                "setting": {
                    "type": "STRING",
                    "description": "Specific setting name"
                },
                "value": {
                    "type": "STRING",
                    "description": "Value to set"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "video_analyzer",
        "description": "YouTube subtitles, transcribe, summarize videos",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "subtitles, transcribe, summarize, chapters"
                },
                "url": {
                    "type": "STRING",
                    "description": "Video URL"
                },
                "video_id": {
                    "type": "STRING",
                    "description": "Video ID"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "web_scraper",
        "description": "Scrape and extract content from web pages",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "scrape, extract_links, extract_images, extract_text, batch, smart"
                },
                "url": {
                    "type": "STRING",
                    "description": "URL to scrape"
                },
                "selector": {
                    "type": "STRING",
                    "description": "CSS selector"
                }
            },
            "required": [
                "action"
            ]
        }
    },
    {
        "name": "research",
        "description": "Autonomous research on any topic",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {
                    "type": "STRING",
                    "description": "Research topic"
                },
                "depth": {
                    "type": "STRING",
                    "description": "shallow, medium, deep"
                }
            },
            "required": [
                "topic"
            ]
        }
    },
    {
        "name": "send_message",
        "description": "Send via Discord/Signal/Messenger",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver": {
                    "type": "STRING",
                    "description": "Contact name"
                },
                "message_text": {
                    "type": "STRING",
                    "description": "Message"
                },
                "platform": {
                    "type": "STRING",
                    "description": "Telegram, Discord, Signal, Messenger"
                }
            },
            "required": [
                "receiver",
                "message_text",
                "platform"
            ]
        }
    },
    {
        "name": "skill_manage",
        "description": "Manage ERIS skills: list, enable, disable",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "list, enable, disable, info, create, delete"
                },
                "skill": {
                    "type": "STRING",
                    "description": "Skill name"
                }
            },
            "required": [
                "action"
            ]
        }
    }
]

def load_custom_tools(BASE_DIR):
    """Load custom tools from custom_tools.json and append to TOOL_DECLARATIONS."""
    try:
        _custom_tools_path = BASE_DIR / "actions" / "custom_tools.json"
        if _custom_tools_path.exists():
            with open(_custom_tools_path, "r", encoding="utf-8") as _f:
                _custom = json.load(_f)
            if isinstance(_custom, list):
                for _t in _custom:
                    if _t.get("name") not in [td["name"] for td in TOOL_DECLARATIONS]:
                        TOOL_DECLARATIONS.append(_t)
        _extra_tools_path = BASE_DIR / "config" / "extra_tools.json"
        if _extra_tools_path.exists():
            with open(_extra_tools_path, "r", encoding="utf-8") as _f:
                _extra = json.load(_f)
            if isinstance(_extra, list):
                for _t in _extra:
                    if _t.get("name") not in [td["name"] for td in TOOL_DECLARATIONS]:
                        TOOL_DECLARATIONS.append(_t)
    except Exception:
        pass
