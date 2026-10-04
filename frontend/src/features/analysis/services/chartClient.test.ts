import { beforeEach, it, expect, vi } from 'vitest';
import { requestJson } from '../../market/services/http';
import { comparison } from '../../../test/chartFixtures';
import { chartClient } from './chartClient';
import { chartRangeStart } from './chartRanges';
import { chartSetupClient } from './chartSetupClient';
vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
beforeEach(() => {
  chartClient.clear();
  vi.mocked(requestJson).mockResolvedValue(comparison());
});
it('caches identical reads, isolates fields and clears after mutations', async () => {
  const signal = new AbortController().signal;
  await chartClient.series(['reference:a'], '2026-01-01', '2026-02-01', 'CLOSE', signal);
  await chartClient.series(['reference:a'], '2026-01-01', '2026-02-01', 'CLOSE', signal);
  expect(requestJson).toHaveBeenCalledTimes(1);
  expect(requestJson).toHaveBeenLastCalledWith(expect.stringContaining('target=reference%3Aa'), {
    signal,
  });
  await chartClient.series(['reference:a'], null, '2026-02-01', 'ADJUSTED_CLOSE');
  chartClient.clear();
  await chartClient.series(['reference:a'], null, '2026-02-01', 'ADJUSTED_CLOSE');
  expect(requestJson).toHaveBeenCalledTimes(3);
});
it('bounds its cache and never caches failures', async () => {
  for (let index = 0; index < 17; index++)
    await chartClient.series([`listing:${index}`], null, '2026-02-01', 'CLOSE');
  await chartClient.series(['listing:0'], null, '2026-02-01', 'CLOSE');
  expect(requestJson).toHaveBeenCalledTimes(18);
  vi.mocked(requestJson).mockRejectedValueOnce(new Error('unavailable'));
  await expect(chartClient.series(['new'], null, '2026-02-01', 'CLOSE')).rejects.toThrow(
    'unavailable',
  );
  await chartClient.series(['new'], null, '2026-02-01', 'CLOSE');
  expect(requestJson).toHaveBeenCalledTimes(20);
});
it('uses public context and administration endpoints', async () => {
  await chartClient.catalog('2026-02-01');
  await chartClient.underlying('id', '2026-02-01');
  await chartSetupClient.proposals();
  await chartSetupClient.write('sectors', { code: '10' });
  expect(requestJson).toHaveBeenLastCalledWith(
    expect.stringContaining('/top-down-reference-data/sectors'),
    { method: 'POST', body: { code: '10' } },
  );
});
it('clamps months at leap days and year boundaries', () => {
  expect(chartRangeStart('2024-03-31', '1')).toBe('2024-02-29');
  expect(chartRangeStart('2025-03-31', '1')).toBe('2025-02-28');
  expect(chartRangeStart('2026-01-31', '3')).toBe('2025-10-31');
  expect(chartRangeStart('2026-01-31', 'all')).toBeNull();
});
