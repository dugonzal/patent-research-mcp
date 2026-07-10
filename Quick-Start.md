# Quick Start

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# For fetching patents (optional):
pip install playwright
playwright install chromium
```

## Verify

```bash
patent-research seeds
patent-research fetch US7979296B2
patent-research sections US7979296B2
patent-research patterns
patent-research export
```

## MCP Server

```bash
python -m patent_research_mcp.server
```
