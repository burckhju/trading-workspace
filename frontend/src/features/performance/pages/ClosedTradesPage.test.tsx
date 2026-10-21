import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';

import {
  closedTradeContribution,
  closedTradeFilters,
  closedTradeItem,
  closedTradeReport,
} from '../../../test/closedTradesFixtures';
import { reportSource } from '../../../test/realizedGrossFixtures';
import { performanceApiClient } from '../services/client';
import { closedTradeSourceLink } from '../services/closedReportContext';
import type { ClosedTradeGroup, ClosedTradeReport } from '../types/api';
import { ClosedTradesPage } from './ClosedTradesPage';

vi.mock('../services/client', () => ({
  performanceApiClient: { closedTrades: vi.fn(), realizedGross: vi.fn() },
}));
const api = vi.mocked(performanceApiClient);

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function renderPage() {
  return render(
    <MemoryRouter>
      <ClosedTradesPage />
    </MemoryRouter>,
  );
}
function chooseOctober() {
  fireEvent.change(screen.getByLabelText('Von (einschließlich)'), {
    target: { value: '2026-10-01' },
  });
  fireEvent.change(screen.getByLabelText('Bis (einschließlich)'), {
    target: { value: '2026-10-31' },
  });
  fireEvent.change(screen.getByLabelText('Berichtswährung'), { target: { value: 'EUR' } });
}
function read() {
  fireEvent.click(screen.getByRole('button', { name: 'Bericht lesen' }));
}
function openSources(tradeId = 'trade-1') {
  fireEvent.click(
    within(screen.getByRole('article', { name: `Trade ${tradeId}` })).getByRole('button', {
      name: 'Quellen und Gesamtverlauf',
    }),
  );
  return within(screen.getByRole('region', { name: `Herkunft Trade ${tradeId}` }));
}
const nullSummary = {
  status: 'NOT_COMPUTABLE' as const,
  total: null,
  total_display: null,
  subtotal: null,
  subtotal_display: null,
  rounding_difference: null,
  rounding_difference_display: null,
};

beforeEach(() => {
  vi.resetAllMocks();
  api.closedTrades.mockResolvedValue(closedTradeReport());
});

