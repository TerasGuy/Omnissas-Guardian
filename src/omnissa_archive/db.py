import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
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
    http_status INTEGER,
    product TEXT NOT NULL DEFAULT '',
    product_family TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    published_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    facets_at TEXT NOT NULL DEFAULT ''
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    title,
    text,
    content='documents',
    content_rowid='id',
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, title, text) VALUES (new.id, new.title, new.text);
END;

CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, text)
    VALUES ('delete', old.id, old.title, old.text);
END;

CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, text)
    VALUES ('delete', old.id, old.title, old.text);
    INSERT INTO documents_fts(rowid, title, text) VALUES (new.id, new.title, new.text);
END;

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    source_url TEXT NOT NULL UNIQUE,
    local_path TEXT,
    sha256 TEXT,
    content_type TEXT,
    document_id INTEGER REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY,
    from_url TEXT NOT NULL,
    to_url TEXT NOT NULL,
    UNIQUE(from_url, to_url)
);

CREATE TABLE IF NOT EXISTS crawl_queue (
    url TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TEXT
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def content_hash(title: str, text: str) -> str:
    payload = f"{title}\n{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


FACET_COLUMNS = (
    "product",
    "product_family",
    "version",
    "category",
    "published_at",
    "updated_at",
    "facets_at",
)


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    have = {row["name"] for row in conn.execute("PRAGMA table_info(documents)")}
    for name in FACET_COLUMNS:
        if name not in have:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS documents_source_published ON documents(source, published_at)"
    )
    conn.commit()


def enqueue(conn: sqlite3.Connection, items: list[tuple[str, str]]) -> int:
    if not items:
        return 0
    now = utcnow()
    before = conn.execute("SELECT COUNT(*) AS n FROM crawl_queue").fetchone()["n"]
    rows = [(url, source, now) for url, source in items]
    for offset in range(0, len(rows), 400):
        conn.executemany(
            """
            INSERT OR IGNORE INTO crawl_queue (url, source, status, attempts, updated_at)
            VALUES (?, ?, 'pending', 0, ?)
            """,
            rows[offset : offset + 400],
        )
    conn.commit()
    after = conn.execute("SELECT COUNT(*) AS n FROM crawl_queue").fetchone()["n"]
    return after - before


def pending_urls(conn: sqlite3.Connection, source: str, limit: int = 0) -> list[str]:
    sql = """
        SELECT url FROM crawl_queue
        WHERE source = ? AND status IN ('pending', 'error') AND attempts < 3
        ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, url
    """
    rows = conn.execute(sql, (source,)).fetchall()
    urls = [row["url"] for row in rows]
    if limit > 0:
        return urls[:limit]
    return urls


def mark_done(conn: sqlite3.Connection, url: str) -> None:
    conn.execute(
        """
        UPDATE crawl_queue
        SET status = 'done', last_error = NULL, updated_at = ?
        WHERE url = ?
        """,
        (utcnow(), url),
    )


def mark_error(conn: sqlite3.Connection, url: str, error: str) -> None:
    conn.execute(
        """
        UPDATE crawl_queue
        SET status = 'error',
            attempts = attempts + 1,
            last_error = ?,
            updated_at = ?
        WHERE url = ?
        """,
        (error[:500], utcnow(), url),
    )


def get_document(conn: sqlite3.Connection, url: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM documents WHERE url = ?", (url,)).fetchone()


def _kept(new: str, previous: str | None) -> str:
    cleaned = " ".join((new or "").split())
    if cleaned:
        return cleaned
    return previous or ""


def upsert_document(
    conn: sqlite3.Connection,
    *,
    source: str,
    url: str,
    locale: str,
    title: str,
    guide: str,
    html: str,
    text: str,
    http_status: int,
    product: str = "",
    product_family: str = "",
    version: str = "",
    category: str = "",
    published_at: str = "",
    updated_at: str = "",
) -> tuple[int, bool]:
    digest = content_hash(title, text)
    existing = get_document(conn, url)
    now = utcnow()
    facets = (
        _kept(product, existing["product"] if existing else ""),
        _kept(product_family, existing["product_family"] if existing else ""),
        _kept(version, existing["version"] if existing else ""),
        _kept(category, existing["category"] if existing else ""),
        _kept(published_at, existing["published_at"] if existing else ""),
        _kept(updated_at, existing["updated_at"] if existing else ""),
        now,
    )
    if existing and existing["content_hash"] == digest:
        conn.execute(
            """
            UPDATE documents
            SET fetched_at = ?, http_status = ?,
                product = ?, product_family = ?, version = ?, category = ?,
                published_at = ?, updated_at = ?, facets_at = ?
            WHERE id = ?
            """,
            (now, http_status, *facets, existing["id"]),
        )
        return existing["id"], False
    if existing:
        conn.execute(
            """
            UPDATE documents
            SET source = ?, locale = ?, title = ?, guide = ?, html = ?, text = ?,
                content_hash = ?, fetched_at = ?, http_status = ?,
                product = ?, product_family = ?, version = ?, category = ?,
                published_at = ?, updated_at = ?, facets_at = ?
            WHERE id = ?
            """,
            (source, locale, title, guide, html, text, digest, now, http_status, *facets, existing["id"]),
        )
        return existing["id"], True
    cur = conn.execute(
        """
        INSERT INTO documents (
            source, url, locale, title, guide, html, text, content_hash, fetched_at, http_status,
            product, product_family, version, category, published_at, updated_at, facets_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (source, url, locale, title, guide, html, text, digest, now, http_status, *facets),
    )
    return int(cur.lastrowid), True


def update_facets(
    conn: sqlite3.Connection,
    url: str,
    *,
    product: str,
    product_family: str,
    version: str,
    category: str,
    published_at: str,
    updated_at: str,
) -> None:
    existing = get_document(conn, url)
    if existing is None:
        return
    conn.execute(
        """
        UPDATE documents
        SET product = ?, product_family = ?, version = ?, category = ?,
            published_at = ?, updated_at = ?, facets_at = ?
        WHERE id = ?
        """,
        (
            _kept(product, existing["product"]),
            _kept(product_family, existing["product_family"]),
            _kept(version, existing["version"]),
            _kept(category, existing["category"]),
            _kept(published_at, existing["published_at"]),
            _kept(updated_at, existing["updated_at"]),
            utcnow(),
            existing["id"],
        ),
    )


def upsert_asset(
    conn: sqlite3.Connection,
    *,
    source_url: str,
    local_path: str,
    sha256: str,
    content_type: str,
    document_id: int | None,
) -> None:
    conn.execute(
        """
        INSERT INTO assets (source_url, local_path, sha256, content_type, document_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(source_url) DO UPDATE SET
            local_path = excluded.local_path,
            sha256 = excluded.sha256,
            content_type = excluded.content_type,
            document_id = excluded.document_id
        """,
        (source_url, local_path, sha256, content_type, document_id),
    )


def get_asset(conn: sqlite3.Connection, source_url: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM assets WHERE source_url = ?", (source_url,)).fetchone()


def replace_links(conn: sqlite3.Connection, from_url: str, to_urls: list[str]) -> None:
    conn.execute("DELETE FROM links WHERE from_url = ?", (from_url,))
    unique = sorted(set(to_urls))
    conn.executemany(
        "INSERT OR IGNORE INTO links (from_url, to_url) VALUES (?, ?)",
        [(from_url, target) for target in unique],
    )


def search(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT d.source, d.url, d.title
        FROM documents_fts
        JOIN documents d ON d.id = documents_fts.rowid
        WHERE documents_fts MATCH ?
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()
