"""Shared archive lookup used by Guardian and the reader."""

from __future__ import annotations

import re
import sqlite3

from omnissa_archive.reader import fts_query

NOISE = re.compile(
    r"\b(?:error|exception|failed|failure|fatal|critical|warn|warning|info|debug|"
    r"unable|cannot|could|timeout|timed|out|null|none|true|false|http|https|"
    r"omnissa|vmware|horizon|windows|server)\b",
    re.I,
)
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{2,}|\d{4,}")


def extract_search_terms(error_line: str, limit: int = 8) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for match in TOKEN.finditer(error_line or ""):
        token = match.group(0)
        lowered = token.lower()
        if lowered in seen:
            continue
        if NOISE.fullmatch(token):
            continue
        seen.add(lowered)
        tokens.append(token)
        if len(tokens) >= limit:
            break
    if not tokens:
        for match in TOKEN.finditer(error_line or ""):
            token = match.group(0)
            lowered = token.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            tokens.append(token)
            if len(tokens) >= 4:
                break
    return tokens


def suggest_solutions(
    conn: sqlite3.Connection,
    error_line: str,
    *,
    limit: int = 5,
    reader_base: str = "http://127.0.0.1:8765",
) -> list[dict]:
    terms = extract_search_terms(error_line)
    if not terms:
        plain = fts_query(error_line)
        queries = [plain] if plain else []
    else:
        # OR keeps recall high for noisy log lines; bm25 still ranks better matches first.
        queries = [
            " OR ".join(f'"{token}"*' for token in terms),
            fts_query(" ".join(terms[:3])),
        ]
    rows = []
    seen: set[int] = set()
    for fts in queries:
        if not fts:
            continue
        try:
            found = conn.execute(
                """
                SELECT d.id, d.source, d.title, d.url, d.published_at, d.updated_at,
                       snippet(documents_fts, 1, '', '', ' … ', 32) AS snippet
                FROM documents_fts
                JOIN documents d ON d.id = documents_fts.rowid
                WHERE documents_fts MATCH ?
                ORDER BY bm25(documents_fts)
                LIMIT ?
                """,
                (fts, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            continue
        for row in found:
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            rows.append(row)
            if len(rows) >= limit:
                break
        if len(rows) >= limit:
            break
    base = reader_base.rstrip("/")
    results: list[dict] = []
    for row in rows:
        published = row["published_at"] or row["updated_at"] or ""
        results.append(
            {
                "id": row["id"],
                "source": row["source"],
                "title": row["title"] or "",
                "url": row["url"] or "",
                "published_at": published,
                "excerpt": (row["snippet"] or "").strip(),
                "reader_link": f"{base}/read/{row['id']}",
                "terms": terms,
            }
        )
    return results
