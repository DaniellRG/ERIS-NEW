"""
data_visualize.py - Generacion de graficos PNG desde CSV/Excel/JSON sin dependencias pesadas.

Usa solo PIL (ya en el proyecto) para dibujar: bar, line, pie, hist, scatter.
Los graficos se guardan en data/generated/ y se devuelve la ruta + resumen estadistico.
Complementa a data_analyst (que analiza) con visualizacion real.
"""
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

_BASE = Path(__file__).resolve().parent.parent
_GEN_DIR = _BASE / "data" / "generated"

sys_path_added = False


def _ensure_reader():
    import sys
    global sys_path_added
    if not sys_path_added:
        sys.path.insert(0, str(_BASE))
        sys_path_added = True
    try:
        from actions.data_analyst import _read_data, _detect_type, _to_number
        return _read_data, _detect_type, _to_number
    except Exception:
        return None, None, None


def _load_data(file_path):
    read_data, _, _ = _ensure_reader()
    if read_data is None:
        raise RuntimeError("No se pudo importar data_analyst")
    headers, rows = read_data(file_path)
    if not rows:
        raise RuntimeError("El archivo no tiene datos")
    return headers, rows


def _numeric_series(headers, rows, col):
    _, _, to_number = _ensure_reader()
    if col not in headers:
        raise RuntimeError(f"Columna '{col}' no existe. Disponibles: {', '.join(headers)}")
    vals = []
    for r in rows:
        n = to_number(r.get(col, ""))
        if n is not None:
            vals.append(n)
    if not vals:
        raise RuntimeError(f"Columna '{col}' no tiene valores numericos")
    return vals


def _categorical_series(headers, rows, col):
    if col not in headers:
        raise RuntimeError(f"Columna '{col}' no existe. Disponibles: {', '.join(headers)}")
    return [str(r.get(col, "")).strip() or "(vacío)" for r in rows]


def _font(size):
    """Tipografia: usa DejaVuSans si existe, si no la default."""
    try:
        from PIL import ImageFont
        candidates = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\consola.ttf",
        ]
        for c in candidates:
            if os.path.exists(c):
                return ImageFont.truetype(c, size)
    except Exception:
        pass
    return ImageFont.load_default()


def _draw_bar(img, labels, values, title, color="#FFC000"):
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline=(255, 192, 0), width=2)
    draw.text((20, 15), title[:60], fill=(240, 240, 240), font=_font(16))

    n = max(len(labels), 1)
    x0, y0, x1, y1 = 70, 60, w - 40, h - 50
    vmin, vmax = min(values + [0]), max(values + [0])
    rng = (vmax - vmin) or 1
    bw = max(6, int((x1 - x0) / n * 0.7))
    for i, (lab, val) in enumerate(zip(labels, values)):
        x = x0 + i * (x1 - x0) / n + ((x1 - x0) / n - bw) / 2
        bh = (val - vmin) / rng * (y1 - y0)
        y = y1 - bh
        draw.rectangle([x, y, x + bw, y1], fill=tuple(int(color.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4)))
        draw.text((x, y1 + 6), str(lab)[:10], fill=(200, 200, 200), font=_font(9))
    # grid + labels de valores
    for g in range(5):
        gy = y1 - g * (y1 - y0) / 4
        draw.line([x0, gy, x1, gy], fill=(70, 70, 70))
        val = vmin + g * rng / 4
        draw.text((6, gy - 6), f"{val:.0f}", fill=(150, 150, 150), font=_font(10))
    draw.line([x0, y1, x1, y1], fill=(200, 200, 200), width=2)
    draw.line([x0, y0, x0, y1], fill=(200, 200, 200), width=2)


