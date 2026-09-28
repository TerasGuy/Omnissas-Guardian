import re
import sqlite3

from omnissa_archive.db import init_db
from omnissa_archive.progress import (
    download_message,
    format_queue_summary,
    local_timestamp,
    progress_line,
)


_TS = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def test_local_timestamp_format():
    assert _TS.match(local_timestamp())


def test_progress_line_prefixes_message_without_changing_it():
    message = "docs 12/100 Example Title"
    line = progress_line(message)
    assert _TS.match(line[:19])
    assert line[19] == " "
    assert line[20:] == message
    assert re.match(
        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} docs 12/100 Example Title$",
        line,
    )


def test_download_message_kb_includes_article_id():
    url = "https://kb.omnissa.com/s/article/1027744"
    msg = download_message("kb", 12, 4902, url, "Location of Horizon View log files")
    assert msg == (
        "kb 12/4902 KB 1027744 | Location of Horizon View log files"
    )


def test_download_message_docs_uses_em_dash_for_kb():
    url = "https://docs.omnissa.com/bundle/horizon/page/release-notes.html"
    msg = download_message("docs", 13, 34278, url, "Omnissa Horizon 8 Release Notes")
    assert msg == (
        "docs 13/34278 KB — | Omnissa Horizon 8 Release Notes"
    )


def test_format_queue_summary_counts(tmp_path):
    conn = sqlite3.connect(tmp_path / "t.sqlite")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.execute(
        "INSERT INTO documents (source, url, title, html, text, content_hash, fetched_at) "
        "VALUES ('docs', 'https://example/a', 'A', '', '', 'h', 't')"
    )
    conn.execute(
        "INSERT INTO crawl_queue (url, source, status, attempts, updated_at) VALUES "
        "('https://example/a', 'docs', 'done', 1, 't'),"
        "('https://example/b', 'docs', 'pending', 0, 't'),"
        "('https://example/c', 'kb', 'running', 1, 't'),"
        "('https://example/d', 'kb', 'error', 2, 't')"
    )
    conn.commit()
    assert format_queue_summary(conn) == (
        "saved=1 done=1 pending=1 running=1 error=1"
    )
