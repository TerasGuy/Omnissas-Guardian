import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from omnissa_archive.urls import (
    canonicalize,
    canonical_queue_url,
    is_asset_candidate,
    resolve_link,
)


_VERSION_IN_URL = re.compile(r"-V(\d{4}|SaaS)(?:/|$)", re.IGNORECASE)
_ISO_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass
class Extracted:
    title: str
    html: str
    text: str
    assets: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    product: str = ""
    product_family: str = ""
    version: str = ""
    category: str = ""
    published_at: str = ""
    updated_at: str = ""


def _meta_content(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
    if tag is None:
        return ""
    return " ".join((tag.get("content") or "").split())


def _date_only(value: str) -> str:
    match = _ISO_DATE.search(value or "")
    return match.group(1) if match else ""


def _join_tags(values: list[str]) -> str:
    seen: list[str] = []
    for value in values:
        cleaned = " ".join(value.split())
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return ",".join(seen)


def _version_from_url(page_url: str) -> str:
    match = _VERSION_IN_URL.search(urlparse(page_url).path)
    if not match:
        return ""
    token = match.group(1)
    return "SaaS" if token.lower() == "saas" else token


def metadata_from_docs(soup: BeautifulSoup, page_url: str) -> dict[str, str]:
    version = _meta_content(soup, "omnissa-version") or _version_from_url(page_url)
    return {
        "product": _meta_content(soup, "omnissa-product"),
        "product_family": _meta_content(soup, "omnissa-family"),
        "version": version,
        "category": _meta_content(soup, "omnissa-contenttype"),
        "published_at": _date_only(_meta_content(soup, "omnissa-datecreated")),
        "updated_at": _date_only(
            _meta_content(soup, "omnissa-dateupdated") or _meta_content(soup, "omnissa-lastmod")
        ),
    }


def metadata_from_kb(soup: BeautifulSoup, page_url: str = "") -> dict[str, str]:
    del page_url
    groups: dict[str, list[str]] = {}
    for group in soup.select(".tag-group"):
        title_node = group.select_one(".tag-title")
        title = title_node.get_text(" ", strip=True).lower() if title_node else ""
        groups[title] = [pill.get_text(" ", strip=True) for pill in group.select(".tag")]
    category = _join_tags(groups.get("category", [])) or _meta_content(soup, "article:section")
    return {
        "product": _join_tags(groups.get("product", [])),
        "product_family": "",
        "version": _join_tags(groups.get("version", [])),
        "category": category,
        "published_at": _date_only(_meta_content(soup, "article:published_time")),
        "updated_at": _date_only(_meta_content(soup, "article:modified_time")),
    }


def _apply_metadata(extracted: Extracted, meta: dict[str, str]) -> Extracted:
    for key, value in meta.items():
        setattr(extracted, key, value)
    return extracted


def _clean_title(raw: str | None) -> str:
    if not raw:
        return ""
    title = " ".join(raw.split())
    for suffix in (" | Omnissa Docs", " | Omnissa"):
        if title.endswith(suffix):
            title = title[: -len(suffix)].strip()
    return title


def _absolutize_media(node: BeautifulSoup, page_url: str) -> None:
    for tag in node.find_all(["img", "source"]):
        for attr in ("src", "data-src"):
            value = tag.get(attr)
            if value:
                tag[attr] = resolve_link(page_url, value) or value


def _collect(node, page_url: str) -> tuple[list[str], list[str]]:
    assets: list[str] = []
    links: list[str] = []
    for tag in node.find_all(["img", "source"]):
        for attr in ("src", "data-src"):
            value = tag.get(attr)
            if value and is_asset_candidate(value):
                assets.append(value)
    for anchor in node.find_all("a"):
        href = anchor.get("href")
        absolute = resolve_link(page_url, href) if href else None
        if not absolute:
            continue
        if is_asset_candidate(absolute):
            assets.append(absolute)
            continue
        queued = canonical_queue_url(absolute)
        if queued and canonicalize(queued) != canonicalize(page_url):
            links.append(queued)
    return list(dict.fromkeys(assets)), list(dict.fromkeys(links))


def _from_node(node, page_url: str, title: str) -> Extracted | None:
    text = node.get_text("\n", strip=True)
    if len(text) < 40:
        return None
    _absolutize_media(node, page_url)
    assets, links = _collect(node, page_url)
    return Extracted(title=title, html=str(node), text=text, assets=assets, links=links)


def extract_docs(page_url: str, html: str) -> Extracted | None:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("article .doc-body") or soup.select_one(".doc-body")
    if node is None:
        return None
    title = _clean_title(soup.title.get_text(" ", strip=True) if soup.title else "")
    if not title:
        heading = node.find(["h1", "h2"])
        title = heading.get_text(" ", strip=True) if heading else ""
    extracted = _from_node(node, page_url, title)
    if extracted is None:
        return None
    return _apply_metadata(extracted, metadata_from_docs(soup, page_url))


def extract_kb(page_url: str, html: str) -> Extracted | None:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("#article_content")
    if node is None:
        return None
    heading = soup.select_one("h1.article-title") or soup.select_one("#articleContent h1")
    title = heading.get_text(" ", strip=True) if heading else ""
    if not title or title.strip().lower() == "knowledge base":
        title = _clean_title(soup.title.get_text(" ", strip=True) if soup.title else "")
    if title.strip().lower() == "knowledge base":
        parsed = urlparse(page_url)
        title = parsed.path.rstrip("/").split("/")[-1]
    extracted = _from_node(node, page_url, title)
    if extracted is None:
        return None
    return _apply_metadata(extracted, metadata_from_kb(soup, page_url))


def apply_local_paths(html: str, mapping: dict[str, str]) -> str:
    if not mapping:
        return html
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        for attr in ("src", "href", "data-src"):
            value = tag.get(attr)
            if not value or value not in mapping:
                continue
            if attr == "href":
                tag["data-original-href"] = value
            else:
                tag["data-original-src"] = value
            tag[attr] = mapping[value]
    return str(soup)
