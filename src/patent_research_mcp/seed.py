"""Seed patent data for Patent Research MCP."""

from __future__ import annotations

from .schemas import SeedPatent

SEED_PATENTS: list[SeedPatent] = [
    SeedPatent(
        publication_number="US20220237532A1",
        title="Digital twin of organizational processes",
        domain="Digital Twin / Process Mining",
        why_it_matters=(
            "Core reference for system object → state → event → action pattern. "
            "Shows how to model organizational processes as living digital twins "
            "with state machines and event-driven orchestration."
        ),
        google_patents_url="https://patents.google.com/patent/US20220237532A1/en",
    ),
    SeedPatent(
        publication_number="US7979296B2",
        title="Universal Worklist Service",
        domain="Workflow / Human Tasks / Inbox",
        why_it_matters=(
            "Shows how to consolidate human tasks from multiple backends into a "
            "single worklist. Direct inspiration for system Exception Console as "
            "a unified human task inbox across commerce operations."
        ),
        google_patents_url="https://patents.google.com/patent/US7979296B2/en",
    ),
    SeedPatent(
        publication_number="US20120150676A1",
        title="Order management system with orchestration plan",
        domain="Order Management / Orchestration",
        why_it_matters=(
            "Shows orchestration plans that coordinate order fulfillment across "
            "multiple systems. Aligns with system commerce graph and state machine "
            "approach for order lifecycle management."
        ),
        google_patents_url="https://patents.google.com/patent/US20120150676A1/en",
    ),
    SeedPatent(
        publication_number="US20150081744A1",
        title="Metadata model repository",
        domain="Metadata / Ontology / Model Repository",
        why_it_matters=(
            "Shows how to store and manage ontology/metadata models. Foundation "
            "for system extensible thing type registry and YAML-driven ontology."
        ),
        google_patents_url="https://patents.google.com/patent/US20150081744A1/en",
    ),
    SeedPatent(
        publication_number="US20140351261A1",
        title="Enterprise data in a knowledge graph",
        domain="Knowledge Graph / Enterprise Data",
        why_it_matters=(
            "Shows how to model enterprise data as a knowledge graph with "
            "entities, relationships, and semantic queries. Aligns with system "
            "Neo4j-driven commerce ontology graph."
        ),
        google_patents_url="https://patents.google.com/patent/US20140351261A1/en",
    ),
    SeedPatent(
        publication_number="US11928630B2",
        title="Issue tracking systems and methods",
        domain="Issue Tracking / Work Management",
        why_it_matters=(
            "Shows modern issue tracking with state machines, transitions, "
            "and multi-dimensional status. Pattern for work items in system "
            "dev and commerce operations pipelines."
        ),
        google_patents_url="https://patents.google.com/patent/US11928630B2/en",
    ),
    SeedPatent(
        publication_number="US11295260B2",
        title="Multi-process workflow designer",
        domain="Workflow Design / BPM",
        why_it_matters=(
            "Shows visual workflow design across multiple processes. "
            "Pattern for system business rules engine and YAML-driven "
            "state machine definitions."
        ),
        google_patents_url="https://patents.google.com/patent/US11295260B2/en",
    ),
    SeedPatent(
        publication_number="US8170901B2",
        title="Extensible framework for designing workflows",
        domain="Workflow Framework / Extensibility",
        why_it_matters=(
            "Shows extensible workflow framework with pluggable activities. "
            "Pattern for system action/effect system and the extensible "
            "rules engine architecture."
        ),
        google_patents_url="https://patents.google.com/patent/US8170901B2/en",
    ),
]


def get_seed_patents() -> list[SeedPatent]:
    """Return the seed patent list."""
    return SEED_PATENTS
