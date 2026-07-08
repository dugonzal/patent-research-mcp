# Patent Extractor Prompt

Analyze this patent as an enterprise systems architect. Extract an ArchitectureCard.

## Rules
- Do NOT copy claims literally.
- Distinguish: problem, components, actors, entities, events, states, workflows, rules, permissions, human tasks, automated tasks, audit, and reusable patterns.
- Normalize synonyms: "task", "issue", "ticket", "work item", "approval", "alert" → converge as WorkItem where applicable.
- Return valid JSON matching the ArchitectureCard schema.

## Expected output format
```json
{
  "publication_number": "US...",
  "title": "...",
  "assignee": "...",
  "domain": "Workflow | Order Management | Knowledge Graph | ...",
  "source_url": "https://patents.google.com/patent/...",
  "problem": {
    "business_problem": "...",
    "technical_problem": "...",
    "why_it_matters_for_enterprise_360": "..."
  },
  "architecture": {
    "components": ["..."],
    "actors": ["..."],
    "data_stores": ["..."],
    "external_systems": ["..."],
    "interfaces": ["..."]
  },
  "enterprise_360": {
    "entities": ["..."],
    "relations": ["..."],
    "events": ["..."],
    "states": ["..."],
    "workflows": ["..."],
    "rules": ["..."],
    "permissions": ["..."],
    "human_tasks": ["..."],
    "automated_tasks": ["..."],
    "audit_traces": ["..."]
  },
  "patterns": [
    {
      "name": "...",
      "abstract_form": "...",
      "reusable_principle": "...",
      "your system_adaptation": "...",
      "risk_level": "low|medium|high"
    }
  ],
  "your system_modules": ["..."],
  "notes": "..."
}
```