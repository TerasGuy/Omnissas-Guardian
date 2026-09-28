"""Progress lines printed during crawl/fetch, with local timestamps."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from omnissa_archive.db import queue_counts
from omnissa_archive.urls import kb_article_id


def local_timestamp() -> str:
    """Local wall-clock time matching the user's system clock (not UTC)."""
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")


def progress_line(message: str) -> str:
    return f"{local_timestamp()} {message}"


def log_progress(message: str) -> None:
    print(progress_line(message), flush=True)


def format_queue_summary(conn: Any) -> str:
    """Cheap counts for the end of each download line."""
    saved = int(conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"])
    counts = queue_counts(conn)
    return (
        f"saved={saved} "
        f"done={counts.get('done', 0)} "
        f"pending={counts.get('pending', 0)} "
        f"running={counts.get('running', 0)} "
        f"error={counts.get('error', 0)}"
    )


def download_message(
    source: str,
    index: int,
    total: int,
    url: str,
    detail: str,
) -> str:
    """Body of a download line (without timestamp or queue summary)."""
    kb_field = kb_article_id(url) or "—"
    return f"{source} {index}/{total} KB {kb_field} | {detail}"


def log_download(
    conn: Any,
    source: str,
    index: int,
    total: int,
    url: str,
    detail: str,
) -> None:
    """Print one processed-URL line with timestamp, KB id, title/URL, and queue counts."""
    log_progress(
        f"{download_message(source, index, total, url, detail)} | {format_queue_summary(conn)}"
    )
