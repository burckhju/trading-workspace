# ADR-S9-006 – Pre-Execution Decision-Support Boundary

## Status
Accepted for Sprint 9 specification after S9-00 review.

## Decision
A PreExecutionCheck is optional decision support before a purchase. It is not a prerequisite for recording an execution that has already happened.

Historic FT-008 ProductSelection/evaluation data is never overwritten with later live data. Missing provider capability or stale live data may block a pre-execution assessment but must not block historical execution capture.

## Consequences
Decision support and historical fact capture remain separate. Provider availability cannot erase the user's ability to document reality.

## User impact
The user may inspect current product conditions before buying, but can always record a purchase that actually occurred even if live-data services are unavailable afterward.
