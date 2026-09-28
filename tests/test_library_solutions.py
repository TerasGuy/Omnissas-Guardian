from pathlib import Path

from omnissa_archive.db import connect, init_db, upsert_document
from omnissa_archive.library import LibraryWatcher, install_uploaded_database, prepare_customer_package
from omnissa_archive.solutions import extract_search_terms, suggest_solutions


def _seed(db: Path) -> None:
    conn = connect(db)
    init_db(conn)
    upsert_document(
        conn,
        source="kb",
        url="https://kb.omnissa.com/s/article/1027744",
        locale="en",
        title="Location of Horizon View log files (1027744)",
        guide="kb",
        html="<p>Horizon Connection Server LDAP authentication timeout details.</p>",
        text="Horizon Connection Server LDAP authentication timeout and log file locations.",
        http_status=200,
        published_at="2025-04-01",
        category="Troubleshooting",
    )
    conn.commit()
    conn.close()


def test_live_reload_promotes_inbox_database(tmp_path: Path):
    data = tmp_path / "data"
    live = data / "library" / "archive.sqlite"
    live.parent.mkdir(parents=True)
    _seed(live)
    watcher = LibraryWatcher(data)
    watcher.bind(live)
    inbox = data / "library" / "inbox"
    inbox.mkdir(parents=True)
    newer = inbox / "monthly.sqlite"
    _seed(newer)
    # ensure newer mtime
    newer.write_bytes(newer.read_bytes())
    event = watcher.poll(live)
    assert event is not None
    assert event.path == live
    assert "תיבה" in event.notice
    assert not newer.exists()


def test_install_uploaded_database_copies_into_library(tmp_path: Path):
    data = tmp_path / "data"
    source = tmp_path / "pack.sqlite"
    _seed(source)
    target = install_uploaded_database(data, "pack.sqlite", source.read_bytes())
    assert target == data / "library" / "archive.sqlite"
    assert target.is_file()


def test_suggest_solutions_returns_reader_link(tmp_path: Path):
    db = tmp_path / "archive.sqlite"
    _seed(db)
    conn = connect(db)
    rows = suggest_solutions(
        conn,
        "ERROR Broker: Unable to authenticate user — Connection Server LDAP timeout",
        reader_base="http://127.0.0.1:8765",
    )
    conn.close()
    assert rows
    assert rows[0]["title"].startswith("Location of Horizon")
    assert rows[0]["published_at"] == "2025-04-01"
    assert rows[0]["reader_link"].endswith("/read/1")
    assert "LDAP" in extract_search_terms("Connection Server LDAP timeout")


def test_prepare_customer_package_writes_open_bat(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    _seed(data / "archive.sqlite")
    (data / "assets").mkdir()
    (data / "assets" / "pic.png").write_bytes(b"png")
    package = prepare_customer_package(data, tmp_path / "dist")
    assert (package / "library" / "archive.sqlite").is_file()
    assert (package / "assets" / "pic.png").is_file()
    assert (package / "Open-Archive.bat").is_file()
