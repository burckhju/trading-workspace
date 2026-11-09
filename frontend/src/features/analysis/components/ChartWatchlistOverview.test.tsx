import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { watchlistFixture, watchlistSeries } from '../../../test/watchlistFixtures';
import { chartClient } from '../services/chartClient';
import { watchlistClient } from '../services/watchlistClient';
import type { ChartWatchlist } from '../types/watchlist';
import { ChartWatchlistOverview } from './ChartWatchlistOverview';

vi.mock('../services/chartClient', () => ({
  chartClient: { series: vi.fn(), invalidateTargets: vi.fn() },
}));
vi.mock('../services/watchlistClient', () => ({
  watchlistClient: { read: vi.fn(), activate: vi.fn() },
}));
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}));

let model: ChartWatchlist;
beforeEach(() => {
  model = watchlistFixture(31);
  vi.mocked(watchlistClient.read)
    .mockReset()
    .mockImplementation(() => Promise.resolve(structuredClone(model)));
  vi.mocked(watchlistClient.activate)
    .mockReset()
    .mockImplementation(() => {
      model = watchlistFixture(31);
      return Promise.resolve(structuredClone(model));
    });
  vi.mocked(chartClient.series)
    .mockReset()
    .mockImplementation((keys, start, end, field) =>
      Promise.resolve(watchlistSeries(keys[0], start, end, field)),
    );
});

function show(onOpenDetail = vi.fn()) {
  return {
    onOpenDetail,
    ...render(
      <ChartWatchlistOverview
        end="2026-10-04"
        period="3"
        field="CLOSE"
        onOpenDetail={onOpenDetail}
      />,
    ),
  };
}

