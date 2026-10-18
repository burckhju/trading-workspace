import { expect, it, vi } from 'vitest';

import { realizedGrossReport, reportFilters } from '../../../test/realizedGrossFixtures';
import { performanceApiClient } from './client';

it('issues only the qualified GET with explicit filters and preserves exact API decimal strings', async () => {
  const report = realizedGrossReport();
  report.summary.total = '9007199254740993.0000000001';
  const fetchMock = vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValue(new Response(JSON.stringify(report), { status: 200 }));
  const signal = new AbortController().signal;
  const result = await performanceApiClient.realizedGross(reportFilters, signal);
  expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
    'http://localhost:8000/api/v1/performance/realized-gross?from_date=2026-09-01&to_date=2026-09-30&report_currency=EUR&report_timezone=Europe%2FBerlin',
    expect.objectContaining({ method: 'GET', body: undefined, signal }),
  );
  expect(result.summary.total).toBe('9007199254740993.0000000001');
  expect(result.items[1].realized_gross_pnl_delta).toBe('-20.0000000000');
});
