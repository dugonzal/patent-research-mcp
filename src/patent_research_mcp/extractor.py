"""Patent extraction engine — source-agnostic, registry-driven.

PatentExtractor takes a SourceConfig and iterates selector candidates
in order, logging which succeeded/failed. When all candidates fail,
automatically falls back to SelectorProbe for DOM discovery.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from parsel import Selector

if TYPE_CHECKING:
    from .registry import SourceConfig

logger = logging.getLogger(__name__)


class ExtractionAttempt:
    """Record of a single selector attempt for debugging / LLM feedback."""

    def __init__(self, section: str, selector: str, success: bool, preview: str = ""):
        self.section = section
        self.selector = selector
        self.success = success
        self.preview = preview[:120]

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"[{status}] {self.section}: {self.selector} -> {self.preview}"


class ExtractionReport:
    """Full extraction trace — which selectors were tried and which worked."""

    def __init__(self) -> None:
        self.attempts: list[ExtractionAttempt] = []

    def log(self, section: str, selector: str, success: bool, preview: str = "") -> None:
        self.attempts.append(ExtractionAttempt(section, selector, success, preview))

    def failed_selectors(self) -> list[str]:
        """Return all selectors that failed. Useful for LLM auto-correction."""
        return [a.selector for a in self.attempts if not a.success]

    def summary(self) -> str:
        lines = [f"Extraction report: {sum(1 for a in self.attempts if a.success)}/{len(self.attempts)} selectors succeeded"]
        for a in self.attempts:
            lines.append(f"  {a}")
        return "\n".join(lines)


class PatentExtractor:
    """Extracts patent sections using registry-driven selector strategy.

    Usage:
        extractor = PatentExtractor(source_config)
        title = extractor.extract_title(sel)
        abstract = extractor.extract_section(sel, "abstract")

    Tracks fallback rate: if SelectorProbe activates > FALLBACK_THRESHOLD
    of total extractions, logs a critical warning — signals the source's
    DOM has fundamentally changed.
    """

    FALLBACK_THRESHOLD = 0.10  # warn if >10% of extractions fall back to probe

    def __init__(self, source: SourceConfig):
        self.source = source
        self._report = ExtractionReport()
        self._total_calls = 0
        self._fallback_calls = 0

    @property
    def report(self) -> ExtractionReport:
        return self._report

    @property
    def fallback_rate(self) -> float:
        """Ratio of extractions that fell back to SelectorProbe (0.0–1.0)."""
        if self._total_calls == 0:
            return 0.0
        return self._fallback_calls / self._total_calls

    def _check_fallback_rate(self) -> None:
        """Log critical warning if fallback rate exceeds threshold."""
        if self._total_calls >= 5 and self.fallback_rate > self.FALLBACK_THRESHOLD:
            logger.critical(
                "Fallback rate %.0f%% exceeds threshold %.0f%% for source '%s' — "
                "DOM may have changed, update registry.py manually",
                self.fallback_rate * 100, self.FALLBACK_THRESHOLD * 100,
                self.source.get("label", "unknown"),
            )

    # ── Public API ────────────────────────────────────────────────────

    def extract_title(self, sel: Selector) -> str:
        """Extract patent title using ordered selectors from registry."""
        for css_path in self.source.get("title_selectors", []):
            if css_path.endswith("::attr(content)"):
                text = sel.css(css_path).get("")
            else:
                text = sel.css(css_path).get("")
            if text:
                text = text.strip()
                if text:
                    # Clean site name suffix for title tags
                    text = re.sub(r"\s*[-–|]\s*Google\s+Patents.*$", "", text).strip()
                    text = re.sub(r"\s+", " ", text).strip()
                    if text:
                        self._report.log("title", css_path, True, text[:80])
                        return text
            self._report.log("title", css_path, False)
        return ""

    def extract_section(self, sel: Selector, section: str) -> str:
        """Extract a section (abstract/claims/description/background).

        Iterates ordered selectors from registry. Returns first non-empty result.
        Uses getall() for multi-line sections (claims, description), get() for
        single-line sections (abstract via meta tags).
        """
        selectors = self.source.get("selectors", {}).get(section, [])
        if not selectors:
            logger.warning("No selectors registered for section '%s'", section)
            return ""

        self._total_calls += 1
        is_multi = section in ("claims", "description", "background")

        for css_path in selectors:
            try:
                if is_multi:
                    texts = sel.css(f"{css_path} ::text").getall()
                    if texts:
                        result = "\n".join(t.strip() for t in texts if t.strip())
                        self._report.log(section, css_path, True, result[:80])
                        return result
                else:
                    raw = sel.css(css_path).get("")
                    if raw:
                        # Clean inline HTML (e.g. meta tag content containing markup)
                        cleaned = Selector(text=raw)
                        text = " ".join(cleaned.css("::text").getall()).strip()
                        if text:
                            self._report.log(section, css_path, True, text[:80])
                            return text
                self._report.log(section, css_path, False)
            except Exception as e:
                logger.debug("Selector %s failed on section '%s': %s", css_path, section, e)
                self._report.log(section, css_path, False, f"error: {e}")

        # ── Fallback: probe DOM when all registered selectors fail ──
        self._fallback_calls += 1
        logger.info("All %d selectors failed for '%s' — probing DOM (fallback rate %.0f%%)",
                     len(selectors), section, self.fallback_rate * 100)
        self._check_fallback_rate()
        from .probe import SelectorProbe  # lazy import to avoid circular dep at module level

        probe = SelectorProbe(sel)
        report = probe.probe_section(section)
        if best := report.best():
            logger.info("Probe found candidate for '%s': %s (confidence %.2f)",
                        section, best.selector, best.confidence)
            if best.text:
                self._report.log(section, f"[probe] {best.selector}", True, best.text[:80])
                return best.text

        return ""

    def extract_meta(self, sel: Selector, itemprop: str) -> str:
        """Extract a single meta tag by itemprop, e.g. 'assignee', 'inventor'."""
        val = sel.css(f'meta[itemprop="{itemprop}"]::attr(content)').get("")
        return val.strip() if val else ""

    def extract_meta_list(self, sel: Selector, itemprop: str) -> list[str]:
        """Extract multiple meta tags by itemprop, e.g. 'inventor'."""
        vals = sel.css(f'meta[itemprop="{itemprop}"]::attr(content)').getall()
        return [v.strip() for v in vals if v.strip()]
