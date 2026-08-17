# ADR-S9-002 – Trade Origin and Consumer Handoff

## Status
Accepted for Sprint 9 specification after S9-00 review.

## Decision
FT-009 supports two V1 origins: `WORKSPACE_SELECTION` and `EXTERNAL`.

A workspace-origin Trade references the exact historical FT-008 ProductSelection and consumes the existing FT-007/FT-008/FT-004 context without rewriting it.

An external Trade may exist without TradePlanVersion or ProductSelection, but its product must resolve to the existing stable product/reference identity. FT-009 must not create a shadow product identity.

## Consequences
External trade capture remains possible without fabricating planning history. Workspace history remains reproducible.

## User impact
A user can record both tool-guided and externally proposed trades. The tool asks for product identification only when it cannot already derive the product from the workspace context.
