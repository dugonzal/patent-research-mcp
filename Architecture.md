# Architecture

## Data Flow

```
Google Patents → fetch() → raw/
                    ↓
              get_sections() → sections/
                    ↓
              ArchitectureCard → cards/
              ClaimsFirewall   → claims/
              PatternCard      → patterns/
                    ↓
              export() → exports/
```

## Components

- **server.py** — 11 MCP tools + CLI entry point
- **patents.py** — Playwright-based fetcher with rate limiting
- **extractor.py** — CSS selector extraction with probe fallback
- **registry.py** — Declarative selector definitions
- **probe.py** — SelectorProbe with fallback rate tracking
- **schemas.py** — Pydantic models (ArchitectureCard, ClaimsFirewall, PatternCard)
- **store.py** — JSON file storage
- **prompts.py** — LLM prompt templates
- **exporter.py** — Markdown report generator
- **normalizer.py** — Term normalization and synonym mapping
