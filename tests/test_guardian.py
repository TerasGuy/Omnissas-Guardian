from pathlib import Path

from omnissa_archive.guardian import GuardianApp, expand_path


def test_guardian_scan_detects_error_and_suggests_article(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    from omnissa_archive.db import connect, init_db, upsert_document

    conn = connect(data / "archive.sqlite")
    init_db(conn)
    upsert_document(
        conn,
        source="kb",
        url="https://kb.omnissa.com/s/article/1027744",
        locale="en",
        title="Location of Horizon View log files (1027744)",
        guide="kb",
        html="<p>Connection Server LDAP authentication failures.</p>",
        text="Connection Server LDAP authentication failures and Horizon log locations.",
        http_status=200,
        published_at="2025-04-01",
    )
    conn.commit()
    conn.close()

    logs = tmp_path / "logs"
    logs.mkdir()
    log_file = logs / "broker.log"
    log_file.write_text("INFO starting\n", encoding="utf-8")

    app = GuardianApp(data, reader_base="http://127.0.0.1:8765")
    app.state["targets"] = [
        {"id": "custom", "label": "Test logs", "path": str(logs), "enabled": True}
    ]
    app.state["extra_paths"] = []
    app.state["interval_seconds"] = 60
    # Prime offsets at EOF on first pass.
    app.scan_once()
    assert app.alerts == []

    with log_file.open("a", encoding="utf-8") as handle:
        handle.write("ERROR Broker: Connection Server LDAP authentication timeout\n")
    count = app.scan_once()
    assert count == 1
    assert app.alerts
    assert "LDAP" in app.alerts[0]["line"]
    assert app.alerts[0]["suggestions"]
    assert app.alerts[0]["suggestions"][0]["reader_link"].endswith("/read/1")


def test_expand_path_keeps_unc_prefix():
    assert expand_path(r"\\server\share\logs").startswith("\\\\")
