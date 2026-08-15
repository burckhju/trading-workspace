import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../services/client';
import { IssuerAdminPage } from './IssuerAdminPage';

vi.mock('../services/client', () => ({
  marketApiClient: {
    listIssuersForAdmin: vi.fn(),
    createIssuer: vi.fn(),
    updateIssuer: vi.fn(),
    deactivateIssuer: vi.fn(),
    reactivateIssuer: vi.fn(),
  },
}));

const client = vi.mocked(marketApiClient);
const issuer = {
  id: '00000000-0000-4000-8001-000000000101',
  legal_name: 'Société Générale S.A.',
  display_name: 'Société Générale',
  country_code: 'FR',
  lei: 'O2RNE8IBXP4R0TD8PU41',
  is_active: true,
  version: 3,
  created_at: '2026-08-15T04:00:00Z',
  updated_at: '2026-08-15T04:00:00Z',
};

describe('IssuerAdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    client.listIssuersForAdmin.mockResolvedValue({ items: [issuer] });
    client.createIssuer.mockResolvedValue(issuer);
    client.updateIssuer.mockResolvedValue({ ...issuer, version: 4 });
    client.deactivateIssuer.mockResolvedValue({ ...issuer, is_active: false, version: 4 });
    client.reactivateIssuer.mockResolvedValue({ ...issuer, version: 4 });
  });

  it('keeps issuer maintenance in a dedicated administration surface', async () => {
    render(<IssuerAdminPage />);
    expect(await screen.findByText('Société Générale')).toBeInTheDocument();
    expect(
      screen.getByText(/technische IDs oder Versionen müssen nicht eingegeben werden/),
    ).toBeInTheDocument();
  });

  it('creates an issuer with optional external reference data', async () => {
    client.listIssuersForAdmin.mockResolvedValue({ items: [] });
    render(<IssuerAdminPage />);

    fireEvent.change(screen.getByLabelText('Juristischer Name'), { target: { value: 'UBS AG' } });
    fireEvent.change(screen.getByLabelText('Anzeigename'), { target: { value: 'UBS' } });
    fireEvent.change(screen.getByLabelText('Land'), { target: { value: 'ch' } });
    fireEvent.click(screen.getByRole('button', { name: 'Emittent anlegen' }));

    await waitFor(() =>
      expect(client.createIssuer).toHaveBeenCalledWith({
        legal_name: 'UBS AG',
        display_name: 'UBS',
        country_code: 'CH',
        lei: null,
      }),
    );
  });

  it('uses the stored version for lifecycle changes instead of asking the admin', async () => {
    render(<IssuerAdminPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Deaktivieren' }));
    await waitFor(() => expect(client.deactivateIssuer).toHaveBeenCalledWith(issuer.id, 3));
  });
  it('updates issuer master data without exposing technical identifiers', async () => {
    render(<IssuerAdminPage />);

    fireEvent.click(await screen.findByRole('button', { name: 'Bearbeiten' }));

    fireEvent.change(screen.getByLabelText('Anzeigename'), {
      target: { value: 'Société Générale Markets' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Änderungen speichern' }));

    await waitFor(() =>
      expect(client.updateIssuer).toHaveBeenCalledWith(issuer.id, {
        legal_name: issuer.legal_name,
        display_name: 'Société Générale Markets',
        country_code: issuer.country_code,
        lei: issuer.lei,
        expected_version: 3,
      }),
    );
  });


  it('reactivates an inactive issuer using the stored version', async () => {
    const inactiveIssuer = { ...issuer, is_active: false };
    client.listIssuersForAdmin.mockResolvedValue({ items: [inactiveIssuer] });
    render(<IssuerAdminPage />);

    fireEvent.click(await screen.findByRole('button', { name: 'Reaktivieren' }));

    await waitFor(() =>
      expect(client.reactivateIssuer).toHaveBeenCalledWith(inactiveIssuer.id, 3),
    );
  });

});
