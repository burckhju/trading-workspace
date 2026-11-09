import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { chartCatalog } from '../../../test/chartFixtures';
import { watchlistSeries } from '../../../test/watchlistFixtures';
import { chartClient } from '../services/chartClient';
import { saveChartViewPreferences } from '../services/chartViewPreferences';
import { MarketChartsPage } from './MarketChartsPage';

vi.mock('../services/chartClient', () => ({
  chartClient: { catalog: vi.fn(), series: vi.fn(), underlying: vi.fn() },
}));
vi.mock('../components/UnderlyingSearchCombobox', () => ({
  UnderlyingSearchCombobox: () => <div>Bestehende Basiswertauswahl</div>,
}));
vi.mock('../components/TimeSeriesChart', () => ({
  TimeSeriesChart: () => <div>Bestehendes Detaildiagramm</div>,
}));
vi.mock('../components/ChartWatchlistOverview', () => ({
  ChartWatchlistOverview: ({
    end,
    period,
    field,
    onOpenDetail,
  }: {
    end: string;
    period: string;
    field: string;
    onOpenDetail: (targets: string[]) => void;
  }) => (
    <section aria-label="Gespeicherte Marktübersicht">
      <p>
        {end} · {period} · {field}
      </p>
      <button onClick={() => onOpenDetail(['listing:etf-1'])}>Testreihe im Detail öffnen</button>
    </section>
  ),
}));

beforeEach(() => {
  window.localStorage.clear();
  vi.mocked(chartClient.catalog).mockResolvedValue(chartCatalog());
  vi.mocked(chartClient.series).mockImplementation((keys, start, end, field) =>
    Promise.resolve(watchlistSeries(keys[0], start, end, field)),
  );
});
afterEach(() => vi.useRealTimers());

function show(url = '/market-charts') {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <MarketChartsPage />
    </MemoryRouter>,
  );
}

describe('MarketChartsPage overview integration', () => {
  it('opens the durable overview by default without starting a duplicate detail read', async () => {
    const user = userEvent.setup();
    show();
    expect(screen.getByRole('region', { name: 'Gespeicherte Marktübersicht' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Marktübersicht' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(chartClient.catalog).not.toHaveBeenCalled();
    expect(chartClient.series).not.toHaveBeenCalled();
    await user.selectOptions(screen.getByLabelText('Zeitraum'), '12');
    expect(screen.getByRole('region', { name: 'Gespeicherte Marktübersicht' })).toHaveTextContent(
      '12 · CLOSE',
    );
    expect(chartClient.series).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Testreihe im Detail öffnen' }));
    expect(await screen.findByText('Bestehendes Detaildiagramm')).toBeInTheDocument();
    expect(chartClient.series).toHaveBeenLastCalledWith(
      ['listing:etf-1'],
      expect.any(String),
      expect.any(String),
      'CLOSE',
      expect.any(AbortSignal),
    );
  });

  it('keeps explicit historical URLs and price fields ahead of saved presentation', async () => {
    saveChartViewPreferences({
      period: '36',
      field: 'ADJUSTED_CLOSE',
      display: { mode: 'change_percent', singleKey: null, hiddenKeys: [] },
    });
    show('/market-charts?target=reference:sp500&end=2026-10-04&period=3&field=CLOSE');
    expect(
      screen.queryByRole('region', { name: 'Gespeicherte Marktübersicht' }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText('Enddatum')).toHaveValue('2026-10-04');
    await waitFor(() =>
      expect(chartClient.series).toHaveBeenCalledWith(
        ['reference:sp500'],
        '2026-07-04',
        '2026-10-04',
        'CLOSE',
        expect.any(AbortSignal),
      ),
    );
  });

  it('retains saved period and field after a fresh mount without freezing today', () => {
    saveChartViewPreferences({
      period: '6',
      field: 'ADJUSTED_CLOSE',
      display: { mode: null, singleKey: null, hiddenKeys: [] },
    });
    show();
    expect(screen.getByLabelText('Zeitraum')).toHaveValue('6');
    expect(screen.getByLabelText('Preisgrundlage')).toHaveValue('ADJUSTED_CLOSE');
    expect(screen.getByText('Rollierendes Enddatum: heute (UTC)')).toBeInTheDocument();
  });

  it('advances the rolling UTC day and offers an explicit return from a fixed historical day', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-11-09T23:59:00Z'));
    const timers = vi.spyOn(window, 'setInterval');
    const rendered = show();
    expect(screen.getByLabelText('Enddatum')).toHaveValue('2026-11-09');
    vi.setSystemTime(new Date('2026-11-10T00:01:00Z'));
    const tick = timers.mock.calls.find(([, interval]) => interval === 60_000)![0] as () => void;
    act(() => tick());
    expect(screen.getByLabelText('Enddatum')).toHaveValue('2026-11-10');
    rendered.unmount();
    const user = userEvent.setup();
    show('/market-charts?view=overview&end=2026-10-04');
    expect(screen.getByLabelText('Enddatum')).toHaveValue('2026-10-04');
    await user.click(screen.getByRole('button', { name: 'Bis heute fortführen' }));
    expect(screen.getByLabelText('Enddatum')).toHaveValue('2026-11-10');
    expect(screen.getByRole('region', { name: 'Gespeicherte Marktübersicht' })).toBeInTheDocument();
  });
});
