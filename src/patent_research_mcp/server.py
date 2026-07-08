"""MCP Server for Patent Research.

Exposes tools for patent research, architecture extraction, claims analysis,
pattern synthesis, and module proposal generation.

Start with:
    python -m patent_research_mcp.server

CLI:
    patent-research seeds
    patent-research fetch US7979296B2
    patent-research sections US7979296B2
    patent-research patterns
    patent-research export
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import typer
from mcp.server.fastmcp import FastMCP
from rich.console import Console
from rich.table import Table

from .exporter import generate_module_proposal, generate_research_summary_markdown
from .patents import get_sections as extract_sections, fetch_patent
from .schemas import (
    ArchitectureCard,
    ClaimsFirewall,
    CompareResult,
    PatternCard,
    SeedPatent,
)
from .seed import get_seed_patents as _get_core_seeds
from .store import (
    list_patterns,
    save_architecture_card,
    save_claims_firewall,
    save_pattern,
    save_sections,
)


def get_seed_patents():
    """Load seed patents, checking RESEARCH_PLUGIN env var first."""
    plugin_path = os.environ.get("RESEARCH_PLUGIN")
    if plugin_path:
        pf = Path(plugin_path) / "patents.json"
        if pf.exists():
            try:
                data = json.loads(pf.read_text())
                return [SeedPatent(**s) for s in data]
            except Exception as e:
                print(f"Warning: plugin seeds failed: {e}")
    return _get_core_seeds()

# ── MCP Server ────────────────────────────────────────────────────────

mcp = FastMCP(
    "patent-research-mcp",
    instructions="""Patent research and architecture analysis server.

Tools for the complete patent research pipeline:
  fetch → extract → analyze → assess → synthesize → export

Workflow:
  1. patent_seed_list — browse available seed patents
  2. patent_fetch — download patent from Google Patents
  3. patent_get_sections — extract structured sections
  4. architecture_card_save — save architecture analysis
  5. claims_firewall_save — save claims risk assessment
  6. pattern_save — save reusable pattern
  7. research_export_markdown — generate summary

