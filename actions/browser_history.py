"""Browser history module for reading Chrome/Edge history and bookmarks."""

import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta


def _get_chrome_history_path() -> str:
    local = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local, "Google", "Chrome", "User Data", "Default", "History")


def _get_edge_history_path() -> str:
    local = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "History")


def _get_chrome_bookmarks_path() -> str:
    local = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local, "Google", "Chrome", "User Data", "Default", "Bookmarks")


def _get_edge_bookmarks_path() -> str:
    local = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Bookmarks")


def _chrome_time_to_datetime(chrome_timestamp: int) -> str:
    if not chrome_timestamp:
        return "unknown"
    epoch_start = datetime(1601, 1, 1)
    try:
        dt = epoch_start + timedelta(microseconds=chrome_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OverflowError):
        return "unknown"


def _read_sqlite_copy(db_path: str) -> tuple[sqlite3.Connection | None, str | None]:
    if not os.path.exists(db_path):
        return None, f"Database not found: {db_path}"

    try:
        tmp = tempfile.mktemp(suffix=".db")
        shutil.copy2(db_path, tmp)
        conn = sqlite3.connect(tmp)
        return conn, None
    except PermissionError:
        return None, f"Cannot access {db_path}. Close the browser first."
    except Exception as e:
        return None, f"Error copying database: {e}"


def _get_bookmarks_recursive(data: dict, bookmarks: list):
    if isinstance(data, dict):
        if data.get("type") == "url":
            bookmarks.append({
                "name": data.get("name", ""),
                "url": data.get("url", ""),
                "date_added": _chrome_time_to_datetime(data.get("date_added", 0))
            })
        for key, val in data.items():
            if isinstance(val, (dict, list)):
                _get_bookmarks_recursive(val, bookmarks)
    elif isinstance(data, list):
        for item in data:
            _get_bookmarks_recursive(item, bookmarks)


