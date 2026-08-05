# FT-001 Frontend Tests

Status: Implemented and architecture reviewed, Sprint 2 step 13.

## Scope

The frontend test suite verifies the user-visible FT-001 behavior implemented in step 12 without introducing an additional data-access or state-management layer.

Covered areas:

- underlying list loading and rendering,
- compact primary-listing display,
- controlled trading-venue and currency options,
- server-side query, venue, and currency filters,
- empty search results,
- detail loading with listings, usages, and audit history,
- optimistic-lock version forwarding for status changes,
- confirmation and navigation after physical deletion,
- atomic creation with a primary listing,
- editing of underlying master data with the loaded version,
- route-level application smoke coverage,
- typed API-client request and error contracts.

## Test structure

Component and interaction tests are colocated with the pages:

- `UnderlyingListPage.test.tsx`
- `UnderlyingDetailPage.test.tsx`
- `UnderlyingFormPage.test.tsx`

The tests use React Testing Library and `user-event`. The single `MarketApiClient` is mocked at the feature boundary. No component test calls `fetch` directly and no backend behavior is reimplemented in the browser test suite.

## Architectural assertions

The tests demonstrate that:

- list filters are sent to the backend rather than applied to a paginated subset,
- list rows use the search response's `primary_listing` instead of issuing detail requests,
- reference values are loaded through the controlled read API,
- mutations pass the current aggregate version,
- deletion remains an explicit confirmed operation,
- creation sends underlying and primary-listing data atomically,
- edit mode does not create a parallel listing editor.

## Execution result

The repaired frontend quality run completed successfully:

```text
TypeScript typecheck: passed
ESLint --max-warnings=0: passed
Vitest: 18 passed
Frontend production build: passed
```

The previous registry limitation applied only to the isolated implementation environment. The project was subsequently executed in the target development environment with its npm dependencies available.

## Remaining scope

Browser-level execution is documented in `INTEGRATION_E2E_TESTS.md`. The foundation scenario was updated after the first Compose run because it still asserted the removed Sprint-0 placeholder heading.
