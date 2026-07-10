"""Centralized selector registry for patent sources.

Single Source of Truth for all CSS/XPath selectors and URL patterns.
Adding a new source (EPO, WIPO, etc.) = new dict entry in SOURCES.
"""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


class SelectorSet(TypedDict, total=False):
    """Ordered list of CSS selectors for each section, tried in sequence."""
    abstract: list[str]
    claims: list[str]
    description: list[str]
    background: list[str]


class SourceConfig(TypedDict):
    """Configuration for a patent source."""
    label: str
    base_url: str
    selectors: NotRequired[SelectorSet]
    title_selectors: NotRequired[list[str]]
    pdf_urls: NotRequired[list[str]]
    user_agent: NotRequired[str]
    lang: NotRequired[str]  # language suffix, e.g. "en"
    fetch_timeout: NotRequired[int]  # ms
    viewport: NotRequired[dict[str, int]]  # {"width": N, "height": N}
    block_extensions: NotRequired[list[str]]  # resource types to block
    wait_until: NotRequired[Literal["commit", "domcontentloaded", "load", "networkidle"]]


SOURCES: dict[str, SourceConfig] = {
    "google_patents": {
        "label": "Google Patents",
        "base_url": "https://patents.google.com/patent",
        "lang": "en",
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "fetch_timeout": 30000,
        "viewport": {"width": 1280, "height": 800},
        "wait_until": "load",
        "block_extensions": ["png", "jpg", "jpeg", "gif", "svg", "ico", "woff", "woff2", "ttf", "eot", "mp4", "webm"],
        "selectors": {
            "abstract": [
                'section[itemprop="abstract"] div[itemprop="content"]',
                'section[itemprop="abstract"]',
                "div.abstract",
                'meta[name="DC.description"]::attr(content)',
            ],
            "claims": [
                'section[itemprop="claims"] div[itemprop="content"]',
                'section[itemprop="claims"]',
                "div.claims",
            ],
            "description": [
                'section[itemprop="description"] div[itemprop="content"]',
                'section[itemprop="description"]',
                "div.description",
            ],
            "background": [
                'section[itemprop="background"]',
                "section.background",
            ],
        },
        "title_selectors": [
            'meta[property="og:title"]::attr(content)',
            "h1::text",
            "title::text",
        ],
        "pdf_urls": [
            "https://patentimages.storage.googleapis.com/pdfs/{pub_num}.pdf",
            "https://patentimages.storage.googleapis.com/{pub_num}/{pub_num}.pdf",
            "https://patents.google.com/patent/{pub_num}/en?ogf=true",
            "https://pdfpiw.uspto.gov/{pub_num}.pdf",  # USPTO fallback
        ],
    },
}


def get_source(name: str = "google_patents") -> SourceConfig:
    """Get source config by name, with friendly error."""
    if name not in SOURCES:
        available = ", ".join(SOURCES)
        raise KeyError(f"Unknown source '{name}'. Available: {available}")
    return SOURCES[name]


def register_source(name: str, config: SourceConfig) -> None:
    """Register a new patent source at runtime."""
    SOURCES[name] = config
