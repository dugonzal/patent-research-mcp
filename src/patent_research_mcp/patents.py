"""Patent fetching and section extraction for Patent Research MCP.

Downloads patents from Google Patents, extracts structured sections,
and normalizes text for further analysis. Uses httpx + parsel for
modern async HTTP and XPath/CSS-based parsing.
"""

from __future__ import annotations

import re

from parsel import Selector
from playwright.async_api import async_playwright

from .schemas import FetchResult, PatentSections
from .store import _home, load_raw_html, load_raw_text, save_raw_html, save_raw_text

GOOGLE_PATENTS_BASE = "https://patents.google.com/patent"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


async def fetch_patent(
    publication_number: str | None = None,
    url: str | None = None,
    pdf: bool = False,
) -> FetchResult:
    """Download a patent from Google Patents.

    Accepts either a publication_number (e.g. 'US7979296B2') or a full URL.
    Saves HTML to data/raw/{pub_num}.html and text to data/raw/{pub_num}.txt.
    If pdf=True, also attempts PDF download.
    Returns FetchResult with paths, title, and status.
    """
    if url:
        pub_num = _extract_pub_number(url)
    elif publication_number:
        pub_num = publication_number.upper().strip()
        url = f"{GOOGLE_PATENTS_BASE}/{pub_num}/en"
    else:
        return FetchResult(
            publication_number="unknown",
            html_path="",
            text_path="",
            status="error: no publication_number or url provided",
        )

    # Check if already downloaded
    existing = load_raw_html(pub_num)
    if existing:
        pdf_result_path = None
        if pdf:
            pdf_result_path = await _fetch_pdf(pub_num)
        title = _extract_title(Selector(text=existing[:5000]))
        result = FetchResult(
            publication_number=pub_num,
            html_path=str(pub_num),
            text_path=str(pub_num),
            title=title,
            status="already_exists",
            pdf_path=pdf_result_path,
        )
        return result

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=USER_AGENT, viewport={"width": 1280, "height": 800})
            # Block images, fonts, and media for faster patent page loading
            await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot,mp4,webm}", lambda route: route.abort())
            await page.goto(url, wait_until="load", timeout=30000)
            html = await page.content()
            await browser.close()
    except Exception as e:
        return FetchResult(
            publication_number=pub_num,
            html_path="",
            text_path="",
            title=None,
            status=f"error: {e}",
        )

    save_raw_html(pub_num, html)

    # Extract text content from HTML
    sel = Selector(text=html)
    text_parts: list[str] = []

    # Remove scripts and styles
    for tag in sel.css("script, style, nav, footer, header"):
        tag.drop()

    # Get all visible text
    body = sel.css("body")
    if body:
        text_parts.append(body.xpath("normalize-space(//body//text())").get(""))

    # Also extract sections more carefully
    for section_type in ["abstract", "claims", "description", "background"]:
        section_text = _extract_section_text(sel, section_type)
        if section_text:
            text_parts.append(f"\n\n=== {section_type.upper()} ===\n\n{section_text}")

    full_text = "\n\n".join(p for p in text_parts if p.strip())
    save_raw_text(pub_num, full_text)

    # Download PDF if requested
    pdf_result_path = None
    if pdf:
        pdf_result_path = await _fetch_pdf(pub_num)

    title = _extract_title(sel)
    return FetchResult(
        publication_number=pub_num,
        html_path=_save_path(pub_num, "html"),
        text_path=_save_path(pub_num, "txt"),
        title=title,
        status="fetched",
            pdf_path=pdf_result_path,
        )


async def get_sections(publication_number: str) -> PatentSections:
    """Extract structured sections from a previously fetched patent.

    Reads from saved HTML. Returns title, abstract, background, summary,
    description, claims, assignee, inventors, dates.
    Saves to data/sections/{pub_num}.sections.json.
    """
    pub_num = publication_number.upper().strip()
    html = load_raw_html(pub_num)

    if not html:
        return PatentSections(
            publication_number=pub_num,
            title="",
            abstract="",
            claims="",
            description="",
            status="not_found: fetch the patent first",
        )

    sel = Selector(text=html)

    # Title
    title = _extract_title(sel)

    # Abstract — meta tag or section
    abstract = ""
    abs_meta = sel.css('meta[name="description"]::attr(content)').get("")
    if abs_meta:
        abstract = abs_meta.strip()
    else:
        abstract = _extract_section_text(sel, "abstract")

    # Claims
    claims = _extract_section_text(sel, "claims") or _extract_claims_from_text(pub_num)

    # Description
    desc_text = _extract_section_text(sel, "description")
    background = _extract_section_text(sel, "background")

    # Assignee
    assignee = ""
    assignee_meta = sel.css('meta[itemprop="assignee"]::attr(content)').get("")
    if assignee_meta:
        assignee = assignee_meta.strip()
    if not assignee:
        assignee = _extract_by_regex(sel, r"Assignee:\s*(.+?)(?:\\n|$)")
    if not assignee:
        assignee = _extract_by_regex(sel, r"(?:Current )?Assignee[s]?:?\s*</strong>\s*(.+?)(?:<|\\n)")

    # Inventors
    inventors: list[str] = []
    invs = sel.css('meta[itemprop="inventor"]::attr(content)').getall()
    if invs:
        inventors = [i.strip() for i in invs if i.strip()]
    if not inventors:
        inv_text = _extract_by_regex(sel, r"Inventors?:\s*(.+?)(?:\\n|$)")
        if inv_text:
            inventors = [i.strip() for i in inv_text.split(";") if i.strip()]

    # Dates
    pub_date = ""
    filing_date = ""
    pub_date_meta = sel.css('meta[itemprop="publicationDate"]::attr(content)').get("")
    if pub_date_meta:
        pub_date = pub_date_meta.strip()
    filing_date_meta = sel.css('meta[itemprop="filingDate"]::attr(content)').get("")
    if filing_date_meta:
        filing_date = filing_date_meta.strip()

    result = PatentSections(
        publication_number=pub_num,
        title=title,
        abstract=abstract[:5000],
        background=background[:3000] if background else "",
        summary="",
        description=desc_text[:10000] if desc_text else "",
        claims=claims[:10000] if claims else "",
        assignee=assignee or None,
        inventors=inventors or [],
        publication_date=pub_date or None,
        filing_date=filing_date or None,
        status="extracted",
    )

    # Save sections
    from .store import save_sections

    save_sections(pub_num, result)

    return result


