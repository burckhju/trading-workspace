import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, it, expect, vi } from 'vitest';
import { chartCatalog } from '../../../test/chartFixtures';
import { chartClient } from '../services/chartClient';
import { chartSetupClient } from '../services/chartSetupClient';
import { topDownAdminClient } from '../../administration/services/topDownAdminClient';
import { marketApiClient } from '../../market/services/client';
import { ChartSetupPage } from './ChartSetupPage';
vi.mock('../services/chartClient', () => ({ chartClient: { catalog: vi.fn(), clear: vi.fn() } }));
vi.mock('../services/chartSetupClient', () => ({
  chartSetupClient: { proposals: vi.fn(), write: vi.fn() },
}));
vi.mock('../../administration/services/topDownAdminClient', () => ({
  topDownAdminClient: {
    mappings: vi.fn(),
    createMapping: vi.fn(),
    validateMapping: vi.fn(),
    venueReconciliation: vi.fn(),
    importHistory: vi.fn(),
  },
}));
vi.mock('../../market/services/client', () => ({ marketApiClient: { getUnderlying: vi.fn() } }));
vi.mock('../components/UnderlyingSearchCombobox', () => ({
  UnderlyingSearchCombobox: ({ onChange }: { onChange: (id: string) => void }) => (
    <button type="button" onClick={() => onChange('stock')}>
      ETF auswählen
    </button>
  ),
}));
beforeEach(() => {
  vi.mocked(topDownAdminClient.venueReconciliation).mockResolvedValue({
    status: 'AMBIGUOUS',
    listing_venue_id: 'venue',
    evidence_venue_ids: ['venue', 'other'],
    explanation: 'Provider-Code umfasst mehrere Handelsplätze.',
  });
  vi.mocked(chartClient.catalog).mockResolvedValue(chartCatalog());
  vi.mocked(chartSetupClient.proposals).mockResolvedValue([
    {
      code: '10',
      sector: 'Energy',
      benchmark: 'Energy Select Sector Index',
      ticker: 'XLE',
      isin: 'US81369Y5069',
      mic: 'ARCX',
      currency: 'USD',
      source_url: 'https://example.test/etf',
      classification_system: 'GICS',
      classification_version: 'v1',
      reviewed_on: '2026-10-04',
      taxonomy_source: 'https://example.test/gics',
      venue_source: 'https://example.test/mic',
      provider_coverage: 'NOT_VERIFIED',
    },
  ]);
  vi.mocked(chartSetupClient.write).mockResolvedValue({ id: 'new' });
  vi.mocked(topDownAdminClient.mappings).mockResolvedValue([
    {
      id: 'm',
      listing_id: 'listing',
      status: 'ACTIVE',
      provider_symbol: 'XLE',
      provider_exchange_code: 'US',
    },
  ]);
  vi.mocked(marketApiClient.getUnderlying).mockResolvedValue({
    id: 'stock',
    type: 'ETF',
    listings: [
      {
        id: 'listing',
        ticker: 'XLE',
        trading_venue_mic: 'ARCX',
        currency_code: 'USD',
        is_primary: true,
      },
    ],
  } as Awaited<ReturnType<typeof marketApiClient.getUnderlying>>);
});
function show() {
  render(
    <MemoryRouter>
      <ChartSetupPage />
    </MemoryRouter>,
  );
}
async function confirm(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('checkbox'));
  await user.click(screen.getByRole('button', { name: 'Geprüften Schritt ausführen' }));
}
it('performs no mutation until a reviewed step is confirmed', async () => {
  const user = userEvent.setup();
  show();
  await screen.findByText('US81369Y5069');
  expect(screen.getByRole('button', { name: 'Geprüften Schritt ausführen' })).toBeDisabled();
  expect(chartSetupClient.write).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Sektorformular vorbereiten' }));
  expect(screen.getByLabelText('Klassifikationssystem')).toHaveValue('GICS');
  await confirm(user);
  await waitFor(() =>
    expect(chartSetupClient.write).toHaveBeenCalledWith('sectors', {
      code: '10',
      name: 'Energy',
      classification_system: 'GICS',
      classification_version: 'v1',
    }),
  );
  expect(await screen.findByRole('status')).toHaveTextContent('Schritt gespeichert');
  expect(screen.getByRole('checkbox')).not.toBeChecked();
});
it.each([
  'bootstrap',
  'reference',
  'sectorReference',
  'proxy',
  'stockSector',
  'stockMarket',
  'referenceMapping',
  'referenceValidate',
  'basis',
  'referenceImport',
  'listingMapping',
  'listingValidate',
  'listingImport',
])('submits explicit %s via existing contracts', async (action) => {
  const user = userEvent.setup();
  show();
  await screen.findByText('US81369Y5069');
  if (action === 'reference')
    await user.click(screen.getByRole('button', { name: 'Benchmarkformular vorbereiten' }));
  else await user.selectOptions(screen.getByLabelText('Aktion'), action);
  const ref = screen.queryByLabelText(/Markt- \/ Sektor-Benchmark/);
  if (ref) await user.selectOptions(ref, 'sp500');
  const sector = screen.queryByLabelText('Administrierter Sektor');
  if (sector) await user.selectOptions(sector, 'Energy');
  const underlying = screen.queryByRole('button', { name: 'ETF auswählen' });
  if (underlying) {
    await user.click(underlying);
    await waitFor(() => expect(marketApiClient.getUnderlying).toHaveBeenCalled());
  }
  const source = screen.queryByLabelText('Quellenbeleg (HTTPS)');
  if (source) await user.type(source, 'https://example.test/evidence');
  const symbol = screen.queryByLabelText('Geprüftes EODHD-Symbol');
  if (symbol) {
    await user.type(symbol, 'XLE');
    await user.type(screen.getByLabelText('Geprüfter EODHD-Exchange-Code'), 'US');
  }
  await confirm(user);
  await waitFor(() => expect(chartClient.clear).toHaveBeenCalled());
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  if (action === 'listingValidate') {
    expect(topDownAdminClient.venueReconciliation).toHaveBeenCalledWith('m');
    expect(screen.getByText(/Provider-Code umfasst mehrere Handelsplätze/)).toBeInTheDocument();
  }
});
it('retains errors for a deliberate retry', async () => {
  const user = userEvent.setup();
  vi.mocked(chartSetupClient.write).mockRejectedValueOnce(new Error('Mapping nicht aktiv'));
  show();
  await screen.findByText('US81369Y5069');
  await confirm(user);
  expect(await screen.findByRole('alert')).toHaveTextContent('Mapping nicht aktiv');
  expect(chartClient.clear).not.toHaveBeenCalled();
});
