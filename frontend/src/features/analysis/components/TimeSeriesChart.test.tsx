import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { vi, describe, it, expect } from 'vitest';
import { chartIdentity, chartSeries, comparison } from '../../../test/chartFixtures';
import { TimeSeriesChart } from './TimeSeriesChart';
// jsdom has no layout; the real SVG interactions are covered by Playwright.
vi.mock('recharts', async (original) => ({
  ...(await original<typeof import('recharts')>()),
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

function show(value = comparison()) {
  return render(
    <MemoryRouter>
      <TimeSeriesChart result={value} />
    </MemoryRouter>,
  );
}
describe('TimeSeriesChart', () => {
  it('uses backend values and exposes accessible sources without inventing timestamps', async () => {
    const user = userEvent.setup();
    show();
    expect(screen.getByText(/Einheit: Indexpunkte/)).toBeInTheDocument();
    await user.click(screen.getByText(/Datentabelle und Quellen/));
    expect(screen.getAllByText('Unbekannt')).toHaveLength(3);
    expect(screen.getByRole('columnheader', { name: 'Empfangen (UTC)' })).toBeInTheDocument();
    expect(screen.getAllByRole('cell', { name: '120' })).toHaveLength(2);
    await user.selectOptions(screen.getByLabelText('Darstellung'), 'change_percent');
    expect(screen.getByText(/Einheit: %/)).toBeInTheDocument();
  });
  it('switches single series and legend independently from stored comparisons', async () => {
    const user = userEvent.setup();
    const result = comparison([
      chartSeries(),
      chartSeries(chartIdentity('listing:energy', 'TEST ETF', 'ETF')),
    ]);
    show(result);
    await user.selectOptions(screen.getByLabelText('Einzelserie'), '1');
    expect(screen.getByText(/Einheit: USD/)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Darstellung'), 'normalized');
    await user.click(screen.getByRole('checkbox', { name: '2. TEST ETF' }));
    expect(screen.getByRole('checkbox', { name: '2. TEST ETF' })).not.toBeChecked();
    expect(result.series[1].points[2].normalized).toBe('120');
  });
  it('explains unavailable comparison and empty values but permits absolute inspection', async () => {
    const user = userEvent.setup();
    show({ ...comparison(), comparison_status: 'INVALID_START_VALUE' });
    expect(screen.getByRole('status')).toHaveTextContent('gültiger positiver Startwert');
    await user.selectOptions(screen.getByLabelText('Darstellung'), 'normalized');
    expect(screen.queryByTestId('time-series-chart')).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Darstellung'), 'value');
    expect(screen.getByTestId('time-series-chart')).toBeInTheDocument();
  });
  it('paginates table and changes table series', async () => {
    const user = userEvent.setup();
    const item = chartSeries();
    item.points = Array.from({ length: 55 }, (_, index) => ({
      ...item.points[0],
      trading_date: new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10),
      value: String(index + 1),
    }));
    show(comparison([item, chartSeries(chartIdentity('listing:b', 'SECOND', 'ETF'))]));
    await user.click(screen.getByText(/Datentabelle und Quellen/));
    await user.click(screen.getByRole('button', { name: 'Weitere Werte' }));
    expect(screen.getByText('Seite 2 / 2')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Vorige Werte' }));
    await user.selectOptions(screen.getByLabelText('Tabellenserie'), '1');
    expect(screen.getByText('Seite 1 / 1')).toBeInTheDocument();
  });
});
