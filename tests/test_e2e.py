"""E2E test: complete patent research pipeline with local fixtures.

Tests the full pipeline without network or Playwright:
  raw HTML → PatentExtractor → ArchitectureCard → ClaimsFirewall → PatternCard → export

Uses a local HTML fixture mimicking Google Patents structure.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from parsel import Selector

from src.patent_research_mcp.exporter import generate_research_summary_markdown
from src.patent_research_mcp.extractor import PatentExtractor
from src.patent_research_mcp.patents import get_sections
from src.patent_research_mcp.registry import SOURCES
from src.patent_research_mcp.schemas import (
    Architecture,
    ArchitectureCard,
    ClaimsFirewall,
    EnterpriseOntology,
    PatternCard,
    Problem,
    RiskLevel,
)
from src.patent_research_mcp.store import (
    _home,
    list_patterns,
    load_raw_html,
    save_architecture_card,
    save_claims_firewall,
    save_pattern,
    save_sections,
)

PUB = "US7979296B2"

# ── Fixture: realistic Google Patents HTML ─────────────────────────────

PATENT_HTML_FIXTURE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta property="og:title" content="Automated Commerce Operations System and Method - Google Patents">
  <meta name="description" content="A system for automated commerce operations using a state machine kernel with configurable transitions.">
  <meta itemprop="publicationDate" content="2023-06-15">
  <meta itemprop="filingDate" content="2022-01-20">
  <meta itemprop="assignee" content="Nexo Systems Inc.">
  <meta itemprop="inventor" content="John Smith">
  <meta itemprop="inventor" content="Jane Doe">
  <title>Automated Commerce Operations System - Google Patents</title>
</head>
<body>
  <h1>Automated Commerce Operations System and Method</h1>

  <section id="abstract-section" itemprop="abstract">
    <div itemprop="content">
      A system for automated commerce operations comprising a kernel that processes Thing objects through configurable state machines. Each Thing has orthogonal state dimensions representing commercial, compliance, and logistics status. The kernel executes governed actions when preconditions are met, records decisions in an append-only ledger, and emits CloudEvents for downstream consumers.
    </div>
  </section>

  <section id="claims-section" itemprop="claims">
    <div itemprop="content">
      1. A commerce operations system comprising: a processor; a memory storing state machines defining transitions for a plurality of Thing types; a rules engine evaluating action preconditions against current state; and a ledger recording each action decision with an evidence pointer.
      2. The system of claim 1 wherein the state machines define orthogonal dimensions including commercial status, compliance status, and logistics status.
      3. The system of claim 1 wherein the rules engine supports AND and OR precondition blocks.
      4. The method of claim 1 further comprising a conformance checker that validates state transitions against the state machine after each action.
      5. The system of claim 1 further comprising a decay engine that marks Things as stale after a configurable freshness SLA.
    </div>
  </section>

  <section id="description-section" itemprop="description">
    <div itemprop="content">
      The present invention relates to commerce operations and more particularly to a kernel that receives Things with state dimensions and executes governed actions through a rules engine. In one embodiment, a CustomerOrder Thing has commercial, compliance, and logistics dimensions each with independent state machines.
    </div>
  </section>

  <section id="background-section" itemprop="background">
    <div itemprop="content">
      Existing commerce systems use monolithic code that mixes business logic with infrastructure concerns, making it difficult to audit or modify individual workflows.
    </div>
  </section>

  <div class="patent-information">
    <dl>
      <dt>Current Assignee:</dt><dd>Nexo Systems Inc.</dd>
      <dt>Inventors:</dt><dd>John Smith; Jane Doe</dd>
    </dl>
  </div>
</body></html>"""


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def patent_html_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Save the HTML fixture to a temporary location."""
    tmp = tmp_path_factory.mktemp("patent_fixture")
    html_file = tmp / f"{PUB}.html"
    html_file.write_text(PATENT_HTML_FIXTURE)
    return html_file


# ── Step 1: Extraction from local fixture ──────────────────────────────


def test_01_extraction():
    """Registry-driven extraction works on realistic Google Patents HTML."""
    cfg = SOURCES["google_patents"]
    ext = PatentExtractor(cfg)
    sel = Selector(text=PATENT_HTML_FIXTURE)

    # Title
    title = ext.extract_title(sel)
    assert title, "Title should be extracted"
    assert "Commerce Operations" in title, f"Expected 'Commerce Operations' in title, got: {title}"
    assert "Google Patents" not in title, "Site suffix should be stripped from title"

    # Sections via registry selectors
    abstract = ext.extract_section(sel, "abstract")
    assert abstract, "Abstract should not be empty"
    assert "state machines" in abstract.lower(), f"Abstract missing expected content: {abstract[:80]}"
    assert "Thing" in abstract, "Abstract should contain ontology term 'Thing'"

    claims = ext.extract_section(sel, "claims")
    assert claims, "Claims should not be empty"
    assert "commerce operations system" in claims.lower(), f"Claims missing expected content: {claims[:80]}"

    description = ext.extract_section(sel, "description")
    assert description, "Description should not be empty"
    assert "kernel" in description.lower(), "Description missing expected content"

    background = ext.extract_section(sel, "background")
    assert background, "Background should not be empty"
    assert "monolithic" in background.lower(), "Background missing expected content"

    # Cross-section integrity: no section should contain another section's heading
    assert "CLAIMS" not in abstract.upper(), "Abstract should not contain CLAIMS"
    assert "DESCRIPTION" not in claims.upper(), "Claims should not contain DESCRIPTION"
    assert "BACKGROUND" not in description.upper(), "Description should not contain BACKGROUND"

    # Metadata extraction via meta tags
    assignee = ext.extract_meta(sel, "assignee")
    assert assignee == "Nexo Systems Inc.", f"Assignee mismatch: {assignee}"

    inventors = ext.extract_meta_list(sel, "inventor")
    assert len(inventors) == 2, f"Expected 2 inventors, got {len(inventors)}"
    assert "John Smith" in inventors
    assert "Jane Doe" in inventors

    pub_date = ext.extract_meta(sel, "publicationDate")
    assert pub_date == "2023-06-15", f"Publication date mismatch: {pub_date}"

    filing_date = ext.extract_meta(sel, "filingDate")
    assert filing_date == "2022-01-20", f"Filing date mismatch: {filing_date}"

    # ExtractionReport is populated
    report = ext.report
    assert len(report.attempts) >= 4, f"Expected >=4 extraction attempts, got {len(report.attempts)}"
    successful = [a for a in report.attempts if a.success]
    assert len(successful) >= 4, f"Expected >=4 successful extractions, got {len(successful)}"
    assert ext.fallback_rate == 0.0, "All registry selectors should match — no fallback needed"


def test_02_fallback_extraction():
    """When HTML structure changes (CSS classes renamed), probe recovers."""
    mutated_html = PATENT_HTML_FIXTURE.replace(
        'itemprop="abstract"', 'data-section="abs"'
    ).replace(
        'itemprop="claims"', 'data-section="clm"'
    ).replace(
        'itemprop="description"', 'data-section="desc"'
    ).replace(
        'itemprop="background"', 'data-section="bg"'
    )

    cfg = SOURCES["google_patents"]
    ext = PatentExtractor(cfg)
    sel = Selector(text=mutated_html)

    abstract = ext.extract_section(sel, "abstract")
    assert abstract, "Abstract should be extracted via probe fallback"
    assert "Thing" in abstract, f"Probe should find abstract content: {abstract[:80]}"

    claims = ext.extract_section(sel, "claims")
    assert claims, "Claims should be extracted via probe fallback"
    assert "orthogonal dimensions" in claims, f"Probe should find claims content: {claims[:80]}"

    # Probe attempts are logged
    report = ext.report
    probe_attempts = [a for a in report.attempts if "[probe]" in a.selector]
    assert len(probe_attempts) >= 2, f"Expected >=2 probe attempts, got {len(probe_attempts)}"
    assert all(a.success for a in probe_attempts), "All probe attempts should succeed"

    # Fallback rate increased
    assert ext.fallback_rate > 0, "Fallback rate should be > 0 after probe activations"


# ── Step 3: ArchitectureCard pipeline ────────────────────────────────


def test_03_architecture_card_roundtrip():
    """Save and validate ArchitectureCard with proper data."""
    card = ArchitectureCard(
        publication_number=PUB,
        title="Automated Commerce Operations System",
        assignee="Nexo Systems Inc.",
        domain="Commerce Operations",
        source_url=f"https://patents.google.com/patent/{PUB}/en",
        problem=Problem(
            business_problem="Commerce systems mix business logic with infrastructure",
            technical_problem="State machines need configurable transitions per domain",
            why_it_matters="Kernel needs orthogonal state dimensions",
        ),
        architecture=Architecture(
            components=["Kernel", "Rules Engine", "Ledger"],
            actors=["Operator", "System"],
            data_stores=["State Store", "Ledger Store"],
            external_systems=["NATS", "PostgreSQL"],
        ),
        enterprise_ontology=EnterpriseOntology(
            entities=["Thing", "Action", "LedgerEntry"],
            events=["action.executed", "thing.created"],
            states=["PENDING", "CONFIRMED", "BLOCKED"],
            workflows=["Order → Approve → Ship → Deliver"],
            rules=["Preconditions must be met before action execution"],
            permissions=["operator can execute actions", "supervisor can approve"],
            audit_traces=["ledger_entry.created for each action"],
        ),
    )
    path = save_architecture_card(card)
    assert Path(path).exists(), "Card file should exist"

    saved = json.loads(Path(path).read_text())
    assert saved["publication_number"] == PUB
    assert saved["title"] == "Automated Commerce Operations System"
    assert saved["assignee"] == "Nexo Systems Inc."
    assert saved["domain"] == "Commerce Operations"
    assert "components" in saved["architecture"]
    assert "entities" in saved["enterprise_ontology"]


# ── Step 4: ClaimsFirewall pipeline ──────────────────────────────────


def test_04_claims_firewall_roundtrip():
    """Save and validate ClaimsFirewall with proper data."""
    fw = ClaimsFirewall(
        publication_number=PUB,
        protected_claims_summary=[
            "Claim 1: Kernel with configurable state machines for commerce objects",
            "Claim 5: Freshness SLA decay engine for stale detection",
        ],
        dangerous_to_copy=[
            "The orthogonal state dimension implementation",
            "The precondition evaluation loop ordering",
        ],
        safe_abstractions=[
            "General concept of state machines for workflow management",
            "Append-only logging for audit trails",
            "Role-based action authorization",
        ],
        design_around_ideas=[
            "Use YAML-based rules engine instead of hardcoded transition logic",
            "Implement evidence collection as separate pipeline instead of inline",
        ],
        original_direction="Nexo uses a generic Thing type with map-based state dimensions instead of typed enums, making the system extensible via configuration rather than code changes",
        risk_level=RiskLevel.MEDIUM,
    )
    path = save_claims_firewall(fw)
    assert Path(path).exists()
    saved = json.loads(Path(path).read_text())
    assert saved["publication_number"] == PUB
    assert len(saved["safe_abstractions"]) >= 3
    assert len(saved["design_around_ideas"]) >= 2
    assert saved["original_direction"].startswith("Nexo uses a generic Thing type")


# ── Step 5: PatternCard pipeline ─────────────────────────────────────


def test_05_pattern_roundtrip():
    """Save and list patterns."""
    pattern = PatternCard(
        name="Configurable State Machine Kernel",
        slug="configurable_sm_kernel",
        domain="Commerce Operations",
        description="A kernel with configurable state machines for commerce object lifecycle management",
        source_patents=[PUB],
        core_entities=["Thing", "Action", "State", "Transition", "LedgerEntry"],
        core_events=["action.executed", "thing.state_changed", "ledger.entry_appended"],
        core_states=["NEGOTIATION", "CONFIRMED", "IN_TRANSIT", "DELIVERED", "CANCELLED"],
        core_workflows=["Quote → Order → Approve → Ship → Deliver → Complete"],
        reusable_principle="State machines should be configurable per Thing type with orthogonal dimensions",
        suggested_module="commerce-kernel",
        risk_level="low",
    )
    save_pattern(pattern)
    all_patterns = list_patterns()
    assert any(p.slug == "configurable_sm_kernel" for p in all_patterns), "Pattern should be saved and listable"


# ── Step 6: Export ───────────────────────────────────────────────────


def test_06_export_generation():
    """Generate research export markdown."""
    md = asyncio.run(generate_research_summary_markdown())
    assert "Patents Processed" in md, f"Export should contain 'Patents Processed', got: {md[:100]}"
    assert PUB in md, f"Export should reference the patent"
    assert "Summary" in md, "Export should have summary header"


# ── Step 7: Artifact verification ────────────────────────────────────


def test_07_artifacts_exist():
    """Verify all pipeline artifacts are persisted."""
    data = _home()
    cards = list(data.glob("cards/*.json"))
    claims = list(data.glob("claims/*.json"))
    patterns = list(data.glob("patterns/*.json"))
    print(f"\nArtifacts: {len(cards)} cards, {len(claims)} firewalls, {len(patterns)} patterns")
    assert len(cards) >= 1
    assert len(claims) >= 1
    assert len(patterns) >= 1


# ── Step 8: Extraction report integrity ──────────────────────────────


def test_08_report_summary():
    """ExtractionReport.summary() produces readable output."""
    cfg = SOURCES["google_patents"]
    ext = PatentExtractor(cfg)
    sel = Selector(text=PATENT_HTML_FIXTURE)

    ext.extract_section(sel, "abstract")
    ext.extract_section(sel, "claims")

    summary = ext.report.summary()
    assert summary.startswith("Extraction report:"), "Summary should start with header"
    assert "abstract:" in summary, "Summary should include section names"
    assert "claims:" in summary, "Summary should include all attempted sections"
    assert "✓" in summary, "Successful attempts should be marked with checkmark"


# ── Step 9: Fallback rate edge case ──────────────────────────────────


def test_09_fallback_rate_edge_cases():
    """Fallback rate handles edge cases correctly."""
    cfg = SOURCES["google_patents"]
    ext = PatentExtractor(cfg)
    assert ext.fallback_rate == 0.0, "Fresh extractor should have 0 fallback rate"

    # Extract from empty HTML — all registry selectors fail, probe finds nothing
    empty_sel = Selector(text="<html></html>")
    result = ext.extract_section(empty_sel, "abstract")
    assert result == "", "Empty HTML should produce empty extraction"
    assert ext.fallback_rate > 0, "Fallback rate should increase after failed extraction"
    assert ext.fallback_rate <= 1.0, "Fallback rate should never exceed 1.0"
