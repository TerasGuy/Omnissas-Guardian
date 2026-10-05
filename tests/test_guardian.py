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
    log_file.write_text(
        "INFO starting\nERROR Broker: Connection Server LDAP authentication timeout\n",
        encoding="utf-8",
    )

    app = GuardianApp(data, reader_base="http://127.0.0.1:8765")
    app.state["targets"] = [
        {"id": "custom", "label": "Test logs", "path": str(logs), "enabled": True}
    ]
    app.state["extra_paths"] = []
    app.state["interval_seconds"] = 60
    count = app.scan_once()
    assert count == 1
    assert app.alerts
    assert "LDAP" in app.alerts[0]["line"]
    assert app.alerts[0]["suggestions"]
    assert app.alerts[0]["suggestions"][0]["reader_link"].endswith("/read/1")

    assert app.scan_once() == 0
    assert len(app.alerts) == 1

    with log_file.open("a", encoding="utf-8") as handle:
        handle.write("ERROR Broker: Connection Server LDAP authentication refused\n")
    assert app.scan_once() == 1
    assert len(app.alerts) == 2


def test_first_scan_of_large_log_reads_the_tail(tmp_path: Path, monkeypatch):
    from omnissa_archive import guardian
    from omnissa_archive.db import connect, init_db

    monkeypatch.setattr(guardian, "FIRST_SCAN_MAX_BYTES", 180)
    data = tmp_path / "data"
    data.mkdir()
    conn = connect(data / "archive.sqlite")
    init_db(conn)
    conn.close()

    logs = tmp_path / "logs"
    logs.mkdir()
    log_file = logs / "broker.log"
    log_file.write_text(
        "ERROR old LDAP authentication failure that should be outside the tail\n"
        + ("x" * 400)
        + "\nERROR Broker: Connection Server LDAP authentication timeout\n",
        encoding="utf-8",
    )
    app = GuardianApp(data, reader_base="http://127.0.0.1:8765")
    app.state["targets"] = [
        {"id": "custom", "label": "Test logs", "path": str(log_file), "enabled": True}
    ]
    app.state["extra_paths"] = []
    assert app.scan_once() == 1
    assert "timeout" in app.alerts[0]["line"]
    assert "outside the tail" not in app.alerts[0]["line"]


def test_expand_path_keeps_unc_prefix():
    assert expand_path(r"\\server\share\logs").startswith("\\\\")


def test_online_search_stays_off_unless_enabled(tmp_path: Path, monkeypatch):
    from omnissa_archive import guardian

    calls = {"n": 0}

    def _boom(*_args, **_kwargs):
        calls["n"] += 1
        raise AssertionError("network should not be checked while online search is off")

    monkeypatch.setattr(guardian, "network_reachable", _boom)
    data = tmp_path / "data"
    data.mkdir()
    app = GuardianApp(data)
    blocked = app.prepare_online_search("LDAP timeout")
    assert blocked["status"] == "disabled"
    assert blocked["urls"] == []
    assert calls["n"] == 0
    assert any("kb.omnissa.com" in item["url"] for item in app.snapshot()["online_sources"])

    app.set_online_search(True)
    monkeypatch.setattr(guardian, "network_reachable", lambda *_a, **_k: False)
    offline = app.prepare_online_search("LDAP timeout")
    assert offline["status"] == "offline"
    assert offline["urls"] == []

    monkeypatch.setattr(guardian, "network_reachable", lambda *_a, **_k: True)
    opened = app.prepare_online_search("LDAP timeout")
    assert opened["status"] == "ok"
    assert "LDAP+timeout" in opened["urls"][0]["url"]
    assert opened["urls"][0]["url"].startswith("https://kb.omnissa.com/")


def test_log_scan_does_not_query_online_sources(tmp_path: Path, monkeypatch):
    from omnissa_archive import guardian
    from omnissa_archive.db import connect, init_db

    def _boom(*_args, **_kwargs):
        raise AssertionError("log scan must not touch the network")

    monkeypatch.setattr(guardian, "network_reachable", _boom)
    data = tmp_path / "data"
    data.mkdir()
    conn = connect(data / "archive.sqlite")
    init_db(conn)
    conn.close()
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "broker.log").write_text("ERROR LDAP timeout\n", encoding="utf-8")
    app = GuardianApp(data)
    app.state["online_search"] = True
    app.state["targets"] = [
        {"id": "custom", "label": "Test logs", "path": str(logs), "enabled": True}
    ]
    app.state["extra_paths"] = []
    assert app.scan_once() == 1


def test_stopping_monitor_drops_the_rest_of_the_scan(tmp_path: Path, monkeypatch):
    from omnissa_archive.db import connect, init_db

    data = tmp_path / "data"
    data.mkdir()
    conn = connect(data / "archive.sqlite")
    init_db(conn)
    conn.close()
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "broker.log").write_text(
        "ERROR first LDAP timeout\nERROR second LDAP timeout\n",
        encoding="utf-8",
    )
    app = GuardianApp(data)
    app.set_monitoring(True)
    app.state["targets"] = [
        {"id": "custom", "label": "Test logs", "path": str(logs), "enabled": True}
    ]
    original = app._make_alert

    def stop_after_first(*args, **kwargs):
        alert = original(*args, **kwargs)
        app.set_monitoring(False)
        return alert

    monkeypatch.setattr(app, "_make_alert", stop_after_first)
    assert app.scan_once(stop_when_paused=True) == 1
    assert len(app.alerts) == 1
    app.set_monitoring("false")
    assert app.state["running"] is False


def test_builtin_watch_paths_can_be_edited_and_removed(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    app = GuardianApp(data)
    assert any(item["id"] == "connection-server" for item in app.state["targets"])
    kept = [dict(item) for item in app.state["targets"] if item["id"] != "connection-server"]
    kept[0]["label"] = "Renamed logs"
    kept[0]["path"] = r"D:\site\logs"
    app.set_watch_targets(kept, 45)

    reloaded = GuardianApp(data)
    ids = [item["id"] for item in reloaded.state["targets"]]
    assert "connection-server" not in ids
    renamed = next(item for item in reloaded.state["targets"] if item["id"] == kept[0]["id"])
    assert renamed["label"] == "Renamed logs"
    assert renamed["path"] == r"D:\site\logs"
    assert reloaded.state["interval_seconds"] == 45

    reloaded.set_watch_targets([], 60)
    empty = GuardianApp(data)
    assert empty.state["targets"] == []


def test_saved_extra_path_becomes_an_editable_target(tmp_path: Path):
    import json

    data = tmp_path / "data"
    data.mkdir()
    (data / "guardian_config.json").write_text(
        json.dumps({"targets": [], "extra_paths": ["\\\\server\\share\\logs"]}),
        encoding="utf-8",
    )
    app = GuardianApp(data)
    assert app.state["extra_paths"] == []
    assert app.state["targets"][0]["path"] == r"\\server\share\logs"
    assert app.state["targets"][0]["enabled"] is True
