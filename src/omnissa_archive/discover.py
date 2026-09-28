import xml.etree.ElementTree as ET

import httpx

from omnissa_archive.config import DOCS_SITEMAP, KB_SITEMAP
from omnissa_archive.db import apply_remote_revisions, enqueue
from omnissa_archive.urls import canonical_queue_url, queue_source


def parse_locs(xml_text: str) -> list[str]:
    return [loc for loc, _lastmod in parse_sitemap_entries(xml_text)] or _locs_only(xml_text)


def _locs_only(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    locs: list[str] = []
    for element in root.iter():
        if element.tag.endswith("loc") and element.text:
            locs.append(element.text.strip())
    return locs


def parse_sitemap_entries(xml_text: str) -> list[tuple[str, str]]:
    root = ET.fromstring(xml_text)
    entries: list[tuple[str, str]] = []
    for element in root.iter():
        if not element.tag.endswith("url"):
            continue
        loc = ""
        lastmod = ""
        for child in list(element):
            if child.tag.endswith("loc") and child.text:
                loc = child.text.strip()
            elif child.tag.endswith("lastmod") and child.text:
                lastmod = child.text.strip()[:10]
        if loc:
            entries.append((loc, lastmod))
    return entries


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


def _collect(xml_text: str, source: str, revisions: dict[str, str]) -> list[tuple[str, str]]:
    entries = parse_sitemap_entries(xml_text)
    if not entries:
        entries = [(loc, "") for loc in _locs_only(xml_text)]
    items: list[tuple[str, str]] = []
    seen: set[str] = set()
    for loc, lastmod in entries:
        queued = canonical_queue_url(loc)
        if not queued or queued in seen or queue_source(queued) != source:
            continue
        seen.add(queued)
        items.append((queued, source))
        if lastmod:
            revisions[queued] = lastmod
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
    revisions: dict[str, str] = {}
    for sitemap_url in sitemap_urls:
        limiter.wait()
        response = client.get(sitemap_url)
        if response.status_code != 200:
            print(f"docs sitemap skipped {response.status_code} {sitemap_url}", flush=True)
            continue
        items = _collect(response.text, "docs", revisions)
        english += len(items)
        new_rows = enqueue(conn, items)
        added += new_rows
        print(
            f"docs {sitemap_url.rsplit('/', 1)[-1]} english={len(items)} new={new_rows}",
            flush=True,
        )
    stats = apply_remote_revisions(conn, revisions)
    print(f"docs revisions stamped={stats['stamped']} changed={stats['changed']}", flush=True)
    return english, added


def discover_kb(conn, client: httpx.Client, limiter) -> tuple[int, int]:
    limiter.wait()
    response = client.get(KB_SITEMAP)
    response.raise_for_status()
    revisions: dict[str, str] = {}
    items = _collect(response.text, "kb", revisions)
    added = enqueue(conn, items)
    stats = apply_remote_revisions(conn, revisions)
    print(
        f"kb sitemap articles={len(items)} new={added} stamped={stats['stamped']} changed={stats['changed']}",
        flush=True,
    )
    return len(items), added
