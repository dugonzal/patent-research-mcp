"""Markdown export utilities for Nexo Research MCP."""

from __future__ import annotations

from .schemas import ModuleProposal
from .store import (
    list_patterns,
    load_architecture_card,
    load_claims_firewall,
    load_sections,
    save_export,
)


async def generate_research_summary_markdown() -> str:
    """Generate a comprehensive Markdown summary of all research."""
    lines: list[str] = [
        "# Nexo Enterprise OS 360 — Research Summary",
        "",
        f"*Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "---",
        "",
        "## Patents Processed",
        "",
    ]

    # Discover processed patents from stored files
    from .store import _home

    raw_dir = _home() / "raw"
    _home() / "sections"
    _home() / "cards"

    # List all .txt files in raw
    raw_files = sorted(raw_dir.glob("*.txt")) if raw_dir.exists() else []
    for rf in raw_files:
        pub_num = rf.stem
        sections = load_sections(pub_num)
        card = load_architecture_card(pub_num)
        firewall = load_claims_firewall(pub_num)

        title = sections.get("title") if sections else ""
        lines.append(f"### {pub_num}: {title or '(title unknown)'}")
        lines.append("")
        if card:
            lines.append(f"- **Domain:** {card.domain}")
            lines.append(f"- **Assignee:** {card.assignee or 'Unknown'}")
            lines.append(f"- **Nexo Modules:** {', '.join(card.suggested_modules) if card.suggested_modules else '—'}")
        if firewall:
            levels = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            risk_icon = levels.get(firewall.risk_level.value, "⚪")
            lines.append(f"- **Claims Risk:** {risk_icon} {firewall.risk_level.value}")
            lines.append(f"- **Nexo Direction:** {firewall.original_direction}")
        lines.append("")

    # Patterns section
    lines.extend([
        "---",
        "",
        "## Patterns Found",
        "",
    ])
    patterns = list_patterns()
    if patterns:
        for p in patterns:
            levels = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            risk_icon = levels.get(p.risk_level.value, "⚪")
            lines.append(f"### {p.name} {risk_icon}")
            lines.append(f"- **Slug:** `{p.slug}`")
            lines.append(f"- **Domain:** {p.domain}")
            lines.append(f"- **Description:** {p.description}")
            lines.append(f"- **Reusable Principle:** {p.reusable_principle}")
            lines.append(f"- **Nexo Module:** {p.suggested_module}")
            lines.append(f"- **Source Patents:** {', '.join(p.source_patents)}")
            lines.append("")
    else:
        lines.append("*No patterns extracted yet. Use pattern_save after creating ArchitectureCards.*")
        lines.append("")

    # Safe Abstractions section
    lines.extend([
        "---",
        "",
        "## Safe Abstractions (ClaimsFirewall Summary)",
        "",
    ])
    for rf in raw_files:
        pub_num = rf.stem
        firewall = load_claims_firewall(pub_num)
        if firewall and firewall.safe_abstractions:
            lines.append(f"### {pub_num}")
            for sa in firewall.safe_abstractions:
                lines.append(f"- {sa}")
            lines.append("")

    if not any(load_claims_firewall(rf.stem) for rf in raw_files if rf.exists()):
        lines.append("*No ClaimsFirewalls created yet.*")
        lines.append("")

    # Suggested modules section
    lines.extend([
        "---",
        "",
        "## Suggested Nexo Modules",
        "",
    ])
    all_modules: set[str] = set()
    for rf in raw_files:
        card = load_architecture_card(rf.stem)
        if card:
            all_modules.update(card.suggested_modules)
    if all_modules:
        for mod in sorted(all_modules):
            lines.append(f"- `{mod}`")
    else:
        lines.append("*No modules proposed yet.*")
    lines.append("")

    lines.extend([
        "---",
        "",
        "*End of research summary. Update by running `research_export_markdown` after processing new patents.*",
        "",
    ])

    md = "\n".join(lines)
    save_export("nexo_research_summary.md", md)
    return md


async def generate_module_proposal(module_name: str) -> str:
    """Generate a module proposal template for a Nexo module."""
    patterns = list_patterns()
    relevant_patterns = [p for p in patterns if p.suggested_module == module_name]

    proposal = ModuleProposal(
        module_name=module_name,
        purpose="(Define the purpose of this module)",
        entities=["(List core entities)"],
        states=["(Define state machine states)"],
        events=["(Define events that trigger state transitions)"],
        workflows=["(Describe key workflows)"],
        rules=["(Business rules)"],
        permissions=["(Access control rules)"],
        integrations=["(External systems)"],
        audit=["(Audit trail entries)"],
        inspired_by=[p.name for p in relevant_patterns],
        output_path=f"exports/{module_name}.module.md",
    )

    lines = [
        f"# Module: {module_name}",
        "",
        "> Proposed for Nexo Enterprise OS 360",
        f"> *Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "---",
        "",
        "## Purpose",
        "",
        proposal.purpose,
        "",
        "---",
        "",
        "## Entities",
        "",
    ]
    for e in proposal.entities:
        lines.append(f"- `{e}`")

    lines.extend([
        "",
        "---",
        "",
        "## State Machine",
        "",
        "| State | Description |",
        "|-------|-------------|",
    ])
    for s in proposal.states:
        lines.append(f"| `{s}` | |")

    lines.extend([
        "",
        "---",
        "",
        "## Events",
        "",
    ])
    for e in proposal.events:
        lines.append(f"- `{e}`")

    lines.extend([
        "",
        "---",
        "",
        "## Workflows",
        "",
    ])
    for w in proposal.workflows:
        lines.append(f"1. **{w}**")

    lines.extend([
        "",
        "---",
        "",
        "## Business Rules",
        "",
    ])
    for r in proposal.rules:
        lines.append(f"- {r}")

    lines.extend([
        "",
        "---",
        "",
        "## Permissions",
        "",
    ])
    for p in proposal.permissions:
        lines.append(f"- {p}")

    lines.extend([
        "",
        "---",
        "",
        "## Integrations",
        "",
    ])
    for i in proposal.integrations:
        lines.append(f"- {i}")

    lines.extend([
        "",
        "---",
        "",
        "## Audit Trail",
        "",
    ])
    for a in proposal.audit:
        lines.append(f"- {a}")

    lines.extend([
        "",
        "---",
        "",
        "## Inspiration from Patents",
        "",
    ])
    if proposal.inspired_by:
        for name in proposal.inspired_by:
            lines.append(f"- *{name}* — See pattern card for safe abstractions.")
    else:
        lines.append("*No specific patent inspiration yet.*")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*This is a template. Fill in details based on research findings.*")

    md = "\n".join(lines)
    filename = f"{module_name}.module.md"
    save_export(filename, md)
    return md
