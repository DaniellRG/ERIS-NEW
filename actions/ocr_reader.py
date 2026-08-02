import base64
import json
import os
import subprocess
import tempfile
import re
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

_HAS_PYTESSERACT = False
try:
    import pytesseract
    _HAS_PYTESSERACT = True
except ImportError:
    pass

WIN_OCR_SCRIPT = """
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTaskGeneric' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function AsTask($WinRtTask, $ResultType) {
    $asTaskGeneric = $asTask.MakeGenericMethod($ResultType)
    $netTask = $asTaskGeneric.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

Add-Type -AssemblyName System.Windows
$bitmap = [System.Windows.Media.Imaging.BitmapImage]::new()
$bitmap.BeginInit()
$bitmap.UriSource = [Uri]::new('{image_path}')
$bitmap.CacheOption = [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad'
$bitmap.EndInit()
$bitmap.Freeze()

$encoder = [System.Windows.Media.Imaging.PngBitmapEncoder]::new()
$encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
$ms = [System.IO.MemoryStream]::new()
$encoder.Save($ms)
$bytes = $ms.ToArray()

$softwareBitmap = AsTask ([Windows.Graphics.Imaging.SoftwareBitmap]::CreateCopyFromBytes($bytes)) ([Windows.Graphics.Imaging.SoftwareBitmap])

$ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en'))
if (-not $ocrEngine) {{
    $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromPreferredLanguages()
}}

$result = AsTask ($ocrEngine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult])

Write-Output $result.Text
"""

WIN_OCR_BATCH = """
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTaskGeneric' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
function AsTask($WinRtTask, $ResultType) {
    $asTaskGeneric = $asTask.MakeGenericMethod($ResultType)
    $netTask = $asTaskGeneric.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

Add-Type -AssemblyName System.Windows

$bitmap = [System.Windows.Media.Imaging.BitmapImage]::new()
$bitmap.BeginInit()
$bitmap.UriSource = [Uri]::new('{image_path}')
$bitmap.CacheOption = [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad
$bitmap.EndInit()
$bitmap.Freeze()

$encoder = [System.Windows.Media.Imaging.PngBitmapEncoder]::new()
$encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
$ms = [System.IO.MemoryStream]::new()
$encoder.Save($ms)
$bytes = $ms.ToArray()

$softwareBitmap = AsTask ([Windows.Graphics.Imaging.SoftwareBitmap]::CreateCopyFromBytes($bytes)) ([Windows.Graphics.Imaging.SoftwareBitmap])

$langs = [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages
$ocrEngine = $null
foreach ($lang in $langs) {{
    $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    if ($ocrEngine) {{ break }}
}}
if (-not $ocrEngine) {{
    $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromPreferredLanguages()
}}

$result = AsTask ($ocrEngine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult])

$confidences = @()
foreach ($line in $result.Lines) {{
    foreach ($word in $line.Words) {{
        $confidences += "$($word.Text): $($word.Confidence)"
    }}
}}

Write-Output "===TEXT==="
Write-Output $result.Text
Write-Output "===CONFIDENCES==="
Write-Output ($confidences -join "`n")
Write-Output "===LANG==="
Write-Output $ocrEngine.RecognizerLanguage.DisplayName
"""


def _ocr_windows(image_path):
    script = WIN_OCR_BATCH.replace("{image_path}", image_path.replace("\\", "/"))
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if "===TEXT===" in output:
            parts = output.split("===TEXT===")
            text_part = parts[1].split("===CONFIDENCES===")[0].strip() if len(parts) > 1 else ""
            conf_part = parts[1].split("===CONFIDENCES===")[1].split("===LANG===")[0].strip() if "===CONFIDENCES===" in parts[1] else ""
            lang_part = parts[1].split("===LANG===")[1].strip() if "===LANG===" in parts[1] else ""
            confidences = []
            for line in conf_part.split("\n"):
                line = line.strip()
                if ":" in line and line:
                    word, conf = line.rsplit(":", 1)
                    try:
                        confidences.append({"word": word.strip(), "confidence": float(conf.strip())})
                    except ValueError:
                        confidences.append({"word": word.strip(), "confidence": 0.0})
            avg_conf = sum(c["confidence"] for c in confidences) / len(confidences) if confidences else 0
            return {
                "text": text_part,
                "language": lang_part,
                "confidence": round(avg_conf, 3),
                "word_count": len(confidences),
                "words": confidences[:50]
            }
        if output:
            return {"text": output, "language": "en", "confidence": 0, "word_count": 0, "words": []}
        if result.stderr:
            return None
    except Exception:
        pass
    return None


