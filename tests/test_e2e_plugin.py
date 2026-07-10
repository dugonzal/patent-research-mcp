"""E2E: exercise all MCP tools through a plugin.

Usage:
    RESEARCH_PLUGIN=/tmp/nexo-research-plugin pytest tests/test_e2e_plugin.py -v -s

Requires Playwright browsers + internet for fetch/extract probes.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

# ── runner ────────────────────────────────────────────────────────────


@dataclass
class Probe:
    name: str
    tool: str
    args: dict | None = None
    expect: str | None = None  # key that must exist in response
    expected_count: int | None = None  # expected array or count length
    checks: list[tuple[str, Callable[[dict], bool]]] = field(default_factory=list)


async def run_tool(session, tool: str, args: dict | None = None) -> dict:
    result = await session.call_tool(tool, args or {})
    return json.loads(result.content[0].text)


async def probe(session, p: Probe) -> None:
    """Run a single probe, raise AssertionError on failure."""
    data = await run_tool(session, p.tool, p.args)
    if p.expect and p.expect not in data:
        raise AssertionError(f"[{p.tool}] missing key '{p.expect}'")
    if p.expected_count is not None:
        val = data.get(p.expect) if p.expect else data
        actual = len(val) if isinstance(val, list) else (val.get("count") if isinstance(val, dict) else -1)
        if actual != p.expected_count:
            raise AssertionError(f"[{p.tool}] count: expected {p.expected_count}, got {actual}")
    for label, fn in p.checks:
        if not fn(data):
            raise AssertionError(f"[{p.tool}] check failed: {label}")


# ── probes ─────────────────────────────────────────────────────────────


async def run_all_probes(session) -> list[Probe]:
    """Build and execute all probes, returning failures."""
    probes: list[Probe] = []

    # 1. Tools
    tools_raw = await session.list_tools()
    tool_names = sorted(t.name for t in tools_raw.tools)
    assert "prompt_get" in tool_names, "prompt_get tool missing"
    assert len(tool_names) == 11, f"expected 11 tools, got {len(tool_names)}"

    # 2. Seeds (plugin-specific count)
    seed_count = 0
    seeds_r = await run_tool(session, "patent_seed_list")
    if isinstance(seeds_r, list):
        seed_count = len(seeds_r)
    probes.append(
        Probe(
            name="seeds",
            tool="patent_seed_list",
            expected_count=seed_count,
            checks=[
                ("no Nexo Twin domain", lambda d: any("Digital Twin" in s.get("domain", "") for s in d)),
            ],
        )
    )

    # 3. Prompts
    probes.append(
        Probe(
            name="prompts",
            tool="prompt_get",
            expect="available",
        )
    )

    # 4. Fetch + extract (e2e — requires Playwright + network)
    probes.append(
        Probe(
            name="fetch",
            tool="patent_fetch",
            args={"publication_number": "US7979296B2"},
            expect="status",
        )
    )
    probes.append(
        Probe(
            name="sections",
            tool="patent_get_sections",
            args={"publication_number": "US7979296B2"},
            expect="title",
        )
    )

    # 5. Save + read
    test_card = {
        "publication_number": "E2E0000001",
        "title": "E2E Probe Card",
        "domain": "Debug",
        "problem": {"business_problem": "N/A", "technical_problem": "N/A"},
        "architecture": {"components": ["X"], "actors": [], "data_stores": []},
        "enterprise_ontology": {
            "entities": ["E"],
            "events": [],
            "states": [],
            "workflows": [],
            "rules": [],
            "permissions": [],
        },
        "patterns": [],
        "suggested_modules": [],
    }
    probes.append(
        Probe(
            name="card_save",
            tool="architecture_card_save",
            args={"card_json": json.dumps(test_card)},
            checks=[("save failed", lambda d: d.get("status") == "saved")],
        )
    )

    test_pattern = {
        "name": "E2E",
        "slug": "e2e",
        "domain": "Debug",
        "description": ".",
        "reusable_principle": ".",
        "source_patents": ["E2E0000001"],
        "core_entities": ["E"],
        "core_events": [],
        "core_workflows": [],
        "risk_level": "low",
        "suggested_module": "e2e",
    }
    probes.append(
        Probe(
            name="pattern_save",
            tool="pattern_save",
            args={"pattern_json": json.dumps(test_pattern)},
            checks=[("save failed", lambda d: d.get("status") == "saved")],
        )
    )
    probes.append(
        Probe(
            name="pattern_list",
            tool="pattern_list",
            checks=[("no patterns", lambda d: isinstance(d, list) and len(d) > 0)],
        )
    )
    probes.append(
        Probe(
            name="export",
            tool="research_export_markdown",
            checks=[("export failed", lambda d: d.get("status") == "exported")],
        )
    )

    # Run all probes sequentially (order matters: fetch → sections)
    for p in probes:
        await probe(session, p)

    return probes


# ── test ───────────────────────────────────────────────────────────────


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_plugin_pipeline() -> None:
    """Connect, run all MCP tool probes, assert no failures."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    plugin = os.environ.get("RESEARCH_PLUGIN") or ""
    params = StdioServerParameters(
        command="python",
        args=["-m", "patent_research_mcp.server"],
        env=dict(os.environ, RESEARCH_PLUGIN=plugin) if plugin else dict(os.environ),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            probes_ran = await run_all_probes(session)
            print(f"\nProbes: {len(probes_ran)} all passed")


# ── standalone ─────────────────────────────────────────────────────────


if __name__ == "__main__":
    asyncio.run(test_plugin_pipeline())
    print("✅")
