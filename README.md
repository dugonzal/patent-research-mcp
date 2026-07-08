# Patent Research MCP

An MCP server for patent research and enterprise architecture pattern extraction.

Download patents from Google Patents, extract structured sections, analyze architecture,
identify claims risks, and synthesize reusable patterns — all through MCP tools.

## Quick Start

```bash
# Install
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# List seed patents
patent-research seeds

# Fetch a patent (with optional PDF)
patent-research fetch US7979296B2 --pdf

# Extract sections
patent-research sections US7979296B2

# List saved patterns
patent-research patterns

# Export research summary
patent-research export
```

## MCP Server

```bash
python -m patent_research_mcp.server
```

## Schemas

The tool uses three core schemas for patent analysis:

### PatentAnalysis (ArchitectureCard)
Structured analysis of a patent as enterprise architecture:
- Problem (business + technical)
- Architecture (components, actors, systems, interfaces)
- Entities, events, states, workflows
- Business rules, permissions, human/automated tasks
- Audit traces
- Reusable patterns with risk assessment
- Suggested modules for system architects

### PatentRiskAnalysis (ClaimsFirewall)
Claims liability assessment:
- Protected claims summary
- Dangerous patterns to avoid copying
- Safe abstractions (prior art / well-known patterns)
- Design-around ideas
- Original direction for new implementations

### ArchitecturePattern (PatternCard)
Reusable architectural pattern:
- Core entities, events, states, workflows
- Reusable principle (no claim references)
- Suggested system module mapping
- Risk level and design notes

## CLI Commands

| Command | Description |
|---------|-------------|
| `patent-research seeds` | List 8 seed patents for research |
| `patent-research fetch <num>` | Download patent HTML + TXT (+ PDF with --pdf) |
| `patent-research sections <num>` | Extract structured sections |
| `patent-research patterns` | List saved patterns |
| `patent-research export` | Generate research summary markdown |

## Architecture

```
patent-research-mcp/
├── src/patent_research_mcp/
│   ├── server.py     — MCP server (10 tools) + CLI
│   ├── schemas.py    — Pydantic models
│   ├── patents.py    — Google Patents fetcher
│   ├── store.py      — JSON file storage
│   ├── normalizer.py — Text & synonym normalization
│   ├── exporter.py   — Markdown export
│   └── seed.py       — Seed patent data
├── prompts/          — Analysis prompt templates
├── data/             — Patent data (raw, sections, analysis)
├── tests/
└── pyproject.toml
```

## MCP Tools (10 total)

| Tool | Description |
|------|-------------|
| `patent_seed_list` | List 8 seed patents with metadata |
| `patent_fetch` | Download patent HTML + TXT (+ PDF) |
| `patent_get_sections` | Extract structured sections (abstract, claims, description) |
| `architecture_card_save` | Save structured patent analysis (PatentAnalysis schema) |
| `claims_firewall_save` | Save claims risk assessment (PatentRiskAnalysis schema) |
| `pattern_save` | Save reusable architecture pattern (ArchitecturePattern schema) |
| `pattern_list` | List all saved patterns |
| `pattern_compare` | Compare patterns across patents |
| `research_export_markdown` | Generate research summary |
| `module_proposal` | Generate module proposal template |

## License

MIT
