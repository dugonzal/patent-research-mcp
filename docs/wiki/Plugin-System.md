# Plugin System

Customize patent research with private plugins.

## Structure

```
plugins/your-plugin/
  patents.json    # Custom seeds (override defaults)
  prompts/        # Custom .md prompts (merge with core)
```

## Usage

```bash
export RESEARCH_PLUGIN=plugins/your-plugin
python -m patent_research_mcp.server
```

Plugin prompts override core prompts on filename match. Custom filenames are added as extra prompts.

See [[Plugin-Development]] for building a plugin.
