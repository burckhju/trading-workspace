import { describe, expect, it } from 'vitest';

import { realizedGrossReport, reportSource } from '../../../test/realizedGrossFixtures';
import type { RealizedGrossItem, RealizedGrossReport, RealizedGrossSource } from '../types/api';
import { realizedTradeLink, type RealizedReportContext } from './performanceReportContext';
import { buildRealizedCurrencyNotice, currencyResolutionLabel } from './realizedCurrencyNotice';

type Resolution = NonNullable<RealizedGrossSource['currency_resolution']>;

function setup() {
  const report = realizedGrossReport();
  const item = report.items[1];
  const context: RealizedReportContext = {
    filters: { ...report.filters },
    basis: report.basis.id,
    view: 'candidates',
    page: 0,
  };
  const source = (id: string) => report.sources.find((entry) => entry.execution_id === id)!;
  const build = () => buildRealizedCurrencyNotice(item, report, context)!;
  return { report, item, context, source, build };
}

function unresolvedItem(item: RealizedGrossItem, reasons = ['CURRENCY_UNKNOWN']) {
  Object.assign(item, {
    status: 'NOT_COMPUTABLE',
    reasons,
    average_cost_per_unit: null,
    cost_basis_before: null,
    cost_basis_after: null,
    realized_gross_pnl_delta: null,
    realized_gross_pnl_delta_display: null,
  });
}

function unknownResolution(overrides: Partial<Resolution> = {}): Resolution {
  return {
    currency_code: null,
    source: 'UNKNOWN',
    source_execution_ids: [],
    confirmation_ids: [],
    ...overrides,
  };
}

function detailText(notice: ReturnType<typeof buildRealizedCurrencyNotice>): string {
  return notice!.details.map((row) => `${row.label}: ${row.value}`).join('\n');
}

