# Plugin System

`patent-research-mcp` supports plugins with custom seeds and custom prompts.

## Structure

```
plugins/your-plugin/
  patents.json    # Custom seed patents (optional)
  prompts/        # Custom analysis prompts as .md files (optional)
```

## Usage

1. Copy example: `cp -r plugins/example plugins/my-research`
2. Edit plugin.json
3. Set env: `export RESEARCH_PLUGIN=plugins/my-research`
4. Run: `python -m patent_research_mcp.server`

### Custom Prompts

Any `.md` file in the plugin's `prompts/` directory is loaded and merged
into the `ALL_PROMPTS` dictionary. Plugin prompts override core prompts
on name conflict. The content is available via the `prompt_get` MCP tool.

### Example: custom_prompt.md

```
Analyze this patent from {DOMAIN} perspective.

## Instructions
1. Extract components and interactions
2. Identify entities, events, states
3. Describe reusable principles
4. Do NOT copy claims literally
```
