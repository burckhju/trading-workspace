import {
  originalBidCheckKeys,
  type HebeltraderOriginalBidReport,
  type OriginalBidCheck,
} from '../hebeltraderOriginalBid';
import {
  sessionCalendar,
  sessionCount,
  sessionPeriod,
  syntheticSessionDays,
} from './hebeltraderSessionsFixture';

const evaluatedAt = '2026-09-21T13:05:00Z';
const bidAt = '2026-09-21T13:00:00Z';

export function originalBidReport(
  overrides: Partial<HebeltraderOriginalBidReport> = {},
): HebeltraderOriginalBidReport {
  const trade = overrides.trade_id ?? 'trade-1';
  const position = overrides.position_id ?? 'position-1';
  const product = overrides.product_id ?? 'product-1';
  const underlying = overrides.underlying_id ?? 'underlying-1';
  const calendar = sessionCalendar({
    instrument_id: underlying,
    known_at: evaluatedAt,
    read_at: evaluatedAt,
  });
  calendar.binding!.instrument_id = underlying;
  const days = syntheticSessionDays(21);
  const interval = {
    opens_at: '2026-09-21T09:00:00+02:00',
    closes_at: '2026-09-21T17:00:00+02:00',
  };
  const labels = [
    'Gehaltenes Instrument und Kursroute',
    'Original-Geldkurszeit und Kursalter',
    'Historische Ausführungswährung',
    'Dokumentierte Produktsitzung zur Geldkurszeit',
    'Dokumentierte Produktsitzung zum Lesestand',
    '20 Basiswertsitzungen zur Geldkurszeit',
    'Historischer Produkt-Preismaßstab',
    'Verifizierte offene Produktsitzung',
  ];
  const checks: OriginalBidCheck[] = originalBidCheckKeys.map((key, index) => ({
    key,
    label: labels[index],
    status: index < 6 ? 'SATISFIED' : 'MISSING',
    detail:
      index < 6
        ? 'Diese Teilvoraussetzung ist anhand der gespeicherten synthetischen Belege erfüllt.'
        : index === 6
          ? 'Der Ownerbeleg für den Produktmaßstab zwischen Einstand und Geldkurs fehlt; die Basiswertqualifikation ersetzt ihn nicht.'
          : 'Ein unabhängiger Live-Nachweis der geöffneten Produktsitzung fehlt; Kalender und Quellenmeldung OPEN ersetzen ihn nicht.',
    reasons:
      index < 6
        ? []
        : [
            index === 6
              ? 'WARRANT_EXECUTION_BID_SCALE_EVIDENCE_MISSING'
              : 'VERIFIED_LIVE_PRODUCT_SESSION_MISSING',
          ],
    affected_rules: ['B04', 'B58'],
  }));
  return {
    trade_id: trade,
    position_id: position,
    product_id: product,
    underlying_id: underlying,
    position_state: 'OPEN',
    basis_id: 'original-bid-report-basis',
    read_started_at: evaluatedAt,
    read_completed_at: '2026-09-21T13:05:00.050000Z',
    evaluated_at: evaluatedAt,
    economic_basis: {
      definition_version: 'position-unrealized-gross-v1',
      basis_id: 'execution-owner-basis',
      position: {
        id: position,
        trade_id: trade,
        product_id: product,
        open_quantity: 7,
        cost_basis: '6.913580247',
        average_entry_price: '0.987654321',
        realized_gross_pnl: '0',
        opened_at: '2026-08-31T08:00:00Z',
        last_execution_at: '2026-09-05T08:00:00Z',
        closed_at: null,
      },
      cost_basis_currency: 'EUR',
      currency_status: 'KNOWN',
      effective_execution_ids: ['effective-buy-1', 'effective-sale-1', 'effective-buy-2'],
      buy_currency_evidence: [
        {
          execution_id: 'effective-buy-1',
          currency_code: 'EUR',
          source: 'USER_CONFIRMED',
          source_execution_ids: [],
          confirmation_ids: ['currency-confirmation-1'],
        },
      ],
    },
    entry: {
      execution_id: 'effective-buy-1',
      executed_at: null,
      executed_on: '2026-08-31',
      execution_timezone: 'Europe/Berlin',
      time_precision: 'DATE_ONLY',
    },
    saved_quote: {
      reason: 'LAST_SUCCESS_IS_NOT_A_PRICE_SERIES',
      provider: 'FRANKFURT_QUOTES',
      retrieved_at: '2026-09-21T13:00:03Z',
      identity_key: 'explicit-quote-route',
      refresh_status: 'LATEST_REFRESH_NOT_OBSERVED_BY_PERSISTED_READER',
      history_observations: 1,
      route: {
        workspace_id: 'workspace-1',
        position_id: position,
        warrant_id: product,
        warrant_listing_id: 'warrant-listing-1',
        trading_venue_id: 'frankfurt-venue',
        venue_mic: 'XFRA',
        currency: 'EUR',
        identity_key: 'explicit-quote-route',
        selection_id: 'quote-selection-1',
        selected_at: '2026-09-01T08:00:00Z',
      },
      provenance: {
        read_at: evaluatedAt,
        raw_payload_fingerprint: 'f'.repeat(64),
        retrieved_at: '2026-09-21T13:00:03Z',
        quality_status: 'VALID',
        warnings: [],
        reason_code: null,
        stored_at: null,
        stored_at_status: 'NOT_RECORDED_BY_LAST_SUCCESS_STORE',
        storage_kind: 'LAST_SUCCESS',
        mutable: true,
        historical_read: false,
      },
      quote: {
        warrant_listing_id: 'warrant-listing-1',
        bid: '1.234567890123',
        ask: '1.24',
        currency: 'EUR',
        provider_symbol: 'DE000TEST1234',
        provider_exchange_code: 'XFRA',
        observed_at: '2026-09-21T12:59:58Z',
        isin: 'DE000TEST1234',
        wkn: 'TEST12',
        source_mode: 'FRANKFURT_DELAYED_MONITORING',
        trading_status: 'OPEN',
        reference_price: null,
        reference_price_type: null,
        assessed_at: '2026-09-21T13:00:03Z',
        feed_delay_seconds: 300,
        venue_mic: 'XFRA',
        max_quote_age_seconds: 900,
        refresh_error: null,
        retained: true,
        quote_time_text: null,
        quote_time_basis: null,
        bid_volume: 100,
        ask_volume: 100,
        original_evidence: {
          version: 'original-quote-evidence-v1',
          source_contract: 'frankfurt-quotes-v1',
          source_reference: 'SYNTHETIC-FRANKFURT',
          generated_at: '2026-09-21T13:00:02Z',
          isin: 'DE000TEST1234',
          currency: 'EUR',
          venue_mic: 'XFRA',
          bid: {
            price: '1.234567890123',
            observed_at: bidAt,
            original_time_text: '2026-09-21T15:00:00+02:00',
            source_field: 'bid_at',
            time_basis: 'SEPARATE_SIDE_TIMESTAMP',
          },
          ask: {
            price: '1.24',
            observed_at: '2026-09-21T12:59:58Z',
            original_time_text: '2026-09-21T14:59:58+02:00',
            source_field: 'ask_at',
            time_basis: 'SEPARATE_SIDE_TIMESTAMP',
          },
        },
      },
    },
    bid: {
      status: 'AVAILABLE',
      price: '1.234567890123',
      currency: 'EUR',
      original_bid_at: bidAt,
      age_seconds: '300',
      evaluated_at: evaluatedAt,
      reasons: [],
      maximum_age_seconds: 900,
      price_axis: 'WARRANT_BID',
    },
    product_sessions: {
      calendar: {
        ...calendar,
        instrument_kind: 'WARRANT',
        instrument_id: product,
        calendar_id: 'synthetic-product-calendar',
        revision_id: 'product-calendar-revision-1',
        binding: {
          ...calendar.binding!,
          instrument_kind: 'WARRANT',
          instrument_id: product,
          listing_id: 'warrant-listing-1',
          trading_venue_id: 'frankfurt-venue',
          venue_mic: 'XFRA',
        },
      },
      period: sessionPeriod({
        start_date: '2026-09-20',
        end_date: '2026-09-21',
        days: days.slice(19),
      }),
      at_bid: {
        status: 'IN_DOCUMENTED_INTERVAL',
        event_at: bidAt,
        session_date: '2026-09-21',
        interval,
        reasons: [],
      },
      at_read: {
        status: 'IN_DOCUMENTED_INTERVAL',
        event_at: evaluatedAt,
        session_date: '2026-09-21',
        interval,
        reasons: [],
      },
      interval_relation: 'SAME_INTERVAL',
    },
    underlying_sessions: {
      calendar,
      period: sessionPeriod({ start_date: '2026-09-01', end_date: '2026-09-21', days }),
      count: sessionCount({
        evaluated_at: bidAt,
        anchor_date: '2026-08-31',
        completed_sessions: 20,
        completed_session_dates: days.slice(0, 20).map((day) => day.session_date),
        twentieth_session_date: '2026-09-20',
        twentieth_closes_at: '2026-09-20T17:00:00+02:00',
        threshold_reached: true,
      }),
    },
    coverage_status: 'PARTIAL',
    checks,
    notices: [
      'Synthetischer Lesebefund. Dieser Read bucht keine Ausführung und ruft keinen Provider auf.',
    ],
    definition_version: 'hebeltrader-original-bid-v1',
    baseline_id: 'HEBELTRADER_CONFIRMED_BASELINE',
    baseline_version: '1.0.0',
    implementation_status: 'F207_3_ORIGINAL_BID_EVIDENCE_ONLY',
    rule_evaluation_status: 'B04_B05_B06_B58_NOT_EVALUATED',
    operation_status: 'NOT_ACTIVATED',
    read_status: 'READ_ONLY',
    ...overrides,
  };
}

