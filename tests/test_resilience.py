"""Tests for extraction resilience: DOM mutation, probe fallback, rate limits."""

from __future__ import annotations

from parsel import Selector

from src.patent_research_mcp.extractor import PatentExtractor
from src.patent_research_mcp.registry import SOURCES

# ── Fixtures ───────────────────────────────────────────────────────────

GOOGLE_PATENT_HTML = """<html><body>
  <section id="abstract-section" itemprop="abstract">
    <div itemprop="content">A method for autonomous commerce operations comprising a kernel engine that processes Things through configurable state machines with orthogonal dimensions.</div>
  </section>
  <section id="claims-section" itemprop="claims">
    <div itemprop="content">
      1. A system comprising a processor and memory configured to execute governed actions on commerce objects with precondition validation.
      2. The system of claim 1 wherein the processor executes state transitions across multiple orthogonal dimensions simultaneously.
      3. The method of claim 2 further comprising a ledger that records each decision with evidence pointers.
    </div>
  </section>
  <section id="description-section" itemprop="description">
    <div itemprop="content">The present invention relates to commerce operations and more particularly to a kernel that receives Things with state dimensions and executes governed actions through a rules engine.</div>
  </section>
</body></html>"""

MUTATED_HTML = """<html><body>
  <!-- Google changed all class names — registry selectors fail -->
  <div id="gp-content">
    <h2>ABSTRACT</h2>
    <div class="gp-body">A method for autonomous commerce operations comprising a kernel engine that processes Things through configurable state machines with orthogonal dimensions.</div>
    <h2>CLAIMS</h2>
    <div class="gp-body">
      1. A system comprising a processor and memory configured to execute governed actions on commerce objects with precondition validation.
      2. The system of claim 1 wherein the processor executes state transitions across multiple orthogonal dimensions simultaneously.
    </div>
    <h2>DETAILED DESCRIPTION</h2>
    <div class="gp-body">The present invention relates to commerce operations and more particularly to a kernel that receives Things with state dimensions and executes governed actions through a rules engine.</div>
  </div>
</body></html>"""


# ── Tests ──────────────────────────────────────────────────────────────


def test_registry_selectors_work():
    """Happy path: registry selectors extract correctly."""
    cfg = SOURCES["google_patents"]
    ext = PatentExtractor(cfg)
    sel = Selector(text=GOOGLE_PATENT_HTML)

    abstract = ext.extract_section(sel, "abstract")
    assert "autonomous commerce" in abstract, f"Expected abstract text, got: {abstract[:50]}"
    assert ext.fallback_rate == 0.0, "Should not fall back on standard HTML"


def test_dom_mutation_probe_fallback():
    """When Google changes CSS classes, probe falls back to semantic headings."""
    cfg = SOURCES["google_patents"]
    ext = PatentExtractor(cfg)
    sel = Selector(text=MUTATED_HTML)

    # Registry selectors fail (different classes) → probe kicks in
    abstract = ext.extract_section(sel, "abstract")
    assert abstract, "Abstract should be extracted via probe"
    assert "autonomous commerce" in abstract, f"Expected abstract text, got: {abstract[:50]}"

    claims = ext.extract_section(sel, "claims")
    assert claims, "Claims should be extracted via probe"
    assert "system comprising" in claims, f"Expected claims text, got: {claims[:50]}"

    description = ext.extract_section(sel, "description")
    assert description, "Description should be extracted via probe"
    assert "present invention" in description, f"Expected description, got: {description[:50]}"

    # Verify probe extracted the correct sections (not mixed up)
    assert "CLAIMS" not in abstract.upper() or claims, "Claims should not appear in abstract"
    assert description != claims, "Description should differ from Claims"

    # Verify report logs probe usage
    report = ext.report
    probe_attempts = [a for a in report.attempts if "[probe]" in a.selector]
    assert len(probe_attempts) >= 3, f"Expected >=3 probe attempts, got: {len(probe_attempts)}"
    assert all(a.success for a in probe_attempts), "All probe attempts should succeed"


def test_fallback_rate_tracking():
    """Fallback rate increases and triggers warning threshold."""
    cfg = SOURCES["google_patents"]
    ext = PatentExtractor(cfg)
    sel = Selector(text=MUTATED_HTML)

    assert ext.fallback_rate == 0.0, "Initial rate should be 0"

    # Extract 3 sections, all should fall back to probe
    for section in ["abstract", "claims", "description"]:
        result = ext.extract_section(sel, section)
        assert result, f"{section} should extract"

    assert ext._total_calls == 3, f"Expected 3 total calls, got: {ext._total_calls}"
    assert ext._fallback_calls == 3, f"Expected 3 fallback calls, got: {ext._fallback_calls}"
    assert ext.fallback_rate == 1.0, "Fallback rate should be 100%"

    # 2nd extraction from normal HTML uses registry (no fallback)
    norm_sel = Selector(text=GOOGLE_PATENT_HTML)
    ext.extract_section(norm_sel, "abstract")
    assert ext._total_calls == 4, f"Expected 4 total calls, got: {ext._total_calls}"
    assert ext._fallback_calls == 3, "Fallback calls should not increase for registry match"


def test_sections_distinct_after_probe():
    """Probe must return distinct content per section, not the same container."""
    cfg = SOURCES["google_patents"]
    ext = PatentExtractor(cfg)
    sel = Selector(text=MUTATED_HTML)

    abstract = ext.extract_section(sel, "abstract") or ""
    claims = ext.extract_section(sel, "claims") or ""
    description = ext.extract_section(sel, "description") or ""

    assert abstract not in claims, "Abstract text should not appear in Claims"
    assert abstract not in description, "Abstract text should not appear in Description"
    assert claims not in abstract, "Claims text should not appear in Abstract"


def test_probe_candidates_ranked():
    """Probe should return highest-confidence candidate first."""
    cfg = SOURCES["google_patents"]
    ext = PatentExtractor(cfg)
    from src.patent_research_mcp.probe import SelectorProbe

    sel = Selector(text=MUTATED_HTML)
    probe = SelectorProbe(sel)

    report = probe.probe_section("claims")
    assert report.found, "Probe should find claims candidates"
    assert len(report.candidates) > 0, "Should have at least one candidate"

    best = report.best()
    assert best is not None, "Should return a best candidate"
    assert best.confidence > 0.0, "Best candidate should have confidence > 0"
    assert "system comprising" in best.text, "Best candidate should contain claim text"


def test_extraction_report_format():
    """ExtractionReport properly logs all selector attempts."""
    cfg = SOURCES["google_patents"]
    ext = PatentExtractor(cfg)
    sel = Selector(text=MUTATED_HTML)

    ext.extract_section(sel, "abstract")

    summary = ext.report.summary()
    assert "Extraction report:" in summary
    assert "abstract:" in summary
    assert "[probe]" in summary  # should have probe attempts


def test_rate_limit_config():
    """Google Patents has rate limit defaults in registry."""
    cfg = SOURCES["google_patents"]
    rl = cfg.get("rate_limit", {})
    assert rl.get("delay_seconds") == 2.0
    assert rl.get("max_retries") == 3
    assert rl.get("backoff_base") == 2.0
