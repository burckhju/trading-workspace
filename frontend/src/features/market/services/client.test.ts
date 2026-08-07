import { marketApiClient } from './client';
import { MarketApiError, MarketTransportError } from './http';

const UNDERLYING_ID = '11111111-1111-4111-8111-111111111111';
const LISTING_ID = '22222222-2222-4222-8222-222222222222';
const VENUE_ID = '00000000-0000-4000-8001-000000000001';

function requestInputUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

function requestBodyText(body: BodyInit | null | undefined): string {
  if (typeof body !== 'string') {
    throw new TypeError('Expected a JSON string request body.');
  }
  return body;
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function summary() {
  return {
    id: UNDERLYING_ID,
    type: 'STOCK',
    name: 'Siemens AG',
    isin: 'DE0007236101',
    wkn: '723610',
    lifecycle_status: 'ACTIVE',
    quality_status: 'COMPLETE',
    version: 1,
    created_at: '2026-08-04T00:00:00Z',
    updated_at: '2026-08-04T00:00:00Z',
  };
}

describe('marketApiClient', () => {
  it('serializes search parameters with the REST contract names', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ items: [summary()], total: 1, offset: 10, limit: 25 }),
    );

    await marketApiClient.searchUnderlyings({
      query: 'SIE',
      lifecycleStatus: 'ACTIVE',
      offset: 10,
      limit: 25,
    });

    const [requestUrl, request] = vi.mocked(fetch).mock.calls[0];
    const url = new URL(requestInputUrl(requestUrl));
    expect(url.pathname).toBe('/api/v1/underlyings');
    expect(Object.fromEntries(url.searchParams)).toEqual({
      q: 'SIE',
      lifecycle_status: 'ACTIVE',
      offset: '10',
      limit: '25',
    });
    expect(request?.method).toBe('GET');
  });

  it('creates an underlying with JSON and optional audit actor headers', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(summary(), 201));
    const payload = {
      name: 'Siemens AG',
      primary_listing: {
        trading_venue_id: VENUE_ID,
        ticker: 'SIE',
        currency_code: 'EUR',
      },
    };

    await marketApiClient.createUnderlying(payload, {
      actorId: 'user-1',
      actorName: 'Test User',
    });

    const [requestUrl, request] = vi.mocked(fetch).mock.calls[0];
    expect(requestInputUrl(requestUrl)).toBe('http://localhost:8000/api/v1/underlyings');
    expect(request?.method).toBe('POST');
    expect(JSON.parse(requestBodyText(request?.body))).toEqual(payload);
    const headers = new Headers(request?.headers);
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(headers.get('X-Actor-ID')).toBe('user-1');
    expect(headers.get('X-Actor-Name')).toBe('Test User');
  });

  it('preserves omitted and explicit null fields in update requests', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(summary()));

    await marketApiClient.updateUnderlying(UNDERLYING_ID, { version: 2, isin: null });

    const [, request] = vi.mocked(fetch).mock.calls[0];
    expect(JSON.parse(requestBodyText(request?.body))).toEqual({ version: 2, isin: null });
  });

  it('calls listing and primary-listing resource paths', async () => {
    const listing = {
      id: LISTING_ID,
      underlying_id: UNDERLYING_ID,
      trading_venue_id: VENUE_ID,
      ticker: 'SIE',
      currency_code: 'EUR',
      lifecycle_status: 'ACTIVE',
      is_primary: true,
      version: 2,
      created_at: '2026-08-04T00:00:00Z',
      updated_at: '2026-08-04T00:00:00Z',
    };
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(listing))
      .mockResolvedValueOnce(jsonResponse(listing));

    await marketApiClient.updateListing(UNDERLYING_ID, LISTING_ID, {
      version: 1,
      ticker: 'SIE1',
    });
    await marketApiClient.setPrimaryListing(UNDERLYING_ID, LISTING_ID, { version: 2 });

    expect(requestInputUrl(vi.mocked(fetch).mock.calls[0][0])).toContain(
      `/underlyings/${UNDERLYING_ID}/listings/${LISTING_ID}`,
    );
    expect(requestInputUrl(vi.mocked(fetch).mock.calls[1][0])).toContain(
      `/underlyings/${UNDERLYING_ID}/primary-listing/${LISTING_ID}`,
    );
  });

  it('sends the delete version as a query parameter and accepts an empty response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }));

    await marketApiClient.deleteUnderlying(UNDERLYING_ID, 3);

    const [requestUrl, request] = vi.mocked(fetch).mock.calls[0];
    const url = new URL(requestInputUrl(requestUrl));
    expect(url.searchParams.get('version')).toBe('3');
    expect(request?.method).toBe('DELETE');
  });

  it('maps the central API error contract to MarketApiError', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse(
        {
          code: 'UNDERLYING_CONCURRENT_MODIFICATION',
          message: 'The underlying was modified concurrently.',
          details: [],
          timestamp: '2026-08-04T00:00:00Z',
        },
        409,
      ),
    );

    const error = await marketApiClient
      .verifyUnderlying(UNDERLYING_ID, { version: 1 })
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(MarketApiError);
    expect(error).toMatchObject({
      status: 409,
      response: { code: 'UNDERLYING_CONCURRENT_MODIFICATION' },
    });
  });

  it('distinguishes network failures from API failures', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'));

    await expect(marketApiClient.listCurrencies()).rejects.toBeInstanceOf(MarketTransportError);
  });

  it('loads controlled reference data from the shared read endpoints', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ items: [] }))
      .mockResolvedValueOnce(jsonResponse({ items: [] }));

    await marketApiClient.listTradingVenues();
    await marketApiClient.listCurrencies();

    expect(
      requestInputUrl(vi.mocked(fetch).mock.calls[0][0]).endsWith(
        '/api/v1/market-reference-data/trading-venues',
      ),
    ).toBe(true);
    expect(
      requestInputUrl(vi.mocked(fetch).mock.calls[1][0]).endsWith(
        '/api/v1/market-reference-data/currencies',
      ),
    ).toBe(true);
  });

  it('calls the remaining underlying, history, usage, status and listing endpoints', async () => {
    const listing = {
      id: LISTING_ID,
      underlying_id: UNDERLYING_ID,
      trading_venue_id: VENUE_ID,
      ticker: 'SIE',
      currency_code: 'EUR',
      lifecycle_status: 'ACTIVE',
      is_primary: false,
      version: 1,
      created_at: '2026-08-04T00:00:00Z',
      updated_at: '2026-08-04T00:00:00Z',
    };
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ ...summary(), primary_listing: null, listings: [] }))
      .mockResolvedValueOnce(jsonResponse({ items: [], total: 0, offset: 5, limit: 10 }))
      .mockResolvedValueOnce(jsonResponse({ items: [] }))
      .mockResolvedValueOnce(jsonResponse(summary()))
      .mockResolvedValueOnce(jsonResponse(summary()))
      .mockResolvedValueOnce(jsonResponse(listing, 201));

    await marketApiClient.getUnderlying(UNDERLYING_ID);
    await marketApiClient.getUnderlyingAuditEvents(UNDERLYING_ID, { offset: 5, limit: 10 });
    await marketApiClient.getUnderlyingUsages(UNDERLYING_ID);
    await marketApiClient.deactivateUnderlying(UNDERLYING_ID, { version: 2 });
    await marketApiClient.reactivateUnderlying(UNDERLYING_ID, { version: 3 });
    await marketApiClient.addListing(UNDERLYING_ID, {
      trading_venue_id: VENUE_ID,
      ticker: 'SIE2',
      currency_code: 'EUR',
      is_primary: false,
    });

    const urls = vi.mocked(fetch).mock.calls.map(([input]) => requestInputUrl(input));
    expect(urls[0]).toContain(`/underlyings/${UNDERLYING_ID}`);
    expect(urls[1]).toContain(`/underlyings/${UNDERLYING_ID}/audit-events`);
    expect(urls[1]).toContain('offset=5');
    expect(urls[1]).toContain('limit=10');
    expect(urls[2]).toContain(`/underlyings/${UNDERLYING_ID}/usages`);
    expect(urls[3]).toContain(`/underlyings/${UNDERLYING_ID}/deactivate`);
    expect(urls[4]).toContain(`/underlyings/${UNDERLYING_ID}/reactivate`);
    expect(urls[5]).toContain(`/underlyings/${UNDERLYING_ID}/listings`);
    expect(vi.mocked(fetch).mock.calls[5][1]?.method).toBe('POST');
  });
});

it('adds the centrally resolved request identity when no feature actor is provided', async () => {
  const { configureRequestIdentityProvider, resetRequestIdentityProvider } = await import(
    '../../../services/identity/requestIdentity'
  );
  configureRequestIdentityProvider(() => ({ actorId: 'central-user', actorName: 'Central User' }));
  vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
    new Response(JSON.stringify({ items: [], total: 0, offset: 0, limit: 25 }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  );

  try {
    await marketApiClient.searchUnderlyings({ offset: 0, limit: 25 });
    const request = vi.mocked(fetch).mock.calls.at(-1);
    const headers = new Headers(request?.[1]?.headers);
    expect(headers.get('X-Actor-ID')).toBe('central-user');
    expect(headers.get('X-Actor-Name')).toBe('Central User');
  } finally {
    resetRequestIdentityProvider();
  }
});
