import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { watchlistFixture, watchlistSeries } from '../../../test/watchlistFixtures';
import { chartClient } from '../services/chartClient';
import { useWatchlistSeries } from './useWatchlistSeries';

vi.mock('../services/chartClient', () => ({
  chartClient: { series: vi.fn(), invalidateTargets: vi.fn() },
}));

beforeEach(() => {
  vi.mocked(chartClient.series).mockImplementation((keys, start, end, field) =>
    Promise.resolve(watchlistSeries(keys[0], start, end, field)),
  );
});

describe('useWatchlistSeries', () => {
  it('loads every one of 31 series with at most four parallel reads and rereads only changed evidence', async () => {
    const data = watchlistFixture(31);
    let active = 0;
    let peak = 0;
    const complete: (() => void)[] = [];
    vi.mocked(chartClient.series).mockImplementation(
      (keys, start, end, field) =>
        new Promise((resolve) => {
          active += 1;
          peak = Math.max(peak, active);
          complete.push(() => {
            active -= 1;
            resolve(watchlistSeries(keys[0], start, end, field));
          });
        }),
    );
    const { result, rerender } = renderHook(
      ({ items }) => useWatchlistSeries(items, '2026-07-04', '2026-10-04', 'CLOSE'),
      { initialProps: { items: data.items } },
    );
    await waitFor(() => expect(chartClient.series).toHaveBeenCalledTimes(4));
    for (let done = 0; done < 31; done += 4) {
      await act(() => {
        complete.splice(0).forEach((finish) => finish());
        return Promise.resolve();
      });
      await waitFor(() => expect(chartClient.series).toHaveBeenCalledTimes(Math.min(31, done + 8)));
    }
    await waitFor(() =>
      expect(
        Object.values(result.current.states).every((state) => state.result && !state.loading),
      ).toBe(true),
    );
    expect(peak).toBe(4);
    rerender({ items: structuredClone(data.items) });
    expect(chartClient.series).toHaveBeenCalledTimes(31);
    const updated = structuredClone(data.items);
    updated[17].history.last_received_at = '2026-11-09T09:00:00Z';
    rerender({ items: updated });
    await waitFor(() => expect(chartClient.series).toHaveBeenCalledTimes(32));
    expect(chartClient.series).toHaveBeenLastCalledWith(
      [updated[17].target_key],
      '2026-07-04',
      '2026-10-04',
      'CLOSE',
      expect.any(AbortSignal),
    );
    await act(() => {
      complete.splice(0).forEach((finish) => finish());
      return Promise.resolve();
    });
  });

  it('hides stale results immediately and drains old requests before a new date generation', async () => {
    const items = watchlistFixture(4).items;
    const complete: (() => void)[] = [];
    const signals: AbortSignal[] = [];
    vi.mocked(chartClient.series).mockImplementation(
      (keys, start, end, field, signal) =>
        new Promise((resolve) => {
          signals.push(signal!);
          complete.push(() => resolve(watchlistSeries(keys[0], start, end, field)));
        }),
    );
    const { result, rerender } = renderHook(
      ({ end }) => useWatchlistSeries(items, '2026-07-04', end, 'CLOSE'),
      { initialProps: { end: '2026-10-04' } },
    );
    await waitFor(() => expect(chartClient.series).toHaveBeenCalledTimes(4));
    rerender({ end: '2026-10-05' });
    expect(signals.every((signal) => signal.aborted)).toBe(true);
    expect(Object.values(result.current.states).every((state) => state.result === null)).toBe(true);
    expect(chartClient.series).toHaveBeenCalledTimes(4);
    await act(() => {
      complete.splice(0).forEach((finish) => finish());
      return Promise.resolve();
    });
    await waitFor(() => expect(chartClient.series).toHaveBeenCalledTimes(8));
    await act(() => {
      complete.splice(0).forEach((finish) => finish());
      return Promise.resolve();
    });
    await waitFor(() =>
      expect(result.current.states.SP500.result?.requested_end).toBe('2026-10-05'),
    );
  });

  it('isolates a failed or foreign series and retries only its stored read', async () => {
    const items = watchlistFixture(2).items;
    vi.mocked(chartClient.series).mockResolvedValueOnce(
      watchlistSeries('listing:foreign', '2026-07-04', '2026-10-04'),
    );
    const { result } = renderHook(() =>
      useWatchlistSeries(items, '2026-07-04', '2026-10-04', 'CLOSE'),
    );
    await waitFor(() => expect(result.current.states.SP500.error).toContain('Identität'));
    expect(result.current.states.SP500.result).toBeNull();
    expect(result.current.states.ETF1.result).not.toBeNull();
    act(() => result.current.retry('SP500'));
    await waitFor(() => expect(result.current.states.SP500.result).not.toBeNull());
    expect(chartClient.series).toHaveBeenCalledTimes(3);
    expect(chartClient.invalidateTargets).toHaveBeenLastCalledWith(['reference:sp500']);
  });

  it('does not read unconfigured preview entries and rejects responses for another requested field', async () => {
    const preview = watchlistFixture(31, false).items;
    const { result, rerender } = renderHook(
      ({ items }) => useWatchlistSeries(items, null, '2026-10-04', 'ADJUSTED_CLOSE'),
      { initialProps: { items: preview } },
    );
    expect(chartClient.series).not.toHaveBeenCalled();
    vi.mocked(chartClient.series).mockResolvedValueOnce(
      watchlistSeries('reference:sp500', null, '2026-10-04', 'CLOSE'),
    );
    rerender({ items: watchlistFixture(1).items });
    await waitFor(() => expect(result.current.states.SP500.error).toContain('Zeitraum'));
    expect(result.current.states.SP500.result).toBeNull();
  });
});
