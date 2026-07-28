"""Data analyst module for CSV/Excel data analysis."""

import csv
import json
import os
import statistics
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict


def _detect_type(values: list) -> str:
    int_count = 0
    float_count = 0
    date_count = 0
    total = len(values)
    if total == 0:
        return "text"

    for v in values:
        v = str(v).strip()
        if not v:
            continue
        try:
            int(v)
            int_count += 1
            continue
        except ValueError:
            pass
        try:
            float(v)
            float_count += 1
            continue
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
            try:
                datetime.strptime(v, fmt)
                date_count += 1
                break
            except ValueError:
                continue

    threshold = 0.8
    if int_count / total >= threshold:
        return "integer"
    if (int_count + float_count) / total >= threshold:
        return "number"
    if date_count / total >= threshold:
        return "date"
    return "text"


def _to_number(val: str):
    val = val.strip()
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return None


def _read_csv(file_path: str) -> tuple[list[str], list[dict]]:
    rows = []
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for row in reader:
            rows.append(dict(row))
    return headers, rows


def _read_excel(file_path: str) -> tuple[list[str], list[dict]]:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(next(rows_iter, []))]
        rows = []
        for row in rows_iter:
            row_dict = {}
            for i, h in enumerate(headers):
                val = row[i] if i < len(row) else ""
                row_dict[h] = str(val) if val is not None else ""
            rows.append(row_dict)
        wb.close()
        return headers, rows
    except ImportError:
        raise ImportError("openpyxl not installed. Install with: pip install openpyxl")


def _read_data(file_path: str) -> tuple[list[str], list[dict]]:
    ext = Path(file_path).suffix.lower()
    if ext == ".csv":
        return _read_csv(file_path)
    elif ext in (".xlsx", ".xls"):
        return _read_excel(file_path)
    elif ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            headers = list(data[0].keys()) if isinstance(data[0], dict) else []
            return headers, [dict(row) if isinstance(row, dict) else {"value": row} for row in data]
        return [], []
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def _col_stats(headers: list[str], rows: list[dict], col: str) -> dict:
    values = [r.get(col, "") for r in rows]
    non_empty = [v for v in values if v.strip()]
    col_type = _detect_type(non_empty)

    stats = {
        "column": col,
        "type": col_type,
        "count": len(non_empty),
        "empty": len(values) - len(non_empty),
        "unique": len(set(non_empty)),
    }

    if col_type in ("integer", "number"):
        nums = [_to_number(v) for v in non_empty]
        nums = [n for n in nums if n is not None]
        if nums:
            stats.update({
                "min": min(nums),
                "max": max(nums),
                "mean": round(statistics.mean(nums), 4),
                "median": round(statistics.median(nums), 4),
            })
            try:
                stats["stdev"] = round(statistics.stdev(nums), 4) if len(nums) > 1 else 0
            except statistics.StatisticsError:
                stats["stdev"] = 0
    elif col_type == "text":
        counter = Counter(non_empty)
        stats["top_values"] = counter.most_common(5)
    elif col_type == "date":
        stats["values_sample"] = non_empty[:5]

    return stats


