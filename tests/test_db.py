from pathlib import Path

from omnissa_archive.db import connect, content_hash, enqueue, get_document, init_db, search, upsert_document
from omnissa_archive.discover import parse_locs


def test_parse_sitemap_locs():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://docs.omnissa.com/Guide/Topic</loc></url>
      <url><loc>https://docs.omnissa.com/de-DE/Guide/Topic</loc></url>
    </urlset>
    """
    assert parse_locs(xml) == [
        "https://docs.omnissa.com/Guide/Topic",
        "https://docs.omnissa.com/de-DE/Guide/Topic",
    ]


def test_document_upsert_hash_and_search(tmp_path: Path):
    conn = connect(tmp_path / "archive.sqlite")
    init_db(conn)
    enqueue(conn, [("https://docs.omnissa.com/Guide/Topic", "docs")])
    doc_id, changed = upsert_document(
        conn,
        source="docs",
        url="https://docs.omnissa.com/Guide/Topic",
        locale="en",
        title="Horizon ports",
        guide="Guide",
        html="<p>Horizon connection server ports</p>",
        text="Horizon connection server ports",
        http_status=200,
    )
    conn.commit()
    assert changed is True
    same_id, changed_again = upsert_document(
        conn,
        source="docs",
        url="https://docs.omnissa.com/Guide/Topic",
        locale="en",
        title="Horizon ports",
        guide="Guide",
        html="<p>Horizon connection server ports</p>",
        text="Horizon connection server ports",
        http_status=200,
    )
    conn.commit()
    assert same_id == doc_id
    assert changed_again is False
    stored = get_document(conn, "https://docs.omnissa.com/Guide/Topic")
    assert stored["content_hash"] == content_hash("Horizon ports", "Horizon connection server ports")
    hits = search(conn, "Horizon", limit=5)
    assert len(hits) == 1
    assert hits[0]["url"].endswith("/Topic")
    stored_again = get_document(conn, "https://docs.omnissa.com/Guide/Topic")
    assert stored_again["product"] == ""


def test_facet_columns_are_added_and_kept_when_content_is_unchanged(tmp_path: Path):
    db_path = tmp_path / "archive.sqlite"
    conn = connect(db_path)
    conn.execute(
        """
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            locale TEXT,
            title TEXT,
            guide TEXT,
            html TEXT,
            text TEXT,
            content_hash TEXT,
            fetched_at TEXT,
            http_status INTEGER
        )
        """
    )
    conn.commit()
    init_db(conn)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)")}
    assert {"product", "version", "published_at", "facets_at"} <= columns
    upsert_document(
        conn,
        source="docs",
        url="https://docs.omnissa.com/Guide-V2606/Topic",
        locale="en",
        title="Horizon ports",
        guide="Guide-V2606",
        html="<p>Horizon connection server ports</p>",
        text="Horizon connection server ports",
        http_status=200,
    )
    _, changed = upsert_document(
        conn,
        source="docs",
        url="https://docs.omnissa.com/Guide-V2606/Topic",
        locale="en",
        title="Horizon ports",
        guide="Guide-V2606",
        html="<p>Horizon connection server ports</p>",
        text="Horizon connection server ports",
        http_status=200,
        product="Horizon",
        version="2606",
        published_at="2024-03-29",
    )
    conn.commit()
    assert changed is False
    stored = get_document(conn, "https://docs.omnissa.com/Guide-V2606/Topic")
    assert stored["product"] == "Horizon"
    assert stored["version"] == "2606"
    assert stored["published_at"] == "2024-03-29"
    assert stored["facets_at"]
