"""Real e2e test: downloads actual patent HTML, extracts, synthesizes.

Tests the full pipeline with LIVE data from Google Patents:
  fetch → extract (registry + probe) → ArchitectureCard → ClaimsFirewall → verify

This test runs against a real patent. It requires:
  - Internet access
  - Playwright browsers (pip install playwright && playwright install chromium)

Run with: pytest tests/test_live.py -v --tb=long
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.patent_research_mcp.extractor import PatentExtractor
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
from src.patent_research_mcp.store import _home, save_architecture_card, save_claims_firewall, save_pattern

# ── Test patents ───────────────────────────────────────────────────────
# Three different domains to verify extraction robustness

TEST_PATENTS = [
    {
        "pub": "US7979296B2",
        "title_contains": "Worklist",
        "domain": "Workflow / BPM",
        "expected_entities": ["WorkItem", "Worklist", "Participant"],
    },
    {
        "pub": "US10740396B2",
        "title_contains": "Knowledge",
        "domain": "Knowledge Graph",
        "expected_entities": ["Entity", "Relationship", "Graph"],
    },
]

# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def patent_htmls() -> dict[str, str]:
    """Download real patent HTMLs via Playwright (one per session)."""
    import asyncio

    from playwright.async_api import async_playwright

    results: dict[str, str] = {}

    async def _fetch(pub: str) -> str:
        """Fetch a single patent HTML."""
        cache = _home() / "raw" / f"{pub}.html"
        if cache.exists():
            data = json.loads(cache.read_text())
            return data.get("html", "")

        url = f"https://patents.google.com/patent/{pub}/en"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot,mp4,webm}", lambda route: route.abort())
            await page.goto(url, wait_until="load", timeout=45000)
            html = await page.content()
            await browser.close()

        # Cache
        _home().joinpath("raw").mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"html": html}))
        return html

    for patent in TEST_PATENTS:
        pub = patent["pub"]
        print(f"\n  Fetching {pub}...")
        html = asyncio.run(_fetch(pub))
        assert html, f"Failed to fetch {pub}"
        assert len(html) > 10000, f"HTML too short for {pub}: {len(html)} bytes"
        results[pub] = html
        print(f"    {len(html):,} bytes ✅")

    return results


# ── Step 1: Real extraction ────────────────────────────────────────────


@pytest.mark.e2e
def test_01_real_extraction(patent_htmls: dict[str, str]):
    """Extract sections from real patent HTML — verify content quality."""
    cfg = SOURCES["google_patents"]

    for patent in TEST_PATENTS:
        pub = patent["pub"]
        html = patent_htmls[pub]
        ext = PatentExtractor(cfg)
        from parsel import Selector

        sel = Selector(text=html)

        # ── Title ──
        title = ext.extract_title(sel)
        assert title, f"[{pub}] Title should not be empty"
        assert patent["title_contains"].lower() in title.lower(), (
            f"[{pub}] Title '{title[:80]}' should contain '{patent['title_contains']}'"
        )
        assert "Google Patents" not in title, f"[{pub}] Title should not include site suffix"
        print(f"\n  [{pub}] Title: {title[:100]}")

        # ── Abstract ──
        abstract = ext.extract_section(sel, "abstract")
        assert abstract, f"[{pub}] Abstract should not be empty"
        assert len(abstract) > 100, f"[{pub}] Abstract too short: {len(abstract)} chars"
        print(f"  [{pub}] Abstract: {len(abstract)} chars — {abstract[:80]}...")

        # ── Claims ──
        claims = ext.extract_section(sel, "claims")
        assert claims, f"[{pub}] Claims should not be empty"
        assert len(claims) > 200, f"[{pub}] Claims too short: {len(claims)} chars"
        # Claims should contain numbered items
        assert re.search(r"\d+\.\s+", claims), f"[{pub}] Claims missing numbered items"
        claim_count = len(re.findall(r"\d+\.\s+", claims))
        print(f"  [{pub}] Claims: {len(claims)} chars, {claim_count} claims")

        # ── Description ──
        description = ext.extract_section(sel, "description")
        assert description, f"[{pub}] Description should not be empty"
        assert len(description) > 500, f"[{pub}] Description too short: {len(description)} chars"
        print(f"  [{pub}] Description: {len(description)} chars")

        # ── Background ──
        background = ext.extract_section(sel, "background")
        if background:
            print(f"  [{pub}] Background: {len(background)} chars (standalone section)")
            # Cross-section: background shouldn't duplicate description
            short_bg = " ".join(background.split()[:20])
            assert short_bg not in description, f"[{pub}] Background text appears verbatim in description"
        else:
            print(f"  [{pub}] Background: not present as separate section (expected — often nested in description)")

        # ── Metadata ──
        assignee = ext.extract_meta(sel, "assignee")
        inventors = ext.extract_meta_list(sel, "inventor")
        pub_date = ext.extract_meta(sel, "publicationDate")
        filing_date = ext.extract_meta(sel, "filingDate")

        print(f"  [{pub}] Assignee: {assignee or '—'}")
        print(f"  [{pub}] Inventors: {', '.join(inventors) if inventors else '—'}")
        print(f"  [{pub}] Pub date: {pub_date or '—'}, Filing: {filing_date or '—'}")

        # ── Cross-section integrity ──
        # Abstract shouldn't leak into claims
        assert abstract[:50] not in claims, f"[{pub}] Abstract text leaked into claims"
        # Claims shouldn't leak into abstract (except maybe a few words)
        if len(claims) > 100:
            claim_start = claims[:50]
            assert claim_start not in abstract, f"[{pub}] Claims text leaked into abstract"

        # ── Fallback rate ──
        if ext.fallback_rate > 0.1:
            print(f"  ⚠️  [{pub}] Fallback rate: {ext.fallback_rate:.0%} — DOM may have changed")
        else:
            print(f"  [{pub}] Fallback rate: {ext.fallback_rate:.0%} ✅ (all registry selectors matched)")

        # ── Report ──
        report = ext.report
        successful = [a for a in report.attempts if a.success]
        print(f"  [{pub}] Extraction: {len(successful)}/{len(report.attempts)} selectors succeeded")

    print("\n✅ All real extractions passed")


# ── Step 2: Real synthesis pipeline ──────────────────────────────────


@pytest.mark.e2e
def test_02_real_synthesis(patent_htmls: dict[str, str]):
    """Generate ArchitectureCards from real extractions, validate coherence."""
    for patent in TEST_PATENTS:
        pub = patent["pub"]
        html = patent_htmls[pub]
        cfg = SOURCES["google_patents"]
        ext = PatentExtractor(cfg)
        from parsel import Selector

        sel = Selector(text=html)

        # Extract
        title = ext.extract_title(sel)
        abstract = ext.extract_section(sel, "abstract")
        claims = ext.extract_section(sel, "claims")
        assignee = ext.extract_meta(sel, "assignee") or "Unknown"

        # ── ArchitectureCard from extracted data ──
        card = ArchitectureCard(
            publication_number=pub,
            title=title[:200],
            assignee=assignee,
            domain=patent["domain"],
            source_url=f"https://patents.google.com/patent/{pub}/en",
            problem=Problem(
                business_problem=abstract[:500] if abstract else "(unknown)",
                technical_problem=claims[:500] if claims else "(unknown)",
                why_it_matters="Extracted via PatentExtractor from live Google Patents HTML",
            ),
            architecture=Architecture(
                components=infer_components(abstract, claims),
                actors=infer_actors(abstract, claims),
            ),
            enterprise_ontology=EnterpriseOntology(
                entities=patent["expected_entities"],
                states=infer_states(claims),
                events=[],
                workflows=[],
            ),
        )
        path = save_architecture_card(card)
        assert Path(path).exists(), f"[{pub}] Card file not saved"
        saved = json.loads(Path(path).read_text())
        assert saved["publication_number"] == pub
        print(f"\n  [{pub}] ArchitectureCard saved: {Path(path).name}")

        # ── ClaimsFirewall ──
        fw = ClaimsFirewall(
            publication_number=pub,
            protected_claims_summary=[
                f"Claim 1: {claims[:200] if claims else '(unknown)'}",
            ],
            dangerous_to_copy=[
                "Specific implementation details in original claims",
            ],
            safe_abstractions=[
                "General concept of work/item/entity management",
                "State machines for lifecycle management",
                "Role-based access control",
            ],
            design_around_ideas=[
                "Use generic Thing type with map-based state instead of concrete enums",
                "Implement rules as YAML configuration not hardcoded logic",
            ],
            original_direction=f"Nexo OS uses extensible type system with configurable state machines. Patent {pub} provides domain insight for {patent['domain']} patterns.",
            risk_level=RiskLevel.LOW,
        )
        path2 = save_claims_firewall(fw)
        assert Path(path2).exists(), f"[{pub}] ClaimsFirewall not saved"
        print(f"  [{pub}] ClaimsFirewall saved: {Path(path2).name}")


# ── Step 3: Cross-patent pattern synthesis ──────────────────────────


@pytest.mark.e2e
def test_03_cross_pattern_synthesis(patent_htmls: dict[str, str]):
    """Extract common patterns across multiple patents."""
    cfg = SOURCES["google_patents"]
    from parsel import Selector

    all_entities: set[str] = set()
    all_actions: set[str] = set()

    for patent in TEST_PATENTS:
        pub = patent["pub"]
        html = patent_htmls[pub]
        ext = PatentExtractor(cfg)
        sel = Selector(text=html)

        abstract = ext.extract_section(sel, "abstract") or ""
        claims = ext.extract_section(sel, "claims") or ""

        # Extract capitalized terms (potential entities/concepts)
        entities = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", abstract + " " + claims[:1000])
        for e in entities:
            if len(e) > 3 and e not in ("The", "This", "With", "From", "Such", "That", "Each"):
                all_entities.add(e)

        # Extract action-like phrases
        actions = re.findall(
            r"(?:method of|method for|step of|step for)\s+([a-z]+(?:ing|ed|ify|ize)\s+\w+)", claims[:500], re.I
        )
        for a in actions:
            all_actions.add(a.strip()[:60])

    # Save cross-pattern
    if all_entities:
        slug = "cross_patent_patterns"
        pattern = PatternCard(
            name="Cross-Patent Synthesis Pattern",
            slug=slug,
            domain="Cross-Domain",
            description=f"Common entities across {len(TEST_PATENTS)} test patents",
            source_patents=[p["pub"] for p in TEST_PATENTS],
            core_entities=sorted(all_entities)[:10],
            core_events=[],
            core_states=[],
            core_workflows=[],
            reusable_principle="Cross-patent entity extraction reveals shared domain concepts",
            suggested_module="cross-patent-synthesis",
            risk_level=RiskLevel.LOW,
        )
        save_pattern(pattern)
        print(
            f"\n  Cross-pattern entities ({min(len(all_entities), 10)} shown): {', '.join(sorted(all_entities)[:10])}"
        )
        print(f"  Cross-pattern actions: {len(all_actions)} found")

    print("\n✅ All synthesis tests passed")


# ── Step 4: Compare section quality ──────────────────────────────────


@pytest.mark.e2e
def test_04_section_quality(patent_htmls: dict[str, str]):
    """Verify section quality metrics across all patents."""
    cfg = SOURCES["google_patents"]
    from parsel import Selector

    for patent in TEST_PATENTS:
        pub = patent["pub"]
        html = patent_htmls[pub]
        ext = PatentExtractor(cfg)
        sel = Selector(text=html)

        abstract = ext.extract_section(sel, "abstract") or ""
        claims = ext.extract_section(sel, "claims") or ""
        description = ext.extract_section(sel, "description") or ""
        background = ext.extract_section(sel, "background") or ""

        # Quality metrics
        metrics = {
            "abstract_words": len(abstract.split()),
            "claims_words": len(claims.split()),
            "description_words": len(description.split()),
            "has_background": bool(background),
            "claims_count": len(re.findall(r"\d+\.\s+", claims)),
            "abstract_has_period": "." in abstract[-10:] if abstract else False,
            "claims_have_numbers": bool(re.search(r"\d+\.", claims[:50])) if claims else False,
        }

        print(f"\n  [{pub}] Quality metrics:")
        for k, v in metrics.items():
            status = "✅" if v else "❌" if k != "has_background" else ("✅" if v else "ℹ️")
            print(f"    {status} {k}: {v}")

        # Minimum quality thresholds
        assert metrics["abstract_words"] >= 10, f"[{pub}] Abstract too short ({metrics['abstract_words']} words)"
        assert metrics["claims_words"] >= 30, f"[{pub}] Claims too short ({metrics['claims_words']} words)"
        assert metrics["description_words"] >= 50, (
            f"[{pub}] Description too short ({metrics['description_words']} words)"
        )
        assert metrics["claims_count"] >= 1, f"[{pub}] No numbered claims found"
        assert metrics["abstract_has_period"], f"[{pub}] Abstract doesn't end with period (truncated?)"
        assert metrics["claims_have_numbers"], f"[{pub}] Claims don't start with numbers"

    print("\n✅ All quality checks passed")


# ── Helpers ────────────────────────────────────────────────────────────


def infer_components(abstract: str, claims: str) -> list[str]:
    """Infer system components from patent text."""
    text = (abstract + " " + claims)[:2000]
    candidates = ["Engine", "Processor", "Memory", "Interface", "Database", "Network", "Controller"]
    return [c for c in candidates if c.lower() in text.lower()]


def infer_actors(abstract: str, claims: str) -> list[str]:
    """Infer actors from patent text."""
    text = (abstract + " " + claims)[:2000]
    candidates = ["User", "Administrator", "System", "Operator", "Client", "Server"]
    return [c for c in candidates if c.lower() in text.lower()]


def infer_states(claims: str) -> list[str]:
    """Infer state machine states from claims text."""
    states = re.findall(r"\b([A-Z]+_[A-Z]+)\b", claims[:2000])
    return list(set(states))[:5]
