from pathlib import Path

import httpx

from omnissa_archive.assets import RateLimiter
from omnissa_archive.config import (
    DOCS_RPS,
    DOCS_SEED_URLS,
    HEADERS,
    KB_SEED_URLS,
    PILOT_DOCS,
    PILOT_KB,
)
from omnissa_archive.db import connect, get_document, init_db, pending_urls, search
from omnissa_archive.discover import discover_docs, discover_kb
from omnissa_archive.fetch_docs import fetch_docs
from omnissa_archive.fetch_kb import fetch_kb
from omnissa_archive.urls import canonical_queue_url


def _pick(conn, source: str, seeds: list[str], limit: int) -> list[str]:
    ordered: list[str] = []
    for seed in seeds:
        queued = canonical_queue_url(seed) or seed
        if queued not in ordered:
            ordered.append(queued)
    for url in pending_urls(conn, source):
        if url not in ordered:
            ordered.append(url)
        if len(ordered) >= limit:
            break
    return ordered[:limit]


def _asset_files(conn, data_dir: Path) -> list[Path]:
    rows = conn.execute("SELECT local_path FROM assets WHERE local_path IS NOT NULL").fetchall()
    return [data_dir / row["local_path"] for row in rows if row["local_path"] and (data_dir / row["local_path"]).is_file()]


def verify_archive(conn, data_dir: Path) -> list[str]:
    problems: list[str] = []
    docs = conn.execute(
        """
        SELECT COUNT(*) AS n FROM documents
        WHERE source = 'docs' AND title != '' AND length(text) > 80
        """
    ).fetchone()["n"]
    if docs < PILOT_DOCS:
        problems.append(f"docs with body: {docs}, expected {PILOT_DOCS}")
    for seed in DOCS_SEED_URLS:
        row = get_document(conn, seed)
        if row is None or not row["title"] or len(row["text"] or "") < 80:
            problems.append(f"missing docs page {seed}")
    tables = conn.execute(
        "SELECT COUNT(*) AS n FROM documents WHERE source = 'docs' AND html LIKE '%<table%'"
    ).fetchone()["n"]
    if tables < 1:
        problems.append("no docs table was stored")
    links = conn.execute(
        """
        SELECT COUNT(*) AS n FROM links
        WHERE from_url LIKE 'https://docs.omnissa.com/%'
          AND (
            to_url LIKE 'https://docs.omnissa.com/%'
            OR to_url LIKE 'https://kb.omnissa.com/%'
          )
        """
    ).fetchone()["n"]
    if links < 1:
        problems.append("no internal docs link was stored")
    if not _asset_files(conn, data_dir):
        problems.append("no asset file was saved")
    kb = conn.execute(
        """
        SELECT COUNT(*) AS n FROM documents
        WHERE source = 'kb' AND title != '' AND length(text) > 80
        """
    ).fetchone()["n"]
    if kb < PILOT_KB:
        problems.append(f"kb articles with body: {kb}, expected {PILOT_KB}")
    article = get_document(conn, KB_SEED_URLS[0])
    if article is None or "1027744" not in (article["title"] or "") or len(article["text"] or "") < 200:
        problems.append("KB 1027744 was not stored")
    if not search(conn, "Horizon", limit=5):
        problems.append("full-text search returned nothing for Horizon")
    return problems


def _image_candidates(conn, limit: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT url FROM crawl_queue
        WHERE source = 'docs' AND status = 'pending'
          AND (
            url LIKE '%Figure%' OR url LIKE '%Diagram%' OR url LIKE '%Architecture%'
            OR url LIKE '%Overview%' OR url LIKE '%Image%' OR url LIKE '%screenshot%'
          )
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [row["url"] for row in rows]


def run_pilot(data_dir: Path) -> int:
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(data_dir / "archive.sqlite")
    init_db(conn)
    from omnissa_archive.db import enqueue

    enqueue(conn, [(url, "docs") for url in DOCS_SEED_URLS])
    enqueue(conn, [(url, "kb") for url in KB_SEED_URLS])
    limiter = RateLimiter(DOCS_RPS)
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=60.0) as client:
        docs_count, docs_new = discover_docs(conn, client, limiter)
        kb_count, kb_new = discover_kb(conn, client, limiter)
    print(f"discovered docs={docs_count} new={docs_new} kb={kb_count} new={kb_new}", flush=True)

    seen_docs: set[str] = set()
    saved_docs = 0
    while saved_docs < PILOT_DOCS and len(seen_docs) < PILOT_DOCS * 2:
        docs_urls = [url for url in _pick(conn, "docs", DOCS_SEED_URLS, PILOT_DOCS) if url not in seen_docs]
        if not docs_urls:
            break
        seen_docs.update(docs_urls)
        fetch_docs(conn, data_dir, docs_urls)
        saved_docs = conn.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE source = 'docs' AND length(text) > 80"
        ).fetchone()["n"]
    if not _asset_files(conn, data_dir):
        extra = _image_candidates(conn, 30)
        if extra:
            print(f"looking for an image on {len(extra)} more docs pages", flush=True)
            fetch_docs(conn, data_dir, extra)
    saved_kb = 0
    seen_kb: set[str] = set()
    while saved_kb < PILOT_KB and len(seen_kb) < PILOT_KB * 3:
        kb_urls = [url for url in _pick(conn, "kb", KB_SEED_URLS, PILOT_KB) if url not in seen_kb]
        if not kb_urls:
            break
        seen_kb.update(kb_urls)
        fetch_kb(conn, data_dir, kb_urls)
        saved_kb = conn.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE source = 'kb' AND length(text) > 80"
        ).fetchone()["n"]
    problems = verify_archive(conn, data_dir)
    docs_saved = conn.execute("SELECT COUNT(*) AS n FROM documents WHERE source = 'docs'").fetchone()["n"]
    kb_saved = conn.execute("SELECT COUNT(*) AS n FROM documents WHERE source = 'kb'").fetchone()["n"]
    assets = len(_asset_files(conn, data_dir))
    print(f"stored docs={docs_saved} kb={kb_saved} asset_files={assets}", flush=True)
    if problems:
        print("pilot checks failed:", flush=True)
        for problem in problems:
            print(f"- {problem}", flush=True)
        return 1
    print("pilot checks passed", flush=True)
    return 0
