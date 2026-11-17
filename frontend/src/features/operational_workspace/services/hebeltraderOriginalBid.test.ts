import { MarketApiError, requestJson } from '../../market/services/http';
import type { HebeltraderOriginalBidReport } from '../hebeltraderOriginalBid';
import {
  documentedPriceScaleReport,
  missingBidSideReport,
  originalBidReport,
} from '../test/hebeltraderOriginalBidFixture';
import { readHebeltraderOriginalBid, verifyHebeltraderOriginalBid } from './hebeltraderOriginalBid';

vi.mock('../../market/services/http', async (original) => ({
  ...(await original<typeof import('../../market/services/http')>()),
  requestJson: vi.fn(),
}));

it('uses only the scoped owner GET and preserves exact decimals and the two event clocks', async () => {
  const report = documentedPriceScaleReport({ trade_id: 'trade/a', position_id: 'position/b' });
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

it('accepts documented product units only as an input proof while the live-market gap remains', () => {
  const report = documentedPriceScaleReport();
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
  expect(report.checks[6].status).toBe('SATISFIED');
  expect(report.checks[7].status).toBe('MISSING');
  expect(report.product_price_scale?.purchases[0].remaining_quantity).toBe('5');
  expect(report.product_price_scale?.purchases[0].executed_at).toBeNull();
  expect(report.coverage_status).toBe('PARTIAL');
});

it.each(['ISIN', 'UNDERLYING', 'BUY_CURRENCY'] as const)(
  'rejects an internally consistent documented product source with a foreign %s',
  (mismatch) => {
    const report = documentedPriceScaleReport();
    const scale = report.product_price_scale!;
    if (mismatch === 'ISIN') {
      scale.evidence.binding!.isin = 'DE0000000001';
      scale.evidence.manifest!.binding.isin = 'DE0000000001';
    } else if (mismatch === 'UNDERLYING') {
      scale.evidence.binding!.underlying_id = 'foreign-underlying';
      scale.evidence.manifest!.binding.underlying_id = 'foreign-underlying';
    } else scale.purchases[0].currency_code = 'USD';
    expect(() => verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toThrow(
      'nicht sicher zuordnen',
    );
  },
);

it.each(['OMITTED', 'DUPLICATE', 'SELL', 'OWNER_CURRENCY'] as const)(
  'rejects a documented comparison whose owner BUY set or currency is %s',
  (mismatch) => {
    const report = documentedPriceScaleReport();
    const scale = report.product_price_scale!;
    if (mismatch === 'OMITTED') scale.purchases.pop();
    else if (mismatch === 'DUPLICATE') scale.purchases[1].execution_id = 'effective-buy-1';
    else if (mismatch === 'SELL') scale.purchases[1].execution_id = 'effective-sale-1';
    else report.economic_basis.buy_currency_evidence[1].currency_code = 'USD';
    expect(() => verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toThrow(
      'nicht sicher zuordnen',
    );
  },
);

it('retains unsuitable historical product bindings and purchase currencies for clarification', () => {
  const report = documentedPriceScaleReport({ coverage_status: 'UNSUITABLE' });
  const scale = report.product_price_scale!;
  scale.evidence.status = 'UNSUITABLE';
  scale.evidence.binding!.isin = 'DE0000000001';
  scale.evidence.binding!.underlying_id = 'former-underlying';
  scale.evidence.manifest!.binding = { ...scale.evidence.binding! };
  scale.evidence.reasons = ['PRODUCT_PRICE_SCALE_BINDING_CHANGED'];
  scale.status = 'UNSUITABLE';
  scale.bid_status = 'UNSUITABLE';
  scale.purchases = scale.purchases.map((row) => ({
    ...row,
    currency_code: 'USD',
    status: 'UNSUITABLE',
    reasons: ['PRODUCT_SCALE_BUY_CURRENCY_MISMATCH'],
  }));
  report.checks[6].status = 'UNSUITABLE';
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
});

it.each(['ADJUSTMENT_REQUIRED', 'WITHDRAWN'] as const)(
  'preserves an unsuitable %s original product document and its correction chain',
  (status) => {
    const report = documentedPriceScaleReport({ coverage_status: 'UNSUITABLE' });
    const scale = report.product_price_scale!;
    scale.evidence.status = 'UNSUITABLE';
    scale.evidence.manifest!.status = status;
    scale.evidence.reasons = [`PRODUCT_PRICE_SCALE_${status}`];
    scale.status = 'UNSUITABLE';
    scale.bid_status = 'UNSUITABLE';
    scale.purchases = scale.purchases.map((row) => ({ ...row, status: 'UNSUITABLE' }));
    report.checks[6].status = 'UNSUITABLE';
    expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
    expect(scale.evidence.supersedes_revision_id).toBe('product-scale-revision-1');
    expect(scale.purchases[0].supersedes_execution_id).toBe('original-buy-1');
  },
);

it('keeps missing purchase coverage visible without discarding a remaining owner contribution', () => {
  const report = documentedPriceScaleReport();
  const scale = report.product_price_scale!;
  scale.status = 'MISSING';
  scale.purchases[1] = {
    ...scale.purchases[1],
    status: 'MISSING',
    reasons: ['PRODUCT_SCALE_BUY_OUTSIDE_DOCUMENTED_PERIOD'],
  };
  report.checks[6].status = 'MISSING';
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
  expect(scale.purchases).toHaveLength(2);
  expect(scale.purchases[1].remaining_quantity).toBe('2');
});

it('accepts an absent owner revision with actual purchase facts and no fabricated source', () => {
  const report = documentedPriceScaleReport();
  const scale = report.product_price_scale!;
  scale.status = 'MISSING';
  scale.bid_status = 'MISSING';
  scale.purchases = scale.purchases.map((row) => ({ ...row, status: 'MISSING' }));
  scale.evidence = {
    ...scale.evidence,
    status: 'MISSING',
    revision_id: null,
    supersedes_revision_id: null,
    revision_number: null,
    manifest: null,
    binding: null,
    source: null,
    recorded_at: null,
    reasons: ['PRODUCT_PRICE_SCALE_MISSING'],
  };
  report.checks[6].status = 'MISSING';
  expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
});

it.each(['CLOSED', 'CANCELLED'] as const)(
  'retains %s product evidence with every contribution not applicable',
  (position_state) => {
    const report = documentedPriceScaleReport({
      position_state,
      coverage_status: 'NOT_APPLICABLE',
    });
    const scale = report.product_price_scale!;
    scale.status = 'NOT_APPLICABLE';
    scale.bid_status = 'NOT_APPLICABLE';
    scale.purchases = scale.purchases.map((row) => ({ ...row, status: 'NOT_APPLICABLE' }));
    report.checks = report.checks.map((check) => ({ ...check, status: 'NOT_APPLICABLE' }));
    expect(verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toBe(report);
  },
);

it('rejects mixed scale scopes, owner bases, clocks, units and unsupported complete claims', () => {
  const mutations: Array<(report: HebeltraderOriginalBidReport) => void> = [
    (r) => {
      r.product_price_scale = null;
    },
    (r) => {
      delete r.product_price_scale;
    },
    (r) => {
      r.product_price_scale!.execution_basis_id = 'foreign-owner-basis';
    },
    (r) => {
      r.product_price_scale!.bid_at = r.evaluated_at;
    },
    (r) => {
      r.product_price_scale!.evidence.workspace_id = 'foreign-workspace';
    },
    (r) => {
      r.product_price_scale!.evidence.warrant_id = 'foreign-product';
    },
    (r) => {
      r.product_price_scale!.evidence.known_at = r.bid.original_bid_at!;
    },
    (r) => {
      r.product_price_scale!.evidence.manifest!.binding.warrant_id = 'foreign-product';
    },
    (r) => {
      r.product_price_scale!.evidence.manifest!.binding.current_terms_id = 'different-terms';
    },
    (r) => {
      r.product_price_scale!.evidence.manifest!.currency = 'USD';
    },
    (r) => {
      r.product_price_scale!.evidence.manifest!.source_document_sha256 = '0'.repeat(64);
    },
    (r) => {
      r.product_price_scale!.evidence.source!.published_on = '2026-09-22';
    },
    (r) => {
      r.product_price_scale!.purchases[0].execution_id = 'foreign-purchase';
    },
    (r) => {
      r.product_price_scale!.purchases[1].execution_id = 'effective-buy-1';
    },
    (r) => {
      r.product_price_scale!.purchases[0].executed_at = '2026-08-31T00:00:00Z';
    },
    (r) => {
      r.product_price_scale!.purchases[1].status = 'MISSING';
    },
    (r) => {
      r.product_price_scale!.bid_status = 'MISSING';
    },
    (r) => {
      r.product_price_scale!.evidence.status = 'UNSUITABLE';
    },
    (r) => {
      r.product_price_scale!.evidence.manifest!.status = 'WITHDRAWN';
    },
    (r) => {
      r.product_price_scale!.purchases = [];
    },
    (r) => {
      r.checks[6].status = 'MISSING';
    },
    (r) => {
      r.checks[7].status = 'SATISFIED';
    },
  ];
  for (const mutate of mutations) {
    const report = documentedPriceScaleReport();
    mutate(report);
    expect(() => verifyHebeltraderOriginalBid(report, 'trade-1', 'position-1')).toThrow(
      'nicht sicher zuordnen',
    );
  }
  for (const [key, value] of [
    ['axis', 'UNDERLYING'],
    ['unit', 'CENT_PER_WARRANT'],
    ['valid_until', null],
    ['schema_version', 'future-scale'],
  ]) {
    const report = documentedPriceScaleReport();
    const malformed = {
      ...report,
      product_price_scale: {
        ...report.product_price_scale,
        evidence: {
          ...report.product_price_scale!.evidence,
          manifest: { ...report.product_price_scale!.evidence.manifest, [key as string]: value },
        },
      },
    };
    expect(() => verifyHebeltraderOriginalBid(malformed, 'trade-1', 'position-1')).toThrow(
      'nicht sicher zuordnen',
    );
  }
  const report = documentedPriceScaleReport();
  expect(() =>
    verifyHebeltraderOriginalBid(
      {
        ...report,
        product_price_scale: { ...report.product_price_scale, adjustment_applied: true },
      },
      'trade-1',
      'position-1',
    ),
  ).toThrow('nicht sicher zuordnen');
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
