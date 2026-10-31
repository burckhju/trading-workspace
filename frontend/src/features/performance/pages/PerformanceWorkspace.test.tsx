import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import {
  closedTradeFilters,
  closedTradeItem,
  closedTradeReport,
  closedTradeStatistics,
  unavailableClosedTradeStatistics,
} from '../../../test/closedTradesFixtures';
import {
  realizedGrossReport,
  reportFilters,
  reportItem,
} from '../../../test/realizedGrossFixtures';
import { performanceApiClient } from '../services/client';
import type { ClosedTradeReport, RealizedGrossFilters, RealizedGrossReport } from '../types/api';
import { PerformanceWorkspace } from './PerformanceWorkspace';

vi.mock('../services/client', () => ({
  performanceApiClient: { closedTrades: vi.fn(), realizedGross: vi.fn() },
}));

const api = vi.mocked(performanceApiClient);
const kinds = ['realized-gross', 'closed-trades'] as const;
type Kind = (typeof kinds)[number];
const names: Record<Kind, string> = {
  'realized-gross': 'Verkäufe im Zeitraum',
  'closed-trades': 'Trades mit Vollabschluss im Zeitraum',
};
const sellBasis = 'b'.repeat(64);
const closedBasis = 'a'.repeat(64);

// Independent input construction exercises the public URL contract, not its serializer.
function reportUrl(
  kind: Kind,
  filters: RealizedGrossFilters = reportFilters,
  extra: Record<string, string> = {},
) {
  return `/performance/${kind}?${new URLSearchParams({
    report_context: kind,
    ...filters,
    report_view: 'candidates',
    report_page: '1',
    ...extra,
  })}`;
}

function mount(entries: string[] = ['/performance/realized-gross'], initialIndex?: number) {
  const router = createMemoryRouter(
    kinds.map((kind) => ({
      path: `/performance/${kind}`,
      element: <PerformanceWorkspace kind={kind} />,
    })),
    { initialEntries: entries, initialIndex },
  );
  return { router, ...render(<RouterProvider router={router} />) };
}

function sellReport(filters: RealizedGrossFilters = reportFilters): RealizedGrossReport {
  const report = realizedGrossReport({ filters: { ...filters } });
  report.basis.id = sellBasis;
  return report;
}

function closedReport(filters: RealizedGrossFilters = reportFilters): ClosedTradeReport {
  return closedTradeReport({ filters: { ...filters } });
}

function setFilters(filters: RealizedGrossFilters) {
  fireEvent.change(screen.getByLabelText('Von (einschließlich)'), {
    target: { value: filters.from_date },
  });
  fireEvent.change(screen.getByLabelText('Bis (einschließlich)'), {
    target: { value: filters.to_date },
  });
  fireEvent.change(screen.getByLabelText('Berichtszeitzone (IANA)'), {
    target: { value: filters.report_timezone },
  });
}

function expectFilters(filters: RealizedGrossFilters) {
  expect(screen.getByLabelText('Von (einschließlich)')).toHaveValue(filters.from_date);
  expect(screen.getByLabelText('Bis (einschließlich)')).toHaveValue(filters.to_date);
  expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveValue(filters.report_timezone);
  expect(screen.getByLabelText('Berichtswährung')).toHaveValue('EUR');
}

function submit() {
  fireEvent.click(screen.getByRole('button', { name: 'Bericht lesen' }));
}

function switchTo(kind: Kind) {
  fireEvent.click(screen.getByRole('button', { name: names[kind] }));
}

function client(kind: Kind) {
  return kind === 'realized-gross' ? api.realizedGross : api.closedTrades;
}

function totalId(kind: Kind) {
  return kind === 'realized-gross' ? 'realized-gross-total' : 'closed-trades-total';
}

function other(kind: Kind): Kind {
  return kind === 'realized-gross' ? 'closed-trades' : 'realized-gross';
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

function browserTimezone(timeZone: string) {
  const options = Intl.DateTimeFormat().resolvedOptions();
  vi.spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions').mockReturnValue({
    ...options,
    timeZone,
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  api.realizedGross.mockImplementation((filters) => Promise.resolve(sellReport(filters)));
  api.closedTrades.mockImplementation((filters) => Promise.resolve(closedReport(filters)));
});

afterEach(() => vi.restoreAllMocks());