describe('one current SELL contribution and its actual BUY evidence', () => {
  it('keeps a known SELL currency separate from an unresolved preceding BUY', () => {
    const { item, source, build } = setup();
    unresolvedItem(item);
    source('buy-august').currency_resolution = unknownResolution({
      reason: 'NO_HISTORICAL_EVIDENCE',
    });
    source('buy-august').currency_confirmation = null;
    const notice = build();
    expect(notice.presentation).toEqual({ kind: 'warning', priority: 'relevant-problem' });
    expect(notice.title).toBe('Währungsherkunft dieses Beitrags ungeklärt');
    expect(notice.impact).toContain('Bruttobeitrag dieses Verkaufs derzeit nicht berechnen');
    expect(detailText(notice)).toContain('Kauf 1 · Währungsherkunft: unbekannt');
    expect(detailText(notice)).toContain('kein passender historischer Währungsbeleg');
    expect(detailText(notice)).toContain(
      'Verkauf · Währungsherkunft: EUR · ausdrücklich bestätigt',
    );
    expect(notice.userNeed.kind).toBe('optional-inspection');
  });

  it('does not repair a mixed BUY basis with an explicitly confirmed EUR SELL', () => {
    const { item, source, build } = setup();
    unresolvedItem(item, ['CURRENCY_MIXED']);
    source('buy-september').currency_resolution!.currency_code = 'USD';
    source('buy-september').currency_confirmation!.currency_code = 'USD';
    const notice = build();
    expect(notice.presentation.kind).toBe('warning');
    expect(notice.cause.explanation).toContain('keine einheitliche Währungszuordnung');
    expect(detailText(notice)).toContain('Kauf 2 · Währungsherkunft: USD · ausdrücklich bestätigt');
    expect(detailText(notice)).toContain(
      'Verkauf · Währungsherkunft: EUR · ausdrücklich bestätigt',
    );
    expect(item.realized_gross_pnl_delta).toBeNull();
  });

  it.each(['unknown', 'USD'])(
    'ignores the earlier SELL currency (%s) as BUY cost evidence',
    (code) => {
      const { source, build } = setup();
      const initial = build();
      source('sell-september-1').currency_resolution =
        code === 'unknown'
          ? unknownResolution({ reason: 'DOCUMENT_CONFLICT' })
          : { ...source('sell-september-1').currency_resolution!, currency_code: code };
      const notice = build();
      expect(notice.presentation.kind).toBe('information');
      expect(notice.id).toBe(initial.id);
      expect(detailText(notice)).not.toContain('DOCUMENT_CONFLICT');
      expect(detailText(notice)).not.toContain('USD');
    },
  );

  it('does not attach later or historically replaced BUY problems to this contribution', () => {
    const { report, build } = setup();
    const initial = build();
    report.sources.push(
      reportSource('later-buy', {
        executed_at: '2026-10-10T10:00:00Z',
        currency_resolution: unknownResolution({ reason: 'LISTING_HISTORY_INCOMPLETE' }),
      }),
      reportSource('replaced-buy', {
        is_effective: false,
        superseded_by_execution_id: 'buy-august',
        currency_resolution: unknownResolution({ source: 'CONFLICT', reason: 'DOCUMENT_CONFLICT' }),
      }),
    );
    const notice = build();
    expect(notice.id).toBe(initial.id);
    expect(notice.presentation.kind).toBe('information');
    expect(detailText(notice)).not.toContain('LISTING_HISTORY_INCOMPLETE');
    expect(detailText(notice)).not.toContain('DOCUMENT_CONFLICT');
  });

  it.each(['OUTSIDE_PERIOD', 'OTHER_CURRENCY'])(
    'keeps EXCLUDED plus CURRENCY_UNKNOWN neutral (%s)',
    (exclusion) => {
      const { item, source, report, build } = setup();
      unresolvedItem(item, [exclusion, 'CURRENCY_UNKNOWN']);
      item.status = 'EXCLUDED';
      source('buy-august').currency_resolution = unknownResolution();
      const summary = structuredClone(report.summary);
      const notice = build();
      expect(notice.presentation.kind).toBe('information');
      expect(notice.userNeed.kind).toBe('optional-inspection');
      expect(notice.impact).toContain('von der gewählten Berichtssumme ausgeschlossen');
      expect(notice.impact).toContain('blockiert die gewählte Summe nicht');
      expect(notice.title).not.toContain('ungeklärt');
      expect(report.summary).toEqual(summary);
    },
  );

  it('does not invent a currency cause for a different noncomputable owner reason', () => {
    const { item, build } = setup();
    unresolvedItem(item, ['HISTORY_INVALID', 'FUTURE_OWNER_REASON']);
    const notice = build();
    expect(notice.presentation.kind).toBe('information');
    expect(notice.impact).toContain(
      'Eine nähere Währungsursache kann diese Ansicht aus den gelieferten Gründen nicht erläutern',
    );
    expect(detailText(notice)).toContain('HISTORY_INVALID · FUTURE_OWNER_REASON');
  });

  it.each([
    ['0.0000000000', '0.00'],
    [null, null],
  ])(
    'preserves the original amount pair %s / %s and never calculates a substitute',
    (raw, display) => {
      const { report, item, build } = setup();
      if (raw === null) unresolvedItem(item);
      item.realized_gross_pnl_delta = raw;
      item.realized_gross_pnl_delta_display = display;
      const original = structuredClone(report);
      const notice = build();
      expect(notice.presentation.kind).toBe(raw === null ? 'warning' : 'information');
      expect(report).toEqual(original);
      expect(item.realized_gross_pnl_delta).toBe(raw);
      expect(item.realized_gross_pnl_delta_display).toBe(display);
    },
  );
});

