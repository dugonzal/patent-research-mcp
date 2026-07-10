# Quick Start

## Install
```
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Verify
```
patent-research seeds
patent-research fetch US7979296B2
patent-research sections US7979296B2
patent-research export
```

## MCP Server
```
python -m patent_research_mcp.server
```
