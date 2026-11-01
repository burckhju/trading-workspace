import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { realizedGrossReport, reportSource } from '../../../test/realizedGrossFixtures';
import type { RealizedReportContext } from '../services/performanceReportContext';
import type { RealizedGrossReport, RealizedGrossSource } from '../types/api';
import { RealizedGrossReportView } from './RealizedGrossReportView';
import { RealizedGrossSources } from './RealizedGrossSources';
import { ReportSourceEntry } from './ReportSourceEntry';

const tradeId = '6b39ab21-3c1d-48cd-a853-43c3828d11d1';
const productId = '1e49ef64-7878-4bf8-933f-f957e1627ffd';
const executionIds: Record<string, string> = {
  'buy-august': '70000000-0000-4000-8000-000000000001',
  'sell-august': '70000000-0000-4000-8000-000000000002',
  'sell-september-1': '70000000-0000-4000-8000-000000000003',
  'buy-september': '70000000-0000-4000-8000-000000000004',
  'sell-september-2': '70000000-0000-4000-8000-000000000005',
};
const buyId = executionIds['buy-august'];
const saleId = executionIds['sell-september-2'];
const title = 'Währungsherkunft dieses Beitrags';
const warningTitle = `${title} ungeklärt`;
const actionName = 'Buchungen und Währungsbestätigungen im Trade prüfen';
const unknown = {
  currency_code: null,
  source: 'UNKNOWN' as const,
  source_execution_ids: [],
  confirmation_ids: [],
  reason: 'NO_HISTORICAL_EVIDENCE',
};

// Preserve the existing server-shaped monetary examples; only give their
// identities realistic UUIDs so technical labels cannot accidentally pass.
function knownReport(): RealizedGrossReport {
  const report = realizedGrossReport();
  const execution = (id: string) => executionIds[id] ?? id;
  report.items = report.items.map((item) => ({
    ...item,
    trade_id: tradeId,
    product_id: productId,
    execution_id: execution(item.execution_id),
    cost_basis_execution_ids: item.cost_basis_execution_ids.map(execution),
    currency_confirmation_ids: item.currency_confirmation_ids.map(
      (id) => `currency-${execution(id.slice('currency-'.length))}`,
    ),
  }));
  report.sources = report.sources.map((source) => {
    const id = execution(source.execution_id);
    const confirmation = {
      ...source.currency_confirmation!,
      id: `currency-${id}`,
      execution_id: id,
      trade_id: tradeId,
      request_id: `request-${id}`,
    };
    return {
      ...source,
      trade_id: tradeId,
      product_id: productId,
      execution_id: id,
      currency_confirmation: confirmation,
      currency_history: [confirmation],
      currency_resolution: {
        currency_code: 'EUR',
        source: 'USER_CONFIRMED',
        source_execution_ids: [id],
        confirmation_ids: [confirmation.id],
      },
    };
  });
  return report;
}

function source(report: RealizedGrossReport, id: string): RealizedGrossSource {
  return report.sources.find((entry) => entry.execution_id === id)!;
}

function unknownBuyReport() {
  const report = knownReport();
  Object.assign(source(report, buyId), {
    currency_confirmation: null,
    currency_history: [],
    currency_resolution: { ...unknown },
  });
  report.items = report.items.map((item) => ({
    ...item,
    status: 'NOT_COMPUTABLE',
    reasons: ['CURRENCY_UNKNOWN'],
    currency_code: null,
    average_cost_per_unit: null,
    cost_basis_before: null,
    cost_basis_after: null,
    realized_gross_pnl_delta: null,
    realized_gross_pnl_delta_display: null,
    currency_confirmation_ids: item.currency_confirmation_ids.filter(
      (id) => id !== `currency-${buyId}`,
    ),
  }));
  report.summary = {
    status: 'NOT_COMPUTABLE',
    total: null,
    total_display: null,
    subtotal: null,
    subtotal_display: null,
    rounding_difference: null,
    rounding_difference_display: null,
  };
  report.counts = { ...report.counts, usable: 0, unresolved: 2 };
  return report;
}