def browser_history(parameters: dict, player=None) -> str:
    action = parameters.get("action", "chrome")
    limit = parameters.get("limit", 50)

    if action == "chrome":
        db_path = _get_chrome_history_path()
        conn, err = _read_sqlite_copy(db_path)
        if err:
            return f"Error: {err}"

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT url, title, visit_count, last_visit_time FROM urls "
                "ORDER BY last_visit_time DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
        except sqlite3.OperationalError as e:
            conn.close()
            return f"Error reading Chrome history: {e}"

        conn.close()

        if not rows:
            return "No Chrome history found."

        lines = [f"Chrome History (last {len(rows)} entries):", "=" * 70]
        for i, (url, title, visits, ts) in enumerate(rows, 1):
            dt = _chrome_time_to_datetime(ts)
            title_short = (title or "No title")[:50]
            url_short = url[:60] + ("..." if len(url) > 60 else "")
            lines.append(f"  {i:3d}. [{dt}] ({visits} visits) {title_short}")
            lines.append(f"       {url_short}")
        return "\n".join(lines)

    elif action == "edge":
        db_path = _get_edge_history_path()
        conn, err = _read_sqlite_copy(db_path)
        if err:
            return f"Error: {err}"

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT url, title, visit_count, last_visit_time FROM urls "
                "ORDER BY last_visit_time DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
        except sqlite3.OperationalError as e:
            conn.close()
            return f"Error reading Edge history: {e}"

        conn.close()

        if not rows:
            return "No Edge history found."

        lines = [f"Edge History (last {len(rows)} entries):", "=" * 70]
        for i, (url, title, visits, ts) in enumerate(rows, 1):
            dt = _chrome_time_to_datetime(ts)
            title_short = (title or "No title")[:50]
            url_short = url[:60] + ("..." if len(url) > 60 else "")
            lines.append(f"  {i:3d}. [{dt}] ({visits} visits) {title_short}")
            lines.append(f"       {url_short}")
        return "\n".join(lines)

    elif action == "bookmarks":
        browser = parameters.get("browser", "chrome")

        if browser == "chrome":
            bm_path = _get_chrome_bookmarks_path()
        else:
            bm_path = _get_edge_bookmarks_path()

        if not os.path.exists(bm_path):
            return f"Error: Bookmarks file not found: {bm_path}"

        try:
            with open(bm_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return f"Error reading bookmarks: {e}"

        bookmarks = []
        roots = data.get("roots", {})
        _get_bookmarks_recursive(roots, bookmarks)

        if not bookmarks:
            return f"No {browser.title()} bookmarks found."

        lines = [f"{browser.title()} Bookmarks ({len(bookmarks)} total):", "=" * 70]
        for i, bm in enumerate(bookmarks[:limit], 1):
            lines.append(f"  {i:3d}. {bm['name']}")
            lines.append(f"       {bm['url']}")
        if len(bookmarks) > limit:
            lines.append(f"\n  ... {len(bookmarks) - limit} more bookmarks")
        return "\n".join(lines)

    elif action == "search":
        query = parameters.get("query", "").lower()
        if not query:
            return "Error: 'query' parameter required."

        results = []
        for browser_name, get_path in [("Chrome", _get_chrome_history_path), ("Edge", _get_edge_history_path)]:
            db_path = get_path()
            conn, err = _read_sqlite_copy(db_path)
            if err:
                continue

            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT url, title, visit_count, last_visit_time FROM urls "
                    "WHERE lower(url) LIKE ? OR lower(title) LIKE ? "
                    "ORDER BY last_visit_time DESC LIMIT ?",
                    (f"%{query}%", f"%{query}%", limit)
                )
                for url, title, visits, ts in cursor.fetchall():
                    results.append((browser_name, url, title or "No title", visits, ts))
            except sqlite3.OperationalError:
                pass
            finally:
                conn.close()

        results.sort(key=lambda x: x[4], reverse=True)
        results = results[:limit]

        if not results:
            return f"No results found for '{query}'."

        lines = [f"Search Results for '{query}' ({len(results)} found):", "=" * 70]
        for i, (browser, url, title, visits, ts) in enumerate(results, 1):
            dt = _chrome_time_to_datetime(ts)
            url_short = url[:60] + ("..." if len(url) > 60 else "")
            lines.append(f"  {i:3d}. [{browser}] [{dt}] ({visits} visits) {title[:50]}")
            lines.append(f"       {url_short}")
        return "\n".join(lines)

    elif action == "stats":
        stats = {}
        for browser_name, get_path in [("Chrome", _get_chrome_history_path), ("Edge", _get_edge_history_path)]:
            db_path = get_path()
            conn, err = _read_sqlite_copy(db_path)
            if err:
                continue

            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM urls")
                total_urls = cursor.fetchone()[0]

                cursor.execute("SELECT SUM(visit_count) FROM urls")
                total_visits = cursor.fetchone()[0] or 0

                cursor.execute(
                    "SELECT url, visit_count FROM urls ORDER BY visit_count DESC LIMIT 5"
                )
                top_sites = cursor.fetchall()

                now = datetime.now()
                week_ago = now - timedelta(days=7)
                chrome_epoch = datetime(1601, 1, 1)
                ts_week = int((week_ago - chrome_epoch).total_seconds() * 1_000_000)

                cursor.execute(
                    "SELECT COUNT(*) FROM urls WHERE last_visit_time >= ?",
                    (ts_week,)
                )
                recent = cursor.fetchone()[0]

                stats[browser_name] = {
                    "total_urls": total_urls,
                    "total_visits": total_visits,
                    "recent_7_days": recent,
                    "top_sites": top_sites
                }
            except sqlite3.OperationalError:
                pass
            finally:
                conn.close()

        if not stats:
            return "No browser history data available."

        lines = ["Browsing Statistics:", "=" * 60]
        for browser, data in stats.items():
            lines.append(f"\n  {browser}:")
            lines.append(f"    Total URLs visited: {data['total_urls']}")
            lines.append(f"    Total page visits: {data['total_visits']}")
            lines.append(f"    Visits in last 7 days: {data['recent_7_days']}")
            if data["top_sites"]:
                lines.append(f"    Top visited sites:")
                for url, visits in data["top_sites"]:
                    url_short = url[:50] + ("..." if len(url) > 50 else "")
                    lines.append(f"      {visits:5d}x  {url_short}")
        return "\n".join(lines)

    elif action == "export":
        output = parameters.get("output", "")
        if not output:
            return "Error: 'output' parameter required."

        output = os.path.expanduser(output)
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

        all_entries = []
        for browser_name, get_path in [("Chrome", _get_chrome_history_path), ("Edge", _get_edge_history_path)]:
            db_path = get_path()
            conn, err = _read_sqlite_copy(db_path)
            if err:
                continue

            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT url, title, visit_count, last_visit_time FROM urls "
                    "ORDER BY last_visit_time DESC"
                )
                for url, title, visits, ts in cursor.fetchall():
                    all_entries.append({
                        "browser": browser_name,
                        "url": url,
                        "title": title or "",
                        "visit_count": visits,
                        "last_visit": _chrome_time_to_datetime(ts)
                    })
            except sqlite3.OperationalError:
                pass
            finally:
                conn.close()

        if not all_entries:
            return "No browser history to export."

        all_entries.sort(key=lambda x: x.get("last_visit", ""), reverse=True)

        if output.endswith(".json"):
            Path(output).write_text(json.dumps(all_entries, indent=2, ensure_ascii=False), encoding="utf-8")
        elif output.endswith(".csv"):
            import csv
            with open(output, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["browser", "url", "title", "visit_count", "last_visit"])
                writer.writeheader()
                writer.writerows(all_entries)
        else:
            Path(output).write_text(json.dumps(all_entries, indent=2, ensure_ascii=False), encoding="utf-8")

        return f"Exported {len(all_entries)} history entries to {output}"

    else:
        return (
            f"Error: Unknown action '{action}'. Available:\n"
            "  chrome, edge, bookmarks, search, stats, export"
        )
