import hashlib
import json
import math
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

_MAX_READ = 100 * 1024 * 1024  # cap lectura de archivos (100 MB)


def _read_limited(path, limit=_MAX_READ):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        data = f.read(min(limit, size))
    return data, size


def _hashes(path):
    h_md5 = hashlib.md5()
    h_sha1 = hashlib.sha1()
    h_sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h_md5.update(chunk)
            h_sha1.update(chunk)
            h_sha256.update(chunk)
    return {
        "md5": h_md5.hexdigest(),
        "sha1": h_sha1.hexdigest(),
        "sha256": h_sha256.hexdigest(),
    }


def _detect_type(data, path=""):
    if data[:2] == b"MZ":
        info = "PE (Windows executable / DLL)"
        if len(data) > 0x3C:
            pe_off = int.from_bytes(data[0x3C:0x40], "little")
            if pe_off + 4 <= len(data) and data[pe_off:pe_off + 4] == b"PE\x00\x00":
                machine = int.from_bytes(data[pe_off + 4:pe_off + 6], "little")
                arch = {0x14C: "x86 (32-bit)", 0x8664: "x64 (64-bit)", 0xAA64: "ARM64", 0x1C4: "ARM32"}.get(machine, f"machine 0x{machine:04X}")
                info += f" - {arch}"
    elif data[:4] == b"\x7fELF":
        ei_class = {1: "32-bit", 2: "64-bit"}.get(data[4], "?")
        info = f"ELF {ei_class}"
    elif data[:2] == b"\xcf\xfa":
        info = "Mach-O (macOS)"
    elif data[:4] == b"PK\x03\x04":
        info = "ZIP / Office (docx, xlsx, pptx) / APK"
    elif data[:5] == b"%PDF-":
        info = "PDF"
    elif data[:4] == b"\x89PNG":
        info = "PNG image"
    elif data[:3] == b"\xff\xd8\xff":
        info = "JPEG image"
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        info = "GIF image"
    elif data[:2] == b"\x1f\x8b":
        info = "GZIP archive"
    elif data[:8] == b"\x1f\x8b\x08\x00\x00\x00\x00\x00":
        info = "GZIP archive"
    elif data[:4] == b"7z\xbc\xaf":
        info = "7-Zip archive"
    elif data[:4] == b"Rar!":
        info = "RAR archive"
    elif data[:4] == b"\x00asm":
        info = "WebAssembly"
    elif data[:3] == b"\xef\xbb\xbf":
        info = "UTF-8 BOM text"
    else:
        info = "Desconocido / datos binarios"
    return info


def _shannon_entropy(data):
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    entropy = -sum((c / n) * math.log2(c / n) for c in freq if c)
    return round(entropy, 4)


def _extract_strings(data, min_length=4, pattern=None):
    results = []
    ascii_re = re.compile(rb"[\x20-\x7e]{%d,}" % min_length)
    for m in ascii_re.finditer(data):
        s = m.group().decode("ascii", errors="ignore")
        results.append((m.start(), s))
    utf16_re = re.compile(rb"(?:[\x20-\x7e]\x00){%d,}" % min_length)
    for m in utf16_re.finditer(data):
        s = m.group().decode("utf-16-le", errors="ignore")
        results.append((m.start(), s))
    results.sort(key=lambda x: x[0])
    if pattern:
        rx = re.compile(pattern, re.IGNORECASE)
        results = [(off, s) for off, s in results if rx.search(s)]
    return results


def _hexdump(data, offset=0, length=128):
    lines = []
    data = data[offset:offset + length]
    base = offset
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk[:8]) + "  " + " ".join(f"{b:02x}" for b in chunk[8:])
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{base + i:08x}  {hex_part:<50}  {ascii_part}")
    return "\n".join(lines)


