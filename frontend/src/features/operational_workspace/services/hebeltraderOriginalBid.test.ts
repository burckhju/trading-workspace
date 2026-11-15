import { MarketApiError, requestJson } from '../../market/services/http';
import type { HebeltraderOriginalBidReport } from '../hebeltraderOriginalBid';
import { missingBidSideReport, originalBidReport } from '../test/hebeltraderOriginalBidFixture';
import { readHebeltraderOriginalBid, verifyHebeltraderOriginalBid } from './hebeltraderOriginalBid';

vi.mock('../../market/services/http', async (original) => ({
  ...(await original<typeof import('../../market/services/http')>()),
  requestJson: vi.fn(),
}));

it('uses only the scoped owner GET and preserves exact decimals and the two event clocks', async () => {
  const report = originalBidReport({ trade_id: 'trade/a', position_id: 'position/b' });
  vi.mocked(requestJson).mockResolvedValueOnce(report);
  const signal = new AbortController().signal;
  expect(await readHebeltraderOriginalBid('trade/a', 'position/b', signal)).toBe(report);
  expect(requestJson).toHaveBeenCalledOnce();
  expect(requestJson).toHaveBeenCalledWith(
    expect.stringMatching(/trades\/trade%2Fa\/hebeltrader-original-bid\?position_id=position%2Fb$/),
    { signal },
  );
  expect(report.bid.price).toBe('1.234567890123');
  expect(report.underlying_sessions.count?.evaluated_at).toBe(report.bid.original_bid_at);
  expect(report.underlying_sessions.count?.evaluated_at).not.toBe(report.evaluated_at);
});

it('keeps legacy side gaps inspectable without replacing the BID clock with snapshot or retrieval time', () => {
  const report = missingBidSideReport();
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
  expect(report.saved_quote.quote?.observed_at).not.toBeNull();
  expect(report.bid.original_bid_at).toBeNull();
  expect(report.underlying_sessions.count).toBeNull();
});

it('accepts an unsuitable stored payload with route/provenance and no quote, and a missing product route', () => {
  const report = missingBidSideReport();
  report.coverage_status = 'UNSUITABLE';
  report.saved_quote.quote = null;
  report.saved_quote.reason = 'SAVED_QUOTE_PAYLOAD_INVALID';
  report.bid = {
    ...report.bid,
    status: 'UNSUITABLE',
    price: null,
    currency: null,
    reasons: ['SAVED_QUOTE_PAYLOAD_INVALID'],
  };
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
  report.saved_quote.route = null;
  report.saved_quote.provenance = null;
  report.product_sessions.calendar = null;
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
});

it('does not equate decimal formatting with a price correction or requalify an owner currency conflict', () => {
  const report = originalBidReport();
  report.saved_quote.quote!.bid = '1.2300';
  report.saved_quote.quote!.original_evidence!.bid!.price = '1.23';
  report.bid.price = '1.2300';
  report.economic_basis.cost_basis_currency = 'USD';
  report.coverage_status = 'UNSUITABLE';
  report.checks[2] = {
    ...report.checks[2],
    status: 'UNSUITABLE',
    detail: 'Kauf und Geldkurs besitzen verschiedene Währungen.',
    reasons: ['EXECUTION_BID_CURRENCY_MISMATCH'],
  };
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
});

