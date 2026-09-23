import xml.etree.ElementTree as ET

import httpx

from omnissa_archive.config import DOCS_SITEMAP, KB_SITEMAP
from omnissa_archive.db import enqueue
from omnissa_archive.urls import canonical_queue_url, queue_source


def parse_locs(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    locs: list[str] = []
    for element in root.iter():
        if element.tag.endswith("loc") and element.text:
            locs.append(element.text.strip())
    return locs


def _queue_items(locs: list[str], source: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    seen: set[str] = set()
    for loc in locs:
        queued = canonical_queue_url(loc)
        if not queued or queued in seen or queue_source(queued) != source:
            continue
        seen.add(queued)
        items.append((queued, source))
    return items


def discover_docs(conn, client: httpx.Client, limiter) -> tuple[int, int]:
    limiter.wait()
    index = client.get(DOCS_SITEMAP)
    index.raise_for_status()
    sitemap_urls = [url for url in parse_locs(index.text) if url.rstrip("/").endswith(".xml")]
    if not sitemap_urls:
        sitemap_urls = [DOCS_SITEMAP]
    english = 0
    added = 0
    for sitemap_url in sitemap_urls:
        limiter.wait()
        response = client.get(sitemap_url)
        if response.status_code != 200:
            print(f"docs sitemap skipped {response.status_code} {sitemap_url}", flush=True)
            continue
        items = _queue_items(parse_locs(response.text), "docs")
        english += len(items)
        new_rows = enqueue(conn, items)
        added += new_rows
        print(
            f"docs {sitemap_url.rsplit('/', 1)[-1]} english={len(items)} new={new_rows}",
            flush=True,
        )
    return english, added


def discover_kb(conn, client: httpx.Client, limiter) -> tuple[int, int]:
    limiter.wait()
    response = client.get(KB_SITEMAP)
    response.raise_for_status()
    items = _queue_items(parse_locs(response.text), "kb")
    added = enqueue(conn, items)
    print(f"kb sitemap articles={len(items)} new={added}", flush=True)
    return len(items), added