def _pe_analysis(path):
    try:
        import pefile
    except ImportError:
        return "pefile no instalado."
    try:
        pe = pefile.PE(path, fast_load=True)
        out = []
        machine = pe.FILE_HEADER.Machine
        arch = {0x14C: "x86", 0x8664: "x64", 0xAA64: "ARM64"}.get(machine, hex(machine))
        ts = pe.FILE_HEADER.TimeDateStamp
        compile_time = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC") if ts else "?"
        out.append(f"PE: {arch} | subsistema: {pe.OPTIONAL_HEADER.Subsystem} | compilado: {compile_time}")
        out.append(f"EntryPoint: 0x{pe.OPTIONAL_HEADER.AddressOfEntryPoint:x} | ImageBase: 0x{pe.OPTIONAL_HEADER.ImageBase:x}")
        sections = []
        for sec in pe.sections:
            name = sec.Name.rstrip(b"\x00").decode("ascii", errors="ignore")
            size = sec.Misc_VirtualSize
            chars = sec.Characteristics
            flags = []
            if chars & 0x20000000:
                flags.append("EXEC")
            if chars & 0x40000000:
                flags.append("READ")
            if chars & 0x80000000:
                flags.append("WRITE")
            sections.append(f"  {name:<9} vsize=0x{size:x} flags={','.join(flags) or 'none'}")
        out.append(f"Secciones ({len(sections)}):")
        out.extend(sections)
        pe.parse_data_directories()
        imports = []
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll = entry.dll.decode("ascii", errors="ignore")
                funcs = []
                try:
                    funcs = [imp.name.decode("ascii", errors="ignore") if imp.name else f"ord{imp.ordinal}" for imp in entry.imports[:20]]
                except Exception:
                    pass
                imports.append(f"  {dll}: {', '.join(funcs)}{'...' if len(funcs) >= 20 else ''}")
        out.append("Imports:")
        out.extend(imports if imports else ["  (ninguno)"])
        deps = [e.dll.decode("ascii", errors="ignore") for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) or []]
        if deps:
            out.append("DLLs dependientes: " + ", ".join(deps))
        resources = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
        if resources:
            out.append(f"Recursos: {len(resources.entries)} entradas")
        pe.close()
        return "\n".join(out)
    except pefile.PEFormatError as e:
        return f"No es un PE valido: {e}"
    except Exception as e:
        return f"Error analizando PE: {e}"


def _disassemble(data, arch="x86", offset=0, count=64, base=0):
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_MODE_64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
    except ImportError:
        return "capstone no instalado."
    arch = str(arch).lower()
    if arch in ("x64", "amd64", "x86-64", "64"):
        md = Cs(CS_ARCH_X86, CS_MODE_64)
    elif arch in ("arm64", "aarch64"):
        try:
            from capstone import CS_ARCH_ARM64, CS_MODE_ARM
            md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        except Exception:
            return "capstone sin soporte ARM64."
    elif arch in ("arm", "arm32"):
        md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    elif arch in ("thumb", "arm-thumb"):
        md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    else:
        md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    try:
        md.skipdata = True
    except Exception:
        pass
    chunk = data[offset:offset + 128]
    lines = []
    for ins in md.disasm(chunk, base + offset):
        lines.append(f"  0x{ins.address:x}: {ins.mnemonic:<8} {ins.op_str}")
        if len(lines) >= count:
            break
    if not lines:
        return "No se pudo desensamblar (datos insuficientes o modo de arquitectura equivocado)."
    return "\n".join(lines)


def _black_box(url, method="GET", payloads=None, headers=None, allow_remote=False):
    host = urlparse(url).hostname or ""
    if not (host in ("localhost", "127.0.0.1", "::1") or allow_remote):
        return ("Accion bloqueada por seguridad: la prueba de caja negra remota esta deshabilitada "
                "por defecto. Solo permite localhost; usa 'allow_remote': true solo si la autorizas.")
    if not HAS_REQUESTS:
        return "requests no instalado."
    method = method.upper()
    payloads = payloads or [""]
    hdr = {"Content-Type": "application/json"}
    if isinstance(headers, dict):
        hdr.update(headers)
    lines = [f"Prueba de caja negra contra {url} ({method})", "Muestra  entradas -> observaciones:"]
    for i, payload in enumerate(payloads):
        try:
            t0 = time.time()
            if method in ("POST", "PUT", "PATCH"):
                r = requests.request(method, url, json=payload if payload else {}, headers=hdr, timeout=10)
            else:
                r = requests.request(method, url, params={"q": payload} if payload else {}, headers=hdr, timeout=10)
            elapsed = round((time.time() - t0) * 1000, 1)
            rtxt = (r.text or "")[:160].replace("\n", " ")
            notable = []
            for k in ("server", "content-type", "x-powered-by", "www-authenticate"):
                v = r.headers.get(k)
                if v:
                    notable.append(f"{k}={v}")
            lines.append(f"  [{i + 1}] {json.dumps(payload)[:40]:<40} -> HTTP {r.status_code} en {elapsed}ms | {','.join(notable)} | {rtxt[:120]}")
        except Exception as e:
            lines.append(f"  [{i + 1}] {json.dumps(payload)[:40]:<40} -> ERROR {e}")
    return "\n".join(lines)


