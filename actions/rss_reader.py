from __future__ import annotations

"""RSS / Atom Feed Reader — Subscribe, read, and search syndication feeds.

Actions
-------
add    – Subscribe to a feed URL with an optional alias.
list   – Show all subscribed feeds.
read   – Fetch the latest entries from a specific feed or all feeds.
remove – Unsubscribe from a feed.
check  – Return only entries published since the last check.
search – Keyword search across all subscribed feeds.
"""

import json
import os
import time
from datetime import datetime
from typing import Any

try:
    import feedparser
except ImportError:
    feedparser = None  # type: ignore[assignment,misc]

_STORAGE = os.path.join(os.path.dirname(__file__), "..", "data", "rss_feeds.json")
os.makedirs(os.path.dirname(_STORAGE), exist_ok=True)


def _load() -> dict[str, Any]:
    if os.path.isfile(_STORAGE):
        with open(_STORAGE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"feeds": {}, "last_check": {}}


def _save(data: dict[str, Any]) -> None:
    with open(_STORAGE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def _format_entry(idx: int, entry: Any) -> str:
    title = getattr(entry, "title", "No title")
    link = getattr(entry, "link", "")
    published = getattr(entry, "published", getattr(entry, "updated", "Unknown date"))
    summary = getattr(entry, "summary", "")
    if summary:
        summary = summary[:200].replace("\n", " ")
        summary = f"\n    {summary}..."
    return f"{idx}. {title}\n   Published: {published}\n   Link: {link}{summary}"


def rss_reader(parameters: dict = None, player=None) -> str:  # noqa: C901
    """Manage and read RSS / Atom feeds."""
    if feedparser is None:
        return "Error: feedparser is not installed. Run: pip install feedparser"

    params = parameters or {}
    action = str(params.get("action", "list")).strip().lower()
    text = str(params.get("text", "")).strip()
    url = str(params.get("url", "")).strip()
    feed_name = str(params.get("feed_name", "")).strip()
    max_entries = int(str(params.get("max_entries", 10)).strip() or 10)
    query = str(params.get("query", "")).strip().lower()

    data = _load()

    if action == "add":
        if not url:
            return "Error: No URL provided."
        alias = feed_name or url
        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                return f"Error: Failed to parse feed — {parsed.bozo_exception}"
            title = parsed.feed.get("title", alias)
            data["feeds"][alias] = {"url": url, "title": title, "added": datetime.now().isoformat()}
            _save(data)
            return f"Subscribed to '{title}' ({url})."
        except Exception as exc:
            return f"Error adding feed: {exc}"

    if action == "list":
        feeds = data.get("feeds", {})
        if not feeds:
            return "No subscriptions."
        lines = [f"  • {name} — {info.get('title', '')} ({info.get('url', '')})" for name, info in feeds.items()]
        return f"Subscriptions ({len(feeds)}):\n" + "\n".join(lines)

    if action == "read":
        feeds = data.get("feeds", {})
        targets: list[tuple[str, str]] = []
        if feed_name and feed_name in feeds:
            targets = [(feed_name, feeds[feed_name]["url"])]
        elif url:
            targets = [("custom", url)]
        else:
            targets = [(n, i["url"]) for n, i in feeds.items()]

        if not targets:
            return "No feeds to read."

        all_entries: list[str] = []
        for name, feed_url in targets:
            try:
                parsed = feedparser.parse(feed_url)
                for idx, entry in enumerate(parsed.entries[:max_entries], 1):
                    all_entries.append(f"[{name}] {_format_entry(idx, entry)}")
            except Exception as exc:
                all_entries.append(f"[{name}] Error: {exc}")

        if not all_entries:
            return "No entries found."
        return "\n\n".join(all_entries)

    if action == "remove":
        feeds = data.get("feeds", {})
        key = feed_name or url
        if key not in feeds:
            return f"Error: Feed '{key}' not found."
        removed = feeds.pop(key)
        _save(data)
        return f"Removed '{removed.get('title', key)}'."

    if action == "check":
        feeds = data.get("feeds", {})
        if not feeds:
            return "No subscriptions."
        last = data.get("last_check", {})
        new_entries: list[str] = []
        for name, info in feeds.items():
            try:
                parsed = feedparser.parse(info["url"])
                for idx, entry in enumerate(parsed.entries[:max_entries], 1):
                    published = getattr(entry, "published", getattr(entry, "updated", ""))
                    last_seen = last.get(name, "")
                    if published > last_seen if last_seen else True:
                        new_entries.append(f"[{name}] {_format_entry(idx, entry)}")
                if parsed.entries:
                    last[name] = getattr(parsed.entries[0], "published", datetime.now().isoformat())
            except Exception as exc:
                new_entries.append(f"[{name}] Error: {exc}")
        data["last_check"] = last
        _save(data)
        if not new_entries:
            return "No new entries since last check."
        return "New entries:\n" + "\n\n".join(new_entries)

    if action == "search":
        if not query:
            return "Error: No query provided."
        feeds = data.get("feeds", {})
        if not feeds:
            return "No subscriptions."
        matches: list[str] = []
        for name, info in feeds.items():
            try:
                parsed = feedparser.parse(info["url"])
                for idx, entry in enumerate(parsed.entries, 1):
                    title = getattr(entry, "title", "")
                    summary = getattr(entry, "summary", "")
                    if query in title.lower() or query in summary.lower():
                        matches.append(f"[{name}] {_format_entry(idx, entry)}")
            except Exception:
                continue
        if not matches:
            return f"No results for '{query}'."
        return f"Results for '{query}' ({len(matches)}):\n" + "\n\n".join(matches)

    return f"Error: Unknown action '{action}'."
