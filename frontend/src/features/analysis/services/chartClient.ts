import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { ChartCatalog, ChartComparison, UnderlyingChartContext } from '../types/charts';
import { queuedChartRead } from './chartReadQueue';

const base = `${environment.apiBaseUrl}/api/v1/market-charts`;
// Bounded page-session cache. Hover, legend and display-mode changes never query.
const cache = new Map<string, { until: number; value: ChartComparison }>();

export const chartClient = {
  catalog: (asOf: string, signal?: AbortSignal) =>
    requestJson<ChartCatalog>(`${base}/catalog?as_of=${asOf}`, { signal }),
  underlying: (id: string, asOf: string, signal?: AbortSignal) =>
    requestJson<UnderlyingChartContext>(
      `${base}/underlyings/${encodeURIComponent(id)}?as_of=${asOf}`,
      { signal },
    ),
  async series(
    this: void,
    keys: string[],
    start: string | null,
    end: string,
    field: 'CLOSE' | 'ADJUSTED_CLOSE',
    signal?: AbortSignal,
  ) {
    const params = new URLSearchParams({ end_date: end, price_field: field });
    if (start) params.set('start_date', start);
    keys.forEach((key) => params.append('target', key));
    const url = `${base}/series?${params.toString()}`;
    const found = cache.get(url);
    if (found && found.until > Date.now()) return found.value;
    const value = await queuedChartRead(
      () => requestJson<ChartComparison>(url, { signal }),
      signal,
    );
    if (signal?.aborted) throw new DOMException('Chart read cancelled', 'AbortError');
    if (cache.size >= 16) cache.delete(cache.keys().next().value ?? '');
    cache.set(url, { until: Date.now() + 30_000, value });
    return value;
  },
  invalidateTargets: (keys: string[]) => {
    for (const url of cache.keys()) {
      if (new URL(url).searchParams.getAll('target').some((key) => keys.includes(key))) {
        cache.delete(url);
      }
    }
  },
  clear: () => cache.clear(),
};
