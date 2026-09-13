import { beforeEach, describe, expect, it, vi } from 'vitest';
import { warrantApiClient } from './client';

const productId = '10000000-0000-4000-8000-000000000001';
const venueId = '10000000-0000-4000-8000-000000000002';

beforeEach(() => vi.restoreAllMocks());

describe('symbol-less warrant listing requests', () => {
  it.each(['', '   ', null, undefined])(
    'sends missing symbol %s as null, not an invented identity',
    async (symbol) => {
      const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
        new Response(JSON.stringify({ id: 'listing', symbol: null }), { status: 201 }),
      );
      const result = await warrantApiClient.addListing(productId, {
        trading_venue_id: venueId,
        quotation_currency_code: 'USD',
        ...(symbol === undefined ? {} : { symbol }),
      });
      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, options] = fetchMock.mock.calls[0];
      expect(String(url)).toBe(`http://localhost:8000/api/v1/warrants/${productId}/listings`);
      expect(options?.method).toBe('POST');
      expect(JSON.parse(String(options?.body))).toEqual({
        trading_venue_id: venueId,
        quotation_currency_code: 'USD',
        symbol: null,
      });
      expect(result.symbol).toBeNull();
    },
  );

  it('preserves an explicitly supplied venue symbol and the quotation currency', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 'listing', symbol: 'TESTCALL' }), { status: 201 }),
    );
    await warrantApiClient.addListing(productId, {
      trading_venue_id: venueId,
      quotation_currency_code: 'CHF',
      symbol: ' TESTCALL ',
    });
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      trading_venue_id: venueId,
      quotation_currency_code: 'CHF',
      symbol: 'TESTCALL',
    });
  });
});
