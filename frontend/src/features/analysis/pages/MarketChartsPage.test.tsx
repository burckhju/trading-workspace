import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, it, expect, vi } from 'vitest';
import { chartCatalog, comparison, chartIdentity } from '../../../test/chartFixtures';
import { chartClient } from '../services/chartClient';
import { MarketChartsPage } from './MarketChartsPage';
vi.mock('../services/chartClient', () => ({
  chartClient: { catalog: vi.fn(), series: vi.fn(), underlying: vi.fn() },
}));
vi.mock('../components/UnderlyingSearchCombobox', () => ({
  UnderlyingSearchCombobox: () => <div>Basiswertauswahl</div>,
}));
vi.mock('../components/TimeSeriesChart', () => ({ TimeSeriesChart: () => <div>Kursverlauf</div> }));
function show(url = '/market-charts?end=2026-10-04') {
  render(
    <MemoryRouter initialEntries={[url]}>
      <MarketChartsPage />
    </MemoryRouter>,
  );
}
beforeEach(() => {
  vi.mocked(chartClient.catalog).mockResolvedValue(chartCatalog());
  vi.mocked(chartClient.series).mockResolvedValue(comparison());
});
describe('MarketChartsPage', () => {
  it('opens SP500, lists multiple sectors and missing setup, and queries bounded periods', async () => {
    const user = userEvent.setup();
    show();
    await screen.findByText('Kursverlauf');
    expect(chartClient.series).toHaveBeenLastCalledWith(
      ['reference:sp500'],
      '2026-07-04',
      '2026-10-04',
      'CLOSE',
      expect.any(AbortSignal),
    );
    expect(screen.getByRole('rowheader', { name: /Industrials/ })).toBeInTheDocument();
    expect(screen.getByText(/Sektorreferenz fehlt/)).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: 'Vergleichen' })[0]);
    await waitFor(() =>
      expect(chartClient.series).toHaveBeenLastCalledWith(
        ['reference:sp500', 'listing:Energy'],
        '2026-07-04',
        '2026-10-04',
        'CLOSE',
        expect.any(AbortSignal),
      ),
    );
    await user.selectOptions(screen.getByLabelText('Zeitraum'), 'all');
    await waitFor(() =>
      expect(chartClient.series).toHaveBeenLastCalledWith(
        expect.any(Array),
        null,
        '2026-10-04',
        'CLOSE',
        expect.any(AbortSignal),
      ),
    );
    await user.selectOptions(screen.getByLabelText('Preisgrundlage'), 'ADJUSTED_CLOSE');
    await waitFor(() =>
      expect(chartClient.series).toHaveBeenLastCalledWith(
        expect.any(Array),
        null,
        '2026-10-04',
        'ADJUSTED_CLOSE',
        expect.any(AbortSignal),
      ),
    );
  });
  it('uses backend assignments for stock comparison and explains missing assignments', async () => {
    vi.mocked(chartClient.underlying).mockResolvedValue({
      underlying_id: 'stock',
      subject: chartIdentity('listing:stock', 'Stock', 'STOCK'),
      market: chartIdentity(),
      sector: null,
      issues: ['NO_UNAMBIGUOUS_SECTOR_REFERENCE'],
      assignment_date: '2026-10-04',
    });
    show('/market-charts?underlying=stock&end=2026-10-04');
    expect(await screen.findByText(/Sektorvergleich fehlt/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mit zugeordnetem/ })).toBeDisabled();
    await waitFor(() =>
      expect(chartClient.series).toHaveBeenLastCalledWith(
        ['listing:stock'],
        expect.any(String),
        '2026-10-04',
        'CLOSE',
        expect.any(AbortSignal),
      ),
    );
  });
  it('retains catalog errors and rejects excessive visual series', async () => {
    vi.mocked(chartClient.catalog).mockRejectedValueOnce(new Error('Übersicht fehlgeschlagen'));
    show();
    expect(await screen.findByRole('alert')).toHaveTextContent('Übersicht fehlgeschlagen');
  });
  it('does not crash on malformed period in shared URLs', async () => {
    show('/market-charts?period=bad&end=2026-10-04');
    await screen.findByText('Kursverlauf');
    expect(chartClient.series).toHaveBeenLastCalledWith(
      expect.any(Array),
      '2026-07-04',
      '2026-10-04',
      'CLOSE',
      expect.any(AbortSignal),
    );
  });
});