it.each(kinds)('starts %s with one shared form, fixed EUR, and no implicit report read', (kind) => {
  browserTimezone('Europe/Vienna');
  mount([`/performance/${kind}`]);
  expect(screen.getAllByRole('form')).toHaveLength(1);
  expect(screen.getByRole('form', { name: 'Performance-Zeitraum auswählen' })).toBeVisible();
  expect(screen.getAllByLabelText('Von (einschließlich)')).toHaveLength(1);
  expect(screen.getAllByLabelText('Bis (einschließlich)')).toHaveLength(1);
  expect(screen.getAllByLabelText('Berichtszeitzone (IANA)')).toHaveLength(1);
  expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveValue('Europe/Vienna');
  expect(screen.getByLabelText('Berichtswährung')).toHaveAttribute('readonly');
  expect(screen.getByLabelText('Berichtswährung')).toHaveValue('EUR');
  expect(screen.getByRole('heading', { level: 1, name: names[kind] })).toBeVisible();
  expect(screen.getByRole('button', { name: names[kind] })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByRole('button', { name: names[other(kind)] })).toHaveAttribute(
    'aria-pressed',
    'false',
  );
  expect(api.realizedGross).not.toHaveBeenCalled();
  expect(api.closedTrades).not.toHaveBeenCalled();
});

it.each(kinds)(
  'prefers the explicit %s URL zone over the browser and retains a manual correction on switch',
  async (kind) => {
    browserTimezone('Asia/Tokyo');
    const filters = { ...reportFilters, report_timezone: 'America/New_York' };
    mount([reportUrl(kind, filters)]);
    await screen.findByTestId(totalId(kind));
    expectFilters(filters);
    expect(client(kind)).toHaveBeenCalledExactlyOnceWith(filters, expect.any(AbortSignal));
    const details = screen.getByText('Herkunft der Berichtsauswahl').closest('details')!;
    expect(details).not.toHaveAttribute('open');
    fireEvent.click(screen.getByText('Herkunft der Berichtsauswahl'));
    expect(details).toHaveAttribute('open');
    expect(details).toHaveTextContent('Ein eindeutiger Berichtskontext im Link');
    const corrected = { ...filters, report_timezone: 'Europe/Vienna' };
    fireEvent.change(screen.getByLabelText('Berichtszeitzone (IANA)'), {
      target: { value: corrected.report_timezone },
    });
    expect(client(kind)).toHaveBeenCalledOnce();
    expect(client(other(kind))).not.toHaveBeenCalled();
    switchTo(other(kind));
    await screen.findByTestId(totalId(other(kind)));
    expectFilters(corrected);
    expect(client(other(kind))).toHaveBeenCalledExactlyOnceWith(corrected, expect.any(AbortSignal));
  },
);

it.each(kinds)('never repairs an invalid %s URL zone with the browser suggestion', (kind) => {
  browserTimezone('Europe/Vienna');
  mount([reportUrl(kind, { ...reportFilters, report_timezone: 'Not/AZone' })]);
  expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveValue('Not/AZone');
  expect(screen.getByRole('alert')).toBeVisible();
  expect(api.realizedGross).not.toHaveBeenCalled();
  expect(api.closedTrades).not.toHaveBeenCalled();
});

it.each(kinds)(
  'switches from %s using the visible valid draft, with only target defaults and one active report',
  async (kind) => {
    const target = other(kind);
    const { router } = mount([
      reportUrl(kind, reportFilters, {
        report_view: kind === 'realized-gross' ? 'usable' : 'qualified',
        report_page: '2',
        report_basis: kind === 'realized-gross' ? sellBasis : closedBasis,
      }),
    ]);
    await screen.findByTestId(totalId(kind));
    const draft = { ...closedTradeFilters, report_timezone: 'Asia/Tokyo' };
    setFilters(draft);
    expect(screen.queryByTestId(totalId(kind))).not.toBeInTheDocument();
    expect(client(kind)).toHaveBeenCalledOnce();
    expect(client(target)).not.toHaveBeenCalled();
    switchTo(target);
    await screen.findByTestId(totalId(target));
    expectFilters(draft);
    expect(router.state.location.pathname).toBe(`/performance/${target}`);
    const query = new URLSearchParams(router.state.location.search);
    expect(Object.fromEntries(query)).toEqual({
      report_context: target,
      ...draft,
      report_view: 'candidates',
      report_page: '1',
    });
    expect(client(target)).toHaveBeenCalledExactlyOnceWith(draft, expect.any(AbortSignal));
    expect(client(kind)).toHaveBeenCalledOnce();
    expect(screen.getAllByRole('form')).toHaveLength(1);
    expect(screen.queryByTestId(totalId(kind))).not.toBeInTheDocument();
    expect(screen.getAllByTestId(totalId(target))).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1, name: names[target] })).toBeVisible();
    expect(screen.getByRole('button', { name: names[target] })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(
      screen.queryByRole('region', { name: 'Basisstatistiken des Abschlussberichts' }) !== null,
    ).toBe(target === 'closed-trades');
  },
);

