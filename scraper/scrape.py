"""
Web scraper for DarGlobal and Wasalt public data.
This script scrapes publicly available information and saves it for the chatbot.
"""

import json
import os
import re
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser


class SimpleHTMLTextExtractor(HTMLParser):
    """Extract text content from HTML, ignoring scripts and styles."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = False
        self._skip_tags = {"script", "style", "noscript"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)

    def get_text(self):
        return " ".join(self.text_parts)


class JSONLDExtractor(HTMLParser):
    """Extract JSON-LD structured data from HTML."""

    def __init__(self):
        super().__init__()
        self._in_jsonld = False
        self._data = []
        self._json_objects = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attr_dict = dict(attrs)
            if attr_dict.get("type") == "application/ld+json":
                self._in_jsonld = True
                self._data = []

    def handle_endtag(self, tag):
        if tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            raw = "".join(self._data)
            try:
                self._json_objects.append(json.loads(raw))
            except json.JSONDecodeError:
                pass

    def handle_data(self, data):
        if self._in_jsonld:
            self._data.append(data)

    def get_json_ld(self):
        return self._json_objects


class MetaExtractor(HTMLParser):
    """Extract meta tags from HTML."""

    def __init__(self):
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attr_dict = dict(attrs)
            name = attr_dict.get("name") or attr_dict.get("property", "")
            content = attr_dict.get("content", "")
            if name and content:
                self.meta[name] = content


def fetch_page(url: str, timeout: int = 15) -> str:
    """Fetch a web page and return its HTML content."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except (URLError, HTTPError) as e:
        print(f"  Warning: Could not fetch {url}: {e}")
        return ""


def extract_structured_data(html: str) -> dict:
    """Extract structured data (JSON-LD, meta tags, text) from HTML."""
    # JSON-LD
    jsonld_ext = JSONLDExtractor()
    jsonld_ext.feed(html)
    jsonld = jsonld_ext.get_json_ld()

    # Meta tags
    meta_ext = MetaExtractor()
    meta_ext.feed(html)
    meta = meta_ext.meta

    # Plain text
    text_ext = SimpleHTMLTextExtractor()
    text_ext.feed(html)
    text = text_ext.get_text()

    return {"json_ld": jsonld, "meta": meta, "text_preview": text[:3000]}


def scrape_darglobal() -> dict:
    """Scrape publicly available data from DarGlobal website."""
    print("Scraping DarGlobal (darglobal.co.uk)...")
    base = "https://www.darglobal.co.uk"
    pages = {
        "home": base,
        "about": f"{base}/about",
        "projects": f"{base}/projects",
        "press": f"{base}/press",
        "investor": f"{base}/investor",
    }

    results = {}
    for name, url in pages.items():
        print(f"  Fetching {name}: {url}")
        html = fetch_page(url)
        if html:
            results[name] = extract_structured_data(html)
        else:
            results[name] = {"error": "Could not fetch page"}

    return results


def scrape_wasalt() -> dict:
    """Scrape publicly available data from Wasalt website."""
    print("Scraping Wasalt (wasalt.com)...")
    urls = [
        "https://www.wasalt.com",
        "https://www.wasalt.com/en",
        "https://wasalt.com/en/about",
    ]

    results = {}
    for url in urls:
        name = url.split("/")[-1] or "home"
        print(f"  Fetching {name}: {url}")
        html = fetch_page(url)
        if html:
            results[name] = extract_structured_data(html)
        else:
            results[name] = {"error": f"Could not fetch page (may require JS or return 403)"}

    return results


def build_knowledge_base():
    """Build the knowledge base from scraped data and curated information."""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    # Attempt live scraping
    print("=" * 60)
    print("Starting web scraping for DarGlobal and Wasalt...")
    print("=" * 60)

    scraped = {
        "darglobal_pages": scrape_darglobal(),
        "wasalt_pages": scrape_wasalt(),
    }

    # Save raw scraped data
    raw_path = os.path.join(data_dir, "raw_scraped.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(scraped, f, indent=2, ensure_ascii=False)
    print(f"\nRaw scraped data saved to: {raw_path}")

    # Load curated data (already prepared)
    curated_path = os.path.join(data_dir, "scraped_data.json")
    if os.path.exists(curated_path):
        with open(curated_path, "r", encoding="utf-8") as f:
            curated = json.load(f)
        print(f"Curated data loaded from: {curated_path}")
    else:
        curated = {}
        print("Warning: No curated data found.")

    # Build text chunks for the knowledge base
    chunks = build_text_chunks(curated)
    chunks_path = os.path.join(data_dir, "knowledge_chunks.json")
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"Knowledge chunks saved to: {chunks_path}")
    print(f"Total chunks: {len(chunks)}")

    return chunks


