"""Example: Connect to the patent-research-mcp server from Python."""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    """Connect to the MCP server and exercise a few tools."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "patent_research_mcp.server"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # List available tools
            result = await session.list_tools()
            print(f"Tools ({len(result.tools)}):")
            for tool in result.tools:
                print(f"  {tool.name}: {tool.description}")

            # List seed patents
            seeds = await session.call_tool("patent_seed_list", {})
            print(f"\nSeeds ({len(seeds.content)}):")
            for item in seeds.content:
                print(f"  {item.text[:200]}")

            # Export research summary
            export = await session.call_tool("research_export_markdown", {})
            print(f"\nExport: {len(export.content)} items")


if __name__ == "__main__":
    asyncio.run(main())
