from pathlib import Path

# Akamai returns 403 for a custom bot user-agent. A normal browser
# identifier is required to read the public pages. This is not a
# search-engine crawler impersonation.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

DOCS_SITEMAP = "https://docs.omnissa.com/sitemap.xml"
KB_SITEMAP = "https://kb.omnissa.com/SitemapGeneratorVF"
DOCS_HOST = "docs.omnissa.com"
KB_HOST = "kb.omnissa.com"

DOCS_RPS = 3.0
KB_DELAY_SECONDS = 2.0
MAX_ATTEMPTS = 3
PILOT_DOCS = 20
PILOT_KB = 20

DOCS_SEED_URLS = [
    "https://docs.omnissa.com/horizon8-rn-V2606/Horizon8-ReleaseNotes",
    "https://docs.omnissa.com/Horizon8InstallUpgrade/SystemRequirementsforServerComponents",
]
KB_SEED_URLS = [
    "https://kb.omnissa.com/s/article/1027744",
]

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]