it('accepts an optional snapshot ISIN when the original instrument is bound to the provider symbol', () => {
  const report = originalBidReport();
  report.saved_quote.quote!.isin = null;
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
  report.saved_quote.quote!.original_evidence!.isin = 'FOREIGN-INSTRUMENT';
  expect(() => verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toThrow(
    'nicht sicher zuordnen',
  );
});

it('keeps an unsuitable calendar listing mismatch readable without claiming a matching available binding', () => {
  const report = originalBidReport();
  report.product_sessions.calendar!.status = 'UNSUITABLE';
  report.product_sessions.calendar!.binding!.listing_id = 'other-listing';
  report.coverage_status = 'UNSUITABLE';
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
});

it('preserves a withdrawn calendar as owner-qualified unsuitable evidence', () => {
  const report = originalBidReport();
  report.underlying_sessions.calendar.status = 'UNSUITABLE';
  report.underlying_sessions.calendar.evidence_status = 'WITHDRAWN';
  report.underlying_sessions.count = {
    ...report.underlying_sessions.count!,
    status: 'NOT_ASSESSABLE',
    completed_sessions: null,
    completed_session_dates: [],
    twentieth_session_date: null,
    twentieth_closes_at: null,
    threshold_reached: null,
    reasons: ['SESSION_EVIDENCE_WITHDRAWN'],
  };
  report.checks[5] = {
    ...report.checks[5],
    status: 'UNSUITABLE',
    detail: 'Der Kalender wurde zurückgezogen.',
    reasons: ['SESSION_EVIDENCE_WITHDRAWN'],
  };
  report.coverage_status = 'UNSUITABLE';
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
});

it.each(['CLOSED', 'CANCELLED'] as const)(
  'accepts %s only with all eight not-applicable prerequisites',
  (position_state) => {
    const report = missingBidSideReport({ position_state, coverage_status: 'NOT_APPLICABLE' });
    report.bid.status = 'NOT_APPLICABLE';
    report.checks = report.checks.map((check) => ({ ...check, status: 'NOT_APPLICABLE' }));
    expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
  },
);

it('rejects mixed identities and clocks, wrong price axes and any claim of complete or activated qualification', () => {
  const cases: Array<(value: HebeltraderOriginalBidReport) => unknown> = [
    (r) => ({ ...r, trade_id: 'other' }),
    (r) => ({ ...r, position_id: 'other' }),
    (r) => ({ ...r, definition_version: 'future' }),
    (r) => ({ ...r, coverage_status: 'COMPLETE' }),
    (r) => ({ ...r, rule_evaluation_status: 'B04_EVALUATED' }),
    (r) => ({ ...r, operation_status: 'ACTIVE' }),
    (r) => ({ ...r, read_status: 'WRITE' }),
    (r) => ({
      ...r,
      economic_basis: {
        ...r.economic_basis,
        position: { ...r.economic_basis.position, product_id: 'foreign' },
      },
    }),
    (r) => ({
      ...r,
      saved_quote: { ...r.saved_quote, route: { ...r.saved_quote.route, workspace_id: 'foreign' } },
    }),
    (r) => ({
      ...r,
      saved_quote: { ...r.saved_quote, route: { ...r.saved_quote.route, position_id: 'foreign' } },
    }),
    (r) => ({
      ...r,
      saved_quote: {
        ...r.saved_quote,
        quote: { ...r.saved_quote.quote, warrant_listing_id: 'foreign' },
      },
    }),
    (r) => ({
      ...r,
      saved_quote: { ...r.saved_quote, quote: { ...r.saved_quote.quote, currency: 'USD' } },
    }),
    (r) => ({
      ...r,
      saved_quote: {
        ...r.saved_quote,
        provenance: { ...r.saved_quote.provenance, historical_read: true },
      },
    }),
    (r) => ({
      ...r,
      saved_quote: {
        ...r.saved_quote,
        provenance: { ...r.saved_quote.provenance, stored_at: r.evaluated_at },
      },
    }),
    (r) => ({
      ...r,
      saved_quote: {
        ...r.saved_quote,
        provenance: { ...r.saved_quote.provenance, read_at: r.bid.original_bid_at },
      },
    }),
    (r) => ({
      ...r,
      underlying_sessions: {
        ...r.underlying_sessions,
        calendar: { ...r.underlying_sessions.calendar, known_at: r.bid.original_bid_at },
      },
    }),
    (r) => ({
      ...r,
      product_sessions: {
        ...r.product_sessions,
        calendar: { ...r.product_sessions.calendar, known_at: r.bid.original_bid_at },
      },
    }),
    ...['listing_id', 'trading_venue_id', 'venue_mic'].map(
      (key) => (r: HebeltraderOriginalBidReport) => ({
        ...r,
        product_sessions: {
          ...r.product_sessions,
          calendar: {
            ...r.product_sessions.calendar,
            binding: { ...r.product_sessions.calendar!.binding, [key]: 'foreign' },
          },
        },
      }),
    ),
    (r) => ({ ...r, bid: { ...r.bid, price_axis: 'UNDERLYING' } }),
    (r) => ({ ...r, bid: { ...r.bid, age_seconds: 300 } }),
    (r) => ({ ...r, bid: { ...r.bid, original_bid_at: r.saved_quote.quote?.observed_at } }),
    (r) => ({ ...r, bid: { ...r.bid, evaluated_at: '2026-09-21T13:05:00' } }),
    (r) => ({
      ...r,
      underlying_sessions: {
        ...r.underlying_sessions,
        count: { ...r.underlying_sessions.count, evaluated_at: r.evaluated_at },
      },
    }),
    (r) => ({
      ...r,
      product_sessions: {
        ...r.product_sessions,
        calendar: { ...r.product_sessions.calendar, instrument_kind: 'UNDERLYING' },
      },
    }),
    (r) => ({
      ...r,
      product_sessions: {
        ...r.product_sessions,
        at_bid: { ...r.product_sessions.at_bid, event_at: r.evaluated_at },
      },
    }),
    (r) => ({ ...r, checks: r.checks.slice(1) }),
    (r) => ({
      ...r,
      checks: r.checks.map((check) =>
        check.key === 'PRICE_SCALE' ? { ...check, status: 'SATISFIED' } : check,
      ),
    }),
    (r) => ({
      ...r,
      checks: r.checks.map((check) =>
        check.key === 'VERIFIED_LIVE_MARKET_STATUS' ? { ...check, status: 'SATISFIED' } : check,
      ),
    }),
    (r) => ({ ...r, checks: [...r.checks.slice(0, 7), r.checks[6]] }),
  ];
  for (const invalid of [null, [], ...cases.map((mutate) => mutate(originalBidReport()))]) {
    expect(() => verifyHebeltraderOriginalBid(invalid, 'trade-1', 'position-1')).toThrow(
      'nicht sicher zuordnen',
    );
  }
});

it('keeps permission and technical read failures distinct from missing or unsuitable evidence', async () => {
  vi.mocked(requestJson).mockRejectedValueOnce(
    new MarketApiError(403, {
      code: 'FORBIDDEN',
      message: 'Forbidden',
      details: [],
      timestamp: '2026-09-21T13:05:00Z',
    }),
  );
  await expect(readHebeltraderOriginalBid('trade-1', 'position-1')).rejects.toThrow(
    'Keine Berechtigung',
  );
  vi.mocked(requestJson).mockRejectedValueOnce(new Error('offline'));
  await expect(readHebeltraderOriginalBid('trade-1', 'position-1')).rejects.toThrow(
    'Fehlende oder ungeeignete Kursbelege sind damit nicht festgestellt',
  );
});