describe('original resolution provenance and bounded explanations', () => {
  it.each([
    ['PRIOR_BUYS', 'aus vorherigen Käufen übernommen'],
    ['REPLACED_EXECUTION', 'aus ursprünglicher Buchung übernommen'],
    ['EXECUTION_DOCUMENT', 'automatisch aus Ausführungsbeleg abgeleitet'],
    ['HISTORICAL_LISTING', 'automatisch aus historischer Notierung abgeleitet'],
    ['HISTORICAL_LISTINGS', 'automatisch aus historischen Notierungen abgeleitet'],
  ] as const)('reuses %s without manufacturing a new confirmation or recovery', (origin, label) => {
    const { source, build } = setup();
    const sell = source('sell-september-2');
    sell.currency_confirmation = null;
    sell.currency_history = [];
    sell.currency_resolution = {
      currency_code: 'EUR',
      source: origin,
      source_execution_ids: ['buy-august'],
      confirmation_ids: ['currency-buy-august'],
      evidence_ids: ['evidence-version-1'],
      resolver_version: 'execution-currency-v3',
      evidence: [
        {
          id: 'evidence-version-1',
          kind: 'HISTORICAL_LISTINGS',
          source_reference: 'Geprüftes historisches Archiv',
          source_fingerprint: 'source-fingerprint-1',
          recorded_at: '2026-10-17T09:00:00Z',
          valid_from: '2026-08-01T00:00:00Z',
          valid_to: '2026-10-01T00:00:00Z',
        },
      ],
    };
    const notice = build();
    expect(notice.presentation.kind).toBe('information');
    expect(notice.automatic.kind).toBe('owner-result-reused');
    expect(notice.automatic.explanation).toContain('keine erneute Bestätigung nötig');
    expect(detailText(notice)).toContain(`Verkauf · Währungsherkunft: EUR · ${label}`);
    expect(detailText(notice)).toContain('Geprüftes historisches Archiv');
    expect(detailText(notice)).toContain('source-fingerprint-1');
    expect(detailText(notice)).toContain('bis ausschließlich 2026-10-01T00:00:00Z');
    expect(detailText(notice)).not.toContain(
      'Verkauf · Währungsherkunft: EUR · ausdrücklich bestätigt',
    );
    expect(sell.currency_confirmation).toBeNull();
    expect(sell.currency_history).toEqual([]);
  });

  it.each([
    ['DOCUMENT_CONFLICT', 'CONFLICT', 'Währung oder Handelsplatz'],
    ['LISTING_CONFLICT', 'CONFLICT', 'denselben Handelsplatz'],
    ['MULTIPLE_LISTING_CURRENCIES', 'MIXED', 'historischen Handelsplätze'],
    [
      'LISTING_HISTORY_INCOMPLETE',
      'UNKNOWN',
      'reichen für eine eindeutige Währungszuordnung nicht aus',
    ],
    ['EXECUTION_TIME_UNKNOWN', 'UNKNOWN', 'Ausführungsdatum oder Zeitzone'],
    ['CORRECTION_SOURCE_REVIEW_REQUIRED', 'UNKNOWN', 'ersetzten Buchung'],
    ['EVIDENCE_HISTORY_INVALID', 'CONFLICT', 'Historie der Währungsbelege ist widersprüchlich'],
  ] as const)(
    'explains %s without adding a narrower unproven cause',
    (reason, origin, expected) => {
      const { item, source, build } = setup();
      unresolvedItem(item, [
        origin === 'MIXED'
          ? 'CURRENCY_MIXED'
          : origin === 'CONFLICT'
            ? 'CURRENCY_CONFLICT'
            : 'CURRENCY_UNKNOWN',
      ]);
      source('buy-august').currency_resolution = unknownResolution({ source: origin, reason });
      const notice = build();
      expect(detailText(notice)).toContain(expected);
      expect(detailText(notice)).toContain(reason);
      expect(detailText(notice)).not.toContain('widersprüchliche Kaufwährungen');
      expect(notice.title).not.toContain(reason);
      expect(notice.cause.explanation).not.toContain(reason);
    },
  );

  it('keeps an unknown source reason as secondary original evidence without guessing its meaning', () => {
    const { item, source, build } = setup();
    unresolvedItem(item);
    source('buy-august').currency_resolution = unknownResolution({ reason: 'NEW_OWNER_REASON' });
    const notice = build();
    expect(detailText(notice)).toContain('noch nicht näher erläuterten Grund');
    expect(detailText(notice)).toContain('NEW_OWNER_REASON');
    expect(notice.title).not.toContain('NEW_OWNER_REASON');
    expect(notice.cause.explanation).not.toContain('NEW_OWNER_REASON');
    expect(detailText(notice)).not.toContain('kein passender historischer Währungsbeleg');
  });

  it('keeps two independent equal reasons and their sources visible', () => {
    const { item, source, build } = setup();
    unresolvedItem(item);
    for (const id of ['buy-august', 'buy-september']) {
      source(id).currency_resolution = unknownResolution({
        reason: 'LISTING_HISTORY_INCOMPLETE',
        evidence_ids: [`evidence-${id}`],
      });
    }
    const notice = build();
    expect(notice.details.filter((row) => row.label.endsWith(' · Ursache'))).toHaveLength(2);
    expect(detailText(notice)).toContain('evidence-buy-august');
    expect(detailText(notice)).toContain('evidence-buy-september');
    expect(notice.id).toContain('evidence-buy-august');
    expect(notice.id).toContain('evidence-buy-september');
  });

  it('does not synthesize a missing resolution from an existing manual confirmation', () => {
    const { source, build } = setup();
    delete source('buy-august').currency_resolution;
    const notice = build();
    expect(source('buy-august').currency_confirmation?.currency_code).toBe('EUR');
    expect(detailText(notice)).toContain('keine Währungsauflösung für diese Buchung');
    expect(detailText(notice)).toContain('nicht zu einer Auflösung ergänzt');
    expect(notice.presentation.kind).toBe('information');
    expect(notice.cause.known).toBe(false);
  });

  it('keeps compact labels neutral for unknown and multiple historical listing currencies', () => {
    expect(currencyResolutionLabel(unknownResolution())).toBe('unbekannt');
    expect(currencyResolutionLabel(unknownResolution({ source: 'USER_CONFIRMED' }))).toBe(
      'unbekannt',
    );
    expect(
      currencyResolutionLabel(
        unknownResolution({ source: 'MIXED', reason: 'MULTIPLE_LISTING_CURRENCIES' }),
      ),
    ).toBe('keine eindeutige Währungszuordnung');
  });
});

