from pathlib import Path

import httpx

from omnissa_archive.assets import RateLimiter
from omnissa_archive.config import DOCS_RPS, HEADERS
from omnissa_archive.db import enqueue, get_document, mark_error, mark_running
from omnissa_archive.extract import extract_docs
from omnissa_archive.store import keep_current, page_is_current, save_page


def fetch_docs(conn, data_dir: Path, urls: list[str]) -> int:
    if not urls:
        return 0
    limiter = RateLimiter(DOCS_RPS)
    saved = 0
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=45.0) as client:
        for index, url in enumerate(urls, start=1):
            enqueue(conn, [(url, "docs")])
            mark_running(conn, url)
            try:
                limiter.wait()
                response = client.get(url)
            except httpx.HTTPError as exc:
                mark_error(conn, url, str(exc))
                conn.commit()
                print(f"docs {index}/{len(urls)} error {url}: {exc}", flush=True)
                continue
            if response.status_code != 200:
                mark_error(conn, url, f"http {response.status_code}")
                conn.commit()
                print(f"docs {index}/{len(urls)} http {response.status_code} {url}", flush=True)
                continue
            extracted = extract_docs(str(response.url), response.text)
            if extracted is None:
                mark_error(conn, url, "missing doc-body")
                conn.commit()
                print(f"docs {index}/{len(urls)} no body {url}", flush=True)
                continue
            if page_is_current(get_document(conn, url), extracted):
                keep_current(conn, url, response.status_code)
                print(f"docs {index}/{len(urls)} unchanged {extracted.updated_at or extracted.title}", flush=True)
                continue
            save_page(
                conn,
                data_dir,
                client,
                limiter,
                source="docs",
                url=url,
                http_status=response.status_code,
                extracted=extracted,
            )
            saved += 1
            print(f"docs {index}/{len(urls)} {extracted.title}", flush=True)
    return saved
