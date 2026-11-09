import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { watchlistFixture, watchlistSeries } from '../../../test/watchlistFixtures';
import type { ChartPlotRow } from '../services/chartPlotRows';
import { parseReferenceDataContext } from '../../administration/services/referenceDataContext';
import { WatchlistChartCard } from './WatchlistChartCard';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  LineChart: ({ children, data }: { children: ReactNode; data: unknown }) => (
    <div data-testid="mini-plot-data" data-points={JSON.stringify(data)}>
      {children}
    </div>
  ),
  CartesianGrid: () => null,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}));

function setup() {
  const item = watchlistFixture(1).items[0];
  const result = watchlistSeries(item.target_key!, '2026-07-04', '2026-10-04');
  return {
    item,
    state: { loading: false, result, error: null },
    selected: false,
    comparisonFull: false,
    onSelect: vi.fn(),
    onOpen: vi.fn(),
    onRetry: vi.fn(),
  };
}

describe('WatchlistChartCard', () => {
  it('preserves unknown basis, gaps, exact original prices and unknown source time', async () => {
    const user = userEvent.setup();
    const props = setup();
    const series = props.state.result.series[0];
    series.return_basis = 'UNKNOWN';
    series.issues = ['RETURN_BASIS_UNKNOWN', 'UNOBSERVED_WEEKDAYS'];
    series.points[1].gap_before = true;
    series.points[1].trading_date = '2026-09-08';
    series.points = series.points.slice(0, 2);
    series.points[0].value = '7688.6222000000';
    series.points[1].value = null;
    render(<WatchlistChartCard {...props} />);
    expect(screen.getByText('Grundlage unbekannt · CLOSE')).toBeInTheDocument();
    expect(screen.getByText(/Feiertage und fehlende Daten/)).toBeInTheDocument();
    const data = JSON.parse(
      screen.getByTestId('mini-plot-data').getAttribute('data-points')!,
    ) as ChartPlotRow[];
    expect(data.map((row) => row.values[0])).toEqual([7688.6222, null, null]);
    expect(screen.getByText('—')).toBeInTheDocument();
    await user.click(screen.getByText('Werte, Quellen und Einrichtung'));
    const table = await screen.findByRole('table');
    expect(within(table).getByText('7688.6222000000')).toBeInTheDocument();
    expect(within(table).getAllByText('Unbekannt')).toHaveLength(2);
    expect(within(table).queryByText(/00:00:00/)).not.toBeInTheDocument();
    expect(props.onRetry).not.toHaveBeenCalled();
  });

  it('exposes all rows through local pagination without fetching again', async () => {
    const user = userEvent.setup();
    const props = setup();
    const series = props.state.result.series[0];
    series.points = Array.from({ length: 64 }, (_, index) => ({
      ...series.points[0],
      trading_date: new Date(Date.UTC(2026, 6, index + 1)).toISOString().slice(0, 10),
      value: String(index),
    }));
    series.observation_count = 64;
    render(<WatchlistChartCard {...props} />);
    await user.click(screen.getByText('Werte, Quellen und Einrichtung'));
    await screen.findByRole('table');
    expect(screen.getByText('Seite 1 / 2')).toBeInTheDocument();
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(51);
    await user.click(screen.getByRole('button', { name: 'Weitere Werte' }));
    expect(screen.getByText('Seite 2 / 2')).toBeInTheDocument();
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(15);
    await user.click(screen.getByRole('button', { name: 'Vorige Werte' }));
    expect(props.onRetry).not.toHaveBeenCalled();
  });

  it('keeps a read error separate from empty history and never links an unsafe source URL', () => {
    const props = setup();
    props.item.source_url = 'javascript:alert(1)';
    render(
      <WatchlistChartCard
        {...props}
        state={{ loading: false, result: null, error: 'Lesefehler' }}
      />,
    );
    expect(screen.getByText('Kurse nicht lesbar: Lesefehler')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Kurse erneut lesen' }));
    expect(props.onRetry).toHaveBeenCalledTimes(1);
  });

  it('keeps process-local refresh failures separate from configured setup and stored prices', () => {
    const props = setup();
    props.item.refresh = {
      status: 'ERROR',
      reason: 'EODHD_REQUEST_FAILED',
      checked_at: '2026-11-09T10:00:00Z',
      last_success_at: null,
      next_run_at: '2026-11-09T11:00:00Z',
      scope: 'PROCESS_LOCAL',
    };
    const view = render(<WatchlistChartCard {...props} />);
    expect(screen.getByText('Datenbasis eingerichtet')).toBeInTheDocument();
    expect(screen.getByText('Abruf fehlgeschlagen · ERROR')).toBeInTheDocument();
    expect(screen.getByText('Abrufgrund: EODHD_REQUEST_FAILED')).toBeInTheDocument();
    expect(screen.getByText(/nach einem Backendneustart nicht fortgeführt/)).toBeInTheDocument();
    expect(
      screen.getByText(/Letzter erfolgreicher Abruf im Prozess.*Nicht belegt/),
    ).toBeInTheDocument();
    expect(screen.getByTestId('watchlist-chart-SP500')).toBeInTheDocument();
    for (const [status, label] of [
      ['BLOCKED', 'Abruf blockiert'],
      ['DEFERRED', 'Abruf zurückgestellt'],
    ]) {
      props.item.refresh = { ...props.item.refresh, status };
      view.rerender(<WatchlistChartCard {...props} />);
      expect(screen.getByText(label + ' · ' + status)).toBeInTheDocument();
      expect(screen.getByText('Datenbasis eingerichtet')).toBeInTheDocument();
    }
    props.item.refresh = null;
    view.rerender(<WatchlistChartCard {...props} />);
    expect(screen.getByText(/Kein Abrufbeleg im aktuellen Backendprozess/)).toBeInTheDocument();
    expect(screen.queryByText(/Abrufgrund:/)).not.toBeInTheDocument();
    expect(screen.getByTestId('watchlist-chart-SP500')).toBeInTheDocument();
    expect(props.onRetry).not.toHaveBeenCalled();
  });

  it('returns from setup to the same historical overview and price field', () => {
    const props = setup();
    props.item.setup_status = 'BLOCKED';
    props.state.result.series[0].identity.setup_url = '/chart-setup?reference_id=sp500';
    render(
      <WatchlistChartCard
        {...props}
        chartParams={
          new URLSearchParams('view=overview&end=2026-10-04&period=6&field=ADJUSTED_CLOSE')
        }
      />,
    );
    const href = screen.getByRole('link', { name: 'Datenbasis prüfen' }).getAttribute('href')!;
    const context = parseReferenceDataContext(new URLSearchParams(href.split('?')[1]));
    expect(context.referenceId).toBe('sp500');
    const returned = new URL(context.returnTo, 'https://workspace.test');
    expect(returned.pathname).toBe('/market-charts');
    expect(Object.fromEntries(returned.searchParams)).toEqual({
      view: 'overview',
      end: '2026-10-04',
      period: '6',
      field: 'ADJUSTED_CLOSE',
    });
  });
});
