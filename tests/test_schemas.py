"""Tests for Pydantic schemas."""

import json

import pytest
from pydantic import ValidationError

from patent_research_mcp.schemas import (
    Architecture,
    ArchitectureCard,
    ClaimsFirewall,
    EnterpriseOntology,
    PatternCard,
    PatternInfo,
    Problem,
)


class TestArchitectureCard:
    def test_minimal_valid(self):
        card = ArchitectureCard(
            publication_number="US7979296B2",
            title="Universal Worklist Service",
            domain="Workflow",
            problem=Problem(
                business_problem="Too many inboxes",
                technical_problem="No unified task API",
                why_it_matters_for_enterprise_ontology="Inbox consolidation pattern",
            ),
            architecture=Architecture(),
            enterprise_ontology=EnterpriseOntology(),
        )
        assert card.publication_number == "US7979296B2"

    def test_with_patterns(self):
        card = ArchitectureCard(
            publication_number="US7979296B2",
            title="Test",
            domain="WF",
            problem=Problem(
                business_problem="X",
                technical_problem="Y",
                why_it_matters_for_enterprise_ontology="Z",
            ),
            architecture=Architecture(
                components=["Worklist Engine"],
                actors=["User"],
            ),
            enterprise_ontology=EnterpriseOntology(entities=["WorkItem"]),
            patterns=[
                PatternInfo(
                    name="Unified Inbox",
                    abstract_form="Aggregate tasks from multiple sources",
                    reusable_principle="Single inbox pattern",
                    adaptation="the Exception Console",
                    risk_level="low",
                )
            ],
            suggested_modules=["workhub"],
        )
        assert len(card.patterns) == 1
        assert card.patterns[0].name == "Unified Inbox"

    def test_invalid_empty(self):
        with pytest.raises(ValidationError):
            ArchitectureCard()  # type: ignore[call-arg]

    def test_risk_enum(self):
        for val in ["low", "medium", "high"]:
            pi = PatternInfo(
                name="test",
                abstract_form="test",
                reusable_principle="test",
                adaptation="test",
                risk_level=val,
            )
            assert pi.risk_level.value == val

    def test_invalid_risk(self):
        with pytest.raises(ValidationError):
            PatternInfo(
                name="test",
                abstract_form="test",
                reusable_principle="test",
                adaptation="test",
                risk_level="extreme",
            )


class TestClaimsFirewall:
    def test_minimal_valid(self):
        fw = ClaimsFirewall(
            publication_number="US7979296B2",
            original_direction="Event-driven worklist",
            risk_level="low",
        )
        assert fw.publication_number == "US7979296B2"

    def test_with_data(self):
        fw = ClaimsFirewall(
            publication_number="US7979296B2",
            protected_claims_summary=["Claim 1: Worklist UI"],
            dangerous_to_copy=["The specific polling mechanism"],
            safe_abstractions=["Unified worklist concept"],
            design_around_ideas=["Use webhooks instead of polling"],
            original_direction="the Exception Console with push-based updates",
            risk_level="medium",
            notes="Good prior art reference",
        )
        assert len(fw.dangerous_to_copy) == 1
        assert fw.risk_level.value == "medium"


class TestPatternCard:
    def test_minimal_valid(self):
        p = PatternCard(
            name="Unified Inbox",
            slug="unified_inbox",
            domain="Workflow",
            description="A unified inbox pattern",
            reusable_principle="Aggregate all human tasks into one view",
            suggested_module="workhub",
            risk_level="low",
        )
        assert p.slug == "unified_inbox"

    def test_json_roundtrip(self):
        p = PatternCard(
            name="Test",
            slug="test",
            domain="DM",
            description="Desc",
            source_patents=["US1", "US2"],
            core_entities=["Item", "User"],
            core_events=["created", "assigned"],
            core_states=["open", "closed"],
            core_workflows=["create", "assign"],
            reusable_principle="RP",
            suggested_module="mod",
            risk_level="high",
            design_notes="Notes",
        )
        data = json.loads(p.model_dump_json())
        restored = PatternCard(**data)
        assert restored.slug == p.slug
        assert restored.core_entities == p.core_entities


class TestSeedPatents:
    def test_import(self):
        from patent_research_mcp.seed import get_seed_patents

        seeds = get_seed_patents()
        assert len(seeds) == 0  # No seed patents shipped by default
        for s in seeds:
            assert s.publication_number
            assert s.title
            assert s.domain
            assert s.why_it_matters
            assert "patents.google.com" in s.google_patents_url.lower()
