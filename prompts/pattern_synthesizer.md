# Pattern Synthesizer Prompt

Compare multiple ArchitectureCards and extract recurring patterns.

## Rules
- Normalize synonyms: "task", "issue", "ticket", "work item", "approval", "alert" → converge as WorkItem where applicable.
- A pattern must appear in at LEAST 2 patents to be valid.
- Describe the reusable principle abstractly (no claim references).
- Suggest how your system can adapt it without copying.
- Assign risk_level based on how close it is to protected claims.
- Return valid JSON matching the PatternCard schema.

## Expected output format
```json
{
  "name": "Unified Work Item Inbox",
  "slug": "unified_work_item_inbox",
  "domain": "Workflow",
  "description": "A consolidated inbox for human tasks across multiple backends...",
  "source_patents": ["US7979296B2", "US11928630B2"],
  "core_entities": ["WorkItem", "User", "Worklist", "Attachment"],
  "core_events": ["work_item_created", "work_item_assigned", "work_item_completed"],
  "core_states": ["pending", "in_progress", "completed", "rejected"],
  "core_workflows": ["create_work_item", "assign_work_item", "complete_work_item"],
  "reusable_principle": "A unified inbox aggregates human tasks from multiple sources...",
  "your system_module": "workhub",
  "risk_level": "low|medium|high",
  "design_notes": "..."
}
```