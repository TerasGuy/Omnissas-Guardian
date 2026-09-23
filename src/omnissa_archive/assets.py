import hashlib
import time
from pathlib import Path

import httpx

from omnissa_archive.db import get_asset, upsert_asset
from omnissa_archive.urls import docs_path_allowed, is_asset_candidate

CONTENT_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "application/pdf": ".pdf",
}
MAX_BYTES = 30 * 1024 * 1024


class RateLimiter:
    def __init__(self, per_second: float) -> None:
        self.min_interval = 1.0 / per_second if per_second > 0 else 0
        self._next = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        if now < self._next:
            time.sleep(self._next - now)
        self._next = time.monotonic() + self.min_interval


def asset_filename(source_url: str, content_type: str, body: bytes) -> str:
    digest = hashlib.sha256(body).hexdigest()[:20]
    path = source_url.split("?", 1)[0]
    suffix = Path(path).suffix.lower()
    if suffix not in CONTENT_EXT.values():
        suffix = CONTENT_EXT.get(content_type.split(";")[0].strip().lower(), "")
    return f"{digest}{suffix}"


def download_assets(
    client: httpx.Client,
    limiter: RateLimiter,
    urls: list[str],
    data_dir: Path,
    conn,
    document_id: int | None,
) -> dict[str, str]:
    assets_dir = data_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    for url in urls:
        if not is_asset_candidate(url) or not docs_path_allowed(url):
            continue
        existing = get_asset(conn, url)
        if existing and existing["local_path"] and (data_dir / existing["local_path"]).is_file():
            mapping[url] = existing["local_path"]
            if document_id is not None:
                upsert_asset(
                    conn,
                    source_url=url,
                    local_path=existing["local_path"],
                    sha256=existing["sha256"] or "",
                    content_type=existing["content_type"] or "",
                    document_id=document_id,
                )
            continue
        try:
            limiter.wait()
            response = client.get(url)
        except httpx.HTTPError:
            continue
        if response.status_code != 200:
            continue
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type not in CONTENT_EXT:
            continue
        body = response.content
        if not body or len(body) > MAX_BYTES:
            continue
        name = asset_filename(url, content_type, body)
        relative = f"assets/{name}"
        target = data_dir / relative
        target.write_bytes(body)
        digest = hashlib.sha256(body).hexdigest()
        upsert_asset(
            conn,
            source_url=url,
            local_path=relative,
            sha256=digest,
            content_type=content_type,
            document_id=document_id,
        )
        mapping[url] = relative
    return mapping