# ─── Internal helpers ───


def _extract_title(sel: Selector) -> str:
    """Extract patent title from parsed HTML."""
    title = ""
    # Try meta tag first
    meta_title = sel.css('meta[property="og:title"]::attr(content)').get("")
    if meta_title:
        title = meta_title.strip()
    # Try h1
    if not title:
        h1 = sel.css("h1::text").get("")
        if h1:
            title = h1.strip()
    # Try title tag
    if not title:
        t = sel.css("title::text").get("")
        if t:
            # Remove site name suffix
            title = re.sub(r"\s*[-–|]\s*Google\s+Patents.*$", "", t).strip()
    # Clean
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _extract_section_text(sel: Selector, section_type: str) -> str:
    """Extract a specific section (abstract, claims, description, background)."""
    # Google Patents uses structured HTML sections
    if section_type == "abstract":
        # Multiple possible selectors
        for selector in [
            'section[itemprop="abstract"] div[itemprop="content"]',
            'section[itemprop="abstract"]',
            'div.abstract',
            'meta[name="DC.description"]::attr(content)',
        ]:
            text = sel.css(selector).get("")
            if text:
                # Clean HTML tags
                cleaner = Selector(text=text)
                text = " ".join(cleaner.css("::text").getall()).strip()
                if text:
                    return text

    elif section_type == "claims":
        for selector in [
            'section[itemprop="claims"] div[itemprop="content"]',
            'section[itemprop="claims"]',
            'div.claims',
        ]:
            texts = sel.css(f"{selector} ::text").getall()
            if texts:
                return "\n".join(t.strip() for t in texts if t.strip())

    elif section_type == "description":
        for selector in [
            'section[itemprop="description"] div[itemprop="content"]',
            'section[itemprop="description"]',
            'div.description',
        ]:
            texts = sel.css(f"{selector} ::text").getall()
            if texts:
                return "\n".join(t.strip() for t in texts if t.strip())

    elif section_type == "background":
        for selector in [
            'section[itemprop="background"]',
            'section.background',
        ]:
            texts = sel.css(f"{selector} ::text").getall()
            if texts:
                return "\n".join(t.strip() for t in texts if t.strip())

    return ""


def _extract_by_regex(sel: Selector, pattern: str) -> str:
    """Extract text using regex on the full HTML."""
    html = sel.get()
    if not html:
        return ""
    m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def _extract_pub_number(url: str) -> str:
    """Extract publication number from a Google Patents URL."""
    m = re.search(r"/patent/([A-Za-z0-9]+)", url)
    if m:
        return m.group(1)
    return url.strip("/").split("/")[-1]


def _extract_claims_from_text(pub_num: str) -> str:
    """Fallback: extract claims from saved raw text."""
    text = load_raw_text(pub_num)
    if not text:
        return ""
    # Look for claims section in text
    m = re.search(
        r"(?:CLAIMS|What is claimed is:|What we claim is:)(.*?)(?:\n\s*(?:DESCRIPTION|ABSTRACT|DRAWINGS|BACKGROUND))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return m.group(1).strip()
    return ""


async def _fetch_pdf(pub_num: str) -> str | None:
    """Download PDF version of a patent, trying multiple sources."""
    sources = [
        f"https://patentimages.storage.googleapis.com/pdfs/{pub_num}.pdf",
        f"https://patentimages.storage.googleapis.com/{pub_num}/{pub_num}.pdf",
        f"https://patents.google.com/patent/{pub_num}/en?ogf=true",
    ]
    pdf_path = _home() / "raw" / f"{pub_num}.pdf"

    for source_url in sources:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                resp = await page.goto(source_url, timeout=10000)
                if resp and resp.status == 200:
                    body = await resp.body()
                    if len(body) > 1000:
                        pdf_path.write_bytes(body)
                        await browser.close()
                        return str(pdf_path)
                await browser.close()
        except Exception:
            continue

    # Try USPTO as last resort
    try:
        uspto_url = f"https://pdfpiw.uspto.gov/{pub_num}.pdf"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            resp = await page.goto(uspto_url, timeout=10000)
            if resp and resp.status == 200 and len(await resp.body()) > 1000:
                pdf_path.write_bytes(await resp.body())
                await browser.close()
                return str(pdf_path)
            await browser.close()
    except Exception:
        pass

    return None


def _save_path(pub_num: str, ext: str) -> str:
    """Return the expected file path for a given extension."""
    return str(_home() / "raw" / f"{pub_num}.{ext}")
