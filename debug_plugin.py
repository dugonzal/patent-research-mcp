#!/usr/bin/env python3
"""Diagnostic: exercise all MCP tools through a plugin, report results."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field

# ── terminal ──────────────────────────────────────────────────────────

G, Y, C, R, B, D, X = (
    "\033[92m",
    "\033[93m",
    "\033[96m",
    "\033[91m",
    "\033[1m",
    "\033[2m",
    "\033[0m",
)


def say(tag: str, msg: str | None = None, detail: str = "", nl: bool = True) -> None:
    end = "\n" if nl else ""
    if msg is None:
        print(f"  {tag}", end=end)
    else:
        print(f"  {tag} {msg} {D}{detail}{X}".rstrip(), end=end)


# ── runner ────────────────────────────────────────────────────────────


@dataclass
class Probe:
    name: str
    tool: str
    args: dict | None = None
    expect: str | None = None  # key to check in response
    expected_count: int | None = None  # array length
    checks: list[tuple[str, callable]] = field(default_factory=list)  # (label, fn(data)->bool)


@dataclass
class Result:
    tool: str
    ok: bool
    detail: str


async def run_tool(session, tool: str, args: dict | None = None) -> dict:
    """Call an MCP tool, return parsed JSON."""
    result = await session.call_tool(tool, args or {})
    text = result.content[0].text
    return json.loads(text)


async def probe(session, p: Probe) -> Result:
    """Execute one probe, return result."""
    try:
        data = await run_tool(session, p.tool, p.args)

        # Check expected key exists
        if p.expect and p.expect not in data:
            return Result(p.tool, False, f"missing key '{p.expect}'")

        # Check count
        if p.expected_count is not None:
            val = data.get(p.expect) if p.expect else data
            actual = len(val) if isinstance(val, list) else (val.get("count") if isinstance(val, dict) else -1)
            if actual != p.expected_count:
                return Result(p.tool, False, f"expected {p.expected_count}, got {actual}")

        # Custom checks
        for label, fn in p.checks:
            if not fn(data):
                return Result(p.tool, False, label)

        return Result(p.tool, True, "")

    except Exception as e:
        return Result(p.tool, False, str(e).split("\n")[0])


# ── main ──────────────────────────────────────────────────────────────


async def main() -> None:
    plugin = os.environ.get("RESEARCH_PLUGIN") or "—"
    print(f"{B}patent-research-mcp — plugin probe{X}")
    say(f"plugin:  {C}{plugin}{X}")
    say(f"python:  {sys.executable}")

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "patent_research_mcp.server"],
        env=dict(os.environ, RESEARCH_PLUGIN=plugin) if plugin != "—" else dict(os.environ),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            say(f"connected  {G}✅{X}")

            probes: list[Probe] = []

            # 1. Tools
            tools_raw = await session.list_tools()
            tool_names = sorted(t.name for t in tools_raw.tools)
            say(f"\n{B}tools{X}  {len(tool_names)} registered")
            for tn in tool_names:
                say(f"  • {tn}", nl=False)
                say(f"{G}✓{X}" if tn != "prompt_get" else f"{G}✓ prompt_get present{X}", detail="", nl=True)

            # 2. Seeds
            probes.append(
                Probe(
                    name="seeds",
                    tool="patent_seed_list",
                    expected_count=12,
                    checks=[
                        ("missing Nexo Twin domain", lambda d: any("Digital Twin" in s.get("domain", "") for s in d)),
                    ],
                )
            )

            # 3. Prompts
            prompts_list = await run_tool(session, "prompt_get", {})
            pnames = prompts_list.get("available", [])
            pnames.sort()
            say(f"\n{B}prompts{X}  {len(pnames)} loaded: {C}{', '.join(pnames)}{X}")
            for pn in pnames:
                pd = await run_tool(session, "prompt_get", {"name": pn})
                c = pd.get("content", "")
                if "Nexo" in c:
                    say(f"  • {pn:20s} {D}{len(c)} chars, Nexo ✅{X}")
                else:
                    say(f"  • {pn:20s} {Y}default (no Nexo content){X}")

            probes.append(
                Probe(
                    name="prompts",
                    tool="prompt_get",
                )
            )

            # 4. Fetch + extract
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
                "publication_number": "DBG0000001",
                "title": "Debug Probe Card",
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
                "name": "Dbg",
                "slug": "dbg",
                "domain": "Debug",
                "description": ".",
                "reusable_principle": ".",
                "source_patents": ["DBG0000001"],
                "core_entities": ["E"],
                "core_events": [],
                "core_workflows": [],
                "risk_level": "low",
                "suggested_module": "dbg",
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

            # ── Run probes ──────────────────────────────────────────
            say(f"\n{B}probes{X}")
            results = await asyncio.gather(*(probe(session, p) for p in probes))

            ok_count = 0
            for r in results:
                if r.ok:
                    ok_count += 1
                    say(f"{G}✅{X}  {r.tool:25s}  {D}{r.detail}{X}")
                else:
                    say(f"{R}❌{X}  {r.tool:25s}  {R}{r.detail}{X}")

            # ── Report ──────────────────────────────────────────────
            total = len(probes)
            fail_count = total - ok_count
            color = G if fail_count == 0 else R
            say(f"\n{color}{B}result{X}  {ok_count}/{total} passed")
            if fail_count == 0:
                say(f"{G}✅  everything looks good{X}")
            else:
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