def data_analyst(parameters: dict, player=None) -> str:
    action = parameters.get("action", "analyze")
    file_path = parameters.get("file", "")

    if not file_path and action != "export":
        return "Error: No file path provided. Use 'file' parameter."

    if file_path and not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    if action == "analyze" or action == "summary":
        try:
            headers, rows = _read_data(file_path)
        except Exception as e:
            return f"Error reading file: {e}"

        if not rows:
            return "Error: File is empty or has no data rows."

        lines = [
            f"{'ANALYSIS' if action == 'analyze' else 'SUMMARY'}: {os.path.basename(file_path)}",
            "=" * 60,
            f"Rows: {len(rows)} | Columns: {len(headers)}",
            f"Column list: {', '.join(headers)}",
            ""
        ]

        for col in headers:
            stats = _col_stats(headers, rows, col)
            lines.append(f"  [{stats['type'].upper()}] {col}:")
            lines.append(f"    Count: {stats['count']} | Unique: {stats['unique']} | Empty: {stats['empty']}")
            if "min" in stats:
                lines.append(f"    Min: {stats['min']} | Max: {stats['max']}")
                lines.append(f"    Mean: {stats['mean']} | Median: {stats['median']}")
                if "stdev" in stats:
                    lines.append(f"    StdDev: {stats['stdev']}")
            elif "top_values" in stats:
                top = stats["top_values"]
                top_str = ", ".join(f"'{v}'({c})" for v, c in top)
                lines.append(f"    Top values: {top_str}")
            lines.append("")

        return "\n".join(lines)

    elif action == "filter":
        try:
            headers, rows = _read_data(file_path)
        except Exception as e:
            return f"Error reading file: {e}"

        column = parameters.get("column", "")
        value = parameters.get("value", "")
        op = parameters.get("operator", "eq")

        if not column or column not in headers:
            return f"Error: Column '{column}' not found. Available: {', '.join(headers)}"

        filtered = []
        for row in rows:
            cell = row.get(column, "")
            cell_num = _to_number(cell)
            val_num = _to_number(value)

            match = False
            if op == "eq":
                match = cell.lower() == value.lower() if cell else False
            elif op == "neq":
                match = cell.lower() != value.lower() if cell else True
            elif op in ("gt", "lt", "gte", "lte") and cell_num is not None and val_num is not None:
                if op == "gt":
                    match = cell_num > val_num
                elif op == "lt":
                    match = cell_num < val_num
                elif op == "gte":
                    match = cell_num >= val_num
                elif op == "lte":
                    match = cell_num <= val_num
            elif op == "contains":
                match = value.lower() in cell.lower() if cell else False
            elif op == "startswith":
                match = cell.lower().startswith(value.lower()) if cell else False

            if match:
                filtered.append(row)

        lines = [
            f"Filtered Results: {column} {op} '{value}'",
            f"Matched: {len(filtered)} of {len(rows)} rows",
            "=" * 60,
        ]
        for row in filtered[:30]:
            vals = [f"{k}={v}" for k, v in row.items() if v]
            lines.append("  " + " | ".join(vals))
        if len(filtered) > 30:
            lines.append(f"  ... and {len(filtered) - 30} more rows")
        return "\n".join(lines)

    elif action == "sort":
        try:
            headers, rows = _read_data(file_path)
        except Exception as e:
            return f"Error reading file: {e}"

        column = parameters.get("column", headers[0] if headers else "")
        desc = parameters.get("descending", False)

        if column not in headers:
            return f"Error: Column '{column}' not found. Available: {', '.join(headers)}"

        def sort_key(row):
            val = row.get(column, "")
            num = _to_number(val)
            return (0, num) if num is not None else (1, val.lower())

        rows.sort(key=sort_key, reverse=desc)

        direction = "DESC" if desc else "ASC"
        lines = [
            f"Sorted by {column} ({direction})",
            "=" * 60,
        ]
        for row in rows[:50]:
            vals = [f"{k}={v}" for k, v in row.items() if v]
            lines.append("  " + " | ".join(vals))
        if len(rows) > 50:
            lines.append(f"  ... {len(rows) - 50} more rows")
        return "\n".join(lines)

    elif action == "group":
        try:
            headers, rows = _read_data(file_path)
        except Exception as e:
            return f"Error reading file: {e}"

        column = parameters.get("column", "")
        if column not in headers:
            return f"Error: Column '{column}' not found. Available: {', '.join(headers)}"

        groups = defaultdict(list)
        for row in rows:
            key = row.get(column, "(empty)")
            groups[key].append(row)

        num_col = parameters.get("agg_column", "")
        use_agg = num_col in headers

        lines = [
            f"Grouped by: {column} ({len(groups)} groups)",
            "=" * 60,
        ]
        for key, group_rows in sorted(groups.items(), key=lambda x: -len(x[1])):
            line = f"  '{key}': {len(group_rows)} rows"
            if use_agg:
                nums = [_to_number(r.get(num_col, "")) for r in group_rows]
                nums = [n for n in nums if n is not None]
                if nums:
                    line += f" | {num_col} sum={sum(nums)}, avg={round(statistics.mean(nums), 2)}"
            lines.append(line)
        return "\n".join(lines)

    elif action == "chart":
        try:
            headers, rows = _read_data(file_path)
        except Exception as e:
            return f"Error reading file: {e}"

        x_col = parameters.get("x_column", headers[0] if headers else "")
        y_col = parameters.get("y_column", "")

        if x_col not in headers:
            return f"Error: Column '{x_col}' not found."
        if y_col and y_col not in headers:
            return f"Error: Column '{y_col}' not found."

        lines = [f"Chart Description: {os.path.basename(file_path)}", "=" * 60]

        x_values = [r.get(x_col, "") for r in rows]
        x_type = _detect_type([v for v in x_values if v])

        if y_col:
            groups = defaultdict(list)
            for row in rows:
                k = row.get(x_col, "")
                v = _to_number(row.get(y_col, ""))
                if v is not None:
                    groups[k].append(v)

            lines.append(f"X-axis: {x_col} ({x_type}) | Y-axis: {y_col} (number)")
            lines.append(f"Groups: {len(groups)}")
            lines.append("")
            max_bar = 40
            all_vals = [v for vals in groups.values() for v in vals]
            if all_vals:
                data_max = max(all_vals) if max(all_vals) > 0 else 1
                for k in sorted(groups.keys(), key=lambda x: -statistics.mean(groups[x]))[:15]:
                    avg = statistics.mean(groups[k])
                    bar_len = int((avg / data_max) * max_bar) if data_max else 0
                    bar = "#" * bar_len
                    lines.append(f"  {str(k)[:20]:>20} | {bar} {avg:.1f}")
        else:
            if x_type in ("integer", "number"):
                nums = [_to_number(v) for v in x_values]
                nums = [n for n in nums if n is not None]
                lines.append(f"X-axis: {x_col} (number) | {len(nums)} values")
                if nums:
                    lines.append(f"Range: {min(nums)} to {max(nums)}")
                    lines.append(f"Mean: {statistics.mean(nums):.2f} | Median: {statistics.median(nums):.2f}")
            else:
                counter = Counter(x_values)
                lines.append(f"X-axis: {x_col} (categorical) | {len(counter)} categories")
                total = len(x_values)
                for k, c in counter.most_common(15):
                    pct = (c / total * 100) if total else 0
                    bar_len = int(pct / 2)
                    bar = "#" * bar_len
                    lines.append(f"  {str(k)[:25]:>25} | {bar} {c} ({pct:.1f}%)")

        return "\n".join(lines)

    elif action == "compare":
        file2 = parameters.get("file2", "")
        if not file2:
            return "Error: 'file2' parameter required for comparison."
        if not os.path.exists(file2):
            return f"Error: File2 not found: {file2}"

        try:
            h1, r1 = _read_data(file_path)
            h2, r2 = _read_data(file2)
        except Exception as e:
            return f"Error reading files: {e}"

        lines = [
            f"Comparing: {os.path.basename(file_path)} vs {os.path.basename(file2)}",
            "=" * 60,
            f"File 1: {len(r1)} rows, {len(h1)} columns",
            f"File 2: {len(r2)} rows, {len(h2)} columns",
            "",
            "Column Comparison:",
        ]
        common = set(h1) & set(h2)
        only1 = set(h1) - set(h2)
        only2 = set(h2) - set(h1)
        lines.append(f"  Common: {', '.join(sorted(common)) or 'None'}")
        if only1:
            lines.append(f"  Only in File 1: {', '.join(sorted(only1))}")
        if only2:
            lines.append(f"  Only in File 2: {', '.join(sorted(only2))}")

        for col in sorted(common):
            s1 = _col_stats(h1, r1, col)
            s2 = _col_stats(h2, r2, col)
            lines.append(f"\n  {col}:")
            lines.append(f"    File1: count={s1['count']}, unique={s1['unique']}")
            lines.append(f"    File2: count={s2['count']}, unique={s2['unique']}")
            if "mean" in s1 and "mean" in s2:
                lines.append(f"    File1: mean={s1['mean']}, min={s1['min']}, max={s1['max']}")
                lines.append(f"    File2: mean={s2['mean']}, min={s2['min']}, max={s2['max']}")

        return "\n".join(lines)

    elif action == "export":
        source = parameters.get("source", "")
        output = parameters.get("output", "")
        fmt = parameters.get("format", "json")

        if not source or not os.path.exists(source):
            return f"Error: Source file not found: {source}"
        if not output:
            return "Error: 'output' parameter required."

        try:
            headers, rows = _read_data(source)
        except Exception as e:
            return f"Error reading source: {e}"

        output = os.path.expanduser(output)
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

        if fmt == "json":
            with open(output, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2, ensure_ascii=False, default=str)
        elif fmt == "csv":
            with open(output, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
        elif fmt == "txt":
            with open(output, "w", encoding="utf-8") as f:
                f.write("\t".join(headers) + "\n")
                f.write("-" * 80 + "\n")
                for row in rows:
                    vals = [row.get(h, "") for h in headers]
                    f.write("\t".join(vals) + "\n")
        else:
            return f"Error: Unknown format '{fmt}'. Use: json, csv, txt"

        return f"Exported {len(rows)} rows to {output} ({fmt})"

    else:
        return (
            f"Error: Unknown action '{action}'. Available:\n"
            "  analyze, summary, filter, sort, group, chart, compare, export"
        )
