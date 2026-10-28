import { afterEach, expect, it, vi } from 'vitest';
import type { CurrencyEvidenceRequest } from '../types/currencyEvidence';
import { currencyEvidenceApi } from './currencyEvidence';

afterEach(() => vi.restoreAllMocks());

it('reads the exact product history and sends a reviewed immutable source with its pinned predecessor and original time offsets', async () => {
  const request: CurrencyEvidenceRequest = {
    kind: 'HISTORICAL_LISTINGS',
    source_reference: 'Synthetic historical source, page 4',
    supersedes_evidence_id: 'previous-source',
    revoked: false,
    trade_id: null,
    execution_id: null,
    currency_code: null,
    trading_venue_id: null,
    valid_from: '2026-09-01T00:00:00+02:00',
    valid_to: '2026-11-01T00:00:00+01:00',
    listings: [{ trading_venue_id: 'venue', currency_code: null }],
    complete_listing_set: false,
    request_id: 'stable-request',
    confirmation: 'CONFIRM_SOURCE_REVIEW',
  };
  const fetch = vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify({ history: [] }), { status: 200 }))
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ id: 'new-source', ...request }), { status: 201 }),
    );
  const controller = new AbortController();
  await currencyEvidenceApi.history('product', controller.signal);
  expect(fetch).toHaveBeenCalledOnce();
  expect(fetch.mock.calls[0][0]).toBe(
    'http://localhost:8000/api/v1/warrants/product/currency-evidence',
  );
  expect(fetch.mock.calls[0][1]?.method).toBe('GET');
  expect(fetch.mock.calls[0][1]?.body).toBeUndefined();
  await currencyEvidenceApi.record('product', request, controller.signal);
  expect(fetch.mock.calls[1][1]?.method).toBe('POST');
  expect(fetch.mock.calls[1][1]?.signal).toBe(controller.signal);
  expect(fetch.mock.calls[1][1]?.body).toBe(JSON.stringify(request));
});
