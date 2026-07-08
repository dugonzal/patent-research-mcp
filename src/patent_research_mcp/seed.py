"""Seed patent data for Patent Research MCP — add your own patents here."""

from __future__ import annotations

from .schemas import SeedPatent

# Seed patent list is empty by default.
# Users can add their own patents or use the CLI to fetch them.


SEED_PATENTS: list[SeedPatent] = [
    # Add seed patents here using SeedPatent(...)
    # See schemas.py for the SeedPatent model
]


def get_seed_patents() -> list[SeedPatent]:
    """Return the seed patent list."""
    return SEED_PATENTS
