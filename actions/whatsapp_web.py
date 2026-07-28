import os
import json
import webbrowser
import subprocess
import time
import urllib.parse

WHATSAPP_WEB_URL = "https://web.whatsapp.com"


def whatsapp_web(parameters: dict, player=None) -> str:
    action = parameters.get("action", "open_chat").lower()

    if action == "send_message":
        return _send_message(parameters)
    elif action == "send_file":
        return _send_file(parameters)
    elif action == "open_chat":
        return _open_chat(parameters)
    elif action == "contacts":
        return _list_contacts()
    elif action == "search":
        return _search_messages(parameters)
    elif action == "read_last":
        return _read_last(parameters)
    else:
        return f"Unknown action: {action}. Valid: send_message, send_file, open_chat, contacts, search, read_last"


def _open_chat(parameters: dict):
    phone = parameters.get("phone", "")
    if phone:
        phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        url = f"https://web.whatsapp.com/send?phone={phone}"
        text = parameters.get("text", "")
        if text:
            url += f"&text={urllib.parse.quote(text)}"
        webbrowser.open(url)
        return f"Opening WhatsApp Web chat with {phone}..."
    webbrowser.open(WHATSAPP_WEB_URL)
    return "Opening WhatsApp Web. Scan QR code if not logged in."


def _send_message(parameters: dict):
    phone = parameters.get("phone", "")
    message = parameters.get("message", "")
    if not phone or not message:
        return "Both 'phone' and 'message' parameters required."

    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    url = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(message)}"
    webbrowser.open(url)
    return (
        f"Opening WhatsApp Web to send message to {phone}.\n"
        "The message will be pre-filled. Press Enter to send.\n"
        "Note: WhatsApp Web must be logged in. If not, scan QR code first."
    )


def _send_file(parameters: dict):
    phone = parameters.get("phone", "")
    if not phone:
        return "'phone' parameter required."

    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    webbrowser.open(f"https://web.whatsapp.com/send?phone={phone}")

    file_path = parameters.get("file", "")
    if file_path and os.path.exists(file_path):
        return (
            f"Opening chat with {phone}. "
            f"Attach file manually: {file_path}\n"
            "Use the attachment button to select the file."
        )
    return f"Opening chat with {phone}. Use attachment button to send files."


def _list_contacts():
    try:
        ps = (
            "$contacts = @(); "
            "$filePath = $env:LOCALAPPDATA + '\\Microsoft\\Windows\\Contacts\\*.contact'; "
            "Get-ChildItem $filePath -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty Name | "
            "ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, str):
                data = [data]
            lines = [f"Local contacts ({len(data)}):"]
            for c in data[:30]:
                lines.append(f"  - {c}")
            return "\n".join(lines)
    except Exception:
        pass

    webbrowser.open("https://web.whatsapp.com")
    return (
        "Opening WhatsApp Web to view recent chats.\n"
        "WhatsApp Web does not expose contacts via automation. "
        "View your recent chats in the browser."
    )


def _search_messages(parameters: dict):
    query = parameters.get("query", "")
    if not query:
        return "'query' parameter required."

    phone = parameters.get("phone", "")
    if phone:
        phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        webbrowser.open(f"https://web.whatsapp.com/send?phone={phone}")

    return (
        f"Opening WhatsApp Web. Search for '{query}' using the search box.\n"
        "Note: WhatsApp Web search must be performed manually."
    )


def _read_last(parameters: dict):
    phone = parameters.get("phone", "")
    if phone:
        phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        webbrowser.open(f"https://web.whatsapp.com/send?phone={phone}")

    return (
        f"Opening WhatsApp Web{' chat with ' + phone if phone else ''}.\n"
        "Reading messages via automation is limited by WhatsApp's encryption.\n"
        "View messages directly in the browser."
    )
