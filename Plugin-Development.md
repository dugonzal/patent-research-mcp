# Plugin Development

Build a plugin for domain-specific patent research.

## Step-by-Step

1. Create directory: `mkdir -p plugins/my-research/prompts`
2. Add `patents.json`:

```json
[{
  "publication_number": "US20220237532A1",
  "title": "Digital Twin of Organizational Processes",
  "domain": "Your Domain",
  "why_it_matters": "Notes on relevance",
  "google_patents_url": "https://patents.google.com/patent/US20220237532A1/"
}]
```

3. Add custom prompts (optional): `.md` files in `prompts/`
4. Run: `export RESEARCH_PLUGIN=plugins/my-research`
5. Verify: `patent-research seeds`

Prompt filenames matching core names (`extractor.md`, `claims_firewall.md`, `synthesizer.md`) override the default. Other names are added as extras.
