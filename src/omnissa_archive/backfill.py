from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from omnissa_archive.assets import RateLimiter
from omnissa_archive.config import DOCS_RPS, HEADERS, KB_DELAY_SECONDS, USER_AGENT
from omnissa_archive.db import update_facets
from omnissa_archive.extract import metadata_from_docs, metadata_from_kb
from omnissa_archive.fetch_kb import _wait_for_article, kb_render_state


def _pending(conn, source: str) -> list[str]:
    sql = """
        SELECT url FROM documents
        WHERE source = ? AND ifnull(facets_at, '') = ''
        ORDER BY id
    """
    if source == "all":
        sql = """
            SELECT url FROM documents
            WHERE ifnull(facets_at, '') = ''
            ORDER BY CASE source WHEN 'docs' THEN 0 ELSE 1 END, id
        """
        return [row["url"] for row in conn.execute(sql)]
    return [row["url"] for row in conn.execute(sql, (source,))]


def _store(conn, url: str, meta: dict[str, str]) -> None:
    update_facets(conn, url, **meta)
    conn.commit()


def backfill_docs(conn, urls: list[str]) -> int:
    if not urls:
        return 0
    limiter = RateLimiter(DOCS_RPS)
    saved = 0
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=45.0) as client:
        for index, url in enumerate(urls, start=1):
            try:
                limiter.wait()
                response = client.get(url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"meta docs {index}/{len(urls)} error {url}: {exc}", flush=True)
                continue
            meta = metadata_from_docs(BeautifulSoup(response.text, "html.parser"), str(response.url))
            _store(conn, url, meta)
            saved += 1
            if index == 1 or index % 25 == 0 or index == len(urls):
                print(
                    f"meta docs {index}/{len(urls)} {meta['product'] or '-'} {meta['version'] or '-'} {meta['published_at'] or '-'}",
                    flush=True,
                )
    return saved


def backfill_kb(conn, urls: list[str]) -> int:
    if not urls:
        return 0
    from playwright.sync_api import sync_playwright

    saved = 0
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True, channel="chrome")
        except Exception:
            browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="en-US")
        page = context.new_page()
        try:
            for index, url in enumerate(urls, start=1):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    state, html = _wait_for_article(page)
                except Exception as exc:
                    print(f"meta kb {index}/{len(urls)} error {url}: {exc}", flush=True)
                    continue
                if state != "ready" and kb_render_state(html) != "ready":
                    print(f"meta kb {index}/{len(urls)} no article {url}", flush=True)
                    continue
                meta = metadata_from_kb(BeautifulSoup(html, "html.parser"), url)
                _store(conn, url, meta)
                saved += 1
                print(
                    f"meta kb {index}/{len(urls)} {meta['product'] or '-'} {meta['version'] or '-'} {meta['published_at'] or '-'}",
                    flush=True,
                )
                page.wait_for_timeout(int(KB_DELAY_SECONDS * 1000))
        finally:
            context.close()
            browser.close()
    return saved


def backfill(conn, data_dir: Path, source: str = "all") -> int:
    del data_dir
    urls = _pending(conn, source)
    docs = [url for url in urls if "docs.omnissa.com" in url]
    kb = [url for url in urls if url not in docs]
    if source == "docs":
        kb = []
    elif source == "kb":
        docs = []
    print(f"meta pending docs={len(docs)} kb={len(kb)}", flush=True)
    return backfill_docs(conn, docs) + backfill_kb(conn, kb)
