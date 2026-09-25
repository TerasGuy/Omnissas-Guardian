from pathlib import Path

from omnissa_archive.db import connect, init_db, upsert_document
from omnissa_archive.reader import (
    ArchiveReader,
    _parse_multipart,
    fts_query,
    local_target,
    prepare_article,
    search_documents,
)


def test_fts_query_prefixes_every_word():
    assert fts_query("connection error") == '"connection"* AND "error"*'
    assert fts_query("  ") == ""
    assert fts_query("תקלה") == '"תקלה"*'


def test_local_target_rewrites_assets_and_known_pages():
    by_url = {"https://kb.omnissa.com/s/article/1027744": 7}
    by_slug = {("Horizon8InstallUpgrade", "CompatibilityMatrix"): 4}
    assert local_target("assets/abc.png", "https://docs.omnissa.com/Guide/Topic", by_url, by_slug) == "/assets/abc.png"
    assert (
        local_target("https://kb.omnissa.com/kb/s/article/1027744", "https://docs.omnissa.com/Guide/Topic", by_url, by_slug)
        == "/read/7"
    )
    bundle = "https://docs.omnissa.com/bundle/Horizon8InstallUpgrade/page/CompatibilityMatrix.html"
    assert local_target(bundle, "https://docs.omnissa.com/Guide/Topic", by_url, by_slug) == "/read/4"
    missing = local_target("https://kb.omnissa.com/s/article/999", "https://docs.omnissa.com/Guide/Topic", by_url, by_slug)
    assert missing.startswith("/missing?url=")


def test_search_documents_matches_a_word(tmp_path: Path):
    conn = connect(tmp_path / "archive.sqlite")
    init_db(conn)
    upsert_document(
        conn,
        source="kb",
        url="https://kb.omnissa.com/s/article/1",
        locale="en",
        title="Connection error",
        guide="kb",
        html="<p>The connection error is logged.</p>",
        text="The connection error is logged.",
        http_status=200,
    )
    conn.commit()
    rows = search_documents(conn, "error")
    assert len(rows) == 1
    assert "error" in rows[0]["snippet"].lower()


def test_install_database_switches_the_reader(tmp_path: Path):
    packaged = tmp_path / "monthly.sqlite"
    conn = connect(packaged)
    init_db(conn)
    upsert_document(
        conn,
        source="kb",
        url="https://kb.omnissa.com/s/article/1",
        locale="en",
        title="Monthly article",
        guide="kb",
        html="<p>Monthly article</p>",
        text="Monthly article",
        http_status=200,
    )
    conn.commit()
    conn.close()
    reader = ArchiveReader(tmp_path / "data")
    saved = reader.install_database("monthly.sqlite", packaged.read_bytes())
    assert Path(saved).is_file()
    assert reader.counts()["kb"] == 1
    reader.use_download_database()
    assert reader.database_path().name == "archive.sqlite"


def test_parse_multipart_file():
    body = (
        b"--bound\r\n"
        b'Content-Disposition: form-data; name="database"; filename="pack.sqlite"\r\n'
        b"\r\n"
        b"SQLite format 3\x00hi\r\n"
        b"--bound--\r\n"
    )
    files = _parse_multipart("multipart/form-data; boundary=bound", body)
    assert files["database"][0] == "pack.sqlite"
    assert files["database"][1].startswith(b"SQLite format 3")


def test_prepare_article_highlights_and_strips_scripts():
    html = '<div class="doc-body"><script>alert(1)</script><p>Horizon connection error</p><img src="assets/pic.png"></div>'
    rendered = prepare_article(html, "https://docs.omnissa.com/Guide/Topic", {}, {}, ["error"])
    assert "<script>" not in rendered
    assert "<mark>error</mark>" in rendered
    assert 'src="/assets/pic.png"' in rendered


def test_catalog_filters_by_product_version_and_date(tmp_path: Path):
    reader = ArchiveReader(tmp_path)
    conn = connect(tmp_path / "archive.sqlite")
    init_db(conn)
    shared = {
        "locale": "en",
        "guide": "Guide",
        "html": "<p>Horizon connection server details for this archived page.</p>",
        "text": "Horizon connection server details for this archived page.",
        "http_status": 200,
        "product_family": "Horizon",
        "category": "Product Documentation",
    }
    upsert_document(
        conn,
        source="docs",
        url="https://docs.omnissa.com/a",
        title="Notification",
        product="App Volumes",
        version="2606",
        published_at="2024-03-29",
        **shared,
    )
    upsert_document(
        conn,
        source="docs",
        url="https://docs.omnissa.com/b",
        title="Old ports",
        product="Horizon",
        version="2212",
        published_at="2022-12-01",
        **shared,
    )
    conn.commit()
    conn.close()
    page = reader.catalog_page(
        "docs",
        {
            "family": "Horizon",
            "product": "App Volumes",
            "version": "2606",
            "category": "",
            "from": "2024-01-01",
            "to": "2024-12-31",
        },
        1,
    ).decode("utf-8")
    assert "Notification" in page
    assert "Old ports" not in page
    assert "מתאריך" in page
    assert "גרסה" in page
    assert "<th>תאריך</th><th>מספר KB</th><th>נושא</th><th>קטגוריה</th>" in page
    assert "2024-03-29" in page
    assert "App Volumes" in page


def test_catalog_shows_kb_article_id_only_for_kb_rows(tmp_path: Path):
    reader = ArchiveReader(tmp_path)
    conn = connect(tmp_path / "archive.sqlite")
    init_db(conn)
    shared = {
        "locale": "en",
        "guide": "Guide",
        "html": "<p>Archived page body for catalog rendering.</p>",
        "text": "Archived page body for catalog rendering.",
        "http_status": 200,
        "product_family": "Horizon",
        "category": "Product Documentation",
        "published_at": "2024-03-29",
    }
    upsert_document(
        conn,
        source="kb",
        url="https://kb.omnissa.com/s/article/1027744",
        title="Log locations",
        product="Horizon",
        version="8",
        **shared,
    )
    upsert_document(
        conn,
        source="docs",
        url="https://docs.omnissa.com/Horizon8InstallUpgrade/CompatibilityMatrix",
        title="Compatibility matrix",
        product="Horizon",
        version="8",
        **shared,
    )
    conn.commit()
    conn.close()

    kb_page = reader.catalog_page("kb", {}, 1).decode("utf-8")
    assert "<th>מספר KB</th>" in kb_page
    assert ">1027744<" in kb_page
    assert "Log locations" in kb_page

    docs_page = reader.catalog_page("docs", {}, 1).decode("utf-8")
    assert "<th>מספר KB</th>" in docs_page
    assert "1027744" not in docs_page
    assert '<td class="kbnum">—</td>' in docs_page
    assert "Compatibility matrix" in docs_page
