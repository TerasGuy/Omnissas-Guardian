import html
import json
import re
import sqlite3
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from bs4 import BeautifulSoup, NavigableString

from omnissa_archive.db import connect, init_db
from omnissa_archive.urls import canonical_queue_url, resolve_link

TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)
BUNDLE_RE = re.compile(r"/bundle/([^/]+)/page/([^/.]+)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FILTER_KEYS = ("family", "product", "version", "category", "from", "to")
ASSET_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".pdf": "application/pdf",
}

PAGE_CSS = """
:root {
  color-scheme: light;
  --ink: #2c2c3e;
  --coral: #f07a58;
  --teal: #365565;
  --teal-mid: #4d889d;
  --gold: #e8b545;
  --muted: #365565;
  --paper: #f4f4f6;
  --line: #bebec6;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: radial-gradient(900px 420px at 50% -120px, #f8d2c6, transparent 55%), var(--paper); color: var(--ink); }
header { padding: 28px 24px 8px; text-align: center; }
header a { color: var(--ink); text-decoration: none; letter-spacing: -0.03em; font-size: 22px; }
header form { display: flex; gap: 10px; justify-content: center; margin: 18px auto 0; max-width: 680px; }
input[type=search] { flex: 1; padding: 14px 16px; border: 1px solid var(--line); border-radius: 999px; font-size: 16px; background: white; color: var(--ink); box-shadow: 0 8px 24px rgba(44,44,62,.06); }
button { background: var(--coral); color: white; border: 0; border-radius: 999px; padding: 14px 22px; font-weight: 700; cursor: pointer; }
main { max-width: 980px; margin: 0 auto; padding: 12px 24px 48px; }
.board { display: grid; grid-template-columns: repeat(2, minmax(260px, 420px)); gap: 24px; justify-content: center; margin: 36px auto 0; }
.cube { background: white; border-radius: 28px; padding: 28px 26px 18px; min-height: 360px; box-shadow: 0 20px 50px rgba(44,44,62,.08); }
.cube.kb { background: linear-gradient(#fff, #fff) padding-box, linear-gradient(160deg, #365565, #4d889d) border-box; border: 1px solid transparent; }
.cube.docs { background: linear-gradient(#fff, #fff) padding-box, linear-gradient(160deg, #e8b545, #f6e3b0) border-box; border: 1px solid transparent; }
.kicker { margin: 0 0 6px; color: var(--teal); font-size: 13px; font-weight: 700; }
.cube h2 { margin: 0 0 18px; font-size: 28px; letter-spacing: -0.04em; color: var(--ink); }
.cube ol { list-style: none; margin: 0; padding: 0; }
.cube li { border-top: 1px solid var(--line); }
.cube a { display: block; padding: 14px 2px; color: var(--ink); text-decoration: none; font-weight: 600; line-height: 1.35; }
.cube a:hover { color: var(--coral); }
.empty { color: var(--teal); }
.card { background: white; border: 1px solid var(--line); border-radius: 18px; padding: 16px 18px; margin: 12px 0; }
.card a { color: var(--ink); font-weight: 700; text-decoration: none; }
.meta { color: var(--teal); font-size: 13px; margin-top: 4px; }
mark { background: #f6e3b0; padding: 0 2px; }
article { background: white; border: 1px solid var(--line); border-radius: 24px; padding: 32px; line-height: 1.65; box-shadow: 0 16px 40px rgba(44,44,62,.06); }
article a { color: var(--teal); }
article img, article svg { max-width: 100%; height: auto; }
article table { border-collapse: collapse; width: 100%; margin: 12px 0; }
article td, article th { border: 1px solid var(--line); padding: 8px; vertical-align: top; }
article pre { overflow: auto; background: #f4f4f6; padding: 12px; }
a.missing { color: var(--coral); }
.shell { display: flex; min-height: 100vh; }
nav.side { width: 230px; flex: none; background: var(--ink); padding: 28px 16px; }
nav.side a { display: block; color: #bebec6; text-decoration: none; padding: 12px 14px; border-radius: 12px; margin-bottom: 6px; }
nav.side a.active, nav.side a:hover { background: var(--teal); color: white; }
.content { flex: 1; min-width: 0; }
.filters { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; margin: 8px 0 18px; }
.filters label { display: flex; flex-direction: column; gap: 4px; color: var(--teal); font-size: 13px; font-weight: 700; }
.filters select, .filters input[type=date] { min-width: 140px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 12px; background: white; color: var(--ink); font: inherit; }
.filters button { padding: 10px 18px; }
.filters a.clear { align-self: center; color: var(--teal); font-weight: 700; }
.catalog { list-style: none; margin: 0; padding: 0; }
.catalog li { background: white; border: 1px solid var(--line); border-radius: 14px; margin: 8px 0; }
.catalog a { display: block; padding: 14px 16px; color: var(--ink); text-decoration: none; font-weight: 600; }
.catalog a:hover { color: var(--coral); }
.guide { color: var(--teal); font-weight: 500; font-size: 13px; }
.pager { display: flex; gap: 16px; justify-content: center; align-items: center; }
.pager a { color: var(--teal); font-weight: 700; }
.settings { max-width: 640px; margin: 24px auto; background: white; border: 1px solid var(--line); border-radius: 24px; padding: 28px; }
.settings input[type=file] { display: block; margin: 16px 0; }
@media (max-width: 860px) {
  .board { grid-template-columns: minmax(0, 420px); }
  .shell { flex-direction: column; }
  nav.side { width: auto; display: flex; gap: 8px; overflow: auto; }
}
"""


