import type {
  PositionPriceHistoryReport,
  PositionPriceSeries,
} from '../features/operational_workspace/positionPriceHistory';

export function positionPriceSeries(
  overrides: Partial<PositionPriceSeries> = {},
): PositionPriceSeries {
  return {
    id: 'series-1',
    provider: 'BOERSE_STUTTGART_DELAYED',
    identity_key: 'original-identity',
    warrant_listing_id: 'listing-1',
    isin: 'DE000TEST1234',
    currency: 'EUR',
    price_kind: 'BID',
    source_mode: 'DELAYED',
    venue_mic: 'XSTU',
    provider_exchange_code: '_STU',
    points: [
      {
        id: 'point-1',
        observed_at: '2026-09-08T08:00:00Z',
        price: '0.2312345678',
        captured_at: null,
        retrieved_at: '2026-10-29T12:00:00Z',
        status: 'STALE',
        storage: 'RETAINED',
        quote_time_basis: 'PROVIDER_UTC',
      },
    ],
    ...overrides,
  };
}

export function positionPriceHistory(
  overrides: Partial<PositionPriceHistoryReport> = {},
): PositionPriceHistoryReport {
  return {
    trade_id: 'trade-1',
    position_id: 'position-1',
    warrant_id: 'warrant-1',
    isin: 'DE000TEST1234',
    window_start: null,
    window_end: '2026-10-30T12:00:00Z',
    sampling_policy: 'FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1',
    sample_limit: 10000,
    samples_considered: 0,
    samples_available: 0,
    truncated: false,
    collection_started_at: null,
    excluded: {},
    series: [positionPriceSeries()],
    events: [],
    ...overrides,
  };
}
