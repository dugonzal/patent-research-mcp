"""Dynamic selector probing — auto-discovers structure when registry fails.

When ExtractionReport shows 0/N selectors succeeded for a section,
SelectorProbe scans the HTML DOM for likely patent content and proposes
candidate CSS selectors. This makes extraction resilient to HTML changes.

Two probing strategies:
1. Structural — looks for sections with itemprop, headings, text density
2. Semantic — uses common patent section keywords in headings
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from parsel import Selector

if TYPE_CHECKING:
    from .registry import SourceConfig  # noqa: F401

# Keywords that identify patent sections in heading text
SECTION_SIGNALS: dict[str, list[str]] = {
    "abstract": ["abstract", "brief summary", "disclosure"],
    "claims": ["claims", "what is claimed", "what we claim"],
    "description": ["description", "detailed description", "best mode"],
    "background": ["background", "field of the invention", "technical field"],
}

# Common structural patterns: elements with these selectors near text
STRUCTURAL_PATTERNS = [
    'section[itemprop$="{section}"]',
    'div[class*="{section}"]',
    '[class*="{section}"]',
    'div[id*="{section}"]',
    '[id*="{section}"]',
    'section[data-testid*="{section}"]',
]


@dataclass
class ProbeCandidate:
    """A candidate selector discovered by probing."""

    selector: str
    confidence: float  # 0.0–1.0
    match_type: str  # "structural", "semantic", "id"
    text: str = ""  # extracted text for immediate use
    score_reason: str = ""


@dataclass
class ProbeReport:
    """Result of probing a single section."""

    section: str
    candidates: list[ProbeCandidate] = field(default_factory=list)
    found: bool = False

    def best(self) -> ProbeCandidate | None:
        return max(self.candidates, key=lambda c: c.confidence) if self.candidates else None


class SelectorProbe:
    """Scans HTML DOM to discover selectors for patent sections.

    Use when ExtractionReport shows all selectors failed for a section.
    """

    def __init__(self, sel: Selector):
        self.sel = sel

    # ── Public API ────────────────────────────────────────────────────

    def probe_section(self, section: str) -> ProbeReport:
        """Probe HTML for a given section and return ranked candidates."""
        report = ProbeReport(section=section)
        candidates: list[ProbeCandidate] = []
        seen: set[str] = set()  # dedup selectors

        # Strategy 1: structural patterns
        for pattern in STRUCTURAL_PATTERNS:
            css = pattern.format(section=section)
            elements = self.sel.css(css)
            for el in elements:
                selector = _element_css_path(el)
                if selector and selector not in seen:
                    seen.add(selector)
                    text = " ".join(el.css("::text").getall()).strip()
                    if len(text) > 50:
                        confidence = _score_selector(el, section, text)
                        candidates.append(
                            ProbeCandidate(
                                selector=selector,
                                confidence=confidence,
                                match_type="structural",
                                text=text[:5000],
                                score_reason=f"pattern matched + text length {len(text)}",
                            )
                        )

        # Strategy 2: semantic — find headings matching section keywords
        keywords = SECTION_SIGNALS.get(section, [section])
        for heading_tag in ["h1", "h2", "h3", "h4", "strong", "th"]:
            for el in self.sel.css(heading_tag):
                text = " ".join(el.css("::text").getall()).strip().lower()
                if any(kw in text for kw in keywords):
                    # Try next sibling first (common structure: <h2>ABSTRACT</h2><div>content</div>)
                    siblings = el.xpath("following-sibling::*[1]")
                    if siblings:
                        content = siblings[0]
                        section_text = " ".join(content.css("::text").getall()).strip()
                        if len(section_text) > 50:
                            selector = _element_css_path(content)
                            if selector and selector not in seen:
                                seen.add(selector)
                                confidence = min(0.6 + _score_selector(content, section, section_text), 1.0)
                                candidates.append(
                                    ProbeCandidate(
                                        selector=selector,
                                        confidence=confidence,
                                        match_type="semantic",
                                        text=section_text[:5000],
                                        score_reason=f"heading '{text[:40]}' + following-sibling text",
                                    )
                                )
                                continue

                    # Fallback: walk up 1 level to parent
                    parents = el.xpath("..")
                    if parents:
                        parent = parents[0]
                        selector = _element_css_path(parent)
                        if selector and selector not in seen:
                            seen.add(selector)
                            section_text = " ".join(parent.css("::text").getall()).strip()
                            confidence = _score_semantic(text, section) + 0.2
                            candidates.append(
                                ProbeCandidate(
                                    selector=selector,
                                    confidence=min(confidence, 0.7),
                                    match_type="semantic",
                                    text=section_text[:5000],
                                    score_reason=f"heading '{text[:40]}' + parent container",
                                )
                            )

        # Strategy 3: text density — look for large text blocks near section
        large_blocks = self.sel.css("div, section, article")
        for el in large_blocks:
            text = " ".join(el.css("::text").getall()).strip()
            if 200 < len(text) < 20000:
                parent_id = el.css("::attr(id)").get("") or ""
                parent_class = el.css("::attr(class)").get("") or ""
                combined = f"{parent_id} {parent_class}".lower()
                if any(kw in combined for kw in keywords):
                    selector = _element_css_path(el)
                    if selector and selector not in seen:
                        seen.add(selector)
                        candidates.append(
                            ProbeCandidate(
                                selector=selector,
                                confidence=0.3,
                                match_type="id",
                                text=text[:5000],
                                score_reason=f"id/class contains keyword: {combined[:40]}",
                            )
                        )

        report.candidates = sorted(candidates, key=lambda c: c.confidence, reverse=True)
        report.found = len(report.candidates) > 0
        return report

    def propose_all(self) -> dict[str, ProbeReport]:
        """Probe all known section types and return ranked proposals."""
        return {s: self.probe_section(s) for s in SECTION_SIGNALS}


# ─── Internal helpers ───


def _element_css_path(el) -> str:
    """Build a unique-ish CSS path for an element using XPath name()."""
    tag = (el.xpath("name(.)").get("") or "div").lower()
    el_id = el.css("::attr(id)").get("")
    if el_id:
        return f"#{el_id}"

    classes = el.css("::attr(class)").get("")
    if classes:
        cls = ".".join(c for c in classes.split() if c)[:40]
        return f"{tag}.{cls}" if cls else tag

    return tag


def _score_selector(el, section: str, text: str) -> float:
    """Score a candidate selector 0.0–1.0 based on text signals."""
    score = 0.3  # base
    # More text = more likely to be a real section
    if len(text) > 500:
        score += 0.3
    elif len(text) > 100:
        score += 0.2
    # Check for numbered items (claims, paragraphs)
    if re.search(r"(?:^|\n)\s*\d+\.\s", text):
        score += 0.2
    # Check for patent-like sentences
    if re.search(r"(comprising|wherein|the method of|apparatus of)", text[:500], re.I):
        score += 0.2
    # itemprop match is strong signal
    itemprop = el.css("::attr(itemprop)").get("")
    if itemprop and section in itemprop:
        score += 0.3
    return min(score, 1.0)


def _score_semantic(heading: str, section: str) -> float:
    """Score a semantic match 0.0–1.0."""
    keywords = SECTION_SIGNALS.get(section, [section])
    matches = sum(1 for kw in keywords if kw in heading)
    if matches == 0:
        return 0.1
    return min(0.5 + (matches / len(keywords)) * 0.5, 1.0)