def fts_query(raw: str) -> str:
    tokens = TOKEN_RE.findall(raw or "")
    if not tokens:
        return ""
    return " AND ".join(f'"{token}"*' for token in tokens)


def _csv_like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%,{escaped},%"


def _facet_tokens(rows, column: str) -> list[str]:
    found: set[str] = set()
    for row in rows:
        for part in (row[column] or "").split(","):
            token = part.strip()
            if token:
                found.add(token)
    return sorted(found, key=str.lower)


def _facet_line(row, include_source: bool = True) -> str:
    parts: list[str] = []
    if include_source:
        parts.append(_source_label(row["source"]))
    for key in ("product_family", "product", "version", "category"):
        value = row[key] or ""
        if value:
            parts.append(value.replace(",", ", "))
    if row["published_at"]:
        parts.append(row["published_at"])
    return " · ".join(parts)


def _select(name: str, label: str, values: list[str], selected: str) -> str:
    pool = list(values)
    if selected and selected not in pool:
        pool.append(selected)
    options = ['<option value="">הכל</option>']
    for value in pool:
        mark = " selected" if value == selected else ""
        options.append(f'<option value="{html.escape(value)}"{mark}>{html.escape(value)}</option>')
    return f'<label>{html.escape(label)}<select name="{name}">{"".join(options)}</select></label>'


def _request_filters(query: dict) -> dict[str, str]:
    found: dict[str, str] = {}
    for key in FILTER_KEYS:
        value = (query.get(key, [""])[0] or "").strip()
        if key in ("from", "to") and value and DATE_RE.match(value) is None:
            value = ""
        found[key] = value
    return found


def _filter_query(chosen: dict[str, str], page: int) -> str:
    pairs = [f"{key}={quote(chosen[key])}" for key in FILTER_KEYS if chosen.get(key)]
    if page > 1:
        pairs.append(f"page={page}")
    return f"?{'&'.join(pairs)}" if pairs else ""


def _slug(url: str) -> str:
    path = urlparse(url).path.strip("/")
    slug = path.split("/")[-1] if path else ""
    for suffix in (".html", ".md"):
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
    return slug