def _draw_line(img, labels, values, title, color="#00C8FF"):
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline=(255, 192, 0), width=2)
    draw.text((20, 15), title[:60], fill=(240, 240, 240), font=_font(16))

    x0, y0, x1, y1 = 70, 60, w - 40, h - 50
    vmin, vmax = min(values), max(values)
    rng = (vmax - vmin) or 1
    n = max(len(values), 2)
    for g in range(5):
        gy = y1 - g * (y1 - y0) / 4
        draw.line([x0, gy, x1, gy], fill=(70, 70, 70))
        val = vmin + g * rng / 4
        draw.text((6, gy - 6), f"{val:.0f}", fill=(150, 150, 150), font=_font(10))
    prev = None
    for i, (lab, val) in enumerate(zip(labels, values)):
        x = x0 + i * (x1 - x0) / (n - 1)
        y = y1 - (val - vmin) / rng * (y1 - y0)
        r = 3
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(0, 200, 255))
        if prev:
            draw.line([prev[0], prev[1], x, y], fill=(0, 200, 255), width=2)
        prev = (x, y)
        if i % max(1, n // 8) == 0:
            draw.text((x, y1 + 6), str(lab)[:8], fill=(200, 200, 200), font=_font(9))
    draw.line([x0, y1, x1, y1], fill=(200, 200, 200), width=2)
    draw.line([x0, y0, x0, y1], fill=(200, 200, 200), width=2)


def _draw_pie(img, labels, values, title):
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline=(255, 192, 0), width=2)
    draw.text((20, 15), title[:60], fill=(240, 240, 240), font=_font(16))

    cx, cy = w // 2, h // 2 + 10
    radius = min(w, h) // 3
    total = sum(values) or 1
    palette = [(255, 192, 0), (0, 200, 255), (0, 200, 120), (255, 120, 120),
               (200, 120, 255), (120, 160, 255), (255, 180, 60), (120, 220, 180)]
    start = -90
    legend_y = 20
    for i, (lab, val) in enumerate(zip(labels, values)):
        sweep = val / total * 360
        color = palette[i % len(palette)]
        draw.pieslice([cx - radius, cy - radius, cx + radius, cy + radius],
                      start=start, end=start + sweep, fill=color, outline=(10, 12, 18))
        start += sweep
        pct = val / total * 100
        if pct >= 4:
            draw.ellipse([15, legend_y, 25, legend_y + 10], fill=color)
            draw.text((30, legend_y), f"{str(lab)[:26]}: {val} ({pct:.1f}%)",
                      fill=(220, 220, 220), font=_font(10))
            legend_y += 16


def _draw_hist(img, values, title):
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline=(255, 192, 0), width=2)
    draw.text((20, 15), title[:60], fill=(240, 240, 240), font=_font(16))

    bins = 12
    vmin, vmax = min(values), max(values)
    rng = (vmax - vmin) or 1
    hist, edges = [0] * bins, []
    for i in range(bins):
        lo = vmin + i * rng / bins
        hi = vmin + (i + 1) * rng / bins
        edges.append(lo)
        count = sum(1 for v in values if lo <= v < (hi if i < bins - 1 else vmax + 1))
        hist[i] = count
    edges.append(vmax)

    x0, y0, x1, y1 = 70, 60, w - 40, h - 50
    max_count = max(hist + [1])
    bw = (x1 - x0) / bins
    for i, cnt in enumerate(hist):
        x = x0 + i * bw
        bh = cnt / max_count * (y1 - y0)
        draw.rectangle([x + 1, y1 - bh, x + bw - 1, y1], fill=(255, 192, 0))
        if i % 2 == 0:
            draw.text((x, y1 + 6), f"{edges[i]:.0f}", fill=(180, 180, 180), font=_font(8))
    draw.line([x0, y1, x1, y1], fill=(200, 200, 200), width=2)
    draw.line([x0, y0, x0, y1], fill=(200, 200, 200), width=2)
    for g in range(5):
        gy = y1 - g * (y1 - y0) / 4
        draw.line([x0, gy, x1, gy], fill=(70, 70, 70))


def _draw_scatter(img, xs, ys, title):
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline=(255, 192, 0), width=2)
    draw.text((20, 15), title[:60], fill=(240, 240, 240), font=_font(16))

    x0, y0, x1, y1 = 70, 60, w - 40, h - 50
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xr = (xmax - xmin) or 1
    yr = (ymax - ymin) or 1
    for g in range(5):
        gy = y1 - g * (y1 - y0) / 4
        draw.line([x0, gy, x1, gy], fill=(70, 70, 70))
    for px, py in zip(xs, ys):
        x = x0 + (px - xmin) / xr * (x1 - x0)
        y = y1 - (py - ymin) / yr * (y1 - y0)
        r = 4
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(0, 200, 255), outline=(10, 12, 18))
    draw.line([x0, y1, x1, y1], fill=(200, 200, 200), width=2)
    draw.line([x0, y0, x0, y1], fill=(200, 200, 200), width=2)


def _summary_text(headers, rows, col):
    _, _, to_number = _ensure_reader()
    if col not in headers:
        return f"  Sin estadisticas para '{col}'"
    vals = [to_number(r.get(col, "")) for r in rows]
    nums = [v for v in vals if v is not None]
    lines = [f"  Columna: {col}"]
    lines.append(f"  Filas: {len(rows)} | Valores numericos: {len(nums)}")
    if nums:
        lines.append(f"  Min: {min(nums)} | Max: {max(nums)}")
        lines.append(f"  Promedio: {statistics.mean(nums):.2f} | Mediana: {statistics.median(nums):.2f}")
        if len(nums) > 1:
            try:
                lines.append(f"  Desvio estandar: {statistics.stdev(nums):.2f}")
            except statistics.StatisticsError:
                pass
    return "\n".join(lines)


