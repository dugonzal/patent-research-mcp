# patent-research-mcp

**Python 3.11+** • **MIT License** • **MCP Server** • **Ruff**

**A generic MCP server for patent research, architecture extraction, claims analysis, and pattern synthesis.**

Fetches patents from Google Patents, extracts structured sections, analyzes architectural patterns, assesses claims risk, and synthesizes reusable design patterns — all through [Model Context Protocol (MCP)](https://modelcontextprotocol.io) tools.

---

## Why

Patent research for system architecture is repetitive and error-prone. This tool automates the pipeline:

```
fetch → extract → analyze → firewall → pattern → export
```

Each step produces structured, reviewable artifacts that feed into architecture decision records (ADRs), not unstructured notes.

---

## Quick Start

```bash
# Install with dev dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verify
patent-research seeds
```

---

## CLI Usage

| Command | Description |
|---------|-------------|
| `patent-research seeds` | List seed patents with metadata |
| `patent-research fetch <number> [--pdf]` | Download patent HTML + plain text |
| `patent-research sections <number>` | Extract structured sections (abstract, claims, description, etc.) |
| `patent-research patterns` | List saved architectural patterns |
| `patent-research export` | Generate complete research summary |

```bash
# Complete workflow
patent-research seeds
patent-research fetch US7979296B2
patent-research sections US7979296B2 --save
patent-research patterns
patent-research export
```

---

## MCP Server

Run as a standard MCP server for use with any MCP client (Claude Desktop, Hermes, etc.):

```bash
python -m patent_research_mcp.server
```

### Tools (10 total)

| Tool | Description |
|------|-------------|
| `patent_seed_list` | List all seed patents with metadata |
| `patent_fetch` | Download patent HTML, plain text, and optional PDF |
| `patent_get_sections` | Extract structured sections from a fetched patent |
| `architecture_card_save` | Save a structured architecture analysis |
| `claims_firewall_save` | Save a claims risk assessment |
| `pattern_save` | Save a reusable architecture pattern |
| `pattern_list` | List all saved patterns |
| `pattern_compare` | Compare patterns across patents for shared concepts |
| `research_export_markdown` | Generate a complete research summary |
| `module_proposal` | Generate a module proposal template |

### Example: Hermes config

```yaml
mcp:
  servers:
    patent-research:
      command: /path/to/.venv/bin/python
      args: [-m, patent_research_mcp.server]
      enabled: true
      env:
        RESEARCH_PLUGIN: /path/to/private-plugin  # optional
```

---

## Data Flow

```
Google Patents
     │
     ▼
  fetch()        ─── raw/ (HTML + TXT + optional PDF)
     │
     ▼
  get_sections() ─── sections/ (structured JSON)
     │
     ▼
  ArchitectureCard  ─── cards/ (architecture analysis)
  ClaimsFirewall    ─── claims/ (risk assessment)
  PatternCard       ─── patterns/ (reusable patterns)
     │
     ▼
  export()        ─── exports/ (research summary)
```

### Artifacts

| Artifact | Schema | Purpose |
|----------|--------|---------|
| **ArchitectureCard** | `ArchitectureCard` | Structured architecture analysis: problem, components, ontology, patterns |
| **ClaimsFirewall** | `ClaimsFirewall` | Risk assessment: dangerous claims, safe abstractions, design-around |
| **PatternCard** | `PatternCard` | Reusable pattern: entities, events, states, reusable principle |

---

## Plugin System

The server supports private plugins via the `RESEARCH_PLUGIN` environment variable. When set, the plugin's `patents.json` overrides the default seed list. This allows domain-specific patent collections without forking the generic core.

```
patent-research-mcp/          # public, generic
└── src/patent_research_mcp/
    └── server.py             # checks $RESEARCH_PLUGIN/patents.json

private-plugin/               # private, domain-specific
└── patents.json              # SeedPatent array
```

Example `patents.json`:

```json
[
  {
    "publication_number": "US20220237532A1",
    "title": "Digital Twin of Organizational Processes",
    "domain": "enterprise-architecture",
    "why_it_matters": "...",
    "google_patents_url": "https://patents.google.com/patent/US20220237532A1/"
  }
]
```

---

## Schemas

| Class | File | Description |
|-------|------|-------------|
| `ArchitectureCard` | `schemas.py` | Full patent architecture analysis |
| `ClaimsFirewall` | `schemas.py` | Claims liability assessment |
| `PatternCard` | `schemas.py` | Reusable architectural pattern |
| `SeedPatent` | `schemas.py` | Seed patent entry |
| `CompareResult` | `schemas.py` | Cross-pattern comparison result |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PATENT_RESEARCH_DATA` | `$CWD/data` | Data storage directory |
| `RESEARCH_PLUGIN` | — | Path to private plugin with custom seeds |

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Lint
ruff check src/
ruff format --check src/

# Type check (optional)
mypy src/
```

### Project Structure

```
patent-research-mcp/
├── src/patent_research_mcp/
│   ├── __init__.py
│   ├── server.py       — MCP server (tools) + CLI
│   ├── schemas.py      — Pydantic models
│   ├── patents.py      — Google Patents fetcher (Playwright)
│   ├── store.py        — JSON file storage
│   ├── normalizer.py   — Text & synonym normalization
│   ├── exporter.py     — Markdown report generation
│   └── seed.py         — Default seed patent data
├── data/               — Patent artifacts (gitignored except examples)
├── tests/              — pytest suite
└── pyproject.toml      — Build config
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