def load_index(conn) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    by_url: dict[str, int] = {}
    by_slug: dict[tuple[str, str], int] = {}
    for row in conn.execute("SELECT id, url, guide FROM documents"):
        by_url[row["url"]] = row["id"]
        slug = _slug(row["url"])
        if row["guide"] and slug:
            by_slug[(row["guide"], slug)] = row["id"]
    return by_url, by_slug


def local_target(href: str, page_url: str, by_url: dict[str, int], by_slug: dict[tuple[str, str], int]) -> str:
    if not href or href.startswith(("#", "mailto:", "javascript:", "data:")):
        return href
    if href.startswith("assets/"):
        return "/assets/" + href[len("assets/") :]
    if href.startswith("/assets/"):
        return href
    absolute = resolve_link(page_url, href) or href
    queued = canonical_queue_url(absolute)
    if queued and queued in by_url:
        return f"/read/{by_url[queued]}"
    path = urlparse(absolute).path
    match = BUNDLE_RE.search(path)
    if match:
        key = (match.group(1), match.group(2))
        if key in by_slug:
            return f"/read/{by_slug[key]}"
    if queued or absolute.startswith("http"):
        target = queued or absolute
        return "/missing?url=" + quote(target, safe="")
    return href


def prepare_article(html_body: str, page_url: str, by_url, by_slug, terms: list[str]) -> str:
    soup = BeautifulSoup(html_body or "", "html.parser")
    for tag in soup.find_all(["script", "iframe", "object"]):
        tag.decompose()
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith("on"):
                del tag.attrs[attr]
        for attr in ("src", "href"):
            value = tag.get(attr)
            if isinstance(value, str):
                rewritten = local_target(value, page_url, by_url, by_slug)
                tag[attr] = rewritten
                if attr == "href" and rewritten.startswith("/missing"):
                    tag["class"] = ["missing"]
    if terms:
        pattern = re.compile("(" + "|".join(re.escape(term) for term in terms) + ")", re.I)
        for text in list(soup.find_all(string=True)):
            parent = text.parent
            if parent is None or parent.name in {"script", "style"}:
                continue
            if not pattern.search(str(text)):
                continue
            pieces = []
            for part in pattern.split(str(text)):
                if not part:
                    continue
                if pattern.fullmatch(part):
                    mark = soup.new_tag("mark")
                    mark.string = part
                    pieces.append(mark)
                else:
                    pieces.append(NavigableString(part))
            text.replace_with(*pieces)
    return str(soup)


def _snippet_html(raw: str) -> str:
    escaped = html.escape(raw or "")
    return escaped.replace("\x01", "<mark>").replace("\x02", "</mark>")


