"""Text normalization utilities for patent research."""

from __future__ import annotations

import re


def clean_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into single space."""
    return re.sub(r"\s+", " ", text).strip()


def normalize_patent_text(text: str) -> str:
    """Normalize patent text: clean whitespace, remove repeated headers."""
    text = clean_whitespace(text)
    # Remove repeated "Google Patents" references
    text = re.sub(r"Google Patents\s*", "", text)
    return text


def normalize_entity_name(name: str) -> str:
    """Normalize entity names for comparison.

    'WorkItem', 'Work Item', 'work_item' → 'work_item'
    """
    name = name.strip().lower()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9_]", "", name)
    return name


# Known synonym groups: map any variant → canonical key
SYNONYM_MAP: dict[str, str] = {
    # Work items
    "work_item": "work_item",
    "workitem": "work_item",
    "work item": "work_item",
    "task": "work_item",
    "issue": "work_item",
    "ticket": "work_item",
    "approval": "work_item",
    "alert": "work_item",
    "notification": "work_item",
    # Business objects
    "business_object": "business_object",
    "businessobject": "business_object",
    "business object": "business_object",
    "entity": "business_object",
    # Workflow
    "workflow": "workflow",
    "work_flow": "workflow",
    "process": "workflow",
    "business process": "workflow",
    # Rules
    "rule": "rule",
    "business_rule": "rule",
    "business rule": "rule",
    "policy": "rule",
    # Permissions
    "permission": "permission",
    "role": "permission",
    "access_control": "permission",
    "access control": "permission",
    # Audit
    "audit": "audit_trail",
    "audit_trail": "audit_trail",
    "audit trail": "audit_trail",
    "log": "audit_trail",
    "ledger": "audit_trail",
}


def normalize_term(term: str) -> str:
    """Normalize a single term to its canonical form."""
    key = normalize_entity_name(term)
    return SYNONYM_MAP.get(key, key)


def normalize_list(terms: list[str]) -> list[str]:
    """Normalize a list of terms, removing duplicates."""
    seen: set[str] = set()
    result: list[str] = []
    for term in terms:
        canon = normalize_term(term)
        if canon not in seen:
            seen.add(canon)
            result.append(canon)
    return result


def find_shared_concepts(
    lists: list[list[str]],
) -> list[str]:
    """Find concepts that appear across multiple lists (after normalization)."""
    if not lists:
        return []

    normalized: list[list[str]] = [normalize_list(lst) for lst in lists]
    if not normalized:
        return []

    # Start with all items from the first list
    common = set(normalized[0])
    for lst in normalized[1:]:
        common &= set(lst)

    return sorted(common)