it.each(kinds)(
  'loads a complete %s URL once and never duplicates submit plus router reads',
  async (kind) => {
    const { router } = mount([reportUrl(kind)]);
    await screen.findByTestId(totalId(kind));
    expect(client(kind)).toHaveBeenCalledExactlyOnceWith(reportFilters, expect.any(AbortSignal));
    const draft = { ...reportFilters, to_date: '2026-09-15' };
    setFilters(draft);
    expect(client(kind)).toHaveBeenCalledOnce();
    submit();
    await screen.findByTestId(totalId(kind));
    expect(client(kind)).toHaveBeenCalledTimes(2);
    expect(new URLSearchParams(router.state.location.search).get('to_date')).toBe(draft.to_date);
    submit();
    await screen.findByTestId(totalId(kind));
    expect(client(kind)).toHaveBeenCalledTimes(3);
    expect(client(other(kind))).not.toHaveBeenCalled();
  },
);

it('restores both report modes and their applied filters through back, forward, and a fresh router', async () => {
  const first = mount([reportUrl('realized-gross')]);
  await screen.findByTestId('realized-gross-total');
  const changed = { ...closedTradeFilters, report_timezone: 'Etc/UTC' };
  setFilters(changed);
  switchTo('closed-trades');
  await screen.findByTestId('closed-trades-total');
  const closedUrl = first.router.state.location.pathname + first.router.state.location.search;
  fireEvent.change(screen.getByLabelText('Berichtszeitzone (IANA)'), {
    target: { value: 'Unapplied/Zone' },
  });
  await act(() => first.router.navigate(-1));
  await screen.findByTestId('realized-gross-total');
  expectFilters(reportFilters);
  expect(screen.queryByTestId('closed-trades-total')).not.toBeInTheDocument();
  await act(() => first.router.navigate(1));
  await screen.findByTestId('closed-trades-total');
  expectFilters(changed);
  expect(first.router.state.location.pathname + first.router.state.location.search).toBe(closedUrl);
  expect(api.realizedGross).toHaveBeenCalledTimes(2);
  expect(api.closedTrades).toHaveBeenCalledTimes(2);
  first.unmount();
  mount([closedUrl]);
  await screen.findByTestId('closed-trades-total');
  expectFilters(changed);
  expect(api.closedTrades).toHaveBeenCalledTimes(3);
  expect(api.realizedGross).toHaveBeenCalledTimes(2);
});

