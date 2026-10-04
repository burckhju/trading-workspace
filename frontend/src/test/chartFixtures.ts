// Synthetic data, imported only by unit and browser tests.
import type {
  ChartCatalog,
  ChartComparison,
  ChartIdentity,
  ChartSeries,
} from '../features/analysis/types/charts';
export function chartIdentity(
  key = 'reference:sp500',
  name = 'TEST S&P 500',
  kind = 'INDEX',
): ChartIdentity {
  return {
    key,
    name,
    instrument_id: key,
    instrument_type: kind,
    reference_id: kind === 'INDEX' ? key.split(':')[1] : null,
    reference_code: kind === 'INDEX' ? 'SP500' : null,
    underlying_id: kind === 'INDEX' ? null : key.split(':')[1],
    listing_id: kind === 'INDEX' ? null : key.split(':')[1],
    isin: kind === 'ETF' ? 'US81369Y5069' : null,
    ticker: kind === 'ETF' ? 'XLE' : null,
    mic: kind === 'INDEX' ? null : 'ARCX',
    currency: 'USD',
    return_basis: 'PRICE_INDEX',
    basis_source: 'https://example.test/evidence',
    active: true,
    mapping_status: 'ACTIVE',
    provider_identity: 'EODHD:TEST.INDX',
    mapping_id: 'm',
    mapping_version: 1,
    setup_url: '/chart-setup',
  };
}
export function chartSeries(identity = chartIdentity()): ChartSeries {
  return {
    identity,
    currency: 'USD',
    return_basis: 'UNADJUSTED_PRICE_CHANGE',
    points: [1, 2, 3].map((day, index) => ({
      trading_date: `2026-09-0${day}`,
      value: String(100 + index * 10),
      normalized: String(100 + index * 10),
      change_percent: String(index * 10),
      provider: 'EODHD',
      provider_symbol: 'TEST',
      received_at: '2026-09-04T12:00:00Z',
      source_updated_at: null,
      observed_at: null,
      quality: 'VALID',
      warnings: [],
      gap_before: false,
    })),
    first_date: '2026-09-01',
    last_date: '2026-09-03',
    observation_count: 3,
    issues: [],
    missing_comparison_dates: [],
  };
}
export function comparison(series = [chartSeries()]): ChartComparison {
  return {
    series,
    requested_start: '2026-07-04',
    requested_end: '2026-10-04',
    price_field: 'CLOSE',
    common_start: '2026-09-01',
    common_end: '2026-09-03',
    comparison_status: 'READY',
    issues: [],
    model_version: 'TIME_SERIES_COMPARISON/1.0.0',
    resolution: 'EOD_FULL',
    fx_adjusted: false,
    calendar_verified: false,
    max_points_per_series: 10000,
  };
}
export function chartCatalog(): ChartCatalog {
  const history = { count: 3, first_date: '2026-09-01', last_date: '2026-09-03' };
  return {
    references: [{ identity: chartIdentity(), history }],
    proxies: [],
    as_of: '2026-10-04',
    taxonomy_status: 'CONFIGURED',
    sectors: ['Energy', 'Materials', 'Industrials'].map((name, index) => ({
      context: {
        id: name,
        code: String(10 + index * 5),
        name,
        classification_system: 'GICS',
        classification_version: 'test',
        active: true,
        reference: null,
        proxy: index < 2 ? chartIdentity(`listing:${name}`, `TEST ${name} ETF`, 'ETF') : null,
        status: index < 2 ? 'CONFIGURED' : 'MISSING_REFERENCE',
        setup_url: `/chart-setup?sector_id=${name}`,
      },
      reference_history: { count: 0, first_date: null, last_date: null },
      proxy_history: index < 2 ? history : { count: 0, first_date: null, last_date: null },
    })),
  };
}
