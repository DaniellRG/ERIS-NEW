"""
actions/data_viz.py — Data visualization for ERIS.
Generate charts, graphs, and visual reports.
"""
import json
import os
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_OUTPUT_DIR = _BASE / "data" / "charts"

def _ensure_output():
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def data_viz(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "status":
        _ensure_output()
        chart_count = len(list(_OUTPUT_DIR.glob("*.png"))) + len(list(_OUTPUT_DIR.glob("*.html")))
        return (
            f"Data Viz Status:\n"
            f"  Output directory: {_OUTPUT_DIR}\n"
            f"  Charts generated: {chart_count}\n"
            f"  Available: bar, line, pie, scatter, heatmap, histogram, table"
        )

    elif action == "bar":
        return _create_bar_chart(params)
    elif action == "line":
        return _create_line_chart(params)
    elif action == "pie":
        return _create_pie_chart(params)
    elif action == "scatter":
        return _create_scatter_chart(params)
    elif action == "histogram":
        return _create_histogram(params)
    elif action == "table":
        return _create_table(params)
    elif action == "system_report":
        return _system_report()
    elif action == "usage_report":
        return _usage_report()
    elif action == "list_charts":
        _ensure_output()
        charts = sorted(_OUTPUT_DIR.glob("*.*"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not charts:
            return "No charts generated yet."
        lines = [f"Charts ({len(charts)}):"]
        for c in charts[:20]:
            size = c.stat().st_size
            size_str = f"{size / 1024:.1f}KB"
            lines.append(f"  {c.name} ({size_str})")
        return "\n".join(lines)

    return "Actions: status, bar, line, pie, scatter, histogram, table, system_report, usage_report, list_charts"


def _create_bar_chart(params):
    title = params.get("title", "Bar Chart")
    labels = params.get("labels", [])
    values = params.get("values", [])
    if not labels or not values:
        return "Requires 'labels' and 'values' lists."
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _ensure_output()
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = plt.cm.Set2(range(len(labels)))
        bars = ax.bar(range(len(labels)), [float(v) for v in values], color=colors)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_title(title)
        ax.set_ylabel(params.get("ylabel", "Value"))

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(val),
                    ha="center", va="bottom", fontsize=9)

        plt.tight_layout()
        fname = f"bar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = _OUTPUT_DIR / fname
        plt.savefig(str(path), dpi=150)
        plt.close()
        return f"Bar chart saved: {path.name} ({len(labels)} categories)"
    except ImportError:
        return _create_html_chart("bar", title, labels, values)


def _create_line_chart(params):
    title = params.get("title", "Line Chart")
    labels = params.get("labels", [])
    values = params.get("values", [])
    if not labels or not values:
        return "Requires 'labels' and 'values' lists."
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _ensure_output()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(range(len(labels)), [float(v) for v in values], marker="o", linewidth=2, color="#2196F3")
        ax.fill_between(range(len(labels)), [float(v) for v in values], alpha=0.1, color="#2196F3")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_title(title)
        ax.set_ylabel(params.get("ylabel", "Value"))
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fname = f"line_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = _OUTPUT_DIR / fname
        plt.savefig(str(path), dpi=150)
        plt.close()
        return f"Line chart saved: {path.name}"
    except ImportError:
        return _create_html_chart("line", title, labels, values)


def _create_pie_chart(params):
    title = params.get("title", "Pie Chart")
    labels = params.get("labels", [])
    values = params.get("values", [])
    if not labels or not values:
        return "Requires 'labels' and 'values' lists."
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _ensure_output()
        fig, ax = plt.subplots(figsize=(8, 8))
        colors = plt.cm.Pastel1(range(len(labels)))
        wedges, texts, autotexts = ax.pie(
            [float(v) for v in values], labels=labels, autopct="%1.1f%%",
            colors=colors, startangle=90
        )
        ax.set_title(title)

        plt.tight_layout()
        fname = f"pie_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = _OUTPUT_DIR / fname
        plt.savefig(str(path), dpi=150)
        plt.close()
        return f"Pie chart saved: {path.name}"
    except ImportError:
        return _create_html_chart("pie", title, labels, values)


def _create_scatter_chart(params):
    title = params.get("title", "Scatter Plot")
    x = params.get("x", [])
    y = params.get("y", [])
    if not x or not y:
        return "Requires 'x' and 'y' lists."
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _ensure_output()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter([float(v) for v in x], [float(v) for v in y], alpha=0.7, s=60, color="#FF5722")
        ax.set_title(title)
        ax.set_xlabel(params.get("xlabel", "X"))
        ax.set_ylabel(params.get("ylabel", "Y"))
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fname = f"scatter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = _OUTPUT_DIR / fname
        plt.savefig(str(path), dpi=150)
        plt.close()
        return f"Scatter plot saved: {path.name}"
    except ImportError:
        return "matplotlib not installed. Install with: pip install matplotlib"


def _create_histogram(params):
    title = params.get("title", "Histogram")
    values = params.get("values", [])
    if not values:
        return "Requires 'values' list."
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _ensure_output()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist([float(v) for v in values], bins=int(params.get("bins", 10)), color="#4CAF50", alpha=0.7, edgecolor="white")
        ax.set_title(title)
        ax.set_xlabel(params.get("xlabel", "Value"))
        ax.set_ylabel(params.get("ylabel", "Frequency"))
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fname = f"hist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = _OUTPUT_DIR / fname
        plt.savefig(str(path), dpi=150)
        plt.close()
        return f"Histogram saved: {path.name}"
    except ImportError:
        return "matplotlib not installed."


def _create_table(params):
    title = params.get("title", "Data Table")
    headers = params.get("headers", [])
    rows = params.get("rows", [])
    if not headers or not rows:
        return "Requires 'headers' and 'rows'."

    lines = [f"=== {title} ==="]
    header_str = " | ".join(str(h) for h in headers)
    lines.append(header_str)
    lines.append("-" * len(header_str))
    for row in rows:
        lines.append(" | ".join(str(c) for c in row))
    return "\n".join(lines)


def _create_html_chart(chart_type, title, labels, values):
    _ensure_output()
    fname = f"{chart_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    path = _OUTPUT_DIR / fname

    labels_js = json.dumps(labels)
    values_js = json.dumps([float(v) for v in values])

    html = f"""<!DOCTYPE html>
<html><head><title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{{font-family:sans-serif;margin:20px;background:#1a1a2e;color:#fff}}
canvas{{max-width:800px;margin:auto}}</style></head>
<body><h2>{title}</h2>
<canvas id="chart"></canvas>
<script>
new Chart(document.getElementById('chart'),{{
  type: '{chart_type}',
  data: {{ labels: {labels_js}, datasets: [{{ label: '{title}', data: {values_js},
    backgroundColor: ['#4CAF50','#2196F3','#FF9800','#E91E63','#9C27B0','#00BCD4','#FF5722','#607D8B'] }}] }},
  options: {{ responsive: true, plugins: {{ title: {{ display: true, text: '{title}' }} }} }}
}});
</script></body></html>"""

    path.write_text(html, encoding="utf-8")
    return f"HTML chart saved: {path.name} (open in browser)"


def _system_report():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        labels = ["CPU %", "Memory %", "Disk %"]
        values = [cpu, mem.percent, disk.percent]
        return _create_bar_chart({
            "title": "System Health",
            "labels": labels,
            "values": values,
            "ylabel": "Percentage",
        })
    except ImportError:
        return "psutil not installed. Install with: pip install psutil"


def _usage_report():
    try:
        from pathlib import Path
        analytics_file = Path(_BASE) / "data" / "usage_analytics.json"
        if not analytics_file.exists():
            return "No usage data yet. Use 'usage_analytics' tool first."
        data = json.loads(analytics_file.read_text(encoding="utf-8"))
        tool_calls = data.get("tool_calls", {})
        if not tool_calls:
            return "No tool usage data."
        sorted_tools = sorted(tool_calls.items(), key=lambda x: x[1], reverse=True)[:10]
        labels = [t[0] for t in sorted_tools]
        values = [t[1] for t in sorted_tools]
        return _create_bar_chart({
            "title": "Top 10 Tool Usage",
            "labels": labels,
            "values": values,
            "ylabel": "Calls",
        })
    except Exception as e:
        return f"Error generating usage report: {e}"