def data_visualize(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action") or "chart").lower().strip()
    file_path = params.get("file") or params.get("path") or ""

    if action == "status":
        return ("data_visualize activo (graficos PNG via PIL).\n  Tipos: bar, line, pie, hist, scatter\n"
                "  Params: file (ruta CSV/Excel/JSON), x (columna X), y (columna Y), type, title, color, out")

    if action in ("list", "dir"):
        if not _GEN_DIR.exists():
            return "No hay graficos generados aun"
        files = sorted(_GEN_DIR.glob("*.png"))
        if not files:
            return "No hay graficos generados aun"
        return "Graficos generados:\n  " + "\n  ".join(f"{f.name} ({f.stat().st_size // 1024}KB)" for f in files[-20:])

    if action == "open":
        name = params.get("name") or params.get("file") or ""
        if not name:
            return "Error: se requiere 'name' del PNG"
        target = _GEN_DIR / name if not os.path.sep in name else Path(name)
        if not target.exists():
            return f"Grafico no encontrado: {target}"
        try:
            os.startfile(str(target))
            return f"Abierto: {target}"
        except Exception as e:
            return f"Error abriendo: {e}"

    if not file_path:
        return "Error: se requiere 'file' (ruta CSV/Excel/JSON)"
    if not os.path.isfile(file_path):
        return f"Error: archivo no encontrado: {file_path}"
    if not HAS_PIL:
        return "Error: PIL no instalado (pip install pillow)"

    try:
        headers, rows = _load_data(file_path)
    except Exception as e:
        return f"Error leyendo archivo: {e}"

    chart_type = str(params.get("type") or params.get("chart") or "bar").lower().strip()
    x_col = params.get("x") or params.get("x_column") or (headers[0] if headers else "")
    y_col = params.get("y") or params.get("y_column") or ""
    title = params.get("title") or f"{chart_type.upper()} de {os.path.basename(file_path)}"
    color = params.get("color", "#FFC000")
    out_name = params.get("out") or f"viz_{chart_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    if chart_type == "bar":
        labels = _categorical_series(headers, rows, x_col)
        counts = Counter(labels)
        top = counts.most_common(15)
        lab = [str(k)[:18] for k, _ in top]
        val = [float(v) for _, v in top]
        img = Image.new("RGB", (800, 500), (14, 17, 26))
        _draw_bar(img, lab, val, title, color)
        stat = f"  {len(counts)} categorias en '{x_col}'; mostrando top {len(top)}"
    elif chart_type == "line":
        y_vals = _numeric_series(headers, rows, y_col or x_col)
        lab = [str(r.get(x_col, i))[:12] for i, r in enumerate(rows)]
        lab = lab[:100]
        img = Image.new("RGB", (800, 500), (14, 17, 26))
        _draw_line(img, lab, y_vals[:100], title, color)
        stat = f"  Serie de {len(y_vals)} puntos de '{y_col or x_col}'"
    elif chart_type == "pie":
        labels = _categorical_series(headers, rows, x_col)
        counts = Counter(labels)
        top = counts.most_common(10)
        lab = [str(k)[:24] for k, _ in top]
        val = [float(v) for _, v in top]
        img = Image.new("RGB", (800, 500), (14, 17, 26))
        _draw_pie(img, lab, val, title)
        stat = f"  {len(counts)} categorias en '{x_col}'; mostrando top {len(top)}"
    elif chart_type in ("hist", "histogram"):
        vals = _numeric_series(headers, rows, x_col)
        img = Image.new("RGB", (800, 500), (14, 17, 26))
        _draw_hist(img, vals, title)
        stat = f"  Histograma de {len(vals)} valores de '{x_col}'"
    elif chart_type in ("scatter", "dispersion"):
        xs = _numeric_series(headers, rows, x_col)
        ys = _numeric_series(headers, rows, y_col) if y_col else xs
        if len(xs) > 500:
            xs, ys = xs[:500], ys[:500]
        img = Image.new("RGB", (800, 500), (14, 17, 26))
        _draw_scatter(img, xs, ys, title)
        stat = f"  Scatter {len(xs)} puntos: x='{x_col}', y='{y_col or x_col}'"
    else:
        return f"Tipo desconocido: {chart_type}. Usa: bar, line, pie, hist, scatter"

    _GEN_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _GEN_DIR / out_name
    img.save(str(out_path), format="PNG")

    if y_col and chart_type in ("line", "scatter"):
        summary = _summary_text(headers, rows, y_col)
    else:
        summary = _summary_text(headers, rows, x_col)

    return (f"Grafico generado: {out_path} ({out_path.stat().st_size // 1024}KB)\n"
            f"{stat}\n"
            f"{summary}\n"
            f"Para verlo: action=open name={out_name}")
