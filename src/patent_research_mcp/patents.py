"""Patent fetching and section extraction for Patent Research MCP.

Downloads patents from Google Patents, extracts structured sections,
and normalizes text for further analysis.
Uses a registry-driven extractor for selector management.
All configurable values flow from the source config in registry.py.
"""

from __future__ import annotations

import logging
import re

from parsel import Selector
from playwright.async_api import async_playwright

from .extractor import PatentExtractor
from .registry import get_source
from .schemas import FetchResult, PatentSections
from .store import _home, load_raw_html, load_raw_text, save_raw_html, save_raw_text

logger = logging.getLogger(__name__)

# All configuration flows from registry — zero hardcoded values
SOURCE = get_source("google_patents")
_extractor: PatentExtractor | None = None


def _get_extractor() -> PatentExtractor:
    global _extractor
    if _extractor is None:
        _extractor = PatentExtractor(SOURCE)
    return _extractor


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
        lang = SOURCE.get("lang", "en")
        url = f"{SOURCE['base_url']}/{pub_num}/{lang}"
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
        title = _get_extractor().extract_title(Selector(text=existing[:5000]))
        return FetchResult(
            publication_number=pub_num,
            html_path=str(pub_num),
            text_path=str(pub_num),
            title=title,
            status="already_exists",
            pdf_path=pdf_result_path,
        )

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            user_agent = SOURCE.get("user_agent", "")
            viewport = SOURCE.get("viewport", {"width": 1280, "height": 800})
            page = await browser.new_page(user_agent=user_agent, viewport=viewport)
            # Block images, fonts, and media for faster page loading
            extensions = SOURCE.get("block_extensions", [])
            if extensions:
                pattern = f"**/*.{{{','.join(extensions)}}}"
                await page.route(pattern, lambda route: route.abort())
            timeout = SOURCE.get("fetch_timeout", 30000)
            wait_until = SOURCE.get("wait_until", "load")
            await page.goto(url, wait_until=wait_until, timeout=timeout)
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

    # Extract sections via registry-driven extractor
    extractor = _get_extractor()
    for section_type in ["abstract", "claims", "description", "background"]:
        section_text = extractor.extract_section(sel, section_type)
        if section_text:
            text_parts.append(f"\n\n=== {section_type.upper()} ===\n\n{section_text}")

    full_text = "\n\n".join(p for p in text_parts if p.strip())
    save_raw_text(pub_num, full_text)

    # Download PDF if requested
    pdf_result_path = None
    if pdf:
        pdf_result_path = await _fetch_pdf(pub_num)

    title = extractor.extract_title(sel)
    logger.debug("Extraction report:\n%s", extractor.report.summary())
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
    extractor = _get_extractor()

    # ── Title ──
    title = extractor.extract_title(sel)

    # ── Abstract — meta tag or section ──
    abstract = extractor.extract_meta(sel, "description")  # meta[name="description"]
    if not abstract:
        abstract = extractor.extract_section(sel, "abstract")

    # ── Claims ──
    claims = extractor.extract_section(sel, "claims")
    if not claims:
        claims = _extract_claims_from_text(pub_num)

    # ── Description ──
    desc_text = extractor.extract_section(sel, "description")
    background = extractor.extract_section(sel, "background")

    # ── Assignee ──
    assignee = extractor.extract_meta(sel, "assignee")
    if not assignee:
        assignee = _extract_by_regex(sel, r"Assignee:\s*(.+?)(?:\\n|$)")
    if not assignee:
        assignee = _extract_by_regex(sel, r"(?:Current )?Assignee[s]?:?\s*</strong>\s*(.+?)(?:<|\\n)")

    # ── Inventors ──
    inventors = extractor.extract_meta_list(sel, "inventor")
    if not inventors:
        inv_text = _extract_by_regex(sel, r"Inventors?:\s*(.+?)(?:\\n|$)")
        if inv_text:
            inventors = [i.strip() for i in inv_text.split(";") if i.strip()]

    # ── Dates ──
    pub_date = extractor.extract_meta(sel, "publicationDate")
    filing_date = extractor.extract_meta(sel, "filingDate")

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
    logger.debug("Extraction report:\n%s", extractor.report.summary())

    return result


# ─── Internal helpers ───


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
    m = re.search(
        r"(?:CLAIMS|What is claimed is:|What we claim is:)(.*?)(?:\n\s*(?:DESCRIPTION|ABSTRACT|DRAWINGS|BACKGROUND))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return m.group(1).strip()
    return ""


async def _fetch_pdf(pub_num: str) -> str | None:
    """Download PDF version of a patent, trying URLs from registry."""
    pdf_urls = SOURCE.get("pdf_urls", [])
    pdf_path = _home() / "raw" / f"{pub_num}.pdf"

    for url_template in pdf_urls:
        source_url = url_template.format(pub_num=pub_num)
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
            logger.debug("PDF download failed for %s", source_url, exc_info=True)
            continue

    return None


def _save_path(pub_num: str, ext: str) -> str:
    """Return the expected file path for a given extension."""
    return str(_home() / "raw" / f"{pub_num}.{ext}")