describe('one valid report, item and navigation context', () => {
  it.each([
    ['different item instance', (report) => ({ ...report.items[1] })],
    ['item from another response', () => realizedGrossReport().items[1]],
  ] satisfies [string, (report: RealizedGrossReport) => RealizedGrossItem][])(
    'rejects %s without retaining an action',
    (_label, select) => {
      const { report, context } = setup();
      expect(buildRealizedCurrencyNotice(select(report), report, context)).toBeNull();
    },
  );

  it.each([
    'definition',
    'filter',
    'currency',
    'basis',
    'missing-basis',
    'invalid-zone',
    'invalid-page',
    'duplicate-item',
  ])('rejects a mismatched or invalid %s without a substitute', (problem) => {
    const { item, report, context, build } = setup();
    if (problem === 'definition') report.definition_version = 'closed-trade-gross-v1';
    if (problem === 'filter') context.filters.from_date = '2026-09-02';
    if (problem === 'currency') report.currency.code = 'USD';
    if (problem === 'basis') context.basis = 'b'.repeat(64);
    if (problem === 'missing-basis') context.basis = null;
    if (problem === 'invalid-zone')
      report.filters.report_timezone = context.filters.report_timezone = 'not/a-zone';
    if (problem === 'invalid-page') context.page = -1;
    if (problem === 'duplicate-item') report.items.push({ ...item });
    expect(build()).toBeNull();
  });

  it.each([
    'missing',
    'duplicate',
    'foreign-trade',
    'foreign-product',
    'replaced',
    'wrong-sale-side',
  ])('does not consume a %s source as proof', (problem) => {
    const { item, report, source, build } = setup();
    const id = problem === 'wrong-sale-side' ? item.execution_id : 'buy-august';
    const selected = source(id);
    selected.currency_resolution = unknownResolution({ reason: 'MUST_NOT_BE_CONSUMED' });
    if (problem === 'missing')
      report.sources = report.sources.filter((entry) => entry !== selected);
    if (problem === 'duplicate') report.sources.push({ ...selected });
    if (problem === 'foreign-trade') selected.trade_id = 'another-trade';
    if (problem === 'foreign-product') selected.product_id = 'another-product';
    if (problem === 'replaced') {
      selected.is_effective = false;
      selected.superseded_by_execution_id = 'replacement';
    }
    if (problem === 'wrong-sale-side') selected.side = 'BUY';
    const notice = build();
    expect(notice.presentation.kind).toBe('information');
    expect(notice.cause.known).toBe(false);
    expect(detailText(notice)).toContain('Quellenzuordnung');
    expect(detailText(notice)).not.toContain('MUST_NOT_BE_CONSUMED');
    expect(notice.actions[0].destination.subject.id).toBe(item.trade_id);
  });

  it('retains the existing read link with the current report context and known trade', () => {
    const { item, report, context, build } = setup();
    const notice = build();
    expect(notice.actions).toHaveLength(1);
    expect(notice.actions[0]).toMatchObject({
      kind: 'read',
      label: 'Buchungen und Währungsbestätigungen im Trade prüfen',
      destination: {
        href: realizedTradeLink(item.trade_id, context),
        builder: 'realizedTradeLink',
        granularity: 'section',
        subject: { identity: 'known-object', kind: 'trade', id: item.trade_id },
        relationshipProof: { snapshotToken: report.basis.id },
      },
    });
    expect(notice.actions[0].destination.href).toContain('#execution-dates');
    expect(notice.actions[0].destination.href).not.toContain('execution_id=');
    for (const text of [
      notice.title,
      notice.cause.explanation,
      notice.impact,
      notice.userNeed.explanation,
    ]) {
      expect(text).not.toContain(item.execution_id);
      expect(text).not.toContain(item.trade_id);
    }
  });

  it('keeps cause identity across rereads and unrelated basis changes while replacing current proofs and the link', () => {
    const { report, item, context, source, build } = setup();
    unresolvedItem(item);
    source('buy-august').currency_resolution = unknownResolution({
      reason: 'LISTING_HISTORY_INCOMPLETE',
      evidence_ids: ['evidence-v1'],
    });
    const first = build();
    report.basis.id = context.basis = 'b'.repeat(64);
    report.basis.read_completed_at = '2026-11-01T11:00:00Z';
    report.basis.calculated_at = '2026-11-01T11:00:01Z';
    // Another already qualified BUY's declaration is not the unresolved source.
    source('buy-september').currency_resolution!.confirmation_ids = ['new-unrelated-confirmation'];
    const next = build();
    expect(next.id).toBe(first.id);
    expect(next.time.observedAt).toBeNull();
    expect(next.time.checkedAt).toBeNull();
    expect(next.details.find((row) => row.label === 'Bericht gelesen')?.value).toContain(
      report.basis.read_completed_at,
    );
    expect(next.details.find((row) => row.label === 'Bericht berechnet')?.value).toBe(
      report.basis.calculated_at,
    );
    expect(next.actions[0].destination.relationshipProof.snapshotToken).toBe(report.basis.id);
    expect(next.actions[0].destination.href).toContain(`report_basis=${report.basis.id}`);
    expect(next.actions[0].destination.href).not.toBe(first.actions[0].destination.href);
    expect(next.details.every((row) => row.proof?.snapshotToken === report.basis.id)).toBe(true);
  });

  it('changes identity for another real source/evidence version or financial filter context', () => {
    const { report, item, context, source, build } = setup();
    unresolvedItem(item);
    source('buy-august').currency_resolution = unknownResolution({
      reason: 'LISTING_HISTORY_INCOMPLETE',
      evidence_ids: ['evidence-v1'],
    });
    const first = build().id;
    source('buy-august').currency_resolution!.evidence_ids = ['evidence-v2'];
    const second = build().id;
    expect(second).not.toBe(first);
    report.filters.report_timezone = context.filters.report_timezone = 'America/New_York';
    expect(build().id).not.toBe(second);
  });

  it('does not mistake an unresolved SELL provenance prefix for the exact missing BUY cause', () => {
    const { item, source, build } = setup();
    unresolvedItem(item);
    source('buy-august').currency_resolution = unknownResolution();
    source(item.execution_id).currency_resolution = unknownResolution({
      source_execution_ids: ['buy-august', 'buy-september'],
      confirmation_ids: ['currency-buy-september'],
    });
    const first = build();
    source('buy-september').currency_resolution!.confirmation_ids = ['replacement-confirmation'];
    source(item.execution_id).currency_resolution!.confirmation_ids = ['replacement-confirmation'];
    const next = build();
    expect(next.id).toBe(first.id);
    expect(detailText(next)).toContain('replacement-confirmation');
    expect(detailText(next)).toContain('Kauf 1 · Währungsherkunft: unbekannt');
  });

  it.each(['Synthetischer Optionsschein', null])(
    'names the affected product and execution time without a UUID (%s)',
    (productName) => {
      const { item, build } = setup();
      item.product_name = productName;
      const notice = build();
      expect(notice.cause.explanation).toContain(productName ?? 'Produktname nicht verfügbar');
      expect(notice.cause.explanation).toContain('Verkauf');
      expect(notice.cause.explanation).toContain('12.09.2026');
      expect(notice.cause.explanation).toContain('Europe/Berlin');
      expect(notice.cause.explanation).not.toContain(item.execution_id);
      expect(notice.cause.explanation).not.toContain(item.trade_id);
    },
  );
});
