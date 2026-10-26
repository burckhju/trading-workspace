import { beforeEach, describe, expect, it, vi } from 'vitest';
import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import { chartSetupClient } from './chartSetupClient';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
const base = `${environment.apiBaseUrl}/api/v1/top-down-reference-data`;

describe('chartSetupClient existing administrative API contracts', () => {
  beforeEach(() => {
    vi.mocked(requestJson).mockReset();
    vi.mocked(requestJson).mockResolvedValue({ id: 'receipt' });
  });

  it('loads proposals only by an explicitly called abortable read', async () => {
    const signal = new AbortController().signal;
    await chartSetupClient.proposals(signal);
    expect(vi.mocked(requestJson).mock.calls).toEqual([
      [`${base}/sector-proposals`, { method: 'GET', signal }],
    ]);
  });

  it('posts exact assignment identity and evidence without hidden follow-up actions', async () => {
    const body = {
      sector_id: 'sector-target',
      valid_from: '2026-10-26',
      valid_to: null,
      source: 'CHART_SETUP',
      source_reference: 'User proof',
      quality_status: 'GOOD',
    };
    await chartSetupClient.write('underlyings/fixed-underlying/sector-assignments', body);
    expect(vi.mocked(requestJson).mock.calls).toEqual([
      [`${base}/underlyings/fixed-underlying/sector-assignments`, { method: 'POST', body }],
    ]);
  });

  it('keeps direct-index PUT, validation and import on separate explicit owner endpoints', async () => {
    const values = { provider_symbol: 'GSPC', provider_exchange_code: 'INDX' };
    await chartSetupClient.write(
      'market-references/reference-id/provider-mapping/eodhd',
      values,
      'PUT',
    );
    await chartSetupClient.write('market-references/reference-id/provider-mapping/eodhd/validate');
    await chartSetupClient.write('market-references/reference-id/daily-prices/import', {
      start_date: '2026-01-01',
      end_date: '2026-10-26',
    });
    expect(vi.mocked(requestJson).mock.calls).toEqual([
      [
        `${base}/market-references/reference-id/provider-mapping/eodhd`,
        { method: 'PUT', body: values },
      ],
      [
        `${base}/market-references/reference-id/provider-mapping/eodhd/validate`,
        { method: 'POST', body: undefined },
      ],
      [
        `${base}/market-references/reference-id/daily-prices/import`,
        { method: 'POST', body: { start_date: '2026-01-01', end_date: '2026-10-26' } },
      ],
    ]);
  });
});