it('reads an explicitly selected currency and shows one full trade result with all earlier SELL contributions', async () => {
  renderPage();
  expect(api.closedTrades).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Berichtswährung')).toHaveValue('');
  expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveValue('Europe/Berlin');
  expect(
    screen.getByRole('heading', { name: 'Trades mit Vollabschluss im Zeitraum' }),
  ).toBeVisible();
  expect(screen.getByRole('link', { name: 'Verkäufe im Zeitraum ansehen' })).toHaveAttribute(
    'href',
    '/performance/realized-gross',
  );
  chooseOctober();
  read();
  expect(await screen.findByTestId('closed-trades-total')).toHaveTextContent('50,00 EUR');
  expect(api.closedTrades).toHaveBeenCalledExactlyOnceWith(
    closedTradeFilters,
    expect.any(AbortSignal),
  );
  expect(api.realizedGross).not.toHaveBeenCalled();
  expect(screen.getAllByRole('article')).toHaveLength(1);
  expect(screen.getByTestId('closed-trades-positive')).toHaveTextContent('1');
  expect(screen.getByTestId('closed-trades-negative')).toHaveTextContent('0');
  expect(screen.getByTestId('closed-trades-neutral')).toHaveTextContent('0');
  const detail = openSources();
  expect(detail.getByText('50.0000000000')).toBeVisible();
  expect(detail.getAllByText(/Verkauf außerhalb des Berichtszeitraums/)).toHaveLength(3);
  expect(
    within(detail.getByRole('listitem', { name: 'SELL-Beitrag sell-september-2' })).getByText(
      '-20,00 EUR',
    ),
  ).toBeVisible();
  expect(
    within(detail.getByRole('listitem', { name: 'SELL-Beitrag sell-october' })).getByText(
      '30,00 EUR',
    ),
  ).toBeVisible();
  for (const id of [
    'buy-august',
    'sell-august',
    'sell-september-1',
    'buy-september',
    'sell-september-2',
    'sell-october',
  ]) {
    expect(detail.getByRole('listitem', { name: `Buchungsquelle ${id}` })).toBeVisible();
  }
  const inherited = within(detail.getByRole('listitem', { name: 'Buchungsquelle sell-october' }));
  expect(
    inherited.getByText('Ausführungswährung: EUR · aus vorherigen Käufen übernommen'),
  ).toBeVisible();
  expect(inherited.queryByText(/ausdrücklich vom Nutzer bestätigt/)).not.toBeInTheDocument();
  expect(
    detail.getByRole('link', { name: 'Buchungen und Währungsbestätigungen im Trade prüfen' }),
  ).toHaveAttribute('href', '/trade-management?trade_id=trade-1#execution-dates');
  fireEvent.click(
    within(detail.getByRole('listitem', { name: 'SELL-Beitrag sell-october' })).getByText(
      'Präziser Einzelbeitrag und Kostenbasis',
    ),
  );
  expect(detail.getByText('Kostenrest vor Abschlussrücksetzung')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Quellen schließen' }));
  expect(screen.queryByRole('region', { name: 'Herkunft Trade trade-1' })).not.toBeInTheDocument();
  expect(api.closedTrades).toHaveBeenCalledOnce();
});

it('keeps identical product names as distinct trade IDs and never turns known pieces of an unresolved trade into a subtotal or class', async () => {
  const report = closedTradeReport();
  const unknown = closedTradeItem('trade-unknown', {
    group: 'MONETARY_UNRESOLVED',
    status: 'NOT_COMPUTABLE',
    reasons: ['CURRENCY_MIXED'],
    realized_gross_pnl: null,
    realized_gross_pnl_display: null,
    currency_code: null,
    classification: null,
    effective_execution_ids: [],
    execution_ids: [],
    sell_contributions: [
      closedTradeContribution('known-piece', {
        realized_gross_pnl_delta: '5',
        realized_gross_pnl_delta_display: '5.00',
      }),
    ],
  });
  report.items.push(unknown);
  report.summary = {
    ...nullSummary,
    status: 'PARTIAL',
    subtotal: '50.0000000000',
    subtotal_display: '50.00',
    rounding_difference: '0',
    rounding_difference_display: '0.00',
  };
  report.counts = {
    ...report.counts,
    examined: 2,
    in_period: 2,
    monetary_unresolved: 1,
    unresolved: 1,
  };
  api.closedTrades.mockResolvedValue(report);
  renderPage();
  chooseOctober();
  read();
  expect(await screen.findByTestId('closed-trades-total')).toHaveTextContent('Nicht berechenbar');
  expect(screen.getByTestId('closed-trades-subtotal')).toHaveTextContent('50,00 EUR');
  expect(screen.getAllByRole('heading', { name: 'Synthetischer Optionsschein' })).toHaveLength(2);
  const unknownRow = within(screen.getByRole('article', { name: 'Trade trade-unknown' }));
  expect(unknownRow.getByText('Keine Klassifikation')).toBeVisible();
  expect(unknownRow.getByRole('link', { name: 'Trade trade-unknown prüfen' })).toHaveAttribute(
    'href',
    closedTradeSourceLink('trade-unknown', {
      filters: closedTradeFilters,
      view: 'candidates',
      page: 0,
      basis: report.basis.id,
    }),
  );
  const detail = openSources('trade-unknown');
  expect(detail.getByText(/keinen Trade-Teilbetrag/)).toBeVisible();
  expect(detail.getByText('5,00 EUR')).toBeVisible();
  fireEvent.change(screen.getByLabelText('Zeilen anzeigen'), { target: { value: 'unresolved' } });
  expect(screen.getAllByRole('article')).toHaveLength(1);
  expect(screen.getByTestId('closed-trades-subtotal')).toHaveTextContent('50,00 EUR');
  expect(screen.getByTestId('closed-trades-positive')).toHaveTextContent('1');
  expect(api.closedTrades).toHaveBeenCalledOnce();
});

it.each([
  ['EMPTY', 'Keine abgeschlossenen Trades in dieser Auswahl', '0,00 EUR'],
  ['COMPLETE', 'Vollständig auswertbare Abschlussauswahl', '0,00 EUR'],
  ['NOT_COMPUTABLE', 'Abschlussauswahl nicht berechenbar', 'Nicht berechenbar'],
] as const)(
  'distinguishes %s from unknown money and a measured exact zero',
  async (status, heading, amount) => {
    const report = closedTradeReport();
    const neutral = closedTradeItem('neutral', {
      realized_gross_pnl: '0',
      realized_gross_pnl_display: '0.00',
      classification: 'NEUTRAL',
    });
    const unknown = closedTradeItem('unknown', {
      group: 'MONETARY_UNRESOLVED',
      status: 'NOT_COMPUTABLE',
      reasons: ['CURRENCY_UNKNOWN'],
      realized_gross_pnl: null,
      realized_gross_pnl_display: null,
      classification: null,
    });
    report.summary = {
      ...nullSummary,
      status,
      total: status === 'NOT_COMPUTABLE' ? null : '0',
      total_display: status === 'NOT_COMPUTABLE' ? null : '0.00',
    };
    report.items = status === 'EMPTY' ? [] : [status === 'COMPLETE' ? neutral : unknown];
    report.counts = {
      examined: status === 'EMPTY' ? 0 : 1,
      cancelled: 0,
      history_unresolved: 0,
      open: 0,
      outside_period: 0,
      other_currency: 0,
      period_unresolved: 0,
      monetary_unresolved: status === 'NOT_COMPUTABLE' ? 1 : 0,
      qualified: status === 'COMPLETE' ? 1 : 0,
      in_period: status === 'EMPTY' ? 0 : 1,
      unresolved: status === 'NOT_COMPUTABLE' ? 1 : 0,
      positive: 0,
      negative: 0,
      neutral: status === 'COMPLETE' ? 1 : 0,
    };
    api.closedTrades.mockResolvedValue(report);
    renderPage();
    chooseOctober();
    read();
    expect(await screen.findByRole('heading', { name: heading })).toBeVisible();
    expect(screen.getByTestId('closed-trades-total')).toHaveTextContent(amount);
    expect(screen.queryByTestId('closed-trades-subtotal')).not.toBeInTheDocument();
    expect(screen.getByTestId('closed-trades-neutral')).toHaveTextContent(
      status === 'COMPLETE' ? '1' : '0',
    );
    if (status === 'COMPLETE') expect(screen.getByText('Neutral · exakt null')).toBeVisible();
    if (status === 'NOT_COMPUTABLE')
      expect(
        screen.getByText(/weder einen Nullbetrag noch eine neutrale Klassifikation/),
      ).toBeVisible();
  },
);

it('preserves the server sign for rounded zero and all exact decimal digits without client arithmetic', async () => {
  const report = closedTradeReport();
  report.items = [
    closedTradeItem('tiny-positive', {
      realized_gross_pnl: '0.004',
      realized_gross_pnl_display: '0.00',
      classification: 'POSITIVE',
      effective_execution_ids: [],
    }),
    closedTradeItem('tiny-negative', {
      realized_gross_pnl: '-0.004',
      realized_gross_pnl_display: '-0.00',
      classification: 'NEGATIVE',
      effective_execution_ids: [],
    }),
    closedTradeItem('large', {
      realized_gross_pnl: '9007199254740993.0000000001',
      realized_gross_pnl_display: '9007199254740993.00',
      classification: 'POSITIVE',
      effective_execution_ids: [],
    }),
  ];
  report.counts = {
    ...report.counts,
    examined: 3,
    in_period: 3,
    qualified: 3,
    positive: 2,
    negative: 1,
  };
  report.summary = {
    ...report.summary,
    total: '9007199254740993.0000000001',
    total_display: '9007199254740993.00',
  };
  api.closedTrades.mockResolvedValue(report);
  renderPage();
  chooseOctober();
  read();
  expect(await screen.findByTestId('closed-trades-total')).toHaveTextContent(
    '9007199254740993,00 EUR',
  );
  expect(
    within(screen.getByRole('article', { name: 'Trade tiny-positive' })).getByText('Positiv'),
  ).toBeVisible();
  expect(
    within(screen.getByRole('article', { name: 'Trade tiny-negative' })).getByText('Negativ'),
  ).toBeVisible();
  expect(openSources('tiny-negative').getByText('-0.004')).toBeVisible();
  expect(screen.getByText(/Neutral bedeutet exakt null/)).toBeVisible();
  fireEvent.click(screen.getByText('Alle acht Fallgruppen, präzise Summen und Rundung'));
  expect(screen.getByText('9007199254740993.0000000001')).toBeVisible();
});

it('pages and filters trade IDs locally without changing report-wide money, counts, or source basis', async () => {
  const report = closedTradeReport();
  report.items = Array.from({ length: 21 }, (_, index) =>
    closedTradeItem(`trade-${index}`, { effective_execution_ids: [] }),
  );
  report.counts = { ...report.counts, examined: 21, in_period: 21, qualified: 21, positive: 21 };
  report.summary = { ...report.summary, total: '1050', total_display: '1050.00' };
  api.closedTrades.mockResolvedValue(report);
  renderPage();
  chooseOctober();
  read();
  expect(await screen.findByTestId('closed-trades-total')).toHaveTextContent('1050,00 EUR');
  expect(screen.getAllByRole('article')).toHaveLength(20);
  openSources('trade-0');
  fireEvent.click(screen.getByRole('button', { name: 'Nächste Seite' }));
  expect(screen.getAllByRole('article')).toHaveLength(1);
  expect(screen.getByRole('article', { name: 'Trade trade-20' })).toBeVisible();
  expect(screen.queryByRole('region', { name: 'Herkunft Trade trade-0' })).not.toBeInTheDocument();
  expect(screen.getByTestId('closed-trades-positive')).toHaveTextContent('21');
  expect(screen.getByTestId('closed-trades-total')).toHaveTextContent('1050,00 EUR');
  fireEvent.click(screen.getByRole('button', { name: 'Vorherige Seite' }));
  fireEvent.change(screen.getByLabelText('Zeilen anzeigen'), { target: { value: 'qualified' } });
  expect(screen.getAllByRole('article')).toHaveLength(20);
  fireEvent.change(screen.getByLabelText('Zeilen anzeigen'), { target: { value: 'unresolved' } });
  expect(screen.queryAllByRole('article')).toHaveLength(0);
  expect(screen.getByTestId('closed-trades-total')).toHaveTextContent('1050,00 EUR');
  expect(api.closedTrades).toHaveBeenCalledOnce();
});

it('shows all eight disjoint groups while keeping exclusions outside result and sign counts', async () => {
  const groups: ClosedTradeGroup[] = [
    'CANCELLED',
    'HISTORY_UNRESOLVED',
    'OPEN',
    'OUTSIDE_PERIOD',
    'OTHER_CURRENCY',
    'PERIOD_UNRESOLVED',
    'MONETARY_UNRESOLVED',
    'QUALIFIED',
  ];
  const report = closedTradeReport();
  report.items = groups.map((group, index) =>
    closedTradeItem(`group-${index}`, {
      group,
      status:
        group === 'QUALIFIED'
          ? 'USABLE'
          : group.endsWith('UNRESOLVED')
            ? 'NOT_COMPUTABLE'
            : 'EXCLUDED',
      classification: group === 'QUALIFIED' ? 'POSITIVE' : null,
      closing_time: ['CANCELLED', 'HISTORY_UNRESOLVED', 'OPEN'].includes(group)
        ? null
        : closedTradeItem().closing_time,
      reasons: group === 'OPEN' ? ['TRADE_OPEN'] : [],
      currency_code: group === 'OTHER_CURRENCY' ? 'USD' : 'EUR',
      effective_execution_ids: [],
    }),
  );
  report.counts = {
    examined: 8,
    cancelled: 1,
    history_unresolved: 1,
    open: 1,
    outside_period: 1,
    other_currency: 1,
    period_unresolved: 1,
    monetary_unresolved: 1,
    qualified: 1,
    in_period: 2,
    unresolved: 3,
    positive: 1,
    negative: 0,
    neutral: 0,
  };
  report.summary = { ...nullSummary, status: 'PARTIAL', subtotal: '50', subtotal_display: '50.00' };
  api.closedTrades.mockResolvedValue(report);
  renderPage();
  chooseOctober();
  read();
  await screen.findByTestId('closed-trades-total');
  expect(screen.getAllByRole('article')).toHaveLength(4);
  fireEvent.click(screen.getByText('Alle acht Fallgruppen, präzise Summen und Rundung'));
  expect(
    screen.getByRole('table', { name: 'Disjunkte Fallgruppen der untersuchten Trades' }),
  ).toBeVisible();
  expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(9);
  fireEvent.change(screen.getByLabelText('Zeilen anzeigen'), { target: { value: 'excluded' } });
  expect(screen.getAllByRole('article')).toHaveLength(4);
  expect(screen.getAllByText('Nicht in der Summe')).toHaveLength(4);
  expect(screen.getByText('Storno ist kein wirtschaftlicher Abschluss')).toBeVisible();
  expect(screen.getByText('Noch nicht abgeschlossen')).toBeVisible();
  fireEvent.change(screen.getByLabelText('Zeilen anzeigen'), { target: { value: 'all' } });
  expect(screen.getAllByRole('article')).toHaveLength(8);
  expect(screen.getByTestId('closed-trades-positive')).toHaveTextContent('1');
});

it('keeps a date-only closing date and its ambiguous period visible without inventing an execution time', async () => {
  const time = {
    time_precision: 'DATE_ONLY' as const,
    executed_at: null,
    executed_on: '2026-10-01',
    execution_timezone: 'Asia/Tokyo',
    possible_start_at: '2026-09-30T15:00:00Z',
    possible_end_at: '2026-10-01T15:00:00Z',
    recorded_at: '2026-10-17T09:00:00Z',
  };
  const report = closedTradeReport({
    items: [
      closedTradeItem('ambiguous', {
        group: 'PERIOD_UNRESOLVED',
        status: 'NOT_COMPUTABLE',
        reasons: ['PERIOD_AMBIGUOUS'],
        closing_time: time,
        realized_gross_pnl: null,
        realized_gross_pnl_display: null,
        classification: null,
        effective_execution_ids: ['ambiguous-close'],
        sell_contributions: [
          closedTradeContribution('ambiguous-close', {
            ...time,
            period_status: 'PERIOD_AMBIGUOUS',
          }),
        ],
      }),
    ],
    sources: [reportSource('ambiguous-close', { ...time, trade_id: 'ambiguous', side: 'SELL' })],
    summary: nullSummary,
  });
  api.closedTrades.mockResolvedValue(report);
  renderPage();
  chooseOctober();
  read();
  await screen.findByTestId('closed-trades-total');
  expect(screen.getByText('2026-10-01 · Uhrzeit unbekannt · Asia/Tokyo')).toBeVisible();
  expect(screen.queryByText(/2026-09-30T15:00:00Z/)).not.toBeInTheDocument();
  const detail = openSources('ambiguous');
  fireEvent.click(detail.getByText('Datumspräzision'));
  expect(detail.getByText(/Möglicher Zeitbereich: 2026-09-30T15:00:00Z/)).toBeVisible();
  expect(screen.getByTestId('closed-trades-total')).toHaveTextContent('Nicht berechenbar');
});

it('replaces an entire corrected basis, closes old source detail, and preserves superseded audit sources', async () => {
  renderPage();
  chooseOctober();
  read();
  await screen.findByTestId('closed-trades-total');
  openSources();
  const corrected = closedTradeReport();
  corrected.basis.id = 'b'.repeat(64);
  corrected.summary = { ...corrected.summary, total: '70', total_display: '70.00' };
  corrected.items[0] = {
    ...corrected.items[0],
    realized_gross_pnl: '70',
    realized_gross_pnl_display: '70.00',
    effective_execution_ids: corrected.items[0].effective_execution_ids.map((id) =>
      id === 'sell-september-2' ? 'replacement' : id,
    ),
    execution_ids: [...corrected.items[0].execution_ids, 'replacement'],
    sell_contributions: corrected.items[0].sell_contributions.map((sale) =>
      sale.execution_id === 'sell-september-2'
        ? {
            ...sale,
            execution_id: 'replacement',
            price_per_unit: '3.0000000000',
            realized_gross_pnl_delta: '0',
            realized_gross_pnl_delta_display: '0.00',
          }
        : sale,
    ),
  };
  const previous = corrected.sources.find((source) => source.execution_id === 'sell-september-2')!;
  previous.is_effective = false;
  previous.superseded_by_execution_id = 'replacement';
  corrected.sources.push({
    ...previous,
    execution_id: 'replacement',
    is_effective: true,
    superseded_by_execution_id: null,
    supersedes_execution_id: previous.execution_id,
    price_per_unit: '3.0000000000',
  });
  api.closedTrades.mockResolvedValueOnce(corrected);
  read();
  expect(await screen.findByTestId('closed-trades-total')).toHaveTextContent('70,00 EUR');
  expect(screen.getByText(/Der Quellenstand hat sich/)).toBeVisible();
  expect(screen.queryByRole('region', { name: 'Herkunft Trade trade-1' })).not.toBeInTheDocument();
  const detail = openSources();
  expect(detail.getByRole('listitem', { name: 'Buchungsquelle replacement' })).toBeVisible();
  expect(
    detail.queryByRole('listitem', { name: 'Buchungsquelle sell-september-2' }),
  ).not.toBeInTheDocument();
  fireEvent.click(
    detail.getByText('Gesamte gelesene Historie einschließlich ersetzter Buchungen (7)'),
  );
  const historical = within(
    await detail.findByRole('listitem', { name: 'Buchungsquelle sell-september-2' }),
  );
  expect(historical.getByText('historisch ersetzt')).toBeVisible();
  expect(historical.getByText(/zählt nicht zusätzlich/)).toBeVisible();
  expect(api.closedTrades).toHaveBeenCalledTimes(2);
});

it('invalidates visible results and ignores stale success and failure after any filter changes', async () => {
  const old = deferred<ClosedTradeReport>();
  api.closedTrades.mockReturnValueOnce(old.promise);
  renderPage();
  chooseOctober();
  read();
  expect(screen.getByRole('status')).toHaveTextContent('Ein konsistenter Quellenstand');
  const signal = api.closedTrades.mock.calls[0][1];
  fireEvent.change(screen.getByLabelText('Von (einschließlich)'), {
    target: { value: '2026-09-01' },
  });
  fireEvent.change(screen.getByLabelText('Bis (einschließlich)'), {
    target: { value: '2026-09-30' },
  });
  expect(signal?.aborted).toBe(true);
  const newer = closedTradeReport({
    filters: { ...closedTradeFilters, from_date: '2026-09-01', to_date: '2026-09-30' },
    items: [],
    summary: { ...nullSummary, status: 'EMPTY', total: '0', total_display: '0.00' },
  });
  api.closedTrades.mockResolvedValueOnce(newer);
  read();
  expect(await screen.findByTestId('closed-trades-total')).toHaveTextContent('0,00 EUR');
  await act(async () => {
    old.resolve(closedTradeReport());
    await old.promise;
  });
  expect(screen.getByText('Keine abgeschlossenen Trades in dieser Auswahl')).toBeVisible();
  const failed = deferred<ClosedTradeReport>();
  api.closedTrades.mockReturnValueOnce(failed.promise);
  read();
  fireEvent.change(screen.getByLabelText('Berichtszeitzone (IANA)'), {
    target: { value: 'Etc/UTC' },
  });
  expect(screen.queryByTestId('closed-trades-total')).not.toBeInTheDocument();
  await act(async () => {
    failed.reject(new Error('Veralteter Fehler'));
    await failed.promise.catch(() => undefined);
  });
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it.each(['filters', 'currency', 'definition'] as const)(
  'rejects a response with a mismatched %s instead of showing a believable wrong report',
  async (mismatch) => {
    const report = closedTradeReport();
    if (mismatch === 'filters') report.filters.report_timezone = 'Etc/UTC';
    if (mismatch === 'currency') report.currency.code = 'USD';
    if (mismatch === 'definition') report.definition_version = 'realized-gross-sell-v2';
    api.closedTrades.mockResolvedValue(report);
    renderPage();
    chooseOctober();
    read();
    expect(await screen.findByRole('alert')).toHaveTextContent('Die Antwort gehört nicht');
    expect(screen.queryByTestId('closed-trades-total')).not.toBeInTheDocument();
  },
);

it('validates periods and currency and retains filter inputs after read errors', async () => {
  renderPage();
  chooseOctober();
  fireEvent.change(screen.getByLabelText('Von (einschließlich)'), {
    target: { value: '2026-11-01' },
  });
  read();
  expect(screen.getByRole('alert')).toHaveTextContent('Von darf nicht nach Bis liegen');
  expect(api.closedTrades).not.toHaveBeenCalled();
  chooseOctober();
  fireEvent.change(screen.getByLabelText('Berichtswährung'), { target: { value: 'EU' } });
  read();
  expect(screen.getByRole('alert')).toHaveTextContent(
    'Berichtswährung und Berichtszeitzone ausdrücklich',
  );
  expect(api.closedTrades).not.toHaveBeenCalled();
  chooseOctober();
  api.closedTrades.mockRejectedValueOnce(new Error('Quellenstand nicht verfügbar'));
  read();
  expect(await screen.findByRole('alert')).toHaveTextContent('Quellenstand nicht verfügbar');
  expect(screen.getByLabelText('Von (einschließlich)')).toHaveValue('2026-10-01');
  expect(screen.getByLabelText('Berichtswährung')).toHaveValue('EUR');
});

it('aborts an outstanding read when the report page is unmounted', async () => {
  const pending = deferred<ClosedTradeReport>();
  api.closedTrades.mockReturnValueOnce(pending.promise);
  const view = renderPage();
  chooseOctober();
  read();
  const signal = api.closedTrades.mock.calls[0][1];
  view.unmount();
  expect(signal?.aborted).toBe(true);
  await act(async () => {
    pending.resolve(closedTradeReport());
    await pending.promise;
  });
});
