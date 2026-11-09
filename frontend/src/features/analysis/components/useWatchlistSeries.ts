import { useEffect, useRef, useState } from 'react';
import { chartClient } from '../services/chartClient';
import type { ChartComparison } from '../types/charts';
import type { ChartWatchlistItem } from '../types/watchlist';

export interface WatchlistSeriesState {
  loading: boolean;
  result: ChartComparison | null;
  error: string | null;
}

interface SeriesRequest {
  code: string;
  target: string | null;
  marker: string;
}

interface RequestPlan {
  start: string | null;
  end: string;
  field: 'CLOSE' | 'ADJUSTED_CLOSE';
  items: SeriesRequest[];
}

interface CachedSeries extends WatchlistSeriesState {
  marker: string;
}

/** Only stored chart GETs. One bounded worker group survives changing read generations. */
export function useWatchlistSeries(
  items: ChartWatchlistItem[],
  start: string | null,
  end: string,
  field: 'CLOSE' | 'ADJUSTED_CLOSE',
) {
  const cache = useRef(new Map<string, CachedSeries>());
  const running = useRef(Promise.resolve());
  const [states, setStates] = useState<Record<string, CachedSeries>>({});
  const [retries, setRetries] = useState<Record<string, number>>({});
  const plan: RequestPlan = {
    start,
    end,
    field,
    items: items.map((item) => ({
      code: item.code,
      target: item.target_key,
      marker: JSON.stringify([
        item.target_key,
        start,
        end,
        field,
        item.history.last_received_at,
        item.history.last_date,
        item.history.observation_count,
        item.mapping,
        item.setup_status,
        retries[item.code] ?? 0,
      ]),
    })),
  };
  const requestKey = JSON.stringify(plan);

  useEffect(() => {
    const current = JSON.parse(requestKey) as RequestPlan;
    const controller = new AbortController();
    const codes = new Set(current.items.map((item) => item.code));
    for (const code of cache.current.keys()) {
      if (!codes.has(code)) cache.current.delete(code);
    }
    setStates(
      Object.fromEntries(
        current.items.map((item) => {
          const stored = cache.current.get(item.code);
          return [
            item.code,
            stored?.marker === item.marker
              ? stored
              : { marker: item.marker, loading: Boolean(item.target), result: null, error: null },
          ];
        }),
      ),
    );

    const previous = running.current;
    running.current = (async () => {
      // Aborted earlier requests must settle before another group starts. Even
      // rapid date changes cannot create more than four concurrent chart reads.
      await previous;
      if (controller.signal.aborted) return;
      const pending = current.items.filter(
        (item) => item.target && cache.current.get(item.code)?.marker !== item.marker,
      );
      let next = 0;
      const worker = async () => {
        while (!controller.signal.aborted && next < pending.length) {
          const item = pending[next++];
          const target = item.target!;
          let state: WatchlistSeriesState;
          try {
            chartClient.invalidateTargets([target]);
            const result = await chartClient.series(
              [target],
              current.start,
              current.end,
              current.field,
              controller.signal,
            );
            if (controller.signal.aborted) return;
            if (
              result.series.length !== 1 ||
              result.series[0].identity.key !== target ||
              result.price_field !== current.field ||
              result.requested_start !== current.start ||
              result.requested_end !== current.end
            ) {
              throw new Error(
                'Die gelesene Kursreihe passt nicht zur angefragten Identität oder zum Zeitraum.',
              );
            }
            state = { loading: false, result, error: null };
          } catch (reason: unknown) {
            if (controller.signal.aborted) return;
            state = {
              loading: false,
              result: null,
              error: reason instanceof Error ? reason.message : 'Gespeicherte Kurse nicht lesbar.',
            };
          }
          const saved = { ...state, marker: item.marker };
          cache.current.set(item.code, saved);
          setStates((value) => ({ ...value, [item.code]: saved }));
        }
      };
      await Promise.all(Array.from({ length: Math.min(4, pending.length) }, worker));
    })();

    return () => controller.abort();
  }, [requestKey]);

  return {
    states: Object.fromEntries(
      plan.items.map((item) => [
        item.code,
        states[item.code]?.marker === item.marker
          ? states[item.code]
          : { loading: Boolean(item.target), result: null, error: null },
      ]),
    ) as Record<string, WatchlistSeriesState>,
    retry: (code: string) =>
      setRetries((current) => ({ ...current, [code]: (current[code] ?? 0) + 1 })),
  };
}