function automaticReport() {
  const report = knownReport();
  Object.assign(source(report, buyId), {
    currency_confirmation: null,
    currency_history: [],
    currency_resolution: {
      currency_code: 'EUR',
      source: 'HISTORICAL_LISTINGS',
      source_execution_ids: [],
      confirmation_ids: [],
      evidence_ids: ['archive-v2'],
      resolver_version: 'historical-currency-v1',
      evidence: [
        {
          id: 'archive-v2',
          kind: 'HISTORICAL_LISTINGS',
          source_reference: 'Synthetischer Handelskalender, Originalbeleg Seite 7',
          recorded_at: '2026-10-17T10:00:00Z',
          valid_from: '2026-08-01T00:00:00+02:00',
          valid_to: '2026-09-01T00:00:00+02:00',
          source_fingerprint: 'synthetic-source-fingerprint',
          verification: 'USER_VERIFIED_SOURCE',
          supersedes_evidence_id: 'archive-v1',
        },
      ],
    },
  });
  report.items = report.items.map((item) => ({
    ...item,
    currency_confirmation_ids: item.currency_confirmation_ids.filter(
      (id) => id !== `currency-${buyId}`,
    ),
  }));
  return report;
}

function contextFor(report: RealizedGrossReport): RealizedReportContext {
  return { filters: { ...report.filters }, view: 'all', page: 0, basis: report.basis.id };
}

function content(report: RealizedGrossReport, selectedExecutionId = saleId) {
  return (
    <MemoryRouter>
      <RealizedGrossSources
        item={report.items.find((item) => item.execution_id === selectedExecutionId)!}
        report={report}
        context={contextFor(report)}
      />
    </MemoryRouter>
  );
}

function openDetails(container: HTMLElement) {
  for (const details of container.querySelectorAll('details')) {
    const summary = details.querySelector('summary');
    if (!details.open && summary) fireEvent.click(summary);
  }
}

function primaryText(card: HTMLElement) {
  const copy = card.cloneNode(true) as HTMLElement;
  copy.querySelectorAll('details').forEach((details) => details.remove());
  return copy.textContent ?? '';
}

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Unexpected notice request'));
});

afterEach(() => {
  expect(globalThis.fetch).not.toHaveBeenCalled();
  vi.restoreAllMocks();
});

it('explains an unknown BUY without losing the confirmed SELL or making UUIDs primary', () => {
  const report = unknownBuyReport();
  const before = JSON.stringify(report);
  render(content(report));
  const card = screen.getByRole('region', { name: warningTitle });
  expect(within(card).getByText('Warnung', { exact: true })).toBeVisible();
  expect(card).toHaveTextContent(
    'Der Bericht kann den Bruttobeitrag dieses Verkaufs derzeit nicht berechnen.',
  );
  expect(primaryText(card)).not.toMatch(
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i,
  );
  fireEvent.click(within(card).getByText('Ursache und Quellen', { exact: true }));
  expect(card).toHaveTextContent('Kauf 1');
  expect(card).toHaveTextContent(buyId);
  const sale = screen.getByRole('listitem', { name: `Buchungsquelle ${saleId}` });
  openDetails(sale);
  expect(within(sale).getByText(/Währung EUR ausdrücklich vom Nutzer bestätigt/)).toBeVisible();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(JSON.stringify(report)).toBe(before);
});

it('keeps automatic historical evidence, validity and resolver version inspectable without requiring confirmation', () => {
  render(content(automaticReport()));
  const card = screen.getByRole('region', { name: title });
  expect(within(card).getByText('Hinweis', { exact: true })).toBeVisible();
  expect(within(card).queryByText('Warnung', { exact: true })).not.toBeInTheDocument();
  const buy = screen.getByRole('listitem', { name: `Buchungsquelle ${buyId}` });
  openDetails(buy);
  expect(
    within(buy).getByText(/Synthetischer Handelskalender, Originalbeleg Seite 7/),
  ).toBeVisible();
  expect(within(buy).getByText('Quellenversion archive-v2')).toBeVisible();
  expect(within(buy).getByText('Zuordnungsregel historical-currency-v1')).toBeVisible();
  expect(within(buy).getByText('Gültig ab 2026-08-01T00:00:00+02:00')).toBeVisible();
  expect(
    within(buy).getByText('Gültig bis ausschließlich 2026-09-01T00:00:00+02:00'),
  ).toBeVisible();
  expect(within(buy).queryByText(/ausdrücklich vom Nutzer bestätigt/)).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.getAllByRole('link', { name: actionName })).toHaveLength(1);
});

