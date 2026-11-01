import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import {
  realizedGrossReport,
  reportFilters,
  reportItem,
  reportSource,
} from '../../../test/realizedGrossFixtures';
import { performanceApiClient } from '../services/client';
import type { RealizedGrossReport } from '../types/api';
import { RealizedGrossPage } from './RealizedGrossPage';

vi.mock('../services/client', () => ({ performanceApiClient: { realizedGross: vi.fn() } }));
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
      <RealizedGrossPage />
    </MemoryRouter>,
  );
}
function chooseSeptember() {
  fireEvent.change(screen.getByLabelText('Von (einschließlich)'), {
    target: { value: '2026-09-01' },
  });
  fireEvent.change(screen.getByLabelText('Bis (einschließlich)'), {
    target: { value: '2026-09-30' },
  });
  // The historical report fixture uses Berlin, independently of the browser suggestion.
  fireEvent.change(screen.getByLabelText('Berichtszeitzone (IANA)'), {
    target: { value: reportFilters.report_timezone },
  });
}
function read() {
  fireEvent.click(screen.getByRole('button', { name: 'Bericht lesen' }));
}

function expectTradeReturnLink(
  link: HTMLElement,
  tradeId: string,
  view: string,
  filters = reportFilters,
  basis = 'a'.repeat(64),
) {
  const url = new URL(link.getAttribute('href')!, 'https://workspace.test');
  expect(url.pathname).toBe('/trade-management');
  expect(url.hash).toBe('#execution-dates');
  expect(Object.fromEntries(url.searchParams)).toEqual({
    report_context: 'realized-gross',
    ...filters,
    report_view: view,
    report_page: '1',
    report_basis: basis,
    trade_id: tradeId,
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  const browserOptions = Intl.DateTimeFormat().resolvedOptions();
  vi.spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions').mockReturnValue({
    ...browserOptions,
    timeZone: 'America/New_York',
  });
  api.realizedGross.mockResolvedValue(realizedGrossReport());
});

afterEach(() => vi.restoreAllMocks());

it('uses fixed EUR, keeps the visible reporting zone, and displays independent September contributions with all preceding sources', async () => {
  renderPage();
  expect(api.realizedGross).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Berichtswährung')).toHaveValue('EUR');
  expect(screen.getByLabelText('Berichtswährung')).toHaveAttribute('readonly');
  expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveValue('America/New_York');
  chooseSeptember();
  read();
  expect(await screen.findByTestId('realized-gross-total')).toHaveTextContent('10,00 EUR');
  expect(api.realizedGross).toHaveBeenCalledExactlyOnceWith(reportFilters, expect.any(AbortSignal));
  expect(
    screen.getByText(/Journal, Nachbeobachtung und Lessons sind keine Voraussetzung/),
  ).toBeVisible();
  const second = within(screen.getByRole('article', { name: 'Verkauf sell-september-2' }));
  expect(second.getByText('-20,00 EUR')).toBeVisible();
  fireEvent.click(second.getByRole('button', { name: 'Quellen und Berechnung' }));
  const detail = within(screen.getByRole('region', { name: 'Herkunft SELL sell-september-2' }));
  expect(detail.getByRole('listitem', { name: 'Buchungsquelle buy-august' })).toBeVisible();
  expect(detail.getByRole('listitem', { name: 'Buchungsquelle sell-august' })).toBeVisible();
  expect(detail.getByRole('listitem', { name: 'Buchungsquelle sell-september-1' })).toBeVisible();
  expect(detail.getByRole('listitem', { name: 'Buchungsquelle buy-september' })).toBeVisible();
  expect(detail.getByRole('listitem', { name: 'Buchungsquelle sell-september-2' })).toBeVisible();
  expectTradeReturnLink(
    detail.getByRole('link', { name: 'Buchungen und Währungsbestätigungen im Trade prüfen' }),
    'trade-1',
    'candidates',
  );
  expect(api.realizedGross).toHaveBeenCalledOnce();
});

