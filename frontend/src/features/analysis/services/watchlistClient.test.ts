import { beforeEach, describe, expect, it, vi } from 'vitest';
import { watchlistFixture } from '../../../test/watchlistFixtures';
import { requestJson } from '../../market/services/http';
import { watchlistClient } from './watchlistClient';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
beforeEach(() => vi.mocked(requestJson).mockResolvedValue(watchlistFixture()));

describe('watchlistClient', () => {
  it('reads membership without invoking activation and forwards the abort signal', async () => {
    const signal = new AbortController().signal;
    expect(await watchlistClient.read(signal)).toEqual(watchlistFixture());
    expect(requestJson).toHaveBeenCalledExactlyOnceWith(
      expect.stringContaining('/api/v1/market-charts/watchlist'),
      { signal },
    );
  });

  it('binds the single activation command and receipt to the reviewed catalog', async () => {
    const model = watchlistFixture();
    await expect(watchlistClient.activate(model.catalog_version)).resolves.toEqual(model);
    expect(requestJson).toHaveBeenCalledWith(expect.stringContaining('/watchlist/activate'), {
      method: 'POST',
      body: { catalog_version: model.catalog_version, confirmed: true },
    });
    vi.mocked(requestJson).mockResolvedValueOnce({ ...model, enabled: false });
    await expect(watchlistClient.activate(model.catalog_version)).rejects.toThrow(
      'bestätigt nicht',
    );
    vi.mocked(requestJson).mockResolvedValueOnce({ ...model, catalog_version: 'other' });
    await expect(watchlistClient.activate(model.catalog_version)).rejects.toThrow(
      'bestätigt nicht',
    );
  });

  it.each([
    null,
    {},
    { ...watchlistFixture(), items: [] },
    { ...watchlistFixture(), scheduler: {} },
  ])('rejects incomplete read envelopes before activation can be offered (%j)', async (value) => {
    vi.mocked(requestJson).mockResolvedValueOnce(value);
    await expect(watchlistClient.read()).rejects.toThrow('unvollständig');
  });

  it('rejects duplicate identities, wrong target ownership and omitted source-time evidence', async () => {
    const model = watchlistFixture();
    vi.mocked(requestJson).mockResolvedValueOnce({
      ...model,
      items: [model.items[0], model.items[0]],
    });
    await expect(watchlistClient.read()).rejects.toThrow('Identitätsdaten');
    vi.mocked(requestJson).mockResolvedValueOnce({
      ...model,
      items: [{ ...model.items[0], target_key: 'listing:foreign' }],
    });
    await expect(watchlistClient.read()).rejects.toThrow('Identitätsdaten');
    vi.mocked(requestJson).mockResolvedValueOnce({
      ...model,
      items: [
        { ...model.items[0], history: { first_date: null, last_date: null, observation_count: 0 } },
      ],
    });
    await expect(watchlistClient.read()).rejects.toThrow('Identitätsdaten');
    vi.mocked(requestJson).mockResolvedValueOnce(watchlistFixture(31, false));
    expect((await watchlistClient.read()).items).toHaveLength(31);
  });

  it('preserves process-local refresh evidence and rejects missing scope, times or a nonboolean provider flag', async () => {
    const model = watchlistFixture(1);
    model.scheduler.provider_enabled = false;
    model.items[0].refresh = {
      status: 'ERROR',
      reason: 'EODHD_REQUEST_FAILED',
      checked_at: null,
      last_success_at: null,
      next_run_at: null,
      scope: 'PROCESS_LOCAL',
    };
    vi.mocked(requestJson).mockResolvedValueOnce(model);
    expect(await watchlistClient.read()).toEqual(model);
    for (const refresh of [
      { ...model.items[0].refresh, scope: 'HISTORICAL' },
      { ...model.items[0].refresh, checked_at: undefined },
    ]) {
      vi.mocked(requestJson).mockResolvedValueOnce({
        ...model,
        items: [{ ...model.items[0], refresh }],
      });
      await expect(watchlistClient.read()).rejects.toThrow('Identitätsdaten');
    }
    vi.mocked(requestJson).mockResolvedValueOnce({
      ...model,
      scheduler: { ...model.scheduler, provider_enabled: 'false' },
    });
    await expect(watchlistClient.read()).rejects.toThrow('unvollständig');
    model.items[0].refresh = null;
    vi.mocked(requestJson).mockResolvedValueOnce(model);
    expect((await watchlistClient.read()).items[0].refresh).toBeNull();
  });
});
