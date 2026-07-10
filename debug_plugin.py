#!/usr/bin/env python3
"""Debug mode: test plugin integration end-to-end with verbose output.

Usage:
    RESEARCH_PLUGIN=/tmp/nexo-research-plugin python3 debug_plugin.py

Shows every MCP call, response, and validation step.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

# ── helpers ────────────────────────────────────────────────────────────

GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def section(title: str) -> None:
    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}")


def step(msg: str) -> None:
    print(f"  {GREEN}▶{RESET} {msg}")


def ok(msg: str, detail: str = "") -> None:
    print(f"    {GREEN}✅{RESET} {msg} {DIM}{detail}{RESET}".rstrip())


def warn(msg: str) -> None:
    print(f"    {YELLOW}⚠️ {RESET} {msg}")


def fail(msg: str) -> None:
    print(f"    {RED}❌{RESET} {msg}")
    errors.append(msg)


def data(label: str, obj) -> None:
    """Pretty-print a data blob."""
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    # Truncate very long strings
    if len(text) > 600:
        text = text[:600] + f"\n{DIM}  ... ({len(text)} chars total){RESET}"
    print(f"    {DIM}{label}:{RESET}\n{text}")


errors: list[str] = []


# ── main ───────────────────────────────────────────────────────────────


async def main() -> None:
    plugin = os.environ.get("RESEARCH_PLUGIN", "/tmp/nexo-research-plugin")
    print(f"{BOLD}Plugin Debug Mode{RESET}")
    print(f"  Plugin path: {CYAN}{plugin}{RESET}")
    print(f"  Python:      {sys.executable}")

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "patent_research_mcp.server"],
        env={**os.environ, "RESEARCH_PLUGIN": plugin},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"  {GREEN}🔌{RESET} MCP session initialized\n")

            # ── 1. List tools ───────────────────────────────────────
            section("1. Tools Available")
            step("Calling list_tools()...")
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            ok(f"{len(names)} tools registered")
            for t_name in names:
                print(f"      • {t_name}")
            assert "prompt_get" in names, "prompt_get tool missing!"
            ok("prompt_get tool present")

            # ── 2. Seeds ──────────────────────────────────────────────
            section("2. Seed Patents (from plugin)")
            step("Calling patent_seed_list()...")
            result = await session.call_tool("patent_seed_list", {})
            seeds = json.loads(result.content[0].text)
            ok(f"{len(seeds)} seeds loaded", f"(expected 12)")
            if len(seeds) != 12:
                fail(f"Expected 12 seeds, got {len(seeds)}")

            domains = {}
            for s in seeds:
                d = s["domain"]
                domains.setdefault(d, 0)
                domains[d] += 1
                print(
                    f"    {DIM}  • {s['publication_number']:18s} "
                    f"→ {s['domain']:40s}{RESET}"
                )
            ok(f"{len(domains)} unique domains")
            assert (
                "Digital Twin / Process Modeling" in domains
            ), "Missing Nexo Twin seed"
            ok("Nexo Digital Twin seed present")

            # ── 3. Prompts ────────────────────────────────────────────
            section("3. Prompt Templates")
            step("Calling prompt_get()...")
            result = await session.call_tool("prompt_get", {})
            plist = json.loads(result.content[0].text)
            ok(
                f"{plist['count']} prompts available",
                f": {plist['available']}",
            )
            if plist["count"] != 3:
                fail(f"Expected 3 prompts, got {plist['count']}")

            step("Verifying each prompt is Nexo-specific...")
            for pname in plist["available"]:
                r = await session.call_tool("prompt_get", {"name": pname})
                pdata = json.loads(r.content[0].text)
                content = pdata["content"]
                preview = content[:120].replace("\n", " ").strip()
                has_nexo = "Nexo" in content
                if has_nexo:
                    ok(f"{pname}", f"{len(content)} chars — Nexo-specific ✅")
                else:
                    warn(f"{pname} — {len(content)} chars, NO Nexo content!")
                    fail(f"{pname} missing Nexo-specific content")
                print(f"    {DIM}  preview: {preview}...{RESET}")

            # ── 4. Fetch + Extract ─────────────────────────────────────
            section("4. Fetch + Extract Pipeline (e2e smoke)")
            step("Fetching US7979296B2 (already cached or live)...")
            try:
                result = await session.call_tool(
                    "patent_fetch",
                    {"publication_number": "US7979296B2"},
                )
                fetch_data = json.loads(result.content[0].text)
                if fetch_data.get("status") == "failed":
                    warn(f"Fetch: {fetch_data.get('error', 'unknown error')}")
                    warn("(Expected if no Playwright browsers or no network)")
                else:
                    ok("Fetch succeeded", f"title: {fetch_data.get('title', '?')[:80]}")
                    step("Extracting sections...")
                    result = await session.call_tool(
                        "patent_get_sections",
                        {"publication_number": "US7979296B2"},
                    )
                    sec_data = json.loads(result.content[0].text)
                    if "error" in sec_data:
                        warn(f"Sections: {sec_data['error']}")
                    else:
                        ok("Sections extracted")
                        for k in ["title", "abstract", "claims", "assignee"]:
                            if sec_data.get(k):
                                val = str(sec_data[k])[:80]
                                print(f"    {DIM}  {k}: {val}{RESET}")
            except Exception as e:
                warn(f"Fetch pipeline failed: {e}")

            # ── 5. Save artifacts ──────────────────────────────────────
            section("5. Artifact Storage (write + read)")
            step("Saving test ArchitectureCard...")
            try:
                card = {
                    "publication_number": "US0000000A0",
                    "title": "Debug Test Patent",
                    "domain": "Debug",
                    "problem": {
                        "business_problem": "N/A",
                        "technical_problem": "N/A",
                    },
                    "architecture": {
                        "components": ["Debug"],
                        "actors": [],
                        "data_stores": [],
                    },
                    "enterprise_ontology": {
                        "entities": ["DebugEntity"],
                        "events": [],
                        "states": [],
                        "workflows": [],
                        "rules": [],
                        "permissions": [],
                    },
                    "patterns": [],
                    "suggested_modules": [],
                }
                result = await session.call_tool(
                    "architecture_card_save",
                    {"card_json": json.dumps(card)},
                )
                save_result = json.loads(result.content[0].text)
                if save_result.get("status") == "saved":
                    ok("ArchitectureCard saved", f"path: {save_result['path']}")
                else:
                    fail(f"Save failed: {save_result}")
            except Exception as e:
                fail(f"Save exception: {e}")

            step("Saving test PatternCard...")
            try:
                pattern = {
                    "name": "Debug Pattern",
                    "slug": "debug-pattern",
                    "domain": "Debug",
                    "description": "Test pattern from debug mode",
                    "reusable_principle": "Debug first",
                    "source_patents": ["US0000000A0"],
                    "core_entities": ["E1"],
                    "core_events": [],
                    "core_workflows": [],
                    "risk_level": "low",
                    "suggested_module": "debug",
                }
                result = await session.call_tool(
                    "pattern_save",
                    {"pattern_json": json.dumps(pattern)},
                )
                pat_result = json.loads(result.content[0].text)
                if pat_result.get("status") == "saved":
                    ok("PatternCard saved", f"slug: {pat_result['slug']}")
                else:
                    fail(f"Pattern save failed: {pat_result}")
            except Exception as e:
                fail(f"Pattern save exception: {e}")

            step("Listing saved patterns...")
            try:
                result = await session.call_tool("pattern_list", {})
                plist_result = json.loads(result.content[0].text)
                ok(f"{len(plist_result)} patterns in store")
            except Exception as e:
                fail(f"Pattern list exception: {e}")

            step("Generating Markdown export...")
            try:
                result = await session.call_tool("research_export_markdown", {})
                export_result = json.loads(result.content[0].text)
                if export_result.get("status") == "exported":
                    ok("Research export generated", f"path: {export_result['path']}")
                else:
                    warn(f"Export result: {export_result}")
            except Exception as e:
                warn(f"Export exception: {e}")

            # ── Summary ──────────────────────────────────────────────
            section("6. Summary")
            if errors:
                print(f"\n  {RED}{BOLD}❌  {len(errors)} FAILURES:{RESET}")
                for e in errors:
                    print(f"    • {e}")
                sys.exit(1)
            else:
                print(f"\n  {GREEN}{BOLD}✅  ALL CHECKS PASSED{RESET}")
                print(f"  {DIM}Plugin: {plugin}{RESET}")
                print(f"  {DIM}Seeds:  {len(seeds)}  |  Domains: {len(domains)}{RESET}")
                print(f"  {DIM}Tools:  {len(names)}  |  Prompts: {plist['count']}{RESET}")


if __name__ == "__main__":
    asyncio.run(main())
