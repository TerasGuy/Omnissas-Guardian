import subprocess
import time
from pathlib import Path

import httpx

from omnissa_archive.assets import RateLimiter
from omnissa_archive.config import (
    CHROME_CANDIDATES,
    DOCS_RPS,
    HEADERS,
    KB_DELAY_SECONDS,
    MAX_ATTEMPTS,
    USER_AGENT,
)
from omnissa_archive.db import enqueue, get_document, mark_error, mark_running
from omnissa_archive.extract import extract_kb
from omnissa_archive.progress import log_download, log_progress
from omnissa_archive.store import keep_current, page_is_current, save_page


def kb_render_state(html: str) -> str:
    if 'id="article_content"' in html or "id='article_content'" in html:
        return "ready"
    lowered = html.lower()
    if "no longer available" in lowered or "was not found on this server" in lowered:
        return "missing"
    return "pending"


def _mark_missing(conn, url: str) -> None:
    mark_error(conn, url, "article unavailable")
    conn.execute(
        "UPDATE crawl_queue SET attempts = ? WHERE url = ?",
        (MAX_ATTEMPTS, url),
    )
    conn.commit()


def _wait_for_article(page) -> tuple[str, str]:
    deadline = time.monotonic() + 20
    meta_deadline = None
    html = ""
    state = "pending"
    while time.monotonic() < deadline or (meta_deadline is not None and time.monotonic() < meta_deadline):
        html = page.content()
        state = kb_render_state(html)
        if state == "missing":
            return state, html
        if state == "ready":
            if "article:published_time" in html:
                return state, html
            if meta_deadline is None:
                meta_deadline = time.monotonic() + 8
        page.wait_for_timeout(400)
    return state, html


def _chrome_path() -> Path | None:
    for candidate in CHROME_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _render_chrome(url: str) -> str:
    chrome = _chrome_path()
    if chrome is None:
        raise RuntimeError("Chrome or Edge is not installed")
    completed = subprocess.run(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--disable-extensions",
            f"--user-agent={USER_AGENT}",
            "--virtual-time-budget=25000",
            "--timeout=60000",
            "--dump-dom",
            url,
        ],
        capture_output=True,
        timeout=90,
        check=False,
    )
    html = completed.stdout.decode("utf-8", errors="replace")
    if not html.strip():
        detail = completed.stderr.decode("utf-8", errors="replace")[:300]
        raise RuntimeError(detail or "empty render")
    return html


def _store_kb_html(
    conn,
    data_dir: Path,
    client,
    limiter,
    url: str,
    html: str,
    index: int,
    total: int,
) -> str:
    extracted = extract_kb(url, html)
    if extracted is None:
        mark_error(conn, url, "missing article body")
        conn.commit()
        log_download(conn, "kb", index, total, url, f"no body {url}")
        return ""
    if page_is_current(get_document(conn, url), extracted):
        keep_current(conn, url, 200)
        label = extracted.updated_at or extracted.title or url
        log_download(conn, "kb", index, total, url, f"unchanged {label}")
        return "unchanged"
    save_page(
        conn,
        data_dir,
        client,
        limiter,
        source="kb",
        url=url,
        http_status=200,
        extracted=extracted,
    )
    log_download(conn, "kb", index, total, url, extracted.title or url)
    return "saved"


def _fetch_with_playwright(conn, data_dir, client, limiter, urls: list[str]) -> int:
    from playwright.sync_api import sync_playwright

    saved = 0
    total = len(urls)
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True, channel="chrome")
        except Exception:
            browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="en-US")
        page = context.new_page()
        try:
            for index, url in enumerate(urls, start=1):
                enqueue(conn, [(url, "kb")])
                mark_running(conn, url)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    state, html = _wait_for_article(page)
                except Exception as exc:
                    mark_error(conn, url, str(exc))
                    conn.commit()
                    log_download(conn, "kb", index, total, url, f"error {url}: {exc}")
                else:
                    if state == "missing":
                        _mark_missing(conn, url)
                        log_download(
                            conn, "kb", index, total, url, f"unavailable {url}"
                        )
                    elif state != "ready":
                        mark_error(conn, url, "article body did not render")
                        conn.commit()
                        log_download(conn, "kb", index, total, url, f"no body {url}")
                    else:
                        outcome = _store_kb_html(
                            conn, data_dir, client, limiter, url, html, index, total
                        )
                        if outcome == "saved":
                            saved += 1
                time.sleep(KB_DELAY_SECONDS)
        finally:
            context.close()
            browser.close()
    return saved


def _fetch_with_chrome(conn, data_dir, client, limiter, urls: list[str]) -> int:
    saved = 0
    total = len(urls)
    for index, url in enumerate(urls, start=1):
        enqueue(conn, [(url, "kb")])
        mark_running(conn, url)
        try:
            html = _render_chrome(url)
        except Exception as exc:
            mark_error(conn, url, str(exc))
            conn.commit()
            log_download(conn, "kb", index, total, url, f"error {url}: {exc}")
        else:
            state = kb_render_state(html)
            if state == "missing":
                _mark_missing(conn, url)
                log_download(conn, "kb", index, total, url, f"unavailable {url}")
            else:
                outcome = _store_kb_html(
                    conn, data_dir, client, limiter, url, html, index, total
                )
                if outcome == "saved":
                    saved += 1
        time.sleep(KB_DELAY_SECONDS)
    return saved


def fetch_kb(conn, data_dir: Path, urls: list[str]) -> int:
    if not urls:
        return 0
    limiter = RateLimiter(DOCS_RPS)
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=45.0) as client:
        try:
            return _fetch_with_playwright(conn, data_dir, client, limiter, urls)
        except Exception as exc:
            log_progress(f"playwright unavailable ({exc}); using installed Chrome")
            return _fetch_with_chrome(conn, data_dir, client, limiter, urls)
