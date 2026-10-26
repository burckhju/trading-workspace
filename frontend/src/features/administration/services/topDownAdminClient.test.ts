import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import { topDownAdminClient } from './topDownAdminClient';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
const mockedRequestJson = vi.mocked(requestJson);
const references = `${environment.apiBaseUrl}/api/v1/top-down-reference-data`;
const marketData = `${environment.apiBaseUrl}/api/v1/market-data`;
const analyses = `${environment.apiBaseUrl}/api/v1/market-analyses`;
const evidence = {
  valid_from: '2026-10-26',
  valid_to: null,
  source: 'MANUAL_ADMIN',
  source_reference: 'Candidate live workflow',
  quality_status: 'GOOD',
};

describe('topDownAdminClient', () => {
  beforeEach(() => {
    mockedRequestJson.mockReset();
    mockedRequestJson.mockResolvedValue({} as never);
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-26T12:00:00Z'));
  });
  afterEach(() => vi.useRealTimers());

  it('reads authoritative resources with abortable GETs and no side-effect endpoint', async () => {
    const signal = new AbortController().signal;
    await topDownAdminClient.references(signal);
    await topDownAdminClient.sectors(signal);
    await topDownAdminClient.mappings(signal);
    await topDownAdminClient.venueReconciliation('mapping-2', signal);
    expect(mockedRequestJson.mock.calls).toEqual([
      [`${references}/market-references`, { method: 'GET', signal }],
      [`${references}/sectors`, { method: 'GET', signal }],
      [`${marketData}/provider-mappings`, { method: 'GET', signal }],
      [`${marketData}/provider-mappings/mapping-2/venue-reconciliation`, { method: 'GET', signal }],
    ]);
  });

  it('preserves candidate origin, date and distinct assignment identities', async () => {
    await topDownAdminClient.assignBenchmark('u1', 'r1');
    await topDownAdminClient.assignSector('u1', 's1');
    await topDownAdminClient.assignSectorReference('s1', 'r2');
    await topDownAdminClient.assignReferenceListing('r2', 'l1');
    expect(mockedRequestJson.mock.calls).toEqual([
      [
        `${references}/underlyings/u1/benchmark-assignments`,
        { method: 'POST', body: { ...evidence, market_reference_id: 'r1', role: 'BROAD_MARKET' } },
      ],
      [
        `${references}/underlyings/u1/sector-assignments`,
        { method: 'POST', body: { ...evidence, sector_id: 's1' } },
      ],
      [
        `${references}/sectors/s1/reference-assignments`,
        {
          method: 'POST',
          body: {
            valid_from: '2026-10-26',
            valid_to: null,
            source: 'MANUAL_ADMIN',
            quality_status: 'GOOD',
            market_reference_id: 'r2',
          },
        },
      ],
      [
        `${references}/market-references/r2/listing-assignments`,
        { method: 'POST', body: { ...evidence, listing_id: 'l1' } },
      ],
    ]);
  });

  it('keeps mapping PUT and exact mapping validation as separate explicit commands', async () => {
    await topDownAdminClient.createMapping('nonprimary-listing', 'SAP', 'XETRA');
    expect(mockedRequestJson.mock.calls).toEqual([
      [
        `${marketData}/provider-mappings`,
        {
          method: 'PUT',
          body: {
            listing_id: 'nonprimary-listing',
            provider: 'EODHD',
            provider_symbol: 'SAP',
            provider_exchange_code: 'XETRA',
            actor_name: 'Trading Workspace User',
          },
        },
      ],
    ]);
    await topDownAdminClient.validateMapping('mapping-2');
    expect(mockedRequestJson).toHaveBeenLastCalledWith(
      `${marketData}/provider-mappings/mapping-2/validate`,
      { method: 'POST', body: { enabled: true, actor_name: 'Trading Workspace User' } },
    );
  });

  it('retains existing activation endpoints without changing assignment ownership', async () => {
    await topDownAdminClient.activateReference('r1');
    await topDownAdminClient.activateSector('s1');
    expect(mockedRequestJson.mock.calls).toEqual([
      [`${references}/market-references/r1/active`, { method: 'PATCH', body: { active: true } }],
      [`${references}/sectors/s1/active`, { method: 'PATCH', body: { active: true } }],
    ]);
  });

  it('imports only the exact listing/mapping and explicitly supplied period', async () => {
    await topDownAdminClient.importHistory('nonprimary-listing', 'm1', '2026-01-01', '2026-08-01');
    expect(mockedRequestJson.mock.calls).toEqual([
      [
        `${marketData}/daily-prices/import`,
        {
          method: 'POST',
          body: {
            listing_id: 'nonprimary-listing',
            mapping_id: 'm1',
            start_date: '2026-01-01',
            end_date: '2026-08-01',
          },
        },
      ],
    ]);
  });

  it('preserves the separate analysis owner and command payload', async () => {
    mockedRequestJson
      .mockResolvedValueOnce({ id: 'a1', underlying_id: 'u1', listing_id: 'l1' } as never)
      .mockResolvedValueOnce({} as never);

    const analysis = await topDownAdminClient.createAnalysis('u1', 'l1');
    await topDownAdminClient.runAnalysis(analysis.id, '2026-01-01', '2026-08-01');

    expect(analysis.id).toBe('a1');
    expect(mockedRequestJson.mock.calls).toEqual([
      [analyses, { method: 'POST', body: { underlying_id: 'u1', listing_id: 'l1' } }],
      [
        `${analyses}/a1/runs`,
        {
          method: 'POST',
          body: { start_date: '2026-01-01', end_date: '2026-08-01', parameters: {} },
        },
      ],
    ]);
  });
});
