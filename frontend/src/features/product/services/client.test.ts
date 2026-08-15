import { warrantApiClient } from './client';

const WARRANT_ID = '11111111-1111-4111-8111-111111111111';

function requestInputUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

function requestBodyText(body: BodyInit | null | undefined): string {
  if (typeof body !== 'string') throw new TypeError('Expected JSON string body');
  return body;
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const warrant = {
  id: WARRANT_ID,
  workspace_id: '22222222-2222-4222-8222-222222222222',
  issuer_id: '33333333-3333-4333-8333-333333333333',
  underlying_id: '44444444-4444-4444-8444-444444444444',
  product_family: 'WARRANT',
  display_name: 'Example Call',
  isin: 'DE000ABC1234',
  wkn: 'ABC123',
  lifecycle_status: 'ACTIVE',
  version: 1,
  created_at: '2026-08-15T12:00:00Z',
  updated_at: '2026-08-15T12:00:00Z',
};

describe('warrantApiClient', () => {
  it('calls list, create and lifecycle endpoints', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse([warrant]))
      .mockResolvedValueOnce(jsonResponse(warrant, 201))
      .mockResolvedValueOnce(jsonResponse({ ...warrant, lifecycle_status: 'INACTIVE', version: 2 }))
      .mockResolvedValueOnce(jsonResponse({ ...warrant, version: 3 }));

    await warrantApiClient.list();
    await warrantApiClient.create({
      issuer_id: warrant.issuer_id,
      underlying_id: warrant.underlying_id,
      display_name: warrant.display_name,
      isin: warrant.isin,
      wkn: warrant.wkn,
      option_direction: 'CALL',
      strike: '100',
      maturity_date: '2027-06-18',
      ratio: '0.1',
    });
    await warrantApiClient.deactivate(WARRANT_ID, 1);
    await warrantApiClient.reactivate(WARRANT_ID, 2);

    const calls = vi.mocked(fetch).mock.calls;
    expect(requestInputUrl(calls[0][0])).toBe('http://localhost:8000/api/v1/warrants');
    expect(calls[1][1]?.method).toBe('POST');
    expect(JSON.parse(requestBodyText(calls[2][1]?.body))).toEqual({ version: 1 });
    expect(requestInputUrl(calls[2][0])).toContain(`/${WARRANT_ID}/deactivate`);
    expect(requestInputUrl(calls[3][0])).toContain(`/${WARRANT_ID}/reactivate`);
  });

  it('calls terms and listing endpoints with their request bodies', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ id: 'terms-2' }, 201))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ id: 'listing-1' }, 201));

    await warrantApiClient.terms(WARRANT_ID);
    await warrantApiClient.addTerms(WARRANT_ID, {
      expected_version: 1,
      option_direction: 'PUT',
      strike: '95',
      maturity_date: '2027-06-18',
      ratio: '0.1',
    });
    await warrantApiClient.listings(WARRANT_ID);
    await warrantApiClient.addListing(WARRANT_ID, {
      trading_venue_id: '55555555-5555-4555-8555-555555555555',
      symbol: 'ABC123',
      quotation_currency_code: 'EUR',
    });

    const calls = vi.mocked(fetch).mock.calls;
    expect(requestInputUrl(calls[0][0])).toContain(`/${WARRANT_ID}/terms`);
    expect(calls[1][1]?.method).toBe('POST');
    expect(JSON.parse(requestBodyText(calls[1][1]?.body))).toMatchObject({ expected_version: 1 });
    expect(requestInputUrl(calls[2][0])).toContain(`/${WARRANT_ID}/listings`);
    expect(calls[3][1]?.method).toBe('POST');
    expect(JSON.parse(requestBodyText(calls[3][1]?.body))).toMatchObject({ symbol: 'ABC123' });
  });
});
