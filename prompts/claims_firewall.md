# Claims Firewall Prompt

Analyze the claims of this patent. Separate what is dangerous to copy literally, safe abstractions, design-around ideas, and an original direction for your system.

## Rules
- Be specific: identify concrete claims by number where possible.
- "Dangerous to copy" = claims that are concrete processes, detailed algorithms, or very specific data structures.
- "Safe abstraction" = the high-level idea without concrete implementation.
- "Design around" = how to achieve the same business effect with a different implementation.
- "your system original direction" = how your system can solve the same business problem in a distinct way.
- Return valid JSON matching the ClaimsFirewall schema.

## Expected output format
```json
{
  "publication_number": "US...",
  "protected_claims_summary": ["Claim 1: ...", "Claim 2: ..."],
  "dangerous_to_copy": ["The specific process X...", "Data structure Y..."],
  "safe_abstractions": ["A unified worklist is a safe abstraction"],
  "design_around_ideas": ["Use event sourcing instead of polling...", "YAML-based rules architecture..."],
  "your system_original_direction": "your system will implement...",
  "risk_level": "low|medium|high",
  "notes": "..."
}
```