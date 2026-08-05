# FT-001 Frontend Views

Status: Implemented and architecture reviewed, Sprint 2 step 12.

## Scope

The React implementation provides the central underlying administration views required by the approved UI specification:

- searchable and pageable underlying list,
- lifecycle, trading venue, and currency filters,
- guided creation with an atomic primary listing,
- underlying detail with identifiers, listings, usages, and audit history,
- editing of underlying master data,
- verify, deactivate, reactivate, and delete actions.

## Architecture

All server access uses the single typed `MarketApiClient` from step 11. Views do not call `fetch`, repositories, or backend endpoints directly. The hidden workspace remains a backend concern. Trading venues and currencies are loaded from the controlled reference-data endpoints and are not duplicated in frontend constants.

The list uses `primary_listing` from the search response. It does not load details per row and therefore introduces no N+1 request pattern. Filters are sent to the backend and never applied to a paginated subset in the browser.

## Routes

- `/` and `/underlyings`: list
- `/underlyings/new`: creation
- `/underlyings/:underlyingId`: detail
- `/underlyings/:underlyingId/edit`: edit

## User states

Each data-backed view provides loading, empty, and error feedback. Form values remain in local state after failed requests. Destructive actions require confirmation. A version conflict is surfaced through the central API error contract; the UI does not retry or overwrite automatically.

## Deliberate boundaries

Listing creation/edit dialogs and richer concurrency resolution controls are not implemented as parallel solutions. The approved views expose existing listings and primary state; dedicated frontend interaction tests follow in step 13. Database integration and end-to-end coverage remain step 14.