it('shows a sale currency inherited from BUY evidence without claiming a new manual SELL confirmation', async () => {
  const report = realizedGrossReport();
  const sell = report.sources.find((source) => source.execution_id === 'sell-september-2')!;
  sell.currency_confirmation = null;
  sell.currency_history = [];
  sell.currency_resolution = {
    currency_code: 'EUR',
    source: 'PRIOR_BUYS',
    source_execution_ids: ['buy-august', 'buy-september'],
    confirmation_ids: ['currency-buy-august', 'currency-buy-september'],
  };
  report.items[1].currency_confirmation_ids = ['currency-buy-august', 'currency-buy-september'];
  api.realizedGross.mockResolvedValue(report);
  renderPage();
  chooseSeptember();
  read();
  await screen.findByTestId('realized-gross-total');
  fireEvent.click(
    within(screen.getByRole('article', { name: 'Verkauf sell-september-2' })).getByRole('button', {
      name: 'Quellen und Berechnung',
    }),
  );
  const source = within(screen.getByRole('listitem', { name: 'Buchungsquelle sell-september-2' }));
  expect(source.getByText('Gespeicherter Stückpreis:', { exact: false })).toHaveTextContent(
    '2.5000000000 EUR',
  );
  expect(
    source.getByText('Ausführungswährung: EUR · aus vorherigen Käufen übernommen'),
  ).toBeVisible();
  expect(source.queryByText(/ausdrücklich vom Nutzer bestätigt/)).not.toBeInTheDocument();
  expect(source.queryByText(/Ausführungswährung unbekannt/)).not.toBeInTheDocument();
  fireEvent.click(source.getByText('Verwendete Währungsherkunft'));
  expect(source.getByText('Buchung buy-august')).toBeVisible();
  expect(source.getByText('Buchung buy-september')).toBeVisible();
  expect(source.getByText('Bestätigung currency-buy-september')).toBeVisible();
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('10,00 EUR');
  expect(api.realizedGross).toHaveBeenCalledOnce();
});

it.each(['UNKNOWN', 'MIXED'] as const)(
  'keeps an owner %s currency source visibly unresolved in the report',
  async (sourceType) => {
    const unknown = reportItem('unknown-sale', {
      status: 'NOT_COMPUTABLE',
      reasons: [sourceType === 'UNKNOWN' ? 'CURRENCY_UNKNOWN' : 'CURRENCY_MIXED'],
      currency_code: null,
      realized_gross_pnl_delta: null,
      realized_gross_pnl_delta_display: null,
      average_cost_per_unit: null,
      cost_basis_before: null,
      cost_basis_after: null,
      cost_basis_execution_ids: [],
    });
    api.realizedGross.mockResolvedValue(
      realizedGrossReport({
        items: [unknown],
        sources: [
          reportSource(unknown.execution_id, {
            side: 'SELL',
            currency_confirmation: null,
            currency_history: [],
            currency_resolution: {
              currency_code: null,
              source: sourceType,
              source_execution_ids: [],
              confirmation_ids: [],
            },
          }),
        ],
        summary: {
          status: 'NOT_COMPUTABLE',
          total: null,
          total_display: null,
          subtotal: null,
          subtotal_display: null,
          rounding_difference: null,
          rounding_difference_display: null,
        },
      }),
    );
    renderPage();
    chooseSeptember();
    read();
    await screen.findByTestId('realized-gross-total');
    fireEvent.click(screen.getByRole('button', { name: 'Quellen und Berechnung' }));
    const source = within(screen.getByRole('listitem', { name: 'Buchungsquelle unknown-sale' }));
    expect(
      source.getByText(
        sourceType === 'UNKNOWN'
          ? 'Ausführungswährung: unbekannt'
          : 'Ausführungswährung: keine eindeutige Währungszuordnung',
      ),
    ).toBeVisible();
    expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('Nicht berechenbar');
    expect(source.queryByText(/ausdrücklich vom Nutzer bestätigt/)).not.toBeInTheDocument();
  },
);