Designed for system architects and patent researchers.""",
)

console = Console()


# ── Tool: patent_seed_list ─────────────────────────────────────────────


@mcp.tool()
def patent_seed_list() -> str:
    """List all seed patents with metadata.

    Returns a JSON array of seed patents including publication_number,
    title, domain, why_it_matters, and google_patents_url.
    Use this first to discover which patents are available for research.
    """
    seeds = get_seed_patents()
    return json.dumps([s.model_dump() for s in seeds], indent=2, ensure_ascii=False)


# ── Tool: patent_fetch ─────────────────────────────────────────────────


@mcp.tool()
async def patent_fetch(
    publication_number: str | None = None,
    url: str | None = None,
    pdf: bool = False,
) -> str:
    """Download a patent from Google Patents and save raw text.

    Accepts either a publication_number (e.g. 'US7979296B2') or a full URL.
    Saves raw HTML and plain text to the data/raw/ directory.
    When pdf=True, also downloads the PDF version.

    Args:
        publication_number: The patent number (e.g. US7979296B2)
        url: Full Google Patents URL (alternative to publication_number)
        pdf: If True, also download the PDF version
    """
    result = await fetch_patent(publication_number, url, pdf)
    return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)


# ── Tool: patent_get_sections ──────────────────────────────────────────


@mcp.tool()
def patent_get_sections(publication_number: str) -> str:
    """Extract structured sections from a previously fetched patent.

    Reads the saved HTML/text and extracts: title, abstract, background,
    summary, description, claims, assignee, inventors, publication_date.

    Saves the result to data/sections/{pub_num}.sections.json and
    returns the JSON content.

    Args:
        publication_number: The patent number (e.g. US7979296B2)
    """
    sections = extract_sections(publication_number)
    if sections is None:
        return json.dumps(
            {"error": f"Patent {publication_number} not found. Fetch it first with patent_fetch."}
        )
    # Save
    save_sections(publication_number, {k: v for k, v in sections.model_dump().items() if v is not None})
    return json.dumps(sections.model_dump(), indent=2, ensure_ascii=False, default=str)


# ── Tool: architecture_card_save ────────────────────────────────────────


@mcp.tool()
def architecture_card_save(card_json: str) -> str:
    """Save an ArchitectureCard after Hermes extracts it from a patent.

    The ArchitectureCard captures: problem (business + technical),
    architecture components/actors/data_stores, ontology
    (entities, events, states, workflows, rules, permissions), patterns,
    and suggested enterprise architecture modules.

    Args:
        card_json: JSON string conforming to the ArchitectureCard schema.
            Must include at minimum publication_number and title.
    """
    try:
        data = json.loads(card_json)
        card = ArchitectureCard(**data)
        path = save_architecture_card(card)
        return json.dumps(
            {"status": "saved", "publication_number": card.publication_number, "path": path},
            indent=2,
        )
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ── Tool: claims_firewall_save ─────────────────────────────────────────


@mcp.tool()
def claims_firewall_save(firewall_json: str) -> str:
    """Save a ClaimsFirewall analysis for a patent.

    The ClaimsFirewall separates dangerous-to-copy patent claims from
    safe abstractions, provides design-around ideas, and suggests
    system original direction. Always create this BEFORE writing any
    implementation inspired by a patent.

    Args:
        firewall_json: JSON string conforming to the ClaimsFirewall schema.
            Must include publication_number, original_direction, and risk_level.
    """
    try:
        data = json.loads(firewall_json)
        firewall = ClaimsFirewall(**data)
        path = save_claims_firewall(firewall)
        return json.dumps(
            {
                "status": "saved",
                "publication_number": firewall.publication_number,
                "path": path,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ── Tool: pattern_save ──────────────────────────────────────────────────


@mcp.tool()
def pattern_save(pattern_json: str) -> str:
    """Save a reusable architectural pattern synthesized from patents.

    A PatternCard captures a pattern that appears across multiple patents:
    core entities, events, states, workflows, and a reusable principle
    that enterprise architecture can implement without copying claims.

    Args:
        pattern_json: JSON string conforming to the PatternCard schema.
            Must include name, slug, domain, description, and reusable_principle.
    """
    try:
        data = json.loads(pattern_json)
        pattern = PatternCard(**data)
        path = save_pattern(pattern)
        return json.dumps(
            {"status": "saved", "slug": pattern.slug, "name": pattern.name, "path": path},
            indent=2,
        )
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ── Tool: pattern_list ──────────────────────────────────────────────────


@mcp.tool()
def pattern_list() -> str:
    """List all saved architectural patterns.

    Returns a JSON array of PatternCards with name, slug, domain,
    description, and risk level for each saved pattern.
    """
    patterns = list_patterns()
    return json.dumps(
        [
            {
                "name": p.name,
                "slug": p.slug,
                "domain": p.domain,
                "description": p.description,
                "reusable_principle": p.reusable_principle,
                "suggested_module": p.suggested_module,
                "risk_level": p.risk_level.value,
                "source_patents": p.source_patents,
            }
            for p in patterns
        ],
        indent=2,
        ensure_ascii=False,
    )


# ── Tool: pattern_compare ──────────────────────────────────────────────


@mcp.tool()
def pattern_compare(pattern_names: str | None = None) -> str:
    """Compare multiple architectural patterns to find shared concepts.

    Analyzes core_entities, core_events, and core_workflows across
    patterns to find common ground and suggest enterprise architecture modules.

    Args:
        pattern_names: Optional comma-separated list of pattern slugs to compare.
            If omitted, compares all saved patterns.
    """
    all_patterns = list_patterns()
    if not all_patterns:
        return json.dumps({"error": "No patterns saved yet."})

    if pattern_names:
        slugs = [s.strip() for s in pattern_names.split(",")]
        selected = [p for p in all_patterns if p.slug in slugs]
    else:
        selected = all_patterns

    if len(selected) < 1:
        return json.dumps({"error": "No matching patterns found."})

    # Collect entities, events, workflows
    all_entities: list[list[str]] = [p.core_entities for p in selected]
    all_events: list[list[str]] = [p.core_events for p in selected]
    all_workflows: list[list[str]] = [p.core_workflows for p in selected]

    from .normalizer import find_shared_concepts

    result = CompareResult(
        shared_concepts=find_shared_concepts(all_entities + all_events + all_workflows),
        common_entities=find_shared_concepts(all_entities),
        common_events=find_shared_concepts(all_events),
        common_workflows=find_shared_concepts(all_workflows),
        suggested_modules=list(set(p.suggested_module for p in selected)),
        pattern_count=len(selected),
    )

    return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)


# ── Tool: research_export_markdown ──────────────────────────────────────


@mcp.tool()
async def research_export_markdown() -> str:
    """Generate a complete Markdown research summary.

    Reads all stored ArchitectureCards, ClaimsFirewalls, and PatternCards
    and produces a comprehensive export at data/exports/research_summary.md.
    Includes patents processed, patterns found, safe abstractions,
    and suggested enterprise architecture modules.
    """
    md = await generate_research_summary_markdown()
    return json.dumps({"status": "exported", "path": md})


# ── Tool: suggested_module_proposal ─────────────────────────────────────────


@mcp.tool()
async def suggested_module_proposal(module_name: str) -> str:
    """Generate a module proposal template for a enterprise architecture module.

    Creates a Markdown template at data/exports/{module_name}.module.md
    with purpose, entities, state machine, events, workflows, rules,
    permissions, integrations, audit trail, and patent inspiration sections.

    Args:
        module_name: The name of the module (e.g. 'workhub', 'order_orchestrator')
    """
    md = await generate_module_proposal(module_name)
    return json.dumps({"status": "created", "module": module_name, "path": md})


# ── CLI ────────────────────────────────────────────────────────────────

cli_app = typer.Typer(
    name="patent-research",
    help="Patent research and architecture analysis from the command line.",
)


@cli_app.command()
def seeds():
    """List all seed patents."""
    table = Table(title="Seed Patents")
    table.add_column("Number", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Domain", style="yellow")
    table.add_column("Risk", style="red")

    for s in get_seed_patents():
        table.add_row(
            s.publication_number,
            s.title[:60],
            s.domain,
            "research",
        )
    console.print(table)


@cli_app.command()
def fetch(
    pub_num: str = typer.Argument(..., help="Patent publication number (e.g. US7979296B2)"),
    pdf: bool = typer.Option(False, "--pdf", help="Also download PDF version"),
):
    """Fetch a patent from Google Patents."""
    import asyncio

    result = asyncio.run(fetch_patent(publication_number=pub_num, pdf=pdf))
    if result.status == "failed":
        console.print(f"[red]✗[/red] Failed: {result.error}")
    else:
        console.print(f"[green]✓[/green] {result.status}: {pub_num}")
        if result.title:
            console.print(f"  Title: {result.title}")
        if result.pdf_path:
            console.print(f"  PDF:   {result.pdf_path}")


@cli_app.command()
def sections(
    pub_num: str = typer.Argument(..., help="Patent publication number"),
):
    """Extract sections from a fetched patent."""
    result = extract_sections(pub_num)
    if result is None:
        console.print(f"[red]✗[/red] Patent {pub_num} not found. Fetch it first.")
        raise typer.Exit(1)

    # Save
    save_sections(pub_num, {k: v for k, v in result.model_dump().items() if v is not None})
    console.print(f"[green]✓[/green] Sections extracted for {pub_num}")
    console.print(f"  Title: {result.title or '—'}")
    console.print(f"  Assignee: {result.assignee or '—'}")
    console.print(f"  Inventors: {', '.join(result.inventors) if result.inventors else '—'}")
    console.print(f"  Abstract: {(result.abstract or '—')[:120]}...")
    console.print(f"  Claims: {(result.claims or '—')[:120]}...")


@cli_app.command()
def patterns():
    """List all saved architectural patterns."""
    all_patterns = list_patterns()
    if not all_patterns:
        console.print("[yellow]No patterns saved yet.[/yellow]")
        return

    table = Table(title=f"Patterns ({len(all_patterns)})")
    table.add_column("Slug", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Domain", style="yellow")
    table.add_column("Risk", style="red")
    table.add_column("Module", style="blue")

    for p in all_patterns:
        level = p.risk_level.value
        risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(level, "⚪")
        table.add_row(p.slug, p.name[:50], p.domain, f"{risk_icon} {level}", p.suggested_module)
    console.print(table)


@cli_app.command()
def export():
    """Generate the research summary Markdown."""
    import asyncio

    md = asyncio.run(generate_research_summary_markdown())
    console.print("[green]✓[/green] Research summary exported")
    console.print(f"  Path: {md}")


# ── Entry points ───────────────────────────────────────────────────────


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["seeds", "fetch", "sections", "patterns", "export"]:
        cli_app()
    else:
        main()