def _ocr_pytesseract(image_path):
    if not _HAS_PYTESSERACT:
        return None
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words = []
        total_conf = 0
        count = 0
        for i, conf in enumerate(data.get("conf", [])):
            try:
                c = float(conf)
                if c > 0 and data["text"][i].strip():
                    words.append({"word": data["text"][i], "confidence": c / 100.0})
                    total_conf += c / 100.0
                    count += 1
            except (ValueError, IndexError):
                pass
        avg = total_conf / count if count else 0
        return {
            "text": text.strip(),
            "language": "auto",
            "confidence": round(avg, 3),
            "word_count": count,
            "words": words[:50]
        }
    except Exception:
        return None


def _ocr_image(image_path):
    result = _ocr_windows(image_path)
    if result and result.get("text"):
        return result
    result = _ocr_pytesseract(image_path)
    if result and result.get("text"):
        return result
    return {"text": "", "language": "unknown", "confidence": 0, "word_count": 0, "words": [], "error": "No OCR engine available"}


def _format_result(data, source=""):
    text = data.get("text", "")
    conf = data.get("confidence", 0)
    lang = data.get("language", "unknown")
    wc = data.get("word_count", 0)
    header = f"=== OCR Result{': ' + source if source else ''} ==="
    info = f"Language: {lang} | Confidence: {conf:.1%} | Words: {wc}"
    if data.get("error"):
        info += f" | Note: {data['error']}"
    separator = "=" * 50
    return f"{header}\n{info}\n{separator}\n{text}" if text else f"{header}\n{info}\nNo text detected."


def ocr_reader(parameters: dict, player=None) -> str:
    action = parameters.get("action", "read_image")

    if action == "read_image":
        path = parameters.get("path", parameters.get("image", ""))
        if not path:
            return "Error: No image path provided."
        if not os.path.isfile(path):
            return f"Error: File not found: {path}"
        data = _ocr_image(path)
        return _format_result(data, path)

    elif action in ("read_screenshot", "read_from_screen"):
        clipboard_script = """
Add-Type -AssemblyName System.Windows.Forms
$clip = [System.Windows.Forms.Clipboard]::GetImage()
if ($clip) {{
    $path = Join-Path $env:TEMP 'ocr_clipboard.png'
    $clip.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output $path
}} else {{
    Write-Output ''
}}
"""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", clipboard_script],
                capture_output=True, text=True, timeout=10
            )
            clip_path = result.stdout.strip()
            if clip_path and os.path.isfile(clip_path):
                data = _ocr_image(clip_path)
                try:
                    os.remove(clip_path)
                except OSError:
                    pass
                return _format_result(data, "clipboard screenshot")
            return "No image found in clipboard."
        except Exception as e:
            return f"Error reading clipboard: {e}"

    elif action == "read_url":
        url = parameters.get("url", "")
        if not url:
            return "Error: No URL provided."
        try:
            import requests
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            ext = ".png"
            ct = resp.headers.get("Content-Type", "")
            if "jpeg" in ct or "jpg" in ct:
                ext = ".jpg"
            tmp = os.path.join(tempfile.gettempdir(), f"ocr_url{ext}")
            with open(tmp, "wb") as f:
                f.write(resp.content)
            data = _ocr_image(tmp)
            try:
                os.remove(tmp)
            except OSError:
                pass
            return _format_result(data, url)
        except Exception as e:
            return f"Error downloading image: {e}"

    elif action == "languages":
        return ("Idiomas OCR: depende del motor instalado. "
                "Instalá Tesseract (https://github.com/tesseract-ocr/tesseract) y configurá "
                "TESSERACT_CMD para soportar español ('spa') y otros idiomas.")

    return f"Unknown action: {action}. Available: read_image, read_screenshot, read_from_screen, read_url, languages"
