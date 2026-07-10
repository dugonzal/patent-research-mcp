"""Canonical LLM prompts for the patent research pipeline.

Each prompt is a typed constant — importable, inspectable, versioned.
Transforms patents into Nexo OS engineering primitives (Thing, State,
Action, Ledger, Evidence). NOT creative reinterpretation.
"""

from __future__ import annotations

# ── Pipeline ──────────────────────────────────────────────────────────
# Raw Patent
#   │
#   ▼
# Prompt 1: PatentExtractor → ArchitectureCard (entities, states, actions, rules)
#   │
#   ▼
# Prompt 2: ClaimsFirewall → safe_abstractions + design_around + original_direction
#   │
#   ▼
# Prompt 3: ArchitectureSynthesizer → Deep Patterns + Module Proposals

EXTRACTOR_PROMPT = """\
Role: Systems Archeologist / Nexo Architect
Input: Raw Patent Text (Description, Summary, Figures description)
Task: Decompose the technical disclosure into a Nexo-native ArchitectureCard.
Ignore legal jargon; focus on the underlying state machine and data flow.

Extraction Requirements:
1. Things with State: Identify all physical or digital entities. Define their
   internal state variables (e.g., Status: [Locked, Transit, Received]).
2. Action Registry: Map every process step as an Action. Define:
   - Preconditions: State requirements or cryptographic triggers needed.
   - Effects: The exact state delta after execution.
   - Roles: The authorized actor (System, User, Device).
3. Ledger Requirements: Identify which transitions require non-repudiation
   or sequential integrity.
4. Evidence Requirements: Identify what data constitutes "proof" of an
   action (e.g., sensor telemetry, signatures).

Output Format: ArchitectureCard
- System Topology: High-level graph of Things.
- State Transition Table: [Initial State] -> [Action] -> [Resulting State].
- Rule Engine: Boolean logic governing workflows.
- Audit Scope: List of events destined for the Append-only Ledger.
"""

CLAIMS_FIREWALL_PROMPT = """\
Role: Patent Engineer / Defensive Architect
Input: ArchitectureCard from PatentExtractor + Full "Claims" section.
Task: Isolate the "Protected Method" from the "Functional Goal." Define the
boundary for a non-infringing Nexo implementation.

Execution Steps:
1. Claim Mapping: For each Independent Claim, map its elements to the
   specific Actions/Things in the ArchitectureCard.
2. Constraint Isolation: Identify the specific "How" that is patented
   (e.g., "calculating X using algorithm Y").
3. Nexo Design-Around: Propose an alternative implementation using Nexo
   primitives that achieves the same "Functional Goal" but breaks the claim
   chain.
   Example: If the claim requires a "Central Database," pivot to
   "Distributed Ledger with Evidence-based validation."
4. Divergence Documentation: Explicitly list which Nexo primitives
   (Evidence, Roles, Ledger) provide a technical architecture fundamentally
   different from the claimed invention.

Output Format:
- Infringement Risk Matrix: [Claim #] vs [Architecture Component].
- Safe Abstractions: List of functions that are Prior Art or General Logic.
- Nexo Original Direction: Technical specification for a clean-room
  implementation.
"""

SYNTHESIZER_PROMPT = """\
Role: Principal Systems Engineer
Input: Multiple ArchitectureCards from a specific technology sector
(e.g., Supply Chain, IoT Identity).
Task: Perform a cross-reference analysis to find "Deep Patterns" and
synthesize them into reusable Nexo Modules.

Extraction Requirements:
1. Isomorphic Patterns: Identify Actions or State Transitions that appear
   in 80%+ of the analyzed patents (e.g., "Handshake Protocol," "Escrow
   Release").
2. Primitive Composition: Define how Nexo Primitives should be wired to
   solve these patterns generically.
3. Module Definition: Propose 2-3 "Nexo Modules" (standardized Action sets
   and Thing schemas) that encapsulate the sector's requirements.
4. Interface Specification: Define the inputs/outputs required for these
   modules to be interoperable within Nexo OS.

Output Format:
- Deep Pattern Report: Common denominators across the patent set.
- Nexo Module Specs:
  - Module Name
  - Standard Things
  - Standard Action Library (Preconditions/Effects)
  - Validation Logic (Evidence types required).
- Implementation Roadmap: Priority list for primitive deployment.
"""

ALL_PROMPTS: dict[str, str] = {
    "extractor": EXTRACTOR_PROMPT,
    "claims_firewall": CLAIMS_FIREWALL_PROMPT,
    "synthesizer": SYNTHESIZER_PROMPT,
}