def build_text_chunks(data: dict) -> list:
    """Convert structured data into text chunks for RAG retrieval."""
    chunks = []

    # --- DarGlobal chunks ---
    dg = data.get("darglobal", {})

    # Company overview
    overview = dg.get("company_overview", {})
    chunks.append({
        "id": "dg_overview",
        "source": "darglobal",
        "category": "company_overview",
        "text": (
            f"Dar Global PLC (DarGlobal) is {overview.get('type', 'a luxury real estate developer')}. "
            f"Tagline: '{overview.get('tagline', '')}'. "
            f"{overview.get('description', '')} "
            f"The company is listed on the {overview.get('stock_exchange', 'London Stock Exchange')} "
            f"and headquartered in {overview.get('headquarters', 'London, UK')}. "
            f"Website: {overview.get('website', 'https://www.darglobal.co.uk')}"
        ),
    })

    # Key statistics
    stats = dg.get("key_statistics", {})
    chunks.append({
        "id": "dg_stats",
        "source": "darglobal",
        "category": "statistics",
        "text": (
            f"Dar Global key statistics (as of {stats.get('data_as_of', 'Q3 2026')}): "
            f"Track record of {stats.get('track_record', '32 years')}. "
            f"Gross Development Value (GDV) of {stats.get('gross_development_value', '$23 billion')}. "
            f"Present in {stats.get('international_markets', 7)} international markets. "
            f"Has {stats.get('global_brand_partners', '12+')} global brand partners."
        ),
    })

    # Financial results
    fin = dg.get("financial_results", {})
    fy25 = fin.get("fy2025", {})
    fy24 = fin.get("fy2024", {})
    hy26 = fin.get("hy2026", {})
    gdv = fin.get("gdv_growth", {})
    chunks.append({
        "id": "dg_financials_fy25",
        "source": "darglobal",
        "category": "financials",
        "text": (
            f"Dar Global FY2025 Financial Results: Revenue of {fy25.get('revenue', 'US$538.6 million')}, "
            f"Gross Profit of {fy25.get('gross_profit', 'US$189.7 million')}, "
            f"EBITDA of {fy25.get('ebitda', 'US$126.6 million')}, "
            f"Net Profit of {fy25.get('net_profit', 'US$100.8 million')}, "
            f"Return on Equity (ROE) of {fy25.get('return_on_equity', '17.3%')}."
        ),
    })
    chunks.append({
        "id": "dg_financials_fy24",
        "source": "darglobal",
        "category": "financials",
        "text": (
            f"Dar Global FY2024 Financial Results: Revenue of {fy24.get('revenue', 'US$240.3 million')}, "
            f"Gross Profit of {fy24.get('gross_profit', 'US$87.4 million')}, "
            f"EBITDA of {fy24.get('ebitda', 'US$30.1 million')}, "
            f"Net Profit of {fy24.get('net_profit', 'US$14.9 million')}."
        ),
    })
    chunks.append({
        "id": "dg_financials_hy26",
        "source": "darglobal",
        "category": "financials",
        "text": (
            f"Dar Global HY2026 (First Half 2026) Results: Revenue of {hy26.get('revenue', 'US$258.0 million')}, "
            f"representing a {hy26.get('revenue_growth', '66% increase')} compared to HY 2025 revenue "
            f"of {hy26.get('hy2025_revenue', 'US$155.4 million')}."
        ),
    })
    chunks.append({
        "id": "dg_gdv_growth",
        "source": "darglobal",
        "category": "financials",
        "text": (
            f"Dar Global Gross Development Value (GDV) Growth: "
            f"End of 2024: {gdv.get('end_2024', 'US$7.5 billion')}. "
            f"End of 2025: {gdv.get('end_2025', 'US$19 billion')}. "
            f"Heading into 2026: {gdv.get('heading_2026', 'US$23 billion')}."
        ),
    })

    # Geographic presence
    geo = dg.get("geographic_presence", [])
    chunks.append({
        "id": "dg_geography",
        "source": "darglobal",
        "category": "geography",
        "text": (
            f"Dar Global operates across {len(geo)} international markets: "
            f"{', '.join(geo)}. The company focuses on luxury real estate in "
            f"the GCC (UAE, Saudi Arabia, Qatar, Oman), Europe (Spain, Greece, UK), and the Maldives."
        ),
    })

    # Brand partners
    partners = dg.get("brand_partners", [])
    chunks.append({
        "id": "dg_partners",
        "source": "darglobal",
        "category": "partnerships",
        "text": (
            f"Dar Global's luxury brand partners include: {', '.join(partners)}. "
            f"These collaborations bring world-class design, branding, and lifestyle elements "
            f"to Dar Global's real estate developments."
        ),
    })

    # Projects
    for proj in dg.get("latest_projects", []):
        chunk_text = (
            f"Dar Global Project: {proj['name']}. "
            f"Location: {proj.get('location', 'N/A')}. "
            f"Type: {proj.get('type', 'N/A')}. "
            f"Description: {proj.get('description', '')}. "
        )
        if proj.get("details"):
            chunk_text += f"Details: {proj['details']}. "
        if proj.get("url"):
            chunk_text += f"URL: {proj['url']}"
        chunks.append({
            "id": f"dg_project_{proj['name'].lower().replace(' ', '_')[:30]}",
            "source": "darglobal",
            "category": "projects",
            "text": chunk_text,
        })

    # News
    for i, news in enumerate(dg.get("recent_news", [])):
        chunks.append({
            "id": f"dg_news_{i}",
            "source": "darglobal",
            "category": "news",
            "text": (
                f"Dar Global News ({news.get('date', 'N/A')}): "
                f"{news.get('headline', '')}. {news.get('summary', '')}"
            ),
        })

    # Strategic initiatives
    strat = dg.get("strategic_initiatives", {})
    chunks.append({
        "id": "dg_strategy",
        "source": "darglobal",
        "category": "strategy",
        "text": (
            f"Dar Global Strategic Initiatives: "
            f"Asset Management: {strat.get('asset_management', 'N/A')}. "
            f"DGCP: {strat.get('dgcp', 'N/A')}. "
            f"LSE Milestone: {strat.get('lse_milestone', 'N/A')}."
        ),
    })

    # --- Wasalt chunks ---
    ws = data.get("wasalt", {})

    # Company overview
    ws_overview = ws.get("company_overview", {})
    chunks.append({
        "id": "ws_overview",
        "source": "wasalt",
        "category": "company_overview",
        "text": (
            f"Wasalt is {ws_overview.get('type', 'a PropTech company')}. "
            f"{ws_overview.get('description', '')} "
            f"Licensed by: {ws_overview.get('license', 'REGA')}. "
            f"Coverage: {ws_overview.get('coverage', 'major Saudi cities')}. "
            f"Website: {ws_overview.get('website', 'https://www.wasalt.com')}. "
            f"Wasalt is a subsidiary of {ws_overview.get('parent_company', 'Quara Holding')}."
        ),
    })

    # Services
    for svc in ws.get("core_services", []):
        chunks.append({
            "id": f"ws_service_{svc['name'].lower().replace(' ', '_')[:30]}",
            "source": "wasalt",
            "category": "services",
            "text": f"Wasalt Service - {svc['name']}: {svc['description']}",
        })

    # Property types
    prop_types = ws.get("property_types", {})
    all_types = []
    for category, types in prop_types.items():
        all_types.append(f"{category.title()}: {', '.join(types)}")
    chunks.append({
        "id": "ws_property_types",
        "source": "wasalt",
        "category": "properties",
        "text": (
            f"Wasalt lists various property types across Saudi Arabia: "
            f"{'. '.join(all_types)}."
        ),
    })

    # Key features
    features = ws.get("key_features", [])
    chunks.append({
        "id": "ws_features",
        "source": "wasalt",
        "category": "features",
        "text": (
            f"Wasalt platform key features: {'; '.join(features)}."
        ),
    })

    # Coverage cities
    cities = ws.get("coverage_cities", [])
    chunks.append({
        "id": "ws_cities",
        "source": "wasalt",
        "category": "geography",
        "text": (
            f"Wasalt covers major cities across Saudi Arabia including: {', '.join(cities)}."
        ),
    })

    # Relationship
    rel = ws.get("relationship_with_darglobal", "")
    if rel:
        chunks.append({
            "id": "ws_dg_relationship",
            "source": "wasalt",
            "category": "relationship",
            "text": f"Relationship between Wasalt and DarGlobal: {rel}",
        })

    return chunks


if __name__ == "__main__":
    chunks = build_knowledge_base()
    print(f"\nScraping complete! Generated {len(chunks)} knowledge chunks.")
