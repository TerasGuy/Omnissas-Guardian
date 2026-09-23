import re
from urllib.parse import urljoin, urlparse, urlunparse

LOCALE_RE = re.compile(r"^/([a-z]{2}-[A-Z]{2})(/|$)")
KB_ARTICLE_RE = re.compile(r"/s/article/(\d+)")
ASSET_EXT_RE = re.compile(r"\.(png|jpe?g|gif|webp|svg|bmp|pdf)(?:$|\?)", re.I)

DOCS_HOSTS = {"docs.omnissa.com"}
KB_HOSTS = {"kb.omnissa.com", "kb.vmware.com"}


def canonicalize(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    if path.endswith(".md"):
        path = path[:-3]
    return urlunparse((parsed.scheme.lower() or "https", parsed.netloc.lower(), path, "", "", ""))


def locale_of(url: str) -> str:
    match = LOCALE_RE.match(urlparse(url).path or "/")
    return match.group(1) if match else "en"


def is_default_locale(url: str) -> bool:
    return locale_of(url) == "en"


def guide_of(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if parts and LOCALE_RE.match("/" + parts[0]):
        parts = parts[1:]
    if not parts:
        return ""
    if parts[0] == "bundle" and len(parts) > 1:
        return parts[1]
    if parts[0] == "s" and len(parts) > 1 and parts[1] == "article":
        return "kb"
    return parts[0]


def _path(url: str) -> str:
    return urlparse(url).path or "/"


def docs_path_allowed(url: str) -> bool:
    path = _path(url)
    if path == "/api" or path.startswith("/api/"):
        return False
    if path == "/search" or path.startswith("/search/") or path.startswith("/search?"):
        return False
    return True


def is_docs_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.netloc.lower() not in DOCS_HOSTS:
        return False
    return docs_path_allowed(url)


def is_english_doc(url: str) -> bool:
    if not is_docs_url(url):
        return False
    path = _path(url)
    if path in ("", "/"):
        return False
    return is_default_locale(url)


def kb_article_id(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    if parsed.netloc.lower() not in KB_HOSTS:
        return None
    path = parsed.path or "/"
    if path.startswith("/articles/"):
        return None
    match = KB_ARTICLE_RE.search(path)
    return match.group(1) if match else None


def canonical_kb(url: str) -> str | None:
    article_id = kb_article_id(url)
    if not article_id:
        return None
    return f"https://kb.omnissa.com/s/article/{article_id}"


def queue_source(url: str) -> str | None:
    kb = canonical_kb(url)
    if kb:
        return "kb"
    if is_english_doc(url):
        return "docs"
    return None


def canonical_queue_url(url: str) -> str | None:
    source = queue_source(url)
    if source == "kb":
        return canonical_kb(url)
    if source == "docs":
        return canonicalize(url)
    return None


def is_asset_candidate(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if not docs_path_allowed(url) and parsed.netloc.lower() in DOCS_HOSTS:
        return False
    path = parsed.path or ""
    if path.startswith("/articles/"):
        return False
    return bool(ASSET_EXT_RE.search(path))


def resolve_link(page_url: str, href: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith(("#", "mailto:", "javascript:", "data:")):
        return None
    return urljoin(page_url, href)
