// Synthetic frontend fixtures only; never used as a product or provider catalog.
import type { ChartWatchlist } from '../features/analysis/types/watchlist';
import type { ChartComparison } from '../features/analysis/types/charts';
import { chartIdentity, chartSeries, comparison } from './chartFixtures';

export function watchlistFixture(count = 3, enabled = true): ChartWatchlist {
  return {
    catalog_version: 'synthetic-2026-11-09',
    name: 'TEST S&P 500 und ETF-Übersicht',
    enabled,
    scheduler: {
      enabled: true,
      running: true,
      leader: true,
      last_error: null,
      underlying_price_type: 'COMPLETED_EOD',
      settings: { underlyings_interval_seconds: 3600 },
    },
    items: Array.from({ length: count }, (_, index) => ({
      code: index === 0 ? 'SP500' : 'ETF' + index,
      kind: index === 0 ? 'INDEX' : 'ETF',
      name: index === 0 ? 'TEST S&P 500' : 'TEST ETF ' + index,
      group: index === 0 ? 'Index' : index % 2 ? 'Aktien' : 'Anleihen',
      isin: index === 0 ? null : 'US000000000' + index,
      mic: index === 0 ? null : 'ARCX',
      currency: index === 0 ? null : 'USD',
      ticker: index === 0 ? null : 'ETF' + index,
      source_url: 'https://example.test/source/' + index,
      target_key: enabled ? (index === 0 ? 'reference:sp500' : 'listing:etf-' + index) : null,
      setup_status: enabled ? 'CONFIGURED' : 'PENDING',
      setup_reason: null,
      last_attempt_at: enabled ? '2026-11-09T08:00:00Z' : null,
      setup_completed_at: enabled ? '2026-11-09T08:01:00Z' : null,
      history: {
        first_date: enabled ? '2026-09-01' : null,
        last_date: enabled ? '2026-09-03' : null,
        observation_count: enabled ? 3 : 0,
        last_received_at: enabled ? '2026-09-04T12:00:00Z' : null,
      },
      mapping: enabled
        ? {
            id: 'mapping-' + index,
            version: 4,
            status: 'ACTIVE',
            provider_symbol: index === 0 ? 'GSPC' : 'ETF' + index,
            provider_exchange_code: index === 0 ? 'INDX' : 'US',
            validated_at: '2026-11-09T08:00:00Z',
          }
        : null,
    })),
  };
}

export function watchlistSeries(
  target: string,
  start: string | null,
  end: string,
  field: 'CLOSE' | 'ADJUSTED_CLOSE' = 'CLOSE',
): ChartComparison {
  const index = target.startsWith('reference:');
  const result = comparison([
    chartSeries(
      chartIdentity(target, index ? 'TEST S&P 500' : 'TEST ETF', index ? 'INDEX' : 'ETF'),
    ),
  ]);
  return { ...result, requested_start: start, requested_end: end, price_field: field };
}