it.each(['missing', 'unknown'] as const)(
  'keeps a %s resolver currency unknown beside the price despite an existing confirmation',
  (resolutionState) => {
    const report = knownReport();
    const buy = source(report, buyId);
    if (resolutionState === 'missing') delete buy.currency_resolution;
    else buy.currency_resolution = { ...unknown };
    render(content(report));
    const entry = screen.getByRole('listitem', { name: `Buchungsquelle ${buyId}` });
    expect(within(entry).getByText(/Gespeicherter Stückpreis:/)).toHaveTextContent(
      `Gespeicherter Stückpreis: ${buy.price_per_unit} · Ausführungswährung unbekannt`,
    );
    openDetails(entry);
    expect(within(entry).getByText('Währung EUR ausdrücklich vom Nutzer bestätigt.')).toBeVisible();
    expect(entry).toHaveTextContent(
      resolutionState === 'missing'
        ? 'In dieser Antwort ist keine Währungsauflösung enthalten.'
        : 'Ausführungswährung: unbekannt',
    );
  },
);

it.each(['missing', 'unknown'] as const)(
  'preserves the existing source consumer default for a %s resolution',
  (resolutionState) => {
    const report = knownReport();
    const buy = source(report, buyId);
    if (resolutionState === 'missing') delete buy.currency_resolution;
    else buy.currency_resolution = { ...unknown };
    render(
      <ul>
        <ReportSourceEntry source={buy} timezone={report.filters.report_timezone} />
      </ul>,
    );
    const entry = screen.getByRole('listitem', { name: `Buchungsquelle ${buyId}` });
    expect(within(entry).getByText(/Gespeicherter Stückpreis:/)).toHaveTextContent(
      `Gespeicherter Stückpreis: ${buy.price_per_unit} EUR`,
    );
    expect(within(entry).getByText('Währung EUR ausdrücklich vom Nutzer bestätigt.')).toBeVisible();
  },
);

it.each(['trade_id', 'execution_id'] as const)(
  'does not assign foreign %s confirmation details or history to the selected source',
  (scopeField) => {
    const report = knownReport();
    const buy = source(report, buyId);
    const original = buy.currency_confirmation!;
    const ownHistory = { ...original, note: 'Passende gespeicherte Bestätigung' };
    buy.currency_confirmation = {
      ...original,
      id: 'foreign-current-confirmation',
      [scopeField]: 'foreign-object',
      confirmed_by: 'foreign-confirming-actor',
      note: 'Fremde aktuelle Bestätigungsdetails',
    };
    buy.currency_history = [
      ownHistory,
      {
        ...original,
        id: 'foreign-historical-confirmation',
        [scopeField]: 'foreign-object',
        confirmed_by: 'foreign-history-actor',
        note: 'Fremde historische Bestätigungsdetails',
      },
    ];
    render(content(report));
    const entry = screen.getByRole('listitem', { name: `Buchungsquelle ${buyId}` });
    openDetails(entry);
    expect(entry).not.toHaveTextContent('foreign-');
    expect(entry).not.toHaveTextContent('Fremde');
    expect(within(entry).getByText('Währungshistorie (1)')).toBeVisible();
    expect(within(entry).getByText(ownHistory.note)).toBeVisible();
    expect(entry).toHaveTextContent('EUR · gespeichert · ausdrücklich bestätigt');
    // Resolver IDs remain inspectable without borrowing a mismatched detail object.
    expect(within(entry).getAllByText(`Bestätigung ${original.id}`)).toHaveLength(2);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  },
);

