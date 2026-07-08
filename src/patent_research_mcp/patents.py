"""Patent fetching and section extraction for Nexo Research MCP.

Downloads patents from Google Patents, extracts structured sections,
and normalizes text for further analysis.
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .schemas import FetchResult, PatentSections
from .store import _home, load_raw_html, load_raw_text, save_raw_html, save_raw_text

# ── Constants ─────────────────────────────────────────────────────────

GOOGLE_PATENTS_BASE = "https://patents.google.com/patent"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
TIMEOUT = 60.0

# ── Fetch ─────────────────────────────────────────────────────────────


async def fetch_patent(
    publication_number: str | None = None,
    url: str | None = None,
    pdf: bool = False,
) -> FetchResult:
    """Download a patent from Google Patents.

    Accepts either a publication_number (e.g. US7979296B2) or a full URL.
    Saves raw HTML and extracted plain text to data/raw/.
    When pdf=True, also downloads the PDF version.
    """
    if url:
        target_url = url
        pub_num = _extract_pub_number(url)
    elif publication_number:
        pub_num = publication_number
        target_url = f"{GOOGLE_PATENTS_BASE}/{pub_num}/en"
    else:
        return FetchResult(
            publication_number="unknown",
            html_path="",
            text_path="",
            status="failed",
            error="Either publication_number or url is required",
        )

    # Check if already fetched
    existing = load_raw_text(pub_num)
    if existing:
        result = FetchResult(
            publication_number=pub_num,
            html_path=str(pub_num),
            text_path=str(pub_num),
            title=_extract_title(existing),
            status="already_exists",
        )
        if pdf:
            pdf_path = await _fetch_pdf(pub_num)
            if pdf_path:
                result.pdf_path = pdf_path
                result.status = "fetched"
        return result

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(target_url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as e:
        return FetchResult(
            publication_number=pub_num,
            html_path="",
            text_path="",
            status="failed",
            error=str(e),
        )

    # Save raw HTML
    save_raw_html(pub_num, html)

    # Extract plain text
    text = _html_to_text(html)
    save_raw_text(pub_num, text)

    title = _extract_title(text) or _extract_title_from_html(html)

    # Download PDF if requested
    pdf_result_path = None
    if pdf:
        pdf_result_path = await _fetch_pdf(pub_num)

    return FetchResult(
        publication_number=pub_num,
        html_path=pub_num,
        text_path=pub_num,
        pdf_path=pdf_result_path,
        title=title,
        status="fetched",
    )


async def _fetch_pdf(pub_num: str) -> str | None:
    """Download PDF version of a patent.

    Tries multiple sources: Google Patents PDF endpoint,
    USPTO PDF service, and patent images storage.
    Returns the local file path or None.
    """
    pdf_path = str(_home() / "raw" / f"{pub_num}.pdf")

    sources = [
        f"https://patentimages.storage.googleapis.com/pdfs/{pub_num}.pdf",
        f"https://patentimages.storage.googleapis.com/{pub_num}/{pub_num}.pdf",
        f"https://patents.google.com/patent/{pub_num}/en?ogf=true",
    ]

    for url in sources:
        try:
            async with httpx.AsyncClient(
                timeout=10.0, follow_redirects=True
            ) as client:
                resp = await client.get(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                        ),
                        "Accept": "application/pdf,application/octet-stream,*/*",
                    },
                )
                ct = resp.headers.get("content-type", "").lower()
                cd = resp.headers.get("content-disposition", "").lower()
                size = len(resp.content)

                # Valid PDF: correct content-type, or content-disposition with .pdf, or
                # large binary response that's clearly a PDF
                is_pdf = (
                    "pdf" in ct
                    or "pdf" in cd
                    or ("application" in ct and size > 50000)
                    or (ct == "application/octet-stream" and size > 50000)
                )

                if resp.status_code == 200 and is_pdf:
                    Path(pdf_path).write_bytes(resp.content)
                    return pdf_path

                # Skip HTML responses (these are the Google page, not a PDF)
                if "html" in ct:
                    continue
        except Exception:
            continue

    return None


# ── Section extraction ────────────────────────────────────────────────


def extract_sections(publication_number: str) -> PatentSections | None:
    """Extract structured sections from a previously fetched patent."""
    text = load_raw_text(publication_number)
    html = load_raw_html(publication_number)

    if not text and not html:
        return None

    sections = PatentSections(publication_number=publication_number)

    # Extract from HTML first (richer structure)
    if html:
        soup = BeautifulSoup(html, "lxml")

        # Remove scripts and styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        sections.title = _extract_title_from_soup(soup) or sections.title
        sections.assignee = _extract_assignee(soup)
        sections.inventors = _extract_inventors(soup)
        sections.publication_date = _extract_pub_date(soup)
        sections.abstract = _extract_abstract(soup)
        sections.background = _extract_background(soup)
        sections.summary = _extract_summary(soup)
        sections.description = _extract_description(soup)
        sections.claims = _extract_claims(soup)

    # Fallback to text-based extraction
    if text:
        sections.title = sections.title or _extract_title(text)
        sections.abstract = sections.abstract or _extract_section(text, "abstract")
        sections.background = sections.background or _extract_section(text, "background")
        sections.summary = sections.summary or _extract_section(text, "summary")
        sections.description = sections.description or _extract_section(text, "description")
        sections.claims = sections.claims or _extract_claims_from_text(text)

    return sections


# ── HTML extraction helpers ───────────────────────────────────────────


def _extract_pub_number(url: str) -> str:
    """Extract publication number from a Google Patents URL."""
    match = re.search(r"/patent/([A-Z]+\d+[A-Z0-9]*)/", url)
    if match:
        return match.group(1)
    match = re.search(r"patent/([A-Z]+\d+[A-Z0-9]*)", url)
    if match:
        return match.group(1)
    return "unknown"


def _html_to_text(html: str) -> str:
    """Convert patent HTML to plain text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def _extract_title_from_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    return _extract_title_from_soup(soup)


