"""
actions/chart_generator.py — Generate charts and graphs with matplotlib for ERIS.
Actions:
  bar        — Bar chart
  line       — Line chart
  pie        — Pie chart
  scatter    — Scatter plot
  histogram  — Histogram
  compare    — Multiple series comparison
  list       — List generated charts

Storage: D:/Eris_Source/data/charts/
Uses matplotlib with Agg backend (non-interactive). Saves as PNG.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

_BASE_DIR = Path(__file__).resolve().parent.parent
_OUTPUT_DIR = _BASE_DIR / "data" / "charts"


def _ensure_dir():
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _parse_list(val) -> list:
    """Parse a value that might be a JSON string list, comma-separated, or actual list."""
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return []
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return [x.strip() for x in val.split(",") if x.strip()]
    return []


def _parse_numbers(val) -> list[float]:
    """Parse a list of numbers from various input formats."""
    items = _parse_list(val)
    result = []
    for item in items:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            continue
    return result


def _output_path(chart_type: str, output: str = "") -> str:
    """Generate output path for a chart."""
    _ensure_dir()
    if output:
        p = Path(output)
        if not p.is_absolute():
            p = _OUTPUT_DIR / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(_OUTPUT_DIR / f"{chart_type}_{timestamp}.png")


def _apply_style(fig, ax, title: str):
    """Apply consistent styling to a chart."""
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, alpha=0.3, linestyle="--")
    fig.tight_layout()


def _save(fig, path: str) -> str:
    """Save figure and return result message."""
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    size_kb = Path(path).stat().st_size / 1024
    return f"Gráfico guardado: {path} ({size_kb:.0f} KB)"


def chart_generator(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "bar")).strip().lower()

    if player:
        try:
            player.write_log(f"[ChartGen] action={action}")
        except Exception:
            pass

    if action == "bar":
        return _bar(params)
    elif action == "line":
        return _line(params)
    elif action == "pie":
        return _pie(params)
    elif action == "scatter":
        return _scatter(params)
    elif action == "histogram":
        return _histogram(params)
    elif action == "compare":
        return _compare(params)
    elif action == "list":
        return _list_charts()
    return "Actions: bar, line, pie, scatter, histogram, compare, list"


def _bar(params: dict) -> str:
    title = str(params.get("title", "Gráfico de Barras")).strip()
    labels = _parse_list(params.get("labels", []))
    values = _parse_numbers(params.get("values", []))
    output = str(params.get("output", "")).strip()
    color = str(params.get("color", "#4A90D9")).strip()

    if not labels or not values:
        return "Faltan 'labels' y 'values' para el gráfico de barras."
    if len(labels) != len(values):
        return f"labels ({len(labels)}) y values ({len(values)}) deben tener la misma cantidad."

    path = _output_path("bar", output)
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(range(len(labels)), values, color=color, edgecolor="white", linewidth=0.5)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0, ha="right")
        _apply_style(fig, ax, title)

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.01,
                    f"{val:,.0f}", ha="center", va="bottom", fontsize=9)

        return _save(fig, path)
    except Exception as e:
        plt.close("all")
        return f"Error creando gráfico de barras: {e}"


def _line(params: dict) -> str:
    title = str(params.get("title", "Gráfico de Líneas")).strip()
    labels = _parse_list(params.get("labels", []))
    values = _parse_numbers(params.get("values", []))
    output = str(params.get("output", "")).strip()
    color = str(params.get("color", "#4A90D9")).strip()

    if not labels or not values:
        return "Faltan 'labels' y 'values' para el gráfico de líneas."
    if len(labels) != len(values):
        return f"labels ({len(labels)}) y values ({len(values)}) deben coincidir."

    path = _output_path("line", output)
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(range(len(labels)), values, color=color, linewidth=2, marker="o",
                markersize=6, markerfacecolor="white", markeredgecolor=color)
        ax.fill_between(range(len(labels)), values, alpha=0.1, color=color)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0, ha="right")
        _apply_style(fig, ax, title)

        return _save(fig, path)
    except Exception as e:
        plt.close("all")
        return f"Error creando gráfico de líneas: {e}"


def _pie(params: dict) -> str:
    title = str(params.get("title", "Gráfico Circular")).strip()
    labels = _parse_list(params.get("labels", []))
    values = _parse_numbers(params.get("values", []))
    output = str(params.get("output", "")).strip()

    if not labels or not values:
        return "Faltan 'labels' y 'values' para el gráfico circular."
    if len(labels) != len(values):
        return f"labels ({len(labels)}) y values ({len(values)}) deben coincidir."

    colors_palette = [
        "#4A90D9", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6",
        "#1ABC9C", "#E67E22", "#3498DB", "#E91E63", "#00BCD4",
    ]

    path = _output_path("pie", output)
    try:
        fig, ax = plt.subplots(figsize=(8, 8))
        colors = colors_palette[:len(labels)]
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, colors=colors, autopct="%1.1f%%",
            startangle=90, pctdistance=0.85,
            wedgeprops=dict(width=0.4, edgecolor="white", linewidth=2),
        )
        for text in autotexts:
            text.set_fontsize(9)
            text.set_fontweight("bold")
        if title:
            ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
        fig.tight_layout()

        return _save(fig, path)
    except Exception as e:
        plt.close("all")
        return f"Error creando gráfico circular: {e}"


def _scatter(params: dict) -> str:
    title = str(params.get("title", "Scatter Plot")).strip()
    x_values = _parse_numbers(params.get("x_values", params.get("values", [])))
    y_values = _parse_numbers(params.get("y_values", []))
    output = str(params.get("output", "")).strip()
    color = str(params.get("color", "#4A90D9")).strip()

    if not x_values or not y_values:
        return "Faltan 'x_values' y 'y_values' para el scatter plot."
    if len(x_values) != len(y_values):
        return f"x_values ({len(x_values)}) y y_values ({len(y_values)}) deben coincidir."

    path = _output_path("scatter", output)
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(x_values, y_values, color=color, s=80, alpha=0.7,
                   edgecolors="white", linewidth=1.5, zorder=3)
        _apply_style(fig, ax, title)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")

        return _save(fig, path)
    except Exception as e:
        plt.close("all")
        return f"Error creando scatter plot: {e}"


def _histogram(params: dict) -> str:
    title = str(params.get("title", "Histograma")).strip()
    values = _parse_numbers(params.get("values", []))
    bins = int(params.get("bins", 10))
    output = str(params.get("output", "")).strip()
    color = str(params.get("color", "#4A90D9")).strip()

    if not values:
        return "Falta 'values' para el histograma."

    path = _output_path("hist", output)
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(values, bins=max(1, bins), color=color, edgecolor="white",
                linewidth=0.5, alpha=0.85)
        _apply_style(fig, ax, title)
        ax.set_xlabel("Valor")
        ax.set_ylabel("Frecuencia")

        return _save(fig, path)
    except Exception as e:
        plt.close("all")
        return f"Error creando histograma: {e}"


def _compare(params: dict) -> str:
    title = str(params.get("title", "Comparación")).strip()
    labels = _parse_list(params.get("labels", []))
    series_raw = params.get("series", [])
    output = str(params.get("output", "")).strip()

    if not isinstance(series_raw, list):
        try:
            series_raw = json.loads(str(series_raw)) if series_raw else []
        except Exception:
            series_raw = []

    if not series_raw or not labels:
        return "Faltan 'labels' y 'series' (array de {name, values}) para comparar."

    colors_palette = [
        "#4A90D9", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6",
        "#1ABC9C", "#E67E22", "#3498DB",
    ]

    path = _output_path("compare", output)
    try:
        fig, ax = plt.subplots(figsize=(12, 7))
        x = range(len(labels))

        for i, s in enumerate(series_raw):
            if isinstance(s, dict):
                name = s.get("name", f"Serie {i + 1}")
                vals = _parse_numbers(s.get("values", []))
            elif isinstance(s, list):
                name = f"Serie {i + 1}"
                vals = _parse_numbers(s)
            else:
                continue

            if not vals:
                continue
            color = colors_palette[i % len(colors_palette)]
            ax.plot(x, vals, color=color, linewidth=2, marker="o",
                    markersize=5, label=name)

        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0, ha="right")
        ax.legend(loc="best", fontsize=9)
        _apply_style(fig, ax, title)

        return _save(fig, path)
    except Exception as e:
        plt.close("all")
        return f"Error creando comparación: {e}"


def _list_charts() -> str:
    _ensure_dir()
    charts = sorted(_OUTPUT_DIR.glob("*.*"), key=lambda f: f.stat().st_mtime, reverse=True)
    charts = [c for c in charts if c.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg", ".html")]

    if not charts:
        return "No hay gráficos generados aún."

    lines = [f"Gráficos generados ({len(charts)}):\n"]
    for c in charts[:20]:
        size_kb = c.stat().st_size / 1024
        mtime = datetime.fromtimestamp(c.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"  {c.name} ({size_kb:.0f} KB) — {mtime}")
    return "\n".join(lines)