it('keeps an EXCLUDED row with an unknown currency separate from the complete selected total', () => {
  const report = knownReport();
  const excludedId = '70000000-0000-4000-8000-000000000006';
  report.items.push({
    ...report.items[1],
    execution_id: excludedId,
    executed_at: '2026-10-02T10:00:00Z',
    period_status: 'OUTSIDE_PERIOD',
    status: 'EXCLUDED',
    reasons: ['OUTSIDE_PERIOD', 'CURRENCY_UNKNOWN'],
    currency_code: null,
    average_cost_per_unit: null,
    cost_basis_before: null,
    cost_basis_after: null,
    realized_gross_pnl_delta: null,
    realized_gross_pnl_delta_display: null,
    currency_confirmation_ids: [],
    cost_basis_execution_ids: report.sources.map((entry) => entry.execution_id),
  });
  report.sources.push(
    reportSource(excludedId, {
      trade_id: tradeId,
      product_id: productId,
      side: 'SELL',
      executed_at: '2026-10-02T10:00:00Z',
      currency_confirmation: null,
      currency_history: [],
      currency_resolution: { ...unknown },
    }),
  );
  report.counts = { ...report.counts, examined: 3, outside_period: 1, excluded: 1 };
  render(
    <MemoryRouter>
      <RealizedGrossReportView
        report={report}
        context={{ ...contextFor(report), view: 'excluded' }}
        onContext={vi.fn()}
      />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Quellen und Berechnung' }));
  const card = screen.getByRole('region', { name: title });
  expect(within(card).getByText('Hinweis', { exact: true })).toBeVisible();
  expect(card).toHaveTextContent(
    'Dieser Verkauf ist von der gewählten Berichtssumme ausgeschlossen.',
  );
  expect(card).not.toHaveTextContent('Der Bericht kann den Bruttobeitrag');
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('10,00 EUR');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('does not turn earlier SELL, replaced BUY or later BUY provenance into a new current cause', async () => {
  const report = knownReport();
  Object.assign(source(report, executionIds['sell-august']), {
    currency_confirmation: null,
    currency_history: [],
    currency_resolution: { ...unknown },
  });
  report.sources.push(
    reportSource('historical-buy', {
      trade_id: tradeId,
      product_id: productId,
      is_effective: false,
      superseded_by_execution_id: buyId,
      currency_confirmation: null,
      currency_history: [],
      currency_resolution: { ...unknown },
    }),
    reportSource('later-buy', {
      trade_id: tradeId,
      product_id: productId,
      executed_at: '2026-10-15T10:00:00Z',
      currency_confirmation: null,
      currency_history: [],
      currency_resolution: { ...unknown },
    }),
  );
  render(content(report));
  const card = screen.getByRole('region', { name: title });
  expect(within(card).getByText('Hinweis', { exact: true })).toBeVisible();
  fireEvent.click(screen.getByText(/Gesamte gelesene Trade-Historie/));
  await screen.findByRole('list', { name: 'Gesamte Trade-Historie' });
  expect(screen.getAllByRole('region', { name: title })).toHaveLength(1);
  expect(screen.queryByRole('region', { name: warningTitle })).not.toBeInTheDocument();
  expect(card).not.toHaveTextContent('Der Bericht kann den Bruttobeitrag');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('opens existing details and full history without another card, alarm, action or request', async () => {
  render(content(unknownBuyReport()));
  const card = screen.getByRole('region', { name: warningTitle });
  const summary = within(card).getByText('Ursache und Quellen', { exact: true });
  expect(summary.tagName).toBe('SUMMARY');
  fireEvent.click(summary);
  expect(summary.closest('details')).toHaveAttribute('open');
  fireEvent.click(summary);
  expect(summary.closest('details')).not.toHaveAttribute('open');
  fireEvent.click(screen.getByText(/Gesamte gelesene Trade-Historie/));
  await screen.findByRole('list', { name: 'Gesamte Trade-Historie' });
  expect(screen.getAllByRole('region', { name: warningTitle })).toHaveLength(1);
  expect(screen.getAllByRole('link', { name: actionName })).toHaveLength(1);
  expect(card.querySelectorAll('[role="alert"], [role="status"], [aria-live]')).toHaveLength(0);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(
    screen.queryByText('Die Ausführungswährung ist noch nicht vollständig belegt.'),
  ).not.toBeInTheDocument();
});

it('retains a stable cause while a fresh basis replaces the exact booking link and reporting zone', () => {
  const report = unknownBuyReport();
  const view = render(content(report));
  const identity = screen
    .getByRole('region', { name: warningTitle })
    .getAttribute('data-notice-id');
  expect(identity).toBeTruthy();
  const next = unknownBuyReport();
  next.basis = {
    ...next.basis,
    id: 'b'.repeat(64),
    read_completed_at: '2026-10-17T12:00:01Z',
    calculated_at: '2026-10-17T12:00:01Z',
  };
  view.rerender(content(next));
  expect(screen.getByRole('region', { name: warningTitle })).toHaveAttribute(
    'data-notice-id',
    identity,
  );
  next.filters = { ...next.filters, report_timezone: 'Etc/UTC' };
  next.interval_start_at = '2026-09-01T00:00:00Z';
  next.interval_end_at = '2026-10-01T00:00:00Z';
  view.rerender(content(next));
  const link = screen.getByRole('link', { name: actionName });
  expect(link.tagName).toBe('A');
  const url = new URL(link.getAttribute('href')!, 'https://workspace.test');
  expect(url.pathname).toBe('/trade-management');
  expect(url.hash).toBe('#execution-dates');
  expect(Object.fromEntries(url.searchParams)).toEqual({
    report_context: 'realized-gross',
    ...next.filters,
    report_view: 'all',
    report_page: '1',
    report_basis: next.basis.id,
    trade_id: tradeId,
  });
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('replaces source versions and references together instead of retaining old report evidence', () => {
  const report = automaticReport();
  const view = render(content(report));
  const next = automaticReport();
  next.basis.id = 'c'.repeat(64);
  const resolution = source(next, buyId).currency_resolution!;
  resolution.evidence_ids = ['archive-v3'];
  resolution.resolver_version = 'historical-currency-v2';
  resolution.evidence = [
    {
      ...resolution.evidence![0],
      id: 'archive-v3',
      source_reference: 'Synthetischer korrigierter Originalbeleg Seite 9',
      supersedes_evidence_id: 'archive-v2',
    },
  ];
  view.rerender(content(next));
  const buy = screen.getByRole('listitem', { name: `Buchungsquelle ${buyId}` });
  openDetails(buy);
  expect(within(buy).getByText(/Synthetischer korrigierter Originalbeleg Seite 9/)).toBeVisible();
  expect(within(buy).getByText('Quellenversion archive-v3')).toBeVisible();
  expect(within(buy).getByText('Zuordnungsregel historical-currency-v2')).toBeVisible();
  expect(
    screen.queryByText(/Synthetischer Handelskalender, Originalbeleg Seite 7/),
  ).not.toBeInTheDocument();
  expect(screen.queryByText('Quellenversion archive-v2')).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('replaces the object, title, reason, source and complete trade return link together', () => {
  const report = unknownBuyReport();
  const previousReference = 'Vorheriger Ausführungsbeleg ohne Währungsangabe';
  source(report, buyId).currency_resolution = {
    ...unknown,
    evidence_ids: ['previous-document-version'],
    evidence: [
      {
        id: 'previous-document-version',
        kind: 'EXECUTION_DOCUMENT',
        source_reference: previousReference,
        recorded_at: '2026-10-17T09:00:00Z',
      },
    ],
  };
  const view = render(content(report));
  const previousCard = screen.getByRole('region', { name: warningTitle });
  openDetails(previousCard);
  expect(previousCard).toHaveTextContent('NO_HISTORICAL_EVIDENCE');
  expect(previousCard).toHaveTextContent(previousReference);
  const previousLink = screen.getByRole('link', { name: actionName }).getAttribute('href');

  const next = automaticReport();
  const nextTradeId = '6b39ab21-3c1d-48cd-a853-43c3828d11d2';
  const nextProductId = '1e49ef64-7878-4bf8-933f-f957e1627ffe';
  const nextId = (id: string) => id.replace('70000000-', '80000000-');
  const nextConfirmation = (entry: NonNullable<RealizedGrossSource['currency_confirmation']>) => ({
    ...entry,
    id: nextId(entry.id),
    trade_id: nextTradeId,
    execution_id: nextId(entry.execution_id),
  });
  next.basis.id = 'd'.repeat(64);
  next.filters.report_timezone = 'Etc/UTC';
  next.interval_start_at = '2026-09-01T00:00:00Z';
  next.interval_end_at = '2026-10-01T00:00:00Z';
  next.items = next.items.map((item) => ({
    ...item,
    execution_id: nextId(item.execution_id),
    trade_id: nextTradeId,
    product_id: nextProductId,
    product_name: 'Nachfolgendes Produkt',
    cost_basis_execution_ids: item.cost_basis_execution_ids.map(nextId),
    currency_confirmation_ids: item.currency_confirmation_ids.map(nextId),
  }));
  next.sources = next.sources.map((entry) => ({
    ...entry,
    execution_id: nextId(entry.execution_id),
    trade_id: nextTradeId,
    product_id: nextProductId,
    currency_confirmation: entry.currency_confirmation
      ? nextConfirmation(entry.currency_confirmation)
      : null,
    currency_history: entry.currency_history.map(nextConfirmation),
    currency_resolution: {
      ...entry.currency_resolution!,
      source_execution_ids: entry.currency_resolution!.source_execution_ids.map(nextId),
      confirmation_ids: entry.currency_resolution!.confirmation_ids.map(nextId),
    },
  }));
  view.rerender(content(next, nextId(saleId)));
  const nextCard = screen.getByRole('region', { name: title });
  openDetails(nextCard);
  expect(nextCard).toHaveTextContent('Nachfolgendes Produkt');
  expect(nextCard).toHaveTextContent('HISTORICAL_LISTINGS');
  expect(nextCard).toHaveTextContent('Synthetischer Handelskalender, Originalbeleg Seite 7');
  expect(nextCard).toHaveTextContent('Etc/UTC');
  expect(screen.queryByRole('region', { name: warningTitle })).not.toBeInTheDocument();
  expect(view.container).not.toHaveTextContent('NO_HISTORICAL_EVIDENCE');
  expect(view.container).not.toHaveTextContent(previousReference);
  expect(view.container).not.toHaveTextContent(tradeId);
  expect(view.container).not.toHaveTextContent(buyId);
  const nextLink = screen.getByRole('link', { name: actionName }).getAttribute('href');
  expect(nextLink).not.toBe(previousLink);
  const url = new URL(nextLink!, 'https://workspace.test');
  expect(url.pathname).toBe('/trade-management');
  expect(url.hash).toBe('#execution-dates');
  expect(Object.fromEntries(url.searchParams)).toEqual({
    report_context: 'realized-gross',
    ...next.filters,
    report_view: 'all',
    report_page: '1',
    report_basis: next.basis.id,
    trade_id: nextTradeId,
  });
  expect(
    view.container.querySelectorAll('[role="alert"], [role="status"], [aria-live]'),
  ).toHaveLength(0);
});

it('keeps a missing prefix source explicit and quiet with its technical reference in details', async () => {
  const report = unknownBuyReport();
  report.sources = report.sources.filter((entry) => entry.execution_id !== buyId);
  render(content(report));
  const card = screen.getByRole('region', { name: warningTitle });
  openDetails(card);
  expect(card).toHaveTextContent(buyId);
  expect(primaryText(card)).not.toContain(buyId);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  fireEvent.click(screen.getByText(/Gesamte gelesene Trade-Historie/));
  await waitFor(() =>
    expect(screen.getByRole('list', { name: 'Gesamte Trade-Historie' })).toBeVisible(),
  );
  expect(screen.getAllByRole('link', { name: actionName })).toHaveLength(1);
});

it('keeps a globally duplicated source ID unresolved across trade scopes without showing either payload', async () => {
  const report = unknownBuyReport();
  const foreignTradeId = '6b39ab21-3c1d-48cd-a853-43c3828d11d2';
  const foreignProductId = '1e49ef64-7878-4bf8-933f-f957e1627ffe';
  report.sources.push({
    ...source(report, buyId),
    trade_id: foreignTradeId,
    product_id: foreignProductId,
    recorded_by: 'foreign-scope-payload-must-not-appear',
  });
  render(content(report));
  const card = screen.getByRole('region', { name: warningTitle });
  openDetails(card);
  expect(card).toHaveTextContent(
    'Diese Buchungsquelle ist in der Berichtsantwort nicht eindeutig; ihre Währungsherkunft wird nicht zugeordnet.',
  );
  expect(card).toHaveTextContent(buyId);
  expect(primaryText(card)).not.toContain(buyId);
  const prefix = screen.getByRole('list', { name: 'Kostenbasispräfix und Verkauf' });
  expect(
    within(prefix).getByText(
      'Eine Buchungsquelle ist in dieser Antwort nicht eindeutig zugeordnet.',
    ),
  ).toBeVisible();
  expect(
    screen.queryByRole('listitem', { name: `Buchungsquelle ${buyId}` }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByText(/Gesamte gelesene Trade-Historie/));
  const history = await screen.findByRole('list', { name: 'Gesamte Trade-Historie' });
  expect(
    within(history).getByText(
      'Eine Buchungsquelle ist in dieser Antwort nicht eindeutig zugeordnet.',
    ),
  ).toBeVisible();
  expect(
    screen.queryByRole('listitem', { name: `Buchungsquelle ${buyId}` }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/foreign-scope-payload-must-not-appear/)).not.toBeInTheDocument();
  expect(screen.queryByText(new RegExp(foreignTradeId))).not.toBeInTheDocument();
  expect(screen.queryByText(new RegExp(foreignProductId))).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.getAllByRole('region', { name: warningTitle })).toHaveLength(1);
  expect(screen.getAllByRole('link', { name: actionName })).toHaveLength(1);
});
