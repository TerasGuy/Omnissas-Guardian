from pathlib import Path

import httpx

from omnissa_archive.assets import RateLimiter, download_assets
from omnissa_archive.db import enqueue, mark_done, replace_links, upsert_asset, upsert_document
from omnissa_archive.extract import Extracted, apply_local_paths
from omnissa_archive.urls import canonical_queue_url, guide_of, locale_of, queue_source


def save_page(
    conn,
    data_dir: Path,
    client: httpx.Client,
    limiter: RateLimiter,
    *,
    source: str,
    url: str,
    http_status: int,
    extracted: Extracted,
) -> bool:
    mapping = download_assets(
        client,
        limiter,
        extracted.assets,
        data_dir,
        conn,
        document_id=None,
    )
    html = apply_local_paths(extracted.html, mapping)
    document_id, changed = upsert_document(
        conn,
        source=source,
        url=url,
        locale=locale_of(url),
        title=extracted.title,
        guide=guide_of(url),
        html=html,
        text=extracted.text,
        http_status=http_status,
        product=extracted.product,
        product_family=extracted.product_family,
        version=extracted.version,
        category=extracted.category,
        published_at=extracted.published_at,
        updated_at=extracted.updated_at,
    )
    for source_url, local_path in mapping.items():
        row = conn.execute(
            "SELECT sha256, content_type FROM assets WHERE source_url = ?",
            (source_url,),
        ).fetchone()
        upsert_asset(
            conn,
            source_url=source_url,
            local_path=local_path,
            sha256=row["sha256"] if row else "",
            content_type=row["content_type"] if row else "",
            document_id=document_id,
        )
    replace_links(conn, url, extracted.links)
    discovered: list[tuple[str, str]] = []
    for link in extracted.links:
        link_source = queue_source(link)
        queued = canonical_queue_url(link)
        if link_source and queued:
            discovered.append((queued, link_source))
    enqueue(conn, discovered)
    mark_done(conn, url)
    conn.commit()
    return changed
