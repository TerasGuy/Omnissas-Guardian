from pathlib import Path

from omnissa_archive.db import (
    connect,
    enqueue,
    init_db,
    mark_done,
    mark_running,
    pending_urls,
    reclaim_interrupted,
)


def test_fetch_resume_skips_done_retries_pending_and_interrupted(tmp_path: Path):
    conn = connect(tmp_path / "archive.sqlite")
    init_db(conn)
    done = "https://docs.omnissa.com/Guide/Done"
    pending = "https://docs.omnissa.com/Guide/Pending"
    interrupted = "https://docs.omnissa.com/Guide/Interrupted"
    enqueue(
        conn,
        [
            (done, "docs"),
            (pending, "docs"),
            (interrupted, "docs"),
        ],
    )
    mark_done(conn, done)
    conn.commit()
    mark_running(conn, interrupted)

    remaining = pending_urls(conn, "docs")
    assert done not in remaining
    assert pending in remaining
    assert interrupted in remaining
    assert reclaim_interrupted(conn) == 0  # already reclaimed inside pending_urls
    assert conn.execute(
        "SELECT status FROM crawl_queue WHERE url = ?", (interrupted,)
    ).fetchone()["status"] == "pending"
