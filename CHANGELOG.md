# Changelog

## 0.1.1 (2026-07-10)

- Refactor: Registry + Extractor + Probe pattern — remove hardcoded selectors
- Fix: NLM-validated rate limiting, fallback monitoring, DOM mutation test
- Test: 9 self-contained e2e tests with local HTML fixtures (no network)
- Test: 4 live e2e tests with real Google Patents download + selector audit
- Test: 7 resilience tests (rate limit, DOM mutation, probe fallback)
- Fix: mypy type errors, async sections tool, schema field validation
- CI: GitHub Actions workflow (ruff + pytest + mypy)
- Style: ruff cleanup — sorted imports, line length 120, consistent formatting
- Docs: static text badges, fix project tree, add .omh/ to .gitignore
- 47 tests total (+13 from 0.1.0)

## 0.1.0 (2026-07-08)

- Initial release as generic MCP server
- Core schemas: ArchitectureCard, ClaimsFirewall, PatternCard
- Google Patents fetch with Playwright
- Structured section extraction
- Claims liability assessment
- Pattern synthesis and comparison
- Plugin system via `RESEARCH_PLUGIN` env var
- Configurable data path via `PATENT_RESEARCH_DATA` env var
- CLI: seeds, fetch, sections, patterns, export
- 10 MCP tools for AI-assisted patent research
- 34 unit tests
- MIT License
