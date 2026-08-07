import { beforeEach, describe, expect, it, vi } from 'vitest';

import { analysisApiClient } from './client';
import { requestJson } from '../../market/services/http';

vi.mock('../../market/services/http', () => ({
  requestJson: vi.fn(),
}));

const requestJsonMock = vi.mocked(requestJson);

describe('analysisApiClient', () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
    requestJsonMock.mockResolvedValue({});
  });

  it('builds overview URLs and forwards list requests', async () => {
    const signal = new AbortController().signal;

    await analysisApiClient.list(signal);
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/api/v1/market-analyses'),
      { signal },
    );

    await analysisApiClient.listPage(
      20,
      10,
      {
        underlyingId: 'underlying-1',
        status: 'COMPLETED',
        qualityStatus: 'GOOD',
        analysisTimeFrom: '2026-08-01T00:00',
        analysisTimeTo: '2026-08-07T00:00',
        sortBy: 'latest_analysis_time',
        sortDirection: 'desc',
      },
      signal,
    );

    const [url, options] = requestJsonMock.mock.calls.at(-1) ?? [];
    expect(url).toContain('/page?');
    expect(url).toContain('offset=20');
    expect(url).toContain('limit=10');
    expect(url).toContain('underlying_id=underlying-1');
    expect(url).toContain('status=COMPLETED');
    expect(url).toContain('quality_status=GOOD');
    expect(url).toContain('sort_by=latest_analysis_time');
    expect(url).toContain('sort_direction=desc');
    expect(options).toEqual({ signal });

    expect(
      analysisApiClient.exportUrl({
        underlyingId: 'underlying-1',
        status: 'COMPLETED',
      }),
    ).toContain('/export.csv?underlying_id=underlying-1&status=COMPLETED');
  });

  it('calls analysis lifecycle endpoints with the expected contracts', async () => {
    const signal = new AbortController().signal;

    await analysisApiClient.get('analysis-1', signal);
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/market-analyses/analysis-1'),
      { signal },
    );

    await analysisApiClient.create('underlying-1', 'listing-1');
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/api/v1/market-analyses'),
      {
        method: 'POST',
        body: {
          underlying_id: 'underlying-1',
          listing_id: 'listing-1',
        },
      },
    );

    const runRequest = {
      start_date: '2026-01-01',
      end_date: '2026-08-07',
      parameters: {
        price_field: 'ADJUSTED_CLOSE' as const,
        short_window: 20,
        medium_window: 50,
        long_window: 200,
        momentum_windows: [20, 60, 120],
        volatility_window: 20,
        range_window: 20,
        minimum_required_observations: 200,
        maximum_data_age_days: 7,
        annualization_factor: '252',
        rounding_scale: 6,
      },
    };

    await analysisApiClient.run('analysis-1', runRequest);
    expect(requestJsonMock).toHaveBeenLastCalledWith(expect.stringContaining('/analysis-1/runs'), {
      method: 'POST',
      body: runRequest,
    });

    await analysisApiClient.getRun('analysis-1', 3, signal);
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/analysis-1/runs/3?include_snapshot=false'),
      { signal },
    );

    await analysisApiClient.getSnapshot('analysis-1', 3, 50, 25, signal);
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/analysis-1/runs/3/snapshot?offset=50&limit=25'),
      { signal },
    );

    await analysisApiClient.events('analysis-1', signal);
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/analysis-1/events'),
      { signal },
    );

    await analysisApiClient.verify('analysis-1', 3);
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/analysis-1/runs/3/verify'),
      { method: 'POST' },
    );

    await analysisApiClient.retry('analysis-1', 3, 'retry reason');
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/analysis-1/runs/3/retry'),
      {
        method: 'POST',
        body: { reason: 'retry reason' },
      },
    );

    await analysisApiClient.retry('analysis-1', 3);
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/analysis-1/runs/3/retry'),
      {
        method: 'POST',
        body: { reason: null },
      },
    );

    await analysisApiClient.supersede('analysis-1', 3, 4, 'replaced');
    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/analysis-1/runs/3/supersede'),
      {
        method: 'POST',
        body: {
          replacement_version: 4,
          reason: 'replaced',
        },
      },
    );
  });
});