it.each(kinds)('restores an unapplied draft on same-filter %s POP navigation', async (kind) => {
  const view = kind === 'realized-gross' ? 'usable' : 'qualified';
  const { router } = mount([
    reportUrl(kind, reportFilters, { report_view: view }),
    reportUrl(kind, reportFilters, { report_view: 'all' }),
  ]);
  await screen.findByTestId(totalId(kind));
  fireEvent.change(screen.getByLabelText('Berichtszeitzone (IANA)'), {
    target: { value: 'Not/Applied' },
  });
  await act(() => router.navigate(-1));
  await screen.findByTestId(totalId(kind));
  expectFilters(reportFilters);
  expect(screen.getByLabelText('Zeilen anzeigen')).toHaveValue(view);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it.each(kinds)(
  'keeps invalid %s draft fields and focuses their error instead of switching or reading',
  async (kind) => {
    const { router } = mount([reportUrl(kind)]);
    await screen.findByTestId(totalId(kind));
    const original = router.state.location.pathname + router.state.location.search;
    fireEvent.change(screen.getByLabelText('Von (einschließlich)'), {
      target: { value: '2026-10-01' },
    });
    switchTo(other(kind));
    expect(screen.getByLabelText('Von (einschließlich)')).toHaveValue('2026-10-01');
    expect(screen.getByLabelText('Bis (einschließlich)')).toHaveValue(reportFilters.to_date);
    expect(screen.getByLabelText('Von (einschließlich)')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Von (einschließlich)')).toHaveFocus();
    expect(screen.getByRole('alert')).toHaveTextContent('Von darf nicht nach Bis liegen');
    expect(router.state.location.pathname + router.state.location.search).toBe(original);
    expect(client(kind)).toHaveBeenCalledOnce();
    expect(client(other(kind))).not.toHaveBeenCalled();
    expect(screen.queryByTestId(totalId(kind))).not.toBeInTheDocument();
    submit();
    expect(client(kind)).toHaveBeenCalledOnce();
    expect(screen.getByLabelText('Von (einschließlich)')).toHaveValue('2026-10-01');
  },
);

it.each(kinds.flatMap((kind) => ['+01:00', '-0230'].map((zone) => ({ kind, zone }))))(
  'rejects an explicit $kind offset zone $zone without reading or repairing on switch',
  ({ kind, zone }) => {
    const original = reportUrl(kind, { ...reportFilters, report_timezone: zone });
    const { router } = mount([original]);
    expect(api.realizedGross).not.toHaveBeenCalled();
    expect(api.closedTrades).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(/Berichtszeitzone|Kontext/i);
    expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveValue(zone);
    switchTo(other(kind));
    expect(router.state.location.pathname + router.state.location.search).toBe(original);
    expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveValue(zone);
    expect(api.realizedGross).not.toHaveBeenCalled();
    expect(api.closedTrades).not.toHaveBeenCalled();
  },
);

it.each(kinds)(
  'keeps the invalid offset draft and field focus when switching from %s',
  async (kind) => {
    const { router } = mount([reportUrl(kind)]);
    await screen.findByTestId(totalId(kind));
    const original = router.state.location.pathname + router.state.location.search;
    fireEvent.change(screen.getByLabelText('Berichtszeitzone (IANA)'), {
      target: { value: '+01:00' },
    });
    switchTo(other(kind));
    expect(client(kind)).toHaveBeenCalledOnce();
    expect(client(other(kind))).not.toHaveBeenCalled();
    expect(router.state.location.pathname + router.state.location.search).toBe(original);
    expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveValue('+01:00');
    expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveAttribute(
      'aria-invalid',
      'true',
    );
    expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveFocus();
    expect(screen.getByRole('alert')).toHaveTextContent(/Berichtszeitzone/);
    expect(screen.queryByTestId(totalId(kind))).not.toBeInTheDocument();
  },
);

it.each(kinds)(
  'accepts the IANA Etc/GMT+1 identifier on %s and preserves it across modes',
  async (kind) => {
    const filters = { ...reportFilters, report_timezone: 'Etc/GMT+1' };
    mount([reportUrl(kind, filters)]);
    await screen.findByTestId(totalId(kind));
    expect(client(kind)).toHaveBeenCalledExactlyOnceWith(filters, expect.any(AbortSignal));
    expectFilters(filters);
    switchTo(other(kind));
    await screen.findByTestId(totalId(other(kind)));
    expect(client(other(kind))).toHaveBeenCalledExactlyOnceWith(filters, expect.any(AbortSignal));
    expectFilters(filters);
  },
);

const invalidContexts = [
  ['duplicate date', (q: URLSearchParams) => q.append('from_date', reportFilters.from_date)],
  ['duplicate mode', (q: URLSearchParams) => q.append('report_context', q.get('report_context')!)],
  ['empty date', (q: URLSearchParams) => q.set('from_date', '')],
  ['impossible date', (q: URLSearchParams) => q.set('from_date', '2026-02-30')],
  ['reverse interval', (q: URLSearchParams) => q.set('from_date', '2026-10-01')],
  ['unknown zone', (q: URLSearchParams) => q.set('report_timezone', 'Not/AZone')],
  ['incomplete filters', (q: URLSearchParams) => q.delete('report_timezone')],
  ['missing mode', (q: URLSearchParams) => q.delete('report_context')],
  [
    'wrong mode',
    (q: URLSearchParams) => q.set('report_context', other(q.get('report_context') as Kind)),
  ],
  ['empty page', (q: URLSearchParams) => q.set('report_page', '')],
  ['empty basis', (q: URLSearchParams) => q.set('report_basis', '')],
  ['duplicate view', (q: URLSearchParams) => q.append('report_view', 'all')],
] as const;

it.each(
  kinds.flatMap((kind) => invalidContexts.map(([label, change]) => ({ kind, label, change }))),
)(
  'rejects $kind $label context and requires explicit adoption even after valid editing',
  async ({ kind, change }) => {
    const query = new URLSearchParams(reportUrl(kind).split('?')[1]);
    change(query);
    const original = `/performance/${kind}?${query}`;
    const { router } = mount([original]);
    expect(screen.getByRole('alert')).toHaveTextContent(/Ungültig|mehrdeutig/i);
    expect(api.realizedGross).not.toHaveBeenCalled();
    expect(api.closedTrades).not.toHaveBeenCalled();
    switchTo(other(kind));
    expect(router.state.location.pathname + router.state.location.search).toBe(original);
    setFilters(reportFilters);
    switchTo(other(kind));
    expect(router.state.location.pathname + router.state.location.search).toBe(original);
    expect(api.realizedGross).not.toHaveBeenCalled();
    expect(api.closedTrades).not.toHaveBeenCalled();
    submit();
    await screen.findByTestId(totalId(kind));
    expectFilters(reportFilters);
    expect(client(kind)).toHaveBeenCalledExactlyOnceWith(reportFilters, expect.any(AbortSignal));
    expect(client(other(kind))).not.toHaveBeenCalled();
  },
);

it.each(kinds)(
  'never silently converts a non-EUR %s link during report switching',
  async (kind) => {
    const original = reportUrl(kind, { ...reportFilters, report_currency: 'USD' });
    const { router } = mount([original]);
    expect(screen.getByRole('alert')).toHaveTextContent(/USD/);
    expect(screen.getByRole('alert')).toHaveTextContent(/EUR/);
    expect(screen.getByLabelText('Berichtswährung')).toHaveValue('EUR');
    switchTo(other(kind));
    expect(router.state.location.pathname + router.state.location.search).toBe(original);
    expect(api.realizedGross).not.toHaveBeenCalled();
    expect(api.closedTrades).not.toHaveBeenCalled();
    setFilters(reportFilters);
    submit();
    await screen.findByTestId(totalId(kind));
    expect(client(kind)).toHaveBeenCalledExactlyOnceWith(reportFilters, expect.any(AbortSignal));
    expect(new URLSearchParams(router.state.location.search).get('report_currency')).toBe('EUR');
    expect(client(other(kind))).not.toHaveBeenCalled();
  },
);

it.each(['success', 'failure'] as const)(
  'invalidates both earlier mode generations during SELL → closed → SELL, including late %s',
  async (outcome) => {
    const firstSell = deferred<RealizedGrossReport>();
    const closed = deferred<ClosedTradeReport>();
    const latestSell = deferred<RealizedGrossReport>();
    api.realizedGross
      .mockReturnValueOnce(firstSell.promise)
      .mockReturnValueOnce(latestSell.promise);
    api.closedTrades.mockReturnValueOnce(closed.promise);
    mount([reportUrl('realized-gross')]);
    await waitFor(() => expect(api.realizedGross).toHaveBeenCalledOnce());
    const firstSignal = api.realizedGross.mock.calls[0][1];
    switchTo('closed-trades');
    await waitFor(() => expect(api.closedTrades).toHaveBeenCalledOnce());
    const closedSignal = api.closedTrades.mock.calls[0][1];
    switchTo('realized-gross');
    await waitFor(() => expect(api.realizedGross).toHaveBeenCalledTimes(2));
    expect(firstSignal?.aborted).toBe(true);
    expect(closedSignal?.aborted).toBe(true);
    const corrected = sellReport();
    corrected.basis.id = 'c'.repeat(64);
    corrected.summary = { ...corrected.summary, total: '30', total_display: '30.00' };
    corrected.items[1] = {
      ...corrected.items[1],
      execution_id: 'current-replacement',
      price_per_unit: '3.0000000000',
      realized_gross_pnl_delta: '0',
      realized_gross_pnl_delta_display: '0.00',
    };
    await act(async () => {
      latestSell.resolve(corrected);
      await latestSell.promise;
    });
    expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('30,00 EUR');
    await act(async () => {
      if (outcome === 'success') {
        firstSell.resolve(sellReport());
        closed.resolve(closedReport());
      } else {
        firstSell.reject(new Error('Veralteter Verkaufsfehler'));
        closed.reject(new Error('Veralteter Abschlussfehler'));
      }
      await Promise.allSettled([firstSell.promise, closed.promise]);
    });
    expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('30,00 EUR');
    expect(screen.getByRole('article', { name: 'Verkauf current-replacement' })).toBeVisible();
    expect(screen.queryByTestId('closed-trades-total')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(api.realizedGross).toHaveBeenCalledTimes(2);
    expect(api.closedTrades).toHaveBeenCalledOnce();
  },
);

it('invalidates same-mode A → B → A filter requests and never restores the first A', async () => {
  const first = deferred<ClosedTradeReport>();
  const middle = deferred<ClosedTradeReport>();
  const last = deferred<ClosedTradeReport>();
  api.closedTrades
    .mockReturnValueOnce(first.promise)
    .mockReturnValueOnce(middle.promise)
    .mockReturnValueOnce(last.promise);
  mount([reportUrl('closed-trades')]);
  await waitFor(() => expect(api.closedTrades).toHaveBeenCalledOnce());
  setFilters({ ...reportFilters, report_timezone: 'Etc/UTC' });
  submit();
  await waitFor(() => expect(api.closedTrades).toHaveBeenCalledTimes(2));
  setFilters(reportFilters);
  submit();
  await waitFor(() => expect(api.closedTrades).toHaveBeenCalledTimes(3));
  const corrected = closedReport();
  corrected.basis.id = 'd'.repeat(64);
  corrected.statistics = closedTradeStatistics({
    report_basis_id: corrected.basis.id,
    average_gross_pnl: { raw: '70', display: '70.00', reason: null },
    median_gross_pnl: { raw: '70', display: '70.00', reason: null },
  });
  corrected.summary = { ...corrected.summary, total: '70', total_display: '70.00' };
  corrected.items[0] = {
    ...corrected.items[0],
    realized_gross_pnl: '70',
    realized_gross_pnl_display: '70.00',
  };
  await act(async () => {
    last.resolve(corrected);
    await last.promise;
  });
  await act(async () => {
    middle.reject(new Error('Veralteter Zonenfehler'));
    first.resolve(closedReport());
    await Promise.allSettled([first.promise, middle.promise]);
  });
  expect(screen.getByTestId('closed-trades-total')).toHaveTextContent('70,00 EUR');
  expect(screen.getByTestId('closed-trades-average-gross-pnl')).toHaveTextContent('70,00 EUR');
  expect(screen.getByTestId('closed-trades-median-gross-pnl')).toHaveTextContent('70,00 EUR');
  expectFilters(reportFilters);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(api.closedTrades.mock.calls[0][1]?.aborted).toBe(true);
  expect(api.closedTrades.mock.calls[1][1]?.aborted).toBe(true);
  expect(api.realizedGross).not.toHaveBeenCalled();
});

it.each(kinds)('rejects a %s response with the other report definition', async (kind) => {
  if (kind === 'realized-gross') {
    api.realizedGross.mockResolvedValue({
      ...sellReport(),
      definition_version: 'closed-trade-gross-v1',
    });
  } else {
    api.closedTrades.mockResolvedValue({
      ...closedReport(),
      definition_version: 'realized-gross-sell-v2',
    });
  }
  mount([reportUrl(kind)]);
  expect(await screen.findByRole('alert')).toHaveTextContent('Die Antwort gehört nicht');
  expect(screen.queryByTestId(totalId(kind))).not.toBeInTheDocument();
  expect(
    screen.queryByRole('region', { name: 'Basisstatistiken des Abschlussberichts' }),
  ).not.toBeInTheDocument();
});

it.each(['definition', 'basis', 'status'] as const)(
  'rejects mismatched closed statistic %s and retains the visible draft',
  async (field) => {
    const report = closedReport();
    if (field === 'definition') report.statistics.definition_version = 'different-statistics';
    if (field === 'basis') report.statistics.report_basis_id = 'f'.repeat(64);
    if (field === 'status') report.statistics.report_status = 'PARTIAL';
    api.closedTrades.mockResolvedValue(report);
    mount([reportUrl('closed-trades')]);
    expect(await screen.findByRole('alert')).toHaveTextContent('Die Kennzahlen gehören nicht');
    expectFilters(reportFilters);
    expect(screen.queryByTestId('closed-trades-total')).not.toBeInTheDocument();
    expect(screen.queryByTestId('closed-trades-win-rate')).not.toBeInTheDocument();
  },
);

it.each(kinds)(
  'keeps the %s draft through a read failure and allows a deliberate mode switch with it',
  async (kind) => {
    const pending =
      kind === 'realized-gross'
        ? api.realizedGross.mockRejectedValueOnce(
            new Error('REPORT_READ_UNAVAILABLE: Quellenstand nicht verfügbar'),
          )
        : api.closedTrades.mockRejectedValueOnce(
            new Error('REPORT_READ_UNAVAILABLE: Quellenstand nicht verfügbar'),
          );
    const draft = { ...closedTradeFilters, report_timezone: 'America/New_York' };
    mount([`/performance/${kind}`]);
    setFilters(draft);
    submit();
    expect(await screen.findByRole('alert')).toHaveTextContent('Quellenstand nicht verfügbar');
    expectFilters(draft);
    expect(screen.queryByTestId(totalId(kind))).not.toBeInTheDocument();
    expect(pending).toHaveBeenCalledOnce();
    switchTo(other(kind));
    await screen.findByTestId(totalId(other(kind)));
    expectFilters(draft);
    expect(client(other(kind))).toHaveBeenCalledExactlyOnceWith(draft, expect.any(AbortSignal));
  },
);

it('supports SELL page 101, sources and row filters locally, then transparently clamps after a shorter read', async () => {
  const report = sellReport();
  report.items = Array.from({ length: 2001 }, (_, index) => reportItem(`sell-${index}`));
  report.counts = {
    ...report.counts,
    examined: 2001,
    in_period: 2001,
    usable: 2001,
    candidates: 2001,
  };
  api.realizedGross.mockResolvedValueOnce(report);
  const { router } = mount([
    reportUrl('realized-gross', reportFilters, { report_view: 'all', report_page: '101' }),
  ]);
  await screen.findByTestId('realized-gross-total');
  expect(screen.getByText(/Seite 101 von 101/)).toBeVisible();
  expect(screen.getAllByRole('article')).toHaveLength(1);
  expect(screen.getByRole('article', { name: 'Verkauf sell-2000' })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Quellen und Berechnung' }));
  expect(screen.getByRole('region', { name: 'Herkunft SELL sell-2000' })).toBeVisible();
  expect(
    screen.getByRole('link', { name: 'Buchungen und Währungsbestätigungen im Trade prüfen' }),
  ).toHaveAttribute('href', '/trade-management?trade_id=trade-1#execution-dates');
  fireEvent.click(screen.getByRole('button', { name: 'Vorherige Seite' }));
  expect(screen.getByText(/Seite 100 von 101/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Nächste Seite' }));
  expect(new URLSearchParams(router.state.location.search).get('report_page')).toBe('101');
  expect(api.realizedGross).toHaveBeenCalledOnce();
  expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('10,00 EUR');
  submit();
  await screen.findByText(/Die ursprüngliche Seite 101 ist/);
  expect(screen.getByText(/Seite 1 von 1/)).toBeVisible();
  expect(api.realizedGross).toHaveBeenCalledTimes(2);
  fireEvent.change(screen.getByLabelText('Zeilen anzeigen'), { target: { value: 'usable' } });
  expect(new URLSearchParams(router.state.location.search).get('report_view')).toBe('usable');
  expect(new URLSearchParams(router.state.location.search).get('report_page')).toBe('1');
  expect(api.realizedGross).toHaveBeenCalledTimes(2);
  expect(api.closedTrades).not.toHaveBeenCalled();
});

it('keeps closed pagination, statistics and source links bound to one response without extra reads', async () => {
  const report = closedReport();
  report.items = Array.from({ length: 21 }, (_, index) => closedTradeItem(`trade-${index}`));
  report.counts = { ...report.counts, examined: 21, qualified: 21, in_period: 21, positive: 21 };
  report.statistics = closedTradeStatistics({ population: 21 });
  api.closedTrades.mockResolvedValue(report);
  const foreignRequest = vi
    .spyOn(globalThis, 'fetch')
    .mockRejectedValue(new Error('Unexpected network request'));
  const { router } = mount([reportUrl('closed-trades')]);
  await screen.findByTestId('closed-trades-total');
  const statisticText = screen.getByRole('region', {
    name: 'Basisstatistiken des Abschlussberichts',
  }).textContent;
  fireEvent.change(screen.getByLabelText('Zeilen anzeigen'), { target: { value: 'qualified' } });
  fireEvent.click(screen.getByRole('button', { name: 'Nächste Seite' }));
  const row = within(screen.getByRole('article', { name: 'Trade trade-20' }));
  fireEvent.click(row.getByRole('button', { name: 'Quellen und Gesamtverlauf' }));
  expect(screen.getByRole('region', { name: 'Herkunft Trade trade-20' })).toBeVisible();
  const link = new URL(
    row.getByRole('link', { name: 'Trade trade-20 prüfen' }).getAttribute('href')!,
    'http://local',
  );
  expect(link.pathname).toBe('/trade-management');
  expect(link.searchParams.get('view')).toBe('sources');
  expect(link.searchParams.get('trade_id')).toBe('trade-20');
  expect(link.searchParams.get('report_view')).toBe('qualified');
  expect(link.searchParams.get('report_page')).toBe('2');
  expect(link.searchParams.get('report_basis')).toBe(report.basis.id);
  expect(new URLSearchParams(router.state.location.search).get('report_page')).toBe('2');
  expect(
    screen.getByRole('region', { name: 'Basisstatistiken des Abschlussberichts' }).textContent,
  ).toBe(statisticText);
  expect(screen.getByTestId('closed-trades-total')).toHaveTextContent('50,00 EUR');
  expect(api.closedTrades).toHaveBeenCalledOnce();
  expect(api.realizedGross).not.toHaveBeenCalled();
  expect(foreignRequest).not.toHaveBeenCalled();
});

it('compares source fingerprints only within the same mode and full filter context', async () => {
  const { router } = mount([
    reportUrl('realized-gross', reportFilters, { report_basis: sellBasis }),
  ]);
  await screen.findByTestId('realized-gross-total');
  switchTo('closed-trades');
  await screen.findByTestId('closed-trades-total');
  expect(screen.queryByText(/Der Quellenstand hat sich/)).not.toBeInTheDocument();
  expect(new URLSearchParams(router.state.location.search).has('report_basis')).toBe(false);
  switchTo('realized-gross');
  await screen.findByTestId('realized-gross-total');
  expect(screen.queryByText(/Der Quellenstand hat sich/)).not.toBeInTheDocument();
  const corrected = sellReport();
  corrected.basis.id = 'e'.repeat(64);
  api.realizedGross.mockResolvedValueOnce(corrected);
  submit();
  expect(await screen.findByText(/Der Quellenstand hat sich/)).toBeVisible();
  setFilters({ ...reportFilters, report_timezone: 'Etc/UTC' });
  submit();
  await screen.findByTestId('realized-gross-total');
  expect(screen.queryByText(/Der Quellenstand hat sich/)).not.toBeInTheDocument();
});

it('retains the existing reference distinction: September SELL 10 versus no full close, October SELL 30 versus lifetime 50', async () => {
  const septemberClosed = closedReport();
  septemberClosed.summary = {
    ...septemberClosed.summary,
    status: 'EMPTY',
    total: '0',
    total_display: '0.00',
  };
  septemberClosed.items = [
    closedTradeItem('trade-1', {
      group: 'OUTSIDE_PERIOD',
      status: 'EXCLUDED',
      reasons: ['OUTSIDE_PERIOD'],
      period_status: 'OUTSIDE_PERIOD',
      realized_gross_pnl: null,
      realized_gross_pnl_display: null,
      classification: null,
    }),
  ];
  septemberClosed.counts = {
    ...septemberClosed.counts,
    qualified: 0,
    in_period: 0,
    positive: 0,
    outside_period: 1,
  };
  septemberClosed.statistics = unavailableClosedTradeStatistics('EMPTY');
  api.closedTrades.mockResolvedValueOnce(septemberClosed);
  mount([reportUrl('realized-gross')]);
  expect(await screen.findByTestId('realized-gross-total')).toHaveTextContent('10,00 EUR');
  switchTo('closed-trades');
  expect(await screen.findByTestId('closed-trades-total')).toHaveTextContent('0,00 EUR');
  expect(
    screen.getByRole('heading', { name: 'Keine abgeschlossenen Trades in dieser Auswahl' }),
  ).toBeVisible();
  setFilters(closedTradeFilters);
  submit();
  expect(await screen.findByTestId('closed-trades-total')).toHaveTextContent('50,00 EUR');
  const octoberSells = sellReport(closedTradeFilters);
  octoberSells.summary = { ...octoberSells.summary, total: '30.00', total_display: '30.00' };
  api.realizedGross.mockResolvedValueOnce(octoberSells);
  switchTo('realized-gross');
  expect(await screen.findByTestId('realized-gross-total')).toHaveTextContent('30,00 EUR');
  expect(screen.queryByTestId('closed-trades-total')).not.toBeInTheDocument();
  expect(
    screen.queryByRole('region', { name: 'Basisstatistiken des Abschlussberichts' }),
  ).not.toBeInTheDocument();
});