def _extract_title_from_soup(soup: BeautifulSoup) -> str | None:
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Clean " - Google Patents" suffix
        title = re.sub(r"\s*-\s*Google\s+Patents$", "", title)
        return title if title else None
    return None


def _extract_title(text: str) -> str | None:
    """Extract title from first few lines of text."""
    lines = text.strip().split("\n")[:20]
    for line in lines:
        line = line.strip()
        if line and len(line) > 10 and len(line) < 300:
            return line
    return None


def _extract_assignee(soup: BeautifulSoup) -> str | None:
    for span in soup.find_all("span", attrs={"class": "assignee"}):
        text = span.get_text(strip=True)
        if text:
            return text
    return None


def _extract_inventors(soup: BeautifulSoup) -> list[str]:
    inventors: list[str] = []
    for span in soup.find_all("span", attrs={"class": "inventor-name"}):
        text = span.get_text(strip=True)
        if text:
            inventors.append(text)
    return inventors


def _extract_pub_date(soup: BeautifulSoup) -> str | None:
    for td in soup.find_all("td", attrs={"class": "published"}):
        text = td.get_text(strip=True)
        if text:
            return text
    return None


def _extract_abstract(soup: BeautifulSoup) -> str | None:
    section = soup.find("section", attrs={"itemprop": "abstract"})
    if section:
        return section.get_text(separator=" ", strip=True)
    div = soup.find("div", attrs={"class": "abstract", "lang": "EN"})
    if div:
        return div.get_text(separator=" ", strip=True)
    return None


def _extract_background(soup: BeautifulSoup) -> str | None:
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "background" in heading.get_text(strip=True).lower():
            div = heading.find_next("div")
            if div:
                return div.get_text(separator=" ", strip=True)
    return None


def _extract_summary(soup: BeautifulSoup) -> str | None:
    for heading in soup.find_all(["h2", "h3", "h4"]):
        text = heading.get_text(strip=True).lower()
        if "summary" in text and "abstract" not in text:
            div = heading.find_next("div")
            if div:
                return div.get_text(separator=" ", strip=True)
    return None


def _extract_description(soup: BeautifulSoup) -> str | None:
    section = soup.find("section", attrs={"itemprop": "description"})
    if section:
        return section.get_text(separator="\n", strip=True)
    return None


def _extract_claims(soup: BeautifulSoup) -> str | None:
    section = soup.find("section", attrs={"itemprop": "claims"})
    if section:
        return section.get_text(separator="\n", strip=True)
    return None


# ── Text-based section extraction (fallback) ──────────────────────────


SECTION_PATTERNS: dict[str, list[str]] = {
    "abstract": [r"(?i)^\s*abstract\s*$", r"(?i)^abstract[:\s]"],
    "background": [r"(?i)^\s*background\s*$", r"(?i)^background[:\s]"],
    "summary": [r"(?i)^\s*summary\s*$", r"(?i)^summary[:\s]"],
    "description": [r"(?i)^\s*description\s*$", r"(?i)^detailed description[:\s]"],
    "claims": [r"(?i)^\s*claims?\s*$", r"(?i)^what is claimed[:\s]"],
}


def _extract_section(text: str, section_name: str) -> str | None:
    """Extract a section from plain text using heuristic boundaries."""
    lines = text.split("\n")
    patterns = SECTION_PATTERNS.get(section_name, [])
    start_idx = -1

    for i, line in enumerate(lines):
        for pattern in patterns:
            if re.match(pattern, line.strip()):
                start_idx = i + 1
                break
        if start_idx >= 0:
            break

    if start_idx < 0:
        return None

    # Collect lines until next section header or end
    section_lines: list[str] = []
    for line in lines[start_idx:]:
        stripped = line.strip()
        if not stripped:
            if section_lines and not section_lines[-1]:
                continue
            section_lines.append("")
            continue
        # Stop at next known section
        if _is_section_header(stripped) and section_lines:
            break
        section_lines.append(stripped)

    result = " ".join(section_lines).strip()
    return result if result else None


def _is_section_header(line: str) -> bool:
    """Check if a line looks like a section header."""
    section_names = [
        "abstract",
        "background",
        "summary",
        "description",
        "detailed description",
        "claims",
        "what is claimed",
        "brief description",
        "cross-reference",
        "field of the invention",
    ]
    return line.lower().strip() in section_names


def _extract_claims_from_text(text: str) -> str | None:
    """Extract claims section from plain text."""
    return _extract_section(text, "claims")
