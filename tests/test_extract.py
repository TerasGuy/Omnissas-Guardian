from pathlib import Path

from omnissa_archive.extract import apply_local_paths, extract_docs, extract_kb

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_docs_keeps_body_table_and_english_links():
    html = (FIXTURES / "docs_sample.html").read_text(encoding="utf-8")
    page = "https://docs.omnissa.com/Horizon8InstallUpgrade/SystemRequirements"
    extracted = extract_docs(page, html)
    assert extracted is not None
    assert extracted.title == "Server Requirements"
    assert "<table>" in extracted.html
    assert "8 GB" in extracted.text
    assert "https://docs.omnissa.com/images/architecture.png" in extracted.assets
    assert "https://docs.omnissa.com/files/guide.pdf" in extracted.assets
    assert "https://docs.omnissa.com/bundle/Horizon8InstallUpgrade/page/Compatibility.html" in extracted.links
    assert "https://docs.omnissa.com/Horizon8InstallUpgrade/Ports" in extracted.links
    assert "https://kb.omnissa.com/s/article/1027744" in extracted.links
    assert all("/api/" not in link for link in extracted.links)
    assert all("/de-DE/" not in link for link in extracted.links)


def test_extract_docs_reads_product_version_and_dates():
    html = """
    <html><head>
      <title>Enable Notification | Omnissa Docs</title>
      <meta name="omnissa-family" content="Horizon">
      <meta name="omnissa-product" content="App Volumes">
      <meta name="omnissa-version" content="2606">
      <meta name="omnissa-contenttype" content="Product Documentation">
      <meta name="omnissa-datecreated" content="2024-03-29T08:28:12.000Z">
      <meta name="omnissa-dateupdated" content="2026-09-11T04:37:37.000Z">
    </head><body><article><div class="doc-body">
      <p>Using EnableAppChangeNotification, an svservice parameter, notifications can be presented.</p>
    </div></article></body></html>
    """
    extracted = extract_docs(
        "https://docs.omnissa.com/AppVolumesAdminGuide-V2606/EnableNotificationforAppChange",
        html,
    )
    assert extracted is not None
    assert extracted.product == "App Volumes"
    assert extracted.product_family == "Horizon"
    assert extracted.version == "2606"
    assert extracted.category == "Product Documentation"
    assert extracted.published_at == "2024-03-29"
    assert extracted.updated_at == "2026-09-11"


def test_extract_docs_version_falls_back_to_the_url():
    html = """
    <html><head><title>Release notes | Omnissa Docs</title></head>
    <body><article><div class="doc-body">
      <p>Omnissa Horizon 8 release notes describe the changes in this version of the product.</p>
    </div></article></body></html>
    """
    extracted = extract_docs("https://docs.omnissa.com/horizon8-rn-V2606/Horizon8-ReleaseNotes", html)
    assert extracted is not None
    assert extracted.version == "2606"


def test_extract_kb_uses_article_body_not_chrome():
    html = (FIXTURES / "kb_sample.html").read_text(encoding="utf-8")
    page = "https://kb.omnissa.com/s/article/1027744"
    extracted = extract_kb(page, html)
    assert extracted is not None
    assert "1027744" in extracted.title
    assert "log files" in extracted.text
    assert "https://kb.omnissa.com/sfsites/c/resource/diagram.png" in extracted.assets
    assert not any("share-icon" in asset for asset in extracted.assets)
    assert "https://kb.omnissa.com/s/article/1017939" in extracted.links
    assert "https://docs.omnissa.com/bundle/Horizon-Security/page/Horizon8LogFiles.html" in extracted.links
    assert all("/articles/" not in link for link in extracted.links)


def test_extract_kb_reads_tags_and_published_time():
    html = """
    <html><head>
      <meta name="article:published_time" content="2025-04-01 19:50:15">
      <meta name="article:modified_time" content="2025-04-01 19:50:15">
      <meta name="article:section" content="Troubleshooting">
    </head><body>
      <h1 class="article-title">Location of Horizon View log files (1027744)</h1>
      <div class="tag-group"><div class="tag-title">Product</div><div class="tag-pills"><span class="tag">Horizon</span></div></div>
      <div class="tag-group"><div class="tag-title">Version</div><div class="tag-pills"><span class="tag">8.12</span><span class="tag">8.10</span></div></div>
      <div class="tag-group"><div class="tag-title">Category</div><div class="tag-pills"><span class="tag">Troubleshooting</span></div></div>
      <div id="article_content"><p>This article provides the locations of Horizon log files for connection servers and agents.</p></div>
    </body></html>
    """
    extracted = extract_kb("https://kb.omnissa.com/s/article/1027744", html)
    assert extracted is not None
    assert extracted.product == "Horizon"
    assert extracted.version == "8.12,8.10"
    assert extracted.category == "Troubleshooting"
    assert extracted.published_at == "2025-04-01"
    assert extracted.updated_at == "2025-04-01"


def test_kb_render_state_distinguishes_missing_articles():
    from omnissa_archive.fetch_kb import kb_render_state

    assert kb_render_state('<div id="article_content">logs</div>') == "ready"
    assert kb_render_state("<h1>This article is no longer available</h1>") == "missing"
    assert kb_render_state("<h1>Knowledge Base</h1>") == "pending"


def test_apply_local_paths_keeps_original_url():
    html = '<div><img src="https://docs.omnissa.com/images/architecture.png"><a href="https://docs.omnissa.com/files/guide.pdf">PDF</a></div>'
    mapping = {
        "https://docs.omnissa.com/images/architecture.png": "assets/abc.png",
        "https://docs.omnissa.com/files/guide.pdf": "assets/abc.pdf",
    }
    rewritten = apply_local_paths(html, mapping)
    assert 'src="assets/abc.png"' in rewritten
    assert 'data-original-src="https://docs.omnissa.com/images/architecture.png"' in rewritten
    assert 'href="assets/abc.pdf"' in rewritten
    assert 'data-original-href="https://docs.omnissa.com/files/guide.pdf"' in rewritten
