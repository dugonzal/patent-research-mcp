# Plugin System

`patent-research-mcp` supports plugins with custom seeds and prompts.

## Structure

```
plugins/your-plugin/
  plugin.json     # Manifest
  patents.json    # Custom seed patents (optional)
  prompts/        # Custom analysis prompts (optional)
```

## Usage

1. Copy example: `cp -r plugins/example plugins/my-research`
2. Edit plugin.json
3. Set env: `export RESEARCH_PLUGIN=plugins/my-research`
4. Run: `python -m patent_research_mcp.server`

