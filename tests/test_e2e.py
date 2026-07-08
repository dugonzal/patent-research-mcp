"""E2E test: complete patent research pipeline.

Tests: fetch → sections → card → firewall → pattern → export → verify.
"""

import asyncio
import json
from pathlib import Path

import pytest

from patent_research_mcp.exporter import generate_research_summary_markdown
from patent_research_mcp.patents import fetch_patent, get_sections
from patent_research_mcp.schemas import (
    Architecture,
    ArchitectureCard,
    ClaimsFirewall,
    EnterpriseOntology,
    PatternCard,
    Problem,
)
from patent_research_mcp.store import (
    list_patterns,
    load_raw_html,
    save_architecture_card,
    save_claims_firewall,
    save_pattern,
)

PUB = "US11928630B2"  # Issue tracking — smaller, faster to fetch


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_01_fetch():
    """Fetch a patent via Playwright."""
    r = await fetch_patent(PUB, pdf=False)
    assert r.status in ("fetched", "already_exists"), f"Fetch failed: {r.status}"
    assert r.publication_number == PUB
    # Verify files exist
    assert load_raw_html(PUB), "HTML not saved"


@pytest.mark.asyncio
async def test_02_sections():
    """Extract sections from fetched patent."""
    sec = await get_sections(PUB)
    assert sec.publication_number == PUB
    assert sec.abstract, "Abstract empty"
    assert sec.claims, "Claims empty"


@pytest.mark.asyncio
async def test_03_architecture_card():
    """Save and validate ArchitectureCard."""
    card = ArchitectureCard(
        publication_number=PUB,
        title="Issue Tracking Systems",
        assignee="Atlassian",
        domain="Issue Tracking",
        source_url=f"https://patents.google.com/patent/{PUB}/en",
        problem=Problem(
            business_problem="State machines need flexibility",
            technical_problem="Configurable transitions per project",
            why_it_matters_for_enterprise_ontology="Exception Console needs state machines",
        ),
        architecture=Architecture(components=["Engine"], actors=["User"]),
        enterprise_ontology=EnterpriseOntology(
            entities=["Issue", "IssueType"],
            events=["issue_created"],
            states=["open → closed"],
            workflows=["Create → Resolve"],
        ),
    )
    path = save_architecture_card(card)
    assert Path(path).exists(), "Card file not saved"
    data = json.loads(Path(path).read_text())
    assert data["publication_number"] == PUB


@pytest.mark.asyncio
async def test_04_claims_firewall():
    """Save and validate ClaimsFirewall."""
    fw = ClaimsFirewall(
        publication_number=PUB,
        protected_claims_summary=["Claim 1: configurable state engine"],
        dangerous_to_copy=["The transition configuration protocol"],
        safe_abstractions=["State machines with transitions"],
        design_around_ideas=["YAML rules engine instead of config protocol"],
        original_direction="Use YAML preconditions for transitions",
        risk_level="low",
    )
    path = save_claims_firewall(fw)
    assert Path(path).exists()


@pytest.mark.asyncio
async def test_05_pattern():
    """Save and list patterns."""
    p = PatternCard(
        name="Configurable Issue State Machine",
        slug="configurable_issue_sm",
        domain="Issue Tracking",
        description="Issues have configurable workflows per project",
        source_patents=[PUB],
        core_entities=["Issue", "IssueType", "Transition"],
        core_events=["issue_created", "issue_transitioned"],
        core_states=["open", "in_progress", "resolved", "closed"],
        core_workflows=["Create → Transition → Resolve"],
        reusable_principle="State machines should be configurable per project",
        suggested_module="exception-console",
        risk_level="low",
    )
    path = save_pattern(p)
    assert Path(path).exists()
    saved = list_patterns()
    assert any(p.slug == "configurable_issue_sm" for p in saved)


@pytest.mark.asyncio
async def test_06_export():
    """Generate research export."""
    md = await generate_research_summary_markdown()
    assert "Research Summary" in md or PUB in md


@pytest.mark.asyncio
async def test_07_e2e_cleanup():
    """Verify all artifacts exist."""
    from patent_research_mcp.store import _home

    data = _home()
    cards = list(data.glob("cards/*.json"))
    claims = list(data.glob("claims/*.json"))
    patterns = list(data.glob("patterns/*.json"))
    print(f"\nArtifacts: {len(cards)} cards, {len(claims)} firewalls, {len(patterns)} patterns")
    assert len(cards) >= 1
    assert len(claims) >= 1
    assert len(patterns) >= 1
