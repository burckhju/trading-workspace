import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';

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
  fireEvent.change(screen.getByLabelText('Berichtswährung'), { target: { value: 'EUR' } });
}
function read() {
  fireEvent.click(screen.getByRole('button', { name: 'Bericht lesen' }));
}

beforeEach(() => {
  vi.resetAllMocks();
  api.realizedGross.mockResolvedValue(realizedGrossReport());
});

it('requires an explicit currency, keeps the visible reporting zone, and displays independent September contributions with all preceding sources', async () => {
  renderPage();
  expect(api.realizedGross).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Berichtswährung')).toHaveValue('');
  expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveValue('Europe/Berlin');
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
  expect(
    detail.getByRole('link', { name: 'Buchungen und Währungsbestätigungen im Trade prüfen' }),
  ).toHaveAttribute('href', '/trade-management?trade_id=trade-1#execution-dates');
  expect(api.realizedGross).toHaveBeenCalledOnce();
});

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
  api.realizedGross.mockResolvedValueOnce(
    realizedGrossReport({
      items: [
        reportItem('tiny', {
          realized_gross_pnl_delta: '0.0040000000',
          realized_gross_pnl_delta_display: '0.00',
        }),
        unknown,
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
  api.realizedGross.mockResolvedValueOnce(
    realizedGrossReport({
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
    }),
  );
  read();
  expect(await screen.findByTestId('realized-gross-total')).toHaveTextContent('30,00 EUR');
  await act(async () => {
    old.resolve(realizedGrossReport());
    await old.promise;
  });
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('30,00 EUR');
  const failed = deferred<RealizedGrossReport>();
  api.realizedGross.mockReturnValueOnce(failed.promise);
  read();
  fireEvent.change(screen.getByLabelText('Berichtswährung'), { target: { value: 'USD' } });
  expect(screen.queryByTestId('realized-gross-total')).not.toBeInTheDocument();
  await act(async () => {
    failed.reject(new Error('Veralteter Fehler'));
    await failed.promise.catch(() => undefined);
  });
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('rejects a response for another filter and replaces the complete report while marking a changed source basis', async () => {
  api.realizedGross.mockResolvedValueOnce(
    realizedGrossReport({ filters: { ...reportFilters, report_timezone: 'Etc/UTC' } }),
  );
  renderPage();
  chooseSeptember();
  read();
  expect(await screen.findByRole('alert')).toHaveTextContent('Die Antwort gehört nicht');
  expect(screen.queryByTestId('realized-gross-total')).not.toBeInTheDocument();
  read();
  await screen.findByTestId('realized-gross-total');
  expect(screen.queryByText(/Der Quellenstand hat sich/)).not.toBeInTheDocument();
  const corrected = realizedGrossReport();
  corrected.basis.id = 'basis-corrected';
  corrected.summary.total = '30.0000000000';
  corrected.summary.total_display = '30.00';
  corrected.items[1] = {
    ...corrected.items[1],
    execution_id: 'replacement',
    realized_gross_pnl_delta: '0',
    realized_gross_pnl_delta_display: '0.00',
  };
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
  expect(
    screen.getByRole('link', { name: 'Stornierter Testtrade · Trade prüfen' }),
  ).toHaveAttribute('href', '/trade-management?trade_id=cancelled#execution-dates');
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
