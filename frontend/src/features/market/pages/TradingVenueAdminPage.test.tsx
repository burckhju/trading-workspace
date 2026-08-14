import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../services/client';
import { TradingVenueAdminPage } from './TradingVenueAdminPage';

vi.mock('../services/client', () => ({
  marketApiClient: {
    listTradingVenuesForAdmin: vi.fn(),
    createTradingVenue: vi.fn(),
    updateTradingVenue: vi.fn(),
    deactivateTradingVenue: vi.fn(),
    reactivateTradingVenue: vi.fn(),
  },
}));

const client = vi.mocked(marketApiClient);
const venue = {
  id: '00000000-0000-4000-8001-000000000001',
  mic: 'XETR',
  name: 'Xetra',
  country_code: 'DE',
  timezone: 'Europe/Berlin',
  reference_version: 'FT002_MANUAL_V1',
  is_active: true,
  version: 1,
  created_at: '2026-08-13T12:00:00Z',
  updated_at: '2026-08-13T12:00:00Z',
};

describe('TradingVenueAdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    client.listTradingVenuesForAdmin.mockResolvedValue({ items: [venue] });
    client.createTradingVenue.mockResolvedValue(venue);
    client.updateTradingVenue.mockResolvedValue({ ...venue, version: 2 });
    client.deactivateTradingVenue.mockResolvedValue({ ...venue, is_active: false, version: 2 });
    client.reactivateTradingVenue.mockResolvedValue({ ...venue, version: 2 });
  });

  it('shows active and inactive venues only in the dedicated admin surface', async () => {
    render(<TradingVenueAdminPage />);
    expect(await screen.findByText('Xetra')).toBeInTheDocument();
    expect(screen.getByText('Aktiv')).toBeInTheDocument();
    expect(client.listTradingVenuesForAdmin).toHaveBeenCalledOnce();
  });

  it('creates a venue with only the minimal reference-data inputs', async () => {
    client.listTradingVenuesForAdmin.mockResolvedValue({ items: [] });
    render(<TradingVenueAdminPage />);

    fireEvent.change(screen.getByLabelText('MIC'), { target: { value: 'xetr' } });
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Xetra' } });
    fireEvent.click(screen.getByRole('button', { name: 'Handelsplatz anlegen' }));

    await waitFor(() =>
      expect(client.createTradingVenue).toHaveBeenCalledWith({
        mic: 'XETR',
        name: 'Xetra',
        country_code: 'DE',
        timezone: 'Europe/Berlin',
      }),
    );
  });

  it('uses the current version when deactivating instead of asking the admin for it', async () => {
    render(<TradingVenueAdminPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Deaktivieren' }));
    await waitFor(() => expect(client.deactivateTradingVenue).toHaveBeenCalledWith(venue.id, 1));
  });
});
