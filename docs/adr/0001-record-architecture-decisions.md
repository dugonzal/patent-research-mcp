# ADR 0001: Record architecture decisions

**Status:** accepted

## Context

We need a lightweight way to capture architectural decisions made during the
development of this project. Without records, future contributors (including our
future selves) won't know why certain choices were made.

## Decision

Use Architecture Decision Records (ADRs) as described by Michael Nygard
(<https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>).

Each ADR is a short Markdown file in `docs/adr/NNNN-title.md` following the
template: Title, Status, Context, Decision, Consequences.

## Consequences

- Decisions are documented as close as possible to when they were made
- New team members can catch up on architectural context quickly
- ADR 0001 serves as the template anchor for all future ADRs
- Requires discipline to write ADRs alongside implementation
