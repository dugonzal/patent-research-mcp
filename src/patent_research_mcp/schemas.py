"""Pydantic schemas for Patent Research MCP.

ArchitectureCard, ClaimsFirewall, PatternCard, and supporting types
for enterprise architecture research and patent analysis.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level for claims and patterns."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ── ArchitectureCard ──────────────────────────────────────────────────


class Problem(BaseModel):
    """Business and technical problem addressed by a patent."""

    business_problem: str
    technical_problem: str
    why_it_matters_for_enterprise_360: str


class Architecture(BaseModel):
    """Architecture components extracted from a patent."""

    components: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    data_stores: list[str] = Field(default_factory=list)
    external_systems: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)


class Enterprise360(BaseModel):
    """Enterprise OS 360 ontology elements extracted."""

    entities: list[str] = Field(default_factory=list)
    relations: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    human_tasks: list[str] = Field(default_factory=list)
    automated_tasks: list[str] = Field(default_factory=list)
    audit_traces: list[str] = Field(default_factory=list)


class PatternInfo(BaseModel):
    """A reusable pattern extracted from the patent."""

    name: str
    abstract_form: str
    reusable_principle: str
    adaptation: str
    risk_level: RiskLevel


class ArchitectureCard(BaseModel):
    """High-level architecture card for a patent."""

    publication_number: str
    title: str
    assignee: str | None = None
    domain: str
    source_url: str | None = None
    problem: Problem
    architecture: Architecture
    enterprise_360: Enterprise360
    patterns: list[PatternInfo] = Field(default_factory=list)
    suggested_modules: list[str] = Field(default_factory=list)
    notes: str | None = None


# ── ClaimsFirewall ────────────────────────────────────────────────────


class ClaimsFirewall(BaseModel):
    """Firewall analysis of patent claims.

    Separates protectable claims from safe abstractions,
    providing design-around guidance for enterprise architecture research.
    """

    publication_number: str
    protected_claims_summary: list[str] = Field(default_factory=list)
    dangerous_to_copy: list[str] = Field(default_factory=list)
    safe_abstractions: list[str] = Field(default_factory=list)
    design_around_ideas: list[str] = Field(default_factory=list)
    original_direction: str
    risk_level: RiskLevel
    notes: str | None = None


# ── PatternCard ───────────────────────────────────────────────────────


class PatternCard(BaseModel):
    """A reusable architectural pattern synthesized from patents."""

    name: str
    slug: str
    domain: str
    description: str
    source_patents: list[str] = Field(default_factory=list)
    core_entities: list[str] = Field(default_factory=list)
    core_events: list[str] = Field(default_factory=list)
    core_states: list[str] = Field(default_factory=list)
    core_workflows: list[str] = Field(default_factory=list)
    reusable_principle: str
    suggested_module: str
    risk_level: RiskLevel
    design_notes: str = ""


# ── Patent seed metadata ──────────────────────────────────────────────


class SeedPatent(BaseModel):
    """A seed patent for initial research."""

    publication_number: str
    title: str
    domain: str
    why_it_matters: str
    google_patents_url: str


class PatentSections(BaseModel):
    """Extracted sections from a patent document."""

    publication_number: str
    title: str | None = None
    abstract: str | None = None
    background: str | None = None
    summary: str | None = None
    description: str | None = None
    claims: str | None = None
    assignee: str | None = None
    inventors: list[str] = Field(default_factory=list)
    publication_date: str | None = None
    source_url: str | None = None


class FetchResult(BaseModel):
    """Result of a patent fetch operation."""

    publication_number: str
    html_path: str
    text_path: str
    pdf_path: str | None = None
    title: str | None = None
    status: str  # fetched | already_exists | failed
    error: str | None = None


class CompareResult(BaseModel):
    """Result of comparing multiple patterns."""

    shared_concepts: list[str] = Field(default_factory=list)
    common_entities: list[str] = Field(default_factory=list)
    common_events: list[str] = Field(default_factory=list)
    common_workflows: list[str] = Field(default_factory=list)
    suggested_suggested_modules: list[str] = Field(default_factory=list)
    pattern_count: int = 0


class ModuleProposal(BaseModel):
    """A proposed enterprise architecture module."""

    module_name: str
    purpose: str
    entities: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    audit: list[str] = Field(default_factory=list)
    inspired_by: list[str] = Field(default_factory=list)
    output_path: str = ""