export function missingBidSideReport(
  overrides: Partial<HebeltraderOriginalBidReport> = {},
): HebeltraderOriginalBidReport {
  const report = originalBidReport(overrides);
  report.saved_quote.quote!.original_evidence = null;
  report.bid = {
    ...report.bid,
    status: 'MISSING',
    original_bid_at: null,
    age_seconds: null,
    reasons: ['ORIGINAL_BID_SIDE_TIME_MISSING'],
  };
  report.product_sessions = {
    ...report.product_sessions,
    period: sessionPeriod({
      status: 'NOT_REQUESTED',
      start_date: null,
      end_date: null,
      fingerprint: null,
      days: [],
    }),
    at_bid: {
      status: 'NOT_ASSESSABLE',
      event_at: null,
      session_date: null,
      interval: null,
      reasons: report.bid.reasons,
    },
    at_read: {
      status: 'NOT_ASSESSABLE',
      event_at: report.evaluated_at,
      session_date: null,
      interval: null,
      reasons: report.bid.reasons,
    },
    interval_relation: 'NOT_ASSESSABLE',
  };
  report.underlying_sessions = {
    ...report.underlying_sessions,
    count: null,
    period: report.product_sessions.period,
  };
  report.checks = report.checks.map((check) =>
    [
      'ORIGINAL_BID_TIME_AND_AGE',
      'PRODUCT_SESSION_AT_BID',
      'PRODUCT_SESSION_AT_READ',
      'TWENTY_UNDERLYING_SESSIONS_AT_BID',
    ].includes(check.key)
      ? {
          ...check,
          status: 'MISSING',
          detail:
            'Die exakte BID-Seitenzeit fehlt. Gemeinsame Snapshotzeit, ASK-Zeit und Abrufzeit ersetzen sie nicht.',
          reasons: report.bid.reasons,
        }
      : check,
  );
  return report;
}