def search_documents(conn, raw_query: str, limit: int = 40):
    query = fts_query(raw_query)
    if not query:
        return []
    try:
        return conn.execute(
            """
            SELECT d.id, d.source, d.title, d.url,
                   snippet(documents_fts, 1, char(1), char(2), ' … ', 28) AS snippet
            FROM documents_fts
            JOIN documents d ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH ?
            ORDER BY bm25(documents_fts)
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def _layout(title: str, body: str, query: str = "", active: str = "") -> bytes:
    def item(key: str, href: str, label: str) -> str:
        klass = "active" if key == active else ""
        return f'<a class="{klass}" href="{href}">{label}</a>'

    page = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<div class="shell">
<nav class="side">
  {item("home", "/", "ראשי")}
  {item("kb", "/kb", "מאמרי KB")}
  {item("docs", "/docs", "מסמכי תיעוד")}
  {item("settings", "/settings", "הגדרות")}
</nav>
<div class="content">
<header>
  <a href="/"><strong>ארכיון Omnissa</strong></a>
  <form action="/search" method="get">
    <input type="search" name="q" value="{html.escape(query)}" placeholder="חיפוש: error, תקלה, Horizon, מספר מאמר">
    <button type="submit">חיפוש</button>
  </form>
</header>
<main>{body}</main>
</div>
</div>
</body>
</html>"""
    return page.encode("utf-8")


def _source_label(source: str) -> str:
    return "תיעוד" if source == "docs" else "מאגר ידע"


def _cube(title: str, downloaded: int, discovered: int, rows: list[dict], kind: str) -> str:
    if rows:
        items = "".join(
            f'<li><a href="/read/{row["id"]}">{html.escape(row["title"] or "ללא כותרת")}</a></li>'
            for row in rows
        )
        listing = f"<ol>{items}</ol>"
    else:
        listing = '<p class="empty">עדיין אין מסמכים.</p>'
    return (
        f'<section class="cube {kind}">'
        f'<p class="kicker">{len(rows)} אחרונים · {downloaded:,} ירדו מתוך {discovered:,}</p>'
        f"<h2>{html.escape(title)}</h2>"
        f"{listing}</section>"
    )


class ArchiveReader:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        conn = connect(data_dir / "archive.sqlite")
        init_db(conn)
        conn.close()

    def _config_path(self) -> Path:
        return self.data_dir / "reader_config.json"

    def database_path(self) -> Path:
        config_path = self._config_path()
        if config_path.is_file():
            try:
                chosen = Path(json.loads(config_path.read_text(encoding="utf-8"))["database"])
            except (OSError, json.JSONDecodeError, KeyError, TypeError):
                chosen = None
            if chosen is not None and chosen.is_file():
                return chosen
        return self.data_dir / "archive.sqlite"

    def _write_database_path(self, path: Path) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._config_path().write_text(
            json.dumps({"database": str(path)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _conn(self) -> sqlite3.Connection:
        conn = connect(self.database_path())
        init_db(conn)
        return conn

    def counts(self) -> dict[str, int]:
        conn = self._conn()
        try:
            rows = conn.execute("SELECT source, COUNT(*) AS n FROM documents GROUP BY source").fetchall()
            return {row["source"]: row["n"] for row in rows}
        finally:
            conn.close()

    def _latest(self, conn, source: str) -> list[dict]:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT id, title FROM documents WHERE source = ? ORDER BY id DESC LIMIT 5",
                (source,),
            )
        ]

    def discovered(self) -> dict[str, int]:
        conn = self._conn()
        try:
            rows = conn.execute("SELECT source, COUNT(*) AS n FROM crawl_queue GROUP BY source").fetchall()
            return {row["source"]: row["n"] for row in rows}
        finally:
            conn.close()

    def home(self) -> bytes:
        counts = self.counts()
        found = self.discovered()
        conn = self._conn()
        try:
            latest_kb = self._latest(conn, "kb")
            latest_docs = self._latest(conn, "docs")
        finally:
            conn.close()
        body = (
            '<section class="board">'
            + _cube("מאמרי KB", counts.get("kb", 0), found.get("kb", 0), latest_kb, "kb")
            + _cube("מסמכי תיעוד", counts.get("docs", 0), found.get("docs", 0), latest_docs, "docs")
            + "</section>"
        )
        return _layout("ארכיון Omnissa", body, active="home")

    def search_page(self, raw_query: str) -> bytes:
        terms = TOKEN_RE.findall(raw_query or "")
        conn = self._conn()
        try:
            rows = [dict(row) for row in search_documents(conn, raw_query)]
        finally:
            conn.close()
        if not terms:
            body = "<p>כתבו מילה לחיפוש.</p>"
        elif not rows:
            body = f"<p>אין תוצאות עבור <strong>{html.escape(raw_query)}</strong> במה שכבר ירד.</p>"
        else:
            cards = []
            for row in rows:
                cards.append(
                    '<div class="card">'
                    f'<a href="/read/{row["id"]}?q={quote(raw_query)}">{html.escape(row["title"] or "")}</a>'
                    f'<div class="meta">{_source_label(row["source"])}</div>'
                    f'<p>{_snippet_html(row["snippet"])}</p>'
                    "</div>"
                )
            body = f"<p>{len(rows)} תוצאות עבור <strong>{html.escape(raw_query)}</strong></p>" + "".join(cards)
        return _layout(f"חיפוש: {raw_query}", body, raw_query, active="search")

    def read_page(self, document_id: int, raw_query: str) -> bytes | None:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            if row is None:
                return None
            by_url, by_slug = load_index(conn)
            page_url = row["url"]
            title = row["title"]
            source = row["source"]
            article_html = row["html"] or ""
        finally:
            conn.close()
        article = prepare_article(article_html, page_url, by_url, by_slug, TOKEN_RE.findall(raw_query or ""))
        facts = _facet_line(row)
        body = (
            f'<p class="meta">{html.escape(facts)} · {html.escape(page_url)}</p>'
            f'<article dir="auto">{article}</article>'
        )
        return _layout(title or "מסמך", body, raw_query, active=source)

    def catalog_page(self, source: str, filters: dict[str, str], page: int) -> bytes:
        page = max(1, page)
        chosen = {key: (filters.get(key) or "").strip() for key in FILTER_KEYS}
        conn = self._conn()
        try:
            clauses = ["source = ?"]
            params: list[object] = [source]
            for key, column in (
                ("family", "product_family"),
                ("product", "product"),
                ("version", "version"),
                ("category", "category"),
            ):
                if chosen[key]:
                    clauses.append(f"(',' || ifnull({column}, '') || ',') LIKE ? ESCAPE '\\'")
                    params.append(_csv_like(chosen[key]))
            if chosen["from"] or chosen["to"]:
                clauses.append("published_at != ''")
            if chosen["from"]:
                clauses.append("published_at >= ?")
                params.append(chosen["from"])
            if chosen["to"]:
                clauses.append("published_at <= ?")
                params.append(chosen["to"])
            where = " AND ".join(clauses)
            total = conn.execute(f"SELECT COUNT(*) AS n FROM documents WHERE {where}", params).fetchone()["n"]
            rows = [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT id, title, product, product_family, version, category, published_at
                    FROM documents
                    WHERE {where}
                    ORDER BY CASE WHEN published_at = '' THEN 1 ELSE 0 END,
                             published_at DESC, title COLLATE NOCASE
                    LIMIT ? OFFSET ?
                    """,
                    [*params, 40, (page - 1) * 40],
                )
            ]
            facet_rows = conn.execute(
                """
                SELECT product, product_family, version, category
                FROM documents WHERE source = ?
                """,
                (source,),
            ).fetchall()
        finally:
            conn.close()
        title = "מאמרי KB" if source == "kb" else "מסמכי תיעוד"
        base = "/kb" if source == "kb" else "/docs"
        options = {
            "family": _facet_tokens(facet_rows, "product_family"),
            "product": _facet_tokens(facet_rows, "product"),
            "version": _facet_tokens(facet_rows, "version"),
            "category": _facet_tokens(facet_rows, "category"),
        }
        items = []
        for row in rows:
            facts = _facet_line(row, include_source=False)
            detail = f' <span class="guide">{html.escape(facts)}</span>' if facts else ""
            items.append(
                f'<li><a href="/read/{row["id"]}">{html.escape(row["title"] or "ללא כותרת")}{detail}</a></li>'
            )
        rendered_items = "".join(items)
        start = 0 if total == 0 else (page - 1) * 40 + 1
        end = (page - 1) * 40 + len(rows)
        pages = max(1, (total + 39) // 40)
        prev_link = f'<a href="{base}{_filter_query(chosen, page - 1)}">הקודם</a>' if page > 1 else ""
        next_link = f'<a href="{base}{_filter_query(chosen, page + 1)}">הבא</a>' if page < pages else ""
        listing = (
            f'<ul class="catalog">{rendered_items}</ul>'
            if rendered_items
            else '<p class="empty">אין פריטים שתואמים לסינון.</p>'
        )
        body = (
            f"<h2>{title}</h2>"
            f'<form class="filters" action="{base}" method="get">'
            f"{_select('family', 'משפחת מוצר', options['family'], chosen['family'])}"
            f"{_select('product', 'מוצר', options['product'], chosen['product'])}"
            f"{_select('version', 'גרסה', options['version'], chosen['version'])}"
            f"{_select('category', 'קטגוריה', options['category'], chosen['category'])}"
            f'<label>מתאריך<input type="date" name="from" value="{html.escape(chosen["from"])}"></label>'
            f'<label>עד תאריך<input type="date" name="to" value="{html.escape(chosen["to"])}"></label>'
            f'<button type="submit">סינון</button>'
            f'<a class="clear" href="{base}">ניקוי</a>'
            f"</form>"
            f'<p class="meta">מציג {start}–{end} מתוך {total:,}</p>'
            f"{listing}"
            f'<p class="pager">{prev_link}<span>עמוד {page} מתוך {pages}</span>{next_link}</p>'
        )
        return _layout(title, body, active=source)

    def settings_page(self, notice: str = "") -> bytes:
        current = self.database_path()
        note = f'<p class="card">{html.escape(notice)}</p>' if notice else ""
        body = (
            '<section class="settings">'
            "<h2>הגדרות</h2>"
            f"{note}"
            f'<p>המסד שהקורא פותח עכשיו:</p><p class="meta">{html.escape(str(current))}</p>'
            "<p>אחת לחודש אפשר לטעון כאן קובץ SQLite חדש ולתת אותו ללקוחות. "
            "ההורדה השוטפת ממשיכה להיכתב אל <span class=\"meta\">data/archive.sqlite</span>, "
            "ותיקיית התמונות נשארת <span class=\"meta\">data/assets</span>.</p>"
            '<form method="post" action="/settings" enctype="multipart/form-data">'
            '<input type="file" name="database" accept=".sqlite,.db" required>'
            '<button type="submit">טעינת מסד</button></form>'
            '<form method="post" action="/settings">'
            '<input type="hidden" name="use" value="archive">'
            '<button type="submit">חזרה למסד ההורדה</button></form>'
            "</section>"
        )
        return _layout("הגדרות", body, active="settings")

    def install_database(self, filename: str, payload: bytes) -> str:
        if not payload.startswith(b"SQLite format 3\x00"):
            raise ValueError("הקובץ אינו מסד SQLite")
        libraries = self.data_dir / "libraries"
        libraries.mkdir(parents=True, exist_ok=True)
        stem = Path(filename or "archive.sqlite").name
        stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem) or "archive.sqlite"
        if not stem.lower().endswith((".sqlite", ".db")):
            stem += ".sqlite"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        target = libraries / f"{stamp}-{stem}"
        target.write_bytes(payload)
        conn = sqlite3.connect(target)
        try:
            conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        except sqlite3.Error as exc:
            conn.close()
            target.unlink(missing_ok=True)
            raise ValueError("במסד אין טבלת documents") from exc
        conn.close()
        self._write_database_path(target)
        return str(target)

    def use_download_database(self) -> None:
        self._write_database_path(self.data_dir / "archive.sqlite")

    def missing_page(self, url: str) -> bytes:
        body = (
            "<div class='card'><p>העמוד הזה עוד לא נמצא בארכיון המקומי.</p>"
            f"<p class='meta'>{html.escape(url)}</p>"
            "<p>אחרי שפקודת ההורדה תביא אותו, הקישור ייפתח כאן.</p></div>"
        )
        return _layout("עדיין לא בארכיון", body, active="")

    def asset(self, name: str) -> tuple[bytes, str] | None:
        safe_name = Path(name).name
        if not safe_name or safe_name != name:
            return None
        path = (self.data_dir / "assets" / safe_name).resolve()
        root = (self.data_dir / "assets").resolve()
        if path.parent != root or not path.is_file():
            return None
        content_type = ASSET_TYPES.get(path.suffix.lower(), "application/octet-stream")
        return path.read_bytes(), content_type


def _disposition_value(header: str, key: str) -> str:
    match = re.search(rf'{key}="([^"]*)"', header)
    if match:
        return match.group(1)
    match = re.search(rf"{key}=([^;\r\n]+)", header)
    return match.group(1).strip() if match else ""


def _parse_multipart(content_type: str, body: bytes) -> dict[str, tuple[str, bytes]]:
    if "boundary=" not in content_type:
        return {}
    boundary = content_type.split("boundary=", 1)[1].split(";", 1)[0].strip().strip('"')
    found: dict[str, tuple[str, bytes]] = {}
    for part in body.split(b"--" + boundary.encode("utf-8")):
        if b"Content-Disposition" not in part:
            continue
        header_blob, _, content = part.partition(b"\r\n\r\n")
        if content.endswith(b"\r\n"):
            content = content[:-2]
        header = header_blob.decode("utf-8", errors="replace")
        name = _disposition_value(header, "name")
        if name:
            found[name] = (_disposition_value(header, "filename"), content)
    return found


def build_handler(data_dir: Path):
    reader = ArchiveReader(data_dir)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            raw_query = query.get("q", [""])[0]
            if parsed.path in ("/", "/index.html"):
                self._send(200, reader.home(), "text/html; charset=utf-8")
                return
            if parsed.path == "/search":
                self._send(200, reader.search_page(raw_query), "text/html; charset=utf-8")
                return
            if parsed.path in ("/kb", "/docs"):
                source = "kb" if parsed.path == "/kb" else "docs"
                try:
                    page = max(1, int(query.get("page", ["1"])[0]))
                except ValueError:
                    page = 1
                self._send(200, reader.catalog_page(source, _request_filters(query), page), "text/html; charset=utf-8")
                return
            if parsed.path == "/settings":
                notice = unquote(query.get("notice", [""])[0])
                self._send(200, reader.settings_page(notice), "text/html; charset=utf-8")
                return
            if parsed.path.startswith("/read/"):
                id_text = parsed.path.removeprefix("/read/").strip("/")
                if not id_text.isdigit():
                    self._send(404, _layout("לא נמצא", "<p>מסמך לא נמצא.</p>"), "text/html; charset=utf-8")
                    return
                page = reader.read_page(int(id_text), raw_query)
                if page is None:
                    self._send(404, _layout("לא נמצא", "<p>מסמך לא נמצא.</p>"), "text/html; charset=utf-8")
                    return
                self._send(200, page, "text/html; charset=utf-8")
                return
            if parsed.path == "/missing":
                target = unquote(query.get("url", [""])[0])
                self._send(200, reader.missing_page(target), "text/html; charset=utf-8")
                return
            if parsed.path.startswith("/assets/"):
                found = reader.asset(parsed.path.removeprefix("/assets/"))
                if found is None:
                    self._send(404, b"missing", "text/plain; charset=utf-8")
                    return
                body, content_type = found
                self._send(200, body, content_type)
                return
            self._send(404, _layout("לא נמצא", "<p>הדף לא נמצא.</p>"), "text/html; charset=utf-8")

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/settings":
                self._send(404, b"missing", "text/plain; charset=utf-8")
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            payload = self.rfile.read(length)
            content_type = self.headers.get("Content-Type", "")
            notice = "המסד לא הוחלף"
            try:
                if content_type.startswith("multipart/form-data"):
                    files = _parse_multipart(content_type, payload)
                    filename, data = files.get("database", ("", b""))
                    saved = reader.install_database(filename, data)
                    notice = f"המסד נטען: {saved}"
                else:
                    form = parse_qs(payload.decode("utf-8", errors="replace"))
                    if form.get("use", [""])[0] == "archive":
                        reader.use_download_database()
                        notice = "הקורא חזר למסד ההורדה"
            except ValueError as exc:
                notice = str(exc)
            self.send_response(303)
            self.send_header("Location", "/settings?notice=" + quote(notice))
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            return

    return Handler


def serve(data_dir: Path, port: int = 8765, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), build_handler(data_dir))
    url = f"http://127.0.0.1:{port}/"
    print(f"reader {url}", flush=True)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