describe('ChartWatchlistOverview', () => {
  it('shows all 31 independent charts and makes local filter, evidence and comparison interactions read-free', async () => {
    const user = userEvent.setup();
    const { onOpenDetail } = show();
    await waitFor(() => expect(screen.getAllByTestId(/^watchlist-chart-/)).toHaveLength(31));
    expect(screen.getAllByRole('article')).toHaveLength(31);
    expect(chartClient.series).toHaveBeenCalledTimes(31);
    expect(watchlistClient.activate).not.toHaveBeenCalled();
    expect(screen.getAllByRole('link', { name: /quelle/i })).toHaveLength(31);
    expect(screen.getAllByText(/Letzte Beobachtung im Zeitraum: 03.09.2026/)).toHaveLength(31);
    const cards = screen.getAllByRole('article');
    expect(within(cards[0]).getAllByText(/Indexpunkte/).length).toBeGreaterThan(0);
    expect(within(cards[1]).getAllByText(/USD/).length).toBeGreaterThan(0);
    await user.click(within(cards[0]).getByText('Werte, Quellen und Einrichtung'));
    expect(await within(cards[0]).findByRole('table')).toHaveTextContent('EOD');
    expect(within(cards[0]).getAllByText('Unbekannt')).toHaveLength(3);
    for (const card of cards.slice(0, 4)) await user.click(within(card).getByRole('checkbox'));
    expect(within(cards[4]).getByRole('checkbox')).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Auswahl vergleichen (4/4)' }));
    expect(onOpenDetail).toHaveBeenCalledWith(
      model.items.slice(0, 4).map((item) => item.target_key),
    );
    await user.type(screen.getByLabelText('Übersicht filtern'), 'ETF 30');
    expect(screen.getAllByRole('article')).toHaveLength(1);
    await user.clear(screen.getByLabelText('Übersicht filtern'));
    await user.selectOptions(screen.getByLabelText('Gruppe'), 'Index');
    expect(screen.getAllByRole('article')).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: 'Detaildiagramm öffnen' }));
    expect(onOpenDetail).toHaveBeenLastCalledWith(['reference:sp500']);
    expect(chartClient.series).toHaveBeenCalledTimes(31);
    expect(watchlistClient.read).toHaveBeenCalledTimes(1);
  });

  it('activates the visible catalog once, then shows actual pending and blocked item states', async () => {
    const user = userEvent.setup();
    model = watchlistFixture(31, false);
    let finish!: (value: ChartWatchlist) => void;
    vi.mocked(watchlistClient.activate).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    show();
    const activate = await screen.findByRole('button', { name: 'Marktübersicht einrichten' });
    expect(screen.getAllByRole('article')).toHaveLength(31);
    expect(screen.getByText(/als Kursindex ohne Dividenden eingerichtet/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /FRED/ })).toHaveAttribute(
      'href',
      'https://fred.stlouisfed.org/series/SP500',
    );
    expect(chartClient.series).not.toHaveBeenCalled();
    fireEvent.click(activate);
    fireEvent.click(activate);
    expect(watchlistClient.activate).toHaveBeenCalledExactlyOnceWith(model.catalog_version);
    expect(activate).toBeDisabled();
    const accepted = watchlistFixture(31, false);
    accepted.enabled = true;
    accepted.items[1].setup_status = 'BLOCKED';
    accepted.items[1].setup_reason = 'EODHD_MAPPING_IDENTITY_CONFLICT';
    await act(() => {
      finish(accepted);
      return Promise.resolve();
    });
    expect(await screen.findByRole('status')).toHaveTextContent('dauerhaft aktiviert');
    expect(screen.getByText('Einrichtung blockiert')).toBeInTheDocument();
    await user.click(
      within(screen.getAllByRole('article')[1]).getByText('Werte, Quellen und Einrichtung'),
    );
    expect(await screen.findByText('EODHD_MAPPING_IDENTITY_CONFLICT')).toBeInTheDocument();
    expect(screen.getAllByText('Einrichtung ausstehend')).toHaveLength(30);
    expect(chartClient.series).not.toHaveBeenCalled();
    expect(
      screen.queryByRole('button', { name: 'Marktübersicht einrichten' }),
    ).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Gruppe'), 'Index');
    expect(watchlistClient.activate).toHaveBeenCalledTimes(1);
  });

  it('does not replay an uncertain activation and recovers through a stored status read', async () => {
    const user = userEvent.setup();
    model = watchlistFixture(31, false);
    vi.mocked(watchlistClient.activate).mockRejectedValueOnce(new Error('Transport unterbrochen'));
    show();
    await user.click(await screen.findByRole('button', { name: 'Marktübersicht einrichten' }));
    expect(await screen.findByText(/Der Ausgang ist nicht bestätigt/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Marktübersicht einrichten' })).toBeDisabled();
    model = watchlistFixture(31);
    await user.click(screen.getByRole('button', { name: 'Gespeicherten Stand erneut lesen' }));
    expect(await screen.findByText(/Diese Auswahl ist dauerhaft gespeichert/)).toBeInTheDocument();
    expect(watchlistClient.activate).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('polls only while visible and reloads a series only after its stored evidence changes', async () => {
    model = watchlistFixture(2);
    const timers = vi.spyOn(window, 'setInterval');
    const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
    show();
    await waitFor(() => expect(screen.getAllByTestId(/^watchlist-chart-/)).toHaveLength(2));
    const poll = timers.mock.calls.find(([, interval]) => interval === 60_000)![0] as () => void;
    model.items[0].refresh = {
      status: 'ERROR',
      reason: 'EODHD_REQUEST_FAILED',
      checked_at: '2026-11-09T09:00:00Z',
      last_success_at: null,
      next_run_at: null,
      scope: 'PROCESS_LOCAL',
    };
    await act(() => {
      poll();
      return Promise.resolve();
    });
    expect(watchlistClient.read).toHaveBeenCalledTimes(2);
    expect(chartClient.series).toHaveBeenCalledTimes(2);
    expect(screen.getByText('Abruf fehlgeschlagen · ERROR')).toBeInTheDocument();
    visibility.mockReturnValue('hidden');
    await act(() => {
      poll();
      return Promise.resolve();
    });
    expect(watchlistClient.read).toHaveBeenCalledTimes(2);
    visibility.mockReturnValue('visible');
    model.items[1].history.last_received_at = '2026-11-09T09:00:00Z';
    await act(() => {
      poll();
      return Promise.resolve();
    });
    await waitFor(() => expect(chartClient.series).toHaveBeenCalledTimes(3));
    expect(chartClient.series).toHaveBeenLastCalledWith(
      ['listing:etf-1'],
      '2026-07-04',
      '2026-10-04',
      'CLOSE',
      expect.any(AbortSignal),
    );
  });

  it('keeps the last read separate from a status error and explains disabled automation', async () => {
    const user = userEvent.setup();
    model = watchlistFixture(1);
    model.scheduler.enabled = false;
    model.scheduler.running = false;
    model.scheduler.leader = false;
    model.scheduler.last_error = 'CONFIGURATION_REQUIRED';
    model.scheduler.provider_enabled = false;
    show();
    expect(
      await screen.findByText(/Kursaktualisierung ist derzeit ausgeschaltet/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Aktualisierungsfehler: CONFIGURATION_REQUIRED/)).toBeInTheDocument();
    expect(screen.getByText(/EODHD ist ausgeschaltet. Neue Providerabrufe/)).toBeInTheDocument();
    vi.mocked(watchlistClient.read).mockRejectedValueOnce(new Error('Status nicht erreichbar'));
    await user.click(screen.getByRole('button', { name: 'Gespeicherten Stand erneut lesen' }));
    expect(await screen.findByText(/Der zuvor gelesene Stand bleibt sichtbar/)).toHaveTextContent(
      'Status nicht erreichbar',
    );
    expect(screen.getAllByRole('article')).toHaveLength(1);
  });

  it('leaves a failed initial read retryable without creating membership', async () => {
    const user = userEvent.setup();
    vi.mocked(watchlistClient.read).mockRejectedValueOnce(new Error('Lesefehler'));
    show();
    expect(await screen.findByText('Lesefehler')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Marktübersicht einrichten' }),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Gespeicherten Stand erneut lesen' }));
    expect(await screen.findAllByRole('article')).toHaveLength(31);
    expect(watchlistClient.activate).not.toHaveBeenCalled();
  });

  it('rejects an activation receipt for a different visible membership', async () => {
    const user = userEvent.setup();
    model = watchlistFixture(31, false);
    vi.mocked(watchlistClient.activate).mockResolvedValueOnce(watchlistFixture(2));
    show();
    await user.click(await screen.findByRole('button', { name: 'Marktübersicht einrichten' }));
    expect(await screen.findByText(/bestätigt nicht die angezeigte Auswahl/)).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(chartClient.series).not.toHaveBeenCalled();
  });
});
