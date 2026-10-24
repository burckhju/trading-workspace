import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';

import {
  closedTradeFilters,
  closedTradeItem,
  closedTradeReport,
} from '../../../test/closedTradesFixtures';
import { performanceApiClient } from '../services/client';
import { closedContextQuery } from '../services/closedReportContext';
import type { ClosedTradeGroup, ClosedTradeReport } from '../types/api';
import { ClosedTradeResult } from './ClosedTradeResult';

vi.mock('../services/client', () => ({ performanceApiClient: { closedTrades: vi.fn() } }));
const api = vi.mocked(performanceApiClient);
const A = '10000000-0000-4000-8000-000000000001';
const B = '10000000-0000-4000-8000-000000000002';
const query = () =>
  closedContextQuery({ filters: closedTradeFilters, view: 'all', page: 1, basis: 'a'.repeat(64) });
function report(id = A, amount = '50.00') {
  const value = closedTradeReport();
  value.items = [
    closedTradeItem(id, { realized_gross_pnl: amount, realized_gross_pnl_display: amount }),
  ];
  value.sources = value.sources.map((s) => ({ ...s, trade_id: id }));
  return value;
}
function view(id = A, context = query()) {
  return (
    <MemoryRouter>
      <ClosedTradeResult tradeId={id} productId="product-1" query={context} />
    </MemoryRouter>
  );
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
beforeEach(() => {
  vi.resetAllMocks();
  api.closedTrades.mockResolvedValue(report());
});

it('uses the complete qualified result and its sources from one response, never period SELL amounts or URL money', async () => {
  const context = query();
  context.set('total', '9999');
  render(view(A, context));
  expect(await screen.findByText('50,00 EUR')).toBeVisible();
  expect(screen.queryByText(/9999/)).not.toBeInTheDocument();
  expect(screen.getByText(/Berichtsgrundlage stimmt/)).toBeVisible();
  expect(
    within(screen.getByRole('listitem', { name: 'SELL-Beitrag sell-october' })).getByText(
      '30,00 EUR',
    ),
  ).toBeVisible(); // labelled closing SELL source, not total
  expect(api.closedTrades).toHaveBeenCalledExactlyOnceWith(
    closedTradeFilters,
    expect.any(AbortSignal),
  );
  expect(
    screen.queryByRole('link', { name: /Buchungen und Währungsbestätigungen/ }),
  ).not.toBeInTheDocument();
});

it('marks a new full report basis without claiming this trade alone changed or restoring an old report', async () => {
  const value = report(A, '70.00');
  value.basis.id = 'b'.repeat(64);
  api.closedTrades.mockResolvedValue(value);
  render(view());
  expect(await screen.findByText('70,00 EUR')).toBeVisible();
  expect(screen.getByText(/Berichtsgrundlage hat sich/)).toHaveTextContent('auch andere Trades');
  expect(screen.getByText(/keinen früheren Bericht/)).toBeVisible();
  expect(screen.getByText(/eigenen|eigene Lesefenster/)).toBeVisible();
});

it.each([
  ['OPEN', 'Offen – kein vollständiger Abschluss'],
  ['CANCELLED', 'Storniert – kein Verkauf'],
  ['HISTORY_UNRESOLVED', 'Abschluss nicht zuverlässig bestimmbar'],
  ['MONETARY_UNRESOLVED', 'Abgeschlossen'],
  ['OUTSIDE_PERIOD', 'Abgeschlossen'],
  ['OTHER_CURRENCY', 'Abgeschlossen'],
  ['PERIOD_UNRESOLVED', 'Abgeschlossen'],
] as [ClosedTradeGroup, string][])(
  'does not keep a stale closed amount when the owner returns %s',
  async (group, state) => {
    const value = report();
    value.items[0] = {
      ...value.items[0],
      group,
      status: ['OPEN', 'CANCELLED', 'OUTSIDE_PERIOD', 'OTHER_CURRENCY'].includes(group)
        ? 'EXCLUDED'
        : 'NOT_COMPUTABLE',
      realized_gross_pnl: null,
      realized_gross_pnl_display: null,
      classification: null,
    };
    api.closedTrades.mockResolvedValue(value);
    render(view());
    expect(await screen.findByText(`Zustand in dieser Ergebnisgrundlage: ${state}.`)).toBeVisible();
    expect(screen.queryByText('50,00 EUR')).not.toBeInTheDocument();
    expect(screen.queryByText('0,00 EUR')).not.toBeInTheDocument();
  },
);

it('retains a measured zero and does not turn it into missing money', async () => {
  const value = report(A, '0.00');
  value.items[0].classification = 'NEUTRAL';
  api.closedTrades.mockResolvedValue(value);
  render(view());
  expect(await screen.findByText('0,00 EUR')).toBeVisible();
});

it('does not call the report owner without explicit valid context', () => {
  const mounted = render(view(A, new URLSearchParams()));
  expect(screen.getByText(/Kein Abschlussberichtskontext/)).toBeVisible();
  mounted.rerender(
    view(A, new URLSearchParams('report_context=closed-trades&report_currency=EUR')),
  );
  expect(screen.getByRole('alert')).toHaveTextContent('Ungültiger');
  expect(api.closedTrades).not.toHaveBeenCalled();
});

it('distinguishes a missing baseline from equality', async () => {
  const context = query();
  context.delete('report_basis');
  render(view(A, context));
  expect(await screen.findByText('50,00 EUR')).toBeVisible();
  expect(screen.getByText(/Kein Listenfingerprint/)).toBeVisible();
});

it('exposes read failures and performs a conscious read-only retry', async () => {
  api.closedTrades.mockRejectedValueOnce(new Error('synthetic outage'));
  render(view());
  expect(await screen.findByRole('alert')).toHaveTextContent('weder Null noch fehlende Reflexion');
  fireEvent.click(screen.getByRole('button', { name: 'Gesamtergebnis neu lesen' }));
  expect(await screen.findByText('50,00 EUR')).toBeVisible();
  expect(api.closedTrades).toHaveBeenCalledTimes(2);
});

it.each(['trade', 'duplicate', 'product', 'definition', 'currency', 'filters'])(
  'rejects an unrelated %s response rather than rendering its money',
  async (kind) => {
    const value = report();
    if (kind === 'trade') value.items[0].trade_id = B;
    if (kind === 'duplicate') value.items.push(value.items[0]);
    if (kind === 'product') value.items[0].product_id = 'foreign';
    if (kind === 'definition') value.definition_version = 'other';
    if (kind === 'currency') value.currency.code = 'USD';
    if (kind === 'filters') value.filters.to_date = '2026-10-30';
    api.closedTrades.mockResolvedValue(value);
    render(view());
    expect(await screen.findByRole('alert')).toBeVisible();
    expect(screen.queryByText('50,00 EUR')).not.toBeInTheDocument();
  },
);

it.each(['resolve', 'reject'] as const)(
  'isolates A→B→A visits and stale %s, including their loading and error state',
  async (outcome) => {
    const first = deferred<ClosedTradeReport>();
    const last = deferred<ClosedTradeReport>();
    api.closedTrades
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce(report(B, '12.00'))
      .mockReturnValueOnce(last.promise);
    const mounted = render(view());
    const firstSignal = api.closedTrades.mock.calls[0][1]!;
    mounted.rerender(view(B));
    expect(await screen.findByText('12,00 EUR')).toBeVisible();
    mounted.rerender(view());
    await act(async () => {
      if (outcome === 'resolve') first.resolve(report(A, '999.00'));
      else first.reject(new Error('obsolete failure'));
      await first.promise.catch(() => undefined);
    });
    expect(firstSignal.aborted).toBe(true);
    expect(screen.getByRole('status')).toHaveTextContent('wird gelesen');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await act(async () => {
      last.resolve(report(A, '70.00'));
      await last.promise;
    });
    expect(await screen.findByText('70,00 EUR')).toBeVisible();
    expect(screen.queryByText('999,00 EUR')).not.toBeInTheDocument();
    mounted.unmount();
    await waitFor(() => expect(api.closedTrades.mock.calls[2][1]!.aborted).toBe(true));
  },
);
