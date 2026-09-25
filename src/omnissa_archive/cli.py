import argparse
import sys
from pathlib import Path

import httpx

from omnissa_archive.assets import RateLimiter
from omnissa_archive.config import DOCS_RPS, HEADERS
from omnissa_archive.db import connect, init_db, pending_urls, queue_counts, search
from omnissa_archive.discover import discover_docs, discover_kb
from omnissa_archive.fetch_docs import fetch_docs
from omnissa_archive.fetch_kb import fetch_kb
from omnissa_archive.pilot import run_pilot
from omnissa_archive.reader import serve


def _crawl_db(data_dir: Path):
    """Download/queue always use data/archive.sqlite, never the customer library copy."""
    conn = connect(data_dir / "archive.sqlite")
    init_db(conn)
    return conn


def _db(data_dir: Path):
    try:
        from omnissa_archive.library import resolve_default_database

        path = resolve_default_database(data_dir)
    except ImportError:
        path = data_dir / "archive.sqlite"
    conn = connect(path)
    init_db(conn)
    return conn


def _discover(data_dir: Path) -> None:
    conn = _crawl_db(data_dir)
    limiter = RateLimiter(DOCS_RPS)
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=60.0) as client:
        discover_docs(conn, client, limiter)
        discover_kb(conn, client, limiter)


def _fetch(data_dir: Path, source: str, limit: int) -> None:
    conn = _crawl_db(data_dir)
    counts = queue_counts(conn)
    print(
        "resume "
        f"pending={counts.get('pending', 0)} "
        f"running={counts.get('running', 0)} "
        f"done={counts.get('done', 0)} "
        f"error={counts.get('error', 0)}",
        flush=True,
    )
    if source in ("docs", "all"):
        fetch_docs(conn, data_dir, pending_urls(conn, "docs", limit))
    if source in ("kb", "all"):
        kb_limit = limit if source == "kb" else limit
        fetch_kb(conn, data_dir, pending_urls(conn, "kb", kb_limit))


def _refresh(data_dir: Path, source: str, limit: int) -> None:
    _discover(data_dir)
    _fetch(data_dir, source, limit)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="omnissa-archive")
    parser.add_argument("--data-dir", default="data", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover")
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--source", choices=("docs", "kb", "all"), default="all")
    fetch.add_argument("--limit", type=int, default=0)
    refresh = sub.add_parser("refresh")
    refresh.add_argument("--source", choices=("docs", "kb", "all"), default="all")
    refresh.add_argument("--limit", type=int, default=0)
    sub.add_parser("pilot")
    serve_cmd = sub.add_parser("serve")
    serve_cmd.add_argument("--port", type=int, default=8765)
    serve_cmd.add_argument("--no-browser", action="store_true")
    search_cmd = sub.add_parser("search")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--limit", type=int, default=10)
    backfill_cmd = sub.add_parser("backfill")
    backfill_cmd.add_argument("--source", choices=("docs", "kb", "all"), default="all")
    guardian_cmd = sub.add_parser("guardian")
    guardian_cmd.add_argument("--port", type=int, default=8766)
    guardian_cmd.add_argument("--no-browser", action="store_true")
    guardian_cmd.add_argument("--reader-url", default="http://127.0.0.1:8765")
    package_cmd = sub.add_parser("package")
    package_cmd.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    data_dir = args.data_dir
    if args.command == "discover":
        _discover(data_dir)
        return 0
    if args.command == "fetch":
        _fetch(data_dir, args.source, args.limit)
        return 0
    if args.command == "refresh":
        _refresh(data_dir, args.source, args.limit)
        return 0
    if args.command == "pilot":
        return run_pilot(data_dir)
    if args.command == "serve":
        serve(data_dir, port=args.port, open_browser=not args.no_browser)
        return 0
    if args.command == "guardian":
        from omnissa_archive.guardian import serve_guardian

        serve_guardian(
            data_dir,
            port=args.port,
            open_browser=not args.no_browser,
            reader_base=args.reader_url,
        )
        return 0
    if args.command == "package":
        from omnissa_archive.library import prepare_customer_package

        package = prepare_customer_package(data_dir, args.output)
        print(package)
        return 0
    if args.command == "search":
        conn = _db(data_dir)
        rows = search(conn, args.query, args.limit)
        for row in rows:
            print(f"{row['source']}\t{row['title']}\t{row['url']}")
        return 0 if rows else 1
    if args.command == "backfill":
        from omnissa_archive.backfill import backfill

        conn = _crawl_db(data_dir)
        backfill(conn, data_dir, args.source)
        return 0
    return 2
