import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { warrantApiClient } from '../services/client';
import { WarrantAdminPageWithDelete } from './WarrantAdminPageWithDelete';

vi.mock('../services/client', () => ({
  warrantApiClient: {
    list: vi.fn(),
    delete: vi.fn(),
  },
}));
vi.mock('./WarrantAdminPage', () => ({
  WarrantAdminPage: () => <div>Optionsschein-Verwaltung</div>,
}));

const warrants = vi.mocked(warrantApiClient);
const warrant = {
  id: '00000000-0000-4000-8001-000000000401',
  workspace_id: '00000000-0000-4000-8000-000000000001',
  issuer_id: '00000000-0000-4000-8001-000000000301',
  underlying_id: '00000000-0000-4000-8001-000000000201',
  product_family: 'WARRANT' as const,
  display_name: 'Siemens Call 180 12/2026',
  isin: 'DE000TEST001',
  wkn: 'TEST01',
  lifecycle_status: 'ACTIVE' as const,
  version: 4,
  created_at: '2026-08-15T12:00:00Z',
  updated_at: '2026-08-15T12:00:00Z',
};

beforeEach(() => {
  vi.clearAllMocks();
  warrants.list.mockResolvedValue([warrant]);
  warrants.delete.mockResolvedValue(undefined);
});

describe('WarrantAdminPageWithDelete', () => {
  it('loads delete candidates lazily and deletes only after explicit confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<WarrantAdminPageWithDelete />);

    expect(warrants.list).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Löschverwaltung öffnen' }));

    expect(await screen.findByRole('option', { name: /Siemens Call 180 12\/2026/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Endgültig löschen' }));

    await waitFor(() => expect(warrants.delete).toHaveBeenCalledWith(warrant.id, 4));
    expect(screen.getByRole('status')).toHaveTextContent('wurde gelöscht');
  });

  it('does not delete when confirmation is declined', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<WarrantAdminPageWithDelete />);
    fireEvent.click(screen.getByRole('button', { name: 'Löschverwaltung öffnen' }));
    await screen.findByRole('option', { name: /Siemens Call 180 12\/2026/ });

    fireEvent.click(screen.getByRole('button', { name: 'Endgültig löschen' }));

    expect(warrants.delete).not.toHaveBeenCalled();
  });
});