it('keeps an empty reviewed set distinct from entirely unresolved facts and from a measured rounded zero', async () => {
  const unknown = reportItem('unknown', {
    status: 'NOT_COMPUTABLE',
    reasons: ['CURRENCY_UNKNOWN'],
    currency_code: null,
    realized_gross_pnl_delta: null,
    realized_gross_pnl_delta_display: null,
    average_cost_per_unit: null,
    cost_basis_before: null,
    cost_basis_after: null,
  });
  const unknownSource = reportSource(unknown.execution_id, {
    side: 'SELL',
    quantity: unknown.quantity,
    price_per_unit: unknown.price_per_unit,
    executed_at: unknown.executed_at,
    currency_confirmation: null,
    currency_history: [],
    currency_resolution: {
      currency_code: null,
      source: 'UNKNOWN',
      source_execution_ids: [],
      confirmation_ids: [],
      reason: 'NO_HISTORICAL_EVIDENCE',
    },
  });
  api.realizedGross.mockResolvedValueOnce(
    realizedGrossReport({
      items: [],
      sources: [],
      counts: {
        examined: 0,
        in_period: 0,
        outside_period: 0,
        period_ambiguous: 0,
        period_unknown: 0,
        candidates: 0,
        usable: 0,
        unresolved: 0,
        excluded: 0,
        cancelled: 0,
      },
      summary: {
        status: 'EMPTY',
        total: '0',
        total_display: '0.00',
        subtotal: null,
        subtotal_display: null,
        rounding_difference: null,
        rounding_difference_display: null,
      },
    }),
  );
  renderPage();
  chooseSeptember();
  read();
  expect(await screen.findByText('Keine wirksamen Verkäufe in dieser Auswahl')).toBeVisible();
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('0,00 EUR');
  api.realizedGross.mockResolvedValueOnce(
    realizedGrossReport({
      items: [unknown],
      sources: [...realizedGrossReport().sources, unknownSource],
      summary: {
        status: 'NOT_COMPUTABLE',
        total: null,
        total_display: null,
        subtotal: null,
        subtotal_display: null,
        rounding_difference: null,
        rounding_difference_display: null,
      },
    }),
  );
  read();
  expect(await screen.findByText('Auswahl nicht berechenbar')).toBeVisible();
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('Nicht berechenbar');
  expect(screen.queryByTestId('realized-gross-subtotal')).not.toBeInTheDocument();
  expect(
    screen.getByText(/Ausführungswährung für Verkauf oder Kostenbasis nicht vollständig belegt/),
  ).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Quellen und Berechnung' }));
  const unknownDetail = within(screen.getByRole('region', { name: 'Herkunft SELL unknown' }));
  const unknownNotice = within(
    unknownDetail.getByRole('region', { name: 'Währungsherkunft dieses Beitrags ungeklärt' }),
  );
  expect(
    unknownNotice.getByText(/Bruttobeitrag dieses Verkaufs derzeit nicht berechnen/),
  ).toBeVisible();
  const unknownAmount = unknownDetail.getByText('Beitrag · Anzeige').nextElementSibling;
  expect(unknownAmount).toBeVisible();
  expect(unknownAmount).toHaveTextContent('Nicht berechenbar');
  expect(unknownDetail.queryByText('0,00 EUR')).not.toBeInTheDocument();
  fireEvent.click(unknownNotice.getByText('Ursache und Quellen'));
  expect(unknownNotice.getByText(/NO_HISTORICAL_EVIDENCE/)).toBeVisible();
  expectTradeReturnLink(
    unknownNotice.getByRole('link', {
      name: 'Buchungen und Währungsbestätigungen im Trade prüfen',
    }),
    unknown.trade_id,
    'candidates',
  );
  expect(api.realizedGross).toHaveBeenCalledTimes(2);
  const tiny = reportItem('tiny', {
    realized_gross_pnl_delta: '0.0040000000',
    realized_gross_pnl_delta_display: '0.00',
  });
  api.realizedGross.mockResolvedValueOnce(
    realizedGrossReport({
      items: [tiny, unknown],
      sources: [
        ...realizedGrossReport().sources,
        unknownSource,
        reportSource(tiny.execution_id, {
          side: 'SELL',
          quantity: tiny.quantity,
          price_per_unit: tiny.price_per_unit,
          executed_at: tiny.executed_at,
        }),
      ],
      summary: {
        status: 'PARTIAL',
        total: null,
        total_display: null,
        subtotal: '0.0040000000',
        subtotal_display: '0.00',
        rounding_difference: '0.00',
        rounding_difference_display: '0.00',
      },
    }),
  );
  read();
  expect(await screen.findByTestId('realized-gross-subtotal')).toHaveTextContent('0,00 EUR');
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('Nicht berechenbar');
  fireEvent.click(
    within(screen.getByRole('article', { name: 'Verkauf tiny' })).getByRole('button', {
      name: 'Quellen und Berechnung',
    }),
  );
  expect(
    within(screen.getByRole('region', { name: 'Herkunft SELL tiny' })).getByText('0.0040000000'),
  ).toBeVisible();
  const partialDetail = within(screen.getByRole('region', { name: 'Herkunft SELL tiny' }));
  const partialNotice = within(
    partialDetail.getByRole('region', { name: 'Währungsherkunft dieses Beitrags' }),
  );
  expect(partialNotice.getByText(/Bruttobeitrag als verwendbar/)).toBeVisible();
  expect(partialNotice.getByText(/teilweise berechenbar/)).toBeVisible();
  expect(partialNotice.getByText(/keine vollständige Summe/)).toBeVisible();
  const partialAmount = partialDetail.getByText('Beitrag · Anzeige').nextElementSibling;
  expect(partialAmount).toBeVisible();
  expect(partialAmount).toHaveTextContent('0,00 EUR');
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('Nicht berechenbar');
  expect(api.realizedGross).toHaveBeenCalledTimes(3);

  const zero = reportItem('zero', {
    price_per_unit: '2.0000000000',
    realized_gross_pnl_delta: '0.0000000000',
    realized_gross_pnl_delta_display: '0.00',
  });
  api.realizedGross.mockResolvedValueOnce(
    realizedGrossReport({
      items: [zero],
      sources: [
        ...realizedGrossReport().sources,
        reportSource(zero.execution_id, {
          side: 'SELL',
          quantity: zero.quantity,
          price_per_unit: zero.price_per_unit,
          executed_at: zero.executed_at,
        }),
      ],
      summary: {
        status: 'COMPLETE',
        total: '0.0000000000',
        total_display: '0.00',
        subtotal: null,
        subtotal_display: null,
        rounding_difference: '0.00',
        rounding_difference_display: '0.00',
      },
    }),
  );
  read();
  await screen.findByRole('article', { name: 'Verkauf zero' });
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('0,00 EUR');
  expect(screen.queryByTestId('realized-gross-subtotal')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Quellen und Berechnung' }));
  const zeroDetail = within(screen.getByRole('region', { name: 'Herkunft SELL zero' }));
  const zeroNotice = within(
    zeroDetail.getByRole('region', { name: 'Währungsherkunft dieses Beitrags' }),
  );
  expect(zeroNotice.getByText(/Bruttobeitrag als verwendbar/)).toBeVisible();
  expect(zeroDetail.getByText('0.0000000000')).toBeVisible();
  const zeroAmount = zeroDetail.getByText('Beitrag · Anzeige').nextElementSibling;
  expect(zeroAmount).toBeVisible();
  expect(zeroAmount).toHaveTextContent('0,00 EUR');
  expect(zeroNotice.queryByText(/teilweise berechenbar/)).not.toBeInTheDocument();
  expect(screen.queryByRole('region', { name: 'Herkunft SELL unknown' })).not.toBeInTheDocument();
  expect(api.realizedGross).toHaveBeenCalledTimes(4);
});

it('does not derive totals from the visible page or convert high-precision money through a float', async () => {
  const big = '9007199254740993.0000000001';
  const fixture = realizedGrossReport({
    items: Array.from({ length: 21 }, (_, index) =>
      reportItem(`sale-${index}`, {
        realized_gross_pnl_delta: index === 20 ? '1E-27' : '0.004',
        realized_gross_pnl_delta_display: '0.00',
      }),
    ),
    summary: {
      status: 'COMPLETE',
      total: big,
      total_display: '9007199254740993.00',
      subtotal: null,
      subtotal_display: null,
      rounding_difference: '0.01',
      rounding_difference_display: '0.01',
    },
  });
  api.realizedGross.mockResolvedValue(fixture);
  renderPage();
  chooseSeptember();
  read();
  expect(await screen.findByTestId('realized-gross-total')).toHaveTextContent(
    '9007199254740993,00 EUR',
  );
  expect(screen.getAllByRole('article')).toHaveLength(20);
  fireEvent.click(screen.getByText('Präzise Summen, Rundung und weitere Zähler'));
  expect(screen.getByText(big)).toBeVisible();
  expect(screen.getByText(/0,01 EUR/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Nächste Seite' }));
  expect(screen.getAllByRole('article')).toHaveLength(1);
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('9007199254740993,00 EUR');
  fireEvent.click(screen.getByRole('button', { name: 'Quellen und Berechnung' }));
  expect(screen.getByText('1E-27')).toBeVisible();
  expect(api.realizedGross).toHaveBeenCalledOnce();
});

it('never exposes a date-only sort anchor as execution time and retains ambiguous period and mixed currency reasons', async () => {
  const time = {
    time_precision: 'DATE_ONLY' as const,
    executed_at: null,
    executed_on: '2026-09-01',
    execution_timezone: 'Asia/Tokyo',
    possible_start_at: '2026-08-31T15:00:00Z',
    possible_end_at: '2026-09-01T15:00:00Z',
  };
  api.realizedGross.mockResolvedValue(
    realizedGrossReport({
      items: [
        reportItem('ambiguous', {
          ...time,
          period_status: 'PERIOD_AMBIGUOUS',
          status: 'NOT_COMPUTABLE',
          reasons: ['PERIOD_AMBIGUOUS', 'CURRENCY_MIXED'],
          realized_gross_pnl_delta: null,
          realized_gross_pnl_delta_display: null,
          average_cost_per_unit: null,
          cost_basis_before: null,
          cost_basis_after: null,
        }),
      ],
      sources: [reportSource('ambiguous', { ...time, side: 'SELL' })],
    }),
  );
  renderPage();
  chooseSeptember();
  read();
  await screen.findByTestId('realized-gross-total');
  expect(screen.getByText('2026-09-01 · Uhrzeit unbekannt · Asia/Tokyo')).toBeVisible();
  expect(screen.queryByText(/2026-08-31T15:00:00Z/)).not.toBeInTheDocument();
  expect(
    screen.getByText(/Periodenzugehörigkeit wegen der Datums- \/ Zeitzonenpräzision mehrdeutig/),
  ).toBeVisible();
  expect(screen.getByText(/Unterschiedliche Währungen in Verkauf und Kostenbasis/)).toBeVisible();
});

it('invalidates visible results immediately and ignores older success and failure responses after filter changes', async () => {
  const old = deferred<RealizedGrossReport>();
  api.realizedGross.mockReturnValueOnce(old.promise);
  renderPage();
  chooseSeptember();
  read();
  const oldSignal = api.realizedGross.mock.calls[0][1];
  fireEvent.change(screen.getByLabelText('Von (einschließlich)'), {
    target: { value: '2026-10-01' },
  });
  fireEvent.change(screen.getByLabelText('Bis (einschließlich)'), {
    target: { value: '2026-10-31' },
  });
  expect(oldSignal?.aborted).toBe(true);
  const currentReport = realizedGrossReport({
    filters: { ...reportFilters, from_date: '2026-10-01', to_date: '2026-10-31' },
    summary: {
      status: 'COMPLETE',
      total: '30',
      total_display: '30.00',
      subtotal: null,
      subtotal_display: null,
      rounding_difference: '0',
      rounding_difference_display: '0.00',
    },
  });
  currentReport.items[1].product_name = 'Aktueller Oktoberbeitrag';
  const currentSource = currentReport.sources.find(
    (source) => source.execution_id === 'sell-september-2',
  )!;
  currentSource.currency_confirmation = null;
  currentSource.currency_history = [];
  currentSource.currency_resolution = {
    currency_code: 'EUR',
    source: 'HISTORICAL_LISTINGS',
    source_execution_ids: [],
    confirmation_ids: [],
    reason: 'OCTOBER_OWNER_REASON',
    evidence_ids: ['october-evidence'],
    evidence: [
      {
        id: 'october-evidence',
        kind: 'HISTORICAL_LISTINGS',
        source_reference: 'Oktober-Archiv',
        recorded_at: '2026-11-01T10:00:00Z',
      },
    ],
  };
  api.realizedGross.mockResolvedValueOnce(currentReport);
  read();
  expect(await screen.findByTestId('realized-gross-total')).toHaveTextContent('30,00 EUR');
  fireEvent.click(
    within(screen.getByRole('article', { name: 'Verkauf sell-september-2' })).getByRole('button', {
      name: 'Quellen und Berechnung',
    }),
  );
  const currentNotice = within(
    screen.getByRole('region', { name: 'Währungsherkunft dieses Beitrags' }),
  );
  expect(
    currentNotice.getByRole('heading', { name: 'Währungsherkunft dieses Beitrags' }),
  ).toBeVisible();
  expect(currentNotice.getByText(/Aktueller Oktoberbeitrag/)).toBeVisible();
  fireEvent.click(currentNotice.getByText('Ursache und Quellen'));
  expect(currentNotice.getByText(/OCTOBER_OWNER_REASON/)).toBeVisible();
  expect(currentNotice.getByText(/Oktober-Archiv/)).toBeVisible();
  expectTradeReturnLink(
    currentNotice.getByRole('link', {
      name: 'Buchungen und Währungsbestätigungen im Trade prüfen',
    }),
    'trade-1',
    'candidates',
    currentReport.filters,
    currentReport.basis.id,
  );
  expect(api.realizedGross).toHaveBeenCalledTimes(2);
  await act(async () => {
    old.resolve(realizedGrossReport());
    await old.promise;
  });
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('30,00 EUR');
  expect(currentNotice.getByText(/Aktueller Oktoberbeitrag/)).toBeVisible();
  expect(currentNotice.getByText(/OCTOBER_OWNER_REASON/)).toBeVisible();
  expect(currentNotice.getByText(/Oktober-Archiv/)).toBeVisible();
  expectTradeReturnLink(
    currentNotice.getByRole('link', {
      name: 'Buchungen und Währungsbestätigungen im Trade prüfen',
    }),
    'trade-1',
    'candidates',
    currentReport.filters,
    currentReport.basis.id,
  );
  const failed = deferred<RealizedGrossReport>();
  api.realizedGross.mockReturnValueOnce(failed.promise);
  read();
  fireEvent.change(screen.getByLabelText('Berichtszeitzone (IANA)'), {
    target: { value: 'Etc/UTC' },
  });
  expect(screen.queryByTestId('realized-gross-total')).not.toBeInTheDocument();
  expect(
    screen.queryByRole('region', { name: 'Währungsherkunft dieses Beitrags' }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/OCTOBER_OWNER_REASON/)).not.toBeInTheDocument();
  expect(
    screen.queryByRole('link', { name: 'Buchungen und Währungsbestätigungen im Trade prüfen' }),
  ).not.toBeInTheDocument();
  await act(async () => {
    failed.reject(new Error('Veralteter Fehler'));
    await failed.promise.catch(() => undefined);
  });
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.queryByText(/OCTOBER_OWNER_REASON/)).not.toBeInTheDocument();
});

it('rejects a response for another filter and replaces the complete report while marking a changed source basis', async () => {
  api.realizedGross.mockResolvedValueOnce(
    realizedGrossReport({ filters: { ...reportFilters, report_timezone: 'Etc/UTC' } }),
  );
  const initial = realizedGrossReport();
  const initialSource = initial.sources.find(
    (source) => source.execution_id === 'sell-september-2',
  )!;
  initialSource.currency_resolution!.reason = 'INITIAL_OWNER_REASON';
  api.realizedGross.mockResolvedValueOnce(initial);
  renderPage();
  chooseSeptember();
  read();
  expect(await screen.findByRole('alert')).toHaveTextContent('Die Antwort gehört nicht');
  expect(screen.queryByTestId('realized-gross-total')).not.toBeInTheDocument();
  read();
  await screen.findByTestId('realized-gross-total');
  expect(screen.queryByText(/Der Quellenstand hat sich/)).not.toBeInTheDocument();
  fireEvent.click(
    within(screen.getByRole('article', { name: 'Verkauf sell-september-2' })).getByRole('button', {
      name: 'Quellen und Berechnung',
    }),
  );
  const initialNotice = within(
    screen.getByRole('region', { name: 'Währungsherkunft dieses Beitrags' }),
  );
  fireEvent.click(initialNotice.getByText('Ursache und Quellen'));
  expect(initialNotice.getByText(/INITIAL_OWNER_REASON/)).toBeVisible();
  expectTradeReturnLink(
    initialNotice.getByRole('link', {
      name: 'Buchungen und Währungsbestätigungen im Trade prüfen',
    }),
    'trade-1',
    'candidates',
  );
  const corrected = realizedGrossReport();
  corrected.basis.id = 'b'.repeat(64);
  corrected.summary.total = '30.0000000000';
  corrected.summary.total_display = '30.00';
  corrected.items[1] = {
    ...corrected.items[1],
    execution_id: 'replacement',
    product_name: 'Berichtigter Beitrag',
    currency_confirmation_ids: ['currency-buy-august', 'currency-buy-september'],
    realized_gross_pnl_delta: '0',
    realized_gross_pnl_delta_display: '0.00',
  };
  corrected.sources = corrected.sources.map((source) =>
    source.execution_id === 'sell-september-2'
      ? reportSource('replacement', {
          side: 'SELL',
          quantity: corrected.items[1].quantity,
          price_per_unit: corrected.items[1].price_per_unit,
          executed_at: corrected.items[1].executed_at,
          currency_confirmation: null,
          currency_history: [],
          currency_resolution: {
            currency_code: 'EUR',
            source: 'EXECUTION_DOCUMENT',
            source_execution_ids: ['replacement'],
            confirmation_ids: [],
            reason: 'CORRECTED_OWNER_REASON',
            evidence_ids: ['replacement-evidence'],
            evidence: [
              {
                id: 'replacement-evidence',
                kind: 'EXECUTION_DOCUMENT',
                source_reference: 'Berichtigte Originalreferenz',
                recorded_at: '2026-11-01T10:00:00Z',
              },
            ],
          },
        })
      : source,
  );
  api.realizedGross.mockResolvedValueOnce(corrected);
  read();
  await waitFor(() =>
    expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('30,00 EUR'),
  );
  expect(screen.getByText(/Der Quellenstand hat sich/)).toBeVisible();
  expect(
    screen.queryByRole('article', { name: 'Verkauf sell-september-2' }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole('article', { name: 'Verkauf replacement' })).toBeVisible();
  expect(screen.queryByText(/INITIAL_OWNER_REASON/)).not.toBeInTheDocument();
  expect(
    screen.queryByRole('link', { name: 'Buchungen und Währungsbestätigungen im Trade prüfen' }),
  ).not.toBeInTheDocument();
  fireEvent.click(
    within(screen.getByRole('article', { name: 'Verkauf replacement' })).getByRole('button', {
      name: 'Quellen und Berechnung',
    }),
  );
  const correctedDetail = within(screen.getByRole('region', { name: 'Herkunft SELL replacement' }));
  const correctedNotice = within(
    correctedDetail.getByRole('region', { name: 'Währungsherkunft dieses Beitrags' }),
  );
  expect(
    correctedNotice.getByRole('heading', {
      name: 'Währungsherkunft dieses Beitrags',
    }),
  ).toBeVisible();
  expect(correctedNotice.getByText(/Berichtigter Beitrag/)).toBeVisible();
  fireEvent.click(correctedNotice.getByText('Ursache und Quellen'));
  expect(correctedNotice.getByText(/CORRECTED_OWNER_REASON/)).toBeVisible();
  expect(correctedNotice.getByText(/Berichtigte Originalreferenz/)).toBeVisible();
  expect(
    correctedDetail.getByRole('listitem', { name: 'Buchungsquelle replacement' }),
  ).toBeVisible();
  expect(
    correctedDetail.queryByRole('listitem', { name: 'Buchungsquelle sell-september-2' }),
  ).not.toBeInTheDocument();
  expectTradeReturnLink(
    correctedNotice.getByRole('link', {
      name: 'Buchungen und Währungsbestätigungen im Trade prüfen',
    }),
    'trade-1',
    'candidates',
    corrected.filters,
    corrected.basis.id,
  );
  expect(api.realizedGross).toHaveBeenCalledTimes(3);
});

it('shows excluded currencies and cancelled trades without treating them as returns or requesting learning data', async () => {
  const excluded = reportItem('other-currency', {
    status: 'EXCLUDED',
    currency_code: 'USD',
    reasons: ['OTHER_CURRENCY'],
    realized_gross_pnl_delta: null,
    realized_gross_pnl_delta_display: null,
  });
  api.realizedGross.mockResolvedValue(
    realizedGrossReport({
      items: [reportItem(), excluded],
      excluded_trades: [
        {
          trade_id: 'cancelled',
          product_id: 'other',
          product_name: 'Stornierter Testtrade',
          origin: 'EXTERNAL',
          reason: 'TRADE_CANCELLED',
          execution_ids: ['cancelled-buy'],
        },
      ],
    }),
  );
  renderPage();
  chooseSeptember();
  read();
  await screen.findByTestId('realized-gross-total');
  expect(screen.queryByRole('article', { name: 'Verkauf other-currency' })).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Zeilen anzeigen'), { target: { value: 'excluded' } });
  expect(screen.getByText('Nicht in der Summe')).toBeVisible();
  expect(screen.getByText(/Belegte Ausführungswährung außerhalb/)).toBeVisible();
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('10,00 EUR');
  expectTradeReturnLink(
    screen.getByRole('link', { name: 'Stornierter Testtrade · Trade prüfen' }),
    'cancelled',
    'excluded',
  );
  expect(api.realizedGross).toHaveBeenCalledOnce();
});

it('validates reversed periods before a request and preserves entered filters on a read failure', async () => {
  renderPage();
  chooseSeptember();
  fireEvent.change(screen.getByLabelText('Von (einschließlich)'), {
    target: { value: '2026-10-01' },
  });
  read();
  expect(screen.getByRole('alert')).toHaveTextContent('Von darf nicht nach Bis liegen');
  expect(api.realizedGross).not.toHaveBeenCalled();
  chooseSeptember();
  api.realizedGross.mockRejectedValue(new Error('Quellenstand nicht verfügbar'));
  read();
  expect(await screen.findByRole('alert')).toHaveTextContent('Quellenstand nicht verfügbar');
  expect(screen.getByLabelText('Von (einschließlich)')).toHaveValue('2026-09-01');
  expect(screen.queryByTestId('realized-gross-total')).not.toBeInTheDocument();
});

it('shows computed amounts with automatic historical source provenance without claiming a user confirmation', async () => {
  const report = realizedGrossReport();
  const sell = report.sources.find((entry) => entry.execution_id === 'sell-september-2')!;
  sell.currency_confirmation = null;
  sell.currency_history = [];
  sell.currency_resolution = {
    currency_code: 'EUR',
    source: 'HISTORICAL_LISTINGS',
    source_execution_ids: [],
    confirmation_ids: [],
    evidence_ids: ['historical-listing-v2'],
    resolver_version: 'historical-currency-v1',
    evidence: [
      {
        id: 'historical-listing-v2',
        kind: 'HISTORICAL_LISTINGS',
        source_reference: 'Historical venue archive 2026',
        recorded_at: '2026-10-28T12:00:00Z',
        valid_from: '2026-08-01T00:00:00+02:00',
        valid_to: '2026-11-01T00:00:00+01:00',
      },
    ],
  };
  api.realizedGross.mockResolvedValue(report);
  renderPage();
  chooseSeptember();
  read();
  await screen.findByTestId('realized-gross-total');
  fireEvent.click(
    within(screen.getByRole('article', { name: 'Verkauf sell-september-2' })).getByRole('button', {
      name: 'Quellen und Berechnung',
    }),
  );
  const source = within(screen.getByRole('listitem', { name: 'Buchungsquelle sell-september-2' }));
  expect(
    source.getByText(
      'Ausführungswährung: EUR · automatisch aus historischen Notierungen abgeleitet',
    ),
  ).toBeVisible();
  expect(source.queryByText(/ausdrücklich vom Nutzer bestätigt/)).not.toBeInTheDocument();
  fireEvent.click(source.getByText('Verwendete Währungsherkunft'));
  expect(source.getByText('Quelle: Historical venue archive 2026')).toBeVisible();
  expect(source.getByText('Quellenversion historical-listing-v2')).toBeVisible();
  expect(source.getByText('Zuordnungsregel historical-currency-v1')).toBeVisible();
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('10,00 EUR');
  expect(api.realizedGross).toHaveBeenCalledOnce();
});