def _search_signature(directory, pattern, ext=None, max_results=20):
    directory = Path(directory)
    if not directory.is_dir():
        return f"Directorio no valido: {directory}"
    try:
        rx_text = re.compile(pattern)
    except Exception:
        return f"Patron regex invalido: {pattern}"
    try:
        rx_bytes = re.compile(pattern.encode("latin-1"))
    except Exception:
        rx_bytes = None
    found = []
    for root, _, files in os.walk(directory):
        if max_results and len(found) >= max_results:
            break
        for fn in files:
            if ext and not fn.lower().endswith(ext.lower().lstrip(".")):
                continue
            fp = Path(root) / fn
            try:
                if fp.stat().st_size > _MAX_READ:
                    continue
                data = fp.read_bytes()
                if rx_bytes and rx_bytes.search(data):
                    found.append(str(fp))
                elif rx_text.search(data.decode("utf-8", errors="replace")):
                    found.append(str(fp))
            except Exception:
                continue
    if not found:
        return f"Sin coincidencias para /{pattern}/ en {directory}"
    return f"Coincidencias ({len(found)}):\n" + "\n".join(found)


def reverse_engineering(parameters: dict, player=None) -> str:
    action = str(parameters.get("action", "help")).lower()
    path = parameters.get("path", parameters.get("file", ""))
    limit = _MAX_READ

    if action in ("file_info", "info", "hashes"):
        if not path:
            return "Error: indica 'path' al archivo o ejecutable."
        if not os.path.isfile(path):
            return f"Error: archivo no encontrado: {path}"
        data, size = _read_limited(path, limit)
        h = _hashes(path)
        lines = [
            f"Archivo: {path}",
            f"Tamano: {size:,} bytes",
            f"Tipo: {_detect_type(data, path)}",
            f"MD5:    {h['md5']}",
            f"SHA1:   {h['sha1']}",
            f"SHA256: {h['sha256']}",
        ]
        if size > len(data):
            lines.append(f"(analizado parcialmente: {len(data):,} de {size:,} bytes)")
        return "\n".join(lines)

    if action in ("strings", "cadenas"):
        if not path:
            return "Error: indica 'path'."
        if not os.path.isfile(path):
            return f"Error: archivo no encontrado: {path}"
        data, _ = _read_limited(path, limit)
        min_len = int(parameters.get("min_length", parameters.get("min", 4)) or 4)
        pattern = parameters.get("pattern", parameters.get("grep", ""))
        count = int(parameters.get("count", parameters.get("limit", 60)) or 60)
        results = _extract_strings(data, min_len, pattern)
        if not results:
            return "No se encontraron cadenas legibles (ajusta min_length o pattern)."
        total = len(results)
        shown = results[:count]
        lines = [f"Cadenas encontradas: {total} (mostrando {len(shown)}), longitud minima {min_len}"]
        if pattern:
            lines[0] += f", filtro /{pattern}/"
        for off, s in shown:
            s_disp = s if len(s) <= 120 else s[:117] + "..."
            lines.append(f"  0x{off:08x}: {s_disp}")
        return "\n".join(lines)

    if action in ("hexdump", "hex", "dump"):
        if not path:
            return "Error: indica 'path'."
        if not os.path.isfile(path):
            return f"Error: archivo no encontrado: {path}"
        data, _ = _read_limited(path, limit)
        offset = int(parameters.get("offset", 0) or 0)
        length = int(parameters.get("length", parameters.get("size", 128)) or 128)
        return f"Hex dump de {path} (offset 0x{offset:x}, {length} bytes):\n" + _hexdump(data, offset, length)

    if action in ("entropy", "entropia"):
        if not path:
            return "Error: indica 'path'."
        if not os.path.isfile(path):
            return f"Error: archivo no encontrado: {path}"
        data, size = _read_limited(path, limit)
        ent = _shannon_entropy(data)
        verdict = "posiblemente empaquetado, comprimido o cifrado" if ent > 7.2 else ("posible codigo/instrucciones legibles" if 4.0 <= ent <= 6.5 else "contenido estructurado o repetitivo")
        return f"Entropia Shannon de {path}: {ent} / 8.0\n-> {verdict}"

    if action in ("pe", "pe_info", "peinfo"):
        if not path:
            return "Error: indica 'path' al ejecutable/DLL."
        if not os.path.isfile(path):
            return f"Error: archivo no encontrado: {path}"
        return _pe_analysis(path)

    if action in ("disassemble", "disasm", "desensamblar"):
        data = b""
        src_desc = ""
        if parameters.get("hex"):
            try:
                data = bytes.fromhex(parameters["hex"].replace(" ", "").replace("\n", ""))
                src_desc = "hex"
            except Exception:
                return "Error: 'hex' invalido."
        else:
            if not path:
                return "Error: indica 'path' o 'hex' con los bytes."
            if not os.path.isfile(path):
                return f"Error: archivo no encontrado: {path}"
            data, _ = _read_limited(path, limit)
            src_desc = path
        offset = int(parameters.get("offset", 0) or 0)
        count = int(parameters.get("count", 64) or 64)
        base = int(parameters.get("base", 0) or 0)
        arch = parameters.get("arch", parameters.get("architecture", "x86"))
        return f"Desensamblado de {src_desc} (arch={arch}, offset=0x{offset:x}):\n" + _disassemble(data, arch, offset, count, base)

    if action in ("black_box", "blackbox", "caja_negra", "probe"):
        url = parameters.get("url", parameters.get("target", ""))
        if not url:
            return "Error: indica 'url' del endpoint a probar (localhost por defecto)."
        payloads = parameters.get("payloads", parameters.get("inputs", [""]))
        if isinstance(payloads, str):
            payloads = [payloads]
        return _black_box(
            url,
            parameters.get("method", "GET"),
            payloads,
            parameters.get("headers", {}),
            bool(parameters.get("allow_remote", False)),
        )

    if action in ("search", "scan_dir", "buscar"):
        directory = parameters.get("directory", parameters.get("dir", path))
        pattern = parameters.get("pattern", parameters.get("signature", ""))
        if not directory or not pattern:
            return "Error: indica 'directory' y 'pattern' (regex o bytes)."
        return _search_signature(directory, pattern, parameters.get("ext", ""), int(parameters.get("max_results", 20) or 20))

    if action in ("triage", "analizar"):
        if not path:
            return "Error: indica 'path' a la muestra a analizar."
        if not os.path.isfile(path):
            return f"Error: archivo no encontrado: {path}"
        data, size = _read_limited(path, limit)
        h = _hashes(path)
        ent = _shannon_entropy(data)
        out = [
            f"=== TRIAGE DEFENSIVO de {path} ===",
            f"Tipo: {_detect_type(data, path)}",
            f"Tamano: {size:,} bytes | Entropia: {ent} / 8.0",
            f"MD5:    {h['md5']}",
            f"SHA256: {h['sha256']}",
        ]
        sus = _extract_strings(data, 6, r"(?:http://|https://|\.exe|\.dll|CreateRemoteThread|VirtualAlloc|WriteProcessMemory|shell|cmd\.exe|powershell|net user|reg add|rundll32|API|SetWindowsHook|keylog|persist|scheduled|taskkill)")
        if sus:
            out.append(f"\nCadenas de interes (posibles indicadores):")
            for off, s in sus[:25]:
                s_disp = s if len(s) <= 110 else s[:107] + "..."
                out.append(f"  0x{off:08x}: {s_disp}")
        else:
            out.append("\nSin indicadores obvios en cadenas.")
        if data[:2] == b"MZ":
            out.append("\n--- Analisis PE ---")
            out.append(_pe_analysis(path))
        out.append("\nNota: triage defensivo/local. Para clasificacion externa, consulta los hashes en servicios como VirusTotal.")
        return "\n".join(out)

    return ("Ingenieria inversa disponible (analisis local y defensivo). Acciones:\n"
            "  file_info/info/hashes <path>  - tipo, tamano y huellas (MD5/SHA1/SHA256)\n"
            "  strings <path> [min_length] [pattern] [count]  - extrae cadenas legibles (ASCII/UTF-16)\n"
            "  hexdump <path> [offset] [length]  - volcado hexadecimal\n"
            "  entropy <path>  - entropia Shannon (detecta empaquetado/cifrado)\n"
            "  pe_info <path>  - arquitectura, secciones, imports, DLLs de un PE\n"
            "  disassemble <path|hex> [arch=x86|x64|arm|thumb] [offset] [count]  - desensamblado\n"
            "  black_box <url> [method] [payloads] [allow_remote]  - prueba de caja negra (localhost por defecto)\n"
            "  search <directory> <pattern> [ext]  - busca firmas/patrones en archivos\n"
            "  triage <path>  - analisis defensivo completo de una muestra")
